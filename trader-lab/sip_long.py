#!/usr/bin/env python3
"""Stocks in play and end-of-day reversal on 40 names x 4 years of 5-minute bars.

    python3 sip_long.py test [--write]     # needs the 40-name Tiingo store in data/long

STATUS: PRE-REGISTERED 2026-11-23, written while the data was still downloading (fewer than 5 of
the 40 names were complete) and before any result on it was seen. Not to be changed after the
first run.

Why: the 60-day test of stocks in play (lab.py `sip`) was "not shown on our data", not refuted, and
the end-of-day reversal (`eodrev`) needs a cross-section to rank. Both are the strongest published
5-minute claims the lab has not yet judged on years of data:
  * sip: Zarattini, Barbon & Aziz (2024), "A Profitable Day Trading Strategy for the U.S. Equity
    Market": ORB only on the day's highest relative opening volume names (reported Sharpe 2.81).
  * eodrev: Baltussen, Da & Soebhag (2025): at 15:30 buy the day's biggest losers and short the
    biggest winners, out at the close.

Design, fixed now:
  * Universe: lab.UNIVERSE (the lab's 40 names), Tiingo IEX 5-minute bars in data/long, from Nov 2022,
    half days cut at 13:00 (lab.drop_after_early_close). A name that listed later (ARM) joins
    when it has 14 sessions of history, as lab.py's relative-volume code already requires.
  * Engine and gates: lab.backtest() exactly as it is in git at the time of the run, with no edits:
    IS = first 50% of dates, OOS = next 25%, HOLDOUT = last 25%; variant chosen on IS; PASS needs
    IS t >= 2, positive OOS and HOLDOUT means, post-IS t >= 3 and the direction placebo at
    p < 0.05 / (strategies tested). Only `sip` and `eodrev` are run (only=...), with lab.py's grids.
  * Costs: run at 3 bps (lab default) AND at 5 bps (the open is where slippage is worst; the
    paper's live users report it). PASS needs PASS at both.
Caveats up front: 40 of today's liquid survivors, not 7,000 stocks, so "top 5 of 40" is a far
weaker filter than the paper's top 20; Tiingo volume is IEX-only, so relative volume is measured
on one exchange's share of trading (a proxy). A FAIL here is "not shown on 40 names", not a refutation
of the paper. Research, not financial advice.
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lab  # noqa: E402  (engine, gates and strategies, used unchanged)

STRATS = ["sip", "eodrev"]
COSTS = (3.0, 5.0)


def load_universe():
    out, missing = {}, []
    for s in lab.UNIVERSE:
        bars = lab.load_store(s, lab.LONG_STORE)
        if not bars:
            missing.append(s)
            continue
        out[s] = lab.sessions_of(lab.drop_after_early_close(bars))
    return out, missing


def cmd_test(a):
    uni, missing = load_universe()
    if missing:
        raise lab.LabError("the 40-name store is incomplete (missing %s); finish `lab.py fetch-tiingo` first"
                           % ", ".join(missing))
    report = {}
    for cost in COSTS:
        res = lab.backtest(uni, cost_bps=cost, only=STRATS)
        report["cost_%d" % cost] = res
        print("== %.0f bps round trip: %d sessions %s to %s, OOS from %s, HOLDOUT from %s ==" % (
            cost, res["n_dates"], res["dates"][0], res["dates"][1], res["oos_from"], res["ho_from"]))
        print(lab.report_backtest(res))
    verdict = {}
    for s in STRATS:
        ok = all(any(c["strategy"] == s and c.get("keep") for c in report["cost_%d" % cost]["chosen"]) for cost in COSTS)
        verdict[s] = "PASS" if ok else "FAIL"
    print("\nVerdict (PASS needs a PASS at 3 AND 5 bps): %s" % json.dumps(verdict))
    if a.write:
        with open(a.write, "w") as fh:
            json.dump({"verdict": verdict, "runs": report}, fh, indent=1, sort_keys=True, default=str)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("test")
    p.add_argument("--write", nargs="?", const=os.path.join(lab.RESULTS, "sip-long.json"))
    a = ap.parse_args(argv)
    try:
        return cmd_test(a) if a.cmd == "test" else ap.print_help() or 1
    except lab.LabError as e:
        print("sip_long.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
