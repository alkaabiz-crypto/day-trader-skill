#!/usr/bin/env python3
"""Whole-market intraday history from Alpaca's market data (consolidated SIP tape), not Yahoo.

    python3 daybrain/alpaca_days.py check
    python3 daybrain/alpaca_days.py fetch --from 2021-01 --to 2026-10 [--symbols-file F]

Alpaca's free market-data plan serves historical 5-minute bars for every US-listed stock from 2016 on
(SIP: the full consolidated tape, so real volume, not one exchange's slice), up to the last 15 minutes,
about 200 requests a minute, many symbols per request. Keys come from the environment's network secret
for data.alpaca.markets (headers APCA-API-KEY-ID and APCA-API-SECRET-KEY); nothing is stored here.

Storage. Years of raw 5-minute bars for ~1,500 stocks would be tens of gigabytes, so each stock-day is
reduced on the fly to the values the brain needs (DAY_FIELDS), from regular-session bars 9:30-16:00
New York. Saved per month: data/alpaca_days/<YYYY-MM>.json.gz = {SYMBOL: {date: [DAY_FIELDS...]}}.
Resumable by month. Prices are split- and dividend-adjusted (adjustment=all).
Survivorship: the symbol list is today's (trader/universe.txt), so stocks delisted since are missing.
Research, not financial advice.
"""

import argparse
import datetime
import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(HERE)
ROOT = os.path.dirname(LAB)
sys.path.insert(0, LAB)
import lab  # noqa: E402

BASE = "https://data.alpaca.markets/v2/stocks/bars"
STORE = os.path.join(LAB, "data", "alpaca_days")
BATCH = 100
# per stock-day: first bar o h l c v, second bar open, bar 71 close (15:25), bar 76 close (15:55),
# last bar close (15:55-16:00), day high, day low, dollar volume, number of bars
DAY_FIELDS = ["o1", "h1", "l1", "c1", "v1", "o2", "c71", "c76", "c77", "dh", "dl", "dvol", "n"]


class AlpacaError(Exception):
    pass


def get(params, tries=4):
    url = BASE + "?" + urllib.parse.urlencode(params)
    for k in range(tries):
        req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "trader-lab"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise AlpacaError("Alpaca refused the request (HTTP %d): the data.alpaca.markets keys are missing "
                                  "or wrong in the environment's network secrets" % e.code)
            if e.code == 429 or e.code >= 500:
                time.sleep(5 * (k + 1))
                continue
            raise AlpacaError("HTTP %d: %s" % (e.code, e.read()[:200]))
        except (urllib.error.URLError, OSError) as e:
            time.sleep(5 * (k + 1))
            last = e
    raise AlpacaError("no answer from Alpaca")


def summarise(bars):
    """bars: list of Alpaca bar dicts for one symbol -> {date: [DAY_FIELDS]} (complete regular sessions)."""
    by = {}
    for b in bars:
        t = datetime.datetime.strptime(b["t"][:19], "%Y-%m-%dT%H:%M:%S")
        ny = lab.to_eastern(t)
        slot = (ny.hour * 60 + ny.minute - lab.OPEN_MIN) // 5
        if 0 <= slot < 78:
            by.setdefault(ny.date().isoformat(), {})[slot] = b
    out = {}
    for d, s in by.items():
        if not all(i in s for i in (0, 1, 71, 76, 77)) or len(s) < 70:
            continue
        f, g = s[0], s[1]
        out[d] = [f["o"], f["h"], f["l"], f["c"], f["v"], g["o"], s[71]["c"], s[76]["c"], s[77]["c"],
                  max(x["h"] for x in s.values()), min(x["l"] for x in s.values()),
                  round(sum(x["c"] * x["v"] for x in s.values())), len(s)]
    return out


def month_range(frm, to):
    y, m = map(int, frm.split("-"))
    Y, M = map(int, to.split("-"))
    while (y, m) <= (Y, M):
        yield "%04d-%02d" % (y, m)
        m += 1
        if m == 13:
            y, m = y + 1, 1


def fetch_month(month, symbols):
    y, m = map(int, month.split("-"))
    start = "%04d-%02d-01T00:00:00Z" % (y, m)
    end = "%04d-%02d-01T00:00:00Z" % ((y + 1, 1) if m == 12 else (y, m + 1))
    out = {}
    for i in range(0, len(symbols), BATCH):
        batch = symbols[i:i + BATCH]
        raw = {}
        token = None
        while True:
            p = {"symbols": ",".join(batch), "timeframe": "5Min", "start": start, "end": end, "feed": "sip",
                 "adjustment": "all", "limit": 10000}
            if token:
                p["page_token"] = token
            doc = get(p)
            for s, bl in (doc.get("bars") or {}).items():
                raw.setdefault(s, []).extend(bl)
            token = doc.get("next_page_token")
            time.sleep(0.32)                      # under 200 requests a minute
            if not token:
                break
        for s, bl in raw.items():
            sm = summarise(bl)
            if sm:
                out[s] = sm
    return out


def symbols_from(path):
    with open(path) as fh:
        return [ln.split("|")[0].strip() for ln in fh if ln.strip() and not ln.startswith("#")]


def cmd_check(a):
    doc = get({"symbols": "SPY", "timeframe": "5Min", "start": "2016-01-04T14:30:00Z",
               "end": "2016-01-04T15:00:00Z", "feed": "sip", "limit": 10})
    n = len((doc.get("bars") or {}).get("SPY", []))
    print("Alpaca market data works: %d SPY bars for 2016-01-04 9:30-10:00." % n)
    return 0


def cmd_fetch(a):
    os.makedirs(STORE, exist_ok=True)
    syms = symbols_from(a.symbols_file or os.path.join(ROOT, "trader", "universe.txt"))
    for month in month_range(a.frm, a.to):
        p = os.path.join(STORE, month + ".json.gz")
        if os.path.exists(p):
            continue
        t0 = time.time()
        got = fetch_month(month, syms)
        tmp = p + ".tmp"
        with gzip.open(tmp, "wt") as fh:
            json.dump(got, fh)
        os.replace(tmp, p)
        print("  %s: %d stocks (%.0f s)" % (month, len(got), time.time() - t0), flush=True)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="whole-market intraday day summaries from Alpaca")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("check")
    p = sub.add_parser("fetch")
    p.add_argument("--from", dest="frm", default="2021-01")
    p.add_argument("--to", default=None)
    p.add_argument("--symbols-file")
    a = ap.parse_args(argv)
    if a.cmd == "fetch" and not a.to:
        t = datetime.date.today().replace(day=1) - datetime.timedelta(days=1)
        a.to = t.strftime("%Y-%m")
    try:
        return {"check": cmd_check, "fetch": cmd_fetch}[a.cmd](a)
    except KeyError:
        ap.print_help()
        return 1
    except AlpacaError as e:
        print("alpaca_days: %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
