#!/usr/bin/env python3
"""trader-lab: can an investor buy a factor premium? Factor and style ETFs against SPY, after fees.

    python3 daily.py fetch --symbols MTUM,QUAL,USMV,VLUE,SPLV,IWD,IWF,IWN,IJS,AVUV,EFA,VWO,VT,QQQ,IWM
    python3 factor_etfs.py [--json] [--write]

Why: factors.py asks whether the paper premia survived publication. This asks the question that
matters for the monthly plan: did the funds that sell those premia beat simply holding the S&P 500
(SPY), after their fees, trading costs and taxes inside the fund? ETF prices are net of the fund's
expense ratio; dividends are reinvested (adjusted closes).

PRE-REGISTERED 2026-11-24, before any result in this file was run. Not to be changed after:
  Funds: momentum MTUM, quality QUAL, minimum volatility USMV and SPLV, value VLUE and IWD,
  growth IWF, small value IWN, IJS and AVUV, and as diversifiers developed ex-US EFA, emerging VWO,
  world VT, Nasdaq 100 QQQ and small caps IWM. 15 funds.
  Monthly returns (month-end adjusted closes), from each fund's first full month to 2026-10.
  Regression on SPY: excess return = alpha + beta x SPY excess return (T-bill = ^IRX).
  ADDS ALPHA if alpha > 0 with Newey-West (lag 6) t >= 2.94 (5% two-sided, Bonferroni over 15).
  Also reported: yearly return and Sharpe for the fund and for SPY over the same months, the
  deepest drawdown of each, and alpha since 2015 alone.
Research, not financial advice.
"""

import argparse
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import factors  # noqa: E402
import universe_search as us  # noqa: E402

FUNDS = {"MTUM": "momentum", "QUAL": "quality", "USMV": "min volatility", "SPLV": "low volatility",
         "VLUE": "value (MSCI)", "IWD": "large value", "IWF": "large growth", "IWN": "small value",
         "IJS": "small value (S&P)", "AVUV": "small value (Avantis)", "EFA": "developed ex-US",
         "VWO": "emerging markets", "VT": "whole world", "QQQ": "Nasdaq 100", "IWM": "small caps"}
LAST_MONTH = "2026-10"
BONF_T = 2.94


def monthly(A):
    """{yyyy-mm: (total return, T-bill return)} from month-end closes; the first month dropped."""
    d, c, rf = A["d"], A["c"], A["rf"]
    ends = [i for i in range(len(d)) if i == len(d) - 1 or d[i + 1][:7] != d[i][:7]]
    out = {}
    for a, b in zip(ends[:-1], ends[1:]):
        out[d[b][:7]] = (c[b] / c[a] - 1, float(np.sum(rf[a + 1:b + 1])))
    return out


def drawdown(r):
    eq = np.cumprod(1 + np.asarray(r))
    return float((1 - eq / np.maximum.accumulate(eq)).max())


def compare(fund, spy, start=None):
    months = sorted(m for m in fund if m in spy and m <= LAST_MONTH and (start is None or m >= start))
    if len(months) < 36:
        return None
    f = np.array([fund[m][0] for m in months])
    s = np.array([spy[m][0] for m in months])
    rf = np.array([spy[m][1] for m in months])
    y, x = f - rf, s - rf
    beta = float(np.cov(y, x, ddof=1)[0, 1] / np.var(x, ddof=1))
    e = y - beta * x                                    # alpha + noise each month
    alpha = float(e.mean())
    n = len(months)

    def cagr(r):
        return float(np.prod(1 + r) ** (12.0 / n) - 1)

    def sharpe(r):
        z = r - rf
        return float(z.mean() / z.std(ddof=1) * math.sqrt(12))
    return {"from": months[0], "to": months[-1], "months": n, "beta": beta,
            "alpha_pct_year": alpha * 1200, "alpha_t": factors.nw_t(e),
            "cagr": cagr(f), "spy_cagr": cagr(s), "sharpe": sharpe(f), "spy_sharpe": sharpe(s),
            "max_dd": drawdown(f), "spy_max_dd": drawdown(s)}


def run():
    spy = monthly(us.load_asset("SPY"))
    out = {}
    for sym, label in FUNDS.items():
        try:
            m = monthly(us.load_asset(sym))
        except SystemExit:
            out[sym] = {"label": label, "error": "no data"}
            continue
        r = compare(m, spy)
        r["label"] = label
        r["since_2015"] = compare(m, spy, "2015-01")
        r["verdict"] = "ADDS ALPHA" if r["alpha_pct_year"] > 0 and r["alpha_t"] >= BONF_T else "no"
        out[sym] = r
    return out


def report(out):
    print("Factor and style ETFs vs SPY, monthly, after fund fees, dividends reinvested (to %s):" % LAST_MONTH)
    print("  fund  what                    from      beta  alpha/yr (t)     since 2015 (t)   yearly vs SPY    Sharpe vs SPY  worst drop vs SPY  verdict")
    for sym, r in out.items():
        if "error" in r:
            print("  %-5s %-22s no data" % (sym, r["label"]))
            continue
        s = r["since_2015"]
        print("  %-5s %-22s %s  %4.2f  %+5.1f%% (%5.2f)  %s  %5.1f%% / %5.1f%%  %5.2f / %5.2f   %3.0f%% / %3.0f%%      %s" % (
            sym, r["label"], r["from"], r["beta"], r["alpha_pct_year"], r["alpha_t"],
            ("%+5.1f%% (%5.2f)" % (s["alpha_pct_year"], s["alpha_t"])) if s else "      n/a      ",
            100 * r["cagr"], 100 * r["spy_cagr"], r["sharpe"], r["spy_sharpe"],
            100 * r["max_dd"], 100 * r["spy_max_dd"], r["verdict"]))
    print("ADDS ALPHA = alpha > 0 with Newey-West t >= %.2f (Bonferroni over %d funds). Research, not financial advice."
          % (BONF_T, len(FUNDS)))


def main(argv=None):
    ap = argparse.ArgumentParser(description="factor and style ETFs vs SPY")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    out = run()
    if a.write:
        with open(os.path.join(HERE, "results", "factor-etfs.json"), "w") as f:
            json.dump(out, f, indent=1)
    if a.json:
        print(json.dumps(out, indent=1))
    else:
        report(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
