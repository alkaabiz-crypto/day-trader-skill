#!/usr/bin/env python3
"""Backtest the bot's exact rules (bot.py) and its challengers, before trusting them.

    python3 bot_data.py fxcrypto && python3 bot_backtest.py fxcrypto [--write]
    python3 bot_data.py stocks   && python3 bot_backtest.py stocks   [--write]

PRE-REGISTERED 2026-11-24, written before any of these were run. The variants are fixed here and
are not tuned on the result. Every variant is ALSO traded forward on paper by bot.py (as a
challenger), and a challenger replaces the live rule only if, after at least 6 weeks forward, its
daily t beats the live rule's by more than 2 (difference of daily P&L, t >= 2). A backtest alone
never promotes anything.

CRYPTO / FOREX: 730 days of 1-hour bars (crypto from 2024-11, FX from 2024-02, metals from 2024-07).
  base        the live rule: a NEW 20-hour high breakout or 20-hour average reclaim (long) or 20-hour
              closing-low break (short) on the last complete hour; both directions = skip; ranked by
              the size of the last hour's move; 2 a run, 1 per name, 6 open; enter at the next hour's
              open; stop 1.5 x ATR(14), target 2R, out after 24 hours; stop first if a bar hits both.
  groupcap    base + at most 1 crypto, 1 metal and 2 forex trades open (cryptos move together).
  btctrend    groupcap + crypto only in the direction of Bitcoin's trend (BTC close vs its 50-day
              average, i.e. 1,200 hourly closes).
  noweekend   groupcap + no entries on Saturday / Sunday (UTC) or from 21:00 to 23:59 UTC (rollover).
  Costs a round trip (Exness Standard, published averages 2026, rounded UP): FX majors 2 bp, FX crosses
  3 bp, gold / silver 3 bp, BTC / ETH 6 bp, other crypto 15 bp; plus swap for each 00:00 UTC crossed:
  0.5 bp FX / metals, 3 bp crypto. A 2x cost stress is reported too.
  Placebo: the base trades' exact times and names with a random direction, 500 draws.

STOCKS: every liquid US stock ($5+, 1M+ shares), 60 days of 5-minute bars (Yahoo's limit), today's list.
  base        the live rule: at 10:17, 11:17, 12:17, 13:17 and 14:17 New York, names whose 5-minute close
              broke above the 9:30-9:45 range high and are still above it, ranked by traded value so far;
              2 a run, 5 a day, $50 risk a day; stop at the range midpoint, target 2R, $10 risk, $1,000 cap,
              the paper.py cost filter; enter at the next 5-minute open, out by 15:55.
  spytrend    base, only on days when SPY closed above its 200-day average the day before.
  first       base, only the 10:17 decision.
  fresh       base, only breakouts whose first close above the range came in the last hour.
  Placebo: at the same decision times, random liquid names above their range midpoint (no breakout
  needed), same stops, targets and caps, 200 draws.
Reported: trades, net $, $ a trade, win rate, daily t (each day one observation), placebo percentile.
60 days of stocks is ~40 sessions: far too short to prove anything, enough to catch a clear loser.
Research, not financial advice.
"""

import argparse
import datetime
import gzip
import json
import math
import os
import random
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "trader-scanner"))
import bot  # noqa: E402
import bot_data  # noqa: E402
import lab  # noqa: E402
import paper  # noqa: E402
import fxcrypto  # noqa: E402

group, cost_bps, swap_bps = bot.group, bot.cost_bps, bot.swap_bps       # the live bot's own tables


def t_daily(pnl_by_day):
    d = list(pnl_by_day.values())
    if len(d) < 3:
        return 0.0
    m = sum(d) / len(d)
    sd = math.sqrt(sum((x - m) ** 2 for x in d) / (len(d) - 1))
    return m / sd * math.sqrt(len(d)) if sd else 0.0


def stats(trades, key="pnl"):
    by = {}
    for t in trades:
        by[t["day"]] = by.get(t["day"], 0.0) + t[key]
    p = [t[key] for t in trades]
    return {"trades": len(p), "net_usd": round(sum(p), 2), "per_trade": round(sum(p) / len(p), 3) if p else 0,
            "win_rate": round(sum(1 for x in p if x > 0) / len(p), 3) if p else None,
            "days": len(by), "t_daily": round(t_daily(by), 2)}


# ---------------------------------------------------------------- crypto / forex

def load_fx():
    out = {}
    for s in fxcrypto.CRYPTO + fxcrypto.FOREX:
        p = os.path.join(bot_data.FX1H, s + ".json.gz")
        if os.path.exists(p):
            with gzip.open(p, "rt") as fh:
                out[s] = np.array(json.load(fh), float)
    return out


def signals(a):
    """a: [[ts,o,h,l,c]] -> (long_new, short_new, chg1h) arrays, True at bar i when a trend setup is NEW."""
    c = a[:, 4]
    n = len(c)
    lo = np.zeros(n, bool)
    sh = np.zeros(n, bool)
    brk = np.zeros(n, bool)
    rec = np.zeros(n, bool)
    dn = np.zeros(n, bool)
    cs = np.concatenate(([0.0], np.cumsum(c)))
    for i in range(21, n):
        w = c[i - 20:i]
        brk[i] = c[i] > w.max()
        dn[i] = c[i] < w.min()
        ma = (cs[i + 1] - cs[i - 19]) / 20.0
        ma_prev = (cs[i] - cs[i - 20]) / 20.0
        rec[i] = c[i - 1] < ma_prev and c[i] > ma
    for i in range(22, n):
        L = brk[i] or rec[i]
        S = dn[i]
        if L and S:
            continue
        if L and ((brk[i] and not brk[i - 1]) or (rec[i] and not rec[i - 1])):
            lo[i] = True
        if S and not dn[i - 1]:
            sh[i] = True
    chg = np.zeros(n)
    chg[1:] = c[1:] / c[:-1] - 1
    return lo, sh, chg


def atr_at(a, i, n=14):
    h, l, c = a[i - n + 1:i + 1, 2], a[i - n + 1:i + 1, 3], a[i - n:i, 4]
    return float(np.maximum.reduce([h - l, abs(h - c), abs(l - c)]).mean())


def run_fx(data, variant, cost_mult=1.0, rng=None):
    sig = {s: signals(a) for s, a in data.items()}
    idx = {s: {int(t): i for i, t in enumerate(a[:, 0])} for s, a in data.items()}
    btc = data.get("BTC-USD")
    btc_ma = {}
    if btc is not None:
        cs = np.concatenate(([0.0], np.cumsum(btc[:, 4])))
        for i in range(1200, len(btc)):
            btc_ma[int(btc[i, 0])] = 1 if btc[i, 4] > (cs[i + 1] - cs[i - 1199]) / 1200.0 else -1
    hours = sorted({int(t) for a in data.values() for t in a[:, 0]})
    open_ = []          # (exit_ts, sym)
    trades = []
    for T in hours:
        open_ = [x for x in open_ if x[0] > T]
        dt = datetime.datetime.fromtimestamp(T + 3600, datetime.timezone.utc)    # decision at the bar's close
        if variant == "noweekend" and (dt.weekday() >= 5 or dt.hour >= 21):
            continue
        cands = []
        for s, a in data.items():
            i = idx[s].get(T)
            if i is None or i < 40 or i + 1 >= len(a):
                continue
            lo, sh, chg = sig[s]
            side = "buy" if lo[i] else "sell" if sh[i] else None
            if not side:
                continue
            cands.append((-abs(chg[i]), s, side, i))
        room = min(2, 6 - len(open_))
        new = 0
        for _, s, side, i in sorted(cands):
            if new >= room:
                break
            if any(o[1] == s for o in open_):
                continue
            if variant != "base":
                g = group(s)
                cap = bot.GROUP_CAP[g]
                if sum(1 for o in open_ if group(o[1]) == g) >= cap:
                    continue
            if variant == "btctrend" and group(s) == "crypto":
                tr = btc_ma.get(T)
                if tr is None or (tr == 1) != (side == "buy"):
                    continue
            if rng is not None:
                side = rng.choice(("buy", "sell"))
            a = data[s]
            at = atr_at(a, i)
            p = bot.fx_plan(s, side, float(a[i, 4]), at)
            if not p:
                continue
            bars = [tuple(r) for r in a[i + 1:i + 1 + 30]]
            got = bot.fill_hourly(bars, a[i + 1, 0], side, p["stop"], p["target"], 24, 1e18)
            if not got:
                continue
            e, x, how, t0, _ = got
            held = 1                      # bars held: the exit bar's position
            for j, b in enumerate(bars):
                if (side == "buy" and (b[3] <= p["stop"] or b[2] >= p["target"])) or \
                   (side == "sell" and (b[2] >= p["stop"] or b[3] <= p["target"])) or j == 23:
                    held = j + 1
                    break
            exit_ts = int(t0 + 3600 * held)
            nights = sum(1 for h in range(held) if datetime.datetime.fromtimestamp(t0 + 3600 * h, datetime.timezone.utc).hour == 0 and h > 0)
            c_bps = cost_mult * (cost_bps(s) + swap_bps(s) * nights)
            pnl = bot.pnl_usd(side, e, x, p["notional_usd"], c_bps)
            trades.append({"day": dt.date().isoformat(), "sym": s, "side": side, "how": how, "pnl": pnl,
                           "gross": bot.pnl_usd(side, e, x, p["notional_usd"], 0.0), "group": group(s)})
            open_.append((exit_ts, s))
            new += 1
    return trades


def cmd_fxcrypto(a):
    data = load_fx()
    out = {"from": min(datetime.datetime.fromtimestamp(v[0, 0], datetime.timezone.utc).date().isoformat()
                       for v in data.values()), "variants": {}}
    base = None
    for v in ("base", "groupcap", "btctrend", "noweekend"):
        tr = run_fx(data, v)
        st = stats(tr)
        st["stress_2x"] = stats(run_fx(data, v, cost_mult=2.0))["net_usd"]
        st["gross_usd"] = round(sum(t["gross"] for t in tr), 2)
        st["by_group"] = {g: stats([t for t in tr if t["group"] == g]) for g in ("crypto", "forex", "metal")}
        out["variants"][v] = st
        if v == "base":
            base = st
        print("  %-10s %5d trades  net $%+9.2f  ($%+.2f a trade, gross $%+.2f)  win %.0f%%  daily t %+.2f  at 2x cost $%+.2f" % (
            v, st["trades"], st["net_usd"], st["per_trade"], st["gross_usd"], 100 * (st["win_rate"] or 0),
            st["t_daily"], st["stress_2x"]), flush=True)
        for g, s in st["by_group"].items():
            print("      %-7s %5d trades  net $%+9.2f  daily t %+.2f" % (g, s["trades"], s["net_usd"], s["t_daily"]))
    rng = random.Random(11)
    nets = []
    for k in range(a.placebo):
        nets.append(sum(t["pnl"] for t in run_fx(data, "base", rng=rng)))
    pct = sum(1 for x in nets if x < base["net_usd"]) / len(nets) if nets else None
    out["placebo"] = {"draws": len(nets), "median_net": float(np.median(nets)) if nets else None,
                      "base_percentile": pct}
    if nets:
        print("  placebo (random direction, %d draws): median net $%+.2f; the live rule beats %.0f%% of them" % (
            len(nets), float(np.median(nets)), 100 * pct))
    return out


# ---------------------------------------------------------------- stocks

DECISIONS = ["10:17", "11:17", "12:17", "13:17", "14:17"]


def load_stocks():
    with open(os.path.join(bot_data.WM5, "_liquid.json")) as fh:
        syms = json.load(fh)
    out = {}
    for s in syms:
        p = os.path.join(bot_data.WM5, s + ".json.gz")
        if not os.path.exists(p):
            continue
        with gzip.open(p, "rt") as fh:
            bars = json.load(fh)
        days = {d: b for d, b in lab.sessions_of({int(k): v for k, v in bars.items()}) if len(b) > paper.EXIT_SLOT}
        if not days:
            continue
        vol = sum(x["v"] or 0 for b in days.values() for x in b) / len(days)
        last = list(days.values())[-1][-1]["c"]
        if vol >= bot_data.MIN_VOLUME and last >= bot_data.MIN_PRICE:       # the live scanner's floor
            out[s] = days
    return out


def spy_trend():
    import daily
    D = daily.load("SPY")
    c = D["c"]
    out = {}
    for i in range(200, len(c)):
        nxt = D["d"][i + 1] if i + 1 < len(c) else "9999"
        out[nxt] = c[i] > sum(c[i - 199:i + 1]) / 200.0       # yesterday's close vs its 200-day average
    return out, D["d"]


def day_info(bars):
    oh = max(b["h"] for b in bars[:3])
    ol = min(b["l"] for b in bars[:3])
    first = next((k for k in range(3, len(bars)) if bars[k]["c"] > oh), None)
    cv = np.cumsum([b["c"] * b["v"] for b in bars])
    return oh, ol, first, cv


def run_stocks(data, variant, trend=None, rng=None, cost_cache=None):
    days = sorted({d for v in data.values() for d in v})
    trades = []
    info = {}
    for s, v in data.items():
        for d, b in v.items():
            info[(s, d)] = day_info(b)
    for d in days:
        if variant == "spytrend" and not (trend or {}).get(d, False):
            continue
        taken, risk = set(), 0.0
        for hhmm in DECISIONS:
            if variant == "first" and hhmm != "10:17":
                break
            done = (int(hhmm[:2]) * 60 + int(hhmm[3:]) - lab.OPEN_MIN) // 5        # bars complete by then
            slot = bot.next_slot(hhmm)
            room = max(0, min(2, 5 - len(taken), int((50.0 - risk) // 10.0)))
            if room == 0:
                break
            cands = []
            for s, v in data.items():
                if s in taken or d not in v:
                    continue
                oh, ol, first, cv = info[(s, d)]
                px = v[d][done - 1]["c"]
                if rng is None:
                    if first is None or first >= done or not px > oh:
                        continue
                    if variant == "fresh" and first < done - 12:
                        continue
                    cands.append((-cv[done - 1], s, px, oh, ol))
                else:
                    if px > (oh + ol) / 2.0:
                        cands.append((rng.random(), s, px, oh, ol))
            new = 0
            for _, s, px, oh, ol in sorted(cands):
                if new >= room:
                    break
                bars = data[s][d]
                cfg = dict(paper.SCANNER_CFG, target_r=2.0)
                p = paper.scanner_plan({"symbol": s, "price": px, "or_high": oh, "or_low": ol}, bars[:done], set(), cfg)
                if not p:
                    continue
                e, x, how = paper.fill_long(bars, slot, p["stop"], p["target"])
                notional = p["shares"] * e
                pnl = p["shares"] * (x - e) - notional * p["cost_bps"] / 1e4
                trades.append({"day": d, "sym": s, "pnl": pnl, "how": how, "at": hhmm,
                               "gross": p["shares"] * (x - e)})
                taken.add(s)
                risk += p["max_loss_usd"]
                new += 1
    return trades


def cmd_stocks(a):
    data = load_stocks()
    trend, _ = spy_trend()
    days = sorted({d for v in data.values() for d in v})
    out = {"names": len(data), "from": days[0], "to": days[-1], "sessions": len(days), "variants": {}}
    print("Stocks: %d liquid names, %d sessions %s to %s." % (len(data), len(days), days[0], days[-1]), flush=True)
    base = None
    for v in ("base", "spytrend", "first", "fresh"):
        tr = run_stocks(data, v, trend)
        st = stats(tr)
        st["gross_usd"] = round(sum(t["gross"] for t in tr), 2)
        st["stops"] = sum(1 for t in tr if t["how"] == "stop")
        st["targets"] = sum(1 for t in tr if t["how"] == "target")
        out["variants"][v] = st
        if v == "base":
            base = st
        print("  %-9s %4d trades on %2d days  net $%+8.2f  ($%+.2f a trade, gross $%+.2f)  win %.0f%%  "
              "daily t %+.2f  (stops %d, targets %d)" % (
                  v, st["trades"], st["days"], st["net_usd"], st["per_trade"], st["gross_usd"],
                  100 * (st["win_rate"] or 0), st["t_daily"], st["stops"], st["targets"]), flush=True)
    rng = random.Random(5)
    nets = [sum(t["pnl"] for t in run_stocks(data, "base", trend, rng=rng)) for _ in range(a.placebo)]
    pct = sum(1 for x in nets if x < base["net_usd"]) / len(nets) if nets else None
    out["placebo"] = {"draws": len(nets), "median_net": float(np.median(nets)) if nets else None, "base_percentile": pct}
    if nets:
        print("  placebo (random names above their range midpoint, %d draws): median net $%+.2f; the live rule "
              "beats %.0f%% of them" % (len(nets), float(np.median(nets)), 100 * pct))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="backtest the bot's rules and challengers")
    ap.add_argument("what", choices=["fxcrypto", "stocks"])
    ap.add_argument("--placebo", type=int, default=None)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    if a.placebo is None:
        a.placebo = 500 if a.what == "fxcrypto" else 200
    out = cmd_fxcrypto(a) if a.what == "fxcrypto" else cmd_stocks(a)
    if a.write:
        with open(os.path.join(HERE, "results", "bot-backtest-%s.json" % a.what), "w") as fh:
            json.dump(out, fh, indent=1)
    print("History, not a forecast. Research, not financial advice.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
