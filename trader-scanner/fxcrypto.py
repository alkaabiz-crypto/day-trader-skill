#!/usr/bin/env python3
"""Hourly crypto and forex scan (24/7): the scanner's setup rules on 1-hour bars.

    python3 trader-scanner/fxcrypto.py              # print the table
    python3 trader-scanner/fxcrypto.py --json
    python3 trader-scanner/fxcrypto.py --symbols BTC-USD,EURUSD=X

Free Yahoo 1-hour bars (spark, 10 days). Only COMPLETE hours are used: the bar still forming is
dropped. The same five rules as the daily scan, read in hours instead of days:
20-hour closing-high breakout, bull flag, reclaimed the 20-hour average, oversold (RSI under 30),
oversold bounce; plus their short mirrors (20-hour closing-low breakdown, overbought RSI over 70).
Also the 1-hour and 24-hour moves. Writes trader/fxcrypto.json unless --no-write.

These are chart setups, not proven edges: the lab tested this kind of rule on BTC, ETH and
FX majors (2026-11-23/24) and none beat luck after costs. Nothing here places an order.
Research, not financial advice.
"""

import argparse
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import scan  # noqa: E402

CRYPTO = ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "BNB-USD", "DOGE-USD", "ADA-USD",
          "AVAX-USD", "LINK-USD", "LTC-USD", "DOT-USD", "BCH-USD"]
FOREX = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "USDCHF=X", "NZDUSD=X",
         "EURJPY=X", "GBPJPY=X", "EURGBP=X", "AUDJPY=X", "EURCHF=X", "EURAUD=X", "GBPCHF=X",
         "GC=F", "SI=F"]
NAMES = {"GC=F": "gold (XAUUSD)", "SI=F": "silver (XAGUSD)"}
LABELS = {"breakout_20d": "20-hour closing-high breakout", "bull_flag": "bull flag",
          "reclaim_ma20": "reclaimed the 20-hour average", "oversold": "oversold (RSI under 30)",
          "oversold_bounce": "oversold bounce", "breakdown_20h": "20-hour closing-low breakdown",
          "overbought": "overbought (RSI over 70)"}
OUT = os.path.join(os.path.dirname(HERE), "trader", "fxcrypto.json")


def complete_hours(series, now_ts):
    """[(ts, close)] of finished 1-hour bars: nulls dropped, the forming bar dropped."""
    out = {}
    for t, c in zip(series["t"], series["c"]):
        if c is None or t + 3600 > now_ts:
            continue
        out[t] = float(c)
    return sorted(out.items())


def analyse(sym, series, now_ts):
    bars = complete_hours(series, now_ts)
    if len(bars) < 30:
        return None
    c = [x for _, x in bars]
    tags, nums = scan.find_setups(c)
    if c[-1] < min(c[-21:-1]):
        tags.append("breakdown_20h")
    if nums["rsi"] is not None and nums["rsi"] > 70:
        tags.append("overbought")
    t_last = bars[-1][0]
    back = [x for t, x in bars if t <= t_last - 24 * 3600]
    return {"symbol": sym, "name": NAMES.get(sym, sym.replace("=X", "").replace("-USD", "")),
            "kind": "crypto" if sym in CRYPTO else "forex",
            "last": c[-1], "bar_end_utc": datetime.datetime.fromtimestamp(t_last + 3600, datetime.timezone.utc).strftime("%Y-%m-%d %H:%MZ"),
            "chg_1h_pct": (c[-1] / c[-2] - 1) * 100,
            "chg_24h_pct": (c[-1] / back[-1] - 1) * 100 if back else None,
            "rsi": nums["rsi"], "setups": tags}


def run(symbols, now_ts=None, pause=0.3):
    now_ts = now_ts or datetime.datetime.now(datetime.timezone.utc).timestamp()
    data, failed = scan.fetch_spark(symbols, "10d", "1h", pause)
    rows = [r for r in (analyse(s, data[s], now_ts) for s in symbols if s in data) if r]
    return rows, failed


def fmt_price(x):
    return "%.5f" % x if x < 10 else "%.2f" % x if x < 1000 else "{:,.0f}".format(x)


def main(argv=None):
    ap = argparse.ArgumentParser(description="hourly crypto and forex scan")
    ap.add_argument("--symbols", help="comma-separated Yahoo symbols instead of the default list")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    syms = a.symbols.split(",") if a.symbols else CRYPTO + FOREX
    rows, failed = run(syms)
    now = datetime.datetime.now(datetime.timezone.utc)
    doc = {"generated_utc": now.strftime("%Y-%m-%d %H:%MZ"), "rows": rows, "failed": failed}
    if not a.no_write:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "w") as f:
            json.dump(doc, f, indent=1)
    if a.json:
        print(json.dumps(doc, indent=1))
        return 0
    print("Hourly crypto and forex scan, %s (complete 1-hour bars, Yahoo)." % doc["generated_utc"])
    for kind in ("crypto", "forex"):
        part = sorted((r for r in rows if r["kind"] == kind),
                      key=lambda r: -abs(r["chg_24h_pct"] or 0))
        print("\n%s (biggest 24-hour move first):" % kind.upper())
        for r in part:
            print("  %-16s %12s  1h %+6.2f%%  24h %s  RSI %5.1f  %s" % (
                r["name"], fmt_price(r["last"]), r["chg_1h_pct"],
                "%+6.2f%%" % r["chg_24h_pct"] if r["chg_24h_pct"] is not None else "   n/a ",
                r["rsi"] or 0, ", ".join(LABELS[t] for t in r["setups"]) or "-"))
    if failed:
        print("\nNo data: %s" % ", ".join(sorted(failed)))
    print("\nSetups, not proven edges (the lab found none that beats luck after costs). "
          "Nothing is placed. Research, not financial advice.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
