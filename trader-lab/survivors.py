#!/usr/bin/env python3
"""trader-lab survivors: a daily-decision strategy built only from the rules that held up in the lab.

    python3 daily.py fetch --symbols SPY,QQQ,IWM,DIA,MDY,RSP,EFA,EEM,EWJ,VWO,SMH,XLB,XLE,XLF,XLI,XLK,XLP,XLU,XLV,XLY,VNQ,^IRX
    python3 fomc.py fetch
    python3 survivors.py backtest [--write]     # 2000-2026, with placebo
    python3 survivors.py today                  # after the close: settle, mark, decide tomorrow's open orders (paper)
    python3 survivors.py report

Why these rules. Across about 50 million tested rules, every pure same-day trade lost after costs,
and so did both breakout bots (bot_backtest.py, 2026-11-24). What survived the lab's gates were
short dips bought in uptrending index funds, held a few days, and the overnight drift into scheduled
Fed meetings:
  - Connors RSI(2): Wilder RSI(2) < 10 with the close above its 200-day average; out when RSI(2) > 70.
    Lab: post-2014 t about 3.0 with next-open fills (RESEARCH.md, 2026-11-22).
  - Connors & Alvarez Double 7s: the lowest close of 7 days, above the 200-day; out at the highest
    close of 7. Lab: post-2014 t 3.1.
  - FOMC overnight (Lucca & Moench 2015, as the lab found it): SPY from the close before a scheduled
    FOMC announcement day to that day's open. Lab: 2012 on +13.7 bp a night, t 3.5 (fomc.py, H2 PASS).

PRE-REGISTERED 2026-11-24, before this file was run. Fixed, not tuned on the result:
  Universe  21 liquid index and sector ETFs: SPY QQQ IWM DIA MDY RSP EFA EEM EWJ VWO SMH XLB XLE XLF
            XLI XLK XLP XLU XLV XLY VNQ (ETFs only: no survivorship from dead stocks).
  Entries   at the close of day t a name qualifies if close > 200-day average (including day t) AND
            (RSI(2) < 10 OR close is the lowest close of the last 7). Buy at the OPEN of day t+1.
  Exits     at the close of day t, if RSI(2) > 70 OR close is the highest close of the last 7, OR the
            position has been held 10 trading days: sell at the OPEN of day t+1.
  Sizing    at most 5 dip positions, 20% of equity each (ranked by lowest RSI(2)); cash earns T-bills.
            The FOMC sleeve is separate: 20% of equity in SPY from the close before each scheduled FOMC
            announcement day to that day's open (a market-on-close buy).
  Costs     3 bp a round trip on each position (2x and 3x stress reported). Dividends included.
  Judged    2015-2026 (after the rules were published, 2008-2009; after the lab's in-sample to 2014).
  Pass      post-2015 daily excess-return t >= 2, beats 95% of placebos, and still positive at 3x cost.
  Placebo   the same number of dip trades each year, the same holding lengths, random ETFs and random
            entry days (200 draws), FOMC sleeve unchanged.
Honest caveat: the dip rules were picked BECAUSE they passed the lab's earlier sweep, partly on these
same funds, so this backtest is not independent evidence. Connors R3 (a sibling) failed on 110 fresh
ETFs. Only the forward paper record from 2026-11-25 counts as new evidence.
Paper only. Research, not financial advice.
"""

import argparse
import datetime
import json
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import daily  # noqa: E402

UNIVERSE = ["SPY", "QQQ", "IWM", "DIA", "MDY", "RSP", "EFA", "EEM", "EWJ", "VWO", "SMH", "XLB", "XLE",
            "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY", "VNQ"]
SLOTS, SLOT_W, FOMC_W, MAX_HOLD, COST_BPS = 5, 0.20, 0.20, 10, 3.0
START, JUDGED = "2000-01-03", "2015-01-01"
FOMC_DIR = os.path.join(HERE, "data", "fomc")
LEDGER = os.path.join(HERE, "paper", "survivors", "ledger.json")


# ---------------------------------------------------------------- data

def today_ny():
    import lab
    return lab.to_eastern(datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))


def load_all(drop_partial=True):
    """{sym: {d, o, c, f}} aligned to SPY's dates; f = dividend factor a/c. Today's bar is dropped
    before 16:15 New York (it is still forming)."""
    ny = today_ny()
    cut = ny.date().isoformat() if drop_partial and (ny.hour, ny.minute) < (16, 15) else "9999"
    out = {}
    for s in UNIVERSE + ["^IRX"]:
        D = daily.load(s)
        if not D:
            raise SystemExit("no daily data for %s: run daily.py fetch" % s)
        keep = [i for i, d in enumerate(D["d"]) if d < cut and D["c"][i]]
        out[s] = {"d": [D["d"][i] for i in keep], "o": [D["o"][i] for i in keep], "c": [D["c"][i] for i in keep],
                  "a": [(D.get("a") or D["c"])[i] for i in keep]}
    return out


def fomc_days():
    ev = json.load(open(os.path.join(FOMC_DIR, "events.json")))
    up = []
    p = os.path.join(FOMC_DIR, "upcoming.json")
    if os.path.exists(p):
        up = json.load(open(p))
    return sorted(set(ev) | set(up))


# ---------------------------------------------------------------- signals (pure)

def wilder(c, n=2):
    return daily.wilder_series(c, n)


def features(c):
    """Per index i (using closes up to and including i): rsi2, above200, low7, high7."""
    r = wilder(c, 2)
    n = len(c)
    above, low7, high7 = [False] * n, [False] * n, [False] * n
    s = 0.0
    for i in range(n):
        s += c[i]
        if i >= 200:
            s -= c[i - 200]
        if i >= 199:
            above[i] = c[i] > s / 200.0
        if i >= 6:
            w = c[i - 6:i + 1]
            low7[i] = c[i] <= min(w)
            high7[i] = c[i] >= max(w)
    return r, above, low7, high7


def entry_signal(rsi2, above, low7):
    return bool(above) and (rsi2 is not None and rsi2 < 10 or bool(low7))


def exit_signal(rsi2, high7, held):
    return (rsi2 is not None and rsi2 > 70) or bool(high7) or held >= MAX_HOLD


# ---------------------------------------------------------------- backtest

def simulate(data, fomc, cost_bps=COST_BPS, placebo=None, rng=None):
    """Daily equity curve. placebo = {year: [hold lengths]} -> random dip trades instead of the rule."""
    spy = data["SPY"]
    dates = [d for d in spy["d"] if d >= START]
    idx = {s: {d: i for i, d in enumerate(v["d"])} for s, v in data.items()}
    feats = {s: features(data[s]["c"]) for s in UNIVERSE}
    irx = data["^IRX"]
    rf_map = dict(zip(irx["d"], irx["c"]))
    fset = set(fomc)
    eq, last_rf = 1.0, 0.0
    pos = {}           # sym -> {"held": n, "w": weight of equity at entry, "px": entry open adj}
    pending_buy, pending_sell = [], []
    curve, trades = [], []
    plan = None
    if placebo is not None:
        plan = {}
        for y, holds in placebo.items():
            ds = [d for d in dates if d[:4] == y]
            for h in holds:
                plan.setdefault(rng.choice(ds), []).append((rng.choice(UNIVERSE), h))
    for k, d in enumerate(dates):
        last_rf = rf_map.get(d, last_rf)
        day_ret = 0.0
        # 1) sells at today's open, then buys at today's open
        for s in pending_sell:
            p = pos.pop(s, None)
            if p is None:
                continue
            i = idx[s].get(d)
            if i is None:
                pos[s] = p
                continue
            o_adj = data[s]["o"][i] * data[s]["a"][i] / data[s]["c"][i]
            prev = p["mark"]
            r = o_adj / prev - 1.0
            day_ret += p["w_now"] * r - p["w_now"] * cost_bps / 2e4
            trades.append({"sym": s, "in": p["in"], "out": d, "held": p["held"],
                           "ret": p["cum"] * (1 + r) - 1 - cost_bps / 1e4})
        for s in pending_buy:
            if s in pos or len(pos) >= SLOTS:
                continue
            i = idx[s].get(d)
            if i is None or not data[s]["o"][i]:
                continue
            o_adj = data[s]["o"][i] * data[s]["a"][i] / data[s]["c"][i]
            pos[s] = {"held": 0, "w_now": SLOT_W, "mark": o_adj, "in": d, "cum": 1.0}
            day_ret -= SLOT_W * cost_bps / 2e4
        pending_buy, pending_sell = [], []
        # 2) FOMC sleeve: held overnight into an FOMC day -> earns prev close -> today's open
        if d in fset and k > 0:
            i = idx["SPY"][d]
            o_adj = spy["o"][i] * spy["a"][i] / spy["c"][i]
            c_prev = spy["a"][i - 1]
            day_ret += FOMC_W * (o_adj / c_prev - 1.0) - FOMC_W * cost_bps / 1e4
        # 3) open positions earn from their mark to today's close
        for s, p in pos.items():
            i = idx[s].get(d)
            if i is None:
                continue
            c_adj = data[s]["a"][i]
            r = c_adj / p["mark"] - 1.0
            day_ret += p["w_now"] * r
            p["cum"] *= 1 + r
            p["mark"] = c_adj
            p["held"] += 1
        invested = sum(p["w_now"] for p in pos.values())
        day_ret += max(0.0, 1.0 - invested) * last_rf / 100.0 / 252.0
        eq *= 1 + day_ret
        # each open position is held at 20% of current equity (a small daily rebalance; an approximation)
        curve.append((d, eq, day_ret, last_rf / 100.0 / 252.0))
        # 4) decisions at today's close for tomorrow's open
        for s, p in pos.items():
            i = idx[s].get(d)
            if i is None:
                continue
            r2, ab, lo7, hi7 = (f[i] for f in feats[s])
            if plan is None:
                if exit_signal(r2, hi7, p["held"]):
                    pending_sell.append(s)
            elif p["held"] >= p.get("target_hold", MAX_HOLD):
                pending_sell.append(s)
        if plan is None:
            cands = []
            for s in UNIVERSE:
                if s in pos:
                    continue
                i = idx[s].get(d)
                if i is None or i < 200:
                    continue
                r2, ab, lo7, hi7 = (f[i] for f in feats[s])
                if entry_signal(r2, ab, lo7):
                    cands.append((r2 if r2 is not None else 50, s))
            free = SLOTS - len(pos) + len(pending_sell)
            pending_buy = [s for _, s in sorted(cands)[:max(0, free)]]
        else:
            for s, h in plan.get(d, []):
                if s not in pos and s not in pending_buy:
                    pending_buy.append(s)
                    placebo_hold[s] = h
        if plan is not None:
            for s in list(pos):
                if s in placebo_hold:
                    pos[s]["target_hold"] = placebo_hold.pop(s)
    return curve, trades


placebo_hold = {}


def summarize(curve, frm=None, to=None):
    rows = [x for x in curve if (frm is None or x[0] >= frm) and (to is None or x[0] < to)]
    if len(rows) < 30:
        return None
    r = [x[2] for x in rows]
    ex = [x[2] - x[3] for x in rows]
    eq = 1.0
    peak, mdd = 1.0, 0.0
    for x in r:
        eq *= 1 + x
        peak = max(peak, eq)
        mdd = max(mdd, 1 - eq / peak)
    n = len(r)
    m = sum(ex) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in ex) / (n - 1))
    return {"from": rows[0][0], "to": rows[-1][0], "cagr": eq ** (252.0 / n) - 1,
            "sharpe": m / sd * math.sqrt(252) if sd else 0.0, "t": m / sd * math.sqrt(n) if sd else 0.0,
            "max_dd": mdd}


def buy_hold(data, frm, to=None):
    s = data["SPY"]
    rf = dict(zip(data["^IRX"]["d"], data["^IRX"]["c"]))
    curve, last = [], 0.0
    for i in range(1, len(s["d"])):
        d = s["d"][i]
        last = rf.get(d, last)
        curve.append((d, 0, s["a"][i] / s["a"][i - 1] - 1, last / 100.0 / 252.0))
    return summarize(curve, frm, to)


def cmd_backtest(a):
    global placebo_hold
    data = load_all()
    fomc = fomc_days()
    curve, trades = simulate(data, fomc)
    out = {"rule": {}, "stress": {}, "spy": {}}
    for name, frm, to in (("2000-2014", START, JUDGED), ("2015-2026", JUDGED, None), ("all", START, None)):
        out["rule"][name] = summarize(curve, frm, to)
        out["spy"][name] = buy_hold(data, frm, to)
    for m in (2, 3):
        c2, _ = simulate(data, fomc, cost_bps=COST_BPS * m)
        out["stress"]["%dx" % m] = summarize(c2, JUDGED)
    post = [t for t in trades if t["in"] >= JUDGED]
    out["trades_post"] = len(post)
    out["win_rate_post"] = sum(1 for t in post if t["ret"] > 0) / len(post) if post else None
    out["avg_trade_post_bp"] = 1e4 * sum(t["ret"] for t in post) / len(post) if post else None
    inv = sum(t["held"] for t in post) / max(1, len([x for x in curve if x[0] >= JUDGED])) / SLOTS
    out["avg_slots_used_post"] = inv * SLOTS
    # placebo
    holds = {}
    for t in trades:
        holds.setdefault(t["in"][:4], []).append(max(1, t["held"]))
    rng = random.Random(3)
    base_t = out["rule"]["2015-2026"]["t"]
    pts = []
    for k in range(a.placebo):
        placebo_hold = {}
        c3, _ = simulate(data, fomc, placebo=holds, rng=rng)
        s3 = summarize(c3, JUDGED)
        pts.append(s3["t"])
    pct = sum(1 for x in pts if x < base_t) / len(pts) if pts else None
    out["placebo"] = {"draws": len(pts), "median_t": sorted(pts)[len(pts) // 2] if pts else None, "beats": pct}
    passed = base_t >= 2 and (pct or 0) >= 0.95 and out["stress"]["3x"]["cagr"] > 0
    out["verdict"] = "PASS (backtest only; forward paper record decides)" if passed else "FAIL"
    if a.write:
        with open(os.path.join(HERE, "results", "survivors.json"), "w") as fh:
            json.dump(out, fh, indent=1)
    print("Survivors (RSI(2) + Double 7s on 21 ETFs, 5 slots of 20%, plus the FOMC night), 3 bp a round trip:")
    print("  period      per year  Sharpe  max drop   t   |  SPY per year  Sharpe  max drop")
    for name in ("2000-2014", "2015-2026", "all"):
        r, s = out["rule"][name], out["spy"][name]
        print("  %-10s  %6.1f%%   %5.2f   %5.0f%%  %5.2f |  %6.1f%%       %5.2f   %5.0f%%" % (
            name, 100 * r["cagr"], r["sharpe"], 100 * r["max_dd"], r["t"], 100 * s["cagr"], s["sharpe"], 100 * s["max_dd"]))
    print("  after 2015: %d trades, win rate %.0f%%, %.1f bp a trade, %.1f of 5 slots used on average" % (
        out["trades_post"], 100 * (out["win_rate_post"] or 0), out["avg_trade_post_bp"] or 0, out["avg_slots_used_post"]))
    print("  cost stress after 2015: 2x %.1f%% a year, 3x %.1f%% a year" % (
        100 * out["stress"]["2x"]["cagr"], 100 * out["stress"]["3x"]["cagr"]))
    if pts:
        print("  placebo (random ETFs and days, same holds, %d draws): median t %.2f; the rule beats %.0f%%" % (
            len(pts), out["placebo"]["median_t"], 100 * pct))
    print("Verdict: %s. History, not a forecast; research, not financial advice." % out["verdict"])
    return 0


# ---------------------------------------------------------------- paper trading, forward

def load_ledger():
    if os.path.exists(LEDGER):
        return json.load(open(LEDGER))
    return {"start": None, "equity": 10000.0, "cash": 10000.0, "positions": {}, "orders": [], "history": [],
            "trades": [], "fomc_pending": None}


def save_ledger(L):
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "w") as fh:
        json.dump(L, fh, indent=1)


def cmd_today(a):
    """Run after the close (16:15+ New York). Fills yesterday's orders at today's open, marks to today's
    close, then writes the orders for tomorrow's open. $10,000 paper account."""
    ny = today_ny()
    if (ny.hour, ny.minute) < (16, 15) and not a.force:
        print("Run after 16:15 New York (today's close must be final).")
        return 1
    data = load_all(drop_partial=False)
    d = data["SPY"]["d"][-1]
    L = load_ledger()
    if L["history"] and L["history"][-1]["date"] >= d:
        print("Already done for %s." % d)
        return 0
    L["start"] = L["start"] or d
    idx = {s: {x: i for i, x in enumerate(v["d"])} for s, v in data.items()}
    cost = COST_BPS / 2e4
    msgs = []
    # FOMC night bought at yesterday's close -> sold at today's open
    fp = L.get("fomc_pending")
    if fp and fp["day"] == d:
        i = idx["SPY"][d]
        px = data["SPY"]["o"][i]
        val = fp["shares"] * px
        L["cash"] += val * (1 - cost)
        pnl = val * (1 - cost) - fp["cost_basis"]
        L["trades"].append({"sym": "SPY (FOMC night)", "in": fp["bought"], "out": d, "pnl": round(pnl, 2)})
        msgs.append("SOLD SPY (FOMC night) at the open %.2f: $%+.2f" % (px, pnl))
        L["fomc_pending"] = None
    # fill orders at today's open: sells first
    for o in [o for o in L["orders"] if o["side"] == "sell"]:
        p = L["positions"].pop(o["sym"], None)
        i = idx[o["sym"]].get(d)
        if not p or i is None:
            continue
        px = data[o["sym"]]["o"][i]
        val = p["shares"] * px
        L["cash"] += val * (1 - cost)
        pnl = val * (1 - cost) - p["cost_basis"]
        L["trades"].append({"sym": o["sym"], "in": p["in"], "out": d, "pnl": round(pnl, 2)})
        msgs.append("SOLD %s at the open %.2f: $%+.2f (%s)" % (o["sym"], px, pnl, o["why"]))
    for o in [o for o in L["orders"] if o["side"] == "buy"]:
        i = idx[o["sym"]].get(d)
        if i is None or o["sym"] in L["positions"] or len(L["positions"]) >= SLOTS:
            continue
        px = data[o["sym"]]["o"][i]
        budget = min(L["cash"], SLOT_W * L["equity"])
        sh = math.floor(budget / (px * (1 + cost)) * 1000) / 1000.0        # fractional shares to 0.001
        if sh <= 0:
            continue
        cb = sh * px * (1 + cost)
        L["cash"] -= cb
        L["positions"][o["sym"]] = {"shares": sh, "cost_basis": cb, "in": d, "held": 0}
        msgs.append("BOUGHT %s at the open %.2f: %.3f shares ($%.0f)" % (o["sym"], px, sh, cb))
    L["orders"] = []
    # mark to the close
    value = L["cash"]
    for s, p in L["positions"].items():
        i = idx[s].get(d)
        p["held"] += 1
        value += p["shares"] * data[s]["c"][i]
    L["equity"] = round(value, 2)
    # decide tomorrow
    feats = {s: features(data[s]["c"]) for s in UNIVERSE}
    sells = []
    for s, p in L["positions"].items():
        i = idx[s][d]
        r2, ab, lo7, hi7 = (f[i] for f in feats[s])
        if exit_signal(r2, hi7, p["held"]):
            why = "RSI(2) %.0f > 70" % r2 if r2 and r2 > 70 else "highest close of 7" if hi7 else "10 days held"
            sells.append({"side": "sell", "sym": s, "why": why})
    cands = []
    for s in UNIVERSE:
        if s in L["positions"]:
            continue
        i = idx[s].get(d)
        if i is None or i < 200:
            continue
        r2, ab, lo7, hi7 = (f[i] for f in feats[s])
        if entry_signal(r2, ab, lo7):
            cands.append((r2 if r2 is not None else 50, s, "RSI(2) %.1f" % r2 if r2 is not None and r2 < 10 else "lowest close of 7"))
    free = SLOTS - len(L["positions"]) + len(sells)
    buys = [{"side": "buy", "sym": s, "why": w} for _, s, w in sorted(cands)[:max(0, free)]]
    L["orders"] = sells + buys
    # FOMC: buy SPY at today's close if tomorrow is a scheduled announcement day
    nxt = next((x for x in fomc_days() if x > d), None)
    nxt_trading = (datetime.date.fromisoformat(d) + datetime.timedelta(days=3 if datetime.date.fromisoformat(d).weekday() == 4 else 1)).isoformat()
    if nxt == nxt_trading and not L.get("fomc_pending"):
        px = data["SPY"]["c"][idx["SPY"][d]]
        sh = math.floor(FOMC_W * L["equity"] / (px * (1 + cost)) * 1000) / 1000.0
        cb = sh * px * (1 + cost)
        L["cash"] -= cb
        L["fomc_pending"] = {"day": nxt, "shares": sh, "cost_basis": cb, "bought": d}
        msgs.append("BOUGHT SPY at today's close %.2f for the FOMC night (sell at the %s open)" % (px, nxt))
    L["history"].append({"date": d, "equity": L["equity"]})
    save_ledger(L)
    print("Survivors (PAPER, $10,000 start), %s close: equity $%.2f, %d positions, cash $%.2f." % (
        d, L["equity"], len(L["positions"]), L["cash"]))
    for m in msgs:
        print("  " + m)
    for o in L["orders"]:
        print("  ORDER for tomorrow's open: %s %s (%s)" % (o["side"].upper(), o["sym"], o["why"]))
    if not L["orders"] and not msgs:
        print("  No trade: no fund is in a short dip inside an uptrend.")
    return 0


def cmd_report(a):
    L = load_ledger()
    t = L["trades"]
    pnl = sum(x["pnl"] for x in t)
    print("Survivors (PAPER) since %s: equity $%.2f (%+.2f%%), %d closed trades, net $%+.2f, win rate %s; open: %s." % (
        L["start"], L["equity"], (L["equity"] / 10000.0 - 1) * 100, len(t), pnl,
        "%.0f%%" % (100.0 * sum(1 for x in t if x["pnl"] > 0) / len(t)) if t else "-",
        ", ".join(L["positions"]) or "none"))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="survivors: the lab's surviving rules as one daily strategy")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("backtest")
    p.add_argument("--placebo", type=int, default=200)
    p.add_argument("--write", action="store_true")
    p = sub.add_parser("today")
    p.add_argument("--force", action="store_true")
    sub.add_parser("report")
    a = ap.parse_args(argv)
    fn = {"backtest": cmd_backtest, "today": cmd_today, "report": cmd_report}.get(a.cmd)
    if not fn:
        ap.print_help()
        return 1
    return fn(a)


if __name__ == "__main__":
    sys.exit(main())
