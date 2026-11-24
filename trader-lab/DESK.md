# Trader Desk (`trader-lab/desk.py`)

One command, one report. It runs the other skills' scripts and reads the lab's results files. It re-implements
none of them and **never places an order**.

```
python3 trader-lab/desk.py                         # the lab's 40-name universe
python3 trader-lab/desk.py --tickers NVDA,AAPL     # your own list
python3 trader-lab/desk.py --plan AAPL             # plus a paper trade sheet for one ticker
python3 trader-lab/desk.py --json                  # machine-readable
```

## Sections

1. **Investing (the core):** the monthly index-fund plan from `trader-lab/INVESTING-PLAN.md`. This is where real money goes.
2. **Market:** SPY against its 200-day average, plus its volatility. Context, not a signal.
3. **Research scoreboard:** every study with its verdict, from `trader-lab/results/`:
   - **PASS:** cleared every pre-registered gate. None so far.
   - **UNPROVEN:** passed somewhere, failed a stricter test (R3).
   - **FORWARD-TEST:** being scored on new days only.
   - **FAIL**
4. **News radar:**
   - from trader-news: movers of ±3% and headline tags, plus SEC 8-K flags when SEC access and `sec_user_agent` are set
   - from trader-pelosi: new Congress trades
5. **Candidates:** trader-scanner setups, each with what the lab learned about that setup family (FAIL / UNTESTED),
   plus its news and move.
6. **Trade sheet (`--plan`):** trader-exit plan, then trader-budget sizing, then trader-risk check.
   - It reads **PAPER ONLY** unless a study in section 3 is PASS.
   - It writes to a temporary folder and sends nothing.

## Rules for Claude

- Lead with the scoreboard's bottom line. Never present a scanner hit or a headline as a reason to buy.
- A part that can't run shows `unavailable`. Say which part and why (for example, no network access to the SEC or
  the House Clerk) and carry on.
- No orders. Going live is the owner's decision, through trader-broker, and only after a PASS.

Research, not financial advice.
