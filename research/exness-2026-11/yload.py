import json, datetime as dt
Y='/tmp/claude-0/-home-user/a2ae9b93-f4ce-530a-aef6-aecc10044afa/scratchpad/yahoo/'
def load(sym, adj=False):
    d=json.load(open(Y+sym+'.json'))['chart']['result'][0]; q=d['indicators']['quote'][0]; a=d['indicators']['adjclose'][0]['adjclose']
    out={}
    for i,t in enumerate(d['timestamp']):
        o,h,l,c=q['open'][i],q['high'][i],q['low'][i],q['close'][i]
        if None in (o,h,l,c) or o<=0: continue
        f = a[i]/c if adj and a[i] else 1.0
        out[dt.date.fromtimestamp(t).isoformat()]=[o*f,h*f,l*f,c*f]
    return out
