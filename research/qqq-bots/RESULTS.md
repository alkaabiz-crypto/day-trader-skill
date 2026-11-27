# QQQ TREND / QQQ OG intraday bots: backtest result (2026-11-27)

**Verdict: FAIL. Not added to the paper ledger.** Rules were frozen in PREREG.md before the first run.

Data: QQQ 5-minute bars, regular hours. Period B 2022-11..2026-11 (1,005 days, real VWAP), period A 2016-01..2022-11 (1,736 days, TWAP).
Sizing: USTEC 0.05 lot (~$2.05 per $1 QQQ move). Cost 2.5 NDX pts round trip (Exness 1.12 spread, wider near the open, plus slippage).

| bot | trades B | net B | t B | win % | worst drop B | net A | t A | beats random entries |
|---|---|---|---|---|---|---|---|---|
| TREND (trend continuation + ORB) | 2,039 | -$142 | -0.85 | 28% | -$286 | -$381 | -3.84 | 74% (need 95%) |
| OG (VWAP cross + EMA50 cross + ORB) | 1,784 | -$249 | -1.62 | 28% | -$341 | -$342 | -3.52 | 47% |

- With **zero costs** TREND makes +$61 over 4 years (t 0.36) and OG -$59: there is no edge before costs, so cheaper spreads can't save it.
- All 28 variants lose in both periods: long-only, no chop filter, trailing stop 1.0 / 2.5 ATR, tight 0.5 ATR stop, quick target +1 ATR,
  target +2 ATR, no loss brake, and each signal alone (trend, ORB, VWAP cross, EMA50 cross). Full numbers: qqq_bots_results.json.
- Quick target lifts the win rate to 49% but loses more (-$441 B). A high win rate is easy to make; making money is not.
- Losing years: TREND lost in 2023, 2024, 2025 and every year 2016-2022. 2026 is +$58 (one good year out of eleven).
- The reel's 22 wins / 2 losses day is one cherry-picked day on 0DTE options (leverage, not edge). Its own dashboard shows QQQ OG -$792 the same day.
- Limits: 5-minute bars, not 1-minute (no long 1-minute history); my reading of the rules from video frames, the creator's exact code is not public.
