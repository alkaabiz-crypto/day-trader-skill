import sys; sys.path.insert(0, '/home/user/day-trader-skill/trader-lab')
import candles as K
K.COST.update({"stocks": 1.0, "crypto": 1.5, "daily": 1.0, "daily_crypto": 1.5})
K.main(['run', '--parts', sys.argv[1]])
