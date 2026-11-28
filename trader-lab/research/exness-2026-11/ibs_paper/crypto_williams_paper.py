#!/usr/bin/env python3
"""Crypto Williams breakout BASKET paper ledger (batch 24/24b). Rule fixed 2026-11-28, not to be changed.

Same rule as williams_paper.py (BTC), on 10 other coins: ETH LTC XRP BCH ADA SOL DOGE LINK DOT BNB.
Each UTC day, per coin: level = 00:00 UTC open + 0.6 x yesterday's UTC high - low. If an hour's high reaches it, BUY at the
level (or that hour's open if above), SELL at the day's last hourly close. $100 notional per coin (Exness minimum lots for these
coins are NOT verified; check in MT5 before any real use). Cost 5 bp round trip. Swap-free. Paper only.
Kill: the basket stops new trades after a $300 drop from its peak.
Backtest: basket of 11 coins (with BTC) judged 2022-26 t 3.69; XRP, BCH, LINK pass alone; hourly data matches daily bars.

  python3 crypto_williams_paper.py update | report
"""
import csv, json, os, sys, math, urllib.request, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, "crypto_williams_ledger.csv")
START, K, USD, BP, KILL = "2026-11-28", 0.6, 100.0, 5.0, 300.0
COINS = "ETH LTC XRP BCH ADA SOL DOGE LINK DOT BNB".split()
FIELDS = ["date", "coin", "level", "fill", "exit", "pnl_usd", "basket_equity", "status"]

def hours(c):
    u = "https://query1.finance.yahoo.com/v8/finance/chart/%s-USD?range=30d&interval=60m" % c
    r = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30))["chart"]["result"][0]
    q = r["indicators"]["quote"][0]; D = {}
    for i, ts in enumerate(r["timestamp"]):
        if None in (q["open"][i], q["high"][i], q["low"][i], q["close"][i]): continue
        t = dt.datetime.fromtimestamp(ts, dt.timezone.utc)
        if t.minute != 0: continue
        D.setdefault(t.date().isoformat(), []).append((t.hour, q["open"][i], q["high"][i], q["low"][i], q["close"][i]))
    return {d: sorted(v) for d, v in D.items()}

def load():
    return list(csv.DictReader(open(LEDGER))) if os.path.exists(LEDGER) else []

def update():
    rows = load(); done = {(r["date"], r["coin"]) for r in rows}
    equity = float(rows[-1]["basket_equity"]) if rows else 0.0
    peak = max([0.0] + [float(r["basket_equity"]) for r in rows]); stopped = bool(rows) and rows[-1]["status"] == "STOPPED"
    today = dt.datetime.now(dt.timezone.utc).date().isoformat(); new = []
    data = {}
    for c in COINS:
        try: data[c] = hours(c)
        except Exception as e: print("fetch failed", c, e)
    days = sorted({d for H in data.values() for d in H})
    for d in days:
        if d < START or d >= today: continue
        for c, H in data.items():
            ds = sorted(H)
            if d not in H or (d, c) in done: continue
            i = ds.index(d)
            if i == 0 or len(H[d]) < 23 or len(H[ds[i-1]]) < 23: continue
            p, B = H[ds[i-1]], H[d]
            lvl = B[0][1] + K * (max(b[2] for b in p) - min(b[3] for b in p)); fill = ex = None; pnl = 0.0
            if not stopped:
                for (h, o, hi, lo, cl) in B:
                    if hi >= lvl: fill = max(lvl, o); ex = B[-1][4]; pnl = USD * (ex / fill - 1) - USD * BP / 1e4; break
            equity += pnl; peak = max(peak, equity)
            if peak - equity >= KILL: stopped = True
            new.append(dict(date=d, coin=c, level=round(lvl, 6), fill=round(fill, 6) if fill else "", exit=round(ex, 6) if ex else "",
                            pnl_usd=round(pnl, 2), basket_equity=round(equity, 2), status="STOPPED" if stopped else "ACTIVE"))
    exists = os.path.exists(LEDGER)
    with open(LEDGER, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if not exists: w.writeheader()
        w.writerows(new)
    print("crypto basket: %d coin-days added, equity $%+.2f, %s" % (len(new), equity, "STOPPED" if stopped else "ACTIVE"))

def report():
    rows = load()
    if not rows: print("Crypto Williams basket: nothing recorded yet (starts %s)." % START); return
    tr = [float(r["pnl_usd"]) for r in rows if r["fill"]]
    by = {}
    for r in rows: by[r["date"]] = by.get(r["date"], 0.0) + float(r["pnl_usd"])
    x = list(by.values()); n = len(x); m = sum(x) / n
    t = m / (math.sqrt(sum((v - m) ** 2 for v in x) / (n - 1)) / math.sqrt(n)) if n > 2 else float("nan")
    print("Crypto Williams basket since %s ($100 per coin, 10 coins, paper only)" % START)
    print("  days %d | fills %d | won %d | net $%+.2f | daily t %.2f | %s" % (n, len(tr), sum(v > 0 for v in tr), sum(tr), t, rows[-1]["status"]))
    print("  last day: " + "; ".join("%s $%+.2f" % (r["coin"], float(r["pnl_usd"])) for r in rows if r["date"] == rows[-1]["date"] and r["fill"]))
    print("  Review bar (fixed): 60+ days, net > $0, daily t >= 2, never STOPPED.")

if __name__ == "__main__":
    {"update": update, "report": report}[sys.argv[1] if len(sys.argv) > 1 else "report"]()
