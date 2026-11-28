#!/usr/bin/env python3
"""BTCUSD Williams volatility breakout paper ledger. Rule fixed 2026-11-26 (pre-registered), not to be changed.

Each UTC day: level = today's 00:00 UTC open + 0.6 x yesterday's (UTC) high - low.
  If an hour's high reaches the level: BUY 0.01 lot BTCUSD at the level (or that hour's open if it opened above).
  Protective stop $100 below the fill at 0.01 lot (= $10,000 of BTC price). Otherwise SELL at the day's last hourly close.
Long only, one trade a day. Exness Standard, UAE extended swap-free (no swap). Cost: spread $6.40 + $5 slippage per BTC
per round trip, at 0.01 lot = $0.11. Paper only. Kill rule: stop new trades after a $250 drop from the ledger's peak,
and the combined kill in ibs_paper.py's report (both ledgers together down $300 from their combined peak).

  python3 williams_paper.py update | report
"""
import csv, json, os, sys, math, urllib.request, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, "williams_ledger.csv")
START, LOT, K, STOP_USD, COST_PER_BTC, START_USD, KILL = "2026-11-27", 0.01, 0.6, 100.0, 11.4, 1000.0, 250.0

def hours():
    u = "https://query1.finance.yahoo.com/v8/finance/chart/BTC-USD?range=30d&interval=60m"
    r = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30))["chart"]["result"][0]
    q = r["indicators"]["quote"][0]; D = {}
    for i, ts in enumerate(r["timestamp"]):
        if None in (q["open"][i], q["high"][i], q["low"][i], q["close"][i]): continue
        t = dt.datetime.fromtimestamp(ts, dt.timezone.utc)
        if t.minute != 0: continue  # skip the live partial bar
        D.setdefault(t.date().isoformat(), []).append((t.hour, q["open"][i], q["high"][i], q["low"][i], q["close"][i]))
    return {d: sorted(v) for d, v in D.items()}

def load():
    return list(csv.DictReader(open(LEDGER))) if os.path.exists(LEDGER) else []

def update():
    rows = load(); done = {r["date"] for r in rows}; H = hours(); days = sorted(H)
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    equity = float(rows[-1]["equity"]) if rows else START_USD
    peak = max([START_USD] + [float(r["equity"]) for r in rows]); stopped = bool(rows) and rows[-1]["status"] == "STOPPED"
    for i, d in enumerate(days):
        if d < START or d in done or d >= today or i == 0 or len(H[d]) < 23 or len(H[days[i-1]]) < 23: continue
        p, B = H[days[i-1]], H[d]
        lvl = B[0][1] + K * (max(b[2] for b in p) - min(b[3] for b in p))
        action, fill, exitp, pnl = "no trade", "", "", 0.0
        if not stopped:
            for j, (h, o, hi, lo, c) in enumerate(B):
                if hi >= lvl:
                    fill = max(lvl, o); stop = fill - STOP_USD / LOT; exitp = B[-1][4]; action = "BUY/SELL at close"
                    for (h2, o2, hi2, lo2, c2) in B[j:]:
                        if lo2 <= stop: exitp = min(o2, stop) if h2 != h else stop; action = "BUY/STOPPED"; break
                    pnl = LOT * (exitp - fill) - LOT * COST_PER_BTC
                    break
        equity += pnl; peak = max(peak, equity)
        if peak - equity >= KILL: stopped = True
        rows.append(dict(date=d, level=round(lvl, 2), action=action, fill=round(fill, 2) if fill else "", exit=round(exitp, 2) if exitp else "",
                         pnl_usd=round(pnl, 2), equity=round(equity, 2), status="STOPPED" if stopped else "ACTIVE"))
    if rows:
        with open(LEDGER, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print("williams ledger: %d days recorded, last %s" % (len(rows), rows[-1]["date"] if rows else "-"))

def report():
    rows = load()
    if not rows: print("Williams BTC ledger: no days recorded yet (starts %s)." % START); return
    tr = [float(r["pnl_usd"]) for r in rows if r["action"].startswith("BUY")]
    m = sum(tr)/len(tr) if tr else 0
    t = m/(math.sqrt(sum((x-m)**2 for x in tr)/(len(tr)-1))/math.sqrt(len(tr))) if len(tr) > 2 else float("nan")
    last = rows[-1]; wk = (dt.date.fromisoformat(last["date"]) - dt.timedelta(days=6)).isoformat()
    print("Williams BTC ledger since %s (0.01 lot, swap-free, $%.0f start; paper only)" % (START, START_USD))
    print("  days %d | trades %d | won %d | net $%+.2f | t %.2f | equity $%.2f | %s" % (len(rows), len(tr), sum(x > 0 for x in tr), sum(tr), t, float(last["equity"]), last["status"]))
    print("  last 7 days: " + ("; ".join("%s $%+.2f" % (r["date"], float(r["pnl_usd"])) for r in rows if r["date"] >= wk and r["action"].startswith("BUY")) or "no trades"))
    print("  Review bar (fixed): after 60+ trades, net > $0 and t >= 2, and never STOPPED.")

if __name__ == "__main__":
    {"update": update, "report": report}[sys.argv[1] if len(sys.argv) > 1 else "report"]()
