#!/usr/bin/env python3
"""NY AM Range Sweep on stock indices: SPY (S&P 500) and QQQ (Nasdaq 100), Alpaca 5-minute bars. Pre-registered.

    python3 nyam_idx.py fetch [--max-requests N]   # resumable download into data/idx/<sym>.json.gz
    python3 nyam_idx.py run [--write]              # -> results/nyam-idx.json

The indicator's page says it is "Best used on: the 5-minute chart ... indices, forex, futures". Rounds 2 and 3
(nyam2.py, nyam_fx.py) tested crypto, gold and the euro. Indices needed pre-market bars from 05:00 New York, which
Alpaca's market-data API (connected 2026-11-26) serves: SIP feed, split- and dividend-adjusted.

PRE-REGISTERED 2026-11-26, committed before any index data was downloaded. Not to be changed:
  Markets: SPY and QQQ, Alpaca SIP 5-minute bars (adjustment=all), 2016-01-01 on, New York time, weekdays.
  Pre-market is thin, so a day counts if at least 75 of the 79 regular-hours candles 09:30-16:00 are there and at
    least 24 of the 48 range candles 05:00-08:55; every missing candle from the first one at or after 04:00 is
    filled with the previous close (a flat candle).
  Rules: exactly nyam2.day_trade (05:00-09:00 range, close beyond it from 09:00 to 11:55, full engulfing candle
    back the other way, last 45-minute candle agrees, stop at the sweep's extreme, target the opposite side of
    the range, out at 16:00).
  Costs a round trip: 5 bps (the lab's stock cost; pre-market spreads are wider than the regular session's);
    double reported.
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
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import candles  # noqa: E402
import lab  # noqa: E402
import nyam  # noqa: E402
import nyam2  # noqa: E402

STORE = os.path.join(HERE, "data", "idx")
RESULTS = os.path.join(HERE, "results")
SYMBOLS = ["spy", "qqq"]
START = "2016-01-01"
COST_BPS = 5.0
CHUNK_DAYS = 60
MIN_REGULAR, MIN_RANGE = 75, 24
REG_FROM = 114      # 09:30
FILL_FROM = 48      # 04:00


def path(sym):
    return os.path.join(STORE, sym + ".json.gz")


def fetch_chunk(sym, start, end):
    out, token = {}, None
    while True:
        q = {"timeframe": "5Min", "start": start + "T00:00:00Z", "end": end + "T00:00:00Z", "limit": "10000",
             "adjustment": "all", "feed": "sip"}
        if token:
            q["page_token"] = token
        url = "https://data.alpaca.markets/v2/stocks/%s/bars?%s" % (sym.upper(), urllib.parse.urlencode(q))
        with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/json"}), timeout=120) as r:
            js = json.loads(r.read().decode("utf-8"))
        for x in js.get("bars") or []:
            t = datetime.datetime.strptime(x["t"][:19], "%Y-%m-%dT%H:%M:%S")
            out[str(int((t - datetime.datetime(1970, 1, 1)).total_seconds()))] = [x["o"], x["h"], x["l"], x["c"]]
        token = js.get("next_page_token")
        if not token:
            return out


def cmd_fetch(a):
    used, today = 0, datetime.date.today()
    for sym in SYMBOLS:
        bars = candles.load_gz(path(sym)) or {}
        last = max((int(k) for k in bars), default=None)
        start = datetime.datetime.utcfromtimestamp(last).date() if last else datetime.date.fromisoformat(START)
        while start < today and used < a.max_requests:
            end = min(start + datetime.timedelta(days=CHUNK_DAYS), today)
            try:
                got = fetch_chunk(sym, start.isoformat(), end.isoformat())
            except Exception as e:  # noqa: BLE001
                print("%s %s: %s (stopping)" % (sym, start, e))
                candles.save_gz(path(sym), bars)
                return 0
            used += 1
            bars.update(got)
            candles.save_gz(path(sym), bars)
            print("%s %s..%s: %d bars (stored %d)" % (sym, start, end, len(got), len(bars)))
            start = end
            time.sleep(a.pause)
        if start < today:
            print("request budget used: stopping (resumes next time)")
            return 0
    print("index download complete")
    return 0


def idx_days(sym):
    bars = candles.load_gz(path(sym)) or {}
    days = {}
    for k, v in bars.items():
        loc = lab.to_eastern(lab.utc_of(int(k)))
        if loc.weekday() >= 5:
            continue
        days.setdefault(loc.date().isoformat(), {})[(loc.hour * 60 + loc.minute) // 5] = tuple(v[:4])
    out = {}
    for d, b in sorted(days.items()):
        if (sum(s in b for s in range(REG_FROM, nyam.CLOSE_SLOT + 1)) < MIN_REGULAR
                or sum(s in b for s in range(nyam.RANGE_FROM, nyam.RANGE_TO)) < MIN_RANGE):
            continue
        first = min(s for s in b if s >= FILL_FROM)
        for s in range(first + 1, nyam.CLOSE_SLOT + 1):
            if s not in b:
                c = b[s - 1][3]
                b[s] = (c, c, c, c)
        out[d] = b
    return out


def cmd_run(a):
    res = {"markets": {}}
    for sym in SYMBOLS:
        days = idx_days(sym)
        out = {}
        for name, c in (("main", COST_BPS), ("double_cost", 2 * COST_BPS)):
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
        r = res["markets"][sym] = {"days": len(days), "first": min(days) if days else None,
                                   "last": max(days) if days else None, "cost_bps": COST_BPS, **out,
                                   "hold_usd_judged": hold,
                                   "verdict": "PASS" if (m["judged"]["t"] >= nyam.T_BAR and m["in_sample"]["bps"] > 0)
                                   else "FAIL"}
        print("%s (%d days %s..%s) | IS %3d tr %+6.1f bp t %+5.2f win %3.0f%% | judged %3d tr %+6.1f bp t %+5.2f "
              "win %3.0f%% | x2 cost judged %+.1f bp | exits %s | $500 -> $%.0f (held $%.0f) | %s" % (
                  sym, len(days), r["first"], r["last"],
                  m["in_sample"]["trades"], m["in_sample"]["bps"], m["in_sample"]["t"], 100 * (m["in_sample"]["win_rate"] or 0),
                  m["judged"]["trades"], m["judged"]["bps"], m["judged"]["t"], 100 * (m["judged"]["win_rate"] or 0),
                  out["double_cost"]["judged"]["bps"], m["judged"]["exits"], m["judged"]["usd"], hold or 0, r["verdict"]))
    if a.write:
        with open(a.write, "w") as fh:
            json.dump(res, fh, indent=1)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    f = sub.add_parser("fetch")
    f.add_argument("--max-requests", type=int, default=200)
    f.add_argument("--pause", type=float, default=0.5)
    r = sub.add_parser("run")
    r.add_argument("--write", nargs="?", const=os.path.join(RESULTS, "nyam-idx.json"))
    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        return cmd_fetch(a)
    if a.cmd == "run":
        return cmd_run(a)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
