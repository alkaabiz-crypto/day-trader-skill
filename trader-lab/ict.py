#!/usr/bin/env python3
"""ICT (Inner Circle Trader) setups, tested on 4 years of 5-minute bars. Pre-registered.

    python3 ict.py run [--write]      # data/long (Tiingo 5-minute bars) -> results/ict.json

ICT teaches fair value gaps (FVG), liquidity sweeps, market structure shifts and time windows ("killzones").
Many ICT ideas (order blocks, "smart money" intent) have no single agreed definition, so only the two setups
that can be written as exact rules are tested, in their most common published form:

  FVG (fair value gap) on 5-minute candles 1, 2, 3:
    bullish: candle 3's low is above candle 1's high (a gap the middle candle left); the zone is
             candle 1 high .. candle 3 low
    bearish: candle 3's high is below candle 1's low; the zone is candle 3 high .. candle 1 low

  1. SILVER BULLET (ICT's 10:00-11:00 New York window): the first FVG whose third candle closes from 10:00 to
     10:55. Trade in its direction: a limit at the near edge of the zone (bullish: candle 3's low; bearish:
     candle 3's high), live until the 11:00 candle closes. Stop beyond candle 1 (bullish: candle 1's low;
     bearish: candle 1's high).
  2. JUDAS SWING (liquidity sweep + market structure shift, 9:30-11:30): price trades below the previous
     session's low (sweep of sell-side liquidity), then a candle closes back above it; the first bullish FVG
     after that close, before 11:30, gives a long: limit at the zone's near edge, stop at the session low so
     far (below the sweep). Mirror for a sweep of the previous high. The first event of the day only.

PRE-REGISTERED 2026-11-26 (the owner asked "can u test ict"), committed before any run. Not to be changed:
  Markets: QQQ (the Nasdaq-100, standing in for NAS100), SPY and IWM; Tiingo IEX 5-minute bars in data/long,
    full sessions only (half days dropped). One trade per setup per day.
  Target: 2R (primary); 3R reported. If a candle touches both the stop and the target, the stop counts; the fill
    candle can stop out but can't reach the target. Open trades are sold at the 15:55 close.
  Costs: 3 bps a round trip (5 reported).
  Split: in-sample before 2025-01-01, judged from 2025-01-01.
  PASS (per setup, QQQ, 2R): judged t >= 3 on per-trade returns and in-sample t > 0. SPY, IWM and 3R are
    reported but can't pass on their own.
  Reported: what $500 became since 2025 (the whole $500 in each trade, no leverage) next to $500 in QQQ.
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
import paper500 as p5  # noqa: E402

RESULTS = os.path.join(HERE, "results", "ict.json")
MARKETS = ["QQQ", "SPY", "IWM"]
TARGETS = (2.0, 3.0)
COST_BPS, REF_COST_BPS = 3.0, 5.0
SPLIT, T_BAR = "2025-01-01", 3.0
SB_FIRST, SB_LAST = 6, 17      # third candle starting 10:00 .. 10:55 (bar index in the 9:30-based session)
SB_FILL_END = 17               # the limit is live through the 10:55 candle (until 11:00)
JUDAS_END = 24                 # 11:30


def fvg(bars, k):
    """FVG whose third candle is bar k: (+1, near_edge, far_stop) bullish, (-1, ...) bearish, or None."""
    if k < 2:
        return None
    c1, c3 = bars[k - 2], bars[k]
    if c3["l"] > c1["h"]:
        return (1, c3["l"], c1["l"])
    if c3["h"] < c1["l"]:
        return (-1, c3["h"], c1["h"])
    return None


def manage(bars, start, side, entry, stop, r_mult, fill_end):
    """Limit entry from bar `start` to `fill_end`; then stop / target / 15:55 close. -> (entry, exit, why)."""
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    target = entry + side * r_mult * risk
    for j in range(start, min(fill_end, len(bars) - 1) + 1):
        b = bars[j]
        touched = b["l"] <= entry if side > 0 else b["h"] >= entry
        if not touched:
            continue
        e = entry
        if side > 0 and b["o"] < entry:
            e = b["o"]
        if side < 0 and b["o"] > entry:
            e = b["o"]
        if (side > 0 and b["l"] <= stop) or (side < 0 and b["h"] >= stop):
            return (e, stop, "stop")
        for b2 in bars[j + 1:]:
            if (side > 0 and b2["l"] <= stop) or (side < 0 and b2["h"] >= stop):
                return (e, stop, "stop")
            if (side > 0 and b2["h"] >= target) or (side < 0 and b2["l"] <= target):
                return (e, target, "target")
        return (e, bars[-1]["c"], "close")
    return None


def silver_bullet(bars, prev, r_mult):
    for k in range(SB_FIRST, SB_LAST + 1):
        g = fvg(bars, k)
        if g:
            side, edge, stop = g
            got = manage(bars, k + 1, side, edge, stop, r_mult, SB_FILL_END)
            return (side,) + got if got else None
    return None


def judas(bars, prev, r_mult):
    if not prev:
        return None
    pdh = max(b["h"] for b in prev)
    pdl = min(b["l"] for b in prev)
    swept = 0
    for k in range(0, JUDAS_END):
        b = bars[k]
        if not swept:
            if b["l"] < pdl and b["c"] > pdl:
                swept, k0 = 1, k          # swept and closed back above in the same candle
            elif b["h"] > pdh and b["c"] < pdh:
                swept, k0 = -1, k
            elif b["l"] < pdl:
                swept, k0 = 2, k          # swept, waiting for a close back above
            elif b["h"] > pdh:
                swept, k0 = -2, k
            continue
        if swept == 2:
            if b["c"] > pdl:
                swept = 1
            continue
        if swept == -2:
            if b["c"] < pdh:
                swept = -1
            continue
        g = fvg(bars, k)
        if g and g[0] == swept and k - 2 >= k0:
            side, edge, _ = g
            stop = min(x["l"] for x in bars[:k + 1]) if side > 0 else max(x["h"] for x in bars[:k + 1])
            got = manage(bars, k + 1, side, edge, stop, r_mult, JUDAS_END)
            return (side,) + got if got else None
    return None


SETUPS = {"silver_bullet": silver_bullet, "judas_swing": judas}


def run_market(sym, setup, r_mult, cost):
    bars = lab.load_store(sym, lab.LONG_STORE)
    out, prev = [], None
    for d, b in lab.sessions_of(lab.drop_after_early_close(bars)):
        if len(b) != lab.SESSION_BARS:
            prev = None
            continue
        t = SETUPS[setup](b, prev, r_mult)
        prev = b
        if t:
            side, e, x, why = t
            out.append({"date": d, "side": side, "ret": side * (x / e - 1) - cost / 1e4, "why": why})
    return out


def summarize(trades):
    a = [t["ret"] for t in trades if t["date"] < SPLIT]
    b = [t["ret"] for t in trades if t["date"] >= SPLIT]
    f = lambda x: {"trades": len(x), "mean_bps": 1e4 * statistics.mean(x) if x else 0.0, "t": p5.tstat(x),  # noqa: E731
                   "win_rate": (sum(v > 0 for v in x) / len(x)) if x else None}
    usd = 500.0
    for t in trades:
        if t["date"] >= SPLIT:
            usd *= 1 + t["ret"]
    return {"in_sample": f(a), "judged": f(b), "usd_judged": usd,
            "exits": {w: sum(t["why"] == w for t in trades) for w in ("stop", "target", "close")}}


def hold_usd(sym, first):
    bars = lab.load_store(sym, lab.LONG_STORE)
    ss = [(d, b) for d, b in lab.sessions_of(lab.drop_after_early_close(bars)) if len(b) == lab.SESSION_BARS]
    j = [(d, b) for d, b in ss if d >= first]
    return 500.0 * j[-1][1][-1]["c"] / j[0][1][0]["o"] if j else None


def cmd_run(a):
    res = {"setups": {}, "hold_usd_judged": {}}
    for setup in SETUPS:
        res["setups"][setup] = {}
        for sym in MARKETS:
            res["setups"][setup][sym] = {}
            for r in TARGETS:
                s = summarize(run_market(sym, setup, r, COST_BPS))
                s["ref_cost_judged_mean_bps"] = summarize(run_market(sym, setup, r, REF_COST_BPS))["judged"]["mean_bps"]
                res["setups"][setup][sym]["%gR" % r] = s
                print("%-13s %s %gR | IS %3d trades %+6.1f bp t %+5.2f win %.0f%% | judged %3d trades %+6.1f bp "
                      "t %+5.2f win %.0f%% | $500 -> $%.0f since 2025 | exits %s" % (
                          setup, sym, r, s["in_sample"]["trades"], s["in_sample"]["mean_bps"], s["in_sample"]["t"],
                          100 * (s["in_sample"]["win_rate"] or 0), s["judged"]["trades"], s["judged"]["mean_bps"],
                          s["judged"]["t"], 100 * (s["judged"]["win_rate"] or 0), s["usd_judged"], s["exits"]),
                      flush=True)
    for sym in MARKETS:
        res["hold_usd_judged"][sym] = hold_usd(sym, SPLIT)
    res["verdict"] = {}
    for setup in SETUPS:
        p = res["setups"][setup]["QQQ"]["2R"]
        res["verdict"][setup] = "PASS" if (p["judged"]["t"] >= T_BAR and p["in_sample"]["t"] > 0) else "FAIL"
    print("QQQ held from 2025: $500 -> $%.0f | verdicts (QQQ, 2R): %s. Research, not financial advice." % (
        res["hold_usd_judged"]["QQQ"], ", ".join("%s %s" % kv for kv in res["verdict"].items())))
    if a.write:
        with open(RESULTS, "w") as fh:
            json.dump(res, fh, indent=1)
        print("Wrote %s" % os.path.relpath(RESULTS, HERE))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="ICT setups on 5-minute bars")
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
