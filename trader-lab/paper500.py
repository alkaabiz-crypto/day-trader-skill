#!/usr/bin/env python3
"""Shared tools for the $500 event backtests (calendar2.py, insiders.py, congress.py).

prices(sym)          dividend-adjusted daily closes from Yahoo, cached under data/paper500/prices
account(...)         a $500 account that holds the open positions in equal weight each day and keeps the rest
                     in T-bills; returns the daily value path
tstat, monthly       statistics clustered by calendar month
Research, not financial advice.
"""

import datetime
import gzip
import json
import math
import os
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
STORE = os.path.join(HERE, "data", "paper500", "prices")
START = 500.0


def prices(sym, refresh=False):
    """{"d": [...], "a": [...]} adjusted closes, or None if Yahoo has no data for the ticker."""
    import daily
    os.makedirs(STORE, exist_ok=True)
    path = os.path.join(STORE, "%s.json.gz" % sym.replace("^", "_").replace("/", "_"))
    if os.path.exists(path) and not refresh:
        with gzip.open(path, "rt") as fh:
            b = json.load(fh)
        return b or None
    try:
        raw = daily.parse_daily(daily.fetch_daily(sym))
        b = {"d": raw["d"], "a": raw["a"], "c": raw["c"]}
    except Exception:  # noqa: BLE001  (missing ticker: cached as empty so it is not asked again)
        b = {}
    tmp = path + ".tmp"
    with gzip.open(tmp, "wt") as fh:
        json.dump(b, fh)
    os.replace(tmp, path)
    time.sleep(0.2)
    return b or None


def rf_daily():
    """{date: daily T-bill return} from ^IRX (13-week bill, annualized percent)."""
    b = prices("^IRX")
    out, last = {}, 0.0
    for d, c in zip(b["d"], b["c"]):
        last = c if c is not None else last
        out[d] = last / 100.0 / 252.0
    return out


def tstat(x):
    if len(x) < 3 or statistics.stdev(x) == 0:
        return 0.0
    return statistics.mean(x) / (statistics.stdev(x) / math.sqrt(len(x)))


def monthly(pairs):
    """[(date, value)] -> per-month means, for statistics that don't count same-month events as independent."""
    by = {}
    for d, v in pairs:
        by.setdefault(d[:7], []).append(v)
    return [sum(v) / len(v) for _, v in sorted(by.items())]


def account(days, positions, rf, start=START):
    """Daily value of a $start account.

    days: sorted trading dates. positions: list of {"entry": date, "exit": date, "rets": {date: return},
    "cost": round-trip cost as a fraction}. On each day the account is split equally across positions open that
    day (entry < day <= exit); the rest earns the T-bill. Half the round-trip cost is paid on the entry day and
    half on the exit day, out of that position's slice. Returns [(date, value)]."""
    value, path = start, []
    for d in days:
        live = [p for p in positions if p["entry"] < d <= p["exit"] and d in p["rets"]]
        if live:
            w = 1.0 / len(live)
            r = 0.0
            for p in live:
                rr = p["rets"][d]
                if d == p["exit"]:
                    rr -= p["cost"] / 2
                if d == min(x for x in p["rets"] if x > p["entry"]):
                    rr -= p["cost"] / 2
                r += w * rr
        else:
            r = rf.get(d, 0.0)
        value *= 1 + r
        path.append((d, value))
    return path


def window_returns(b, entry_idx, hold):
    """Daily returns of an adjusted-close series from entry_idx (exclusive) to entry_idx + hold (inclusive)."""
    a, d = b["a"], b["d"]
    out = {}
    for k in range(entry_idx + 1, min(entry_idx + hold, len(a) - 1) + 1):
        if a[k - 1] and a[k]:
            out[d[k]] = a[k] / a[k - 1] - 1.0
    return out


def first_after(dates, day):
    """Index of the first trading date strictly after `day` (ISO), or None."""
    import bisect
    i = bisect.bisect_right(dates, day)
    return i if i < len(dates) else None


def dollars(path, first=None, last=None):
    """Value at the end, scaled to $500 at `first` (the path's own start by default)."""
    pts = [(d, v) for d, v in path if (first is None or d >= first) and (last is None or d <= last)]
    if len(pts) < 2:
        return None
    base = [v for d, v in path if d < pts[0][0]]
    v0 = base[-1] if base else START
    return START * pts[-1][1] / v0


def today():
    return datetime.date.today().isoformat()
