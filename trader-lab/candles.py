#!/usr/bin/env python3
"""Candlesticks: the first 5-minute candle, classic candle patterns, and all of them combined. Pre-registered.

    python3 candles.py fetch-crypto [--coins btcusd,ethusd]  # Tiingo 5-minute crypto bars -> data/candles (gitignored)
    python3 candles.py fetch-daily                           # Yahoo daily OHLC for DAILY_MARKETS -> data/candles
    python3 candles.py run [--write] [--parts first,daily,combo]

The guide to what each candle means is CANDLES.md. Every definition, rule, market, cost and pass bar below
was FIXED ON 2026-11-24 and committed before any result was computed. Not to be changed.

CANDLE ANATOMY (o, h, l, c; range R = h - l; body = |c - o|; upper wick = h - max(o, c); lower wick = min(o, c) - l)
  Each candle gets one type, checked in this order:
    doji           body <= 10% of R, split into
                     dragonfly   lower wick >= 60% R and upper wick <= 10% R   (bullish)
                     gravestone  upper wick >= 60% R and lower wick <= 10% R   (bearish)
                     long-legged both wicks >= 30% R
                     doji        any other
    marubozu       body >= 90% R, bull or bear (continuation)
    hammer         lower wick >= 2x body, >= 60% R, upper wick <= 15% R        (bullish "wick candle")
    shooting star  upper wick >= 2x body, >= 60% R, lower wick <= 15% R        (bearish "wick candle")
    spinning top   body <= 30% R and both wicks >= 25% R
    long           body >= 70% R, bull or bear (continuation)
    plain          everything else, bull or bear by colour

PART 1, THE FIRST 5-MINUTE CANDLE. Eleven rules on the session's first candle; trade at the next candle's open,
hold to the session's last close, no stop:
    color (bull long, bear short), dragonfly +, gravestone -, marubozu_bull +, marubozu_bear -, hammer +,
    shooting_star -, long_bull +, long_bear -, lower_wick (lower wick >= 50% R) +, upper_wick (upper >= 50% R) -
  Five market sessions:
    STOCKS   the lab's 40 names (data/long, Tiingo IEX, 9:30-16:00 New York, full 78-bar sessions); the day's
             result is the equal-weight mean over names that trade. 5 bps round trip (3 reported).
    BTC_UTC, ETH_UTC   crypto day 00:00-23:55 UTC, first candle 00:00 (>= 280 of 288 bars needed).
    BTC_NY,  ETH_NY    crypto during the US session 9:30-16:00 New York, first candle 9:30 (all 78 bars).
             Crypto costs 20 bps round trip (about 0.1% taker fee a side; 10 reported).
  In-sample: sessions before 2025-01-01. Judged: from 2025-01-01. 55 tests.

PART 2, CLASSIC PATTERNS ON DAILY CANDLES across DAILY_MARKETS (Yahoo, from 2006). A pattern completed at day t's
  close trades day t+1 close-to-close (dividend-adjusted) in its textbook direction (Nison 1991). Reversal patterns
  need the trend they reverse: bullish ones need close[t0-1] < close[t0-6], bearish ones close[t0-1] > close[t0-6],
  where t0 is the pattern's first candle. Twenty patterns:
    single: hammer +, dragonfly +, shooting_star -, gravestone - (reversals); marubozu_bull +, marubozu_bear -,
            long_bull +, long_bear - (continuation)
    two:    bull_engulfing +, bear_engulfing -, bull_harami +, bear_harami -, piercing +, dark_cloud -,
            tweezer_bottom +, tweezer_top - (reversals)
    three:  morning_star +, evening_star - (reversals); three_soldiers +, three_crows - (continuation)
  The day's result is the mean over markets that signal. 5 bps round trip, crypto 20 bps.
  In-sample: before 2016-01-01. Judged: from 2016-01-01. 20 tests.

PART 3, EVERYTHING COMBINED. A ridge regression (lambda 100 on standardized features, numpy) fitted on in-sample
  data only:
    first-candle model, one per Part 1 market (5 tests): the first candle's signed body, both wicks and close
      location (all / R), its range vs the mean of the 14 prior sessions' first candles, its return, the gap from
      the previous session's close, the previous session's return, its candle type (one-hot) and the 20 daily
      pattern signals on the previous sessions' OHLC. Target: the rest of the session from the 2nd candle's open.
    daily model (1 test): the same candle features for day t plus the 1- and 5-day returns, pooled over
      DAILY_MARKETS. Target: day t+1.
  It trades the prediction's sign when |prediction| > the round-trip cost. Same splits and costs as above.

VERDICT, for each of the 81 tests: PASS only if the judged mean > 0, judged t >= 3.5 (Bonferroni for 81 tests at
5% two-sided is about 3.4) and in-sample t > 0. For a PASS: a placebo with random directions on the same trades,
1,000 draws, reported. Benjamini-Hochberg over all 81 is reported too.
Research, not financial advice.
"""

import argparse
import datetime
import gzip
import json
import math
import os
import random
import statistics
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

STORE = os.path.join(HERE, "data", "candles")
RESULTS = os.path.join(HERE, "results")
COINS = ["btcusd", "ethusd"]
CRYPTO_START = "2022-11-01"
DAILY_MARKETS = ["SPY", "QQQ", "IWM", "DIA", "EFA", "EEM", "TLT", "GLD", "SLV", "USO", "UNG", "FXE", "FXY", "UUP",
                 "XLE", "XLF", "XLK", "XLV", "XLU", "XLP", "XLI", "XLB", "BTC-USD", "ETH-USD", "EURUSD=X",
                 "GBPUSD=X", "USDJPY=X", "^N225", "^GDAXI", "^FTSE"]
DAILY_START = "2006-01-01"
COST = {"stocks": 5.0, "crypto": 20.0, "daily": 5.0, "daily_crypto": 20.0}
REF_COST = {"stocks": 3.0, "crypto": 10.0, "daily": 3.0, "daily_crypto": 10.0}
SPLIT_5M = "2025-01-01"
SPLIT_DAILY = "2016-01-01"
T_BAR = 3.5
RIDGE = 100.0
N_TESTS = 81
PLACEBO_DRAWS = 1000

TYPES = ["dragonfly", "gravestone", "longleg_doji", "doji", "marubozu_bull", "marubozu_bear", "hammer",
         "shooting_star", "spinning_top", "long_bull", "long_bear", "bull", "bear"]


# ---------------------------------------------------------------- anatomy

def anatomy(o, h, l, c):
    R = h - l
    if R <= 0:
        return None
    return {"R": R, "body": abs(c - o), "up": h - max(o, c), "lo": min(o, c) - l, "bull": c > o, "bear": c < o}


def ctype(o, h, l, c):
    a = anatomy(o, h, l, c)
    if a is None:
        return None
    R, b, up, lo = a["R"], a["body"], a["up"], a["lo"]
    if b <= 0.10 * R:
        if lo >= 0.60 * R and up <= 0.10 * R:
            return "dragonfly"
        if up >= 0.60 * R and lo <= 0.10 * R:
            return "gravestone"
        if up >= 0.30 * R and lo >= 0.30 * R:
            return "longleg_doji"
        return "doji"
    if b >= 0.90 * R:
        return "marubozu_bull" if a["bull"] else "marubozu_bear"
    if lo >= 2 * b and lo >= 0.60 * R and up <= 0.15 * R:
        return "hammer"
    if up >= 2 * b and up >= 0.60 * R and lo <= 0.15 * R:
        return "shooting_star"
    if b <= 0.30 * R and up >= 0.25 * R and lo >= 0.25 * R:
        return "spinning_top"
    if b >= 0.70 * R:
        return "long_bull" if a["bull"] else "long_bear"
    return "bull" if a["bull"] else "bear"


FIRST_RULES = ["color", "dragonfly", "gravestone", "marubozu_bull", "marubozu_bear", "hammer", "shooting_star",
               "long_bull", "long_bear", "lower_wick", "upper_wick"]
TYPE_DIR = {"dragonfly": 1, "gravestone": -1, "marubozu_bull": 1, "marubozu_bear": -1, "hammer": 1,
            "shooting_star": -1, "long_bull": 1, "long_bear": -1}


def first_rule(rule, o, h, l, c):
    a = anatomy(o, h, l, c)
    if a is None:
        return 0
    if rule == "color":
        return 1 if a["bull"] else (-1 if a["bear"] else 0)
    if rule == "lower_wick":
        return 1 if a["lo"] >= 0.5 * a["R"] else 0
    if rule == "upper_wick":
        return -1 if a["up"] >= 0.5 * a["R"] else 0
    return TYPE_DIR[rule] if ctype(o, h, l, c) == rule else 0


# ---------------------------------------------------------------- daily patterns (arrays o h l c, index i = last candle)

DAILY_RULES = ["hammer", "dragonfly", "shooting_star", "gravestone", "marubozu_bull", "marubozu_bear", "long_bull",
               "long_bear", "bull_engulfing", "bear_engulfing", "bull_harami", "bear_harami", "piercing",
               "dark_cloud", "tweezer_bottom", "tweezer_top", "morning_star", "evening_star", "three_soldiers",
               "three_crows"]


def _down(C, j):
    return j >= 6 and C[j - 1] < C[j - 6]


def _up(C, j):
    return j >= 6 and C[j - 1] > C[j - 6]


def daily_signal(rule, O, H, L, C, i):
    """+1 / -1 / 0 for the pattern completed at candle i."""
    if i < 8:
        return 0
    t = ctype(O[i], H[i], L[i], C[i])
    if t is None:
        return 0
    if rule in ("hammer", "dragonfly"):
        return 1 if t == rule and _down(C, i) else 0
    if rule in ("shooting_star", "gravestone"):
        return -1 if t == rule and _up(C, i) else 0
    if rule in ("marubozu_bull", "marubozu_bear", "long_bull", "long_bear"):
        return TYPE_DIR[rule] if t == rule else 0
    p = anatomy(O[i - 1], H[i - 1], L[i - 1], C[i - 1])
    a = anatomy(O[i], H[i], L[i], C[i])
    if p is None or a is None:
        return 0
    if rule == "bull_engulfing":
        return 1 if p["bear"] and a["bull"] and O[i] <= C[i - 1] and C[i] >= O[i - 1] and _down(C, i - 1) else 0
    if rule == "bear_engulfing":
        return -1 if p["bull"] and a["bear"] and O[i] >= C[i - 1] and C[i] <= O[i - 1] and _up(C, i - 1) else 0
    lo_b, hi_b = min(O[i - 1], C[i - 1]), max(O[i - 1], C[i - 1])
    inside = min(O[i], C[i]) >= lo_b and max(O[i], C[i]) <= hi_b and a["body"] < p["body"]
    if rule == "bull_harami":
        return 1 if p["bear"] and p["body"] >= 0.6 * p["R"] and inside and _down(C, i - 1) else 0
    if rule == "bear_harami":
        return -1 if p["bull"] and p["body"] >= 0.6 * p["R"] and inside and _up(C, i - 1) else 0
    mid = (O[i - 1] + C[i - 1]) / 2
    if rule == "piercing":
        return 1 if (p["bear"] and p["body"] >= 0.6 * p["R"] and a["bull"] and O[i] < L[i - 1] and mid < C[i] < O[i - 1]
                     and _down(C, i - 1)) else 0
    if rule == "dark_cloud":
        return -1 if (p["bull"] and p["body"] >= 0.6 * p["R"] and a["bear"] and O[i] > H[i - 1] and O[i - 1] < C[i] < mid
                      and _up(C, i - 1)) else 0
    avg_r = (p["R"] + a["R"]) / 2
    if rule == "tweezer_bottom":
        return 1 if p["bear"] and a["bull"] and abs(L[i] - L[i - 1]) <= 0.05 * avg_r and _down(C, i - 1) else 0
    if rule == "tweezer_top":
        return -1 if p["bull"] and a["bear"] and abs(H[i] - H[i - 1]) <= 0.05 * avg_r and _up(C, i - 1) else 0
    q = anatomy(O[i - 2], H[i - 2], L[i - 2], C[i - 2])
    if q is None:
        return 0
    small = p["body"] <= 0.3 * p["R"]
    if rule == "morning_star":
        return 1 if (q["bear"] and q["body"] >= 0.6 * q["R"] and small and a["bull"]
                     and C[i] > (O[i - 2] + C[i - 2]) / 2 and _down(C, i - 2)) else 0
    if rule == "evening_star":
        return -1 if (q["bull"] and q["body"] >= 0.6 * q["R"] and small and a["bear"]
                      and C[i] < (O[i - 2] + C[i - 2]) / 2 and _up(C, i - 2)) else 0
    three = [(O[k], H[k], L[k], C[k]) for k in (i - 2, i - 1, i)]
    an = [anatomy(*x) for x in three]
    if rule == "three_soldiers":
        return 1 if all(x["bull"] and x["body"] >= 0.5 * x["R"] for x in an) and C[i] > C[i - 1] > C[i - 2] else 0
    if rule == "three_crows":
        return -1 if all(x["bear"] and x["body"] >= 0.5 * x["R"] for x in an) and C[i] < C[i - 1] < C[i - 2] else 0
    raise ValueError(rule)


# ---------------------------------------------------------------- data

def save_gz(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with gzip.open(tmp, "wt") as fh:
        json.dump(obj, fh)
    os.replace(tmp, path)


def load_gz(path):
    if not os.path.exists(path):
        return None
    with gzip.open(path, "rt") as fh:
        return json.load(fh)


LOCK = os.path.join(STORE, "fetch.lock")


def take_lock(path=LOCK):
    """True if this process now holds the fetch lock; False if another live process does (so two fetchers never
    write the store at once). A lock left by a dead process is taken over."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        try:
            pid = int(open(path).read().split()[0])
            os.kill(pid, 0)
            if pid != os.getpid():
                return False
        except (ValueError, IndexError, ProcessLookupError, PermissionError, OSError):
            pass
    with open(path, "w") as fh:
        fh.write("%d %d\n" % (os.getpid(), int(time.time())))
    return True


def drop_lock(path=LOCK):
    try:
        if int(open(path).read().split()[0]) == os.getpid():
            os.remove(path)
    except (OSError, ValueError, IndexError):
        pass


def cmd_fetch_crypto(a):
    """Tiingo crypto, 5-minute, 5,000 bars a request (about 17 days); resumes from what is stored.
    --max-requests N stops after N requests (short foreground chunks from the scheduled runs)."""
    if not take_lock():
        print("another fetch-crypto holds %s: skipping" % LOCK)
        return 0
    try:
        return _fetch_crypto(a)
    finally:
        drop_lock()


def _fetch_crypto(a):
    import lab
    budget = a.max_requests if getattr(a, "max_requests", 0) else None
    for coin in a.coins.split(","):
        p = os.path.join(STORE, coin + ".json.gz")
        bars = load_gz(p) or {}
        start = datetime.datetime.strptime(CRYPTO_START, "%Y-%m-%d")
        if bars:
            start = datetime.datetime.utcfromtimestamp(max(int(k) for k in bars)) + datetime.timedelta(minutes=5)
        end = datetime.datetime.utcnow()
        while start < end - datetime.timedelta(minutes=10):
            if budget is not None and budget <= 0:
                print("request budget used: stopping (resumes next time)")
                return 0
            if budget is not None:
                budget -= 1
            stop = min(start + datetime.timedelta(days=17), end)
            q = {"tickers": coin, "startDate": start.strftime("%Y-%m-%dT%H:%M:%S"),
                 "endDate": stop.strftime("%Y-%m-%dT%H:%M:%S"), "resampleFreq": "5min"}
            url = "https://api.tiingo.com/tiingo/crypto/prices?" + urllib.parse.urlencode(q)
            req = urllib.request.Request(url, headers={"User-Agent": lab.UA, "Accept": "application/json"})
            for attempt in range(8):
                try:
                    with urllib.request.urlopen(req, timeout=120) as r:
                        data = json.loads(r.read().decode("utf-8"))
                    break
                except urllib.error.HTTPError as e:
                    if e.code == 429 and budget is not None:
                        print("  rate limit: stopping this chunk (resumes next time)", flush=True)
                        return 0
                    if e.code == 429:
                        print("  rate limit; waiting 10 minutes", flush=True)
                        time.sleep(600)
                        continue
                    raise
            else:
                raise SystemExit("Tiingo kept refusing")
            got = 0
            for row in (data[0]["priceData"] if data else []):
                t = datetime.datetime.strptime(row["date"][:19], "%Y-%m-%dT%H:%M:%S")
                ts = int((t - datetime.datetime(1970, 1, 1)).total_seconds())
                bars[str(ts)] = [row["open"], row["high"], row["low"], row["close"], row.get("volume") or 0]
                got += 1
            save_gz(p, bars)
            last = max((int(k) for k in bars), default=0)
            print("%s %s..%s: %d bars (stored %d)" % (coin, start.date(), stop.date(), got, len(bars)), flush=True)
            nxt = datetime.datetime.utcfromtimestamp(last) + datetime.timedelta(minutes=5) if got else stop
            start = max(nxt, start + datetime.timedelta(minutes=5))
            if got == 0:
                start = stop
            time.sleep(a.pause)
    return 0


def cmd_fetch_daily(a):
    import daily
    out = {}
    for m in DAILY_MARKETS:
        try:
            b = daily.parse_daily(daily.fetch_daily(m))
        except Exception as e:  # noqa: BLE001
            print("dropped %s (%s)" % (m, e))
            continue
        out[m] = {k: b[k] for k in ("d", "o", "h", "l", "c", "a")}
        time.sleep(0.5)
    save_gz(os.path.join(STORE, "daily.json.gz"), out)
    print("daily markets stored: %d of %d" % (len(out), len(DAILY_MARKETS)))
    return 0


# ---------------------------------------------------------------- sessions: [(date, [o,h,l,c] list, prev_close)]

def stock_sessions():
    import lab
    out = {}
    for s in lab.UNIVERSE:
        bars = lab.load_store(s, lab.LONG_STORE)
        if not bars:
            continue
        ss = []
        for d, b in lab.sessions_of(lab.drop_after_early_close(bars)):
            if len(b) == lab.SESSION_BARS:
                ss.append((d, [(x["o"], x["h"], x["l"], x["c"]) for x in b]))
        out[s] = ss
    return out


def crypto_sessions(coin, mode):
    import lab
    bars = load_gz(os.path.join(STORE, coin + ".json.gz")) or {}
    days = {}
    for k, v in bars.items():
        utc = datetime.datetime.utcfromtimestamp(int(k))
        if mode == "utc":
            d, slot = utc.date().isoformat(), (utc.hour * 60 + utc.minute) // 5
        else:
            loc = lab.to_eastern(lab.utc_of(int(k)))
            slot = (loc.hour * 60 + loc.minute - lab.OPEN_MIN) // 5
            if not 0 <= slot < 78 or loc.weekday() >= 5:
                continue
            d = loc.date().isoformat()
        days.setdefault(d, {})[slot] = tuple(v[:4])
    need, n = (280, 288) if mode == "utc" else (78, 78)
    out = []
    for d in sorted(days):
        b = days[d]
        if len(b) >= need and 0 in b and 1 in b and (n - 1) in b:
            out.append((d, [b[k] for k in sorted(b)]))
    return out


def sess_ohlc(bars):
    return bars[0][0], max(x[1] for x in bars), min(x[2] for x in bars), bars[-1][3]


# ---------------------------------------------------------------- statistics

def tstat(x):
    if len(x) < 3 or statistics.stdev(x) == 0:
        return 0.0
    return statistics.mean(x) / (statistics.stdev(x) / math.sqrt(len(x)))


def summarize(daily, split):
    """daily: {date: [trade returns]} -> in-sample / judged stats on the equal-weight daily series."""
    ds = sorted(daily)
    ser = [(d, sum(daily[d]) / len(daily[d])) for d in ds]
    f = lambda xs: {"days": len(xs), "trades": 0, "mean_bps": 1e4 * statistics.mean(xs) if xs else 0.0,  # noqa: E731
                    "t": tstat(xs)}
    a = [v for d, v in ser if d < split]
    b = [v for d, v in ser if d >= split]
    out = {"in_sample": f(a), "judged": f(b)}
    out["in_sample"]["trades"] = sum(len(daily[d]) for d in ds if d < split)
    out["judged"]["trades"] = sum(len(daily[d]) for d in ds if d >= split)
    return out


def verdict(s):
    j, i = s["judged"], s["in_sample"]
    return "PASS" if (j["days"] >= 20 and j["mean_bps"] > 0 and j["t"] >= T_BAR and i["t"] > 0) else "FAIL"


def p_two_sided(t):
    return math.erfc(abs(t) / math.sqrt(2))


# ---------------------------------------------------------------- part 1

def part1_trades(groups):
    """{group: {rule: {date: [(dir, raw_long_return)]}}} for the first-candle rules."""
    out = {}
    for g, by_name in groups.items():
        res = {r: {} for r in FIRST_RULES}
        for name, ss in by_name.items():
            for d, bars in ss:
                o, h, l, c = bars[0]
                entry, exit_ = bars[1][0], bars[-1][3]
                if not entry:
                    continue
                raw = exit_ / entry - 1.0
                for r in FIRST_RULES:
                    k = first_rule(r, o, h, l, c)
                    if k:
                        res[r].setdefault(d, []).append((k, raw))
        out[g] = res
    return out


def net(trades, cost_bps):
    return {d: [k * raw - cost_bps / 1e4 for k, raw in v] for d, v in trades.items()}


def placebo(trades, cost_bps, split, real_mean_bps, draws=PLACEBO_DRAWS, seed=7):
    rng, beat = random.Random(seed), 0
    for _ in range(draws):
        dd = {d: [rng.choice((1, -1)) * raw - cost_bps / 1e4 for _, raw in v] for d, v in trades.items() if d >= split}
        ser = [sum(v) / len(v) for v in dd.values()]
        if ser and 1e4 * statistics.mean(ser) >= real_mean_bps:
            beat += 1
    return beat / draws


# ---------------------------------------------------------------- part 2

def part2_trades(dmk):
    out = {r: {} for r in DAILY_RULES}
    for m, b in dmk.items():
        O, H, L, C, A, D = b["o"], b["h"], b["l"], b["c"], b["a"], b["d"]
        for i in range(8, len(D) - 1):
            if D[i] < DAILY_START or None in (O[i], H[i], L[i], C[i]):
                continue
            raw = A[i + 1] / A[i] - 1.0
            for r in DAILY_RULES:
                k = daily_signal(r, O, H, L, C, i)
                if k:
                    out[r].setdefault(D[i + 1], []).append((k, raw, m))
    return out


def daily_cost(m, ref=False):
    tab = REF_COST if ref else COST
    return tab["daily_crypto"] if m.endswith("-USD") else tab["daily"]


# ---------------------------------------------------------------- part 3

def candle_feats(o, h, l, c):
    a = anatomy(o, h, l, c)
    if a is None:
        return [0.0] * (4 + len(TYPES))
    t = ctype(o, h, l, c)
    return ([(c - o) / a["R"], a["up"] / a["R"], a["lo"] / a["R"], (c - l) / a["R"]]
            + [1.0 if t == x else 0.0 for x in TYPES])


def pattern_feats(O, H, L, C, i):
    return [float(daily_signal(r, O, H, L, C, i)) for r in DAILY_RULES]


def ridge_fit(X, y, lam=RIDGE):
    import numpy as np
    X, y = np.asarray(X, float), np.asarray(y, float)
    mu, sd = X.mean(0), X.std(0)
    sd[sd == 0] = 1.0
    Z = (X - mu) / sd
    Z1 = np.hstack([np.ones((len(Z), 1)), Z])
    I = np.eye(Z1.shape[1])
    I[0, 0] = 0.0
    w = np.linalg.solve(Z1.T @ Z1 + lam * I, Z1.T @ (y - 0.0))
    return mu, sd, w


def ridge_pred(model, X):
    import numpy as np
    mu, sd, w = model
    Z = (np.asarray(X, float) - mu) / sd
    return np.hstack([np.ones((len(Z), 1)), Z]) @ w


def first_rows(ss):
    """Feature rows for one name's sessions: (date, features, rest-of-session return)."""
    rows = []
    O, H, L, C = [], [], [], []
    ranges = []
    for k, (d, bars) in enumerate(ss):
        o, h, l, c = bars[0]
        if k >= 14 and len(O) >= 9 and bars[1][0]:
            prev_c = C[-1]
            prev_ret = C[-1] / O[-1] - 1.0 if O[-1] else 0.0
            mean_r = sum(ranges[-14:]) / 14
            f = (candle_feats(o, h, l, c)
                 + [math.log((h - l) / mean_r) if (h - l) > 0 and mean_r > 0 else 0.0,
                    c / o - 1.0 if o else 0.0, o / prev_c - 1.0 if prev_c else 0.0, prev_ret]
                 + pattern_feats(O, H, L, C, len(C) - 1))
            rows.append((d, f, bars[-1][3] / bars[1][0] - 1.0))
        so = sess_ohlc(bars)
        O.append(so[0]); H.append(so[1]); L.append(so[2]); C.append(so[3])  # noqa: E702
        ranges.append(h - l)
    return rows


def combo_run(rows_by_name, split, cost_bps):
    """Fit on in-sample rows (pooled), trade the sign when |pred| > cost. -> {date: [net returns]}, trades by date."""
    tr = [(d, f, y) for rows in rows_by_name.values() for d, f, y in rows if d < split]
    if len(tr) < 50:
        return {}, {}
    model = ridge_fit([f for _, f, _ in tr], [y for _, _, y in tr])
    daily, trades = {}, {}
    for rows in rows_by_name.values():
        if not rows:
            continue
        pred = ridge_pred(model, [f for _, f, _ in rows])
        for (d, f, y), p in zip(rows, pred):
            if abs(p) > cost_bps / 1e4:
                k = 1 if p > 0 else -1
                daily.setdefault(d, []).append(k * y - cost_bps / 1e4)
                trades.setdefault(d, []).append((k, y))
    return daily, trades


def daily_rows(b):
    O, H, L, C, A, D = b["o"], b["h"], b["l"], b["c"], b["a"], b["d"]
    rows, ranges = [], []
    for i in range(len(D) - 1):
        if None in (O[i], H[i], L[i], C[i]):
            ranges.append(0.0)
            continue
        ranges.append(H[i] - L[i])
        if i < 20 or D[i] < DAILY_START:
            continue
        mean_r = sum(ranges[-15:-1]) / 14
        f = (candle_feats(O[i], H[i], L[i], C[i])
             + [math.log((H[i] - L[i]) / mean_r) if H[i] > L[i] and mean_r > 0 else 0.0,
                A[i] / A[i - 1] - 1.0, A[i] / A[i - 5] - 1.0]
             + pattern_feats(O, H, L, C, i))
        rows.append((D[i + 1], f, A[i + 1] / A[i] - 1.0))
    return rows


# ---------------------------------------------------------------- run

def cmd_run(a):
    parts = set(a.parts.split(","))
    tests = []

    def add(part, market, rule, s, trades=None, cost=None, split=None):
        rec = {"part": part, "market": market, "rule": rule, **s, "verdict": verdict(s)}
        if rec["verdict"] == "PASS" and trades is not None:
            rec["placebo_p"] = placebo(trades, cost, split, s["judged"]["mean_bps"])
        tests.append(rec)

    groups, cost_of = {}, {}
    if parts & {"first", "combo"}:
        groups["STOCKS"] = stock_sessions()
        cost_of["STOCKS"] = (COST["stocks"], REF_COST["stocks"])
        for coin in COINS:
            for mode in ("utc", "ny"):
                ss = crypto_sessions(coin, mode)
                if ss:
                    g = "%s_%s" % (coin[:3].upper(), mode.upper())
                    groups[g] = {coin: ss}
                    cost_of[g] = (COST["crypto"], REF_COST["crypto"])
    if "first" in parts:
        p1 = part1_trades(groups)
        for g, res in p1.items():
            for r in FIRST_RULES:
                s = summarize(net(res[r], cost_of[g][0]), SPLIT_5M)
                s["ref_cost_judged_mean_bps"] = summarize(net(res[r], cost_of[g][1]), SPLIT_5M)["judged"]["mean_bps"]
                add("first_candle", g, r, s, res[r], cost_of[g][0], SPLIT_5M)
    dmk = load_gz(os.path.join(STORE, "daily.json.gz")) if parts & {"daily", "combo"} else None
    if "daily" in parts and dmk:
        p2 = part2_trades(dmk)
        for r in DAILY_RULES:
            tr = p2[r]
            nd = {d: [k * raw - daily_cost(m) / 1e4 for k, raw, m in v] for d, v in tr.items()}
            s = summarize(nd, SPLIT_DAILY)
            s["ref_cost_judged_mean_bps"] = summarize(
                {d: [k * raw - daily_cost(m, True) / 1e4 for k, raw, m in v] for d, v in tr.items()},
                SPLIT_DAILY)["judged"]["mean_bps"]
            simple = {d: [(k, raw) for k, raw, _ in v] for d, v in tr.items()}
            add("daily_pattern", "%d markets" % len(dmk), r, s, simple, COST["daily"], SPLIT_DAILY)
    if "combo" in parts:
        for g, by_name in groups.items():
            rows = {n: first_rows(ss) for n, ss in by_name.items()}
            daily, trades = combo_run(rows, SPLIT_5M, cost_of[g][0])
            if daily:
                add("combined", g, "ridge_first_candle", summarize(daily, SPLIT_5M), trades, cost_of[g][0], SPLIT_5M)
        if dmk:
            rows = {m: daily_rows(b) for m, b in dmk.items()}
            daily, trades = combo_run(rows, SPLIT_DAILY, COST["daily"])
            if daily:
                add("combined", "%d markets" % len(dmk), "ridge_daily", summarize(daily, SPLIT_DAILY), trades,
                    COST["daily"], SPLIT_DAILY)
    # Benjamini-Hochberg at 5% over all tests run (one-sided wrong-way t counts as not significant)
    ps = sorted((p_two_sided(x["judged"]["t"]) if x["judged"]["mean_bps"] > 0 else 1.0, k) for k, x in enumerate(tests))
    m = max(len(tests), 1)
    cut = 0
    for rank, (p, k) in enumerate(ps, 1):
        if p <= 0.05 * rank / m:
            cut = rank
    for rank, (p, k) in enumerate(ps, 1):
        tests[k]["bh_significant"] = rank <= cut
    print("%-14s %-16s %-20s %6s %8s %6s | %6s %8s %6s  %s" % ("part", "market", "rule", "IS n", "IS bp", "IS t",
                                                              "J n", "J bp", "J t", "verdict"))
    for x in tests:
        i, j = x["in_sample"], x["judged"]
        print("%-14s %-16s %-20s %6d %+8.1f %+6.2f | %6d %+8.1f %+6.2f  %s%s" % (
            x["part"], x["market"], x["rule"], i["days"], i["mean_bps"], i["t"], j["days"], j["mean_bps"], j["t"],
            x["verdict"], "  placebo p %.3f" % x["placebo_p"] if "placebo_p" in x else ""))
    passes = [x for x in tests if x["verdict"] == "PASS"]
    print("%d tests run (%d registered), %d PASS, %d Benjamini-Hochberg significant" % (
        len(tests), N_TESTS, len(passes), sum(x["bh_significant"] for x in tests)))
    if a.write:
        with open(a.write, "w") as fh:
            json.dump({"tests": tests, "registered": N_TESTS, "t_bar": T_BAR,
                       "markets": sorted(groups), "daily_markets": sorted(dmk) if dmk else []}, fh, indent=1)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    f = sub.add_parser("fetch-crypto")
    f.add_argument("--coins", default=",".join(COINS))
    f.add_argument("--pause", type=float, default=75.0)
    f.add_argument("--max-requests", type=int, default=0, help="stop after N requests (0: no limit)")
    sub.add_parser("fetch-daily")
    r = sub.add_parser("run")
    r.add_argument("--write", nargs="?", const=os.path.join(RESULTS, "candles.json"))
    r.add_argument("--parts", default="first,daily,combo")
    a = ap.parse_args(argv)
    if a.cmd == "fetch-crypto":
        return cmd_fetch_crypto(a)
    if a.cmd == "fetch-daily":
        return cmd_fetch_daily(a)
    if a.cmd == "run":
        return cmd_run(a)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
