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
KEEP_OOS_T = 3.0    # Harvey, Liu & Zhu (2016), the same bar as daily.py's POST_T: many variants are tried
MIN_IS_T = 2.0      # the chosen variant must have worked where it was chosen
SPLIT = (0.50, 0.75)  # IS = first 50% of dates, OOS = next 25%, HOLDOUT = last 25% (as hourly.py)
PLACEBO_REPS = 200
PLACEBO_P = 0.05    # divided by the number of strategies placebo-tested (Bonferroni)
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
    path = store_path(sym, store)
    tmp = path + ".tmp"      # write then rename, so an interrupted run never leaves a broken store
    with gzip.GzipFile(tmp, "wb", mtime=0) as gz:
        gz.write(json.dumps({k: bars[k] for k in keys}, separators=(",", ":")).encode("utf-8"))
    os.replace(tmp, path)


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


def vol_gate(ctx, p):
    """True if the volatility gate (if any) lets this day trade: yesterday's range vs the median of the
    prior 20 daily ranges (Gao et al. 2018; Li, Sakkas & Urquhart 2022: momentum lives in high volatility)."""
    g = p.get("gate", "none")
    if g == "none":
        return True
    r, med = ctx.get("prev_range"), ctx.get("median_range")
    if r is None or med is None:
        return False
    return r > med if g == "high" else r <= med


def s_orb5g(book, i, bars, ctx, p):
    if vol_gate(ctx, p):
        s_orb5(book, i, bars, ctx, p)


def s_noiseg(book, i, bars, ctx, p):
    """Noise area, optionally long only (the replications' "long survives, short is a mirage"), gated."""
    if not vol_gate(ctx, p):
        return
    before = book.pending
    s_noise(book, i, bars, ctx, p)
    if p.get("long_only") and book.pending is not before and book.pending and book.pending[0] < 0:
        book.pending = (0, None) if book.pos else None


def s_noisepb(book, i, bars, ctx, p):
    """Noise area with a pullback-entry overlay (Concretum 2026, "Fast alphas: a tactical overlay for
    intraday trend trading"): a half-hour band break does not enter at once; it arms a signal that
    enters on the first 5-minute bar closing against it (a down bar for a long, an up bar for a short)
    within `wait` bars, while still outside the band. Exits are the noise area's (half-hour trail)."""
    sig = ctx.get("sigma_%d" % p["lookback"])
    pc = ctx.get("prev_close")
    if sig is None or pc is None or i >= SESSION_BARS - 1:
        return
    if ctx.get("_pb_id") != id(bars):
        ctx["_pb_id"], ctx["_pb"] = id(bars), None
    o = bars[0]["o"]
    ub = max(o, pc) * (1 + p["mult"] * sig[i])
    lb = min(o, pc) * (1 - p["mult"] * sig[i])
    c = bars[i]["c"]
    half = (i + 1) % 6 == 0
    if half:
        if ctx.get("_vwap_id") != id(bars):
            ctx["_vwap"], ctx["_vwap_id"] = vwap_series(bars), id(bars)
        vw = ctx["_vwap"][i]
        if (book.pos > 0 and c < max(ub, vw)) or (book.pos < 0 and c > min(lb, vw)):
            book.open_next(0)
            flat = True
        else:
            flat = not book.pos
        if flat:
            ctx["_pb"] = (1, i + p["wait"]) if c > ub else (-1, i + p["wait"]) if c < lb else None
        return
    arm = ctx["_pb"]
    if arm is None or book.pos or book.pending is not None:
        return
    side, until = arm
    if i > until:
        ctx["_pb"] = None
        return
    prev = bars[i - 1]["c"]
    if side > 0 and c < prev and c > ub:
        book.open_next(1)
        ctx["_pb"] = None
    elif side < 0 and c > prev and c < lb:
        book.open_next(-1)
        ctx["_pb"] = None


def s_rod(book, i, bars, ctx, p):
    """Baltussen, Da, Lammers & Martens (2021): the return from yesterday's close to 15:30 predicts
    15:30 to 16:00. Trade its sign when |ROD| >= min_bps."""
    pc = ctx.get("prev_close")
    if pc is None or i != 71:
        return
    r = bars[71]["c"] / pc - 1
    if abs(r) * 1e4 >= p["min_bps"]:
        book.open_next((1 if r > 0 else -1) * (1 if p["mode"] == "mom" else -1))


def s_eodrev(book, i, bars, ctx, p):
    """Baltussen, Da & Soebhag (2025): end-of-day reversal across stocks. At 15:30 buy today's
    biggest losers (prev close to 15:30) and short the biggest winners; out at the close."""
    if i != 71:
        return
    rk, n = ctx.get("rod_rank"), ctx.get("rod_n")
    if rk is None or not n:
        return
    if rk <= p["k"]:
        book.open_next(-1 if p["side"] != "long" else 0)   # top winners: short
    elif rk > n - p["k"]:
        book.open_next(1 if p["side"] != "short" else 0)   # bottom losers: long


def s_lunch(book, i, bars, ctx, p):
    """Quantpedia lunch effect: long from 12:00 to 14:00 New York time."""
    if i == 29:
        book.open_next(1)
    elif i == 53 and book.pos:
        book.open_next(0)


def s_vwapre(book, i, bars, ctx, p):
    """VWAP reclaim: after at least n bars below VWAP, the first 5-min close back above a rising VWAP
    (before 14:00) -> long, stop at that bar's low, out at the close. Once a day."""
    if ctx.get("_vr_id") != id(bars):
        ctx["_vr_id"], ctx["_vr_vw"], ctx["_vr_below"], ctx["_vr_done"] = id(bars), vwap_series(bars), 0, False
    vw = ctx["_vr_vw"]
    c = bars[i]["c"]
    if ctx["_vr_done"] or book.pos or i > 53:
        ctx["_vr_below"] = ctx["_vr_below"] + 1 if c < vw[i] else 0
        return
    if c > vw[i] and ctx["_vr_below"] >= p["n"] and i >= 1 and vw[i] >= vw[i - 1]:
        book.open_next(1, bars[i]["l"])
        ctx["_vr_done"] = True
    ctx["_vr_below"] = ctx["_vr_below"] + 1 if c < vw[i] else 0


def s_orbfail(book, i, bars, ctx, p):
    """Failed opening-range breakout: price closes outside the first n bars' range, then a bar closes
    back inside within w bars -> fade it, stop at the breakout extreme, out at the close. Once a day."""
    n, w = p["bars"], p["within"]
    if i < n or book.pos or i > 47:
        return
    if ctx.get("_of_id") != id(bars):
        ctx["_of_id"], ctx["_of_brk"], ctx["_of_done"] = id(bars), None, False
    if ctx["_of_done"]:
        return
    hi = max(b["h"] for b in bars[:n])
    lo = min(b["l"] for b in bars[:n])
    c = bars[i]["c"]
    brk = ctx["_of_brk"]
    if brk is None:
        if c > hi:
            ctx["_of_brk"] = (1, i, bars[i]["h"])
        elif c < lo:
            ctx["_of_brk"] = (-1, i, bars[i]["l"])
        return
    side, at, ext = brk
    ext = max(ext, bars[i]["h"]) if side > 0 else min(ext, bars[i]["l"])
    ctx["_of_brk"] = (side, at, ext)
    if i - at > w:
        ctx["_of_done"] = True
        return
    if lo <= c <= hi:
        book.open_next(-side, ext)
        ctx["_of_done"] = True


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
    "orb5g": {"fn": s_orb5g, "source": "orb5 with a volatility gate (Gao et al. 2018 conditioning)",
              "grid": {"stop": ["none", "bar"], "gate": ["high", "low"]}},
    "noiseg": {"fn": s_noiseg, "source": "noise area, long-only and volatility-gated variants",
               "grid": {"lookback": [14], "mult": [1.0, 1.5], "long_only": [True, False], "gate": ["none", "high"]}},
    "rod": {"fn": s_rod, "source": "Baltussen, Da, Lammers & Martens 2021 JFE: hedging demand, last 30 min",
            "grid": {"min_bps": [0, 50, 100], "mode": ["mom", "rev"]}},
    "eodrev": {"fn": s_eodrev, "source": "Baltussen, Da & Soebhag 2025: end-of-day reversal",
               "grid": {"k": [4, 8], "side": ["both", "long"]}},
    "lunch": {"fn": s_lunch, "source": "Quantpedia: lunch effect, long 12:00 to 14:00", "grid": {}},
    "vwapre": {"fn": s_vwapre, "source": "practitioner VWAP reclaim (long only)", "grid": {"n": [6, 12]}},
    "orbfail": {"fn": s_orbfail, "source": "failed opening-range breakout fade",
                "grid": {"bars": [3, 6], "within": [3, 6]}},
    "orb": {"fn": s_orb, "source": "Crabel 1990, opening range breakout",
            "grid": {"bars": [3, 6], "stop": ["mid", "opposite"], "last": [23]}},
    "noise": {"fn": s_noise, "source": "Zarattini, Aziz & Barbon 2024, SFI 24-97",
              "grid": {"lookback": [10, 14], "mult": [1.0, 1.5]}},
    "noisepb": {"fn": s_noisepb, "source": "Concretum 2026 QuanTip: pullback-entry overlay on the noise area",
                "grid": {"lookback": [14], "mult": [1.0, 1.5], "wait": [3, 5]}},
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
    rod_by = {}
    out = {}
    for sym, ss in universe_sessions.items():
        for k, (d, bars) in enumerate(ss):
            rv = first_bar_rvol(ss, k)
            out[(sym, d)] = {"rvol": rv, "rvol_rank": None, "atr14": atr14(ss, k),
                             "rod_rank": None, "rod_n": None}
            out[(sym, d)].update(range_stats(ss, k))
            if rv is not None:
                by_date.setdefault(d, []).append((rv, sym))
            if k > 0 and len(ss[k - 1][1]) == SESSION_BARS and len(bars) > 71:
                rod_by.setdefault(d, []).append((bars[71]["c"] / ss[k - 1][1][-1]["c"] - 1, sym))
    for d, rows in by_date.items():
        for n, (_, sym) in enumerate(sorted(rows, reverse=True)):
            out[(sym, d)]["rvol_rank"] = n + 1
    for d, rows in rod_by.items():
        for n, (_, sym) in enumerate(sorted(rows, reverse=True)):   # rank 1 = biggest winner
            out[(sym, d)]["rod_rank"] = n + 1
            out[(sym, d)]["rod_n"] = len(rows)
    return out


def range_stats(ss, k, n=20):
    """Yesterday's (high - low) / close, and the median of that over the n sessions before it."""
    rs = []
    for j in range(max(0, k - n - 1), k):
        b = ss[j][1]
        if len(b) == SESSION_BARS:
            rs.append((max(x["h"] for x in b) - min(x["l"] for x in b)) / b[-1]["c"])
    if len(rs) < 10:
        return {"prev_range": None, "median_range": None}
    return {"prev_range": rs[-1], "median_range": statistics.median(rs[:-1])}


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
    cuts = (dates[int(len(dates) * SPLIT[0])], dates[int(len(dates) * SPLIT[1])])
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
                        trades.append((d, sym, r, r + cost_bps))   # net, and gross in the trade's direction
                        daily.setdefault(d, []).append(r)
            results.append(summarize(name, p, spec["source"], trades, daily, dates, cuts))
    chosen = choose(results, dates, cuts, cost_bps)
    for r in results:
        r.pop("_trades", None)
    return {"dates": [dates[0], dates[-1]], "n_dates": len(dates), "oos_from": cuts[0], "ho_from": cuts[1],
            "cost_bps": cost_bps, "symbols": sorted(universe_sessions), "variants": results,
            "chosen": chosen}


def stats(series):
    n = len(series)
    if n < 2:
        return {"n": n, "mean": series[0] if n else 0.0, "sd": 0.0, "t": 0.0, "sharpe": 0.0}
    m = statistics.mean(series)
    sd = statistics.stdev(series)
    t = m / (sd / math.sqrt(n)) if sd > 0 else 0.0
    return {"n": n, "mean": m, "sd": sd, "t": t, "sharpe": (m / sd * math.sqrt(252)) if sd > 0 else 0.0}


def summarize(name, p, source, trades, daily, dates, cuts):
    """cuts = (oos_from, ho_from): IS before the first, OOS between, HOLDOUT from the second.
    A bare date is accepted too (IS before it, everything after is OOS; no holdout)."""
    if isinstance(cuts, str):
        cuts = (cuts, "9999-12-31")
    c1, c2 = cuts

    def part(pred):
        # equal-weight portfolio of that day's trades; a day with no trade earns 0
        series = [statistics.mean(daily[d]) if d in daily else 0.0 for d in dates if pred(d)]
        tr = [t[2] for t in trades if pred(t[0])]
        s = stats(series)
        s["trades"] = len(tr)
        s["win"] = (sum(1 for r in tr if r > 0) / len(tr)) if tr else 0.0
        s["avg_trade_bps"] = statistics.mean(tr) if tr else 0.0
        return s
    return {"strategy": name, "params": p, "source": source, "_trades": trades,
            "all": part(lambda d: True), "is": part(lambda d: d < c1),
            "oos": part(lambda d: c1 <= d < c2), "ho": part(lambda d: d >= c2), "post": part(lambda d: d >= c1)}


def direction_placebo(trades, dates, from_date, cost_bps, real_t, reps=PLACEBO_REPS, seed=17):
    """Keep every trade's timing, flip its side at random: does the long/short call add anything?
    -> share of flipped copies whose post-IS t is >= the real one."""
    import random
    rnd = random.Random(seed)
    post = [d for d in dates if d >= from_date]
    tr = [t for t in trades if t[0] >= from_date]
    hits = 0
    for _ in range(reps):
        by = {}
        for d, _, net, gross in tr:
            by.setdefault(d, []).append(net if rnd.random() < 0.5 else -gross - cost_bps)
        t = stats([statistics.mean(by[d]) if d in by else 0.0 for d in post])["t"]
        if t >= real_t:
            hits += 1
    return hits / float(reps)


def choose(results, dates=None, cuts=None, cost_bps=COST_BPS):
    """Per strategy: the variant with the best IN-SAMPLE Sharpe (OOS and HOLDOUT are never used to
    choose). PASS needs IS t >= MIN_IS_T, positive OOS and HOLDOUT means, t >= KEEP_OOS_T on all
    data after IS (Harvey, Liu & Zhu 2016), enough trades, and beating random side flips of its own
    trades at p < PLACEBO_P / (strategies placebo-tested). "watch" = the old loose rule (IS Sharpe
    >= 0.5 and a positive mean after IS): shown in reports, never used in the live signal.
    Results without a holdout (old callers) treat OOS as everything after IS."""
    best = {}
    for r in results:
        cur = best.get(r["strategy"])
        if cur is None or r["is"]["sharpe"] > cur["is"]["sharpe"]:
            best[r["strategy"]] = r

    def post(r):
        return r.get("post") or r["oos"]

    def gates(r):
        ho = r.get("ho")
        return (r["is"].get("t", r["is"]["sharpe"]) >= MIN_IS_T if "t" in r["is"] else True) and \
            r["is"]["trades"] >= MIN_TRADES and r["oos"]["mean"] > 0 and (ho is None or ho["mean"] > 0) and \
            post(r)["t"] >= KEEP_OOS_T and post(r)["trades"] >= MIN_TRADES // 2

    cands = [r for r in best.values() if gates(r)]
    alpha = PLACEBO_P / max(1, len(cands))
    out = []
    for name, r in best.items():
        ok = gates(r)
        pp = None
        if ok and dates is not None and r.get("_trades") is not None:
            pp = direction_placebo(r["_trades"], dates, cuts[0], cost_bps, post(r)["t"])
            ok = pp < alpha
        watch = r["is"]["sharpe"] >= KEEP_IS_SHARPE and post(r)["mean"] > 0
        out.append({"strategy": name, "params": r["params"], "keep": ok,
                    "status": "PASS" if ok else ("watch" if watch else "drop"),
                    "is_sharpe": r["is"]["sharpe"], "is_t": r["is"].get("t"),
                    "oos_sharpe": r["oos"]["sharpe"], "oos_mean_bps": r["oos"]["mean"],
                    "ho_mean_bps": r["ho"]["mean"] if r.get("ho") else None,
                    "oos_t": post(r)["t"], "post_mean_bps": post(r)["mean"], "placebo_p": pp, "weight": 0.0})
    tot = sum(max(c["is_sharpe"], 0) for c in out if c["keep"])
    for c in out:
        c["weight"] = (max(c["is_sharpe"], 0) / tot) if (c["keep"] and tot > 0) else 0.0
    return sorted(out, key=lambda c: (c["status"] != "PASS", c["status"] != "watch", -c["oos_t"]))


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
    a, i, o, h = r["all"], r["is"], r["oos"], r.get("ho") or {"mean": float("nan")}
    q = r.get("post") or o
    return "%-6s %-30s %5d %5.0f%% %7.1f | IS t %5.2f | OOS %6.1fbp HO %6.1fbp | post %6.1fbp t=%5.2f" % (
        r["strategy"], p[:30], a["trades"], a["win"] * 100, a["avg_trade_bps"], i.get("t", 0.0),
        o["mean"], h["mean"], q["mean"], q["t"])


def report_backtest(res):
    lines = ["Strategy Lab: %d sessions %s to %s, %d symbols, %.1f bps round-trip cost" % (
        res["n_dates"], res["dates"][0], res["dates"][1], len(res["symbols"]), res["cost_bps"]),
        "In-sample before %s, OOS %s to %s, HOLDOUT from %s (OOS and HOLDOUT never pick a variant)." % (
            res["oos_from"], res["oos_from"], res.get("ho_from", "-"), res.get("ho_from", "-")),
        "",
        "%-6s %-30s %5s %6s %7s | %9s | %-25s | %s" % ("strat", "params", "trades", "win", "avg bp",
                                                     "IS t", "OOS / HOLDOUT bp a day", "after IS"),
        "-" * 118]
    for r in sorted(res["variants"], key=lambda r: (r["strategy"], -r["is"]["sharpe"])):
        lines.append(fmt_variant(r))
    lines += ["", "Chosen (best in-sample variant per strategy):"]
    for c in res["chosen"]:
        lines.append("  %-7s %-5s IS t %5.2f | after IS %6.1f bp/day t %5.2f | placebo p %s | weight %.2f  %s" % (
            c["strategy"], c.get("status", "KEEP" if c["keep"] else "drop"), c.get("is_t") or 0.0,
            c.get("post_mean_bps", c["oos_mean_bps"]), c["oos_t"],
            ("%.3f" % c["placebo_p"]) if c.get("placebo_p") is not None else "  -  ",
            c["weight"], json.dumps(c["params"], sort_keys=True)))
    lines += ["", "PASS needs: IS t >= %.1f, OOS and HOLDOUT means > 0, t >= %.1f on everything after IS (Harvey,"
              % (MIN_IS_T, KEEP_OOS_T),
              "Liu & Zhu 2016), %d IS / %d later trades, and beating random side flips of its own trades at" % (
                  MIN_TRADES, MIN_TRADES // 2),
              "p < %.2f / strategies tested. 'watch' = IS Sharpe >= %.1f and a positive mean after IS: not in the" % (
                  PLACEBO_P, KEEP_IS_SHARPE),
              "live signal. Research, not financial advice."]
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


ALPACA = "https://data.alpaca.markets/v2/stocks/%s/bars"
ALPACA_STORE = os.path.join(HERE, "data", "alpaca")


def iso_to_epoch(t):
    """'2016-01-04T14:30:00Z' -> epoch seconds."""
    d = datetime.datetime.strptime(t[:19], "%Y-%m-%dT%H:%M:%S")
    return int((d - EPOCH).total_seconds())


def alpaca_page(sym, start, end, token=None, feed="sip"):
    q = {"timeframe": "5Min", "start": start, "end": end, "feed": feed, "adjustment": "split", "limit": "10000"}
    if token:
        q["page_token"] = token
    url = ALPACA % urllib.parse.quote(sym) + "?" + urllib.parse.urlencode(q)
    for attempt in range(4):
        try:
            # credentials are added by the session's network proxy (or pass APCA headers yourself)
            hdr = {"User-Agent": UA, "Accept": "application/json"}
            kid, sec = os.environ.get("APCA_API_KEY_ID"), os.environ.get("APCA_API_SECRET_KEY")
            if kid and sec:
                hdr.update({"APCA-API-KEY-ID": kid, "APCA-API-SECRET-KEY": sec})
            req = urllib.request.Request(url, headers=hdr)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(15 * (attempt + 1))
                continue
            if e.code in (401, 403):
                raise LabError("Alpaca refused the request (HTTP %d): check the API key" % e.code)
            raise LabError("Alpaca answered HTTP %d for %s" % (e.code, sym))
        except (urllib.error.URLError, OSError) as e:
            if attempt == 3:
                raise LabError("could not reach Alpaca: %s" % getattr(e, "reason", e))
            time.sleep(5)
    raise LabError("Alpaca kept rate limiting")


def parse_alpaca(bars):
    """Alpaca bar list -> {ts: [o,h,l,c,v]} for regular-session 5-min bars."""
    out = {}
    for b in bars:
        ts = iso_to_epoch(b["t"])
        local = to_eastern(utc_of(ts))
        mins = local.hour * 60 + local.minute - OPEN_MIN
        if ts % INTERVAL or mins < 0 or mins >= SESSION_BARS * 5:
            continue
        out[str(ts)] = [float(b["o"]), float(b["h"]), float(b["l"]), float(b["c"]), float(b.get("v") or 0)]
    return out


def cmd_fetch_alpaca(a):
    """Years of 5-minute bars from Alpaca's free market data API (SIP feed, split-adjusted, 2016+).
    Saved per symbol in data/alpaca/ (not committed: re-downloadable)."""
    end = (datetime.datetime.utcnow() - datetime.timedelta(minutes=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for s in a.symbols:
        old = load_store(s, ALPACA_STORE)
        start = a.start + "T00:00:00Z"
        if old and not a.full:
            start = datetime.datetime.utcfromtimestamp(max(map(int, old)) + 1).strftime("%Y-%m-%dT%H:%M:%SZ")
        new, token, pages = {}, None, 0
        try:
            while True:
                res = alpaca_page(s, start, end, token)
                new.update(parse_alpaca(res.get("bars") or []))
                pages += 1
                token = res.get("next_page_token")
                if not token:
                    break
                time.sleep(0.35)   # free plan: 200 requests a minute
        except LabError as e:
            print("%-6s stopped: %s (%d pages kept)" % (s, e, pages))
            if not new:
                if "refused" in str(e):
                    return 1
                continue
        allb = merge(old, new)
        save_store(s, allb, ALPACA_STORE)
        ss = sessions_of(allb)
        full = sum(1 for _, b in ss if len(b) == SESSION_BARS)
        print("%-6s %7d new bars, %3d pages, %5d full sessions %s to %s" % (
            s, len(set(new) - set(old)), pages, full, ss[0][0] if ss else "-", ss[-1][0] if ss else "-"))
    return 0


LONG_STORE = os.path.join(HERE, "data", "long")      # years of 5-min bars, committed (the quota is precious)
AV_URL = "https://www.alphavantage.co/query"
AV_DAILY_LIMIT = 25


def av_key():
    """Alpha Vantage key from ALPHAVANTAGE_API_KEY (or APCA_API_KEY_ID, where it was first saved)."""
    for name in ("ALPHAVANTAGE_API_KEY", "ALPHA_VANTAGE_API_KEY", "APCA_API_KEY_ID"):
        v = os.environ.get(name)
        if v and v.strip():
            return v.strip()
    raise LabError("no Alpha Vantage key: set ALPHAVANTAGE_API_KEY in the environment settings, "
                   "then start a new session")


def eastern_to_epoch(local):
    """Naive New York time -> epoch seconds (tries EDT, then EST)."""
    for hours in (4, 5):
        utc = local + datetime.timedelta(hours=hours)
        if to_eastern(utc) == local:
            return int((utc - EPOCH).total_seconds())
    return int((local + datetime.timedelta(hours=5) - EPOCH).total_seconds())


def parse_av_csv(text):
    """Alpha Vantage intraday CSV (timestamp,open,high,low,close,volume; New York time) ->
    {ts: [o,h,l,c,v]} with ts = bar START. Days labelled 09:35..16:00 are bar-end labels and
    are shifted back 5 minutes; days labelled 09:30..15:55 are already starts."""
    first = text.lstrip()[:200]
    if not first.startswith("timestamp"):
        raise LabError("Alpha Vantage: %s" % " ".join(first.split())[:180])
    rows = {}
    for line in text.strip().splitlines()[1:]:
        f = line.split(",")
        if len(f) < 6:
            continue
        t = datetime.datetime.strptime(f[0].strip(), "%Y-%m-%d %H:%M:%S")
        rows.setdefault(t.date(), []).append((t, [float(x) for x in f[1:6]]))
    out = {}
    for day, items in rows.items():
        times = sorted(t for t, _ in items)
        shift = datetime.timedelta(minutes=5) if times[0].time() == datetime.time(9, 35) else datetime.timedelta(0)
        for t, ohlcv in items:
            start = t - shift
            mins = start.hour * 60 + start.minute - OPEN_MIN
            if 0 <= mins < SESSION_BARS * 5 and mins % 5 == 0:
                out[str(eastern_to_epoch(start))] = ohlcv
    return out


TIINGO_URL = "https://api.tiingo.com/iex/%s/prices"
TIINGO_YEARS = 4                # default look-back; Tiingo's IEX 5-minute history goes back to Dec 2016
TIINGO_PAUSE = 75.0             # seconds between requests: stays under the free plan's ~50 an hour


def tiingo_page(sym, start, end):
    """One Tiingo IEX request (at most 10,000 bars come back, the newest ones, so keep ranges short).
    The key goes in 'Authorization: Token ...': added by the session's network proxy, or from
    TIINGO_API_KEY when set."""
    q = {"startDate": start, "endDate": end, "resampleFreq": "5min",
         "columns": "open,high,low,close,volume", "afterHours": "false"}
    url = TIINGO_URL % urllib.parse.quote(sym.lower()) + "?" + urllib.parse.urlencode(q)
    hdr = {"User-Agent": UA, "Accept": "application/json"}
    key = os.environ.get("TIINGO_API_KEY", "").strip()
    if key:
        hdr["Authorization"] = "Token " + key
    for attempt in range(7):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=hdr), timeout=90) as r:
                data = json.loads(r.read().decode("utf-8"))
            if isinstance(data, dict):     # {"detail": "..."} on errors
                raise LabError("Tiingo: %s" % data.get("detail", data))
            return data
        except urllib.error.HTTPError as e:
            if e.code == 429:              # free plan: hourly request cap; wait it out
                print("  Tiingo rate limit; waiting 10 minutes (attempt %d/6)" % (attempt + 1), flush=True)
                time.sleep(600)
                continue
            if e.code in (401, 403):
                raise LabError("Tiingo refused the request (HTTP %d): check the API key" % e.code)
            raise LabError("Tiingo answered HTTP %d for %s" % (e.code, sym))
        except (urllib.error.URLError, OSError) as e:
            if attempt >= 3:
                raise LabError("could not reach Tiingo: %s" % getattr(e, "reason", e))
            time.sleep(10)
    raise LabError("Tiingo kept rate limiting; run again later, it resumes")


EARLY_CLOSE_SLOT = 42   # 13:00 New York: the first bar after an early close


def nyse_early_close(d):
    """True on NYSE 13:00 early-close days: the day after Thanksgiving, Christmas Eve (a weekday,
    not itself a holiday) and July 3 (a weekday, when July 4 is a weekday holiday)."""
    if d.month == 11 and d.weekday() == 4:
        first_thu = 1 + (3 - datetime.date(d.year, 11, 1).weekday()) % 7
        return d.day == first_thu + 22
    if d.month == 12 and d.day == 24:
        return d.weekday() < 4          # Mon-Thu; on a Friday Dec 24 is the observed Christmas holiday
    if d.month == 7 and d.day == 3:
        return d.weekday() < 4          # Mon-Thu; on a Friday July 3 is the observed holiday
    return False


def drop_after_early_close(bars):
    """Remove bars at or after 13:00 on early-close days (feeds such as Tiingo IEX keep printing
    after-hours trades and filler bars there, which would pass for the regular session)."""
    out = {}
    for k, v in bars.items():
        local = to_eastern(utc_of(int(k)))
        if nyse_early_close(local.date()) and (local.hour * 60 + local.minute - OPEN_MIN) // 5 >= EARLY_CLOSE_SLOT:
            continue
        out[k] = v
    return out


def parse_tiingo(rows, trading_days=None):
    """Tiingo bar list -> {ts: [o,h,l,c,v]} for regular-session 5-min bars (ts = bar start).
    Tiingo can emit flat filler bars on market holidays; days in which no bar traded are dropped.
    Volume is IEX-only (a slice of consolidated volume); prices are unadjusted."""
    out, traded = {}, set()
    for b in rows:
        if b.get("open") is None or b.get("close") is None:
            continue
        ts = iso_to_epoch(b["date"])
        local = to_eastern(utc_of(ts))
        mins = local.hour * 60 + local.minute - OPEN_MIN
        if ts % INTERVAL or mins < 0 or mins >= SESSION_BARS * 5:
            continue
        v = float(b.get("volume") or 0)
        out[str(ts)] = [float(b["open"]), float(b["high"]), float(b["low"]), float(b["close"]), v]
        if v > 0:
            traded.add(local.date())
    return drop_after_early_close({k: v for k, v in out.items() if to_eastern(utc_of(int(k))).date() in traded})


def quarter_chunks(start, end):
    """[(YYYY-MM-DD, YYYY-MM-DD), ...] covering start..end in calendar quarters (< 10,000 bars each)."""
    d = datetime.date.fromisoformat(start)
    end = datetime.date.fromisoformat(end)
    out = []
    while d <= end:
        q_end_month = ((d.month - 1) // 3) * 3 + 3
        nxt = datetime.date(d.year + (q_end_month == 12), q_end_month % 12 + 1, 1)
        out.append((d.isoformat(), min(nxt - datetime.timedelta(days=1), end).isoformat()))
        d = nxt
    return out


def cmd_fetch_tiingo(a):
    """Years of 5-minute bars (December 2016 onward) from Tiingo's free IEX endpoint, one quarter per
    request, oldest first. Saved after every quarter into the long store; rerun to resume or update."""
    os.makedirs(a.store_long, exist_ok=True)
    today = datetime.date.today()
    first = a.start or today.replace(year=today.year - TIINGO_YEARS, day=min(today.day, 28)).isoformat()
    today = today.isoformat()
    used = 0
    for s in a.symbols:
        bars = load_store(s, a.store_long)
        start = first
        if bars and not a.full:
            last = to_eastern(utc_of(max(map(int, bars)))).date()
            start = max(start, last.isoformat())      # re-fetch the last day in case it was partial
        got = 0
        for c0, c1 in quarter_chunks(start, today):
            try:
                rows = tiingo_page(s, c0, c1)
            except LabError as e:
                print("%-6s %s..%s: %s" % (s, c0, c1, e), flush=True)
                if "refused" in str(e):
                    return 1
                if "rate limit" in str(e):
                    print("Saved what arrived (%d requests). Run the same command later; it resumes." % used)
                    return 0
                break
            used += 1
            new = parse_tiingo(rows)
            if new:
                bars.update(new)
                save_store(s, bars, a.store_long)
                got += len(new)
            time.sleep(a.pause)
        ss = sessions_of(bars)
        full = sum(1 for _, b in ss if len(b) == SESSION_BARS)
        print("%-6s %7d bars fetched, %5d full sessions %s to %s" % (
            s, got, full, ss[0][0] if ss else "-", ss[-1][0] if ss else "-"), flush=True)
    print("%d Tiingo request%s used." % (used, "" if used == 1 else "s"))
    return 0


def av_error_kind(text):
    """Classify an Alpha Vantage non-CSV reply: 'premium' (endpoint needs a paid plan),
    'daily' (25-a-day limit spent), 'throttle' (too many per second/minute), or None."""
    t = text.lower()
    if t.lstrip().startswith("timestamp"):
        return None
    if "premium endpoint" in t:
        return "premium"
    if "per day" in t or "daily" in t:
        return "daily"
    if "per second" in t or "per minute" in t or "sparingly" in t or "rate limit" in t:
        return "throttle"
    return None


def av_progress_path(store):
    return os.path.join(store, "progress.json")


def months_back(newest, oldest):
    y, m = map(int, newest.split("-"))
    oy, om = map(int, oldest.split("-"))
    out = []
    while (y, m) >= (oy, om):
        out.append("%04d-%02d" % (y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return out


def cmd_fetch_av(a):
    """Fill the long 5-minute store month by month from Alpha Vantage, newest first, within the
    free limit (25 requests a day). Run it every day; it resumes where it stopped."""
    key = av_key()
    os.makedirs(a.store_long, exist_ok=True)
    prog = {}
    if os.path.exists(av_progress_path(a.store_long)):
        with open(av_progress_path(a.store_long)) as fh:
            prog = json.load(fh)
    today = datetime.date.today()
    last_full = (today.replace(day=1) - datetime.timedelta(days=1)).strftime("%Y-%m")
    used = 0
    for s in a.symbols:
        done = set(prog.get(s, []))
        todo = [m for m in months_back(last_full, a.oldest) if m not in done]
        if not todo:
            continue
        bars = load_store(s, a.store_long)
        got = 0
        for m in todo:
            if used >= a.max_requests:
                break
            q = {"function": "TIME_SERIES_INTRADAY", "symbol": s, "interval": "5min", "month": m,
                 "outputsize": "full", "extended_hours": "false", "adjusted": "true", "datatype": "csv",
                 "apikey": key}
            req = urllib.request.Request(AV_URL + "?" + urllib.parse.urlencode(q), headers={"User-Agent": UA})
            try:
                for attempt in range(3):
                    with urllib.request.urlopen(req, timeout=60) as r:
                        text = r.read().decode("utf-8", "replace")
                    used += 1
                    if av_error_kind(text) != "throttle":
                        break
                    time.sleep(15)   # per-second/minute throttle: wait and retry the same month
                new = parse_av_csv(text)
            except LabError as e:
                kind = av_error_kind(str(e))
                print("%-6s %s: %s" % (s, m, e))
                if kind == "premium":
                    print("Alpha Vantage serves 5-minute intraday bars only on premium plans; this key is "
                          "valid but free. Nothing was saved. Use `fetch-alpaca` for free 5-minute history, "
                          "or a premium Alpha Vantage key. (%d request%s used)" % (used, "" if used == 1 else "s"))
                    return 1
                if kind == "daily":
                    print("Alpha Vantage daily limit reached after %d request%s this run. Run again tomorrow; "
                          "it resumes." % (used, "" if used == 1 else "s"))
                    return 0
                break
            except (urllib.error.URLError, OSError) as e:
                print("%-6s %s: could not reach Alpha Vantage: %s" % (s, m, getattr(e, "reason", e)))
                break
            bars.update(new)
            done.add(m)
            got += 1
            time.sleep(13)   # 5 requests a minute on the free key
        if got:
            save_store(s, bars, a.store_long)
            prog[s] = sorted(done)
            with open(av_progress_path(a.store_long), "w") as fh:
                json.dump(prog, fh, indent=1, sort_keys=True)
            ss = sessions_of(bars)
            print("%-6s +%d months, %d full sessions %s to %s" % (
                s, got, sum(1 for _, b in ss if len(b) == SESSION_BARS), ss[0][0], ss[-1][0]))
        if used >= a.max_requests:
            print("Daily request budget used (%d). Run again tomorrow; it resumes." % used)
            break
    return 0


COST_SWEEP = (0.0, 0.5, 1.0, 2.0, 3.0, 5.0)


def cost_sweep(universe_sessions, costs=COST_SWEEP, only=None):
    """Rerun at several round-trip costs. Per strategy: the chosen variant's mean bp/day and t after IS
    at each cost, and the break-even cost per trade (gross bp/day / trades per day after IS)."""
    rows = {}
    for c in costs:
        res = backtest(universe_sessions, c, only=only)
        for ch in res["chosen"]:
            rows.setdefault(ch["strategy"], {})[c] = ch
            if c == 0.0:
                v = [r for r in res["variants"] if r["strategy"] == ch["strategy"] and r["params"] == ch["params"]][0]
                days = max(1, v["post"]["n"])
                rows[ch["strategy"]]["_tpd"] = v["post"]["trades"] / float(days)
    out = []
    for name, by in rows.items():
        g = by.get(0.0)
        tpd = by.get("_tpd", 0.0)
        be = (g["post_mean_bps"] / tpd) if (g and tpd > 0 and g["post_mean_bps"] > 0) else None
        out.append({"strategy": name, "break_even_bps": be, "trades_per_day": tpd,
                    "by_cost": {str(c): {"params": by[c]["params"], "mean": by[c]["post_mean_bps"],
                                         "t": by[c]["oos_t"], "status": by[c]["status"]}
                                for c in costs if c in by}})
    return sorted(out, key=lambda r: -(r["break_even_bps"] or -1))


def cmd_costs(a):
    rows = cost_sweep(load_universe(a.symbols, a.store), only=a.only)
    if a.json:
        print(json.dumps(rows, indent=1, sort_keys=True))
        return 0
    head = "".join("%13s" % ("%.1f bp" % c) for c in COST_SWEEP)
    print("Cost sweep: mean bp/day and t after IS for each strategy's chosen variant, by round-trip cost.")
    print("%-8s %10s %6s%s" % ("strategy", "break-even", "tr/day", head))
    for r in rows:
        cells = "".join("%13s" % ("%+.1f t%+.1f" % (r["by_cost"][str(c)]["mean"], r["by_cost"][str(c)]["t"])
                                  if str(c) in r["by_cost"] else "-") for c in COST_SWEEP)
        be = ("%.1f bp" % r["break_even_bps"]) if r["break_even_bps"] is not None else "never"
        print("%-8s %10s %6.2f%s" % (r["strategy"], be, r["trades_per_day"], cells))
    print("\nBreak-even = the round-trip cost per trade at which the zero-cost edge after IS is used up.")
    print("Compare with costs.py table. Research, not financial advice.")
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
    p = sub.add_parser("fetch-av", help="years of 5-min bars from Alpha Vantage, 25 months a day (free key)")
    common(p)
    p.add_argument("--oldest", default="2006-01", help="oldest month to fetch (YYYY-MM)")
    p.add_argument("--max-requests", type=int, default=AV_DAILY_LIMIT)
    p.add_argument("--store-long", default=LONG_STORE)
    p = sub.add_parser("fetch-alpaca", help="years of 5-min bars from Alpaca (free key needed)")
    common(p)
    p.add_argument("--start", default="2016-01-01")
    p.add_argument("--full", action="store_true", help="re-download from --start even if data exists")
    p = sub.add_parser("fetch-tiingo", help="last 4 years of 5-min bars from Tiingo IEX (free key)")
    common(p)
    p.add_argument("--start", default=None, help="first day YYYY-MM-DD (default: 4 years ago; Dec 2016 at most)")
    p.add_argument("--full", action="store_true", help="re-download from --start even if data exists")
    p.add_argument("--pause", type=float, default=TIINGO_PAUSE, help="seconds between requests (default 75)")
    p.add_argument("--store-long", default=LONG_STORE)
    p = sub.add_parser("backtest", help="every strategy and variant, IS vs OOS, after costs")
    common(p)
    p.add_argument("--only", type=lambda s: s.split(","), help="comma list of strategies")
    p.add_argument("--write", nargs="?", const=os.path.join(RESULTS, "latest.json"), metavar="PATH")
    p = sub.add_parser("costs", help="cost sweep: each strategy at 0 to 5 bp round trip, break-even cost")
    common(p)
    p.add_argument("--only", type=lambda s: s.split(","), help="comma list of strategies")
    p = sub.add_parser("signal", help="today's live signal from the kept strategies")
    common(p)
    p.add_argument("--chosen", default=os.path.join(RESULTS, "latest.json"),
                   help="use the choice saved by backtest --write (default results/latest.json)")
    a = ap.parse_args(argv)
    if not a.cmd:
        ap.print_help()
        return 1
    try:
        return {"fetch": cmd_fetch, "fetch-av": cmd_fetch_av, "fetch-alpaca": cmd_fetch_alpaca,
                "fetch-tiingo": cmd_fetch_tiingo, "backtest": cmd_backtest, "costs": cmd_costs,
                "signal": cmd_signal}[a.cmd](a)
    except LabError as e:
        print("lab.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
