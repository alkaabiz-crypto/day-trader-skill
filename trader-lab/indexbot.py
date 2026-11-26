#!/usr/bin/env python3
"""The indices bot: buy short dips in uptrending stock indices, hold a few days, on PAPER (Exness index CFDs).

    python3 indexbot.py fetch                  # Tiingo daily bars (not Yahoo) -> data/indexbot (gitignored)
    python3 indexbot.py backtest [--write]
    python3 indexbot.py today                  # after 16:15 New York: fill, mark, decide tomorrow (paper, $10,000)
    python3 indexbot.py report

Why this rule. Every same-day index rule the lab tested lost after costs. The one family that held up on
index funds is buying a short dip inside an uptrend and selling the bounce a few days later (Connors RSI(2),
Connors & Alvarez Double 7s; survivors.py). This bot trades that rule on the indices Exness offers as CFDs,
priced from the US-listed fund that tracks each one (Tiingo daily, dividend-adjusted).

PRE-REGISTERED 2026-11-24, before this file was run. Fixed; not tuned on the result:
  Indices   US500 (SPY), USTEC (QQQ), US30 (DIA), US2000 (IWM), DE30 (EWG), UK100 (EWU), JP225 (EWJ),
            STOXX50 (FEZ), HK50 (EWH), AUS200 (EWA)
  Entry     at the close: above its 200-day average AND (Wilder RSI(2) < 10 OR the lowest close of 7 days);
            buy at the next open.
  Exit      RSI(2) > 70, the highest close of 7 days, or 10 days held; sell at the next open.
  Sizing    at most 5 positions, 20% of equity each, lowest RSI(2) first; cash earns nothing (conservative).
  Costs     CFD: 3 bp spread a round trip + 2 bp overnight financing (swap) for every night held (about 5% a year).
  Judged    2015-2026. Pass: daily t >= 2, beats 95% of 200 placebos (random index, random day, same holds),
            and still positive at 3x costs. Compared with buying and holding US500 (SPY).
Fund proxies trade in New York hours, so for DE30 / UK100 / JP225 / STOXX50 / HK50 / AUS200 the bot's prices
are the US-hours prices of the fund, not the CFD's own session. Paper only; nothing reaches any account.
US-ONLY TEST, PRE-REGISTERED 2026-11-26 (the owner's choice), before it was run: `backtest --universe us` runs the
  identical rule, sizing (5 slots x 20%, so at most 4 positions), costs and pass bar on US500, USTEC, US30 and
  US2000 only, whose fund prices trade in the same hours as the CFDs. Placebos draw from the same 4 indices.
  Result in results/indexbot-us.json (3.1% a year, t 1.81: better than 10 indices, still FAIL).
  From 2026-11-26 the PAPER bot trades only these 4 (the owner's decision, `PAPER`); the rule is unchanged.
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
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import survivors  # noqa: E402

CFD = {"SPY": "US500", "QQQ": "USTEC", "DIA": "US30", "IWM": "US2000", "EWG": "DE30", "EWU": "UK100",
       "EWJ": "JP225", "FEZ": "STOXX50", "EWH": "HK50", "EWA": "AUS200"}
UNIVERSE = list(CFD)
US_ONLY = ["SPY", "QQQ", "DIA", "IWM"]   # backtest --universe us (pre-registered 2026-11-26)
PAPER = US_ONLY   # the paper bot trades US-only from 2026-11-26 (owner's decision; was all 10)
SLOTS, SLOT_W, MAX_HOLD = 5, 0.20, 10
SPREAD_BPS, SWAP_BPS = 3.0, 2.0
START, JUDGED = "2000-01-03", "2015-01-01"
STORE = os.path.join(HERE, "data", "indexbot")
LEDGER = os.path.join(HERE, "paper", "indexbot", "ledger.json")


# ---------------------------------------------------------------- data (Tiingo)

def fetch_one(sym, start="1998-01-01"):
    url = "https://api.tiingo.com/tiingo/daily/%s/prices?startDate=%s" % (sym.lower(), start)
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "trader-lab"})
    with urllib.request.urlopen(req, timeout=60) as r:
        rows = json.loads(r.read().decode())
    return {"d": [x["date"][:10] for x in rows], "o": [x["adjOpen"] for x in rows],
            "c": [x["adjClose"] for x in rows]}


def cmd_fetch(a):
    os.makedirs(STORE, exist_ok=True)
    for s in UNIVERSE:
        D = fetch_one(s)
        with gzip.open(os.path.join(STORE, s + ".json.gz"), "wt") as fh:
            json.dump(D, fh)
        print("  %-4s (%s) %d days %s to %s" % (s, CFD[s], len(D["d"]), D["d"][0], D["d"][-1]), flush=True)
        time.sleep(1.0)
    return 0


def load(drop_partial=True):
    ny = survivors.today_ny()
    cut = ny.date().isoformat() if drop_partial and (ny.hour, ny.minute) < (16, 15) else "9999"
    out = {}
    for s in UNIVERSE:
        with gzip.open(os.path.join(STORE, s + ".json.gz"), "rt") as fh:
            D = json.load(fh)
        keep = [i for i, d in enumerate(D["d"]) if d < cut and D["c"][i] and D["o"][i]]
        out[s] = {k: [D[k][i] for i in keep] for k in ("d", "o", "c")}
    return out


# ---------------------------------------------------------------- backtest

def simulate(data, cost_mult=1.0, placebo=None, rng=None):
    dates = sorted({d for v in data.values() for d in v["d"] if d >= START})
    idx = {s: {d: i for i, d in enumerate(v["d"])} for s, v in data.items()}
    feats = {s: survivors.features(data[s]["c"]) for s in data}
    spread, swap = SPREAD_BPS * cost_mult / 1e4, SWAP_BPS * cost_mult / 1e4
    pos, buys, sells, curve, trades = {}, [], [], [], []
    plan, want = {}, {}
    if placebo is not None:
        for y, holds in placebo.items():
            ds = [d for d in dates if d[:4] == y]
            for h in holds:
                plan.setdefault(rng.choice(ds), []).append((rng.choice(sorted(data)), h))
    for d in dates:
        r = 0.0
        for s in sells:
            p = pos.pop(s)
            i = idx[s].get(d)
            if i is None:
                pos[s] = p
                continue
            x = data[s]["o"][i] / p["mark"] - 1
            r += SLOT_W * (x - spread / 2)
            trades.append({"sym": s, "in": p["in"], "held": p["held"], "ret": p["cum"] * (1 + x) - 1})
        for s in buys:
            i = idx[s].get(d)
            if s in pos or len(pos) >= SLOTS or i is None:
                continue
            pos[s] = {"mark": data[s]["o"][i], "held": 0, "in": d, "cum": 1.0, "target": want.pop(s, MAX_HOLD)}
            r -= SLOT_W * spread / 2
        buys, sells = [], []
        for s, p in pos.items():
            i = idx[s].get(d)
            if i is None:
                continue
            x = data[s]["c"][i] / p["mark"] - 1
            r += SLOT_W * (x - swap)
            p["cum"] *= 1 + x
            p["mark"] = data[s]["c"][i]
            p["held"] += 1
        curve.append((d, 0.0, r, 0.0))
        for s, p in pos.items():
            i = idx[s].get(d)
            if i is None:
                continue
            r2, ab, lo7, hi7 = (f[i] for f in feats[s])
            if (placebo is None and survivors.exit_signal(r2, hi7, p["held"])) or \
                    (placebo is not None and p["held"] >= p["target"]):
                sells.append(s)
        free = SLOTS - len(pos) + len(sells)
        if placebo is None:
            cands = []
            for s in data:
                i = idx[s].get(d)
                if s in pos or i is None or i < 200:
                    continue
                r2, ab, lo7, hi7 = (f[i] for f in feats[s])
                if survivors.entry_signal(r2, ab, lo7):
                    cands.append((r2 if r2 is not None else 50, s))
            buys = [s for _, s in sorted(cands)[:max(0, free)]]
        else:
            for s, h in plan.get(d, []):
                if s not in pos and s not in buys and len(buys) < free:
                    buys.append(s)
                    want[s] = h
    return curve, trades


def buy_hold(data, frm, to=None):
    s = data["SPY"]
    c = [(s["d"][i], 0.0, s["c"][i] / s["c"][i - 1] - 1, 0.0) for i in range(1, len(s["d"]))]
    return survivors.summarize(c, frm, to)


def cmd_backtest(a):
    data = load()
    if a.universe == "us":
        data = {k: data[k] for k in US_ONLY}
    curve, trades = simulate(data)
    out = {"rule": {}, "us500": {}, "stress": {}}
    for name, frm, to in (("2000-2014", START, JUDGED), ("2015-2026", JUDGED, None)):
        out["rule"][name] = survivors.summarize(curve, frm, to)
        out["us500"][name] = buy_hold(data, frm, to)
    for m in (2, 3):
        out["stress"]["%dx" % m] = survivors.summarize(simulate(data, cost_mult=m)[0], JUDGED)
    post = [t for t in trades if t["in"] >= JUDGED]
    out["trades_post"] = len(post)
    out["win_rate_post"] = sum(1 for t in post if t["ret"] > 0) / max(1, len(post))
    out["avg_trade_post_bp"] = 1e4 * sum(t["ret"] for t in post) / max(1, len(post))
    holds = {}
    for t in trades:
        holds.setdefault(t["in"][:4], []).append(max(1, t["held"]))
    rng = random.Random(9)
    pts = [survivors.summarize(simulate(data, placebo=holds, rng=rng)[0], JUDGED)["t"] for _ in range(a.placebo)]
    base_t = out["rule"]["2015-2026"]["t"]
    out["placebo"] = {"draws": len(pts), "median_t": sorted(pts)[len(pts) // 2] if pts else None,
                      "beats": sum(1 for x in pts if x < base_t) / len(pts) if pts else None}
    ok = base_t >= 2 and (out["placebo"]["beats"] or 0) >= 0.95 and out["stress"]["3x"]["cagr"] > 0
    out["verdict"] = "PASS (backtest only)" if ok else "FAIL"
    if a.write:
        name = "indexbot-us.json" if a.universe == "us" else "indexbot.json"
        with open(os.path.join(HERE, "results", name), "w") as fh:
            json.dump(out, fh, indent=1)
    print("Indices bot (dip in an uptrend on %d index CFDs via fund proxies, 5 x 20%%, 3 bp + 2 bp a night):" % len(data))
    print("  period      per year  Sharpe  max drop   t   |  US500 hold per year  Sharpe  max drop")
    for n in ("2000-2014", "2015-2026"):
        r, s = out["rule"][n], out["us500"][n]
        print("  %-10s  %6.1f%%   %5.2f   %5.0f%%  %5.2f |  %6.1f%%              %5.2f   %5.0f%%" % (
            n, 100 * r["cagr"], r["sharpe"], 100 * r["max_dd"], r["t"], 100 * s["cagr"], s["sharpe"], 100 * s["max_dd"]))
    print("  after 2015: %d trades, win rate %.0f%%, %.1f bp a trade; at 2x cost %.1f%% a year, 3x %.1f%% a year" % (
        out["trades_post"], 100 * out["win_rate_post"], out["avg_trade_post_bp"],
        100 * out["stress"]["2x"]["cagr"], 100 * out["stress"]["3x"]["cagr"]))
    if pts:
        print("  placebo (%d draws): median t %.2f; the rule beats %.0f%%" % (len(pts), out["placebo"]["median_t"],
                                                                         100 * out["placebo"]["beats"]))
    print("Verdict: %s. History, not a forecast; research, not financial advice." % out["verdict"])
    return 0


# ---------------------------------------------------------------- paper, forward

def load_ledger():
    if os.path.exists(LEDGER):
        return json.load(open(LEDGER))
    return {"start": None, "equity": 10000.0, "cash": 10000.0, "positions": {}, "orders": [], "history": [], "trades": []}


def cmd_today(a):
    ny = survivors.today_ny()
    if (ny.hour, ny.minute) < (16, 15) and not a.force:
        print("Run after 16:15 New York (today's close must be final).")
        return 1
    if not a.no_fetch:
        cmd_fetch(a)
    data = load(drop_partial=False)
    d = max(v["d"][-1] for v in data.values())
    L = load_ledger()
    if L["history"] and L["history"][-1]["date"] >= d:
        print("Already done for %s." % d)
        return 0
    L["start"] = L["start"] or d
    idx = {s: {x: i for i, x in enumerate(v["d"])} for s, v in data.items()}
    half = SPREAD_BPS / 2e4
    msgs = []
    for o in [o for o in L["orders"] if o["side"] == "sell"]:
        p = L["positions"].get(o["sym"])
        i = idx[o["sym"]].get(d)
        if not p or i is None:
            continue
        L["positions"].pop(o["sym"])
        px = data[o["sym"]]["o"][i]
        val = p["units"] * px * (1 - half)
        L["cash"] += val
        pnl = val - p["cost"] - p.get("swap", 0.0)
        L["trades"].append({"sym": o["sym"], "cfd": CFD[o["sym"]], "in": p["in"], "out": d, "pnl": round(pnl, 2)})
        msgs.append("CLOSED %s (%s) at the open: $%+.2f (%s)" % (CFD[o["sym"]], o["sym"], pnl, o["why"]))
    for o in [o for o in L["orders"] if o["side"] == "buy"]:
        i = idx[o["sym"]].get(d)
        if i is None or o["sym"] in L["positions"] or len(L["positions"]) >= SLOTS:
            continue
        px = data[o["sym"]]["o"][i]
        notional = min(L["cash"], SLOT_W * L["equity"])
        units = notional / (px * (1 + half))
        L["cash"] -= notional
        L["positions"][o["sym"]] = {"units": units, "cost": notional, "in": d, "held": 0, "swap": 0.0}
        msgs.append("BOUGHT %s (%s) at the open %.2f: $%.0f" % (CFD[o["sym"]], o["sym"], px, notional))
    L["orders"] = []
    value = L["cash"]
    for s, p in L["positions"].items():
        i = idx[s].get(d)
        px = data[s]["c"][i]
        p["held"] += 1
        p["swap"] += p["units"] * px * SWAP_BPS / 1e4
        value += p["units"] * px - p["swap"]
    L["equity"] = round(value, 2)
    feats = {s: survivors.features(data[s]["c"]) for s in data}
    sells, cands = [], []
    for s, p in L["positions"].items():
        r2, ab, lo7, hi7 = (f[idx[s][d]] for f in feats[s])
        if survivors.exit_signal(r2, hi7, p["held"]):
            sells.append({"side": "sell", "sym": s, "why": "RSI(2) %.0f" % r2 if r2 and r2 > 70 else
                          "highest close of 7" if hi7 else "10 days held"})
    for s in PAPER:
        i = idx[s].get(d)
        if s in L["positions"] or i is None or i < 200:
            continue
        r2, ab, lo7, hi7 = (f[i] for f in feats[s])
        if survivors.entry_signal(r2, ab, lo7):
            cands.append((r2 if r2 is not None else 50, s, "RSI(2) %.1f" % r2 if r2 is not None and r2 < 10 else "lowest close of 7"))
    free = SLOTS - len(L["positions"]) + len(sells)
    L["orders"] = sells + [{"side": "buy", "sym": s, "why": w} for _, s, w in sorted(cands)[:max(0, free)]]
    L["history"].append({"date": d, "equity": L["equity"]})
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    with open(LEDGER, "w") as fh:
        json.dump(L, fh, indent=1)
    print("Indices bot (PAPER, $10,000 start), %s close: equity $%.2f, open: %s." % (
        d, L["equity"], ", ".join(CFD[s] for s in L["positions"]) or "none"))
    for m in msgs:
        print("  " + m)
    for o in L["orders"]:
        print("  ORDER for tomorrow's open: %s %s (%s) - %s" % (o["side"].upper(), CFD[o["sym"]], o["sym"], o["why"]))
    if not L["orders"] and not msgs:
        print("  No trade: no index is in a short dip inside an uptrend.")
    return 0


def cmd_report(a):
    L = load_ledger()
    t = L["trades"]
    print("Indices bot (PAPER) since %s: equity $%.2f (%+.2f%%), %d closed trades, net $%+.2f; open: %s." % (
        L["start"], L["equity"], (L["equity"] / 10000.0 - 1) * 100, len(t), sum(x["pnl"] for x in t),
        ", ".join(CFD[s] for s in L["positions"]) or "none"))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="the indices bot (paper)")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("fetch")
    p = sub.add_parser("backtest")
    p.add_argument("--placebo", type=int, default=200)
    p.add_argument("--universe", choices=["all", "us"], default="all")
    p.add_argument("--write", action="store_true")
    p = sub.add_parser("today")
    p.add_argument("--force", action="store_true")
    p.add_argument("--no-fetch", action="store_true")
    sub.add_parser("report")
    a = ap.parse_args(argv)
    fn = {"fetch": cmd_fetch, "backtest": cmd_backtest, "today": cmd_today, "report": cmd_report}.get(a.cmd)
    if not fn:
        ap.print_help()
        return 1
    return fn(a)


if __name__ == "__main__":
    sys.exit(main())
