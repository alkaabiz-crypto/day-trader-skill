import sys, gzip, json, random, datetime as dt; sys.path.insert(0,'.')
import engine as E
from zoneinfo import ZoneInfo
NY=ZoneInfo('America/New_York'); random.seed(4)
COST=float(sys.argv[1]); FILL=dt.time(int(sys.argv[2]),int(sys.argv[3]))
for mk,f in (('US500','idx/spy.json.gz'),('USTEC','idx/qqq.json.gz')):
    d=json.load(gzip.open('/home/user/day-trader-skill/trader-lab/data/'+f)); S={}; P={}
    for k in sorted(d,key=int):
        t=dt.datetime.fromtimestamp(int(k),NY); day=t.date().isoformat(); b=d[k]
        if dt.time(9,30)<=t.time()<dt.time(16,0):
            if day not in S: S[day]=[b[0],b[1],b[2],b[3]]
            else: s=S[day]; s[1]=max(s[1],b[1]); s[2]=min(s[2],b[2]); s[3]=b[3]
        elif t.time()>=FILL and day not in P: P[day]=b[0]
    days=[x for x in sorted(S) if x in P]
    H=[S[x][1] for x in days]; L=[S[x][2] for x in days]; C=[S[x][3] for x in days]; F=[P[x] for x in days]; n=len(days)
    def ibs(i): return (C[i]-L[i])/(H[i]-L[i]) if H[i]>L[i] else .5
    def rule(exit_):
        s=[];p=0
        for i in range(n):
            if i and p and exit_(i): p=0
            elif not p and ibs(i)<.2: p=1
            s.append(p)
        return s
    R=dict(buyhold=[1]*n, ibs_close=rule(lambda i: C[i]>C[i-1]), ibs_close_08=rule(lambda i: ibs(i)>.8))
    h2=next(i for i,x in enumerate(days) if x>='2021-01-01'); y24=next(i for i,x in enumerate(days) if x>='2024-01-01')
    for name,s in R.items():
        r=[0.0]*n
        for i in range(1,n):
            r[i]=s[i-1]*(F[i]/F[i-1]-1) - abs(s[i]-s[i-1])*COST/1e4   # position set at day i-1's 16:10 fill, marked 16:10 to 16:10
        st=E.stats(r); a,b2=E.stats(r[:h2]),E.stats(r[h2:]); beats=0
        for _ in range(200):
            k=random.randrange(30,n-30); ss=s[k:]+s[:k]
            rr=[ss[i-1]*(F[i]/F[i-1]-1)-abs(ss[i]-ss[i-1])*COST/1e4 for i in range(1,n)]
            if E.stats(rr)['mean']<st['mean']: beats+=1
        v,dd=E.growth(r[y24:])
        print('%s %-13s 2016-26 t %5.2f Sharpe %5.2f | 2016-20 t %5.2f | 2021-26 t %5.2f | placebo %3.0f%% | trades %d | $1,000 from 2024 $%.0f worst %.0f%%'%(mk,name,st['t'],st['sharpe'],a['t'],b2['t'],beats/2,sum(1 for i in range(1,n) if s[i]>s[i-1]),v,dd*100),flush=True)
