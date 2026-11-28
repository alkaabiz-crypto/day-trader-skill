exec(open('b31.py').read().split("print('=== A IBS other indices')")[0])
random.seed(32)
alts = ['ETH', 'LTC', 'XRP', 'BCH', 'ADA', 'SOL', 'DOGE', 'LINK', 'DOT', 'BNB']
AD = {c: series(c+'-USD') for c in alts}
def wfun(X, side, gate_n, bp):
    O, H, L, C = X['O'], X['H'], X['L'], X['C']; s = sma(C, gate_n); r = [0.0]*len(C)
    for t in range(1, len(C)):
        if s[t-1] is None: continue
        if side == 1 and C[t-1] > s[t-1]:
            lv = O[t]+.6*(H[t-1]-L[t-1])
            if H[t] >= lv: r[t] = C[t]/lv-1-bp/1e4
        if side == -1 and C[t-1] < s[t-1]:
            lv = O[t]-.6*(H[t-1]-L[t-1])
            if L[t] <= lv: r[t] = 1-C[t]/lv-bp/1e4
    return r
def nr7fun(X, bp, allow_short=True, sides=None):
    O, H, L, C = X['O'], X['H'], X['L'], X['C']; s50 = sma(C, 50); r = [0.0]*len(C)
    for t in range(8, len(C)):
        k = t-1; R = [H[j]-L[j] for j in range(k-6, k+1)]
        if R[-1] > min(R) or s50[k] is None: continue
        if C[k] > s50[k] and H[t] >= H[k]: f = max(H[k], O[t]); r[t] = C[t]/f-1-bp/1e4; sd = 1
        elif allow_short and C[k] < s50[k] and L[t] <= L[k]: f = min(L[k], O[t]); r[t] = 1-C[t]/f-bp/1e4; sd = -1
        else: continue
        if sides is not None: sides[t] = sd
    return r
def alt_basket(name, f, fam):
    def run(bp, rand=False):
        T = {}
        for c in alts:
            X = AD[c]; sides = [0]*len(X['C']); r = f(X, bp, sides)
            if rand:
                O, C = X['O'], X['C']; idx = [i for i in range(1, len(C))]; pick = random.sample(idx, sum(1 for v in r if v)); sd = [sides[i] or 1 for i in range(len(r)) if r[i]]
                r = [0.0]*len(C)
                for j, s_ in zip(pick, sd): r[j] = s_*(C[j]/O[j]-1)-bp/1e4
            for d, x in zip(X['dates'], r): T[d] = T.get(d, 0)+x*100
        return T
    T1 = run(5.0); T2 = run(10.0); ks = sorted(k for k in T1 if k >= '2022-01-01')
    plc = [sum(v for k, v in run(5.0, True).items() if k >= '2022-01-01') for _ in range(NP)]
    r = judge.verdict(ks, [T1[k] for k in ks], [T2[k] for k in ks], plc); r.update(name=name, mkt='ALTS', fam=fam, map={k: T1[k] for k in ks})
    RESULTS[name] = r; print(judge.line(name, r)); print('      ' + ' '.join('%s %+.0f' % (y, v) for y, v in sorted(r['years'].items())), flush=True)
def fill_sides(X, bp, sides, side):
    r = wfun(X, side, 50, bp)
    for i, v in enumerate(r):
        if v: sides[i] = side
    return r
alt_basket('Q1 alt Williams short basket', lambda X, bp, sides: fill_sides(X, bp, sides, -1), 'crypto short')
alt_basket('Q2 alt NR7 basket', lambda X, bp, sides: nr7fun(X, bp, True, sides), 'contraction')
for m in ['USTEC', 'US500', 'US30', 'GER40', 'JP225']:
    f = (lambda X: (lambda bp: wfun(X, 1, 50, bp)))(D[m]); day_rule('Q3 %s Williams long above SMA50' % m, m, f, 'index breakout')
for m in ['USTEC', 'US500']:
    X = D[m]; f = (lambda X: (lambda bp: wfun(X, -1, 200, bp)))(X); f.sides = [-1]*len(X['C']); day_rule('Q4 %s Williams short below SMA200' % m, m, f, 'index short')
X = D['GOLD']; f = lambda bp: wfun(D['GOLD'], -1, 50, bp); f.sides = [-1]*len(X['C']); day_rule('Q5 gold Williams short below SMA50', 'GOLD', f, 'gold')
for m in ['JP225', 'UK100']:
    X = D[m]; sides = [0]*len(X['C']); f = (lambda X, sides: (lambda bp: nr7fun(X, bp, True, sides)))(X, sides); f(BP[m]); f.sides = sides
    day_rule('Q6 NR7 %s' % m, m, f, 'contraction')
prev = pickle.load(open('b31_all.pkl', 'rb')); allr = {**prev, **RESULTS}
W = sorted([r for r in allr.values() if r['worthy']], key=lambda r: -r['all_t']); chosen = []
print('\nWORTHY:', [r['name'] for r in W])
for r in W:
    cs = {c['name']: judge.corr(r['map'], c['map']) for c in chosen}; ok = all(not (x > .5) for x in cs.values())
    if ok: chosen.append(r)
    top = max(cs.items(), key=lambda kv: kv[1]) if cs else ('-', 0)
    print('  %-36s max corr %.2f (%s) -> %s' % (r['name'], top[1], top[0][:20], 'DISTINCT' if ok else 'near-duplicate'))
pickle.dump(allr, open('b32_all.pkl', 'wb'))
