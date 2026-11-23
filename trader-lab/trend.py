#!/usr/bin/env python3
"""trader-lab trend engine: longer-horizon trend and momentum, volatility targeting and
drawdown control, on index ETFs only (no survivorship bias), cash earning the T-bill rate.

    python3 trend.py backtest            # every strategy, overlay and benchmark, by period
    python3 trend.py backtest --json
    python3 trend.py signal              # this month's positions for the passing strategies

Strategies (decided at a month-end close, traded at the next open, held a month):
  tsmom    Moskowitz, Ooi & Pedersen (2012, JFE) time-series momentum: long each ETF whose
           past L-month return beats cash, else cash. Equal or inverse-volatility weights.
  sma      Faber (2007) "A Quantitative Approach to Tactical Asset Allocation": long each ETF
           whose month-end close is above its 10-month average, else cash.
  xsmom    Jegadeesh & Titman (1993) / ETF relative strength: the top N ETFs by 12-1 month
           return, each only if its own return beats cash.
  dual     Antonacci (2014) dual momentum: SPY vs EFA by 12-month return; if the winner does
           not beat T-bills, hold IEF (bonds).
Overlays (applied to any series):
  vt       Moreira & Muir (2017, JF) volatility-managed: exposure = target vol / last month's
           realized vol, capped at 1 (no margin) or 1.5.
  dd       drawdown control: half exposure while the series is >10% below its peak.
Benchmarks: SPY buy-and-hold; equal-weight buy-and-hold of the same ETFs.

Periods are the daily engine's: IS to 2014, OOS 2015-2021, HOLDOUT 2022+. A strategy PASSES
only if, in IS, OOS and HOLDOUT separately, its Sharpe is at least its benchmark's and its
max drawdown is smaller, and its excess return over cash has t >= 3 after 2014 is NOT
required (it is a risk-reduction test, not an alpha test); it must also beat a random-timing
placebo (same months in the market per ETF, random months) at p < 0.05 / rules tested.
Costs: 2 bps per unit of weight traded. Research, not financial advice.
"""

import argparse
import datetime
import json
import math
import os
import random
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import daily  # noqa: E402

ETFS = ["SPY", "QQQ", "IWM", "MDY", "EFA", "EEM", "EWJ", "TLT", "IEF", "LQD", "AGG",
        "GLD", "DBC", "VNQ", "XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLU", "XLB"]
START = "1998-01-01"
COST_BPS = 2.0
RESULTS = os.path.join(HERE, "results")


class TrendError(Exception):
    pass


# ---------------------------------------------------------------- data

def load(symbols=ETFS):
    uni = {}
    for s in symbols:
        D = daily.load(s)
        if not D:
            continue
        if not D.get("a") or len(D["a"]) != len(D["c"]):
            raise TrendError("%s has no dividend-adjusted closes: run `daily.py fetch --symbols %s`" % (s, s))
        # total-return prices: scale open and close by adjclose / close, so dividends count
        f = [a / c for a, c in zip(D["a"], D["c"])]
        D = dict(D, o=[o * k for o, k in zip(D["o"], f)], c=list(D["a"]))
        idx = {d: i for i, d in enumerate(D["d"])}
        uni[s] = (D, idx)
    if not uni:
        raise TrendError("no daily data: run `daily.py fetch --symbols %s`" % ",".join(symbols))
    irx = daily.load("^IRX")
    cash = {}
    if irx:
        for d, c in zip(irx["d"], irx["c"]):
            cash[d] = c / 100.0 / 252.0      # 13-week T-bill yield, % a year -> per trading day
    return uni, cash


def calendar(uni):
    dates = sorted({d for D, _ in uni.values() for d in D["d"] if d >= START})
    month_end = [i for i in range(len(dates) - 1) if dates[i][:7] != dates[i + 1][:7]]
    return dates, set(dates[i] for i in month_end)


def close_on(uni, s, d):
    D, idx = uni[s]
    i = idx.get(d)
    return None if i is None else D["c"][i]


def lookback_return(uni, s, d, months, skip=0):
    """Return from the close `months` (+skip) months before date d to `skip` months before d,
    using month-end closes on or before those dates."""
    D, idx = uni[s]
    i = idx.get(d)
    if i is None:
        return None
    step = 21
    a, b = i - step * (months + skip), i - step * skip
    if a < 0:
        return None
    return D["c"][b] / D["c"][a] - 1


def realized_vol(uni, s, d, days=63):
    D, idx = uni[s]
    i = idx.get(d)
    if i is None or i < days + 1:
        return None
    r = [D["c"][k] / D["c"][k - 1] - 1 for k in range(i - days + 1, i + 1)]
    return statistics.pstdev(r) * math.sqrt(252)


def cash_return(cash, d, period_days=21):
    return cash.get(d, 0.0) * period_days


# ---------------------------------------------------------------- strategies: weights at a month end

def w_tsmom(uni, cash, d, p):
    avail = [s for s in uni if close_on(uni, s, d) is not None]
    out = {}
    for s in avail:
        r = lookback_return(uni, s, d, p["L"])
        if r is None:
            continue
        if r > cash_return(cash, d, 21 * p["L"]):
            out[s] = 1.0 / realized_vol(uni, s, d) if p["w"] == "iv" and realized_vol(uni, s, d) else 1.0
    n = len([s for s in avail if lookback_return(uni, s, d, p["L"]) is not None])
    if not out or not n:
        return {}
    if p["w"] == "iv":
        # inverse-vol weights scaled so a full house (all ETFs long) sums to 1
        allw = sum(1.0 / v for v in (realized_vol(uni, s, d) for s in avail) if v)
        return {s: w / allw for s, w in out.items()}
    return {s: 1.0 / n for s in out}


def w_sma(uni, cash, d, p):
    out, n = {}, 0
    for s in uni:
        D, idx = uni[s]
        i = idx.get(d)
        if i is None or i < 21 * 10:
            continue
        n += 1
        ma = sum(D["c"][i - 21 * k] for k in range(10)) / 10.0
        if D["c"][i] > ma:
            out[s] = 1.0
    return {s: 1.0 / n for s in out} if n else {}


def w_xsmom(uni, cash, d, p):
    ranked = []
    for s in uni:
        r = lookback_return(uni, s, d, 11, skip=1)
        if r is not None:
            ranked.append((r, s))
    ranked.sort(reverse=True)
    top = [s for r, s in ranked[:p["n"]] if r > cash_return(cash, d, 21 * 11)]
    return {s: 1.0 / p["n"] for s in top}


def w_dual(uni, cash, d, p):
    a = lookback_return(uni, "SPY", d, 12) if "SPY" in uni else None
    b = lookback_return(uni, "EFA", d, 12) if "EFA" in uni else None
    if a is None or b is None:
        return {}
    win, r = ("SPY", a) if a >= b else ("EFA", b)
    if r > cash_return(cash, d, 252):
        return {win: 1.0}
    return {"IEF": 1.0} if "IEF" in uni and close_on(uni, "IEF", d) is not None else {}


def w_hold(uni, cash, d, p):
    avail = [s for s in uni if close_on(uni, s, d) is not None]
    if p.get("only"):
        return {p["only"]: 1.0} if p["only"] in avail else {}
    return {s: 1.0 / len(avail) for s in avail} if avail else {}


STRATS = {
    "tsmom": {"fn": w_tsmom, "src": "Moskowitz, Ooi & Pedersen 2012 JFE",
              "grid": [{"L": 12, "w": "eq"}, {"L": 6, "w": "eq"}, {"L": 3, "w": "eq"}, {"L": 12, "w": "iv"}]},
    "sma": {"fn": w_sma, "src": "Faber 2007, 10-month moving average", "grid": [{}]},
    "xsmom": {"fn": w_xsmom, "src": "Jegadeesh & Titman 1993; ETF relative strength",
              "grid": [{"n": 3}, {"n": 5}]},
    "dual": {"fn": w_dual, "src": "Antonacci 2014, dual momentum", "grid": [{}]},
}
BENCH = {"spy": {"fn": w_hold, "p": {"only": "SPY"}}, "ew": {"fn": w_hold, "p": {}}}


# ---------------------------------------------------------------- simulation

def simulate(uni, cash, dates, month_ends, wfn, p, cost_bps=COST_BPS, sched=None):
    """Daily returns of a monthly-rebalanced strategy. Weights decided at a month-end close
    take effect at the next open; uninvested weight earns the T-bill rate. `sched` optionally
    replaces wfn with precomputed {month_end_date: weights} (used by the placebo)."""
    out = []
    w = {}
    pending = None
    for t in range(1, len(dates)):
        d, prev = dates[t], dates[t - 1]
        if prev in month_ends:
            pending = sched.get(prev, {}) if sched is not None else wfn(uni, cash, prev, p)
        r = 0.0
        if pending is not None:
            new = pending
            pending = None
            turn = sum(abs(new.get(s, 0) - w.get(s, 0)) for s in set(new) | set(w))
            for s in set(w) | set(new):
                D, idx = uni[s]
                i = idx.get(d)
                if i is None or idx.get(prev) is None:
                    continue
                o, c, pc = D["o"][i], D["c"][i], D["c"][idx[prev]]
                r += w.get(s, 0) * (o / pc - 1) + new.get(s, 0) * (c / o - 1)
            r += (1 - sum(new.values())) * cash.get(prev, 0.0)
            r -= turn * cost_bps / 1e4
            w = new
        else:
            for s, ws in w.items():
                D, idx = uni[s]
                i, j = idx.get(d), idx.get(prev)
                if i is not None and j is not None:
                    r += ws * (D["c"][i] / D["c"][j] - 1)
            r += (1 - sum(w.values())) * cash.get(prev, 0.0)
        out.append((d, r))
    return out


def overlay(series, cash, kind, cost_bps=COST_BPS):
    """Monthly-updated exposure scaling of a daily return series (the rest in T-bills).
    vt1 / vt15: target vol = the series' own long-run vol so far, capped at 1 / 1.5.
    dd: half exposure while more than 10% below the running peak (decided at month ends)."""
    out = []
    expo, peak, eq = 1.0, 1.0, 1.0
    hist = []
    for k, (d, r) in enumerate(series):
        if k and d[:7] != series[k - 1][0][:7]:          # first day of a new month: reset exposure
            new = expo
            if kind.startswith("vt") and len(hist) >= 252:
                last = hist[-21:]
                rv = statistics.pstdev(last) * math.sqrt(252)
                target = statistics.pstdev(hist) * math.sqrt(252)
                cap = 1.5 if kind == "vt15" else 1.0
                new = min(cap, target / rv) if rv > 0 else cap
            elif kind == "dd":
                new = 0.5 if eq < 0.9 * peak else 1.0
            r_adj = new * r + (1 - new) * cash.get(d, 0.0) - abs(new - expo) * cost_bps / 1e4
            expo = new
        else:
            r_adj = expo * r + (1 - expo) * cash.get(d, 0.0)
        hist.append(r)
        eq *= 1 + r_adj
        peak = max(peak, eq)
        out.append((d, r_adj))
    return out


# ---------------------------------------------------------------- metrics

def metrics(series, cash, lo=None, hi=None):
    x = [(d, r) for d, r in series if (lo is None or d > lo) and (hi is None or d <= hi)]
    if len(x) < 60:
        return None
    rets = [r for _, r in x]
    ex = [r - cash.get(d, 0.0) for d, r in x]
    eq, peak, mdd = 1.0, 1.0, 0.0
    for r in rets:
        eq *= 1 + r
        peak = max(peak, eq)
        mdd = min(mdd, eq / peak - 1)
    years = len(rets) / 252.0
    sd = statistics.pstdev(ex)
    return {"cagr": eq ** (1 / years) - 1, "vol": statistics.pstdev(rets) * math.sqrt(252),
            "sharpe": statistics.mean(ex) / sd * math.sqrt(252) if sd > 0 else 0.0,
            "mdd": mdd, "t_excess": statistics.mean(ex) / sd * math.sqrt(len(ex)) if sd > 0 else 0.0,
            "days": len(rets)}


PERIODS = [("is", None, daily.IS_END), ("oos", daily.IS_END, daily.OOS_END), ("ho", daily.OOS_END, None)]


def by_period(series, cash):
    return {k: metrics(series, cash, lo, hi) for k, lo, hi in PERIODS}


def placebo_p(uni, cash, dates, month_ends, real_sched, real_sharpe_post, reps=200, seed=13):
    """Random-timing placebo: each ETF keeps its number of invested months and its weights,
    shuffled to random month ends. -> share of placebos with post-2014 Sharpe >= the real one."""
    rnd = random.Random(seed)
    mes = sorted(real_sched)
    per_sym = {}
    for m in mes:
        for s, w in real_sched[m].items():
            per_sym.setdefault(s, []).append(w)
    hits = 0
    for _ in range(reps):
        sched = {m: {} for m in mes}
        for s, ws in per_sym.items():
            ok = [m for m in mes if close_on(uni, s, m) is not None]
            for m, w in zip(rnd.sample(ok, min(len(ws), len(ok))), ws):
                sched[m][s] = w
        ser = simulate(uni, cash, dates, month_ends, None, None, sched=sched)
        m_ = metrics(ser, cash, daily.IS_END)
        if m_ and m_["sharpe"] >= real_sharpe_post:
            hits += 1
    return hits / float(reps)


def schedule(uni, cash, month_ends, wfn, p):
    return {m: wfn(uni, cash, m, p) for m in sorted(month_ends)}


def backtest(placebos=200):
    uni, cash = load()
    dates, month_ends = calendar(uni)
    rows = []
    bench = {}
    for name, b in BENCH.items():
        ser = simulate(uni, cash, dates, month_ends, b["fn"], b["p"])
        bench[name] = ser
        rows.append({"name": "bench:" + name, "periods": by_period(ser, cash)})
        for ov in ("vt1", "vt15", "dd"):
            rows.append({"name": "bench:%s+%s" % (name, ov), "periods": by_period(overlay(ser, cash, ov), cash)})
    tested = 0
    cands = []
    for name, spec in STRATS.items():
        best = None
        for p in spec["grid"]:
            ser = simulate(uni, cash, dates, month_ends, spec["fn"], p)
            per = by_period(ser, cash)
            row = {"name": name, "params": p, "src": spec["src"], "periods": per, "_ser": ser}
            if best is None or per["is"]["sharpe"] > best["periods"]["is"]["sharpe"]:
                best = row
            rows.append(row)
        cands.append(best)
        for ov in ("vt1", "dd"):
            ser = overlay(best["_ser"], cash, ov)
            rows.append({"name": "%s+%s" % (name, ov), "params": best["params"], "src": spec["src"],
                         "periods": by_period(ser, cash)})
    ew = by_period(bench["ew"], cash)
    alpha = 0.05 / max(1, len(cands))
    for best in cands:
        per = best["periods"]
        beats = all(per[k] and ew[k] and per[k]["sharpe"] >= ew[k]["sharpe"] and per[k]["mdd"] > ew[k]["mdd"]
                    for k in ("is", "oos", "ho"))
        post = metrics(best["_ser"], cash, daily.IS_END)
        pp = None
        if beats and placebos:
            tested += 1
            sched = schedule(uni, cash, month_ends, STRATS[best["name"]]["fn"], best["params"])
            pp = placebo_p(uni, cash, dates, month_ends, sched, post["sharpe"], reps=placebos)
        best["beats_bench"] = beats
        best["placebo_p"] = pp
        best["pass"] = bool(beats and pp is not None and pp < alpha)
        best["chosen"] = True
    for r in rows:
        r.pop("_ser", None)
    return {"periods": [p[0] for p in PERIODS], "start": START, "cost_bps": COST_BPS,
            "symbols": sorted(uni), "rows": rows, "placebo_alpha": alpha}


def fmt(m):
    if not m:
        return "%27s" % "-"
    return "%5.1f%% %5.2f %6.1f%%" % (m["cagr"] * 100, m["sharpe"], m["mdd"] * 100)


def report(res):
    L = ["Trend engine: %d ETFs from %s, monthly rebalance at the next open, %.0f bps per unit traded," % (
        len(res["symbols"]), res["start"], res["cost_bps"]),
        "cash earns the 13-week T-bill. Each cell: CAGR, Sharpe (excess of T-bills), max drawdown.", "",
        "%-22s %-18s | %-22s | %-22s | %-22s | %s" % ("strategy", "params", "IS (to 2014)", "OOS 2015-21",
                                                       "HOLDOUT 2022+", "verdict"),
        "-" * 125]
    for r in res["rows"]:
        per = r["periods"]
        p = ",".join("%s=%s" % kv for kv in sorted((r.get("params") or {}).items()))
        verdict = ""
        if r.get("chosen"):
            verdict = "PASS" if r["pass"] else ("beats EW, placebo p %.2f" % r["placebo_p"]
                                                if r.get("placebo_p") is not None else "chosen; does not beat EW")
        L.append("%-22s %-18s | %s | %s | %s | %s" % (r["name"], p[:18], fmt(per["is"]), fmt(per["oos"]),
                                                    fmt(per["ho"]), verdict))
    L += ["", "PASS = in every period a Sharpe at least equal-weight buy-and-hold's AND a smaller drawdown,",
          "and beating random-timing placebos at p < %.3f. Research, not financial advice." % res["placebo_alpha"]]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description="trader-lab trend engine")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("backtest")
    p.add_argument("--json", action="store_true")
    p.add_argument("--placebos", type=int, default=200)
    p.add_argument("--write", nargs="?", const=os.path.join(RESULTS, "trend-latest.json"))
    sub.add_parser("signal")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "backtest":
            res = backtest(a.placebos)
            if a.write:
                with open(a.write, "w") as fh:
                    json.dump(res, fh, indent=1, sort_keys=True)
            print(json.dumps(res, indent=1, sort_keys=True) if a.json else report(res))
            return 0
        if a.cmd == "signal":
            uni, cash = load()
            dates, month_ends = calendar(uni)
            last = sorted(month_ends)[-1]
            print("Positions decided at the %s close (held until the next month end):" % last)
            for name, spec in STRATS.items():
                for p in spec["grid"][:1]:
                    w = spec["fn"](uni, cash, last, p)
                    held = ", ".join("%s %.0f%%" % (s, x * 100) for s, x in sorted(w.items(), key=lambda kv: -kv[1]))
                    print("  %-6s %-16s %s%s" % (name, json.dumps(p, sort_keys=True), held or "all cash",
                                                ("  (cash %.0f%%)" % ((1 - sum(w.values())) * 100)) if w else ""))
            print("\nResearch, not financial advice. Nothing is placed without your yes.")
            return 0
        ap.print_help()
        return 1
    except TrendError as e:
        print("trend.py: %s" % e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
