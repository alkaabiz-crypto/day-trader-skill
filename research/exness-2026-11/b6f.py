import sys; sys.path.insert(0,'.')
import engine as E
from b5 import ld
for sym in ('BTC-USD','ETH-USD'):
    B=ld(sym,adj=False); dates=B['d']; D=dict(dates=dates,O=list(B['o']),H=list(B['h']),L=list(B['l']),C=list(B['c']))
    js=next(i for i,d in enumerate(dates) if d>='2020-01-01'); h2=next(i for i,d in enumerate(dates) if d>='2023-01-01')
    for a,b in ((20,10),(15,7),(25,12),(30,15),(55,20)):
        s=E.turtle(a,b)(D,False); intra=[0]+s[:-1]
        r=E.returns(D,intra,intra[:],1.5,0,0,False)
        print(sym,'%d/%d'%(a,b),'IS t %.2f | judged t %.2f | 2020-22 t %.2f | 2023-26 t %.2f | trades %d'%(E.stats(r[:js])['t'],E.stats(r[js:])['t'],E.stats(r[js:h2])['t'],E.stats(r[h2:])['t'],sum(1 for i in range(1,len(s)) if s[i]>s[i-1])))
