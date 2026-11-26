# The day-trading brain

The lab's day-trading brain has three parts:
- `KNOWLEDGE.md`: what the published studies say about each part of day trading.
- `brain.py`: the engine that tests them all on the whole US market at once.
- This page: the scorecard. It ties each idea to the lab's own test, in plain words.

Research, not financial advice. Nothing here places an order.

## How the brain works

1. **Know it.** `KNOWLEDGE.md` has a section for each topic:
   - the first 5-minute candle and the opening range
   - wicks and candle patterns
   - gaps
   - relative volume and "stocks in play"
   - VWAP
   - time-of-day effects
   - intraday reversal
   - how day traders actually do
   - costs and other flows (closing auctions, leveraged ETFs, index changes)
2. **Measure it.** At 9:35 New York, when the first 5-minute candle closes, `brain.py` measures 12 features for
   every liquid US stock, about 1,490 a day:
   - the candle's colour and size, upper and lower wick, body, close location and range
   - the gap
   - relative volume (how busy the stock is compared with its normal first 5 minutes)
   - yesterday's return, close location and last 30 minutes
   - colour × relative volume
3. **Test it fairly.**
   - Every feature, rule and pass bar was written down and committed before any data was run.
   - The days are split in time: the first half to learn, the second half to check.
   - Costs are charged, and there's a Bonferroni bar for testing 12 features at once.
   - A 4-year history of 40 stocks serves as an independent check.
4. **Combine it.** One "brain score" mixes all 12 features, fitted on the learning days only. It buys the top
   10% and sells the bottom 10% of the market each day.

## Scorecard (2026-11-24)

| Idea | What traders believe | What the studies say (`KNOWLEDGE.md`) | What the lab measured | Verdict |
| --- | --- | --- | --- | --- |
| First 5-minute candle | A green first candle means up for the day | Only the authors' own backtests are positive; an independent test was about zero after costs | Whole market: t +0.07 learning days, −0.93 check days; 4 years: +1.38 | No edge |
| Wicks (rejection) | A long lower wick is bullish, a long upper wick bearish | No peer-reviewed support; 83 candle rules on 5-minute Dow stocks all failed (Duvinage et al. 2013) | Upper wick +1.19, then −2.59 (sign flips); lower wick −0.08, then +1.89; 4 years: weak | No edge |
| Candle body, close location, range | A strong body or close at the high means continuation | Not supported | All under \|t\| 1.6 on learning days | No edge |
| Gap | Gaps fill | For indexes, moves tend to follow the gap; single stocks depend on news | −0.97, then +1.26 | No edge |
| Relative volume / stocks in play | Busy stocks trend | Promising backtests from the authors; an attention cost is documented | rvol −0.56, then +1.42; colour × rvol −1.34, then +1.75; the lab's earlier stocks-in-play test failed | No edge yet |
| Yesterday's return | Momentum or reversal | Short-term reversal is a known, weak effect | −1.19, then +2.43; 4 years −2.16 (weak reversal, below the bar) | Weak, not tradable after costs |
| End-of-day | Strong closes continue | Single stocks tend to reverse in the last 30 minutes (working paper) | −0.15, then −0.66; 4 years −1.83 | No edge |
| VWAP | Above VWAP means buy | No evidence found | Earlier lab tests: VWAP trend and reclaim all negative | No edge |
| Market intraday momentum | The first half hour predicts the last | Replicated in futures; one variant faded after publication | Earlier lab test on SPY: negative | No edge for us |
| All 12 combined (the brain) | More signals means better |, | Learning days +23.6 bp a day (t 0.74); **check days −100.7 bp a day (t −3.22)**; 4 years −21.3 bp a day (t −3.55) | **Fails** |
| Day traders as a group | Many earn a living | Taiwan: losses after fees in every year studied, under 1% reliably profitable. Brazil: 1.1% earned more than the minimum wage |, | The base rate |

## 2-year rerun (2026-11-26, Polygon, 481 days, ~479 stocks a day)

Unchanged study, 8 times as many days. No feature passes; the first candle is t -1.47 then +0.77, the wicks
under 1 both times, yesterday's return -2.50 then -0.22. The combined brain: validation -27.3 bp a day
(t -2.29); 4-year check -18.4 bp a day (t -2.98). FAIL again.

## What the brain has learned

1. **The first 5-minute candle and its wicks don't predict the rest of the day across the US market.** What
   they seem to show in one month flips in the next. That's the sign of noise, not of a signal.
2. **Combining weak signals makes it worse, not better.** The combined brain fitted noise on the learning days
   and lost on the new days and over 4 years.
3. **Costs decide everything intraday.** Even a correct small edge of a few bp disappears into 5–20 bp of
   spread and slippage.
4. **What has survived anywhere in the lab works over days, not minutes:**
   - short dips in uptrending index funds (`survivors.py`: positive but below its bar)
   - the night before Fed meetings (`fomc.py`, forward test)
   - buying the index and holding it

## How to keep developing it, honestly

- **Add an idea only with its rule written first.** Test one hypothesis at a time and keep the Bonferroni bar.
  Use the whole-market data (`bot_data.py stocks`, rerun every 60 days to grow the history) and the 4-year
  store as a check.
- **Let time be the judge.** Refetching the whole market every 60 days builds a longer whole-market history
  (Yahoo keeps only 60 days of 5-minute data). In a year, `brain.py study` can be rerun with no changes on
  about 250 days.
- **Do not tune a failed rule until it passes.** That's how the brain would learn noise.
