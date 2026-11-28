import sys, json, math, statistics, datetime as dt, numpy as np
sys.path.insert(0, '/home/user/day-trader-skill/trader-lab')
import catalog as C
Y = '/tmp/claude-0/-home-user/a2ae9b93-f4ce-530a-aef6-aecc10044afa/scratchpad/yahoo/'
def ld(sym, adj=True):
    d = json.load(open(Y+sym+'.json'))['chart']['result'][0]; q = d['indicators']['quote'][0]
    a = d['indicators'].get('adjclose', [{}])[0].get('adjclose')
    rows = []
    for i, t in enumerate(d['timestamp']):
        o, h, l, c, v = q['open'][i], q['high'][i], q['low'][i], q['close'][i], q['volume'][i]
        if None in (o, h, l, c) or o <= 0: continue
        f = a[i]/c if adj and a and a[i] else 1.0
        rows.append((dt.date.fromtimestamp(t).isoformat(), o*f, h*f, l*f, c*f, v or 0))
    D = {k: np.array([r[j] for r in rows], float) for j, k in enumerate(['_', 'o', 'h', 'l', 'c', 'v']) if k != '_'}
    D['d'] = [r[0] for r in rows]; D['month'] = np.array([int(x[5:7]) for x in D['d']])
    return D
# ---- B: lot sizing
last = {'US500': (ld('SPY')['c'][-1]*10, 0.14, 1), 'USTEC': (ld('QQQ')['c'][-1]*41, 0.05, 1)}
print('B. min-lot exposure (approx index level from ETF x ratio):')
for name, sym, lot, mult in [('US500', 'SPY', 0.14, 1), ('USTEC', 'QQQ', 0.05, 1), ('XAUUSD', 'GC=F', 0.01, 100), ('BTCUSD', 'BTC-USD', 0.01, 1), ('EURUSD', 'EURUSD=X', 0.01, 100000)]:
    D = ld(sym, adj=False); c = D['c']
    px = {'SPY': 6800/ c[-1] , 'QQQ': 25000/c[-1]}.get(sym, 1.0)  # scale ETF to index level
    exp = c[-1]*px*lot*mult
    r1 = min(c[i]/c[i-1]-1 for i in range(1, len(c))); r21 = min(c[i]/c[i-21]-1 for i in range(21, len(c)))
    pk = c[0]; mdd = 0
    for x in c: pk = max(pk, x); mdd = min(mdd, x/pk-1)
    print('  %-6s lot %.2f = $%6.0f exposure (%.1fx a $1,000 account) | worst day $%.0f, worst month $%.0f, worst peak-to-trough $%.0f' % (name, lot, exp, exp/1000, exp*r1, exp*r21, exp*mdd))
# ---- A: Coppock/TRIX 2000-2015
print('\nA. Coppock and TRIX on 2000-2015 (never used by the catalog pass), swap-free 1 bp:')
for rule in ('coppock', 'trix_15'):
    pooled = {}; per = {}
    for sym in ('SPY', 'QQQ', 'GC=F', 'EURUSD=X'):
        D = ld(sym, adj=(sym in ('SPY', 'QQQ')))
        pos = C.build(D)[rule][1]
        net, mkt = C.strategy_returns(D, pos, 0.5)
        idx = [i for i, d in enumerate(D['d']) if d < '2016-01-01' and not math.isnan(mkt[i]) and i > 300]
        x = np.array([mkt[i] for i in idx]); y = np.array([net[i] for i in idx]); beta = float(np.cov(y, x)[0, 1]/np.var(x))
        a = [net[i]-beta*mkt[i] for i in idx]; per[sym] = (round(C.tstat(a), 2), round(1e4*statistics.mean(a), 2), round(beta, 2))
        for i, v in zip(idx, a): pooled.setdefault(D['d'][i], []).append(v)
    P = [sum(v)/len(v) for d, v in sorted(pooled.items())]
    print('  %-8s pooled alpha t %.2f | per market (t, bp/day, beta): %s' % (rule, C.tstat(P), per))
