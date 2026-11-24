#!/usr/bin/env python3
"""trader-lab: stock / bond / gold mixes for the monthly plan, without forecasting (plan item B1).

    python3 daily.py fetch --symbols SPY,VT,IEF,GLD
    python3 mixes.py [--json] [--write]

Why: no timing rule beat buying and holding, so the one lever left is HOW MUCH risk to hold.
Bonds and gold have tended to fall less, or rise, when stocks crash. This shows what each step
down in risk has cost in return, so the mix can be chosen by how big a drop you could sit through.

PRE-REGISTERED 2026-11-24 (descriptive, no pass/fail; nothing is chosen from these numbers by a
search). Mixes, rebalanced to target each January (one trade a year, 5 bp per unit turnover):
  stocks 100        SPY 100
  80/20             SPY 80, IEF 20 (7-10 year Treasuries)
  60/40             SPY 60, IEF 40
  60/30/10 gold     SPY 60, IEF 30, GLD 10
  40/40/20 gold     SPY 40, IEF 40, GLD 20
  world 80/20       VT 80, IEF 20 (from VT's first full year)
Monthly returns from 2005-01 (all of SPY, IEF and GLD exist) to 2026-10, dividends reinvested.
Reported: yearly return, volatility, Sharpe, deepest drop, worst calendar year, and 2008, 2020, 2022.
History, not a forecast. Research, not financial advice.
"""

import argparse
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import factor_etfs as fe  # noqa: E402
import universe_search as us  # noqa: E402

MIXES = {
    "stocks 100": {"SPY": 1.0},
    "80/20": {"SPY": 0.8, "IEF": 0.2},
    "60/40": {"SPY": 0.6, "IEF": 0.4},
    "60/30/10 gold": {"SPY": 0.6, "IEF": 0.3, "GLD": 0.1},
    "40/40/20 gold": {"SPY": 0.4, "IEF": 0.4, "GLD": 0.2},
    "world 80/20": {"VT": 0.8, "IEF": 0.2},
}
START, END = "2005-01", "2026-10"
COST_BPS = 5.0


def simulate(weights, rets, months):
    """Monthly portfolio returns, weights drifting with prices, reset each January."""
    w = dict(weights)
    out = []
    for m in months:
        if m.endswith("-01"):
            turnover = sum(abs(weights[k] - w[k]) for k in weights)
            w = dict(weights)
            cost = turnover * COST_BPS / 1e4
        else:
            cost = 0.0
        r = sum(w[k] * rets[k][m] for k in w)
        out.append(r - cost)
        tot = sum(w[k] * (1 + rets[k][m]) for k in w)
        w = {k: w[k] * (1 + rets[k][m]) / tot for k in w}
    return np.array(out)


def summary(r, rf, months):
    n = len(r)
    eq = np.cumprod(1 + r)
    years = {}
    for m, x in zip(months, r):
        years[m[:4]] = years.get(m[:4], 1.0) * (1 + x)
    ex = r - rf
    return {"from": months[0], "to": months[-1], "cagr": float(eq[-1] ** (12 / n) - 1),
            "vol": float(r.std(ddof=1) * math.sqrt(12)), "sharpe": float(ex.mean() / ex.std(ddof=1) * math.sqrt(12)),
            "max_dd": float((1 - eq / np.maximum.accumulate(eq)).max()),
            "worst_year": min((v - 1, y) for y, v in years.items()),
            "y2008": years.get("2008", float("nan")) - 1, "y2020": years.get("2020", float("nan")) - 1,
            "y2022": years.get("2022", float("nan")) - 1}


def run():
    syms = sorted({k for w in MIXES.values() for k in w})
    data = {s: fe.monthly(us.load_asset(s)) for s in syms}
    rets = {s: {m: v[0] for m, v in data[s].items()} for s in syms}
    rf = {m: v[1] for m, v in data["SPY"].items()}
    out = {}
    for name, w in MIXES.items():
        months = sorted(m for m in rets["SPY"] if START <= m <= END and all(m in rets[k] for k in w))
        first_jan = next(i for i, m in enumerate(months) if m.endswith("-01"))
        months = months[first_jan:]
        r = simulate(w, rets, months)
        out[name] = dict(summary(r, np.array([rf[m] for m in months]), months), weights=w)
    return out


def report(out):
    print("Stock / bond / gold mixes, rebalanced each January, dividends reinvested (monthly, to %s):" % END)
    def yr(x):
        return "   n/a " if x != x else "%+5.1f%%" % (100 * x)
    print("  mix              from     per year  volatility  Sharpe  deepest drop  worst year      2008    2020    2022")
    for k, r in out.items():
        print("  %-15s  %s  %6.1f%%     %5.1f%%    %4.2f      %4.0f%%      %+5.1f%% (%s)  %s  %s  %s" % (
            k, r["from"], 100 * r["cagr"], 100 * r["vol"], r["sharpe"], 100 * r["max_dd"],
            100 * r["worst_year"][0], r["worst_year"][1], yr(r["y2008"]), yr(r["y2020"]), yr(r["y2022"])))
    print("History, not a forecast: bonds and stocks fell together in 2022, and gold's 2005-2026 run may not repeat. Research, not financial advice.")


def main(argv=None):
    ap = argparse.ArgumentParser(description="stock / bond / gold mixes")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    out = run()
    if a.write:
        with open(os.path.join(HERE, "results", "mixes.json"), "w") as f:
            json.dump(out, f, indent=1)
    if a.json:
        print(json.dumps(out, indent=1))
    else:
        report(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
