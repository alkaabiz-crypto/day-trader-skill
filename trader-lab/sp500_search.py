#!/usr/bin/env python3
"""trader-lab S&P 500 combination search: 200,000+ SPY candidates built from published conditions.

    python3 sp500_search.py                 # all candidates, Reality Check + SPA, portfolio test
    python3 sp500_search.py --boot 300 --write

Research script; needs numpy. Uses universe_search.py's execution (next-open fills, costs, T-bill
cash), its risk-adjusted score (Jensen's alpha against SPY buy-and-hold, beta from data before 2015)
and its Reality Check / SPA. Judged only after 2014.

Building blocks: ~170 boolean CONDITIONS known at the close (SPY technicals; volatility: VIX level,
percentile, spikes, term structure VIX/VIX3M (Simon & Campasano 2014), VIX9D/VIX, a variance-risk-
premium proxy (Bollerslev, Tauchen & Zhou 2009); rates and credit: yield-curve slope (Estrella &
Mishkin 1998), short-rate trend, HYG/IEF and LQD/IEF credit ratios, bond trend; cross-asset:
copper/gold, oil shocks (Driesprong et al. 2008), dollar, gold, emerging vs US; breadth: RSP/SPY,
IWM/SPY, XLY/XLP, sectors above their 50-day; calendar: weekday, month, Halloween (Bouman & Jacobsen
2002), turn of month, pre-holiday, option-expiration week, presidential cycle).

Candidates:
  1. single condition: long while true / long unless true; held 1, 3, 5, 10 or 20 days
  2. every PAIR of conditions (AND), the same 2 directions x 5 holds
  3. every condition's first true day as an entry, x take-profit x stop-loss x time stop
Research, not financial advice.
"""

import argparse
import datetime
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import daily  # noqa: E402
import universe_search as us  # noqa: E402

RESULTS = os.path.join(HERE, "results")
HOLDS = [1, 3, 5, 10, 20]
TPS = [None, 0.01, 0.02, 0.03, 0.05, 0.08, 0.12]
SLS = [None, 0.01, 0.02, 0.03, 0.05, 0.08, 0.12]
TIMES = [3, 5, 10, 20, 40]
NEG_HOLDS = [1, 3, 5, 20]


def aligned(sym, dates):
    """A daily series' closes aligned to `dates` (carried forward), NaN before it starts."""
    D = daily.load(sym)
    out = np.full(len(dates), np.nan)
    if not D:
        return out
    src = dict(zip(D["d"], D.get("a") or D["c"]))
    last = np.nan
    for i, d in enumerate(dates):
        v = src.get(d)
        if v is not None:
            last = v
        out[i] = last
    return out


def trend(x, n):
    return x / us.shift(x, n) - 1


def above_ma(x, n):
    return x > us.sma(np.nan_to_num(x, nan=np.nan), n)


def pct_rank(x, n=252):
    from numpy.lib.stride_tricks import sliding_window_view
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        w = sliding_window_view(x, n)
        out[n - 1:] = (w < w[:, -1:]).mean(axis=1)
    return out


def conditions(A):
    """name -> boolean array (known at the close of each day)."""
    d, o, h, l, c = A["d"], A["o"], A["h"], A["l"], A["c"]
    C = {}
    r2, r14 = us.rsi_np(c, 2), us.rsi_np(c, 14)
    for t in (5, 10, 20, 30):
        C["rsi2<%d" % t] = r2 < t
    for t in (70, 80, 90, 95):
        C["rsi2>%d" % t] = r2 > t
    C["rsi14<30"], C["rsi14<40"], C["rsi14>60"], C["rsi14>70"] = r14 < 30, r14 < 40, r14 > 60, r14 > 70
    for n in (5, 10, 20, 50, 100, 200):
        m = us.sma(c, n)
        C["c>ma%d" % n], C["c<ma%d" % n] = c > m, c < m
    m200 = us.sma(c, 200)
    for x in (5, 10):
        C["c<ma200-%d%%" % x] = c < m200 * (1 - x / 100.0)
        C["c>ma200+%d%%" % x] = c > m200 * (1 + x / 100.0)
    for n in (1, 2, 3, 5, 10, 21, 63, 126, 252):
        rr = trend(c, n)
        C["ret%d>0" % n], C["ret%d<0" % n] = rr > 0, rr < 0
    for n in (5, 20, 50, 252):
        C["high%d" % n] = c >= us.rolling_max(c, n)
        C["low%d" % n] = c <= us.rolling_min(c, n)
    up = np.diff(c, prepend=c[0]) > 0
    dn = np.diff(c, prepend=c[0]) < 0
    for k in (2, 3, 4):
        C["down%d" % k] = np.convolve(dn.astype(float), np.ones(k), "full")[:len(c)] >= k
        C["up%d" % k] = np.convolve(up.astype(float), np.ones(k), "full")[:len(c)] >= k
    ibs = (c - l) / np.maximum(h - l, 1e-12)
    C["ibs<0.2"], C["ibs>0.8"] = ibs < 0.2, ibs > 0.8
    gap = o / us.shift(c) - 1
    C["gapdown"], C["gapup"] = gap < -0.005, gap > 0.005
    ret = np.diff(np.log(c), prepend=np.log(c[0]))
    from numpy.lib.stride_tricks import sliding_window_view
    rv20 = np.full(len(c), np.nan)
    rv20[19:] = sliding_window_view(ret, 20).std(axis=1) * math.sqrt(252)
    rv60 = np.full(len(c), np.nan)
    rv60[59:] = sliding_window_view(ret, 60).std(axis=1) * math.sqrt(252)
    med = np.full(len(c), np.nan)
    med[251:] = np.nanmedian(sliding_window_view(rv20, 252), axis=1)
    C["rv_high"], C["rv_low"], C["rv_rising"] = rv20 > med, rv20 < med, rv20 > rv60
    hi252 = us.rolling_max(c, 252)
    C["near52wHigh"], C["deep_drawdown"] = c >= 0.95 * hi252, c <= 0.8 * hi252

    def ratio_conds(name, a, b):
        r = a / b
        C[name + "_up20"], C[name + "_down20"] = trend(r, 20) > 0, trend(r, 20) < 0

    ratio_conds("rsp_spy", aligned("RSP", d), c)
    ratio_conds("iwm_spy", aligned("IWM", d), c)
    ratio_conds("xly_xlp", aligned("XLY", d), aligned("XLP", d))
    ratio_conds("eem_spy", aligned("EEM", d), c)
    vix = aligned("^VIX", d)
    for t in (15, 20, 25, 30, 40):
        C["vix>%d" % t] = vix > t
    for t in (12, 15, 20):
        C["vix<%d" % t] = vix < t
    vp = pct_rank(vix)
    C["vix_pct>80"], C["vix_pct<20"] = vp > 0.8, vp < 0.2
    vch = vix / us.shift(vix) - 1
    C["vix_jump10"], C["vix_jump20"], C["vix_drop10"] = vch > 0.10, vch > 0.20, vch < -0.10
    v3 = aligned("^VIX3M", d)
    C["vix_backwardation"], C["vix_contango10"], C["vix_contango15"] = vix / v3 > 1, vix / v3 < 0.9, vix / v3 < 0.85
    v9 = aligned("^VIX9D", d)
    C["vix9d>vix"] = v9 / vix > 1
    C["vix>ma10"], C["vix<ma10"] = vix > us.sma(vix, 10), vix < us.sma(vix, 10)
    vrp = (vix / 100.0) ** 2 - rv20 ** 2
    C["vrp>0"], C["vrp_high"] = vrp > 0, vrp > np.nanmedian(vrp)
    tnx, irx = aligned("^TNX", d), aligned("^IRX", d)
    slope = tnx - irx
    C["curve_inverted"], C["curve>1"], C["curve>2"] = slope < 0, slope > 1, slope > 2
    C["10y_up20"], C["10y_down20"] = tnx - us.shift(tnx, 20) > 0, tnx - us.shift(tnx, 20) < 0
    C["3m_up63"], C["3m_down63"] = irx - us.shift(irx, 63) > 0, irx - us.shift(irx, 63) < 0
    hyg, ief, lqd, tlt = aligned("HYG", d), aligned("IEF", d), aligned("LQD", d), aligned("TLT", d)
    ratio_conds("hyg_ief", hyg, ief)
    ratio_conds("lqd_ief", lqd, ief)
    C["hyg<ma50"] = hyg < us.sma(hyg, 50)
    C["tlt_up20"], C["tlt_down20"] = trend(tlt, 20) > 0, trend(tlt, 20) < 0
    C["tlt>ma200"] = tlt > us.sma(tlt, 200)
    cu, au, oil, uup = aligned("HG=F", d), aligned("GLD", d), aligned("CL=F", d), aligned("UUP", d)
    ratio_conds("copper_gold", cu, au)
    C["copper_gold>ma50"] = (cu / au) > us.sma(cu / au, 50)
    C["oil_up10"], C["oil_down10"] = trend(oil, 21) > 0.10, trend(oil, 21) < -0.10
    C["usd_up20"], C["usd_down20"] = trend(uup, 20) > 0, trend(uup, 20) < 0
    C["gld>ma200"] = au > us.sma(au, 200)
    secs = [aligned(s, d) for s in ("XLK", "XLY", "XLP", "XLU", "XLF", "XLE", "XLI", "XLV", "XLB")]
    above = sum(np.nan_to_num((s > us.sma(s, 50)).astype(float)) for s in secs)
    C["breadth>=7"], C["breadth<=3"] = above >= 7, above <= 3
    dt = [datetime.date(*map(int, x.split("-"))) for x in d]
    nxt = [dt[i + 1] if i + 1 < len(dt) else dt[i] + datetime.timedelta(days=1) for i in range(len(dt))]
    wd = np.array([x.weekday() for x in nxt])                      # the session the position is held
    mo = np.array([x.month for x in nxt])
    for k in range(5):
        C["next_wd%d" % k] = wd == k
    for m in range(1, 13):
        C["next_m%d" % m] = mo == m
    C["halloween"] = np.isin(mo, [11, 12, 1, 2, 3, 4])
    month_of = np.array([x.month for x in dt])
    last_day = np.array([i + 1 < len(dt) and dt[i + 1].month != dt[i].month for i in range(len(dt))])
    first3 = np.zeros(len(dt), bool)
    k = 0
    for i in range(len(dt)):
        k = 1 if i == 0 or dt[i].month != dt[i - 1].month else k + 1
        first3[i] = k <= 2                                         # held into the 2nd/3rd trading day
    C["turn_of_month"] = last_day | first3
    gaps = np.array([(nxt[i] - dt[i]).days for i in range(len(dt))])
    C["pre_holiday"] = (gaps >= 2) & (np.array([x.weekday() for x in dt]) < 4) | (gaps >= 4)
    third_fri = np.array([(x.day + (4 - x.replace(day=1).weekday()) % 7) for x in nxt])
    C["opex_week"] = np.array([15 <= x.day <= 21 for x in nxt])
    C["pres_y1"], C["pres_y2"] = np.array([x.year % 4 == 1 for x in nxt]), np.array([x.year % 4 == 2 for x in nxt])
    C["pres_y3"], C["pres_y4"] = np.array([x.year % 4 == 3 for x in nxt]), np.array([x.year % 4 == 0 for x in nxt])
    del month_of, third_fri
    return {k: np.nan_to_num(v.astype(float)) > 0 for k, v in C.items()}


def candidates(A, C):
    """Yield (name, params, kind, payload): kind 'pos' -> daily position path; 'trade' -> (pos, exits)."""
    names = sorted(C)
    for nm in names:
        cond = C[nm]
        for hc in HOLDS:
            on = us.hold_for(cond, hc)
            yield "one:" + nm, {"hold": hc, "dir": "long_when"}, "pos", on
            yield "one:" + nm, {"hold": hc, "dir": "long_unless"}, "pos", 1.0 - on
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            cond = C[names[i]] & C[names[j]]
            if cond.sum() < 20:
                continue
            for hc in HOLDS:
                on = us.hold_for(cond, hc)
                yield "pair:%s&%s" % (names[i], names[j]), {"hold": hc, "dir": "long_when"}, "pos", on
                yield "pair:%s&%s" % (names[i], names[j]), {"hold": hc, "dir": "long_unless"}, "pos", 1.0 - on
    for a in names:
        for b in names:
            if a == b:
                continue
            cond = C[a] & ~C[b]
            if cond.sum() < 20 or cond.sum() == C[a].sum():
                continue
            for hc in NEG_HOLDS:
                yield "andnot:%s&!%s" % (a, b), {"hold": hc, "dir": "long_when"}, "pos", us.hold_for(cond, hc)
    for nm in names:
        edge = C[nm] & ~np.concatenate(([False], C[nm][:-1]))
        if edge.sum() < 10:
            continue
        for tp in TPS:
            for sl in SLS:
                for T in TIMES:
                    yield "entry:" + nm, {"tp": tp, "sl": sl, "T": T}, "trade", us.trade_path(A, edge, tp, sl, T)


def search(boot=300, seed=7):
    t0 = time.time()
    A = us.load_asset("SPY")
    C = conditions(A)
    cost = 2.0
    bh = us.returns_for(A, np.ones(len(A["c"])), cost, 0.0)
    dates = np.array(A["d"])
    post, pre = dates > us.IS_END, dates <= us.IS_END
    rf = A["rf"]
    bh_x = bh - rf
    bi = bh_x[pre]
    vb = np.var(bi, ddof=1)
    n_post = int(post.sum())
    names, params, is_t, post_t, post_mean, sharpe = [], [], [], [], [], []
    chunks = []
    buf = []
    for name, p, kind, payload in candidates(A, C):
        if kind == "pos":
            r = us.returns_for(A, payload, cost, 0.0)
        else:
            r = us.returns_exit(A, payload[0], payload[1], cost, 0.0)
        x = r - rf
        xi = x[pre]
        beta = float(((xi - xi.mean()) * (bi - bi.mean())).sum() / (len(xi) - 1) / vb) if vb > 0 else 0.0
        e = x - beta * bh_x
        ep, ei = e[post], e[pre]
        sdi, sdp = ei.std(ddof=1), ep.std(ddof=1)
        names.append(name)
        params.append(p)
        is_t.append(ei.mean() / sdi * math.sqrt(len(ei)) if sdi > 0 else 0.0)
        post_t.append(ep.mean() / sdp * math.sqrt(len(ep)) if sdp > 0 else 0.0)
        post_mean.append(ep.mean() * 1e4)
        xp = x[post]
        sharpe.append(xp.mean() / xp.std() * math.sqrt(252) if xp.std() > 0 else 0.0)
        buf.append(ep.astype(np.float32))
        if len(buf) >= 20000:
            chunks.append(np.vstack(buf))
            buf = []
            print("  %d candidates (%.0fs)" % (len(names), time.time() - t0), file=sys.stderr)
    if buf:
        chunks.append(np.vstack(buf))
    E = np.vstack(chunks)
    del chunks
    print("  %d candidates built (%.0fs); Reality Check..." % (len(names), time.time() - t0), file=sys.stderr)
    rc = reality_check_big(E, boot, seed=seed)
    rc2 = reality_check_big(E, boot, seed=seed + 1000)
    rc["rc_p_seed2"], rc["spa_p_seed2"] = rc2["rc_p"], rc2["spa_p"]
    is_t, post_t, post_mean, sharpe = map(np.array, (is_t, post_t, post_mean, sharpe))
    bh_sh = bh_x[post].mean() / bh_x[post].std() * math.sqrt(252)
    ens = {}
    for K in (1, 10, 50, 200, 1000, 5000):
        sel = np.argsort(-is_t)[:K]
        s = E[sel].astype(np.float64).mean(axis=0)
        ens[str(K)] = {"alpha_t": float(s.mean() / s.std(ddof=1) * math.sqrt(len(s))), "alpha_bp_day": float(s.mean() * 1e4)}
    kinds = {}
    for nm, t, sh in zip(names, post_t, sharpe):
        k = kinds.setdefault(nm.split(":")[0], {"n": 0, "alpha_pos": 0, "t3": 0, "sharpe_over_bh": 0})
        k["n"] += 1
        k["alpha_pos"] += int(t > 0)
        k["t3"] += int(t >= 3)
        k["sharpe_over_bh"] += int(sh > bh_sh)
    best = np.argsort(-post_t)[:10]
    by_mean = np.argsort(-post_mean)[:5]
    sd_post = E.std(axis=1, dtype=np.float64)
    return {"asset": "SPY", "candidates": len(names), "conditions": len(C), "days_post": n_post,
            "bh_sharpe_post": float(bh_sh), "reality_check": rc, "by_kind": kinds,
            "n_t3": int((post_t >= 3).sum()), "n_bonferroni": int((post_t >= rc["bonferroni_z"]).sum()),
            "n_sharpe_over_bh": int((sharpe > bh_sh).sum()), "best_sharpe": float(sharpe.max()),
            "best_post": [{"rule": names[i], "params": params[i], "post_t": float(post_t[i]), "is_t": float(is_t[i]),
                           "alpha_bp_day": float(post_mean[i]), "sharpe": float(sharpe[i])} for i in best],
            "best_by_mean": [{"rule": names[i], "params": params[i], "alpha_bp_day": float(post_mean[i]),
                              "post_t": float(post_t[i]), "is_t": float(is_t[i]), "sd_bp": float(sd_post[i] * 1e4)}
                             for i in by_mean],
            "sd_bp_quantiles": [float(np.quantile(sd_post, q) * 1e4) for q in (0.5, 0.9, 0.99, 1.0)],
            "top_is": [{"rule": names[i], "params": params[i], "is_t": float(is_t[i]), "post_t": float(post_t[i])}
                       for i in np.argsort(-is_t)[:10]],
            "portfolio_is_selected": ens, "seconds": round(time.time() - t0)}


def reality_check_big(E, B=300, block=10, seed=7):
    """Reality Check and SPA for a large rule matrix, in chunks of rules to bound memory."""
    M, n = E.shape
    rng = np.random.default_rng(seed)
    means = E.mean(axis=1, dtype=np.float64)
    sd = E.std(axis=1, ddof=1, dtype=np.float64)
    sd[sd == 0] = np.inf
    tstat = math.sqrt(n) * means / sd
    v = math.sqrt(n) * means.max()
    t_spa = max(tstat.max(), 0.0)
    thr = -math.sqrt(2 * math.log(math.log(n)))
    g = np.where(tstat >= thr, means, 0.0)
    # stationary bootstrap as (start, length) blocks; block sums from prefix sums (no wrap within a block)
    segs = []
    for b in range(B):
        st, ln = [], []
        total = 0
        while total < n:
            L = int(rng.geometric(1.0 / block))
            L = min(L, n - total)
            s0 = int(rng.integers(0, n))
            while L > 0:                                  # split blocks that run past the end (circular)
                take = min(L, n - s0)
                st.append(s0)
                ln.append(take)
                total += take
                L -= take
                s0 = 0
        segs.append((np.array(st), np.array(st) + np.array(ln)))
    vb = np.full(B, -np.inf)
    tb = np.zeros(B)
    sb = np.full(B, -np.inf)                              # Romano-Wolf: max studentized deviation
    step = 20000
    for a in range(0, M, step):
        Eb = E[a:a + step].astype(np.float64)
        P = np.concatenate((np.zeros((Eb.shape[0], 1)), np.cumsum(Eb, axis=1)), axis=1)
        mu, gg, s = means[a:a + step], g[a:a + step], sd[a:a + step]
        for b in range(B):
            st, en = segs[b]
            mb = (P[:, en] - P[:, st]).sum(axis=1) / n
            vb[b] = max(vb[b], math.sqrt(n) * (mb - mu).max())
            tb[b] = max(tb[b], (math.sqrt(n) * (mb - gg) / s).max())
            sb[b] = max(sb[b], (math.sqrt(n) * (mb - mu) / s).max())
        del P, Eb
    return {"M": M, "n": n, "best_mean_bps": float(means.max() * 1e4), "best_t": float(tstat.max()),
            "rc_p": float((vb >= v).mean()), "spa_p": float((np.maximum(tb, 0) >= t_spa).mean()),
            **us.gate(tstat, sb, (np.maximum(tb, 0) >= t_spa).mean()),
            "bonferroni_z": float(us.z_bonferroni(M))}


def report(r):
    rc = r["reality_check"]
    L = ["S&P 500 combination search: %s SPY candidates from %d published conditions; risk-adjusted (Jensen's" % (
        "{:,}".format(r["candidates"]), r["conditions"]),
        "alpha vs buy-and-hold, beta before 2015), T-bill cash, 2 bp costs, judged only after 2014 (%d days)." % r["days_post"],
        "",
        "Best alpha t %.2f (%.2f bp/day). Reality Check p = %.3f | SPA p = %.3f | t >= %.2f (Bonferroni): %d | t >= 3: %d" % (
            rc["best_t"], rc["best_mean_bps"], rc["rc_p"], rc["spa_p"], rc["bonferroni_z"], r["n_bonferroni"], r["n_t3"]),
        us.gate_line(rc),
        "Buy-and-hold Sharpe %.2f; %s candidates beat it (best %.2f)." % (
            r["bh_sharpe_post"], "{:,}".format(r["n_sharpe_over_bh"]), r["best_sharpe"]), "", "By kind:"]
    for k, v in r["by_kind"].items():
        L.append("  %-6s %8s candidates | positive alpha %5.1f%% | t >= 3: %4d | Sharpe > buy-and-hold: %s" % (
            k, "{:,}".format(v["n"]), 100.0 * v["alpha_pos"] / v["n"], v["t3"], "{:,}".format(v["sharpe_over_bh"])))
    L += ["", "Best after 2014 (with their record before 2015):"]
    for b in r["best_post"][:5]:
        L.append("  t %.2f (IS t %5.2f, Sharpe %.2f)  %s %s" % (b["post_t"], b["is_t"], b["sharpe"], b["rule"],
                                                              json.dumps(b["params"], sort_keys=True)))
    L += ["", "Portfolio of the top-K candidates chosen BEFORE 2015, judged after 2014 (one strategy each):",
          "  " + ", ".join("K=%s: t %.2f" % (k, v["alpha_t"]) for k, v in sorted(r["portfolio_is_selected"].items(),
                                                                          key=lambda kv: int(kv[0]))),
          "", "Research, not financial advice."]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description="S&P 500 combination search")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--boot", type=int, default=300)
    ap.add_argument("--write", nargs="?", const=os.path.join(RESULTS, "sp500-latest.json"))
    ap.add_argument("--count", action="store_true", help="only count the candidates")
    a = ap.parse_args(argv)
    if a.count:
        A = us.load_asset("SPY")
        C = conditions(A)
        n = sum(1 for _ in candidates_count(C))
        print("%d conditions -> %s candidates" % (len(C), "{:,}".format(n)))
        return 0
    r = search(a.boot, a.seed)
    if a.write:
        with open(a.write, "w") as fh:
            json.dump(r, fh, indent=1, sort_keys=True)
    print(report(r))
    return 0


def candidates_count(C):
    names = sorted(C)
    for nm in names:
        for _ in range(2 * len(HOLDS)):
            yield 1
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if (C[names[i]] & C[names[j]]).sum() >= 20:
                for _ in range(2 * len(HOLDS)):
                    yield 1
    for a in names:
        for b in names:
            if a != b:
                c = C[a] & ~C[b]
                if c.sum() >= 20 and c.sum() != C[a].sum():
                    for _ in NEG_HOLDS:
                        yield 1
    for nm in names:
        if (C[nm] & ~np.concatenate(([False], C[nm][:-1]))).sum() >= 10:
            for _ in range(len(TPS) * len(SLS) * len(TIMES)):
                yield 1


if __name__ == "__main__":
    sys.exit(main())
