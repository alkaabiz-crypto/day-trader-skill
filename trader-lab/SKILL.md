---
name: trader-lab
description: >-
  Strategy Lab. Tests day-trading strategies from academic studies and famous
  setups on real 5-minute bars, after costs, and turns the ones that survive
  into one live signal per stock. Strategies: the 5-minute opening-range
  breakout (Zarattini & Aziz 2023), the classic opening-range breakout
  (Crabel), the "noise area" intraday momentum band with a VWAP trailing stop
  (Zarattini, Aziz & Barbon 2024), market intraday momentum, first half hour
  predicts the last (Gao, Han, Li & Zhou 2018, JFE), the VWAP trend, the
  overnight gap fade or follow-through, and the opening-range breakout on
  "stocks in play" by relative volume (Zarattini, Barbon & Aziz 2024). Picks each strategy's variant on older
  data only, keeps it only if it still makes money on the newest 30% of the
  dates it never saw, and weights the survivors into a score from -1 to +1.
  The price store grows every run, past Yahoo's 60-day limit. Use when the
  user says "what's the best strategy", "backtest the strategies", "which
  setups work", "give me a signal", "strong signals", "research strategies",
  "evolve the strategy", "run the lab", or at the start of a trading day
  before /trader-scanner.
argument-hint: "[fetch | backtest | signal] [--symbols SPY,QQQ]"
---

# trader-lab

The lab answers one question honestly: of the day-trading rules that
academics and famous traders publish, which ones made money on recent data
after costs, and what do the survivors say right now? It is research, not a
promise. Most day traders lose money: of the Brazilian individuals who day
traded mini-index futures for 300+ days, 97% lost money (Chague, De-Losso &
Giovannetti 2020). The lab is built to stop you from fooling yourself.

`${CLAUDE_SKILL_DIR}` below is this skill's folder (where this SKILL.md lives).

```bash
python3 "${CLAUDE_SKILL_DIR}/lab.py" fetch                      # 60 days of 5-min bars, merged into the store
python3 "${CLAUDE_SKILL_DIR}/lab.py" backtest --write           # every strategy and variant, IS vs OOS
python3 "${CLAUDE_SKILL_DIR}/lab.py" signal                     # today's score per stock from the survivors
python3 "${CLAUDE_SKILL_DIR}/lab.py" backtest --only orb5,noise --cost 5
python3 "${CLAUDE_SKILL_DIR}/lab.py" signal --symbols SPY,QQQ,TSLA --json
```

Two more engines test rules on far more history:

```bash
python3 "${CLAUDE_SKILL_DIR}/daily.py" fetch                    # daily bars back to each listing (SPY: 1993)
python3 "${CLAUDE_SKILL_DIR}/daily.py" backtest --write         # 30 rules, 158 variants, IS / OOS / HOLDOUT
python3 "${CLAUDE_SKILL_DIR}/daily.py" signal                   # open positions and new entries of passing rules
python3 "${CLAUDE_SKILL_DIR}/daily.py" freeze                   # pre-register today's passers for a forward test
python3 "${CLAUDE_SKILL_DIR}/daily.py" forward                  # how frozen rules did after their freeze date
python3 "${CLAUDE_SKILL_DIR}/hourly.py" fetch                   # 60-minute bars, last 730 days, merged
python3 "${CLAUDE_SKILL_DIR}/hourly.py" backtest --write        # time-of-day rules on ~700 sessions
```

`daily.py` splits the dates IS to 2014, OOS 2015 to 2021 and HOLDOUT 2022 onward, and
passes a rule only with IS t >= 2, positive OOS and HOLDOUT, and t >= 3 on everything after
IS (Harvey, Liu & Zhu 2016). It also reports the deflated Sharpe ratio (Bailey & Lopez de
Prado 2014). Multi-day rules can fill at the signal close or the next open; prefer the
next-open result, since nobody knows the close in advance.

Flags: `--symbols` (default: 40 liquid ETFs, large caps and high-volume names), `--cost` round
trip in basis points (default 3), `--oos` out-of-sample fraction (default
0.30), `--store` the price folder (default `data/` next to this file).

## What it reads and writes

| file | what |
| --- | --- |
| Yahoo chart API | `range=60d&interval=5m`, one request per symbol, 0.5 s apart |
| `data/<SYM>.json.gz` | the price store: every regular-session 5-minute bar ever fetched, merged, never shrinks |
| `results/latest.json` | with `backtest --write`: every variant's stats and the chosen, weighted strategies |
| `RESEARCH.md` | the research journal: papers, results, what was kept or dropped and why, the queue of ideas |

## How it decides

1. **Same rules as real trading.** Every strategy is a function of bars that
   had closed at the moment it decides. Orders fill at the NEXT bar's open.
   A stop fills at the stop price, or at the bar's open if price gapped
   through it. Every position is flat by the close. Each trade pays the
   round-trip cost.
2. **A small grid per strategy.** Two to four variants each (stop rule,
   range length, lookback, threshold).
3. **The split.** Dates before the cut are in-sample (IS), the newest 30%
   are out-of-sample (OOS). The variant with the best IS Sharpe is chosen,
   without looking at OOS.
4. **Keep or drop.** A strategy is kept only if its chosen variant has an
   IS Sharpe of at least 0.5 with 20+ trades AND its OOS mean is still
   positive. Survivors are weighted by IS Sharpe.
5. **The signal.** Each survivor runs on today's bars so far: +1 long,
   -1 short, 0 flat. The weighted sum is the score. Below 0.34 in size is
   "no edge"; above that it is a "lean". It is "strong" only when the score
   is 0.67 or more AND at least two kept strategies agree on the side, each
   with an OOS t of 2 or more. One strategy alone is never strong.

Read the t value. Many variants were tried, so an OOS t below about 2.5
can be luck. The lab says so in every report.

## How to talk about it

- Lead with what survived and what did not, with the OOS numbers.
- Say how many sessions the result rests on. 60 days is thin; it grows.
- When everything fails in-sample and works out-of-sample (or the reverse),
  say the market changed regime, not that the strategy is great.
- Never call a score a sure thing. A "strong long" is a lean from rules that
  held up recently.

## Hand-off

A signal is where a trade idea starts, not an order. Next:
`/trader-entry` to time it, `/trader-exit` for the stop and target,
`/trader-timemachine` for the odds, `/trader-budget` to size it,
`/trader-risk` to check it, and `/trader-broker` only after your yes.

## Keep evolving

Each run of the lab should end with one improvement, logged in
`RESEARCH.md`: take the top idea from its queue, implement it as a new
strategy function with its source, add a test, run `backtest --write`, and
record the result whether it was kept or dropped. Never tune on the OOS
window, never delete a strategy that failed (the record of failures is the
point), and never relax the keep rule to make something pass.

## Safety

- Education and tooling, not financial advice. A backtest is history, not a prediction.
- Paper trading by default (`"paper": true`). Going live is the user's own decision.
- This skill never places an order. Nothing in this pack places one except trader-broker, and only
  after trader-risk passed that exact order and the user typed an explicit yes for it.
- Short signals are shown for research. Shorting stays off unless the user turns on `allow_short`.
