# Candlesticks: what they are, how they form, every type, and what the tests say

A guide to the candles `candles.py` tests. The exact definitions in the code are the ones below.

## 1. What a candle is

A candle summarizes all trading in one period (5 minutes, 1 hour, 1 day) with four prices:

| price | meaning |
| --- | --- |
| **Open (O)** | the first trade of the period |
| **High (H)** | the highest trade |
| **Low (L)** | the lowest trade |
| **Close (C)** | the last trade |

```
        |   <- upper wick (shadow): from the top of the body to the HIGH
      +---+
      |   |  <- body: between OPEN and CLOSE
      |   |     green / hollow = close above open (buyers won the period)
      +---+     red / filled   = close below open (sellers won the period)
        |   <- lower wick (shadow): from the bottom of the body to the LOW
```

- **Range** = High - Low: how far price travelled.
- **Body** = |Close - Open|: how far it moved net.
- **Upper wick** = High - max(Open, Close): price went up there, then was pushed back down (selling).
- **Lower wick** = min(Open, Close) - Low: price went down there, then was pushed back up (buying).

### How a candle rises and falls while it forms

A candle isn't fixed until its period ends. In a 5-minute bull candle, price opens, maybe dips first (that dip
becomes the lower wick), then rises to a high (the top of the upper wick), and ends somewhere below or at the
high (the close). The same final candle can come from different paths inside it. That's one reason candles
carry less information than they seem to: two identical candles can hide different stories.

## 2. The "wick" candle (pin bar, rejection candle)

A **wick candle** has one long wick and a small body. It shows that price went far in one direction during the
period and was rejected.
- **Long lower wick** (hammer, dragonfly doji): sellers pushed down, buyers pushed it all the way back. Read as
  bullish.
- **Long upper wick** (shooting star, gravestone doji, inverted hammer): buyers pushed up, sellers pushed it
  back. Read as bearish.

The tests use two versions: a strict one (the hammer and shooting star shapes) and a loose one (any candle whose
wick is at least half its range: `lower_wick` / `upper_wick`).

## 3. Single-candle types (checked in this order; R = range)

| type | rule | textbook reading |
| --- | --- | --- |
| **Doji** | body <= 10% R | indecision: open and close almost equal |
| Dragonfly doji | doji, lower wick >= 60% R, upper <= 10% | bullish rejection of lows |
| Gravestone doji | doji, upper wick >= 60% R, lower <= 10% | bearish rejection of highs |
| Long-legged doji | doji, both wicks >= 30% R | strong indecision |
| **Marubozu** | body >= 90% R (almost no wicks) | one side in full control; continuation |
| **Hammer** | lower wick >= 2x body and >= 60% R, upper <= 15% | bullish, after a fall (a "hanging man" after a rise) |
| **Shooting star** | upper wick >= 2x body and >= 60% R, lower <= 15% | bearish, after a rise (an "inverted hammer" after a fall) |
| **Spinning top** | body <= 30% R, both wicks >= 25% | indecision |
| **Long candle** | body >= 70% R | strong move; continuation |
| Plain bull / bear | anything else | colour only |

## 4. Multi-candle patterns (daily candles, from Nison 1991)

Reversal patterns only count after the trend they reverse (5-day move before the pattern).

| pattern | candles | shape | reading |
| --- | --- | --- | --- |
| Bullish engulfing | 2 | red, then a green body that covers it | reversal up |
| Bearish engulfing | 2 | green, then a red body that covers it | reversal down |
| Bullish harami | 2 | long red, then a small body inside it | reversal up |
| Bearish harami | 2 | long green, then a small body inside it | reversal down |
| Piercing line | 2 | long red, gap down, green closing above its midpoint | reversal up |
| Dark cloud cover | 2 | long green, gap up, red closing below its midpoint | reversal down |
| Tweezer bottom / top | 2 | two equal lows / highs, colours flip | reversal |
| Morning star | 3 | long red, small candle, green past the first one's midpoint | reversal up |
| Evening star | 3 | long green, small candle, red past the first one's midpoint | reversal down |
| Three white soldiers | 3 | three strong green candles, each closing higher | continuation up |
| Three black crows | 3 | three strong red candles, each closing lower | continuation down |

Inside bar (range inside the previous one) and outside bar (range covers the previous one) carry no direction
of their own. They go into the combined model only through the candle shape features.

## 5. The first 5-minute candle

The first candle of a session holds the opening auction and the overnight news, with the most volume of the day.
The idea is that its direction and shape say who controls the day. Sessions tested:
- **Stocks and ETFs:** 9:30-9:35 New York, 40 names, 4 years.
- **Bitcoin and Ethereum:** they trade 24/7, so there is no real "open". Two choices are tested: the UTC day open
  (00:00) and the US stock open (9:30 New York), when US volume arrives.

Trade rule: enter at the next candle's open, hold to the session's last close, no stop.

## 6. What the tests found

`candles.py` was pre-registered in b96edb6. There are 81 tests, and a pass needs t >= 3.5 on data after the
fitting period. Full numbers are in `results/candles.json` and RESEARCH.md.
- **First 5-minute candle on 40 stocks:** all 11 rules FAIL (best: long bull candle +7 bp/day, t 0.98).
- **20 classic daily patterns across 30 markets:** all FAIL, and most point the wrong way after costs.
  Yahoo's daily FX candles carry bad high/low prints that create fake dojis, so the doji rows are distorted
  there. Without FX they are still nothing.
- **Everything combined** (a ridge model on all candle features): FAIL on stocks and on daily markets.
- **Bitcoin and Ethereum:** see RESEARCH.md once the download finishes.

Bottom line: candle shapes describe the past period well, but on their own they don't predict the next one
after costs. The market already reflects that information when the candle closes.
