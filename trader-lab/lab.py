#!/usr/bin/env python3
"""trader-lab: the Strategy Lab.

Tests day-trading rules from the academic literature on real 5-minute bars,
after costs, with an honest in-sample / out-of-sample split, and turns the
rules that survive into one live signal per stock.

    python3 lab.py fetch                      # pull 60 days of 5-min bars, merge into the store
    python3 lab.py backtest                   # every strategy, every variant, IS vs OOS, after costs
    python3 lab.py signal                     # today's live signal from the strategies that survived
    python3 lab.py backtest --json            # machine-readable
    python3 lab.py backtest --write           # also save trader-lab/results/latest.json

The store (trader-lab/data/<SYM>.json.gz) only ever grows: every fetch merges
the newest 60 days into what is already there, so the history gets longer every
time the lab runs and the tests get more data.

Strategies (each is a pure function of bars known at decision time, fills at
the NEXT bar's open, stops fill at the stop or the bar's open if it gapped
through, and every position is flat by the close):

  orb5     Zarattini & Aziz (2023), "Can Day Trading Really Be Profitable?":
           trade in the direction of the first 5-minute bar, stop at its other end.
  orb      Classic opening-range breakout (Crabel 1990; Toby Crabel's ORB):
           first close outside the first N minutes' range.
  noise    Zarattini, Aziz & Barbon (2024), "Beat the Market": the "noise area"
           band from the average move-from-open at each time of day over the last
           L sessions; trade breaks of the band at half-hour marks, trail at
           max(band, VWAP).
  imom     Gao, Han, Li & Zhou (2018, JFE), "Market intraday momentum": the
           return from yesterday's close to 10:00 predicts the last half hour.
  vwap     VWAP trend (Zarattini & Aziz 2023 QQQ VWAP study): side of VWAP at a
           decision time, exit on a close through VWAP.
  gap      Overnight gap fade or follow-through, by gap size.
  sip      Zarattini, Barbon & Aziz (2024), "A Profitable Day Trading Strategy for the
           U.S. Equity Market": the 5-min ORB only on today's top "stocks in play" by
           first-5-minute relative volume, stop at 10% of the 14-day ATR.

This is research, not financial advice. Most day traders lose money
(Chague, De-Losso & Giovannetti 2020: 97% of Brazilian futures day traders who
kept at it for 300+ days lost money). A backtest is not a promise.
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
STORE = os.path.join(HERE, "data")
RESULTS = os.path.join(HERE, "results")
PAUSE = 0.5
INTERVAL = 300
SESSION_BARS = 78
OPEN_MIN = 9 * 60 + 30
EPOCH = datetime.datetime(1970, 1, 1)
UNIVERSE = ["SPY", "QQQ", "IWM", "DIA", "SMH", "XLF", "XLK", "XLE", "TLT", "GLD",
            "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "TSLA", "AMD", "AVGO", "NFLX",
            "PLTR", "COIN", "MSTR", "SMCI", "UBER", "SHOP", "CRWD", "MU", "INTC", "ORCL",
            "CRM", "ARM", "BA", "JPM", "XOM", "LLY", "UNH", "WMT", "COST", "NKE"]
COST_BPS = 3.0      # round trip: spread + slippage + fees, liquid US names
OOS_FRAC = 0.30     # the last 30% of the dates are never used to choose a variant
KEEP_IS_SHARPE = 0.5
MIN_TRADES = 20


class LabError(Exception):
    pass


# ---------------------------------------------------------------- time

def _nth_sunday(year, month, n):
    d = datetime.date(year, month, 1)
    d += datetime.timedelta(days=(6 - d.weekday()) % 7)
    return d + datetime.timedelta(weeks=n - 1)


def to_eastern(utc):
    """US Eastern from naive UTC, DST from the second Sunday of March to the first Sunday of November."""
    y = utc.year
    start = datetime.datetime.combine(_nth_sunday(y, 3, 2), datetime.time(7))
    end = datetime.datetime.combine(_nth_sunday(y, 11, 1), datetime.time(6))
    return utc - datetime.timedelta(hours=4 if start <= utc < end else 5)


def utc_of(ts):
    return EPOCH + datetime.timedelta(seconds=int(ts))


# ---------------------------------------------------------------- data

def chart_url(sym, host="query2", rng="60d"):
    return "https://%s.finance.yahoo.com/v8/finance/chart/%s?range=%s&interval=5m" % (
        host, urllib.parse.quote(sym.upper().replace(".", "-")), rng)


def _get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def fetch_chart(sym):
    last = None
    for host in ("query2", "query1"):
        for attempt in (0, 1):
            try:
                return _get(chart_url(sym, host))
            except urllib.error.HTTPError as e:
                last = e.code
                if e.code == 429 and attempt == 0:
                    time.sleep(5)
                    continue
                if e.code == 404:
                    raise LabError("Yahoo has no chart for %s" % sym)
                break
            except (urllib.error.URLError, OSError) as e:
                raise LabError("could not reach Yahoo: %s" % getattr(e, "reason", e))
        time.sleep(PAUSE)
    raise LabError("Yahoo answered HTTP %s for %s" % (last, sym))


def parse_chart(text, now_utc=None):
    """Yahoo chart JSON -> {ts: [o, h, l, c, v]} for complete regular-session 5-min bars."""
    data = json.loads(text)
    res = ((data.get("chart") or {}).get("result") or [None])[0]
    if not res:
        raise LabError("Yahoo returned no data")
    meta = res.get("meta") or {}
    stamps = res.get("timestamp") or []
    q = ((res.get("indicators") or {}).get("quote") or [{}])[0] or {}
    cols = [q.get(k) or [] for k in ("open", "high", "low", "close", "volume")]
    as_of = now_utc or datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    rmt = meta.get("regularMarketTime")
    if isinstance(rmt, (int, float)) and utc_of(rmt) < as_of:
        as_of = utc_of(rmt)
    out = {}
    for i, ts in enumerate(stamps):
        row = [c[i] if i < len(c) else None for c in cols]
        if ts is None or None in row[:4] or int(ts) % INTERVAL:
            continue
        start = utc_of(ts)
        local = to_eastern(start)
        mins = local.hour * 60 + local.minute - OPEN_MIN
        if mins < 0 or mins >= SESSION_BARS * 5:
            continue
        if start + datetime.timedelta(seconds=INTERVAL) > as_of:
            continue
        out[str(int(ts))] = [float(row[0]), float(row[1]), float(row[2]), float(row[3]), float(row[4] or 0)]
    return out


def store_path(sym, store=STORE):
    return os.path.join(store, "%s.json.gz" % sym.upper())


def load_store(sym, store=STORE):
    p = store_path(sym, store)
    if not os.path.exists(p):
        return {}
    with gzip.open(p, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def save_store(sym, bars, store=STORE):
    os.makedirs(store, exist_ok=True)
    keys = sorted(bars, key=int)
    with gzip.GzipFile(store_path(sym, store), "wb", mtime=0) as gz:
        gz.write(json.dumps({k: bars[k] for k in keys}, separators=(",", ":")).encode("utf-8"))


def merge(old, new):
    out = dict(old)
    out.update(new)
    return out


def sessions_of(bars):
    """{ts: ohlcv} -> [(date, [bar dicts by slot])], oldest first. Each bar: o h l c v slot."""
    days = {}
    for ts, (o, h, l, c, v) in bars.items():
        local = to_eastern(utc_of(int(ts)))
        slot = (local.hour * 60 + local.minute - OPEN_MIN) // 5
        days.setdefault(local.date().isoformat(), {})[slot] = {"o": o, "h": h, "l": l, "c": c, "v": v, "slot": slot}
    out = []
    for d in sorted(days):
        s = days[d]
        # keep sessions that are complete from the open (a live day may be partial, a half day is short)
        n = 0
        while n in s:
            n += 1
        out.append((d, [s[i] for i in range(n)]))
    return out


# ---------------------------------------------------------------- strategy helpers

def vwap_series(bars):
    pv = vol = 0.0
    out = []
    for b in bars:
        tp = (b["h"] + b["l"] + b["c"]) / 3.0
        v = b["v"] if b["v"] > 0 else 1.0
        pv += tp * v
        vol += v
        out.append(pv / vol)
    return out


class Book:
    """Walks one day bar by bar; decisions on a bar's close fill at the next bar's open."""

    def __init__(self, bars):
        self.bars = bars
        self.trades = []
        self.pos = 0
        self.entry = None
        self.entry_slot = None
        self.stop = None
        self.pending = None  # (side) to open at next bar's open, 0 = close at next open
        self.armed = None    # (side, trigger, stop_dist): enter when price trades through trigger

    def open_next(self, side, stop=None):
        self.pending = (side, stop)

    def arm(self, side, trigger, stop_dist):
        """A stop-entry order: long when the high reaches trigger, short when the low does.
        Fills at the trigger, or at the bar's open if it gapped through. Stop = fill -+ stop_dist."""
        self.armed = (side, trigger, stop_dist)

    def step(self, i):
        """Apply pending orders at bar i's open, a stop-entry inside bar i, then the stop inside bar i."""
        b = self.bars[i]
        if self.armed is not None and not self.pos:
            side, trig, dist = self.armed
            hit = b["h"] >= trig if side > 0 else b["l"] <= trig
            if hit:
                px = max(trig, b["o"]) if side > 0 else min(trig, b["o"])
                self.armed = None
                self.pos, self.entry, self.entry_slot = side, px, i
                self.stop = (px - side * dist) if dist else None
        if self.pending is not None:
            side, stop = self.pending
            self.pending = None
            if self.pos and side != self.pos:
                self._close(i, b["o"])
            if side and not self.pos:
                self.pos, self.entry, self.entry_slot, self.stop = side, b["o"], i, stop
        if self.pos and self.stop is not None:
            # the open can only gap past the stop if we held the position before this bar opened
            gap = self.entry_slot < i or (self.entry_slot == i and self.entry == b["o"])
            if self.pos > 0 and b["l"] <= self.stop:
                self._close(i, min(self.stop, b["o"]) if gap else self.stop)
            elif self.pos < 0 and b["h"] >= self.stop:
                self._close(i, max(self.stop, b["o"]) if gap else self.stop)

    def _close(self, i, px):
        self.trades.append({"side": self.pos, "entry": self.entry, "exit": px,
                            "entry_slot": self.entry_slot, "exit_slot": i})
        self.pos, self.entry, self.entry_slot, self.stop = 0, None, None, None

    def finish(self, full):
        """Flat at the close on a full day; on a partial (live) day report the open position."""
        if self.pos and full:
            self._close(len(self.bars) - 1, self.bars[-1]["c"])
        live = None
        if self.pos:
            live = {"side": self.pos, "entry": self.entry, "entry_slot": self.entry_slot, "stop": self.stop}
        elif self.pending and self.pending[0]:
            live = {"side": self.pending[0], "entry": None, "entry_slot": None, "stop": self.pending[1]}
        elif self.armed and not full:
            live = {"side": self.armed[0], "entry": None, "entry_slot": None, "stop": None,
                    "trigger": self.armed[1]}
        return self.trades, live


def run_day(fn, bars, ctx, p, full):
    book = Book(bars)
    for i in range(len(bars)):
        book.step(i)
        if i < len(bars) - 1 or not full:
            fn(book, i, bars, ctx, p)
    return book.finish(full)


# ---------------------------------------------------------------- strategies
# each fn(book, i, bars, ctx, params) is called after bar i closes; it may call book.open_next().

def s_orb5(book, i, bars, ctx, p):
    if i == 0:
        b = bars[0]
        if b["c"] > b["o"]:
            book.open_next(1, b["l"] if p["stop"] == "bar" else None)
        elif b["c"] < b["o"]:
            book.open_next(-1, b["h"] if p["stop"] == "bar" else None)


def s_orb(book, i, bars, ctx, p):
    n = p["bars"]
    if i < n or book.pos or ctx.get("_orb_done") == id(bars) or i > p["last"]:
        return
    hi = max(b["h"] for b in bars[:n])
    lo = min(b["l"] for b in bars[:n])
    mid = (hi + lo) / 2.0
    c = bars[i]["c"]
    if c > hi:
        book.open_next(1, mid if p["stop"] == "mid" else lo)
        ctx["_orb_done"] = id(bars)
    elif c < lo:
        book.open_next(-1, mid if p["stop"] == "mid" else hi)
        ctx["_orb_done"] = id(bars)


def s_noise(book, i, bars, ctx, p):
    sig = ctx.get("sigma_%d" % p["lookback"])
    pc = ctx.get("prev_close")
    if sig is None or pc is None or (i + 1) % 6 or i >= SESSION_BARS - 1:
        return  # decide at the half-hour marks only (10:00, 10:30, ...)
    o = bars[0]["o"]
    ub = max(o, pc) * (1 + p["mult"] * sig[i])
    lb = min(o, pc) * (1 - p["mult"] * sig[i])
    vw = ctx["_vwap"][i] if ctx.get("_vwap_id") == id(bars) else None
    if vw is None:
        ctx["_vwap"], ctx["_vwap_id"] = vwap_series(bars), id(bars)
        vw = ctx["_vwap"][i]
    c = bars[i]["c"]
    want = book.pos
    if book.pos > 0 and c < max(ub, vw):
        want = 0
    elif book.pos < 0 and c > min(lb, vw):
        want = 0
    if want == 0:
        if c > ub:
            want = 1
        elif c < lb:
            want = -1
    if want != book.pos:
        book.open_next(want)


def s_imom(book, i, bars, ctx, p):
    pc = ctx.get("prev_close")
    if pc is None:
        return
    if i == p["entry"] - 1:
        r = bars[5]["c"] / pc - 1 if len(bars) > 5 else 0
        if abs(r) * 1e4 >= p["min_bps"]:
            book.open_next(1 if r > 0 else -1)


def s_vwap(book, i, bars, ctx, p):
    if ctx.get("_vwap_id") != id(bars):
        ctx["_vwap"], ctx["_vwap_id"] = vwap_series(bars), id(bars)
        ctx["_vwap_done"] = None
    vw = ctx["_vwap"][i]
    c = bars[i]["c"]
    if i == p["at"] and not book.pos:
        book.open_next(1 if c > vw else -1)
        ctx["_vwap_done"] = id(bars)
    elif book.pos > 0 and c < vw:
        book.open_next(0)
    elif book.pos < 0 and c > vw:
        book.open_next(0)


def s_gap(book, i, bars, ctx, p):
    pc = ctx.get("prev_close")
    if pc is None or i != 0:
        return
    g = bars[0]["o"] / pc - 1
    if abs(g) * 100 < p["min_pct"]:
        return
    side = (-1 if g > 0 else 1) * (1 if p["mode"] == "fade" else -1)
    # entry at bar 1 open (not the auction print), stop at the first bar's extreme
    book.open_next(side, bars[0]["h"] if side < 0 else bars[0]["l"])


def s_sip(book, i, bars, ctx, p):
    """Stocks in play: only today's top names by opening relative volume trade the 5-min ORB,
    entering on a break of the first bar's high (green bar) or low (red bar)."""
    if i != 0:
        return
    rv, rank, atr = ctx.get("rvol"), ctx.get("rvol_rank"), ctx.get("atr14")
    if rv is None or rank is None or rv < p["min_rvol"] or rank > p["top"]:
        return
    b = bars[0]
    if b["c"] == b["o"]:
        return
    side = 1 if b["c"] > b["o"] else -1
    if p["stop"] == "atr10":
        if not atr:
            return
        dist = 0.10 * atr
    else:
        dist = b["h"] - b["l"]
    book.arm(side, b["h"] if side > 0 else b["l"], dist)


def grid(d):
    keys = sorted(d)
    out = [{}]
    for k in keys:
        out = [dict(x, **{k: v}) for x in out for v in d[k]]
    return out


STRATEGIES = {
    "orb5": {"fn": s_orb5, "source": "Zarattini & Aziz 2023, SSRN 4416622",
             "grid": {"stop": ["bar", "none"]}},
    "sip": {"fn": s_sip, "source": "Zarattini, Barbon & Aziz 2024, SFI 24-98, ORB on stocks in play",
            "grid": {"top": [5, 10], "min_rvol": [1.0, 1.5], "stop": ["atr10", "bar"]}},
    "orb": {"fn": s_orb, "source": "Crabel 1990, opening range breakout",
            "grid": {"bars": [3, 6], "stop": ["mid", "opposite"], "last": [23]}},
    "noise": {"fn": s_noise, "source": "Zarattini, Aziz & Barbon 2024, SFI 24-97",
              "grid": {"lookback": [10, 14], "mult": [1.0, 1.5]}},
    "imom": {"fn": s_imom, "source": "Gao, Han, Li & Zhou 2018, JFE 129(2)",
             "grid": {"entry": [72, 66], "min_bps": [0, 25]}},
    "vwap": {"fn": s_vwap, "source": "Zarattini & Aziz 2023, VWAP trend on QQQ",
             "grid": {"at": [5, 11]}},
    "gap": {"fn": s_gap, "source": "overnight gap fade / go",
            "grid": {"min_pct": [0.5, 1.0], "mode": ["fade", "go"]}},
}


def sigma_table(sessions, k, lookback):
    """Average |close_t / open - 1| at each slot over the `lookback` full sessions before k."""
    past = [b for _, b in sessions[max(0, k - lookback):k] if len(b) == SESSION_BARS]
    if len(past) < lookback:
        return None
    return [sum(abs(D[i]["c"] / D[0]["o"] - 1) for D in past) / len(past) for i in range(SESSION_BARS)]


def first_bar_rvol(sessions, k, lookback=14):
    """Today's first 5-min volume / the average first 5-min volume of the previous `lookback` sessions."""
    if not sessions[k][1]:
        return None
    past = [b[0]["v"] for _, b in sessions[max(0, k - lookback):k] if b]
    if len(past) < lookback or sum(past) <= 0:
        return None
    return sessions[k][1][0]["v"] / (sum(past) / len(past))


def atr14(sessions, k, lookback=14):
    """Average daily true range of the `lookback` full sessions before k, in dollars."""
    trs = []
    for j in range(max(1, k - lookback), k):
        prev, cur = sessions[j - 1][1], sessions[j][1]
        if len(prev) != SESSION_BARS or len(cur) != SESSION_BARS:
            continue
        pc = prev[-1]["c"]
        hi = max(b["h"] for b in cur)
        lo = min(b["l"] for b in cur)
        trs.append(max(hi, pc) - min(lo, pc))
    return (sum(trs) / len(trs)) if len(trs) >= lookback // 2 else None


def cross_section(universe_sessions):
    """{(sym, date): {"rvol", "rvol_rank", "atr14"}}: rank 1 = the highest relative volume that day.
    Uses only the first 5-minute bar of the day, so it is known at 9:35."""
    by_date = {}
    out = {}
    for sym, ss in universe_sessions.items():
        for k, (d, bars) in enumerate(ss):
            rv = first_bar_rvol(ss, k)
            out[(sym, d)] = {"rvol": rv, "rvol_rank": None, "atr14": atr14(ss, k)}
            if rv is not None:
                by_date.setdefault(d, []).append((rv, sym))
    for d, rows in by_date.items():
        for n, (_, sym) in enumerate(sorted(rows, reverse=True)):
            out[(sym, d)]["rvol_rank"] = n + 1
    return out


def contexts(sessions, k, extra=None):
    ctx = dict(extra or {})
    ctx["prev_close"] = None
    if k > 0 and sessions[k - 1][1]:
        prev = sessions[k - 1][1]
        if len(prev) == SESSION_BARS:
            ctx["prev_close"] = prev[-1]["c"]
    for L in (10, 14, 20):
        ctx["sigma_%d" % L] = sigma_table(sessions, k, L)
    return ctx


def trade_bps(t, cost_bps):
    return t["side"] * (t["exit"] / t["entry"] - 1) * 1e4 - cost_bps


# ---------------------------------------------------------------- backtest

def backtest(universe_sessions, cost_bps=COST_BPS, oos_frac=OOS_FRAC, only=None):
    dates = sorted({d for ss in universe_sessions.values() for d, b in ss if len(b) == SESSION_BARS})
    if len(dates) < 25:
        raise LabError("only %d full sessions in the store; need 25+ (run fetch first)" % len(dates))
    cut = dates[int(len(dates) * (1 - oos_frac))]
    xs = cross_section(universe_sessions)
    results = []
    for name, spec in STRATEGIES.items():
        if only and name not in only:
            continue
        for p in grid(spec["grid"]):
            daily = {}
            trades = []
            for sym, ss in universe_sessions.items():
                for k, (d, bars) in enumerate(ss):
                    if len(bars) != SESSION_BARS:
                        continue
                    ctx = contexts(ss, k, xs.get((sym, d)))
                    ts, _ = run_day(spec["fn"], bars, ctx, p, True)
                    for t in ts:
                        r = trade_bps(t, cost_bps)
                        trades.append((d, sym, r))
                        daily.setdefault(d, []).append(r)
            results.append(summarize(name, p, spec["source"], trades, daily, dates, cut))
    return {"dates": [dates[0], dates[-1]], "n_dates": len(dates), "oos_from": cut,
            "cost_bps": cost_bps, "symbols": sorted(universe_sessions), "variants": results,
            "chosen": choose(results)}


def stats(series):
    n = len(series)
    if n < 2:
        return {"n": n, "mean": series[0] if n else 0.0, "sd": 0.0, "t": 0.0, "sharpe": 0.0}
    m = statistics.mean(series)
    sd = statistics.stdev(series)
    t = m / (sd / math.sqrt(n)) if sd > 0 else 0.0
    return {"n": n, "mean": m, "sd": sd, "t": t, "sharpe": (m / sd * math.sqrt(252)) if sd > 0 else 0.0}


def summarize(name, p, source, trades, daily, dates, cut):
    def part(pred):
        # equal-weight portfolio of that day's trades; a day with no trade earns 0
        series = [statistics.mean(daily[d]) if d in daily else 0.0 for d in dates if pred(d)]
        tr = [r for d, _, r in trades if pred(d)]
        s = stats(series)
        s["trades"] = len(tr)
        s["win"] = (sum(1 for r in tr if r > 0) / len(tr)) if tr else 0.0
        s["avg_trade_bps"] = statistics.mean(tr) if tr else 0.0
        return s
    return {"strategy": name, "params": p, "source": source,
            "all": part(lambda d: True), "is": part(lambda d: d < cut), "oos": part(lambda d: d >= cut)}


def choose(results):
    """Per strategy: the variant with the best IN-SAMPLE Sharpe. It is kept only if that is
    >= KEEP_IS_SHARPE with enough trades AND its out-of-sample mean is still positive."""
    best = {}
    for r in results:
        cur = best.get(r["strategy"])
        if cur is None or r["is"]["sharpe"] > cur["is"]["sharpe"]:
            best[r["strategy"]] = r
    out = []
    for name, r in best.items():
        keep = (r["is"]["sharpe"] >= KEEP_IS_SHARPE and r["is"]["trades"] >= MIN_TRADES
                and r["oos"]["mean"] > 0 and r["oos"]["trades"] >= MIN_TRADES // 2)
        out.append({"strategy": name, "params": r["params"], "keep": keep,
                    "is_sharpe": r["is"]["sharpe"], "oos_sharpe": r["oos"]["sharpe"],
                    "oos_mean_bps": r["oos"]["mean"], "oos_t": r["oos"]["t"],
                    "weight": 0.0})
    tot = sum(max(c["is_sharpe"], 0) for c in out if c["keep"])
    for c in out:
        c["weight"] = (max(c["is_sharpe"], 0) / tot) if (c["keep"] and tot > 0) else 0.0
    return sorted(out, key=lambda c: -c["oos_sharpe"])


# ---------------------------------------------------------------- live signal

def live_signal(universe_sessions, chosen):
    """For each symbol, run each kept strategy on today's bars so far. Score in [-1, 1]."""
    out = []
    xs = cross_section(universe_sessions)
    for sym, ss in sorted(universe_sessions.items()):
        if not ss:
            continue
        k = len(ss) - 1
        d, bars = ss[k]
        if not bars:
            continue
        full = len(bars) == SESSION_BARS
        ctx = contexts(ss, k, xs.get((sym, d)))
        comps = []
        score = 0.0
        for c in chosen:
            if not c["keep"]:
                continue
            spec = STRATEGIES[c["strategy"]]
            _, live = run_day(spec["fn"], bars, ctx, c["params"], False)
            side = live["side"] if live else 0
            score += c["weight"] * side
            comps.append({"strategy": c["strategy"], "side": side, "oos_t": c["oos_t"],
                          "stop": live.get("stop") if live else None, "weight": round(c["weight"], 3)})
        sign = 1 if score > 0 else -1
        agree_t = [x["oos_t"] for x in comps if x["side"] == sign]
        out.append({"symbol": sym, "date": d, "bars": len(bars), "session_over": full,
                    "last": bars[-1]["c"], "score": round(score, 3), "label": label(score, agree_t),
                    "components": comps})
    return sorted(out, key=lambda r: -abs(r["score"]))


STRONG_T = 2.0


def label(score, agree_t=None):
    """'strong' needs a big score AND 2+ kept strategies on that side, each with OOS t >= STRONG_T.
    agree_t: the OOS t values of the kept strategies that agree with the score's side."""
    a = abs(score)
    if a < 0.34:
        return "no edge"
    side = "long" if score > 0 else "short"
    sturdy = agree_t is not None and len(agree_t) >= 2 and min(agree_t) >= STRONG_T
    return ("strong " if a >= 0.67 and sturdy else "lean ") + side


# ---------------------------------------------------------------- report

def fmt_variant(r):
    p = ",".join("%s=%s" % kv for kv in sorted(r["params"].items()))
    a, i, o = r["all"], r["is"], r["oos"]
    return "%-6s %-30s %5d %5.0f%% %7.1f %6.2f | IS %5.2f | OOS %5.2f %6.1fbp t=%5.2f" % (
        r["strategy"], p[:30], a["trades"], a["win"] * 100, a["avg_trade_bps"], a["sharpe"],
        i["sharpe"], o["sharpe"], o["mean"], o["t"])


def report_backtest(res):
    lines = ["Strategy Lab: %d sessions %s to %s, %d symbols, %.1f bps round-trip cost" % (
        res["n_dates"], res["dates"][0], res["dates"][1], len(res["symbols"]), res["cost_bps"]),
        "In-sample before %s, out-of-sample from %s (never used to pick a variant)." % (
            res["oos_from"], res["oos_from"]),
        "",
        "%-6s %-28s %5s %6s %7s %6s | %8s | %s" % ("strat", "params", "trades", "win", "avg bp",
                                                 "Sharpe", "IS Shrp", "OOS Sharpe / mean / t"),
        "-" * 108]
    for r in sorted(res["variants"], key=lambda r: (r["strategy"], -r["is"]["sharpe"])):
        lines.append(fmt_variant(r))
    lines += ["", "Chosen (best in-sample variant per strategy; kept only if it held up out of sample):"]
    for c in res["chosen"]:
        lines.append("  %-6s %-5s IS Sharpe %5.2f  OOS Sharpe %5.2f  OOS %6.1f bp/day t=%5.2f  weight %.2f  %s" % (
            c["strategy"], "KEEP" if c["keep"] else "drop", c["is_sharpe"], c["oos_sharpe"],
            c["oos_mean_bps"], c["oos_t"], c["weight"], json.dumps(c["params"], sort_keys=True)))
    lines += ["", "Sharpe is annualized from the equal-weight daily portfolio. Many variants were tried,",
              "so a t below about 2.5 out of sample can be luck. Research, not financial advice."]
    return "\n".join(lines)


def report_signal(rows, chosen):
    kept = [c["strategy"] for c in chosen if c["keep"]]
    lines = ["Live signal from: %s" % (", ".join(kept) or "nothing (no strategy survived out of sample)"), ""]
    for r in rows:
        comp = " ".join("%s%s" % (c["strategy"], {1: "+", -1: "-", 0: "0"}[c["side"]]) for c in r["components"])
        lines.append("%-6s %s %-12s score %+5.2f  last %9.2f  %s%s" % (
            r["symbol"], r["date"], r["label"], r["score"], r["last"], comp,
            "  (session over)" if r["session_over"] else ""))
    lines += ["", "A signal is a lean from backtested rules, not an order. Shorts need allow_short in",
              "trader-budget's config, which is off by default. Run /trader-exit and /trader-risk before",
              "anything, and nothing is placed without your yes. Not financial advice."]
    return "\n".join(lines)


# ---------------------------------------------------------------- commands

def load_universe(symbols, store):
    out = {}
    for s in symbols:
        bars = load_store(s, store)
        if bars:
            out[s] = sessions_of(bars)
    if not out:
        raise LabError("the store is empty: run `lab.py fetch` first")
    return out


def cmd_fetch(a):
    for n, s in enumerate(a.symbols):
        if n:
            time.sleep(PAUSE)
        try:
            new = parse_chart(fetch_chart(s))
        except LabError as e:
            print("%-6s skipped: %s" % (s, e))
            continue
        old = load_store(s, a.store)
        allb = merge(old, new)
        save_store(s, allb, a.store)
        days = len(sessions_of(allb))
        print("%-6s %5d new bars, %6d total, %3d sessions" % (s, len(set(new) - set(old)), len(allb), days))
    return 0


def cmd_backtest(a):
    res = backtest(load_universe(a.symbols, a.store), a.cost, a.oos, a.only)
    if a.write:
        os.makedirs(os.path.dirname(a.write) or ".", exist_ok=True)
        with open(a.write, "w") as fh:
            json.dump(res, fh, indent=1, sort_keys=True)
    print(json.dumps(res, indent=1, sort_keys=True) if a.json else report_backtest(res))
    return 0


def cmd_signal(a):
    uni = load_universe(a.symbols, a.store)
    if a.chosen and os.path.exists(a.chosen):
        with open(a.chosen) as fh:
            chosen = json.load(fh)["chosen"]
    else:
        chosen = backtest(uni, a.cost, a.oos)["chosen"]
    rows = live_signal(uni, chosen)
    print(json.dumps(rows, indent=1) if a.json else report_signal(rows, chosen))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Strategy Lab: test day-trading rules from the literature (trader-lab).")
    sub = ap.add_subparsers(dest="cmd")

    def common(p):
        p.add_argument("--symbols", type=lambda s: [x.strip().upper() for x in s.split(",") if x.strip()],
                       default=UNIVERSE)
        p.add_argument("--store", default=STORE)
        p.add_argument("--cost", type=float, default=COST_BPS, help="round-trip cost in bps (default 3)")
        p.add_argument("--oos", type=float, default=OOS_FRAC, help="out-of-sample fraction (default 0.30)")
        p.add_argument("--json", action="store_true")

    common(sub.add_parser("fetch", help="download 60 days of 5-min bars and merge into the store"))
    p = sub.add_parser("backtest", help="every strategy and variant, IS vs OOS, after costs")
    common(p)
    p.add_argument("--only", type=lambda s: s.split(","), help="comma list of strategies")
    p.add_argument("--write", nargs="?", const=os.path.join(RESULTS, "latest.json"), metavar="PATH")
    p = sub.add_parser("signal", help="today's live signal from the kept strategies")
    common(p)
    p.add_argument("--chosen", default=os.path.join(RESULTS, "latest.json"),
                   help="use the choice saved by backtest --write (default results/latest.json)")
    a = ap.parse_args(argv)
    if not a.cmd:
        ap.print_help()
        return 1
    try:
        return {"fetch": cmd_fetch, "backtest": cmd_backtest, "signal": cmd_signal}[a.cmd](a)
    except LabError as e:
        print("lab.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
