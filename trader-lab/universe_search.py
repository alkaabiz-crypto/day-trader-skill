#!/usr/bin/env python3
"""trader-lab universe search: thousands of technical trading rules, tested together with the
data-snooping corrections they need.

    python3 universe_search.py                    # all rules, all assets, Reality Check + SPA
    python3 universe_search.py --assets SPY,USO --boot 300 --json

Research script: needs numpy (pip install numpy). The trading skills themselves stay stdlib-only.

The rule universe
  The five families of Sullivan, Timmermann & White (1999, Journal of Finance, "Data-Snooping,
  Technical Trading Rule Performance, and the Bootstrap"): filter rules, moving-average crossovers,
  support/resistance (trading range) breaks, channel breakouts and on-balance-volume crossovers,
  each with bands, delays and fixed holding periods; plus the classic oscillators and indicators
  (RSI, Stochastic %K, CCI, MACD, Bollinger Bands, rate of change, ADX/DI, Keltner, Donchian,
  IBS, streaks, calendar). Each rule is run long/flat and long/short.

Execution (realistic)
  A position decided at the close of day t is entered at the open of t+1; the overnight move
  belongs to the old position. Costs are charged per unit of position change (2 bps ETFs, 5 bps
  oil funds), plus 1 bp per night of oil exposure (CFD financing). Prices are dividend-adjusted.

The statistics
  Each rule's daily return is compared with buy-and-hold on the same asset (excess return). On
  everything after 2014 (never used to build the universe):
    * White's Reality Check (2000): is the best rule's mean excess return larger than the best of
      M luckless rules would be? Stationary bootstrap (Politis & Romano 1994), mean block 10 days.
    * Hansen's SPA test (2005): the studentized, less conservative version.
    * A Bonferroni bar on each rule's t-stat for M tests.
  Also: the top 20 rules chosen on data to 2014, and how they did after 2014 (the decay test).
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

ASSETS = ["SPY", "QQQ", "IWM", "DIA", "USO", "BNO"]
OIL = {"USO", "BNO"}
IS_END = "2014-12-31"
RESULTS = os.path.join(HERE, "results")


# ---------------------------------------------------------------- data

def load_asset(sym):
    D = daily.load(sym)
    if not D or not D.get("a"):
        raise SystemExit("no dividend-adjusted data for %s: run daily.py fetch --symbols %s" % (sym, sym))
    k = next((i for i, d in enumerate(D["d"]) if d >= "1996-01-01"), 0)
    c = np.array(D["c"][k:], float)
    a = np.array(D["a"][k:], float)
    f = a / c
    dates = D["d"][k:]
    irx = daily.load("^IRX")
    rf = np.zeros(len(dates))
    if irx:
        m = dict(zip(irx["d"], irx["c"]))
        last = 0.0
        for i, d in enumerate(dates):
            last = m.get(d, last)
            rf[i] = last / 100.0 / 252.0          # 13-week T-bill, per trading day
    return {"d": dates, "o": np.array(D["o"][k:]) * f, "h": np.array(D["h"][k:]) * f,
            "l": np.array(D["l"][k:]) * f, "c": a, "v": np.array(D["v"][k:], float), "rf": rf}


# ---------------------------------------------------------------- vector helpers

def sma(x, n):
    out = np.full(len(x), np.nan)
    if n <= len(x):
        cs = np.cumsum(np.insert(x, 0, 0.0))
        out[n - 1:] = (cs[n:] - cs[:-n]) / n
    return out


def ema(x, n):
    out = np.empty(len(x))
    k = 2.0 / (n + 1)
    e = x[0]
    for i, v in enumerate(x):
        e = v if i == 0 else e + k * (v - e)
        out[i] = e
    return out


def rolling_max(x, n):
    from numpy.lib.stride_tricks import sliding_window_view
    out = np.full(len(x), np.nan)
    if n <= len(x):
        out[n - 1:] = sliding_window_view(x, n).max(axis=1)
    return out


def rolling_min(x, n):
    from numpy.lib.stride_tricks import sliding_window_view
    out = np.full(len(x), np.nan)
    if n <= len(x):
        out[n - 1:] = sliding_window_view(x, n).min(axis=1)
    return out


def shift(x, k=1):
    out = np.full(len(x), np.nan)
    out[k:] = x[:-k]
    return out


def ffill_state(enter, leave):
    """Boolean entry/exit events -> 0/1 state (enter has priority on ties), held until an exit."""
    ev = np.where(enter, 1.0, np.where(leave, 0.0, np.nan))
    idx = np.where(~np.isnan(ev), np.arange(len(ev)), 0)
    np.maximum.accumulate(idx, out=idx)
    st = ev[idx]
    st[np.isnan(st)] = 0.0
    return st


def ffill_pos(long_ev, short_ev):
    """Events -> +1 / -1 positions held until the opposite event (0 before the first)."""
    ev = np.where(long_ev, 1.0, np.where(short_ev, -1.0, np.nan))
    idx = np.where(~np.isnan(ev), np.arange(len(ev)), 0)
    np.maximum.accumulate(idx, out=idx)
    st = ev[idx]
    st[np.isnan(st)] = 0.0
    return st


def hold_for(event, c):
    """1 on the c days starting with each event (fixed holding period)."""
    e = np.nan_to_num(event.astype(float))
    cs = np.cumsum(np.insert(e, 0, 0.0))
    n = len(e)
    lo = np.maximum(np.arange(n) - c + 1, 0)
    return ((cs[np.arange(n) + 1] - cs[lo]) > 0).astype(float)


def delay(sig, d):
    """A crossing must persist d days: position changes only after d equal readings."""
    if d <= 1:
        return sig
    from numpy.lib.stride_tricks import sliding_window_view
    out = np.full(len(sig), np.nan)
    w = sliding_window_view(sig, d)
    same = (w == w[:, :1]).all(axis=1)
    out[d - 1:] = np.where(same, w[:, -1], np.nan)
    idx = np.where(~np.isnan(out), np.arange(len(out)), 0)
    np.maximum.accumulate(idx, out=idx)
    res = out[idx]
    res[np.isnan(res)] = 0.0
    return res


# ---------------------------------------------------------------- the rule universe
# Each generator yields (name, params, signal) with signal in {-1, 0, +1} decided at the close.
# "dir" signals are +1/-1 (long/short); the runner derives the long/flat version as max(sig, 0).

FAST = [1, 2, 5, 10, 15, 20, 25, 30, 40, 50, 75, 100, 125, 150, 200]
SLOW = [2, 5, 10, 15, 20, 25, 30, 40, 50, 75, 100, 125, 150, 200, 250]
BANDS = [0.0, 0.001, 0.005, 0.01, 0.015, 0.02, 0.03, 0.04, 0.05]


def g_ma(A):
    c = A["c"]
    cache = {n: (c if n == 1 else sma(c, n)) for n in sorted(set(FAST + SLOW))}
    for f in FAST:
        for s in SLOW:
            if f >= s:
                continue
            fa, sl = cache[f], cache[s]
            for b in BANDS:
                sig = ffill_pos(fa > sl * (1 + b), fa < sl * (1 - b))
                yield "ma", {"f": f, "s": s, "b": b}, sig
            base = ffill_pos(fa > sl, fa < sl)
            for d in (2, 3, 4, 5):
                yield "ma", {"f": f, "s": s, "d": d}, delay(base, d)
            up = (fa > sl) & ~(shift(fa) > shift(sl))
            for hc in (5, 10, 25, 50):
                yield "ma", {"f": f, "s": s, "hold": hc}, hold_for(up, hc)


def g_obv(A):
    c, v = A["c"], A["v"]
    obv = np.cumsum(np.sign(np.diff(c, prepend=c[0])) * v)
    cache = {n: (obv if n == 1 else sma(obv, n)) for n in sorted(set(FAST + SLOW))}
    for f in FAST:
        for s in SLOW:
            if f >= s:
                continue
            for b in (0.0, 0.01, 0.05):
                fa, sl = cache[f], cache[s]
                yield "obv", {"f": f, "s": s, "b": b}, ffill_pos(fa > sl + b * np.abs(sl), fa < sl - b * np.abs(sl))


SR_N = [5, 10, 15, 20, 25, 50, 100, 150, 200, 250]


def g_sr(A):
    c = A["c"]
    for n in SR_N:
        hi, lo = shift(rolling_max(c, n)), shift(rolling_min(c, n))
        for b in BANDS:
            up, dn = c > hi * (1 + b), c < lo * (1 - b)
            yield "sr", {"n": n, "b": b}, ffill_pos(up, dn)
            for hc in (1, 5, 10, 25, 50):
                yield "sr", {"n": n, "b": b, "hold": hc}, hold_for(up, hc) - hold_for(dn, hc)


def g_cb(A):
    c = A["c"]
    for n in SR_N:
        hi, lo = shift(rolling_max(c, n)), shift(rolling_min(c, n))
        width = (hi - lo) / lo
        for x in (0.01, 0.02, 0.03, 0.05, 0.075, 0.10, 0.15):
            chan = width < x
            for b in (0.0, 0.005, 0.01, 0.02, 0.03, 0.05):
                up = chan & (c > hi * (1 + b))
                dn = chan & (c < lo * (1 - b))
                for hc in (1, 5, 10, 25, 50):
                    yield "cb", {"n": n, "x": x, "b": b, "hold": hc}, hold_for(up, hc) - hold_for(dn, hc)


def g_filter(A):
    c = A["c"]
    xs = [0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.045, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10,
          0.12, 0.14, 0.16, 0.18, 0.20, 0.25, 0.30]
    cl = c.tolist()
    for x in xs:
        for y in (None, 0.5, 0.75):
            ex = x if y is None else x * y
            pos = np.zeros(len(cl))
            state, ext = 0, cl[0]
            for i, p in enumerate(cl):
                if state <= 0:
                    ext = min(ext, p)
                    if p >= ext * (1 + x):
                        state, ext = 1, p
                else:
                    ext = max(ext, p)
                    if p <= ext * (1 - ex):
                        state, ext = -1, p
                pos[i] = state
            yield "filter", {"x": x, "exit": ex}, pos
            for hc in (5, 10, 25, 50):
                entry = (pos == 1) & (shift(pos) != 1)
                yield "filter", {"x": x, "exit": ex, "hold": hc}, hold_for(entry, hc)


def rsi_np(c, n):
    d = np.diff(c, prepend=c[0])
    up, dn = np.maximum(d, 0), np.maximum(-d, 0)
    au, ad = np.empty(len(c)), np.empty(len(c))
    a_u = a_d = 0.0
    for i in range(len(c)):
        if i < n:
            a_u += up[i] / n
            a_d += dn[i] / n
        else:
            a_u = (a_u * (n - 1) + up[i]) / n
            a_d = (a_d * (n - 1) + dn[i]) / n
        au[i], ad[i] = a_u, a_d
    r = np.where(ad == 0, 100.0, 100 - 100 / (1 + au / np.where(ad == 0, 1, ad)))
    r[:n] = np.nan
    return r


def g_osc(A):
    o, h, l, c = A["o"], A["h"], A["l"], A["c"]
    LO = [5, 10, 15, 20, 25, 30, 35]
    HI = [65, 70, 75, 80, 85, 90, 95]
    for n in (2, 3, 4, 5, 7, 9, 14, 21):
        r = rsi_np(c, n)
        for lo in LO:
            for hi in HI:
                yield "rsi_rev", {"n": n, "lo": lo, "hi": hi}, ffill_state(r < lo, r > hi)
                yield "rsi_mom", {"n": n, "lo": lo, "hi": hi}, ffill_state(r > hi, r < lo)
    for n in (5, 9, 14, 21):
        k = sma(100 * (c - rolling_min(l, n)) / np.maximum(rolling_max(h, n) - rolling_min(l, n), 1e-12), 3)
        for lo in (10, 20, 30):
            for hi in (70, 80, 90):
                yield "stoch_rev", {"n": n, "lo": lo, "hi": hi}, ffill_state(k < lo, k > hi)
                yield "stoch_mom", {"n": n, "lo": lo, "hi": hi}, ffill_state(k > hi, k < lo)
    tp = (h + l + c) / 3
    for n in (10, 14, 20, 40):
        m = sma(tp, n)
        from numpy.lib.stride_tricks import sliding_window_view
        md = np.full(len(tp), np.nan)
        w = sliding_window_view(tp, n)
        md[n - 1:] = np.abs(w - w.mean(axis=1, keepdims=True)).mean(axis=1)
        cci = (tp - m) / (0.015 * np.maximum(md, 1e-12))
        for t in (50, 100, 150, 200):
            yield "cci_rev", {"n": n, "t": t}, ffill_state(cci < -t, cci > 0)
            yield "cci_mom", {"n": n, "t": t}, ffill_pos(cci > t, cci < -t)
    for fa, sl, sg in ((5, 35, 5), (8, 17, 9), (12, 26, 9), (19, 39, 9), (3, 10, 16), (6, 13, 5)):
        macd = ema(c, fa) - ema(c, sl)
        sig = ema(macd, sg)
        yield "macd", {"f": fa, "s": sl, "sig": sg, "use": "cross"}, ffill_pos(macd > sig, macd < sig)
        yield "macd", {"f": fa, "s": sl, "sig": sg, "use": "zero"}, ffill_pos(macd > 0, macd < 0)
        hist = macd - sig
        yield "macd", {"f": fa, "s": sl, "sig": sg, "use": "slope"}, ffill_pos(hist > shift(hist), hist < shift(hist))
    for n in (10, 20, 30, 50):
        m = sma(c, n)
        from numpy.lib.stride_tricks import sliding_window_view
        sd = np.full(len(c), np.nan)
        sd[n - 1:] = sliding_window_view(c, n).std(axis=1)
        for k in (1.0, 1.5, 2.0, 2.5, 3.0):
            yield "bb_rev", {"n": n, "k": k}, ffill_state(c < m - k * sd, c > m)
            yield "bb_brk", {"n": n, "k": k}, ffill_state(c > m + k * sd, c < m)
    for n in list(range(1, 21)) + [25, 30, 40, 50, 63, 100, 126, 189, 252]:
        roc = c / shift(c, n) - 1
        for t in (0.0, 0.01, 0.02):
            yield "roc_mom", {"n": n, "t": t}, ffill_pos(roc > t, roc < -t)
            if n <= 20:
                yield "roc_rev", {"n": n, "t": t}, ffill_pos(roc < -t, roc > t)
    tr = np.maximum(h - l, np.maximum(np.abs(h - shift(c)), np.abs(l - shift(c))))
    tr[0] = h[0] - l[0]
    upm, dnm = h - shift(h), shift(l) - l
    pdm = np.where((upm > dnm) & (upm > 0), upm, 0.0)
    ndm = np.where((dnm > upm) & (dnm > 0), dnm, 0.0)
    pdm[0] = ndm[0] = 0.0
    for n in (7, 14, 21, 28):
        atr = ema(tr, 2 * n - 1)
        pdi, ndi = 100 * ema(pdm, 2 * n - 1) / atr, 100 * ema(ndm, 2 * n - 1) / atr
        dx = 100 * np.abs(pdi - ndi) / np.maximum(pdi + ndi, 1e-12)
        adx = ema(dx, 2 * n - 1)
        for t in (15, 20, 25, 30):
            yield "adx", {"n": n, "t": t}, np.where(adx > t, np.where(pdi > ndi, 1.0, -1.0), 0.0)
        for kk in (1.0, 1.5, 2.0, 2.5):
            m = ema(c, n)
            yield "kelt_brk", {"n": n, "k": kk}, ffill_state(c > m + kk * atr, c < m)
            yield "kelt_rev", {"n": n, "k": kk}, ffill_state(c < m - kk * atr, c > m)
    for en in (5, 10, 20, 50, 100, 200):
        for ex in (2, 5, 10, 20, 50):
            if ex >= en:
                continue
            hi, lo = shift(rolling_max(h, en)), shift(rolling_min(l, en))
            exl, exh = shift(rolling_min(l, ex)), shift(rolling_max(h, ex))
            yield "donch", {"en": en, "ex": ex}, ffill_state(c > hi, c < exl) - ffill_state(c < lo, c > exh)
    ibs = (c - l) / np.maximum(h - l, 1e-12)
    for t in (0.1, 0.2, 0.3, 0.4, 0.5):
        yield "ibs", {"t": t, "exit": "next"}, (ibs < t).astype(float)
        yield "ibs", {"t": t, "exit": "ibs>.8"}, ffill_state(ibs < t, ibs > 0.8)
    up = np.diff(c, prepend=c[0]) > 0
    dn = np.diff(c, prepend=c[0]) < 0
    for k in range(1, 8):
        su = np.convolve(up.astype(float), np.ones(k), "full")[:len(c)] >= k
        sd = np.convolve(dn.astype(float), np.ones(k), "full")[:len(c)] >= k
        yield "streak_rev", {"k": k}, np.where(sd, 1.0, np.where(su, -1.0, 0.0))
        yield "streak_mom", {"k": k}, np.where(su, 1.0, np.where(sd, -1.0, 0.0))
    wd = np.array([datetime.date(*map(int, d.split("-"))).weekday() for d in A["d"]])
    mo = np.array([int(d[5:7]) for d in A["d"]])
    for k in range(5):
        # decided at the close of the day BEFORE the chosen weekday: hold that weekday
        yield "dow", {"day": k}, (np.roll(wd, -1) == k).astype(float)
    for m in range(1, 13):
        yield "month", {"m": m}, (np.roll(mo, -1) == m).astype(float)


def entry_events(A):
    """Long entry signals (decided at the close), from the classic setups."""
    o, h, l, c = A["o"], A["h"], A["l"], A["c"]
    ev = {}
    for n in (2, 3, 5, 14):
        r = rsi_np(c, n)
        for lo in (5, 10, 20, 30):
            ev["rsi%d<%d" % (n, lo)] = r < lo
    for n in (10, 20):
        m = sma(c, n)
        from numpy.lib.stride_tricks import sliding_window_view
        sd = np.full(len(c), np.nan)
        sd[n - 1:] = sliding_window_view(c, n).std(axis=1)
        for k in (1.5, 2.0, 2.5):
            ev["bb%d-%.1f" % (n, k)] = c < m - k * sd
    dn = np.diff(c, prepend=c[0]) < 0
    for k in (2, 3, 4, 5):
        ev["down%d" % k] = np.convolve(dn.astype(float), np.ones(k), "full")[:len(c)] >= k
    for n in (10, 20, 55):
        ev["break%d" % n] = c > shift(rolling_max(c, n))
        ev["low%d" % n] = c < shift(rolling_min(c, n))
    for f, s_ in ((5, 20), (10, 50), (20, 100), (50, 200)):
        fa, sl = sma(c, f), sma(c, s_)
        ev["macross%d/%d" % (f, s_)] = (fa > sl) & ~(shift(fa) > shift(sl))
    ibs = (c - l) / np.maximum(h - l, 1e-12)
    for t in (0.1, 0.2):
        ev["ibs<%.1f" % t] = ibs < t
    gap = o / shift(c) - 1
    for x in (0.01, 0.02):
        ev["gapdown%.0f" % (x * 100)] = gap < -x                # known at today's close (gap was this morning)
    m200 = sma(c, 200)
    for name in list(ev):
        ev[name + "&up200"] = ev[name] & (c > m200)            # the same entry, only in an uptrend
    for name in list(ev):
        ev[name] = np.nan_to_num(ev[name].astype(float)) > 0
    return ev


TPS = [None, 0.01, 0.02, 0.03, 0.05, 0.08]
SLS = [None, 0.01, 0.02, 0.03, 0.05, 0.08]
TIMES = [3, 5, 10, 20]


def trade_path(A, entries, tp, sl, T):
    """Non-overlapping long trades: enter at the open after an entry signal; exit at the take-profit,
    the stop-loss (if a day touches both, the STOP is assumed first) or the close of day T.
    -> (position path of 0/1 by session, exit price override {day index: price})."""
    o, h, l, c = A["o"], A["h"], A["l"], A["c"]
    n = len(c)
    pos = np.zeros(n)
    exit_px = {}
    i = 0
    idx = np.flatnonzero(entries)
    k = 0
    while k < len(idx):
        e = idx[k]
        if e + 1 >= n or e < i:
            k += 1
            continue
        start = e + 1
        px = o[start]
        stop = px * (1 - sl) if sl else -np.inf
        targ = px * (1 + tp) if tp else np.inf
        end = min(start + T - 1, n - 1)
        hl = l[start:end + 1] <= stop
        hh = h[start:end + 1] >= targ
        hit = np.flatnonzero(hl | hh)
        if len(hit):
            j = start + hit[0]
            if hl[hit[0]]:
                exit_px[j] = min(stop, o[j]) if j > start else stop
            else:
                exit_px[j] = max(targ, o[j]) if j > start else targ
            end = j
        pos[start:end + 1] = 1.0
        i = end + 1
        k += 1
    return pos, exit_px


def returns_exit(A, pos_session, exit_px, cost_bps, night_bps):
    """Daily returns when pos_session[t] = position during session t (entered at its open) and some
    trades leave intraday at exit_px[t]."""
    o, c = A["o"], A["c"]
    n = len(c)
    prev_s = np.concatenate(([0.0], pos_session[:-1]))
    held_overnight = prev_s * pos_session          # still in the trade overnight into t
    gap = np.concatenate(([0.0], o[1:] / c[:-1] - 1))
    day = c / o - 1
    r = (1 + held_overnight * gap) * (1 + pos_session * day) - 1
    for t, px in exit_px.items():
        r[t] = (1 + held_overnight[t] * gap[t]) * (px / o[t]) - 1
    entries = (pos_session > 0) & (prev_s == 0)
    exits = (pos_session > 0) & ((np.concatenate((pos_session[1:], [0.0])) == 0) | np.isin(np.arange(n), list(exit_px)))
    r = r - (entries + exits) * cost_bps / 2 / 1e4 - held_overnight * night_bps / 1e4
    if "rf" in A:
        r = r + (1 - pos_session) * A["rf"]
    return r


def g_entry_exit(A):
    """Entry signal x take-profit x stop-loss x time stop. Yields precomputed RETURNS (flag 'ret')."""
    for name, ev in entry_events(A).items():
        for tp in TPS:
            for sl in SLS:
                for T in TIMES:
                    pos, ex = trade_path(A, ev, tp, sl, T)
                    yield "ee:" + name, {"tp": tp, "sl": sl, "T": T}, ("ret", pos, ex)


GENERATORS = [g_ma, g_sr, g_cb, g_filter, g_obv, g_osc, g_entry_exit]


# ---------------------------------------------------------------- execution

def returns_for(A, pos, cost_bps, night_bps):
    """Daily returns of a position path (decided at closes) with next-open execution."""
    o, c = A["o"], A["c"]
    p = np.nan_to_num(pos)
    prev = shift(p)
    prev[0] = 0.0
    gap = np.empty(len(c))
    gap[0] = 0.0
    gap[1:] = o[1:] / c[:-1] - 1
    day = c / o - 1
    # day t: the overnight gap belongs to the position from close t-2 (held into t-1's close -> t's open),
    # the session to the new position from close t-1
    pp = shift(prev)
    pp[:2] = 0.0
    # overnight and session returns compound within the day
    r = (1 + pp * gap) * (1 + prev * day) - 1 - np.abs(prev - pp) * cost_bps / 1e4 - np.abs(pp) * night_bps / 1e4
    if "rf" in A:
        r = r + (1 - np.minimum(np.abs(prev), 1.0)) * A["rf"]   # money not in the market earns T-bills
    return r


def stationary_indices(n, B, mean_block, rng):
    """Politis & Romano (1994) stationary bootstrap index matrix (B x n)."""
    p = 1.0 / mean_block
    idx = np.empty((B, n), dtype=np.int64)
    idx[:, 0] = rng.integers(0, n, B)
    jumps = rng.random((B, n)) < p
    fresh = rng.integers(0, n, (B, n))
    for t in range(1, n):
        idx[:, t] = np.where(jumps[:, t], fresh[:, t], (idx[:, t - 1] + 1) % n)
    return idx


def reality_check(E, B=500, block=10, seed=7):
    """E: (M rules x n days) excess returns. -> dict with RC and SPA p-values."""
    M, n = E.shape
    rng = np.random.default_rng(seed)
    means = E.mean(axis=1)
    sd = E.std(axis=1, ddof=1)
    sd[sd == 0] = np.inf
    v = math.sqrt(n) * means.max()
    tstat = math.sqrt(n) * means / sd
    t_spa = max(tstat.max(), 0.0)
    thr = -math.sqrt(2 * math.log(math.log(n)))
    g = np.where(tstat >= thr, means, 0.0)               # Hansen's consistent re-centring
    idx = stationary_indices(n, B, block, rng)
    vb = np.empty(B)
    tb = np.empty(B)
    for b in range(B):
        mb = E[:, idx[b]].mean(axis=1)
        vb[b] = math.sqrt(n) * (mb - means).max()
        tb[b] = max((math.sqrt(n) * (mb - g) / sd).max(), 0.0)
    return {"M": M, "n": n, "best_mean_bps": float(means.max()), "best_t": float(tstat.max()),
            "rc_p": float((vb >= v).mean()), "spa_p": float((tb >= t_spa).mean()),
            "bonferroni_z": float(z_bonferroni(M))}


def z_bonferroni(M, alpha=0.05):
    p = alpha / (2.0 * M)
    lo, hi = 0.0, 10.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if 0.5 * math.erfc(mid / math.sqrt(2)) > p:
            lo = mid
        else:
            hi = mid
    return hi


def search(assets, boot=500, top=20):
    out = {"assets": {}, "is_end": IS_END}
    t0 = time.time()
    for sym in assets:
        A = load_asset(sym)
        oil = sym in OIL
        cost, night = (5.0, 1.0) if oil else (2.0, 0.0)
        bh = returns_for(A, np.ones(len(A["c"])), cost, night)
        dates = np.array(A["d"])
        post = dates > IS_END
        pre = ~post
        rf = A["rf"]
        bh_x = bh - rf                                     # buy-and-hold excess over T-bills
        bh_sharpe_post = bh_x[post].mean() / bh_x[post].std() * math.sqrt(252)
        names, params, ex_post, is_t, post_t, post_mean, sharpe_post = [], [], [], [], [], [], []

        def add(name, p, r):
            x = r - rf
            # Jensen's alpha against buy-and-hold, beta estimated BEFORE 2015 only (no look-ahead)
            xi, bi = x[pre], bh_x[pre]
            beta = float(np.cov(xi, bi)[0, 1] / np.var(bi, ddof=1)) if np.var(bi) > 0 else 0.0
            e = x - beta * bh_x
            ep, ei = e[post], e[pre]
            names.append(name)
            params.append(p)
            ex_post.append(ep.astype(np.float32))
            sdi, sdp = ei.std(ddof=1), ep.std(ddof=1)
            is_t.append(ei.mean() / sdi * math.sqrt(len(ei)) if sdi > 0 else 0.0)
            post_t.append(ep.mean() / sdp * math.sqrt(len(ep)) if sdp > 0 else 0.0)
            post_mean.append(ep.mean() * 1e4)
            xp = x[post]
            sharpe_post.append(xp.mean() / xp.std() * math.sqrt(252) if xp.std() > 0 else 0.0)

        for gen in GENERATORS:
            for name, p, sig in gen(A):
                if isinstance(sig, tuple) and sig[0] == "ret":
                    add(name + "/lf", p, returns_exit(A, sig[1], sig[2], cost, night))
                    continue
                for mode in ("ls", "lf"):
                    pos = sig if mode == "ls" else np.maximum(sig, 0.0)
                    add(name + "/" + mode, p, returns_for(A, pos, cost, night))
        E = np.vstack(ex_post)
        rc = reality_check(E.astype(np.float64), B=boot)
        is_t, post_t, post_mean = np.array(is_t), np.array(post_t), np.array(post_mean)
        sharpe_post = np.array(sharpe_post)
        order = np.argsort(-is_t)[:top]
        # the pre-registered portfolio test: pick the top K rules on data BEFORE 2015 only, hold them
        # equally weighted, judge that ONE strategy after 2014 (no multiple-testing penalty needed)
        ens = {}
        for K in (1, 5, 20, 100, 500):
            sel = np.argsort(-is_t)[:K]
            series = E[sel].mean(axis=0).astype(np.float64)
            sd = series.std(ddof=1)
            ens[str(K)] = {"alpha_t": float(series.mean() / sd * math.sqrt(len(series))) if sd > 0 else 0.0,
                           "alpha_bp_day": float(series.mean() * 1e4)}
        fam = {}
        for nm, t in zip(names, post_t):
            f = fam.setdefault(nm.split("/")[0].split(":")[0], {"n": 0, "pos": 0, "t3": 0})
            f["n"] += 1
            f["pos"] += int(t > 0)
            f["t3"] += int(t >= 3)
        out["assets"][sym] = {
            "rules": len(names), "days_post": int(post.sum()), "cost_bps": cost, "night_bps": night,
            "reality_check": rc,
            "n_post_t_over_bonferroni": int((post_t >= rc["bonferroni_z"]).sum()),
            "n_post_t_over_3": int((post_t >= 3).sum()),
            "share_positive_post": float((post_t > 0).mean()),
            "bh_sharpe_post": float(bh_sharpe_post),
            "n_sharpe_over_bh": int((sharpe_post > bh_sharpe_post).sum()),
            "best_sharpe_post": float(sharpe_post.max()),
            "best_post": [{"rule": names[i], "params": params[i], "post_t": float(post_t[i]),
                           "post_bps_day": float(post_mean[i]), "is_t": float(is_t[i])}
                          for i in np.argsort(-post_t)[:5]],
            "top_is_then_post": [{"rule": names[i], "params": params[i], "is_t": float(is_t[i]),
                                  "post_t": float(post_t[i])} for i in order],
            "families": fam, "ensemble_is_selected": ens}
        print("%-4s %6d rules done (%.0fs)" % (sym, len(names), time.time() - t0), file=sys.stderr)
    out["total_rules"] = sum(a["rules"] for a in out["assets"].values())
    return out


def report(res):
    L = ["Universe search: %s rule tests (%d assets). Risk-adjusted: Jensen's alpha against buy-and-hold" % (
        "{:,}".format(res["total_rules"]), len(res["assets"])),
        "(beta from data before 2015), cash at the T-bill rate, after costs; judged only after %s." % res["is_end"], ""]
    for sym, a in res["assets"].items():
        rc = a["reality_check"]
        L.append("%s: %s rules, %d days after 2014. Best alpha t %.2f (%.2f bp/day). Buy-and-hold Sharpe %.2f; "
                 "%d rules beat it (best %.2f)." % (
            sym, "{:,}".format(a["rules"]), a["days_post"], rc["best_t"], rc["best_mean_bps"] * 1e4,
            a["bh_sharpe_post"], a["n_sharpe_over_bh"], a["best_sharpe_post"]))
        L.append("   Reality Check p = %.3f | SPA p = %.3f | rules with t >= %.2f (Bonferroni): %d | t >= 3: %d | "
                 "positive alpha after 2014: %.1f%%" % (rc["rc_p"], rc["spa_p"], rc["bonferroni_z"],
                                                    a["n_post_t_over_bonferroni"], a["n_post_t_over_3"],
                                                    a["share_positive_post"] * 100))
        b = a["best_post"][0]
        L.append("   best after 2014: %s %s (t %.2f; it had IS t %.2f)" % (
            b["rule"], json.dumps(b["params"], sort_keys=True), b["post_t"], b["is_t"]))
        e = a.get("ensemble_is_selected", {})
        if e:
            L.append("   portfolio of the top-K rules chosen BEFORE 2015, judged after: " + ", ".join(
                "K=%s t %.2f" % (k, v["alpha_t"]) for k, v in sorted(e.items(), key=lambda kv: int(kv[0]))))
        tops = a["top_is_then_post"]
        L.append("   the 20 best rules to 2014 averaged t %.2f after 2014 (%d of 20 positive)" % (
            sum(t["post_t"] for t in tops) / len(tops), sum(1 for t in tops if t["post_t"] > 0)))
    L += ["", "A p-value under 0.05 would mean the best rule beats buy-and-hold by more than the luck of",
          "trying this many rules. Research, not financial advice."]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description="trader-lab universe search with Reality Check / SPA")
    ap.add_argument("--assets", default=",".join(ASSETS))
    ap.add_argument("--boot", type=int, default=500)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write", nargs="?", const=os.path.join(RESULTS, "universe-latest.json"))
    a = ap.parse_args(argv)
    res = search([s.strip().upper() for s in a.assets.split(",") if s.strip()], a.boot)
    if a.write:
        with open(a.write, "w") as fh:
            json.dump(res, fh, indent=1, sort_keys=True)
    print(json.dumps(res, indent=1, sort_keys=True) if a.json else report(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
