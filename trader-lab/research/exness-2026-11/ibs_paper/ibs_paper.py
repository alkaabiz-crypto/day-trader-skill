#!/usr/bin/env python3
"""USTEC "IBS at the close" paper ledger. Rule fixed 2026-11-26 (pre-registered), not to be changed.

Rule, on QQQ's regular session (9:30-16:00 New York) as the proxy for USTEC:
  IBS = (close - low) / (high - low).
  Flat and IBS < 0.2  -> BUY 0.05 lot USTEC at the first 5-minute bar opening at or after 16:10 New York.
  Long and close > the previous close -> SELL at the same time.
Account: Exness Standard, UAE extended swap-free (no swap). Cost: USTEC spread 1.12 pts + 1.0 pt slippage
per round trip at 0.05 lot ($1 per point per lot). Paper only: nothing reaches any account.
Kill rule: if the paper account falls $250 below its peak, the ledger marks STOPPED and takes no new trades.

  python3 ibs_paper.py update   # add every finished session since the start, idempotent
  python3 ibs_paper.py report   # totals, this week, and the pass bar
"""
import csv, json, os, sys, math, urllib.request, datetime as dt
from zoneinfo import ZoneInfo
NY = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, "ledger.csv")
START, LOT, COST_PTS, START_USD, KILL = "2026-11-27", 0.05, 2.12, 1000.0, 250.0
NDX_PER_QQQ = None  # measured each run from ^NDX / QQQ closes

def get(sym, rng, interval, prepost=False):
    u = "https://query1.finance.yahoo.com/v8/finance/chart/%s?range=%s&interval=%s&includePrePost=%s" % (sym, rng, interval, str(prepost).lower())
    r = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=30))["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    return [(r["timestamp"][i], q["open"][i], q["high"][i], q["low"][i], q["close"][i]) for i in range(len(r["timestamp"])) if q["close"][i] is not None]

def sessions():
    bars = get("QQQ", "60d", "5m", True); S = {}
    for ts, o, h, l, c in bars:
        t = dt.datetime.fromtimestamp(ts, NY); d = t.date().isoformat(); s = S.setdefault(d, {"bars": 0})
        if dt.time(9, 30) <= t.time() < dt.time(16, 0):
            if "h" not in s: s.update(h=h, l=l)
            s["h"] = max(s["h"], h); s["l"] = min(s["l"], l); s["c"] = c; s["bars"] += 1; s["last"] = t.time()
        elif t.time() >= dt.time(16, 10) and "fill" not in s and o:
            s["fill"] = o
    return {d: s for d, s in S.items() if "c" in s and "fill" in s and s["bars"] >= 70}  # full sessions only

def load():
    if not os.path.exists(LEDGER): return []
    return list(csv.DictReader(open(LEDGER)))

def update():
    rows = load(); done = {r["date"] for r in rows}
    S = sessions(); days = sorted(S)
    ndx = get("^NDX", "5d", "1d")[-1][4]; qqq = get("QQQ", "5d", "1d")[-1][4]; ratio = ndx / qqq
    pos = int(rows[-1]["pos_after"]) if rows else 0
    entry = float(rows[-1]["entry_fill"]) if rows and rows[-1]["entry_fill"] else None
    equity = float(rows[-1]["equity"]) if rows else START_USD
    peak = max([START_USD] + [float(r["equity"]) for r in rows])
    stopped = bool(rows) and rows[-1]["status"] == "STOPPED"
    prev_close = None
    for i, d in enumerate(days):
        s = S[d]
        if d < START or d in done:
            prev_close = s["c"]; continue
        if d == dt.datetime.now(NY).date().isoformat() and dt.datetime.now(NY).time() < dt.time(16, 15):
            break
        ibs = (s["c"] - s["l"]) / (s["h"] - s["l"]) if s["h"] > s["l"] else 0.5
        action, pnl = "hold", 0.0
        if pos and prev_close is not None and s["c"] > prev_close:
            pnl = (s["fill"] - entry) * ratio * LOT - COST_PTS * LOT
            equity += pnl; pos = 0; entry = None; action = "SELL"
        elif not pos and not stopped and ibs < 0.2:
            pos = 1; entry = s["fill"]; action = "BUY"
        mark = equity + ((s["fill"] - entry) * ratio * LOT if pos else 0.0)
        peak = max(peak, mark)
        if peak - mark >= KILL: stopped = True
        rows.append(dict(date=d, high=round(s["h"], 2), low=round(s["l"], 2), close=round(s["c"], 2), ibs=round(ibs, 3),
                         fill_1610=round(s["fill"], 2), action=action, pnl_usd=round(pnl, 2), pos_after=pos,
                         entry_fill=round(entry, 2) if entry else "", equity=round(equity, 2), mark_to_market=round(mark, 2),
                         status="STOPPED" if stopped else "ACTIVE"))
        prev_close = s["c"]
    with open(LEDGER, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["date"]); w.writeheader(); w.writerows(rows)
    print("ledger: %d sessions recorded, last %s" % (len(rows), rows[-1]["date"] if rows else "-"))

def report():
    rows = load()
    if not rows: print("No sessions recorded yet (the ledger starts %s)." % START); return
    sells = [float(r["pnl_usd"]) for r in rows if r["action"] == "SELL"]
    last = rows[-1]; wk = (dt.date.fromisoformat(last["date"]) - dt.timedelta(days=6)).isoformat()
    week = [r for r in rows if r["date"] >= wk]
    t = (sum(sells)/len(sells)) / (math.sqrt(sum((x - sum(sells)/len(sells))**2 for x in sells)/(len(sells)-1))/math.sqrt(len(sells))) if len(sells) > 2 else float("nan")
    print("USTEC IBS paper ledger since %s (0.05 lot, swap-free, $%.0f start; paper only)" % (START, START_USD))
    print("  sessions %d | closed trades %d | won %d | net $%+.2f | t %.2f | equity $%.2f | marked $%.2f | %s | now %s"
          % (len(rows), len(sells), sum(x > 0 for x in sells), sum(sells), t, float(last["equity"]), float(last["mark_to_market"]),
             last["status"], "LONG since fill %s" % last["entry_fill"] if last["pos_after"] == "1" else "FLAT"))
    print("  last 7 days: " + "; ".join("%s %s%s" % (r["date"], r["action"], " $%+.2f" % float(r["pnl_usd"]) if r["action"] == "SELL" else "") for r in week if r["action"] != "hold") or "  last 7 days: no trades")
    print("  Review bar (fixed): after 30+ closed trades, net > $0 and t >= 2, and never STOPPED. Then going live is the owner's decision.")

if __name__ == "__main__":
    {"update": update, "report": report}[sys.argv[1] if len(sys.argv) > 1 else "report"]()
