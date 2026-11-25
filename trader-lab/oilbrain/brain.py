#!/usr/bin/env python3
"""The oil brain: oil's fundamentals (inventories, positioning, the futures curve) plus price and macro
features, tested together on USO (WTI) with Brent (BNO) as the check.

    python3 oilbrain/oil_data.py fetch       # EIA weekly stocks + CFTC positioning
    python3 oilbrain/brain.py study [--write]
    python3 oilbrain/brain.py today

Why USO. A long USOIL CFD held for days pays the futures roll, and so does USO; a continuous futures
series would show the roll jumps as fake returns. USO trades from 2006-04.

PRE-REGISTERED 2026-11-25, before this file was run on any data. Not to be changed after the result.

FEATURES, each known by the close of day i (fundamentals only after their publication lag, oil_data.py):
  inv       US crude stocks: this week's change minus the average change in the same week of the 5 years
            before (a "surprise" without consensus forecasts)
  cushing   the same for Cushing, Oklahoma (the WTI delivery hub)
  gasoline  the same for US total gasoline stocks
  cot       managed money net long / open interest, as a percentile of the last 156 weeks (crowding)
  cot4      managed money net long / open interest minus its value 4 weeks earlier (flows)
  backw     contract 1 / contract 2 - 1 (backwardation > 0; EIA, ends 2024-04, missing after)
  mom21, mom63, mom252   USO's L-day return (time-series momentum)
  vol20     20-day standard deviation of USO's daily returns
  usd21     UUP's 21-day return (the dollar)
  xle21     XLE's 21-day return minus USO's (energy stocks leading oil)
Each feature is turned into z = (x - mean) / sd over its own last 252 trading days (at least 126 values),
so only the past is used.

TARGETS: h = 1 and h = 5 sessions, from the open of day i+1 to the open of day i+1+h (next-open fills).
  h = 5 decisions are made every 5th session, so its periods don't overlap.

RULE per feature and horizon: position s = sign(dir x z), long or short (a CFD can do both), where dir is
  the sign of the feature's correlation with the target on DISCOVERY days only.
COSTS: 5 bp each time the position changes side (USOIL spread), plus 1 bp a night held (financing).

PERIODS: DISCOVERY to 2014-12-31, VALIDATION 2015-2021, HOLDOUT 2022 on. "After 2014" = VALIDATION +
  HOLDOUT, the only period that judges.

PASS (all of them):
  1. net t >= 3.0 after 2014 (24 tests: 12 features x 2 horizons; 3.0 is about Bonferroni 0.05 / 24, and
     the lab's usual bar)
  2. net mean > 0 on VALIDATION and on HOLDOUT separately
  3. placebo: the same position sequence circularly shifted against the returns 1,000 times (keeps how
     often it's long or short and how long it holds); the real result must beat 99.8% of them (0.05 / 24)
  4. Brent check: the same positions on BNO after 2014 have a net mean > 0
THE BRAIN: one ridge regression (lambda 10) of the h-day target on all 12 z-features (missing = 0), fitted
  on DISCOVERY only; position = sign(score); same gates, judged as a 25th test at h = 5 and h = 1.
OPEC meeting dates were planned but are not included: no verified free list was found, and a list typed
from memory could leak hindsight. Research, not financial advice.
"""

import argparse
import bisect
import datetime
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, LAB)
import daily  # noqa: E402
import oil  # noqa: E402
import oil_data  # noqa: E402

FEATURES = ["inv", "cushing", "gasoline", "cot", "cot4", "backw", "mom21", "mom63", "mom252", "vol20",
            "usd21", "xle21"]
HORIZONS = (1, 5)
COST_BPS = 5.0
NIGHT_BPS = 1.0
DISC_END = "2014-12-31"
VAL_END = "2021-12-31"
T_BAR = 3.0
PLACEBO_PCT = 99.8
N_PLACEBO = 1000
RIDGE_LAMBDA = 10.0
ZWIN, ZMIN = 252, 126
RESULT = os.path.join(LAB, "results", "oilbrain-study.json")


# ---------------------------------------------------------------- weekly fundamentals

def surprise_series(weekly, years=5):
    """{week end: value} -> [(week end, change minus the mean same-week change of the previous `years`)].
    The same week a year back is 52 weeks earlier in the list (364 days; the 1-day drift is ignored)."""
    keys = sorted(weekly)
    vals = [weekly[k] for k in keys]
    out = []
    for n in range(1, len(keys)):
        ch = vals[n] - vals[n - 1]
        past = [vals[n - 52 * y] - vals[n - 52 * y - 1] for y in range(1, years + 1) if n - 52 * y - 1 >= 0]
        if len(past) == years:
            out.append((keys[n], ch - sum(past) / years))
    return out


def cot_series(cot, window=156):
    """{report date: {mm_net, oi}} -> ([(date, percentile of mm_net/oi in the last `window` weeks)],
    [(date, mm_net/oi minus 4 weeks earlier)])."""
    keys = sorted(k for k in cot if cot[k]["oi"] > 0)
    ratio = [cot[k]["mm_net"] / cot[k]["oi"] for k in keys]
    pct, chg = [], []
    for n, k in enumerate(keys):
        if n >= window - 1:
            w = ratio[n - window + 1:n + 1]
            pct.append((k, sum(1 for x in w if x <= ratio[n]) / len(w)))
        if n >= 4:
            chg.append((k, ratio[n] - ratio[n - 4]))
    return pct, chg


def as_of(series, lag_days):
    """[(date, value)] -> a function day -> the latest value whose publication (date + lag) is on or
    before that day, else None."""
    avail = [oil_data.available(d, lag_days) for d, _ in series]
    vals = [v for _, v in series]

    def f(day):
        k = bisect.bisect_right(avail, day) - 1
        return vals[k] if k >= 0 else None
    return f


# ---------------------------------------------------------------- daily features

def ret(c, i, L):
    return c[i] / c[i - L] - 1 if i >= L and c[i - L] > 0 else None


def by_date(D):
    return {d: k for k, d in enumerate(D["d"])}


def raw_features(U, aux, fund):
    """U: the USO price dict. aux: {"UUP": D, "XLE": D}. fund: {"inv": f, ...} as_of functions and the
    curve. Returns {feature: [value or None per USO day]}."""
    n = len(U["d"])
    c = U["c"]
    out = {f: [None] * n for f in FEATURES}
    idx = {s: by_date(D) for s, D in aux.items()}
    for i, d in enumerate(U["d"]):
        for f in ("inv", "cushing", "gasoline", "cot", "cot4"):
            out[f][i] = fund[f](d)
        out["backw"][i] = oil.backwardation(d)
        for L in (21, 63, 252):
            out["mom%d" % L][i] = ret(c, i, L)
        if i >= 20:
            r = [c[k] / c[k - 1] - 1 for k in range(i - 19, i + 1)]
            m = sum(r) / 20
            out["vol20"][i] = math.sqrt(sum((x - m) ** 2 for x in r) / 19)
        for s, f in (("UUP", "usd21"), ("XLE", "xle21")):
            k = idx[s].get(d)
            if k is None:
                continue
            r = ret(aux[s]["c"], k, 21)
            if r is None:
                continue
            if f == "xle21":
                u = ret(c, i, 21)
                out[f][i] = None if u is None else r - u
            else:
                out[f][i] = r
    return out


def zscore(xs, win=ZWIN, minn=ZMIN):
    """Trailing z-score: each value against the last `win` non-missing values up to and including it."""
    out = [None] * len(xs)
    hist = []
    for i, x in enumerate(xs):
        if x is None:
            continue
        hist.append(x)
        w = hist[-win:]
        if len(w) < minn:
            continue
        m = sum(w) / len(w)
        sd = math.sqrt(sum((v - m) ** 2 for v in w) / (len(w) - 1))
        out[i] = 0.0 if sd == 0 else (x - m) / sd
    return out


# ---------------------------------------------------------------- trading and stats

def periods(U, h):
    """Decision days i (every h-th session) with the trade from open i+1 to open i+1+h."""
    n = len(U["d"])
    return [i for i in range(0, n - 1 - h, h)]


def nights(d0, d1):
    return (datetime.date.fromisoformat(d1) - datetime.date.fromisoformat(d0)).days


def gross(P, i, h):
    o = P["o"]
    return o[i + 1 + h] / o[i + 1] - 1


def run(positions, rets, nts, cost_bps=COST_BPS, night_bps=NIGHT_BPS):
    """positions: list of -1/0/+1 per period; rets: gross period returns; nts: nights per period.
    Net return per period: s x r, minus one round trip's cost whenever a new side is taken (a flip closes
    one half and opens the other), minus financing while held. Going flat costs nothing extra."""
    out = []
    prev = 0
    for s, r, nt in zip(positions, rets, nts):
        x = s * r
        if s != 0 and s != prev:
            x -= cost_bps / 1e4
        if s != 0:
            x -= night_bps / 1e4 * nt
        out.append(x)
        prev = s
    return out


def tstat(xs):
    n = len(xs)
    if n < 3:
        return 0.0, 0.0
    m = sum(xs) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))
    return m, (m / sd * math.sqrt(n) if sd > 0 else 0.0)


def corr(a, b):
    pairs = [(x, y) for x, y in zip(a, b) if x is not None and y is not None]
    if len(pairs) < 30:
        return 0.0
    x = np.array([p[0] for p in pairs])
    y = np.array([p[1] for p in pairs])
    if x.std() == 0 or y.std() == 0:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])


def placebo_pct(positions, rets, nts, real_mean, n=N_PLACEBO):
    """Percent of circular shifts of the position sequence whose net mean is below the real one."""
    L = len(positions)
    if L < 10:
        return 0.0
    below = 0
    step = max(1, L // (n + 1))
    for k in range(1, n + 1):
        sh = (k * step) % L or 1
        p = positions[sh:] + positions[:sh]
        m = sum(run(p, rets, nts)) / L
        below += m < real_mean
    return 100.0 * below / n


def split(days, vals):
    a, b, c = [], [], []
    for d, v in zip(days, vals):
        (a if d <= DISC_END else b if d <= VAL_END else c).append(v)
    return a, b, c


def evaluate(U, B, z_by_day, h, dir_=None):
    """z_by_day: list of z (or score) per USO day. Returns the full stats dict for one rule."""
    idx = periods(U, h)
    days = [U["d"][i] for i in idx]
    rets = [gross(U, i, h) for i in idx]
    nts = [nights(U["d"][i + 1], U["d"][i + 1 + h]) for i in idx]
    zs = [z_by_day[i] for i in idx]
    disc = [(z, r) for d, z, r in zip(days, zs, rets) if d <= DISC_END and z is not None]
    if dir_ is None:
        dir_ = 1 if corr([z for z, _ in disc], [r for _, r in disc]) >= 0 else -1
    pos = [0 if z is None or z == 0 else (1 if dir_ * z > 0 else -1) for z in zs]
    net = run(pos, rets, nts)
    after = [k for k, d in enumerate(days) if d > DISC_END]
    pa = [pos[k] for k in after]
    ra = [rets[k] for k in after]
    na = [nts[k] for k in after]
    na_net = run(pa, ra, na)
    m_after, t_after = tstat(na_net)
    nd, nv, nh = split(days, net)
    ic = [corr([z for d, z in zip(days, zs) if sel(d)], [r for d, r in zip(days, rets) if sel(d)])
          for sel in (lambda d: d <= DISC_END, lambda d: DISC_END < d <= VAL_END, lambda d: d > VAL_END)]
    out = {"dir": dir_, "ic": [round(x, 4) for x in ic],
           "disc": stat(nd), "val": stat(nv), "hold": stat(nh),
           "after": {"n": len(na_net), "bp": round(m_after * 1e4, 2), "t": round(t_after, 2)},
           "long_share_after": round(sum(1 for p in pa if p > 0) / max(1, sum(1 for p in pa if p)), 3)}
    out["placebo_pct"] = round(placebo_pct(pa, ra, na, m_after), 1)
    out["brent"] = brent_check(U, B, idx, pos, h)
    v, ho = out["val"], out["hold"]
    out["pass"] = bool(t_after >= T_BAR and v["bp"] > 0 and ho["bp"] > 0 and out["placebo_pct"] >= PLACEBO_PCT
                       and out["brent"]["bp"] > 0)
    return out


def stat(xs):
    m, t = tstat(xs)
    return {"n": len(xs), "bp": round(m * 1e4, 2), "t": round(t, 2)}


def brent_check(U, B, idx, pos, h):
    """The same positions on BNO, after 2014, matched by date."""
    bi = by_date(B)
    p, r, nt = [], [], []
    for k, i in enumerate(idx):
        d = U["d"][i]
        j = bi.get(d)
        if d <= DISC_END or j is None or j + 1 + h >= len(B["d"]):
            continue
        p.append(pos[k])
        r.append(gross(B, j, h))
        nt.append(nights(B["d"][j + 1], B["d"][j + 1 + h]))
    return stat(run(p, r, nt))


def ridge_scores(U, Z, h, lam=RIDGE_LAMBDA):
    """Fit target ~ Z (missing = 0) on DISCOVERY decision days; return the score for every day."""
    idx = periods(U, h)
    X, y = [], []
    for i in idx:
        if U["d"][i] > DISC_END:
            break
        row = [Z[f][i] if Z[f][i] is not None else 0.0 for f in FEATURES]
        if all(v == 0.0 for v in row):
            continue
        X.append(row)
        y.append(gross(U, i, h))
    X, y = np.array(X), np.array(y)
    beta = np.linalg.solve(X.T @ X + lam * np.eye(X.shape[1]), X.T @ (y - y.mean()))
    scores = []
    for i in range(len(U["d"])):
        row = [Z[f][i] if Z[f][i] is not None else 0.0 for f in FEATURES]
        scores.append(None if all(v == 0.0 for v in row) else float(np.dot(beta, row)))
    return scores, {f: round(float(b) * 1e4, 3) for f, b in zip(FEATURES, beta)}


# ---------------------------------------------------------------- loading

def load_all():
    P = oil.load(["USO", "BNO", "UUP", "XLE"])
    oil.load_curve()
    inv = surprise_series(oil_data.load("crude"))
    cus = surprise_series(oil_data.load("cushing"))
    gas = surprise_series(oil_data.load("gasoline"))
    cpct, cchg = cot_series(oil_data.load("cot"))
    fund = {"inv": as_of(inv, oil_data.EIA_LAG_DAYS), "cushing": as_of(cus, oil_data.EIA_LAG_DAYS),
            "gasoline": as_of(gas, oil_data.EIA_LAG_DAYS), "cot": as_of(cpct, oil_data.COT_LAG_DAYS),
            "cot4": as_of(cchg, oil_data.COT_LAG_DAYS)}
    U = P["USO"]
    raw = raw_features(U, {"UUP": P["UUP"], "XLE": P["XLE"]}, fund)
    Z = {f: zscore(raw[f]) for f in FEATURES}
    return U, P["BNO"], raw, Z


def cmd_study(a):
    U, B, raw, Z = load_all()
    print("USO %s to %s, %d sessions. Discovery to %s, validation to %s, holdout after. Bar: t >= %.1f after "
          "2014, placebo >= %.1f%%." % (U["d"][0], U["d"][-1], len(U["d"]), DISC_END, VAL_END, T_BAR, PLACEBO_PCT))
    rows = {}
    for h in HORIZONS:
        print("\nHorizon %d session%s (net of 5 bp per side change + 1 bp a night):" % (h, "" if h == 1 else "s"))
        print("  %-9s %4s  %-22s %-15s %-15s %-15s %-16s %7s %8s  %s" % (
            "feature", "dir", "IC disc/val/hold", "discovery", "validation", "holdout", "after 2014",
            "placebo", "Brent", "verdict"))
        for f in FEATURES + ["BRAIN"]:
            if f == "BRAIN":
                sc, beta = ridge_scores(U, Z, h)
                r = evaluate(U, B, sc, h, dir_=1)
                r["beta_bp"] = beta
            else:
                r = evaluate(U, B, Z[f], h)
            rows["%s_h%d" % (f, h)] = r
            print("  %-9s %+4d  %-22s %-15s %-15s %-15s %-16s %6.1f%% %8s  %s" % (
                f, r["dir"], "/".join("%+.3f" % x for x in r["ic"]),
                "%+.1fbp t%+.2f" % (r["disc"]["bp"], r["disc"]["t"]),
                "%+.1fbp t%+.2f" % (r["val"]["bp"], r["val"]["t"]),
                "%+.1fbp t%+.2f" % (r["hold"]["bp"], r["hold"]["t"]),
                "%+.1fbp t%+.2f" % (r["after"]["bp"], r["after"]["t"]),
                r["placebo_pct"], "%+.1fbp" % r["brent"]["bp"], "PASS" if r["pass"] else "fail"))
    passed = [k for k, r in rows.items() if r["pass"]]
    # controls: always long and always short USO after 2014, same costs
    ctrl = {}
    for h in HORIZONS:
        idx = [i for i in periods(U, h) if U["d"][i] > DISC_END]
        rets = [gross(U, i, h) for i in idx]
        nts = [nights(U["d"][i + 1], U["d"][i + 1 + h]) for i in idx]
        for name, s in (("always_long", 1), ("always_short", -1)):
            ctrl["%s_h%d" % (name, h)] = stat(run([s] * len(idx), rets, nts))
    print("\nControls after 2014: " + ", ".join("%s %+.1fbp t%+.2f" % (k, v["bp"], v["t"]) for k, v in ctrl.items()))
    verdict = "PASS: " + ", ".join(passed) if passed else "FAIL: nothing passes every gate"
    print("\nVerdict: %s. Research, not financial advice." % verdict)
    if a.write:
        os.makedirs(os.path.dirname(RESULT), exist_ok=True)
        with open(RESULT, "w") as fh:
            json.dump({"generated": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%MZ"),
                       "range": [U["d"][0], U["d"][-1]], "rows": rows, "controls": ctrl,
                       "passed": passed, "verdict": verdict}, fh, indent=1)
        print("Wrote %s" % os.path.relpath(RESULT, LAB))
    return 0


def cmd_today(a):
    U, B, raw, Z = load_all()
    i = len(U["d"]) - 1
    print("Oil brain readings at the close of %s (USO %.2f). Directions come from the 2006-2014 discovery "
          "days; none of these passed the study's gates unless it says PASS." % (U["d"][i], U["c"][i]))
    res = {}
    if os.path.exists(RESULT):
        with open(RESULT) as fh:
            res = json.load(fh).get("rows", {})
    for f in FEATURES:
        z = Z[f][i]
        r = res.get("%s_h5" % f, {})
        d = r.get("dir", 0)
        lean = "-" if z is None or not d else ("long" if d * z > 0 else "short")
        print("  %-9s raw %-12s z %-6s  5-day lean %-5s %s" % (
            f, "-" if raw[f][i] is None else "%.4g" % raw[f][i], "-" if z is None else "%+.2f" % z, lean,
            "PASS" if r.get("pass") else ""))
    for h in HORIZONS:
        sc, _ = ridge_scores(U, Z, h)
        s = sc[i]
        print("  BRAIN h%d score %s -> %s" % (h, "-" if s is None else "%+.2f bp" % (s * 1e4),
                                             "-" if s is None else ("long" if s > 0 else "short")))
    print("Research, not financial advice. Nothing here places an order.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="oil brain")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("study")
    p.add_argument("--write", action="store_true")
    sub.add_parser("today")
    a = ap.parse_args(argv)
    fn = {"study": cmd_study, "today": cmd_today}.get(a.cmd)
    if not fn:
        ap.print_help()
        return 1
    return fn(a)


if __name__ == "__main__":
    sys.exit(main())
