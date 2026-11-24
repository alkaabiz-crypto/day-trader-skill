# Oil brain: what we know about the US oil market, and what we tested

A living memory. Every run reads this first and adds to it. Facts carry a source; results carry
the date, the script and the verdict. Nothing is deleted: a failed idea stays, so it is not
retried by accident.

## Rules of the lab (fixed 2026-11-24)

- **Splits:** IS up to 2013, OOS 2014-2019, HOLDOUT 2020 on. Parameters are chosen on IS or
  taken from the paper. HOLDOUT is never tuned on.
- **PASS** (`engine.py`): OOS and HOLDOUT Sharpe > 0.3 after costs, post-2014 Sharpe above the
  benchmark, post-2014 t >= 2, placebo p <= 0.05 (500 time-shifted copies of the same
  positions), still positive at 2x costs.
- **Costs:** 5 bp per unit of turnover on ETFs (spread + slippage); double for the stress test.
- **A PASS is a candidate, not proof.** It must also hold on most neighbouring parameters and
  then survive a forward paper test (real dates after the test was written). Count how many
  rules were tried: with ~20 tries, one t = 2 result is expected by luck alone.
- **Instruments:** USO (real ETF; its returns include the roll cost of the front month). Not
  CL=F: Yahoo's continuous front-month series jumps at every roll and fakes returns.
- Paper money only. Research, not financial advice.

## How the market works (mechanisms)

- **Roll and curve shape.** USO holds the front WTI future and rolls monthly. In contango
  (later months dearer) each roll loses money; in backwardation it gains. USO fell 74% from
  2006 to 2026 while spot WTI rose: mostly roll drag. USL spreads over 12 months, so
  USO minus USL return is a free proxy for the curve shape.
- **Weekly calendar.** API inventory estimate Tuesday 16:30 ET; EIA Weekly Petroleum Status
  Report Wednesday 10:30 ET; Baker Hughes rig count Friday 13:00 ET; NYMEX settlement
  14:28-14:30 ET; CFTC Commitments of Traders Friday 15:30 ET (Tuesday data).
- **Holidays thin the market:** Thanksgiving (closed Thursday, early close Friday).
- Literature: see "Academic evidence" below.

## Academic evidence

From a literature review on 2026-11-24 (web search summaries of abstracts; paper tables not
read directly because ssrn.com / nber.org were unreachable, so treat unlisted numbers as
unverified). Grades: **A** replicated and alive after 2010; **B** published, thin or mixed;
**C** weak, decayed or not tradable.

| topic | key papers | what they say | grade |
|---|---|---|---|
| Curve shape / carry | Szymanowska et al. 2014 JF; Gorton, Hayashi & Rouwenhorst 2013 RoF; Koijen et al. 2018 JFE "Carry"; Erb & Harvey 2006 FAJ | Backwardation (low inventories) earns a premium, mostly **across** commodities. For crude alone, "long when backwardated" is weak (Peterson 2015: mostly random) | A cross-section, B-/C single oil |
| Basis-momentum | Boons & Porras Prado 2019 JF | 12m return of nearby minus 2nd contract predicts returns, beats basis and momentum (cross-section) | A- cross-section |
| Time-series momentum | Moskowitz, Ooi & Pedersen 2012 JFE; Hurst, Ooi & Pedersen 2017 | 12m sign, vol-scaled, works across 58 futures; century of evidence Sharpe ~0.77 for a diversified portfolio. Whipsaw years 2009-2013 | A portfolio, noisy for oil alone |
| Cross-sectional momentum | Miffre & Rallis 2007 JBF; Fuertes, Miffre & Rallis 2010 | Long winners / short losers across 20-30 commodities | B+, needs a broad universe |
| Hedging pressure (COT) | De Roon et al. 2000 JF; Kang, Rouwenhorst & Tang 2020 JF; Maréchal 2023 | Short-term changes in hedgers' positions earn a liquidity premium (prices rise after hedgers buy); the level premium does not survive | B+ for changes; C for levels in crude |
| EIA report | Halova, Kurov & Kucher 2014; Ye & Karali 2016; Geman & Li; Rousse & Sévi | A surprise build lowers prices within minutes; overshoot then partial reversal; informed trading before 10:30 | A direction (needs consensus data) |
| EIA-day intraday momentum | Wen, Indriawan, Lien & Xu 2023 Energy J; Wen et al. 2021 | 10:30-11:00 return predicts the last half hour on EIA days (USO) | B |
| Goldman roll front-running | Mou 2011 | 3.6%/yr transferred from index rolls (pre-2010); now arbitraged | C |
| USO roll days | Bessembinder et al. 2016 JFE | ~30 bp cost per roll; deeper books and narrower spreads on roll days; no predatory front-running | B (fact) |
| Seasonality / weekday | CXO; JP Morgan 2015; Auer 2014 | Mar-May strong, Nov-Dec weak, but too noisy; seasonality factor failed since 2010; Monday weak, not significant | C |
| Oil -> stocks | Driesprong et al. 2008 JFE; Ready 2018; Thorbecke 2019 | Lagged negative effect pre-2008; decayed; shale era flipped the sign at times | C |
| OPEC cuts | Demirer & Kutan 2010; IMF 2022 | Drift after cut announcements (1983-2008); later: ~3% jump that fades | B- |
| Variance risk premium | Trolle & Schwartz 2010 | Implied oil vol exceeds realized on average; needs options | B, not tradable here |
| Short-term reversal | mixed (Fin. Res. Letters 2020) | No reliable reversal profit across 29 commodities 1979-2017 | C |
| Liquidity / costs | Chung, Van Ness & Van Ness; Chan et al. (1990s) | Spreads U-shaped by time of day, widest after the open | practical rule: skip the first 5-15 minutes |

**What the literature implies for us:** the robust oil premia (carry, momentum, basis-momentum,
hedging pressure) are slow (monthly) and strongest in a **diversified cross-section** of
commodities, not in oil alone. Short-horizon effects (EIA, OPEC, reversal) are either about
information we do not have (consensus forecasts) or too small after costs.

## Results log

### 2026-11-24, study 1 (`study1.py`): academic signals, daily data. 0 PASS of 9

| rule | OOS | HOLDOUT | post-2014 Sharpe (bench) | t | placebo p | verdict |
|---|---|---|---|---|---|---|
| H1 SPY only after oil fell last month (Driesprong et al. 2008) | 1.09 | 0.56 | 0.74 (0.80) | 2.66 | 0.21 | FAIL: just market exposure |
| H2 carry long/short, USO-USL 21d | 0.26 | 0.73 | 0.54 (0.05) | 1.92 | 0.01 | FAIL (near miss) |
| H2b carry long/flat | -0.08 | 0.83 | 0.48 | 1.74 | 0.01 | FAIL |
| H3 TSMOM 12m vol-scaled (Moskowitz et al. 2012) | 0.41 | 0.31 | 0.35 | 1.26 | 0.13 | FAIL |
| H3b TSMOM 1m vol-scaled | 0.42 | 0.52 | 0.47 | 1.70 | 0.05 | FAIL (t only) |
| H4 long 1 day after a -2 sd USO day | 0.13 | -0.22 | -0.12 | -0.41 | 0.52 | FAIL |
| H5 long USO on Wednesdays (EIA day) | -0.17 | -0.47 | -0.34 | -1.21 | 0.61 | FAIL |
| H6 long USO 5 days after OVX +20% | -0.50 | -0.38 | -0.34 | -1.23 | 0.89 | FAIL |
| H7 XLE catches up with oil next day | -0.40 | 0.38 | 0.08 (0.36) | 0.28 | 0.19 | FAIL |

### 2026-11-24, study 2 (`study2.py`): robustness grid for the near misses. Chosen after study 1

- **Carry is not robust:** lookbacks 21 and 126 days are close (t 1.9), 10 and 63 days are
  zero or negative. Not a candidate on its own.
- **Monthly-rebalanced time-series momentum is the first candidate:** all 5 lookbacks have a
  positive post-2014 Sharpe (0.33 to 0.70); 10, 42 and 126 days PASS every gate, 21 days
  misses only on t (1.70), 63 days fails. Weekly rebalancing is worse (more cost, more noise).
- **Carry + momentum average (21d each) PASSES:** post-2014 Sharpe 0.60, t 2.15, placebo 0.01.
- **Caveats:** IS (2008-2013) Sharpe is negative for most momentum lookbacks; post-2014
  includes two huge oil crashes (2014-15, 2020) where trend rules shine. 23 rules tried so
  far. Treat as candidates for a forward paper test, not as an edge.

### 2026-11-24, study 3 (`study3.py`): is momentum just the crashes? Mostly yes

Post-2014 Sharpe with the two crash windows removed (2014-07..2016-02, 2020-01-15..2020-06):

| rule | post-2014 | without crashes | t without | long leg | short leg | years positive |
|---|---|---|---|---|---|---|
| TSMOM 10d | 0.58 | 0.16 | 0.51 | 0.35 | 0.47 | 9/13 |
| TSMOM 21d | 0.47 | 0.13 | 0.41 | 0.25 | 0.41 | 10/13 |
| TSMOM 42d | 0.56 | 0.11 | 0.36 | 0.32 | 0.47 | 9/13 |
| TSMOM 63d | 0.33 | -0.01 | -0.02 | 0.14 | 0.32 | 6/13 |
| TSMOM 126d | 0.70 | 0.33 | 1.08 | 0.41 | 0.56 | 10/13 |
| carry + TSMOM | 0.60 | 0.17 | 0.54 | 0.51 | 0.37 | 8/13 |

TSMOM 42d by year: 2014 +45%, 2015 +39%, 2016 -4%, 2017 +21%, 2018 +21%, 2019 -17%, 2020 +48%,
2021 +4%, 2022 +13%, 2023 -11%, 2024 -21%, 2025 +13%, 2026 +20% (to Nov 23).

**Reading:** oil momentum is "crisis alpha": most of the profit comes from riding the big
crashes short. In normal years it is close to zero (t < 1.1). That matches the trend-following
literature. Useful as insurance inside a portfolio; not a steady edge for short-term trading.

### 2026-11-24, study 4 (`study4.py`): EIA Wednesday 10:30 reaction, hourly USO. 0 PASS of 4

~150 Wednesdays (2023-12 to 2026-11), 5 bp round trip. Every |t| < 2:
following the 10:30-11:30 move to the close: -6.2 bp (t -0.59); fading it: -3.8 bp (t -0.36);
only big reactions (> 0.75%): +10.8 bp (t 0.40, n 42); drifting into the report
(Tue close -> Wed 10:30): -6.6 bp (t -0.39). Other weekdays at the same hour look the same, so
the report adds noise, not a pattern. Matches the lab's earlier hourly finding
(skipping Wednesdays did not help). CL=F hourly bars start on the hour, not at :30, so the
futures test was not valid; USO answers the question.

### 2026-11-24, study 5 (`study5.py`): literature's top intraday and curve ideas. 0 PASS of 9

Intraday momentum into the last half hour (Wen et al. 2021, 2023), hourly USO 2023-12 to 2026-11:

| rule | n | mean at 2 bp | t | win |
|---|---|---|---|---|
| EIA Wed: sign(10:30-11:30) -> 15:30-16:00 | 146 | -3.5 bp | -2.00 | 42% |
| same, only big first moves | 79 | -3.0 bp | -1.26 | 43% |
| control: other days | 577 | -1.6 bp | -1.36 | 41% |
| non-EIA: sign(prev close -> 10:30) -> 15:30-16:00 | 577 | -3.0 bp | -2.63 | 39% |
| control: Wednesdays | 146 | -0.4 bp | -0.22 | 49% |

The published effect is **absent** after publication: gross returns are about zero to slightly
negative, so costs make it a loser. Do not retry with other bar times (that would be a search).

Basis-momentum proxy (USO minus USL return), month-end, 2009 on:
252d long/short: OOS 0.42, HOLDOUT 0.37, post-2014 Sharpe 0.39, t 1.39, placebo 0.05, FAIL;
252d long/flat: t 1.31, FAIL; 63d long/short: t 1.18, FAIL; 63d long/flat: t 1.11, FAIL.
Positive like the paper says, but for oil alone too weak to clear t >= 2.

### 2026-11-24, study 6 (`study6.py`): diversified commodity trend and carry. 0 PASS of 4

12 commodity ETFs (USO, UNG, UGA, GLD, SLV, DBB, DBA, CORN, WEAT, SOYB, PALL, PPLT), equal risk,
month-end, 5 bp. Benchmark DBC (post-2014 Sharpe 0.22).

| rule | IS | OOS | HOLDOUT | post-2014 | t | placebo p | max DD | verdict |
|---|---|---|---|---|---|---|---|---|
| P1 trend blend 1/3/12m (Hurst et al.) | 0.07 | -0.06 | 0.78 | 0.42 | 1.49 | 0.10 | -11% | FAIL |
| P2 trend 12m (Moskowitz et al.) | 0.12 | 0.11 | 0.56 | 0.35 | 1.26 | 0.15 | -17% | FAIL |
| P3 carry, oil and gas only | 0.65 | 0.43 | 0.31 | 0.37 | 1.32 | 0.09 | -6% | FAIL |
| P4 trend blend + carry | 0.22 | -0.08 | 0.79 | 0.41 | 1.48 | 0.08 | -12% | FAIL |

P1 by year: losing or flat 2014-2019, strong 2020-2022, mixed since. Matches the literature's
post-2009 trend whipsaw. Carry is the most stable (positive in all three periods, smallest
drawdown) but only two ETF pairs exist, so it is thin. At month-end Nov 2026 P1 was short
almost everything except a small long in USO.

### 2026-11-24, study 7 (`study7.py`): extreme days, Brent-WTI, crack spread. 0 PASS of 7

| rule | IS | OOS | HOLDOUT | post-2014 | t | placebo p | verdict |
|---|---|---|---|---|---|---|---|
| X1 fade a +/-2.5 sd USO day, hold 1d | -0.33 | 0.40 | -0.67 | -0.35 | -1.24 | 0.78 | FAIL |
| X2 same, hold 3d | -0.25 | -0.36 | -0.53 | -0.45 | -1.63 | 0.92 | FAIL |
| X3 same, hold 5d | -0.08 | -0.74 | -0.70 | -0.70 | -2.49 | 0.99 | FAIL |
| X4 fade, hold 3d, OVX high | 0.04 | -0.01 | -0.70 | -0.46 | -1.64 | 0.94 | FAIL |
| X5 fade, hold 3d, OVX low | -0.38 | -0.72 | 0.45 | -0.08 | -0.28 | 0.60 | FAIL |
| S1 Brent-WTI z>2 reversion | -0.65 | 0.42 | -0.47 | -0.11 | -0.38 | 0.38 | FAIL |
| C1 crack spread z>1, long USO | 0.12 | -0.38 | 0.30 | 0.04 | 0.15 | 0.38 | FAIL |

**Fading big oil days loses, and the loss grows with the holding period** (t -2.49 at 5 days):
after a shock, oil tends to keep going, not snap back. This contradicts the reversal idea and
fits short-term momentum. The flipped rule ("follow a +/-2.5 sd day for 5 days") was NOT
pre-registered and its IS was flat (+0.08), so it is only a hypothesis for a forward test.

## Candidates for forward paper testing

1. TSMOM on USO, monthly rebalance, vol-scaled to 20% a year, lookback 126 days
   (the most robust: positive without crashes too, but t only 1.08). Crisis-alpha profile.
2. Carry + momentum average.
Neither is a 1-3 day trading edge.

## Idea queue (top first)

1. Forward-test "follow a +/-2.5 sd USO day for 5 days" from 2026-11-24 (not pre-registered;
   only forward results count). Log each event in oil-brain/forward.csv.
2. CFTC COT liquidity premium (Kang, Rouwenhorst & Tang 2020): weekly change in producer/merchant
   net position in crude; needs www.cftc.gov (ask the user to allow the host).
3. ~~Diversified commodity trend + carry~~ done (study 6): FAIL, whipsaw 2014-2019.
4. ~~Extreme-day fades, Brent-WTI, crack spread~~ done (study 7): FAIL.
5. Energy equities: XLE/XOP vs oil (beta-hedged residual momentum), daily.
6. OPEC cut drift: needs a hand-built list of meeting dates.
7. ~~Check momentum candidates for crash dependence~~ done (study 3): crash-driven.
8. ~~EIA 10:30 Wednesday reaction~~ done (study 4); ~~EIA-day intraday momentum~~ done (study 5).
9. ~~Basis-momentum on USO/USL~~ done (study 5): positive, not significant.

**Rules tried so far: 47** (study 1: 9, study 2: 14, study 4: 4, study 5: 9, study 6: 4,
study 7: 7; study 3 re-scored old rules). At this count, a couple of t = 2 results are expected by chance alone.
