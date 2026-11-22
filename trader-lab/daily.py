#!/usr/bin/env python3
"""trader-lab daily engine: test day-trading rules on 20-30+ years of daily bars.

Many day-trading rules only need each day's open, high, low and close: enter at the
open (or on a stop order during the day) and exit at the close. Yahoo serves daily
bars back to each listing date (SPY: 1993), which gives about 100x the trades of the
60-day 5-minute store, so a real edge can be told apart from luck.

    python3 daily.py fetch                    # full daily history for the universe
    python3 daily.py backtest                 # every rule and variant, three periods, after costs
    python3 daily.py backtest --only ibs,rsi2 --json
    python3 daily.py signal                   # which rules fire for the next session

Periods (fixed in advance, never moved after seeing results):
  IS       start to 2014-12-31  variants are chosen here only
  OOS      2015-01-01 to 2021-12-31
  HOLDOUT  2022-01-01 to today  looked at last, never used to choose anything

A rule passes only if the chosen variant has IS t >= 2, OOS mean > 0 and HOLDOUT mean > 0,
and its deflated Sharpe ratio (Bailey & Lopez de Prado 2014), which charges for every
variant tried across the whole lab, is >= 0.95 on OOS + HOLDOUT together.

Hold types:
  oc     enter at the open, exit at the close (a day trade)
  stop   enter on a stop order during the day, exit at the close (a day trade); with an
         optional stop-loss, a day whose range covers both is counted as the loss
  cc     enter at the close, exit at the next close (an overnight swing, shown separately)
  co     enter at the close, exit at the next open (overnight only, shown separately)

Research, not financial advice.
"""

import argparse
import datetime
import gzip
import json
import math
import os
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (compatible; day-trader-skill/2.0; +https://github.com/Jakeschincariol/day-trader-skill)"
HERE = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.join(HERE, "data", "daily")
RESULTS = os.path.join(HERE, "results")
PAUSE = 0.5
UNIVERSE = ["SPY", "QQQ", "IWM", "DIA", "MDY", "XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI",
            "XLU", "XLB", "SMH", "TLT", "GLD", "EEM", "EFA",
            "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "AMD", "AVGO", "NFLX",
            "JPM", "XOM", "LLY", "UNH", "WMT", "COST", "ORCL", "INTC", "BA", "NKE", "MU"]
DATA_START = "1996-01-01"  # Yahoo's daily opens before the mid-1990s are often copies of the close
IS_END = "2014-12-31"
OOS_END = "2021-12-31"
COST_BPS = 2.0
MIN_IS_T = 2.0
DSR_MIN = 0.95     # reported; the deflated Sharpe bar
POST_T = 3.0       # Harvey, Liu & Zhu (2016): t >= 3 for a new factor after heavy data mining


class LabError(Exception):
    pass


# ---------------------------------------------------------------- data

def fetch_daily(sym):
    url = ("https://%s.finance.yahoo.com/v8/finance/chart/%s?period1=0&period2=9999999999&interval=1d")
    last = None
    for host in ("query2", "query1"):
        for attempt in (0, 1):
            try:
                req = urllib.request.Request(url % (host, urllib.parse.quote(sym.replace(".", "-"))),
                                             headers={"User-Agent": UA, "Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    return r.read().decode("utf-8", "replace")
            except urllib.error.HTTPError as e:
                last = e.code
                if e.code == 429 and attempt == 0:
                    time.sleep(5)
                    continue
                break
            except (urllib.error.URLError, OSError) as e:
                raise LabError("could not reach Yahoo: %s" % getattr(e, "reason", e))
        time.sleep(PAUSE)
    raise LabError("Yahoo answered HTTP %s for %s" % (last, sym))


def parse_daily(text):
    """-> {"d": [dates], "o": [], "h": [], "l": [], "c": [], "v": []}, complete bars only, oldest first."""
    res = ((json.loads(text).get("chart") or {}).get("result") or [None])[0]
    if not res:
        raise LabError("no daily data")
    q = ((res.get("indicators") or {}).get("quote") or [{}])[0]
    off = (res.get("meta") or {}).get("gmtoffset", -18000) or -18000
    out = {k: [] for k in "dohlcv"}
    seen = set()
    for i, ts in enumerate(res.get("timestamp") or []):
        row = [(q.get(k) or [None] * (i + 1))[i] for k in ("open", "high", "low", "close", "volume")]
        if ts is None or None in row[:4] or min(row[:4]) <= 0:
            continue
        d = (datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=int(ts) + off)).date().isoformat()
        if d in seen:
            continue
        seen.add(d)
        if not (row[2] <= min(row[0], row[3]) + 1e-9 and row[1] >= max(row[0], row[3]) - 1e-9):
            continue  # a bad print: high/low do not contain open/close
        out["d"].append(d)
        for k, x in zip("ohlcv", row):
            out[k].append(float(x or 0))
    return out


def store_path(sym, store=STORE):
    return os.path.join(store, "%s.json.gz" % sym.upper())


def load(sym, store=STORE):
    p = store_path(sym, store)
    if not os.path.exists(p):
        return None
    with gzip.open(p, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def save(sym, D, store=STORE):
    os.makedirs(store, exist_ok=True)
    with gzip.GzipFile(store_path(sym, store), "wb", mtime=0) as gz:
        gz.write(json.dumps(D, separators=(",", ":")).encode("utf-8"))


# ---------------------------------------------------------------- indicators (all use data up to day i-1)

def sma(c, i, n):
    """Mean of closes i-n .. i-1 (the n closes before day i)."""
    if i < n:
        return None
    return sum(c[i - n:i]) / float(n)


def rsi(c, i, n):
    """Wilder-style RSI over the n closes up to i-1, simple average version (Connors uses this for RSI(2))."""
    if i < n + 1:
        return None
    up = dn = 0.0
    for j in range(i - n, i):
        ch = c[j] - c[j - 1]
        if ch > 0:
            up += ch
        else:
            dn -= ch
    if up + dn == 0:
        return 50.0
    return 100.0 * up / (up + dn)


def ibs(D, j):
    rng = D["h"][j] - D["l"][j]
    return (D["c"][j] - D["l"][j]) / rng if rng > 0 else 0.5


def rng(D, j):
    return D["h"][j] - D["l"][j]


def trading_gap_days(D, i):
    """Calendar days from day i to the next trading day in the data (3 = a normal weekend)."""
    if i + 1 >= len(D["d"]):
        return None
    a = datetime.date(*map(int, D["d"][i].split("-")))
    b = datetime.date(*map(int, D["d"][i + 1].split("-")))
    return (b - a).days


def weekday(D, i):
    return datetime.date(*map(int, D["d"][i].split("-"))).weekday()


# ---------------------------------------------------------------- rules
# rule(D, i, p) decides for day i using closes up to i-1 and, for oc/stop rules, day i's OPEN.
# returns None, or {"side": +1/-1, "hold": "oc"|"stop"|"cc"|"co", "entry": price (stop only), "sl": price}

def r_baseline(D, i, p):
    return {"side": 1, "hold": p["hold"]}


def r_ibs(D, i, p):
    """Connors / Pagonidis: buy after a close near the day's low (IBS < x)."""
    if i < 1:
        return None
    v = ibs(D, i - 1)
    if p["side"] > 0 and v < p["x"]:
        return {"side": 1, "hold": p["hold"]}
    if p["side"] < 0 and v > 1 - p["x"]:
        return {"side": -1, "hold": p["hold"]}
    return None


def r_rsi2(D, i, p):
    """Connors RSI(2): long when RSI(2) < x and close above the 200-day average."""
    r = rsi(D["c"], i, 2)
    m = sma(D["c"], i, 200)
    if r is None or m is None:
        return None
    if r < p["x"] and (not p["trend"] or D["c"][i - 1] > m):
        return {"side": 1, "hold": p["hold"]}
    return None


def r_downdays(D, i, p):
    """N consecutive lower closes, then long."""
    n = p["n"]
    if i < n + 1:
        return None
    if all(D["c"][j] < D["c"][j - 1] for j in range(i - n, i)):
        return {"side": 1, "hold": p["hold"]}
    return None


def r_gap(D, i, p):
    """Gap from yesterday's close to today's open, faded or followed to the close."""
    if i < 1:
        return None
    g = D["o"][i] / D["c"][i - 1] - 1
    if abs(g) * 100 < p["min"] or (p.get("max") and abs(g) * 100 > p["max"]):
        return None
    side = -1 if g > 0 else 1
    if p["mode"] == "go":
        side = -side
    if p.get("dir") == "down" and g > 0:
        return None
    if p.get("dir") == "up" and g < 0:
        return None
    return {"side": side, "hold": "oc"}


def r_wvb(D, i, p):
    """Larry Williams volatility breakout: buy stop at open + k x yesterday's range, out at the close."""
    if i < 1:
        return None
    r = rng(D, i - 1)
    if r <= 0:
        return None
    if p["side"] > 0:
        return {"side": 1, "hold": "stop", "entry": D["o"][i] + p["k"] * r}
    return {"side": -1, "hold": "stop", "entry": D["o"][i] - p["k"] * r}


def r_nr(D, i, p):
    """Crabel: after the narrowest range of the last n days (NR4 / NR7), trade the break of that day's
    high (buy stop) or low (sell stop), out at the close."""
    n = p["n"]
    if i < n:
        return None
    rs = [rng(D, j) for j in range(i - n, i)]
    if rs[-1] > min(rs):
        return None
    if p.get("inside") and not (D["h"][i - 1] <= D["h"][i - 2] and D["l"][i - 1] >= D["l"][i - 2]):
        return None
    if p["side"] > 0:
        return {"side": 1, "hold": "stop", "entry": D["h"][i - 1], "sl": D["l"][i - 1] if p["sl"] else None}
    return {"side": -1, "hold": "stop", "entry": D["l"][i - 1], "sl": D["h"][i - 1] if p["sl"] else None}


def r_oops(D, i, p):
    """Larry Williams Oops!: open gaps below yesterday's low, buy stop at yesterday's low (and the mirror)."""
    if i < 1:
        return None
    if p["side"] > 0 and D["o"][i] < D["l"][i - 1] * (1 - p["min"] / 100.0):
        return {"side": 1, "hold": "stop", "entry": D["l"][i - 1]}
    if p["side"] < 0 and D["o"][i] > D["h"][i - 1] * (1 + p["min"] / 100.0):
        return {"side": -1, "hold": "stop", "entry": D["h"][i - 1]}
    return None


def r_dow(D, i, p):
    """Day of week: long the chosen weekday."""
    if weekday(D, i) == p["day"]:
        return {"side": 1, "hold": p["hold"]}
    return None


def r_tom(D, i, p):
    """Turn of month: the last trading day of the month and the first `n` of the next."""
    d = D["d"]
    if i < 1 or i + 1 >= len(d):
        return None
    month = d[i][:7]
    # position from the end of this month (0 = last day), and from the start (1 = first day)
    k_start = 1
    j = i - 1
    while j >= 0 and d[j][:7] == month:
        k_start += 1
        j -= 1
    last = d[i + 1][:7] != month
    if last or k_start <= p["n"]:
        return {"side": 1, "hold": p["hold"]}
    return None


def r_preholiday(D, i, p):
    """The trading day before a market holiday (the next trading day is 2+ calendar days away
    on a weekday, or 4+ over a weekend)."""
    g = trading_gap_days(D, i)
    if g is None:
        return None
    wd = weekday(D, i)
    if (wd < 4 and g >= 2) or (wd == 4 and g >= 4):
        return {"side": 1, "hold": p["hold"]}
    return None


def r_prevday(D, i, p):
    """Yesterday's open-to-close move: follow it (mom) or fade it (rev) from today's open."""
    if i < 1:
        return None
    r = D["c"][i - 1] / D["o"][i - 1] - 1
    if abs(r) * 100 < p["min"]:
        return None
    side = 1 if r > 0 else -1
    if p["mode"] == "rev":
        side = -side
    return {"side": side, "hold": "oc"}


def r_3low(D, i, p):
    """Connors: close below the lowest low of the prior n days, above the 200-day average -> long."""
    n = p["n"]
    if i < max(n + 2, 201):
        return None
    if D["c"][i - 1] < min(D["l"][i - 1 - n:i - 1]) and D["c"][i - 1] > sma(D["c"], i, 200):
        return {"side": 1, "hold": p["hold"]}
    return None


def r_turnaround(D, i, p):
    """Turnaround Tuesday: Monday closes down >= x% vs Friday -> buy Monday's close, sell Tuesday's close."""
    if i < 2 or weekday(D, i) != 1 or weekday(D, i - 1) != 0:
        return None
    if D["c"][i - 1] / D["c"][i - 2] - 1 <= -p["x"] / 100.0:
        return {"side": 1, "hold": p["hold"]}
    return None


def r_smash(D, i, p):
    """Larry Williams smash day: yesterday closed below the day before's low (a smash) ->
    buy stop at yesterday's high today, stop-loss at yesterday's low, out at the close."""
    if i < 2:
        return None
    if p["side"] > 0 and D["c"][i - 1] < D["l"][i - 2]:
        return {"side": 1, "hold": "stop", "entry": D["h"][i - 1], "sl": D["l"][i - 1] if p["sl"] else None}
    if p["side"] < 0 and D["c"][i - 1] > D["h"][i - 2]:
        return {"side": -1, "hold": "stop", "entry": D["l"][i - 1], "sl": D["h"][i - 1] if p["sl"] else None}
    return None


def r_soup(D, i, p):
    """Raschke/Connors Turtle Soup Plus One: yesterday closed at or below the prior 20-day low, which is
    3+ days old -> buy stop at that old low today, stop at yesterday's low, out at the close."""
    n = 20
    if i < n + 3:
        return None
    window = D["l"][i - 1 - n:i - 1]
    lo = min(window)
    age = n - 1 - max(k for k, v in enumerate(window) if v == lo)
    if p["side"] > 0 and D["c"][i - 1] <= lo and age >= 3:
        return {"side": 1, "hold": "stop", "entry": lo, "sl": D["l"][i - 1]}
    hw = D["h"][i - 1 - n:i - 1]
    hi = max(hw)
    age = n - 1 - max(k for k, v in enumerate(hw) if v == hi)
    if p["side"] < 0 and D["c"][i - 1] >= hi and age >= 3:
        return {"side": -1, "hold": "stop", "entry": hi, "sl": D["h"][i - 1]}
    return None


def r_8020(D, i, p):
    """Raschke 80-20: yesterday opened in the top 20% of its range and closed in the bottom 20%.
    If today opens below yesterday's low, buy stop at yesterday's low; stop at today's open; out at close."""
    if i < 1:
        return None
    r = rng(D, i - 1)
    if r <= 0:
        return None
    o, c, lo, hi = D["o"][i - 1], D["c"][i - 1], D["l"][i - 1], D["h"][i - 1]
    if (o - lo) / r >= 0.8 and (c - lo) / r <= 0.2 and D["o"][i] < lo:
        return {"side": 1, "hold": "stop", "entry": lo, "sl": D["o"][i] if p["sl"] else None}
    return None


def r_stretch(D, i, p):
    """Crabel stretch: stop entry at open +- m x (10-day average of min(high - open, open - low)),
    optionally only after an NR7 day; stop-loss at the opposite stretch; out at the close."""
    if i < 11:
        return None
    noise = [min(D["h"][j] - D["o"][j], D["o"][j] - D["l"][j]) for j in range(i - 10, i)]
    st = p["m"] * sum(noise) / 10.0
    if st <= 0:
        return None
    if p["nr7"]:
        rs = [rng(D, j) for j in range(i - 7, i)]
        if rs[-1] > min(rs):
            return None
    o = D["o"][i]
    if p["side"] > 0:
        return {"side": 1, "hold": "stop", "entry": o + st, "sl": o - st}
    return {"side": -1, "hold": "stop", "entry": o - st, "sl": o + st}


def r_gsv(D, i, p):
    """Larry Williams greatest swing value: buy stop at open + 1.8 x mean(high - open) over the
    last 4 down closes; stop 1.5 x that below the entry; out at the close."""
    if i < 30:
        return None
    sw = []
    j = i - 1
    while j > 0 and len(sw) < 4:
        if D["c"][j] < D["c"][j - 1]:
            sw.append(D["h"][j] - D["o"][j])
        j -= 1
    if len(sw) < 4:
        return None
    g = sum(sw) / 4.0
    e = D["o"][i] + p["m"] * g
    return {"side": 1, "hold": "stop", "entry": e, "sl": e - 1.5 * g}


# ---------------------------------------------------------------- swing rules (multi-day, marked to market)
# entry(D, j, p) at the close of day j -> side or 0; exit(D, k, p, j) at the close of day k -> bool.

def ema_series(c, n):
    out, k, e = [], 2.0 / (n + 1), None
    for x in c:
        e = x if e is None else e + k * (x - e)
        out.append(e)
    return out


def sw_rsi2(D, j, p):
    r = rsi(D["c"], j + 1, 2)
    m = sma(D["c"], j + 1, 200)
    return 1 if (r is not None and m is not None and r < p["x"] and D["c"][j] > m) else 0


def sw_crsi2(D, j, p):
    """Connors cumulative RSI(2): sum of RSI(2) over the last 2 days < x, above the 200-day."""
    m = sma(D["c"], j + 1, 200)
    a, b = rsi(D["c"], j + 1, 2), rsi(D["c"], j, 2)
    return 1 if (m is not None and a is not None and b is not None and a + b < p["x"] and D["c"][j] > m) else 0


def sw_r3(D, j, p):
    """Connors R3: above the 200-day, RSI(2) down 3 days in a row from below 60, today < 10."""
    m = sma(D["c"], j + 1, 200)
    if m is None or D["c"][j] <= m or j < 205:
        return 0
    r = [rsi(D["c"], j + 1 - k, 2) for k in (3, 2, 1, 0)]
    if None in r:
        return 0
    return 1 if (r[0] < 60 and r[0] > r[1] > r[2] > r[3] and r[3] < 10) else 0


def sw_mdd(D, j, p):
    """Connors multiple days down: above the 200-day, below the 5-day, 4+ down closes of the last 5."""
    m, m5 = sma(D["c"], j + 1, 200), sma(D["c"], j + 1, 5)
    if m is None or j < 6:
        return 0
    downs = sum(1 for k in range(j - 4, j + 1) if D["c"][k] < D["c"][k - 1])
    return 1 if (D["c"][j] > m and D["c"][j] < m5 and downs >= 4) else 0


def sw_3hl(D, j, p):
    """Connors 3-day high/low: above the 200-day, below the 5-day, 3 days of lower highs and lower lows."""
    m, m5 = sma(D["c"], j + 1, 200), sma(D["c"], j + 1, 5)
    if m is None or j < 4:
        return 0
    lh = all(D["h"][k] < D["h"][k - 1] and D["l"][k] < D["l"][k - 1] for k in range(j - 2, j + 1))
    return 1 if (D["c"][j] > m and D["c"][j] < m5 and lh) else 0


def sw_d7(D, j, p):
    """Connors Double 7s: above the 200-day, the close is the lowest of the last 7."""
    m = sma(D["c"], j + 1, 200)
    if m is None:
        return 0
    return 1 if (D["c"][j] > m and D["c"][j] <= min(D["c"][j - 6:j + 1])) else 0


def sw_bb(D, j, p):
    """Close below the lower Bollinger band (20, k), optionally above the 200-day."""
    if j < 200:
        return 0
    w = D["c"][j - 19:j + 1]
    mu = sum(w) / 20.0
    sd = statistics.pstdev(w)
    if p["trend"] and D["c"][j] <= sma(D["c"], j + 1, 200):
        return 0
    return 1 if D["c"][j] < mu - p["k"] * sd else 0


def sw_ibs(D, j, p):
    return 1 if ibs(D, j) < p["x"] else 0


def sw_donchian(D, j, p):
    """Close above the prior n-day high: long (trend following)."""
    if j < p["n"] + 1:
        return 0
    return 1 if D["c"][j] > max(D["h"][j - p["n"]:j]) else 0


def ex_sma5(D, k, p, j):
    return D["c"][k] > sma(D["c"], k + 1, 5)


def ex_rsi(D, k, p, j):
    r = rsi(D["c"], k + 1, 2)
    return r is not None and r > p.get("out", 70)


def ex_high7(D, k, p, j):
    return D["c"][k] >= max(D["c"][k - 6:k + 1])


def ex_mid(D, k, p, j):
    return D["c"][k] > sum(D["c"][k - 19:k + 1]) / 20.0


def ex_upclose(D, k, p, j):
    return D["c"][k] > D["c"][k - 1]


def ex_donchian(D, k, p, j):
    return D["c"][k] < min(D["l"][k - p["x"]:k])


EXITS = {"sma5": ex_sma5, "rsi": ex_rsi, "high7": ex_high7, "mid": ex_mid, "up": ex_upclose,
         "donch": ex_donchian}


VIX = {}   # date -> VIX close, filled by load_universe from data/daily/^VIX.json.gz


def vix_ok(date_prev, p):
    """VIX regime gate on the signal day's close: 'high' = above its trailing 252-day median."""
    g = p.get("vix", "any")
    if g == "any":
        return True
    info = VIX.get(date_prev)
    if info is None:
        return False
    v, med = info
    return v > med if g == "high" else v <= med


def run_swing(D, entry, p, cost_bps):
    """Enter at the close of a signal day, mark to market each close, exit at the close the exit fires
    (or after max_days). -> ({date: bps}, trades). Cost is charged on the exit day."""
    out = {}
    n_tr = 0
    ex = EXITS[p["exit"]]
    maxd = p.get("max_days", 10)
    c = D["c"]
    j = 0
    N = len(c)
    while j < N - 1:
        if j < 21 or not entry(D, j, p) or not vix_ok(D["d"][j], p):
            j += 1
            continue
        n_tr += 1
        k = j + 1
        while k < N:
            base = D["o"][k] if (k == j + 1 and p.get("fill") == "open") else c[k - 1]
            out[D["d"][k]] = (c[k] / base - 1) * 1e4
            if ex(D, k, p, j) or k - j >= maxd:
                out[D["d"][k]] -= cost_bps
                break
            k += 1
        j = k
    return out, n_tr


def r_ccrev(D, i, p):
    """Baltussen, van Bekkum & Da (2019): index daily reversal. Fade yesterday's close-to-close move,
    open to close today, when it was bigger than x%."""
    if i < 2:
        return None
    r = D["c"][i - 1] / D["c"][i - 2] - 1
    if abs(r) * 100 < p["x"]:
        return None
    return {"side": -1 if r > 0 else 1, "hold": "oc"}


def r_gapfill(D, i, p):
    """Small-gap fade with a target at yesterday's close: if the day reaches it, exit there,
    else at the close (daily bars: a day that also hit the stop is counted as stopped)."""
    if i < 1:
        return None
    pc = D["c"][i - 1]
    g = D["o"][i] / pc - 1
    if not (p["lo"] <= abs(g) * 100 < p["hi"]):
        return None
    side = -1 if g > 0 else 1
    return {"side": side, "hold": "target", "target": pc}


def r_overnight_trend(D, i, p):
    """Quantpedia: hold close to open only when the close is above its 20-day average."""
    if i < 22:
        return None
    if D["c"][i - 1] > sma(D["c"], i, 20):
        return {"side": 1, "hold": "co"}
    return None


def r_tlt_eom(D, i, p):
    """Month-end index-extension buying: long the last n trading days of the month (close to close)."""
    d = D["d"]
    if i + p["n"] >= len(d):
        return None
    m = d[i][:7]
    if d[i + p["n"] - 1][:7] == m and d[i + p["n"]][:7] != m:
        pass
    # day i is within the last n trading days of its month
    k = i
    left = 0
    while k + 1 < len(d) and d[k + 1][:7] == m:
        left += 1
        k += 1
    if left < p["n"]:
        return {"side": 1, "hold": "cc"}
    return None


def r_opex(D, i, p):
    """Option-expiration week: Monday to the third Friday of the month (close to close)."""
    dt = datetime.date(*map(int, D["d"][i].split("-")))
    first = dt.replace(day=1)
    third_fri = first + datetime.timedelta(days=(4 - first.weekday()) % 7 + 14)
    if third_fri - datetime.timedelta(days=4) <= dt <= third_fri:
        return {"side": 1, "hold": p["hold"]}
    return None


STOP_RULES = ("wvb", "nr", "oops", "smash", "soup", "8020", "stretch", "gsv")


def grid(d):
    keys = sorted(d)
    out = [{}]
    for k in keys:
        out = [dict(x, **{k: v}) for x in out for v in d[k]]
    return out


RULES = {
    "base": {"fn": r_baseline, "source": "buy and hold, split into day (oc) and overnight (co)",
             "grid": {"hold": ["oc", "co", "cc"]}},
    "ibs": {"fn": r_ibs, "source": "Pagonidis 2013 / Connors: internal bar strength",
            "grid": {"x": [0.1, 0.2, 0.3], "side": [1, -1], "hold": ["oc", "cc"]}},
    "rsi2": {"fn": r_rsi2, "source": "Connors & Alvarez 2008, Short Term Trading Strategies That Work",
             "grid": {"x": [5, 10], "trend": [True, False], "hold": ["oc", "cc"]}},
    "down": {"fn": r_downdays, "source": "consecutive down closes (Connors, QuantifiedStrategies)",
             "grid": {"n": [2, 3, 4], "hold": ["oc", "cc"]}},
    "gap": {"fn": r_gap, "source": "opening gap fade / go, open to close",
            "grid": {"min": [0.25, 0.5, 1.0], "mode": ["fade", "go"], "dir": ["up", "down"]}},
    "wvb": {"fn": r_wvb, "source": "Larry Williams, Long-Term Secrets to Short-Term Trading: volatility breakout",
            "grid": {"k": [0.3, 0.5, 0.7], "side": [1, -1]}},
    "nr": {"fn": r_nr, "source": "Toby Crabel 1990: NR4 / NR7, inside day",
           "grid": {"n": [4, 7], "side": [1, -1], "inside": [False, True], "sl": [False, True]}},
    "oops": {"fn": r_oops, "source": "Larry Williams: Oops! gap reversal",
             "grid": {"min": [0.0, 0.5], "side": [1, -1]}},
    "dow": {"fn": r_dow, "source": "day-of-week effect (French 1980; Monday effect)",
            "grid": {"day": [0, 1, 2, 3, 4], "hold": ["oc", "cc"]}},
    "tom": {"fn": r_tom, "source": "turn of the month (Ariel 1987; Lakonishok & Smidt 1988)",
            "grid": {"n": [1, 3], "hold": ["oc", "cc"]}},
    "prehol": {"fn": r_preholiday, "source": "pre-holiday effect (Ariel 1990)",
               "grid": {"hold": ["oc", "cc"]}},
    "prev": {"fn": r_prevday, "source": "yesterday's open-to-close: momentum or reversal",
             "grid": {"min": [0.0, 1.0], "mode": ["mom", "rev"]}},
    "lowx": {"fn": r_3low, "source": "Connors: close below the n-day low in an uptrend",
             "grid": {"n": [3, 5], "hold": ["oc", "cc"]}},
    "tuesday": {"fn": r_turnaround, "source": "Turnaround Tuesday (QuantifiedStrategies; StrategyQuant)",
                "grid": {"x": [0.0, 1.0], "hold": ["cc", "oc"]}},
    "smash": {"fn": r_smash, "source": "Larry Williams smash day reversal",
              "grid": {"side": [1, -1], "sl": [False, True]}},
    "soup": {"fn": r_soup, "source": "Connors & Raschke 1995, Street Smarts: Turtle Soup Plus One",
             "grid": {"side": [1, -1]}},
    "8020": {"fn": r_8020, "source": "Connors & Raschke 1995, Street Smarts: 80-20",
             "grid": {"sl": [False, True]}},
    "stretch": {"fn": r_stretch, "source": "Toby Crabel 1990: stretch breakout",
                "grid": {"m": [1.0, 2.0], "nr7": [False, True], "side": [1, -1]}},
    "ccrev": {"fn": r_ccrev, "source": "Baltussen, van Bekkum & Da 2019 JFE: index daily reversal",
              "grid": {"x": [0.0, 0.5, 1.0]}},
    "gapfill": {"fn": r_gapfill, "source": "small-gap fill to yesterday's close (Plastun et al. 2020; practitioner stats)",
                "grid": {"lo": [0.1, 0.25], "hi": [0.5, 1.0]}},
    "ontrend": {"fn": r_overnight_trend, "source": "Quantpedia: overnight anomaly with a trend filter",
                "grid": {"x": [1]}},
    "eom": {"fn": r_tlt_eom, "source": "month-end index extension (TLT, QuantifiedStrategies)",
            "grid": {"n": [3, 5]}},
    "opex": {"fn": r_opex, "source": "Stivers & Sun 2013: option-expiration week",
             "grid": {"hold": ["oc", "cc"]}},
    "gsv": {"fn": r_gsv, "source": "Larry Williams 1999: greatest swing value",
            "grid": {"m": [1.0, 1.8]}},
}

SWING = {
    "s_rsi2": {"fn": sw_rsi2, "source": "Connors RSI(2), exit above the 5-day or RSI(2) > 70",
               "grid": {"x": [5, 10], "exit": ["sma5", "rsi"], "fill": ["close", "open"]}},
    "s_rsi2v": {"fn": sw_rsi2, "source": "RSI(2) with a VIX regime gate (Quantpedia; Zarattini et al. VIX > 20)",
                "grid": {"x": [10], "exit": ["sma5"], "fill": ["open"], "vix": ["high", "low"]}},
    "s_d7v": {"fn": sw_d7, "source": "Double 7s with a VIX regime gate",
              "grid": {"exit": ["high7"], "max_days": [30], "fill": ["open"], "vix": ["high", "low"]}},
    "s_crsi2": {"fn": sw_crsi2, "source": "Connors & Alvarez 2009: cumulative RSI(2)",
                "grid": {"x": [35, 50], "exit": ["rsi"], "out": [65], "fill": ["close", "open"]}},
    "s_r3": {"fn": sw_r3, "source": "Connors 2009, High Probability ETF Trading: R3",
             "grid": {"exit": ["rsi"]}},
    "s_mdd": {"fn": sw_mdd, "source": "Connors 2009: multiple days down", "grid": {"exit": ["sma5"]}},
    "s_3hl": {"fn": sw_3hl, "source": "Connors & Alvarez: 3-day high/low", "grid": {"exit": ["sma5"]}},
    "s_d7": {"fn": sw_d7, "source": "Connors & Alvarez: Double 7s", "grid": {"exit": ["high7"], "max_days": [30], "fill": ["close", "open"]}},
    "s_bb": {"fn": sw_bb, "source": "Bollinger lower-band reversion",
             "grid": {"k": [1.5, 2.0], "trend": [True, False], "exit": ["mid", "up"]}},
    "s_ibs": {"fn": sw_ibs, "source": "IBS < x, exit on the first up close",
              "grid": {"x": [0.1, 0.2], "exit": ["up"], "fill": ["close", "open"]}},
    "s_donch": {"fn": sw_donchian, "source": "Donchian breakout (trend following)",
                "grid": {"n": [20, 55], "exit": ["donch"], "x": [10, 20], "max_days": [60]}},
}


# ---------------------------------------------------------------- execution

def fill(D, i, sig):
    """-> (entry, exit) for day i, or None if a stop entry never triggered."""
    h, l, o, c = D["h"][i], D["l"][i], D["o"][i], D["c"][i]
    hold = sig["hold"]
    s = sig["side"]
    if hold == "oc":
        return o, c
    if hold == "stop":
        e = sig["entry"]
        if s > 0:
            if h < e:
                return None
            px = max(e, o)
        else:
            if l > e:
                return None
            px = min(e, o)
        sl = sig.get("sl")
        if sl is not None:
            # daily bars hide the order of the high and the low: count a day that touched both as stopped
            if (s > 0 and l <= sl) or (s < 0 and h >= sl):
                return px, sl
        return px, c
    if hold == "target":
        t = sig["target"]
        if (s > 0 and h >= t) or (s < 0 and l <= t):
            return o, t
        return o, c
    if hold == "cc":  # bought at the close of i-1
        return D["c"][i - 1], c
    if hold == "co":  # bought at the close of i-1, out at the open of i
        return D["c"][i - 1], o
    raise LabError("unknown hold %s" % hold)


def run_rule(D, fn, p, cost_bps):
    """-> {date: net bps} for every day the rule traded."""
    out = {}
    for i in range(1, len(D["d"])):
        sig = fn(D, i, p)
        if not sig:
            continue
        f = fill(D, i, sig)
        if f is None:
            continue
        e, x = f
        out[D["d"][i]] = sig["side"] * (x / e - 1) * 1e4 - cost_bps
    return out


# ---------------------------------------------------------------- statistics

def norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def norm_ppf(p):
    """Acklam's rational approximation, good to about 1e-9."""
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02,
         -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01,
         -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00,
         4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00]
    if p < 0.02425:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > 1 - 0.02425:
        return -norm_ppf(1 - p)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def moments(x):
    n = len(x)
    m = sum(x) / n
    var = sum((v - m) ** 2 for v in x) / n
    if var <= 0:
        return m, 0.0, 0.0, 3.0
    sd = math.sqrt(var)
    skew = sum((v - m) ** 3 for v in x) / n / sd ** 3
    kurt = sum((v - m) ** 4 for v in x) / n / sd ** 4
    return m, sd, skew, kurt


def deflated_sharpe(series, n_trials, sr_trials_var):
    """Bailey & Lopez de Prado (2014). Probability that the true (per-period) Sharpe is above the
    best Sharpe expected from n_trials unskilled tries whose Sharpes vary by sr_trials_var."""
    n = len(series)
    if n < 30:
        return 0.0
    m, sd, skew, kurt = moments(series)
    if sd == 0:
        return 0.0
    sr = m / sd
    emc = 0.5772156649
    if n_trials > 1 and sr_trials_var > 0:
        sr0 = math.sqrt(sr_trials_var) * ((1 - emc) * norm_ppf(1 - 1.0 / n_trials)
                                          + emc * norm_ppf(1 - 1.0 / (n_trials * math.e)))
    else:
        sr0 = 0.0
    den = 1 - skew * sr + (kurt - 1) / 4.0 * sr * sr
    if den <= 0:
        return 0.0
    return norm_cdf((sr - sr0) * math.sqrt(n - 1) / math.sqrt(den))


def robust_var(x):
    """Variance of the trial Sharpes from the median absolute deviation (1.4826 x MAD)^2, so a few
    cost-crushed variants far below zero do not inflate the bar for everyone."""
    if len(x) < 3:
        return 0.0
    med = statistics.median(x)
    mad = statistics.median([abs(v - med) for v in x])
    return (1.4826 * mad) ** 2


def stats(series):
    n = len(series)
    if n < 2:
        return {"n": n, "mean": series[0] if n else 0.0, "t": 0.0, "sharpe": 0.0}
    m = statistics.mean(series)
    sd = statistics.pstdev(series)
    return {"n": n, "mean": m, "t": (m / sd * math.sqrt(n)) if sd > 0 else 0.0,
            "sharpe": (m / sd * math.sqrt(252)) if sd > 0 else 0.0}


# ---------------------------------------------------------------- backtest

def period_of(d):
    return "is" if d <= IS_END else ("oos" if d <= OOS_END else "ho")


def portfolio(per_sym, all_dates):
    """Equal weight across the symbols that traded that day; a day with no trade earns 0.
    Only dates where at least one symbol has data are counted."""
    by_day = {}
    for trades in per_sym.values():
        for d, r in trades.items():
            by_day.setdefault(d, []).append(r)
    return [(d, statistics.mean(by_day[d]) if d in by_day else 0.0) for d in all_dates]


def backtest(universe, cost_bps=COST_BPS, only=None):
    all_dates = sorted({d for D in universe.values() for d in D["d"]})
    variants = []
    jobs = [(n, s, False) for n, s in RULES.items()] + [(n, s, True) for n, s in SWING.items()]
    for name, spec, swing in jobs:
        if only and name not in only:
            continue
        for p in grid(spec["grid"]):
            if swing:
                runs = {s: run_swing(D, spec["fn"], p, cost_bps) for s, D in universe.items()}
                per_sym = {s: r[0] for s, r in runs.items()}
                n_tr = sum(r[1] for r in runs.values())
                hold = "mc"
            else:
                per_sym = {s: run_rule(D, spec["fn"], p, cost_bps) for s, D in universe.items()}
                n_tr = sum(len(t) for t in per_sym.values())
                hold = p.get("hold", "stop" if name in STOP_RULES else
                             {"ontrend": "co", "eom": "cc"}.get(name, "oc"))
            series = portfolio(per_sym, all_dates)
            days = [r for t in per_sym.values() for r in t.values()]
            row = {"rule": name, "params": p, "source": spec["source"], "hold": hold,
                   "trades": n_tr, "win": (sum(1 for r in days if r > 0) / len(days)) if days else 0,
                   "avg_trade_bps": (sum(days) / n_tr) if n_tr else 0.0}
            for part in ("is", "oos", "ho"):
                row[part] = stats([r for d, r in series if period_of(d) == part])
            row["_post"] = [r for d, r in series if period_of(d) != "is"]
            row["post"] = stats(row["_post"])
            variants.append(row)
    # deflated Sharpe over everything after the IS period, charged for every variant the lab tried
    srs = [r["oos"]["sharpe"] / math.sqrt(252) for r in variants if r["oos"]["n"] > 30]
    var = robust_var(srs)
    for r in variants:
        r["dsr"] = deflated_sharpe(r.pop("_post"), len(variants), var)
    return {"periods": {"is_end": IS_END, "oos_end": OOS_END}, "cost_bps": cost_bps,
            "n_variants": len(variants), "symbols": sorted(universe), "variants": variants,
            "chosen": choose(variants)}


def choose(variants):
    """Per rule and kind (day trade or overnight swing): the variant with the best IS Sharpe.
    It passes only if IS t >= 2, OOS mean > 0, HOLDOUT mean > 0 and t >= 3 on OOS + HOLDOUT."""
    best = {}
    for r in variants:
        key = (r["rule"], "day" if r["hold"] in ("oc", "stop") else ("multi" if r["hold"] == "mc" else "swing"))
        if key not in best or r["is"]["sharpe"] > best[key]["is"]["sharpe"]:
            best[key] = r
    out = []
    for (rule, kind), r in best.items():
        ok = (r["is"]["t"] >= MIN_IS_T and r["oos"]["mean"] > 0 and r["ho"]["mean"] > 0
              and r["post"]["t"] >= POST_T)
        out.append({"rule": rule, "kind": kind, "params": r["params"], "hold": r["hold"],
                    "trades": r["trades"], "win": r["win"], "avg_trade_bps": r["avg_trade_bps"],
                    "is_t": r["is"]["t"], "is_sharpe": r["is"]["sharpe"],
                    "oos_sharpe": r["oos"]["sharpe"], "oos_mean": r["oos"]["mean"], "oos_t": r["oos"]["t"],
                    "ho_sharpe": r["ho"]["sharpe"], "ho_mean": r["ho"]["mean"], "ho_t": r["ho"]["t"],
                    "post_t": r["post"]["t"], "post_sharpe": r["post"]["sharpe"],
                    "dsr": r["dsr"], "pass": ok, "source": r["source"]})
    return sorted(out, key=lambda c: (not c["pass"], -c["post_t"]))


# ---------------------------------------------------------------- live: what fires next session

def next_session(universe, chosen):
    """For each passing day-trade rule, which symbols it fires on for the session after the last bar.
    A rule that needs today's open says 'at the open, if ...'."""
    rows = []
    for c in chosen:
        if not c["pass"] or c["rule"] not in RULES:
            continue  # swing rules: see the swing section of the report
        fn = RULES[c["rule"]]["fn"]
        for sym, D in sorted(universe.items()):
            n = len(D["d"])
            # extend the series by one placeholder day so i = n refers to the next session
            E = {k: list(v) for k, v in D.items()}
            E["d"].append("next")
            for k in "ohlcv":
                E[k].append(D["c"][-1] if k != "v" else 0.0)
            try:
                sig = fn(E, n, c["params"])
            except (ValueError, IndexError):
                sig = None
            if sig:
                rows.append({"rule": c["rule"], "kind": c["kind"], "symbol": sym, "side": sig["side"],
                             "hold": sig["hold"], "entry": sig.get("entry"), "last_date": D["d"][-1],
                             "note": "assumes it opens at yesterday's close" if c["rule"] in ("gap", "oops", "wvb") else ""})
    return rows


# ---------------------------------------------------------------- report and commands

def report(res):
    L = ["Daily engine: %d variants, %d symbols, %.1f bps per trade. IS to %s, OOS to %s, HOLDOUT after." % (
        res["n_variants"], len(res["symbols"]), res["cost_bps"], res["periods"]["is_end"], res["periods"]["oos_end"]),
        "Chosen variant per rule (best IS Sharpe), and whether it passed every gate:", "",
        "%-7s %-5s %-34s %7s %5s %6s | %5s | %6s %6s | %6s %6s | %6s %5s" % (
            "rule", "kind", "params", "trades", "win", "avg bp", "IS t", "OOS Sh", "OOS t", "HO Sh", "HO t",
            "post t", "DSR"),
        "-" * 118]
    for c in res["chosen"]:
        p = ",".join("%s=%s" % kv for kv in sorted(c["params"].items()))
        L.append("%-7s %-5s %-34s %7d %4.0f%% %6.1f | %5.2f | %6.2f %6.2f | %6.2f %6.2f | %6.2f %5.3f %s" % (
            c["rule"], c["kind"], p[:34], c["trades"], c["win"] * 100, c["avg_trade_bps"], c["is_t"],
            c["oos_sharpe"], c["oos_t"], c["ho_sharpe"], c["ho_t"], c["post_t"], c["dsr"],
            "PASS" if c["pass"] else ""))
    L += ["", "PASS = IS t >= %.1f, OOS and HOLDOUT both positive, and t >= %.1f on all data after %s"
          % (MIN_IS_T, POST_T, IS_END),
          "(Harvey, Liu & Zhu 2016). DSR = deflated Sharpe (Bailey & Lopez de Prado 2014) charged for all",
          "%d variants; 0.95+ would be strong. Research, not financial advice." % res["n_variants"]]
    return "\n".join(L)


def load_vix(store=STORE):
    """^VIX closes with their trailing 252-day median (known at that close)."""
    V = load("^VIX", store)
    VIX.clear()
    if not V:
        return
    c = V["c"]
    for i in range(252, len(c)):
        VIX[V["d"][i]] = (c[i], statistics.median(c[i - 252:i]))


def load_universe(symbols, store=STORE):
    load_vix(store)
    out = {}
    for s in symbols:
        D = load(s, store)
        if D:
            k = next((i for i, d in enumerate(D["d"]) if d >= DATA_START), len(D["d"]))
            D = {key: v[k:] for key, v in D.items()}
        if D and len(D["d"]) > 250 and not s.startswith("^"):
            out[s] = D
    if not out:
        raise LabError("no daily data: run `daily.py fetch` first")
    return out


def cmd_fetch(a):
    for n, s in enumerate(a.symbols):
        if n:
            time.sleep(PAUSE)
        try:
            D = parse_daily(fetch_daily(s))
        except LabError as e:
            print("%-6s skipped: %s" % (s, e))
            continue
        save(s, D, a.store)
        print("%-6s %5d days %s to %s" % (s, len(D["d"]), D["d"][0], D["d"][-1]))
    return 0


def cmd_backtest(a):
    res = backtest(load_universe(a.symbols, a.store), a.cost, a.only)
    if a.write:
        os.makedirs(os.path.dirname(a.write), exist_ok=True)
        with open(a.write, "w") as fh:
            json.dump(res, fh, indent=1, sort_keys=True)
    print(json.dumps(res, indent=1, sort_keys=True) if a.json else report(res))
    return 0


def swing_state(D, entry, p):
    """For a multi-day rule on one symbol: 'enter' if the last close is a fresh signal, ('hold', days, entry px)
    if a position from an earlier signal is still open, else None."""
    c = D["c"]
    N = len(c)
    ex = EXITS[p["exit"]]
    maxd = p.get("max_days", 10)
    j = 21
    while j < N:
        if not entry(D, j, p) or not vix_ok(D["d"][j], p):
            j += 1
            continue
        if j == N - 1:
            return ("enter", 0, c[j])
        k = j + 1
        while k < N:
            if ex(D, k, p, j) or k - j >= maxd:
                break
            k += 1
        if k >= N:
            return ("hold", N - 1 - j, D["o"][j + 1] if p.get("fill") == "open" else c[j])
        j = k + 1 if k == j + 1 else k
    return None


def cmd_signal(a):
    uni = load_universe(a.symbols, a.store)
    path = os.path.join(RESULTS, "daily-latest.json")
    if os.path.exists(path):
        with open(path) as fh:
            chosen = json.load(fh)["chosen"]
    else:
        chosen = backtest(uni, a.cost)["chosen"]
    rows = next_session(uni, chosen)
    swings = []
    for c in chosen:
        if c["rule"] in SWING and (c["pass"] or c["post_t"] >= 2.9):
            for sym, D in sorted(uni.items()):
                st = swing_state(D, SWING[c["rule"]]["fn"], c["params"])
                if st:
                    swings.append({"rule": c["rule"], "pass": c["pass"], "symbol": sym, "state": st[0],
                                   "days": st[1], "entry": round(st[2], 2), "last_date": D["d"][-1],
                                   "last": D["c"][-1], "params": c["params"]})
    if a.json:
        print(json.dumps({"day": rows, "multi_day": swings}, indent=1))
        return 0
    if swings:
        print("Multi-day rules (passed, or within 0.1 of the t >= 3 bar), as of the last close:")
        for r in swings:
            what = ("NEW: buy at the next open" if r["state"] == "enter"
                    else "open %d day(s), in at %.2f, last %.2f" % (r["days"], r["entry"], r["last"]))
            print("  %-8s %-4s %-6s %s" % (r["rule"], "PASS" if r["pass"] else "near", r["symbol"], what))
        print("")
    if not rows:
        print("No passing rule fires for the next session.")
    for r in rows:
        print("%-7s %-5s %-6s %-5s %s%s %s" % (r["rule"], r["kind"], r["symbol"], "long" if r["side"] > 0 else "short",
                                             r["hold"], (" stop-entry %.2f" % r["entry"]) if r["entry"] else "", r["note"]))
    print("\nFrom rules that passed every gate. A lean, not an order; run /trader-risk first. Not financial advice.")
    return 0


FROZEN = os.path.join(RESULTS, "frozen.json")


def cmd_freeze(a):
    """Pre-register: append today's passing rules (and the near misses, marked) with their exact
    parameters. They are then judged only on sessions after the freeze date."""
    with open(os.path.join(RESULTS, "daily-latest.json")) as fh:
        chosen = json.load(fh)["chosen"]
    reg = []
    if os.path.exists(FROZEN):
        with open(FROZEN) as fh:
            reg = json.load(fh)
    today = a.date or datetime.date.today().isoformat()
    have = {(r["rule"], json.dumps(r["params"], sort_keys=True)) for r in reg}
    for c in chosen:
        if c["pass"] or c["post_t"] >= a.min_t:
            key = (c["rule"], json.dumps(c["params"], sort_keys=True))
            if key not in have:
                reg.append({"rule": c["rule"], "params": c["params"], "frozen": today, "passed": c["pass"],
                            "post_t_at_freeze": round(c["post_t"], 2)})
    with open(FROZEN, "w") as fh:
        json.dump(reg, fh, indent=1, sort_keys=True)
    for r in reg:
        print("%-8s frozen %s  %s  %s" % (r["rule"], r["frozen"], "PASS" if r["passed"] else "near",
                                         json.dumps(r["params"], sort_keys=True)))
    return 0


def cmd_forward(a):
    """How each frozen rule has done on sessions strictly after its freeze date."""
    if not os.path.exists(FROZEN):
        print("Nothing frozen yet: run `daily.py freeze` after a backtest --write.")
        return 0
    with open(FROZEN) as fh:
        reg = json.load(fh)
    uni = load_universe(a.symbols, a.store)
    dates = sorted({d for D in uni.values() for d in D["d"]})
    for r in reg:
        spec = RULES.get(r["rule"]) or SWING.get(r["rule"])
        if spec is None:
            continue
        if r["rule"] in SWING:
            per = {s: run_swing(D, spec["fn"], r["params"], a.cost)[0] for s, D in uni.items()}
        else:
            per = {s: run_rule(D, spec["fn"], r["params"], a.cost) for s, D in uni.items()}
        ser = [x for d, x in portfolio(per, dates) if d > r["frozen"]]
        st = stats(ser) if ser else {"n": 0, "mean": 0.0, "t": 0.0, "sharpe": 0.0}
        print("%-8s since %s: %3d sessions, mean %6.1f bp/day, t %5.2f" % (
            r["rule"], r["frozen"], st["n"], st["mean"], st["t"]))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="trader-lab daily engine: day-trading rules on decades of daily bars.")
    sub = ap.add_subparsers(dest="cmd")

    def common(p):
        p.add_argument("--symbols", type=lambda s: [x.strip().upper() for x in s.split(",") if x.strip()],
                       default=UNIVERSE + ["^VIX"])
        p.add_argument("--store", default=STORE)
        p.add_argument("--cost", type=float, default=COST_BPS, help="cost per trade in bps (default 2)")
        p.add_argument("--json", action="store_true")

    common(sub.add_parser("fetch", help="full daily history for the universe"))
    p = sub.add_parser("backtest", help="every rule and variant over IS, OOS and HOLDOUT")
    common(p)
    p.add_argument("--only", type=lambda s: s.split(","))
    p.add_argument("--write", nargs="?", const=os.path.join(RESULTS, "daily-latest.json"), metavar="PATH")
    common(sub.add_parser("signal", help="which passing rules fire for the next session"))
    p = sub.add_parser("freeze", help="pre-register today's passing rules for a forward test")
    common(p)
    p.add_argument("--date", help="freeze date (default today)")
    p.add_argument("--min-t", type=float, default=2.5, help="also freeze near misses with post t >= this")
    common(sub.add_parser("forward", help="results of frozen rules after their freeze date"))
    a = ap.parse_args(argv)
    if not a.cmd:
        ap.print_help()
        return 1
    try:
        return {"fetch": cmd_fetch, "backtest": cmd_backtest, "signal": cmd_signal,
                "freeze": cmd_freeze, "forward": cmd_forward}[a.cmd](a)
    except LabError as e:
        print("daily.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
