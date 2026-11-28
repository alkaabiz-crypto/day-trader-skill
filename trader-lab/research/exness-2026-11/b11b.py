import sys, random; sys.path.insert(0,'.')
import engine as E
from yload import load
random.seed(12)
def rules(D, ls):
    O,H,L,C=D['O'],D['H'],D['L'],D['C']; n=len(C); m20=E.sma(C,20); m50=E.sma(C,50); A=E.atr(H,L,C,14)
    def st(enter, exit_, start=260):
        s=[0]*n; p=0
        for i in range(start,n):
            if p==1 and exit_(i,1): p=0
            elif p==-1 and exit_(i,-1): p=0
            if p==0:
                e=enter(i)
                if e==1 or (e==-1 and ls): p=e
            s[i]=p
        return s
    bw=[None]*n
    for i in range(19,n):
        w=C[i-19:i+1]; m=sum(w)/20; sd=(sum((x-m)**2 for x in w)/20)**.5; bw[i]=(4*sd/m, m+2*sd, m-2*sd)
    R={}
    R['squeeze']=st(lambda i: (1 if C[i]>bw[i][1] else (-1 if C[i]<bw[i][2] else 0)) if bw[i-1][0]<=min(x[0] for x in bw[i-120:i]) else 0,
                    lambda i,p: (C[i]<m20[i]) if p==1 else (C[i]>m20[i]))
    box={}
    def darv(i):
        hi=max(H[i-23:i-3]) if i>23 else None
        if hi and max(H[i-3:i])<=hi and C[i]>hi: box['lo']=min(L[i-3:i]); return 1
        return 0
    R['darvas']=st(darv, lambda i,p: C[i]<box.get('lo',0))
    R['high52']=st(lambda i: 1 if C[i]>=max(C[i-251:i+1]) else 0, lambda i,p: C[i]<m50[i])
    R['weekly_high']=st(lambda i: 1 if C[i]>max(H[i-5:i]) else (-1 if C[i]<min(L[i-5:i]) else 0),
                        lambda i,p: (C[i]<min(L[i-5:i])) if p==1 else (C[i]>max(H[i-5:i])))
    held={'n':0}
    def nr4(i):
        if H[i-1]-L[i-1]<=min(H[j]-L[j] for j in range(i-4,i)) and C[i]>H[i-1]: held['n']=0; return 1
        return 0
    def nr4x(i,p): held['n']+=1; return held['n']>=5
    R['nr4']=st(nr4,nr4x)
    R['atr_channel']=st(lambda i: 1 if C[i]>m20[i]+2*A[i] else (-1 if C[i]<m20[i]-2*A[i] else 0), lambda i,p: (C[i]<m20[i]) if p==1 else (C[i]>m20[i]))
    br={}
    def dbr(i):
        if C[i]>max(H[i-20:i]): br.update(stop=C[i]-2*A[i], tp=C[i]+4*A[i]); return 1
        return 0
    R['donchian_bracket']=st(dbr, lambda i,p: L[i]<=br['stop'] or H[i]>=br['tp'])  # approx: exits at next open after touch
    return R
def williams(D, cost):
    O,H,L,C=D['O'],D['H'],D['L'],D['C']; r=[0.0]*len(C)
    for i in range(1,len(C)):
        lvl=O[i]+0.6*(H[i-1]-L[i-1])
        if H[i]>=lvl: r[i]=C[i]/max(lvl,O[i])-1-cost/1e4
    return r
MK=[('US500','SPY',True,1.0,'2013-01-01',False),('USTEC','QQQ',True,1.0,'2013-01-01',False),('GOLD','GC=F',False,1.0,'2013-01-01',True),('BTC','BTC-USD',False,1.5,'2020-01-01',False)]
for mk,sym,adj,cost,split,ls in MK:
    raw=load(sym,adj=adj); dates=sorted(raw)
    D=dict(dates=dates,O=[raw[d][0] for d in dates],H=[raw[d][1] for d in dates],L=[raw[d][2] for d in dates],C=[raw[d][3] for d in dates])
    js=next(i for i,d in enumerate(dates) if d>=split); y24=next(i for i,d in enumerate(dates) if d>='2024-01-01')
    bh=E.returns(D,[1]*len(dates),[1]*len(dates),cost,0,0,False); bhs=E.stats(bh[js:])['sharpe']
    v,dd=E.growth(bh[y24:]); print('%-6s %-16s judged Sharpe %.2f | $1,000 from 2024 $%.0f worst %.0f%%'%(mk,'buy and hold',bhs,v,dd*100))
    R=rules(D,ls)
    for name,s in list(R.items())+[('williams',None)]:
        if s is None:
            r=williams(D,cost); r2=williams(D,2*cost); beats=None
        else:
            intra=[0]+s[:-1]; over=intra[:]
            r=E.returns(D,intra,over,cost,0,0,False); r2=E.returns(D,intra,over,cost,0,0,False,mult=2)
            si,so=intra[js:],over[js:]; Dj=dict(dates=dates[js:],O=D['O'][js:],C=D['C'][js:]); b=0
            J=E.stats(r[js:])
            for _ in range(200):
                k=random.randrange(30,len(si)-30)
                if E.stats(E.returns(Dj,si[k:]+si[:k],so[k:]+so[:k],cost,0,0,False))['mean']<J['mean']: b+=1
            beats=b/200
        IS,J,J2=E.stats(r[:js]),E.stats(r[js:]),E.stats(r2[js:]); v,dd=E.growth(r[y24:])
        ok=IS['mean']>0 and J['t']>=3 and J['sharpe']>bhs and J2['mean']>0 and (beats is None or beats>=.95)
        print('%-6s %-16s IS t %5.2f | judged t %5.2f Sharpe %5.2f | 2x t %5.2f | placebo %s | $1,000 from 2024 $%.0f worst %.0f%% | %s'%(mk,name,IS['t'],J['t'],J['sharpe'],J2['t'],'%3.0f%%'%(beats*100) if beats is not None else ' n/a',v,dd*100,'PASS' if ok else 'FAIL'),flush=True)
