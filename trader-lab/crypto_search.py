#!/usr/bin/env python3
"""trader-lab crypto combination search: 600,000+ daily candidates for BTC-USD or ETH-USD.

    python3 crypto_search.py --asset BTC-USD --count      # only count the candidates
    python3 crypto_search.py --asset BTC-USD --boot 300 --write
    python3 crypto_search.py --asset ETH-USD --boot 300 --write

Research script; needs numpy. Same method as sp500_search.py, adapted to a market that trades every
day:
  * signal at the daily close (00:00 UTC on Yahoo), filled at the next day's open, COST_BPS per
    position change (spread plus fees); cash earns the T-bill rate per calendar day
  * score: Jensen's alpha against buy-and-hold of the same coin, beta estimated in-sample only
  * judged only after IS_END (BTC: 2019-12-31, ETH: 2021-06-30); nothing after it is used to choose
  * multiple testing over every candidate: Hansen's SPA AND Romano-Wolf's studentized max-t
    (universe_search.gate); White's Reality Check is printed for information only (it rejected on
    null data, RESEARCH.md 2026-11-23). The bootstrap runs in chunks, so the return matrix
    (600k x 2,500 days) is never held in memory.

Conditions (known at the close), from the crypto literature and the S&P 500 search:
  time-series momentum over 1 to 365 days (Liu & Tsyvinski 2021, Rev. Fin. Studies), moving-average
  ratios (Detzel, Liu, Strauss, Zhou & Zhu 2021, Financial Management), Mayer multiple (price/200-day
  average), RSI, MACD, Bollinger, stochastics, Donchian highs and lows, streaks, IBS, realized
  volatility regimes, distance from the all-time high, volume shocks as attention (Liu & Tsyvinski),
  ETH/BTC ratio, links to stocks, VIX, the dollar, gold, rates, credit, oil and copper, and the
  calendar: weekday and weekend (Caporale & Plastun 2019), month, turn of month, Halloween, and
  the halving cycle.

Candidates: each condition alone, every AND pair and every "A and not B" pair, as long-while-true,
long-unless-true or short-while-true, held HOLDS days; and each condition's first true day as an
entry with take-profit x stop x time-stop exits. Research, not financial advice.
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
from sp500_search import aligned, trend, pct_rank  # noqa: E402

RESULTS = os.path.join(HERE, "results")
IS_ENDS = {"BTC-USD": "2019-12-31", "ETH-USD": "2021-06-30"}
OTHER = {"BTC-USD": "ETH-USD", "ETH-USD": "BTC-USD"}
COST_BPS = 10.0
HOLDS = [1, 2, 3, 5, 7, 10, 14, 21, 30]
NEG_HOLDS = [1, 3, 7, 14, 30]
TPS = [None, 0.02, 0.04, 0.06, 0.10, 0.15, 0.25]
SLS = [None, 0.02, 0.04, 0.06, 0.10, 0.15, 0.25]
TIMES = [3, 7, 14, 30, 60]
HALVINGS = [datetime.date(2012, 11, 28), datetime.date(2016, 7, 9), datetime.date(2020, 5, 11),
            datetime.date(2024, 4, 20)]
MIN_DAYS = 20


def load_coin(sym):
    D = daily.load(sym)
    if not D:
        raise SystemExit("no data for %s: run daily.py fetch --symbols %s" % (sym, sym))
    dates = D["d"]
    irx = daily.load("^IRX")
    rf = np.zeros(len(dates))
    if irx:
        m = dict(zip(irx["d"], irx["c"]))
        last = 0.0
        for i, d in enumerate(dates):
            last = m.get(d, last)
            rf[i] = last / 100.0 / 365.0           # T-bill rate per calendar day
    return {"d": dates, "o": np.array(D["o"], float), "h": np.array(D["h"], float),
            "l": np.array(D["l"], float), "c": np.array(D["c"], float), "v": np.array(D["v"], float), "rf": rf}


def rolling_std(x, n):
    from numpy.lib.stride_tricks import sliding_window_view
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        out[n - 1:] = sliding_window_view(x, n).std(axis=1)
    return out


def streak(flags, k):
    return np.convolve(flags.astype(float), np.ones(k), "full")[:len(flags)] >= k


def conditions(A, sym):
    """name -> boolean array (known at the close of each day)."""
    d, o, h, l, c, v = A["d"], A["o"], A["h"], A["l"], A["c"], A["v"]
    C = {}
    r2, r7, r14 = us.rsi_np(c, 2), us.rsi_np(c, 7), us.rsi_np(c, 14)
    for t in (5, 10, 20, 30):
        C["rsi2<%d" % t] = r2 < t
    for t in (70, 80, 90, 95):
        C["rsi2>%d" % t] = r2 > t
    C["rsi7<20"], C["rsi7>80"] = r7 < 20, r7 > 80
    for t in (30, 40):
        C["rsi14<%d" % t] = r14 < t
    for t in (60, 70, 80):
        C["rsi14>%d" % t] = r14 > t
    for n in (5, 10, 20, 50, 100, 140, 200, 350):
        m = us.sma(c, n)
        C["c>ma%d" % n], C["c<ma%d" % n] = c > m, c < m
    m200 = us.sma(c, 200)
    mayer = c / m200
    for x in (10, 20, 40):
        C["c>ma200+%d%%" % x] = mayer > 1 + x / 100.0
    C["c<ma200-10%"], C["c<ma200-20%"] = mayer < 0.9, mayer < 0.8
    C["mayer>2.4"] = mayer > 2.4
    for f, s in ((5, 20), (10, 50), (20, 50), (20, 100), (50, 200), (7, 30)):
        mf, ms = us.sma(c, f), us.sma(c, s)
        C["ma%d>ma%d" % (f, s)], C["ma%d<ma%d" % (f, s)] = mf > ms, mf < ms
    for n in (1, 2, 3, 5, 7, 14, 21, 30, 60, 90, 180, 365):
        rr = trend(c, n)
        C["ret%d>0" % n], C["ret%d<0" % n] = rr > 0, rr < 0
    r1, r7d = trend(c, 1), trend(c, 7)
    C["ret1>5%"], C["ret1<-5%"], C["ret1>10%"], C["ret1<-10%"] = r1 > 0.05, r1 < -0.05, r1 > 0.10, r1 < -0.10
    C["ret7>20%"], C["ret7<-20%"] = r7d > 0.20, r7d < -0.20
    C["ret30>50%"], C["ret30<-30%"] = trend(c, 30) > 0.5, trend(c, 30) < -0.3
    for n in (7, 20, 50, 100, 365):
        C["high%d" % n] = c >= us.rolling_max(c, n)
        C["low%d" % n] = c <= us.rolling_min(c, n)
    up = np.diff(c, prepend=c[0]) > 0
    dn = np.diff(c, prepend=c[0]) < 0
    for k in (2, 3, 4, 5):
        C["down%d" % k], C["up%d" % k] = streak(dn, k), streak(up, k)
    ibs = (c - l) / np.maximum(h - l, 1e-12)
    C["ibs<0.2"], C["ibs>0.8"] = ibs < 0.2, ibs > 0.8
    rng = (h - l) / c
    avg_rng = us.sma(rng, 20)
    C["wide_range"], C["narrow_range"] = rng > 2 * avg_rng, rng < 0.5 * avg_rng
    C["inside_day"] = (h < us.shift(h)) & (l > us.shift(l))
    ret = np.diff(np.log(c), prepend=np.log(c[0]))
    rv20 = rolling_std(ret, 20) * math.sqrt(365)
    rv90 = rolling_std(ret, 90) * math.sqrt(365)
    from numpy.lib.stride_tricks import sliding_window_view
    med = np.full(len(c), np.nan)
    med[364:] = np.nanmedian(sliding_window_view(rv20, 365), axis=1)
    C["rv_high"], C["rv_low"], C["rv_rising"], C["rv_falling"] = rv20 > med, rv20 < med, rv20 > rv90, rv20 < rv90
    C["rv20>100%"], C["rv20<40%"] = rv20 > 1.0, rv20 < 0.4
    ath = np.maximum.accumulate(c)
    C["near_ath"], C["dd>50%"], C["dd>75%"] = c >= 0.95 * ath, c <= 0.5 * ath, c <= 0.25 * ath
    C["dd365>30%"] = c <= 0.7 * us.rolling_max(c, 365)
    av20 = us.sma(v, 20)
    C["vol>2x"], C["vol<0.5x"], C["vol_rising"] = v > 2 * av20, v < 0.5 * av20, us.sma(v, 5) > av20
    C["up_on_vol"], C["down_on_vol"] = (r1 > 0) & (v > 1.5 * av20), (r1 < 0) & (v > 1.5 * av20)
    m20, s20 = us.sma(c, 20), rolling_std(c, 20)
    C["c>bb_upper"], C["c<bb_lower"] = c > m20 + 2 * s20, c < m20 - 2 * s20
    macd = us.ema(c, 12) - us.ema(c, 26)
    sig = us.ema(macd, 9)
    C["macd>signal"], C["macd<signal"], C["macd>0"], C["macd<0"] = macd > sig, macd < sig, macd > 0, macd < 0
    lo14, hi14 = us.rolling_min(l, 14), us.rolling_max(h, 14)
    k14 = (c - lo14) / np.maximum(hi14 - lo14, 1e-12)
    C["stoch<20"], C["stoch>80"] = k14 < 0.2, k14 > 0.8
    gap_hl = c / us.rolling_max(c, 20)
    C["pullback5_in_uptrend"] = (gap_hl < 0.95) & (c > m200)

    # the other coin (ETH for BTC, BTC for ETH) and the ETH/BTC ratio
    oth = aligned(OTHER[sym], d)
    C["other>ma50"], C["other<ma50"] = oth > us.sma(oth, 50), oth < us.sma(oth, 50)
    C["other_ret7>0"], C["other_ret7<0"] = trend(oth, 7) > 0, trend(oth, 7) < 0
    C["other_ret1>0"], C["other_ret1<0"] = trend(oth, 1) > 0, trend(oth, 1) < 0
    ratio = (oth / c) if sym == "BTC-USD" else (c / oth)                  # ETH/BTC either way
    C["ethbtc_up20"], C["ethbtc_down20"] = trend(ratio, 20) > 0, trend(ratio, 20) < 0
    C["ethbtc>ma50"] = ratio > us.sma(ratio, 50)

    # cross-asset (last weekday value carried over weekends)
    spy, qqq = aligned("SPY", d), aligned("QQQ", d)
    C["spy>ma200"], C["spy<ma200"] = spy > us.sma(spy, 140), spy < us.sma(spy, 140)   # 140 days ~ 200 sessions
    C["spy_ret7>0"], C["spy_ret7<0"] = trend(spy, 7) > 0, trend(spy, 7) < 0
    C["spy_ret1>0"], C["spy_ret1<0"] = trend(spy, 1) > 0, trend(spy, 1) < 0
    C["qqq_up30"], C["qqq_down30"] = trend(qqq, 30) > 0, trend(qqq, 30) < 0
    vix = aligned("^VIX", d)
    C["vix>20"], C["vix>30"], C["vix<15"] = vix > 20, vix > 30, vix < 15
    vch = vix / us.shift(vix) - 1
    C["vix_jump10"], C["vix_drop10"] = vch > 0.10, vch < -0.10
    vp = pct_rank(vix, 365)
    C["vix_pct>80"], C["vix_pct<20"] = vp > 0.8, vp < 0.2
    uup, gld = aligned("UUP", d), aligned("GLD", d)
    C["usd_up30"], C["usd_down30"] = trend(uup, 30) > 0, trend(uup, 30) < 0
    C["gold_up30"], C["gold_down30"] = trend(gld, 30) > 0, trend(gld, 30) < 0
    C["gld>ma200"] = gld > us.sma(gld, 280)
    tnx, irx = aligned("^TNX", d), aligned("^IRX", d)
    C["10y_up30"], C["10y_down30"] = tnx - us.shift(tnx, 30) > 0, tnx - us.shift(tnx, 30) < 0
    C["3m_up90"], C["3m_down90"] = irx - us.shift(irx, 90) > 0, irx - us.shift(irx, 90) < 0
    C["curve_inverted"] = tnx - irx < 0
    hyg, ief, tlt = aligned("HYG", d), aligned("IEF", d), aligned("TLT", d)
    C["hyg_ief_up30"], C["hyg_ief_down30"] = trend(hyg / ief, 30) > 0, trend(hyg / ief, 30) < 0
    C["tlt_up30"], C["tlt_down30"] = trend(tlt, 30) > 0, trend(tlt, 30) < 0
    oil, cu = aligned("CL=F", d), aligned("HG=F", d)
    C["oil_up10"], C["oil_down10"] = trend(oil, 30) > 0.10, trend(oil, 30) < -0.10
    C["copper_gold_up30"], C["copper_gold_down30"] = trend(cu / gld, 30) > 0, trend(cu / gld, 30) < 0

    # calendar, for the day the position is held (the next day)
    dt = [datetime.date(*map(int, x.split("-"))) for x in d]
    nxt = [x + datetime.timedelta(days=1) for x in dt]
    wd = np.array([x.weekday() for x in nxt])
    mo = np.array([x.month for x in nxt])
    dom = np.array([x.day for x in nxt])
    for k in range(7):
        C["next_wd%d" % k] = wd == k
    C["next_weekend"] = wd >= 5
    for m in range(1, 13):
        C["next_m%d" % m] = mo == m
    C["halloween"] = np.isin(mo, [11, 12, 1, 2, 3, 4])
    C["turn_of_month"] = (dom <= 3) | (np.array([(x + datetime.timedelta(days=2)).month != x.month for x in nxt]))
    C["mid_month"] = (dom >= 10) & (dom <= 20)
    C["quarter_end"] = np.isin(mo, [3, 6, 9, 12]) & (dom >= 24)
    since = np.array([(x - max(hv for hv in HALVINGS if hv <= x)).days if x >= HALVINGS[0] else -1 for x in nxt])
    for a, b in ((0, 365), (365, 730), (730, 1095), (1095, 1500)):
        C["halving_%d-%d" % (a, b)] = (since >= a) & (since < b)
    nxt_halving = np.array([min([(hv - x).days for hv in HALVINGS + [datetime.date(2028, 4, 15)] if hv > x])
                            for x in nxt])
    C["pre_halving180"] = nxt_halving <= 180
    return {k: np.nan_to_num(np.asarray(v, float)) > 0 for k, v in C.items()}


def candidates(A, C, count_only=False):
    """Yield (name, params, kind, payload); with count_only the payload is None."""
    names = sorted(C)

    def pos(cond, hc, sign=1.0):
        return None if count_only else sign * us.hold_for(cond, hc)

    for nm in names:
        cond = C[nm]
        for hc in HOLDS:
            on = pos(cond, hc)
            yield "one:" + nm, {"hold": hc, "dir": "long_when"}, "pos", on
            yield "one:" + nm, {"hold": hc, "dir": "long_unless"}, "pos", None if count_only else 1.0 - on
            yield "one:" + nm, {"hold": hc, "dir": "short_when"}, "pos", None if count_only else -on
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            cond = C[names[i]] & C[names[j]]
            if cond.sum() < MIN_DAYS or cond.sum() == C[names[i]].sum() or cond.sum() == C[names[j]].sum():
                continue
            nm = "pair:%s&%s" % (names[i], names[j])
            for hc in HOLDS:
                on = pos(cond, hc)
                yield nm, {"hold": hc, "dir": "long_when"}, "pos", on
                yield nm, {"hold": hc, "dir": "long_unless"}, "pos", None if count_only else 1.0 - on
                yield nm, {"hold": hc, "dir": "short_when"}, "pos", None if count_only else -on
    for a in names:
        for b in names:
            if a == b:
                continue
            cond = C[a] & ~C[b]
            if cond.sum() < MIN_DAYS or cond.sum() == C[a].sum():
                continue
            for hc in NEG_HOLDS:
                on = pos(cond, hc)
                yield "andnot:%s&!%s" % (a, b), {"hold": hc, "dir": "long_when"}, "pos", on
                yield "andnot:%s&!%s" % (a, b), {"hold": hc, "dir": "short_when"}, "pos", None if count_only else -on
    for nm in names:
        edge = C[nm] & ~np.concatenate(([False], C[nm][:-1]))
        if edge.sum() < 10:
            continue
        for tp in TPS:
            for sl in SLS:
                for T in TIMES:
                    yield ("entry:" + nm, {"tp": tp, "sl": sl, "T": T}, "trade",
                           None if count_only else us.trade_path(A, edge, tp, sl, T))


class StreamingGate:
    """Reality Check, SPA and Romano-Wolf over rules that arrive in chunks (Politis-Romano stationary
    bootstrap drawn once, as blocks, and shared by every chunk)."""

    def __init__(self, n, B=300, block=10, seed=7):
        rng = np.random.default_rng(seed)
        self.n, self.B = n, B
        self.segs = []
        for _ in range(B):
            st, ln, total = [], [], 0
            while total < n:
                L = min(int(rng.geometric(1.0 / block)), n - total)
                s0 = int(rng.integers(0, n))
                while L > 0:                                  # blocks wrap around the end
                    take = min(L, n - s0)
                    st.append(s0)
                    ln.append(take)
                    total += take
                    L -= take
                    s0 = 0
            st = np.array(st)
            self.segs.append((st, st + np.array(ln)))
        self.thr = -math.sqrt(2 * math.log(math.log(n)))
        self.vb = np.full(B, -np.inf)
        self.tb = np.zeros(B)
        self.sb = np.full(B, -np.inf)
        self.means, self.tstat = [], []

    def add(self, Eb):
        Eb = np.asarray(Eb, np.float64)
        n = self.n
        mu = Eb.mean(axis=1)
        sd = Eb.std(axis=1, ddof=1)
        sd[sd == 0] = np.inf
        t = math.sqrt(n) * mu / sd
        g = np.where(t >= self.thr, mu, 0.0)
        self.means.append(mu)
        self.tstat.append(t)
        P = np.concatenate((np.zeros((Eb.shape[0], 1)), np.cumsum(Eb, axis=1)), axis=1)
        for b in range(self.B):
            st, en = self.segs[b]
            mb = (P[:, en] - P[:, st]).sum(axis=1) / n
            self.vb[b] = max(self.vb[b], math.sqrt(n) * (mb - mu).max())
            self.tb[b] = max(self.tb[b], (math.sqrt(n) * (mb - g) / sd).max())
            self.sb[b] = max(self.sb[b], (math.sqrt(n) * (mb - mu) / sd).max())

    def result(self):
        means, tstat = np.concatenate(self.means), np.concatenate(self.tstat)
        n = self.n
        spa_p = float((self.tb >= max(tstat.max(), 0.0)).mean())
        out = {"M": int(len(means)), "n": n, "best_mean_bps": float(means.max() * 1e4), "best_t": float(tstat.max()),
               "rc_p": float((self.vb >= math.sqrt(n) * means.max()).mean()), "spa_p": spa_p,
               "bonferroni_z": float(us.z_bonferroni(len(means)))}
        out.update(us.gate(tstat, self.sb, spa_p))
        return out


def search(sym, boot=300, seed=7, chunk=20000):
    t0 = time.time()
    A = load_coin(sym)
    C = conditions(A, sym)
    is_end = IS_ENDS[sym]
    bh = us.returns_for(A, np.ones(len(A["c"])), COST_BPS, 0.0)
    dates = np.array(A["d"])
    post, pre = dates > is_end, dates <= is_end
    rf = A["rf"]
    bh_x = bh - rf
    bi = bh_x[pre]
    vbh = np.var(bi, ddof=1)
    n_post = int(post.sum())
    gate = StreamingGate(n_post, boot, seed=seed)
    names, params, is_t, post_t, post_mean, sharpe = [], [], [], [], [], []
    buf = []
    for name, p, kind, payload in candidates(A, C):
        r = us.returns_for(A, payload, COST_BPS, 0.0) if kind == "pos" else \
            us.returns_exit(A, payload[0], payload[1], COST_BPS, 0.0)
        x = r - rf
        xi = x[pre]
        beta = float(((xi - xi.mean()) * (bi - bi.mean())).sum() / (len(xi) - 1) / vbh) if vbh > 0 else 0.0
        e = x - beta * bh_x
        ep, ei = e[post], e[pre]
        sdi, sdp = ei.std(ddof=1), ep.std(ddof=1)
        names.append(name)
        params.append(p)
        is_t.append(ei.mean() / sdi * math.sqrt(len(ei)) if sdi > 0 else 0.0)
        post_t.append(ep.mean() / sdp * math.sqrt(len(ep)) if sdp > 0 else 0.0)
        post_mean.append(ep.mean() * 1e4)
        xp = x[post]
        sharpe.append(xp.mean() / xp.std() * math.sqrt(365) if xp.std() > 0 else 0.0)
        buf.append(ep)
        if len(buf) >= chunk:
            gate.add(np.vstack(buf))
            buf = []
            print("  %d candidates (%.0fs)" % (len(names), time.time() - t0), file=sys.stderr, flush=True)
    if buf:
        gate.add(np.vstack(buf))
    rc = gate.result()
    is_t, post_t, post_mean, sharpe = map(np.array, (is_t, post_t, post_mean, sharpe))
    bh_sh = bh_x[post].mean() / bh_x[post].std() * math.sqrt(365)
    kinds = {}
    for nm, t, sh in zip(names, post_t, sharpe):
        k = kinds.setdefault(nm.split(":")[0], {"n": 0, "alpha_pos": 0, "t3": 0, "sharpe_over_bh": 0})
        k["n"] += 1
        k["alpha_pos"] += int(t > 0)
        k["t3"] += int(t >= 3)
        k["sharpe_over_bh"] += int(sh > bh_sh)
    top_is = np.argsort(-is_t)[:20]

    def row(i):
        return {"rule": names[i], "params": params[i], "post_t": float(post_t[i]), "is_t": float(is_t[i]),
                "alpha_bp_day": float(post_mean[i]), "sharpe": float(sharpe[i])}

    return {"asset": sym, "is_end": is_end, "cost_bps": COST_BPS, "candidates": len(names), "conditions": len(C),
            "days_post": n_post, "days_pre": int(pre.sum()), "bh_sharpe_post": float(bh_sh), "reality_check": rc,
            "by_kind": kinds, "n_t3": int((post_t >= 3).sum()), "n_bonferroni": int((post_t >= rc["bonferroni_z"]).sum()),
            "n_sharpe_over_bh": int((sharpe > bh_sh).sum()), "best_sharpe": float(sharpe.max()),
            "best_post": [row(i) for i in np.argsort(-post_t)[:10]],
            "top_is": [row(i) for i in top_is],
            "top_is_mean_post_t": float(post_t[top_is].mean()),
            "corr_is_post_t": float(np.corrcoef(is_t, post_t)[0, 1]),
            "seconds": round(time.time() - t0)}


def report(r):
    rc = r["reality_check"]
    L = ["%s combination search: %s candidates from %d conditions; Jensen's alpha vs buy-and-hold (beta to %s)," % (
        r["asset"], "{:,}".format(r["candidates"]), r["conditions"], r["is_end"]),
        "T-bill cash, %.0f bp per trade, judged only after %s (%d days; %d days before)." % (
            r["cost_bps"], r["is_end"], r["days_post"], r["days_pre"]),
        "",
        "Best alpha t %.2f (%.2f bp/day). SPA p = %.3f | Reality Check p = %.3f | t >= %.2f (Bonferroni): %d | t >= 3: %d" % (
            rc["best_t"], rc["best_mean_bps"], rc["spa_p"], rc["rc_p"], rc["bonferroni_z"], r["n_bonferroni"], r["n_t3"]),
        us.gate_line(rc),
        "Buy-and-hold Sharpe %.2f; %s candidates beat it (best %.2f)." % (
            r["bh_sharpe_post"], "{:,}".format(r["n_sharpe_over_bh"]), r["best_sharpe"]), "", "By kind:"]
    for k, v in r["by_kind"].items():
        L.append("  %-6s %8s candidates | positive alpha %5.1f%% | t >= 3: %5d | Sharpe > buy-and-hold: %s" % (
            k, "{:,}".format(v["n"]), 100.0 * v["alpha_pos"] / v["n"], v["t3"], "{:,}".format(v["sharpe_over_bh"])))
    L += ["", "Best after %s (with their record before):" % r["is_end"]]
    for b in r["best_post"][:5]:
        L.append("  t %.2f (IS t %5.2f, Sharpe %.2f)  %s %s" % (b["post_t"], b["is_t"], b["sharpe"], b["rule"],
                                                              json.dumps(b["params"], sort_keys=True)))
    L += ["", "The 20 best candidates BEFORE %s averaged t %.2f after it; correlation of t before and after: %.2f." % (
        r["is_end"], r["top_is_mean_post_t"], r["corr_is_post_t"])]
    for b in r["top_is"][:5]:
        L.append("  IS t %.2f -> after t %5.2f  %s %s" % (b["is_t"], b["post_t"], b["rule"],
                                                           json.dumps(b["params"], sort_keys=True)))
    L += ["", "Research, not financial advice."]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description="crypto combination search")
    ap.add_argument("--asset", default="BTC-USD", choices=sorted(IS_ENDS))
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--boot", type=int, default=300)
    ap.add_argument("--write", nargs="?", const="")
    ap.add_argument("--count", action="store_true", help="only count the candidates")
    a = ap.parse_args(argv)
    if a.count:
        A = load_coin(a.asset)
        C = conditions(A, a.asset)
        kinds = {}
        for nm, _, _, _ in candidates(A, C, count_only=True):
            k = nm.split(":")[0]
            kinds[k] = kinds.get(k, 0) + 1
        print("%s: %d conditions, %s candidates %s" % (a.asset, len(C), "{:,}".format(sum(kinds.values())), kinds))
        return 0
    r = search(a.asset, a.boot, a.seed)
    print(report(r))
    if a.write is not None:
        path = a.write or os.path.join(RESULTS, "crypto-%s-latest.json" % a.asset.split("-")[0].lower())
        with open(path, "w") as f:
            json.dump(r, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
