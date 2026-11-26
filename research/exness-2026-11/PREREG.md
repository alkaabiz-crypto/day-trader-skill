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
