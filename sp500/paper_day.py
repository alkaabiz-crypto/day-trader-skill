"""SPY paper day trade, run by the day-trader skills (paper money only, no broker).

Pipeline: trader-entry (15-minute opening-range breakout, long only)
-> trader-exit (stop at the range midpoint, target 2R, flat by 15:55)
-> trader-budget (size to sp500/config.json: $5,000 paper, $50 max loss)
-> trader-risk (must PASS) -> simulated fill at the trigger bar's close.
Then it walks 5-minute bars: stop first if a bar touches both, a gap past the
stop fills at that bar's open, otherwise out at the 15:50 bar's close.
Costs: 2 bp round trip. Stateless: rerun it any time today and it gives the
same answer for the bars seen so far.

Usage: python3 sp500/paper_day.py [--date YYYY-MM-DD] [--final]
"""
import argparse, csv, datetime as dt, json, os, subprocess, sys
from zoneinfo import ZoneInfo

import yfinance as yf

NY = ZoneInfo("America/New_York")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CFG = os.path.join(HERE, "config.json")
COST_BP = 2.0


def sh(args):
    p = subprocess.run([sys.executable] + args, cwd=ROOT, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date")
    ap.add_argument("--final", action="store_true", help="append the result to sp500/journal.csv")
    a = ap.parse_args()
    now = dt.datetime.now(NY)
    day = a.date or now.strftime("%Y-%m-%d")
    if a.date and a.date != now.strftime("%Y-%m-%d"):
        now = dt.datetime.fromisoformat(day + " 16:00").replace(tzinfo=NY)
    d = os.path.join(HERE, day)
    os.makedirs(d, exist_ok=True)
    stamp = now.strftime("%Y-%m-%d %H:%M")
    entry_now = min(now, dt.datetime.fromisoformat(day + " 15:30").replace(tzinfo=NY)).strftime("%Y-%m-%d %H:%M")
    print(f"SPY paper day trade, {day}, run at {stamp} New York (paper money, no real orders)")

    if now.strftime("%H:%M") < "09:45":
        print("Opening range not finished (9:30-9:45). Nothing to do yet.")
        return
    ej = os.path.join(d, "entry.json")
    rc, out = sh(["trader-entry/entry.py", "check", "SPY", "--config", CFG, "--now", entry_now, "--write", ej])
    print("\n[trader-entry]\n" + out)
    st = json.load(open(ej)) if os.path.exists(ej) else {}
    if st.get("status") != "triggered":
        print("\nNo entry yet." if now.strftime("%H:%M") < "15:30" else "\nNo trade today: no breakout before 15:30.")
        if a.final and now.strftime("%H:%M") >= "15:30":
            log(day, None)
        return

    # When it triggered, run the rest of the skills as of that moment.
    # The fill is the trigger bar's close, e.g. time "10:25 AM" for the 10:20 bar.
    trig = dt.datetime.strptime(day + " " + st["time"], "%Y-%m-%d %I:%M %p").replace(tzinfo=NY)
    when = (trig + dt.timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M")
    pj, oj = os.path.join(d, "plan.json"), os.path.join(d, "orders.json")
    rc, out = sh(["trader-exit/exit.py", "plan", "--from", ej, "--stop", "or-mid", "--target", "2R",
                  "--config", CFG, "--now", when, "--write", pj])
    print("\n[trader-exit]\n" + out)
    if rc or not os.path.exists(pj):
        print("Exit plan refused: no trade.")
        return
    rc, out = sh(["trader-budget/size.py", "--plan", pj, "--config", CFG, "--now", when, "--write", oj])
    print("\n[trader-budget]\n" + out)
    rc, out = sh(["trader-risk/check.py", "--orders", oj, "--config", CFG, "--now", when, "--today", day,
                  "--portfolio", os.path.join(d, "portfolio.json"), "--state", os.path.join(d, "state.json"),
                  "--out", os.path.join(d, "verdicts.json")])
    print("\n[trader-risk]\n" + out)
    if "1 passed, 0 blocked" not in out:
        print("Risk check did not pass: no trade.")
        return

    plan = json.load(open(pj))
    order = json.load(open(oj))
    order = order["orders"][0]
    qty = int(float(order["qty"]))
    entry = float(plan["entry"]); stop = float(plan["stop"]); target = float(plan["target"])
    entry_time = trig

    bars = yf.Ticker("SPY").history(start=day, end=(dt.date.fromisoformat(day) + dt.timedelta(days=1)).isoformat(),
                                    interval="5m", prepost=False)
    bars.index = bars.index.tz_convert(NY)
    # Bars that start at or after the fill (the trigger bar itself is not walked).
    bars = bars[(bars.index >= entry_time) & (bars.index.strftime("%H:%M") <= "15:50")]
    # Only bars that have finished by now.
    bars = bars[bars.index + dt.timedelta(minutes=5) <= now]
    exit_px = exit_why = exit_at = None
    for ts, b in bars.iterrows():
        if b.Low <= stop:
            exit_px, exit_why = (min(stop, b.Open), "stop") ; exit_at = ts; break
        if b.High >= target:
            exit_px, exit_why = (max(target, b.Open) if b.Open > target else target, "target"); exit_at = ts; break
    done = exit_px is not None
    if not done and now.strftime("%H:%M") >= "15:55" and len(bars):
        exit_px, exit_why, exit_at, done = float(bars.Close.iloc[-1]), "flat by 15:55", bars.index[-1], True
    last = float(bars.Close.iloc[-1]) if len(bars) else entry
    px = exit_px if done else last
    gross = (px - entry) * qty
    cost = entry * qty * COST_BP / 1e4
    print("\n[paper position]")
    print(f"  Bought {qty} SPY at ${entry:.2f} ({entry_time:%H:%M}), stop ${stop:.2f}, target ${target:.2f}")
    if done:
        print(f"  CLOSED at ${px:.2f} ({exit_why}, {exit_at:%H:%M}): P&L ${gross - cost:+.2f} after ${cost:.2f} costs")
    else:
        print(f"  OPEN. Last 5-minute close ${last:.2f}: unrealised P&L ${gross - cost:+.2f} after costs. "
              f"Out by 15:55 at the latest.")
    if a.final and done:
        log(day, dict(qty=qty, entry=entry, entry_time=f"{entry_time:%H:%M}", stop=stop, target=target,
                      exit=round(px, 2), exit_time=f"{exit_at:%H:%M}", why=exit_why,
                      pnl=round(gross - cost, 2)))


def log(day, r):
    path = os.path.join(HERE, "journal.csv")
    cols = ["date", "qty", "entry", "entry_time", "stop", "target", "exit", "exit_time", "why", "pnl"]
    rows = list(csv.DictReader(open(path))) if os.path.exists(path) else []
    rows = [x for x in rows if x["date"] != day]
    rows.append({"date": day, **(r or {"why": "no trade", "pnl": 0})})
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    pnl = sum(float(x["pnl"] or 0) for x in rows)
    n = sum(1 for x in rows if x.get("qty"))
    print(f"\nJournal: {len(rows)} days, {n} trades, total P&L ${pnl:+.2f} on the $5,000 paper account.")


if __name__ == "__main__":
    main()
