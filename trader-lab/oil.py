#!/usr/bin/env python3
"""trader-lab oil: test oil strategies (WTI / Brent; Exness USOIL / UKOIL) with the lab's gates.

    python3 oil.py fetch          # daily CL=F, BZ=F, USO, BNO (+ XLE, UUP) and hourly CL=F, BZ=F
    python3 oil.py backtest       # every candidate: day trades, multi-day, DCA ladders, spread, hourly
    python3 oil.py backtest --json --write

Instruments and why:
  * Same-day rules (enter at the open or on a stop, out at the close) run on the continuous
    front-month futures CL=F (WTI, the Exness USOIL reference) and BZ=F (Brent, UKOIL). The
    monthly contract roll happens between sessions, so it never touches an open-to-close trade.
  * Multi-day rules and DCA ladders run on USO (WTI) and BNO (Brent): real funds that pay the
    roll every month, like a long USOIL / UKOIL CFD held for days. A continuous futures series
    would show the roll jumps as fake returns.
  * Hourly rules use CL=F / BZ=F hourly bars, New York clock hours 09:00-14:00 (the NYMEX day
    session; settlement 14:30).

Gates (same as daily.py): variant chosen on data to 2014 only; positive 2015-2021 and 2022+;
t >= 3 on everything after 2014; long exposure across a close must beat random-entry placebos
(Bonferroni); no fills at a close nobody knows in advance. Hourly: first half / next quarter /
last quarter. Costs: 5 bps per round trip (USOIL spread ~3-4 cents on ~$70-90), plus 1 bp per
night for multi-day CFD financing on USO/BNO trades. Research, not financial advice.
"""

import argparse
import datetime
import json
import math
import os
import random
import statistics
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import daily  # noqa: E402
import hourly  # noqa: E402

FUT = ["CL=F", "BZ=F"]
FUNDS = ["USO", "BNO"]
COST_BPS = 5.0
NIGHT_BPS = 1.0
RESULTS = os.path.join(HERE, "results")
HSTORE = os.path.join(HERE, "data", "hourly_oil")


# ---------------------------------------------------------------- oil-specific daily rules

def r_month(D, i, p):
    """Seasonality: long the chosen calendar month (open to close)."""
    if int(D["d"][i][5:7]) in p["months"]:
        return {"side": 1, "hold": "oc"}
    return None


def r_wed_eia(D, i, p):
    """EIA weekly report day (Wednesday, 10:30 ET): follow or fade Tuesday's open-to-close move."""
    if i < 1 or daily.weekday(D, i) != 2:
        return None
    r = D["c"][i - 1] / D["o"][i - 1] - 1
    if abs(r) * 100 < p["min"]:
        return None
    s = 1 if r > 0 else -1
    return {"side": s if p["mode"] == "mom" else -s, "hold": "oc"}


def r_inside_break(D, i, p):
    """After an inside day, trade the break of its high (buy stop) or low (sell stop), out at the close."""
    if i < 2 or not (D["h"][i - 1] <= D["h"][i - 2] and D["l"][i - 1] >= D["l"][i - 2]):
        return None
    if p["side"] > 0:
        return {"side": 1, "hold": "stop", "entry": D["h"][i - 1]}
    return {"side": -1, "hold": "stop", "entry": D["l"][i - 1]}


def sw_tsmom(D, j, p):
    """Time-series momentum (Moskowitz, Ooi & Pedersen 2012): long while the L-day return is positive."""
    L = p["L"]
    return 1 if j > L and D["c"][j] > D["c"][j - L] else 0


def ex_tsmom(D, k, p, j):
    L = p["L"]
    return k > L and D["c"][k] <= D["c"][k - L]


def sw_sma(D, j, p):
    """Long while the close is above its n-day average."""
    m = daily.sma(D["c"], j + 1, p["n"])
    return 1 if m is not None and D["c"][j] > m else 0


def ex_sma(D, k, p, j):
    m = daily.sma(D["c"], k + 1, p["n"])
    return m is not None and D["c"][k] < m


def sw_season(D, j, p):
    """Long from the close of the last trading day before the chosen months start."""
    if j + 1 >= len(D["d"]):
        return 0
    return 1 if int(D["d"][j + 1][5:7]) in p["months"] and D["d"][j][5:7] != D["d"][j + 1][5:7] else 0


def ex_season(D, k, p, j):
    return int(D["d"][k][5:7]) not in p["months"] or (k + 1 < len(D["d"]) and int(D["d"][k + 1][5:7]) not in p["months"])


# ---- carry (term structure) proxy: the continuous front-month series jumps at each roll, a fund that
# rolls does not, so over L days ln(front change) - ln(fund change) = the roll jumps = minus the roll
# yield. Negative = backwardation (Gorton, Hayashi & Rouwenhorst 2013; Erb & Harvey 2006).
CARRY = {}   # id(fund dict) -> {date: {L: carry}}


def carry_series(fut, fund, Ls=(21, 63, 126)):
    fi = {d: i for i, d in enumerate(fut["d"])}
    out = {}
    for j, d in enumerate(fund["d"]):
        i = fi.get(d)
        row = {}
        for L in Ls:
            if i is None or j < L or i < L or fut["d"][i - L] != fund["d"][j - L]:
                continue
            row[L] = math.log(fut["c"][i] / fut["c"][i - L]) - math.log(fund["c"][j] / fund["c"][j - L])
        if row:
            out[d] = row
    return out


def sw_carry(D, j, p):
    """Long while the L-day roll yield is positive (backwardation); with trend=True also require a
    positive L-day fund return (Moskowitz et al.; carry + momentum)."""
    v = CARRY.get(id(D), {}).get(D["d"][j], {}).get(p["L"])
    if v is None or v >= 0:
        return 0
    if p.get("trend") and not (j > p["L"] and D["c"][j] > D["c"][j - p["L"]]):
        return 0
    return 1


def ex_carry(D, k, p, j):
    v = CARRY.get(id(D), {}).get(D["d"][k], {}).get(p["L"])
    if v is None or v >= 0:
        return True
    return bool(p.get("trend")) and k > p["L"] and D["c"][k] <= D["c"][k - p["L"]]


# ---- the real WTI futures curve from the EIA: daily settlements of contracts 1-4 since 1983
EIA_URL = "https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=RCLC%d&f=D"
MONTHS = {m: i for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct",
                                       "Nov", "Dec"], 1)}
CURVE = {}   # date -> {1: F1, 2: F2, ...}


def parse_eia(html):
    """EIA weekly table -> {date: price}. Each row: '1983 Apr- 4 to Apr- 8' then five cells Mon..Fri
    (empty on holidays)."""
    import re
    out = {}
    for row in re.findall(r"<tr>(.*?)</tr>", html, re.S):
        m = re.search(r"class='B6'>[^0-9]*(\d{4})\s+(\w{3})-\s*(\d+)\s+to", row)
        if not m:
            continue
        y, mon, day = int(m.group(1)), MONTHS.get(m.group(2)), int(m.group(3))
        if not mon:
            continue
        start = datetime.date(y, mon, day)
        cells = re.findall(r"<td class='B3'>([^<]*)</td>", row)
        for k, v in enumerate(cells[:5]):
            v = v.strip().replace(",", "")
            if v:
                try:
                    out[(start + datetime.timedelta(days=k)).isoformat()] = float(v)
                except ValueError:
                    pass
    return out


def fetch_curve(n_max=2):
    path = os.path.join(daily.STORE, "EIA_CL_curve.json")
    data = {}
    for n in range(1, n_max + 1):
        req = urllib.request.Request(EIA_URL % n, headers={"User-Agent": daily.UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            for d, px in parse_eia(r.read().decode("utf-8", "replace")).items():
                data.setdefault(d, {})[str(n)] = px
    with open(path, "w") as fh:
        json.dump(data, fh, separators=(",", ":"), sort_keys=True)
    return data


def load_curve():
    CURVE.clear()
    path = os.path.join(daily.STORE, "EIA_CL_curve.json")
    if os.path.exists(path):
        with open(path) as fh:
            for d, row in json.load(fh).items():
                if "1" in row and "2" in row and row["1"] > 0 and row["2"] > 0:
                    CURVE[d] = (row["1"], row["2"])
    return CURVE


def backwardation(d):
    """F1 / F2 - 1 in % on date d (positive = backwardation), or None."""
    v = CURVE.get(d)
    return None if v is None else (v[0] / v[1] - 1) * 100


def sw_curve(D, j, p):
    """Long while contract 1 is at least x% above contract 2; trend=L also needs a positive L-day return."""
    b = backwardation(D["d"][j])
    if b is None or b <= p["x"]:
        return 0
    if p.get("trend") and not (j > p["trend"] and D["c"][j] > D["c"][j - p["trend"]]):
        return 0
    return 1


def ex_curve(D, k, p, j):
    b = backwardation(D["d"][k])
    if b is None or b <= 0:
        return True
    return bool(p.get("trend")) and k > p["trend"] and D["c"][k] <= D["c"][k - p["trend"]]


BMOM = {}    # date -> {L: basis momentum}


def basis_momentum(Ls=(63, 126, 252)):
    """Boons & Porras Prado (2019): the L-day sum of (F1 daily return - F2 daily return). Days where the
    contracts roll (contract 1 expires) show as jumps in both; their difference is kept small by
    skipping days where either series moves more than 15% (a roll or a bad print)."""
    BMOM.clear()
    days = sorted(CURVE)
    diffs = []
    for k in range(1, len(days)):
        a, b = CURVE[days[k - 1]], CURVE[days[k]]
        r1, r2 = b[0] / a[0] - 1, b[1] / a[1] - 1
        diffs.append(0.0 if abs(r1) > 0.15 or abs(r2) > 0.15 else r1 - r2)
        row = {}
        for L in Ls:
            if len(diffs) >= L:
                row[L] = sum(diffs[-L:])
        if row:
            BMOM[days[k]] = row
    return BMOM


def sw_bmom(D, j, p):
    v = BMOM.get(D["d"][j], {}).get(p["L"])
    return 1 if v is not None and v > 0 else 0


def ex_bmom(D, k, p, j):
    v = BMOM.get(D["d"][k], {}).get(p["L"])
    return v is None or v <= 0


daily.EXITS.update({"tsmom": ex_tsmom, "sma": ex_sma, "season": ex_season, "carry": ex_carry,
                    "curve": ex_curve, "bmom": ex_bmom})

DAY_RULES = {
    "o_month": {"fn": r_month, "source": "oil seasonality by calendar month",
                "grid": {"months": [[m] for m in range(1, 13)]}},
    "o_eia": {"fn": r_wed_eia, "source": "EIA Weekly Petroleum Status Report day (Wednesday)",
              "grid": {"min": [0.0, 1.0, 2.0], "mode": ["mom", "rev"]}},
    "o_inside": {"fn": r_inside_break, "source": "inside-day breakout (Crabel; practitioner)",
                 "grid": {"side": [1, -1]}},
}
SWING_RULES = {
    "o_tsmom": {"fn": sw_tsmom, "source": "Moskowitz, Ooi & Pedersen 2012: time-series momentum",
                "grid": {"L": [21, 63, 126, 252], "exit": ["tsmom"], "max_days": [400], "fill": ["open"]}},
    "o_sma": {"fn": sw_sma, "source": "moving-average trend filter (Faber 2007 style)",
              "grid": {"n": [20, 50, 100, 200], "exit": ["sma"], "max_days": [400], "fill": ["open"]}},
    # o_carry (USO-vs-front proxy) is NOT in the search: USO stopped holding only the front month in
    # April 2020, so the proxy shows contango in 2022's steep backwardation. Replaced by o_curve (EIA).
    "o_curve": {"fn": lambda D, j, p: sw_curve(D, j, p), "source": "backwardation from EIA contracts 1-2 "
                "(Gorton, Hayashi & Rouwenhorst 2013; Erb & Harvey 2006)",
                "grid": {"x": [0.0, 0.5, 1.0], "trend": [0, 63], "exit": ["curve"], "max_days": [400], "fill": ["open"]}},
    "o_bmom": {"fn": lambda D, j, p: sw_bmom(D, j, p), "source": "basis momentum (Boons & Porras Prado 2019, JF)",
               "grid": {"L": [63, 126, 252], "exit": ["bmom"], "max_days": [400], "fill": ["open"]}},
    "o_season": {"fn": sw_season, "source": "oil seasonality: hold through chosen months",
                 "grid": {"months": [[4, 5, 6], [5, 6, 7, 8], [11, 12, 1, 2], [12, 1, 2, 3]],
                          "exit": ["season"], "max_days": [130], "fill": ["open"]}},
}

# day-trade rules from the general engine that make sense on front-month futures (no close fills)
GENERAL_DAY = ["gap", "gapfill", "prev", "ccrev", "wvb", "nr", "oops", "dow", "rsi2", "down", "lowx",
               "tom", "prehol", "8020", "smash", "soup", "stretch", "gsv", "base"]
GENERAL_SWING = ["s_rsi2", "s_crsi2", "s_r3", "s_mdd", "s_3hl", "s_d7", "s_bb", "s_ibs", "s_donch"]


def install():
    daily.RULES.update(DAY_RULES)
    daily.SWING.update(SWING_RULES)


def load(symbols):
    out = {}
    for s in symbols:
        D = daily.load(s)
        if D:
            k = next((i for i, d in enumerate(D["d"]) if d >= daily.DATA_START), len(D["d"]))
            out[s] = {key: v[k:] for key, v in D.items()}
    return out


def add_financing(res, universe):
    """Charge NIGHT_BPS per night held to every multi-day trade (CFD financing)."""
    return res   # applied inside run_swing via a wrapper (see swing_cost)


# ---------------------------------------------------------------- DCA ladders on funds

def dca(D, p, cost_bps=COST_BPS, night_bps=NIGHT_BPS, starts=None):
    """A DCA campaign: the first buy when the close is >= drop% below its 20-day high (or at given
    `starts`), then one more equal layer each further step% below the LAST buy, at most `layers`;
    sell everything at the close when it is >= tp% above the average cost, or after max_days.
    Every buy fills at the next open. Daily marks are in bps of the full ladder's capital
    (layers x layer size); each layer earns from its own fill price on its first day.
    Returns ({date: bps}, campaigns [(start, end, return on average cost in bps, layers used)])."""
    c, o, d = D["c"], D["o"], D["d"]
    n = len(c)
    cap = float(p["layers"])
    out, camps = {}, []
    starts = sorted(starts) if starts is not None else None
    si = 0
    j = 21
    while j < n - 2:
        if starts is not None:
            while si < len(starts) and starts[si] < j:
                si += 1
            if si >= len(starts):
                break
            j = starts[si]
        elif c[j] > max(c[j - 19:j + 1]) * (1 - p["drop"] / 100.0):
            j += 1
            continue
        start = j + 1
        layers = [(start, o[start])]           # (day bought, fill price)
        k = start
        closed = False
        while k < n:
            r = 0.0
            for (kb, px) in layers:
                base = px if kb == k else c[k - 1]
                r += (c[k] / base - 1) * 1e4 / cap
                if kb == k:
                    r -= cost_bps / 2 / cap    # half the round trip on the buy
                if kb < k:
                    r -= night_bps / cap       # financing for the night just held
            avg = sum(px for _, px in layers) / len(layers)
            if c[k] >= avg * (1 + p["tp"] / 100.0) or k - start >= p["max_days"]:
                r -= len(layers) * cost_bps / 2 / cap
                out[d[k]] = out.get(d[k], 0.0) + r
                camps.append((start, k, (c[k] / avg - 1) * 1e4, len(layers)))
                closed = True
                break
            out[d[k]] = out.get(d[k], 0.0) + r
            if len(layers) < p["layers"] and k + 1 < n and c[k] <= layers[-1][1] * (1 - p["step"] / 100.0):
                layers.append((k + 1, o[k + 1]))
            k += 1
        j = (k + 1) if closed else n
    return out, camps


def dca_grid():
    out = []
    for drop in (5, 10, 15, 20):
        for step in (3, 5, 8):
            for layers in (3, 5):
                for tp in (3, 5, 10):
                    out.append({"drop": drop, "step": step, "layers": layers, "tp": tp, "max_days": 120})
    return out


def run_dca(funds, cost_bps):
    """Every DCA variant on every fund; chosen on IS Sharpe; gated like the rest, with a random-start
    placebo (same campaign count, same ladder rules, random first buy)."""
    all_dates = sorted({d for D in funds.values() for d in D["d"]})
    rows = []
    for p in dca_grid():
        per, camps = {}, {}
        for s, D in funds.items():
            per[s], camps[s] = dca(D, p, cost_bps)
        ser = daily.portfolio(per, all_dates)
        row = {"rule": "o_dca", "params": p, "hold": "mc", "source": "DCA ladder on drawdowns",
               "trades": sum(len(v) for v in camps.values()),
               "win": (sum(1 for v in camps.values() for x in v if x[2] > 0) /
                       max(1, sum(len(v) for v in camps.values()))),
               "avg_trade_bps": (statistics.mean([x[2] for v in camps.values() for x in v])
                                 if any(camps.values()) else 0.0), "_camps": camps}
        for part in ("is", "oos", "ho"):
            row[part] = daily.stats([r for d, r in ser if daily.period_of(d) == part])
        row["post"] = daily.stats([r for d, r in ser if daily.period_of(d) != "is"])
        rows.append(row)
    best = max(rows, key=lambda r: r["is"]["sharpe"])
    ok = (best["is"]["t"] >= daily.MIN_IS_T and best["oos"]["mean"] > 0 and best["ho"]["mean"] > 0
          and best["post"]["t"] >= daily.POST_T)
    pl = None
    if best["post"]["t"] >= 1.5:
        rnd = random.Random(23)
        hits = 0
        reps = 200
        for _ in range(reps):
            per = {}
            for s, D in funds.items():
                k = len(best["_camps"][s])
                starts = sorted(rnd.sample(range(25, len(D["c"]) - 30), k)) if k else []
                per[s] = dca(D, best["params"], cost_bps, starts=starts)[0]
            t = daily.stats([r for d, r in daily.portfolio(per, all_dates) if daily.period_of(d) != "is"])["t"]
            hits += t >= best["post"]["t"]
        pl = hits / float(reps)
        ok = ok and pl < daily.PLACEBO_P
    for r in rows:
        r.pop("_camps", None)
    return rows, {"rule": "o_dca", "kind": "multi", "params": best["params"], "trades": best["trades"],
                  "win": best["win"], "avg_trade_bps": best["avg_trade_bps"], "is_t": best["is"]["t"],
                  "oos_t": best["oos"]["t"], "ho_t": best["ho"]["t"], "post_t": best["post"]["t"],
                  "ho_sharpe": best["ho"]["sharpe"], "placebo_p": pl, "pass": bool(ok),
                  "source": "DCA ladder on drawdowns"}


# ---------------------------------------------------------------- Brent-WTI spread

def spread_rule(cl, bz, p, cost_bps):
    """Brent-WTI log spread z-score over `lb` days. z > entry: short Brent / long WTI open to close next
    day; z < -entry: the reverse. Same-day legs on futures (no roll exposure). -> {date: bps}."""
    common = sorted(set(cl["d"]) & set(bz["d"]))
    ic = {d: i for i, d in enumerate(cl["d"])}
    ib = {d: i for i, d in enumerate(bz["d"])}
    s = [math.log(bz["c"][ib[d]] / cl["c"][ic[d]]) for d in common]
    out = {}
    lb = p["lb"]
    for t in range(lb + 1, len(common)):
        w = s[t - 1 - lb:t - 1]
        mu, sd = statistics.mean(w), statistics.pstdev(w)
        if sd <= 0:
            continue
        z = (s[t - 1] - mu) / sd
        if abs(z) < p["z"]:
            continue
        side = -1 if z > 0 else 1        # +1 = long Brent / short WTI
        d = common[t]
        rb = bz["c"][ib[d]] / bz["o"][ib[d]] - 1
        rc = cl["c"][ic[d]] / cl["o"][ic[d]] - 1
        out[d] = side * (rb - rc) / 2 * 1e4 - cost_bps   # two legs, half capital each, two spreads ~ one cost
    return out


def run_spread(cl, bz, cost_bps):
    rows = []
    for lb in (10, 20, 60):
        for z in (1.0, 1.5, 2.0, 2.5):
            per = {"BZ-CL": spread_rule(cl, bz, {"lb": lb, "z": z}, cost_bps)}
            dates = sorted(set(cl["d"]) & set(bz["d"]))
            ser = daily.portfolio(per, dates)
            row = {"rule": "o_spread", "params": {"lb": lb, "z": z}, "trades": len(per["BZ-CL"])}
            for part in ("is", "oos", "ho"):
                row[part] = daily.stats([r for d, r in ser if daily.period_of(d) == part])
            row["post"] = daily.stats([r for d, r in ser if daily.period_of(d) != "is"])
            rows.append(row)
    best = max(rows, key=lambda r: r["is"]["sharpe"])
    ok = (best["is"]["t"] >= daily.MIN_IS_T and best["oos"]["mean"] > 0 and best["ho"]["mean"] > 0
          and best["post"]["t"] >= daily.POST_T)
    return rows, {"rule": "o_spread", "kind": "day", "params": best["params"], "trades": best["trades"],
                  "win": None, "avg_trade_bps": None, "is_t": best["is"]["t"], "oos_t": best["oos"]["t"],
                  "ho_t": best["ho"]["t"], "post_t": best["post"]["t"], "ho_sharpe": best["ho"]["sharpe"],
                  "placebo_p": None, "pass": bool(ok), "source": "Brent-WTI spread mean reversion"}


# ---------------------------------------------------------------- hourly (NYMEX day session)

def hourly_sessions(sym):
    """{date: [bars 09:00 .. 14:00 New York]} from the oil hourly store; full sessions only."""
    p = os.path.join(HSTORE, "%s.json.gz" % sym)
    if not os.path.exists(p):
        return []
    import gzip
    with gzip.open(p, "rt") as fh:
        bars = json.load(fh)
    days = {}
    for ts, (o, h, l, c, v) in bars.items():
        loc = hourly.to_eastern(datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=int(ts)))
        if loc.minute or not 9 <= loc.hour <= 14:
            continue
        days.setdefault(loc.date().isoformat(), {})[loc.hour] = {"o": o, "h": h, "l": l, "c": c}
    return [(d, [days[d][h] for h in range(9, 15)]) for d in sorted(days) if len(days[d]) == 6]


def fetch_hourly(sym):
    url = "https://query2.finance.yahoo.com/v8/finance/chart/%s?range=730d&interval=60m" % sym
    req = urllib.request.Request(url, headers={"User-Agent": daily.UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.loads(r.read().decode())["chart"]["result"][0]
    q = res["indicators"]["quote"][0]
    out = {}
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    for i, ts in enumerate(res["timestamp"]):
        row = [q[k][i] for k in ("open", "high", "low", "close", "volume")]
        if None in row[:4]:
            continue
        if datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=ts + 3600) > now:
            continue
        out[str(ts)] = [float(x or 0) for x in row]
    return out


def h_rules():
    """(name, fn(S, k, p) -> [(side, entry, exit)], grid, source). Bars: 0=09:00 .. 5=14:00 New York."""
    def first_hour(S, k, p):
        B = S[k][1]
        r = B[0]["c"] / B[0]["o"] - 1
        if abs(r) * 1e4 < p["min"]:
            return []
        s = (1 if r > 0 else -1) * (1 if p["mode"] == "mom" else -1)
        return [(s, B[1]["o"], B[5]["c"])]

    def overnight_to_day(S, k, p):
        B, P = S[k][1], S[k - 1][1]
        r = B[0]["o"] / P[5]["c"] - 1
        if abs(r) * 1e4 < p["min"]:
            return []
        s = (1 if r > 0 else -1) * (1 if p["mode"] == "mom" else -1)
        return [(s, B[0]["o"], B[5]["c"])]

    def eia_hour(S, k, p):
        d = datetime.date(*map(int, S[k][0].split("-")))
        if d.weekday() != 2:
            return []
        B = S[k][1]
        r = B[1]["c"] / B[1]["o"] - 1            # the 10:00-11:00 bar holds the 10:30 release
        if abs(r) * 1e4 < p["min"]:
            return []
        s = (1 if r > 0 else -1) * (1 if p["mode"] == "mom" else -1)
        return [(s, B[2]["o"], B[5]["c"])]

    def hour_long(S, k, p):
        b = S[k][1][p["slot"]]
        return [(1, b["o"], b["c"])]

    def morning_to_close(S, k, p):
        B = S[k][1]
        r = B[3]["c"] / B[0]["o"] - 1           # 09:00 -> 13:00
        if abs(r) * 1e4 < p["min"]:
            return []
        s = (1 if r > 0 else -1) * (1 if p["mode"] == "mom" else -1)
        return [(s, B[4]["o"], B[5]["c"])]

    return [
        ("oh_first", first_hour, daily.grid({"min": [0, 50, 100], "mode": ["mom", "rev"]}), "first-hour momentum/reversal"),
        ("oh_gap", overnight_to_day, daily.grid({"min": [0, 50, 100], "mode": ["mom", "rev"]}), "overnight move -> day session"),
        ("oh_eia", eia_hour, daily.grid({"min": [0, 30, 60], "mode": ["mom", "rev"]}), "EIA release hour (Wed 10:30) -> rest of day"),
        ("oh_hour", hour_long, daily.grid({"slot": list(range(6))}), "time-of-day seasonality control"),
        ("oh_late", morning_to_close, daily.grid({"min": [0, 50, 100], "mode": ["mom", "rev"]}), "09:00-13:00 move -> 13:00-14:00+"),
    ]


def run_hourly(cost_bps):
    uni = {s: hourly_sessions(s) for s in FUT}
    dates = sorted({d for ss in uni.values() for d, _ in ss})
    if len(dates) < 100:
        return [], []
    c1, c2 = dates[len(dates) // 2], dates[(3 * len(dates)) // 4]
    part = lambda d: "is" if d < c1 else ("oos" if d < c2 else "ho")
    rows, chosen = [], []
    for name, fn, grid, src in h_rules():
        best = None
        for p in grid:
            by = {}
            n = 0
            for sym, ss in uni.items():
                for k in range(1, len(ss)):
                    for s, e, x in fn(ss, k, p):
                        by.setdefault(ss[k][0], []).append(s * (x / e - 1) * 1e4 - cost_bps)
                        n += 1
            ser = [(d, statistics.mean(by[d]) if d in by else 0.0) for d in dates]
            row = {"rule": name, "params": p, "trades": n, "source": src}
            for pt in ("is", "oos", "ho"):
                row[pt] = daily.stats([r for d, r in ser if part(d) == pt])
            row["post"] = daily.stats([r for d, r in ser if part(d) != "is"])
            rows.append(row)
            if best is None or row["is"]["sharpe"] > best["is"]["sharpe"]:
                best = row
        ok = (best["is"]["t"] >= daily.MIN_IS_T and best["oos"]["mean"] > 0 and best["ho"]["mean"] > 0
              and best["post"]["t"] >= daily.POST_T)
        chosen.append({"rule": name, "kind": "hourly", "params": best["params"], "trades": best["trades"],
                       "win": None, "avg_trade_bps": None, "is_t": best["is"]["t"], "oos_t": best["oos"]["t"],
                       "ho_t": best["ho"]["t"], "post_t": best["post"]["t"], "ho_sharpe": best["ho"]["sharpe"],
                       "placebo_p": None, "pass": bool(ok), "source": src})
    return rows, chosen


# ---------------------------------------------------------------- the whole oil search

def swing_cost_wrapper(cost_bps):
    """Charge NIGHT_BPS per night on multi-day trades by wrapping daily.run_swing."""
    orig = daily.run_swing

    def run(D, entry, p, c):
        out, n = orig(D, entry, p, c)
        # daily.run_swing stores its trades on the module-level name, which is this wrapper now
        trades = run.last_trades
        for j, k, _ in trades:
            nights = max(0, k - j)
            if nights and D["d"][k] in out:
                out[D["d"][k]] -= nights * NIGHT_BPS
        run.last_trades = [(j, k, r - max(0, k - j) * NIGHT_BPS) for j, k, r in trades]
        return out, n
    run.last_trades = []
    return orig, run


def search(cost_bps=COST_BPS):
    install()
    fut, funds = load(FUT), load(FUNDS)
    if not fut or not funds:
        raise SystemExit("oil.py: no data; run `oil.py fetch` first")
    load_curve()
    basis_momentum()
    out = {"cost_bps": cost_bps, "night_bps": NIGHT_BPS, "families": {}}
    # 1. same-day rules on futures
    day_names = GENERAL_DAY + list(DAY_RULES)
    res = daily.backtest(fut, cost_bps, only=day_names)
    keep = [v for v in res["variants"] if v["hold"] in ("oc", "stop", "target")]
    chosen_day = daily.choose(keep, fut, sorted({d for D in fut.values() for d in D["d"]}), cost_bps)
    out["families"]["day_futures"] = {"n_variants": len(keep), "chosen": chosen_day}
    # 2. multi-day rules on funds (with nightly financing)
    orig, wrapped = swing_cost_wrapper(cost_bps)
    daily.run_swing = wrapped
    try:
        res2 = daily.backtest(funds, cost_bps, only=GENERAL_SWING + list(SWING_RULES))
    finally:
        daily.run_swing = orig
    out["families"]["multi_funds"] = {"n_variants": res2["n_variants"], "chosen": res2["chosen"]}
    # 3. DCA ladders on funds
    dca_rows, dca_best = run_dca(funds, cost_bps)
    out["families"]["dca_funds"] = {"n_variants": len(dca_rows), "chosen": [dca_best],
                                    "top": sorted(({"params": r["params"], "is_t": r["is"]["t"], "post_t": r["post"]["t"],
                                                    "oos_mean": r["oos"]["mean"], "ho_mean": r["ho"]["mean"],
                                                    "trades": r["trades"]} for r in dca_rows),
                                                  key=lambda x: -x["post_t"])[:10]}
    # 4. Brent-WTI spread
    sp_rows, sp_best = run_spread(fut["CL=F"], fut["BZ=F"], cost_bps)
    out["families"]["spread"] = {"n_variants": len(sp_rows), "chosen": [sp_best]}
    # 5. hourly
    h_rows, h_chosen = run_hourly(cost_bps)
    out["families"]["hourly_futures"] = {"n_variants": len(h_rows), "chosen": h_chosen}
    out["n_variants"] = sum(f["n_variants"] for f in out["families"].values())
    out["passes"] = [dict(c, family=f) for f, v in out["families"].items() for c in v["chosen"] if c.get("pass")]
    return out


def report(res):
    L = ["Oil search: %d candidate variants, %.0f bp a round trip, %.0f bp a night on multi-day holds." % (
        res["n_variants"], res["cost_bps"], res["night_bps"]),
        "Chosen on data to 2014 (hourly: first half), judged on 2015-2021 and 2022+ (hourly: later quarters).", ""]
    for fam, v in res["families"].items():
        L.append("== %s (%d variants)" % (fam, v["n_variants"]))
        for c in sorted(v["chosen"], key=lambda c: -(c.get("post_t") or -9))[:12]:
            pp = c.get("placebo_p")
            L.append("  %-9s %-5s IS t %5.2f | OOS t %5.2f | HO t %5.2f | post t %5.2f | placebo %s | %s %s" % (
                c["rule"], c.get("kind", ""), c.get("is_t") or 0, c.get("oos_t") or 0, c.get("ho_t") or 0,
                c.get("post_t") or 0, ("%.3f" % pp) if pp is not None else "  -  ",
                "PASS" if c.get("pass") else "    ", json.dumps(c["params"], sort_keys=True)[:60]))
    L += ["", "PASSED every gate: %d" % len(res["passes"])]
    for p in res["passes"]:
        L.append("  %s %s %s" % (p["family"], p["rule"], json.dumps(p["params"], sort_keys=True)))
    L.append("Research, not financial advice.")
    return "\n".join(L)


# ---------------------------------------------------------------- cross-asset and risk overlays (monthly)

def cross_tests():
    """Monthly tests judged like trend.py (CAGR / Sharpe over T-bills / max drawdown by period):
    - oil -> stocks (Driesprong, Jacobsen & Maat 2008, JFE): hold SPY next month only if WTI fell (or
      rose less than x%) over the past month; else T-bills. Benchmark: SPY buy-and-hold.
    - volatility-managed oil (Moreira & Muir 2017): USO with exposure target/realized vol, capped at 1,
      monthly. Benchmark: USO buy-and-hold."""
    import trend
    uni, cash = trend.load(["SPY", "USO", "BNO"])
    dates, month_ends = trend.calendar(uni)
    cl = daily.load("CL=F")
    cli = {d: i for i, d in enumerate(cl["d"])}

    def oil_month_ret(d):
        i = cli.get(d)
        if i is None:
            i = max((cli[x] for x in cl["d"] if x <= d), default=None)
        if i is None or i < 21:
            return None
        return cl["c"][i] / cl["c"][i - 21] - 1

    rows = []
    spy = trend.simulate(uni, cash, dates, month_ends, trend.w_hold, {"only": "SPY"})
    rows.append({"name": "SPY buy-and-hold (benchmark)", "periods": trend.by_period(spy, cash)})
    for x in (0.0, 5.0):
        def w(u, c, d, p, x=x):
            r = oil_month_ret(d)
            return {} if r is None or r * 100 > x else {"SPY": 1.0}
        ser = trend.simulate(uni, cash, dates, month_ends, w, {})
        rows.append({"name": "SPY only after oil <= %+.0f%% last month" % x, "periods": trend.by_period(ser, cash),
                     "bench": "SPY"})
    uso = trend.simulate(uni, cash, dates, month_ends, trend.w_hold, {"only": "USO"})
    rows.append({"name": "USO buy-and-hold (benchmark)", "periods": trend.by_period(uso, cash)})
    for ov in ("vt1", "dd"):
        rows.append({"name": "USO + %s" % {"vt1": "vol targeting", "dd": "drawdown control"}[ov],
                     "periods": trend.by_period(trend.overlay(uso, cash, ov), cash), "bench": "USO"})
    return rows


def report_cross(rows):
    import trend
    L = ["Cross-asset and risk overlays (monthly; CAGR, Sharpe over T-bills, max drawdown):",
         "%-38s | %-22s | %-22s | %-22s" % ("strategy", "IS (to 2014)", "OOS 2015-21", "HOLDOUT 2022+")]
    for r in rows:
        L.append("%-38s | %s | %s | %s" % (r["name"][:38], trend.fmt(r["periods"]["is"]), trend.fmt(r["periods"]["oos"]),
                                           trend.fmt(r["periods"]["ho"])))
    return "\n".join(L)


# ---------------------------------------------------------------- the daily simulated oil track

TRACK_START = "2026-11-24"
TRACK_DCA = {"drop": 20, "layers": 5, "step": 8, "tp": 3, "max_days": 120}   # chosen on data to 2014
TRACK_BUDGET = 1000.0
CFD = {"USO": "USOIL (WTI)", "BNO": "UKOIL (Brent)"}


def dca_state(D, p):
    """Replay the ladder to the last close. -> dict: open campaign (layers with fill prices, average,
    take-profit level, next add level) or None, and the action for the next session."""
    c, o, d = D["c"], D["o"], D["d"]
    n = len(c)
    j = 21
    while j < n:
        if c[j] > max(c[j - 19:j + 1]) * (1 - p["drop"] / 100.0):
            j += 1
            continue
        if j == n - 1:
            return {"open": False, "action": "BUY first layer at the next open (close %.2f is %.0f%%+ below its "
                    "20-day high %.2f)" % (c[j], p["drop"], max(c[j - 19:j + 1]))}
        start = j + 1
        layers = [o[start]]
        k = start
        while k < n:
            avg = sum(layers) / len(layers)
            if c[k] >= avg * (1 + p["tp"] / 100.0) or k - start >= p["max_days"]:
                break
            if len(layers) < p["layers"] and k + 1 < n and c[k] <= layers[-1] * (1 - p["step"] / 100.0):
                layers.append(o[k + 1])
            elif len(layers) < p["layers"] and k == n - 1 and c[k] <= layers[-1] * (1 - p["step"] / 100.0):
                pass
            k += 1
        if k >= n:
            avg = sum(layers) / len(layers)
            add = layers[-1] * (1 - p["step"] / 100.0)
            act = "HOLD"
            if c[-1] <= add and len(layers) < p["layers"]:
                act = "ADD a layer at the next open"
            return {"open": True, "since": d[start], "layers": [round(x, 2) for x in layers], "avg": round(avg, 2),
                    "take_profit_close": round(avg * (1 + p["tp"] / 100.0), 2),
                    "next_add_close": round(add, 2) if len(layers) < p["layers"] else None,
                    "days": n - 1 - start, "time_stop_days": p["max_days"], "last": c[-1], "action": act}
        j = k + 1
    return {"open": False, "action": "WAIT: no trigger (close %.2f, needs <= %.2f)" % (
        c[-1], max(c[-20:]) * (1 - p["drop"] / 100.0))}


def cmd_today(a):
    funds = load(FUNDS)
    print("Oil track (SIMULATED, unproven: no oil rule passed the lab's gates; see RESEARCH.md). Signals from")
    print("USO / BNO closes, applied to USOIL / UKOIL as percentages. $%.0f budget, %d equal layers." % (
        TRACK_BUDGET, TRACK_DCA["layers"]))
    for s, D in funds.items():
        st = dca_state(D, TRACK_DCA)
        print("\n%s, last close %s %.2f:" % (CFD.get(s, s), D["d"][-1], D["c"][-1]))
        if st["open"]:
            print("  ladder open since %s: %d layer(s) at %s, average %.2f" % (
                st["since"], len(st["layers"]), st["layers"], st["avg"]))
            print("  sell all on a close >= %.2f (+%d%% on average cost), or after %d days (day %d now)" % (
                st["take_profit_close"], TRACK_DCA["tp"], st["time_stop_days"], st["days"]))
            if st["next_add_close"]:
                print("  next layer if a close <= %.2f" % st["next_add_close"])
        print("  -> %s" % st["action"])
    print("\nRule: first layer when the close is %d%% below its 20-day high; add a layer at each further %d%% "
          "below the last buy (max %d); sell all at +%d%% on average cost or after %d days. Fills at the next open." % (
              TRACK_DCA["drop"], TRACK_DCA["step"], TRACK_DCA["layers"], TRACK_DCA["tp"], TRACK_DCA["max_days"]))
    print("Simulated only; nothing is placed. Research, not financial advice.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="trader-lab oil search")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("fetch")
    sub.add_parser("today", help="today's simulated oil DCA ladder state and action")
    sub.add_parser("cross", help="oil -> stocks and volatility-managed oil (monthly)")
    p = sub.add_parser("backtest")
    p.add_argument("--json", action="store_true")
    p.add_argument("--cost", type=float, default=COST_BPS)
    p.add_argument("--write", nargs="?", const=os.path.join(RESULTS, "oil-latest.json"))
    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        daily.main(["fetch", "--symbols", ",".join(FUT + FUNDS + ["XLE", "UUP"])])
        try:
            c = fetch_curve(2)
            print("EIA WTI curve: %d days, contracts 1-2, %s to %s" % (len(c), min(c), max(c)))
        except Exception as e:      # the EIA site is optional; the rest still works
            print("EIA curve: could not fetch (%s)" % e)
        import gzip
        os.makedirs(HSTORE, exist_ok=True)
        for s in FUT:
            path = os.path.join(HSTORE, "%s.json.gz" % s)
            old = {}
            if os.path.exists(path):
                with gzip.open(path, "rt") as fh:
                    old = json.load(fh)
            old.update(fetch_hourly(s))
            with gzip.GzipFile(path, "wb", mtime=0) as gz:
                gz.write(json.dumps({k: old[k] for k in sorted(old, key=int)}).encode())
            print("%-5s hourly: %d bars, %d full day sessions" % (s, len(old), len(hourly_sessions(s))))
        return 0
    if a.cmd == "today":
        return cmd_today(a)
    if a.cmd == "cross":
        print(report_cross(cross_tests()))
        print("Research, not financial advice.")
        return 0
    if a.cmd == "backtest":
        res = search(a.cost)
        if a.write:
            with open(a.write, "w") as fh:
                json.dump(res, fh, indent=1, sort_keys=True, default=str)
        print(json.dumps(res, indent=1, sort_keys=True, default=str) if a.json else report(res))
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
