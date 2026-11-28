"""USTEC "IBS at the close" forward-test signal (pre-registered 2026-11-26).
After the 16:00 New York cash close, from QQQ's 9:30-16:00 high, low and close:
  IBS = (close - low) / (high - low).
  If flat and IBS < 0.2: BUY 0.05 lot USTEC between 16:10 and 16:55 New York (01:10-01:55 UAE in winter).
  If long and today's close > yesterday's close: SELL in the same window.
Long or flat. No stop in the backtest; the worst day at 0.05 lot was about -$150.
Usage: python3 ustec_ibs_signal.py  (needs Yahoo access)"""
import json, urllib.request, datetime as dt
u = "https://query1.finance.yahoo.com/v8/finance/chart/QQQ?range=1mo&interval=1d"
d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})))['chart']['result'][0]
q = d['indicators']['quote'][0]
rows = [(dt.date.fromtimestamp(t).isoformat(), q['high'][i], q['low'][i], q['close'][i]) for i, t in enumerate(d['timestamp']) if q['close'][i]]
p = 0
for i in range(1, len(rows)):
    _, h, l, c = rows[i]; ibs = (c - l) / (h - l) if h > l else .5
    act = 'hold'
    if p and c > rows[i-1][3]: p = 0; act = 'SELL'
    elif not p and ibs < .2: p = 1; act = 'BUY'
    print('%s IBS %.2f close %.2f -> %s, now %s' % (rows[i][0], ibs, c, act, 'LONG' if p else 'FLAT'))
print('Note: the state above is replayed over one month only; the last line is what to do after today\'s close.')
