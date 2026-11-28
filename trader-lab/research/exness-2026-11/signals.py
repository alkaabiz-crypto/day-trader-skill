import sys, gzip, json, datetime as dt, csv, statistics; sys.path.insert(0,'.')
import engine as E
from yload import load
from zoneinfo import ZoneInfo
NY=ZoneInfo('America/New_York')
# USTEC IBS, realistic 16:10 fills (as b8r), $ at 0.05 lot ~ $1,250 notional
d=json.load(gzip.open('/home/user/day-trader-skill/trader-lab/data/idx/qqq.json.gz')); S={}; P={}
for k in sorted(d,key=int):
    t=dt.datetime.fromtimestamp(int(k),NY); day=t.date().isoformat(); b=d[k]
    if dt.time(9,30)<=t.time()<dt.time(16,0):
        if day not in S: S[day]=[b[1],b[2],b[3]]
        else: s=S[day]; s[0]=max(s[0],b[1]); s[1]=min(s[1],b[2]); s[2]=b[3]
    elif t.time()>=dt.time(16,10) and day not in P: P[day]=b[0]
days=[x for x in sorted(S) if x in P]; ibs={}; p=0; prevF=None; prevC=None
for x in days:
    h,l,c=S[x]; f=P[x]; pnl=0.0; sig=p
    if prevF is not None: pnl=p*1250*(f/prevF-1)
    i=(c-l)/(h-l) if h>l else .5; newp=p
    if p and prevC is not None and c>prevC: newp=0
    elif not p and i<.2: newp=1
    if newp!=p: pnl-=1250*1.5e-4/2*1  # half round trip at each change
    ibs[x]=(newp,pnl); p=newp; prevF=f; prevC=c
# BTC Williams and Donchian, $ at 0.01 lot ~ $630 notional (fixed, for comparability)
raw=load('BTC-USD'); bd=sorted(raw); O=[raw[x][0] for x in bd];H=[raw[x][1] for x in bd];L=[raw[x][2] for x in bd];C=[raw[x][3] for x in bd]
wil={}
for i in range(1,len(bd)):
    lvl=O[i]+0.6*(H[i-1]-L[i-1]); r=(C[i]/max(lvl,O[i])-1-1.5e-4) if H[i]>=lvl else 0.0
    wil[bd[i]]=(1 if H[i]>=lvl else 0, 630*r)
D=dict(dates=bd,O=O,H=H,L=L,C=C); s=E.turtle(20,10)(D,False); intra=[0]+s[:-1]; r=E.returns(D,intra,intra[:],1.5,0,0,False)
don={bd[i]:(intra[i],630*r[i]) for i in range(len(bd))}
allD=sorted(set(ibs)|set(wil))
with open('/mnt/project-files/day-trader-skill-research/signals.csv','w',newline='') as f:
    w=csv.writer(f); w.writerow(['date','ustec_ibs_pos','ustec_ibs_pnl_usd_0.05lot','btc_williams_traded','btc_williams_pnl_usd_0.01lot','btc_donchian_pos','btc_donchian_pnl_usd_0.01lot'])
    for x in allD:
        if x<'2016-01-01': continue
        a=ibs.get(x,('','')); b=wil.get(x,('','')); c=don.get(x,('',''))
        w.writerow([x,a[0],round(a[1],2) if a[1]!='' else '',b[0],round(b[1],2) if b[1]!='' else '',c[0],round(c[1],2) if c[1]!='' else ''])
def corr(a,b):
    ks=[k for k in a if k in b and k>='2016-01-01']; x=[a[k][1] for k in ks]; y=[b[k][1] for k in ks]
    return statistics.correlation(x,y), len(ks)
print('daily P&L correlation, IBS vs Williams %.2f (n %d)'%corr(ibs,wil))
print('daily P&L correlation, IBS vs Donchian %.2f (n %d)'%corr(ibs,don))
print('daily P&L correlation, Williams vs Donchian %.2f (n %d)'%corr(wil,don))
for start in ('2016-01-01','2020-01-01','2024-01-01'):
    for name,parts in (('IBS + Williams',(ibs,wil)),('IBS + Williams + Donchian',(ibs,wil,don)),('IBS',(ibs,)),('Williams',(wil,))):
        eq=0;pk=0;dd=0;worst=0
        dd_days={}
        for x in allD:
            if x<start: continue
            v=sum(p[x][1] for p in parts if x in p); eq+=v; pk=max(pk,eq); dd=min(dd,eq-pk); worst=min(worst,v)
        print('from %s  %-26s net $%+6.0f | worst drop $%5.0f | worst day $%4.0f'%(start,name,eq,dd,worst))
