#!/usr/bin/env python3
"""The crypto/forex bot's crypto rules on 7+ years of hourly candles (Binance spot, 2019 on), swap-free.

    python3 crypto_long.py fetch      # data-api.binance.vision 1-hour klines -> data/fx1h_long/ (gitignored)
    python3 crypto_long.py run [--write]

Why. The bot's backtest used Yahoo's 2 years of hourly bars, almost all of it a single market regime.
Binance's public market-data mirror (data-api.binance.vision, no key) has hourly candles since 2017-2020
for all 12 of the bot's coins (USDT pairs as stand-ins for the USD CFDs).

PRE-REGISTERED 2026-11-26, committed before any run. Not to be changed after the result:
  Markets: the bot's 12 coins (fxcrypto.CRYPTO) as Binance USDT pairs, 1-hour candles from 2019-01-01
    (or listing) to 2026-11-25. Forex and metals are not on Binance and are left out.
  Rules, unchanged and run by the same code:
    breakout   the live bot (bot_backtest.run_fx, variant "groupcap": the bot's own caps, sizing, ATR stop,
               2R target, 24-hour exit)
    rsi_bot / rsi_mean / band_mean   the three buy-low/sell-high variants (fx_meanrev.run)
  Costs: Exness spreads (bot.cost_bps: BTC/ETH 6 bp, other coins 15 bp a round trip) and NO swap (the
    owner's swap-free account).
  Judged: daily t over the whole period and per calendar year. PASS (backtest only): daily t >= 3 and
    positive in at least 6 of the 8 years, and beats the random-direction placebo (20 draws) 95% of the time.
Research, not financial advice.
"""

import argparse
import datetime
import gzip
import json
import os
import random
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bot  # noqa: E402
import bot_backtest as bb  # noqa: E402
import fxcrypto  # noqa: E402
import numpy as np  # noqa: E402

STORE = os.path.join(HERE, "data", "fx1h_long")
URL = "https://data-api.binance.vision/api/v3/klines?symbol=%s&interval=1h&startTime=%d&limit=1000"
START = datetime.datetime(2019, 1, 1, tzinfo=datetime.timezone.utc)
END = datetime.datetime(2026, 11, 25, tzinfo=datetime.timezone.utc)
RESULT = os.path.join(HERE, "results", "crypto-long.json")


def pair(sym):
    return sym.split("-")[0] + "USDT"


def fetch_one(sym):
    t, end = int(START.timestamp() * 1000), int(END.timestamp() * 1000)
    rows = []
    while t < end:
        req = urllib.request.Request(URL % (pair(sym), t), headers={"User-Agent": "trader-lab"})
        for tries in range(6):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    k = json.loads(r.read().decode())
                break
            except (OSError, ValueError):
                if tries == 5:
                    raise
                time.sleep(5 * (tries + 1))
        if not k:
            break
        rows += [[x[0] / 1000.0, float(x[1]), float(x[2]), float(x[3]), float(x[4])] for x in k if x[0] < end]
        t = k[-1][0] + 3600 * 1000
        time.sleep(0.15)
    return rows


def cmd_fetch(a):
    os.makedirs(STORE, exist_ok=True)
    for s in fxcrypto.CRYPTO:
        p = os.path.join(STORE, s + ".json.gz")
        if os.path.exists(p):
            continue
        rows = fetch_one(s)
        with gzip.open(p, "wt") as fh:
            json.dump(rows, fh)
        print("  %-9s %s: %d hours from %s" % (s, pair(s), len(rows), datetime.datetime.fromtimestamp(
            rows[0][0], datetime.timezone.utc).date() if rows else "-"), flush=True)
    return 0


def load():
    out = {}
    for s in fxcrypto.CRYPTO:
        p = os.path.join(STORE, s + ".json.gz")
        if os.path.exists(p):
            with gzip.open(p, "rt") as fh:
                out[s] = np.array(json.load(fh), float)
    return out


def yearly(trades):
    by = {}
    for t in trades:
        by.setdefault(t["day"][:4], {}).setdefault(t["day"], 0.0)
        by[t["day"][:4]][t["day"]] += t["pnl"]
    return {y: {"net_usd": round(sum(v.values()), 2), "t": round(bb.t_daily(v), 2)} for y, v in sorted(by.items())}


def cmd_run(a):
    import fx_meanrev
    bb.swap_bps = lambda s: 0.0                 # swap-free
    data = load()
    print("Crypto, Binance 1-hour, %d coins, swap-free, Exness spreads:" % len(data), flush=True)
    out = {"coins": sorted(data), "rules": {}}
    runs = {"breakout": lambda rng=None: bb.run_fx(data, "groupcap", rng=rng)}
    for v in fx_meanrev.VARIANTS:
        runs[v] = (lambda v: lambda rng=None: fx_meanrev.run(data, v, rng=rng))(v)
    for name, fn in runs.items():
        tr = fn()
        st = bb.stats(tr)
        st["years"] = yearly(tr)
        rng = random.Random(3)
        nets = [sum(t["pnl"] for t in fn(rng)) for _ in range(a.placebo)]
        st["placebo_beats"] = round(sum(1 for x in nets if x < st["net_usd"]) / len(nets), 3) if nets else None
        pos = sum(1 for y in st["years"].values() if y["net_usd"] > 0)
        st["verdict"] = "PASS (backtest only)" if (st["t_daily"] >= 3 and pos >= 6 and
                                                   (st["placebo_beats"] or 0) >= 0.95) else "FAIL"
        out["rules"][name] = st
        print("  %-10s %6d trades  net $%+10.2f  ($%+.2f a trade)  win %.0f%%  daily t %+.2f  years + %d/%d  "
              "placebo %.0f%%  %s" % (name, st["trades"], st["net_usd"], st["per_trade"], 100 * (st["win_rate"] or 0),
                                      st["t_daily"], pos, len(st["years"]), 100 * (st["placebo_beats"] or 0),
                                      st["verdict"]), flush=True)
        print("      " + "  ".join("%s $%+.0f" % (y, v["net_usd"]) for y, v in st["years"].items()), flush=True)
    print("Research, not financial advice.")
    if a.write:
        with open(RESULT, "w") as fh:
            json.dump(out, fh, indent=1)
        print("Wrote %s" % os.path.relpath(RESULT, HERE))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="the bot's crypto rules on 7 years of Binance hourly candles")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("fetch")
    p = sub.add_parser("run")
    p.add_argument("--placebo", type=int, default=20)
    p.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    fn = {"fetch": cmd_fetch, "run": cmd_run}.get(a.cmd)
    if not fn:
        ap.print_help()
        return 1
    return fn(a)


if __name__ == "__main__":
    sys.exit(main())
