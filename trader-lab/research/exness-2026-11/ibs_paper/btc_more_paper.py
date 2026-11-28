#!/usr/bin/env python3
"""Paper ledger for three BTC rules that passed the judge.py WORTHY bar in batches 31-34. Rules fixed 2026-11-28, not to be changed.

All on UTC daily BTC-USD bars (Yahoo), 0.01 lot BTCUSD, cost $11.40 per BTC per round trip ($0.114 at 0.01 lot), swap-free. Paper only.
  NR4    yesterday's range is the narrowest of the last 4 days. Today: if yesterday's close > its 50-day average, buy-stop at yesterday's
         high (fill at the high, or the open if it opened above); if below, sell-stop at yesterday's low. Exit at today's close.
  WSHORT only when yesterday's close < its 50-day average: sell-stop at today's open - 0.6 x yesterday's range (or the open if it opened
         below). Exit at today's close.
  WWEEK  weekly (Monday-Sunday UTC): level = Monday's open + 0.6 x the previous week's high-low range. The first day whose high reaches it:
         buy at the level (or that day's open if above). Exit at Sunday's close.
Kill per book: $300 below its peak -> STOPPED. Backtest (2016-2026, batch 31-34): NR4 t 5.27 worst -$94; WSHORT t 3.58 worst -$210;
WWEEK t 4.43 worst -$245.

  python3 btc_more_paper.py update | report
"""
import csv, json, os, sys, math, urllib.request, datetime as dt
HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER, STATE = os.path.join(HERE, "btc_more_ledger.csv"), os.path.join(HERE, "btc_more_state.json")
START, LOT, COST, KILL = "2026-11-28", 0.01, 11.4 * 0.01, 300.0
FIELDS = ["date", "book", "side", "entry", "exit", "pnl_usd", "equity", "status"]

def bars():
    u = "https://query1.finance.yahoo.com/v8/finance/chart/BTC-USD?range=1y&interval=1d"
    r = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30))["chart"]["result"][0]
    q = r["indicators"]["quote"][0]; out = []
    for i, t in enumerate(r["timestamp"]):
        if None in (q["open"][i], q["high"][i], q["low"][i], q["close"][i]): continue
        out.append((dt.datetime.fromtimestamp(t, dt.timezone.utc).date().isoformat(), q["open"][i], q["high"][i], q["low"][i], q["close"][i]))
    return out

def load_state():
    if os.path.exists(STATE): return json.load(open(STATE))
    return {"last": "", "books": {b: {"equity": 0.0, "peak": 0.0, "stopped": False} for b in ("NR4", "WSHORT", "WWEEK")}, "week": {}}

def update():
    st = load_state(); rows = []
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    B = [b for b in bars() if b[0] < today]
    D = [b[0] for b in B]; O = [b[1] for b in B]; H = [b[2] for b in B]; L = [b[3] for b in B]; C = [b[4] for b in B]
    def book(name, d, side, e, x):
        bk = st["books"][name]
        if bk["stopped"]: return
        pnl = LOT * side * (x - e) - COST; bk["equity"] += pnl; bk["peak"] = max(bk["peak"], bk["equity"])
        if bk["peak"] - bk["equity"] >= KILL: bk["stopped"] = True
        rows.append(dict(date=d, book=name, side="BUY" if side == 1 else "SELL", entry=round(e, 2), exit=round(x, 2), pnl_usd=round(pnl, 2),
                         equity=round(bk["equity"], 2), status="STOPPED" if bk["stopped"] else "ACTIVE"))
    for t in range(51, len(B)):
        d = D[t]
        if d < START or d <= st["last"]: continue
        k = t - 1; sma = sum(C[k-49:k+1]) / 50
        # NR4
        if H[k] - L[k] <= min(H[j] - L[j] for j in range(k-3, k+1)):
            if C[k] > sma and H[t] >= H[k]: book("NR4", d, 1, max(H[k], O[t]), C[t])
            elif C[k] < sma and L[t] <= L[k]: book("NR4", d, -1, min(L[k], O[t]), C[t])
        # WSHORT
        if C[k] < sma:
            lv = O[t] - 0.6 * (H[k] - L[k])
            if L[t] <= lv: book("WSHORT", d, -1, min(lv, O[t]), C[t])
        # WWEEK (state carries the open position within the week)
        day = dt.date.fromisoformat(d); wkey = "%d-%02d" % day.isocalendar()[:2]; w = st["week"]
        if day.weekday() == 0:
            prev = [i for i in range(t-7, t) if i >= 0 and (dt.date.fromisoformat(D[i]) - day).days >= -7]
            w.clear()
            if len(prev) == 7: w.update(key=wkey, level=O[t] + 0.6 * (max(H[i] for i in prev) - min(L[i] for i in prev)), entry=None)
        if w.get("key") == wkey:
            if w["entry"] is None and H[t] >= w["level"]: w["entry"] = max(w["level"], O[t])
            if day.weekday() == 6 and w["entry"] is not None: book("WWEEK", d, 1, w["entry"], C[t]); w.clear()
        st["last"] = d
    exists = os.path.exists(LEDGER)
    with open(LEDGER, "a", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=FIELDS)
        if not exists: wr.writeheader()
        wr.writerows(rows)
    json.dump(st, open(STATE, "w"), indent=1)
    print("btc_more: through %s; %d trades this run; " % (st["last"] or "-", len(rows)) +
          "; ".join("%s $%+.2f %s" % (b, k["equity"], "STOPPED" if k["stopped"] else "ACTIVE") for b, k in st["books"].items()) +
          ("; WWEEK holding from %.2f" % st["week"]["entry"] if st["week"].get("entry") else ""))

def report():
    st = load_state(); rows = list(csv.DictReader(open(LEDGER))) if os.path.exists(LEDGER) else []
    print("BTC NR4 / Williams-short / weekly-Williams paper since %s (0.01 lot each, paper only)" % START)
    for b in ("NR4", "WSHORT", "WWEEK"):
        x = [float(r["pnl_usd"]) for r in rows if r["book"] == b]; n = len(x)
        t = (sum(x) / n) / (math.sqrt(sum((v - sum(x) / n) ** 2 for v in x) / (n - 1)) / math.sqrt(n)) if n > 2 else float("nan")
        print("  %s: trades %d | won %d | net $%+.2f | t %.2f | %s" % (b, n, sum(v > 0 for v in x), sum(x), t, "STOPPED" if st["books"][b]["stopped"] else "ACTIVE"))
    print("  Review bar (fixed): NR4 and WSHORT 60+ trades, WWEEK 30+ trades; net > $0, t >= 2, never STOPPED.")

if __name__ == "__main__":
    {"update": update, "report": report}[sys.argv[1] if len(sys.argv) > 1 else "report"]()
