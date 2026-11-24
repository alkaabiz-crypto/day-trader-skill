#!/usr/bin/env python3
"""Data for the bot backtests (bot_backtest.py).

    python3 bot_data.py stocks     # every liquid US stock: 60 days of 5-minute bars (Yahoo's limit)
    python3 bot_data.py fxcrypto   # the 28 crypto / forex / metals names: 730 days of 1-hour bars

Stocks: the universe is trader/universe.txt (scan.py universe, about 5,900 US common stocks and
ADRs). Pre-filter: last price $5+ and 200,000+ shares so far today (spark, one request per 20 names); the
backtest then keeps names with a 60-day average of 1,000,000+ shares a day, the live scanner's floor. Each liquid name's 60-day 5-minute chart is saved to
data/wm5/<SYM>.json.gz as {ts: [o, h, l, c, v]} (lab.parse_chart, regular session only).
Resumable: names already saved today are skipped. Survivorship: the list is today's, so names
delisted in the last 60 days are missing (a small bias over 60 days).
FX / crypto: data/fx1h/<SYM>.json.gz as [[ts, o, h, l, c], ...] complete hours.
Research, not financial advice.
"""

import datetime
import gzip
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "trader-scanner"))
import lab  # noqa: E402
import scan  # noqa: E402
import fxcrypto  # noqa: E402

WM5 = os.path.join(HERE, "data", "wm5")
FX1H = os.path.join(HERE, "data", "fx1h")
MIN_PRICE, MIN_VOLUME, PREFILTER_VOLUME = 5.0, 1_000_000, 200_000


def universe():
    with open(os.path.join(ROOT, "trader", "universe.txt")) as fh:
        return [ln.split("|")[0].strip() for ln in fh if ln.strip() and not ln.startswith("#")]


def liquid(symbols):
    data, _ = scan.fetch_spark(symbols, "5d", "1d", 0.3)
    out = []
    for s, v in data.items():
        m = v.get("meta") or {}
        p = m.get("regularMarketPrice")
        vol = m.get("regularMarketVolume")
        # a generous pre-filter (during the session the volume is only partial); the backtest keeps
        # names whose 60-day average daily volume is 1M+ and price $5+, the live scanner's floor
        if p and vol and p >= MIN_PRICE and vol >= PREFILTER_VOLUME:
            out.append((p * vol, s))
    return [s for _, s in sorted(out, reverse=True)]


def fresh(path):
    return os.path.exists(path) and time.time() - os.path.getmtime(path) < 20 * 3600


def cmd_stocks():
    os.makedirs(WM5, exist_ok=True)
    syms = liquid(universe())
    with open(os.path.join(WM5, "_liquid.json"), "w") as fh:
        json.dump(syms, fh)
    print("%d liquid names" % len(syms), flush=True)
    done = bad = 0
    for i, s in enumerate(syms):
        p = os.path.join(WM5, s + ".json.gz")
        if fresh(p):
            done += 1
            continue
        try:
            bars = lab.parse_chart(lab.fetch_chart(s))
        except (lab.LabError, ValueError, KeyError, TypeError):
            bad += 1
            continue
        with gzip.open(p, "wt") as fh:
            json.dump({str(k): v for k, v in bars.items()}, fh)
        done += 1
        if i % 100 == 0:
            print("  %d / %d" % (i, len(syms)), flush=True)
        time.sleep(0.15)
    print("saved %d, failed %d" % (done, bad))


def cmd_fxcrypto():
    os.makedirs(FX1H, exist_ok=True)
    now = time.time()
    for s in fxcrypto.CRYPTO + fxcrypto.FOREX:
        doc = json.loads(scan.yahoo_get(scan.chart_path(s, "730d", "1h")))
        res = doc["chart"]["result"][0]
        q = res["indicators"]["quote"][0]
        rows = []
        for i, t in enumerate(res.get("timestamp") or []):
            o, h, l, c = (q[k][i] for k in ("open", "high", "low", "close"))
            if None in (o, h, l, c) or t + 3600 > now:
                continue
            rows.append([t, o, h, l, c])
        with gzip.open(os.path.join(FX1H, s + ".json.gz"), "wt") as fh:
            json.dump(rows, fh)
        print("  %-9s %d hours from %s" % (s, len(rows), datetime.datetime.utcfromtimestamp(rows[0][0]).date()
                                           if rows else "-"), flush=True)
        time.sleep(0.5)


if __name__ == "__main__":
    {"stocks": cmd_stocks, "fxcrypto": cmd_fxcrypto}[sys.argv[1]]()
