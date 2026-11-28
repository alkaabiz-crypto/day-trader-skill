import sys, math, statistics; sys.path.insert(0,'.')
from b5 import ld
import catalog as C
S = {k: ld(s, adj=(s in ('SPY','QQQ'))) for k, s in [('US500','SPY'),('USTEC','QQQ'),('GOLD','GC=F'),('BTC','BTC-USD')]}
closes = {k: dict(zip(D['d'], D['c'])) for k, D in S.items()}
opens = {k: dict(zip(D['d'], D['o'])) for k, D in S.items()}
days = sorted(set(closes['US500']))  # trade on US trading days
def px(k, d, which):
    src = closes[k] if which=='c' else opens[k]
    # last available on or before d
    return src.get(d)
def run(assets, start='2016-01-01', cost=1e-4):
    ds = [d for d in days if d >= '2014-10-01' and all(d in closes[a] for a in assets)]
    hold = None; val = 1.0; vals = []; rets = []; bh = []
    for i in range(253, len(ds)-1):
        d, nx = ds[i], ds[i+1]
        if ds[i][:7] != ds[i-1][:7]:  # first trading day of month: decide at prior close, trade at today's open (approx: use close-to-close from here)
            mom = {a: closes[a][ds[i-1]]/closes[a][ds[i-253]]-1 for a in assets}
            best = max(mom, key=mom.get); new = best if mom[best] > 0 else None
            if new != hold: val *= 1 - cost*(1 if hold is None or new is None else 2)
            hold = new
        r = closes[hold][nx]/closes[hold][d]-1 if hold else 0.0
        e = sum(closes[a][nx]/closes[a][d]-1 for a in assets)/len(assets)
        if nx >= start: rets.append(r); bh.append(e)
    def sh(x): return statistics.mean(x)/statistics.stdev(x)*252**.5
    def grow(x, s=0):
        v=1000; pk=v; dd=0
        for y in x: v*=1+y; pk=max(pk,v); dd=min(dd,v/pk-1)
        return v, dd
    ex = [a-b for a,b in zip(rets,bh)]
    v,dd = grow(rets); vb,ddb = grow(bh)
    return sh(rets), sh(bh), C.tstat(ex), v, dd, vb, ddb
for assets in (['US500','USTEC','GOLD','BTC'], ['US500','USTEC','BTC'], ['US500','USTEC','GOLD']):
    s, sb, t, v, dd, vb, ddb = run(assets)
    print('%-24s 2016-on Sharpe %.2f vs equal hold %.2f | excess t %.2f | $1,000 -> $%.0f (worst %.0f%%) vs hold $%.0f (worst %.0f%%)' % ('+'.join(assets), s, sb, t, v, dd*100, vb, ddb*100))
    s, sb, t, v, dd, vb, ddb = run(assets, start='2024-01-01')
    print('   since 2024: $%.0f (worst %.0f%%) vs equal hold $%.0f' % (v, dd*100, vb))
