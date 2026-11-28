# Pre-registration: famous daily strategies on Exness costs (written 2026-11-26, before any run)

Data (offline, from the repo's stores): US500 proxy = SPY session bars 2016-01 to 2026-11 (data/idx/spy),
USTEC proxy = QQQ (data/idx/qqq); XAUUSD and EURUSD 5-minute bars 2022-11 to 2026-11 (data/fx), daily bars cut at 17:00 New York.
Rules use their published default settings. No parameter is tuned.

Fills: signal rules decide on day t's close and trade at day t+1's open. Calendar rules (overnight, turn of month,
turnaround Tuesday) trade at the close, which an always-open CFD can do at 16:00.

Costs (Exness's own pages did not load; third-party figures, made cautious):
- spread per round trip: US500/USTEC 2 bp, XAUUSD 1.5 bp, EURUSD 1.5 bp; no commission (Standard)
- Standard swap per calendar night held (Wednesday rollovers are triple in practice; counted as calendar nights):
  indices long 6.5%/yr, short 1%/yr; gold long 5%/yr, short 1%/yr; EURUSD long 2.5%/yr, short 0.5%/yr (all /360)
- Swap-free: swap 0. Caveat: extended swap-free fees after some nights are unknown and ignored.
- stress: everything x2

Periods: indices IS 2016-2020, JUDGED 2021-01 to 2026-11. Gold/EURUSD IS to 2024-06, JUDGED 2024-07 on (short, weak).
PASS (per rule x market x account): IS net mean > 0, JUDGED t >= 3.0 (about 18 rules x 4 markets x 2 accounts tested),
JUDGED Sharpe above buy-and-hold's under the same account, still positive at 2x costs, and beating 95% of
200 circular time-shift placebos of its own position series on the judged period.
Also reported: $1,000 from 2024-01-02 to the end, with the worst drop.

Rules: buyhold, sma200, golden 50/200, tsmom 252, turtle20 (20/10), turtle55 (55/20), macd 12/26/9, supertrend 10/3,
ema 9/21 cross, rsi2 (Connors: RSI2<10 above SMA200, out close>SMA5), double7, ibs (<0.2 in, >0.8 out),
bollinger 20/2 (below lower in, above mid out), overnight (close to open daily), turn of month (last trading day-1 close
to 3rd trading day close), turnaround tuesday (Monday down close to Tuesday close), donchian-breakout long-short on gold/fx
via turtle rules; trend rules are long/flat on indices, long/short on gold and EURUSD; mean-reversion rules long-only.
Thu Nov 26 20:55:59 UTC 2026

## Batch 2 (written after batch 1's results, before batch 2 runs; same data, costs, gates)
rsi14 30/70 (long below 30, out above 70; long-short on gold/fx: short above 70, out below 30), stoch 14/3 (k<20 in, k>80 out),
williams %R 14 (<-90 in, >-10 out), cci 20 (<-100 in, >0 out), adx 14 > 25 with +DI>-DI (trend, long/flat or LS),
parabolic SAR 0.02/0.2, ichimoku (close above cloud long, below short/flat), hull 55 slope, keltner 20/2 ATR breakout,
nr7 breakout (after a narrowest-of-7 range day, long above its high, exit 5 days), inside-day breakout (same, 5 days),
3 down closes buy (out on first up close), cumulative RSI(2) (sum of 2 days < 35 above SMA200, out RSI2 > 65),
heikin-ashi colour (long green, out/short red), 10-week (50-day) SMA weekly-style filter, halloween (long Nov-Apr only).

## Batch 3: the gold-trend lead on long history (written before downloading any long data)
Data: Yahoo daily GC=F (gold futures) from 2000, plus SPY, QQQ, EURUSD=X, IEF, TLT, GLD (adjusted closes) for a dividend-correct mix rerun.
Rules, unchanged settings: sma200, ichimoku, sma50 long/short on gold; plus buyhold. Costs as batch 1 (XAUUSD 1.5 bp, swap long 5%/yr, short 1%/yr).
Judged period: 2010-01 to 2024-06 (BEFORE the batch-1 judged window, so the lead is tested on years it never saw), IS 2000-2009.
PASS: IS mean > 0, judged t >= 3 (3 rules), judged Sharpe > gold buy-and-hold's, positive at 2x costs, placebo >= 95%.
Thu Nov 26 21:36:28 UTC 2026

## Batch 4: old repo ideas re-run at measured Exness Standard costs (written before any run)
Costs (measured Standard spreads given 2026-11-26, plus 0.4 bp slippage per round trip; $0 commission):
US500/SPY and USTEC/QQQ 1.0 bp, IWM/DIA proxies 1.0 bp, XAUUSD 1.0 bp, EURUSD 1.2 bp, BTCUSD 1.5 bp (spread ~$6 on ~$60k), ETH 1.5 bp.
Overnight: Standard as batch 1 (indices long 6.5%/yr, short 1%; BTC 3 bp a night as in dtc_btc), swap-free 0.
Each repo engine runs UNCHANGED (rules, data, splits, its own pass bar); only its cost constants are replaced, from a
scratch runner, without editing repo files:
 a. lab.py 5-minute rules on the 4-year SPY/QQQ/IWM store (bar: lab.py's gates, OOS t >= 3)
 b. hourly.py time-of-day rules (its bar)
 c. candles.py parts 1 (stocks->index ETFs not possible; run as written with stocks at 1.0 bp is NOT Exness-realistic for
    single stocks, so reported only as a lower bound) and 2 (daily patterns at 1.0 bp, crypto 1.5 bp) (bar t >= 3.5)
 d. catalog.py 60 named strategies, 5 bp -> 1.0 bp, crypto 20 bp -> 1.5 bp (bar t >= 3.5)
 e. dtc_btc.py, spread 6 -> 1.5 bp, swap 3 -> 0 and 3 (its bar)
 f. oilbrain/brain.py: no measured USOIL spread was given, so its 5 bp stays; nights 1 bp -> 0 (swap-free)
 g. the 15:30 reversal shadow trial at 1.0 bp
 h. my batches 1-2 at the new costs
New lower costs make more rules look better by construction, so the bars are NOT lowered.
Thu Nov 26 21:41:18 UTC 2026

## Batch 4 follow-up (written after catalog showed coppock t 3.64 and trix_15 t 3.57 at the new costs, before any check)
Checks for coppock and trix_15, all on the catalog's own positions and judged period (2016 on):
 1. per-market judged alpha t (where does it come from)
 2. 500 circular time-shift placebos of each market's positions, pooled alpha: must beat 95%
 3. both halves positive: 2016-2020 and 2021-2026
 4. Standard account: long swap charged (ETFs/indices 6.5%/yr per calendar night, BTC/ETH 3 bp a day) - does it survive?
 5. $1,000 on BTC alone from 2024-01-01, swap-free and Standard, vs holding BTC
Only if 2 and 3 hold is it called a candidate for a forward (paper) test. It is never called proven.

## Batch 5 (written 2026-11-26 22:40 UTC, before any run): earlier years, real lot sizes
A. Coppock and TRIX 15 exactly as in catalog.py (its build()), on 2000-01 to 2015-12 only: SPY, QQQ, GLD/GC=F, EURUSD=X
   (years the catalog's judged period never used; BTC/ETH have no data then). Swap-free, 1 bp round trip.
   Confirmation needs pooled alpha t >= 2.0 on 2000-2015 AND positive in each market's mean.
B. Lot sizing on $1,000: exposure of one minimum lot at the last price (US500 0.14, USTEC 0.05, XAUUSD 0.01 = 1 oz,
   BTCUSD 0.01, EURUSD 0.01 = 1,000 EUR). Report worst historical 1-day, 1-month and peak-to-trough loss in $ at min lot.
C. Dual momentum rotation (Antonacci-style, monthly): hold the best 12-month performer of US500, USTEC, gold, BTC if its
   12-month return > 0, else cash; and a 3-asset version without BTC. Judged 2016 on (BTC from 2015). Swap-free, 1 bp.
   PASS: Sharpe above an equal-weight hold of the same assets, t on excess vs that hold >= 3.
Thu Nov 26 22:34:51 UTC 2026

## Batch 6 (written before running): Bitcoin, the only market where a 0.01 minimum lot (~$630) fits a $1,000 account
Yahoo BTC-USD daily (UTC days) 2014-09 on. IS before 2020-01-01, JUDGED 2020 on. Swap-free, 1.5 bp round trip
(spread $6.40 on ~$60k ~ 1.1 bp + slippage). Long or flat, one 0.01 lot.
Rules: sma200 (Mayer filter), mayer_dip (long when price/SMA200 < 1.0, out above 1.5), donchian 20/10, sma50/200 cross,
vol_filter (long only when 30-day realized vol is below its trailing 1-year median), weekend (hold only Fri 00:00 to Mon 00:00 UTC),
weekdays (hold Mon-Fri only), tom (last 2 and first 3 UTC days of the month), coppock and trix (catalog definitions, for reference).
PASS: IS mean > 0, judged t >= 3, judged Sharpe > BTC hold's, positive at 2x cost, beats 95% of 200 time-shift placebos.
Thu Nov 26 22:36:04 UTC 2026

## Batch 6 follow-up (written after donchian 20/10 on BTC passed at t 3.00, before any check)
Robustness, reported not tuned: judged halves 2020-2022 and 2023-2026; neighbour settings 15/7, 25/12, 30/15, 55/20;
the same 20/10 rule on ETH (2017 on, judged 2020 on); and 1-lot dollar results from 2024 on a $1,000 account.
Called a forward-test candidate only if both halves are positive, most neighbours are positive judged, and ETH is positive.

## Batch 7 (written before running): all 29 batch 1-2 rules on 26 years of US500 and USTEC
Yahoo dividend-adjusted SPY (US500, whose CFD also gets dividend adjustments) and QQQ (USTEC), 2000-01 to 2026-11.
IS 2000-2012 (two crashes), JUDGED 2013 on. Swap-free, 1.0 bp. Long or flat. Dollar results at the minimum lot:
US500 0.14 (~1.0x a $1,000 account), USTEC 0.05 (~1.3x). Same PASS bar as batch 1.
Thu Nov 26 22:38:02 UTC 2026

## Batch 8 (written before running): close-fill mean reversion, possible only because index CFDs trade at 16:00 NY
The repo found IBS's edge is the overnight bounce, lost with next-open fills. An Exness CFD can be bought at 15:59 New York.
Rules filled AT the signal day's close (approximating a 15:59 order; cost 1.5 bp to cover the gap from the official close):
 ibs_close (IBS < 0.2 in, out at the first close above the prior close), ibs_close_08 (out when IBS > 0.8),
 rsi2_close (Wilder RSI2 < 10 above SMA200, out close > SMA5), double7_close.
US500 and USTEC, Yahoo adjusted SPY/QQQ 2000 on, IS 2000-2012, JUDGED 2013 on, swap-free. Same PASS bar as batch 1.
Thu Nov 26 22:39:14 UTC 2026

## Batch 8 realism check (written after ibs_close passed, before this check)
Danger: batch 8 decides on the close AND fills at that same close (look-ahead). Realistic version, on the repo's
extended-hours 5-minute SPY/QQQ bars (data/idx, 2016-2026): signal from the 9:30-16:00 session OHLC; entry and exit
filled at the first 5-minute bar opening at or after 16:10 New York (an order placed after the cash close, while the
CFD still trades). Cost 1.5 bp. Confirmation needs 2016-2026 t >= 3 for ibs_close and ibs_close_08 on each market,
positive in 2016-2020 and 2021-2026, placebo >= 95%. Price-only data (no dividends), so buy-and-hold is understated slightly.

## Batch 10 (written 2026-11-26 ~23:00 UTC, before any run): 18 well-known intraday setups with stop-loss and take-profit
Data: repo 5-minute bars. US500 = SPY, USTEC = QQQ (data/idx, 2016-2026, session 9:30-16:00 NY, entries 9:35-15:00,
flat at 15:55). XAUUSD, EURUSD (data/fx, 2022-11 to 2026-11, session 03:00-15:55 NY, entries 03:00-12:00, Asian range
19:00-03:00 NY). One trade per setup per day (the first signal). Entry at the next bar's open after the signal bar closes.
Bracket: stop SL and target TP set from the 14-day average daily range (ADR): SL in {0.15, 0.30} x ADR, TP = R x SL,
R in {1, 2, 3} (6 variants). If a bar touches both, the STOP is assumed first. Unfilled by the flat time: out at market.
Costs per round trip (Exness measured spread + slippage): US500 1.0 bp, USTEC 0.65 bp, XAUUSD 0.85 bp, EURUSD 1.0 bp.
No swap (flat daily; swap-free anyway). Dollars at min lot: US500 0.14 (~$950), USTEC 0.05 (~$1,250), XAUUSD 0.01 (~$3,740),
EURUSD 0.01 (~$1,100).
Setups (L long, S short):
 orb15 / orb30: break of the first 15/30-minute range, both sides
 dip_open: buy when price falls 0.5 ADR below the day's open (buy low); rally_open: short 0.5 ADR above (sell high)
 vwap_pb: after 10:30 (FX: after 05:00), in the direction of price vs VWAP at 10:30, enter on the first touch of VWAP
 bb_rev: 5-min close outside Bollinger(20,2): fade it back
 rsi_rev: 5-min RSI(14) < 30 long / > 70 short
 pdhl_break: break of the previous day's high (L) or low (S)
 pdhl_fade: touch of the previous day's high (S) or low (L), i.e. support/resistance bounce
 sweep: price trades beyond the previous day's low/high, then a 5-min close back inside: trade the reclaim (liquidity sweep)
 gap_fill: open gapped >= 0.2 ADR from the previous close: trade toward the previous close at the open (indices only)
 ema_cross: 5-min EMA9 crosses EMA21 (first cross after 10:00 / FX 04:00)
 pivot_bounce: classic floor pivots from yesterday: touch S1 long, R1 short
 first30_mom: first 30 minutes moved > 0.3 ADR: continue at 10:00
 inside_break: the 2nd 5-min bar inside the 1st: trade the break of the 1st bar
 three_pb: 3 lower 5-min closes while above EMA50 -> long; 3 higher closes while below -> short
 london_break (FX/gold only): break of the Asian range after 03:00 NY
 ny_reversal: at 10:00, fade the move from the open if > 0.4 ADR
Choice and judging: the variant with the best in-sample mean is chosen per setup x market. IS: indices before 2022,
FX/gold before 2024-07. JUDGED after. PASS needs IS t > 0, judged t >= 3.0, positive at 2x cost, and beating 95% of
1,000 random-direction placebos (each trade's side flipped at random, re-simulated with the same bracket).
Thu Nov 26 22:54:56 UTC 2026

## Batch 11 (written 2026-11-26 23:40 UTC, before any run)
A. The repo's skill chain as one system (scanner > entry > exit > Time Machine > budget > risk), replayed on the 40-name
   4-year 5-minute store (data/long), 2024-01-02 to 2026-11-25, $1,000 account. Copy of bot.py's stock rule:
   at 10:17, 11:17, 12:17, 13:17, 14:17 NY, names whose 5-min close broke above the 9:30-9:45 range high and are still above,
   ranked by traded value so far; 2 a run, 5 a day; entry next 5-min open; stop = range midpoint; target 2R; out 15:55;
   $10 risk a trade (shares = 10 / (entry - stop)), notional cap $1,000; risk check: stop the day after -$30.
   Variant TM: also require the Time Machine's history check (the same rule on that stock's previous 59 sessions hit the
   target first at least as often as the stop first). Costs: 3 bp round trip (Exness stock CFD spreads are not measured; 5 bp stress).
   The news skill can't be replayed (no headline archive) and is left out; this is stated in the report.
B. Breakout strategies on daily bars (Yahoo adjusted SPY = US500, QQQ = USTEC, GC=F gold, BTC-USD), swap-free 1 bp (BTC 1.5):
   squeeze (Bollinger 20/2 width at a 120-day low, then a close above the upper band; out below the 20-day mean),
   darvas (box = 20-day high not exceeded for 3 days; buy a close above it; out below the box low),
   high52 (close at a 252-day high; out below the 50-day mean), weekly_high (close above the prior 5-day high; out below the
   prior 5-day low), nr4 (after a narrowest-of-4 range day, buy a break of its high; out after 5 days),
   williams (Larry Williams volatility breakout: buy intraday at open + 0.6 x prior range, out at the close; stop-free),
   atr_channel (close above SMA20 + 2 ATR14; out below SMA20), donchian_bracket (20-day breakout, stop 2 ATR, target 4 ATR).
   Long only (gold long and short for the channel rules). IS: before 2013 (BTC before 2020); judged after.
   PASS as batch 1 (judged t >= 3, Sharpe above holding, 2x cost positive, placebo >= 95%, IS mean > 0).
Thu Nov 26 23:33:55 UTC 2026

## Batch 11 follow-up (written after Williams volatility breakout passed on BTC t 5.96 and gold t 3.14, before checks)
Darvas results equal buy-and-hold exactly: an exit bug, so darvas is excluded (not re-run with a fix tonight).
Checks for williams (buy-stop at open + k x yesterday's range, out at the day's close):
 k neighbours 0.4 / 0.5 / 0.7 / 0.8 (reported, not chosen); halves 2020-22 and 2023-26 (gold: 2013-19 and 2020-26);
 3x cost; ETH; and the exact intraday path on the repo's 1-hour BTC bars (data/fx1h, 2024-11 on): fill at the level
 when an hour's high reaches it, exit at the last hour before 00:00 UTC; compare to the daily-bar result on the same days.

## Batch 12 (written 2026-11-27 00:31 UTC, before any run): rules that fit $228-$1,000 at Exness minimum lots
Markets limited to those whose minimum lot is <= ~1.3x a $1,000 account: BTCUSD 0.01, USTEC 0.05, US500 0.14, EURUSD 0.01.
Costs: swap-free main case (BTC 1.5 bp, USTEC 2.12 pt round trip = spread 1.12 + 1 pt slippage, US500 0.40 + 0.5 pt,
EURUSD 1.0 pip + 0.2); Standard case adds the swap for any position held past 00:00 server time (same rates as batch 1).
A. BTC daily (UTC bars, Yahoo BTC-USD 2014-09 on; IS before 2020, judged 2020 on), trade at the UTC close (24/7 market):
   btc_ibs (IBS < 0.2 buy, out at first close > prior close), btc_ibs_mom (IBS > 0.8 buy, out next close),
   btc_rsi2 (RSI2 < 10 and close > SMA200 buy, out close > SMA5), btc_3low (3 lower closes buy, out first up close).
B. Williams volatility breakout SHORT side (sell-stop at open - 0.6 x yesterday's range, cover at the day's close), k fixed at 0.6:
   BTC (judged 2020 on), USTEC and US500 cash session from QQQ/SPY daily bars (judged 2013 on), EURUSD (judged 2013 on);
   plus the long side on EURUSD (not tested before). Also BTC long+short combined.
C. Intraday momentum (Gao, Han, Li, Zhou 2018) on QQQ = USTEC and SPY = US500, 5-minute bars 2016-2026
   (IS 2016-2020, judged 2021-2026): r1 = previous 16:00 close to 10:00 return; trade 15:30-16:00 in the sign of r1.
   Variant C2 (Baltussen et al.): sign of 9:30-15:30 return, trade 15:30-16:00. Variant C3: both signals must agree.
   Fills at the 15:30 bar open, out at the 15:55 bar close. No overnight hold, so Standard = swap-free.
PASS (unchanged): IS mean > 0, judged t >= 3, positive at 2x cost, beats 95% of 200 placebos (time-shift for daily rules,
random-direction for C), and for always-in-market comparisons judged Sharpe above holding. Dollar results at the min lot from 2024.
Nothing chosen in-sample except where stated: all parameters above are fixed now.

## Batch 13 (written 2026-11-27 00:33 UTC, before any run): more min-lot rules
A. After-close overnight reversal on USTEC (QQQ) and US500 (SPY), 5-minute bars 2016-2026 incl. extended hours
   (IS 2016-2020, judged 2021 on). A1: day's 9:30-16:00 return <= -1% -> buy at the 16:10 bar open, sell at the next
   09:30 bar open. A2: any down day. Costs USTEC 2.12 pt, US500 0.9 pt; Standard adds one night of swap (6.5%/yr).
B. Crude oil (USOIL 0.01 lot = 10 bbl, about $600-700), Yahoo CL=F daily 2000 on (IS before 2013, judged 2013 on;
   front-month rolls make gaps, so open-to-close and close-to-close rules are scored inside each bar only where stated):
   oil_williams_long / oil_williams_short (k 0.6, out at the close, intraday only), oil_ibs (IBS < 0.2 at the close, out
   at the first close above the prior close), oil_rsi2. Cost 5 bp round trip (Exness oil spread not measured; 10 bp stress).
   Close-to-close rules skip roll days (|return| > 8% with a contract change is not detectable, so it's reported as a caveat).
Pre-FOMC drift on USTEC is dropped: the Fed calendar host is not on the network allowlist.
PASS bar unchanged (batch 12).

## Batch 14 (written 2026-11-27 00:34 UTC, before any run): does "IBS at the close" work on other index CFDs?
Exact batch 8 rule (IBS < 0.2 buy at the close, sell at the first close above the prior close), daily-bar close fills
(an always-open CFD can trade minutes after the cash close), swap-free 1.5 bp round trip, Standard adds 6.5%/yr per night.
Yahoo daily: ^DJI (US30), ^RUT (US2000), ^GDAXI (DE30/GER40), ^FTSE (UK100), ^N225 (JP225), ^STOXX50E (STOXX50), ^HSI (HK50).
IS 2000-2012, judged 2013 on. PASS bar as batch 7 (judged t >= 3, Sharpe above holding, 2x cost positive, placebo >= 95%).
Exness minimum lots for these are not verified; any pass needs a lot-size check in the terminal before a paper ledger.

## Batch 15 (written 2026-11-27 00:45 UTC, before any run): scanner strategies that trade EVERY day
Hazza's ask: at least 3 candidates that trade daily, built on the scanner idea (rank the universe by "most oversold", buy the top).
Universe S: the repo's 30 single stocks (AAPL AMD AMZN ARM AVGO BA COIN COST CRM CRWD GOOGL INTC JPM LLY META MSFT MSTR MU
NFLX NKE NVDA ORCL PLTR SHOP SMCI TSLA UBER UNH WMT XOM), Yahoo adjusted daily 2005 on; a name joins once it has 200 days.
Universe M (Exness CFD markets that fit min lots): US500 (SPY), USTEC (QQQ), US30 (DIA), US2000 (IWM), BTC, ETH.
Book: $1,000 split equally across the picks (stock CFD sizes; Exness stock-CFD min lots/spreads not verified).
IS 2010-2018, judged 2019-2026-11. Cost stocks 3 bp round trip (5 and 10 bp stress), M as batch 12 (ETH 3 bp).
Each rule holds new picks EVERY trading day (one-day holds, rebalanced daily):
 D1 ibs3_open: at the close buy the 3 lowest-IBS stocks, sell next open.  D1b same, sell next close.
 D2 rsi2_3: at the close buy the 3 lowest RSI2 stocks among those above their SMA200, sell next close.
 D3 gap2: at the open buy the 2 biggest gap-downs (open / prior close), sell at that day's close.
 D4 rev5_3: at the close buy the 3 worst 5-day returns, sell next close.
 D5 mkt_ibs1: at the close buy the 1 lowest-IBS market of universe M, sell next close (US indices close at 16:00 NY;
    BTC/ETH use the UTC day: decided at 00:00 UTC on the prior UTC day; a simplification, reported).
 D6 scanner + Time Machine, relaxed: batch 11's chain on the 5-min store 2024-26, but take the 1 best-ranked breakout each
    day that passes the TM check, else the 1 best-ranked one without it (so a trade every day there is any breakout).
Placebo for D1-D4: 300 runs buying the same number of RANDOM names from the same universe on the same days with the same
holding times (this controls for the universe being today's winners: survivorship bias). D5: random market.
Ranking for Hazza: judged-period $ profit on $1,000 with worst drop, t, placebo, last 2 years. Top 3 go to the paper ledger even if weak, labelled.
5-min check (2022-11 on, repo data/long + 5-min store) for whichever of D1-D4 ranks top 3: decide at 15:50, fill 15:55 bar.

## Batch 15b (written 2026-11-27 00:48 UTC after batch 15's results: D1 ibs3_open is the only rule beating its random-name placebo, judged t 2.93; D6 relaxed lost money)
1. 5-minute realism check of D1 on the repo's 40-name store (30 stocks only), 2022-11 to 2026-11: IBS from 9:30-15:50 bars,
   buy the 3 lowest at the 15:55 bar open, sell at the next day's 9:30 bar open (also 9:35 and 10:00 open, reported).
2. Neighbours of D1 (reported, not chosen): 1, 2, 5 picks; only names above SMA200; 2005-2026 whole span.
3. New daily rules (fixed now): D7 intraday-loser scan: at 15:55 buy the 3 stocks with the worst 9:30-15:50 return, sell next 9:30 open
   (5-min store). D8 BTC Williams order placed every day (unchanged rule; reported as "trades on ~1/3 of days").
   D9 IBS-low basket on the CFD indices + BTC decided at 00:00 UTC with 1-hour bars (fx1h BTC + 5-min idx data) is skipped: too little BTC hourly history.

## Batch 15c (written 2026-11-27 01:09 UTC, before any run): the two stock scans at Exness stock-CFD hours
Exness stock CFDs trade only 09:40-15:45 New York, are not swap-free, Standard has no commission (web lookup 2026-11-27).
Retest D7 and D1 on the 5-min store: decide on bars through 15:35, buy at the 15:40 bar open, sell at the next day's
09:45 bar open (also 10:00 and 10:30). Cost 3 bp (5 and 10 bp stress) plus a long swap estimate of 8%/yr per calendar
night (Friday held 3 nights); 0 and 12%/yr reported. Placebo: 3 random names, same times. If t < 2 or net <= 0 after swap,
the scan is marked NOT TRADABLE on Exness and removed from the paper ledger.

## Batch 16 (written 2026-11-27 01:51 UTC, before any run): swing "buy low, sell in 2-3 days" + academic anomalies
Markets: US500 (SPY), USTEC (QQQ), US30 (DIA), US2000 (IWM), Yahoo dividend-adjusted daily 2000-2026, IS 2000-2012,
judged 2013-2026-11; BTC and ETH (UTC days, judged 2020 on). Signals on the close, fills at that close (an always-open CFD
trades minutes after 16:00 NY). Long or flat, one position. Swap-free costs: US500 1.3 bp, USTEC 0.9, US30 1.5, US2000 2.0,
BTC 1.5, ETH 3.0 round trip; Standard adds 6.5%/yr per night held (indices). Min lots: US500 0.14, USTEC 0.05, BTC 0.01
(US30, US2000, ETH min lots unverified).
Rules (all parameters fixed now; sources: Connors & Alvarez "Short Term Trading Strategies That Work" 2008 and "High Probability
ETF Trading" 2009; Ariel 1990 pre-holiday; Stivers & Sun 2013 option-expiration week; Bouman & Jacobsen 2002 Halloween):
 R1 rsi2: RSI2 < 10, close > SMA200 -> buy; sell close > SMA5.
 R2 cumrsi: RSI2 today + yesterday < 35, close > SMA200 -> buy; sell RSI2 > 65.
 R3 r3: RSI2 fell 3 days in a row, first day < 60, today < 10, close > SMA200 -> buy; sell RSI2 > 70.
 R4 pctb: Bollinger %b(20,2) < 0.2 three days in a row, close > SMA200 -> buy; sell %b > 0.8.
 R5 mdd: close < SMA5, close > SMA200, and 4 lower closes in a row -> buy; sell close > SMA5.
 R6 low10_3d: close at a 10-day low, close > SMA200 -> buy; sell after 3 days (Hazza's "buy low, sell after 2-3 days").
 R7 low5_2d: close at a 5-day low (any trend) -> buy; sell after 2 days.
 R8 vixstretch (US indices only): VIX close >= 5% above its SMA10 for 3 days, index close > SMA200 -> buy; sell RSI2 > 65.
 R9 ibs_multi: IBS < 0.2 and close < previous close -> buy; sell after 3 days or close > previous day's high.
 R10 preholiday (US): buy the close before a market holiday (a weekday with no session), sell the next session's close.
 R11 opex: hold from the close of the Friday before option-expiration week (3rd Friday of the month) to the close of opex Friday.
 R12 halloween: hold Nov 1 - Apr 30, flat May - Oct (benchmark-style; judged by Sharpe vs hold).
 R13 tom_ext: last trading day through the 3rd trading day of the month (turn of month, Lakonishok & Smidt 1988).
 BTC/ETH get R1-R7 and R9 (with SMA200 rules as written).
PASS: IS mean > 0; judged t >= 3; 2x cost t > 0; time-shift placebo (signal rotated) >= 95%; judged Sharpe > buy-and-hold's;
both judged halves positive. 13 rules x 6 markets ~ 70 tests, so t >= 3 is the bar (about 1 false pass expected at t 3 by chance
under heavy correlation; reported). Passes are then checked for overlap with USTEC IBS (daily return correlation).
Batch 16 result (for the record): 1 PASS of 70 (US30 %b, t 3.72, 37 trades); about 1 false pass is expected by chance.

## Batch 17 (written 2026-11-27 01:53 UTC, before any run)
A. FX swing (min lot 0.01 = 1,000 units, fits $1,000): EURUSD GBPUSD USDJPY AUDUSD USDCAD USDCHF, Yahoo daily closes 2003 on
   (Yahoo FX highs/lows unreliable, so close-only rules): R1 rsi2, R2 cumrsi, R6 low10_3d (no SMA200 filter version too:
   R6n), R7 low5_2d, and the mirror SHORT side of R1 (RSI2 > 90 below SMA200, cover close < SMA5). Cost 1.2 bp.
   IS 2003-2012, judged 2013 on. Same PASS bar as batch 16.
B. Stock swing on the 30 stocks (stock CFDs, swap-free per Hazza, 3 bp): S1 Connors: up to 3 positions, buy at the close
   names with RSI2 < 5 above SMA200 (lowest RSI2 first), sell close > SMA5; S2 weekly reversal (Lehmann 1990): every Friday
   close buy the 3 worst 5-day returns, hold to next Friday close. $1,000 split in 3. IS 2010-2018, judged 2019 on.
   Placebo: same number of random names on the same days and holding periods.
C. Volatility-managed index (Moreira & Muir 2017), US500 and USTEC: V1 hold only when 20-day realized vol < its trailing
   252-day median; V2 hold only when 20-day vol < 20% annualized. Judged by Sharpe vs hold and t of the difference.
D. US mean-reversion ensemble at min lots: R1 + R6 + R9 on US500 (0.14) and USTEC (0.05), summed $ P&L (each runs on its
   own lot). Judged t on the summed daily $ P&L, 2013 on; placebo = each component's signal shifted independently.
Batch 17 results (record): FX swing 0 of 36; vol filter V2 (hold only when 20-day vol < 20%) PASSES on US500 (t 3.69) and USTEC (t 3.61) but earns less than holding (excess t -0.9/-1.6): a drawdown cutter; ensemble t 3.72 but -$543 drop since 2024 at min lots; Connors stock swing t 2.66 (placebo 96%); weekly reversal t 3.13 placebo 83% (fail).

## Batch 18 (written 2026-11-27 01:55 UTC, before any run)
A. Vol filter V2 confirmation on US30 and US2000 (same 20% threshold), judged 2013 on. Confirmation needs t >= 2.5 and Sharpe > hold on both.
B. VIX term structure (Simon & Campasano 2014 style): hold US500 / USTEC only when VIX close < VIX3M close (contango). Data 2006 on, IS 2006-2012.
C. Month-end pension rebalancing (Harvey, Mazzoleni, Melone 2025): long US500 / USTEC over the last 5 trading days of the month only
   when SPY's month-to-date return (to 6 trading days before month end) is below TLT's by more than 2 points.
D. BTC weekend fade ("CME gap"): if BTC's Saturday+Sunday move is beyond +-3%, trade the opposite way Monday open -> Monday close (UTC days).
Same PASS bar as batch 16.
Batch 18 results (record): vol filter confirmed on US30 (t 3.42) but not US2000 (t -0.13); VIX contango t 3.40/3.21 but placebo 89%/54% (fail);
month-end rebalancing t 2.85/2.51, placebo 99%/95%, 4% in market (fail on t); BTC weekend fade fail.

## Batch 19 (written 2026-11-27 01:55 UTC, before any run): crypto time-series momentum (Liu & Tsyvinski 2021, RFS)
BTC and ETH, UTC daily closes, rebalanced each Monday 00:00 UTC: hold the coin for the next 7 days if its past L-day return > 0,
else flat. L = 7 (primary), 14, 28 (reported). IS before 2020, judged 2020 on. Costs BTC 1.5 bp, ETH 3 bp. Same PASS bar.

## Batch 20 (written 2026-11-27 01:57 UTC, before any run): every standard indicator / signal, standard settings
Signals (long entries at the close, standard textbook settings, no tuning):
 Oscillators: RSI14 cross up 30; RSI14 cross up 50; Stochastic 14,3 %K cross %D below 20; StochRSI 14 cross up 0.2; Williams %R 14
 cross up -80; CCI 20 cross up -100; ROC 10 cross up 0; Momentum 10 cross up 0; Ultimate Osc (7,14,28) < 30; CMO 14 < -50;
 MACD 12,26,9 cross up signal; MACD histogram turns up below 0; PPO 12,26 cross up 0; TRIX 15 cross up 0; Awesome Osc cross up 0.
 Trend: SMA50 x SMA200 golden cross; EMA12 x EMA26; close x SMA20; close x SMA50; close x SMA200; ADX14 > 25 with +DI x -DI;
 Parabolic SAR (0.02, 0.2) flip up; Supertrend 10,3 flip up; Ichimoku tenkan 9 x kijun 26 above the cloud; Aroon 25 up x down;
 Donchian 20 breakout; Keltner 20,2xATR10 upper break; Heikin-Ashi first green after 2 red; Vortex 14 +VI x -VI.
 Volatility: close back above the lower Bollinger 20,2; Bollinger squeeze breakout (width at 120-day low, close > upper);
 Keltner lower touch; range > 2x ATR14 down day; NR7 day.
 Volume (from SPY/QQQ/DIA/BTC volume): OBV x its SMA20; Chaikin Money Flow 20 x 0; A/D line x its SMA20; MFI 14 < 20;
 down day with volume > 2x its 20-day mean; Force index 13 x 0.
 Candles: bullish engulfing; hammer; morning star; piercing line; three white soldiers; doji after 3 down days; bullish harami;
 inside bar; key reversal (low < prior low, close > prior close); three black crows (contrarian).
Markets: US500, USTEC, US30 (2000-2026, judged 2013 on), BTC (judged 2020 on). Exits: hold 1 day, hold 3 days (fixed).
Swap-free costs as batch 16. About 50 x 4 x 2 = 400 tests.
MULTIPLE-TESTING GUARD: per market and exit, 300 random entry sets with the same entry count as each signal give a
"max-t over the whole family" distribution (each random draw = one random signal for each of the ~50 slots, maximum t taken).
PASS needs: IS mean > 0, judged t >= 3, judged t above the 95th percentile of that family max, 2x cost positive, both halves > 0.

## Batch 22 (written 2026-11-28 01:43 UTC, before any run): Supertrend on its own (stop-and-reverse)
Already tested: Supertrend 10/3 always-in on daily US500/USTEC/gold/EURUSD (batches 1-2, 7: FAIL) and its flip as a 1/3-day entry
(batch 20: FAIL). Now the full standalone grid: ATR 7/10/14 x multiplier 2/3 (6 variants), position = Supertrend direction,
long-only (long/flat) and long/short. Signals on the close, filled at that close.
Daily: USTEC (QQQ), US500 (SPY), US30 (DIA) 2000-2026, IS before 2013, judged 2013 on, pre-2024 check = 2013-2023;
BTC, ETH (2014/2017 on), judged 2020 on; XAUUSD (GC=F) 2000 on, judged 2013 on (min lot 3.7x a $1,000 account: reported only).
Intraday: 1-hour bars built from the repo's 5-min QQQ/SPY 2016-2026 (all hours in the store), IS 2016-2020, judged 2021 on,
pre-2024 check 2021-2023. Swap-free costs (USTEC 0.9 bp, US500 1.3, US30 1.5, BTC 1.5, ETH 3, gold 1.5).
Robustness rule (no picking the best variant): a market/mode passes only if at least 4 of the 6 variants have IS mean > 0,
judged t >= 3, 2x cost t > 0, and judged Sharpe above buy-and-hold; and the pre-2024 slice is positive for those variants.

## Batch 23 (written 2026-11-28 01:55 UTC, before any run): low-risk daily candidates for a $3,000 account
Sizes: normal minimum lots only (USTEC 0.05 ~$1,250, US500 0.14 ~$950, BTC 0.01 ~$630). Target: worst drop < $300 (10% of $3,000).
Daily bars (QQQ/SPY 2000 on, BTC 2014 on), close fills (CFD after-close), swap-free costs. Judged 2013-2023 (BTC 2020-2023) as the
pre-2024 out-of-sample check, plus 2024-now reported; time-shift placebo 200 (random timing). PASS bar as batch 16 (t >= 3 judged
2013-now, placebo >= 95%, 2x cost > 0, both halves > 0, IS > 0) AND positive in 2013-2023 alone.
New single rules:
 F1 IBS + calm: USTEC IBS at the close, but only take entries while 20-day vol < 20%.
 F2 IBS + trend: USTEC IBS entries only while close > SMA200.
 F3 Williams + trend: BTC Williams breakout only on days BTC's prior close > its SMA50.
 F4 BTC-led USTEC: buy USTEC at the close after a BTC UTC day down > 5% (BTC day ends 19:00 NY, before the decision at the
    next 16:00 NY close... decision uses BTC's PREVIOUS completed UTC day), sell next close.
 F5 IBS overnight only: IBS < 0.2 -> buy at the close, sell at the next 9:30 open (Yahoo open), every signal.
 F6 US500 + USTEC IBS pair: IBS rule on both, each at its min lot (portfolio of two).
Portfolios (fixed weights = one min lot each, no optimisation): P1 USTEC IBS + BTC Williams; P2 P1 + BTC Donchian 20/10;
 P3 P1 + calm USTEC; P4 USTEC IBS + BTC Williams + BTC Donchian + calm USTEC. Reported 2016-now (BTC from 2016), worst drop in $.

## Batch 24 (written 2026-11-28 01:59 UTC, before any run): new edges, not combos
A. Williams breakout (k 0.6, buy-stop at open + 0.6 x prior range, out at the close) on other cryptos Exness lists: ETH, LTC, XRP,
   BCH, ADA, SOL, DOGE, LINK, DOT, BNB (Yahoo daily, from listing; judged 2022 on so each coin has >= 2 years judged).
   Cost 5 bp (alt spreads not measured; 10 bp stress). PASS per coin as batch 16 + random-day placebo >= 95%.
B. Williams breakout on the 30 stocks (stock CFDs, 3 bp), pooled: each day every stock whose high reaches open + 0.6 x prior range
   is bought at that level and sold at the close, $333 each; judged 2019 on. Placebo: same count of random stock-days open->close.
C. Index pair (market-neutral): ratio QQQ/SPY, 20-day z-score of log ratio < -2 -> long USTEC 0.05 / short US500 0.14,
   > +2 -> the reverse; exit when z crosses 0. Judged 2013 on. Costs both legs.
D. Crypto pair: ratio ETH/BTC, same z rules, ETH ~$1,000 vs BTC 0.01 (~$630) legs scaled to equal $; judged 2020 on.
Batch 24 results (record): Williams passes on XRP (t 3.28), BCH (3.85), LINK (3.71); every coin positive in-sample; stocks Williams t 1.50; both pairs fail.
## Batch 24b (written 2026-11-28 02:00 UTC, before running): crypto Williams BASKET, all 11 coins (BTC + the 10 above), no picking
Equal $ per coin ($250 each, so at most $2,750 exposure on a $3,000 account), same rule, 5 bp (BTC 1.5 bp), judged 2022 on,
pre-2024 slice 2022-2023 must be positive, random-day placebo per coin. Report $/yr, worst drop, correlation with USTEC IBS.
Batch 24b result: basket t 3.69 judged, placebo 100%, ~$1,100/yr since 2024 at $250/coin, worst drop -$681 (2022-23): too big at that size.
## Batch 24c (written 2026-11-28 02:01 UTC, before running): Williams long and IBS-at-close on other commodities
Silver (SI=F), natural gas (NG=F), copper (HG=F), platinum (PL=F), Yahoo daily 2000 on, judged 2013 on, 5 bp (10 bp stress).
Same PASS bar; Exness min lots for these not verified.
Batch 24c result: copper/silver passes were Yahoo futures-bar artifacts (hourly-built bars t 0.60 / 1.06); NG, PL, IBS on commodities fail.
## Batch 25 (written 2026-11-28 06:40 UTC, before running): free "terminal-style" data as on/off filters on the candidates
Why: Hazza asked whether Bloomberg-type data helps. FRED/CBOE/Coinmetrics/Binance fetches were refused in this session; free proxies
on Yahoo are used instead. Each filter is a gate known at the prior close, fixed thresholds, no tuning:
 G1 yield curve 10y - 3m (^TNX - ^IRX) > 0          G2 credit: HYG/IEF above its 50-day average (from 2008)
 G3 VIX below VIX3M (contango)                       G4 dollar: DX-Y.NYB below its 50-day average
 G5 MOVE (bond vol) below its 252-day median         G6 SKEW below its 252-day median
 G7 risk appetite: XLY/XLP above its 50-day average  G8 (crypto only) QQQ above its 50-day average
Applied: USTEC IBS and US500 IBS gate the ENTRY (G1-G7); BTC Williams and the coin basket gate each day's trade (G1-G8; day trades,
so exact). Calm USTEC is already a vol filter and is not re-filtered.
A filter HELPS only if all: (1) pre-2024 (2013-23; BTC 2016-23; basket 2022-23) profit per $ of worst drop rises >= 20% and
profit keeps >= 60%; (2) that ratio beats >= 95% of 200 random gates with the same on-fraction (rotated gate); (3) 2024-now the
ratio is also higher than without it and profit > 0. Selection uses pre-2024 only. Report yearly $ and worst drop before/after.
Batch 25 result (record): 0 of 31 filter tests HELP. Most cut profit more than drawdown and fail the random-gate placebo. Closest: coin basket + bond-vol-low (pre-2024 placebo 96%, but 2024-now worst drop got worse -254 vs -189) -> fails rule 3. Full table research/b25.log.
## Batch 26 (written 2026-11-28 08:10 UTC, before running): hourly and 15-minute rules, full Exness spreads, minimum lots
Data: QQQ/SPY 5-min regular hours 2016-01..2026-11 (USTEC/US500 proxies), repo fx1h hourly BTC/ETH 2024-11..2026-11, gold GC=F 2024-07..2026-11.
Costs per round trip: USTEC 1.0 bp (2.0 bp for entries in the first 30 min), US500 1.3 bp (2.0 bp at the open), BTC 1.5, ETH 3, gold 1.5.
Size: USTEC 0.05 ($1,250), US500 0.14 ($950), BTC 0.01 ($630), ETH $1,000, gold 0.01 lot = 1 oz ($3,600).
Index rules: R1 opening-range breakout (9:30-10:00 range), only in the daily trend (prior close vs SMA50), stop at the other side, out 15:55.
 R2 RSI(2) mean reversion on 15m and on 60m: RSI2 < 10 with daily close > SMA200 -> long (RSI2 > 90 below SMA200 -> short); out at RSI2 70/30,
    stop 2 x ATR14, or the last bar of the day. R3 EMA20/EMA50 trend on 15m and 60m, only in the daily SMA50 direction, stop 2 x ATR14,
    exit on the cross back (may hold overnight, swap-free). R4 gap fade: |open gap| > 0.5% -> fade at 9:30, target prior close, stop one gap
    away, out 15:55. R5 intraday momentum (Gao et al. 2018): at 15:30 trade in the sign of prior close -> 10:00 return, out 15:55.
Crypto/gold rules (1h): C1 London breakout (00-08 UTC range, break 08-20 UTC in the daily SMA50 direction, stop other side, out 23:00 UTC),
 C2 = R2 on 60m (daily SMA50 filter, 12-bar max hold), C3 = R3 on 60m.
PASS: develop period (indices 2016-2022; crypto/gold first year) positive with t >= 1.5; confirm period (2023-on; last year) positive with t >= 2;
whole-period t >= 3 (family guard); 2x costs still positive; beats >= 95% of 200 placebos (same trades at random times, same side and length).
Batch 26 result (record): 0 of 23 pass. Near miss: ETH London breakout (t 2.98, placebo 100%, 2nd-year t 1.80) -> paper as WATCH ONLY (eth_london_paper.py). Every index intraday rule fails at full spreads; RSI2 intraday loses in every period. Full table research/b26.log.
## Batch 27 (2026-11-28 08:30 UTC): batch-26 near misses re-run UNCHANGED on longer hourly history (Hazza asked for pre-2024)
Data: Binance ETHUSDT 1h 2017-08..2026-10; gold via Binance PAXGUSDT 1h 2020-08..2026-10 (gold-backed token; Dukascopy XAUUSD was unreachable).
Result: ETH London breakout passes the batch-26 bar on the long data: 2017-23 t 3.58, placebo 100%; 2024-now t 2.00; all t 4.10; 2x cost +.
Worst drop -$672 at $1,000 (Nov 2021-Apr 2022): too big for the $3k low-risk budget at that size. Gold London breakout and gold EMA trend
lose 2020-23 (t -9.06 and -3.03) on PAXG: fail.
## Batch 28 (written 2026-11-28 10:30 UTC, before running): scorecard + candle brain v2 + oil brain v2, one WORTHY bar
Bar = trader-lab/judge.py (committed 1913b56 before this run): before 2024 net > 0 and t >= 2; 2024-now net > 0 and t >= 1; whole t >= 3;
2x costs net > 0; beats >= 95% of 200 placebos (rotated signal, or random days for day trades); worst drop >= -$300 at today's min lot.
Distinct = daily P&L correlation <= 0.5 with every higher-ranked worthy candidate. Judged from 2013 (indices, gold, oil, FX), 2016 (BTC), 2018 (ETH).
Sizes: USTEC $1,336, US500 $1,022, BTC $595, ETH $500 (0.3 lot), gold 1 oz $3,640, USOIL 0.01 lot $831 (USO proxy), EURUSD $1,097.
Costs bp: USTEC 0.9, US500 1.3, BTC 1.9, ETH 8 (unverified, between 3 and 15), gold 1.5, oil 6, EURUSD 1.2.
A. Scorecard of existing candidates: USTEC IBS, US500 IBS, BTC Williams, Calm USTEC, BTC Donchian 20/10, coin Williams basket ($100 x 10),
   ETH London breakout (hourly Binance, $500, 8 bp), ETH 7-day momentum (long when close > close 7 days ago).
B. Candle brain v2 (candles.py definitions; bullish reversal = hammer, dragonfly, bull engulfing, bull harami, piercing, tweezer bottom,
   morning star; bearish = mirrors). CB1 long: bullish reversal at a 10-day closing low while close > SMA200; exit first up close or 5 days.
   CB2 short (BTC, ETH, gold, oil, EURUSD): bearish reversal at a 10-day high while close < SMA200; exit first down close or 5 days.
   CB3 inside-day breakout: day t inside day t-1; on t+1 buy-stop at H_t if close_t > SMA50 (sell-stop at L_t if below, not on indices); out at the close.
   Markets: USTEC, US500, BTC, ETH, gold, oil, EURUSD.
C. Oil brain v2 (USOIL via USO, EIA weekly crude stocks released week end + 5 days, CFTC COT released Tuesday + 3 days):
   O1 IBS < 0.2 above SMA200 only while crude stocks are below their 5-year same-week average; exit first up close.
   O2 hedging pressure: weekly change in producer/merchant net > 0 -> long 5 days from release, < 0 -> short 5 days.
   O3 inventory surprise: weekly change minus 5-year same-week average change < 0 (bigger draw) -> long 5 days from release, > 0 -> short.
   O4 curve + trend: USO 60-day return > USL 60-day return (backwardation proxy) and USO > SMA50 -> long, else flat.
Batch 28 result (record): WORTHY = BTC Williams, USTEC IBS, US500 IBS (near-duplicate of USTEC IBS, corr 0.75), coin Williams basket (corr 0.33 with BTC Williams).
Fails: Calm USTEC (random 66%, 2024-now t 0.98), BTC Donchian (drop -$447), ETH 7-day momentum, ETH London breakout at $500/8 bp (drop -$392).
Candle brain v2: 0 of 19 (inside-day breakouts on BTC/ETH/gold strong before 2024, flat since). Oil brain v2: 0 of 4. EURUSD rules use Yahoo FX bars (bad opens).
## Batch 29 (written 2026-11-28 11:00 UTC, before running): more distinct families, same judge.py bar
 N1 ETH London breakout sized at 0.2 lot (~$330): the largest 0.1-lot step whose 2018-2023 worst drop is within -$300 (chosen on pre-2024 only).
 N2 BTC London breakout, Binance BTCUSDT 1h 2017-26, 0.01 lot ($595), 1.9 bp, judged 2018 on.
 N3 gold IBS < 0.2 above SMA200 (GLD), 1 oz, exit first up close.   N4 gold turn of month: long from the close before the last
 trading day of the month to the close of the 3rd trading day, 1 oz.   N5 gold Williams breakout on GLD daily bars (real ETF bars), 1 oz.
 N6 oil Williams breakout on USO daily bars, 0.01 lot.
Batch 29 result (record): N1 ETH London breakout at 0.2 lot WORTHY (worst -$259). N2 BTC London fails (whole t 2.70, drop -$337). Gold N3-N5 and oil N6 fail.
## Batch 30 (written 2026-11-28 11:15 UTC, before running): session breakouts on more coins and the US session
 P1 alt London breakout basket: XRP, LTC, BNB, ADA, LINK, BCH (Binance 1h), $100 each, 8 bp, same rule as the ETH London breakout; judged 2020 on.
 P2 BTC US-session breakout: range 00:00-12:59 UTC, entries 13:00-19:59 UTC in the daily SMA50 direction, stop other side, out 23:00 UTC; 0.01 lot.
 P3 ETH US-session breakout, same, 0.2 lot ($330), 8 bp.
 Then distinctness vs all worthy candidates (corr <= 0.5).
Batch 30 result (record): P1 alt London basket fails (2024-now -$484), P2 BTC US-session fails, P3 ETH US-session fails (before 2024 t 0.90).
Distinct WORTHY after batches 28-30: BTC Williams, USTEC IBS, coin Williams basket, ETH London breakout at 0.2 lot (US500 IBS worthy but corr 0.75 with USTEC IBS).
