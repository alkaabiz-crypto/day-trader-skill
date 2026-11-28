#!/usr/bin/env python3
"""trader-lab judge: one fixed bar for calling a daily strategy "worthy" of a small Exness account.

    import judge
    r = judge.verdict(dates, pnl, pnl_2x, placebo_totals)      # pnl: dollars per day at the minimum lot
    print(judge.line("USTEC IBS", r))

A strategy is WORTHY only if ALL of these hold (fixed 2026-11-28, written before the batch-28 search ran):
  1. before 2024: net > 0 and t >= 2 (daily dollar P&L, zero days included)
  2. 2024 to now: net > 0 and t >= 1 (it still works, not only in old data)
  3. whole period: t >= 3 (many rules were tried; Harvey, Liu & Zhu 2016)
  4. double costs: whole-period net still > 0
  5. random timing: beats >= 95% of placebo copies (same positions at random dates, e.g. rotated)
  6. worst drop at today's minimum lot >= -$300 (the user's limit on a $3,000 account)
Distinctness is checked across candidates with `corr` (daily P&L correlation <= 0.5).
The t statistic is mean / (sd / sqrt(n)). Research, not financial advice.
"""

import math

SPLIT = "2024-01-01"
BAR = dict(pre_t=2.0, post_t=1.0, all_t=3.0, placebo=0.95, max_drop=-300.0, max_corr=0.5)


def tstat(x):
    n = len(x)
    if n < 3:
        return float("nan")
    m = sum(x) / n
    v = sum((a - m) ** 2 for a in x) / (n - 1)
    return m / math.sqrt(v / n) if v > 0 else float("nan")


def worst_drop(pnl):
    v = peak = dd = 0.0
    for x in pnl:
        v += x
        peak = max(peak, v)
        dd = min(dd, v - peak)
    return dd


def yearly(dates, pnl):
    out = {}
    for d, x in zip(dates, pnl):
        out[d[:4]] = out.get(d[:4], 0.0) + x
    return out


def corr(a, b):
    """Correlation of two {date: pnl} maps over the dates they share (missing dates count as 0 in the union)."""
    ks = sorted(set(a) | set(b))
    x = [a.get(k, 0.0) for k in ks]
    y = [b.get(k, 0.0) for k in ks]
    n = len(ks)
    if n < 3:
        return float("nan")
    mx, my = sum(x) / n, sum(y) / n
    sx = math.sqrt(sum((v - mx) ** 2 for v in x))
    sy = math.sqrt(sum((v - my) ** 2 for v in y))
    return sum((u - mx) * (v - my) for u, v in zip(x, y)) / (sx * sy) if sx and sy else float("nan")


def ge(a, b):
    return a == a and a >= b  # NaN fails


def verdict(dates, pnl, pnl_2x, placebo_totals, split=SPLIT, bar=BAR):
    pre = [x for d, x in zip(dates, pnl) if d < split]
    post = [x for d, x in zip(dates, pnl) if d >= split]
    total = sum(pnl)
    beat = sum(1 for p in placebo_totals if p < total) / len(placebo_totals) if placebo_totals else float("nan")
    r = dict(pre=sum(pre), pre_t=tstat(pre), post=sum(post), post_t=tstat(post), all_t=tstat(pnl), x2=sum(pnl_2x),
             placebo=beat, worst=worst_drop(pnl), years=yearly(dates, pnl))
    checks = dict(
        before_2024=r["pre"] > 0 and ge(r["pre_t"], bar["pre_t"]),
        since_2024=r["post"] > 0 and ge(r["post_t"], bar["post_t"]),
        whole_t=ge(r["all_t"], bar["all_t"]),
        double_cost=r["x2"] > 0,
        random_timing=ge(beat, bar["placebo"]),
        worst_drop=r["worst"] >= bar["max_drop"],
    )
    r["checks"] = checks
    r["failed"] = [k for k, ok in checks.items() if not ok]
    r["worthy"] = not r["failed"]
    return r


def line(name, r):
    return "%-34s %s | pre-24 $%+.0f t %.2f | 24-now $%+.0f t %.2f | all t %.2f | 2x $%+.0f | random %3.0f%% | worst $%.0f%s" % (
        name, "WORTHY" if r["worthy"] else "fail  ", r["pre"], r["pre_t"], r["post"], r["post_t"], r["all_t"], r["x2"],
        r["placebo"] * 100, r["worst"], "" if r["worthy"] else " | failed: " + ", ".join(r["failed"]))
