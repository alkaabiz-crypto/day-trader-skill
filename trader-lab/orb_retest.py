#!/usr/bin/env python3
"""The owner's second video strategy: 15-minute opening range, break and close, then buy the retest. Pre-registered.

    python3 orb_retest.py run [--write]   # uses data/long (Tiingo 5-minute bars) -> results/orb-retest.json

The video (NAS100, 2026-11-25): at 9:30 New York mark the high and low of the first 15 minutes; on the 5-minute
chart wait for a candle to "break and close" outside that range; "no chase price": wait for price to come back and
touch the broken level ("mark zone", "price touch zone"), then enter in the break's direction with a small stop
just inside the zone and a much larger target.

PRE-REGISTERED 2026-11-25, committed before any result. Not to be changed:
  Market: QQQ (the Nasdaq-100 fund, standing in for NAS100), plus SPY and IWM reported alongside; Tiingo IEX
    5-minute bars in data/long, full sessions only (half days dropped).
  Range: high and low of the 9:30, 9:35 and 9:40 candles (9:30-9:45).
  Break: the first candle from 9:45 on whose close is above the range high (long) or below the range low (short).
    One setup a day.
  Entry: a limit order at the broken level, live from the candle after the break until 11:30; it fills when a
    candle trades back to the level (at the level, or at the open if the candle opens past it).
  Stop: 25% of the range height back inside the range from the level. Target: 3 times the stop distance (primary);
    2R and 5R reported as secondary variants (the video's box is drawn at about 5-7R). If a candle touches the
    stop and the target, the stop counts; the fill candle can stop out but can't reach the target. Anything still
    open is sold at the 15:55 close.
  Costs: 3 bps a round trip (5 reported).
  Split: in-sample before 2025-01-01, judged from 2025-01-01.
  Verdict (primary, QQQ, 3R): PASS only if judged t >= 3 on per-trade returns and in-sample t > 0. The 2R and 5R
    variants and SPY/IWM are reported but can't pass on their own.
  Reported: what $500 became, putting the whole $500 into every trade (no leverage), next to $500 in QQQ.
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

RESULTS = os.path.join(HERE, "results")
MARKETS = ["QQQ", "SPY", "IWM"]
RANGE_SLOTS = 3          # 9:30, 9:35, 9:40
LAST_ENTRY_SLOT = 24     # 11:30
STOP_FRAC = 0.25
TARGETS = (3.0, 2.0, 5.0)
COST_BPS, REF_COST_BPS = 3.0, 5.0
SPLIT, T_BAR = "2025-01-01", 3.0


def day_trade(bars, r_mult, stop_frac=STOP_FRAC):
    """bars: one full session of 78 dicts (o h l c). Returns (side, entry, exit, why) or None."""
    hi = max(b["h"] for b in bars[:RANGE_SLOTS])
    lo = min(b["l"] for b in bars[:RANGE_SLOTS])
    rng = hi - lo
    if rng <= 0:
        return None
    side = None
    for k in range(RANGE_SLOTS, len(bars)):
        if bars[k]["c"] > hi:
            side, level, brk = 1, hi, k
            break
        if bars[k]["c"] < lo:
            side, level, brk = -1, lo, k
            break
    if side is None:
        return None
    stop = level - side * stop_frac * rng
    target = level + side * r_mult * stop_frac * rng
    entry = fill = None
    for k in range(brk + 1, min(LAST_ENTRY_SLOT + 1, len(bars))):
        b = bars[k]
        if (side > 0 and b["l"] <= level) or (side < 0 and b["h"] >= level):
            entry = min(level, b["o"]) if side > 0 else max(level, b["o"])
            fill = k
            break
    if entry is None:
        return None
    for k in range(fill, len(bars)):
        b = bars[k]
        if (side > 0 and b["l"] <= stop) or (side < 0 and b["h"] >= stop):
            px = min(stop, b["o"]) if (side > 0 and k > fill) else (max(stop, b["o"]) if (side < 0 and k > fill) else stop)
            return side, entry, px, "stop"
        if k > fill and ((side > 0 and b["h"] >= target) or (side < 0 and b["l"] <= target)):
            px = max(target, b["o"]) if side > 0 else min(target, b["o"])
            return side, entry, px, "target"
    return side, entry, bars[-1]["c"], "close"


def run_market(sym, r_mult, cost):
    bars = lab.load_store(sym, lab.LONG_STORE)
    out = []
    for d, b in lab.sessions_of(lab.drop_after_early_close(bars)):
        if len(b) != lab.SESSION_BARS:
            continue
        t = day_trade(b, r_mult)
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
    usd_all = 500.0
    for t in trades:
        usd_all *= 1 + t["ret"]
    return {"in_sample": f(a), "judged": f(b), "usd_judged": usd, "usd_all": usd_all,
            "exits": {w: sum(t["why"] == w for t in trades) for w in ("stop", "target", "close")}}


def hold_usd(sym, first):
    bars = lab.load_store(sym, lab.LONG_STORE)
    ss = [(d, b) for d, b in lab.sessions_of(lab.drop_after_early_close(bars)) if len(b) == lab.SESSION_BARS]
    j = [(d, b) for d, b in ss if d >= first]
    return 500.0 * j[-1][1][-1]["c"] / j[0][1][0]["o"] if j else None


def cmd_run(a):
    res = {"markets": {}}
    for sym in MARKETS:
        res["markets"][sym] = {}
        for r in TARGETS:
            s = summarize(run_market(sym, r, COST_BPS))
            s["ref_cost_judged_mean_bps"] = summarize(run_market(sym, r, REF_COST_BPS))["judged"]["mean_bps"]
            res["markets"][sym]["%gR" % r] = s
            print("%s %gR | IS %3d trades %+6.1f bp t %+5.2f win %.0f%% | judged %3d trades %+6.1f bp t %+5.2f win %.0f%% "
                  "| $500 -> $%.0f since 2025 | exits %s" % (
                      sym, r, s["in_sample"]["trades"], s["in_sample"]["mean_bps"], s["in_sample"]["t"],
                      100 * (s["in_sample"]["win_rate"] or 0), s["judged"]["trades"], s["judged"]["mean_bps"],
                      s["judged"]["t"], 100 * (s["judged"]["win_rate"] or 0), s["usd_judged"], s["exits"]))
        res["markets"][sym]["hold_usd_judged"] = hold_usd(sym, SPLIT)
    p = res["markets"]["QQQ"]["3R"]
    res["verdict"] = "PASS" if (p["judged"]["t"] >= T_BAR and p["in_sample"]["t"] > 0) else "FAIL"
    print("QQQ held from 2025: $500 -> $%.0f | verdict (QQQ, 3R): %s" % (res["markets"]["QQQ"]["hold_usd_judged"],
                                                                          res["verdict"]))
    if a.write:
        with open(a.write, "w") as fh:
            json.dump(res, fh, indent=1)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("run")
    r.add_argument("--write", nargs="?", const=os.path.join(RESULTS, "orb-retest.json"))
    a = ap.parse_args(argv)
    return cmd_run(a) if a.cmd == "run" else ap.print_help() or 1


if __name__ == "__main__":
    sys.exit(main())
