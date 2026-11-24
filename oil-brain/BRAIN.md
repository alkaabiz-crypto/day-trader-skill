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
- Literature notes: see "Academic evidence" (filled from the literature review).

## Academic evidence

_Pending the literature review of 2026-11-24._

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

## Candidates for forward paper testing

1. TSMOM on USO, monthly rebalance, vol-scaled to 20% a year, lookback 126 days
   (the most robust: positive without crashes too, but t only 1.08). Crisis-alpha profile.
2. Carry + momentum average.
Neither is a 1-3 day trading edge.

## Idea queue (top first)

1. Literature review results: add the top hypotheses with precise rules.
2. ~~Check momentum candidates for crash dependence~~ done (study 3): crash-driven.
3. ~~EIA 10:30 Wednesday reaction~~ done (study 4): nothing. Still open: settlement 14:30 effect.
4. Brent-WTI spread (BNO vs USO) mean reversion.
5. Crack spread (RB + HO vs CL) as a signal for refiners / oil.
6. CFTC positioning (hedging pressure) if a free data host can be reached.
