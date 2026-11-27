#!/usr/bin/env python3
"""30-minute opening range, 10-minute close outside it, then a pullback to the 20 EMA (from a video).

    python3 orb_ema.py test [--write]      # uses the 4-year Tiingo store in data/long

Source: a short-form video by a prop-firm trader ("flexingjoetrades", Nasdaq futures, payouts from Apex
Trader Funding shown as proof). The rules, as shown on screen:
  1. Opening range = high to low of 9:30-10:00 Eastern.
  2. Wait for a 10-minute candle to CLOSE outside the range.
  3. Switch to a 2-minute chart with a 20 EMA; once price pulls back and interacts with the EMA, enter in the
     direction of the break (the video shows a long).
Not shown clearly: where the stop and the target go (the position tool's labels are ambiguous), whether shorts
are taken, and any time cut-off. Payout screenshots are not a track record: they show withdrawals, not losses
or the number of accounts blown.

PRE-REGISTERED 2026-11-23 before any result was seen. Not to be changed after the first run:
  * Instrument: QQQ (the Nasdaq-100 ETF; NQ futures are not in free data). SPY and IWM reported alongside,
    not part of the verdict.
  * Data: Tiingo IEX 5-minute bars, Nov 2022 to Nov 2026, half days cut at 13:00. There are no 2-minute bars
    in the lab, so the 2-minute 20 EMA (a 40-minute span) is approximated by an EMA(8) on 5-minute bars (same
    span); EMA(20) on 5-minute bars is a variant. The EMA runs on the day's bars from the open.
  * Setup: opening range = bars 9:30-9:55 (six 5-minute bars). 10-minute candles = pairs of 5-minute bars
    starting 10:00, 10:10, ... The first 10-minute close above the range high = long setup (below the low =
    short), only the first break of the day, and only if it happens before 14:00.
  * Entry: after the break, the first 5-minute bar whose low touches the EMA (high, for shorts) and that
    closes on the break side of the EMA; enter at that bar's close. If price closes back inside the opening
    range first, the setup is cancelled. No entry after 15:30. One trade per day.
  * Stop: variant "bar" = the entry bar's low (high, for shorts); variant "range" = the broken range edge.
    Target: 2R, 3R, or none (hold to 15:55 close). Always flat at the 15:55 bar's close. If a bar touches both
    stop and target, the stop counts (worst case).
  * Grid: stop {bar, range} x target {2R, 3R, close} x EMA {8, 20} x sides {both, long-only} = 24 variants,
    chosen on QQQ's in-sample t only.
  * Costs per round trip: 1.5 bps (close to NQ futures) and 3 bps (QQQ with slippage). PASS needs both.
  * Gates (as lab.py): IS = first 50% of dates, OOS = next 25%, HOLDOUT = last 25%. PASS needs IS t >= 2, OOS
    and HOLDOUT mean > 0, post-IS t >= 3, and a direction placebo (each trade's side flipped at random,
    1,000 draws) beating the real post-IS t less than 5% of the time.
Research, not financial advice.
"""

import argparse
import json
import math
import os
import random
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lab  # noqa: E402  (data store and calendar helpers only; lab.py is not edited)

SYMS = ["QQQ", "SPY", "IWM"]
COSTS = (1.5, 3.0)
OR_BARS = 6            # 9:30-10:00
LAST_BREAK = 54        # bar index of 14:00
LAST_ENTRY = 72        # bar index of 15:30
GRID = [{"stop": s, "target": t, "ema": e, "sides": d}
        for s in ("bar", "range") for t in (2.0, 3.0, None) for e in (8, 20) for d in ("both", "long")]
PLACEBO_REPS = 1000


def ema_series(closes, n):
    k = 2.0 / (n + 1)
    out, e = [], None
    for c in closes:
        e = c if e is None else e + k * (c - e)
        out.append(e)
    return out


def day_trade(bars, p):
    """One day's trade or None: (side, entry, exit) prices."""
    if len(bars) != lab.SESSION_BARS:
        return None
    hi = max(b["h"] for b in bars[:OR_BARS])
    lo = min(b["l"] for b in bars[:OR_BARS])
    side, brk = 0, None
    for j in range(OR_BARS, LAST_BREAK, 2):          # 10-minute candle = bars j, j+1; close = bar j+1
        c = bars[j + 1]["c"]
        if c > hi:
            side, brk = 1, j + 1
        elif c < lo:
            side, brk = -1, j + 1
        if side:
            break
    if not side or (p["sides"] == "long" and side < 0):
        return None
    ema = ema_series([b["c"] for b in bars], p["ema"])
    entry_i = None
    for i in range(brk + 1, LAST_ENTRY + 1):
        b = bars[i]
        if (side > 0 and b["c"] < hi) or (side < 0 and b["c"] > lo):
            return None                              # back inside the range: setup cancelled
        touch = b["l"] <= ema[i] if side > 0 else b["h"] >= ema[i]
        holds = b["c"] > ema[i] if side > 0 else b["c"] < ema[i]
        if touch and holds:
            entry_i = i
            break
    if entry_i is None:
        return None
    entry = bars[entry_i]["c"]
    if p["stop"] == "bar":
        stop = bars[entry_i]["l"] if side > 0 else bars[entry_i]["h"]
    else:
        stop = hi if side > 0 else lo
    risk = (entry - stop) * side
    if risk <= 0:
        return None
    target = entry + side * p["target"] * risk if p["target"] else None
    for i in range(entry_i + 1, lab.SESSION_BARS):
        b = bars[i]
        hit_stop = b["l"] <= stop if side > 0 else b["h"] >= stop
        if hit_stop:
            fill = min(stop, b["o"]) if side > 0 else max(stop, b["o"])   # gap through the stop fills worse
            return side, entry, fill
        if target is not None and (b["h"] >= target if side > 0 else b["l"] <= target):
            fill = max(target, b["o"]) if side > 0 else min(target, b["o"])
            return side, entry, fill
    return side, entry, bars[-1]["c"]


def run(sessions, p, cost):
    """[(date, net bps, side, gross bps)] for every trade."""
    out = []
    for d, bars in sessions:
        t = day_trade(bars, p)
        if t:
            side, a, b = t
            g = side * (b / a - 1) * 1e4
            out.append((d, g - cost, side, g))
    return out


def tstat(xs):
    if len(xs) < 3:
        return 0.0
    sd = statistics.stdev(xs)
    return statistics.mean(xs) / (sd / math.sqrt(len(xs))) if sd > 0 else 0.0


def parts(trades, dates):
    c1, c2 = dates[int(len(dates) * 0.5)], dates[int(len(dates) * 0.75)]
    pick = lambda f: [x[1] for x in trades if f(x[0])]
    return {"is": pick(lambda d: d < c1), "oos": pick(lambda d: c1 <= d < c2),
            "ho": pick(lambda d: d >= c2), "post": pick(lambda d: d >= c1), "cuts": (c1, c2)}


def summ(xs):
    return {"n": len(xs), "mean_bps": statistics.mean(xs) if xs else 0.0, "t": tstat(xs),
            "win": sum(1 for x in xs if x > 0) / len(xs) if xs else 0.0}


def placebo_p(trades, c1, cost, reps=PLACEBO_REPS, seed=23):
    post = [x for x in trades if x[0] >= c1]
    real = tstat([x[1] for x in post])
    rnd = random.Random(seed)
    hits = 0
    for _ in range(reps):
        flipped = [(x[3] if rnd.random() < 0.5 else -x[3]) - cost for x in post]
        hits += tstat(flipped) >= real
    return hits / reps


def cmd_test(a):
    data = {}
    for s in SYMS:
        bars = lab.load_store(s, lab.LONG_STORE)
        if not bars:
            raise lab.LabError("no %s in data/long: run lab.py fetch-tiingo" % s)
        data[s] = [(d, b) for d, b in lab.sessions_of(lab.drop_after_early_close(bars)) if d < "2026-11-21"]
    dates = [d for d, b in data["QQQ"] if len(b) == lab.SESSION_BARS]
    report = {"variants": [], "chosen": None}
    best = None
    for p in GRID:
        tr = run(data["QQQ"], p, COSTS[0])
        pt = parts(tr, dates)
        s = summ(pt["is"])
        report["variants"].append({"params": p, "is": s})
        if best is None or s["t"] > best[1]["t"]:
            best = (p, s)
    p, s_is = best
    print("Opening range 9:30-10:00, 10-min close outside, pullback to the EMA (QQQ, %s to %s, %d days)" % (
        dates[0], dates[-1], len(dates)))
    print("Chosen on QQQ in-sample t: %s   IS: %d trades, %.1f bp/trade, t %.2f\n" % (
        json.dumps(p), s_is["n"], s_is["mean_bps"], s_is["t"]))
    verdict = True
    res = {"params": p, "is": s_is}
    for cost in COSTS:
        for sym in SYMS:
            tr = run(data[sym], p, cost)
            pt = parts(tr, dates)
            r = {k: summ(pt[k]) for k in ("is", "oos", "ho", "post")}
            if sym == "QQQ":
                r["placebo_p"] = placebo_p(tr, pt["cuts"][0], cost)
                ok = (r["is"]["t"] >= 2 and r["oos"]["mean_bps"] > 0 and r["ho"]["mean_bps"] > 0
                      and r["post"]["t"] >= 3 and r["placebo_p"] < 0.05)
                verdict = verdict and ok
            res["%s_%.1f" % (sym, cost)] = r
            print("%-4s @%.1fbp  IS %3d tr %6.1f bp t %5.2f | OOS %3d tr %6.1f bp | HOLD %3d tr %6.1f bp | post-IS t %5.2f win %3.0f%%%s" % (
                sym, cost, r["is"]["n"], r["is"]["mean_bps"], r["is"]["t"], r["oos"]["n"], r["oos"]["mean_bps"],
                r["ho"]["n"], r["ho"]["mean_bps"], r["post"]["t"], 100 * r["post"]["win"],
                ("  placebo p %.3f" % r["placebo_p"]) if "placebo_p" in r else ""))
    res["verdict"] = "PASS" if verdict else "FAIL"
    report["chosen"] = res
    print("\nVerdict (QQQ, both costs, all gates): %s. Research, not financial advice." % res["verdict"])
    if a.write:
        with open(a.write, "w") as fh:
            json.dump(report, fh, indent=1, sort_keys=True, default=str)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("test")
    p.add_argument("--write", nargs="?", const=os.path.join(lab.RESULTS, "orb-ema.json"))
    a = ap.parse_args(argv)
    try:
        return cmd_test(a) if a.cmd == "test" else ap.print_help() or 1
    except lab.LabError as e:
        print("orb_ema.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
