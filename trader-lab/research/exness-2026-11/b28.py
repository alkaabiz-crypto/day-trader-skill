# Batch 28: scorecard on the judge.py WORTHY bar + candle brain v2 + oil brain v2 (see PREREG batch 28)
import io, contextlib, random, json, datetime as dt, math, pickle, sys, bisect
sys.path.insert(0, '/home/user/day-trader-skill/trader-lab')
import judge
with contextlib.redirect_stdout(io.StringIO()):
    from b16 import series, close_rule
    import b12a
    from b17cd import volsig
    from engine import turtle, sma
random.seed(28)
NP = 200
USD = dict(USTEC=1336, US500=1022, BTC=595, ETH=500, GOLD=3640, OIL=831, EURUSD=1097)
BP = dict(USTEC=.9, US500=1.3, BTC=1.9, ETH=8.0, GOLD=1.5, OIL=6.0, EURUSD=1.2)
START = dict(USTEC='2013-01-01', US500='2013-01-01', BTC='2016-01-01', ETH='2018-01-01', GOLD='2013-01-01', OIL='2013-01-01', EURUSD='2013-01-01')
SYM = dict(USTEC='QQQ', US500='SPY', BTC='BTC-USD', ETH='ETH-USD', GOLD='GLD', OIL='USO', EURUSD='EURUSD=X')
D = {m: series(s) for m, s in SYM.items()}

def rot(a, k): return a[-k:]+a[:-k] if k else a

RESULTS = {}
def finish(name, mkt, ds, pnl, pnl2, plc, fam):
    st = START[mkt]
    keep = [i for i, d in enumerate(ds) if d >= st]
    dd = [ds[i] for i in keep]; p = [pnl[i] for i in keep]; p2 = [pnl2[i] for i in keep]
    r = judge.verdict(dd, p, p2, plc)
    r.update(name=name, mkt=mkt, fam=fam, map=dict(zip(dd, p)), trades=None)
    RESULTS[name] = r
    print(judge.line(name, r), flush=True)
    print('      ' + ' '.join('%s %+.0f' % (y, v) for y, v in sorted(r['years'].items())), flush=True)
    return r

def sig_rule(name, mkt, sig, fam):
    """position held from close t-1 to close t = sig[t-1]; placebo = rotated signal."""
    X = D[mkt]; u, bp = USD[mkt], BP[mkt]; ds = X['dates']; st = START[mkt]
    pn = [x*u for x in close_rule(X, sig, bp)]; p2 = [x*u for x in close_rule(X, sig, 2*bp)]
    n = len(sig); plc = []
    for _ in range(NP):
        r = close_rule(X, rot(sig, random.randint(60, n-60)), bp)
        plc.append(sum(x*u for d, x in zip(ds, r) if d >= st))
    return finish(name, mkt, ds, pn, p2, plc, fam)

def day_rule(name, mkt, rfun, fam):
    """rfun(bp) -> per-day returns of day trades; placebo = same count of random days, same side mix, open->close."""
    X = D[mkt]; u, bp = USD[mkt], BP[mkt]; ds = X['dates']; st = START[mkt]
    r = rfun(bp); pn = [x*u for x in r]; p2 = [x*u for x in rfun(2*bp)]
    O, C = X['O'], X['C']; idx = [i for i in range(1, len(C)) if ds[i] >= st]
    trades = [(i, 1 if r[i] > -bp/1e4*1.0001 or True else 1) for i in range(len(r)) if r[i] != 0 and ds[i] >= st]
    # side of each trade: recover from the rule's sign series if given
    sides = getattr(rfun, 'sides', None)
    plc = []
    for _ in range(NP):
        pick = random.sample(idx, len(trades)); tot = 0.0
        for j, (i, _s) in zip(pick, trades):
            s = sides[i] if sides else 1
            tot += u*(s*(C[j]/O[j]-1) - bp/1e4)
        plc.append(tot)
    return finish(name, mkt, ds, pn, p2, plc, fam)

def ibs_sig(X, gate=None):
    H, L, C = X['H'], X['L'], X['C']; s = []; p = 0
    for i in range(len(C)):
        ib = (C[i]-L[i])/(H[i]-L[i]) if H[i] > L[i] else .5
        if p and C[i] > C[i-1]: p = 0
        elif not p and ib < .2 and (gate is None or gate[i]): p = 1
        s.append(p)
    return s

# ---------------- A. scorecard of existing candidates ----------------
print('=== A. existing candidates', flush=True)
sig_rule('USTEC IBS', 'USTEC', ibs_sig(D['USTEC']), 'index dip')
sig_rule('US500 IBS', 'US500', ibs_sig(D['US500']), 'index dip')
def will(mkt):
    f = lambda bp: b12a.williams(D[mkt], 1, bp); return f
day_rule('BTC Williams', 'BTC', will('BTC'), 'crypto breakout')
sig_rule('Calm USTEC (vol < 20%)', 'USTEC', volsig(D['USTEC'], .2), 'index trend')
sig_rule('BTC Donchian 20/10', 'BTC', turtle(20, 10)(D['BTC'], False), 'crypto trend')
C_ = D['ETH']['C']; sig_rule('ETH 7-day momentum', 'ETH', [1 if i >= 7 and C_[i] > C_[i-7] else 0 for i in range(len(C_))], 'crypto trend')

# coin basket ($100 per coin, 10 alts, 5 bp), judged 2022 on like batch 24b; placebo random days per coin
alts = ['ETH', 'LTC', 'XRP', 'BCH', 'ADA', 'SOL', 'DOGE', 'LINK', 'DOT', 'BNB']
AD = {c: series(c+'-USD') for c in alts}
def basket(bp, rand=False):
    T = {}
    for c in alts:
        X = AD[c]; r = b12a.williams(X, 1, bp)
        if rand: r = b12a.rand_days(X, r, 1)(bp)
        for d, x in zip(X['dates'], r): T[d] = T.get(d, 0)+x*100
    return T
T1 = basket(5.0); T2 = basket(10.0); ks = sorted(k for k in T1 if k >= '2022-01-01')
plc = [sum(v for k, v in basket(5.0, True).items() if k >= '2022-01-01') for _ in range(NP)]
r = judge.verdict(ks, [T1[k] for k in ks], [T2[k] for k in ks], plc); r.update(name='Coin Williams basket', mkt='ALTS', fam='crypto breakout', map={k: T1[k] for k in ks})
RESULTS[r['name']] = r; print(judge.line(r['name'], r)); print('      ' + ' '.join('%s %+.0f' % (y, v) for y, v in sorted(r['years'].items())), flush=True)

# ETH London breakout, hourly Binance, $500, 8 bp
src = open('/tmp/claude-0/-home-user/a2ae9b93-f4ce-530a-aef6-aecc10044afa/scratchpad/lab/b27.py').read().split("eth = binance")[0]
g = {}; exec(src, g)
eth = g['binance']('ETHUSDT'); rb = g['range_break']
def eth_daily(bp):
    T = rb(eth, 0, 480, 480, 1200, 1380, bp); P = {}
    for ei, xi, s, e, x, c in T: P[eth['day'][xi]] = P.get(eth['day'][xi], 0)+500*(s*(x/e-1)-c/1e4)
    return T, P
T, P = eth_daily(8.0); _, P2 = eth_daily(16.0)
days = sorted(set(eth['day'])); days = [d for d in days if d >= '2018-01-01']
n = len(eth['c']); plc = []
for _ in range(NP):
    tot = 0.0
    for ei, xi, s, e, x, c in T:
        if eth['day'][xi] < '2018-01-01': continue
        L = xi-ei
        for _t in range(50):
            j = random.randrange(0, n-L-1)
            if eth['day'][j] == eth['day'][j+L] and eth['day'][j] >= '2018-01-01': break
        tot += 500*(s*(eth['c'][j+L]/eth['c'][j]-1)-c/1e4)
    plc.append(tot)
r = judge.verdict(days, [P.get(d, 0) for d in days], [P2.get(d, 0) for d in days], plc)
r.update(name='ETH London breakout', mkt='ETH', fam='crypto intraday', map={d: P.get(d, 0) for d in days})
RESULTS[r['name']] = r; print(judge.line(r['name'], r)); print('      ' + ' '.join('%s %+.0f' % (y, v) for y, v in sorted(r['years'].items())), flush=True)

# ---------------- B. candle brain v2 ----------------
print('=== B. candle brain v2', flush=True)
def candle_flags(X):
    O, H, L, C = X['O'], X['H'], X['L'], X['C']; n = len(C); bull = [False]*n; bear = [False]*n
    for t in range(2, n):
        R = H[t]-L[t]
        if R <= 0: continue
        body = abs(C[t]-O[t]); uw = H[t]-max(O[t], C[t]); lw = min(O[t], C[t])-L[t]
        R1 = H[t-1]-L[t-1]; b1 = abs(C[t-1]-O[t-1]); R2 = H[t-2]-L[t-2]; b2 = abs(C[t-2]-O[t-2])
        hammer = lw >= 2*body and lw >= .6*R and uw <= .15*R
        dragon = body <= .1*R and lw >= .6*R and uw <= .1*R
        star = uw >= 2*body and uw >= .6*R and lw <= .15*R
        grave = body <= .1*R and uw >= .6*R and lw <= .1*R
        bull_eng = C[t-1] < O[t-1] and C[t] > O[t] and O[t] <= C[t-1] and C[t] >= O[t-1]
        bear_eng = C[t-1] > O[t-1] and C[t] < O[t] and O[t] >= C[t-1] and C[t] <= O[t-1]
        bull_har = C[t-1] < O[t-1] and C[t] > O[t] and O[t] >= C[t-1] and C[t] <= O[t-1] and R1 > 0 and b1 >= .5*R1
        bear_har = C[t-1] > O[t-1] and C[t] < O[t] and O[t] <= C[t-1] and C[t] >= O[t-1] and R1 > 0 and b1 >= .5*R1
        pierce = C[t-1] < O[t-1] and O[t] < C[t-1] and (C[t-1]+O[t-1])/2 < C[t] < O[t-1]
        dark = C[t-1] > O[t-1] and O[t] > C[t-1] and O[t-1] < C[t] < (C[t-1]+O[t-1])/2
        avgR = (R+R1+R2)/3
        tw_b = C[t-1] < O[t-1] and C[t] > O[t] and abs(L[t]-L[t-1]) <= .05*avgR
        tw_t = C[t-1] > O[t-1] and C[t] < O[t] and abs(H[t]-H[t-1]) <= .05*avgR
        mstar = R2 > 0 and C[t-2] < O[t-2] and b2 >= .6*R2 and R1 > 0 and b1 <= .3*R1 and C[t] > O[t] and C[t] > (O[t-2]+C[t-2])/2
        estar = R2 > 0 and C[t-2] > O[t-2] and b2 >= .6*R2 and R1 > 0 and b1 <= .3*R1 and C[t] < O[t] and C[t] < (O[t-2]+C[t-2])/2
        bull[t] = hammer or dragon or bull_eng or bull_har or pierce or tw_b or mstar
        bear[t] = star or grave or bear_eng or bear_har or dark or tw_t or estar
    return bull, bear

def exit_machine(X, entry, side, maxd=5):
    C = X['C']; s = []; p = 0; age = 0
    for i in range(len(C)):
        if p:
            age += 1
            if (side == 1 and C[i] > C[i-1]) or (side == -1 and C[i] < C[i-1]) or age >= maxd: p = 0
        if not p and entry[i]: p = side; age = 0
        s.append(p)
    return s

for m in ['USTEC', 'US500', 'BTC', 'ETH', 'GOLD', 'OIL', 'EURUSD']:
    X = D[m]; C = X['C']; bull, bear = candle_flags(X); s200 = sma(C, 200)
    lo10 = [i >= 9 and C[i] <= min(C[i-9:i+1]) for i in range(len(C))]
    hi10 = [i >= 9 and C[i] >= max(C[i-9:i+1]) for i in range(len(C))]
    e1 = [bull[i] and lo10[i] and s200[i] is not None and C[i] > s200[i] for i in range(len(C))]
    sig_rule('CB1 %s bull candle at 10d low' % m, m, exit_machine(X, e1, 1), 'candle')
    if m not in ('USTEC', 'US500'):
        e2 = [bear[i] and hi10[i] and s200[i] is not None and C[i] < s200[i] for i in range(len(C))]
        sig_rule('CB2 %s bear candle at 10d high' % m, m, exit_machine(X, e2, -1), 'candle')
    # CB3 inside-day breakout
    s50 = sma(C, 50); H, L, O = X['H'], X['L'], X['O']; allow_short = m not in ('USTEC', 'US500')
    sides = [0]*len(C)
    def cb3(bp, X=X, s50=s50, allow_short=allow_short, sides=sides):
        H, L, O, C = X['H'], X['L'], X['O'], X['C']; r = [0.0]*len(C)
        for t in range(2, len(C)):
            k = t-1
            if not (H[k] < H[k-1] and L[k] > L[k-1]) or s50[k] is None: continue
            if C[k] > s50[k] and H[t] >= H[k]:
                f = max(H[k], O[t]); r[t] = C[t]/f-1-bp/1e4; sides[t] = 1
            elif allow_short and C[k] < s50[k] and L[t] <= L[k]:
                f = min(L[k], O[t]); r[t] = 1-C[t]/f-bp/1e4; sides[t] = -1
        return r
    cb3.sides = sides; cb3(BP[m])
    day_rule('CB3 %s inside-day breakout' % m, m, cb3, 'candle')

# ---------------- C. oil brain v2 ----------------
print('=== C. oil brain v2', flush=True)
OB = '/home/user/day-trader-skill/trader-lab/data/oilbrain/'
crude = json.load(open(OB+'crude.json')); cot = json.load(open(OB+'cot.json'))
X = D['OIL']; ds = X['dates']; C = X['C']; n = len(C)
def avail_index(date_str, lag_days):
    """index of the first trading day on/after date+lag (the close we can act on)."""
    d = (dt.date.fromisoformat(date_str)+dt.timedelta(days=lag_days)).isoformat()
    return bisect.bisect_left(ds, d)
# crude: seasonal deviation of level and of weekly change, using the prior 5 years' same week (+-1 week)
ck = sorted(crude); lvl = {k: crude[k] for k in ck}
def seasonal(k, f):
    d = dt.date.fromisoformat(k); vals = []
    for y in range(1, 6):
        for w in (-7, 0, 7):
            t = (d - dt.timedelta(weeks=52*y) + dt.timedelta(days=w)).isoformat()
            j = bisect.bisect_left(ck, t)
            if 0 < j < len(ck) and abs((dt.date.fromisoformat(ck[j])-dt.date.fromisoformat(t)).days) <= 3:
                v = f(j)
                if v is not None: vals.append(v)
    return sum(vals)/len(vals) if len(vals) >= 10 else None
lev_dev = {}; chg_dev = {}
for j, k in enumerate(ck):
    if k < '2005-01-01': continue
    a = seasonal(k, lambda jj: crude[ck[jj]])
    if a is not None: lev_dev[k] = crude[k]-a
    if j:
        b = seasonal(k, lambda jj: crude[ck[jj]]-crude[ck[jj-1]] if jj else None)
        if b is not None: chg_dev[k] = (crude[k]-crude[ck[j-1]])-b
# map to trading days: value known from the release close (week end + 5 days)
def step_series(m, lag):
    out = [None]*n
    for k in sorted(m):
        i = avail_index(k, lag)
        if i < n:
            for t in range(i, n): out[t] = m[k]
    return out
tight = step_series({k: v < 0 for k, v in lev_dev.items()}, 5)
s200 = sma(C, 200)
gate = [tight[i] is True and s200[i] is not None and C[i] > s200[i] for i in range(n)]
sig_rule('O1 oil IBS when stocks below seasonal', 'OIL', ibs_sig(X, gate), 'oil')
def event_sig(events, hold=5):
    s = [0]*n
    for i, side in events:
        for t in range(i, min(n, i+hold)): s[t] = side
    return s
ckc = sorted(cot); ev = []
for a, b in zip(ckc, ckc[1:]):
    dpm = cot[b]['pm_net']-cot[a]['pm_net']
    if dpm: ev.append((avail_index(b, 3), 1 if dpm > 0 else -1))
sig_rule('O2 oil hedging-pressure change', 'OIL', event_sig([e for e in ev if e[0] < n]), 'oil')
ev = [(avail_index(k, 5), 1 if v < 0 else -1) for k, v in chg_dev.items() if v]
sig_rule('O3 oil inventory surprise', 'OIL', event_sig([e for e in ev if e[0] < n]), 'oil')
U = series('USL'); umap = dict(zip(U['dates'], U['C'])); s50 = sma(C, 50)
o4 = []
for i in range(n):
    ok = 0
    if i >= 60 and ds[i] in umap and ds[i-60] in umap and s50[i] is not None:
        ok = 1 if (C[i]/C[i-60]-umap[ds[i]]/umap[ds[i-60]]) > 0 and C[i] > s50[i] else 0
    o4.append(ok)
sig_rule('O4 oil backwardation + trend', 'OIL', o4, 'oil')

pickle.dump({k: {kk: vv for kk, vv in v.items()} for k, v in RESULTS.items()}, open('b28_out.pkl', 'wb'))
W = sorted([r for r in RESULTS.values() if r['worthy']], key=lambda r: -r['all_t'])
print('\nWORTHY:', [r['name'] for r in W])
chosen = []
for r in W:
    cs = [judge.corr(r['map'], c['map']) for c in chosen]
    if all(not (x > judge.BAR['max_corr']) for x in cs): chosen.append(r)
    print('  %-40s max corr with chosen %.2f -> %s' % (r['name'], max(cs) if cs else 0, 'DISTINCT' if r in chosen else 'near-duplicate'))
