#!/usr/bin/env python3
"""Monthly allocation rules: trend, momentum and volatility targeting (weeks-to-months holds).

    python3 alloc.py fetch            # dividend-adjusted daily closes from Yahoo into data/alloc (gitignored)
    python3 alloc.py test [--write]   # every rule, IS / OOS / HOLDOUT, gates, placebo

Why: 30 years of daily bars and 4 years of 5-minute bars found no day-trading rule that beats
costs. The rules with the best published record AFTER publication are slower: trend following
and momentum across assets (Faber 2007; Moskowitz, Ooi & Pedersen 2012; Antonacci 2014;
Hurst, Ooi & Pedersen 2017, "A Century of Evidence on Trend-Following") and volatility-managed
exposure (Moreira & Muir 2017). The claim is not more return than the market, but a better
return per unit of risk and much smaller crashes. This file tests that claim honestly.

PRE-REGISTERED 2026-11-23, before any result was seen. Not to be changed after the first run:

  Data: Yahoo adjusted closes (splits AND dividends). Cash earns the 13-week T-bill (^IRX);
  borrowing above 100% costs T-bill + 1%. Signals use month-end closes; trades happen at the
  close of the NEXT trading day (one day of delay; nobody trades the month-end close they used).
  Cost: 10 bps per unit of turnover (each side); every result is also re-run at 20 bps.

  Part A, SPY alone (data from 1993). IS to 2009-12, OOS 2010-01 to 2017-12, HOLDOUT 2018-01 on.
    A1 sma     hold SPY when its month-end close > its N-month average, else cash. N in 6, 8, 10, 12.
    A2 absmom  hold SPY when its L-month total return beats cash's, else cash. L in 6, 9, 12.
    A3 volman  weight = c / (variance of the last 21 daily returns), c set so the average weight up
               to that month is 1 (expanding, no look-ahead); capped at 1.0, 1.5 or 2.0.
    Benchmark: SPY buy-and-hold.
  Part B, nine ETFs: SPY IWM EFA EEM IEF TLT GLD VNQ DBC (DBC limits the start to 2006).
    IS to 2014-12, OOS 2015-01 to 2020-12, HOLDOUT 2021-01 on.
    B1 gtaa    Faber: SPY EFA IEF VNQ DBC, 1/5 each, held only when above its N-month average,
               else that fifth in cash. N in 10, 12.
    B2 gem     Antonacci dual momentum: if SPY's L-month return beats cash's, hold whichever of
               SPY / EFA did better over L months; else hold IEF. L in 6, 12.
    B3 topk    rank the nine by the average of their 1, 3, 6 and 12-month returns; hold the top K
               equally, each only if its 12-month return beats cash's (else that slot in cash).
               K in 2, 3, 4.
    Benchmark: 60/40 SPY/IEF rebalanced monthly (SPY buy-and-hold is reported too).

  Variant choice: the best IS Sharpe (excess over cash, monthly, annualized). Nothing else.
  PASS (better risk-adjusted return, the real prize). After IS, at 10 AND at 20 bps:
    * Sharpe above the benchmark's in OOS and in HOLDOUT separately;
    * stationary-bootstrap p < 0.05 / 6 (Bonferroni over the 6 rules) that the post-IS Sharpe
      difference over the benchmark is > 0 (paired monthly returns, mean block 6, 2,000 draws);
    * time-shift placebo p < 0.05: the same position series circularly shifted against the
      returns (keeps time in market and switch pattern) beats the real post-IS Sharpe < 5% of
      the time.
  RISK-REDUCER (weaker, stated as such). After IS, at 20 bps: max drawdown <= 0.6 x the
    benchmark's, Sharpe >= 0.9 x the benchmark's in OOS and in HOLDOUT, and placebo p < 0.05.
  Anything else: FAIL.
Caveats up front: ETFs that closed are missing from Yahoo; taxes are ignored (monthly switching
realizes gains); 1993-2009 is one history with two crashes. Research, not financial advice.
"""

import argparse
import bisect
import datetime
import gzip
import json
import math
import os
import random
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import daily  # noqa: E402  (Yahoo fetch only)

STORE = os.path.join(HERE, "data", "alloc")
RESULTS = os.path.join(HERE, "results")
PART_A = ["SPY"]
PART_B = ["SPY", "IWM", "EFA", "EEM", "IEF", "TLT", "GLD", "VNQ", "DBC"]
GTAA = ["SPY", "EFA", "IEF", "VNQ", "DBC"]
CASH = "^IRX"
SPLITS = {"A": ("2009-12-31", "2017-12-31"), "B": ("2014-12-31", "2020-12-31")}
COSTS = (10.0, 20.0)
N_RULES = 6
BOOT_DRAWS = 2000
BOOT_BLOCK = 6
BORROW_SPREAD = 0.01


# ---------------------------------------------------------------- data

def parse_adj(text):
    """Yahoo chart JSON -> {"d": [dates], "c": [adjusted closes]} (dividends and splits)."""
    res = ((json.loads(text).get("chart") or {}).get("result") or [None])[0]
    if not res:
        raise daily.LabError("no data")
    ind = res.get("indicators") or {}
    adj = ((ind.get("adjclose") or [{}])[0]).get("adjclose")
    raw = ((ind.get("quote") or [{}])[0]).get("close")
    col = adj if adj and any(x is not None for x in adj) else raw
    off = (res.get("meta") or {}).get("gmtoffset", -18000) or -18000
    out = {"d": [], "c": []}
    seen = set()
    for ts, x in zip(res.get("timestamp") or [], col or []):
        if ts is None or x is None or x <= 0:
            continue
        d = (datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=int(ts) + off)).date().isoformat()
        if d in seen:
            continue
        seen.add(d)
        out["d"].append(d)
        out["c"].append(float(x))
    return out


def path(sym):
    return os.path.join(STORE, "%s.json.gz" % sym.replace("^", "_"))


def load(sym):
    p = path(sym)
    if not os.path.exists(p):
        return None
    with gzip.open(p, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def cmd_fetch(a):
    os.makedirs(STORE, exist_ok=True)
    for s in sorted(set(PART_A + PART_B + [CASH])):
        D = parse_adj(daily.fetch_daily(s))
        tmp = path(s) + ".tmp"
        with gzip.GzipFile(tmp, "wb", mtime=0) as gz:
            gz.write(json.dumps(D, separators=(",", ":")).encode("utf-8"))
        os.replace(tmp, path(s))
        print("%-5s %5d days %s to %s" % (s, len(D["d"]), D["d"][0], D["d"][-1]))
        time.sleep(daily.PAUSE)
    return 0


# ---------------------------------------------------------------- calendar and returns

def month_ends(dates):
    """Indexes of the last trading day of each month."""
    return [i for i in range(len(dates)) if i + 1 == len(dates) or dates[i + 1][:7] != dates[i][:7]]


def value_on(D, date):
    """Close on `date` or the last day before it (None before the series starts)."""
    k = bisect.bisect_right(D["d"], date) - 1
    return D["c"][k] if k >= 0 else None


class Panel:
    """Month-end signal dates and the next-day trade dates on SPY's calendar, plus helpers."""

    def __init__(self, data, cash):
        self.data, self.cash = data, cash
        cal = data["SPY"]["d"]
        me = month_ends(cal)
        self.sig = [cal[i] for i in me if i + 1 < len(cal)]
        self.trade = [cal[i + 1] for i in me if i + 1 < len(cal)]

    def px(self, sym, date):
        return value_on(self.data[sym], date)

    def ret(self, sym, d0, d1):
        a, b = self.px(sym, d0), self.px(sym, d1)
        return (b / a - 1) if (a and b) else None

    def cash_ret(self, d0, d1):
        """T-bill return between two dates, from ^IRX (annual %, discount basis, ~ simple)."""
        y = value_on(self.cash, d0)
        days = (datetime.date.fromisoformat(d1) - datetime.date.fromisoformat(d0)).days
        return (y or 0.0) / 100.0 * days / 360.0

    def cash_ret_months(self, k, L):
        """Cash total return over the L months ending at signal date k."""
        if k - L < 0:
            return None
        g = 1.0
        for j in range(k - L, k):
            g *= 1 + self.cash_ret(self.sig[j], self.sig[j + 1])
        return g - 1

    def mret(self, sym, k, L):
        """Total return over the L months ending at signal date k (None if not enough data)."""
        if k - L < 0:
            return None
        return self.ret(sym, self.sig[k - L], self.sig[k])

    def sma_above(self, sym, k, n):
        if k - n + 1 < 0:
            return None
        xs = [self.px(sym, self.sig[j]) for j in range(k - n + 1, k + 1)]
        if None in xs:
            return None
        return xs[-1] > sum(xs) / n

    def daily_var(self, sym, date, n=21):
        D = self.data[sym]
        k = bisect.bisect_right(D["d"], date) - 1
        if k - n < 0:
            return None
        rs = [D["c"][j] / D["c"][j - 1] - 1 for j in range(k - n + 1, k + 1)]
        return statistics.pvariance(rs) if len(rs) > 1 else None


# ---------------------------------------------------------------- rules: weights decided at signal k

def w_sma(P, k, p):
    a = P.sma_above("SPY", k, p["n"])
    return None if a is None else {"SPY": 1.0 if a else 0.0}


def w_absmom(P, k, p):
    r, c = P.mret("SPY", k, p["l"]), P.cash_ret_months(k, p["l"])
    return None if r is None or c is None else {"SPY": 1.0 if r > c else 0.0}


def w_volman(P, k, p, _hist={}):
    """Moreira & Muir: c / sigma^2, c fixed so the expanding mean weight (uncapped) is 1."""
    v = P.daily_var("SPY", P.sig[k])
    if not v:
        return None
    key = (id(P), p["cap"])
    inv = _hist.setdefault(key, [])
    inv.append(1.0 / v)
    if len(inv) < 12:
        return None
    c = 1.0 / (sum(inv) / len(inv))
    return {"SPY": min(p["cap"], c / v)}


def w_gtaa(P, k, p):
    w = {}
    for s in GTAA:
        a = P.sma_above(s, k, p["n"])
        if a is None:
            return None
        if a:
            w[s] = 1.0 / len(GTAA)
    return w


def w_gem(P, k, p):
    rs, re, c = P.mret("SPY", k, p["l"]), P.mret("EFA", k, p["l"]), P.cash_ret_months(k, p["l"])
    if None in (rs, re, c) or P.px("IEF", P.sig[k]) is None:
        return None
    if rs > c:
        return {"SPY": 1.0} if rs >= re else {"EFA": 1.0}
    return {"IEF": 1.0}


def w_topk(P, k, p):
    c12 = P.cash_ret_months(k, 12)
    score = {}
    for s in PART_B:
        rr = [P.mret(s, k, L) for L in (1, 3, 6, 12)]
        if None in rr or c12 is None:
            return None
        score[s] = (sum(rr) / 4.0, rr[3])
    top = sorted(PART_B, key=lambda s: -score[s][0])[:p["k"]]
    return {s: 1.0 / p["k"] for s in top if score[s][1] > c12}


def w_bh(P, k, p):
    return {"SPY": 1.0} if P.px("SPY", P.sig[k]) else None


def w_6040(P, k, p):
    return {"SPY": 0.6, "IEF": 0.4} if P.px("IEF", P.sig[k]) else None


RULES = {
    "sma": ("A", w_sma, [{"n": n} for n in (6, 8, 10, 12)], "Faber 2007: 10-month SMA timing"),
    "absmom": ("A", w_absmom, [{"l": l} for l in (6, 9, 12)], "Antonacci 2014; Moskowitz et al. 2012"),
    "volman": ("A", w_volman, [{"cap": c} for c in (1.0, 1.5, 2.0)], "Moreira & Muir 2017, JF"),
    "gtaa": ("B", w_gtaa, [{"n": n} for n in (10, 12)], "Faber 2007 GTAA, 5 assets"),
    "gem": ("B", w_gem, [{"l": l} for l in (6, 12)], "Antonacci 2014 dual momentum"),
    "topk": ("B", w_topk, [{"k": k} for k in (2, 3, 4)], "cross-asset momentum, top K of 9"),
}


# ---------------------------------------------------------------- simulation

def simulate(P, fn, p, cost_bps, start_k=0):
    """Monthly returns. Weights decided at signal k are traded at trade[k] and held to trade[k+1].
    Returns [(trade date, strategy return, cash return, weights)]."""
    out, prev = [], {}
    for k in range(start_k, len(P.sig) - 1):
        w = fn(P, k, p)
        if w is None:
            prev = {}
            continue
        d0, d1 = P.trade[k], P.trade[k + 1]
        cr = P.cash_ret(d0, d1)
        r, gross = 0.0, sum(w.values())
        for s, x in w.items():
            rs = P.ret(s, d0, d1)
            if rs is None:
                break
            r += x * rs
        else:
            r += (1 - gross) * cr if gross <= 1 else -(gross - 1) * (cr + BORROW_SPREAD * (
                (datetime.date.fromisoformat(d1) - datetime.date.fromisoformat(d0)).days / 365.0))
            turn = sum(abs(w.get(s, 0) - prev.get(s, 0)) for s in set(w) | set(prev))
            r -= turn * cost_bps / 1e4
            out.append((d0, r, cr, w))
            prev = w
            continue
        prev = {}
    return out


def stats(rows):
    if len(rows) < 12:
        return {"n": len(rows), "sharpe": float("nan"), "cagr": float("nan"), "mdd": float("nan"),
                "vol": float("nan"), "invested": float("nan")}
    ex = [r - c for _, r, c, _ in rows]
    sd = statistics.pstdev(ex)
    g, peak, mdd = 1.0, 1.0, 0.0
    for _, r, _, _ in rows:
        g *= 1 + r
        peak = max(peak, g)
        mdd = min(mdd, g / peak - 1)
    years = len(rows) / 12.0
    return {"n": len(rows), "sharpe": (statistics.mean(ex) / sd * math.sqrt(12)) if sd > 0 else float("nan"),
            "cagr": g ** (1 / years) - 1, "mdd": mdd, "vol": statistics.pstdev([r for _, r, _, _ in rows]) * math.sqrt(12),
            "invested": statistics.mean(sum(w.values()) for _, _, _, w in rows)}


def sharpe_of(ex):
    sd = statistics.pstdev(ex) if len(ex) > 1 else 0
    return statistics.mean(ex) / sd * math.sqrt(12) if sd > 0 else 0.0


def boot_p(ex_s, ex_b, draws=BOOT_DRAWS, block=BOOT_BLOCK, seed=7):
    """Stationary bootstrap (Politis & Romano 1994) of paired monthly excess returns: the share of
    draws in which the strategy's Sharpe does NOT beat the benchmark's (one-sided p)."""
    rnd = random.Random(seed)
    n = len(ex_s)
    if n < 24:
        return float("nan")
    bad = 0
    for _ in range(draws):
        idx, i = [], rnd.randrange(n)
        while len(idx) < n:
            idx.append(i)
            i = rnd.randrange(n) if rnd.random() < 1.0 / block else (i + 1) % n
        if sharpe_of([ex_s[j] for j in idx]) - sharpe_of([ex_b[j] for j in idx]) <= 0:
            bad += 1
    return bad / draws


def shift_placebo_p(P, rows, cost_bps):
    """Every circular shift of the strategy's weight series against the same months' returns:
    the share that reach the real Sharpe. Keeps time in market, leverage and switch pattern."""
    n = len(rows)
    if n < 24:
        return float("nan")
    W = [w for _, _, _, w in rows]
    D = [d for d, _, _, _ in rows]
    nxt = {P.trade[k]: P.trade[k + 1] for k in range(len(P.trade) - 1)}
    rets = [{s: P.ret(s, d, nxt[d]) for s in set().union(*W)} for d in D]
    cash = [c for _, _, c, _ in rows]
    real = sharpe_of([r - c for _, r, c, _ in rows])
    hits = 0
    for sh in range(1, n):
        ex, prev = [], {}
        for i in range(n):
            w = W[(i + sh) % n]
            r = sum(x * (rets[i].get(s) or 0) for s, x in w.items())
            g = sum(w.values())
            r += (1 - g) * cash[i] if g <= 1 else -(g - 1) * (cash[i] + BORROW_SPREAD / 12)
            r -= sum(abs(w.get(s, 0) - prev.get(s, 0)) for s in set(w) | set(prev)) * cost_bps / 1e4
            prev = w
            ex.append(r - cash[i])
        if sharpe_of(ex) >= real:
            hits += 1
    return hits / (n - 1)


def split(rows, part):
    is_end, oos_end = SPLITS[part]
    return ([x for x in rows if x[0] <= is_end],
            [x for x in rows if is_end < x[0] <= oos_end],
            [x for x in rows if x[0] > oos_end],
            [x for x in rows if x[0] > is_end])


def evaluate(P, write=None):
    report = {"run": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "rules": {}}
    lines = []
    for part in ("A", "B"):
        # the common start: the first month every rule of this part (and its benchmark) can trade
        names = [n for n, r in RULES.items() if r[0] == part]
        bench_fn = w_bh if part == "A" else w_6040
        for name in names:
            _, fn, grid, src = RULES[name]
            best = None
            for p in grid:
                rows = simulate(P, fn, p, COSTS[0])
                is_, _, _, _ = split(rows, part)
                s = stats(is_)
                if best is None or (s["sharpe"] == s["sharpe"] and s["sharpe"] > best[1]["sharpe"]):
                    best = (p, s, rows)
            p, s_is, _ = best
            res = {"source": src, "part": part, "params": p, "is": s_is}
            verdict = {}
            for cost in COSTS:
                rows = simulate(P, fn, p, cost)
                first = rows[0][0] if rows else "9999"
                brows = [x for x in simulate(P, bench_fn, {}, cost) if x[0] >= first]
                spy = [x for x in simulate(P, w_bh, {}, cost) if x[0] >= first]
                _, oos, hold, post = split(rows, part)
                _, b_oos, b_hold, b_post = split(brows, part)
                _, _, _, s_post = split(spy, part)
                bdates = {x[0]: x for x in b_post}
                pair = [(x, bdates[x[0]]) for x in post if x[0] in bdates]
                ex_s = [x[1] - x[2] for x, _ in pair]
                ex_b = [y[1] - y[2] for _, y in pair]
                r = {"oos": stats(oos), "holdout": stats(hold), "post": stats(post),
                     "bench_oos": stats(b_oos), "bench_holdout": stats(b_hold), "bench_post": stats(b_post),
                     "spy_post": stats(s_post), "boot_p": boot_p(ex_s, ex_b),
                     "placebo_p": shift_placebo_p(P, post, cost)}
                res["cost_%d" % cost] = r
                beat = (r["oos"]["sharpe"] > r["bench_oos"]["sharpe"] and
                        r["holdout"]["sharpe"] > r["bench_holdout"]["sharpe"])
                verdict[cost] = {
                    "pass": beat and r["boot_p"] < 0.05 / N_RULES and r["placebo_p"] < 0.05,
                    "risk": (r["post"]["mdd"] >= 0.6 * r["bench_post"]["mdd"] and
                             r["oos"]["sharpe"] >= 0.9 * r["bench_oos"]["sharpe"] and
                             r["holdout"]["sharpe"] >= 0.9 * r["bench_holdout"]["sharpe"] and
                             r["placebo_p"] < 0.05)}
            res["verdict"] = ("PASS" if verdict[10.0]["pass"] and verdict[20.0]["pass"] else
                              "RISK-REDUCER" if verdict[20.0]["risk"] else "FAIL")
            report["rules"][name] = res
            r = res["cost_20"]
            lines.append(
                "%-7s %s %-12s IS Sh %5.2f | post-IS @20bp: Sh %5.2f (bench %5.2f, SPY %5.2f)  CAGR %5.1f%% (bench %5.1f%%)"
                "  maxDD %5.1f%% (bench %5.1f%%)  OOS Sh %5.2f/%5.2f  HOLD Sh %5.2f/%5.2f  boot p %.3f  placebo p %.3f  -> %s" % (
                    name, part, json.dumps(p), s_is["sharpe"], r["post"]["sharpe"], r["bench_post"]["sharpe"],
                    r["spy_post"]["sharpe"], 100 * r["post"]["cagr"], 100 * r["bench_post"]["cagr"],
                    100 * r["post"]["mdd"], 100 * r["bench_post"]["mdd"], r["oos"]["sharpe"], r["bench_oos"]["sharpe"],
                    r["holdout"]["sharpe"], r["bench_holdout"]["sharpe"], r["boot_p"], r["placebo_p"], res["verdict"]))
    print("Monthly allocation rules (pre-registered gates; see this file's docstring)")
    print("Part A: SPY alone, IS to 2009, OOS 2010-2017, HOLDOUT 2018+. Benchmark SPY buy-and-hold.")
    print("Part B: 9 ETFs, IS to 2014, OOS 2015-2020, HOLDOUT 2021+. Benchmark 60/40 SPY/IEF.\n")
    for ln in lines:
        print(ln)
    print("\nSharpe = excess over T-bills, annualized. Research, not financial advice.")
    if write:
        os.makedirs(os.path.dirname(write), exist_ok=True)
        with open(write, "w") as fh:
            json.dump(report, fh, indent=1, sort_keys=True, default=str)
    return report


def cmd_test(a):
    data = {}
    for s in sorted(set(PART_A + PART_B)):
        D = load(s)
        if not D:
            raise daily.LabError("no data for %s: run `alloc.py fetch` first" % s)
        data[s] = D
    cash = load(CASH)
    if not cash:
        raise daily.LabError("no T-bill data: run `alloc.py fetch` first")
    evaluate(Panel(data, cash), write=a.write)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("fetch")
    p = sub.add_parser("test")
    p.add_argument("--write", nargs="?", const=os.path.join(RESULTS, "alloc.json"))
    a = ap.parse_args(argv)
    try:
        return {"fetch": cmd_fetch, "test": cmd_test}[a.cmd](a) if a.cmd else ap.print_help() or 1
    except daily.LabError as e:
        print("alloc.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
