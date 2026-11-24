# SPY paper day trades (paper money only)

The day-trader skills run one S&P 500 (SPY) trade a day, with no broker and no real money:

1. **trader-entry**: 15-minute opening-range breakout, long only (buy when a 5-minute bar closes above the 9:30-9:45 high).
2. **trader-exit**: stop at the opening-range midpoint, target 2x the risk, flat by 15:55 New York.
3. **trader-budget**: sized to `config.json` ($5,000 paper account, $50 max loss a trade, 1 trade a day).
4. **trader-risk**: must PASS.
5. Simulated fill at the trigger bar's close; then stop, target or 15:55, whichever comes first
   (stop first if one bar touches both). 2 bp round-trip cost.

Run: `python3 sp500/paper_day.py` (status now) or `--final` after 15:55 to log the day in `journal.csv`.

Dry run on 2026-11-23: bought 5 at $726.32 (10:25), stopped at $719.16 (11:40), -$36.53.
The lab found no proven edge for opening-range breakouts on SPY (see trader-lab/RESEARCH.md).
Research and practice, not financial advice.
