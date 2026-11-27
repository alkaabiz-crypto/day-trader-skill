#!/usr/bin/env python3
"""Export the paper bots' records as CSV files for the Paper Bots Dashboard artifact.

    python3 dashboard.py [--out DIR]     # writes equity.csv, trades.csv, positions.csv, scoreboard.csv

The dashboard (a private claude.ai artifact) attaches these files; the daily 17:23 run regenerates and re-uploads
them. Read-only over trader-lab/autopaper/ and the desk scoreboard. Research, not financial advice.
"""

import argparse
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
BOOK = os.path.join(HERE, "autopaper")
BOOKS = [("orb", "equity.csv", "trades.csv", "state.json", "Breakouts, full market"),
         ("fed", "fed_equity.csv", "fed_trades.csv", "fed_state.json", "Fed night"),
         ("sip", "sip_equity.csv", "sip_trades.csv", "sip_state.json", "Stocks in play"),
         ("btc", "btc_equity.csv", "btc_trades.csv", "btc_state.json", "Bitcoin trend")]


def rows(path):
    if not os.path.exists(path):
        return []
    with open(path) as fh:
        return list(csv.DictReader(fh))


def write(path, fields, data):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in data:
            w.writerow({k: r.get(k, "") for k in fields})


def export(out, book_dir=BOOK, scoreboard=None):
    os.makedirs(out, exist_ok=True)
    eq, tr, pos = [], [], []
    for key, ef, tf, sf, label in BOOKS:
        for r in rows(os.path.join(book_dir, ef)):
            eq.append({"time": r["time"], "account": label, "equity": r["equity"], "open": r["open"]})
        for r in rows(os.path.join(book_dir, tf)):
            tr.append({"account": label, "symbol": r["symbol"], "shares": r["qty"], "bought": r["entry_time"],
                       "entry": r["entry"], "sold": r["exit_time"], "exit": r["exit"], "reason": r["why"],
                       "pnl_usd": r["pnl_usd"]})
        sp = os.path.join(book_dir, sf)
        if os.path.exists(sp):
            with open(sp) as fh:
                st = json.load(fh)
            for p in st.get("positions", []):
                pos.append({"account": label, "symbol": p["symbol"],
                            "shares": p["qty"] * (p.get("side", 1) or 1), "entry": round(p["entry"], 2),
                            "stop": p.get("stop") if p.get("stop") is not None else "", "since": p["entry_time"]})
    write(os.path.join(out, "equity.csv"), ["time", "account", "equity", "open"], eq)
    write(os.path.join(out, "trades.csv"), ["account", "symbol", "shares", "bought", "entry", "sold", "exit",
                                            "reason", "pnl_usd"], tr)
    write(os.path.join(out, "positions.csv"), ["account", "symbol", "shares", "entry", "stop", "since"], pos)
    if scoreboard is None:
        import desk
        scoreboard = desk.scoreboard()["rows"]
    write(os.path.join(out, "scoreboard.csv"), ["study", "verdict", "detail"], scoreboard)
    return {"equity": len(eq), "trades": len(tr), "positions": len(pos), "scoreboard": len(scoreboard)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=os.path.join(HERE, "results", "dashboard"))
    a = ap.parse_args(argv)
    print(json.dumps(export(a.out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
