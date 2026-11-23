#!/usr/bin/env python3
"""Holding without forecasting: risk parity (inverse volatility) and equal weight vs 60/40.

    python3 parity.py test [--write]      # needs `alloc.py fetch` first (same data)

Why: every timing rule in this lab failed after its tuning period. Weighting rules that make no
forecast cannot be over-fitted to returns the same way. Equal weight (1/N) was hard to beat for
14 optimizers in DeMiguel, Garlappi & Uppal (2009, RFS). Inverse-volatility weighting, the simple
form of risk parity (Asness, Frazzini & Pedersen 2012), lets each asset carry the same risk.

PRE-REGISTERED 2026-11-23, before any result was seen. Not to be changed after the first run:
  Same data, calendar, costs (10 and 20 bps per turnover), one-day trade delay, T-bill cash and
  periods as alloc.py Part B (IS to 2014, OOS 2015-2020, HOLDOUT 2021 on).
    P1 ivol9   the nine Part B ETFs weighted by 1 / (volatility of the last L daily returns), monthly.
               L in 63, 126.
    P2 ivol4   SPY EFA IEF GLD the same way (one stock, one foreign, one bond, one gold). L in 63, 126.
    P3 ew9     the nine ETFs, 1/9 each, rebalanced monthly. (no grid)
  Benchmark: 60/40 SPY/IEF (SPY buy-and-hold reported too). Variant chosen on IS Sharpe.
  PASS: Sharpe above 60/40's in OOS and in HOLDOUT, at 10 AND 20 bps, and bootstrap p < 0.05 / 3
  that the post-IS Sharpe beats 60/40's. (No timing placebo: these rules do not time anything.)
Caveat up front: unlevered risk parity holds mostly bonds; 2022 (stocks and bonds fell together)
is in the holdout, which is the hard case for it. Research, not financial advice.
"""

import argparse
import datetime
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import alloc  # noqa: E402
import daily  # noqa: E402

FOUR = ["SPY", "EFA", "IEF", "GLD"]
N_RULES = 3


def ivol(P, k, names, L):
    inv = {}
    for s in names:
        v = P.daily_var(s, P.sig[k], n=L)
        if not v:
            return None
        inv[s] = 1.0 / v ** 0.5
    t = sum(inv.values())
    return {s: x / t for s, x in inv.items()}


def w_ivol9(P, k, p):
    return ivol(P, k, alloc.PART_B, p["l"])


def w_ivol4(P, k, p):
    return ivol(P, k, FOUR, p["l"])


def w_ew9(P, k, p):
    if any(P.px(s, P.sig[k]) is None for s in alloc.PART_B):
        return None
    return {s: 1.0 / len(alloc.PART_B) for s in alloc.PART_B}


RULES = {"ivol9": (w_ivol9, [{"l": 63}, {"l": 126}], "inverse volatility, 9 ETFs"),
         "ivol4": (w_ivol4, [{"l": 63}, {"l": 126}], "inverse volatility, SPY/EFA/IEF/GLD"),
         "ew9": (w_ew9, [{}], "DeMiguel et al. 2009: 1/N")}


def cmd_test(a):
    data = {s: alloc.load(s) for s in set(alloc.PART_A + alloc.PART_B)}
    cash = alloc.load(alloc.CASH)
    if not all(data.values()) or not cash:
        raise daily.LabError("run `alloc.py fetch` first")
    P = alloc.Panel(data, cash)
    report = {"run": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "rules": {}}
    print("Risk parity and equal weight vs 60/40. IS to 2014, OOS 2015-2020, HOLDOUT 2021+.\n")
    for name, (fn, grid, src) in RULES.items():
        best = None
        for p in grid:
            s = alloc.stats(alloc.split(alloc.simulate(P, fn, p, 10.0), "B")[0])
            if best is None or s["sharpe"] > best[1]["sharpe"]:
                best = (p, s)
        p, s_is = best
        res = {"source": src, "params": p, "is": s_is}
        ok = {}
        for cost in alloc.COSTS:
            rows = alloc.simulate(P, fn, p, cost)
            first = rows[0][0]
            b = [x for x in alloc.simulate(P, alloc.w_6040, {}, cost) if x[0] >= first]
            spy = [x for x in alloc.simulate(P, alloc.w_bh, {}, cost) if x[0] >= first]
            _, oos, hold, post = alloc.split(rows, "B")
            _, b_oos, b_hold, b_post = alloc.split(b, "B")
            bd = {x[0]: x for x in b_post}
            pair = [(x, bd[x[0]]) for x in post if x[0] in bd]
            r = {"oos": alloc.stats(oos), "holdout": alloc.stats(hold), "post": alloc.stats(post),
                 "bench_oos": alloc.stats(b_oos), "bench_holdout": alloc.stats(b_hold), "bench_post": alloc.stats(b_post),
                 "spy_post": alloc.stats(alloc.split(spy, "B")[3]),
                 "boot_p": alloc.boot_p([x[1] - x[2] for x, _ in pair], [y[1] - y[2] for _, y in pair])}
            res["cost_%d" % cost] = r
            ok[cost] = (r["oos"]["sharpe"] > r["bench_oos"]["sharpe"] and r["holdout"]["sharpe"] > r["bench_holdout"]["sharpe"]
                        and r["boot_p"] < 0.05 / N_RULES)
        res["verdict"] = "PASS" if all(ok.values()) else "FAIL"
        report["rules"][name] = res
        r = res["cost_20"]
        print("%-6s %-11s IS Sh %5.2f | post-IS @20bp: Sh %5.2f (60/40 %5.2f, SPY %5.2f)  CAGR %5.1f%% (60/40 %5.1f%%)"
              "  maxDD %6.1f%% (60/40 %6.1f%%)  OOS %5.2f/%5.2f  HOLD %5.2f/%5.2f  boot p %.3f -> %s" % (
                  name, json.dumps(p), s_is["sharpe"], r["post"]["sharpe"], r["bench_post"]["sharpe"], r["spy_post"]["sharpe"],
                  100 * r["post"]["cagr"], 100 * r["bench_post"]["cagr"], 100 * r["post"]["mdd"], 100 * r["bench_post"]["mdd"],
                  r["oos"]["sharpe"], r["bench_oos"]["sharpe"], r["holdout"]["sharpe"], r["bench_holdout"]["sharpe"],
                  r["boot_p"], res["verdict"]))
    print("\nResearch, not financial advice.")
    if a.write:
        with open(a.write, "w") as fh:
            json.dump(report, fh, indent=1, sort_keys=True, default=str)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("test")
    p.add_argument("--write", nargs="?", const=os.path.join(alloc.RESULTS, "parity.json"))
    a = ap.parse_args(argv)
    try:
        return cmd_test(a) if a.cmd == "test" else ap.print_help() or 1
    except daily.LabError as e:
        print("parity.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
