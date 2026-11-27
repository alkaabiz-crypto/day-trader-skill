#!/usr/bin/env python3
"""Same-calendar-month seasonality across sector and country ETFs, pre-registered.

    python3 seasonal_xs.py fetch          # Yahoo adjusted closes -> data/seasonal_xs (gitignored)
    python3 seasonal_xs.py run [--write]  # score -> results/seasonal-xs.json

Sources: Heston & Sadka (2008, JFE 87(2)) "Seasonality in the cross-section of stock returns"; Keloharju,
Linnainmaa & Nyberg (2016, JF 71(4)) "Return Seasonalities", who find the same-month effect in industries
and country indices too: an asset that did well in a calendar month in past years tends to do well in
that month again.

PRE-REGISTERED 2026-11-24, committed before any data was downloaded. Not to be changed:
  * Sets, fixed: SECTORS (the 9 original Select Sector SPDRs, Dec 1998) and COUNTRIES (iShares MSCI
    country ETFs). A ticker Yahoo doesn't serve is dropped mechanically.
  * Monthly returns from dividend-adjusted month-end closes.
  * Signal for month m of year Y: the ETF's mean return in calendar month m over years Y-1..Y-5 (all 5
    needed). Formed at the end of month m-1, held through month m.
  * Each set: equal-weight thirds by signal (at least 6 ETFs, else the set sits out that month).
    H1 (primary): top third minus bottom third. H2: top third minus the set's equal-weight average.
    The month's result is the mean over the sets taking part.
  * Costs: 10 bps per side on every unit of weight traded, per set; 25 bps reported.
  * Split: in-sample = months before 2012-01; judged = 2012-01 on (after both papers' samples).
  * Verdict per hypothesis at 10 bps: PASS only if judged t >= 3 and in-sample t > 0.
  * Placebo: each month's signal taken from a random other calendar month (the same draw for every ETF that
    month), 1,000 draws; reported as the share of draws whose judged mean beats the real one.
Research, not financial advice.
"""

import argparse
import gzip
import json
import math
import os
import random
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import daily  # noqa: E402
import alloc  # noqa: E402  (parse_adj)

STORE = os.path.join(HERE, "data", "seasonal_xs")
RESULTS = os.path.join(HERE, "results")
SECTORS = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
COUNTRIES = ["EWA", "EWC", "EWD", "EWG", "EWH", "EWI", "EWJ", "EWK", "EWL", "EWM", "EWN", "EWO", "EWP", "EWQ",
             "EWS", "EWU", "EWW", "EWZ", "EWT", "EWY"]
YEARS = 5
MIN_SET = 6
COST_BPS = 10.0
REF_COST_BPS = 25.0
SPLIT = "2012-01"
T_BAR = 3.0
PLACEBO_DRAWS = 1000


def path(s):
    return os.path.join(STORE, "%s.json.gz" % s)


def cmd_fetch(a):
    os.makedirs(STORE, exist_ok=True)
    missing = []
    for s in SECTORS + COUNTRIES:
        if os.path.exists(path(s)) and not a.full:
            continue
        try:
            b = alloc.parse_adj(daily.fetch_daily(s))
        except Exception as e:  # noqa: BLE001
            missing.append("%s (%s)" % (s, e))
            continue
        tmp = path(s) + ".tmp"
        with gzip.open(tmp, "wt") as fh:
            json.dump(b, fh)
        os.replace(tmp, path(s))
        time.sleep(1.0)
    print("stored %d of %d" % (len(SECTORS + COUNTRIES) - len(missing), len(SECTORS + COUNTRIES)))
    if missing:
        print("dropped: " + "; ".join(missing))
    return 0


def monthly(b):
    """{"YYYY-MM": return} from month-end closes; the last month only if it's complete is left to the caller."""
    ends = {}
    for d, c in zip(b["d"], b["c"]):
        ends[d[:7]] = c
    ms = sorted(ends)
    return {m: ends[m] / ends[p] - 1.0 for p, m in zip(ms, ms[1:])}


def load():
    out = {}
    for s in SECTORS + COUNTRIES:
        if os.path.exists(path(s)):
            with gzip.open(path(s), "rt") as fh:
                out[s] = monthly(json.load(fh))
    return out


def shift(ym, months):
    y, m = int(ym[:4]), int(ym[5:])
    k = y * 12 + (m - 1) + months
    return "%04d-%02d" % (k // 12, k % 12 + 1)


def signal(rets, ym, cal_offset=0):
    """Mean return in the same calendar month (shifted by cal_offset months for the placebo) over the past YEARS."""
    vals = []
    for y in range(1, YEARS + 1):
        k = shift(ym, -12 * y + cal_offset)
        if k >= ym or k not in rets:
            return None
        vals.append(rets[k])
    return sum(vals) / len(vals)


def months_all(data):
    ms = sorted({m for r in data.values() for m in r})
    return ms


def set_weights(data, members, ym, cal_offset):
    sig = {}
    for s in members:
        if s in data and ym in data[s]:
            v = signal(data[s], ym, cal_offset)
            if v is not None:
                sig[s] = v
    if len(sig) < MIN_SET:
        return None
    ranked = sorted(sig, key=lambda s: sig[s])
    n = len(ranked) // 3
    top, bot = ranked[-n:], ranked[:n]
    w1 = {s: 1.0 / n for s in top}
    for s in bot:
        w1[s] = w1.get(s, 0.0) - 1.0 / n
    w2 = {s: 1.0 / n for s in top}
    for s in ranked:
        w2[s] = w2.get(s, 0.0) - 1.0 / len(ranked)
    return w1, w2


def series(data, cost_bps, rng=None):
    months, h1, h2 = [], [], []
    prev = {}
    for ym in months_all(data):
        off = 0 if rng is None else rng.choice([k for k in range(-11, 12) if k != 0])
        parts1, parts2 = [], []
        for name, members in (("sectors", SECTORS), ("countries", COUNTRIES)):
            w = set_weights(data, members, ym, off)
            if w is None:
                prev.pop(name, None)
                continue
            res = []
            for i, wi in enumerate(w):
                old = (prev.get(name) or ({}, {}))[i]
                turn = sum(abs(wi.get(s, 0.0) - old.get(s, 0.0)) for s in set(wi) | set(old))
                res.append(sum(x * data[s][ym] for s, x in wi.items()) - turn * cost_bps / 1e4)
            prev[name] = w
            parts1.append(res[0])
            parts2.append(res[1])
        if parts1:
            months.append(ym)
            h1.append(sum(parts1) / len(parts1))
            h2.append(sum(parts2) / len(parts2))
    return months, h1, h2


def tstat(x):
    if len(x) < 3 or statistics.stdev(x) == 0:
        return 0.0
    return statistics.mean(x) / (statistics.stdev(x) / math.sqrt(len(x)))


def split_stats(ms, x):
    a = [v for m, v in zip(ms, x) if m < SPLIT]
    b = [v for m, v in zip(ms, x) if m >= SPLIT]
    f = lambda s: {"months": len(s), "mean_pct_mo": 100 * statistics.mean(s) if s else 0.0, "t": tstat(s)}  # noqa: E731
    return {"in_sample": f(a), "judged": f(b)}


def cmd_run(a):
    data = load()
    if not data:
        print("no data: run `seasonal_xs.py fetch` first")
        return 1
    import datetime
    this_month = datetime.date.today().strftime("%Y-%m")
    for r in data.values():
        r.pop(this_month, None)              # the current month isn't over
    out = {"etfs_with_data": sorted(data)}
    for cost in (COST_BPS, REF_COST_BPS):
        ms, h1, h2 = series(data, cost)
        out["cost_%g" % cost] = {"H1_top_minus_bottom": split_stats(ms, h1),
                                 "H2_top_minus_set": split_stats(ms, h2)}
    ms, h1, h2 = series(data, COST_BPS)
    out["first"], out["last"] = ms[0], ms[-1]
    real = {"H1": statistics.mean([v for m, v in zip(ms, h1) if m >= SPLIT]),
            "H2": statistics.mean([v for m, v in zip(ms, h2) if m >= SPLIT])}
    rng, beat = random.Random(7), {"H1": 0, "H2": 0}
    for _ in range(PLACEBO_DRAWS):
        m2, p1, p2 = series(data, COST_BPS, rng)
        for k, s in (("H1", p1), ("H2", p2)):
            if statistics.mean([v for m, v in zip(m2, s) if m >= SPLIT]) >= real[k]:
                beat[k] += 1
    out["placebo_p"] = {k: v / PLACEBO_DRAWS for k, v in beat.items()}
    out["verdict"] = {}
    for k, key in (("H1", "H1_top_minus_bottom"), ("H2", "H2_top_minus_set")):
        s = out["cost_%g" % COST_BPS][key]
        out["verdict"][k] = "PASS" if (s["judged"]["t"] >= T_BAR and s["in_sample"]["t"] > 0) else "FAIL"
        print("%s %-20s IS %3d mo %+5.2f%%/mo t %+5.2f | judged %3d mo %+5.2f%%/mo t %+5.2f | placebo p %.3f -> %s" % (
            k, key, s["in_sample"]["months"], s["in_sample"]["mean_pct_mo"], s["in_sample"]["t"],
            s["judged"]["months"], s["judged"]["mean_pct_mo"], s["judged"]["t"], out["placebo_p"][k],
            out["verdict"][k]))
    print("%d ETFs, %s to %s" % (len(data), out["first"], out["last"]))
    if a.write:
        with open(a.write, "w") as fh:
            json.dump(out, fh, indent=1)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    f = sub.add_parser("fetch")
    f.add_argument("--full", action="store_true")
    r = sub.add_parser("run")
    r.add_argument("--write", nargs="?", const=os.path.join(RESULTS, "seasonal-xs.json"))
    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        return cmd_fetch(a)
    if a.cmd == "run":
        return cmd_run(a)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
