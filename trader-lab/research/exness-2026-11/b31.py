exec(open('b28.py').read().split('# ---------------- A.')[0])
exec(open('b28.py').read().split('# ---------------- B. candle brain v2 ----------------')[1].split('for m in [')[0])  # candle_flags, exit_machine
random.seed(31)
NEW = dict(US30=('^DJI', 1000, 1.0), GER40=('^GDAXI', 1000, 1.5), UK100=('^FTSE', 1000, 2.0), JP225=('^N225', 1000, 2.0),
           GBPUSD=('GBPUSD=X', 1000, 1.5), USDJPY=('USDJPY=X', 1000, 1.2), SILVER=('SLV', 1850, 4.0), SPX=('^GSPC', 1022, 1.3))
for m, (s, u, b) in NEW.items():
    D[m] = series(s); USD[m] = u; BP[m] = b; START[m] = '2013-01-01'
def rsi2(C):
    out = [50.0]*len(C); up = dn = None
    for i in range(1, len(C)):
        ch = C[i]-C[i-1]; u_, d_ = max(ch, 0), max(-ch, 0)
        up = u_ if up is None else up+(u_-up)/2; dn = d_ if dn is None else dn+(d_-dn)/2
        out[i] = 100 if dn == 0 else 100-100/(1+up/dn)
    return out
print('=== A IBS other indices')
for m in ['US30', 'GER40', 'UK100', 'JP225']: sig_rule('A IBS %s' % m, m, ibs_sig(D[m]), 'index dip')
print('=== B turn of month')
def tom(X):
    ds = X['dates']; s = [0]*len(ds)
    for i in range(len(ds)-1):
        if ds[i][:7] != ds[i+1][:7]:
            for t in range(i-1, min(len(ds), i+3)): s[t] = 1
    return s
for m in ['US500', 'GER40']: sig_rule('B turn of month %s' % m, m, tom(D[m]), 'calendar')
print('=== C pre-holiday')
X = D['US500']; ds = X['dates']; s = [0]*len(ds)
for i in range(len(ds)-1):
    a, b = dt.date.fromisoformat(ds[i]), dt.date.fromisoformat(ds[i+1]); gap = [a+dt.timedelta(days=k) for k in range(1, (b-a).days)]
    if any(g.weekday() < 5 for g in gap) and i > 0: s[i-1] = 1    # position held over day i (the pre-holiday session)
sig_rule('C pre-holiday US500', 'US500', s, 'calendar')
print('=== D weekly IBS')
def weekly_ibs(X):
    ds, H, L, C = X['dates'], X['H'], X['L'], X['C']; s = [0]*len(ds); wk = {}
    for i, d in enumerate(ds): wk.setdefault(dt.date.fromisoformat(d).isocalendar()[:2], []).append(i)
    ks = sorted(wk)
    for a, b in zip(ks, ks[1:]):
        I = wk[a]; hi = max(H[i] for i in I); lo = min(L[i] for i in I); c = C[I[-1]]
        if hi > lo and (c-lo)/(hi-lo) < .2:
            for t in [I[-1]] + wk[b][:-1]: s[t] = 1   # held from the week's last close to the next week's last close
    return s
for m in ['USTEC', 'US500', 'BTC']: sig_rule('D weekly IBS %s' % m, m, weekly_ibs(D[m]), 'index dip' if m != 'BTC' else 'crypto dip')
print('=== E short side')
X = D['USTEC']; H, L, C = X['H'], X['L'], X['C']; s200 = sma(C, 200); s = []; p = 0
for i in range(len(C)):
    ib = (C[i]-L[i])/(H[i]-L[i]) if H[i] > L[i] else .5
    if p and C[i] < C[i-1]: p = 0
    elif not p and ib > .8 and s200[i] is not None and C[i] < s200[i]: p = -1
    s.append(p)
sig_rule('E USTEC IBS short below SMA200', 'USTEC', s, 'index short')
for m in ['BTC', 'ETH']:
    X = D[m]; s50 = sma(X['C'], 50)
    def wshort(bp, X=X, s50=s50):
        O, H, L, C = X['O'], X['H'], X['L'], X['C']; r = [0.0]*len(C)
        for t in range(1, len(C)):
            if s50[t-1] is None or C[t-1] >= s50[t-1]: continue
            lv = O[t]-.6*(H[t-1]-L[t-1])
            if L[t] <= lv: r[t] = 1-C[t]/lv-bp/1e4
        return r
    wshort.sides = [-1]*len(X['C'])
    day_rule('E %s Williams short below SMA50' % m, m, wshort, 'crypto short')
print('=== F pair GER40/US500')
A_, B_ = D['GER40'], D['SPX']; bm = dict(zip(B_['dates'], B_['C'])); ds = [d for d in A_['dates'] if d in bm]
am = dict(zip(A_['dates'], A_['C'])); lr = [math.log(am[d]/bm[d]) for d in ds]; n = len(ds)
def pair_pnl(sig, bp):
    out = [0.0]*n
    for t in range(1, n):
        p = sig[t-1]; prev = sig[t-2] if t > 1 else 0
        ra = am[ds[t]]/am[ds[t-1]]-1; rb_ = bm[ds[t]]/bm[ds[t-1]]-1
        out[t] = 1000*p*(ra-rb_) - abs(p-prev)*1000*(1.5+1.3)/2e4*(bp/1.0)
    return out
sig = [0]*n; p = 0
for t in range(20, n):
    w = lr[t-19:t+1]; mu = sum(w)/20; sd = (sum((x-mu)**2 for x in w)/19)**.5; z = (lr[t]-mu)/sd if sd else 0
    if p == 0 and z > 2: p = -1
    elif p == 0 and z < -2: p = 1
    elif (p == 1 and z >= 0) or (p == -1 and z <= 0): p = 0
    sig[t] = p
pn = pair_pnl(sig, 1.0); p2 = pair_pnl(sig, 2.0)
plc = [sum(x for d, x in zip(ds, pair_pnl(rot(sig, random.randint(60, n-60)), 1.0)) if d >= '2013-01-01') for _ in range(NP)]
keep = [i for i, d in enumerate(ds) if d >= '2013-01-01']
r = judge.verdict([ds[i] for i in keep], [pn[i] for i in keep], [p2[i] for i in keep], plc)
r.update(name='F pair GER40/US500', mkt='PAIR', fam='pair', map={ds[i]: pn[i] for i in keep}); RESULTS[r['name']] = r
print(judge.line(r['name'], r)); print('      ' + ' '.join('%s %+.0f' % (y, v) for y, v in sorted(r['years'].items())))
print('=== G NR7')
for m in ['BTC', 'ETH', 'USTEC', 'US500', 'US30', 'GER40', 'GOLD', 'SILVER']:
    X = D[m]; s50 = sma(X['C'], 50); allow_short = m not in ('USTEC', 'US500', 'US30'); sides = [0]*len(X['C'])
    def nr7(bp, X=X, s50=s50, allow_short=allow_short, sides=sides):
        O, H, L, C = X['O'], X['H'], X['L'], X['C']; r = [0.0]*len(C)
        for t in range(8, len(C)):
            k = t-1; R = [H[j]-L[j] for j in range(k-6, k+1)]
            if R[-1] > min(R) or s50[k] is None: continue
            if C[k] > s50[k] and H[t] >= H[k]: f = max(H[k], O[t]); r[t] = C[t]/f-1-bp/1e4; sides[t] = 1
            elif allow_short and C[k] < s50[k] and L[t] <= L[k]: f = min(L[k], O[t]); r[t] = 1-C[t]/f-bp/1e4; sides[t] = -1
        return r
    nr7.sides = sides; nr7(BP[m])
    day_rule('G NR7 %s' % m, m, nr7, 'contraction')
print('=== H FX RSI2')
for m in ['EURUSD', 'GBPUSD', 'USDJPY']:
    X = D[m]; C = X['C']; r2 = rsi2(C); s200 = sma(C, 200); s = []; p = 0
    for i in range(len(C)):
        if p == 1 and r2[i] > 50: p = 0
        elif p == -1 and r2[i] < 50: p = 0
        if p == 0 and s200[i] is not None:
            if r2[i] < 10 and C[i] > s200[i]: p = 1
            elif r2[i] > 90 and C[i] < s200[i]: p = -1
        s.append(p)
    sig_rule('H FX RSI2 %s' % m, m, s, 'fx')
print('=== I silver')
X = D['SILVER']; C = X['C']; s200 = sma(C, 200)
sig_rule('I silver IBS above SMA200', 'SILVER', ibs_sig(X, [s200[i] is not None and C[i] > s200[i] for i in range(len(C))]), 'silver')
day_rule('I silver Williams', 'SILVER', lambda bp: b12a.williams(D['SILVER'], 1, bp), 'silver')
prev = pickle.load(open('b30_all.pkl', 'rb')); allr = {**prev, **RESULTS}
W = sorted([r for r in allr.values() if r['worthy']], key=lambda r: -r['all_t']); chosen = []
print('\nWORTHY:', [r['name'] for r in W])
for r in W:
    cs = {c['name']: judge.corr(r['map'], c['map']) for c in chosen}; ok = all(not (x > .5) for x in cs.values())
    if ok: chosen.append(r)
    print('  %-34s max corr %.2f -> %s' % (r['name'], max(cs.values()) if cs else 0, 'DISTINCT' if ok else 'near-duplicate'))
pickle.dump(allr, open('b31_all.pkl', 'wb'))
