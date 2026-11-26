import sys, math, random, statistics, numpy as np
sys.path.insert(0, '/home/user/day-trader-skill/trader-lab')
import catalog as C
random.seed(5)
data = {m: C.load(m) for m in C.MARKETS}
def alpha_series(D, pos, cost, swap_day):
    net, mkt = C.strategy_returns(D, pos, cost)
    if swap_day:
        d = D['d']; p = pos.astype(float)
        for i in range(len(d)-2):
            import datetime as dt
            n = (dt.date.fromisoformat(d[i+2]) - dt.date.fromisoformat(d[i+1])).days
            net[i] -= max(p[i], 0) * swap_day * n
    ins = [(net[i], mkt[i]) for i, x in enumerate(D['d']) if x < C.SPLIT and not math.isnan(mkt[i])]
    if len(ins) <= 250: ins = [(net[i], mkt[i]) for i in range(min(len(D['d']), 400)) if not math.isnan(mkt[i])]
    x = np.array([q[1] for q in ins]); y = np.array([q[0] for q in ins])
    beta = float(np.cov(y, x)[0, 1] / np.var(x))
    return {D['d'][i]: (net[i] - beta*mkt[i], net[i]) for i in range(len(D['d'])) if not math.isnan(mkt[i])}
for rule in ('coppock', 'trix_15'):
    for acct in ('swapfree', 'standard'):
        per = {}; pos_by = {}
        for m, D in data.items():
            cr = m.endswith('-USD'); cost = 0.75 if cr else 0.5
            sw = 0 if acct == 'swapfree' else (3e-4 if cr else 0.065/360)
            pos = C.build(D)[rule][1]; pos_by[m] = pos
            per[m] = alpha_series(D, pos, cost, sw)
        def pooled(per):
            days = {}
            for m, s in per.items():
                for d, (a, n) in s.items(): days.setdefault(d, []).append(a)
            return [(d, sum(v)/len(v)) for d, v in sorted(days.items())]
        P = pooled(per); J = [v for d, v in P if d >= C.SPLIT]
        h1 = [v for d, v in P if C.SPLIT <= d < '2021-01-01']; h2 = [v for d, v in P if d >= '2021-01-01']
        print('\n%s %s pooled judged t %.2f | 2016-20 t %.2f | 2021-26 t %.2f' % (rule, acct, C.tstat(J), C.tstat(h1), C.tstat(h2)))
        print('  per market judged t:', {m: round(C.tstat([a for d, (a, n) in s.items() if d >= C.SPLIT]), 2) for m, s in per.items()})
        if acct == 'swapfree':
            real = statistics.mean(J); beats = 0
            for _ in range(500):
                pp = {}
                for m, D in data.items():
                    p = pos_by[m]; k = random.randrange(50, len(p)-50); cr = m.endswith('-USD')
                    pp[m] = alpha_series(D, np.concatenate([p[k:], p[:k]]), 0.75 if cr else 0.5, 0)
                if statistics.mean([v for d, v in pooled(pp) if d >= C.SPLIT]) < real: beats += 1
            print('  placebo beats %.1f%%' % (beats/5))
        b = per['BTC-USD']; v = 1000.0; pk = v; dd = 0
        for d in sorted(b):
            if d >= '2024-01-01': v *= 1 + b[d][1]; pk = max(pk, v); dd = min(dd, v/pk-1)
        print('  BTC only, $1,000 from 2024: $%d, worst drop %.0f%%' % (v, dd*100))
D = data['BTC-USD']; o = D['o']; i0 = next(i for i, d in enumerate(D['d']) if d >= '2024-01-01')
print('\nBTC held from 2024: $%d' % (1000*o[-1]/o[i0+1]))
