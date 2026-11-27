#!/usr/bin/env python3
"""Copying clusters of insider buying, backtested on a $500 account. Pre-registered.

    python3 insiders.py fetch [--max-quarters N]   # SEC insider-transaction data sets -> data/insiders (gitignored)
    python3 insiders.py run [--write]              # -> results/insiders.json

Sources: Lakonishok & Lee (2001, RFS 14(1)) "Are insider trades informative?"; Cohen, Malloy & Pomorski (2012,
JF 67(3)) "Decoding inside information". Open-market purchases by several insiders of the same company have been
followed by above-market returns.

PRE-REGISTERED 2026-11-24, committed before any data was downloaded. Not to be changed:
  Data: the SEC's quarterly "Insider Transactions Data Sets" (Forms 3/4/5 as filed), 2014 Q1 to the latest quarter
    published. Only original Form 4 filings (DOCUMENT_TYPE "4"). A purchase is a non-derivative row with
    transaction code P, acquired (A), shares > 0 and price > 0; value = shares x price.
  Event: an issuer on filing date F where purchases filed in the 30 days ending F come from at least 3 different
    reporting owners and total at least $100,000. Only the first F per issuer, then none for 90 days.
  Trade: buy at the close of the first trading day after F (filings can come after the close), hold 21 trading
    days, sell at the close. The entry price must be at least $2. The ticker is the filing's issuer symbol; an event
    whose ticker Yahoo doesn't serve is dropped (so delisted companies are missing: a survivor bias that flatters
    the result, to be kept in mind if it passes). Cost 20 bps a round trip.
  Statistic: each event's return minus SPY's over the same 21 days, net of cost; averaged per entry month.
    In-sample: entries 2014-2019. Judged: entries from 2020. PASS only if judged t >= 3 and in-sample t > 0.
  Reported: what $500 became, holding every open position in equal weight each day and T-bills when none is
    open, next to $500 in SPY, for the judged period and all years.
Research, not financial advice.
"""

import argparse
import csv
import datetime
import gzip
import io
import json
import os
import statistics
import sys
import time
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import paper500 as p5  # noqa: E402

STORE = os.path.join(HERE, "data", "insiders")
RESULTS = os.path.join(HERE, "results")
URL = "https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/%dq%d_form345.zip"
FIRST_Q = (2014, 1)
MIN_OWNERS, MIN_VALUE, WINDOW_DAYS, QUIET_DAYS = 3, 100000.0, 30, 90
HOLD, COST_BPS, MIN_PRICE = 21, 20.0, 2.0
SPLIT, T_BAR = "2020-01-01", 3.0
MON = {m: i + 1 for i, m in enumerate("JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split())}


def sec_date(s):
    """'31-MAR-2023' -> '2023-03-31' (the data sets' format); ISO passes through."""
    s = (s or "").strip()
    if len(s) == 11 and s[2] == "-":
        return "%s-%02d-%s" % (s[7:], MON[s[3:6].upper()], s[:2])
    return s[:10]


def quarters():
    y, q = FIRST_Q
    today = datetime.date.today()
    while (y, q) <= (today.year, (today.month - 1) // 3 + 1):
        yield y, q
        q += 1
        if q == 5:
            y, q = y + 1, 1


def reduce_zip(data):
    """Purchase rows [filed, issuer_cik, symbol, owner_cik, value] from one quarter's zip."""
    z = zipfile.ZipFile(io.BytesIO(data))
    names = {n.split("/")[-1].upper(): n for n in z.namelist()}

    def rows(name):
        with z.open(names[name]) as fh:
            yield from csv.DictReader(io.TextIOWrapper(fh, "utf-8", errors="replace"), delimiter="\t")

    sub = {}
    for r in rows("SUBMISSION.TSV"):
        if (r.get("DOCUMENT_TYPE") or "").strip() == "4":
            sub[r["ACCESSION_NUMBER"]] = (sec_date(r["FILING_DATE"]), r["ISSUERCIK"].strip(),
                                          (r.get("ISSUERTRADINGSYMBOL") or "").strip().upper())
    owner = {}
    for r in rows("REPORTINGOWNER.TSV"):
        owner.setdefault(r["ACCESSION_NUMBER"], r["RPTOWNERCIK"].strip())
    out = []
    for r in rows("NONDERIV_TRANS.TSV"):
        acc = r["ACCESSION_NUMBER"]
        if acc not in sub or (r.get("TRANS_CODE") or "").strip() != "P":
            continue
        if (r.get("TRANS_ACQUIRED_DISP_CD") or "").strip() != "A":
            continue
        try:
            sh, px = float(r["TRANS_SHARES"]), float(r["TRANS_PRICEPERSHARE"])
        except (TypeError, ValueError):
            continue
        if sh <= 0 or px <= 0:
            continue
        f, cik, sym = sub[acc]
        out.append([f, cik, sym, owner.get(acc, acc), sh * px])
    return out


def cmd_fetch(a):
    ua = os.environ.get("SEC_USER_AGENT", "").strip()
    if not ua:
        print("SEC_USER_AGENT is not set in this environment: the SEC refuses requests without a contact")
        return 1
    os.makedirs(STORE, exist_ok=True)
    done = 0
    for y, q in quarters():
        path = os.path.join(STORE, "%dq%d.json.gz" % (y, q))
        if os.path.exists(path):
            continue
        if a.max_quarters and done >= a.max_quarters:
            break
        req = urllib.request.Request(URL % (y, q), headers={"User-Agent": ua})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = r.read()
        except urllib.error.HTTPError as e:
            print("%dq%d: HTTP %d (not published yet?)" % (y, q, e.code))
            if e.code == 404:
                continue
            return 1
        rows = reduce_zip(data)
        with gzip.open(path + ".tmp", "wt") as fh:
            json.dump(rows, fh)
        os.replace(path + ".tmp", path)
        print("%dq%d: %d purchase rows" % (y, q, len(rows)), flush=True)
        done += 1
        time.sleep(1.0)
    return 0


def load_rows():
    out = []
    for name in sorted(os.listdir(STORE)) if os.path.isdir(STORE) else []:
        if name.endswith(".json.gz"):
            with gzip.open(os.path.join(STORE, name), "rt") as fh:
                out += json.load(fh)
    return out


def events(rows):
    """[(filed, cik, symbol)] cluster events by the pre-registered rule."""
    by = {}
    for f, cik, sym, own, val in rows:
        by.setdefault(cik, []).append((f, sym, own, val))
    out = []
    for cik, rs in by.items():
        rs.sort()
        last = None
        dates = sorted({r[0] for r in rs})
        for F in dates:
            if last and (datetime.date.fromisoformat(F) - datetime.date.fromisoformat(last)).days < QUIET_DAYS:
                continue
            lo = (datetime.date.fromisoformat(F) - datetime.timedelta(days=WINDOW_DAYS - 1)).isoformat()
            win = [r for r in rs if lo <= r[0] <= F]
            owners = {r[2] for r in win}
            if len(owners) >= MIN_OWNERS and sum(r[3] for r in win) >= MIN_VALUE:
                sym = next((r[1] for r in reversed(win) if r[1]), "")
                out.append((F, cik, sym))
                last = F
    return sorted(out)


def run_events(evs, spy, rf, hold=HOLD, cost_bps=COST_BPS, min_price=MIN_PRICE, split=SPLIT, get=p5.prices):
    spy_i = {d: i for i, d in enumerate(spy["d"])}
    obs, positions, dropped = [], [], {"no_ticker": 0, "no_prices": 0, "too_cheap": 0, "too_recent": 0}
    for F, cik, sym in evs:
        if not sym or not sym.replace(".", "").replace("-", "").isalnum():
            dropped["no_ticker"] += 1
            continue
        b = get(sym.replace(".", "-"))
        if not b or not b.get("d"):
            dropped["no_prices"] += 1
            continue
        i = p5.first_after(b["d"], F)
        if i is None or i + hold >= len(b["d"]):
            dropped["too_recent"] += 1
            continue
        if (b["c"][i] or 0) < min_price:
            dropped["too_cheap"] += 1
            continue
        d0, d1 = b["d"][i], b["d"][i + hold]
        if d0 not in spy_i or d1 not in spy_i:
            dropped["too_recent"] += 1
            continue
        r = b["a"][i + hold] / b["a"][i] - 1.0
        rs = spy["a"][spy_i[d1]] / spy["a"][spy_i[d0]] - 1.0
        obs.append((d0, r - rs - cost_bps / 1e4))
        positions.append({"entry": d0, "exit": d1, "rets": p5.window_returns(b, i, hold), "cost": cost_bps / 1e4})
    m_in = p5.monthly([o for o in obs if o[0] < split])
    m_j = p5.monthly([o for o in obs if o[0] >= split])
    f = lambda m, n: {"events": n, "months": len(m), "mean_pct": 100 * statistics.mean(m) if m else 0.0,  # noqa: E731
                      "t": p5.tstat(m)}
    res = {"in_sample": f(m_in, sum(o[0] < split for o in obs)), "judged": f(m_j, sum(o[0] >= split for o in obs)),
           "dropped": dropped}
    days = [d for d in spy["d"] if d > (min(o[0] for o in obs) if obs else "9999")]
    path = p5.account(days, positions, rf)
    bh, v = [], p5.START
    for k in range(1, len(spy["d"])):
        d = spy["d"][k]
        if days and d >= days[0]:          # SPY bought and held from the account's first day, not from 1993
            v *= spy["a"][k] / spy["a"][k - 1]
            bh.append((d, v))
    res["usd_judged"], res["usd_all"] = p5.dollars(path, split), p5.dollars(path)
    res["spy_usd_judged"], res["spy_usd_all"] = p5.dollars(bh, split), p5.dollars(bh)
    res["first"], res["last"] = (days[0], days[-1]) if days else (None, None)
    res["verdict"] = "PASS" if (res["judged"]["t"] >= T_BAR and res["in_sample"]["t"] > 0) else "FAIL"
    return res


def cmd_run(a):
    rows = load_rows()
    evs = events(rows)
    spy = p5.prices("SPY")
    res = run_events(evs, spy, p5.rf_daily())
    res["purchase_rows"], res["cluster_events"] = len(rows), len(evs)
    i, j = res["in_sample"], res["judged"]
    print("insider clusters: %d events from %d purchases | IS %d events, %+.2f%%/event-month t %+.2f | judged %d events, "
          "%+.2f%% t %+.2f | $500 -> $%.0f since 2020 (SPY $%.0f); all years $%.0f (SPY $%.0f) | dropped %s -> %s" % (
              len(evs), len(rows), i["events"], i["mean_pct"], i["t"], j["events"], j["mean_pct"], j["t"],
              res["usd_judged"] or 0, res["spy_usd_judged"] or 0, res["usd_all"] or 0, res["spy_usd_all"] or 0,
              res["dropped"], res["verdict"]))
    if a.write:
        with open(a.write, "w") as fh:
            json.dump(res, fh, indent=1)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    f = sub.add_parser("fetch")
    f.add_argument("--max-quarters", type=int, default=0)
    r = sub.add_parser("run")
    r.add_argument("--write", nargs="?", const=os.path.join(RESULTS, "insiders.json"))
    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        return cmd_fetch(a)
    if a.cmd == "run":
        return cmd_run(a)
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
