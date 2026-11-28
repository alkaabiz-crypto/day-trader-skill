import sys, random, json; sys.path.insert(0,'.')
import engine as E, batch2
from yload import load
random.seed(11)
raw=load('GC=F'); dates=sorted(raw)
D=dict(dates=dates,O=[raw[d][0] for d in dates],H=[raw[d][1] for d in dates],L=[raw[d][2] for d in dates],C=[raw[d][3] for d in dates])
js=next(i for i,d in enumerate(dates) if d>='2010-01-01'); je=next(i for i,d in enumerate(dates) if d>='2024-07-01')
out=[]
for name in ['buyhold','sma200','ichimoku','sma50']:
    intra,over=E.series(D,name,True)
    for acct,sw in (('standard',True),('swapfree',False)):
        r=E.returns(D,intra,over,1.5,5.0,1.0,sw); r2=E.returns(D,intra,over,1.5,5.0,1.0,sw,mult=2)
        IS,J,J2,LATE=E.stats(r[:js]),E.stats(r[js:je]),E.stats(r2[js:je]),E.stats(r[je:])
        b=0
        si,so=intra[js:je],over[js:je]; Dj=dict(dates=dates[js:je],O=D['O'][js:je],C=D['C'][js:je])
        for _ in range(200):
            k=random.randrange(20,len(si)-20)
            if E.stats(E.returns(Dj,si[k:]+si[:k],so[k:]+so[:k],1.5,5.0,1.0,sw))['mean']<J['mean']: b+=1
        v,dd=E.growth(r[js:je])
        out.append((name,acct,round(IS['t'],2),round(J['t'],2),round(J['sharpe'],2),round(J2['t'],2),b/200,round(LATE['t'],2),round(v),round(dd*100,1)))
        print(*out[-1],flush=True)
json.dump(out,open('results3.json','w'))
