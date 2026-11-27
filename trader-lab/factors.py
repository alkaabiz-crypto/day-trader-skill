#!/usr/bin/env python3
"""trader-lab: do the classic stock-market factor premia survive after they were published?

    python3 factors.py fetch          # Ken French's data library -> data/french (gitignored)
    python3 factors.py test [--json] [--write]

Why: every timing rule in this lab failed out of sample. The best-documented sources of return
beyond the market are the cross-sectional factors. McLean & Pontiff (2016, JF 71(1)) "Does
Academic Research Destroy Stock Return Predictability?" find that anomaly returns are about 26%
lower out of sample and 58% lower after publication. This file checks that on 100 years of
Kenneth French's factor returns (monthly, US stocks, CRSP), judged only on the years AFTER each
paper came out.

PRE-REGISTERED 2026-11-24, before any result in this file was run. Not to be changed after:
  factor  paper (sample)                                         judged from
  MKT     the equity premium, market minus T-bills (no paper)    whole sample, and 1990 on
  SMB     Banz (1981, JFE) size (1936-1975)                      1981-01
  HML     Rosenberg, Reid & Lanstein (1985) / Fama & French
          (1992, JF) value (1963-1990)                           1992-07
  UMD     Jegadeesh & Titman (1993, JF) momentum (1965-1989)     1993-03
  RMW     Novy-Marx (2013, JFE) profitability (1963-2010)        2013-04
  CMA     Titman, Wei & Xie (2004) / Fama & French (2015, JFE)
          investment (1963-2013)                                 2015-04
  Test: mean monthly return after publication, t with Newey-West (lag 6) errors. SURVIVES if the
  post-publication mean > 0 and t >= 2.0; also reported: the in-sample mean, the decay
  (1 - post / in-sample), Sharpe, the worst 12 months, and the last 10 years.
  Caveat stated before running: these are long-short paper portfolios, GROSS of trading costs,
  shorting fees and taxes. Novy-Marx & Velikov (2016, RFS) put momentum's costs at several % a
  year. A surviving factor is a reason to look at investable funds (factor_etfs.py), not a trade.
Research, not financial advice.
"""

import argparse
import io
import json
import math
import os
import sys
import urllib.request
import zipfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(HERE, "data", "french")
BASE = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
FILES = {"ff5": "F-F_Research_Data_5_Factors_2x3_CSV.zip", "ff3": "F-F_Research_Data_Factors_CSV.zip",
         "mom": "F-F_Momentum_Factor_CSV.zip"}
UA = "Mozilla/5.0 (compatible; research script)"
PAPERS = {
    "MKT": ("equity premium", None, None, "1990-01"),
    "SMB": ("Banz (1981)", "1936-01", "1975-12", "1981-01"),
    "HML": ("Fama & French (1992)", "1963-07", "1990-12", "1992-07"),
    "UMD": ("Jegadeesh & Titman (1993)", "1965-01", "1989-12", "1993-03"),
    "RMW": ("Novy-Marx (2013)", "1963-07", "2010-12", "2013-04"),
    "CMA": ("Fama & French (2015)", "1963-07", "2013-12", "2015-04"),
}


def fetch():
    os.makedirs(DIR, exist_ok=True)
    for key, name in FILES.items():
        req = urllib.request.Request(BASE + name, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            z = zipfile.ZipFile(io.BytesIO(r.read()))
        text = z.read(z.namelist()[0]).decode("latin1")
        with open(os.path.join(DIR, key + ".csv"), "w") as f:
            f.write(text)
        print("%s: %d lines" % (key, text.count("\n")))


def parse_monthly(text):
    """French CSV -> (columns, {yyyy-mm: [values in %]}). Only the first (monthly) block."""
    cols, rows, started = None, {}, False
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if cols is None:
            if len(parts) > 1 and parts[0] == "" and parts[1]:
                cols = parts[1:]
            continue
        if len(parts) == len(cols) + 1 and len(parts[0]) == 6 and parts[0].isdigit():
            rows["%s-%s" % (parts[0][:4], parts[0][4:])] = [float(x) for x in parts[1:]]
            started = True
        elif started:
            break
    return cols, rows


def load():
    out = {}
    for key in ("ff3", "ff5", "mom"):
        with open(os.path.join(DIR, key + ".csv")) as f:
            cols, rows = parse_monthly(f.read())
        for m, vals in rows.items():
            d = out.setdefault(m, {})
            for c, v in zip(cols, vals):
                name = {"Mkt-RF": "MKT", "Mom": "UMD"}.get(c, c)
                if name not in d or key == "ff5":       # 5-factor file wins where both exist
                    d[name] = v
    return out


def nw_t(x, lag=6):
    """t of the mean with Newey-West (Bartlett) standard errors."""
    x = np.asarray(x, float)
    n = len(x)
    e = x - x.mean()
    s = (e @ e) / n
    for k in range(1, lag + 1):
        s += 2 * (1 - k / (lag + 1)) * (e[k:] @ e[:-k]) / n
    return float(x.mean() / math.sqrt(s / n)) if s > 0 else 0.0


def stats(x):
    x = np.asarray(x, float)
    if len(x) < 24:
        return None
    roll = np.convolve(x, np.ones(12), "valid")
    return {"months": int(len(x)), "mean_pct": float(x.mean()), "t_nw": nw_t(x),
            "sharpe": float(x.mean() / x.std(ddof=1) * math.sqrt(12)), "worst_12m_pct": float(roll.min())}


def test(data):
    months = sorted(data)
    last10 = months[-120]
    res = {}
    for f, (paper, s0, s1, post) in PAPERS.items():
        def sl(a=None, b=None):
            return [data[m][f] for m in months if f in data[m] and (a is None or m >= a) and (b is None or m <= b)]
        r = {"paper": paper, "post_from": post, "whole": stats(sl()), "post": stats(sl(post)),
             "last10": stats(sl(last10)), "in_sample": stats(sl(s0, s1)) if s0 else None}
        p = r["post"]
        r["decay"] = (1 - p["mean_pct"] / r["in_sample"]["mean_pct"]) if r["in_sample"] and r["in_sample"]["mean_pct"] else None
        r["verdict"] = "SURVIVES" if p["mean_pct"] > 0 and p["t_nw"] >= 2.0 else "does not survive"
        res[f] = r
    return {"first": months[0], "last": months[-1], "factors": res}


def report(r):
    print("Factor premia, Ken French data %s to %s (monthly, %% a month, long-short, gross of costs):" % (r["first"], r["last"]))
    print("  factor  paper                       in-sample mean   after publication (from)        decay  last 10y     verdict")
    for f, x in r["factors"].items():
        i, p, l = x["in_sample"], x["post"], x["last10"]
        print("  %-6s  %-26s  %s  %+5.2f t %5.2f (%s, Sharpe %.2f)  %s  %+5.2f t %5.2f  %s" % (
            f, x["paper"], ("%+5.2f t %5.2f" % (i["mean_pct"], i["t_nw"])) if i else "      n/a     ",
            p["mean_pct"], p["t_nw"], x["post_from"], p["sharpe"],
            ("%4.0f%%" % (100 * x["decay"])) if x["decay"] is not None else "  n/a",
            l["mean_pct"], l["t_nw"], x["verdict"]))
    print("SURVIVES = after-publication mean > 0 with Newey-West t >= 2. Paper portfolios, before costs;"
          " see factor_etfs.py for what an investor can actually buy. Research, not financial advice.")


def main(argv=None):
    ap = argparse.ArgumentParser(description="factor premia before and after publication")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("fetch")
    t = sub.add_parser("test")
    t.add_argument("--json", action="store_true")
    t.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        fetch()
        return 0
    if a.cmd != "test":
        ap.print_help()
        return 1
    r = test(load())
    if a.write:
        with open(os.path.join(HERE, "results", "factors.json"), "w") as f:
            json.dump(r, f, indent=1)
    if a.json:
        print(json.dumps(r, indent=1))
    else:
        report(r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
