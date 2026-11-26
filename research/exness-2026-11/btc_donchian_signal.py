"""Today's BTC Donchian 20/10 state (pre-registered forward test, 2026-11-26).
Rule: at the 00:00 UTC daily close, if flat and close > highest high of the prior 20 days: buy 0.01 BTCUSD at the next open.
If long and close < lowest low of the prior 10 days: sell at the next open. Long or flat only. No other stop.
Usage: python3 btc_donchian_signal.py path/to/BTC-USD.json (Yahoo chart JSON)"""
import json, sys, datetime as dt
d = json.load(open(sys.argv[1]))['chart']['result'][0]; q = d['indicators']['quote'][0]
rows = [(dt.date.fromtimestamp(t).isoformat(), q['high'][i], q['low'][i], q['close'][i]) for i, t in enumerate(d['timestamp']) if None not in (q['high'][i], q['low'][i], q['close'][i])]
rows = rows[:-1]  # drop today's unfinished UTC day
p = 0; last = None
for i in range(20, len(rows)):
    hi = max(r[1] for r in rows[i-20:i]); lo = min(r[2] for r in rows[i-10:i]); c = rows[i][3]
    if p and c < lo: p = 0; last = ('SELL', rows[i][0], c)
    elif not p and c > hi: p = 1; last = ('BUY', rows[i][0], c)
i = len(rows) - 1
print('as of %s close %.0f: %s | 20-day high to beat %.0f | 10-day low exit %.0f | last signal %s'
      % (rows[i][0], rows[i][3], 'LONG 0.01 lot' if p else 'FLAT', max(r[1] for r in rows[i-19:i+1]), min(r[2] for r in rows[i-9:i+1]), last))
