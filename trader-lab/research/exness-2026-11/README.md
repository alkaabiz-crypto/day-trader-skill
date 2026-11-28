# Exness strategy research, 2026-11-26

Independent research run in one session. Nothing here places an order; everything is paper.

- `exness-daily-strategies.md`: every batch's results (about 450 rule x market x account tests), newest batches at the end.
- `PREREG.md`: the rules, costs and pass bars, each batch written down before it ran.
- `PLAYBOOK.md`: the two survivors (USTEC IBS at the close, BTC Williams volatility breakout), sizes and stops for a small swap-free account.
- `signals.csv`: daily positions and $ P&L at minimum lots for the survivors, 2016 on (fixed notional at today's lot sizes).
- `ibs_paper/`: the paper ledgers (`ibs_paper.py`, `williams_paper.py`), run by a scheduled task each weekday.
- The `*.py` files are the scripts as they were run. They read the repo's stores in `trader-lab/data/` (from the
  strategy-lab branch) and Yahoo downloads kept in a scratch folder, so paths are absolute and need editing to rerun.

Costs: measured Exness Standard spreads (US500 0.40 pt, USTEC 1.12 pt, gold $0.20, BTC $6.40, EURUSD ~0.9 pip),
no commission, plus slippage; UAE extended swap-free account. Research, not financial advice.
