import sys, random; sys.path.insert(0,'.')
import engine as E
from yload import load
random.seed(9)
def ibs(H,L,C,i): return (C[i]-L[i])/(H[i]-L[i]) if H[i]>L[i] else .5
for mk,sym in (('US500','SPY'),('USTEC','QQQ')):
    raw=load(sym,adj=True); dates=sorted(raw)
    D=dict(dates=dates,O=[raw[d][0] for d in dates],H=[raw[d][1] for d in dates],L=[raw[d][2] for d in dates],C=[raw[d][3] for d in dates])
    H,L,C=D['H'],D['L'],D['C']; n=len(C); m200=E.sma(C,200); m5=E.sma(C,5); r2=E.rsi_w(C,2)
    def mk_rule(enter, exit_):
        s=[];p=0
        for i in range(n):
            if m200[i] is None or r2[i] is None or i<7: s.append(0); continue
            if p and exit_(i): p=0
            elif not p and enter(i): p=1
            s.append(p)
        return s
    rules=dict(buyhold=[1]*n,
        ibs_close=mk_rule(lambda i: ibs(H,L,C,i)<.2, lambda i: C[i]>C[i-1]),
        ibs_close_08=mk_rule(lambda i: ibs(H,L,C,i)<.2, lambda i: ibs(H,L,C,i)>.8),
        rsi2_close=mk_rule(lambda i: r2[i]<10 and C[i]>m200[i], lambda i: C[i]>m5[i]),
        double7_close=mk_rule(lambda i: C[i]<=min(C[i-6:i+1]) and C[i]>m200[i], lambda i: C[i]>=max(C[i-6:i+1])))
    js=next(i for i,d in enumerate(dates) if d>='2013-01-01'); y24=next(i for i,d in enumerate(dates) if d>='2024-01-01'); bh=None
    for name,s in rules.items():
        # decided and filled at close t: held overnight t->t+1 and intraday t+1, until changed at a later close
        over=s[:]; intra=[0]+s[:-1]
        r=E.returns(D,intra,over,1.5,0,0,False); r2x=E.returns(D,intra,over,1.5,0,0,False,mult=2)
        IS,J,J2=E.stats(r[:js]),E.stats(r[js:]),E.stats(r2x[js:])
        if name=='buyhold': bh=J['sharpe']
        si,so=intra[js:],over[js:]; Dj=dict(dates=dates[js:],O=D['O'][js:],C=C[js:]); b=0
        for _ in range(200):
            k=random.randrange(30,len(si)-30)
            if E.stats(E.returns(Dj,si[k:]+si[:k],so[k:]+so[:k],1.5,0,0,False))['mean']<J['mean']: b+=1
        v,dd=E.growth(r[y24:]); ex=sum(1 for x in over[js:] if x)/len(over[js:])
        ok=IS['mean']>0 and J['t']>=3 and J['sharpe']>bh and J2['mean']>0 and b/200>=.95 and name!='buyhold'
        print('%s %-14s IS t %5.2f | judged t %5.2f Sharpe %5.2f | 2x t %5.2f | placebo %3.0f%% | in market %2.0f%% | $1,000 from 2024 $%.0f worst %.0f%% | %s'%(mk,name,IS['t'],J['t'],J['sharpe'],J2['t'],b/2,ex*100,v,dd*100,'PASS' if ok else 'FAIL'),flush=True)
