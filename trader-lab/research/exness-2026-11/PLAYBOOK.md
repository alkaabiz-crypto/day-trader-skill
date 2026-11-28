# Playbook: the two rules that survived (Exness swap-free, small account)

Research, not financial advice. Demo first: run both on the Exness demo (or the paper ledgers) until each clears its review bar. Going live is your decision.

## Account size
- **$1,000 is the smallest sensible size.** One minimum lot of each rule is about $1,250 (USTEC) and $630 (BTC) of exposure.
- **$228 is too small.** The two rules together dropped up to $242 since 2016 at minimum lots, more than the whole account. At $228, 1:200 leverage lets you open the trades, but one bad stretch could wipe the account.
- Never add gold: its 0.01 minimum lot is about $3,740, 3.7x a $1,000 account.

## Rule 1: USTEC "IBS at the close" (about 36 trades a year)
1. After the 4:00 pm New York cash close (1:00 am UAE in winter, midnight in summer), take QQQ's 9:30-16:00 high, low and close (or USTEC's for the same hours).
2. IBS = (close - low) / (high - low).
3. **Flat and IBS < 0.2: BUY 0.05 lot USTEC** between 4:10 and 4:55 pm New York.
4. **Long and today's close > yesterday's close: SELL** in the same window.
5. No take-profit. Disaster stop: -$150 at 0.05 lot (3,000 points below the fill), about the worst trade since 2000.
- Backtest 2016-2026 (realistic 4:10 pm fills): t 4.27; +$539 at 0.05 lot since 2024, worst drop -$108.
- Weak spot: long bear markets (it was flat in 2000-02 and 2008).

## Rule 2: BTCUSD Williams volatility breakout (about 120 trades a year)
1. At 00:00 UTC (4:00 am UAE), compute level = today's open + 0.6 x yesterday's high - low (UTC day).
2. **Place a buy-stop for 0.01 lot BTCUSD at the level.** Cancel it if not filled by the end of the day.
3. If filled: protective stop $100 below (0.01 lot = $10,000 of BTC price; never hit in the backtest). **Close at 23:55 UTC** (3:55 am UAE).
- Backtest 2020-2026: t 5.96; +$562 at 0.01 lot since 2024, worst drop -$150, worst day -$34.
- Weak spot: the last two years alone are only t 1.2. The edge may be fading.

## Together
- Daily P&L correlation between the two: 0.08 (almost independent).
- Since 2016 at minimum lots: worst combined drop -$242, worst combined day -$95. Since 2024: +$1,100, worst drop -$149.
- **Hard stop for both: if the two together are $300 below their combined peak, stop both and review.** The paper ledgers apply it automatically.
- Left out: BTC Donchian 20/10 (correlated 0.43 with Rule 2, and adding it pushes the combined worst drop to -$371).

## Before going live (fixed review bars)
- USTEC IBS: 30+ closed paper trades, net > $0, t >= 2, never stopped.
- BTC Williams: 60+ paper trades, net > $0, t >= 2, never stopped.
- Check in MT5 that the after-hours USTEC spread and the BTC spread match what was assumed (USTEC 1.12 pt, BTC $6.40).
- Start at the minimum lot. Don't raise size after a good week.
