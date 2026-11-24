#!/usr/bin/env python3
"""Copying the stock purchases US House members disclose, backtested on a $500 account. Pre-registered.

    python3 congress.py fetch [--max-docs N]   # House Clerk PTR index + PDFs -> data/congress (gitignored)
    python3 congress.py run [--write]          # -> results/congress.json

Background: Ziobrowski et al. (2011) found House members' purchases beat the market in 1985-2001; Eggers &
Hainmueller (2013, JOP 75(2)) found no edge on average. This tests what a copier could actually do: act on the
public filing date, not the trade date.

PRE-REGISTERED 2026-11-24, committed before any filing was downloaded. Not to be changed:
  Data: the House Clerk's yearly financial-disclosure indexes 2019 to today, Periodic Transaction Reports only,
    each PDF read with pdftotext and trader-pelosi/ptr.py's parser. A scanned (paper) PTR that yields no rows is
    dropped mechanically.
  Event: a purchase row (type P) of a stock with a ticker, not an option (no option details in the row, asset type
    ST or none given). One event per (filing, ticker).
  Trade: buy at the close of the first trading day after the filing date (the day the public could see it), hold 63
    trading days (about 3 months), sell at the close. Entry price at least $2; a ticker Yahoo doesn't serve is
    dropped. Cost 10 bps a round trip.
  Statistic: each event's return minus SPY's over the same 63 days, net of cost; averaged per entry month.
    In-sample: entries 2019-2021. Judged: entries from 2022. PASS only if judged t >= 3 and in-sample t > 0.
  Reported: what $500 became, holding every open position in equal weight each day and T-bills when none is
    open, next to $500 in SPY, for the judged period and all years.
Research, not financial advice.
"""

import argparse
import concurrent.futures
import gzip
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "trader-pelosi"))
import paper500 as p5  # noqa: E402
import insiders  # noqa: E402  (run_events: the same event engine)

STORE = os.path.join(HERE, "data", "congress")
RESULTS = os.path.join(HERE, "results")
FIRST_YEAR = 2019
HOLD, COST_BPS, MIN_PRICE = 63, 10.0, 2.0
SPLIT, T_BAR = "2022-01-01", 3.0


def ptr_index():
    import ptr
    import datetime
    out = []
    for y in range(FIRST_YEAR, datetime.date.today().year + 1):
        out += [r for r in ptr.load_index(y) if r["type"] == "P" and r["filed"]]
    return out


def one(row):
    """Download, read and parse one PTR; store its rows. Returns (doc_id, n_rows or None)."""
    import ptr
    rows_path = os.path.join(STORE, "rows", "%s.json" % row["doc_id"])
    if os.path.exists(rows_path):
        return row["doc_id"], -1
    pdf = os.path.join(STORE, "pdf", "%s.pdf" % row["doc_id"])
    try:
        if not os.path.exists(pdf):
            data = ptr.download(row["url"])
            if not data.startswith(b"%PDF"):
                raise ValueError("not a PDF")
            with open(pdf, "wb") as fh:
                fh.write(data)
        text = ptr.pdf_to_text(pdf) or ""
        rep = ptr.parse_ptr_text(text, filed=row["filed"]) if text.strip() else {"rows": []}
    except Exception as e:  # noqa: BLE001
        rep = {"rows": [], "error": str(e)[:200]}
    keep = [{"ticker": r.get("ticker"), "type": r.get("type"), "asset_type": r.get("asset_type"),
             "option": bool(r.get("option")), "date": r.get("date")} for r in rep.get("rows", [])]
    with open(rows_path + ".tmp", "w") as fh:
        json.dump({"filed": row["filed"], "name": row["name"], "rows": keep, "error": rep.get("error")}, fh)
    os.replace(rows_path + ".tmp", rows_path)
    try:
        os.remove(pdf)          # keep the parsed rows, not the PDFs
    except OSError:
        pass
    return row["doc_id"], len(keep)


def cmd_fetch(a):
    os.makedirs(os.path.join(STORE, "rows"), exist_ok=True)
    os.makedirs(os.path.join(STORE, "pdf"), exist_ok=True)
    idx_path = os.path.join(STORE, "index.json.gz")
    if os.path.exists(idx_path) and not a.refresh_index:
        with gzip.open(idx_path, "rt") as fh:
            idx = json.load(fh)
    else:
        idx = ptr_index()
        with gzip.open(idx_path, "wt") as fh:
            json.dump(idx, fh)
    todo = [r for r in idx if not os.path.exists(os.path.join(STORE, "rows", "%s.json" % r["doc_id"]))]
    if a.max_docs:
        todo = todo[:a.max_docs]
    n = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        for doc, k in ex.map(one, todo):
            n += 1
    left = len([r for r in idx if not os.path.exists(os.path.join(STORE, "rows", "%s.json" % r["doc_id"]))])
    print("PTRs in index %d; read now %d; left %d" % (len(idx), n, left))
    return 0


def events():
    out = set()
    d = os.path.join(STORE, "rows")
    for name in os.listdir(d) if os.path.isdir(d) else []:
        if not name.endswith(".json"):
            continue
        with open(os.path.join(d, name)) as fh:
            rep = json.load(fh)
        for r in rep["rows"]:
            if r["type"] == "P" and r["ticker"] and not r["option"] and r["asset_type"] in (None, "ST"):
                out.add((rep["filed"], name[:-5], r["ticker"]))
    return sorted((f, doc, t) for f, doc, t in out)


def cmd_run(a):
    evs = events()
    spy = p5.prices("SPY")
    res = insiders.run_events([(f, doc, t) for f, doc, t in evs], spy, p5.rf_daily(), hold=HOLD, cost_bps=COST_BPS,
                              min_price=MIN_PRICE, split=SPLIT)
    res["purchase_events"] = len(evs)
    i, j = res["in_sample"], res["judged"]
    print("congress purchases: %d events | IS %d, %+.2f%%/event-month t %+.2f | judged %d, %+.2f%% t %+.2f | "
          "$500 -> $%.0f since 2022 (SPY $%.0f); all years $%.0f (SPY $%.0f) | dropped %s -> %s" % (
              len(evs), i["events"], i["mean_pct"], i["t"], j["events"], j["mean_pct"], j["t"], res["usd_judged"] or 0,
              res["spy_usd_judged"] or 0, res["usd_all"] or 0, res["spy_usd_all"] or 0, res["dropped"], res["verdict"]))
    if a.write:
        with open(a.write, "w") as fh:
            json.dump(res, fh, indent=1)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    f = sub.add_parser("fetch")
    f.add_argument("--max-docs", type=int, default=0)
    f.add_argument("--refresh-index", action="store_true")
    r = sub.add_parser("run")
    r.add_argument("--write", nargs="?", const=os.path.join(RESULTS, "congress.json"))
    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        return cmd_fetch(a)
    if a.cmd == "run":
        return cmd_run(a)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
