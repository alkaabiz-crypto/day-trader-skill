import gzip, json, datetime as dt, math, random, statistics, sys
from zoneinfo import ZoneInfo
NY = ZoneInfo("America/New_York"); REPO = "/home/user/day-trader-skill/trader-lab/data/"
MK = {'US500': ('idx/spy.json.gz', 1.0, 'idx', '2022-01-01'), 'USTEC': ('idx/qqq.json.gz', 0.65, 'idx', '2022-01-01'),
      'XAUUSD': ('fx/xauusd.json.gz', 0.85, 'fx', '2024-07-01'), 'EURUSD': ('fx/eurusd.json.gz', 1.0, 'fx', '2024-07-01')}
def load(f, kind):
    d = json.load(gzip.open(REPO+f)); days = {}
    for k in sorted(d, key=int):
        t = dt.datetime.fromtimestamp(int(k), NY); b = d[k]; tm = t.hour*60+t.minute
        if kind == 'idx':
            if not (570 <= tm < 960): continue
            day = t.date()
        else:
            day = (t + dt.timedelta(hours=5)).date()   # FX day starts 19:00 NY
            if day.weekday() >= 5: continue
            tm = tm if t.hour >= 19 and False else tm
        days.setdefault(day.isoformat(), []).append((tm if kind == 'idx' else (tm - 1140) % 1440, b[0], b[1], b[2], b[3]))
    return days   # fx minutes are counted from 19:00 NY (0) ; 03:00 NY = 480, 12:00 = 1020, 15:55 = 1255
def ema(x, n):
    a = 2/(n+1); e = None; o = []
    for v in x: e = v if e is None else e + a*(v-e); o.append(e)
    return o
def rsi(x, n=14):
    o = [None]*len(x); ag = al = 0
    for i in range(1, len(x)):
        ch = x[i]-x[i-1]; g, l = max(ch, 0), max(-ch, 0)
        if i <= n: ag += g/n; al += l/n
        else: ag = (ag*(n-1)+g)/n; al = (al*(n-1)+l)/n
        if i >= n: o[i] = 100 if al == 0 else 100-100/(1+ag/al)
    return o
def bracket(bars, i, side, sl, tp, last):
    """enter at open of bar i; return gross return (fraction)."""
    e = bars[i][1]; stop = e - side*sl; targ = e + side*tp
    for j in range(i, len(bars)):
        tm, o, h, l, c = bars[j]
        if tm > last: return side*(o/e-1)
        if side == 1:
            if l <= stop: return (min(o, stop)/e-1)
            if h >= targ: return (max(o, targ) if j > i else targ)/e-1
        else:
            if h >= stop: return -(max(o, stop)/e-1)
            if l <= targ: return -((min(o, targ) if j > i else targ)/e-1)
    return side*(bars[-1][4]/e-1)
