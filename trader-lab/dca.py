#!/usr/bin/env python3
"""trader-lab: what a plain monthly index-fund plan would have done (the yardstick no rule beat).

    python3 dca.py                       # $500 a month into SPY and VT, every start since the data begins
    python3 dca.py --monthly 200 --symbols SPY
    python3 dca.py --years 10            # every 10-year window: worst, median, best

Buys on the first trading day of each month at the open, dividend-adjusted prices (dividends
reinvested), no fees (a broker's commission-free ETF buy). No timing, no selling. Shows the
money put in, the value now, the yearly return on that money (money-weighted, the IRR), the
deepest drop in the portfolio along the way, and how every N-year window would have ended.
This is history, not a forecast. Research, not financial advice.
"""

import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import universe_search as us  # noqa: E402


def month_starts(dates):
    return [i for i in range(len(dates)) if i == 0 or dates[i][:7] != dates[i - 1][:7]]


def irr(flows, years):
    """Money-weighted yearly return: flows[k] at time years[k] (negative = money in), solved by bisection."""
    lo, hi = -0.99, 1.0
    f = lambda r: sum(c / (1 + r) ** t for c, t in zip(flows, years))  # noqa: E731
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(mid) > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def plan(A, monthly, start=0, end=None):
    """Monthly buys from month-start index `start` to day `end` (exclusive). -> dict."""
    d, o, c = A["d"], A["o"], A["c"]
    end = len(d) if end is None else end
    buys = [i for i in month_starts(d) if start <= i < end]
    units = np.zeros(len(d))
    for i in buys:
        units[i] += monthly / o[i]
    held = np.cumsum(units)[:end]
    value = held * c[:end]
    invested = np.cumsum(np.where(units[:end] > 0, monthly, 0.0))
    live = slice(buys[0], end)
    v = value[live]
    peak = np.maximum.accumulate(v)
    dd = float(((peak - v) / peak).max())
    under = invested[live] > v
    t0 = buys[0]
    yrs = [(i - t0) / 252.0 for i in buys] + [(end - 1 - t0) / 252.0]
    flows = [-monthly] * len(buys) + [float(value[end - 1])]
    return {"from": d[buys[0]], "to": d[end - 1], "months": len(buys), "invested": float(invested[end - 1]),
            "value": float(value[end - 1]), "irr": irr(flows, yrs), "max_drop": dd,
            "share_days_below_invested": float(under.mean())}


def windows(A, monthly, years):
    d = A["d"]
    ms = month_starts(d)
    n = int(round(years * 252))
    out = []
    for i in ms:
        if i + n > len(d):
            break
        out.append(plan(A, monthly, i, i + n))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="monthly index-fund plan, historically")
    ap.add_argument("--monthly", type=float, default=500.0)
    ap.add_argument("--symbols", default="SPY,VT")
    ap.add_argument("--years", type=float, default=10.0)
    a = ap.parse_args(argv)
    for sym in a.symbols.split(","):
        A = us.load_asset(sym)
        p = plan(A, a.monthly)
        print("%s: $%.0f a month from %s to %s (%d buys): put in $%s, worth $%s now, %.1f%% a year (money-weighted). "
              "Deepest drop along the way %.0f%%; below the money put in on %.0f%% of days." % (
                  sym, a.monthly, p["from"], p["to"], p["months"], "{:,.0f}".format(p["invested"]),
                  "{:,.0f}".format(p["value"]), 100 * p["irr"], 100 * p["max_drop"], 100 * p["share_days_below_invested"]))
        w = windows(A, a.monthly, a.years)
        if w:
            r = sorted(x["irr"] for x in w)
            worst = min(w, key=lambda x: x["irr"])
            print("  every %g-year window (%d starts): worst %.1f%% a year (%s to %s), median %.1f%%, best %.1f%%; "
                  "%.0f%% of windows ended with more than was put in." % (
                      a.years, len(w), 100 * r[0], worst["from"], worst["to"], 100 * r[len(r) // 2], 100 * r[-1],
                      100 * sum(1 for x in w if x["value"] > x["invested"]) / len(w)))
    print("History, not a forecast: dividends reinvested, no fees or taxes. Research, not financial advice.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
