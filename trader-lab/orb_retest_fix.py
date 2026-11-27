#!/usr/bin/env python3
"""Fix round for the video strategy (orb_retest.py): choose on 2022-2024 only, then test once on 2025 on.

    python3 orb_retest_fix.py run [--write]   # -> results/orb-retest-fix.json

The owner asked to "fix the fails". Trying fixes until something passes would just fit the past, so this round
follows the only honest procedure: every fix is fixed in advance below, the choice is made on the in-sample years
alone, and the chosen version is run once on the judged years it never saw.

PRE-REGISTERED 2026-11-25, committed before any fix was run. Not to be changed:
  Base: orb_retest.day_trade on QQQ (the video's NAS100), same costs (3 bps), same fills, same 4 years.
  Fixes (each alone, and each with long-only), the common add-ons for opening-range strategies:
    none          the video as tested
    trend         only in the direction of the daily trend: close of the prior day vs its 20-day average
    rvol          only when the opening range's volume is at least 1.5x its 14-day average
    gap           only when the opening gap (open vs prior close) has the break's sign
    narrow        only when the range is below the median of the prior 20 days' ranges
    wide          only when the range is above that median
    fade          the opposite trade at the same level: when the retest happens, bet the break fails
                  (stop and target mirrored)
    breakout      no retest: enter at the close of the break candle, stop 25% inside the range, same target
  Targets 2R and 3R. That is 8 fixes x 2 directions x 2 targets = 32 versions.
  Choice: the version with the highest in-sample (2022-11 to 2024-12) t, with at least 150 in-sample trades.
  Test: that one version on 2025 on. PASS only if judged t >= 3 (Bonferroni over 32 at 5% is about 3.2, so 3 is
    near it, and only one version is judged). Also reported: every version's judged numbers (for honesty; they
    play no part in the choice) and $500 for the chosen one against holding QQQ.
Research, not financial advice.
"""

import argparse
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lab  # noqa: E402
import orb_retest as orr  # noqa: E402
import paper500 as p5  # noqa: E402

RESULTS = os.path.join(HERE, "results")
FIXES = ["none", "trend", "rvol", "gap", "narrow", "wide", "fade", "breakout"]
TARGETS = (2.0, 3.0)
MIN_IS_TRADES = 150
SYMBOL = "QQQ"


def trade(bars, fix, r_mult):
    """(side, entry, exit) for one session under a fix's entry logic, before filters."""
    if fix == "breakout":
        hi = max(b["h"] for b in bars[:orr.RANGE_SLOTS])
        lo = min(b["l"] for b in bars[:orr.RANGE_SLOTS])
        rng = hi - lo
        if rng <= 0:
            return None
        for k in range(orr.RANGE_SLOTS, len(bars)):
            side = 1 if bars[k]["c"] > hi else (-1 if bars[k]["c"] < lo else 0)
            if side:
                if k > orr.LAST_ENTRY_SLOT:
                    return None
                e = bars[k]["c"]
                level = hi if side > 0 else lo
                stop = level - side * orr.STOP_FRAC * rng
                risk = abs(e - stop)
                target = e + side * r_mult * risk
                for j in range(k + 1, len(bars)):
                    b = bars[j]
                    if (side > 0 and b["l"] <= stop) or (side < 0 and b["h"] >= stop):
                        return side, e, (min(stop, b["o"]) if side > 0 else max(stop, b["o"]))
                    if (side > 0 and b["h"] >= target) or (side < 0 and b["l"] <= target):
                        return side, e, (max(target, b["o"]) if side > 0 else min(target, b["o"]))
                return side, e, bars[-1]["c"]
        return None
    if fix == "fade":
        base = orr.day_trade(bars, 1.0)          # find the retest fill; the trade itself is mirrored below
        if base is None:
            return None
        side0, e, _, _ = base
        hi = max(b["h"] for b in bars[:orr.RANGE_SLOTS])
        lo = min(b["l"] for b in bars[:orr.RANGE_SLOTS])
        dist = orr.STOP_FRAC * (hi - lo)
        side = -side0
        stop, target = e - side * dist, e + side * r_mult * dist
        fill = None
        for k in range(orr.RANGE_SLOTS, len(bars)):
            if (side0 > 0 and bars[k]["l"] <= e) or (side0 < 0 and bars[k]["h"] >= e):
                if k > orr.RANGE_SLOTS and any((side0 > 0 and bars[j]["c"] > hi) or (side0 < 0 and bars[j]["c"] < lo)
                                               for j in range(orr.RANGE_SLOTS, k)):
                    fill = k
                    break
        if fill is None:
            return None
        for k in range(fill, len(bars)):
            b = bars[k]
            if (side > 0 and b["l"] <= stop) or (side < 0 and b["h"] >= stop):
                return side, e, stop if k == fill else (min(stop, b["o"]) if side > 0 else max(stop, b["o"]))
            if k > fill and ((side > 0 and b["h"] >= target) or (side < 0 and b["l"] <= target)):
                return side, e, (max(target, b["o"]) if side > 0 else min(target, b["o"]))
        return side, e, bars[-1]["c"]
    t = orr.day_trade(bars, r_mult)
    return None if t is None else t[:3]


def context(sessions, k):
    """Prior-day facts for session k: prior close, 20-day average close, 14-day average opening-range volume,
    median of the prior 20 ranges."""
    if k < 21:
        return None
    prev = [sessions[j][1] for j in range(k - 20, k)]
    closes = [b[-1]["c"] for b in prev]
    ranges = [max(x["h"] for x in b[:orr.RANGE_SLOTS]) - min(x["l"] for x in b[:orr.RANGE_SLOTS]) for b in prev]
    vols = [sum(x["v"] for x in b[:orr.RANGE_SLOTS]) for b in prev[-14:]]
    return {"prev_close": closes[-1], "avg20": sum(closes) / 20, "avg_vol": sum(vols) / 14,
            "med_range": sorted(ranges)[10]}


def allowed(fix, side, bars, ctx):
    if fix in ("none", "fade", "breakout"):
        return True
    rng = max(b["h"] for b in bars[:orr.RANGE_SLOTS]) - min(b["l"] for b in bars[:orr.RANGE_SLOTS])
    if fix == "trend":
        return (ctx["prev_close"] > ctx["avg20"]) == (side > 0)
    if fix == "rvol":
        return sum(b["v"] for b in bars[:orr.RANGE_SLOTS]) >= 1.5 * ctx["avg_vol"]
    if fix == "gap":
        g = bars[0]["o"] - ctx["prev_close"]
        return g != 0 and (g > 0) == (side > 0)
    if fix == "narrow":
        return rng < ctx["med_range"]
    if fix == "wide":
        return rng > ctx["med_range"]
    raise ValueError(fix)


def run_version(sessions, fix, long_only, r_mult):
    out = []
    for k, (d, bars) in enumerate(sessions):
        ctx = context(sessions, k)
        if ctx is None:
            continue
        t = trade(bars, fix, r_mult)
        if t is None:
            continue
        side, e, x = t
        if long_only and side < 0:
            continue
        if not allowed(fix, side if fix != "fade" else -side, bars, ctx):
            continue
        out.append((d, side * (x / e - 1) - orr.COST_BPS / 1e4))
    return out


def stats(trades, lo=None, hi=None):
    x = [r for d, r in trades if (lo is None or d >= lo) and (hi is None or d < hi)]
    return {"trades": len(x), "mean_bps": 1e4 * statistics.mean(x) if x else 0.0, "t": p5.tstat(x),
            "win_rate": (sum(v > 0 for v in x) / len(x)) if x else None}


def cmd_run(a):
    bars = lab.load_store(SYMBOL, lab.LONG_STORE)
    sessions = [(d, b) for d, b in lab.sessions_of(lab.drop_after_early_close(bars)) if len(b) == lab.SESSION_BARS]
    versions = []
    for fix in FIXES:
        for long_only in (False, True):
            for r in TARGETS:
                tr = run_version(sessions, fix, long_only, r)
                versions.append({"fix": fix, "long_only": long_only, "target_r": r, "trades": tr,
                                 "in_sample": stats(tr, hi=orr.SPLIT)})
    eligible = [v for v in versions if v["in_sample"]["trades"] >= MIN_IS_TRADES]
    best = max(eligible, key=lambda v: v["in_sample"]["t"])
    for v in versions:
        v["judged"] = stats(v["trades"], lo=orr.SPLIT)
    usd = 500.0
    for d, r in best["trades"]:
        if d >= orr.SPLIT:
            usd *= 1 + r
    hold = orr.hold_usd(SYMBOL, orr.SPLIT)
    verdict = "PASS" if best["judged"]["t"] >= orr.T_BAR else "FAIL"
    print("%-9s %-5s %3s | %4s %8s %6s | %4s %8s %6s" % ("fix", "long", "R", "IS n", "IS bp", "IS t", "J n", "J bp", "J t"))
    for v in sorted(versions, key=lambda v: -v["in_sample"]["t"]):
        mark = "  <- chosen on 2022-2024 only" if v is best else ""
        print("%-9s %-5s %3g | %4d %+8.1f %+6.2f | %4d %+8.1f %+6.2f%s" % (
            v["fix"], "yes" if v["long_only"] else "no", v["target_r"], v["in_sample"]["trades"],
            v["in_sample"]["mean_bps"], v["in_sample"]["t"], v["judged"]["trades"], v["judged"]["mean_bps"],
            v["judged"]["t"], mark))
    print("chosen: %s%s %gR -> judged t %.2f, $500 -> $%.0f since 2025 (QQQ held $%.0f) -> %s" % (
        best["fix"], " long-only" if best["long_only"] else "", best["target_r"], best["judged"]["t"], usd, hold, verdict))
    if a.write:
        for v in versions:
            v.pop("trades")
        with open(a.write, "w") as fh:
            json.dump({"versions": versions, "chosen": {k: best[k] for k in ("fix", "long_only", "target_r", "in_sample",
                                                                             "judged")},
                       "usd_judged": usd, "hold_usd_judged": hold, "verdict": verdict}, fh, indent=1)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("run")
    r.add_argument("--write", nargs="?", const=os.path.join(RESULTS, "orb-retest-fix.json"))
    a = ap.parse_args(argv)
    return cmd_run(a) if a.cmd == "run" else ap.print_help() or 1


if __name__ == "__main__":
    sys.exit(main())
