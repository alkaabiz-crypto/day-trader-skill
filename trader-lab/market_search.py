#!/usr/bin/env python3
"""trader-lab multi-market search: ~850,000 daily candidates per market, ~50 million in all.

    python3 market_search.py --list                       # the markets, costs and peers
    python3 market_search.py --count                      # candidates per market and the total
    python3 market_search.py run [--only EURUSD=X,GLD] [--boot 200]
                                                          # each market once; skips finished ones
    python3 market_search.py summary                      # table + the correction across markets

Research script; needs numpy. Method as crypto_search.py and sp500_search.py:
  * signal at the close, filled at the next session's open, COST_BPS[class] per position change,
    T-bill cash, dividend-adjusted prices where Yahoo has them; swaps / overnight financing on CFDs
    are NOT included (they matter for multi-day holds at Exness and must be added before any use)
  * score: Jensen's alpha against buy-and-hold of the same market, beta estimated up to IS_END
  * judged only after IS_END = 2014-12-31
  * per market: Hansen's SPA AND Romano-Wolf studentized max-t over all its candidates (streaming)
  * ACROSS markets: a market's result counts only if it also passes at alpha / number of markets
    (Bonferroni over markets), so 60 markets cannot manufacture a winner either
Candidates (from crypto_search.candidates): each condition alone, every AND pair and every
"A and not B" pair, long-while / long-unless / short-while, several holds; and entries with
take-profit x stop x time exits. Research, not financial advice.
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
import crypto_search as cs  # noqa: E402
from sp500_search import aligned, trend, pct_rank  # noqa: E402

OUT = os.path.join(HERE, "results", "markets")
IS_END = "2014-12-31"
START = "2000-01-01"
COST_BPS = {"fx": 1.0, "fx_cross": 2.0, "index": 2.0, "metal": 3.0, "commodity": 5.0, "stock": 3.0}
FX = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "USDCHF=X", "NZDUSD=X"]
FX_CROSS = ["EURJPY=X", "GBPJPY=X", "EURGBP=X", "AUDJPY=X", "EURCHF=X", "EURAUD=X", "GBPCHF=X"]
METALS = ["GLD", "SLV", "PPLT"]
COMMODITIES = ["CPER", "UNG", "DBA", "DBC"]
INDICES = ["^GDAXI", "^FTSE", "^N225", "^HSI", "^AXJO", "^FCHI", "^STOXX50E", "IWM"]
STOCKS = ["AAPL", "MSFT", "AMZN", "GOOGL", "NVDA", "TSLA", "JPM", "XOM", "JNJ", "PG", "KO", "PFE", "WMT",
          "INTC", "CSCO", "ORCL", "BAC", "GE", "IBM", "CVX", "MRK", "PEP", "DIS", "HD", "MCD", "BA", "CAT",
          "NFLX", "AMD", "COST", "UNH", "LLY"]
CROSS = ["SPY", "QQQ", "^VIX", "UUP", "GLD", "^TNX", "^IRX", "HYG", "IEF", "TLT", "CL=F", "HG=F"]


def markets():
    """symbol -> (class, cost in bp, peer symbol)."""
    M = {}
    for s in FX:
        M[s] = ("fx", COST_BPS["fx"], "USD")
    for s in FX_CROSS:
        M[s] = ("fx_cross", COST_BPS["fx_cross"], "USD")
    for s in METALS:
        M[s] = ("metal", COST_BPS["metal"], "USD")
    for s in COMMODITIES:
        M[s] = ("commodity", COST_BPS["commodity"], "USD")
    for s in INDICES:
        M[s] = ("index", COST_BPS["index"], "SPY")
    for s in STOCKS:
        M[s] = ("stock", COST_BPS["stock"], "QQQ" if s in ("AAPL", "MSFT", "AMZN", "GOOGL", "NVDA", "TSLA", "INTC",
                                                         "CSCO", "ORCL", "IBM", "NFLX", "AMD") else "SPY")
    return M


def usd_index(d):
    """The ICE dollar index rebuilt from its formula (SEK, 4.2% of it, left out and the rest renormalised)."""
    w = {"EURUSD=X": -0.576, "USDJPY=X": 0.136, "GBPUSD=X": -0.119, "USDCAD=X": 0.091, "USDCHF=X": 0.036}
    tot = sum(abs(x) for x in w.values())
    out = np.zeros(len(d))
    for s, e in w.items():
        out += e / tot * np.log(aligned(s, d))
    return np.exp(out)


NON_US_CLOSE = {"^GDAXI", "^FTSE", "^N225", "^HSI", "^AXJO", "^FCHI", "^STOXX50E"}


def lags(sym):
    """How many days to lag outside series so each is known at this market's close (no look-ahead).
    US series (SPY, VIX, rates, US ETFs, 16:00 New York) close after European and Asian indices;
    Yahoo's FX bars (the dollar index) close around 19:00 New York, after every US market."""
    cls = markets()[sym][0]
    return {"us": 1 if sym in NON_US_CLOSE else 0, "fx": 0 if cls.startswith("fx") else 1}


def series(sym, d, lag):
    if sym == "USD":
        x = usd_index(d)
        k = lag["fx"]
    else:
        x = aligned(sym, d)
        k = lag["us"]
    return us.shift(x, k) if k else x


def load_market(sym):
    D = daily.load(sym)
    if not D:
        raise SystemExit("no data for %s: run daily.py fetch --symbols %s" % (sym, sym))
    k = next((i for i, d in enumerate(D["d"]) if d >= START), 0)
    c = np.array(D["c"][k:], float)
    a = np.array((D.get("a") or D["c"])[k:], float)
    f = a / c
    dates = D["d"][k:]
    keep = np.isfinite(a) & np.isfinite(np.array(D["o"][k:], float)) & (np.array(D["o"][k:], float) > 0)
    irx = daily.load("^IRX")
    rf = np.zeros(len(dates))
    if irx:
        m = dict(zip(irx["d"], irx["c"]))
        last = 0.0
        for i, d in enumerate(dates):
            last = m.get(d, last)
            rf[i] = last / 100.0 / 252.0
    A = {"d": dates, "o": np.array(D["o"][k:], float) * f, "h": np.array(D["h"][k:], float) * f,
         "l": np.array(D["l"][k:], float) * f, "c": a, "v": np.nan_to_num(np.array(D["v"][k:], float)), "rf": rf}
    idx = np.flatnonzero(keep)
    return {key: ([v[i] for i in idx] if key == "d" else v[idx]) for key, v in A.items()}


def conditions(A, peer, lag=None):
    """name -> boolean array known at the close. Trading-day windows (252 a year)."""
    d, o, h, l, c, v = A["d"], A["o"], A["h"], A["l"], A["c"], A["v"]
    C = {}
    lag = lag or {"us": 0, "fx": 0}

    def X(sym):
        return series(sym, d, lag)

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
    for n in (5, 10, 20, 50, 100, 150, 200, 250):
        m = us.sma(c, n)
        C["c>ma%d" % n], C["c<ma%d" % n] = c > m, c < m
    m200 = us.sma(c, 200)
    ratio200 = c / m200
    for x in (5, 10, 20):
        C["c>ma200+%d%%" % x] = ratio200 > 1 + x / 100.0
    for x in (5, 10, 20):
        C["c<ma200-%d%%" % x] = ratio200 < 1 - x / 100.0
    for f, s in ((5, 20), (10, 50), (20, 50), (20, 100), (50, 200), (5, 21)):
        mf, ms = us.sma(c, f), us.sma(c, s)
        C["ma%d>ma%d" % (f, s)], C["ma%d<ma%d" % (f, s)] = mf > ms, mf < ms
    for n in (1, 2, 3, 5, 10, 15, 21, 42, 63, 126, 189, 252):
        rr = trend(c, n)
        C["ret%d>0" % n], C["ret%d<0" % n] = rr > 0, rr < 0
    ret = np.diff(np.log(c), prepend=np.log(c[0]))
    sd60 = cs.rolling_std(ret, 60)
    r1, r5 = trend(c, 1), trend(c, 5)
    C["ret1>2sd"], C["ret1<-2sd"], C["ret1>3sd"], C["ret1<-3sd"] = r1 > 2 * sd60, r1 < -2 * sd60, r1 > 3 * sd60, r1 < -3 * sd60
    C["ret5>2sd"], C["ret5<-2sd"] = r5 > 2 * sd60 * math.sqrt(5), r5 < -2 * sd60 * math.sqrt(5)
    r21 = trend(c, 21)
    C["ret21>2sd"], C["ret21<-2sd"] = r21 > 2 * sd60 * math.sqrt(21), r21 < -2 * sd60 * math.sqrt(21)
    for n in (5, 20, 50, 100, 252):
        C["high%d" % n] = c >= us.rolling_max(c, n)
        C["low%d" % n] = c <= us.rolling_min(c, n)
    up = np.diff(c, prepend=c[0]) > 0
    dn = np.diff(c, prepend=c[0]) < 0
    for k in (2, 3, 4, 5):
        C["down%d" % k], C["up%d" % k] = cs.streak(dn, k), cs.streak(up, k)
    ibs = (c - l) / np.maximum(h - l, 1e-12)
    C["ibs<0.2"], C["ibs>0.8"] = ibs < 0.2, ibs > 0.8
    rng = (h - l) / c
    avg_rng = us.sma(rng, 20)
    C["wide_range"], C["narrow_range"] = rng > 2 * avg_rng, rng < 0.5 * avg_rng
    C["inside_day"] = (h < us.shift(h)) & (l > us.shift(l))
    gap = o / us.shift(c) - 1
    C["gapdown"], C["gapup"] = gap < -sd60, gap > sd60
    rv20 = cs.rolling_std(ret, 20) * math.sqrt(252)
    rv60 = sd60 * math.sqrt(252)
    from numpy.lib.stride_tricks import sliding_window_view
    med = np.full(len(c), np.nan)
    if len(c) >= 252:
        med[251:] = np.nanmedian(sliding_window_view(rv20, 252), axis=1)
    C["rv_high"], C["rv_low"], C["rv_rising"], C["rv_falling"] = rv20 > med, rv20 < med, rv20 > rv60, rv20 < rv60
    rvp = pct_rank(rv20, 252)
    C["rv_pct>90"], C["rv_pct<10"] = rvp > 0.9, rvp < 0.1
    hi252 = us.rolling_max(c, 252)
    C["near52wHigh"], C["dd252>10%"], C["dd252>20%"], C["dd252>40%"] = (
        c >= 0.97 * hi252, c <= 0.9 * hi252, c <= 0.8 * hi252, c <= 0.6 * hi252)
    ath = np.maximum.accumulate(c)
    C["at_ath"] = c >= ath
    if v.max() > 0:
        av20 = us.sma(v, 20)
        C["vol>2x"], C["vol<0.5x"], C["vol_rising"] = v > 2 * av20, v < 0.5 * av20, us.sma(v, 5) > av20
        C["up_on_vol"], C["down_on_vol"] = (r1 > 0) & (v > 1.5 * av20), (r1 < 0) & (v > 1.5 * av20)
    m20, s20 = us.sma(c, 20), cs.rolling_std(c, 20)
    C["c>bb_upper"], C["c<bb_lower"] = c > m20 + 2 * s20, c < m20 - 2 * s20
    macd = us.ema(c, 12) - us.ema(c, 26)
    sig = us.ema(macd, 9)
    C["macd>signal"], C["macd<signal"], C["macd>0"], C["macd<0"] = macd > sig, macd < sig, macd > 0, macd < 0
    lo14, hi14 = us.rolling_min(l, 14), us.rolling_max(h, 14)
    k14 = (c - lo14) / np.maximum(hi14 - lo14, 1e-12)
    C["stoch<20"], C["stoch>80"] = k14 < 0.2, k14 > 0.8
    C["pullback5_in_uptrend"] = (c / us.rolling_max(c, 20) < 0.95) & (c > m200)
    C["pullback_rsi_uptrend"] = (r2 < 10) & (c > m200)                          # Connors-style

    pe = X(peer)
    C["peer>ma50"], C["peer<ma50"] = pe > us.sma(pe, 50), pe < us.sma(pe, 50)
    C["peer_ret5>0"], C["peer_ret5<0"] = trend(pe, 5) > 0, trend(pe, 5) < 0
    C["peer_ret1>0"], C["peer_ret1<0"] = trend(pe, 1) > 0, trend(pe, 1) < 0
    rel = c / pe
    C["rel_peer_up20"], C["rel_peer_down20"] = trend(rel, 20) > 0, trend(rel, 20) < 0
    C["rel_peer>ma50"] = rel > us.sma(rel, 50)

    spy, qqq = X("SPY"), X("QQQ")
    C["spy>ma200"], C["spy<ma200"] = spy > us.sma(spy, 200), spy < us.sma(spy, 200)
    C["spy_ret5>0"], C["spy_ret5<0"] = trend(spy, 5) > 0, trend(spy, 5) < 0
    C["spy_ret1>0"], C["spy_ret1<0"] = trend(spy, 1) > 0, trend(spy, 1) < 0
    C["qqq_up21"], C["qqq_down21"] = trend(qqq, 21) > 0, trend(qqq, 21) < 0
    vix = X("^VIX")
    C["vix>20"], C["vix>30"], C["vix<15"] = vix > 20, vix > 30, vix < 15
    vch = vix / us.shift(vix) - 1
    C["vix_jump10"], C["vix_drop10"] = vch > 0.10, vch < -0.10
    vp = pct_rank(vix, 252)
    C["vix_pct>80"], C["vix_pct<20"] = vp > 0.8, vp < 0.2
    usd, gld = X("USD"), X("GLD")
    C["usd_up21"], C["usd_down21"] = trend(usd, 21) > 0, trend(usd, 21) < 0
    C["gold_up21"], C["gold_down21"] = trend(gld, 21) > 0, trend(gld, 21) < 0
    C["gld>ma200"] = gld > us.sma(gld, 200)
    tnx, irx = X("^TNX"), X("^IRX")
    C["10y_up21"], C["10y_down21"] = tnx - us.shift(tnx, 21) > 0, tnx - us.shift(tnx, 21) < 0
    C["3m_up63"], C["3m_down63"] = irx - us.shift(irx, 63) > 0, irx - us.shift(irx, 63) < 0
    C["curve_inverted"] = tnx - irx < 0
    hyg, ief, tlt = X("HYG"), X("IEF"), X("TLT")
    C["hyg_ief_up21"], C["hyg_ief_down21"] = trend(hyg / ief, 21) > 0, trend(hyg / ief, 21) < 0
    C["tlt_up21"], C["tlt_down21"] = trend(tlt, 21) > 0, trend(tlt, 21) < 0
    oil, cu = X("CL=F"), X("HG=F")
    C["oil_up10"], C["oil_down10"] = trend(oil, 21) > 0.10, trend(oil, 21) < -0.10
    C["copper_gold_up21"], C["copper_gold_down21"] = trend(cu / gld, 21) > 0, trend(cu / gld, 21) < 0

    dt = [datetime.date(*map(int, x.split("-"))) for x in d]
    nxt = []
    for i in range(len(dt)):                       # the next session (holidays are known in advance)
        if i + 1 < len(dt):
            nxt.append(dt[i + 1])
        else:
            x = dt[i] + datetime.timedelta(days=1)
            while x.weekday() >= 5:
                x += datetime.timedelta(days=1)
            nxt.append(x)
    wd = np.array([x.weekday() for x in nxt])
    mo = np.array([x.month for x in nxt])
    for k in range(5):
        C["next_wd%d" % k] = wd == k
    for m in range(1, 13):
        C["next_m%d" % m] = mo == m
    C["halloween"] = np.isin(mo, [11, 12, 1, 2, 3, 4])
    last_day = np.array([i + 1 < len(dt) and nxt[i].month != dt[i].month for i in range(len(dt))])
    first3 = np.zeros(len(dt), bool)
    k = 0
    for i in range(len(dt)):
        k = 1 if i == 0 or dt[i].month != dt[i - 1].month else k + 1
        first3[i] = k <= 2
    C["turn_of_month"] = last_day | first3
    C["mid_month"] = np.array([10 <= x.day <= 20 for x in nxt])
    C["opex_week"] = np.array([15 <= x.day <= 21 for x in nxt])
    gaps = np.array([(nxt[i] - dt[i]).days for i in range(len(dt))])
    C["pre_holiday"] = ((gaps >= 2) & (np.array([x.weekday() for x in dt]) < 4)) | (gaps >= 4)
    for y in range(4):
        C["pres_y%d" % (y if y else 4)] = np.array([x.year % 4 == y for x in nxt])
    return {key: np.nan_to_num(np.asarray(val, float)) > 0 for key, val in C.items()}


def search_market(sym, boot=200, seed=7, chunk=20000):
    cls, cost, peer = markets()[sym]
    t0 = time.time()
    A = load_market(sym)
    C = conditions(A, peer, lags(sym))
    bh = us.returns_for(A, np.ones(len(A["c"])), cost, 0.0)
    dates = np.array(A["d"])
    post, pre = dates > IS_END, dates <= IS_END
    rf = A["rf"]
    bh_x = bh - rf
    bi = bh_x[pre]
    vbh = np.var(bi, ddof=1)
    gate = cs.StreamingGate(int(post.sum()), boot, seed=seed)
    names, params, is_t, post_t, post_mean, sharpe = [], [], [], [], [], []
    buf = []
    for name, p, kind, payload in cs.candidates(A, C):
        r = us.returns_for(A, payload, cost, 0.0) if kind == "pos" else \
            us.returns_exit(A, payload[0], payload[1], cost, 0.0)
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
        sharpe.append(xp.mean() / xp.std() * math.sqrt(252) if xp.std() > 0 else 0.0)
        buf.append(ep)
        if len(buf) >= chunk:
            gate.add(np.vstack(buf))
            buf = []
            print("  %s %d candidates (%.0fs)" % (sym, len(names), time.time() - t0), file=sys.stderr, flush=True)
    if buf:
        gate.add(np.vstack(buf))
    rc = gate.result()
    n_mk = len(markets())
    across = us.gate(np.concatenate(gate.tstat), gate.sb, rc["spa_p"], alpha=0.05 / n_mk)
    rc["across_markets"] = {"alpha": 0.05 / n_mk, **across}
    is_t, post_t, post_mean, sharpe = map(np.array, (is_t, post_t, post_mean, sharpe))
    bh_sh = bh_x[post].mean() / bh_x[post].std() * math.sqrt(252)
    top_is = np.argsort(-is_t)[:20]

    def row(i):
        return {"rule": names[i], "params": params[i], "post_t": float(post_t[i]), "is_t": float(is_t[i]),
                "alpha_bp_day": float(post_mean[i]), "sharpe": float(sharpe[i])}

    return {"asset": sym, "class": cls, "peer": peer, "cost_bps": cost, "is_end": IS_END, "first_day": A["d"][0],
            "candidates": len(names), "conditions": len(C), "days_post": int(post.sum()), "days_pre": int(pre.sum()),
            "bh_sharpe_post": float(bh_sh), "reality_check": rc, "n_t3": int((post_t >= 3).sum()),
            "n_bonferroni": int((post_t >= rc["bonferroni_z"]).sum()),
            "n_sharpe_over_bh": int((sharpe > bh_sh).sum()), "best_sharpe": float(sharpe.max()),
            "share_positive_post": float((post_t > 0).mean()),
            "best_post": [row(i) for i in np.argsort(-post_t)[:10]], "top_is": [row(i) for i in top_is],
            "top_is_mean_post_t": float(post_t[top_is].mean()),
            "corr_is_post_t": float(np.corrcoef(is_t, post_t)[0, 1]), "seconds": round(time.time() - t0)}


def path_for(sym):
    return os.path.join(OUT, sym.replace("^", "IDX_").replace("=", "_") + ".json")


def locked(lock):
    """True while the runner that wrote the lock is alive (a stopped runner's lock is ignored)."""
    try:
        pid = int(open(lock).read().strip() or 0)
        os.kill(pid, 0)
        return pid != os.getpid()
    except (OSError, ValueError):
        return False


def run(only=None, boot=200, seed=7):
    os.makedirs(OUT, exist_ok=True)
    for sym in markets():
        if only and sym not in only:
            continue
        p = path_for(sym)
        if os.path.exists(p) or locked(p + ".lock"):
            continue
        with open(p + ".lock", "w") as f:                      # lets several runners share the queue
            f.write(str(os.getpid()))
        try:
            r = search_market(sym, boot, seed)
            with open(p, "w") as f:
                json.dump(r, f, indent=1)
            rc = r["reality_check"]
            print("%-10s %8s cand | best t %.2f | SPA p %.3f | RC p %.3f | RW above %d | %s | %ds" % (
                sym, "{:,}".format(r["candidates"]), rc["best_t"], rc["spa_p"], rc["rc_p"], rc["rw_rejects"],
                "PASS" if rc["passes"] else "no pass", r["seconds"]), flush=True)
        finally:
            os.remove(p + ".lock")


def summary():
    rows = []
    for sym in markets():
        p = path_for(sym)
        if os.path.exists(p):
            rows.append(json.load(open(p)))
    L = ["Multi-market search: %d of %d markets done, %s candidates. Judged after %s; Jensen's alpha vs buy-and-hold." % (
        len(rows), len(markets()), "{:,}".format(sum(r["candidates"] for r in rows)), IS_END), "",
        "%-10s %-9s %9s  %6s %6s %6s %5s %8s  %s" % ("market", "class", "cand", "best t", "SPA p", "RC p", "t>=3",
                                                     "IS->OOS", "verdict (per market | across markets)")]
    for r in rows:
        rc = r["reality_check"]
        L.append("%-10s %-9s %9s  %6.2f %6.3f %6.3f %5d %8.2f  %s | %s" % (
            r["asset"], r["class"], "{:,}".format(r["candidates"]), rc["best_t"], rc["spa_p"], rc["rc_p"], r["n_t3"],
            r["top_is_mean_post_t"], "PASS" if rc["passes"] else "no", "PASS" if rc["across_markets"]["passes"] else "no"))
    passed = [r for r in rows if r["reality_check"]["across_markets"]["passes"]]
    L += ["", "Markets passing after the correction across markets: %d" % len(passed)]
    for r in passed:
        b = r["best_post"][0]
        L.append("  %s: %s %s (t %.2f after, IS t %.2f)" % (r["asset"], b["rule"], json.dumps(b["params"]), b["post_t"], b["is_t"]))
    L += ["", "IS->OOS = how the 20 best candidates before 2015 did after 2014 (mean t). Swaps are not included.",
          "Research, not financial advice."]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description="multi-market combination search")
    ap.add_argument("cmd", nargs="?", default="summary", choices=["run", "summary"])
    ap.add_argument("--only", type=lambda s: [x.strip() for x in s.split(",") if x.strip()])
    ap.add_argument("--boot", type=int, default=200)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--count", action="store_true")
    a = ap.parse_args(argv)
    if a.list:
        for s, (cls, cost, peer) in markets().items():
            print("%-10s %-9s %.0f bp  peer %s" % (s, cls, cost, peer))
        return 0
    if a.count:
        total = 0
        for s, (cls, cost, peer) in markets().items():
            if a.only and s not in a.only:
                continue
            A = load_market(s)
            C = conditions(A, peer, lags(s))
            n = sum(1 for _ in cs.candidates(A, C, count_only=True))
            total += n
            print("%-10s %s days from %s, %d conditions, %s candidates" % (s, len(A["d"]), A["d"][0], len(C),
                                                                           "{:,}".format(n)), flush=True)
        print("TOTAL %s candidates" % "{:,}".format(total))
        return 0
    if a.cmd == "run":
        run(a.only, a.boot, a.seed)
    else:
        print(summary())
    return 0


if __name__ == "__main__":
    sys.exit(main())
