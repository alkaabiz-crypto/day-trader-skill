#!/usr/bin/env python3
"""Every multi-day rule rerun with no overnight swap: the owner's Exness swap-free account (2026-11-26).

    python3 swapfree.py run [--write]

PRE-REGISTERED 2026-11-26, committed before any run. Not to be changed after the result:
  Each engine runs unchanged (its rules, data, spreads, fills and its own pass bar), with only the overnight
  cost set to zero:
    1. indices bot (indexbot.py): all 10 indices and US-only, SWAP_BPS 2 -> 0
    2. indices walk-forward optimization (indexopt.py), US-only, swap 0
    3. Bitcoin: the DTC-style ribbon and the 60 named indicators (dtc_btc.py), swap 3 bp a night -> 0, Exness
       spread 6 bp a round trip kept
    4. oil (oil.py backtest): CFD financing 1 bp a night -> 0 (DCA ladders and every multi-day rule)
    5. crypto/forex bot (bot_backtest.py fxcrypto) and buy-low/sell-high (fx_meanrev.py): swap -> 0
  The verdicts use each engine's own bar. Nothing else is tuned.
  Caveat: some Exness swap-free instruments carry a fixed fee after a number of nights; the tests assume zero.
Research, not financial advice.
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
RESULT = os.path.join(HERE, "results", "swapfree.json")


def ns(**kw):
    return argparse.Namespace(**kw)


def indices(out):
    import indexbot as ib
    ib.SWAP_BPS = 0.0
    for uni in ("all", "us"):
        print("\n=== indices bot, %s, swap-free" % uni, flush=True)
        ib.cmd_backtest(ns(universe=uni, placebo=200, write=False))
        data = ib.load()
        if uni == "us":
            data = {k: data[k] for k in ib.US_ONLY}
        curve, trades = ib.simulate(data)
        post = ib.survivors.summarize(curve, ib.JUDGED)
        out["indices_" + uni] = post
    import indexopt
    print("\n=== indices walk-forward (US), swap-free", flush=True)
    indexopt.cmd_run(ns(placebo=200, write=False))


def bitcoin(out):
    import dtc_btc
    dtc_btc.SWAP_BPS = 0.0
    dtc_btc.returns.__defaults__ = (dtc_btc.SPREAD_BPS, 0.0)
    print("\n=== Bitcoin ribbon + 60 indicators, swap-free", flush=True)
    dtc_btc.cmd_run(ns(write=False))


def oil_rules(out):
    import oil
    oil.NIGHT_BPS = 0.0
    oil.dca.__defaults__ = (oil.COST_BPS, 0.0, None)
    print("\n=== oil, no financing", flush=True)
    oil.main(["backtest"])


def fx(out):
    import bot_backtest as bb
    bb.swap_bps = lambda s: 0.0
    print("\n=== crypto/forex bot, swap-free", flush=True)
    out["fxcrypto"] = bb.cmd_fxcrypto(ns(placebo=20))
    import fx_meanrev
    print("\n=== buy low / sell high, swap-free", flush=True)
    fx_meanrev.cmd_run(ns(placebo=20, write=False))


def cmd_run(a):
    out = {}
    for f in (indices, bitcoin, oil_rules, fx):
        f(out)
    if a.write:
        with open(RESULT, "w") as fh:
            json.dump(out, fh, indent=1, default=str)
        print("Wrote %s" % os.path.relpath(RESULT, HERE))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="multi-day rules with no overnight swap")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("run")
    p.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd != "run":
        ap.print_help()
        return 1
    return cmd_run(a)


if __name__ == "__main__":
    sys.exit(main())
