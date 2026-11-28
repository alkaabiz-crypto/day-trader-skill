import sys; sys.path.insert(0, '/home/user/day-trader-skill/trader-lab/oilbrain'); sys.path.insert(0, '/home/user/day-trader-skill/trader-lab')
import brain as B
c, n = float(sys.argv[1]), float(sys.argv[2])
B.COST_BPS, B.NIGHT_BPS = c, n; B.run.__defaults__ = (c, n)
B.main(['study'])
