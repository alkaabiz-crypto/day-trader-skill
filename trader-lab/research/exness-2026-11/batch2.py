import sys; sys.path.insert(0,'.')
import engine as E
from engine import sma, ema, rsi_w, atr
def mr(enter, exit_):
    def f(D, ls):
        s=[]; p=0
        for i in range(len(D['C'])):
            e = enter(D,i)
            if e is None: s.append(0); continue
            x = exit_(D,i)
            if p and x: p=0
            elif not p and e: p=1
            s.append(p)
        return s
    return f
def cache(D, key, fn):
    c=D.setdefault('_c',{})
    if key not in c: c[key]=fn()
    return c[key]
def R14(D): return cache(D,'r14',lambda: rsi_w(D['C'],14))
def r_rsi14(D, ls):
    r=R14(D); s=[]; p=0
    for i in range(len(D['C'])):
        if r[i] is None: s.append(0); continue
        if p==1 and r[i]>70: p=0
        if p==-1 and r[i]<30: p=0
        if p==0:
            if r[i]<30: p=1
            elif ls and r[i]>70: p=-1
        s.append(p)
    return s
def stochk(D,n=14):
    def f():
        H,L,C=D['H'],D['L'],D['C']; k=[None]*len(C)
        for i in range(n-1,len(C)):
            hh=max(H[i-n+1:i+1]); ll=min(L[i-n+1:i+1]); k[i]=100*(C[i]-ll)/(hh-ll) if hh>ll else 50
        return k
    return cache(D,'k%d'%n,f)
def r_stoch(D,ls):
    k=stochk(D); d=[None]*len(k)
    for i in range(len(k)):
        w=[x for x in k[max(0,i-2):i+1] if x is not None]; d[i]=sum(w)/3 if len(w)==3 else None
    return mr(lambda D,i: None if d[i] is None else d[i]<20, lambda D,i: d[i]>80)(D,ls)
def r_wr(D,ls):
    k=stochk(D); return mr(lambda D,i: None if k[i] is None else k[i]<10, lambda D,i: k[i]>90)(D,ls)
def r_cci(D,ls):
    H,L,C=D['H'],D['L'],D['C']; tp=[(H[i]+L[i]+C[i])/3 for i in range(len(C))]; m=sma(tp,20); cc=[None]*len(C)
    for i in range(19,len(C)):
        md=sum(abs(x-m[i]) for x in tp[i-19:i+1])/20; cc[i]=(tp[i]-m[i])/(0.015*md) if md else 0
    return mr(lambda D,i: None if cc[i] is None else cc[i]<-100, lambda D,i: cc[i]>0)(D,ls)
def dmi(D,n=14):
    H,L,C=D['H'],D['L'],D['C']; N=len(C); pdm=[0]*N; mdm=[0]*N; tr=[0]*N
    for i in range(1,N):
        up=H[i]-H[i-1]; dn=L[i-1]-L[i]; pdm[i]=up if up>dn and up>0 else 0; mdm[i]=dn if dn>up and dn>0 else 0
        tr[i]=max(H[i]-L[i],abs(H[i]-C[i-1]),abs(L[i]-C[i-1]))
    def w(x):
        o=[None]*N; a=None
        for i in range(1,N):
            a = x[i] if a is None else a-(a/n)+x[i]; o[i]=a if i>=n else None
        return o
    T,P,M=w(tr),w(pdm),w(mdm); pdi=[None]*N; mdi=[None]*N; dx=[None]*N
    for i in range(N):
        if T[i]: pdi[i]=100*P[i]/T[i]; mdi[i]=100*M[i]/T[i]; s=pdi[i]+mdi[i]; dx[i]=100*abs(pdi[i]-mdi[i])/s if s else 0
    adx=[None]*N; a=None; cnt=0
    for i in range(N):
        if dx[i] is None: continue
        cnt+=1; a = dx[i] if a is None else (a*(n-1)+dx[i])/n
        if cnt>=n: adx[i]=a
    return pdi,mdi,adx
def r_adx(D,ls):
    p,m,a=dmi(D); return [0 if a[i] is None else (1 if a[i]>25 and p[i]>m[i] else (-1 if ls and a[i]>25 and m[i]>p[i] else 0)) for i in range(len(a))]
def r_psar(D,ls):
    H,L=D['H'],D['L']; N=len(H); s=[0]*N; up=True; af=.02; ep=H[0]; sar=L[0]
    for i in range(1,N):
        sar=sar+af*(ep-sar)
        if up:
            sar=min(sar,L[i-1],L[i-2] if i>1 else L[i-1])
            if L[i]<sar: up=False; sar=ep; ep=L[i]; af=.02
            elif H[i]>ep: ep=H[i]; af=min(af+.02,.2)
        else:
            sar=max(sar,H[i-1],H[i-2] if i>1 else H[i-1])
            if H[i]>sar: up=True; sar=ep; ep=H[i]; af=.02
            elif L[i]<ep: ep=L[i]; af=min(af+.02,.2)
        s[i]=1 if up else (-1 if ls else 0)
    return s
def r_ichimoku(D,ls):
    H,L,C=D['H'],D['L'],D['C']; N=len(C); s=[0]*N
    mid=lambda a,b: (max(H[a:b])+min(L[a:b]))/2
    for i in range(78,N):
        j=i-26; ten=mid(j-8,j+1); kij=mid(j-25,j+1); A=(ten+kij)/2; B=mid(j-51,j+1)
        top,bot=max(A,B),min(A,B); s[i]=1 if C[i]>top else (-1 if ls and C[i]<bot else 0)
    return s
def wma(x,n):
    o=[None]*len(x); w=sum(range(1,n+1))
    for i in range(n-1,len(x)):
        if any(v is None for v in x[i-n+1:i+1]): continue
        o[i]=sum(x[i-n+1+k]*(k+1) for k in range(n))/w
    return o
def r_hull(D,ls):
    C=D['C']; n=55; a=wma(C,n//2); b=wma(C,n); raw=[None if a[i] is None or b[i] is None else 2*a[i]-b[i] for i in range(len(C))]
    h=wma(raw,int(n**.5)); return [0 if i==0 or h[i] is None or h[i-1] is None else (1 if h[i]>h[i-1] else (-1 if ls else 0)) for i in range(len(C))]
def r_keltner(D,ls):
    C=D['C']; m=ema(C,20); A=atr(D['H'],D['L'],C,10); s=[]; p=0
    for i in range(len(C)):
        if m[i] is None or A[i] is None: s.append(0); continue
        if p==1 and C[i]<m[i]: p=0
        if p==-1 and C[i]>m[i]: p=0
        if p==0:
            if C[i]>m[i]+2*A[i]: p=1
            elif ls and C[i]<m[i]-2*A[i]: p=-1
        s.append(p)
    return s
def pattern_break(test):
    def f(D,ls):
        H,L,C=D['H'],D['L'],D['C']; N=len(C); s=[0]*N; p=0; held=0; arm=None
        for i in range(N):
            if p:
                held+=1
                if held>=5: p=0
            elif arm is not None and C[i]>H[arm]: p=1; held=0
            if not p: arm = i if test(D,i) else (arm if arm is not None and i-arm<3 else None)
            s[i]=p
        return s
    return f
nr7=pattern_break(lambda D,i: i>=6 and D['H'][i]-D['L'][i]<=min(D['H'][j]-D['L'][j] for j in range(i-6,i+1)))
inside=pattern_break(lambda D,i: i>=1 and D['H'][i]<D['H'][i-1] and D['L'][i]>D['L'][i-1])
def r_3down(D,ls):
    C=D['C']; return mr(lambda D,i: None if i<3 else C[i]<C[i-1]<C[i-2]<C[i-3], lambda D,i: C[i]>C[i-1])(D,ls)
def r_crsi(D,ls):
    C=D['C']; r=rsi_w(C,2); m=sma(C,200)
    return mr(lambda D,i: None if m[i] is None or r[i] is None or r[i-1] is None else (r[i]+r[i-1]<35 and C[i]>m[i]), lambda D,i: r[i]>65)(D,ls)
def r_ha(D,ls):
    O,H,L,C=D['O'],D['H'],D['L'],D['C']; s=[]; ho=(O[0]+C[0])/2
    for i in range(len(C)):
        hc=(O[i]+H[i]+L[i]+C[i])/4
        if i: ho=(ho+hcp)/2
        hcp=hc; s.append(1 if hc>ho else (-1 if ls else 0))
    return s
def r_sma50(D,ls):
    m=sma(D['C'],50); return [0 if m[i] is None else (1 if c>m[i] else (-1 if ls else 0)) for i,c in enumerate(D['C'])]
def r_halloween(D,ls):
    return [1 if int(d[5:7]) in (11,12,1,2,3,4) else 0 for d in D['dates']]
NEW=dict(rsi14=r_rsi14, stoch=r_stoch, willr=r_wr, cci=r_cci, adx=r_adx, psar=r_psar, ichimoku=r_ichimoku, hull=r_hull,
         keltner=r_keltner, nr7=nr7, insideday=inside, down3=r_3down, cumrsi2=r_crsi, heikin=r_ha, sma50=r_sma50, halloween=r_halloween)
E.SIGNAL.update(NEW)
