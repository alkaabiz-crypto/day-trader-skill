#!/usr/bin/env python3
"""The swarm: 100,000 randomly generated timing rules, searched with an honest correction for luck.

    python3 swarm.py fetch                 # dividend-adjusted daily closes for ~129 ETFs into data/swarm (gitignored)
    python3 swarm.py test [--rules 100000] [--write]

Why: hand-picked rules from papers and videos have all failed here. A machine search over a large
space of rules finds the best of everything that can be built from common ingredients, but it also
manufactures luck: the best of 100,000 random rules looks brilliant by chance alone. So the gates
below are built around the number of rules tried.

PRE-REGISTERED 2026-11-24, before any rule was scored. Not to be changed after the first run:

  Universe: the lab's 19 index/sector/bond/gold ETFs (audit.ETFS) plus the 110 ETFs of r3_etfs.py
  (countries, bonds, commodities, factors, sectors). ETFs, not single stocks, so delisting bias is
  small. Yahoo dividend-adjusted closes. A fund joins once it has 260 days of history.
  Periods: IS 1998-01-01 to 2012-12-31, OOS 2013-2019, HOLDOUT 2020-01-01 on.

  Ingredients (all computed from closes up to and including day t):
    ret_L      return over L days, L in 1 2 3 5 10 20 60 120 250
    sma_n      close / n-day average - 1, n in 5 10 20 50 100 200
    rsi_n      Wilder RSI, n in 2 3 5 14
    hi_n/lo_n  close / n-day high (low) - 1, n in 5 20 60 250
    vol_r      20-day / 120-day realized volatility
  A rule: feature F compared with a threshold = the q-th percentile of F for that fund over IS
  (q in 5 10 20 30 50 70 80 90 95), "above" or "below"; optionally AND a second such condition
  (half the rules); go LONG when true; hold H days after the last signal (H in 1 2 5 10 20).
  Rules are drawn at random (seed 2026) from this grammar; duplicates are dropped.

  Execution and scoring: the signal at day t's close is traded at day t+1's close (one day of delay)
  and earns day t+2's return onward. Score = timing only: each day's return minus the fund's own
  trailing 250-day mean daily return, so plain long exposure to a rising market earns nothing.
  Portfolio = the equal-weight average over funds holding a position that day (0 on days with none).
  Cost: 10 bps per unit of turnover per fund (each side), re-run at 20 bps.

  Gates (every step fixed now):
    1. IS: rank all rules by IS t-stat of the daily portfolio after costs; keep the top 1,000.
    2. OOS: of those 1,000, keep the rules with OOS t > 0 and a Benjamini-Hochberg false discovery
       rate of 5% on one-sided OOS p-values (over the 1,000).
    3. HOLDOUT, the only verdict: a survivor PASSES if its HOLDOUT t >= 3 at 10 bps (Bonferroni-sized
       for the survivors) and its HOLDOUT mean is > 0 at 20 bps.
    Luck benchmark reported alongside: the same pipeline on 1,000 rules whose signals are circularly
    shifted in time per fund (keeping each rule's time in market and its runs), to show how good the
    best of the search looks with no information at all.
Caveats: closes only (no opens: a one-day delay instead); Yahoo history only; ETF launch dates vary.
Research, not financial advice.
"""

import argparse
import gzip
import json
import math
import os
import random
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import alloc  # noqa: E402  (adjusted-close parsing)
import audit  # noqa: E402  (ETF list)
import daily  # noqa: E402  (Yahoo fetch)
import r3_etfs  # noqa: E402  (ETF list)

STORE = os.path.join(HERE, "data", "swarm")
RESULTS = os.path.join(HERE, "results")
IS_END, OOS_END, START = "2012-12-31", "2019-12-31", "1998-01-01"
COSTS = (10.0, 20.0)
SEED = 2026
TOP_IS = 1000
FDR = 0.05
HOLD_T = 3.0


def universe():
    out = []
    for s in list(audit.ETFS) + list(r3_etfs.NEW_ETFS):
        if s not in out:
            out.append(s)
    return out


def path(s):
    return os.path.join(STORE, "%s.json.gz" % s)


def cmd_fetch(a):
    os.makedirs(STORE, exist_ok=True)
    for s in universe():
        if os.path.exists(path(s)):
            continue
        try:
            D = alloc.parse_adj(daily.fetch_daily(s))
        except daily.LabError as e:
            print("%-5s skipped: %s" % (s, e))
            continue
        with gzip.open(path(s), "wt", encoding="utf-8") as fh:
            json.dump(D, fh, separators=(",", ":"))
        print("%-5s %5d days from %s" % (s, len(D["d"]), D["d"][0]), flush=True)
        time.sleep(daily.PAUSE)
    return 0


# ---------------------------------------------------------------- panel and features

def load_panel():
    syms, series = [], {}
    for s in universe():
        if not os.path.exists(path(s)):
            continue
        with gzip.open(path(s), "rt", encoding="utf-8") as fh:
            D = json.load(fh)
        series[s] = dict(zip(D["d"], D["c"]))
        syms.append(s)
    dates = sorted(d for d in series["SPY"] if d >= START)
    C = np.full((len(syms), len(dates)), np.nan)
    for i, s in enumerate(syms):
        m = series[s]
        C[i] = [m.get(d, np.nan) for d in dates]
    # carry the last close over a missing day (holidays differ for a few funds), never backwards
    for i in range(len(syms)):
        row = C[i]
        for t in range(1, len(row)):
            if np.isnan(row[t]) and not np.isnan(row[t - 1]):
                row[t] = row[t - 1]
    return syms, np.array(dates), C


def rolling_mean(X, n):
    out = np.full_like(X, np.nan)
    cs = np.nancumsum(np.nan_to_num(X), axis=1)
    out[:, n - 1:] = (cs[:, n - 1:] - np.concatenate([np.zeros((X.shape[0], 1)), cs[:, :-n]], axis=1)) / n
    out[np.isnan(X)] = np.nan
    return out


def rolling_ext(X, n, fn):
    out = np.full_like(X, np.nan)
    for t in range(n - 1, X.shape[1]):
        out[:, t] = fn(X[:, t - n + 1:t + 1], axis=1)
    return out


def wilder_rsi(C, n):
    d = np.diff(C, axis=1, prepend=np.nan)
    up, dn = np.clip(d, 0, None), np.clip(-d, 0, None)
    out = np.full_like(C, np.nan)
    au = ad = None
    for t in range(1, C.shape[1]):
        u, v = np.nan_to_num(up[:, t]), np.nan_to_num(dn[:, t])
        if au is None:
            au, ad = u.copy(), v.copy()
        else:
            au = (au * (n - 1) + u) / n
            ad = (ad * (n - 1) + v) / n
        with np.errstate(divide="ignore", invalid="ignore"):
            out[:, t] = 100 - 100 / (1 + au / np.where(ad == 0, np.nan, ad))
        out[np.isnan(C[:, t]), t] = np.nan
    return np.where(np.isnan(out), 100.0, out) * np.where(np.isnan(C), np.nan, 1)


def features(C):
    F = {}
    for L in (1, 2, 3, 5, 10, 20, 60, 120, 250):
        F["ret_%d" % L] = C / np.roll(C, L, axis=1) - 1
        F["ret_%d" % L][:, :L] = np.nan
    for n in (5, 10, 20, 50, 100, 200):
        F["sma_%d" % n] = C / rolling_mean(C, n) - 1
    for n in (2, 3, 5, 14):
        F["rsi_%d" % n] = wilder_rsi(C, n)
    for n in (5, 20, 60, 250):
        F["hi_%d" % n] = C / rolling_ext(C, n, np.nanmax) - 1
        F["lo_%d" % n] = C / rolling_ext(C, n, np.nanmin) - 1
    r = np.diff(np.log(C), axis=1, prepend=np.nan)
    v20 = np.sqrt(rolling_mean(r * r, 20))
    v120 = np.sqrt(rolling_mean(r * r, 120))
    with np.errstate(divide="ignore", invalid="ignore"):
        F["vol_r"] = v20 / v120
    return F


# ---------------------------------------------------------------- rules

QS = (5, 10, 20, 30, 50, 70, 80, 90, 95)
HOLDS = (1, 2, 5, 10, 20)


def draw_rules(names, n, seed=SEED):
    rnd = random.Random(seed)
    seen, out = set(), []
    while len(out) < n:
        c1 = (rnd.choice(names), rnd.choice(QS), rnd.choice((">", "<")))
        c2 = (rnd.choice(names), rnd.choice(QS), rnd.choice((">", "<"))) if rnd.random() < 0.5 else None
        h = rnd.choice(HOLDS)
        key = (c1, c2, h)
        if key in seen or (c2 and c2[0] == c1[0]):
            continue
        seen.add(key)
        out.append(key)
    return out


def thresholds(F, is_mask):
    """Per feature, per fund, per q: the IS percentile."""
    T = {}
    for k, X in F.items():
        Xi = np.where(is_mask[None, :], X, np.nan)
        T[k] = {q: np.nanpercentile(Xi, q, axis=1) for q in QS}
    return T


def held(sig, h):
    """True for h days after any True (inclusive of the signal day)."""
    if h == 1:
        return sig
    cs = np.cumsum(sig, axis=1)
    lag = np.concatenate([np.zeros((sig.shape[0], h)), cs[:, :-h]], axis=1)
    return (cs - lag) > 0


class Engine:
    def __init__(self, C, dates):
        self.dates = dates
        r = C / np.roll(C, 1, axis=1) - 1
        r[:, 0] = np.nan
        drift = rolling_mean(r, 250)
        # position decided at t, held from close t+1: earns the return of day t+2
        ex = np.full_like(r, np.nan)
        ex[:, :-2] = r[:, 2:] - drift[:, :-2]
        self.ex = ex
        self.live = ~np.isnan(ex) & ~np.isnan(drift)
        self.is_m = dates <= IS_END
        self.oos_m = (dates > IS_END) & (dates <= OOS_END)
        self.ho_m = dates > OOS_END

    def daily(self, pos, cost):
        """Equal-weight daily portfolio of funds holding a position; turnover cost per fund."""
        pos = pos & self.live
        p = pos.astype(float)
        turn = np.abs(np.diff(p, axis=1, prepend=0.0))
        pnl = np.where(pos, np.nan_to_num(self.ex), 0.0) - turn * cost / 1e4
        n = p.sum(axis=0)
        with np.errstate(invalid="ignore", divide="ignore"):
            port = np.where(n > 0, pnl.sum(axis=0) / np.maximum(n, 1), 0.0)
        return port

    @staticmethod
    def t(x):
        x = x[~np.isnan(x)]
        if len(x) < 30 or x.std() == 0:
            return 0.0, 0.0
        return float(x.mean() / (x.std(ddof=1) / math.sqrt(len(x)))), float(x.mean() * 1e4)


def signal(rule, F, T):
    (f1, q1, o1), c2, h = rule
    a = F[f1]
    th = T[f1][q1][:, None]
    s = (a > th) if o1 == ">" else (a < th)
    if c2:
        f2, q2, o2 = c2
        b = F[f2]
        th2 = T[f2][q2][:, None]
        s &= (b > th2) if o2 == ">" else (b < th2)
    s &= ~np.isnan(a)
    return held(s, h)


def describe(rule):
    (f1, q1, o1), c2, h = rule
    s = "%s %s p%d" % (f1, o1, q1)
    if c2:
        s += " AND %s %s p%d" % (c2[0], c2[1], c2[2])
    return "%s, hold %dd" % (s, h)


def bh_keep(pvals, alpha):
    order = np.argsort(pvals)
    m = len(pvals)
    keep = np.zeros(m, bool)
    best = -1
    for rank, i in enumerate(order, 1):
        if pvals[i] <= alpha * rank / m:
            best = rank
    if best > 0:
        keep[order[:best]] = True
    return keep


def norm_sf(t):
    return 0.5 * math.erfc(t / math.sqrt(2))


def pipeline(rules, sig_fn, E, label):
    is_t = np.zeros(len(rules))
    for k, r in enumerate(rules):
        port = E.daily(sig_fn(r), COSTS[0])
        is_t[k] = E.t(port[E.is_m])[0]
        if (k + 1) % 10000 == 0:
            print("  %s: %d rules scored" % (label, k + 1), flush=True)
    top = np.argsort(-is_t)[:TOP_IS]
    rows = []
    for k in top:
        pos = sig_fn(rules[k])
        p10, p20 = E.daily(pos, COSTS[0]), E.daily(pos, COSTS[1])
        rows.append({"rule": describe(rules[k]), "is_t": is_t[k],
                     "oos_t": E.t(p10[E.oos_m])[0], "oos_bp": E.t(p10[E.oos_m])[1],
                     "ho_t": E.t(p10[E.ho_m])[0], "ho_bp": E.t(p10[E.ho_m])[1],
                     "ho_bp20": E.t(p20[E.ho_m])[1]})
    pv = np.array([norm_sf(r["oos_t"]) for r in rows])
    keep = bh_keep(pv, FDR) & (np.array([r["oos_t"] for r in rows]) > 0)
    surv = [r for r, k in zip(rows, keep) if k]
    passed = [r for r in surv if r["ho_t"] >= HOLD_T and r["ho_bp20"] > 0]
    return {"label": label, "n_rules": len(rules), "is_t_max": float(is_t.max()),
            "is_t_top1000_min": float(is_t[top[-1]]), "is_t_ge3": int((is_t >= 3).sum()),
            "top10": rows[:10], "oos_survivors": surv, "passed": passed}


def cmd_test(a):
    syms, dates, C = load_panel()
    print("Swarm: %d funds, %s to %s, %d days" % (len(syms), dates[0], dates[-1], len(dates)), flush=True)
    F = features(C)
    E = Engine(C, dates)
    T = thresholds(F, E.is_m)
    names = sorted(F)
    rules = draw_rules(names, a.rules)
    real = pipeline(rules, lambda r: signal(r, F, T), E, "real")
    # luck benchmark: 1,000 rules whose signals are circularly shifted per fund by a random offset
    rnd = np.random.default_rng(SEED)
    luck_rules = rules[:1000]
    shifts = {i: rnd.integers(500, C.shape[1] - 500, size=C.shape[0]) for i in range(len(luck_rules))}
    idx = {id(r): i for i, r in enumerate(luck_rules)}

    def shifted(r):
        s = signal(r, F, T)
        sh = shifts[idx[id(r)]]
        return np.stack([np.roll(s[j], sh[j]) for j in range(s.shape[0])])
    luck = pipeline(luck_rules, shifted, E, "luck")
    for res in (real, luck):
        print("\n[%s] %d rules: best IS t %.2f, %d with IS t >= 3, OOS survivors (BH 5%%): %d, PASS: %d" % (
            res["label"], res["n_rules"], res["is_t_max"], res["is_t_ge3"], len(res["oos_survivors"]), len(res["passed"])))
        for r in res["top10"][:5]:
            print("   IS t %5.2f | OOS t %5.2f (%5.2f bp/d) | HOLD t %5.2f (%5.2f bp/d, %5.2f at 20bp) | %s" % (
                r["is_t"], r["oos_t"], r["oos_bp"], r["ho_t"], r["ho_bp"], r["ho_bp20"], r["rule"]))
    print("\nPassed (HOLDOUT t >= 3 after costs):")
    for r in real["passed"]:
        print("   HOLD t %.2f  %.2f bp/d  | %s" % (r["ho_t"], r["ho_bp"], r["rule"]))
    if not real["passed"]:
        print("   none")
    print("\nResearch, not financial advice.")
    if a.write:
        with open(a.write, "w") as fh:
            json.dump({"real": real, "luck": luck, "funds": syms}, fh, indent=1, default=float)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("fetch")
    p = sub.add_parser("test")
    p.add_argument("--rules", type=int, default=100000)
    p.add_argument("--write", nargs="?", const=os.path.join(RESULTS, "swarm.json"))
    a = ap.parse_args(argv)
    try:
        return {"fetch": cmd_fetch, "test": cmd_test}[a.cmd](a) if a.cmd else ap.print_help() or 1
    except daily.LabError as e:
        print("swarm.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
