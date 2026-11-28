import sys, json, random; sys.path.insert(0, '.')
from engine import *
RULES = list(SIGNAL) + list(CAL)
random.seed(7)
rows = []
for mk, M in MARKETS.items():
    raw = M['src'](); dates = sorted(raw)
    D = dict(dates=dates, O=[raw[d][0] for d in dates], H=[raw[d][1] for d in dates], L=[raw[d][2] for d in dates], C=[raw[d][3] for d in dates])
    js = next(i for i, d in enumerate(dates) if d >= M['split']); y24 = next(i for i, d in enumerate(dates) if d >= '2024-01-02')
    bh = {}
    for name in RULES:
        if M['ls'] and name in CAL: continue  # calendar rules are stock-index effects
        intra, over = series(D, name, M['ls'])
        for acct, swap in (('standard', True), ('swapfree', False)):
            r = returns(D, intra, over, M['spread'], M['swl'], M['sws'], swap)
            r2 = returns(D, intra, over, M['spread'], M['swl'], M['sws'], swap, mult=2.0)
            IS, J = stats(r[:js]), stats(r[js:]); J2 = stats(r2[js:])
            if name == 'buyhold': bh[acct] = J['sharpe']
            # placebo: circular shift of positions on the judged period
            jr = None; beats = 0; N = 200
            seg_i, seg_o = intra[js:], over[js:]
            Dj = dict(dates=dates[js:], O=D['O'][js:], C=D['C'][js:])
            for _ in range(N):
                k = random.randrange(20, len(seg_i)-20)
                pi = seg_i[k:]+seg_i[:k]; po = seg_o[k:]+seg_o[:k]
                if stats(returns(Dj, pi, po, M['spread'], M['swl'], M['sws'], swap))['mean'] < J['mean']: beats += 1
            v24, dd24 = growth(r[y24:]); exposure = sum(1 for x in intra[js:] if x)/len(intra[js:])
            ok = IS['mean'] > 0 and J['t'] >= 3 and J['sharpe'] > bh.get(acct, -9) and J2['mean'] > 0 and beats/N >= .95 and name != 'buyhold'
            rows.append(dict(market=mk, rule=name, acct=acct, is_t=round(IS['t'], 2), j_t=round(J['t'], 2), j_sharpe=round(J['sharpe'], 2),
                             j_bp_day=round(J['mean']*1e4, 2), j_t_2x=round(J2['t'], 2), placebo=beats/N, exposure=round(exposure, 2),
                             usd_2024=round(v24), dd_2024=round(dd24*100, 1), verdict='PASS' if ok else 'FAIL'))
            print(mk, name, acct, rows[-1]['is_t'], rows[-1]['j_t'], rows[-1]['j_sharpe'], rows[-1]['placebo'], rows[-1]['usd_2024'], rows[-1]['dd_2024'], rows[-1]['verdict'], flush=True)
json.dump(rows, open('results.json', 'w'), indent=1)
