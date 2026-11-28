#!/usr/bin/env python3
"""ETH London-breakout paper ledger (WATCH ONLY: a near miss in batch 26, not a pass). Rule fixed 2026-11-28, not to be changed.

Each UTC day: range = high/low of the 00:00-07:59 UTC hourly bars. Trend = yesterday's daily close vs the 50-day average of daily
closes up to yesterday (above -> long only, below -> short only). From 08:00 to 19:59 UTC, the first hour that breaks the range in
the trend direction: enter at the range edge (or that hour's open if it opened beyond), stop at the other side of the range,
otherwise exit at the 23:00 UTC hourly close. One trade a day. $1,000 of ETH, cost 3 bp a round trip, swap-free.
Batch 26 backtest (2024-11..2026-11, only 2 years of hourly data): t 2.98, random-time placebo 100%, worst drop -$146; failed
because the second year's t was 1.80 (needed 2) and the whole-period t needed 3. Kill: -$300 from peak -> STOPPED. Paper only.

  python3 eth_london_paper.py update | report
"""
import csv, json, os, sys, math, urllib.request, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, "eth_london_ledger.csv")
START, USD, BP, KILL = "2026-11-28", 1000.0, 3.0, 300.0
FIELDS = ["date", "trend", "range_hi", "range_lo", "action", "entry", "exit", "pnl_usd", "equity", "status"]

def chart(rng, interval):
    u = "https://query1.finance.yahoo.com/v8/finance/chart/ETH-USD?range=%s&interval=%s" % (rng, interval)
    r = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30))["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    return [(r["timestamp"][i], q["open"][i], q["high"][i], q["low"][i], q["close"][i]) for i in range(len(r["timestamp"]))
            if None not in (q["open"][i], q["high"][i], q["low"][i], q["close"][i])]

def load():
    return list(csv.DictReader(open(LEDGER))) if os.path.exists(LEDGER) else []

def update():
    rows = load(); done = {r["date"] for r in rows}
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    H = {}
    for ts, o, h, l, c in chart("30d", "60m"):
        t = dt.datetime.fromtimestamp(ts, dt.timezone.utc)
        if t.minute == 0: H.setdefault(t.date().isoformat(), []).append((t.hour, o, h, l, c))
    daily = {dt.datetime.fromtimestamp(ts, dt.timezone.utc).date().isoformat(): c for ts, o, h, l, c in chart("6mo", "1d")}
    dk = sorted(d for d in daily if d < today)
    equity = float(rows[-1]["equity"]) if rows else 0.0
    peak = max([0.0] + [float(r["equity"]) for r in rows]); stopped = bool(rows) and rows[-1]["status"] == "STOPPED"
    for d in sorted(H):
        if d < START or d in done or d >= today or len(H[d]) < 23: continue
        prior = [x for x in dk if x < d]
        if len(prior) < 51: continue
        sma = sum(daily[x] for x in prior[-50:]) / 50; s = 1 if daily[prior[-1]] > sma else -1
        B = sorted(H[d]); rg = [b for b in B if b[0] < 8]
        hi, lo = max(b[2] for b in rg), min(b[3] for b in rg)
        action, e, x, pnl = "no trade", "", "", 0.0
        if not stopped:
            for j, (hr, o, h, l, c) in enumerate(B):
                if not 8 <= hr < 20: continue
                if (s == 1 and h >= hi) or (s == -1 and l <= lo):
                    e = max(hi, o) if s == 1 else min(lo, o); stop = lo if s == 1 else hi; x = None; action = "BUY" if s == 1 else "SELL"
                    for (hr2, o2, h2, l2, c2) in B[j:]:
                        if hr2 > 23: break
                        if (s == 1 and l2 <= stop) or (s == -1 and h2 >= stop):
                            x = stop if hr2 == hr else (min(o2, stop) if s == 1 else max(o2, stop)); action += "/STOPPED"; break
                    if x is None: x = [b for b in B if b[0] <= 23][-1][4]; action += "/OUT 23:00"
                    pnl = USD * (s * (x / e - 1) - BP / 1e4)
                    break
        equity += pnl; peak = max(peak, equity)
        if peak - equity >= KILL: stopped = True
        rows.append(dict(date=d, trend="up" if s == 1 else "down", range_hi=round(hi, 2), range_lo=round(lo, 2), action=action,
                         entry=round(e, 2) if e else "", exit=round(x, 2) if x else "", pnl_usd=round(pnl, 2), equity=round(equity, 2),
                         status="STOPPED" if stopped else "ACTIVE"))
    if rows:
        with open(LEDGER, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    print("eth london ledger: %d days, last %s, equity $%+.2f" % (len(rows), rows[-1]["date"] if rows else "-", equity))

def report():
    rows = load()
    if not rows: print("ETH London breakout (watch only): no days yet (starts %s)." % START); return
    tr = [float(r["pnl_usd"]) for r in rows if r["action"] != "no trade"]
    m = sum(tr) / len(tr) if tr else 0
    t = m / (math.sqrt(sum((v - m) ** 2 for v in tr) / (len(tr) - 1)) / math.sqrt(len(tr))) if len(tr) > 2 else float("nan")
    print("ETH London breakout since %s (WATCH ONLY, $1,000, paper)" % START)
    print("  days %d | trades %d | won %d | net $%+.2f | t %.2f | %s" % (len(rows), len(tr), sum(v > 0 for v in tr), sum(tr), t, rows[-1]["status"]))
    print("  Review bar (fixed): 100+ trades, net > $0, t >= 2, never STOPPED.")

if __name__ == "__main__":
    {"update": update, "report": report}[sys.argv[1] if len(sys.argv) > 1 else "report"]()
