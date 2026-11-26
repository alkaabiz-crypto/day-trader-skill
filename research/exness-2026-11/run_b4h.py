import sys; sys.path.insert(0,'.')
import engine as E, batch2
for m,c in (('US500',1.0),('USTEC',1.0),('XAUUSD',1.0),('EURUSD',1.2)): E.MARKETS[m]['spread']=c
exec(open('run.py').read().replace("from engine import *","from engine import *\nimport engine as E").replace("RULES = list(SIGNAL) + list(CAL)","RULES = list(E.SIGNAL) + list(CAL)").replace("results.json","results_b4.json"))
