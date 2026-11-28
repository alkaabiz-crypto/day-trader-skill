import sys, math, random, json, gzip, datetime as dt
from zoneinfo import ZoneInfo
sys.path.insert(0, '.')
from daily import daily, REPO
NY = ZoneInfo("America/New_York")

def fxdaily(path):
    d = json.load(gzip.open(REPO + path)); out = {}
    for k in sorted(d, key=int):
        t = dt.datetime.fromtimestamp(int(k), NY)
        day = (t + dt.timedelta(hours=7)).date()  # 17:00 NY roll
        if day.weekday() >= 5: continue
        b = d[k]; day = day.isoformat()
        if day not in out: out[day] = list(b[:4])
        else:
            r = out[day]; r[1] = max(r[1], b[1]); r[2] = min(r[2], b[2]); r[3] = b[3]
    return out

MARKETS = {
 'US500': dict(src=lambda: daily('idx/spy.json.gz'), spread=2.0, swl=6.5, sws=1.0, split='2021-01-01', ls=False),
 'USTEC': dict(src=lambda: daily('idx/qqq.json.gz'), spread=2.0, swl=6.5, sws=1.0, split='2021-01-01', ls=False),
 'XAUUSD': dict(src=lambda: fxdaily('fx/xauusd.json.gz'), spread=1.5, swl=5.0, sws=1.0, split='2024-07-01', ls=True),
 'EURUSD': dict(src=lambda: fxdaily('fx/eurusd.json.gz'), spread=1.5, swl=2.5, sws=0.5, split='2024-07-01', ls=True),
}

# ---------- indicators
def sma(x, n):
    out = [None]*len(x); s = 0
    for i, v in enumerate(x):
        s += v
        if i >= n: s -= x[i-n]
        if i >= n-1: out[i] = s/n
    return out
def ema(x, n):
    out = [None]*len(x); a = 2/(n+1); e = None
    for i, v in enumerate(x):
        e = v if e is None else e + a*(v-e); out[i] = e if i >= n-1 else None
    return out
def rsi_w(x, n):
    out = [None]*len(x); ag = al = None
    for i in range(1, len(x)):
        ch = x[i]-x[i-1]; g = max(ch, 0); l = max(-ch, 0)
        if i <= n:
            ag = (ag or 0) + g/n; al = (al or 0) + l/n
            if i == n: out[i] = 100 if al == 0 else 100-100/(1+ag/al)
        else:
            ag = (ag*(n-1)+g)/n; al = (al*(n-1)+l)/n
            out[i] = 100 if al == 0 else 100-100/(1+ag/al)
    return out
def atr(H, L, C, n):
    tr = [H[0]-L[0]] + [max(H[i]-L[i], abs(H[i]-C[i-1]), abs(L[i]-C[i-1])) for i in range(1, len(C))]
    out = [None]*len(C); a = None
    for i, v in enumerate(tr):
        a = v if a is None else (a*(n-1)+v)/n
        out[i] = a if i >= n-1 else None
    return out

# ---------- rules: return list s[t] = target position decided at close of t (signal rules) ----------
def r_buyhold(D, ls): return [1]*len(D['C'])
def r_sma200(D, ls):
    m = sma(D['C'], 200); return [0 if m[i] is None else (1 if c > m[i] else (-1 if ls else 0)) for i, c in enumerate(D['C'])]
def r_golden(D, ls):
    a, b = sma(D['C'], 50), sma(D['C'], 200)
    return [0 if b[i] is None else (1 if a[i] > b[i] else (-1 if ls else 0)) for i in range(len(a))]
def r_tsmom(D, ls):
    C = D['C']; return [0 if i < 252 else (1 if C[i] > C[i-252] else (-1 if ls else 0)) for i in range(len(C))]
def turtle(n_in, n_out):
    def f(D, ls):
        H, L, C = D['H'], D['L'], D['C']; s = []; p = 0
        for i in range(len(C)):
            if i < n_in: s.append(0); continue
            hi = max(H[i-n_in:i]); lo = min(L[i-n_in:i]); xo_l = min(L[i-n_out:i]); xo_h = max(H[i-n_out:i])
            if p == 1 and C[i] < xo_l: p = 0
            if p == -1 and C[i] > xo_h: p = 0
            if p == 0:
                if C[i] > hi: p = 1
                elif ls and C[i] < lo: p = -1
            s.append(p)
        return s
    return f
def r_macd(D, ls):
    C = D['C']; e12, e26 = ema(C, 12), ema(C, 26)
    m = [None if e26[i] is None else e12[i]-e26[i] for i in range(len(C))]
    first = next(i for i, v in enumerate(m) if v is not None)
    sig = [None]*first + ema(m[first:], 9)
    return [0 if sig[i] is None else (1 if m[i] > sig[i] else (-1 if ls else 0)) for i in range(len(C))]
def r_supertrend(D, ls, n=10, k=3.0):
    H, L, C = D['H'], D['L'], D['C']; A = atr(H, L, C, n); s = []; dirn = 1; ub = lb = None
    for i in range(len(C)):
        if A[i] is None: s.append(0); continue
        mid = (H[i]+L[i])/2; bu = mid + k*A[i]; bl = mid - k*A[i]
        ub = bu if ub is None or bu < ub or C[i-1] > ub else ub
        lb = bl if lb is None or bl > lb or C[i-1] < lb else lb
        if C[i] > ub: dirn = 1
        elif C[i] < lb: dirn = -1
        s.append(1 if dirn == 1 else (-1 if ls else 0))
    return s
def r_ema921(D, ls):
    a, b = ema(D['C'], 9), ema(D['C'], 21)
    return [0 if b[i] is None else (1 if a[i] > b[i] else (-1 if ls else 0)) for i in range(len(a))]
def r_rsi2(D, ls):
    C = D['C']; r = rsi_w(C, 2); m200 = sma(C, 200); m5 = sma(C, 5); s = []; p = 0
    for i in range(len(C)):
        if m200[i] is None or r[i] is None: s.append(0); continue
        if p and C[i] > m5[i]: p = 0
        elif not p and r[i] < 10 and C[i] > m200[i]: p = 1
        s.append(p)
    return s
def r_double7(D, ls):
    C = D['C']; m200 = sma(C, 200); s = []; p = 0
    for i in range(len(C)):
        if m200[i] is None or i < 7: s.append(0); continue
        if p and C[i] >= max(C[i-6:i+1]): p = 0
        elif not p and C[i] <= min(C[i-6:i+1]) and C[i] > m200[i]: p = 1
        s.append(p)
    return s
def r_ibs(D, ls):
    H, L, C = D['H'], D['L'], D['C']; s = []; p = 0
    for i in range(len(C)):
        ib = (C[i]-L[i])/(H[i]-L[i]) if H[i] > L[i] else 0.5
        if p and ib > 0.8: p = 0
        elif not p and ib < 0.2: p = 1
        s.append(p)
    return s
def r_boll(D, ls):
    C = D['C']; m = sma(C, 20); s = []; p = 0
    for i in range(len(C)):
        if m[i] is None: s.append(0); continue
        sd = (sum((c-m[i])**2 for c in C[i-19:i+1])/20) ** .5
        if p and C[i] > m[i]: p = 0
        elif not p and C[i] < m[i]-2*sd: p = 1
        s.append(p)
    return s

SIGNAL = dict(buyhold=r_buyhold, sma200=r_sma200, golden=r_golden, tsmom=r_tsmom, turtle20=turtle(20, 10),
              turtle55=turtle(55, 20), macd=r_macd, supertrend=r_supertrend, ema921=r_ema921, rsi2=r_rsi2,
              double7=r_double7, ibs=r_ibs, bollinger=r_boll)
CAL = ('overnight', 'tom', 'turnaround')

def calendar(name, dates):
    """Return (intraday pos for day t, overnight pos close t -> open t+1)."""
    n = len(dates); intra = [0]*n; over = [0]*n
    dd = [dt.date.fromisoformat(d) for d in dates]
    if name == 'overnight': over = [1]*n
    if name == 'tom':
        # trading-day index within month and from month end
        for i in range(n):
            # position held over close i -> close i+1 if i is (last-1) .. day 2 of next month (exit close of 3rd day)
            j = i; k = 0
            while j+1 < n and dd[j+1].month == dd[i].month: j += 1; k += 1
            from_end = k  # 0 = last day
            m = 0; j = i
            while j-1 >= 0 and dd[j-1].month == dd[i].month: j -= 1; m += 1
            day_no = m+1
            if from_end in (0, 1) or day_no in (1, 2):
                over[i] = 1
                if i+1 < n: intra[i+1] = 1
    if name == 'turnaround':
        for i in range(1, n):
            if dd[i].weekday() == 0 and i+1 < n and dd[i+1].weekday() == 1 and None is None:
                pass
    return intra, over

def series(D, name, ls):
    n = len(D['C'])
    if name in CAL:
        if name == 'turnaround':
            intra = [0]*n; over = [0]*n; dd = [dt.date.fromisoformat(x) for x in D['dates']]
            for i in range(1, n-1):
                if dd[i].weekday() == 0 and dd[i+1].weekday() == 1 and D['C'][i] < D['C'][i-1]:
                    over[i] = 1; intra[i+1] = 1
            return intra, over
        return calendar(name, D['dates'])
    s = SIGNAL[name](D, ls)
    intra = [0] + s[:-1]           # decided at close t-1, held from open t
    over = [0] + s[:-1]            # still held overnight after close t (position changes only at next open)
    over = intra[:]                # held across close t -> open t+1 until changed at open t+1
    return intra, over

def returns(D, intra, over, spread_bp, swl, sws, swap_on=True, mult=1.0):
    O, C, dates = D['O'], D['C'], D['dates']; n = len(C); out = []; prev = 0  # position just before open t
    for t in range(n):
        r = 0.0
        # change at open t: from over[t-1] to intra[t]
        p_before = over[t-1] if t else 0
        r -= abs(intra[t]-p_before) * spread_bp*mult/2e4
        r += intra[t] * (C[t]/O[t]-1)
        # change at close t: intra[t] -> over[t]
        r -= abs(over[t]-intra[t]) * spread_bp*mult/2e4
        if t+1 < n:
            r += over[t] * (O[t+1]/C[t]-1)
            if swap_on and over[t]:
                nights = (dt.date.fromisoformat(dates[t+1]) - dt.date.fromisoformat(dates[t])).days
                rate = swl if over[t] > 0 else sws
                r -= abs(over[t]) * rate*mult/100/360 * nights
        out.append(r)
    return out

def stats(r):
    n = len(r)
    if n < 20: return dict(n=n, mean=0, t=0, sharpe=0)
    m = sum(r)/n; sd = (sum((x-m)**2 for x in r)/(n-1)) ** .5
    return dict(n=n, mean=m, t=(m/sd*n**.5 if sd else 0), sharpe=(m/sd*252**.5 if sd else 0))
def growth(r, start=1000.0):
    v = start; pk = v; dd = 0
    for x in r: v *= 1+x; pk = max(pk, v); dd = min(dd, v/pk-1)
    return v, dd
