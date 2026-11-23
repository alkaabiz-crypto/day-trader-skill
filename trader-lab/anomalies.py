#!/usr/bin/env python3
"""trader-lab pre-registered published anomalies on the US index (one rule each, no tuning).

    python3 anomalies.py            # all five, SPY (Li & Yu on DIA, the Dow, as in the paper)
    python3 anomalies.py --json

Each is a single hypothesis fixed from its paper BEFORE looking at the data. Scored like the
searches: next-open fills, 2 bp per change, T-bill cash, Jensen's alpha against buy-and-hold
(beta before 2015), judged after 2014. Five hypotheses, so a PASS needs after-2014 t >= 3 (the
lab's Harvey-Liu-Zhu bar, stricter than Bonferroni over 5) and a positive in-sample t.

  dash_avoid   Etula, Rinne, Suominen & Vaittinen (2020, RFS 33(1)) "Dash for Cash": institutions
               sell to raise month-end cash on T-(settlement+1) trading days before month end,
               then prices revert. Rule: hold the index except from the close of T-(s+4) to the
               close of T-(s+1) (the selling days), where s is the settlement lag in force:
               3 days before 2017-09-05, 2 days to 2024-05-27, 1 day after.
  dash_revert  Same paper: long only from the close of the selling day T-(s+1) to the close of
               the 3rd trading day of the next month (the reversal), else T-bills.
  li_yu        Li & Yu (2012, JFE 104(2)): nearness to the 52-week high predicts the market up,
               nearness to the historical high predicts it down. Predictive regression of the next
               21 days' DIA excess return on both, fitted only on data up to 2014, rebalanced each
               month end: long when the fitted forecast is above 0, else T-bills.
  vix_spike    VIX at least 20% above its 10-day average (fear spike): long SPY for 5 days
               (short-term reversal after volatility spikes; Connors & Alvarez 2009 practitioner rule).
  hv_down      High-volume down day: SPY down with volume over 1.5x its 20-day average: long 5 days
               (Gervais, Kaniel & Mingelgrin 2001 high-volume return premium, applied to the index).
Research, not financial advice.
"""

import argparse
import datetime
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import universe_search as us  # noqa: E402
from sp500_search import aligned  # noqa: E402

COST = 2.0
SETTLE_CHANGES = [("2017-09-05", 2), ("2024-05-28", 1)]


def settle_lag(day):
    s = 3
    for d, v in SETTLE_CHANGES:
        if day >= d:
            s = v
    return s


def month_position(dates):
    """For each day: trading days to the month's last trading day (0 on it), and the trading-day
    number within the month (1 on the first)."""
    n = len(dates)
    to_end = np.zeros(n, int)
    k = 0
    for i in range(n - 1, -1, -1):
        last = i == n - 1 or dates[i + 1][:7] != dates[i][:7]
        k = 0 if last else k + 1
        to_end[i] = k
    num = np.zeros(n, int)
    for i in range(n):
        num[i] = 1 if i == 0 or dates[i][:7] != dates[i - 1][:7] else num[i - 1] + 1
    return to_end, num


def dash_positions(dates):
    """Positions decided at each close (1 = hold the index during the next session)."""
    to_end, num = month_position(dates)
    avoid = np.ones(len(dates))
    revert = np.zeros(len(dates))
    for i, d in enumerate(dates):
        s = settle_lag(d)
        sell = s + 1                                   # the selling day is T-(s+1)
        if sell + 1 <= to_end[i] <= sell + 3:          # out over the 3 sessions into the selling day
            avoid[i] = 0.0
        if to_end[i] <= sell or num[i] <= 2:           # in from the selling day's close to day 3's close
            revert[i] = 1.0
    return avoid, revert


def li_yu_positions(A, is_end):
    c = A["c"]
    x52 = c / us.rolling_max(c, 252)
    xmax = c / np.maximum.accumulate(c)
    fwd = np.full(len(c), np.nan)
    fwd[:-21] = c[21:] / c[:-21] - 1
    rf21 = np.convolve(A["rf"], np.ones(21), "full")[20:][:len(c)]
    y = fwd - rf21
    dates = np.array(A["d"])
    to_end, _ = month_position(A["d"])
    month_end = to_end == 0
    fit = month_end & (dates <= is_end) & np.isfinite(y) & np.isfinite(x52)
    # the last 21-day window must end by is_end too: drop fits whose forward window crosses it
    last_ok = np.zeros(len(c), bool)
    k = int(np.searchsorted(dates, is_end, side="right"))
    last_ok[:max(k - 21, 0)] = True
    fit &= last_ok
    X = np.column_stack([np.ones(fit.sum()), x52[fit], xmax[fit]])
    beta = np.linalg.lstsq(X, y[fit], rcond=None)[0]
    pos = np.zeros(len(c))
    cur = 0.0
    for i in range(len(c)):
        if month_end[i] and np.isfinite(x52[i]):
            cur = 1.0 if beta[0] + beta[1] * x52[i] + beta[2] * xmax[i] > 0 else 0.0
        pos[i] = cur
    return pos, beta


def score(A, pos, is_end):
    r = us.returns_for(A, pos, COST, 0.0)
    bh = us.returns_for(A, np.ones(len(r)), COST, 0.0)
    rf = A["rf"]
    x, bx = r - rf, bh - rf
    dates = np.array(A["d"])
    pre, post = (dates <= is_end) & (dates >= dates[0]), dates > is_end
    pre[:253] = False                                   # warm-up
    bi = bx[pre]
    xi = x[pre]
    beta = float(((xi - xi.mean()) * (bi - bi.mean())).sum() / (len(xi) - 1) / np.var(bi, ddof=1))
    e = x - beta * bx

    def t(v):
        return float(v.mean() / v.std(ddof=1) * math.sqrt(len(v)))

    xp = x[post]
    return {"is_t": t(e[pre]), "post_t": t(e[post]), "post_alpha_bp_day": float(e[post].mean() * 1e4),
            "beta": beta, "exposure": float(np.abs(pos).mean()),
            "post_sharpe": float(xp.mean() / xp.std() * math.sqrt(252)),
            "bh_post_sharpe": float(bx[post].mean() / bx[post].std() * math.sqrt(252)),
            "verdict": "PASS (needs audit)" if t(e[post]) >= 3 and t(e[pre]) > 0 else "fail"}


def run(is_end=us.IS_END):
    spy = us.load_asset("SPY")
    dia = us.load_asset("DIA")
    out = {}
    avoid, revert = dash_positions(spy["d"])
    out["dash_avoid"] = score(spy, avoid, is_end)
    out["dash_revert"] = score(spy, revert, is_end)
    pos, beta = li_yu_positions(dia, is_end)
    out["li_yu"] = score(dia, pos, is_end)
    out["li_yu"]["coefficients"] = [float(b) for b in beta]
    vix = aligned("^VIX", spy["d"])
    spike = vix >= 1.2 * us.sma(vix, 10)
    out["vix_spike"] = score(spy, us.hold_for(np.nan_to_num(spike.astype(float)) > 0, 5), is_end)
    v, c = spy["v"], spy["c"]
    hv = (np.diff(c, prepend=c[0]) < 0) & (v > 1.5 * us.sma(v, 20))
    out["hv_down"] = score(spy, us.hold_for(np.nan_to_num(hv.astype(float)) > 0, 5), is_end)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="pre-registered published anomalies")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    r = run()
    if a.json:
        print(json.dumps(r, indent=1))
        return 0
    print("Pre-registered anomalies (one rule each; Jensen's alpha vs buy-and-hold, judged after %s, 2 bp):" % us.IS_END)
    for k, v in r.items():
        print("  %-12s IS t %5.2f | after t %5.2f (%5.2f bp/day) | exposure %3.0f%% | Sharpe %.2f vs BH %.2f | %s" % (
            k, v["is_t"], v["post_t"], v["post_alpha_bp_day"], 100 * v["exposure"], v["post_sharpe"],
            v["bh_post_sharpe"], v["verdict"]))
    print("A PASS needs after-2014 t >= 3 and a positive in-sample t. Research, not financial advice.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
