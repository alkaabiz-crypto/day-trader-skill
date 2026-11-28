import sys; sys.path.insert(0, '/home/user/day-trader-skill/trader-lab')
import dtc_btc as T
sw = float(sys.argv[1])
T.SPREAD_BPS, T.SWAP_BPS = 1.5, sw
T.returns.__defaults__ = (1.5, sw)
sys.argv = ['dtc_btc.py', 'run']; T.main()
