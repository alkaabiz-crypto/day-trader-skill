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

## Idea queue (top first)

0. **Survivorship-free test of R3**: add stocks that fell hard or were delisted (e.g. from an
   S&P 500 membership history), or test on many more ETFs and country funds. Until then R3 is
   unproven.
1. **R3 on a wider ETF set** (country, bond, commodity and leveraged funds back to the 2000s):
   more survivorship-free trades to see if the ETF-only t of 1.53 was just too few trades.
2. **New strategies from the web**: each daily run adds at least one rule not yet tested.
3. **Forward test**: score R3 and the near misses on sessions after 2026-11-22 (`daily.py forward`).
4. **Last-half-hour reversal on the 5-minute store**, pre-registered after imom's OOS t of -3.6 (judged only after 2026-11-20).
5. **Stocks in play, revisited** once the 5-minute store has 120+ sessions.
6. **FOMC and CPI days** (needs an event calendar): pre-FOMC drift (Lucca & Moench 2015) is reported dead after 2015, so a control, not a hope.
7. **Earnings-day drift and the earnings announcement premium** for single stocks (needs an earnings calendar from trader-analyst).

## Log

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
