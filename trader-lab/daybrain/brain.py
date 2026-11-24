#!/usr/bin/env python3
"""The day-trading brain: every studied intraday feature, measured on the whole US market at once.

    python3 bot_data.py stocks              # whole-market 5-minute bars (60 days) -> data/wm5
    python3 daybrain/brain.py study [--write]

What it does. At 9:35 New York, after the FIRST 5-MINUTE CANDLE closes, it measures every feature the
studies talk about (KNOWLEDGE.md) for every liquid US stock. Then it asks one question per feature: across
the whole market, on the same day, do stocks with more of this feature do better for the rest of the day
(from 9:35 to 15:55)? Looking across ~1,400 stocks a day, instead of one stock at a time, gives about
1,400 times as many observations per day. That's the strongest test 60 days of 5-minute data allows.

PRE-REGISTERED 2026-11-24, before this file was run on any data. Not to be changed after the result.

FEATURES, known at 9:35 (first candle o1 h1 l1 c1 v1, range R1 = h1 - l1; the previous session's bars):
  f1  candle      first candle return  c1/o1 - 1                        (colour and size)
  f2  gap         o1 / previous close - 1
  f3  upwick      (h1 - max(o1, c1)) / R1                               (rejection from above)
  f4  lowwick     (min(o1, c1) - l1) / R1                               (rejection from below)
  f5  body        |c1 - o1| / R1
  f6  clv         (c1 - l1) / R1 - 0.5                                  (where the candle closed)
  f7  range       R1 / c1 divided by the mean daily (h - l)/c of the previous 14 sessions
  f8  rvol        log(v1 / mean first-candle volume of the previous 14 sessions)   (stocks in play)
  f9  prevday     previous session's close-to-close return
  f10 prevclv     previous session's daily close location (c - l)/(h - l) - 0.5
  f11 prevlast    previous session's last 30 minutes, c[77]/c[71] - 1  (end-of-day momentum)
  f12 inplay      f1 x f8 (candle direction amplified by relative volume, Zarattini et al.)
TARGET: o[1] (the second candle's open, 9:35) to c[76] (15:55): the trade you could actually make.

TEST 1, each feature alone: each day, the rank correlation (Spearman) of the feature with the target across
  all stocks; the mean over days and its t. Bonferroni over 12 features: |t| >= 2.87 passes, two-sided.
  Days 1-14 are used only to build f7 / f8 history; the rest are split in time: DISCOVERY (first half),
  VALIDATION (second half). A feature counts only if it passes on DISCOVERY and has the same sign with
  t >= 2 on VALIDATION.
TEST 2, the brain: one ridge regression (lambda 1.0) of the target's daily cross-sectional rank on the 12
  features' ranks (scaled to -0.5..0.5), fitted on DISCOVERY only. On VALIDATION each day: long the top 10%
  by brain score, short the bottom 10%, equal weight, 9:35 to 15:55, 10 bp round trip per name per side
  (spread plus slippage on liquid names). Passes if the VALIDATION net daily t >= 2 and the long top 10%
  alone beats the equal-weight market (net) with t >= 2.
TEST 3, independent check: the same fitted brain, unchanged, on the lab's 4-year store (data/long, 40 names,
  2022-2026, Tiingo IEX volume) with top 4 minus bottom 4. Reported, and needed for a full PASS.
Survivorship: today's list of liquid names (small over 60 days; not small over 4 years, hence test 3 is only
a check). Research, not financial advice.
"""

import argparse
import gzip
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(HERE)
sys.path.insert(0, LAB)
import bot_data  # noqa: E402
import lab  # noqa: E402

NAMES = ["candle", "gap", "upwick", "lowwick", "body", "clv", "range", "rvol", "prevday", "prevclv",
         "prevlast", "inplay"]
BONF_T, VAL_T, COST_BPS, LAMBDA = 2.87, 2.0, 10.0, 1.0
EXIT = 76


def load_wm5():
    with open(os.path.join(bot_data.WM5, "_liquid.json")) as fh:
        syms = json.load(fh)
    out = {}
    for s in syms:
        p = os.path.join(bot_data.WM5, s + ".json.gz")
        if os.path.exists(p):
            with gzip.open(p, "rt") as fh:
                bars = json.load(fh)
            out[s] = lab.sessions_of({int(k): v for k, v in bars.items()})
    return out


def load_long():
    out = {}
    for f in sorted(os.listdir(lab.LONG_STORE)):
        if not f.endswith(".json.gz"):
            continue
        with gzip.open(os.path.join(lab.LONG_STORE, f), "rt") as fh:
            bars = json.load(fh)
        out[f[:-8]] = lab.sessions_of({int(k): (tuple(v) if isinstance(v, (list, tuple)) else
                                                (v["o"], v["h"], v["l"], v["c"], v["v"])) for k, v in bars.items()})
    return out


def rows_for(sessions, min_price=5.0, min_dollar_vol=5e6):
    """sessions: [(date, bars)] of one stock -> {date: (features[12], target)} for full sessions."""
    out = {}
    full = [(d, b) for d, b in sessions if len(b) >= 78]
    for k in range(15, len(full)):
        d, b = full[k]
        hist = full[k - 14:k]
        pd, pb = full[k - 1]
        o1, h1, l1, c1, v1 = b[0]["o"], b[0]["h"], b[0]["l"], b[0]["c"], b[0]["v"] or 0
        R1 = h1 - l1
        if not (o1 and c1 and R1 > 0) or c1 < min_price:
            continue
        dvol = sum((x["c"] or 0) * (x["v"] or 0) for x in pb)
        if dvol < min_dollar_vol:
            continue
        prev_c = pb[-1]["c"]
        drange = np.mean([(max(x["h"] for x in hb) - min(x["l"] for x in hb)) / hb[-1]["c"] for _, hb in hist])
        v1h = np.mean([hb[0]["v"] or 0 for _, hb in hist])
        if not v1h or not drange or v1 <= 0:
            continue
        ph, pl = max(x["h"] for x in pb), min(x["l"] for x in pb)
        f = [c1 / o1 - 1, o1 / prev_c - 1, (h1 - max(o1, c1)) / R1, (min(o1, c1) - l1) / R1, abs(c1 - o1) / R1,
             (c1 - l1) / R1 - 0.5, (R1 / c1) / drange, math.log(v1 / v1h),
             prev_c / full[k - 2][1][-1]["c"] - 1, (prev_c - pl) / (ph - pl) - 0.5 if ph > pl else 0.0,
             pb[77]["c"] / pb[71]["c"] - 1 if len(pb) > 77 else 0.0, 0.0]
        f[11] = f[0] * f[7]
        tgt = b[EXIT]["c"] / b[1]["o"] - 1
        out[d] = (f, tgt)
    return out


def panel(data):
    """-> {date: (symbols, X[n,12], y[n])}"""
    by = {}
    for s, sess in data.items():
        for d, (f, y) in rows_for(sess).items():
            by.setdefault(d, []).append((s, f, y))
    out = {}
    for d in sorted(by):
        rows = by[d]
        if len(rows) < 8:
            continue
        out[d] = ([r[0] for r in rows], np.array([r[1] for r in rows], float), np.array([r[2] for r in rows], float))
    return out


def ranks(x):
    """Cross-sectional ranks scaled to -0.5..0.5 (ties averaged)."""
    order = x.argsort(kind="mergesort")
    r = np.empty(len(x))
    r[order] = np.arange(len(x))
    # average ties
    _, inv, cnt = np.unique(x, return_inverse=True, return_counts=True)
    sums = np.bincount(inv, weights=r)
    r = sums[inv] / cnt[inv]
    return r / max(1, len(x) - 1) - 0.5


def ic_table(P, days):
    out = {}
    for j, name in enumerate(NAMES):
        ics = []
        for d in days:
            _, X, y = P[d]
            ics.append(np.corrcoef(ranks(X[:, j]), ranks(y))[0, 1])
        ics = np.array([v for v in ics if np.isfinite(v)])
        t = ics.mean() / ics.std(ddof=1) * math.sqrt(len(ics)) if len(ics) > 2 and ics.std() > 0 else 0.0
        out[name] = {"ic": float(ics.mean()), "t": float(t), "days": len(ics)}
    return out


def fit(P, days):
    Xs = np.vstack([np.column_stack([ranks(P[d][1][:, j]) for j in range(len(NAMES))]) for d in days])
    ys = np.concatenate([ranks(P[d][2]) for d in days])
    A = Xs.T @ Xs + LAMBDA * np.eye(Xs.shape[1])
    return np.linalg.solve(A, Xs.T @ ys)


def long_short(P, days, w, frac=0.10, k_min=None, cost=COST_BPS):
    ls, lo, mk = [], [], []
    for d in days:
        _, X, y = P[d]
        sc = np.column_stack([ranks(X[:, j]) for j in range(len(NAMES))]) @ w
        k = max(k_min or 1, int(len(y) * frac))
        o = sc.argsort()
        top, bot = y[o[-k:]].mean(), y[o[:k]].mean()
        c = cost / 1e4
        ls.append(top - bot - 2 * c)
        lo.append(top - c - (y.mean() - c))
        mk.append(y.mean())
    def tt(x):
        x = np.array(x)
        return float(x.mean() / x.std(ddof=1) * math.sqrt(len(x))) if len(x) > 2 and x.std() > 0 else 0.0
    return {"days": len(days), "ls_bp": float(np.mean(ls) * 1e4), "ls_t": tt(ls),
            "long_vs_mkt_bp": float(np.mean(lo) * 1e4), "long_vs_mkt_t": tt(lo), "mkt_bp": float(np.mean(mk) * 1e4)}


def cmd_study(a):
    P = panel(load_wm5())
    days = sorted(P)
    half = len(days) // 2
    disc, val = days[:half], days[half:]
    out = {"days": len(days), "from": days[0], "to": days[-1], "discovery": [disc[0], disc[-1]],
           "validation": [val[0], val[-1]], "avg_names": float(np.mean([len(P[d][2]) for d in days]))}
    ic_d, ic_v = ic_table(P, disc), ic_table(P, val)
    out["features"] = {}
    print("Day-trading brain, whole market: %d days (%s to %s), about %.0f stocks a day." % (
        len(days), days[0], days[-1], out["avg_names"]))
    print("Each feature alone (rank correlation with 9:35-15:55 return; pass: |t| >= %.2f on discovery, same sign t >= 2 on validation):" % BONF_T)
    print("  feature     disc IC    t     |  valid IC    t    | verdict")
    for n in NAMES:
        dd, vv = ic_d[n], ic_v[n]
        ok = abs(dd["t"]) >= BONF_T and np.sign(vv["t"]) == np.sign(dd["t"]) and abs(vv["t"]) >= VAL_T
        out["features"][n] = {"discovery": dd, "validation": vv, "pass": bool(ok)}
        print("  %-9s  %+.4f  %+5.2f  |  %+.4f  %+5.2f  | %s" % (n, dd["ic"], dd["t"], vv["ic"], vv["t"], "PASS" if ok else "-"))
    w = fit(P, disc)
    out["weights"] = dict(zip(NAMES, map(float, w)))
    out["brain_discovery"] = long_short(P, disc, w)
    out["brain_validation"] = long_short(P, val, w)
    bv = out["brain_validation"]
    print("The brain (all 12 features, fitted on discovery only), top 10%% minus bottom 10%%, %.0f bp a name a side:" % COST_BPS)
    for k in ("brain_discovery", "brain_validation"):
        r = out[k]
        print("  %-17s %2d days: long-short %+6.1f bp/day (t %+5.2f); long top 10%% vs market %+6.1f bp/day (t %+5.2f)" % (
            k.split("_")[1], r["days"], r["ls_bp"], r["ls_t"], r["long_vs_mkt_bp"], r["long_vs_mkt_t"]))
    print("  weights: " + ", ".join("%s %+.3f" % (n, v) for n, v in out["weights"].items()))
    L = panel(load_long())
    ld = sorted(L)
    out["long_store"] = long_short(L, ld, w, frac=0.10, k_min=4)
    out["long_store"]["from"], out["long_store"]["to"] = ld[0], ld[-1]
    out["long_store_ic"] = ic_table(L, ld)
    r = out["long_store"]
    print("  4-year check (40 names, %s to %s, %d days): top 4 minus bottom 4 %+6.1f bp/day (t %+5.2f)" % (
        ld[0], ld[-1], r["days"], r["ls_bp"], r["ls_t"]))
    passed = bv["ls_t"] >= 2 and bv["long_vs_mkt_t"] >= 2 and r["ls_t"] >= 2
    out["verdict"] = "PASS" if passed else "FAIL"
    print("Verdict: %s. History, not a forecast; research, not financial advice." % out["verdict"])
    if a.write:
        with open(os.path.join(LAB, "results", "daybrain.json"), "w") as fh:
            json.dump(out, fh, indent=1)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="the day-trading brain")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("study")
    p.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "study":
        return cmd_study(a)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
