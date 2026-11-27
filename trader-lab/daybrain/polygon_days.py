#!/usr/bin/env python3
"""Multi-year intraday history from Polygon.io (not Yahoo, not Alpaca), reduced to day summaries.

    python3 daybrain/polygon_days.py check
    python3 daybrain/polygon_days.py fetch [--top 500] [--from 2024-11-25]

Polygon's free plan: 5-minute aggregates for every US stock for the last 2 years, consolidated volume,
5 requests a minute. The key is the environment's network secret for api.polygon.io (Authorization:
Bearer); nothing is stored here. One stock's 2 years take about 8 requests (12.5 s apart), so the top 500
names take about 12 hours. Resumable: one file per stock, data/polygon_days/<SYM>.json.gz =
{date: [o1 h1 l1 c1 v1 o2 c71 c76 c77 dh dl dvol n]} (alpaca_days.DAY_FIELDS, regular session only).
Names: the most-traded first, from data/wm5/_liquid.json (bot_data.py stocks). Survivorship: today's names.
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
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, LAB)
import alpaca_days  # noqa: E402  (summarise and DAY_FIELDS)
import bot_data  # noqa: E402

STORE = os.path.join(LAB, "data", "polygon_days")
PAUSE = 12.5


class PolygonError(Exception):
    pass


def get(url):
    for k in range(5):
        req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "trader-lab"})
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise PolygonError("Polygon refused (HTTP %d): check the api.polygon.io key" % e.code)
            if e.code == 429 or e.code >= 500:
                time.sleep(30 * (k + 1))
                continue
            raise PolygonError("HTTP %d" % e.code)
        except (urllib.error.URLError, OSError):
            time.sleep(15 * (k + 1))
    raise PolygonError("no answer from Polygon")


def to_bars(results):
    return [{"t": datetime.datetime.fromtimestamp(r["t"] / 1000, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "o": r["o"], "h": r["h"], "l": r["l"], "c": r["c"], "v": r.get("v", 0)} for r in results]


def fetch_symbol(sym, frm, to):
    url = ("https://api.polygon.io/v2/aggs/ticker/%s/range/5/minute/%s/%s?adjusted=true&sort=asc&limit=50000"
           % (sym, frm, to))
    bars = []
    while url:
        doc = get(url)
        if doc.get("status") not in ("OK", "DELAYED"):
            raise PolygonError(doc.get("message") or doc.get("status"))
        bars += to_bars(doc.get("results") or [])
        url = doc.get("next_url")
        time.sleep(PAUSE)
    return alpaca_days.summarise(bars)


def cmd_check(a):
    doc = get("https://api.polygon.io/v2/aggs/ticker/SPY/range/5/minute/%s/%s?adjusted=true&limit=10" % (a.frm, a.frm))
    print("Polygon works: status %s, %d bars for SPY on %s." % (doc.get("status"), doc.get("resultsCount", 0), a.frm))
    return 0


def cmd_fetch(a):
    os.makedirs(STORE, exist_ok=True)
    with open(os.path.join(bot_data.WM5, "_liquid.json")) as fh:
        syms = json.load(fh)[:a.top]
    to = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    done = 0
    for s in syms:
        p = os.path.join(STORE, s + ".json.gz")
        if os.path.exists(p):
            done += 1
            continue
        try:
            sm = fetch_symbol(s, a.frm, to)
        except PolygonError as e:
            print("  %s: %s" % (s, e), flush=True)
            if "refused" in str(e):
                return 2
            continue
        tmp = p + ".tmp"
        with gzip.open(tmp, "wt") as fh:
            json.dump(sm, fh)
        os.replace(tmp, p)
        done += 1
        print("  %d/%d %s: %d days" % (done, len(syms), s, len(sm)), flush=True)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="2-year intraday day summaries from Polygon")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("check")
    p.add_argument("--from", dest="frm", default="2024-11-26")
    p = sub.add_parser("fetch")
    p.add_argument("--top", type=int, default=500)
    p.add_argument("--from", dest="frm", default="2024-11-26")
    a = ap.parse_args(argv)
    fn = {"check": cmd_check, "fetch": cmd_fetch}.get(a.cmd)
    if not fn:
        ap.print_help()
        return 1
    try:
        return fn(a)
    except PolygonError as e:
        print("polygon_days: %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
