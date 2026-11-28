exec(open('b28.py').read().split('# ---------------- A.')[0])
random.seed(29)
src = open('b27.py').read().split("eth = binance")[0]; g = {}; exec(src, g); rb = g['range_break']
def hourly_rule(name, sym, usd, bp, start):
    H = g['binance'](sym)
    def run(b):
        T = rb(H, 0, 480, 480, 1200, 1380, b); P = {}
        for ei, xi, s, e, x, c in T: P[H['day'][xi]] = P.get(H['day'][xi], 0)+usd*(s*(x/e-1)-c/1e4)
        return T, P
    T, P = run(bp); _, P2 = run(2*bp); days = [d for d in sorted(set(H['day'])) if d >= start]; n = len(H['c']); plc = []
    for _ in range(NP):
        tot = 0.0
        for ei, xi, s, e, x, c in T:
            if H['day'][xi] < start: continue
            L = xi-ei
            for _t in range(50):
                j = random.randrange(0, n-L-1)
                if H['day'][j] == H['day'][j+L] and H['day'][j] >= start: break
            tot += usd*(s*(H['c'][j+L]/H['c'][j]-1)-c/1e4)
        plc.append(tot)
    r = judge.verdict(days, [P.get(d, 0) for d in days], [P2.get(d, 0) for d in days], plc)
    r.update(name=name, mkt=sym, fam='crypto intraday', map={d: P.get(d, 0) for d in days}); RESULTS[name] = r
    print(judge.line(name, r)); print('      ' + ' '.join('%s %+.0f' % (y, v) for y, v in sorted(r['years'].items())), flush=True)
    pre = [P.get(d, 0) for d in days if d < '2024-01-01']; print('      pre-2024 worst drop $%.0f' % judge.worst_drop(pre))
hourly_rule('N1 ETH London breakout 0.2 lot', 'ETHUSDT', 330, 8.0, '2018-01-01')
hourly_rule('N2 BTC London breakout 0.01 lot', 'BTCUSDT', 595, 1.9, '2018-01-01')
X = D['GOLD']; C = X['C']; s200 = sma(C, 200)
sig_rule('N3 gold IBS above SMA200', 'GOLD', ibs_sig(X, [s200[i] is not None and C[i] > s200[i] for i in range(len(C))]), 'gold')
ds = X['dates']; tom = [0]*len(C)
for i in range(len(ds)-1):
    if ds[i][:7] != ds[i+1][:7]:          # i = last trading day of the month
        for t in range(i-1, min(len(C), i+3)): tom[t] = 1   # hold from close i-1 through close i+3 (3rd day of new month)
sig_rule('N4 gold turn of month', 'GOLD', tom, 'gold')
day_rule('N5 gold Williams (GLD bars)', 'GOLD', lambda bp: b12a.williams(D['GOLD'], 1, bp), 'gold')
day_rule('N6 oil Williams (USO bars)', 'OIL', lambda bp: b12a.williams(D['OIL'], 1, bp), 'oil')
pickle.dump(RESULTS, open('b29_out.pkl', 'wb'))
