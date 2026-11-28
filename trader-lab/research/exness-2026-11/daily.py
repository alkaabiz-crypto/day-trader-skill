"""Build daily closes (New York regular session) from the repo's 5-minute stores."""
import gzip, json, datetime as dt
from zoneinfo import ZoneInfo
NY = ZoneInfo("America/New_York")
REPO = "/home/user/day-trader-skill/trader-lab/data/"
def daily(path, session=True):
    d = json.load(gzip.open(REPO + path))
    out = {}
    for k in sorted(d, key=int):
        t = dt.datetime.fromtimestamp(int(k), NY)
        if session and not (dt.time(9,30) <= t.time() < dt.time(16,0)): continue
        b = d[k]; day = t.date().isoformat()
        o,h,l,c = b[0],b[1],b[2],b[3]
        if day not in out: out[day] = [o,h,l,c]
        else:
            r = out[day]; r[1]=max(r[1],h); r[2]=min(r[2],l); r[3]=c
    return out
