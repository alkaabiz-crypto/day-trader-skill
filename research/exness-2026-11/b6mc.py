import sys, random; sys.path.insert(0,'.')
import engine as E
from b5 import ld
random.seed(1)
B=ld('BTC-USD',adj=False); dates=B['d']; D=dict(dates=dates,O=list(B['o']),H=list(B['h']),L=list(B['l']),C=list(B['c']))
s=E.turtle(20,10)(D,False); intra=[0]+s[:-1]; r=E.returns(D,intra,intra[:],1.5,0,0,False)
js=next(i for i,d in enumerate(dates) if d>='2020-01-01')
# trades in the judged period, in $ at 0.01 lot (~$630 at today's price, so scale each trade's return by $630)
tr=[]; cur=None
for i in range(js,len(r)):
    if intra[i] and cur is None: cur=0.0
    if cur is not None: cur=(1+cur)*(1+r[i])-1
    if not intra[i] and cur is not None: tr.append(cur); cur=None
usd=[630*x for x in tr]
print('judged trades %d, win %.0f%%, avg $%.1f, best $%.0f, worst $%.0f'%(len(usd),100*sum(u>0 for u in usd)/len(usd),sum(usd)/len(usd),max(usd),min(usd)))
per_year=len(usd)/((len(r)-js)/365)
yrs=[]; dd=[]
for _ in range(20000):
    k=max(1,round(random.gauss(per_year,1.5))); seq=[random.choice(usd) for _ in range(k)]
    v=0; pk=0; m=0
    for u in seq: v+=u; pk=max(pk,v); m=min(m,v-pk)
    yrs.append(v); dd.append(m)
yrs.sort(); dd.sort()
print('one year, bootstrapped (%.1f trades/yr): median $%.0f, 10th pct $%.0f, chance of losing money %.0f%%, chance of a $200+ drop on the way %.0f%%, $300+ %.0f%%'%(per_year,yrs[len(yrs)//2],yrs[len(yrs)//10],100*sum(y<0 for y in yrs)/len(yrs),100*sum(x<=-200 for x in dd)/len(dd),100*sum(x<=-300 for x in dd)/len(dd)))
