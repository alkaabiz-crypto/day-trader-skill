# Paper day-trading trial: pre-registration

Written 2026-11-23, before the first trade. Nothing here changes during the trial. A changed
rule is a new trial with a new start date.

## Why a trial, not a strategy

The lab tested about 100 published day-trading rules on 30 years of daily, 3 years of hourly and
4 years of 5-minute data. None has a proven edge after costs (`RESEARCH.md`). This trial asks
one narrow question with real prices and no money: does the best remaining candidate make money,
after costs, in the days *after* it was chosen? The honest prior is "about zero": on 2022-2026
data its average trade nets about 0 bp at 2 bp of cost.

## The rule (fixed)

- **What:** the 15:30 New York reversal. Hedging-flow research (Baltussen, Da, Lammers &
  Martens 2021, JFE) finds end-of-day momentum in index futures; on 2022-2026 ETFs the
  *reverse* was the least bad variant, chosen on in-sample data only (pre-registered idea 4).
- **Signal:** the move from yesterday's 16:00 close to 15:30 today, measured on SPY (for US500),
  QQQ (for USTEC) and DIA (for US30). If the move is at least 1.0%, trade the other way.
- **Entry:** at 15:30 New York; no new entries after 15:35.
- **Stop:** 0.5% from the fill.
- **Exit:** flat by 15:55 New York (before the index CFD session break).
- **Size:** notional = $10 / 0.5% = $2,000, capped at the $1,000 budget, so $1,000 notional
  (max loss $5) and never leverage above 1:1.
- **Limits:** at most 3 trades a day and $30 risk a day. The largest moves come first.

## How it is recorded

- `paper.py tickets` posts each day's tickets at 15:31 New York. You place them by hand on an
  **Exness demo** account.
- `paper.py log` shadow-fills every ticket from 5-minute ETF bars at 2 bp round trip, every
  trading day, whether or not anyone trades. The 2 bp is a cautious guess; Exness spreads float,
  so check MT5 and change `cost_bps` before the first trade if yours differ.
- `paper.py record` stores your real demo results, for comparison.
- Journal: `paper/journal.csv`, committed daily.

## Pass bar (fixed)

After at least **20 trading days and 30 shadow trades**, all of:

1. net profit > $0 after costs
2. t-stat of per-trade net returns >= 2.0
3. max drawdown < $60 at this sizing
4. your demo results lag the shadow log by no more than 30%

**FAIL:** no live trading with this rule. The lab moves on to the next candidate, which gets
its own trial.

**PASS:** going live is your decision. Start at this size, keep these limits, and know that 30
trades is a small sample.

## Risks

- **CFDs carry leverage**, and Exness states most retail CFD accounts lose money. This trial
  uses 1:1 exposure.
- **Exness doesn't serve some countries** (for example the US). Check that yours is allowed.
- **Signals come from ETF prices.** The CFD can differ slightly, especially near the cash close.
- Research, not financial advice.

## Amendment 2026-11-24 (stricter only)

The bar also requires the shadow log to stay net positive if every round trip cost 5 bp instead of
the assumed 2 bp (`stress_cost_bps` in `config.json`). This is a stress figure for Exness's spread at
15:30–15:55, not a quoted Exness number. `paper.py report` also prints the cost at which the trial
breaks even. These trades pay no swap: every one is flat by 15:55 New York, before Exness's rollover.
Nothing else in the plan changed.

## Amendment 2026-11-24 (2), stricter only

`power.py` replayed these exact rules on 995 sessions (2022-11 to 2026-11). Trades on the same day
are about 0.93 correlated, so the per-trade t counts one bet two or three times. With zero true edge,
the bar would pass 11% of the time instead of about 2.5%.
- The bar now also needs **t >= 2 on daily P&L** (each trading day's total is one observation). With
  that check the false-pass rate is about 3%.
- The median trial takes about 38 trading days to reach 30 trades. The review is when both minimums
  are met, not on a fixed date.
- The same replay nets -1.33 bp a trade at 2 bp cost (t -1.68), so the honest prior is no edge.

Nothing else changed.
