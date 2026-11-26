#!/usr/bin/env python3
"""Walk-forward optimization of the indices bot's dip rule on the US indices (US500, USTEC, US30, US2000).

    python3 indexopt.py run [--write] [--placebo 200]

Why walk-forward. Picking the settings that look best on the whole history fits the past and proves nothing.
Here each year is traded with the settings that scored best on the years BEFORE it only, and only those
unseen years are judged.

PRE-REGISTERED 2026-11-26, committed before any run. Not to be changed after the result:
  Markets, costs, fills: as indexbot.py (US-only list; 3 bp spread a round trip + 2 bp a night; next-open fills).
  Grid, 48 settings:
    entry  RSI(2) below 5, 10 or 15 (or the lowest close of 7 days), above its 100- or 200-day average
    exit   RSI(2) above 50 or 70, or the highest close of 7 days, or after 5 or 10 days held
    sizing 5 slots x 20% or 4 slots x 25%
    The current rule is entry 10 / trend 200 / exit 70 / hold 10 / 5 x 20%.
  Walk-forward: for each year 2015 to 2026, choose the setting with the best Sharpe from 2000-01-03 to the
    end of the year before (expanding window), then take that setting's daily returns for that year. Each
    setting runs as one continuous simulation, so a trade open at a year's end belongs to the setting that
    opened it (a small approximation, the same for every setting).
  Pass (indexbot's bar): t >= 2 on the stitched 2015-2026 curve; beats 95% of 200 random-entry placebos on
    the same 4 indices (indexbot's placebo, with the hold lengths of the stitched trades and the sizing most
    often chosen); still positive at 3x costs with the same chosen settings.
  Also reported: the current rule; the best single setting on the whole history (in-sample, overstates); how
  many of the 48 settings are positive after 2015; the setting chosen each year; US500 held.
Research, not financial advice.
"""

import argparse
import itertools
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import indexbot  # noqa: E402
import survivors  # noqa: E402

ENTRY = (5, 10, 15)
TREND = (100, 200)
EXIT = (50, 70)
HOLD = (5, 10)
SIZING = ((5, 0.20), (4, 0.25))
CURRENT = (10, 200, 70, 10, (5, 0.20))
YEARS = list(range(2015, 2027))
RESULT = os.path.join(HERE, "results", "indexopt.json")


def grid():
    return list(itertools.product(ENTRY, TREND, EXIT, HOLD, SIZING))


def label(p):
    return "rsi<%d sma%d exit>%d hold%d %dx%d%%" % (p[0], p[1], p[2], p[3], p[4][0], round(100 * p[4][1]))


def make_features(trend):
    def features(c):
        r = survivors.wilder(c, 2)
        n = len(c)
        above, low7, high7 = [False] * n, [False] * n, [False] * n
        s = 0.0
        for i in range(n):
            s += c[i]
            if i >= trend:
                s -= c[i - trend]
            if i >= trend - 1:
                above[i] = c[i] > s / float(trend)
            if i >= 6:
                w = c[i - 6:i + 1]
                low7[i] = c[i] <= min(w)
                high7[i] = c[i] >= max(w)
        return r, above, low7, high7
    return features


def run(data, p, cost_mult=1.0, placebo=None, rng=None):
    """One indexbot simulation with setting p; restores the module defaults afterwards."""
    entry, trend, ex, hold, (slots, w) = p
    saved = (survivors.features, survivors.entry_signal, survivors.exit_signal, indexbot.SLOTS, indexbot.SLOT_W)
    survivors.features = make_features(trend)
    survivors.entry_signal = lambda r2, ab, lo7: bool(ab) and ((r2 is not None and r2 < entry) or bool(lo7))
    survivors.exit_signal = lambda r2, hi7, held: (r2 is not None and r2 > ex) or bool(hi7) or held >= hold
    indexbot.SLOTS, indexbot.SLOT_W = slots, w
    try:
        return indexbot.simulate(data, cost_mult=cost_mult, placebo=placebo, rng=rng)
    finally:
        (survivors.features, survivors.entry_signal, survivors.exit_signal, indexbot.SLOTS,
         indexbot.SLOT_W) = saved


def sharpe(curve, frm, to):
    s = survivors.summarize(curve, frm, to)
    return s["sharpe"] if s else float("-inf")


def walk_forward(curves, years=YEARS, start=indexbot.START):
    """curves: {setting: curve}. -> ({year: setting}, stitched curve). Each year's choice sees only earlier days."""
    picks, stitched = {}, []
    for y in years:
        cut = "%d-01-01" % y
        best = max(curves, key=lambda p: (sharpe(curves[p], start, cut), p == CURRENT))
        picks[y] = best
        stitched += [x for x in curves[best] if cut <= x[0] < "%d-01-01" % (y + 1)]
    return picks, stitched


def cmd_run(a):
    data = {k: v for k, v in indexbot.load().items() if k in indexbot.US_ONLY}
    G = grid()
    print("Running %d settings on %s ..." % (len(G), ", ".join(indexbot.CFD[s] for s in indexbot.US_ONLY)), flush=True)
    sims = {p: run(data, p) for p in G}
    curves = {p: c for p, (c, _) in sims.items()}
    picks, stitched = walk_forward(curves)
    wf = survivors.summarize(stitched, indexbot.JUDGED)
    cur = survivors.summarize(curves[CURRENT], indexbot.JUDGED)
    after = {p: survivors.summarize(c, indexbot.JUDGED) for p, c in curves.items()}
    best_is = max(G, key=lambda p: after[p]["sharpe"])
    positive = sum(1 for p in G if after[p]["cagr"] > 0)
    # 3x costs with the same yearly choices
    c3 = {p: run(data, p, cost_mult=3)[0] for p in set(picks.values())}
    st3 = []
    for y, p in picks.items():
        st3 += [x for x in c3[p] if "%d-01-01" % y <= x[0] < "%d-01-01" % (y + 1)]
    wf3 = survivors.summarize(st3, indexbot.JUDGED)
    # placebo: random entries with the stitched trades' hold lengths, the sizing most often chosen
    holds = {}
    for y, p in picks.items():
        for t in sims[p][1]:
            if t["in"][:4] == str(y):
                holds.setdefault(t["in"][:4], []).append(max(1, t["held"]))
    sizing = max(SIZING, key=lambda s: sum(1 for p in picks.values() if p[4] == s))
    rng = random.Random(9)
    pts = []
    for _ in range(a.placebo):
        c = run(data, (10, 200, 70, 10, sizing), placebo=holds, rng=rng)[0]
        pts.append(survivors.summarize(c, indexbot.JUDGED)["t"])
    beats = sum(1 for x in pts if x < wf["t"]) / len(pts) if pts else 0.0
    hold = indexbot.buy_hold(data, indexbot.JUDGED)
    ok = wf["t"] >= 2 and beats >= 0.95 and wf3["cagr"] > 0
    verdict = "PASS (backtest only)" if ok else "FAIL"

    print("\n2015-2026, US indices, net of 3 bp + 2 bp a night:")
    print("  %-44s %8s %7s %9s %6s" % ("", "per year", "Sharpe", "max drop", "t"))
    for name, s in (("walk-forward (judged)", wf), ("current rule (fixed)", cur),
                    ("best single setting, in-sample: " + label(best_is), after[best_is]), ("US500 held", hold)):
        print("  %-44s %7.1f%% %7.2f %8.0f%% %6.2f" % (name[:44], 100 * s["cagr"], s["sharpe"], 100 * s["max_dd"],
                                                     s["t"]))
    print("  walk-forward at 3x costs: %.1f%% a year; placebo (%d draws): beats %.0f%%" % (
        100 * wf3["cagr"], len(pts), 100 * beats))
    print("  settings positive after 2015: %d of %d" % (positive, len(G)))
    print("  chosen each year: " + "; ".join("%d %s" % (y, label(p)) for y, p in picks.items()))
    print("Verdict: %s. History, not a forecast; research, not financial advice." % verdict)
    if a.write:
        out = {"walk_forward": wf, "walk_forward_3x": wf3, "current": cur, "us500": hold,
               "best_in_sample": {"setting": label(best_is), **after[best_is]},
               "positive_settings": positive, "settings": len(G),
               "picks": {y: label(p) for y, p in picks.items()},
               "placebo": {"draws": len(pts), "beats": beats}, "verdict": verdict,
               "all": {label(p): after[p] for p in G}}
        with open(RESULT, "w") as fh:
            json.dump(out, fh, indent=1)
        print("Wrote %s" % os.path.relpath(RESULT, HERE))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="walk-forward optimization of the US index dip rule")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("run")
    p.add_argument("--placebo", type=int, default=200)
    p.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd != "run":
        ap.print_help()
        return 1
    return cmd_run(a)


if __name__ == "__main__":
    sys.exit(main())
