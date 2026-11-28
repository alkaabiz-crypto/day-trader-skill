exec(open('b33.py').read().split("for nm, sym, usd, bp in [('R1")[0])
exec(open('b32.py').read().split("def alt_basket")[0].split("AD = {c: series(c+'-USD') for c in alts}")[1])  # wfun, nr7fun
random.seed(34)
def weekly_will2(X, bp, side, gate=None, minlen=7):
    ds, O, H, L, C = X['dates'], X['O'], X['H'], X['L'], X['C']; wk = {}
    for i, d in enumerate(ds): wk.setdefault(dt.date.fromisoformat(d).isocalendar()[:2], []).append(i)
    ks = sorted(wk); r = [0.0]*len(C)
    for a, b in zip(ks, ks[1:]):
        I, J = wk[a], wk[b]
        if len(I) < minlen or len(J) < minlen: continue
        if gate is not None and not gate(I[-1]): continue
        rg = max(H[i] for i in I)-min(L[i] for i in I); lv = O[J[0]]+side*.6*rg
        for j in J:
            if (side == 1 and H[j] >= lv) or (side == -1 and L[j] <= lv):
                f = max(lv, O[j]) if side == 1 else min(lv, O[j]); r[J[-1]] = side*(C[J[-1]]/f-1)-bp/1e4; break
    return r
X = D['BTC']; s140 = sma(X['C'], 140)
f = lambda b: weekly_will2(D['BTC'], b, -1, lambda i: s140[i] is not None and D['BTC']['C'][i] < s140[i]); f.sides = [-1]*len(X['C'])
day_rule('S1 BTC weekly Williams short', 'BTC', f, 'crypto short')
def nr4(X, bp, sides):
    O, H, L, C = X['O'], X['H'], X['L'], X['C']; s50 = sma(C, 50); r = [0.0]*len(C)
    for t in range(5, len(C)):
        k = t-1; R = [H[j]-L[j] for j in range(k-3, k+1)]
        if R[-1] > min(R) or s50[k] is None: continue
        if C[k] > s50[k] and H[t] >= H[k]: f_ = max(H[k], O[t]); r[t] = C[t]/f_-1-bp/1e4; sides[t] = 1
        elif C[k] < s50[k] and L[t] <= L[k]: f_ = min(L[k], O[t]); r[t] = 1-C[t]/f_-bp/1e4; sides[t] = -1
    return r
sd = [0]*len(D['BTC']['C']); f = lambda b: nr4(D['BTC'], b, sd); f(BP['BTC']); f.sides = sd
day_rule('S3 BTC NR4', 'BTC', f, 'contraction')
day_rule('S11 gold weekly Williams', 'GOLD', lambda b: weekly_will2(D['GOLD'], b, 1, None, 4), 'gold')
for m in ['USTEC', 'US500']:
    X = D[m]; s200 = sma(X['C'], 200)
    day_rule('S12 %s weekly Williams' % m, m, (lambda X, s200: (lambda b: weekly_will2(X, b, 1, lambda i: s200[i] is not None and X['C'][i] > s200[i], 4)))(X, s200), 'index breakout')
prev = pickle.load(open('b33_all.pkl', 'rb')); allr = {**prev, **RESULTS}
def wk(m):
    o = {}
    for d, v in m.items():
        k = dt.date.fromisoformat(d).isocalendar()[:2]; o[k] = o.get(k, 0)+v
    return o
W = sorted([r for r in allr.values() if r['worthy']], key=lambda r: -r['all_t']); chosen = []
print('\nWORTHY:', [r['name'] for r in W])
for r in W:
    cs = {c['name']: max(judge.corr(r['map'], c['map']), judge.corr(wk(r['map']), wk(c['map']))) for c in chosen}; ok = all(not (x > .5) for x in cs.values())
    if ok: chosen.append(r)
    top = max(cs.items(), key=lambda kv: kv[1]) if cs else ('-', 0)
    print('  %-36s max corr %.2f (%s) -> %s' % (r['name'], top[1], top[0][:20], 'DISTINCT' if ok else 'near-duplicate'))
pickle.dump(allr, open('b34_all.pkl', 'wb'))
