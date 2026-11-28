import sys; sys.path.insert(0,'.')
from daily import daily
S={s:daily(f'long/{s}.json.gz') for s in ['SPY','TLT','GLD']}
days=sorted(set.intersection(*[set(v) for v in S.values()]))
days=[d for d in days if d>='2023-12-29']
W={'SPY':.6,'TLT':.3,'GLD':.1}
def run(W, start=1000.0):
    val=start; hold={s:val*w/S[s][days[0]][3] for s,w in W.items()}; peak=val; mdd=0; yr=days[0][:4]; curve=[]
    for d in days[1:]:
        if d[:4]!=yr:  # rebalance first day of year at prior close
            yr=d[:4]; prev=days[days.index(d)-1]; v=sum(hold[s]*S[s][prev][3] for s in W)
            v-=v*0.0005; hold={s:v*w/S[s][prev][3] for s,w in W.items()}
        val=sum(hold[s]*S[s][d][3] for s in W); peak=max(peak,val); mdd=min(mdd,val/peak-1); curve.append((d,val))
    return curve,mdd
for name,W in [('60/30/10 SPY/TLT/GLD',W),('100 SPY',{'SPY':1}),('60/40 SPY/TLT',{'SPY':.6,'TLT':.4})]:
    c,m=run(W); 
    ye={}; 
    for d,v in c: ye[d[:4]]=v
    print(name, 'start',days[0],'end',c[-1][0],'final $%.0f'%c[-1][1],'maxDD %.1f%%'%(m*100), {y:round(v) for y,v in ye.items()})
