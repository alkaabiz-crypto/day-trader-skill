import sys, random, statistics, math, json; sys.path.insert(0, '.')
from intra import MK, load, bracket
from setups import make
random.seed(10)
VAR = [(a, r) for a in (0.15, 0.30) for r in (1, 2, 3)]
NOTIONAL = {'US500': 950, 'USTEC': 1250, 'XAUUSD': 3740, 'EURUSD': 1100}
def t(x): return 0 if len(x) < 3 or statistics.stdev(x) == 0 else statistics.mean(x)/statistics.stdev(x)*len(x)**.5
rows = []
for mk in sys.argv[1:] or MK:
    f, cost, kind, split = MK[mk]; days = load(f, kind); setups, sess, FLAT = make(kind)
    ds = sorted(days); rng = []; recs = {}   # recs[setup][var] = list of (date, gross, gross_flipped)
    for i, d in enumerate(ds):
        B = sess(days[d]); full = days[d]
        if len(B) < 40: continue
        if i >= 15:
            prev = [sess(days[x]) for x in ds[i-14:i]]; prev = [p for p in prev if p]
            adr = sum(max(b[2] for b in p)-min(b[3] for b in p) for p in prev)/len(prev)
            pb = sess(days[ds[i-1]])
            if not pb: continue
            pdh, pdl, pc = max(b[2] for b in pb), min(b[3] for b in pb), pb[-1][4]
            asia = [b for b in full if b[0] < 480] if kind == 'fx' else []
            ctx = dict(adr=adr, pdh=pdh, pdl=pdl, pc=pc, pivot=(pdh+pdl+pc)/3,
                       asia_h=max(b[2] for b in asia) if asia else None, asia_l=min(b[3] for b in asia) if asia else None)
            for name, (k, side) in setups(B, ctx).items():
                if k+1 >= len(B): continue
                for a, r in VAR:
                    sl = a*adr; tp = r*sl
                    g = bracket(B, k+1, side, sl, tp, FLAT); gf = bracket(B, k+1, -side, sl, tp, FLAT)
                    recs.setdefault(name, {}).setdefault((a, r), []).append((d, g, gf))
    for name, V in sorted(recs.items()):
        best = max(V, key=lambda v: statistics.mean([g - cost/1e4 for d, g, gf in V[v] if d < split] or [-1]))
        L = V[best]; IS = [g-cost/1e4 for d, g, gf in L if d < split]; J = [(d, g, gf) for d, g, gf in L if d >= split]
        net = [g-cost/1e4 for d, g, gf in J]; net2 = [g-2*cost/1e4 for d, g, gf in J]
        if len(net) < 20: continue
        real = statistics.mean(net); beats = 0
        for _ in range(1000):
            pm = statistics.mean([(g if random.random() < .5 else gf) - cost/1e4 for d, g, gf in J])
            if pm < real: beats += 1
        y24 = [g-cost/1e4 for d, g, gf in J if d >= '2024-01-01']
        usd = NOTIONAL[mk]*sum(y24); win = sum(x > 0 for x in net)/len(net)
        eq = 0; pk = 0; dd = 0
        for x in y24: eq += NOTIONAL[mk]*x; pk = max(pk, eq); dd = min(dd, eq-pk)
        ok = t(IS) > 0 and t(net) >= 3 and statistics.mean(net2) > 0 and beats/1000 >= .95
        rows.append(dict(market=mk, setup=name, sl=best[0], R=best[1], is_t=round(t(IS), 2), n=len(net), j_bp=round(1e4*real, 2),
                         j_t=round(t(net), 2), t2x=round(t(net2), 2), win=round(win, 2), placebo=beats/1000, usd_2024=round(usd), dd_2024=round(dd),
                         verdict='PASS' if ok else 'FAIL'))
        r_ = rows[-1]
        print('%-6s %-12s SL %.2f ADR R %d | IS t %5.2f | judged %4d trades %6.2f bp t %5.2f (2x %5.2f) win %2.0f%% placebo %3.0f%% | since 2024 at min lot $%+5.0f (worst run $%.0f) | %s' % (
            mk, name, best[0], best[1], r_['is_t'], r_['n'], r_['j_bp'], r_['j_t'], r_['t2x'], win*100, beats/10, usd, dd, r_['verdict']), flush=True)
json.dump(rows, open('results10_%s.json' % '_'.join(sys.argv[1:] or ['all']), 'w'), indent=1)
