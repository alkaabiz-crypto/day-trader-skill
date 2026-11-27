#!/usr/bin/env python3
"""NY AM Range Sweep on the markets it was built for: gold and the euro (Tiingo 5-minute FX). Pre-registered.

    python3 nyam_fx.py fetch [--max-requests N]   # resumable download into data/fx/<pair>.json.gz
    python3 nyam_fx.py run [--write]              # -> results/nyam-fx.json

The indicator's page says it is "Best used on: the 5-minute chart ... indices, forex, futures"; round 2
(nyam2.py) could only test crypto. Tiingo (already connected) serves 5-minute forex and gold back to 2022.

PRE-REGISTERED 2026-11-26, committed before any FX data was downloaded. Not to be changed:
  Markets: XAU/USD (gold) and EUR/USD, Tiingo 5-minute mid prices, 2022-11-01 on, New York time, weekdays.
  A day counts if at least 125 of the 133 candles 05:00-16:00 are there; missing candles are filled with the
    previous close (a flat candle).
  Rules: exactly nyam2.day_trade (05:00-09:00 range, close beyond it from 09:00 to 11:55, full engulfing candle
    back the other way, last 45-minute candle agrees, stop at the sweep's extreme, target the opposite side of
    the range, out at 16:00).
  Costs a round trip: gold 5 bps, EUR/USD 2 bps (retail spreads); double reported.
  Split: in-sample before 2025-01-01, judged from 2025-01-01.
  Verdict per market: PASS only if judged t >= 3 and in-sample mean > 0.
  Reported: $500 compounded on the judged years (whole $500 per trade, no leverage) vs $500 held.
Research, not financial advice.
"""

import argparse
import datetime
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import candles  # noqa: E402
import lab  # noqa: E402
import nyam  # noqa: E402
import nyam2  # noqa: E402

STORE = os.path.join(HERE, "data", "fx")
RESULTS = os.path.join(HERE, "results")
PAIRS = {"xauusd": 5.0, "eurusd": 2.0}
START = "2022-11-01"
CHUNK_DAYS = 30
MIN_CANDLES = 125


def path(pair):
    return os.path.join(STORE, pair + ".json.gz")


def fetch_chunk(pair, start, end):
    url = "https://api.tiingo.com/tiingo/fx/%s/prices?startDate=%s&endDate=%s&resampleFreq=5min" % (pair, start, end)
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        rows = json.loads(r.read().decode("utf-8"))
    out = {}
    for x in rows:
        t = datetime.datetime.strptime(x["date"][:19], "%Y-%m-%dT%H:%M:%S")
        ts = int((t - datetime.datetime(1970, 1, 1)).total_seconds())
        out[str(ts)] = [x["open"], x["high"], x["low"], x["close"]]
    return out


def cmd_fetch(a):
    if not candles.take_lock():                   # the Tiingo quota is shared with the candles download
        print("another Tiingo fetch holds the lock: skipping")
        return 0
    try:
        used = 0
        today = datetime.date.today()
        for pair in PAIRS:
            bars = candles.load_gz(path(pair)) or {}
            last = max((int(k) for k in bars), default=None)
            start = (datetime.datetime.utcfromtimestamp(last).date() if last
                     else datetime.date.fromisoformat(START))
            while start < today and used < a.max_requests:
                end = min(start + datetime.timedelta(days=CHUNK_DAYS), today)
                try:
                    got = fetch_chunk(pair, start.isoformat(), end.isoformat())
                except Exception as e:  # noqa: BLE001
                    print("%s %s: %s (stopping)" % (pair, start, e))
                    candles.save_gz(path(pair), bars)
                    return 0
                used += 1
                bars.update(got)
                candles.save_gz(path(pair), bars)
                print("%s %s..%s: %d bars (stored %d)" % (pair, start, end, len(got), len(bars)))
                if not got:
                    start = end
                else:
                    nxt = datetime.datetime.utcfromtimestamp(max(int(k) for k in got)).date()
                    start = nxt if nxt > start else end
                time.sleep(a.pause)
            if start < today:
                print("request budget used: stopping (resumes next time)")
                return 0
        print("fx download complete")
        return 0
    finally:
        candles.drop_lock()


def fx_days(pair):
    bars = candles.load_gz(path(pair)) or {}
    days = {}
    for k, v in bars.items():
        loc = lab.to_eastern(lab.utc_of(int(k)))
        if loc.weekday() >= 5:
            continue
        days.setdefault(loc.date().isoformat(), {})[(loc.hour * 60 + loc.minute) // 5] = tuple(v[:4])
    out = {}
    need = range(nyam.RANGE_FROM, nyam.CLOSE_SLOT + 1)
    for d, b in sorted(days.items()):
        if sum(s in b for s in need) < MIN_CANDLES or nyam.RANGE_FROM not in b:
            continue
        for s in need:
            if s not in b:
                c = b[s - 1][3]
                b[s] = (c, c, c, c)
        out[d] = b
    return out


def cmd_run(a):
    res = {"markets": {}}
    for pair, cost in PAIRS.items():
        days = fx_days(pair)
        out = {}
        for name, c in (("main", cost), ("double_cost", 2 * cost)):
            tr = []
            for d, b in days.items():
                t = nyam2.day_trade(b)
                if t:
                    side, e, x, why = t
                    tr.append({"date": d, "ret": side * (x / e - 1) - c / 1e4, "why": why})
            out[name] = {"in_sample": nyam.summary(tr, hi=nyam.SPLIT), "judged": nyam.summary(tr, lo=nyam.SPLIT)}
        jd = [d for d in days if d >= nyam.SPLIT]
        hold = 500.0 * days[jd[-1]][nyam.CLOSE_SLOT][0] / days[jd[0]][nyam.RANGE_FROM][0] if jd else None
        m = out["main"]
        res["markets"][pair] = {"days": len(days), "first": min(days) if days else None, "last": max(days) if days else None,
                                "cost_bps": cost, **out, "hold_usd_judged": hold,
                                "verdict": "PASS" if (m["judged"]["t"] >= nyam.T_BAR and m["in_sample"]["bps"] > 0) else "FAIL"}
        print("%s (%d days %s..%s) | IS %3d tr %+6.1f bp t %+5.2f win %3.0f%% | judged %3d tr %+6.1f bp t %+5.2f win %3.0f%% "
              "| x2 cost judged %+.1f bp | $500 -> $%.0f (held $%.0f) | %s" % (
                  pair, len(days), res["markets"][pair]["first"], res["markets"][pair]["last"],
                  m["in_sample"]["trades"], m["in_sample"]["bps"], m["in_sample"]["t"], 100 * (m["in_sample"]["win_rate"] or 0),
                  m["judged"]["trades"], m["judged"]["bps"], m["judged"]["t"], 100 * (m["judged"]["win_rate"] or 0),
                  out["double_cost"]["judged"]["bps"], m["judged"]["usd"], hold or 0, res["markets"][pair]["verdict"]))
    if a.write:
        with open(a.write, "w") as fh:
            json.dump(res, fh, indent=1)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    f = sub.add_parser("fetch")
    f.add_argument("--max-requests", type=int, default=20)
    f.add_argument("--pause", type=float, default=20)
    r = sub.add_parser("run")
    r.add_argument("--write", nargs="?", const=os.path.join(RESULTS, "nyam-fx.json"))
    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        return cmd_fetch(a)
    if a.cmd == "run":
        return cmd_run(a)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
