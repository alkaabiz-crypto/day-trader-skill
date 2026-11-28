import sys, gzip, json, os, datetime as dt, statistics, random
from zoneinfo import ZoneInfo
NY = ZoneInfo('America/New_York'); D0 = '/home/user/day-trader-skill/trader-lab/data/long/'
COST = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
def load(sym):
    d = json.load(gzip.open(D0+sym+'.json.gz')); days = {}
    for k in sorted(d, key=int):
        t = dt.datetime.fromtimestamp(int(k), NY); tm = t.hour*60+t.minute
        if 570 <= tm < 960: days.setdefault(t.date().isoformat(), []).append((tm,)+tuple(d[k][:5]))
    return days
syms = [f[:-8] for f in os.listdir(D0) if f.endswith('.json.gz')]
DATA = {s: load(s) for s in syms}
alldays = sorted({d for s in DATA for d in DATA[s]})
def sim(B, i, stop, targ):
    e = B[i][1]
    for tm, o, h, l, c, v in B[i:]:
        if tm >= 955: return o
        if l <= stop: return min(o, stop)
        if h >= targ: return max(o, targ)
    return B[-1][4]
def rule_outcome(B):
    """first breakout of the day (any time 9:50-14:20), for the Time Machine history: +1 target first, -1 stop first, 0 neither"""
    r = [b for b in B if b[0] < 585]
    if len(r) < 3: return None
    hi = max(b[2] for b in r); lo = min(b[3] for b in r); mid = (hi+lo)/2
    for k, b in enumerate(B):
        if 585 <= b[0] <= 860 and b[4] > hi and k+1 < len(B):
            e = B[k+1][1]; risk = e-mid
            if risk <= 0: return None
            x = sim(B, k+1, mid, e+2*risk)
            return 1 if x >= e+2*risk-1e-9 else (-1 if x <= mid+1e-9 else 0)
    return None
hist = {s: {} for s in syms}
for s in syms:
    for d, B in DATA[s].items(): hist[s][d] = rule_outcome(B)
def run(tm_gate, start='2024-01-02'):
    eq = 1000.0; pk = eq; mdd = 0; trades = []; daily = {}
    for di, d in enumerate(alldays):
        if d < start: continue
        taken = set(); day_pnl = 0.0; n_day = 0
        for dec in (617, 677, 737, 797, 857):   # 10:17 ... 14:17
            if n_day >= 5 or day_pnl <= -30: break
            cands = []
            for s in syms:
                B = DATA[s].get(d)
                if not B or s in taken or len(B) < 70: continue
                r = [b for b in B if b[0] < 585]; hi = max(b[2] for b in r); lo = min(b[3] for b in r); mid = (hi+lo)/2
                upto = [b for b in B if b[0] + 5 <= dec]
                if not upto or upto[-1][4] <= hi: continue
                if not any(b[4] > hi for b in upto if b[0] >= 585): continue
                if tm_gate:
                    past = [hist[s][x] for x in alldays[max(0, di-59):di] if x in hist[s] and hist[s][x] is not None]
                    if not past or sum(1 for x in past if x == 1) < sum(1 for x in past if x == -1): continue
                val = sum(b[4]*b[5] for b in upto)
                k = next((j for j, b in enumerate(B) if b[0] >= dec - 2), None)  # next bar open after the decision
                if k is None: continue
                cands.append((val, s, B, k, mid))
            for val, s, B, k, mid in sorted(cands, reverse=True)[:2]:
                if n_day >= 5: break
                e = B[k][1]; risk = e - mid
                if risk <= e*0.001: continue
                sh = min(10/risk, 1000/e); x = sim(B, k, mid, e+2*risk)
                pnl = sh*(x-e) - sh*e*COST/1e4
                trades.append(pnl); day_pnl += pnl; n_day += 1; taken.add(s)
        if n_day:
            eq += day_pnl; pk = max(pk, eq); mdd = min(mdd, eq-pk); daily[d] = day_pnl
    dv = list(daily.values())
    t = statistics.mean(dv)/statistics.stdev(dv)*len(dv)**.5 if len(dv) > 2 else 0
    print('%-28s trades %4d | won %2.0f%% | net $%+.0f | $ a trade %+.2f | worst drop $%.0f | daily t %.2f | end equity $%.0f' % (
        ('with Time Machine gate' if tm_gate else 'scanner>entry>exit>size>risk') + ' @%gbp' % COST, len(trades),
        100*sum(p > 0 for p in trades)/max(1, len(trades)), sum(trades), sum(trades)/max(1, len(trades)), mdd, t, eq), flush=True)
run(False); run(True)
