import sys; sys.path.insert(0,'.')
import engine as E, batch2
from yload import load
E.MARKETS.clear()
E.MARKETS['US500']=dict(src=lambda: load('SPY',adj=True), spread=1.0, swl=6.5, sws=1.0, split='2013-01-01', ls=False)
E.MARKETS['USTEC']=dict(src=lambda: load('QQQ',adj=True), spread=1.0, swl=6.5, sws=1.0, split='2013-01-01', ls=False)
src=open('run.py').read().replace("from engine import *","from engine import *\nimport engine as E").replace("RULES = list(SIGNAL) + list(CAL)","RULES = list(E.SIGNAL) + list(CAL)").replace("results.json","results7.json")
exec(src)
