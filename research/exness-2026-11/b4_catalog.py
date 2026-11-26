import sys, argparse
sys.path.insert(0, '/home/user/day-trader-skill/trader-lab')
import catalog as C
orig = C.strategy_returns
C.strategy_returns = lambda D, pos, cost: orig(D, pos, 0.75 if cost == 20.0 else 0.5)
sys.argv = ['catalog.py', 'run']
C.main()
