import sys, random, datetime as dt, statistics, math; sys.path.insert(0,'.')
import engine as E
from b5 import ld
import catalog as C
random.seed(3)
B = ld('BTC-USD', adj=False); dates = B['d']
D = dict(dates=dates, O=list(B['o']), H=list(B['h']), L=list(B['l']), C=list(B['c']))
n = len(dates); Cl = D['C']; m200 = E.sma(Cl, 200); m50 = E.sma(Cl, 50)
wd = [dt.date.fromisoformat(d).weekday() for d in dates]
def mayer():
    s=[]; p=0
    for i in range(n):
        if m200[i] is None: s.append(0); continue
        x = Cl[i]/m200[i]
        if p and x > 1.5: p = 0
        elif not p and x < 1.0: p = 1
        s.append(p)
    return s
def volf():
    r = [0]+[math.log(Cl[i]/Cl[i-1]) for i in range(1,n)]; v=[None]*n
    for i in range(30,n): v[i]=statistics.pstdev(r[i-29:i+1])
    s=[0]*n
    for i in range(400,n):
        med = statistics.median([x for x in v[i-365:i] if x is not None]); s[i] = 1 if v[i] < med else 0
    return s
def tom():
    s=[0]*n
    for i in range(n):
        d=dt.date.fromisoformat(dates[i]); nxt=d+dt.timedelta(days=1)
        # decide at close of day i for holding day i+1
        days_left=( (d.replace(day=28)+dt.timedelta(days=4)).replace(day=1) - nxt).days
        s[i]= 1 if (nxt.day<=3 or days_left<2) else 0
    return s
cp = C.build(B)
SIG = dict(buyhold=[1]*n, sma200=[0 if m200[i] is None else int(Cl[i]>m200[i]) for i in range(n)], mayer_dip=mayer(),
           donchian=E.turtle(20,10)(D, False), cross50_200=[0 if m200[i] is None else int(m50[i]>m200[i]) for i in range(n)],
           vol_filter=volf(), weekend=[1 if wd[i] in (3,4,5) else 0 for i in range(n)],  # decided Thu..Sat close -> held Fri,Sat,Sun
           weekdays=[1 if wd[i] in (6,0,1,2,3) else 0 for i in range(n)], tom=tom(),
           coppock=list(cp['coppock'][1].astype(int)), trix=list(cp['trix_15'][1].astype(int)))
js = next(i for i,d in enumerate(dates) if d>='2020-01-01'); y24 = next(i for i,d in enumerate(dates) if d>='2024-01-01')
bh=None
for name, s in SIG.items():
    intra = [0]+s[:-1]; over = intra[:]
    r = E.returns(D, intra, over, 1.5, 0, 0, False); r2 = E.returns(D, intra, over, 1.5, 0, 0, False, mult=2)
    IS, J, J2 = E.stats(r[:js]), E.stats(r[js:]), E.stats(r2[js:])
    if name=='buyhold': bh=J['sharpe']
    si, so = intra[js:], over[js:]; Dj = dict(dates=dates[js:], O=D['O'][js:], C=Cl[js:]); b=0
    for _ in range(200):
        k=random.randrange(30,len(si)-30)
        if E.stats(E.returns(Dj, si[k:]+si[:k], so[k:]+so[:k], 1.5,0,0,False))['mean'] < J['mean']: b+=1
    v,dd = E.growth([x*0.63 for x in r[y24:]])  # one 0.01 lot ~ $630 exposure on a $1,000 account
    ok = IS['mean']>0 and J['t']>=3 and J['sharpe']>bh and J2['mean']>0 and b/200>=.95 and name!='buyhold'
    print('%-11s IS t %5.2f | judged t %5.2f Sharpe %5.2f | 2x t %5.2f | placebo %3.0f%% | $1,000 acct from 2024 (0.01 lot) $%.0f worst %.0f%% | %s' % (name, IS['t'], J['t'], J['sharpe'], J2['t'], b/2, v, dd*100, 'PASS' if ok else 'FAIL'), flush=True)
