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
