import sys, json, gzip, datetime as dt; sys.path.insert(0,'.')
import engine as E
from yload import load
def wr(D,k,cost):
    O,H,L,C=D['O'],D['H'],D['L'],D['C']; r=[0.0]*len(C)
    for i in range(1,len(C)):
        lvl=O[i]+k*(H[i-1]-L[i-1])
        if H[i]>=lvl: r[i]=C[i]/max(lvl,O[i])-1-cost/1e4
    return r
for mk,sym,cost,split,h1,h2 in [('BTC','BTC-USD',1.5,'2020-01-01','2023-01-01','2027'),('ETH','ETH-USD',1.5,'2020-01-01','2023-01-01','2027'),('GOLD','GC=F',1.0,'2013-01-01','2020-01-01','2027')]:
    raw=load(sym,adj=False); dates=sorted(raw); D=dict(dates=dates,O=[raw[d][0] for d in dates],H=[raw[d][1] for d in dates],L=[raw[d][2] for d in dates],C=[raw[d][3] for d in dates])
    js=next(i for i,d in enumerate(dates) if d>=split); jh=next(i for i,d in enumerate(dates) if d>=h1)
    for k in (0.4,0.5,0.6,0.7,0.8):
        r=wr(D,k,cost); r3=wr(D,k,3*cost)
        print('%-4s k %.1f | judged t %5.2f | first half t %5.2f | second half t %5.2f | 3x cost t %5.2f | days traded %.0f%%'%(mk,k,E.stats(r[js:])['t'],E.stats(r[js:jh])['t'],E.stats(r[jh:])['t'],E.stats(r3[js:])['t'],100*sum(1 for x in r[js:] if x)/len(r[js:])))
# hourly path check, BTC
a=json.load(gzip.open('/home/user/day-trader-skill/trader-lab/data/fx1h/BTC-USD.json.gz'))
days={}
for ts,o,h,l,c in a: days.setdefault(dt.datetime.utcfromtimestamp(ts).date().isoformat(),[]).append((ts,o,h,l,c))
ds=[d for d in sorted(days) if len(days[d])==24]; rh=[]; rd=[]
for i in range(1,len(ds)):
    p=days[ds[i-1]]; B=days[ds[i]]; ph=max(b[2] for b in p); pl=min(b[3] for b in p); o=B[0][1]; lvl=o+0.6*(ph-pl)
    x=0.0
    for b in B:
        if b[2]>=lvl: x=B[-1][4]/max(lvl,b[1] if b is not B[0] else o)-1-1.5e-4; break
    rh.append(x)
    hi=max(b[2] for b in B); rd.append(B[-1][4]/max(lvl,o)-1-1.5e-4 if hi>=lvl else 0.0)
print('BTC hourly-path check %s to %s: hourly fills t %.2f, %.2f bp a day | daily-bar method on same days t %.2f, %.2f bp a day'%(ds[0],ds[-1],E.stats(rh)['t'],1e4*E.stats(rh)['mean'],E.stats(rd)['t'],1e4*E.stats(rd)['mean']))
