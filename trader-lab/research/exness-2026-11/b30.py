exec(open('b29.py').read().split("hourly_rule('N1")[0])
random.seed(30)
def basket_hourly(name, syms, usd, bp, start, rf, rt, tf, tt, out):
    Hs = {s: g['binance'](s) for s in syms}
    def run(b):
        P = {}; Ts = {}
        for s, H in Hs.items():
            T = rb(H, rf, rt, tf, tt, out, b); Ts[s] = T
            for ei, xi, sd, e, x, c in T: P[H['day'][xi]] = P.get(H['day'][xi], 0)+usd*(sd*(x/e-1)-c/1e4)
        return Ts, P
    Ts, P = run(bp); _, P2 = run(2*bp); days = sorted(d for d in set().union(*[set(H['day']) for H in Hs.values()]) if d >= start); plc = []
    for _ in range(NP):
        tot = 0.0
        for s, T in Ts.items():
            H = Hs[s]; n = len(H['c'])
            for ei, xi, sd, e, x, c in T:
                if H['day'][xi] < start: continue
                L = xi-ei
                for _t in range(50):
                    j = random.randrange(0, n-L-1)
                    if H['day'][j] == H['day'][j+L] and H['day'][j] >= start: break
                tot += usd*(sd*(H['c'][j+L]/H['c'][j]-1)-c/1e4)
        plc.append(tot)
    r = judge.verdict(days, [P.get(d, 0) for d in days], [P2.get(d, 0) for d in days], plc)
    r.update(name=name, mkt='+'.join(syms), fam='crypto intraday', map={d: P.get(d, 0) for d in days}); RESULTS[name] = r
    print(judge.line(name, r)); print('      ' + ' '.join('%s %+.0f' % (y, v) for y, v in sorted(r['years'].items())), flush=True)
basket_hourly('N1 ETH London breakout 0.2 lot', ['ETHUSDT'], 330, 8.0, '2018-01-01', 0, 480, 480, 1200, 1380)
basket_hourly('P1 alt London breakout basket', ['XRPUSDT', 'LTCUSDT', 'BNBUSDT', 'ADAUSDT', 'LINKUSDT', 'BCHUSDT'], 100, 8.0, '2020-01-01', 0, 480, 480, 1200, 1380)
basket_hourly('P2 BTC US-session breakout', ['BTCUSDT'], 595, 1.9, '2018-01-01', 0, 780, 780, 1200, 1380)
basket_hourly('P3 ETH US-session breakout', ['ETHUSDT'], 330, 8.0, '2018-01-01', 0, 780, 780, 1200, 1380)
prev = pickle.load(open('b28_out.pkl', 'rb'))
allr = {**prev, **RESULTS}
W = sorted([r for r in allr.values() if r['worthy']], key=lambda r: -r['all_t'])
print('\nWORTHY:', [r['name'] for r in W])
chosen = []
for r in W:
    cs = {c['name']: judge.corr(r['map'], c['map']) for c in chosen}
    ok = all(not (x > judge.BAR['max_corr']) for x in cs.values())
    if ok: chosen.append(r)
    print('  %-34s corr %s -> %s' % (r['name'], ', '.join('%s %.2f' % (k[:14], v) for k, v in cs.items()), 'DISTINCT' if ok else 'near-duplicate'))
pickle.dump(allr, open('b30_all.pkl', 'wb'))
