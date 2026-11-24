#!/usr/bin/env python3
"""Forward test of the one near-miss: stocks in play, scored only on days after it was frozen.

    python3 sip_forward.py score [--write]       # needs data/long kept up to date (lab.py fetch-tiingo)

Why: on 4 years x 40 names, stocks in play (Zarattini, Barbon & Aziz 2024) was the closest any 5-minute rule
came to passing: positive OOS and HOLDOUT, but after-IS t 1.60-2.02 and IS t under 1 (RESEARCH.md
2026-11-24). The only data nobody can have tuned it on is the future. This scores it there.

PRE-REGISTERED 2026-11-24, before any forward session existed. Not to be changed:
  * Rule, frozen: lab.py strategy "sip" with {"min_rvol": 1.5, "stop": "bar", "top": 5} (its IS choice in
    sip_long.py), on lab.UNIVERSE (40 names), Tiingo IEX 5-minute bars, half days cut at 13:00.
  * Simulation: lab.py's own code (cross_section, contexts, run_day, trade_bps), imported, unchanged.
  * Scored sessions: only full sessions dated after FREEZE (2026-11-24). Daily portfolio = equal-weight mean of
    that day's trades (0 on a day with none).
  * Costs: 5 bps per round trip (the verdict); 3 bps reported.
  * Verdict: FORWARD-TEST until 60 forward sessions; then PROMOTE only if forward mean > 0 and forward t >= 2
    at 5 bps, else FAIL. Checked once at 60 sessions, not repeatedly, so there's no stopping when it looks good.
Research, not financial advice.
"""

import argparse
import json
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lab  # noqa: E402  (simulation code, unchanged)

FREEZE = "2026-11-24"
PARAMS = {"min_rvol": 1.5, "stop": "bar", "top": 5}
COSTS = (5.0, 3.0)
MIN_DAYS = 60


def universe():
    out = {}
    for s in lab.UNIVERSE:
        bars = lab.load_store(s, lab.LONG_STORE)
        if bars:
            out[s] = lab.sessions_of(lab.drop_after_early_close(bars))
    return out


def forward_series(uni, cost, freeze=FREEZE):
    """(dates, daily equal-weight bp series, trade count) for full sessions after `freeze`."""
    xs = lab.cross_section(uni)
    fn = lab.STRATEGIES["sip"]["fn"]
    daily, n = {}, 0
    dates = sorted({d for ss in uni.values() for d, b in ss if len(b) == lab.SESSION_BARS and d > freeze})
    for sym, ss in uni.items():
        for k, (d, bars) in enumerate(ss):
            if d <= freeze or len(bars) != lab.SESSION_BARS:
                continue
            ts, _ = lab.run_day(fn, bars, lab.contexts(ss, k, xs.get((sym, d))), PARAMS, True)
            for t in ts:
                daily.setdefault(d, []).append(lab.trade_bps(t, cost))
                n += 1
    series = [statistics.mean(daily[d]) if d in daily else 0.0 for d in dates]
    return dates, series, n


def tstat(xs):
    if len(xs) < 3 or statistics.stdev(xs) == 0:
        return 0.0
    return statistics.mean(xs) / (statistics.stdev(xs) / math.sqrt(len(xs)))


def verdict(n_days, mean, t):
    if n_days < MIN_DAYS:
        return "FORWARD-TEST"
    return "PROMOTE" if (mean > 0 and t >= 2) else "FAIL"


def cmd_score(a):
    uni = universe()
    out = {"freeze": FREEZE, "params": PARAMS, "names": len(uni)}
    for cost in COSTS:
        dates, s, n = forward_series(uni, cost)
        m = statistics.mean(s) if s else 0.0
        out["cost_%g" % cost] = {"days": len(dates), "trades": n, "mean_bp_day": m, "t": tstat(s),
                                 "first": dates[0] if dates else None, "last": dates[-1] if dates else None}
    r = out["cost_5"]
    out["verdict"] = verdict(r["days"], r["mean_bp_day"], r["t"])
    print("Stocks in play, forward since %s (%d names): %d sessions, %d trades, %.1f bp/day, t %.2f at 5 bps "
          "(3 bps: %.1f bp/day) -> %s (decided at %d sessions)" % (
              FREEZE, len(uni), r["days"], r["trades"], r["mean_bp_day"], r["t"],
              out["cost_3"]["mean_bp_day"], out["verdict"], MIN_DAYS))
    if a.write:
        with open(a.write, "w") as fh:
            json.dump(out, fh, indent=1)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("score")
    p.add_argument("--write", nargs="?", const=os.path.join(lab.RESULTS, "sip-forward.json"))
    a = ap.parse_args(argv)
    return cmd_score(a) if a.cmd == "score" else ap.print_help() or 1


if __name__ == "__main__":
    sys.exit(main())
