#!/usr/bin/env python3
"""The overnight / intraday "tug of war" on the lab's 19 ETFs (daily opens and closes since 1996).

    python3 tugofwar.py run [--write]

Source. Lou, Polk & Skouras (2019, Journal of Financial Economics) "A tug of war: Overnight versus
intraday expected returns": momentum profits are earned overnight, and stocks with high past overnight
returns tend to give some back during the day. This is a test on ETFs (no survivorship problem), not stocks.

PRE-REGISTERED 2026-11-27, committed before any run. Not to be changed after the result:
  Universe: the 19 ETFs in daily.UNIVERSE (SPY ... EFA), dividend-adjusted: overnight return
    a[i] * o[i] / c[i] / a[i-1] - 1 (adjusted open over the previous adjusted close), intraday c[i] / o[i] - 1.
  Signal: at each month end, rank the ETFs with 252+ days of history by their summed overnight log return over
    the last 252 trading days. Top third = winners, bottom third = losers. Held the next month.
  Variants (one fixed grid, nothing tuned):
    overnight   long winners, short losers, held close to next open only (each night)
    intraday    long losers, short winners, held open to close only (the reversal leg)
    monthly     long winners, short losers, held close to close for the month
  Costs: COST_BPS (2 bp) a round trip per leg each time a leg is opened and closed: every day for the
    overnight and intraday variants, once a month for monthly. Returns are of $1 long plus $1 short, per day.
  Judged on 2015-01-01 onward (in-sample 1996-2014 only reported). PASS (backtest only): judged daily t >= 3,
    in-sample mean > 0, and beats a random-ranking placebo (200 draws, same legs sizes) 95% of the time.
Research, not financial advice.
"""

import argparse
import json
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import daily  # noqa: E402

JUDGED = "2015-01-01"
LOOKBACK = 252
VARIANTS = ("overnight", "intraday", "monthly")
RESULT = os.path.join(HERE, "results", "tugofwar.json")


def legs(D):
    """{date: (overnight, intraday)} returns, dividend-adjusted."""
    out = {}
    for i in range(1, len(D["d"])):
        if min(D["o"][i], D["c"][i], D["c"][i - 1], D["a"][i - 1]) <= 0:
            continue
        on = D["a"][i] * D["o"][i] / D["c"][i] / D["a"][i - 1] - 1
        out[D["d"][i]] = (on, D["c"][i] / D["o"][i] - 1)
    return out


def month_ends(dates):
    return [d for k, d in enumerate(dates) if k + 1 == len(dates) or dates[k + 1][:7] != d[:7]]


def signals(R, dates):
    """{month-end date: score per symbol}: summed overnight log return over the last LOOKBACK days."""
    out = {}
    for me in month_ends(dates):
        k = dates.index(me)
        if k < LOOKBACK:
            continue
        win = dates[k - LOOKBACK + 1:k + 1]
        sc = {}
        for s, r in R.items():
            if all(d in r for d in win[:1]) and sum(1 for d in win if d in r) >= LOOKBACK - 5:
                sc[s] = sum(math.log1p(r[d][0]) for d in win if d in r)
        if len(sc) >= 6:
            out[me] = sc
    return out


def simulate(R, dates, variant, cost_bps=daily.COST_BPS, rng=None):
    """Daily returns {date: r} of the variant; rng shuffles the ranking (placebo)."""
    sig = signals(R, dates)
    mes = sorted(sig)
    out = {}
    for n, me in enumerate(mes):
        sc = sig[me]
        names = sorted(sc, key=lambda s: sc[s])
        if rng:
            rng.shuffle(names)
        third = len(names) // 3
        losers, winners = names[:third], names[-third:]
        k0 = dates.index(me) + 1
        k1 = dates.index(mes[n + 1]) + 1 if n + 1 < len(mes) else len(dates)
        for k in range(k0, k1):
            d = dates[k]

            def avg(group, j):
                v = [R[s][d][j] for s in group if d in R[s]]
                return sum(v) / len(v) if v else 0.0
            if variant == "overnight":
                r = avg(winners, 0) - avg(losers, 0) - 2 * cost_bps / 1e4
            elif variant == "intraday":
                r = avg(losers, 1) - avg(winners, 1) - 2 * cost_bps / 1e4
            else:
                full = lambda g: avg(g, 0) + avg(g, 1) + avg(g, 0) * avg(g, 1)  # noqa: E731
                r = full(winners) - full(losers) - (2 * cost_bps / 1e4 if k == k0 else 0.0)
            out[d] = r
    return out


def tstat(x):
    n = len(x)
    if n < 3:
        return 0.0
    m = sum(x) / n
    sd = math.sqrt(sum((v - m) ** 2 for v in x) / (n - 1))
    return m / sd * math.sqrt(n) if sd > 0 else 0.0


def load_all():
    R = {}
    for s in daily.UNIVERSE[:19]:
        D = daily.load(s)
        if D:
            k = next((i for i, d in enumerate(D["d"]) if d >= daily.DATA_START), len(D["d"]))
            D = {f: v[k:] for f, v in D.items()}
            R[s] = legs(D)
    dates = sorted(set(d for r in R.values() for d in r))
    return R, dates


def cmd_run(a):
    R, dates = load_all()
    print("Tug of war, %d ETFs, %s to %s, cost %.0f bp a round trip per leg:" % (len(R), dates[0], dates[-1],
                                                                                 daily.COST_BPS))
    out = {"etfs": sorted(R), "variants": {}}
    for v in VARIANTS:
        r = simulate(R, dates, v)
        ins = [x for d, x in r.items() if d < JUDGED]
        jud = [x for d, x in r.items() if d >= JUDGED]
        t = tstat(jud)
        rng = random.Random(7)
        jm = sum(jud) / len(jud)
        beats = 0
        for _ in range(a.placebo):
            p = [x for d, x in simulate(R, dates, v, rng=rng).items() if d >= JUDGED]
            beats += jm > sum(p) / len(p)
        pb = beats / a.placebo if a.placebo else 0.0
        verdict = "PASS (backtest only)" if t >= 3 and sum(ins) > 0 and pb >= 0.95 else "FAIL"
        st = {"in_sample_bp_day": round(1e4 * sum(ins) / len(ins), 2), "judged_bp_day": round(1e4 * jm, 2),
              "judged_t": round(t, 2), "judged_ann_pct": round(100 * 252 * jm, 2), "placebo_beats": pb,
              "verdict": verdict}
        out["variants"][v] = st
        print("  %-10s in-sample %+.2f bp/day | judged %+.2f bp/day (%+.1f%%/yr) t %+.2f | placebo %.0f%% | %s" % (
            v, st["in_sample_bp_day"], st["judged_bp_day"], st["judged_ann_pct"], t, 100 * pb, verdict))
    print("Research, not financial advice.")
    if a.write:
        with open(RESULT, "w") as fh:
            json.dump(out, fh, indent=1)
        print("Wrote %s" % os.path.relpath(RESULT, HERE))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="overnight vs intraday tug of war on ETFs")
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
