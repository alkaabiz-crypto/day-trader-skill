# Strategy Lab research journal

Newest entry first under "Log". Every entry: the date, what was tested, the
result after costs, and whether it was kept. Failures stay in the record.

## The evidence base

| idea | source | what it claims |
| --- | --- | --- |
| Most day traders lose | Chague, De-Losso & Giovannetti (2020), [Day Trading for a Living?](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3423101) | 97% of Brazilian individuals who day traded mini-index futures for 300+ days lost money; no evidence of learning |
| 5-minute ORB | Zarattini & Aziz (2023), [Can Day Trading Really Be Profitable?](https://papers.ssrn.com/abstract=4416622) | trade the first 5-minute bar's direction on QQQ/TQQQ; profitable 2016 to 2023 in their backtest |
| ORB on stocks in play | Zarattini, Barbon & Aziz (2024), [A Profitable Day Trading Strategy for the U.S. Equity Market](https://abarbon.com/papers/a-profitable-day-trading-strategy-for-the-u-s-equity-market) | limiting ORB to the top-20 stocks by relative opening volume lifts results a lot |
| Noise area | Zarattini, Aziz & Barbon (2024), [Beat the Market](https://www.sfi.ch/de/publications/n-24-97-beat-the-market-an-effective-intraday-momentum-strategy-for-s-p500-etf-spy), SFI 24-97 | SPY: trade breaks of a band built from the average move-from-open over 14 days, trail at max(band, VWAP) |
| Market intraday momentum | Gao, Han, Li & Zhou (2018), [Market intraday momentum](https://econpapers.repec.org/RePEc:eee:jfinec:v:129:y:2018:i:2:p:394-414), JFE 129(2) | SPY 1993 to 2013: the first half hour's return predicts the last half hour's (R2 1.6%), stronger on volatile, high-volume days |
| Replication warning | [MQL5 replication of the ORB paper](https://www.mql5.com/en/blogs/post/776235) | gross results reproduced on five index CFDs, net of costs about zero |

## Current strategies

| name | rule | variants |
| --- | --- | --- |
| orb5 | first 5-min bar green: long, red: short; stop at its other end, or none | stop |
| orb | first close outside the first 15 or 30 minutes' range, before 11:30 | range, stop at mid or opposite |
| noise | at each half hour, close outside open-or-prev-close x (1 +- k x sigma_t), trail at max(band, VWAP) | lookback 10/14, k 1.0/1.5 |
| imom | sign of prev close to 10:00 return, held 15:00 or 15:30 to the close | entry time, min move |
| vwap | side of VWAP at 10:00 or 10:30, exit on a close through VWAP | decision time |
| gap | gap over 0.5% or 1%: fade it or go with it, stop at the first bar's extreme | size, mode |
| sip | stocks in play: only today's top names by first-5-min relative volume (vs 14 days) trade the 5-min ORB, entering on a break of the first bar's high/low | top 5/10, rvol 1.0/1.5, stop 10% of ATR14 or the first bar's range |

## Research plan (widened 2026-11-24)

The lab has tested about 53 million timing rules, and none beats luck after costs. The plan widens
the question from "which signal beats the market?" to "what reliably improves an investor's result?".
That covers the premia that survive publication, what investors can actually buy, how to put money
in, and whether our own tests can be trusted. Every item is pre-registered and tests one hypothesis
(or uses a Bonferroni bar). No more giant searches after the 62-market one.

**A. Done 2026-11-24** (see Log):
- factor premia before and after publication (`factors.py`)
- investable factor ETFs vs SPY (`factor_etfs.py`)
- lump sum vs spreading in (`dca.py --lump`)
- power of the paper-trial bar (`power.py`)

**B. Next, in order:**
1. ~~**Portfolio mixes for the monthly plan, without forecasting.**~~ Done 2026-11-24 (`mixes.py`, see Log). Stocks with bonds and gold (100/0,
   80/20, 60/40, a three-way mix) on ETFs since 2004, rebalanced yearly. Measure the cost in return
   of each step down in drawdown, so the plan's mix can be chosen by risk tolerance. `parity.py`
   data is reused.
2. **Forward ledger.** Score every rule that ever came close (`results/frozen.json`) on new data
   only, monthly, in the daily run. Out of sample in real time is the one test that can't be
   overfitted.
3. ~~**Crypto cross-sectional factors.**~~ Done 2026-11-24 (`crypto_xs.py`): FAIL, see Log. Liu, Tsyvinski & Wu (2022, JF) "Common Risk Factors in
   Cryptocurrency": coin momentum, size and market. Pre-registered, weekly, on the top coins. Caveat:
   dead coins are missing from Yahoo, so a pass would need a survivorship audit.
4. ~~**FOMC and CPI days.**~~ FOMC done 2026-11-24 (`fomc.py`): overnight version PASS, on forward test; CPI not done. Lucca & Moench (2015) pre-FOMC drift, using the Fed's public meeting
   calendar, run as a control (reported dead after 2015).
5. **FX carry.** Lustig, Roussanov & Verdelhan (2011) carry needs each country's interest rate. On
   Exness, carry *is* the swap, so test the swap-inclusive version only. Needs a rates source; FRED
   is not on the network allowlist.
6. **Survivorship-free S&P 500** (membership history). Unlocks single-stock momentum and reversal
   without survivor bias, and an honest retest of R3. Needs a membership source not yet allowed on
   the network.

**C. Older queue** (kept):

- **Oil term structure:** download individual CL / BZ contract months (Yahoo `CLF27.NYM`-style
  tickers) to build front-minus-second spreads; test backwardation-only longs and basis momentum.
- **Oil events:** a hand-built OPEC / OPEC+ decision list (2000+) and EIA release dates
  (holiday shifts); DCA with a 252-day-high trigger and a hard stop (agent rule 30).

0. **Survivorship-free test of R3**: add stocks that fell hard or were delisted (e.g. from an
   S&P 500 membership history), or test on many more ETFs and country funds. Until then R3 is
   unproven.
1. ~~**R3 on a wider ETF set**~~ done 2026-11-23: FAILED after 2014 (see Log). R3 stays unproven.
2. **New strategies from the web**: each daily run adds at least one rule not yet tested.
3. **Forward test**: score R3 and the near misses on sessions after 2026-11-22 (`daily.py forward`).
4. **Last-half-hour reversal on the 5-minute store**, pre-registered after imom's OOS t of -3.6 (judged only after 2026-11-20).
5. **Stocks in play on 4 years of the 40-name universe**: `fetch-tiingo --symbols <universe>` (free
   plan: 500 tickers a month, about 50 requests an hour, so about 14 hours for 40 names). The paper's top-20-of-7,000
   is still out of reach; 40 names is a weak test. The same store also unlocks `eodrev`.
5b. ~~Tighten the 5-minute keep rule~~ done 2026-11-23 (OOS t >= 3). A placebo gate for the 5-minute
   engine is still open.
6. **FOMC and CPI days** (needs an event calendar): pre-FOMC drift (Lucca & Moench 2015) is reported dead after 2015, so a control, not a hope.
7. **Earnings-day drift and the earnings announcement premium** for single stocks (needs an earnings calendar from trader-analyst).

## Log

### 2026-11-25: fix round for the video strategy, 32 standard fixes chosen on 2022-2024 only (`orb_retest_fix.py`). FAIL

The owner asked to "fix the fails". Pre-registered in b403823. The base was orb_retest on QQQ, with each of these
fixes alone and each also long-only, at 2R and 3R:
- trend: prior close vs its 20-day average;
- rvol: opening-range volume 1.5x its 14-day average;
- gap direction;
- narrow or wide range vs the prior 20-day median;
- fade the break;
- plain breakout entry with no retest.

The best in-sample version (at least 150 trades) was to be judged once on 2025 on.

- No fix reaches even in-sample t 1. The best is "wide range, 3R" at +1.8 bp, t 0.88. Judged, that one lost
  -1.6 bp a trade (t -0.64), and $500 became $485 against $620 holding QQQ. FAIL.
- Fading the break loses most of all (t -7.5 to -10). With the stop inside the zone both ways, the retest level
  gets whipsawed in both directions. The setup has no direction to exploit, so it can't be fixed with filters.
- The lab's other fails already had their fix rounds: the 53M-variant searches, the swarm and the catalog. That
  produced the one lead now on a forward test, the Bitcoin 200-day trend bot.

### 2026-11-25: the owner's second video strategy, opening range + break-and-close + retest (`orb_retest.py`). FAIL

The video is NAS100. It marks the 9:30-9:45 high and low; on the 5-minute chart it waits for a candle to close
outside them; "no chase price": it buys the retest of the broken level, with a small stop inside the zone and a
much bigger target. Pre-registered in 0e563fb:
- QQQ stands in for NAS100, with SPY and IWM alongside, on 4 years of 5-minute bars;
- the entry is a limit at the broken level until 11:30;
- the stop is 25% of the range back inside it, and the target is 3R (2R and 5R reported);
- worst-case fills, 3 bps costs, judged from 2025.

| QQQ | 2022-2024 | 2025 on | $500 since 2025 |
| --- | --- | --- | --- |
| 3R (primary) | 439 trades, -0.5 bp, t -0.48, 29% wins | 395 trades, -2.0 bp, t -1.47, 27% wins | $462 |
| 2R | -1.0 bp, t -1.15 | -2.6 bp, t -2.41 | $451 |
| 5R | +0.4 bp, t 0.26 | -3.1 bp, t -1.90 | $442 |

QQQ held over the same time turned $500 into $620. SPY and IWM lose at every target too, in both periods
(SPY in-sample t -4.4 to -6.3). The retest fills mostly on days the break fails: about 70% of trades stop out.
FAIL.

### 2026-11-25: the strategy catalog, 60 named public strategies on 10 markets (`catalog.py`). 0 PASS; trend following on crypto stands out

The owner asked for every strategy on the internet. Posted variants number in the millions, but most are a few
dozen ideas with different settings, and trying settings until one wins is how false discoveries are made. So
each distinct named strategy appears once, with its published settings. Sources:
- TradingView's built-in strategies: MACD, Supertrend, Parabolic SAR, Price Channel, InSide/OutSide Bar,
  Consecutive Up/Down, BarUpDn, Greedy, Volty Expan Close, Stochastic Slow, RSI, MovingAvg Cross / 2Line;
- Investopedia's indicators: Ichimoku, ADX/DMI, Aroon, Vortex, TRIX, KST, Coppock, CCI, Williams %R, MFI,
  Ultimate, OBV, Chaikin MF, A/D, Hull, Elder impulse, Heikin Ashi, chandelier, pivots, envelopes, DPO;
- the classic books: Turtle S1/S2, Keltner, Bollinger, TTM squeeze, NR7, Connors RSI(2);
- papers: Faber 10-month, 12-month TSMOM, Halloween, low-vol regime.

The rules were pre-registered in 81d9237, before any data was downloaded:
- markets: SPY QQQ IWM EFA EEM TLT GLD USO BTC ETH;
- long or flat, with next-open fills;
- costs of 5 bps (crypto 20 bps);
- the statistic is the rule's alpha over holding, scaled by its in-sample beta;
- the judged period starts in 2016, and PASS needs t >= 3.5.

The first run had a bug in the moving-average helper: a leading NaN blanked the rest of the series, so KST and
Stochastic Slow never traded. It was fixed with tests, and the rerun didn't change any other row.

Results:
- **0 PASS.** The best are Coppock t 3.49, TRIX t 3.44, 12-month TSMOM t 3.29, golden cross t 3.28, Faber
  t 3.15 and the 200-day SMA t 3.14. Ten trend rules are Benjamini-Hochberg significant at 5%, but all have
  in-sample t of only about 1.
- **Reading:** the judged alpha of every trend rule comes almost entirely from BTC and ETH (BTC t 3.1-3.9),
  by sitting out crypto's crashes. On stocks, bonds, gold and oil they are t 0-2. Only TRIX ended ahead of
  holding the 10 markets in equal parts ($17,574 vs $15,928 from $500 since 2016). The others ended behind.
- **Mean reversion loses everywhere:** RSI 30/50, Bollinger, CCI, Williams %R, IBS, MFI, Keltner, the envelope
  and the z-score are all negative judged. The one-day bar patterns are the worst: BarUpDn t -4.07, Greedy
  -3.67, inside bar -2.80.
- **Lead, not a pass:** trend following on Bitcoin. The lab's crypto_search.py (844k BTC candidates with
  Reality Check) passed nothing, so this needs its own pre-registered forward test before it means anything.

### 2026-11-25: the bots crypto platforms sell (AstraBit/3Commas/Bybit style), BTC with $500 (`bot_types.py`). FAIL

Pre-registered in a4332f9. It uses BTC 5-minute candles from Nov 2022 to Mar 2025, 0.1% fees and worst-case
fills inside a candle; the judged period starts in 2024.

| bot | $500 became 2024 to Mar 2025 | BTC held | since Nov 2022 | BTC held | max drawdown | verdict |
| --- | --- | --- | --- | --- | --- | --- |
| DCA bot: $100 plus four $100 buys at -2/-4/-6/-8%, +2% target, -15% stop | $572 | $991 | $888 | $2,045 | 22% | FAIL (t 0.73) |
| Grid bot: 10 levels, +-10%, reset monthly | $558 | $991 | $579 | $2,045 | 8% | FAIL (t 1.09) |

Both make a little and lag holding badly, because small take-profits sell the rallies. These were bull-market
years, where both designs lag the most. Platform fees (AstraBit $0.33-1.33 a day) are not even charged here.

### 2026-11-24: four more ideas, each backtested on a $500 account (`calendar2.py`, `insiders.py`, `congress.py`). All FAIL

Pre-registered in 9c02e46 before any data was downloaded or any return computed. "$500 became" holds the rule's
positions and T-bills otherwise, net of costs, over the judged years. The SPY column is $500 bought and held over
the same years.

| idea | before | judged | $500 became (judged) | $500 in SPY | verdict |
| --- | --- | --- | --- | --- | --- |
| FOMC cycle, even weeks (Cieslak et al. 2019) | 1994-2016 +8.8 bp/day, t 3.99 | 2017 on +2.0 bp/day, t 0.63 | $724 | $1,871 | FAIL |
| Day before a holiday (Ariel 1990) | before 2010 +5.5 bp, t 0.58 | 2010 on +10.5 bp, t 1.73 | $752 | $4,331 | FAIL |
| Options-expiration week | before 2010 +24 bp/week, t 1.28 | 2010 on +0.9 bp, t 0.06 | $623 | $4,331 | FAIL |
| Insider buying clusters (3+ insiders, $100k+, SEC Form 4) | 2014-19 +1.15%/mo vs SPY, t 2.05 | 2020 on -1.15%/mo, t -1.60 | $431 | $1,228 | FAIL |
| Copying House members' disclosed stock buys | 2019-21 +0.34%/mo vs SPY, t 0.48 | 2022 on -0.89%/mo, t -2.18 | $616 | $806 | FAIL |

Notes:
- The FOMC cycle is the clearest case of a published effect disappearing. It is strong in the paper's own
  sample (t 4) and gone after it.
- Insiders: 9,378 clusters from 372,233 open-market purchases (2014 Q1 to 2026 Q1). Yahoo had no prices for
  3,763 of them, mostly delisted companies. That survivor bias flatters the result, and it still failed.
- Congress: 4,627 House PTRs (2019 to today), 3,808 readable (the rest are scanned paper), 10,835 stock
  purchases. Entry is on the public filing date, not the trade date, because a copier can't know before that.
- The timing rules sit in T-bills most of the time, so they lag buy-and-hold badly even where their days earn
  a little.

Nothing here is kept.

### 2026-11-24 13:12: the paper bots, version 2 (owner's request): full market, every 15 minutes, three books

- **orb**: the same skill chain (scan > entry > exit > size > risk), but the scanner now covers the full US
  market. That is 5,925 names from Nasdaq Trader's lists, of which about 800 are liquid enough (price >= $5,
  >= 500k shares). Runs are every 15 minutes, 9:37 to 15:52. Only breakouts whose trigger candle closed in the
  last 30 minutes are bought. Its 60-day clock restarts 2026-11-25. First v2 buy: BBY at 13:12.
- **fed**: the pre-registered PASS (`fomc.py` H2) traded on paper. It buys SPY at the 15:52 run before each
  scheduled FOMC announcement and sells at the next open. First trade: buy 2026-12-08, sell 2026-12-09.
- **sip**: stocks in play (the near-miss) traded live on paper with resting stop orders placed at 9:37 on
  the lab's 40 names. Its first orders are on 2026-11-25.

Each book has its own $10,000, ledger (`trader-lab/autopaper/<book>_*.csv`) and line on the desk. No real orders.

### 2026-11-24: plan B4, pre-FOMC drift (`fomc.py`, Lucca & Moench 2015). H1 FAIL, **H2 PASS (first pre-registered pass)**

Pre-registered in b6d3290 before any return was computed. The events are the 263 scheduled FOMC announcements
from Feb 1994 to Oct 2026, taken from the Fed's own pages (federalreserve.gov, newly allowed in the environment).
Conference calls, notation votes, unscheduled and cancelled meetings are excluded. The rule as written counts
the Fed's separate 15 and 16 Sep 2003 entries twice: one extra in-sample event, kept as registered. Costs are
2 bps round trip, and the judged period starts in 2012.

| | 1994-2011 (145) | 2012 on (118) | placebo p | verdict |
| --- | --- | --- | --- | --- |
| H1 SPY close before to close of FOMC day, over T-bills | +30.4 bp, t 2.96 | +8.1 bp, t 0.84 | 0.318 | FAIL |
| H2 SPY close before to the open of FOMC day | +9.5 bp, t 1.62 | **+13.7 bp, t 3.53** | 0.024 | **PASS** |

At 5 bps, H2 after 2012 is +10.7 bp, t 2.76. Checks that don't change the verdict:
- both halves are positive: 2012-18 +6.9 bp (t 1.65), 2019-26 +19.8 bp (t 3.16);
- without the best 5 events: +7.8 bp, t 2.66;
- 61% of events are positive, median +6.7 bp;
- no event day is ex-dividend;
- ordinary nights since 2012 average +2.8 bp, and non-FOMC Wednesday nights +4.8 bp;
- the FOMC day's own open-to-close is -4.9 bp, t -0.59.

The drift has moved: it now comes overnight, before the open, rather than in the paper's 2pm-to-2pm window.
Close-to-close it's gone.

What it's worth: about +14 bp on each of 8 nights a year, roughly 1% a year of the money used. It's real
evidence but small. It's one pass among about a dozen pre-registered hypotheses today. At t 3.5 chance is an
unlikely explanation, but not impossible. **Kept as a forward test, not live:** events after 2026-11-24 are
scored separately (`forward_H2`). The desk shows the next date: FOMC 2026-12-09, so the rule buys SPY at the
2026-12-08 close and sells at the 12-09 open, on paper.

### 2026-11-24: same-month seasonality across sector and country ETFs (`seasonal_xs.py`). FAIL

Pre-registered in 6db6e66 before any data was downloaded (Heston & Sadka 2008; Keloharju, Linnainmaa & Nyberg
2016). The universe is 9 sector SPDRs and 20 country ETFs, all 29 served. The signal is each ETF's mean return
in the same calendar month over the past 5 years. Each month the portfolio is ranked into thirds: H1 is top
minus bottom, H2 is top minus the set. Costs are 10 bps a side, and the judged period starts in 2012.

| at 10 bps | 2001-2011 (129 mo) | 2012 on (178 mo) | placebo p | verdict |
| --- | --- | --- | --- | --- |
| H1 top third minus bottom third | -0.52%/mo, t -2.43 | -0.63%/mo, t -4.03 | 0.993 | FAIL |
| H2 top third minus the set | -0.26%/mo, t -2.16 | -0.33%/mo, t -3.90 | 0.993 | FAIL |

Before costs (descriptive): H1 -0.26%/mo (t -1.19) in-sample and -0.35%/mo (t -2.23) after 2012. That is
sectors -0.50%/mo and countries -0.20%/mo after 2012. The rest is cost: the thirds change almost completely
every month. In ETFs the same-month effect doesn't just fail, it points slightly the wrong way. Betting the
other way was not pre-registered, and its in-sample t is only 1.2, so it is an observation, not a candidate.
Not kept.

### 2026-11-24: the bots trade on their own, on paper, every market hour (`autopaper.py`)

The owner asked for the bots to scan, decide and buy without asking. Real orders are out (CLAUDE.md, no broker
access here, and no rule has a proven edge), so this is fully automatic **paper** trading. Every weekday at
:52 past each hour from 9:52 to 15:52 New York, the skills run in a chain: scan (ORB, 40 names), then entry
check, exit plan (stop at the range midpoint, 2R target), sizing, and the risk check. A PASS is filled on paper
at the last 5-minute close plus 2 bps. The rules were frozen before the first run: $10,000 account, $50 risk a
trade, 3 open, 4 buys a day, no buys after 15:00 or once the day is down $150, everything sold at 15:50+,
5 bps round trip. Verdict after 60 trading days: LIVE-REVIEW only if P&L > 0, it beats SPY over the same days,
and the daily t >= 2. Otherwise FAIL. The lab's ORB results so far (none passed after costs) say to expect FAIL.
The ledger is in `trader-lab/autopaper/`. First run 10:46: paper buys CRM, MSFT, NFLX.

### 2026-11-24: plan B3, crypto coin momentum (`crypto_xs.py`, Liu, Tsyvinski & Wu 2022). FAIL

Pre-registered in 9f6bff6 before any coin data was downloaded: 78 coins fixed in advance (dead ones
included), weekly, past 3-week return, terciles, 25 bps a side, judged on weeks from 2021, PASS needs t >= 3.
Yahoo served 74 (MIOTA, MATIC, LUNA1 and COMP were missing, so they were dropped mechanically). That leaves
468 weeks, Dec 2017 to Nov 2026, with an average of 53 eligible coins.

| at 25 bps | 2018-2020 (160 wk) | 2021 on (308 wk) | verdict |
| --- | --- | --- | --- |
| H1 long top third, short bottom third | +1.27%/wk, t 1.95 | -0.40%/wk, t -1.18 | FAIL |
| H2 top third minus all coins | +0.73%/wk, t 1.89 | -0.22%/wk, t -1.05 | FAIL |

At 10 bps the judged period is still negative (H1 -0.17%/wk, t -0.50). The momentum the paper found in
its own 2014-2020 sample is there in 2018-2020 and gone after publication, which is the usual pattern. The
shuffled-rank placebo (p 0.11 / 0.17) is lenient here: random ranks trade far more, so they pay far more in
costs. It doesn't change the verdict. LUNA's absence makes the result, if anything, too kind to the long
side. Not kept.

### 2026-11-24: stocks in play and end-of-day reversal on 40 names x 4 years (`sip_long.py`). FAIL

Pre-registered (commit 66d2f0a) while the download had 5 of 40 names. lab.backtest's own gates, unchanged:
IS = first 50% of the 995 sessions (to 2024-11-19), OOS to 2025-11-21, HOLDOUT after; PASS at both 3 and
5 bps round trip. Tiingo IEX 5-minute bars, half days cut at 13:00. `results/sip-long.json`.

| strategy | chosen on IS | 3 bps: IS t / after IS | 5 bps: IS t / after IS | verdict |
| --- | --- | --- | --- | --- |
| stocks in play (Zarattini, Barbon & Aziz 2024) | top 5, rvol 1.5, bar stop | 0.69 / +9.6 bp/day, t 2.02 | 0.31 / +7.6 bp/day, t 1.60 | FAIL |
| end-of-day reversal (Baltussen, Da & Soebhag 2025) | long losers, k 8 / k 4 | -2.96 / -1.3 bp/day, t -0.66 | -4.25 / -4.1 bp/day, t -1.74 | FAIL |

Stocks in play is the closest any 5-minute rule has come: positive in OOS and HOLDOUT (6.5 and 8.6 bp a day
at 5 bps), with every bar-stop variant positive after IS. But it did nothing in the period it was chosen in (IS
t 0.31-0.69) and stays under the t >= 3 bar. With 40 survivors instead of the paper's top 20 of 7,000 stocks,
this is "not shown here", not refuted; it goes on the watch list, not into the signal. The paper's
10%-of-ATR stop loses heavily (t -4.5 to -7.4; 10-11% win rate): that stop is too tight for these names.
End-of-day reversal did the opposite of the paper: buying the day's biggest losers at 15:30 lost money in
every variant (both sides, k 8: IS t -9.2, after IS t -3.8). Into the close, losers kept losing.

### 2026-11-24: news as a signal, post-earnings drift on 30 stocks (`news_events.py`). FAIL, no news edge

Pre-registered (commit d30874a, text fix a0e96c0) before any data was fetched. Events: every SEC 8-K with
item 2.02 (earnings release) for the 30 single stocks, 2,320 reaction days; reaction day = first close after
the filing's acceptance time in New York. Rule: after a reaction of at least k%, follow it (or long only),
enter at the next close, hold H days; score = return minus the equal-weight return of all 30 stocks, minus
10 or 20 bps. Grid of 12 (k 2/4, H 5/20/60, both/long), chosen on IS 2006-2014; OOS 2015-2020; HOLDOUT
2021+. t-stats over monthly averages. Placebo: the same rule on big moves with no earnings filing within 5
trading days, resampled to the same trade count 1,000 times.

Chosen on IS: **k 4%, hold 20 days, long only** (long after an earnings jump of 4%+). Means are bp per
trade (20-day hold), averaged by month:

| cost | IS t (207 tr, mean) | OOS (178 tr) | HOLDOUT (208 tr) | post-IS t (386 tr, mean) | big moves w/o earnings | placebo p |
| --- | --- | --- | --- | --- | --- | --- |
| 10 bp | 1.12 (56.3 bp) | 84.3 bp, t 1.43 | 37.3 bp, t 0.32 | 0.92 (60.4 bp) | 89.6 bp | 0.625 |
| 20 bp | 0.92 (46.3 bp) | 74.3 bp, t 1.26 | 27.3 bp, t 0.24 | 0.77 (50.4 bp) | 79.6 bp | 0.625 |

Verdict: **FAIL**. Not even the best IS variant reaches t 2 (1.12), post-IS t is under 1, and the placebo
kills it outright: buying after big up days *without* earnings news earned more (89.6 bp) than after
earnings jumps (60.4 bp); 62.5% of random placebo draws beat the real trades. Whatever positive drift there
is in these names (survivor-biased winners) comes from "big move", not from the news. Consistent with the
literature saying post-earnings drift has largely gone in large caps. The news skill stays a context tool,
not a signal.

Data checks: about 4 earnings 8-Ks a year for US filers (SHOP 8, ARM 0: foreign filers, as stated). Spot
checks: AAPL 2015-01-27 after close -> 2015-01-28 +5.7%; NFLX 2013-10-21 -> 10-22 -9.1%; META 2022-02-02 ->
02-03 -26.4%; XOM's pre-market filings react the same day. Two execution fixes made after the first fetch
and before the test ever ran (design untouched): (1) SEC's acceptanceDateTime is UTC, not Eastern as the
code assumed (Apple's 16:30 ET releases are stamped 20:30Z/21:30Z), now converted to New York time; (2)
SEC's ticker map points only at today's registrant, which had dropped history for XOM (2 events; a 2026
holding-company reorganisation), GOOGL (Google Inc. before 2015) and AVGO (Avago, Broadcom Ltd); their
predecessor CIKs are now included (XOM 128, GOOGL 93, AVGO 72). Results: `results/news-events.json`.
Research, not financial advice.

### 2026-11-24: plan item B1, stock / bond / gold mixes (`mixes.py`, descriptive)

Rebalanced each January, 2005-01 to 2026-10, dividends reinvested, 5 bp per unit of turnover:

| mix | per year | volatility | Sharpe | deepest drop | 2008 | 2022 |
| --- | --- | --- | --- | --- | --- | --- |
| SPY 100 | 10.7% | 14.8% | 0.65 | 51% | -36.8% | -18.2% |
| 80/20 SPY/IEF | 9.6% | 11.7% | 0.69 | 39% | -25.9% | -17.6% |
| 60/40 | 8.2% | 8.9% | 0.73 | 27% | -14.9% | -17.0% |
| 60/30/10 with gold | 8.9% | 9.2% | 0.79 | 27% | -16.2% | -15.5% |
| 40/40/20 with gold | 8.2% | 7.7% | 0.83 | 18% | -6.6% | -13.5% |
| VT 80 / IEF 20 (from 2009) | 9.7% | 12.4% | 0.70 | 24% | n/a | -17.4% |

- Each step down in risk cost about 1 to 1.5 points of yearly return, and roughly halved the worst crash.
- Bonds failed as a hedge in 2022, when stocks and bonds fell together.
- Gold helped over this window, but its 2005-2026 run is hindsight and may not repeat.
- No mix is "best": the right one is the deepest drop the owner can sit through without selling.

### 2026-11-24: widened plan, part A. Only the market premium survives; no factor ETF beats SPY; the trial bar was too lenient

The user asked to widen the research plan (see "Research plan" above). Four pre-registered studies:

**1. Factor premia before and after publication** (`factors.py`, Ken French data 1926-07 to 2026-09,
long-short, gross of costs, Newey-West t):

| factor | paper | in-sample mean (t) | after publication (t) | decay | last 10 years (t) | verdict |
| --- | --- | --- | --- | --- | --- | --- |
| MKT | equity premium | n/a | +0.75%/month (3.61), from 1990 | n/a | +1.09 (3.41) | SURVIVES |
| SMB | Banz 1981 | +0.18 (1.28) | +0.04 (0.33) | 78% | -0.22 (-0.80) | no |
| HML | Fama-French 1992 | +0.42 (2.63) | +0.17 (0.86) | 61% | -0.01 (-0.03) | no |
| UMD | Jegadeesh-Titman 1993 | +0.82 (4.32) | +0.40 (1.65) | 52% | +0.26 (0.85) | no |
| RMW | Novy-Marx 2013 | +0.28 (2.55) | +0.15 (0.91) | 46% | +0.18 (0.85) | no |
| CMA | Fama-French 2015 | +0.32 (3.49) | -0.04 (-0.18) | 112% | -0.04 (-0.17) | no |

The average decay is about 70%, worse than McLean & Pontiff's 58%. Only the plain equity premium
holds up, and these figures are before costs.

**2. Factor and style ETFs vs SPY** (`factor_etfs.py`, 15 funds, after fund fees, Bonferroni bar
t >= 2.94). **None adds alpha.**
- Best alphas: momentum MTUM +1.1%/yr (t 0.48), Nasdaq 100 QQQ +1.2% (t 0.46).
- Low-volatility funds (USMV, SPLV): smaller drawdowns (19-21% vs 24%) but lower return.
- World fund VT: -3.3%/yr alpha vs SPY (t -3.12), because US stocks beat the rest of the world from
  2008 to 2026. That is hindsight: no rule picked the US in 2008.

For the monthly plan, a plain index fund is the right choice. Factor tilts haven't paid.

**3. Lump sum vs spreading in** (`dca.py --lump`, $12,000, all at once vs over 12 months with the
waiting cash in T-bills):
- All at once ended ahead 73% of the time (SPY and VT, 10-year horizon), by +2.9% to +3.6% on average.
- Worst case for all at once: -29% (start in mid-2008).

This matches Vanguard's 2012 study. Spreading in buys peace of mind, not return.

**4. Power of the paper-trial bar** (`power.py`). The trial's exact rules, replayed on 995 sessions
of 5-minute bars (2022-11 to 2026-11):
- 422 signal days, 778 trades.
- Net -1.33 bp a trade at 2 bp cost (t -1.68). The prior is no edge, slightly negative.
- Same-day trades correlate 0.93, so a per-trade t counts one bet two or three times.

| scenario | passes with per-trade t | passes with daily t |
| --- | --- | --- |
| null (zero edge) | **11.2%** | 3.1% |
| 2022-2026 as it was | 6.3% | 1.8% |
| real +5 bp edge | 34.2% | 16.3% |

Median trial length: **38 trading days**, not 20, because 30 trades take that long.
- **Amendment** (`paper/PLAN.md`, stricter only): the bar also needs t >= 2 on daily P&L.
- Honest reading: the trial mainly guards against luck. With 30 trades it can't confirm a small real
  edge, and the 4-year replay already leans negative.

Tests: 4 new files, all passing.

### 2026-11-24: the swarm, 100,000 machine-generated timing rules on 129 ETFs (`swarm.py`). No real edge

Pre-registered (commit 89b6f14) before any rule was scored: 100,000 random rules from a grammar of 28
features (past returns, distance from averages, RSI, distance from highs/lows, volatility ratio), IS
percentile thresholds, an optional second condition and a 1-20 day hold; long only; one day of delay; 10
and 20 bps per turnover. 129 ETFs, 1998-2026. IS 1998-2012 picks the top 1,000; OOS 2013-2019 keeps those
passing a 5% false discovery rate; HOLDOUT 2020+ needs t >= 3. Luck benchmark: the same pipeline on rules
whose signals are slid in time.

| | rules | best IS t | IS t >= 3 | OOS survivors | HOLDOUT PASS |
| --- | --- | --- | --- | --- | --- |
| real | 100,000 | 5.20 | 1,576 | 850 | 2 |
| luck (time-shifted) | 1,000 | 1.92 | 0 | 0 | 0 |

Nearly every survivor is one idea: **buy funds trading far below their 52-week high, hold 5-20 days**.
The two "passes" were `ret_120 < p50 AND hi_250 < p5, hold 5d` (HOLDOUT t 3.01) and
`ret_250 < p10 AND ret_20 > p30, hold 20d` (t 3.22).

**They are an artifact of my scoring, not edges.** The pre-registered score subtracted each fund's
trailing 250-day mean return to remove market drift. After a deep fall that trailing mean is strongly
negative, so merely holding a beaten-down fund on a flat day counted as a gain, which rewards exactly
"buy deep drawdowns". Re-scored fairly (10 bps):

| rule | baseline | IS t | OOS t | HOLDOUT t |
| --- | --- | --- | --- | --- |
| A (ret_120, hi_250, 5d) | trailing drift (as run) | 4.34 | 3.24 | 3.01 |
| A | raw return | 2.70 | 1.72 | 2.01 |
| A | vs all funds' average that day | 3.26 | 1.18 | 1.07 |
| B (ret_250, ret_20, 20d) | trailing drift (as run) | 3.90 | 1.99 | 3.22 |
| B | raw return | 2.05 | 0.21 | 1.87 |
| B | vs all funds' average that day | 2.20 | -1.27 | -0.07 |

Against the fair baselines neither rule is significant after 2012. Verdict: **FAIL; the design flaw was
mine and is recorded here so it is not repeated.** What survives as a weak, honest observation: deeply
beaten-down ETFs rebounded slightly more than the average fund in 1998-2012 (IS t 3.26), much less since
(t about 1). That is the dip-buying family again (R3, RSI(2)), and it fades the same way. A rerun would
score timing against the same-day cross-sectional average; it would be a new pre-registration, not a
retune of this one.

### 2026-11-24: the plan, a cost stress test for the paper trial, and the index-fund yardstick

The user asked what is smart to do now and approved the plan in `INVESTING-PLAN.md`:
- real money goes into a monthly index-fund plan
- trading stays on the Exness demo until the paper trial passes
- the scans are a watchlist, not buy signals
- no more giant searches after the 62-market one

**Paper trial cost stress** (`paper.py`, `paper/PLAN.md` amendment, stricter only). The bar now also
needs the trial to be net positive at 5 bp per round trip, against the assumed 2 bp. Day 1: +$9.00 at
5 bp; it breaks even at 35 bp a trade. No swap applies, because every trade is flat by 15:55 New York.

**Index-fund yardstick** (`dca.py`): $500 a month, bought at the month's first open, dividends reinvested.

| fund | period | put in | worth now | per year | deepest drop | 10-year windows ahead |
| --- | --- | --- | --- | --- | --- | --- |
| SPY | 1996–2026 | $185,500 | $1,242,273 | 10.5% | −51% | 95% (worst −9.4%/yr, 1999–2009) |
| VT | 2008–2026 | $111,000 | $325,327 | 10.6% | −34% | 100% (worst +3.6%/yr) |

These are history, not forecasts.

### 2026-11-23 (daily run, 21:41 UTC): everything rerun, five pre-registered anomalies. No pass

**Paper trial** (pre-registered 15:30 reversal): day 1, 3 shadow trades, net +$9.90. IN PROGRESS;
it needs 20+ days and 30+ trades. Scanner track (simulated): 3 trades, net -$10.53.

**Oil track** (SIMULATED):
- DCA ladder: first-layer BUY at the next open on both USOIL and UKOIL. Each closed more than 20%
  below its 20-day high (USO 133.36 vs 168.83; BNO 56.66 vs 71.39).
- MA-cross candidate: flat on both.
- Oil backtest: 0 candidates passed every gate.

**Reruns.** Nothing reached PASS anywhere:
- 5-minute, 60-day: best after-IS t 1.46 (noise).
- Long 5-minute store, 995 sessions: every chosen rule's after-IS t is between -1.91 and 0.52.
- Hourly: best post t 0.68.
- Daily: best post t 0.97 (tuesday).
- Trend: no rule beats equal-weight.
- Frozen rules: day 1 of forward data, too early to judge.
- Tiingo: +156 bars each for SPY, QQQ and IWM (995 sessions).

**New: `anomalies.py`, five pre-registered single hypotheses** (no tuning; a PASS needs after-2014
t >= 3 and a positive IS t):

| rule | source | IS t | after-2014 t |
| --- | --- | --- | --- |
| dash_avoid: out over the 3 sessions into the month-end selling day T-(settlement+1); the window moves with the 2017 (T+2) and 2024 (T+1) settlement changes | Etula, Rinne, Suominen & Vaittinen 2020, RFS | 1.46 | 0.56 |
| dash_revert: long from the selling day to the 3rd session of the next month | same | 1.51 | 0.26 |
| li_yu: DIA, regression on nearness to the 52-week and historical highs, fitted to 2014, monthly | Li & Yu 2012, JFE | 0.81 | -0.56 |
| vix_spike: VIX >= 1.2x its 10-day average, long 5 days | Connors & Alvarez practitioner rule | 1.35 | -0.51 |
| hv_down: down day on 1.5x volume, long 5 days | Gervais, Kaniel & Mingelgrin 2001 | 0.74 | -0.68 |

All five fail. "Dash for cash" was positive before 2015 but has faded since, including in the
window that follows the settlement changes.

### 2026-11-23 (twelfth run): Bitcoin 844,664 and Ethereum 863,003 candidates. No pass

`crypto_search.py`: 199 conditions known at the daily close. Combined alone, as AND pairs and as
"A and not B" pairs; long-while, long-unless or short-while; held 1 to 30 days. Plus entries with
take-profit / stop / time exits. Conditions from the crypto literature:
- time-series momentum (Liu & Tsyvinski 2021) and moving-average ratios (Detzel et al. 2021)
- Mayer multiple, RSI, MACD, Bollinger, stochastics, streaks, volatility regimes
- distance from the all-time high, volume shocks, the ETH/BTC ratio
- stocks, VIX, the dollar, gold, rates, credit, oil and copper
- weekday and weekend, month, turn of month, the halving cycle

Next-open fills, 10 bp per change, T-bill cash, Jensen's alpha against buy-and-hold. The gate is
SPA plus Romano-Wolf, computed in chunks (a test checks that it matches the in-memory version
exactly). A second test checks that no condition changes when future data is cut off.

| | BTC-USD | ETH-USD |
| --- | --- | --- |
| judged after | 2019-12-31 (2,518 days) | 2021-06-30 (1,971 days) |
| candidates | 844,664 | 863,003 |
| best alpha t | 4.10 (13.2 bp/day) | 3.86 (13.7 bp/day) |
| SPA p / Reality Check p | 0.807 / 0.263 | 0.917 / 0.927 |
| Romano-Wolf critical t, rules above | 6.55, 0 | 6.69, 0 |
| t >= 3 | 531 | 117 |
| 20 best before, mean t after | 0.48 | 0.86 |
| correlation of t before / after | 0.19 | 0.12 |

- **BTC:** the best rule after 2019 is "ETH up yesterday and RSI14 > 70, long 21 days" (t 4.10).
  Before 2020 it had IS t 0.16.
- **ETH:** the best rule is "Tuesday when TLT rose over 30 days, long 1 day" (t 3.86, IS t 0.56).
  That is calendar noise.
- **Reading:** no edge beyond the luck of trying ~850k rules on either coin. Many candidates beat
  buy-and-hold's Sharpe (91k on BTC, 204k on ETH), but ETH's buy-and-hold Sharpe after mid-2021 was
  only 0.24, which makes that comparison easy and meaningless.
- **Not included:** Exness swap on crypto CFDs, which would make multi-day holds worse.

### 2026-11-23 (eleventh run): 203,968 S&P 500 candidates, and a check of the test itself. No pass

**What was tested.** `sp500_search.py`: 148 published conditions on SPY, used alone, as AND pairs,
as "A and not B", and as entries with take-profit / stop / time exits. That makes 203,968 candidates.
Conditions cover technicals, VIX and its term structure, variance risk premium, yield curve, credit,
copper/gold, oil, the dollar, breadth and the calendar. Scored as Jensen's alpha against buy-and-hold
(beta estimated before 2015), with T-bill cash and 2 bp costs, judged only after 2014 (2,991 days).

**Result.** Best alpha t 4.02 (4.74 bp/day). 181 candidates had t >= 3, none reached Bonferroni
(5.16), and 20,700 beat buy-and-hold's Sharpe (0.66; best 1.32). The two multiple-testing checks
disagreed: **Reality Check p = 0.030, SPA p = 0.693.** The best rules after 2014 had nothing before
2015 (IS t -1.62 to 0.15). A portfolio of the top-K chosen before 2015 scored t -0.36 (K=1) to
0.73 after 2014.

**Is the test good? Calibration on null data.** I fixed the decision rule before running: if
the Reality Check rejects at 5% on 2 or more of 12 null datasets, it is miscalibrated here. The
null data is the same pipeline (27,280 candidates: all singles plus 3,000 sampled pairs) with SPY's
returns circularly shifted against the signals. This destroys any real edge but keeps the
volatility clustering and fat tails.

| data | best t | Reality Check p | SPA p |
| --- | --- | --- | --- |
| real | 3.87 | 0.060 | 0.495 |
| shift 4205 | 3.22 | 0.565 | 0.860 |
| shift 4387 | 3.38 | 0.410 | 0.790 |
| shift 2621 | 3.17 | 0.675 | 0.950 |
| shift 1375 | 3.74 | **0.030** | 0.605 |
| shift 2211 | 4.41 | 0.260 | 0.270 |
| shift 3461 | 3.61 | 0.125 | 0.640 |
| shift 4776 | 3.39 | 0.140 | 0.775 |
| shift 1984 | 3.34 | 0.375 | 0.880 |
| shift 6047 | 3.48 | 0.455 | 0.800 |
| shift 6421 | 3.88 | **0.005** | 0.525 |
| shift 1851 | 3.87 | 0.105 | 0.475 |
| shift 1649 | 3.68 | 0.470 | 0.645 |

- **Reality Check:** p < 0.05 on 2 of 12 null shifts, which meets the rule, so it is
  **miscalibrated for this setting**. It compares raw means, so the most volatile rules (long-hold,
  levered-looking combinations) dominate its maximum.
- **SPA** (studentized): never below 0.27 on null data. It behaves.
- **Real data:** best t 3.87 sits inside the null range (3.17 to 4.41), so the real result looks
  like what pure luck produces from this many tries.

**Decision.**
- The S&P 500 search is **not a pass**.
- The gate in `universe_search.py` and `sp500_search.py` is now **SPA p < 0.05 AND at least one rule
  above Romano-Wolf's studentized max-t critical value** (first step of StepM). The Reality Check
  is printed for information only.
- `tests/test_universe.py::GateCalibration` checks the gate on synthetic rules: on/off copies of a
  fat-tailed, volatility-clustered market at 0.3x to 5x leverage. It passed 0 of 40 null sets and
  caught a planted 40 bp/day edge. The synthetic data did not reproduce the Reality Check's false
  alarms (0 of 40), so the evidence for dropping it is the real-data calibration above.
- **Diagnostic re-run** (1,000 bootstrap samples, two seeds): Reality Check p 0.028 / 0.028, SPA
  0.726 / 0.723, so the conflict is not bootstrap noise. The rule with the largest mean
  (`andnot:vix9d>vix&!pres_y2`, long 20 days, 4.74 bp/day, after-2014 t 3.26, before t 0.93) has a
  daily volatility of 79 bp. That is above the 90th percentile of all 203,968 candidates (median
  46 bp, max 98 bp). The unstudentized Reality Check rewards exactly this kind of high-volatility
  rule, which is consistent with the null calibration.
- The earlier universe runs are unchanged in substance: their best Reality Check p was QQQ 0.076,
  with SPA 0.31 to 0.91, so nothing there passed either way.

### 2026-11-23 (tenth run): fair scoring, entry x exit rules, and the first candidate to clear the bar

The user challenged the "everything fails" result. Two fair points, both fixed in `universe_search.py`:
(1) excess return over buy-and-hold punished lower exposure, so rules are now scored by Jensen's alpha
against buy-and-hold (beta from data before 2015) and by Sharpe, with uninvested money earning
T-bills; (2) entries now also exit by take-profit x stop-loss x time stop (64 entries x 6 x 6 x 4).
Overnight and session returns now compound exactly. The engine matches an independent loop to 0.0.

147,984 tests (24,664 per asset). Many rules look good risk-adjusted (50% positive alpha on SPY, 910
beat its Sharpe, 21 with t >= 3), but no Reality Check / SPA p < 0.05 (QQQ closest, 0.076); the best
after-2014 rules mostly had NEGATIVE records before 2015, the signature of luck.

**Pre-selected portfolios** (top-K by pre-2015 alpha only, judged after 2014; 30 tests, Bonferroni bar
t 2.94): mostly positive but weak (t 0.6-1.8), except **USO, K = 1: alpha t 3.16**. The rule: when
WTI's 40-day average crosses above its 50-day, long for 25 sessions. Before 2015 t 3.84. After 2014:
Sharpe 0.85 (USO buy-and-hold 0.05), 16.9% a year, max drawdown -28%, long 32% of the days.

| audit | result |
| --- | --- |
| 19 neighbouring settings | all positive, t 0.98-2.76 (40/50 is the peak: expect less) |
| hold 15-50 sessions | all positive (30: t 3.26) |
| costs 10 / 20 bp | t 3.09 / 2.96 |
| one-day delay | t 2.71 |
| Brent (BNO) | t 1.55 |
| SPY / QQQ control | -1.77 / -0.26 (oil-specific, like commodity trend-following) |

(An audit script first gave t 2.36: it built a long/short version, a different rule. Traced and fixed;
the engine's 3.156 reproduces exactly.) **Status: candidate, not proven.** Frozen in
`results/frozen-oil.json` and added to `oil.py today` as the second simulated oil track; judged only
on sessions after 2026-11-23.

### 2026-11-23 (ninth run): 78,864 technical rule tests with data-snooping corrections

`universe_search.py` rebuilds the rule universe of Sullivan, Timmermann & White (1999, Journal of
Finance; filter rules, moving averages, support/resistance, channel breakouts, OBV, with bands,
delays and holding periods) and adds RSI, Stochastic, CCI, MACD, Bollinger, rate of change,
ADX/DI, Keltner, Donchian, IBS, streak and calendar rules: 6,572 rules, each long/flat and
long/short = 13,144 per asset, on SPY, QQQ, IWM, DIA, USO and BNO. Next-open fills, 2 bp (ETFs) or
5 bp + 1 bp/night (oil) costs, dividend-adjusted prices. Judged only after 2014, as excess return
over buy-and-hold, with White's Reality Check (2000) and Hansen's SPA (2005) on 500 stationary-
bootstrap resamples. Tests show the bootstrap gives p > 0.2 on noise and p < 0.01 on a planted edge.

| asset | best rule after 2014 | Reality Check p | SPA p | t >= 3 | beat buy-and-hold | top-20 IS rules after 2014 |
| --- | --- | --- | --- | --- | --- | --- |
| SPY | t 1.84 (RSI(9) mean reversion) | 1.000 | 0.722 | 0 | 0.4% | avg t 0.73 |
| QQQ | t 1.41 | 1.000 | 0.956 | 0 | 0.2% | avg t -1.17 |
| IWM | t 1.34 | 0.970 | 0.978 | 0 | 1.6% | avg t -0.90 |
| DIA | t 0.87 | 0.996 | 1.000 | 0 | 0.2% | avg t -0.58 |
| USO | t 2.07 (4.5% filter) | 0.592 | 0.670 | 0 | 29.9% | avg t 0.73 |
| BNO | t 2.00 (MA 15/25, 50-day hold) | 0.846 | 0.716 | 0 | 7.9% | avg t 0.36 |

No technical rule beats buy-and-hold by more than the luck of trying this many. The oil numbers
look better only because holding USO/BNO lost to roll costs, so any rule that is often out of oil
"beats" it: avoiding a bad benchmark, not an edge. The best stock rules to 2014 decayed to
negative afterwards on QQQ, IWM and DIA, the post-publication decay McLean & Pontiff (2016)
describe. This matches Sullivan, Timmermann & White (1999: no rule survives after 1986) and
Psaradellis et al. (2019, oil).

Running totals: stocks about 300 hand-built rules + 52,576 universe tests; oil 293 + 26,288
universe tests. Passed every gate: 0.

### 2026-11-23: the user's video strategy, ORB + 10-minute close + 20 EMA pullback (`orb_ema.py`). FAIL

From a short video by a prop-firm Nasdaq trader (payout screenshots shown as proof): mark the
9:30-10:00 range, wait for a 10-minute candle to close outside it, then enter on a pullback to the
2-minute 20 EMA. Pre-registered (commit a2ccec4) before the run: QQQ, 4 years of 5-minute Tiingo bars
(the 2-minute 20 EMA approximated by a 5-minute EMA(8), same 40-minute span), 24 variants of stop
(entry bar or range edge), target (2R, 3R, close), EMA (8, 20) and sides (both, long-only), chosen on
in-sample t; 1.5 and 3 bps per round trip.

| QQQ, chosen: range-edge stop, hold to close, EMA 8, both sides | IS (275 trades) | OOS (135) | HOLDOUT (125) | post-IS t | placebo p |
| --- | --- | --- | --- | --- | --- |
| 1.5 bps | +2.2 bp, t 0.83 | -6.8 bp | +7.7 bp | 0.05 | 0.27 |
| 3 bps | +0.7 bp, t 0.26 | -8.3 bp | +6.2 bp | -0.46 | 0.27 |

SPY and IWM: post-IS t 1.50 and 0.22 at 1.5 bps, below zero or near it at 3 bps. Even the best of all 24
variants picked with hindsight reaches only post-IS t 1.01. Why: two-thirds of trades are stopped out (the
pullback usually goes back to the range edge), and the winners don't cover them. This rule's
core, a 30-minute opening-range breakout, had already failed here (`orb`, 2026-11-23 second run); the EMA
pullback entry does not rescue it. The video's evidence is payout screenshots, which show withdrawals but not
losses, fees or failed accounts, so they say nothing about the rule's edge.

### 2026-11-23 (eighth run): oil predicts stocks; volatility-managed oil

`oil.py cross` (monthly, next-open fills, T-bill cash, dividends counted; CAGR / Sharpe / max drawdown):

| strategy | source | to 2014 | 2015-2021 | 2022+ |
| --- | --- | --- | --- | --- |
| SPY buy-and-hold | benchmark | 6.2% / 0.29 / -55% | 14.8% / 0.83 / -34% | 10.5% / 0.43 / -25% |
| SPY only after an oil down month | Driesprong, Jacobsen & Maat 2008, JFE | 4.6% / 0.24 / -42% | 4.0% / 0.29 / -34% | 12.0% / 0.68 / -17% |
| USO buy-and-hold | benchmark | -5.6% / -0.21 / -83% | -14.5% / -0.18 / -90% | 20.2% / 0.57 / -36% |
| USO + volatility targeting | Moreira & Muir 2017 | -1.2% / -0.16 / -55% | -10.7% / -0.25 / -77% | 17.0% / 0.53 / -31% |
| USO + drawdown control | | -0.6% / -0.13 / -58% | -5.1% / -0.18 / -63% | 13.9% / 0.57 / -18% |

Oil -> stocks works only after 2022 and lost badly before: the published effect has faded. Vol
targeting and drawdown control cut the oil drawdowns but cannot fix the return. The warning for
the user: holding oil through a rolling instrument lost 14.5% a year in 2015-2021 (contango roll
drag, -90% drawdown). A long USOIL CFD held for months pays the same drag; the simulated DCA
track's 120-day time stop exists for this reason.

### 2026-11-23 (seventh run): the oil futures curve (backwardation, basis momentum)

The strongest economic case for oil returns is the term structure: when the front contract trades
above the next one (backwardation), long holders earn the roll (Gorton, Hayashi & Rouwenhorst 2013;
Erb & Harvey 2006). Two attempts:

1. **USO-vs-front proxy (withdrawn).** ln(front change) - ln(USO change) = the roll jumps, but USO
   stopped holding only the front month in April 2020, so the proxy said "contango" in March 2022's
   steep backwardation. Removed from the search; documented in `oil.py`.
2. **The real curve from the EIA** (`www.eia.gov`, now allowed): daily settlements of WTI contracts
   1 and 2 since 1983. Sanity check passes: contango Mar 2009 (-5.4%), 2015-16 (-3.8 to -5.2%),
   Apr 2020 (-14.5%); backwardation Mar 2022 (+3.2%). **The EIA stopped this series in April 2024**,
   so the holdout is 2022 to 2024-04 only; live values now come from Yahoo's active contracts.

| rule (on USO, next-open fills, 5 bp + 1 bp/night) | chosen on data to 2014 | IS t | OOS t | HO t | after 2014 | verdict |
| --- | --- | --- | --- | --- | --- | --- |
| backwardation long (`o_curve`) | F1 > F2 and a positive 63-day trend | 2.53 | 0.97 | 0.36 | 0.91 | best oil candidate yet, not a pass |
| basis momentum (`o_bmom`, Boons & Porras Prado 2019) | 63-day | 1.63 | -0.72 | 0.63 | -0.21 | fails |

Backwardation + trend is the only oil rule positive in all three periods, with the strongest
theory behind it, but t 0.91 after 2014 is far from 3. It joins the watch list. On 2026-11-23 the
live curve (CLF27 80.39, CLG27 79.34, CLH27 78.21) is in backwardation (+1.3%), but oil's 63-day
trend is down after the 22% fall, so the rule is flat. 288 oil variants now; none passes.

### 2026-11-23 (sixth run): oil (WTI / Brent, Exness USOIL / UKOIL), 279 candidates, none pass

`oil.py` runs the lab's gates on oil. Same-day rules on CL=F / BZ=F front-month futures (the roll
happens between sessions, so it never touches them); multi-day rules and DCA ladders on USO / BNO
(real funds that pay the monthly roll, like a long CFD held for days) with 1 bp a night financing;
Brent-WTI spread; hourly NYMEX-session rules incl. the Wednesday 10:30 EIA report hour.
5 bp a round trip. A research agent brought 32 oil-specific rules; the codable ones are in.

| family | variants | best after 2014 (t) | passed |
| --- | --- | --- | --- |
| same-day on futures (RSI(2), pre-holiday, 80-20, gaps, Crabel/Williams, day of week, month, EIA day) | 105 | RSI(2) day trade 1.38 | 0 |
| multi-day on funds (Connors family, Donchian, trend, seasonal holds) | 60 | Donchian 20 1.20 | 0 |
| DCA ladders (drop 5-20%, step 3-8%, 3-5 layers, TP 3-10%) | 72 | 1.18 | 0 |
| Brent-WTI spread z-score | 12 | -0.45 | 0 |
| hourly (first hour, overnight gap, EIA hour, time of day) | 30 | 0.75 | 0 |

The DCA lesson: the ladder chosen on data to 2014 (first buy 20% below the 20-day high, up to 5
layers 8% apart, sell at +3% on average cost) won 94% of its 32 campaigns (+3.9% each), yet its
t was -0.89 to 2014 and 1.07 after: the rare losers (2008, 2014-16, 2020) are enormous. A high
win rate is not an edge. This matches Psaradellis et al. (2019, European Journal of Finance):
7,846 technical rules on CL/USO, none persistently profitable after data-snooping controls.

Not testable yet with our data (strongest economic logic): term structure / roll yield
(Gorton, Hayashi & Rouwenhorst 2013) and basis momentum (Boons & Porras Prado 2019) need the
second-month contract; EIA surprise rules need consensus forecasts; OPEC rules need an event list.

The user asked for daily oil trades from 2026-11-24: `oil.py today` runs that DCA ladder as a
SIMULATED track on USOIL / UKOIL (signals from USO / BNO). On 2026-11-23 oil was ~20-26% below
its 20-day high (WTI futures 104.12 -> 80.56 since 2026-10-29), so both ladders open tomorrow.

### 2026-11-23 (fifth run): paper trial starts

The user wants to day trade, chose paper trading first, a live budget under $1,000 and Exness.
The best remaining day-trading candidate (the 15:30 reversal, pre-registered idea 4) now runs as
a pre-registered paper trial: `paper/PLAN.md` (rule, limits, pass bar, written before the first
trade), `paper.py` (tickets at 15:31 New York, a shadow log of every ticket, the user's demo
fills, and a report against the bar). Honest prior: about 0 bp a trade net of 2 bp on
2022-2026. Replaying 2026-11-20: three buy tickets (QQQ -5.1%, SPY -3.2%, DIA -1.6% by 15:30),
all lost about 35-41 bp to 15:55, -$11.50 in total at $1,000 notional each.

### 2026-11-23 (sixth run): risk parity and equal weight, no forecasting (`parity.py`). FAIL

If every timing rule fails, maybe the answer is how to hold, not when. Pre-registered in `parity.py`:
inverse-volatility weights on the nine ETFs or on SPY/EFA/IEF/GLD, and 1/N on the nine, monthly,
vs 60/40 (alloc.py's Part B setup). After IS at 20 bps (`results/parity.json`):

| rule | chosen | Sharpe (60/40) | CAGR (60/40) | max DD (60/40) | OOS Sh | HOLDOUT Sh | boot p | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ivol9 | 63 days | 0.41 (0.70) | 5.4% (8.7%) | -18.1% (-18.8%) | 0.58 vs 0.91 | 0.26 vs 0.49 | 1.00 | FAIL |
| ivol4 | 63 days | 0.58 (0.70) | 6.2% (8.7%) | -16.2% (-18.8%) | 0.89 vs 0.91 | 0.38 vs 0.49 | 0.79 | FAIL |
| ew9 | | 0.52 (0.70) | 7.2% (8.7%) | -17.8% (-18.8%) | 0.60 vs 0.91 | 0.44 vs 0.49 | 0.93 | FAIL |

**The pattern across today's runs:** from 2010 to 2026, adding anything to US large caps (foreign
stocks, emerging markets, commodities, REITs, gold, small caps) or timing them lowered the
risk-adjusted return. SPY buy-and-hold had the best post-IS Sharpe (0.76-0.84) of every strategy
and benchmark in alloc.py, vrp.py and parity.py. That is a fact about one exceptional decade for US
large caps, not proof it will continue. But no rule here has beaten it on the evidence.

### 2026-11-23 (fifth run): the volatility risk premium (short VIX futures, `vrp.py`). FAIL

The premium for selling crash insurance has the strongest economic reason to persist of anything
tested so far. Pre-registered in `vrp.py`: hold SVXY only when spot VIX is below 3-month VIX
(contango; Simon & Campasano 2014) by a factor k (0.90/0.95/1.00), or the same plus SPY above its
200-day. IS 2011-10 to 2017 (SVXY at -1x), OOS 2018-2021 (with 2018-02-05, when SVXY lost 83% in one
session), HOLDOUT 2022+. Results after IS at 20 bps (`results/vrp.json`):

| rule | chosen | IS Sharpe | OOS Sharpe (SPY) | HOLDOUT Sharpe (SPY) | post-IS CAGR (SPY) | max DD | worst day | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| contango | k 0.90 | 1.34 | -0.32 (0.83) | -0.48 (0.36) | -7.4% (12.9%) | -58% | -12.8% | FAIL |
| contango + trend | | 0.89 | -0.06 (0.83) | -0.25 (0.36) | -7.3% (12.9%) | -68% | -32.0% | FAIL |

As a 20% sleeve next to 80% SPY, both lowered the Sharpe (0.43 vs SPY's 0.59). Checked it isn't
a bug: before costs the k 0.90 rule was a 64%-a-year, Sharpe-1.4 strategy in 2011-2017 and about
zero afterwards (gross Sharpe -0.07 OOS, -0.19 HOLDOUT; about 28 switches a year). Plain SVXY
lost 41% a year in 2018-2021 (max DD -95%) and the filter, which did dodge the February 2018
crash, still lost money after it. This is the cleanest example in the lab of a backtest that
looked superb in sample (Sharpe 1.34, the best IS number of any rule here) and failed afterwards.
That's exactly why the gates exist.

### 2026-11-23 (fourth run): full gates for the 5-minute engine, and what trading costs allow

`lab.py` now judges 5-minute rules like the other engines: IS / OOS / HOLDOUT 50/25/25, PASS
needs IS t >= 2, positive OOS and HOLDOUT, t >= 3 after IS, and beating random side flips of its
own trades (Bonferroni). The old loose rule survives only as a "watch" label, never in the live
signal. On 4 years of SPY/QQQ/IWM (Tiingo) at 3 bp **nothing passes; the best t after IS is 0.52**.

`lab.py costs` reruns at 0 to 5 bp round trip. Average gross profit per trade after IS (= the
break-even cost) for each strategy's chosen variant:

| strategy | gross bp/trade | t after IS at 0 / 1 / 3 bp |
| --- | --- | --- |
| stocks in play (3 ETFs only) | 3.9 | 0.8 / 0.6 / 0.3 |
| 15:30 reversal (`rod` rev) | 3.0 | 2.4 / 1.8 / 0.5 |
| lunch (long only, so mostly market drift) | 2.5 | 1.0 / 0.6 / -0.2 |
| gap fade | 2.5 | 0.8 / -0.1 / -0.6 |
| 5-min ORB | 2.3 | 0.6 / 0.4 / -0.2 |
| noise area + pullback | 2.1 | 0.8 / 0.4 / -0.4 |
| noise area | 1.3 | 0.4 / -0.1 / -0.9 |
| first half hour -> last, VWAP trend, VWAP reclaim | <= 0 | negative at any cost |

Even at a realistic 1 bp for these ETFs, no rule gets near t 3; the closest is the 15:30
reversal (t 1.8), which is pre-registered idea 4 and only forward data may judge. Bug caught in
the sweep: the first break-even column divided by trades across all symbols and understated it
up to 3x; fixed to the average gross per trade.

### 2026-11-23 (fourth run): monthly trend, momentum and volatility targeting (`alloc.py`). All FAIL

New direction: rules that hold for weeks to months, the family with the best published record after
publication. Pre-registered in `alloc.py`'s docstring before the first run: six rules, small grids,
variant picked on IS Sharpe only, dividend-adjusted prices, T-bill cash, trades one day after the
signal, 10 and 20 bps per turnover. PASS needs a higher Sharpe than the benchmark in OOS and HOLDOUT,
a bootstrap p < 0.05/6 and a time-shift placebo p < 0.05 (the same positions slid in time). Results
after IS, at 20 bps (`results/alloc.json`):

| rule | source | chosen | Sharpe (bench) | CAGR (bench) | max DD (bench) | boot p | placebo p | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sma (SPY) | Faber 2007 | 12 months | 0.66 (0.84) | 9.0% (13.9%) | -18.7% (-23.8%) | 0.89 | 0.82 | FAIL |
| absmom (SPY) | Antonacci 2014 | 9 months | 0.47 (0.84) | 7.0% (13.9%) | -27.7% (-23.8%) | 0.99 | 1.00 | FAIL |
| volman (SPY) | Moreira & Muir 2017 | cap 2.0 | 0.66 (0.84) | 9.1% (13.9%) | -20.1% (-23.8%) | 0.87 | 0.37 | FAIL |
| gtaa (5 ETFs) | Faber 2007 | 12 months | 0.40 (0.70) | 4.4% (8.7%) | -10.7% (-18.8%) | 0.89 | 0.52 | FAIL |
| gem | Antonacci 2014 | 6 months | 0.07 (0.70) | 2.1% (8.7%) | -31.0% (-18.8%) | 1.00 | 1.00 | FAIL |
| topk (9 ETFs) | cross-asset momentum | top 4 | 0.55 (0.70) | 7.1% (8.7%) | -17.7% (-18.8%) | 0.73 | 0.22 | FAIL |

Benchmarks: SPY buy-and-hold for SPY rules (2010-2026); 60/40 SPY/IEF for the ETF rules (2015-2026).

Reading it. Every timing rule chosen on its best years (1994-2009 for SPY, with two crashes)
then lost to plain holding after 2009. Getting out after falls kept missing the sharp V-shaped
rebounds (2020, 2025). For absolute momentum and dual momentum the timing was worse than every
time-shifted copy of itself (placebo p 1.00; checked: the placebo reproduces the real Sharpe at
zero shift). GTAA did halve the drawdown (-10.7% vs -18.8%) but at half the return and a lower
Sharpe, so it is not a risk-reducer by the pre-registered bar (Sharpe >= 0.9x the benchmark's).

**Verdict:** the published trend and momentum timing rules did not beat buy-and-hold (or 60/40)
on risk-adjusted terms after 2009/2014, and none survived the placebo. This matches the post-2009
complaints in the trend-following literature (e.g. Hurst, Ooi & Pedersen's century study shows the
weakest decade in 2010s). Holding the index is still the bar nothing here has cleared.

**Independent agreement.** The entry below (a separate session's `trend.py`, 23 ETFs, its own code and gates) tested the same family the same day and reached the same answer: trend timing halves the worst loss but does not beat buy-and-hold on risk-adjusted terms after 2014. Two separate implementations agree.

### 2026-11-23 (third run): longer horizons, risk overlays and real trading costs

The day-trading search found nothing, so this run tests where the evidence is stronger.
New tools: `trend.py` (monthly trend and momentum, volatility targeting, drawdown control on
23 index ETFs, so no survivorship bias; cash earns the 13-week T-bill) and `costs.py` (bid-ask
spread estimates and a pre-trade cost check).

**Data fix first:** Yahoo's daily "close" leaves out dividends, which understated buy-and-hold
(SPY 1998-2014: 4.5% a year price-only vs 6.3% with dividends) and bonds even more, while cash
earned T-bills. `daily.py` now also stores the dividend-adjusted close (`a`); `trend.py` uses it.

**Trend and momentum** (monthly, next-open fills, 2 bp per unit traded; CAGR / Sharpe over
T-bills / max drawdown; `results/trend-latest.json`):

| strategy | source | IS to 2014 | OOS 2015-21 | HOLDOUT 2022+ |
| --- | --- | --- | --- | --- |
| equal-weight buy-and-hold (benchmark) | | 7.5% / 0.38 / -42% | 10.4% / 0.76 / -28% | 6.9% / 0.28 / -19% |
| SPY buy-and-hold | | 6.2% / 0.29 / -55% | 14.8% / 0.83 / -34% | 9.4% / 0.38 / -25% |
| time-series momentum, 12 m | Moskowitz, Ooi & Pedersen 2012 | 7.7% / 0.59 / -16% | 5.7% / 0.61 / -16% | 5.8% / 0.25 / -9% |
| 10-month average | Faber 2007 | 7.3% / 0.57 / -12% | 6.6% / 0.78 / -11% | 4.9% / 0.15 / -9% |
| top-5 relative strength | Jegadeesh & Titman 1993 | 8.4% / 0.46 / -35% | 8.0% / 0.52 / -23% | 11.4% / 0.52 / -16% |
| dual momentum | Antonacci 2014 | 9.3% / 0.60 / -20% | 7.4% / 0.47 / -34% | 4.3% / 0.09 / -25% |

None passes the gate (a Sharpe at least equal-weight's AND a smaller drawdown in every period,
then a random-timing placebo). The pattern is consistent and well known: trend timing cuts the
worst loss by half to two-thirds in every period, at a similar or lower Sharpe and a lower
return after 2014. It is crash insurance, not extra return.

**Risk overlays.** Volatility targeting (Moreira & Muir 2017): better before 2015, neutral to
slightly worse after. Drawdown control (cut exposure while X% below the peak): the first
setting tried (10%, half exposure, SPY) improved both Sharpe and drawdown in all three periods,
but a robustness grid (4 thresholds x 2 cuts x 7 assets = 56 variants) found that only 3 of 56
did, about what luck gives. What holds almost everywhere: the worst loss shrinks by 10-50
points, and the Sharpe usually falls. No free improvement.

**Costs.** `costs.py` estimates the spread three ways, best first: a live IEX bid/ask from
Tiingo (market hours only), the Corwin & Schultz (2012) high-low estimator on 5-minute bars,
or on daily bars. Daily high-low estimates are useless for liquid names in volatile markets
(SPY: 23.5 bp vs about 0.15 bp real); on 5-minute bars they rank names sensibly (TLT 0.9,
SPY 2.7-3.9, TSLA 7.9, NVDA 8.7, SMCI 11.9 bp) but still overstate the most liquid ones.
`costs.py check` warns when costs exceed 10% of a plan's reward or 20% of its risk.

### 2026-11-23 (third run): the 5-minute keep rule now needs OOS t >= 3

The 5-minute engine used to keep a rule with IS Sharpe >= 0.5 and any positive out-of-sample mean.
On 60 days that let noise, orb5g and orb5 into the live signal (OOS t 0.2 to 1.5), and all three
failed on 4 years (second run below). The keep rule now also needs OOS t >= 3, the bar `daily.py`
uses (Harvey, Liu & Zhu 2016). `results/latest.json` was rewritten: **the live 5-minute signal now
holds no strategy** and `lab.py signal` says "no edge" for every name. That's the honest output until
a rule clears the bar.

### 2026-11-23 (second run): all 5-minute rules on 4 years of SPY, QQQ and IWM. Nothing survives

**Data.** Tiingo's free IEX feed (`lab.py fetch-tiingo`), Nov 2022 to Nov 2026, 1,002 sessions
per ETF (993 full). Checked before use: no holidays, no gaps, the big moves are real (2025-04-09
SPY +9.4%). Caveats: volume is IEX-only, a slice of the tape, which matters only for `sip`; prices are
unadjusted, which is harmless because none of the three split. **Data trap found and fixed:** on NYSE half days the IEX
feed keeps printing thin after-hours trades and zero-volume filler bars until 16:00. Those days
looked like full sessions whose "close" was an after-hours print. Bars from 13:00 on early-close
days are now dropped (`drop_after_early_close`, tested on all 2022-2026 half days).

**Test.** 15 strategies and their variants, 3 bps round trip, variant chosen on the first 70%
(to 2025-09-11), judged on the last 30% (290 sessions). `results/long-3etf.json`.

| strategy | source | chosen variant | IS Sharpe | OOS Sharpe | OOS bp/day | OOS t |
| --- | --- | --- | --- | --- | --- | --- |
| sip | Zarattini, Barbon & Aziz 2024 | top 5, rvol 1.5, bar stop | -0.33 | 0.78 | 2.0 | 0.85 |
| rod | Baltussen et al. 2021 | reversal, 100 bp | -0.17 | 0.40 | 0.4 | 0.44 |
| noisepb | Concretum 2026 (pullback entry) | k 1.0, wait 5 | -0.44 | -0.17 | -0.3 | -0.18 |
| noiseg | noise area, vol-gated | k 1.5, high-vol days | -0.06 | -0.29 | -0.5 | -0.31 |
| orbfail | failed ORB fade | 3 bars | 0.05 | -0.41 | -1.1 | -0.44 |
| orb5g | ORB + vol gate | high-vol days | 0.13 | -0.66 | -2.3 | -0.72 |
| gap | gap fade | 1% | -0.20 | -0.86 | -1.1 | -0.94 |
| orb | Crabel 1990 | 15 min, opposite stop | 0.05 | -0.91 | -3.2 | -0.99 |
| orb5 | Zarattini & Aziz 2023 | no stop | -0.36 | -0.97 | -3.5 | -1.06 |
| lunch | Quantpedia | | -0.21 | -1.13 | -2.5 | -1.23 |
| noise | Zarattini, Aziz & Barbon 2024 | lookback 10, k 1.5 | -0.27 | -1.52 | -2.9 | -1.65 |
| vwap | Zarattini & Aziz 2023 | 10:00 | -0.77 | -1.62 | -3.6 | -1.76 |
| imom | Gao et al. 2018 | 15:00, 25 bp | -0.59 | -1.63 | -2.8 | -1.77 |
| vwapre | practitioner | 6 bars | -1.06 | -2.96 | -3.9 | -3.23 |
| eodrev | Baltussen, Da & Soebhag 2025 | | needs a cross-section; 3 ETFs is not one | | | |

No strategy is kept. Every in-sample Sharpe is at most 0.13: none of them worked even in the period
used to tune them.

**Before costs.** Rerunning the main eight at 0 bps, the best OOS result is the 15:30 reversal
(`rod` rev, all moves): t 1.91, 1.8 bp a day, which is less than one round trip's cost.
`noisepb` (t 0.95) is the only other positive one. The ORB family and the noise area are not
just eaten by costs: they have no gross edge on 2022-2026 ETFs. Note that `rod` reversal is close
to the pre-registered idea 4, which is judged only on sessions after 2026-11-20. This
backward look is consistent with it but is not evidence for it.

**Outside replication agrees.** Paz Serpa (2026, [code and paper](https://github.com/PazSheimy/spy-intraday-momentum-oos))
reproduced the noise area's paper results on SPY in sample (Sharpe 1.34, 2015-2024), then found the
Sharpe fell to 0.39 from May 2024 to Mar 2026, below buy-and-hold, with professional 1-minute data and volatility-targeted sizing.
Our -1.65 OOS t (no vol targeting, 5-minute bars) points the same way: the published intraday
momentum edge on index ETFs has not survived publication. Concretum's own pullback overlay
([QuanTip](https://concretumgroup.com/quantip-improving-performance-with-fast-alphas-a-tactical-overlay-for-intraday-trend-trading/),
reported Sharpe 0.87 to 0.99 on 2007-2026) made our noise area less bad (OOS t -0.18 vs -1.65) but not
positive.

**Verdict.** This supersedes the SPY-only first run below, which reached the same answer on 338
days. Four years and three ETFs say the same thing as 30 years of daily bars: **no published pure
day-trading rule on index ETFs makes money after realistic costs today.** The 60-day results
earlier in this log (noise "KEEP", orb5 "KEEP") were noise from a short window. The live 5-minute
signal should not be trusted.

### 2026-11-23: the 5-minute strategies on 338 days of SPY (Tiingo, Nov 2022 to Mar 2024)

First run on the long Tiingo store (SPY only; the download was still going). 3 bps round
trip; tuned on the first 70% of days, judged on the last 30%. `results/long-spy.json`.

| strategy | source | best variant, out-of-sample | verdict |
| --- | --- | --- | --- |
| noise area | Zarattini, Aziz & Barbon 2024 | +0.3 bp/day, t 0.15 | "kept" by the lab's loose 5-min gate, but no evidence |
| noise + pullback entry | Concretum 2026 | -0.2 bp/day | fails |
| 5-min ORB | Zarattini & Aziz 2023 | -9.0 bp/day, t -1.82 | fails |
| ORB + volatility gate | | -4.9 bp/day | fails |
| classic ORB, failed ORB | Crabel; practitioner | -3.6 to -3.8 bp/day | fail |
| first half hour -> last | Gao et al. 2018 | -1.1 bp/day (15:00 entry) | fails |
| last 30 minutes | Baltussen et al. 2021 | momentum t -2.85 (all variants negative) | fails |
| VWAP trend / reclaim, lunch, gap | | all negative | fail |

Stocks in play and end-of-day reversal need several stocks to rank; with SPY alone they are
not meaningful. Reading: on SPY 2022-2024 none of the published 5-minute rules makes money
after costs; the only positive one, the noise area, is indistinguishable from zero. The
5-minute engine's own keep rule (IS Sharpe >= 0.5 and OOS mean > 0) is much looser than the
daily engine's and should get the same t >= 3 and placebo gates once QQQ and IWM are in.

### 2026-11-23: R3 on 110 fresh ETFs (pre-registered). FAILED

`r3_etfs.py` tests Connors R3 (independent code from `audit.py`: Wilder RSI(2), next-open fill,
exit RSI(2) > 70, 30-day stop) on 110 ETFs the lab never used, in five groups: US equity (17),
US industry (24), international (35), bonds (16), commodities and FX (18). The gates were written
into the script before the first run: placebo p < 0.05 in both the full history and post-2014,
t >= 2 at 5 bps in both, and beating the placebo median in 3 of 5 groups.

| set | full t | placebo p | post-2014 t | placebo median | placebo p | t at 5 bps |
| --- | --- | --- | --- | --- | --- | --- |
| 110 new ETFs (6,311 trades) | 2.59 | 0.005 | 1.08 | 0.92 | 0.385 | 0.85 |
| old 19 ETFs (reference) | 3.33 | 0.005 | 1.69 | 1.28 | 0.244 | 1.53 |
| leveraged (not in the test) | 1.88 | 0.26 | 1.15 | 1.15 | 0.50 | 1.12 |

By group, post-2014 (200 placebos each): only bonds beat random entry (t 1.14 vs median -0.60,
p 0.035), and that dies at 5 bps (t 0.79) because bond trades average 12 bp. US equity, industry,
international and commodities are all within luck.

**Verdict: FAIL** (2 of 5 gates fail). R3 had a real edge over random entry before 2015, on old
and new ETFs alike, but since 2015 it is no better than buying on random days. The stock-heavy
40-symbol result (post t 4.02) came from the 21 surviving stocks. R3 stays unproven and frozen
for the forward test; do not trade it. Caveats: Yahoo has no closed ETFs, and prices are not
dividend-adjusted.

### 2026-11-22 (fourth run): AUDIT. The earlier "passed" results were wrong

Asked to quadruple-check everything, I audited the daily engine with `audit.py`, an
independent re-implementation, and found real problems. **The conclusions of the third run
are withdrawn**; the table below replaces them.

What was wrong, and what was fixed:

1. **Wrong benchmark (the big one).** Long-only rules were tested against zero. In a rising
   market any long exposure beats zero. The right benchmark is random entries with the same
   number of trades and the same holding times. Double 7s: real post-2014 t 3.11, placebo
   median 3.09 (49% of random copies did as well). RSI(2), IBS, cumulative RSI(2), 3-day
   high/low, multiple days down: all indistinguishable from random entry. Fix: a placebo gate
   (Bonferroni across the rules tested) for every rule that is long across a close.
2. **Wrong RSI.** Connors uses Wilder's RSI; the engine used a simple-average (Cutler) RSI,
   which fires about 2.5x as often. Fixed to Wilder.
3. **Unknowable fills.** Rules that buy AT the signal close passed. Nobody knows the close in
   advance. Multi-day rules also defaulted to the close fill silently. Fix: only next-open
   fills (or calendar rules) can pass.
4. **Stop-loss inside a daily bar.** Daily bars cannot say whether the low came before or after
   a stop entry. The worst-case rule condemned these rules; the "fair path" guess I tried next
   (up days go low first) invented a huge fake edge (GSV post t +9.6 vs -6.5 with no stop).
   Fix: stop-loss rules are not judged on daily bars. On hourly bars (2023-2026), Williams'
   GSV, Crabel's stretch and Raschke's 80-20 all lose even in the best case.
5. **Undocumented 10-day time stop** on multi-day rules (default `max_days`). Harmless but
   now stated; the pure Connors R3 exit gives t 3.58 instead of 4.02.
6. **Win rate** for multi-day rules was per day held, not per trade. Fixed.

What the audit confirmed: the data is clean (every big jump is a real event, no duplicate or
unsorted dates, one 6-day gap = 9/11), and the engine matches the independent code exactly
(Double 7s: 9,528 trades, t 3.089 in both; RSI(2): 19,955 trades, t 2.979 in both).

**Result after the fixes:** exactly one rule clears every gate, Connors' **R3** (RSI(2) down
3 days from below 60 to under 10, above the 200-day; out when RSI(2) > 70; next-open fill):
3,382 trades, IS t 4.24, OOS t 3.07, holdout t 2.60, post t 4.02, placebo p 0.007 over 1,000
draws, t 3.56 at 10 bps and 2.98 at 20 bps, positive in 27 of 31 years (2008: -194 bp a
trade). **But on the 19 ETFs alone it fails: t 1.53, placebo p 0.31.** ETFs cannot go
bankrupt; our 40 stocks are today's survivors. Buying deep dips looks brilliant in stocks
known to have recovered from every dip. So R3 is **not proven**: it needs a survivorship-free
stock universe, which free data does not have.

**Honest verdict:** after quadruple-checking, no rule in this lab has a proven edge. No pure
day trade works after costs; the dip-buying family is mostly market exposure; R3 is the one
open question.

### 2026-11-22 (third run): the big sweep, 30 years of daily bars and 3 years of hourly

Three research agents searched papers, practitioner books and quant blogs and came back with
about 80 rules. Every one that can be coded from the data we have is now in the lab:
`daily.py` (daily bars from 1996, 40 symbols, 158 variants), `hourly.py` (hourly bars
2023-12 to 2026-11, 49 symbols, 34 variants) and `lab.py` (5-minute bars, 60 days, 14
strategies). The gates were fixed before looking: variant chosen on IS only (daily: to
2014; hourly: first half), then OOS (2015-2021 / next quarter) and an untouched HOLDOUT
(2022 onward / last quarter) must both be positive, and the t-stat on everything after IS
must reach 3 (Harvey, Liu & Zhu 2016). The deflated Sharpe ratio (Bailey & Lopez de Prado
2014) is reported too; with 158 widely spread variants its bar is about a 2.3 annual
Sharpe after 2015, and nothing reaches it.

**What passed (daily, 1996-2026, 2 bps per trade, multi-day holds):**

| rule | source | trades | avg bp | IS t | OOS t | HOLDOUT t | post t | holdout Sharpe |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| IBS < 0.1, out on the first up close | Pagonidis 2013 | 25,964 | 37.8 | 5.89 | 3.66 | 1.22 | 3.58 | 0.55 |
| Cumulative RSI(2) < 35, out RSI(2) > 65 | Connors & Alvarez 2009 | 14,477 | 38.7 | 4.64 | 3.38 | 1.06 | 3.18 | 0.48 |
| Double 7s (lowest close of 7, above the 200-day) | Connors & Alvarez | 9,528 | 80.2 | 3.56 | 3.15 | 1.10 | 3.11 | 0.50 |
| RSI(2) < 10 above the 200-day, out > 70 (next-open fill) | Connors 2008 | 19,955 | 27.7 | 5.03 | 3.00 | 1.03 | 2.98 | 0.47 (misses by 0.02) |

**Fill realism, the most useful finding of the day.** Those results assume buying at the
exact close, which nobody can know in advance. Re-run buying at the NEXT OPEN instead:
RSI(2) (post t 2.98 to 3.60 across variants) and Double 7s (3.09) barely change, so their
edge is real and capturable. IBS collapses (post t 3.58 to 2.31, holdout Sharpe 0.55 to
0.15): its edge is the overnight bounce right after the close, which you only get with a
market-on-close order.

**The honest comparison.** Buy-and-hold of the same 40 names had a Sharpe of 0.86 in
2015-2021 and 0.48 in 2022-2026. The mean-reversion rules beat it in 2015-2021 (1.1 to 1.5)
but only match it in the holdout (about 0.5), while invested a fraction of the time. The
classic edge is fading, exactly as McLean & Pontiff (2016) predict for published anomalies.

**What failed (daily):** every pure open-to-close day trade. Larry Williams' volatility
breakout (post t -6.6), greatest swing value (-52), Crabel's stretch (-11), NR4/NR7 (1.1),
Oops! (-3.3), smash day (-2.9), Turtle Soup (-4.8), 80-20 (-1.6), gap fade and gap fill,
index daily reversal (Baltussen et al. 2019), Turnaround Tuesday (1.7), day of week,
turn of month, pre-holiday, option-expiration week, month-end, overnight with a trend
filter (2.1). The open-to-close leg of buy-and-hold itself earns nothing (post t 0.24);
nearly all of the return since 1996 came overnight.

**What failed (hourly, 2023-2026):** first half hour predicts last half hour (Gao et al.
2018; OOS t -3.1 for the momentum version), last-30-minute momentum and reversal
(Baltussen et al. 2021), first-hour momentum and reversal, the 60-minute ORB, lunch
(Quantpedia), every single hour as a seasonal, and gap-plus-first-hour. All negative or
insignificant after 2 bps.

**5-minute (60 days):** a volatility gate (trade orb5 only after a high-range day) gave
the best IS Sharpe yet (4.46) and kept a positive OOS, so it is in the live 5-minute signal
with the noise area and plain orb5. End-of-day reversal (Baltussen, Da & Soebhag 2025),
VWAP reclaim, lunch and the long-only noise area all failed. Nothing on 60 days has a t
near significance.

**Follow-ups the same day.** A VIX gate (trade RSI(2) and Double 7s only when VIX is above
its 1-year median) raises the average trade (RSI(2): 42 vs 28 bp) and the IS t, but the
2022+ holdout gets worse (Sharpe 0.18 vs 0.47), so it is not adopted. The three passers and
five near misses (post t >= 2.5) are frozen in `results/frozen.json` as of 2026-11-22:
`daily.py forward` scores them only on sessions after that date, the one test nobody can
have tuned. `daily.py signal` now lists each multi-day rule's open positions and fresh
entries. On 2026-11-20 most of them were open and underwater after a ~10% fall in SPY:
the known tail of buying dips with no stop.

**Verdict so far.** No pure day trade (in and out the same session) survives honest
testing on decades of data. The only strategies that pass are 1 to 5 day "buy the
oversold dip in an uptrend" holds, and their edge has shrunk to about buy-and-hold's
Sharpe since 2022. The gold, if there is any, is in risk reduction (lower time in market,
smaller drawdowns), not in beating the market.

### 2026-11-22 (second run): stocks in play, wider universe

Tested idea 1 from the queue: Zarattini, Barbon & Aziz (2024), [A Profitable
Day Trading Strategy for the U.S. Equity Market](https://www.alexandria.unisg.ch/server/api/core/bitstreams/3c2989c4-688d-4d78-8a71-f02690990d51/content).
Their rules: relative volume = first-5-minute volume / its 14-day average,
at least 100%, top 20 by that each day; enter on a break of the first
5-minute bar's high (green bar) or low (red bar); stop at 10% of the 14-day
ATR; out at the close. They report a 2.81 Sharpe on 7,000+ stocks 2016 to
2023; a trader running it live warns that slippage at the open is large.

Changes: universe widened from 20 to 40 symbols (added 20 high-volume,
higher-beta names: PLTR, COIN, MSTR, SMCI, ...), stop-entry orders added to
the simulator, and a bug fixed: a stop hit in the same bar as the entry now
fills at the stop, not at that bar's open (which came before the entry).

60 sessions (2026-08-28 to 2026-11-20), 40 symbols, 3 bps round trip.

| strategy | chosen variant | IS Sharpe | OOS Sharpe | OOS bp/day | OOS t | verdict |
| --- | --- | --- | --- | --- | --- | --- |
| noise | lookback 10, k 1.5 | 0.96 | 5.41 | 17.4 | 1.45 | KEEP (weight 0.40) |
| orb5 | no stop | 1.43 | 0.58 | 3.2 | 0.16 | KEEP (weight 0.60) |
| sip | top 5, rvol 1.0, bar stop | -0.73 | -1.28 | -12.8 | -0.34 | drop |
| orb | 30-min range, opposite stop | -0.76 | 2.76 | 17.6 | 0.74 | drop |
| vwap | 10:30 | -2.94 | 2.78 | 13.9 | 0.74 | drop |
| gap | fade, 0.5% | 2.00 | -0.15 | -0.3 | -0.04 | drop |
| imom | 15:30, 25 bp | -2.72 | -13.35 | -12.8 | -3.57 | drop |

Reading it: stocks in play failed in both halves with every variant. The
10%-of-ATR stop wins only 8 to 12% of trades; at 3 bps of cost per trade a
stop that tight is mostly paying the spread. With 40 names the "top 5 by
relative volume" is not the same animal as the paper's top 20 of 7,000, so
this is "not shown on our data", not "refuted". It goes back in the queue
for when the store is bigger.

The wider universe changed the picture: noise now survives, orb5 barely
does (OOS t 0.16), and the gap fade that looked fine before now fails out
of sample. That instability is itself the finding: with 60 sessions, which
rules "work" depends on which stocks you test. Nothing has an OOS t near
2.5. The one strong number is a negative one: imom lost money with
t = -3.57 out of sample.

### 2026-11-22: first run

60 sessions (2026-08-28 to 2026-11-20), 20 symbols, 3 bps round trip.
IS to 2026-10-27, OOS from 2026-10-28.

| strategy | chosen variant | IS Sharpe | OOS Sharpe | OOS bp/day | OOS t | verdict |
| --- | --- | --- | --- | --- | --- | --- |
| orb5 | no stop, hold to close | 1.43 | 4.36 | 29.1 | 1.17 | KEEP |
| noise | lookback 14, k 1.0 | 0.08 | 4.00 | 21.5 | 1.07 | drop (IS too weak) |
| orb | 30-min range, opposite stop | -2.42 | 4.43 | 32.4 | 1.18 | drop |
| gap | fade, 0.5% | -1.80 | 5.37 | 12.8 | 1.44 | drop |
| vwap | 10:00 | -4.45 | 2.39 | 9.0 | 0.64 | drop |
| imom | 15:30, 25 bp min | -4.53 | -6.35 | -9.7 | -1.70 | drop |

Reading it: almost every trend rule lost in September and October and made
money in November. That is a regime change (a choppy market turned into a
trending one), not proof any rule is good. orb5 was the only one positive in
both halves, so it is the only one in the signal for now. No OOS t is near
2.5, so none of this is statistically strong yet. Intraday momentum (imom)
lost in both halves on this window, unlike the 1993 to 2013 paper.

Next: idea 1 (stocks in play) and idea 5 (volatility gate), since both are
claimed to fix exactly this regime problem.

### 2026-11-24: the bot makes the trade calls (paper), rules fixed before its first trade

The owner asked that the trade calls be the bot's. `bot.py` takes trades by fixed rules and fills
them on paper from real prices, with a running ledger in `paper/bot/ledger.json`. Nothing reaches an
account. The rules are in the bot.py docstring and are written here before any result:
- **stocks:**
  - the most-traded opening-range breakouts still above the range, long only
  - 2 a run, 5 a day, $50 risk a day, no entries after 15:00
  - stop at the range midpoint, 2R target, flat by 15:55, the paper.py cost filter
- **crypto/forex:**
  - only setups new since the previous hourly run
  - long on a 20-hour high breakout or reclaim, short on a 20-hour low break; RSI setups not traded,
    and a name with both directions skipped
  - 2 an hour, 6 open
  - 1.5 × ATR(14 h) stop, 2R target, 24-hour time exit, 2 bp (FX) or 10 bp (crypto) cost

One rule was added during the first live run, before any fill: AAPL and AVGO had broken out at 9:50
and fallen back under the range high by 10:39, so a breakout now counts only while the price is still
above the range. Those two entries were removed unfilled.

The bot's record is reported separately from the pre-registered trial and doesn't change its bar.
Expectation from the lab: no edge after costs.

### 2026-11-24: the bots' exact rules, backtested (bot_backtest.py), and four upgrades

The bots went live this morning before their exact rules had been tested, so `bot_backtest.py` replays
them. The variants were written down before any run. Data comes from `bot_data.py`:
- **Stocks:** 1,444 liquid US stocks, the whole market at the live scanner's floor, over 59 sessions
  (2026-09-01 to 2026-11-23, Yahoo's 60-day limit for 5-minute bars).
- **Crypto, forex and metals:** 28 names, 2 years of hourly bars.

**Crypto / forex**, costs as in bot.py (spreads plus swap):

| rule | trades | net | a trade | daily t |
| --- | --- | --- | --- | --- |
| live rule, as it was | 11,951 | −$15,155 | −$1.27 | −8.1 |
| + group cap (now live) | 5,762 | −$7,077 | −$1.23 | −6.8 |
| + Bitcoin trend | 5,360 | −$6,688 | −$1.25 | −6.6 |
| + no weekends / rollover | 5,255 | −$5,250 | −$1.00 | −5.2 |

- Before costs the live rule made about $0 (+$850 over 12,000 trades).
- With random directions at the same times and names, the live rule beat only 12% of 100 placebo draws.
- The hourly stop is tight, so $10 of risk needs about $5,000 of forex exposure, and costs then take
  about 10% of the risk on every trade.
- Metals are the only group near zero (daily t −0.3 to +0.3).

**Stocks**, the opening-range breakout:

| rule | trades | net | a trade | daily t |
| --- | --- | --- | --- | --- |
| live rule | 295 | −$328 | −$1.11 | −3.05 |
| SPY above its 200-day | 280 | −$281 | −$1.00 | −2.71 |
| 10:17 decision only | 118 | −$153 | −$1.29 | −1.92 |
| fresh breakouts only | 295 | −$299 | −$1.01 | −2.51 |

- The live rule lost before costs too (−$167).
- Out of 295 trades, 81 hit the stop and only 13 reached the 2R target.
- Random names above their range midpoint, at the same times, lost a median $259. The live rule beat
  only 30% of them.

**Reading:** neither bot has an edge. Both lose about $1 a trade after costs, and the challengers don't
change that. 59 sessions of stocks is short, but it's long enough to show a loser.

**What stays and what changes:**
- The bots keep trading on paper, since the owner wants the record. That costs nothing and gives a
  forward check of this result.
- Live money stays off, as the plan already says.
- The group cap and the Exness cost table are now live. They're risk and accounting fixes, not edges.
- Challengers run forward. One is promoted only on the forward rule written in bot_backtest.py.

### 2026-11-24: "survivors", the lab's surviving rules as one daily strategy (`survivors.py`). FAIL

The owner asked for smart strategies for daily trading over the long term. Same-day trades all failed, so
this combines the only rules that held up, decided daily and held for a few days:
- RSI(2) under 10, or the lowest close of 7 days, on 21 index and sector ETFs above their 200-day average
- out at RSI(2) above 70, the highest close of 7, or 10 days held
- 5 slots of 20%, bought at the next open
- plus 20% in SPY on the night before each scheduled FOMC announcement

The rules, universe, costs and pass bar were fixed in the docstring before the first run. Costs are 3 bp a
round trip, and dividends are included.

| period | rule per year | Sharpe | max drop | t | SPY per year | Sharpe | max drop |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2000-2014 | 6.6% | 0.47 | 18% | 1.83 | 4.2% | 0.21 | 55% |
| 2015-2026 (judged) | 7.8% | 0.54 | 16% | 1.87 | 13.0% | 0.66 | 34% |

- After 2015 there were 1,510 trades, 68% of them winners, at 26.6 bp a trade, with 2.4 of the 5 slots
  used on average.
- At 3x cost it still makes 6.1% a year.
- Placebo (random ETFs and days with the same holding times): the rule beats only 60% of 200 draws.

**Verdict: FAIL** on the pre-registered bar, which needed t ≥ 2 and beating 95% of placebos. Most of the
return is the stock market's own return, earned while about half invested, not timing skill. It does cut
the deepest drop to about a third of SPY's. After 2015 it earns less than buying SPY and holding.

Not changed after the result. Kept for a forward paper record only if the owner wants it, and labelled as
having failed its own bar.

### 2026-11-24: the day-trading brain, every first-candle feature on the whole market (`daybrain/brain.py`). FAIL

Pre-registered in 19406b9 before any run. At 9:35 New York, after the first 5-minute candle, 12 features
were measured for every liquid US stock, about 1,490 a day over 44 usable days (2026-09-23 to 11-23):
- the candle itself: colour and size, upper wick, lower wick, body, close location, range against normal
- the gap
- relative volume of the first candle (stocks in play)
- the previous day's return, close location and last 30 minutes
- the candle's direction times its relative volume

Each was tested as a cross-sectional rank correlation with the 9:35 to 15:55 return. It had to clear
Bonferroni |t| ≥ 2.87 on the first 22 days and keep its sign with t ≥ 2 on the last 22.

**Each feature alone:** none passes. None even reaches the discovery bar; the largest |t| there is 1.55.
Several flip sign between the two halves:
- previous day: −1.19, then +2.43
- range: −0.80, then +3.17
- upper wick: +1.19, then −2.59

**The brain**, a ridge regression on all 12 fitted on the first half, top 10% minus bottom 10% at 10 bp a
side:

| test | long-short a day | t |
| --- | --- | --- |
| discovery | +23.6 bp | 0.74 |
| validation | −100.7 bp | −3.22 |
| long top 10% vs the market, validation | −39.7 bp | −2.19 |
| 4-year check (40 names, 977 days, top 4 minus bottom 4) | −21.3 bp | −3.55 |

On the 4-year store the strongest single feature is the previous day's return, a weak short-term reversal
(IC −0.019, t −2.16, below the bar). The candle's colour reaches only t +1.38, and the wicks t −1.40 and
+0.27.

**Reading:** the first 5-minute candle, its wicks, the gap and relative volume tell nothing reliable about
the rest of the day across the US market. What they seem to say in one month flips the next. That agrees
with the candle-pattern literature (Marshall, Young & Rose 2006) and with the lab's earlier ORB and
stocks-in-play results. **Verdict: FAIL**, not changed after the result.

### 2026-11-24: stock bot limits raised at the owner's request (rule change, not from results)

The owner asked for a limit of 20. `bot.py` STOCK is now 4 a run, 20 a day and $200 of risk a day, up
from 2, 5 and $50. The time window, stops, targets and the $10 risk a trade are unchanged. This scales the
same rule up. The backtest (bot_backtest.py, 2026-11-24) puts the rule at about −$1.11 a trade after costs,
so more trades are expected to lose more on paper, not less. The bot's record is reported from this date
with the new limits noted.

Later the same day the owner raised the limit again, to 50 trades a day: 10 a run and $500 of risk a day. The rule itself is unchanged.

### 2026-11-24: the indices bot (`indexbot.py`), dip in an uptrend on 10 index CFDs. FAIL, runs on paper

The owner asked for an indices bot. It uses the one family that held up on index funds, buying short dips
inside an uptrend (Connors RSI(2), Double 7s; survivors.py). It trades the Exness index CFDs, priced from the
fund tracking each:

| CFD | fund |
| --- | --- |
| US500 | SPY |
| USTEC | QQQ |
| US30 | DIA |
| US2000 | IWM |
| DE30 | EWG |
| UK100 | EWU |
| JP225 | EWJ |
| STOXX50 | FEZ |
| HK50 | EWH |
| AUS200 | EWA |

Daily data comes from Tiingo, not Yahoo, dividend-adjusted. Costs are CFD costs: 3 bp spread plus 2 bp of
swap for each night held. Pre-registered in its own commit before any run.

| period | bot per year | Sharpe | max drop | t | US500 hold per year | Sharpe | max drop |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2000-2014 | 3.4% | 0.39 | 16% | 1.51 | 4.2% | 0.30 | 55% |
| 2015-2026 | 1.6% | 0.23 | 21% | 0.79 | 13.0% | 0.78 | 34% |

- After 2015: 1,059 trades, 68% of them winners, at 24.3 bp a trade before swap.
- At 2x cost it loses 0.6% a year, and at 3x it loses 2.8% a year.
- It beats only 56% of 200 placebos.

**Verdict: FAIL.** CFD overnight financing takes most of the dip edge, and outside the US the edge is weaker
than on US funds (survivors.py's 21 ETFs made 7.8% a year after 2015). Not tuned after the result. It runs
on paper from 2026-11-24 at the owner's request, with a $10,000 pretend account, after each close.

### 2026-11-24 (daily run): bots, trial, oil, engines

**Bots, paper, first day:**
- **Stocks:** 19 trades, net −$9.38. 7 won, 12 lost, and none reached its stop or target (all were out
  at 15:55). That's in line with the backtest's −$1.11 a trade.
- **Crypto/forex:** 1 closed (the LTC stop, −$10.86) and 4 open (short silver, BNB, USDCAD; long USDJPY).
- **Fresh-breakout challenger:** 3 trades, −$4.16.

**Paper trial:** 2 days, 4 shadow trades, net +$14.46. Today's ticket was a USTEC buy after QQQ fell
2.45% by 15:30; it made +$4.56. Still IN PROGRESS: it needs 20+ days and 30+ trades, about mid-January.
- **Scanner track** (not part of the trial's bar): 6 trades, −$23.74. Today AFRM and BAC hit their stops
  and SAP made +$4.77.

**Oil:**
- The DCA ladder holds 1 layer on each of USOIL and UKOIL.
- The MA-cross candidate says BUY USOIL at the next open, and UKOIL is flat.
- 0 oil candidates have passed every gate.

**Engines rerun:** lab, hourly, daily, trend, the daily forward test, the long-store 5-minute rules
and the costs table.
- Nothing new passes. The daily engine's chosen s_r3 still shows its old in-sample PASS label, but it
  failed on 110 fresh ETFs (2026-11-23).
- Long store: end-of-day reversal −3.3 bp a trade (t −3.19); gaps about zero.
- Trend positions for November:
  - tsmom: 4% in each of 16 funds, 30% cash
  - sma: 15 funds, 35% cash
  - xsmom: DBC, XLE and XLK
  - dual: EFA

No new strategy was searched tonight. Today's own work already covered it (bot backtests, survivors,
daybrain, indexbot, all FAIL), and the plan is to stop adding rules and let the forward records run.
The Polygon 2-year download for daybrain resumed after a container restart (61 of 500 names).


## 2026-11-25: crypto/forex bot group cap raised to 10 per group (owner's request)

- The owner asked for 10 trades allowed in each group. `GROUP_CAP` in `bot.py` went from crypto 1,
  metals 1, forex 2 to 10, 10 and 10, and the overall `max_open` from 6 to 30 so it doesn't bind first.
- Everything else is unchanged: $10 risk a trade, up to 2 new trades an hour, stop 1.5 × ATR, target 2R,
  out after 24 hours.
- Metals have only 2 symbols (gold and silver), so that group can't go past 2. The most at risk at once
  is about $220 (10 + 2 + 10 trades).
- This is a risk setting, not an edge. The 2-year backtest lost money with the old cap (−$1.23 a trade,
  daily t −6.8) and without it (−$1.27, t −8.1).
- Rerun with the new caps (2026-11-25): 11,951 trades, net −$15,155, −$1.27 a trade, win 36%, daily t
  −8.14, −$31,160 at 2× costs. That's the same as having no cap at all: 10 a group never binds. By group,
  crypto −$7,799 (t −5.07), forex −$7,237 (t −7.21), metals −$119 (t −0.28).

## 2026-11-25: the oil brain (`oilbrain/`), fundamentals plus price. FAIL

The owner asked to upgrade the oil brain. Every earlier oil test (293 hand-built rules, 26,288 universe
rules) used oil's own price. `oilbrain/` adds the data with the strongest economic case, each dated by
when it became public:
- **EIA weekly stocks:** US crude (1982+), Cushing (2004+) and gasoline (1990+), as a surprise against
  the same week of the previous 5 years. Counted as known from the Thursday close after the week ends.
- **CFTC Commitments of Traders** (WTI, 2006+): managed money net long as a 3-year percentile, and its
  4-week change. Counted as known from the Monday close after the Tuesday report date.
- **The futures curve:** contract 1 over contract 2 (EIA, ends 2024-04).
- **Price and macro:** USO momentum (21, 63 and 252 days), 20-day volatility, the dollar (UUP), and
  energy stocks against oil (XLE minus USO).

Pre-registered in `oilbrain/brain.py` and committed before the run (d97d888):
- Each feature is a trailing z-score. Long or short USO by its sign, with the direction taken from
  2006-2014 only.
- Two horizons: the next session, and the next 5 sessions without overlap.
- Costs: 5 bp per side change and 1 bp a night.
- Pass needs all of these: t >= 3 after 2014; positive in 2015-2021 and in 2022 on; beating 99.8% of
  1,000 shifted placebos; positive on Brent (BNO).
- One ridge "brain" combines all 12 features, fitted on 2006-2014 only.

| best after 2014 | 1 session | 5 sessions |
| --- | --- | --- |
| backwardation (long when contract 1 is above contract 2) | +6.0 bp, t 1.49, placebo 84% | +26.5 bp, t 1.35, placebo 83% |
| COT percentile (follow the crowd) | +1.8 bp, t 0.39 | +11.9 bp, t 0.51 |
| crude inventory surprise | −5.2 bp, t −1.14 | −2.9 bp, t −0.13 |
| the combined brain | −1.1 bp, t −0.25 | −1.3 bp, t −0.06 |

- **Verdict: FAIL.** Nothing reaches t 1.5 after 2014. The inventory surprise worked to 2014 and then
  flipped sign in 2022 on.
- **The brain overfits.** Its 2006-2014 fit had the highest correlation (0.25 at 5 days) and then went
  to zero on the new years. That's the same lesson as the day-trading brain.
- **Backwardation is again the only idea positive in every period.** That matches the seventh run and
  the roll-yield studies, but it is far from the bar. Its holdout is thin: the EIA curve ends in
  2024-04, so the rule is flat after that.
- The two simulated oil tracks (the DCA ladder and the frozen MA 40/50 cross) are unchanged.
- `oilbrain/brain.py today` shows each reading. It is information only, not a signal.

## 2026-11-25: TradingView "DTC - 1.3.6" stand-in and 60 indicators on Bitcoin (`dtc_btc.py`). FAIL

The owner asked to use the DTC 1.3.6 indicator on Bitcoin and to test other indicators. DTC is invite-only on
TradingView with hidden code, so it can't be run here. Its page describes a trend system on a 6-layer EMA
structure from 30 to 60, and the lab tested the plainest version of that:
- **Rule:** long when the EMAs 30, 36, 42, 48, 54 and 60 are stacked upward and the close is above EMA 30.
- **Variants:** long/flat, and a long/short variant that also goes short when the ribbon is stacked downward.
- **The other indicators:** catalog.py's 60 named strategies, run on Bitcoin alone.

Pre-registered in a271b53:
- next-bar-open fills;
- Exness BTCUSD costs: 6 bp a round trip, plus 3 bp swap per night held;
- the statistic is alpha over holding Bitcoin, with the in-sample period before 2020 and the judged period from 2020;
- PASS needs t >= 3.5.

| rule | judged t (2020 on) | $500 from 2020 | without swap | max drawdown |
| --- | --- | --- | --- | --- |
| DTC-style ribbon, long/flat (daily) | +1.01 | $2,918 | $3,899 | −44% |
| DTC-style ribbon, long/short (daily) | +0.54 | $858 | $1,405 | −61% |
| best of the 60 (TTM squeeze) | +2.26 | $1,536 | $1,713 | −34% |
| best $ of the 60 (Vortex 14) | +1.72 | $6,482 | $9,768 | −63% |
| Bitcoin held | | $4,378 | | −77% |

The 4-hour and 1-hour DTC-style ribbon over the last 2 years: judged t from −1.47 to +0.05. On 1-hour bars,
$500 became $305 to $344.

- **0 of 64 pass.** The DTC-style ribbon ranks in the middle. Long/flat cut the worst drawdown from 77% to 44%,
  but it made less than holding.
- **The swap is the hidden cost of a Bitcoin CFD.** At 3 bp a night, it eats about 11% a year while a trend rule
  is in. With Exness costs, the 200-day SMA rule's judged t drops to −0.18, from 3.35 in the catalog, which had
  no swap and judged from 2016. Holding real coins avoids the swap; the paper bot `btc_trend.py` models
  spot coins.
- Mean reversion (CCI, Bollinger, z-score, DPO, stochastic) loses on Bitcoin, as it does everywhere else.

## 2026-11-25: Can we spot a fake breakout in advance? (`fakeout.py`)

The test was pre-registered and committed before it ran (2dc1664). It uses the live stocks-in-play setups,
4 years of 5-minute bars on 40 names, and 3,824 trades. It was chosen on data before 2025 and judged from 2025.

- **Fakes are normal.** About half of all breakouts hit their stop: 51% in-sample, 46% judged. The strategy
  still made +9 bp a trade from 2025 (t 1.96, not proven), because the winners pay for the fakes.
- **0 of 7 warning signs pass.** The signs tested: market against, tiny first candle, big gap, weak close,
  extreme relative volume, instant fill and late fill.
- Two signs point the opposite way, though not significantly. Big gaps and extreme relative volume had fewer
  fakes, not more.
- A tiny first candle does predict stop-outs: 69–72% faked, against about 48%. Those losses are small, though
  (the stop is small), so skipping them barely changes the money.
- **Waiting for a candle to close past the level cuts fakes from 46% to 33%.** It doesn't raise profit:
  +0.4 bp a setup, t 0.22. The fakes it avoids are traded for later entries.
- Verdict: no rule found that filters fakes for a profit. The stop-loss is the fake-out defence. The live book
  is unchanged.

## 2026-11-25: Pairs trading on 60 ETFs, GGR distance method (`pairs.py`). FAIL

Pre-registered in ebee980 before the run. The rule:
- each month, pick the 20 ETF pairs that tracked each other most closely over the past year;
- for 6 months, when a pair drifts more than 2 standard deviations apart, buy the cheap one and short the dear
  one at the next close (the one-day wait);
- close when the pair meets again;
- costs 5 bp per leg per trade.

| | in-sample 2000–2014 | judged 2015–2026 | $500 since 2015 |
|---|---|---|---|
| pairs, 5 bp | +0.05%/mo, t 1.06 | −0.03%/mo, t −0.76 | $476 |
| pairs, 10 bp | +0.01%/mo, t 0.22 | −0.07%/mo, t −1.71 | $449 |
| random pairs (control) | −0.10%/mo, t −0.72 | +0.05%/mo, t +0.35 | $525 |
| SPY held | | | $2,123 |

- The chosen pairs do no better than random pairs. Any small edge before 2015 is gone after costs. This matches
  the papers that followed GGR: Do & Faff (2010) report the profits shrinking since the 1990s.

### 2026-11-25 (daily run): bots, trial, oil, engines

**Bot (paper):**
- **Stocks today:** 50 trades (the new daily limit), net +$295.34, 40 won. 10 hit the target, 3 hit the
  stop, and 37 were out at 15:55. The best were ANT +$21.38 and GE +$20.27; the worst XOM −$8.89.
- **Stocks total:** 69 trades, +$285.96. This was one strong afternoon (the AI selloff turned up into the
  close). The 59-session backtest says about −$1.11 a trade, so one day changes nothing.
- **Crypto/forex** (caps raised to 10 a group today, at the owner's request): 21 closed, +$42.26, 43% won,
  4 open.
- **Challengers:** fresh +$293.87 on 48 trades; first +$75.48 on 10; btctrend +$12.87; noweekend +$32.80.

**Paper trial:** 3 days, 5 trades, +$16.16, all winners; the daily t is 2.24. Today's ticket was a USTEC
buy after QQQ fell 1.01% by 15:30, for +$1.70. Still IN PROGRESS: it needs 20+ days and 30+ trades.
- **Scanner track:** 9 trades, −$9.56. Today's 3 picks (ENPH, VIST, ADM) were run late at 10:17, after a
  restart, using the 09:50 bars.

**Oil:**
- No DCA ladder is open: the earlier layers closed, and neither market is 20% below its 20-day high.
- The MA-cross candidate holds USOIL (1 of 25 sessions); UKOIL is flat.
- The oil backtest: 0 of all candidates pass. Today's oil brain (fundamentals: EIA stocks, CFTC
  positioning, curve) failed too; see its entry.

**Engines rerun:** lab, hourly, daily, trend, the long-store 5-minute rules and the costs table. 0 new
passes.
- The daily forward test of the frozen dip rules: 3 sessions, all positive (s_r3 t 5.27, s_rsi2
  t 3.21). Three sessions right after a sharp fall are what dip rules are built for. They mean nothing
  until a much longer record.
- Trend positions are unchanged for November (rebalanced monthly):
  - tsmom: 16 funds at 4%, 30% cash
  - sma: 15 funds, 35% cash
  - xsmom: DBC, XLE, XLK
  - dual: EFA

**Today's research:** both FAIL; see their entries above.
- the oil brain (`oilbrain/`)
- the DTC-style EMA ribbon and 60 indicators on Bitcoin (`dtc_btc.py`)

The Polygon 2-year download for daybrain is at about 395 of 500 names. It keeps being stopped by
container restarts and is restarted each hour.

### 2026-11-26: indices bot on US indices only (`indexbot.py backtest --universe us`). Better, still FAIL

The owner chose to test the US-only version. For the 6 non-US CFDs, the 10-index bot uses US-listed
fund prices, which trade in New York hours rather than each CFD's own session. The US-only version keeps
the identical rule, sizing, costs and pass bar, on US500, USTEC, US30 and US2000. It was pre-registered in
fb79de6 before the run.

| 2015-2026 | per year | Sharpe | max drop | t | trades | win rate | bp a trade (before swap) | at 3x cost | placebo |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10 indices (rerun) | 1.6% | 0.23 | 21% | 0.78 | 1,060 | 68% | 24.1 | −2.9% a year | beats 48% |
| **US only** | **3.1%** | **0.53** | **14%** | **1.81** | 594 | 75% | 43.9 | +0.6% a year | beats 82% |
| US500 held | 12.9% | 0.78 | 34% | | | | | | |

- **The US-only version is better on every line.** It earns nearly twice as much per trade, it stays
  positive at 3x costs, and its worst drop is smaller.
- **It still fails its bar.** It needs t >= 2 and to beat 95% of placebos, and it gets t 1.81 and 82%.
- **Holding US500 still made four times as much.** The dip rule is out of the market most of the time.
- The paper bot keeps all 10 indices unless the owner chooses otherwise.

### 2026-11-26: walk-forward optimization of the US index dip rule (`indexopt.py`). FAIL

The owner asked to optimize the strategy. Pre-registered in 7c1af34:
- **The grid:** 48 settings (RSI(2) entry 5/10/15, trend 100/200 days, exit RSI 50/70, hold 5/10 days,
  sizing 5 x 20% or 4 x 25%) on US500, USTEC, US30 and US2000.
- **The method:** each year from 2015 is traded with the setting that had the best Sharpe on the years
  before it only. Only those unseen years are judged, with indexbot's bar.

| 2015-2026 | per year | Sharpe | max drop | t |
| --- | --- | --- | --- | --- |
| walk-forward (the judged result) | 3.3% | 0.54 | 20% | 1.85 |
| current rule, fixed | 3.1% | 0.53 | 14% | 1.81 |
| best single setting, chosen on the whole history (in-sample, overstates) | 3.6% | 0.64 | 15% | 2.21 |
| US500 held | 12.9% | 0.78 | 34% | 2.68 |

- **Optimizing adds almost nothing.** The walk-forward beats the fixed rule by 0.2% a year, with a bigger
  drawdown. It is 0.9% a year at 3x costs, and it beats 84% of placebos (95% needed). FAIL.
- **The rule is robust, though.** All 48 settings are positive after 2015, and every year picked nearly
  the same setting (RSI < 10, the 100-day trend, exit at RSI 70, hold 10). The dip effect is real but
  small; the settings were never the problem.
- **Even the best setting chosen with hindsight makes 3.6% a year,** against 12.9% for holding US500. The
  limit is time out of the market, not the settings.

### 2026-11-26: the indices paper bot now trades US indices only

At the owner's request, `indexbot.py today` trades only US500, USTEC, US30 and US2000 (`PAPER = US_ONLY`).
The rule, sizing and costs are unchanged. The 10-index backtest stays available as the default
`backtest`. Why: the US-only backtest was better on every line (3.1% against 1.6% a year, t 1.81 against
0.78), and the non-US CFDs were priced from US-hours fund prices. It is still a FAIL, so the paper record
is a forward check only. No position was open at the switch.

### 2026-11-26: buy low, sell high on the crypto/forex bot's markets (`fx_meanrev.py`). FAIL

The owner asked why the crypto bot doesn't buy low and sell high. The test was pre-registered in 3383f9e
and uses the bot's 2 years of 1-hour bars, its sizing ($10 risk), its group cap and Exness costs. The live
bot is unchanged.

| variant | trades | net | $ a trade | gross (before costs) | win rate | daily t | placebo beats |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RSI(14) dips, bot's exits (1.5 ATR stop, 2R) | 8,249 | −$11,408 | −$1.38 | −$567 | 36% | −6.71 | 6% |
| RSI(14) dips, target the 20-hour average | 8,272 | −$10,638 | −$1.29 | +$216 | 37% | −6.18 | 0% |
| Bollinger 2-sd dips, target the 20-hour average | 14,554 | −$18,734 | −$1.29 | +$1,794 | 43% | −9.62 | 0% |
| (the live breakout rule, for comparison) | 11,951 | −$15,155 | −$1.27 | +$850 | 36% | −8.14 | |

- **All three FAIL.** They lose in crypto, forex and metals alike, and doubling costs doubles the losses.
- **Before costs, buy low/sell high is about break-even.** At best it makes +$0.12 a trade, while the
  spread and swap cost about $1.40 a trade.
- **It loses to random coin-flip directions** (placebo 0-6%). On these markets, fading the hour's big
  move is worse than chance, not better.
- **Same reading as the breakout rule:** short-term hourly trading on these markets has no edge after
  Exness costs, whichever direction the bot takes.

### 2026-11-26: the day-trading brain on 2 years of Polygon data (481 days, ~479 stocks a day). FAIL again

The Polygon 5-minute download finished: the 500 most-traded US stocks, 2024-12 to 2026-11. `daybrain/brain.py
study --store polygon` reran the pre-registered study, unchanged, on 481 days instead of 60. That is 8 times as
many days.

- **No feature passes.** None of the 12 reaches |t| 2.87 on discovery: not the first 5-minute candle (t −1.47,
  then +0.77), not the wicks (upper −0.93 then +0.06, lower +0.14 then −0.37), not relative volume, not the gap.
  The closest is yesterday's return (t −2.50, a weak reversal), and it vanishes on validation (−0.22).
- **The combined brain fails again.** Discovery: −5.2 bp a day (t −0.62). Validation: −27.3 bp a day
  (t −2.29). The 4-year check is −18.4 bp a day (t −2.98).
- **The reading is the same as on 60 days, now with 8 times the data.** The first candle and its wicks don't
  predict the rest of the day across the US market, and combining weak signals fits noise.

### 2026-11-26: ICT (Inner Circle Trader) silver bullet and Judas swing (`ict.py`). FAIL

The owner asked to test ICT. Its two setups that can be written as exact rules were pre-registered in 30bc033:
- **Silver bullet:** the first fair value gap of 10:00-11:00 New York, with a limit entry at the gap and the
  stop beyond candle 1.
- **Judas swing:** a sweep of the previous day's low or high, a close back inside it, then the first gap in the
  reversal's direction before 11:30, with the stop at the sweep extreme.

Both use 2R targets (3R reported), 3 bps a round trip, and 4 years of 5-minute bars (QQQ for NAS100, plus SPY
and IWM). The in-sample period runs to 2024, and the judged period starts in 2025.

| setup (2R) | QQQ in-sample | QQQ judged | SPY judged | IWM judged | $500 since 2025 (QQQ) |
| --- | --- | --- | --- | --- | --- |
| silver bullet | −1.2 bp, t −0.56 (319 trades) | −1.8 bp, t −0.57 (264), 34% wins | −2.6 bp, t −1.26 | +1.5 bp, t +0.52 | $476 |
| Judas swing | −8.8 bp, t −2.35 (162) | −5.5 bp, t −1.17 (148), 36% wins | −6.3 bp, t −1.52 | +2.9 bp, t +0.55 | $460 |

QQQ held from 2025 turned $500 into $616.

- **Both FAIL.** On QQQ and SPY both lose in both periods. IWM's small judged gains (t 0.5-0.7) come after
  in-sample losses, so they are noise.
- **The 3R targets are no better.**
- **Most trades end at the stop** (silver bullet: 361 stops against 172 targets). A gap entry with a tight stop
  is mostly a bet that pays 2:1 and loses more than two thirds of the time.
- **Not tested:** order blocks, "smart money" intent and higher-timeframe bias have no single exact
  definition. Testing many versions of them would be a search for a lucky one.

## 2026-11-26: "NY AM range sweep" indicator on Bitcoin and Ether 5-minute bars (`nyam.py`). FAIL

The owner asked to test "nyam". It's the TradingView "NY AM Range Sweep" indicator:
- mark the 05:00–09:00 New York range;
- wait for a candle to close beyond it;
- wait for a 5-minute engulfing candle and a 45-minute check that agree;
- target 2R.

The TradingView page itself was blocked by the network allowlist, so I wrote the rules down from its public
description. Both readings were tested: fade the sweep, and follow the break. Pre-registered in 41b81bf.
Costs are 20 bp a round trip. Chosen on data before 2025, judged from 2025.

| BTC | in-sample | judged 2025+ | $500 since 2025 |
|---|---|---|---|
| reversal (fade the sweep) | 115 trades, +27.9 bp, t 2.22 | 131 trades, −18.8 bp, t −2.09 | $388 |
| continuation (follow the break) | 226 trades, −7.1 bp, t −1.62 | 226 trades, −17.1 bp, t −4.14 | $338 |
| BTC held | | | $323 |

- **FAIL on both readings.** The fade looked good before 2025 (t 2.22) and then lost money from 2025.
- Even at 10 bp costs both still lose (−8.8 and −7.1 bp a trade).
- Ether agrees: −5.1 bp in-sample for the reversal, −22.7 bp (t −5.02) for the continuation.
- Both readings beat holding BTC since 2025 only because BTC fell 35%. They spent most of the time in cash.

**Round 2, with the indicator's published rules** (`nyam2.py`, pre-registered in b2fecfc). I read the TradingView
page directly. It says the setup is a reversal ("trade the other side of that trap"). The engulfing candle must
cover the previous candle's body and wick. The stop is at the sweep's extreme, and the target is the opposite side
of the AM range. The 45-minute check was set as "the last completed 45-minute candle has the trade's colour".

| | in-sample | judged 2025+ | $500 since 2025 |
|---|---|---|---|
| BTC | 49 trades, −30.0 bp, t −3.17 | 45 trades, −4.6 bp, t −0.50 (+5.4 bp at 10 bp cost) | $489 |
| ETH | 33 trades, −17.7 bp, t −1.63 | 5 trades | $472 |

- **FAIL.** The full rules fire only about once a month. They lost clearly before 2025 and roughly broke even after.
- The page says it's meant for indices, forex and futures. The lab has no 24-hour data for those; this is the
  crypto test only.

### 2026-11-26: ICT full backtest, 40 markets, about 4 years each (`ict.py full`). FAIL

The owner asked to test ICT on more days. The extension was pre-registered in 491ddf2. It covers the silver
bullet, ICT's afternoon silver bullet (14:00-15:00) and the Judas swing, with the same rules, on all 40 stocks
and funds in data/long. The statistic is pooled: one observation per day, the average over the markets that
traded.

| setup (2R) | trades | win rate | in-sample (to 2024) | judged (2025 on) | markets positive since 2025 |
| --- | --- | --- | --- | --- | --- |
| silver bullet (10-11) | 25,732 | 36% | −0.2 bp/day, t −0.20 | −1.2 bp/day, t −0.98 | 12 of 40 |
| silver bullet PM (2-3) | 25,912 | 35% | −1.6 bp/day, t −2.56 | −2.4 bp/day, t −3.40 | 4 of 40 |
| Judas swing | 13,262 | 40% | −2.2 bp/day, t −1.22 | −1.1 bp/day, t −0.48 | 17 of 40 |

- **All three FAIL** on about 65,000 trades.
- **The afternoon silver bullet reliably loses** (t −3.4 judged). Only 4 of 40 markets are positive.
- **The 3R targets are no better.**
- With 40 times more trades than the QQQ-only test, the answer is the same: ICT's fair value gap entries lose
  slightly before costs and more after them.

**Round 3, on the markets the indicator names** (`nyam_fx.py`, pre-registered in 0dafab4 before any FX data was
downloaded). The data is Tiingo 5-minute gold (XAU/USD) and EUR/USD from 2022-11, with the round-2 rules. Costs are
5 bp a round trip for gold and 2 bp for EUR/USD.

| | in-sample | judged 2025+ | $500 since 2025 | held |
|---|---|---|---|---|
| gold | 45 trades, −9.6 bp, t −2.84 | 48 trades, −3.6 bp, t −0.58 | $491 | $678 |
| EUR/USD | 59 trades, −0.8 bp, t −0.46 | 57 trades, −2.4 bp, t −1.53 | $493 | $530 |

- **FAIL on both.** The NY AM range sweep lost on Bitcoin, Ether, gold and the euro, before and after 2025.

### 2026-11-26: every multi-day rule, swap-free (`swapfree.py`; the owner's Exness swap-free account)

The owner now has an Exness swap-free account (standard spreads, no overnight swap). Pre-registered in
f2ebb44: each engine is rerun unchanged, with only the overnight cost set to zero, judged by its own bar.

| rule (judged period) | with swap | swap-free | bar | verdict |
| --- | --- | --- | --- | --- |
| indices bot, 10 indices (2015-26) | 1.6%/yr, t 0.78, placebo 48% | 3.4%/yr, t 1.45, placebo 44% | t >= 2, placebo 95%, +3x cost | FAIL |
| indices bot, US only (2015-26) | 3.1%/yr, t 1.81, placebo 82% | **4.0%/yr, t 2.33**, placebo 78%, +3.4%/yr at 3x cost | same | FAIL (placebo) |
| indices walk-forward, US (2015-26) | 3.3%/yr, t 1.85, placebo 84% | **4.3%/yr, t 2.61**, placebo 90%, +3.7%/yr at 3x | same | FAIL (placebo) |
| US500 held | | 12.9%/yr, t 2.68 | | |
| Bitcoin: TTM squeeze / Vortex / DTC ribbon / 200-day (2020 on) | t 2.26 / 1.72 / 1.01 / −0.18 | t 2.46 / 2.25 / 1.39 / 0.36 | t >= 3.5 | FAIL |
| oil: 0 of all candidates (2015 on) | best post t 1.38 | best post t 1.43 (Donchian 20) | t >= 3 | FAIL |
| crypto/forex bot (2 years) | −$1.27/trade, t −8.14 | −$1.18/trade, t −7.58 | | FAIL |
| buy low/sell high, 3 variants | −$1.29 to −$1.38/trade | −$1.17 to −$1.27/trade | | FAIL |

- **Swap-free helps the slow rules most.** The US index dip rule now clears t 2 and survives triple costs.
- **It still fails the placebo.** Random entries into the same uptrending indices with the same hold
  lengths do almost as well (median t 1.78, and the rule beats only 78-90% of them). The rule's return is
  mostly from holding the index, not from the timing.
- **Holding US500 is still three times better** (12.9% against 4.0-4.3% a year).
- **Short-term rules barely move.** The crypto/forex hourly rules lose about $1.2 a trade on the spread
  alone, so removing the swap can't save them.
- No rule passes. Caveat: Exness swap-free accounts can charge a fixed fee after some nights on some
  instruments; these tests assume zero.
**Round 4, on stock indices** (`nyam_idx.py`, pre-registered in 3f9df1c before any index data was downloaded). The
data is Alpaca SIP 5-minute SPY and QQQ from 2016, including the 05:00 pre-market, with the round-2 rules and 5 bp
a round trip. One fix (424b65a) came before any result: the first run crashed on days with no candle before 05:00,
and those days are now skipped.

| | in-sample 2016–2024 | judged 2025+ | $500 since 2025 | held |
|---|---|---|---|---|
| SPY | 404 trades, −6.8 bp, t −4.06 | 59 trades, −7.3 bp, t −1.83 | $479 | $619 |
| QQQ | 349 trades, −7.3 bp, t −2.89 | 58 trades, −9.7 bp, t −1.24 | $472 | $620 |

- **FAIL on both.** The losses are clear in nine years of in-sample data. Before costs it is still slightly
  negative (SPY −1.8 bp in-sample), so the 05:00–09:00 sweep reversal has no edge on indices either.
