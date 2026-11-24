#!/usr/bin/env python3
"""trader-lab bot: the bot makes the trade calls, on PAPER. Nothing reaches any account.

    python3 bot.py stocks       # hourly 10:17-15:17 New York: take the best fresh opening-range breakouts
    python3 bot.py fxcrypto     # hourly 24/7: take fresh crypto / forex setups
    python3 bot.py settle       # close open trades from real prices since entry
    python3 bot.py report [--json]

The owner asked on 2026-11-24 that the trade calls be the bot's. These rules were fixed before the
first bot trade (RESEARCH.md, 2026-11-24) and are not tuned on results:

STOCKS  whole-market opening-range breakout (scan.py orb, 15-minute range), ranked by today's traded
        value, and only while the price is still above the range high. Long only. At most 10 new a run, 50 a day, $500 total risk a day,
        no entries after 15:00 (raised from 2 / 5 / $50, then 4 / 20 / $200, on 2026-11-24 at the owner's request).
        Stop at the opening-range midpoint, target 2R, $10 risk, $1,000 a position at most, the
        paper.py cost filter. Entered at the open of the next 5-minute bar after the decision, out by
        15:55 (paper.fill_long).
FXCRYPTO only setups that are NEW since the previous run. Trend setups only: long on a 20-hour high
        breakout or a reclaim of the 20-hour average, short on a 20-hour closing-low breakdown. The
        RSI setups (oversold, overbought, bounce) are not traded: on a trend name they contradict the
        breakout and the lab found no edge in either. A name with both a long and a short setup is
        skipped. At most 2 new an hour, 1 open per name, 6 open at once, and (since 2026-11-24, group
        cap) at most 1 crypto, 1 metal and 2 forex open. Stop 1.5 x ATR(14 hours), target 2R, $10
        risk, closed after 24 hours. Entered at the open of the next 1-hour bar; a bar touching stop
        and target is the stop.
COSTS   (since 2026-11-24, Exness Standard published averages rounded up) a round trip: FX majors 2 bp,
        crosses 3 bp, gold / silver 3 bp, BTC / ETH 6 bp, other crypto 15 bp, plus swap for each
        00:00 UTC crossed: 0.5 bp FX / metals, 3 bp crypto.
CHALLENGERS (pre-registered in bot_backtest.py, 2026-11-24) are traded on paper next to the live rule,
        each with its own caps, tagged by "variant": stocks spytrend / first / fresh, crypto-forex
        btctrend / noweekend. A challenger replaces the live rule only after 6+ weeks forward and a
        daily t >= 2 on the difference; never from a backtest alone.

P&L is in USD on a USD notional sized so the stop loses $10 (an approximation for non-USD pairs).
The pre-registered paper trial (paper/PLAN.md) and its pass bar are separate and unchanged.
Research, not financial advice.
"""

import argparse
import datetime
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "trader-scanner"))
import lab  # noqa: E402
import paper  # noqa: E402
import scan  # noqa: E402
import fxcrypto  # noqa: E402

LEDGER = os.path.join(HERE, "paper", "bot", "ledger.json")
STOCK = {"per_run": 10, "per_day": 50, "day_risk_usd": 500.0, "last_entry": "15:00", "target_r": 2.0}
FX = {"per_run": 2, "max_open": 6, "atr_n": 14, "atr_mult": 1.5, "target_r": 2.0, "risk_usd": 10.0,
      "max_hours": 24}
GROUP_CAP = {"crypto": 1, "metal": 1, "forex": 2}
MAJORS = {"EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "USDCHF=X", "NZDUSD=X"}
METALS = {"GC=F", "SI=F"}
STOCK_VARIANTS = ("live", "spytrend", "first", "fresh")
FX_VARIANTS = ("live", "btctrend", "noweekend")


def group(sym):
    return "crypto" if sym in fxcrypto.CRYPTO else "metal" if sym in METALS else "forex"


def cost_bps(sym):
    """Round-trip spread cost (Exness Standard, published averages 2026, rounded up)."""
    if sym in ("BTC-USD", "ETH-USD"):
        return 6.0
    if sym in fxcrypto.CRYPTO:
        return 15.0
    if sym in METALS:
        return 3.0
    return 2.0 if sym in MAJORS else 3.0


def swap_bps(sym):
    """Overnight financing for each 00:00 UTC crossed (an estimate; Exness publishes swaps only in MT5)."""
    return 3.0 if sym in fxcrypto.CRYPTO else 0.5


def nights(t0, t1):
    """00:00 UTC boundaries crossed holding from t0 to t1 (epoch seconds)."""
    return max(0, int(t1 // 86400) - int(t0 // 86400))


def variant_of(t):
    return t.get("variant", "live")
LONG_SETUPS = ("breakout_20d", "reclaim_ma20")
SHORT_SETUPS = ("breakdown_20h",)


# ---------------------------------------------------------------- ledger

def load(path=LEDGER):
    if not os.path.exists(path):
        return {"trades": [], "last_fx": {}}
    with open(path) as fh:
        return json.load(fh)


def save(led, path=LEDGER):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(led, fh, indent=1)


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


def iso(dt):
    return dt.strftime("%Y-%m-%d %H:%MZ")


def parse_iso(s):
    return datetime.datetime.strptime(s, "%Y-%m-%d %H:%MZ")


# ---------------------------------------------------------------- fx / crypto rules (pure)

def direction(setups):
    """-> 'buy', 'sell' or None (no trend setup, or both directions)."""
    long_ = any(s in LONG_SETUPS for s in setups)
    short = any(s in SHORT_SETUPS for s in setups)
    if long_ == short:
        return None
    return "buy" if long_ else "sell"


def new_setups(rows, last):
    """rows from fxcrypto.run; last = {symbol: [setups]} from the previous run -> {symbol: [new setups]}."""
    out = {}
    for r in rows:
        fresh = [s for s in r["setups"] if s not in (last.get(r["symbol"]) or [])]
        if fresh:
            out[r["symbol"]] = fresh
    return out


def atr(bars, n):
    """bars: [(ts, o, h, l, c)] oldest first -> average true range of the last n bars."""
    tr = []
    for i in range(1, len(bars)):
        h, l, pc = bars[i][2], bars[i][3], bars[i - 1][4]
        tr.append(max(h - l, abs(h - pc), abs(l - pc)))
    tr = tr[-n:]
    return sum(tr) / len(tr) if tr else None


def fx_plan(sym, side, last, a, cfg=FX):
    dist = cfg["atr_mult"] * a
    if not dist or dist <= 0:
        return None
    sgn = 1 if side == "buy" else -1
    kind = "crypto" if sym in fxcrypto.CRYPTO else "forex"
    return {"symbol": sym, "side": side, "entry_est": last, "stop": last - sgn * dist,
            "target": last + sgn * cfg["target_r"] * dist, "risk_usd": cfg["risk_usd"],
            "notional_usd": round(cfg["risk_usd"] / (dist / last), 2),
            "cost_bps": cost_bps(sym), "swap_bps": swap_bps(sym), "kind": kind}


def fill_hourly(bars, start_ts, side, stop, target, max_hours, now_ts):
    """bars [(ts,o,h,l,c)] complete 1-hour bars. Enter at the open of the first bar starting at or after
    start_ts. -> (entry, exit, how, entry_ts, exit_ts) or None while still open / not yet entered."""
    later = [b for b in bars if b[0] >= start_ts]
    if not later:
        return None
    e, t0 = later[0][1], later[0][0]
    for i, (t, o, h, l, c) in enumerate(later):
        first = i == 0
        if side == "buy":
            if l <= stop:
                return e, (min(stop, o) if not first else min(stop, e)), "stop", t0, t + 3600
            if h >= target:
                return e, (max(target, o) if not first else max(target, e)), "target", t0, t + 3600
        else:
            if h >= stop:
                return e, (max(stop, o) if not first else max(stop, e)), "stop", t0, t + 3600
            if l <= target:
                return e, (min(target, o) if not first else min(target, e)), "target", t0, t + 3600
        if t + 3600 >= t0 + max_hours * 3600:
            return e, c, "time", t0, t + 3600
    return None


def pnl_usd(side, entry, exit_, notional, cost_bps):
    ret = (exit_ / entry - 1) * (1 if side == "buy" else -1)
    return notional * (ret - cost_bps / 1e4)


def hourly_bars(sym, now_ts):
    doc = json.loads(scan.yahoo_get(scan.chart_path(sym, "10d", "1h")))
    res = ((doc.get("chart") or {}).get("result") or [None])[0]
    if not res:
        return []
    q = res["indicators"]["quote"][0]
    out = []
    for i, t in enumerate(res.get("timestamp") or []):
        o, h, l, c = (q[k][i] for k in ("open", "high", "low", "close"))
        if None in (o, h, l, c) or t + 3600 > now_ts:
            continue
        out.append((t, float(o), float(h), float(l), float(c)))
    return out


# ---------------------------------------------------------------- stock rules (pure)

def stock_caps(trades, date, cfg=STOCK):
    """-> how many new stock trades may be taken now, given today's bot stock trades."""
    today = [t for t in trades if t["track"] == "stocks" and t["date"] == date]
    risk = sum(t["risk_usd"] for t in today)
    room_risk = int((cfg["day_risk_usd"] - risk) // 10.0)
    return max(0, min(cfg["per_run"], cfg["per_day"] - len(today), room_risk))


def still_above(hit, price):
    """A breakout counts only while the price is still above the opening-range high: a name that
    broke out at 9:50 and fell back is a failed breakout, not a buy."""
    return bool(price) and price > float(hit["or_high"])


def next_slot(hhmm):
    """The first 5-minute bar that starts at or after hh:mm (no look-ahead)."""
    h, m = map(int, hhmm.split(":"))
    return -(-(h * 60 + m - lab.OPEN_MIN) // 5)


def slot_time(slot):
    m = lab.OPEN_MIN + 5 * slot
    return "%02d:%02d" % (m // 60, m % 60)


# ---------------------------------------------------------------- commands

def settle(led, now=None):
    now = now or utc_now()
    now_ts = (now - datetime.datetime(1970, 1, 1)).total_seconds()
    closed = []
    for t in led["trades"]:
        if t["status"] != "open":
            continue
        try:
            if t["track"] == "stocks":
                ny = lab.to_eastern(now)
                if t["date"] == ny.date().isoformat() and (ny.hour, ny.minute) < (16, 5):
                    continue
                sess = dict(lab.sessions_of(lab.parse_chart(lab.fetch_chart(t["symbol"]))))
                bars = sess.get(t["date"])
                if not bars or len(bars) <= paper.EXIT_SLOT:
                    continue
                e, x, how = paper.fill_long(bars, t["slot"], t["stop"], t["target"])
                notional = t["shares"] * e
                pnl = t["shares"] * (x - e) - notional * t["cost_bps"] / 1e4
            else:
                got = fill_hourly(hourly_bars(t["symbol"], now_ts), t["start_ts"], t["side"], t["stop"],
                                  t["target"], FX["max_hours"], now_ts)
                if not got:
                    continue
                e, x, how, t0, t1 = got
                notional = t["notional_usd"]
                c_bps = t["cost_bps"] + t.get("swap_bps", 0.0) * nights(t0, t1)
                pnl = pnl_usd(t["side"], e, x, notional, c_bps)
        except (lab.LabError, scan.ScanError, ValueError, KeyError) as err:
            print("  could not settle %s %s: %s" % (t["track"], t["symbol"], err), file=sys.stderr)
            continue
        t.update(status="closed", entry=round(e, 6), exit=round(x, 6), how=how, pnl_usd=round(pnl, 2),
                 closed_at=iso(now))
        closed.append(t)
    return closed


def cmd_settle(a):
    led = load()
    closed = settle(led)
    save(led)
    print_closed(closed)
    return 0


def print_closed(closed):
    if not closed:
        print("No bot trade closed since the last check.")
    for t in closed:
        print("  CLOSED %-8s %-4s %-9s entry %s exit %s (%s)  $%+.2f" % (
            t["track"], t["side"].upper(), t["symbol"], fxcrypto.fmt_price(t["entry"]),
            fxcrypto.fmt_price(t["exit"]), t["how"], t["pnl_usd"]))


def spy_above_200d():
    """SPY's last COMPLETE daily close above its 200-day average? (None if unknown)."""
    try:
        data, _ = scan.fetch_spark(["SPY"], "2y", "1d", 0)
        s = data["SPY"]
        today = lab.to_eastern(utc_now()).date()
        c = [x for t, x in zip(s["t"], s["c"]) if x is not None
             and lab.to_eastern(datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=t)).date() < today]
        return c[-1] > sum(c[-200:]) / 200.0 if len(c) >= 200 else None
    except (scan.ScanError, KeyError, ValueError):
        return None


def btc_trend():
    """+1 if BTC's last daily close is above its 50-day average, -1 below, None if unknown."""
    try:
        data, _ = scan.fetch_spark(["BTC-USD"], "6mo", "1d", 0)
        c = [x for x in data["BTC-USD"]["c"] if x is not None][:-1]       # drop today's forming day
        return (1 if c[-1] > sum(c[-50:]) / 50.0 else -1) if len(c) >= 50 else None
    except (scan.ScanError, KeyError, ValueError):
        return None


def stock_variant_ok(variant, hit, hhmm, spy_up):
    if variant == "spytrend":
        return spy_up is True
    if variant == "first":
        return hhmm < "10:30"
    if variant == "fresh":
        h, m = map(int, hhmm.split(":"))
        t = h * 60 + m - 60
        return hit.get("bar_start", "00:00") >= "%02d:%02d" % (t // 60, t % 60)
    return True


def cmd_stocks(a):
    led = load()
    print_closed(settle(led))
    now = utc_now()
    ny = lab.to_eastern(now)
    date, hhmm = ny.date().isoformat(), ny.strftime("%H:%M")
    if ny.weekday() >= 5 or not ("09:50" <= hhmm <= STOCK["last_entry"]):
        save(led)
        print("Bot (stocks): no new entries now (%s New York; entries 09:50 to %s on trading days)." % (
            hhmm, STOCK["last_entry"]))
        return 0
    rooms = {v: stock_caps([t for t in led["trades"] if variant_of(t) == v], date) for v in STOCK_VARIANTS}
    if not any(rooms.values()):
        save(led)
        print("Bot (stocks): today's limit is reached (%d trades or $%.0f risk)" % (STOCK["per_day"], STOCK["day_risk_usd"]) + ". No new entry.")
        return 0
    out = subprocess.run([sys.executable, paper.SCAN, "orb", "--json", "--no-write"], capture_output=True,
                         text=True, cwd=ROOT)
    try:
        doc = json.loads(out.stdout)
    except ValueError:
        save(led)
        print("Bot (stocks): the scan failed: %s" % (out.stderr.strip()[-300:]))
        return 1
    hits = {h["symbol"]: h for h in doc.get("hits", [])}
    data, _ = scan.fetch_spark(list(hits), "1d", "5m", 0.3)
    now_px = {s: v["meta"].get("regularMarketPrice") or 0 for s, v in data.items()}
    ranked = [s for _, s in sorted(((now_px[s] * (v["meta"].get("regularMarketVolume") or 0), s)
                                    for s, v in data.items() if still_above(hits[s], now_px[s])), reverse=True)]
    spy_up = spy_above_200d() if rooms.get("spytrend") else None
    cfg = dict(paper.SCANNER_CFG, target_r=STOCK["target_r"])
    slot = next_slot(hhmm)
    sess_cache, new = {}, []
    for v in STOCK_VARIANTS:
        taken = {t["symbol"] for t in led["trades"] if t["track"] == "stocks" and t["date"] == date
                 and variant_of(t) == v}
        k = 0
        for sym in ranked:
            if k >= rooms[v]:
                break
            if sym in taken or not stock_variant_ok(v, hits[sym], hhmm, spy_up):
                continue
            if sym not in sess_cache:
                try:
                    sess_cache[sym] = dict(lab.sessions_of(lab.parse_chart(lab.fetch_chart(sym)))).get(date) or []
                except lab.LabError:
                    sess_cache[sym] = None
            if not sess_cache[sym]:
                continue
            p = paper.scanner_plan(dict(hits[sym], price=now_px[sym]), sess_cache[sym][:slot], set(), cfg)
            if not p:
                continue
            p.update(track="stocks", variant=v, date=date, opened_at=iso(now), decided_at=hhmm, slot=slot,
                     status="open", risk_usd=p["max_loss_usd"], setup="opening-range breakout",
                     id="S-%s-%s-%s" % (v, date, sym))
            led["trades"].append(p)
            new.append(p)
            k += 1
    save(led)
    live = [p for p in new if p["variant"] == "live"]
    print("Bot (stocks, SIMULATED), %s %s New York: %d breakouts; the bot took %d%s." % (
        date, hhmm, len(hits), len(live), "" if rooms["live"] else " (today's limit reached)"))
    for p in live:
        print("  BUY %-6s ~%.2f  %d sh  stop %.2f  target %.2f (2R)  risk $%.2f  in at %s, out by 15:55" % (
            p["symbol"], p["entry_est"], p["shares"], p["stop"], p["target"], p["max_loss_usd"], slot_time(slot)))
    ch = [p for p in new if p["variant"] != "live"]
    if ch:
        print("  challengers (paper, not the live rule): " + ", ".join("%s %s" % (p["variant"], p["symbol"]) for p in ch))
    return 0


def fx_variant_ok(variant, sym, side, now, trend):
    if variant == "noweekend":
        return now.weekday() < 5 and now.hour < 21
    if variant == "btctrend" and group(sym) == "crypto":
        return trend is not None and (trend == 1) == (side == "buy")
    return True


def cmd_fxcrypto(a):
    led = load()
    print_closed(settle(led))
    now = utc_now()
    now_ts = (now - datetime.datetime(1970, 1, 1)).total_seconds()
    rows, _ = fxcrypto.run(fxcrypto.CRYPTO + fxcrypto.FOREX, now_ts)
    last = led.get("last_fx") or {}
    if not last and os.path.exists(fxcrypto.OUT):        # first run: the last hourly scan is the baseline
        with open(fxcrypto.OUT) as fh:
            last = {r["symbol"]: r["setups"] for r in json.load(fh).get("rows", [])}
    fresh = new_setups(rows, last)
    led["last_fx"] = {r["symbol"]: r["setups"] for r in rows}
    by = {r["symbol"]: r for r in rows}
    cands = []
    for sym, fs in fresh.items():
        side = direction(by[sym]["setups"])
        if side and any(s in (LONG_SETUPS if side == "buy" else SHORT_SETUPS) for s in fs):
            cands.append((-abs(by[sym]["chg_1h_pct"] or 0), sym, side))
    cands.sort()
    trend = btc_trend() if any(group(s) == "crypto" for _, s, _ in cands) else None
    bars_cache, new = {}, []
    for v in FX_VARIANTS:
        open_ = [t for t in led["trades"] if t["track"] == "fxcrypto" and t["status"] == "open" and variant_of(t) == v]
        room = max(0, min(FX["per_run"], FX["max_open"] - len(open_)))
        k = 0
        for _, sym, side in cands:
            if k >= room:
                break
            g = group(sym)
            if any(t["symbol"] == sym for t in open_) or \
                    sum(1 for t in open_ if group(t["symbol"]) == g) >= GROUP_CAP[g] or \
                    not fx_variant_ok(v, sym, side, now, trend):
                continue
            if sym not in bars_cache:
                try:
                    bars_cache[sym] = hourly_bars(sym, now_ts)
                except (scan.ScanError, ValueError) as err:
                    print("  %s: no hourly bars (%s)" % (sym, err), file=sys.stderr)
                    bars_cache[sym] = []
            bars = bars_cache[sym]
            a_ = atr(bars, FX["atr_n"]) if len(bars) > FX["atr_n"] else None
            p = fx_plan(sym, side, bars[-1][4], a_) if a_ else None
            if not p:
                continue
            p.update(track="fxcrypto", variant=v, date=iso(now)[:10], opened_at=iso(now),
                     start_ts=bars[-1][0] + 3600, status="open",
                     setup=", ".join(fxcrypto.LABELS[s] for s in by[sym]["setups"]),
                     id="F-%s-%s-%s" % (v, iso(now), sym))
            led["trades"].append(p)
            open_.append(p)
            new.append(p)
            k += 1
    save(led)
    stamp = "%s (%s New York)" % (iso(now), lab.to_eastern(now).strftime("%H:%M"))
    live = [p for p in new if p["variant"] == "live"]
    n_open = sum(1 for t in led["trades"] if t["track"] == "fxcrypto" and t["status"] == "open" and variant_of(t) == "live")
    if not live:
        print("Bot (crypto/forex, SIMULATED), %s: no new trade (%d new setups, %d open)." % (stamp, len(fresh), n_open))
    else:
        print("Bot (crypto/forex, SIMULATED), %s: the bot took %d." % (stamp, len(live)))
    for p in live:
        print("  %-4s %-16s ~%s  stop %s  target %s (2R)  $%.0f notional, risk $10  (%s)" % (
            p["side"].upper(), fxcrypto.NAMES.get(p["symbol"], p["symbol"]), fxcrypto.fmt_price(p["entry_est"]),
            fxcrypto.fmt_price(p["stop"]), fxcrypto.fmt_price(p["target"]), p["notional_usd"], p["setup"]))
    ch = [p for p in new if p["variant"] != "live"]
    if ch:
        print("  challengers (paper, not the live rule): " + ", ".join("%s %s %s" % (p["variant"], p["side"], p["symbol"]) for p in ch))
    return 0


def summary(trades, track, variant="live"):
    trades = [t for t in trades if variant_of(t) == variant]
    c = [t for t in trades if t["track"] == track and t["status"] == "closed"]
    o = [t for t in trades if t["track"] == track and t["status"] == "open"]
    pnl = [t["pnl_usd"] for t in c]
    by_day = {}
    for t in c:
        by_day[t["closed_at"][:10]] = by_day.get(t["closed_at"][:10], 0.0) + t["pnl_usd"]
    d = list(by_day.values())
    t_daily = None
    if len(d) >= 3:
        m = sum(d) / len(d)
        sd = math.sqrt(sum((x - m) ** 2 for x in d) / (len(d) - 1))
        t_daily = m / sd * math.sqrt(len(d)) if sd else None
    return {"closed": len(c), "open": len(o), "net_usd": round(sum(pnl), 2),
            "win_rate": (sum(1 for x in pnl if x > 0) / len(pnl)) if pnl else None,
            "days": len(d), "t_daily": t_daily}


def cmd_report(a):
    led = load()
    out = {k: summary(led["trades"], k) for k in ("stocks", "fxcrypto")}
    out["challengers"] = {"%s/%s" % (k, v): summary(led["trades"], k, v)
                          for k, vs in (("stocks", STOCK_VARIANTS), ("fxcrypto", FX_VARIANTS)) for v in vs if v != "live"}
    if a.json:
        print(json.dumps(out, indent=1))
        return 0
    print("Bot (SIMULATED, paper only; nothing reaches any account):")
    for k, name in (("stocks", "stocks"), ("fxcrypto", "crypto/forex")):
        s = out[k]
        print("  %-12s %d closed, net $%+.2f%s, %d open%s" % (
            name, s["closed"], s["net_usd"],
            "" if s["win_rate"] is None else ", win rate %.0f%%" % (100 * s["win_rate"]), s["open"],
            "" if s["t_daily"] is None else ", daily t %.2f over %d days" % (s["t_daily"], s["days"])))
    for k, s in out["challengers"].items():
        if s["closed"] or s["open"]:
            print("  challenger %-20s %d closed, net $%+.2f, %d open" % (k, s["closed"], s["net_usd"], s["open"]))
    for t in led["trades"]:
        if t["status"] == "open" and variant_of(t) == "live":
            print("    open: %-8s %-4s %-9s ~%s  stop %s  target %s  since %s" % (
                t["track"], t["side"].upper(), t["symbol"], fxcrypto.fmt_price(t["entry_est"]),
                fxcrypto.fmt_price(t["stop"]), fxcrypto.fmt_price(t["target"]), t["opened_at"]))
    print("A record needs weeks before it means anything. Research, not financial advice.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="the bot's simulated trade calls")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("stocks")
    sub.add_parser("fxcrypto")
    sub.add_parser("settle")
    p = sub.add_parser("report")
    p.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    fn = {"stocks": cmd_stocks, "fxcrypto": cmd_fxcrypto, "settle": cmd_settle, "report": cmd_report}.get(a.cmd)
    if not fn:
        ap.print_help()
        return 1
    return fn(a)


if __name__ == "__main__":
    sys.exit(main())
