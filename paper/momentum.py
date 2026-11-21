#!/usr/bin/env python3
"""Momentum forward test: a simulated $5,000 account, one decision a month.

The rule, frozen when the test started (see paper/forward/universe.json):

  universe   the 100 most traded US stocks on 2026-11-20, frozen (no later picking)
  score      return from 12 months ago to 1 month ago (252 to 21 trading days, adjusted closes)
  hold       the top 10 by score, equal weight, fractional shares
  rebalance  at the close of the first trading day of each month
  costs      0.05 % of every dollar bought or sold
  benchmark  the same starting cash in SPY, bought on the same day, held

Nothing here talks to a broker. Fills are Yahoo daily closes.

    python3 paper/momentum.py backtest       # the same rule on 10 years of history
    python3 paper/momentum.py start          # buy the first top 10 at the latest close
    python3 paper/momentum.py daily          # mark to market; rebalance if a new month began
    python3 paper/momentum.py status         # holdings, value, vs SPY

The ledger lives in paper/forward/momentum.json and is meant to be committed,
so the test survives a wiped machine. Not financial advice: a backtest is not
a promise, and this universe is today's winners, so the backtest flatters the rule.
"""

import argparse
import datetime
import json
import math
import os
import statistics as st
import sys
import time
import importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FWD = os.path.join(ROOT, "paper", "forward")
LEDGER = os.path.join(FWD, "momentum.json")
UNIVERSE = os.path.join(FWD, "universe.json")
CACHE = os.path.join(ROOT, "trader", "daily")
TOP, LOOK, SKIP, COST = 10, 252, 21, 0.0005

sys.dont_write_bytecode = True
_spec = importlib.util.spec_from_file_location("mom_scan", os.path.join(ROOT, "trader-scanner", "scan.py"))
scan = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scan)


# ---------------------------------------------------------------- data

def parse_daily(text):
    """Yahoo v8 daily chart -> {date: (close, adjclose)} for complete sessions."""
    r = json.loads(text)["chart"]["result"][0]
    ts = r.get("timestamp") or []
    q = r["indicators"]["quote"][0]
    ac = (r["indicators"].get("adjclose") or [{}])[0].get("adjclose") or q["close"]
    out = {}
    for t, c, a in zip(ts, q["close"], ac):
        if c and a:
            out[scan.ts_to_eastern(t).date()] = (float(c), float(a))
    return out


def fetch(symbols, rng, refresh=True):
    """{sym: {date: (close, adj)}}; caches to trader/daily/<SYM>.json."""
    os.makedirs(CACHE, exist_ok=True)
    data = {}
    for s in symbols:
        path = os.path.join(CACHE, s + ".json")
        text = None
        if refresh:
            try:
                text = scan.yahoo_get(scan.chart_path(s, rng, "1d"))
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(text)
                time.sleep(scan.PAUSE)
            except scan.ScanError as e:
                print("  %s: %s" % (s, e), file=sys.stderr)
        if text is None and os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        if text:
            try:
                data[s] = parse_daily(text)
            except (KeyError, IndexError, TypeError, ValueError):
                print("  %s: unreadable chart" % s, file=sys.stderr)
    return data


def complete_dates(spy, now_et):
    """SPY's session dates, minus today's until 4:00 PM ET."""
    ds = sorted(spy)
    if ds and ds[-1] == now_et.date() and now_et.time() < datetime.time(16, 5):
        ds = ds[:-1]
    return ds


# ---------------------------------------------------------------- the rule

def rank(data, dates, i, symbols):
    """Top 10 at date index i: (score list, picks). Needs 252 sessions of history."""
    if i < LOOK:
        return [], []
    d0, d1, d = dates[i - LOOK], dates[i - SKIP], dates[i]
    scored = []
    for s in symbols:
        ser = data.get(s) or {}
        if d0 in ser and d1 in ser and d in ser:
            scored.append((ser[d1][1] / ser[d0][1] - 1, s))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return scored, [s for _, s in scored[:TOP]]


def first_trading_days(dates):
    """Indexes of the first session of each month."""
    return [i for i in range(1, len(dates)) if dates[i].month != dates[i - 1].month]


def backtest(data, dates, symbols):
    """Monthly returns of the rule, of holding every eligible stock equally, and of SPY."""
    marks = [i for i in first_trading_days(dates) if i >= LOOK]
    rows, held = [], {}
    for a, b in zip(marks, marks[1:]):
        _, picks = rank(data, dates, a, symbols)
        elig = [s for s in symbols if dates[a] in data.get(s, {}) and dates[b] in data.get(s, {})]
        picks = [s for s in picks if s in elig]
        if len(picks) < TOP or len(elig) < 20:
            continue
        r = lambda s: data[s][dates[b]][1] / data[s][dates[a]][1] - 1
        new = {s: 1.0 / TOP for s in picks}
        turnover = sum(abs(new.get(s, 0) - held.get(s, 0)) for s in set(new) | set(held))
        rows.append({"start": dates[a], "mom": st.mean(r(s) for s in picks) - COST * turnover,
                     "all": st.mean(r(s) for s in elig), "spy": r("SPY")})
        held = new
    return rows


def summary(rets, per_year=12):
    eq, peak, mdd = 1.0, 1.0, 0.0
    for r in rets:
        eq *= 1 + r
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1)
    yrs = len(rets) / float(per_year)
    sd = st.pstdev(rets)
    return {"cagr": eq ** (1 / yrs) - 1 if yrs else 0, "sharpe": st.mean(rets) / sd * math.sqrt(per_year) if sd else 0,
            "mdd": mdd, "months": len(rets)}


# ---------------------------------------------------------------- the ledger

def load_ledger():
    if not os.path.exists(LEDGER):
        return None
    with open(LEDGER, encoding="utf-8") as fh:
        return json.load(fh)


def save_ledger(doc):
    os.makedirs(FWD, exist_ok=True)
    tmp = LEDGER + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)
        fh.write("\n")
    os.replace(tmp, LEDGER)


def value(doc, data, d):
    v = doc["cash"]
    for s, h in doc["holdings"].items():
        v += h["shares"] * data[s][d][0] if d in data.get(s, {}) else h["shares"] * h["last_price"]
    return v


def rebalance(doc, data, dates, i, symbols):
    d = dates[i]
    scored, picks = rank(data, dates, i, symbols)
    if len(picks) < TOP:
        raise SystemExit("only %d stocks have a year of history on %s" % (len(picks), d))
    total = value(doc, data, d)
    old = {s: h["shares"] for s, h in doc["holdings"].items()}
    new_value = total
    # every dollar traded pays the cost: solve for the equal weight after costs
    traded = 0.0
    target = {}
    for _ in range(3):
        each = new_value / TOP
        target = {s: each / data[s][d][0] for s in picks}
        traded = sum(abs(target.get(s, 0) - old.get(s, 0)) * data[s][d][0]
                     for s in set(target) | set(old) if d in data.get(s, {}))
        new_value = total - COST * traded
    doc["holdings"] = {s: {"shares": round(target[s], 6), "last_price": data[s][d][0]} for s in picks}
    doc["cash"] = round(total - COST * traded - sum(target[s] * data[s][d][0] for s in picks), 2)
    sold, bought = sorted(set(old) - set(picks)), sorted(set(picks) - set(old))
    doc["rebalances"].append({"date": d.isoformat(), "picks": picks, "sold": sold, "bought": bought,
                              "value_before": round(total, 2), "costs": round(COST * traded, 2),
                              "scores": {s: round(v * 100, 1) for v, s in scored[:TOP]}})
    doc["last_rebalance"] = d.isoformat()
    return picks, sold, bought


def mark(doc, data, d):
    v = value(doc, data, d)
    for s, h in doc["holdings"].items():
        if d in data.get(s, {}):
            h["last_price"] = data[s][d][0]
    spy = doc["benchmark"]["shares"] * data["SPY"][d][0]
    doc["marks"] = [m for m in doc["marks"] if m["date"] != d.isoformat()]
    doc["marks"].append({"date": d.isoformat(), "value": round(v, 2), "spy_value": round(spy, 2)})
    return v, spy


# ---------------------------------------------------------------- commands

def universe():
    with open(UNIVERSE, encoding="utf-8") as fh:
        return json.load(fh)["symbols"]


def cmd_backtest(a):
    syms = universe()
    data = fetch(syms + ["SPY"], "10y", refresh=not a.cached)
    dates = complete_dates(data["SPY"], scan.to_eastern(scan.parse_now(None)))
    rows = backtest(data, dates, syms)
    mid = rows[len(rows) // 2]["start"]
    print("Momentum backtest: top %d of the frozen %d, monthly, %s to %s (%d months), 0.05%% costs"
          % (TOP, len(syms), rows[0]["start"], rows[-1]["start"], len(rows)))
    for key, name in (("mom", "Momentum top 10"), ("all", "Hold all equally"), ("spy", "Hold SPY")):
        parts = []
        for label, sub in (("all", rows), ("1st half", [r for r in rows if r["start"] < mid]),
                           ("2nd half", [r for r in rows if r["start"] >= mid])):
            s = summary([r[key] for r in sub])
            parts.append("%s %+.1f%%/yr (worst drop %.0f%%)" % (label, s["cagr"] * 100, s["mdd"] * 100))
        print("  %-17s %s" % (name, " | ".join(parts)))
    beat = sum(r["mom"] > r["all"] for r in rows)
    print("  Momentum beat 'hold all' in %d of %d months (%.0f%%)." % (beat, len(rows), 100.0 * beat / len(rows)))
    print("  Caveat: the universe is today's most traded stocks, the last decade's winners. That flatters")
    print("  every row, momentum most. Only the forward test is free of it. Not financial advice.")


def cmd_start(a):
    if load_ledger() and not a.force:
        raise SystemExit("the forward test already started; see `status` (use --force to restart it)")
    syms = universe()
    data = fetch(syms + ["SPY"], "2y")
    dates = complete_dates(data["SPY"], scan.to_eastern(scan.parse_now(None)))
    i = len(dates) - 1
    d = dates[i]
    doc = {"simulated": True, "rule": "top %d by 12-1 month return, monthly, %.2f%% costs" % (TOP, COST * 100),
           "started": d.isoformat(), "starting_cash": a.cash, "cash": a.cash, "holdings": {},
           "benchmark": {"symbol": "SPY", "shares": round(a.cash / data["SPY"][d][0], 6), "price": data["SPY"][d][0]},
           "rebalances": [], "marks": []}
    picks, _, _ = rebalance(doc, data, dates, i, syms)
    mark(doc, data, d)
    save_ledger(doc)
    print("Started the momentum forward test at the %s close with $%.2f simulated." % (d, a.cash))
    report(doc, data, d)


def cmd_daily(a):
    doc = load_ledger()
    if not doc:
        raise SystemExit("not started: run `momentum.py start`")
    syms = universe()
    data = fetch(sorted(set(doc["holdings"]) | set(syms) | {"SPY"}), "2y")
    dates = complete_dates(data["SPY"], scan.to_eastern(scan.parse_now(None)))
    d = dates[-1]
    did = None
    last = datetime.date.fromisoformat(doc["last_rebalance"])
    if (d.year, d.month) != (last.year, last.month):
        did = rebalance(doc, data, dates, len(dates) - 1, syms)
    mark(doc, data, d)
    save_ledger(doc)
    if did:
        picks, sold, bought = did
        print("REBALANCED at the %s close: sold %s; bought %s." % (d, ", ".join(sold) or "nothing",
                                                                   ", ".join(bought) or "nothing"))
    report(doc, data, d)


def report(doc, data, d):
    v, spy = value(doc, data, d), doc["benchmark"]["shares"] * data["SPY"][d][0]
    c = doc["starting_cash"]
    print("%s close: momentum $%.2f (%+.2f%%) vs SPY $%.2f (%+.2f%%), since %s. Simulated, not advice."
          % (d, v, (v / c - 1) * 100, spy, (spy / c - 1) * 100, doc["started"]))
    for s, h in sorted(doc["holdings"].items()):
        px = data[s][d][0] if d in data.get(s, {}) else h["last_price"]
        print("  %-6s %10.4f sh  $%9.2f  worth $%8.2f" % (s, h["shares"], px, h["shares"] * px))
    if doc["cash"]:
        print("  cash   $%.2f" % doc["cash"])


def cmd_status(a):
    doc = load_ledger()
    if not doc:
        raise SystemExit("not started: run `momentum.py start`")
    data = fetch(sorted(set(doc["holdings"]) | {"SPY"}), "5d")
    d = complete_dates(data["SPY"], scan.to_eastern(scan.parse_now(None)))[-1]
    report(doc, data, d)


def main(argv=None):
    p = argparse.ArgumentParser(description="Momentum forward test (simulated money, no broker).")
    p.add_argument("cmd", choices=["backtest", "start", "daily", "status"])
    p.add_argument("--cash", type=float, default=5000.0)
    p.add_argument("--cached", action="store_true", help="backtest from trader/daily without downloading")
    p.add_argument("--force", action="store_true")
    a = p.parse_args(argv)
    {"backtest": cmd_backtest, "start": cmd_start, "daily": cmd_daily, "status": cmd_status}[a.cmd](a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
