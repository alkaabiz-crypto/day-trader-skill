exec(open('b30.py').read().split("basket_hourly('N1")[0])
random.seed(33)
def four_hour(H):
    out = dict(day=[], m=[], o=[], h=[], l=[], c=[], last=[]); cur = None
    for i in range(len(H['c'])):
        key = (H['day'][i], H['m'][i]//240)
        if key != cur:
            cur = key; out['day'].append(H['day'][i]); out['m'].append((H['m'][i]//240)*240); out['o'].append(H['o'][i]); out['h'].append(H['h'][i]); out['l'].append(H['l'][i]); out['c'].append(H['c'][i])
        else:
            out['h'][-1] = max(out['h'][-1], H['h'][i]); out['l'][-1] = min(out['l'][-1], H['l'][i]); out['c'][-1] = H['c'][i]
    n = len(out['c']); out['last'] = [i == n-1 or out['day'][i+1] != out['day'][i] for i in range(n)]
    return out
def nr7_4h(B, bp):
    tr = g['daily_trend'](B, 50); T = []; n = len(B['c']); i = 7
    while i < n-1:
        k = i; R = [B['h'][j]-B['l'][j] for j in range(k-6, k+1)]; t = k+1
        if R[-1] <= min(R) and tr[t] and B['day'][t] == B['day'][k]:
            s = tr[t]; hi, lo = B['h'][k], B['l'][k]
            if (s == 1 and B['h'][t] >= hi) or (s == -1 and B['l'][t] <= lo):
                e = max(hi, B['o'][t]) if s == 1 else min(lo, B['o'][t]); stop = lo if s == 1 else hi; x = None; j = t
                while True:
                    if (s == 1 and B['l'][j] <= stop) or (s == -1 and B['h'][j] >= stop):
                        x = stop if j == t else (min(B['o'][j], stop) if s == 1 else max(B['o'][j], stop)); break
                    if B['last'][j] or j == n-1: x = B['c'][j]; break
                    j += 1
                T.append((t, j, s, e, x, bp)); i = j+1; continue
        i += 1
    return T
def judge_trades(name, B, Tf, usd, bp, start, fam):
    def run(b):
        T = Tf(b); P = {}
        for ei, xi, s, e, x, c in T: P[B['day'][xi]] = P.get(B['day'][xi], 0)+usd*(s*(x/e-1)-c/1e4)
        return T, P
    T, P = run(bp); _, P2 = run(2*bp); days = [d for d in sorted(set(B['day'])) if d >= start]; n = len(B['c']); plc = []
    for _ in range(NP):
        tot = 0.0
        for ei, xi, s, e, x, c in T:
            if B['day'][xi] < start: continue
            L = xi-ei
            for _t in range(50):
                j = random.randrange(0, n-L-1)
                if B['day'][j] == B['day'][j+L] and B['day'][j] >= start: break
            tot += usd*(s*(B['c'][j+L]/B['c'][j]-1)-c/1e4)
        plc.append(tot)
    r = judge.verdict(days, [P.get(d, 0) for d in days], [P2.get(d, 0) for d in days], plc)
    r.update(name=name, mkt=name, fam=fam, map={d: P.get(d, 0) for d in days}); RESULTS[name] = r
    print(judge.line(name, r), '| trades %d' % len(T)); print('      ' + ' '.join('%s %+.0f' % (y, v) for y, v in sorted(r['years'].items())), flush=True)
for nm, sym, usd, bp in [('R1 BTC 4h NR7', 'BTCUSDT', 595, 1.9), ('R2 ETH 4h NR7 0.2 lot', 'ETHUSDT', 330, 8.0)]:
    B = four_hour(g['binance'](sym)); judge_trades(nm, B, (lambda B: (lambda b: nr7_4h(B, b)))(B), usd, bp, '2018-01-01', 'contraction')
# weekly Williams on daily bars (UTC days, Monday-Sunday weeks)
def weekly_will(X, bp):
    ds, O, H, L, C = X['dates'], X['O'], X['H'], X['L'], X['C']; wk = {}
    for i, d in enumerate(ds): wk.setdefault(dt.date.fromisoformat(d).isocalendar()[:2], []).append(i)
    ks = sorted(wk); r = [0.0]*len(C)
    for a, b in zip(ks, ks[1:]):
        I, J = wk[a], wk[b]
        if len(I) < 7 or len(J) < 7: continue
        rg = max(H[i] for i in I)-min(L[i] for i in I); lv = O[J[0]]+.6*rg
        for j in J:
            if H[j] >= lv:
                f = max(lv, O[j]); r[J[-1]] = C[J[-1]]/f-1-bp/1e4; break
    return r
for nm, m, usd in [('R3 BTC weekly Williams', 'BTC', 595), ('R4 ETH weekly Williams 0.2 lot', 'ETH', 330)]:
    USD[m] = usd; day_rule(nm, m, (lambda X: (lambda b: weekly_will(X, b)))(D[m]), 'crypto breakout')
prev = pickle.load(open('b32_all.pkl', 'rb')); allr = {**prev, **RESULTS}
W = sorted([r for r in allr.values() if r['worthy']], key=lambda r: -r['all_t']); chosen = []
print('\nWORTHY:', [r['name'] for r in W])
for r in W:
    cs = {c['name']: judge.corr(r['map'], c['map']) for c in chosen}; ok = all(not (x > .5) for x in cs.values())
    if ok: chosen.append(r)
    top = max(cs.items(), key=lambda kv: kv[1]) if cs else ('-', 0)
    print('  %-36s max corr %.2f (%s) -> %s' % (r['name'], top[1], top[0][:20], 'DISTINCT' if ok else 'near-duplicate'))
pickle.dump(allr, open('b33_all.pkl', 'wb'))
