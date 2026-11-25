#!/usr/bin/env python3
"""Bitcoin trend paper bot: hold BTC while it closes above its 200-day average, cash otherwise. Paper only.

    python3 btc_trend.py run       # once a day after the UTC close: catch up on completed days, trade, mark
    python3 btc_trend.py report

Why this rule: in the strategy catalog (catalog.py, 2026-11-25) the trend family's edge came almost entirely from
Bitcoin (BTC t 3.1-3.9), but that was found after looking, so it isn't a pass. This is its forward test on days
nobody has seen. The rule is the plainest member of the family (the 200-day SMA, BTC t 3.35), not the best scorer
(Coppock), so the choice isn't fitted to the result.

FROZEN 2026-11-25, before the first run:
  $10,000 paper account. Each completed UTC day: if BTC's close (Yahoo BTC-USD daily) is above the average of
  the last 200 closes, hold BTC; otherwise hold cash. A change trades at that day's close, used as the next day's
  open (crypto trades round the clock, so they are the same moment), with 20 bps cost each way. No leverage, no
  stop, no shorting.
  Verdict after 365 days: LIVE-REVIEW only if the account is ahead of $10,000 of BTC bought on the start day and
  held. Otherwise FAIL. Drawdowns of both are reported. Until then: PAPER.
Ledger: trader-lab/autopaper/btc_state.json, btc_equity.csv, btc_trades.csv (the dashboard reads these).
Research, not financial advice.
"""

import argparse
import csv
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

BOOK = os.path.join(HERE, "autopaper")
CFG = {"cash": 10000.0, "sma": 200, "cost_bps": 20.0, "min_days": 365, "frozen": "2026-11-25"}
TRADE_FIELDS = ["date", "symbol", "qty", "entry_time", "entry", "stop", "target", "exit_time", "exit", "why",
                "gross_usd", "cost_usd", "pnl_usd"]


def load_state():
    p = os.path.join(BOOK, "btc_state.json")
    if os.path.exists(p):
        with open(p) as fh:
            return json.load(fh)
    return {"cash": CFG["cash"], "positions": [], "start": None, "last_day": None, "hold_qty": None}


def save_state(st):
    os.makedirs(BOOK, exist_ok=True)
    p = os.path.join(BOOK, "btc_state.json")
    with open(p + ".tmp", "w") as fh:
        json.dump(st, fh, indent=1)
    os.replace(p + ".tmp", p)


def append(name, fields, rows):
    p = os.path.join(BOOK, name)
    new = not os.path.exists(p)
    with open(p, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        if new:
            w.writeheader()
        for r in rows:
            w.writerow(r)


def completed(bars, today):
    """[(date, close)] for UTC days before `today` (Yahoo leaves out the day in progress, but be sure)."""
    return [(d, c) for d, c in zip(bars["d"], bars["c"]) if d < today and c]


def step(st, days, cfg=CFG):
    """Process each completed day after st['last_day']. Returns (closed trades, equity rows, log lines)."""
    closed, eq, log = [], [], []
    closes = [c for _, c in days]
    for i, (d, c) in enumerate(days):
        if st["last_day"] and d <= st["last_day"]:
            continue
        if i + 1 < cfg["sma"]:
            continue
        avg = sum(closes[i + 1 - cfg["sma"]:i + 1]) / cfg["sma"]
        want = c > avg
        if st["start"] is None:
            st["start"] = d
            st["hold_qty"] = cfg["cash"] / c          # the benchmark: $10,000 of BTC on the start day
        held = bool(st["positions"])
        if want and not held:
            cost = st["cash"] * cfg["cost_bps"] / 1e4
            qty = (st["cash"] - cost) / c
            st["positions"] = [{"symbol": "BTC-USD", "qty": qty, "entry": c, "side": 1, "date": d,
                                "entry_time": d, "stop": None, "cost_in": cost}]
            st["cash"] = 0.0
            log.append("%s BUY %.5f BTC @ %.0f (close %.0f > 200-day %.0f)" % (d, qty, c, c, avg))
        elif not want and held:
            p = st["positions"][0]
            gross = p["qty"] * c
            cost = gross * cfg["cost_bps"] / 1e4
            st["cash"] = gross - cost
            pnl = gross - cost - (p["qty"] * p["entry"] + p.get("cost_in", 0.0))
            closed.append({"date": p["date"], "symbol": "BTC-USD", "qty": round(p["qty"], 6), "entry_time": p["entry_time"],
                           "entry": round(p["entry"], 2), "stop": "", "target": "", "exit_time": d, "exit": round(c, 2),
                           "why": "close under the 200-day average", "gross_usd": round(p["qty"] * (c - p["entry"]), 2),
                           "cost_usd": round(cost + p.get("cost_in", 0.0), 2), "pnl_usd": round(pnl, 2)})
            st["positions"] = []
            log.append("%s SELL BTC @ %.0f (close %.0f < 200-day %.0f), P&L %+.2f" % (d, c, c, avg, pnl))
        value = st["cash"] + sum(p["qty"] * c for p in st["positions"])
        eq.append({"time": d + " 23:59", "cash": round(st["cash"], 2), "open": len(st["positions"]),
                   "equity": round(value, 2)})
        st["last_day"] = d
        st["last_close"], st["last_avg"] = c, avg
    return closed, eq, log


def report(st):
    p = os.path.join(BOOK, "btc_equity.csv")
    rows = list(csv.DictReader(open(p))) if os.path.exists(p) else []
    if not rows or not st.get("hold_qty"):
        return {"verdict": "PAPER", "days": 0}
    vals = [float(r["equity"]) for r in rows]
    hold_now = st["hold_qty"] * st["last_close"]
    peak, mdd = vals[0], 0.0
    for v in vals:
        peak = max(peak, v)
        mdd = max(mdd, 1 - v / peak)
    out = {"start": st["start"], "days": len(rows), "equity": vals[-1], "hold_btc": hold_now,
           "in_btc": bool(st["positions"]), "max_drawdown_pct": 100 * mdd, "last_close": st["last_close"],
           "last_avg": st["last_avg"]}
    if len(rows) < CFG["min_days"]:
        out["verdict"] = "PAPER"
    else:
        out["verdict"] = "LIVE-REVIEW" if vals[-1] > hold_now else "FAIL"
    return out


def cmd_run(a):
    import daily
    today = a.today or datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    bars = daily.parse_daily(daily.fetch_daily("BTC-USD"))
    st = load_state()
    days = completed(bars, today)
    if st["last_day"] is None:                     # first run: start from the latest completed day only
        st["last_day"] = days[-2][0]
    closed, eq, log = step(st, days)
    append("btc_trades.csv", TRADE_FIELDS, closed)
    append("btc_equity.csv", ["time", "cash", "open", "equity"], eq)
    save_state(st)
    r = report(st)
    print("BTC trend (paper): %s | equity $%.2f vs $%.2f holding BTC since %s | %s | close %.0f vs 200-day %.0f | %s" % (
        "; ".join(log) or "no trade", r.get("equity", 0), r.get("hold_btc", 0), r.get("start"),
        "in BTC" if r.get("in_btc") else "in cash", r.get("last_close", 0), r.get("last_avg", 0), r["verdict"]))
    with open(os.path.join(HERE, "results", "btc-trend.json"), "w") as fh:
        json.dump(r, fh, indent=1)
    return 0


def cmd_report(a):
    print(json.dumps(report(load_state()), indent=1))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("run")
    r.add_argument("--today", help="UTC date YYYY-MM-DD (default: now)")
    sub.add_parser("report")
    a = ap.parse_args(argv)
    if a.cmd == "run":
        return cmd_run(a)
    if a.cmd == "report":
        return cmd_report(a)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
