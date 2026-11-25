#!/usr/bin/env python3
"""The strategy catalog: every distinct, named public strategy we could collect, each tested once with its textbook
settings on the same 10 markets. Pre-registered.

    python3 catalog.py fetch            # Yahoo daily OHLCV for MARKETS -> data/catalog (gitignored)
    python3 catalog.py run [--write]    # -> results/catalog.json

Why a catalog and not "every strategy on the internet": the posted variants number in the millions, but most are a
few dozen ideas with different settings, and trying settings until one looks good is how false discoveries are
made. So each idea below appears once, with the settings its source publishes (TradingView's built-in strategy
scripts, Investopedia's indicator pages, the original books and papers). The lab's other engines (daily.py,
universe_search.py, market_search.py, swarm.py) have already searched tens of millions of parameter variants.

PRE-REGISTERED 2026-11-25, committed before any data was downloaded. Not to be changed:
  Markets (daily, Yahoo, dividend-adjusted where Yahoo adjusts): SPY QQQ IWM EFA EEM TLT GLD USO BTC-USD ETH-USD,
    from 2006 (crypto from its first Yahoo day).
  Execution: every rule is long or flat (cash earns nothing extra, so the comparison is conservative for the rule).
    The position is decided from day t's completed candle and held from day t+1's open to day t+2's open (no fill
    at a price nobody knew in advance). Cost: 5 bps per change of position (each way), 20 bps for crypto.
  Statistic per rule and market: the daily return of the rule minus beta x the market's own return, where beta is
    the rule's in-sample beta to that market (its alpha over just holding, scaled for time in the market). The rule's
    result is the equal-weight average of that alpha over the 10 markets each day.
  Split: in-sample before 2016-01-01, judged from 2016-01-01.
  Verdict per rule: PASS only if judged alpha t >= 3.5 (Bonferroni for about 60 rules at 5% two-sided) and
    in-sample t > 0. Benjamini-Hochberg over all rules is reported too.
  Reported: what $500 became from 2016, the rule run on all 10 markets in equal parts, next to $500 bought and held in
    the same 10 markets in equal parts.
Research, not financial advice.
"""

import argparse
import gzip
import json
import math
import os
import statistics
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

STORE = os.path.join(HERE, "data", "catalog")
RESULTS = os.path.join(HERE, "results")
MARKETS = ["SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "GLD", "USO", "BTC-USD", "ETH-USD"]
START = "2006-01-01"
SPLIT = "2016-01-01"
T_BAR = 3.5


# ---------------------------------------------------------------- indicators (numpy, causal: index t uses data <= t)

def sma(x, n):
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        c = np.cumsum(np.insert(x, 0, 0.0))
        out[n - 1:] = (c[n:] - c[:-n]) / n
    return out


def ema(x, n):
    out = np.full(len(x), np.nan)
    a = 2.0 / (n + 1)
    s = np.nan
    for i, v in enumerate(x):
        if np.isnan(v):
            continue
        s = v if np.isnan(s) else a * v + (1 - a) * s
        out[i] = s
    return out


def wilder(x, n):
    out = np.full(len(x), np.nan)
    s, k = 0.0, 0
    for i, v in enumerate(x):
        if np.isnan(v):
            continue
        k += 1
        if k < n:
            s += v
        elif k == n:
            s = (s + v) / n
            out[i] = s
        else:
            s = (s * (n - 1) + v) / n
            out[i] = s
    return out


def rsi(c, n):
    d = np.diff(c, prepend=np.nan)
    up, dn = wilder(np.where(d > 0, d, 0.0) * (~np.isnan(d)) + np.where(np.isnan(d), np.nan, 0), n), None
    g = np.where(np.isnan(d), np.nan, np.maximum(d, 0))
    l = np.where(np.isnan(d), np.nan, np.maximum(-d, 0))
    ag, al = wilder(g, n), wilder(l, n)
    with np.errstate(divide="ignore", invalid="ignore"):
        return 100 - 100 / (1 + ag / al)


def true_range(h, l, c):
    pc = np.roll(c, 1)
    pc[0] = np.nan
    return np.nanmax(np.vstack([h - l, np.abs(h - pc), np.abs(l - pc)]), axis=0)


def atr(h, l, c, n):
    return wilder(true_range(h, l, c), n)


def rolling(x, n, fn):
    out = np.full(len(x), np.nan)
    for i in range(n - 1, len(x)):
        out[i] = fn(x[i - n + 1:i + 1])
    return out


def hh(x, n):
    return rolling(x, n, np.max)


def ll(x, n):
    return rolling(x, n, np.min)


def shift(x, k=1):
    out = np.roll(x, k).astype(float)
    out[:k] = np.nan
    return out


def latch(enter, exit_):
    """In position from an enter day until an exit day (exit wins on a tie)."""
    pos = np.zeros(len(enter), bool)
    on = False
    for i in range(len(enter)):
        if on and exit_[i]:
            on = False
        elif not on and enter[i]:
            on = True
        pos[i] = on
    return pos


def gt(a, b):
    with np.errstate(invalid="ignore"):
        return np.nan_to_num(a, nan=-np.inf) > np.nan_to_num(b, nan=np.inf)


def lt(a, b):
    with np.errstate(invalid="ignore"):
        return np.nan_to_num(a, nan=np.inf) < np.nan_to_num(b, nan=-np.inf)


# ---------------------------------------------------------------- the catalog

def macd(c, f=12, s=26, sig=9):
    m = ema(c, f) - ema(c, s)
    return m, ema(m, sig)


def stoch(h, l, c, n=14, k=3, d=3):
    lo, hi = ll(l, n), hh(h, n)
    with np.errstate(divide="ignore", invalid="ignore"):
        raw = 100 * (c - lo) / (hi - lo)
    kk = sma(np.nan_to_num(raw, nan=50.0), k)
    return kk, sma(kk, d)


def supertrend(h, l, c, n=10, mult=3.0):
    a = atr(h, l, c, n)
    mid = (h + l) / 2
    up, dn = mid - mult * a, mid + mult * a
    trend = np.ones(len(c), bool)
    fu, fd = up.copy(), dn.copy()
    for i in range(1, len(c)):
        if np.isnan(a[i]):
            continue
        fu[i] = max(up[i], fu[i - 1]) if c[i - 1] > fu[i - 1] else up[i]
        fd[i] = min(dn[i], fd[i - 1]) if c[i - 1] < fd[i - 1] else dn[i]
        if trend[i - 1] and c[i] < fu[i]:
            trend[i] = False
        elif not trend[i - 1] and c[i] > fd[i]:
            trend[i] = True
        else:
            trend[i] = trend[i - 1]
    trend[np.isnan(a)] = False
    return trend


def psar(h, l, step=0.02, mx=0.2):
    n = len(h)
    up = np.zeros(n, bool)
    if n < 3:
        return up
    bull, sar, ep, af = True, l[0], h[0], step
    for i in range(1, n):
        sar = sar + af * (ep - sar)
        if bull:
            sar = min(sar, l[i - 1], l[i - 2] if i > 1 else l[i - 1])
            if l[i] < sar:
                bull, sar, ep, af = False, ep, l[i], step
            elif h[i] > ep:
                ep, af = h[i], min(af + step, mx)
        else:
            sar = max(sar, h[i - 1], h[i - 2] if i > 1 else h[i - 1])
            if h[i] > sar:
                bull, sar, ep, af = True, ep, h[i], step
            elif l[i] < ep:
                ep, af = l[i], min(af + step, mx)
        up[i] = bull
    return up


def adx(h, l, c, n=14):
    uh, dl = np.diff(h, prepend=np.nan), -np.diff(l, prepend=np.nan)
    pdm = np.where((uh > dl) & (uh > 0), uh, 0.0)
    ndm = np.where((dl > uh) & (dl > 0), dl, 0.0)
    pdm[0] = ndm[0] = np.nan
    tr = true_range(h, l, c)
    a = wilder(tr, n)
    with np.errstate(divide="ignore", invalid="ignore"):
        pdi, ndi = 100 * wilder(pdm, n) / a, 100 * wilder(ndm, n) / a
        dx = 100 * np.abs(pdi - ndi) / (pdi + ndi)
    return wilder(dx, n), pdi, ndi


def heikin(o, h, l, c):
    hc = (o + h + l + c) / 4
    ho = np.full(len(c), np.nan)
    ho[0] = (o[0] + c[0]) / 2
    for i in range(1, len(c)):
        ho[i] = (ho[i - 1] + hc[i - 1]) / 2
    return ho, hc


def build(D):
    """{name: (source, position array)} for one market's daily OHLCV dict of numpy arrays."""
    o, h, l, c, v, mo = D["o"], D["h"], D["l"], D["c"], D["v"], D["month"]
    S = {}

    def add(name, src, pos):
        S[name] = (src, np.asarray(pos, bool))

    s50, s200, s20 = sma(c, 50), sma(c, 200), sma(c, 20)
    add("golden_cross_50_200", "Investopedia: golden cross (SMA 50 over SMA 200)", gt(s50, s200))
    add("price_above_200sma", "Investopedia / Faber: close above the 200-day SMA", gt(c, s200))
    add("faber_10_month", "Faber 2007, A Quantitative Approach to TAA: close above the 10-month (210-day) SMA",
        gt(c, sma(c, 210)))
    add("ema_cross_12_26", "Investopedia: EMA 12 over EMA 26", gt(ema(c, 12), ema(c, 26)))
    add("ema_cross_50_200", "EMA golden cross 50/200", gt(ema(c, 50), ema(c, 200)))
    m, sg = macd(c)
    add("macd_signal", "TradingView built-in: MACD Strategy (12, 26, 9)", gt(m, sg))
    add("macd_zero", "Appel: MACD line above zero", gt(m, 0))
    add("triple_ma_10_20_50", "triple moving average stack 10 > 20 > 50", gt(sma(c, 10), s20) & gt(s20, s50))
    add("ma2line_cross_9_18", "TradingView built-in: MovingAvg2Line Cross (9, 18)", gt(sma(c, 9), sma(c, 18)))
    add("ma_cross_9", "TradingView built-in: MovingAvg Cross (close over SMA 9)", gt(c, sma(c, 9)))
    hull = 2 * ema(c, 10) - ema(c, 20)
    hull = ema(hull, int(math.sqrt(20)))
    add("hull_ma_rising", "Alan Hull: Hull MA(20) rising", gt(hull, shift(hull)))
    tr3 = ema(ema(ema(c, 15), 15), 15)
    add("trix_15", "Jack Hutson: TRIX(15) above zero", gt(tr3, shift(tr3)))
    add("supertrend_10_3", "TradingView built-in: Supertrend (10, 3)", supertrend(h, l, c))
    add("parabolic_sar", "Wilder 1978: Parabolic SAR (0.02, 0.2), TradingView built-in", psar(h, l))
    tenkan = (hh(h, 9) + ll(l, 9)) / 2
    kijun = (hh(h, 26) + ll(l, 26)) / 2
    span_a = shift((tenkan + kijun) / 2, 26)
    span_b = shift((hh(h, 52) + ll(l, 52)) / 2, 26)
    add("ichimoku_cloud", "Hosoda: Ichimoku, close above the cloud and tenkan over kijun",
        gt(c, np.fmax(span_a, span_b)) & gt(tenkan, kijun))
    ax, pdi, ndi = adx(h, l, c)
    add("adx_dmi_25", "Wilder: ADX(14) > 25 with +DI over -DI", gt(ax, 25) & gt(pdi, ndi))
    au = 100 * rolling(h, 26, lambda x: (len(x) - 1 - (len(x) - 1 - np.argmax(x))) / (len(x) - 1))
    ad = 100 * rolling(l, 26, lambda x: (len(x) - 1 - (len(x) - 1 - np.argmin(x))) / (len(x) - 1))
    add("aroon_25", "Tushar Chande: Aroon(25) up over down", gt(au, ad))
    tr = true_range(h, l, c)
    vmp, vmn = np.abs(h - shift(l)), np.abs(l - shift(h))
    with np.errstate(invalid="ignore", divide="ignore"):
        vip, vin = rolling(vmp, 14, np.sum) / rolling(tr, 14, np.sum), rolling(vmn, 14, np.sum) / rolling(tr, 14, np.sum)
    add("vortex_14", "Botes & Siepman 2010: Vortex VI+ over VI-", gt(vip, vin))
    add("turtle_20_10", "Dennis/Faith, Way of the Turtle: System 1, 20-day high in, 10-day low out",
        latch(gt(c, shift(hh(h, 20))), lt(c, shift(ll(l, 10)))))
    add("turtle_55_20", "Way of the Turtle: System 2, 55-day high in, 20-day low out",
        latch(gt(c, shift(hh(h, 55))), lt(c, shift(ll(l, 20)))))
    add("price_channel_20", "TradingView built-in: Price Channel Strategy (20)",
        latch(gt(c, shift(hh(h, 20))), lt(c, shift(ll(l, 20)))))
    e20, a10 = ema(c, 20), atr(h, l, c, 10)
    add("keltner_breakout", "Chester Keltner / Linda Raschke: close above EMA20 + 2 ATR, out below EMA20",
        latch(gt(c, e20 + 2 * a10), lt(c, e20)))
    sd20 = rolling(c, 20, np.std)
    add("bollinger_breakout", "Bollinger: close above the upper band (20, 2), out below the middle",
        latch(gt(c, s20 + 2 * sd20), lt(c, s20)))
    add("tsmom_12m", "Moskowitz, Ooi & Pedersen 2012: 12-month time-series momentum", gt(c, shift(c, 252)))
    add("roc_10", "Investopedia: ROC(10) above zero", gt(c, shift(c, 10)))
    mom = c - shift(c, 12)
    add("momentum_tv", "TradingView built-in: Momentum Strategy (12, momentum of momentum > 0)",
        gt(mom, 0) & gt(mom - shift(mom), 0))
    rocs = [sma(100 * (c / shift(c, r) - 1), s) for r, s in ((10, 10), (15, 10), (20, 10), (30, 15))]
    kst = rocs[0] + 2 * rocs[1] + 3 * rocs[2] + 4 * rocs[3]
    add("kst", "Martin Pring: KST above its 9-day signal", gt(kst, sma(np.nan_to_num(kst), 9)))
    copp = 100 * (c / shift(c, 294) - 1) + 100 * (c / shift(c, 231) - 1)
    copp = ema(np.nan_to_num(copp), 210)
    add("coppock", "Edwin Coppock 1962: Coppock curve rising", gt(copp, shift(copp)))
    e13 = ema(c, 13)
    hist = m - sg
    add("elder_impulse", "Alexander Elder: impulse system, EMA13 rising and MACD histogram rising",
        gt(e13, shift(e13)) & gt(hist, shift(hist)))
    ho, hc = heikin(o, h, l, c)
    add("heikin_ashi", "Heikin Ashi trend: HA close above HA open", gt(hc, ho))
    a22 = atr(h, l, c, 22)
    add("chandelier", "Chuck LeBeau: chandelier exit, close above the 22-day high minus 3 ATR",
        latch(gt(c, s50), lt(c, hh(h, 22) - 3 * a22)))
    obv = np.cumsum(np.sign(np.diff(c, prepend=c[0])) * v)
    add("obv_trend", "Granville: OBV above its 20-day SMA", gt(obv, sma(obv, 20)))
    with np.errstate(invalid="ignore", divide="ignore"):
        mfm = np.where(h > l, ((c - l) - (h - c)) / (h - l), 0.0)
        cmf = rolling(mfm * v, 20, np.sum) / rolling(v, 20, np.sum)
    add("chaikin_mf", "Marc Chaikin: Chaikin money flow(20) above zero", gt(cmf, 0))
    adl = np.cumsum(mfm * v)
    add("accum_dist", "Chaikin: accumulation/distribution line above its 20-day SMA", gt(adl, sma(adl, 20)))
    r14, r2 = rsi(c, 14), rsi(c, 2)
    add("rsi_30_50", "Wilder / TradingView built-in RSI Strategy: RSI(14) < 30 in, > 50 out", latch(lt(r14, 30), gt(r14, 50)))
    add("rsi_70_trend", "RSI(14) above 50 as a trend filter", gt(r14, 50))
    add("rsi2_connors", "Connors: RSI(2) < 10 in, > 70 out (above the 200-day SMA)",
        latch(lt(r2, 10) & gt(c, s200), gt(r2, 70)))
    add("bollinger_revert", "Bollinger: close below the lower band in, above the middle out",
        latch(lt(c, s20 - 2 * sd20), gt(c, s20)))
    k, d = stoch(h, l, c)
    add("stochastic_slow", "Lane / TradingView built-in Stochastic Slow: %K over %D under 20 in, %K over 80 out",
        latch(gt(k, d) & lt(k, 20), gt(k, 80)))
    with np.errstate(invalid="ignore", divide="ignore"):
        wr = -100 * (hh(h, 14) - c) / (hh(h, 14) - ll(l, 14))
    add("williams_r", "Larry Williams: %R(14) below -80 in, above -20 out", latch(lt(wr, -80), gt(wr, -20)))
    tp = (h + l + c) / 3
    with np.errstate(invalid="ignore", divide="ignore"):
        cci = (tp - sma(tp, 20)) / (0.015 * rolling(tp, 20, lambda x: np.mean(np.abs(x - x.mean()))))
    add("cci", "Donald Lambert: CCI(20) below -100 in, above 0 out", latch(lt(cci, -100), gt(cci, 0)))
    rmf = tp * v
    pos_f = rolling(np.where(tp > shift(tp), rmf, 0.0), 14, np.sum)
    neg_f = rolling(np.where(tp < shift(tp), rmf, 0.0), 14, np.sum)
    with np.errstate(invalid="ignore", divide="ignore"):
        mfi = 100 - 100 / (1 + pos_f / neg_f)
    add("mfi", "Quong & Soudack: MFI(14) below 20 in, above 50 out", latch(lt(mfi, 20), gt(mfi, 50)))
    down3 = lt(c, shift(c)) & lt(shift(c), shift(c, 2)) & lt(shift(c, 2), shift(c, 3))
    add("three_down_closes", "three down closes in, first up close out", latch(down3, gt(c, shift(c))))
    with np.errstate(invalid="ignore", divide="ignore"):
        z = (c - s20) / sd20
    add("zscore_revert", "z-score of close vs 20-day mean below -2 in, above 0 out", latch(lt(z, -2), gt(z, 0)))
    add("keltner_revert", "close below EMA20 - 2 ATR in, above EMA20 out", latch(lt(c, e20 - 2 * a10), gt(c, e20)))
    bp = c - np.fmin(l, shift(c))
    trr = np.fmax(h, shift(c)) - np.fmin(l, shift(c))
    with np.errstate(invalid="ignore", divide="ignore"):
        uo = 100 * (4 * rolling(bp, 7, np.sum) / rolling(trr, 7, np.sum) + 2 * rolling(bp, 14, np.sum) / rolling(trr, 14, np.sum)
                    + rolling(bp, 28, np.sum) / rolling(trr, 28, np.sum)) / 7
    add("ultimate_osc", "Larry Williams: Ultimate Oscillator below 30 in, above 50 out", latch(lt(uo, 30), gt(uo, 50)))
    with np.errstate(invalid="ignore", divide="ignore"):
        ibs = (c - l) / (h - l)
    add("ibs", "internal bar strength below 0.2 in, above 0.8 out", latch(lt(ibs, 0.2), gt(ibs, 0.8)))
    squeeze = lt(s20 + 2 * sd20, e20 + 1.5 * a10) & gt(s20 - 2 * sd20, e20 - 1.5 * a10)
    add("ttm_squeeze", "John Carter, Mastering the Trade: squeeze fires with momentum up, out when momentum turns",
        latch(shift(squeeze.astype(float)).astype(bool) & ~squeeze & gt(c, shift(c, 12)), lt(c, shift(c, 12))))
    rng = h - l
    nr7 = rng <= rolling(rng, 7, np.min)
    add("nr7_breakout", "Toby Crabel: close above an NR7 day's high, one day", gt(c, shift(np.where(nr7, h, np.nan))))
    inside = lt(h, shift(h)) & gt(l, shift(l))
    add("inside_bar", "TradingView built-in: InSide Bar Strategy, close above an inside bar's high, one day",
        gt(c, shift(np.where(inside, h, np.nan))))
    outside_bull = gt(h, shift(h)) & lt(l, shift(l)) & gt(c, o)
    add("outside_bar", "TradingView built-in: OutSide Bar Strategy, bullish outside bar, one day", outside_bull)
    up3 = gt(c, shift(c)) & gt(shift(c), shift(c, 2)) & gt(shift(c, 2), shift(c, 3))
    add("consecutive_up", "TradingView built-in: Consecutive Up/Down Strategy, after 3 up closes, one day", up3)
    add("bar_up_dn", "TradingView built-in: BarUpDn Strategy, gap up and close above the open, one day",
        gt(o, shift(c)) & gt(c, o))
    add("volty_expan_close", "TradingView built-in: Volty Expan Close, close above yesterday's close + 0.75 SMA(TR,5)",
        gt(c, shift(c) + 0.75 * shift(sma(tr, 5))))
    pr = (shift(h) + shift(l) + shift(c)) / 3
    add("pivot_point", "floor-trader pivot: close above the daily pivot point", gt(c, pr))
    add("greedy_gap", "TradingView built-in: Greedy Strategy, buy a gap down that closes above its open, one day",
        lt(o, shift(l)) & gt(c, o))
    add("halloween", "Bouman & Jacobsen 2002: hold November to April only", np.isin(mo, [11, 12, 1, 2, 3, 4]))
    vol20 = rolling(np.diff(np.log(c), prepend=np.nan), 20, np.std)
    add("low_vol_regime", "volatility regime: 20-day volatility below its 1-year median",
        lt(vol20, rolling(np.nan_to_num(vol20, nan=1.0), 252, np.median)))
    add("ma_envelope_revert", "moving-average envelope: close 5% under SMA 20 in, back above SMA 20 out",
        latch(lt(c, 0.95 * s20), gt(c, s20)))
    add("dpo_revert", "detrended price oscillator below zero after an uptrend (above SMA 200), one day",
        lt(c - shift(sma(c, 20), 11), 0) & gt(c, s200))
    return S


# ---------------------------------------------------------------- data and scoring

def path(m):
    return os.path.join(STORE, "%s.json.gz" % m.replace("^", "_").replace("=", "_"))


def cmd_fetch(a):
    import daily
    os.makedirs(STORE, exist_ok=True)
    for m in MARKETS:
        b = daily.parse_daily(daily.fetch_daily(m))
        with gzip.open(path(m) + ".tmp", "wt") as fh:
            json.dump({k: b[k] for k in ("d", "o", "h", "l", "c", "v", "a")}, fh)
        os.replace(path(m) + ".tmp", path(m))
        print(m, len(b["d"]), b["d"][0], b["d"][-1])
        time.sleep(0.5)
    return 0


def load(m):
    with gzip.open(path(m), "rt") as fh:
        b = json.load(fh)
    keep = [i for i, d in enumerate(b["d"]) if d >= START and None not in (b["o"][i], b["h"][i], b["l"][i], b["c"][i])]
    D = {k: np.array([b[k][i] if b[k][i] is not None else 0.0 for i in keep], float) for k in ("o", "h", "l", "c", "v")}
    D["d"] = [b["d"][i] for i in keep]
    D["month"] = np.array([int(d[5:7]) for d in D["d"]])
    return D


def strategy_returns(D, pos, cost_bps):
    """Daily returns of holding `pos` (decided at close t) from open t+1 to open t+2, net of costs."""
    o = D["o"]
    r = np.full(len(o), np.nan)
    r[:-2] = o[2:] / o[1:-1] - 1.0          # r[t] = open t+1 -> open t+2, earned by the day-t decision
    p = pos.astype(float)
    turn = np.abs(np.diff(p, prepend=0.0))
    net = p * r - turn * cost_bps / 1e4
    mkt = r
    return net, mkt


def tstat(x):
    x = [v for v in x if not math.isnan(v)]
    if len(x) < 3 or statistics.stdev(x) == 0:
        return 0.0
    return statistics.mean(x) / (statistics.stdev(x) / math.sqrt(len(x)))


def p_two(t):
    return math.erfc(abs(t) / math.sqrt(2))


def cmd_run(a):
    data = {m: load(m) for m in MARKETS if os.path.exists(path(m))}
    per = {}                          # name -> {date: [alpha per market]}, src, and $ paths
    src = {}
    usd = {}
    bh_daily = {}
    for m, D in data.items():
        cost = 20.0 if m.endswith("-USD") else 5.0
        S = build(D)
        dates = D["d"]
        for name, (s, pos) in S.items():
            src[name] = s
            net, mkt = strategy_returns(D, pos, cost)
            ins = [(net[i], mkt[i]) for i, d in enumerate(dates) if d < SPLIT and not math.isnan(mkt[i])]
            if len(ins) > 250:
                x = np.array([q[1] for q in ins])
                y = np.array([q[0] for q in ins])
                beta = float(np.cov(y, x)[0, 1] / np.var(x)) if np.var(x) > 0 else 0.0
            else:                      # crypto with little in-sample history: beta from its first year
                fy = [(net[i], mkt[i]) for i in range(min(len(dates), 400)) if not math.isnan(mkt[i])]
                x = np.array([q[1] for q in fy])
                y = np.array([q[0] for q in fy])
                beta = float(np.cov(y, x)[0, 1] / np.var(x)) if len(fy) > 30 and np.var(x) > 0 else 0.0
            for i, d in enumerate(dates):
                if math.isnan(mkt[i]):
                    continue
                per.setdefault(name, {}).setdefault(d, []).append(net[i] - beta * mkt[i])
                usd.setdefault(name, {}).setdefault(d, []).append(net[i])
        for i, d in enumerate(dates):
            r = strategy_returns(D, np.ones(len(dates), bool), 0.0)[1][i]
            if not math.isnan(r):
                bh_daily.setdefault(d, []).append(r)
    rows = []
    days_j = sorted(d for d in bh_daily if d >= SPLIT)
    bh_val = 500.0
    for d in days_j:
        bh_val *= 1 + sum(bh_daily[d]) / len(bh_daily[d])
    for name in sorted(per):
        series = [(d, sum(v) / len(v)) for d, v in sorted(per[name].items())]
        ins = [v for d, v in series if d < SPLIT]
        jud = [v for d, v in series if d >= SPLIT]
        val = 500.0
        for d in days_j:
            vs = usd[name].get(d)
            if vs:
                val *= 1 + sum(vs) / len(vs)
        rows.append({"rule": name, "source": src[name], "is_t": tstat(ins), "is_alpha_bp": 1e4 * statistics.mean(ins),
                     "judged_t": tstat(jud), "judged_alpha_bp": 1e4 * statistics.mean(jud), "usd_from_2016": val,
                     "hold_usd_from_2016": bh_val})
    for r in rows:
        r["verdict"] = "PASS" if (r["judged_t"] >= T_BAR and r["is_t"] > 0) else "FAIL"
    ps = sorted((p_two(r["judged_t"]) if r["judged_t"] > 0 else 1.0, k) for k, r in enumerate(rows))
    cut = 0
    for rank, (p, k) in enumerate(ps, 1):
        if p <= 0.05 * rank / len(rows):
            cut = rank
    for rank, (p, k) in enumerate(ps, 1):
        rows[k]["bh_significant"] = rank <= cut
    rows.sort(key=lambda r: -r["judged_t"])
    print("%-22s %8s %6s | %8s %6s | %8s  %s" % ("rule", "IS a bp", "IS t", "J a bp", "J t", "$500->", "verdict"))
    for r in rows:
        print("%-22s %+8.2f %+6.2f | %+8.2f %+6.2f | %8.0f  %s" % (r["rule"], r["is_alpha_bp"], r["is_t"],
                                                              r["judged_alpha_bp"], r["judged_t"], r["usd_from_2016"],
                                                              r["verdict"]))
    print("%d rules on %d markets; $500 held in the same markets from 2016: $%.0f; %d PASS, %d BH-significant" % (
        len(rows), len(data), bh_val, sum(r["verdict"] == "PASS" for r in rows), sum(r["bh_significant"] for r in rows)))
    if a.write:
        with open(a.write, "w") as fh:
            json.dump({"rules": rows, "markets": sorted(data), "hold_usd_from_2016": bh_val, "t_bar": T_BAR}, fh, indent=1)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("fetch")
    r = sub.add_parser("run")
    r.add_argument("--write", nargs="?", const=os.path.join(RESULTS, "catalog.json"))
    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        return cmd_fetch(a)
    if a.cmd == "run":
        return cmd_run(a)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
