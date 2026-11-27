#!/usr/bin/env python3
"""The bots that platforms like AstraBit, 3Commas, Bybit and Bitget sell, backtested on Bitcoin with $500.

    python3 bot_types.py run [--write]   # needs candles.py fetch-crypto (BTC 5-minute bars) -> results/bot-types.json

PRE-REGISTERED 2026-11-25, committed before any of these was run. Not to be changed:
  Data: Tiingo BTC/USD 5-minute candles in data/candles/btcusd.json.gz, all that is stored at run time
    (Nov 2022 on). Fills happen inside a candle only if its high/low reaches the price; if one candle reaches both
    a buy-more level and the stop, or the target and the stop, the worse one counts. Fees 0.1% of each fill (a
    typical taker fee), plus each platform's own subscription is NOT charged (it would only make things worse).
  B1 DCA bot ("buy more on dips", the AstraBit Standard / 3Commas DCA design, with common default settings):
    a $100 first buy, then up to 4 more $100 buys when price falls 2%, 4%, 6% and 8% below the first buy. Sell
    everything when price is 2% above the average cost (take profit) or 15% below the first buy (stop loss).
    A new cycle starts at the open of the next candle. Uninvested cash earns nothing.
  B2 Grid bot (the Bybit / Bitget spot grid design): at the first candle of each calendar month, 10 price levels
    spaced evenly in % from 10% below to 10% above that price; $50 rests as a buy order at each level below the
    price; each filled buy places a sell one level higher (from the next candle on); a filled sell re-arms its buy.
    At the first candle of the next month everything held is sold at its open and a new grid is laid.
  Benchmark: $500 of BTC bought at the first candle and held.
  Split: in-sample = before 2024-01-01; judged = from 2024-01-01.
  Verdict per bot: PASS only if the judged daily return (on the $500 account) has t >= 3 AND the bot ends the judged
    period ahead of $500 of BTC held over the same days, and the in-sample t > 0.
Research, not financial advice.
"""

import argparse
import datetime
import gzip
import json
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import paper500 as p5  # noqa: E402

STORE = os.path.join(HERE, "data", "candles", "btcusd.json.gz")
RESULTS = os.path.join(HERE, "results")
FEE = 0.001
SPLIT, T_BAR, START = "2024-01-01", 3.0, 500.0
DCA = {"order": 100.0, "steps": [0.02, 0.04, 0.06, 0.08], "tp": 0.02, "sl": 0.15}
GRID = {"levels": 10, "span": 0.10, "per_level": 50.0}


def candles(path=STORE):
    with gzip.open(path, "rt") as fh:
        d = json.load(fh)
    out = []
    for k in sorted(d, key=int):
        o, h, l, c = d[k][:4]
        out.append((int(k), o, h, l, c))
    return out


def day(ts):
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%d")


def run_dca(bars, cfg=DCA, fee=FEE):
    """-> [(date, end-of-day account value)], trades count."""
    cash, coins, cost, first, filled = START, 0.0, 0.0, None, 0
    out, trades, last_day = [], 0, None
    pending_start = True
    for ts, o, h, l, c in bars:
        if pending_start and cash >= cfg["order"]:
            px = o
            q = cfg["order"] * (1 - fee) / px
            cash -= cfg["order"]
            coins, cost, first, filled = q, cfg["order"], px, 0
            pending_start = False
        if coins > 0:
            stop = first * (1 - cfg["sl"])
            levels = [first * (1 - s) for s in cfg["steps"]]
            # worst case inside a candle: buys at the levels it reaches, then the stop if reached
            while filled < len(levels) and l <= levels[filled] and cash >= cfg["order"]:
                px = levels[filled]
                coins += cfg["order"] * (1 - fee) / px
                cash -= cfg["order"]
                cost += cfg["order"]
                filled += 1
            avg = cost / coins * (1 - fee)
            tp = cost / coins / (1 - fee) * (1 + cfg["tp"])
            if l <= stop:
                cash += coins * min(stop, o) * (1 - fee)
                coins, trades, pending_start = 0.0, trades + 1, True
            elif h >= tp:
                cash += coins * max(tp, o) * (1 - fee)
                coins, trades, pending_start = 0.0, trades + 1, True
        d = day(ts)
        val = cash + coins * c
        if out and out[-1][0] == d:
            out[-1] = (d, val)
        else:
            out.append((d, val))
        last_day = d
    return out, trades


def run_grid(bars, cfg=GRID, fee=FEE):
    cash, out, trades = START, [], 0
    month, grid, held = None, [], {}
    for i, (ts, o, h, l, c) in enumerate(bars):
        m = day(ts)[:7]
        if m != month:
            # month change: sell all at this candle's open, then lay a new grid around it
            for lv, q in list(held.items()):
                cash += q * o * (1 - fee)
                trades += 1
            held = {}
            month = m
            n, span = cfg["levels"], cfg["span"]
            lo, hi = o * (1 - span), o * (1 + span)
            ratio = (hi / lo) ** (1.0 / (n - 1))
            grid = [lo * ratio ** k for k in range(n)]
            armed = {k: grid[k] < o for k in range(n)}       # a buy rests at each level below the price
        bought_now = set()
        for k in range(len(grid) - 1):
            if armed.get(k) and k not in held and l <= grid[k] and cash >= cfg["per_level"] * 0.999:
                spend = min(cfg["per_level"], cash)
                held[k] = spend * (1 - fee) / grid[k]
                cash -= spend
                armed[k] = False
                bought_now.add(k)
                trades += 1
        for k, q in list(held.items()):
            if k in bought_now:            # a level bought in this candle sells from the next candle on
                continue
            target = grid[k + 1]
            if h >= target:                # sell one level up
                cash += q * target * (1 - fee)
                del held[k]
                armed[k] = True
                trades += 1
        val = cash + sum(q * c for q in held.values())
        d = day(ts)
        if out and out[-1][0] == d:
            out[-1] = (d, val)
        else:
            out.append((d, val))
    return out, trades


def hold(bars):
    q = START / bars[0][1]
    out = []
    for ts, o, h, l, c in bars:
        d = day(ts)
        if out and out[-1][0] == d:
            out[-1] = (d, q * c)
        else:
            out.append((d, q * c))
    return out


def daily_returns(path):
    return [(path[i][0], path[i][1] / path[i - 1][1] - 1.0) for i in range(1, len(path))]


def judge(path, bench):
    r = daily_returns(path)
    a = [v for d, v in r if d < SPLIT]
    b = [v for d, v in r if d >= SPLIT]
    f = lambda x: {"days": len(x), "mean_pct_day": 100 * statistics.mean(x) if x else 0.0, "t": p5.tstat(x)}  # noqa: E731
    out = {"in_sample": f(a), "judged": f(b)}
    out["usd_judged"] = p5.dollars(path, SPLIT)
    out["btc_usd_judged"] = p5.dollars(bench, SPLIT)
    out["usd_all"], out["btc_usd_all"] = path[-1][1], bench[-1][1]
    worst = 0.0
    peak = path[0][1]
    for _, v in path:
        peak = max(peak, v)
        worst = max(worst, 1 - v / peak)
    out["max_drawdown_pct"] = 100 * worst
    beat = (out["usd_judged"] or 0) > (out["btc_usd_judged"] or 0)
    out["verdict"] = "PASS" if (out["judged"]["t"] >= T_BAR and out["in_sample"]["t"] > 0 and beat) else "FAIL"
    return out


def cmd_run(a):
    bars = candles()
    bench = hold(bars)
    res = {"first": day(bars[0][0]), "last": day(bars[-1][0]), "candles": len(bars)}
    for name, fn in (("B1_dca_bot", run_dca), ("B2_grid_bot", run_grid)):
        path, n = fn(bars)
        s = judge(path, bench)
        s["trades"] = n
        res[name] = s
        print("%s: %d trades | IS %+.3f%%/day t %+.2f | judged %+.3f%%/day t %+.2f | $500 -> $%.0f since 2024 "
              "(BTC held $%.0f); all $%.0f (BTC $%.0f); max drawdown %.0f%% -> %s" % (
                  name, n, s["in_sample"]["mean_pct_day"], s["in_sample"]["t"], s["judged"]["mean_pct_day"],
                  s["judged"]["t"], s["usd_judged"] or 0, s["btc_usd_judged"] or 0, s["usd_all"], s["btc_usd_all"],
                  s["max_drawdown_pct"], s["verdict"]))
    print("data %s to %s, %d candles" % (res["first"], res["last"], res["candles"]))
    if a.write:
        with open(a.write, "w") as fh:
            json.dump(res, fh, indent=1)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("run")
    r.add_argument("--write", nargs="?", const=os.path.join(RESULTS, "bot-types.json"))
    a = ap.parse_args(argv)
    return cmd_run(a) if a.cmd == "run" else ap.print_help() or 1


if __name__ == "__main__":
    sys.exit(main())
