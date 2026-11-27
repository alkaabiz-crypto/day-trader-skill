#!/usr/bin/env python3
"""Buy low, sell high: a mean-reversion version of the crypto/forex bot, backtested on its own 2 years of
hourly data. A backtest only: the live bot (bot.py) is not changed.

    python3 fx_meanrev.py run [--write] [--placebo 50]

PRE-REGISTERED 2026-11-26 (the owner asked "why don't you buy low and sell high"), committed before any run:
  Markets, data: the bot's list (fxcrypto.CRYPTO + FOREX, incl. gold and silver), data/fx1h, 1-hour bars.
  Signal on a completed hour (Wilder RSI(14) of the close):
    buy  when RSI crosses below 30 (the price fell hard: buy low)
    sell when RSI crosses above 70 (the price rose hard: sell high, i.e. go short)
  Variants (3, fixed):
    rsi_bot     the bot's own exits: stop 1.5 x ATR(14), target 2R, out after 24 hours
    rsi_mean    stop 1.5 x ATR(14), target = the 20-hour average at entry (the "mean"), out after 24 hours
    band_mean   Bollinger instead of RSI: buy a close below the 20-hour average - 2 sd, sell a close above
                + 2 sd (new crossings only); stop 1.5 x ATR(14), target the 20-hour average, 24 hours
  Same as the live bot: $10 risk a trade at the stop, next-hour-open fills, stop first when a bar hits both,
    Exness costs (bot.cost_bps + bot.swap_bps per 00:00 UTC crossed), up to 2 new trades an hour, the
    group cap (bot.GROUP_CAP) and at most bot.FX["max_open"] open.
  PASS (each variant): daily t >= 2.4 (Bonferroni for 3 at 5% two-sided), still positive at 2x costs, and
    beats 95% of random-direction placebos (same entries and exits, the side chosen by a coin).
  Compared with the live breakout rule's own backtest (bot_backtest.py: about -$1.27 a trade, t -8.1).
Research, not financial advice.
"""

import argparse
import datetime
import json
import os
import random
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bot  # noqa: E402
import bot_backtest as bb  # noqa: E402

VARIANTS = ("rsi_bot", "rsi_mean", "band_mean")
T_BAR = 2.4
RESULT = os.path.join(HERE, "results", "fx-meanrev.json")


def rsi14(c, n=14):
    out = np.full(len(c), np.nan)
    if len(c) <= n:
        return out
    d = np.diff(c)
    up, dn = np.maximum(d, 0), np.maximum(-d, 0)
    au, ad = up[:n].mean(), dn[:n].mean()
    for i in range(n, len(c)):
        if i > n:
            au = (au * (n - 1) + up[i - 1]) / n
            ad = (ad * (n - 1) + dn[i - 1]) / n
        out[i] = 100.0 if ad == 0 else 100 - 100 / (1 + au / ad)
    return out


def signals(a, variant):
    """-> (buy_new, sell_new, sma20) arrays for bar i (its close)."""
    c = a[:, 4]
    n = len(c)
    buy = np.zeros(n, bool)
    sell = np.zeros(n, bool)
    sma = np.full(n, np.nan)
    sd = np.full(n, np.nan)
    for i in range(19, n):
        w = c[i - 19:i + 1]
        sma[i], sd[i] = w.mean(), w.std(ddof=1)
    if variant.startswith("rsi"):
        r = rsi14(c)
        for i in range(1, n):
            if np.isnan(r[i]) or np.isnan(r[i - 1]):
                continue
            buy[i] = r[i] < 30 <= r[i - 1]
            sell[i] = r[i] > 70 >= r[i - 1]
    else:
        lo, hi = sma - 2 * sd, sma + 2 * sd
        for i in range(20, n):
            buy[i] = c[i] < lo[i] and not c[i - 1] < lo[i - 1]
            sell[i] = c[i] > hi[i] and not c[i - 1] > hi[i - 1]
    return buy, sell, sma


def run(data, variant, cost_mult=1.0, rng=None):
    sig = {s: signals(a, variant) for s, a in data.items()}
    idx = {s: {int(t): i for i, t in enumerate(a[:, 0])} for s, a in data.items()}
    hours = sorted({int(t) for a in data.values() for t in a[:, 0]})
    open_, trades = [], []
    for T in hours:
        open_ = [x for x in open_ if x[0] > T]
        dt = datetime.datetime.fromtimestamp(T + 3600, datetime.timezone.utc)
        cands = []
        for s, a in data.items():
            i = idx[s].get(T)
            if i is None or i < 40 or i + 1 >= len(a):
                continue
            b, sl, _ = sig[s]
            side = "buy" if b[i] else "sell" if sl[i] else None
            if side:
                chg = a[i, 4] / a[i - 1, 4] - 1
                cands.append((-abs(chg), s, side, i))
        room = min(bot.FX["per_run"], bot.FX["max_open"] - len(open_))
        new = 0
        for _, s, side, i in sorted(cands):
            if new >= room:
                break
            if any(o[1] == s for o in open_):
                continue
            g = bb.group(s)
            if sum(1 for o in open_ if bb.group(o[1]) == g) >= bot.GROUP_CAP[g]:
                continue
            if rng is not None:
                side = rng.choice(("buy", "sell"))
            a = data[s]
            p = bot.fx_plan(s, side, float(a[i, 4]), bb.atr_at(a, i))
            if not p:
                continue
            if variant != "rsi_bot":
                tgt = float(sig[s][2][i])
                if (side == "buy" and tgt <= p["entry_est"]) or (side == "sell" and tgt >= p["entry_est"]):
                    continue
                p["target"] = tgt
            bars = [tuple(r) for r in a[i + 1:i + 1 + 30]]
            got = bot.fill_hourly(bars, a[i + 1, 0], side, p["stop"], p["target"], 24, 1e18)
            if not got:
                continue
            e, x, how, t0, t1 = got
            nights = bot.nights(t0, t1)
            c_bps = cost_mult * (bb.cost_bps(s) + bb.swap_bps(s) * nights)
            trades.append({"day": dt.date().isoformat(), "sym": s, "side": side, "how": how, "group": g,
                           "pnl": bot.pnl_usd(side, e, x, p["notional_usd"], c_bps),
                           "gross": bot.pnl_usd(side, e, x, p["notional_usd"], 0.0)})
            open_.append((int(t1), s))
            new += 1
    return trades


def cmd_run(a):
    data = bb.load_fx()
    out = {"variants": {}}
    print("Buy low / sell high on the crypto/forex bot's markets, 2 years of 1-hour bars, Exness costs:")
    for v in VARIANTS:
        tr = run(data, v)
        st = bb.stats(tr)
        st["gross_usd"] = round(sum(t["gross"] for t in tr), 2)
        st["at_2x"] = bb.stats(run(data, v, cost_mult=2.0))["net_usd"]
        st["by_group"] = {g: bb.stats([t for t in tr if t["group"] == g]) for g in ("crypto", "forex", "metal")}
        rng = random.Random(5)
        nets = [sum(t["pnl"] for t in run(data, v, rng=rng)) for _ in range(a.placebo)]
        st["placebo_beats"] = round(sum(1 for x in nets if x < st["net_usd"]) / len(nets), 3) if nets else None
        st["verdict"] = "PASS" if (st["t_daily"] >= T_BAR and st["at_2x"] > 0 and (st["placebo_beats"] or 0) >= 0.95) \
            else "FAIL"
        out["variants"][v] = st
        print("  %-10s %5d trades  net $%+9.2f  ($%+.2f a trade, gross $%+.2f)  win %.0f%%  daily t %+.2f  "
              "2x cost $%+.2f  placebo %.0f%%  %s" % (v, st["trades"], st["net_usd"], st["per_trade"], st["gross_usd"],
                                                       100 * (st["win_rate"] or 0), st["t_daily"], st["at_2x"],
                                                       100 * (st["placebo_beats"] or 0), st["verdict"]), flush=True)
        for g, s in st["by_group"].items():
            print("      %-7s %5d trades  net $%+9.2f  daily t %+.2f" % (g, s["trades"], s["net_usd"], s["t_daily"]))
    print("The live breakout rule's own backtest: about -$1.27 a trade, daily t -8.1. Research, not financial advice.")
    if a.write:
        with open(RESULT, "w") as fh:
            json.dump(out, fh, indent=1)
        print("Wrote %s" % os.path.relpath(RESULT, HERE))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="buy low / sell high on the crypto/forex bot's markets")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("run")
    p.add_argument("--placebo", type=int, default=50)
    p.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd != "run":
        ap.print_help()
        return 1
    return cmd_run(a)


if __name__ == "__main__":
    sys.exit(main())
