# The plan (2026-11-24)

The lab tested about 53 million trading rules across stocks, indices, crypto, forex, metals and
commodities. None of them beat buying and holding after costs by more than luck would explain
(see `RESEARCH.md`). So the plan has two parts:
- the money you want to grow goes into a cheap index fund
- trading stays on the demo until the paper trial earns a real result

Research, not financial advice. The amounts are yours to choose.

## 1. Real money: a monthly index-fund plan

- **What:** one broad, low-cost index ETF.
  - VT or a similar global fund holds the whole world, about 9,000 stocks.
  - SPY / VOO / IVV hold the US S&P 500 only.
  - One is enough; a global fund spreads the risk wider.
- **Where:** a broker that sells the real ETF, not a CFD.
  - Exness offers index CFDs, which charge overnight financing (swap) every night, so they're the wrong tool for holding for years.
  - Use a regular stock broker with no commission on ETF buys, and check what the fund and the broker charge each year (aim for under 0.2%).
- **How:**
  - the same amount on the same day each month
  - set up an automatic buy if the broker offers it
  - no timing, no selling when it drops
  - reinvest the dividends
- **How much:** only money you won't need for at least 5–10 years.
  - Keep an emergency fund in cash first, about 3–6 months of expenses.
  - Pay off expensive debt first.
- **What to expect:** from `python3 trader-lab/dca.py`, at $500 a month, dividends reinvested, before tax.

| fund | period | put in | worth on 2026-11-23 | per year | deepest drop on the way |
| --- | --- | --- | --- | --- | --- |
| SPY | 1996–2026 | $185,500 | $1,242,273 | 10.5% | −51% (2008–09) |
| VT | 2008–2026 | $111,000 | $325,327 | 10.6% | −34% |

Every 10-year window:
- **SPY:** 95% of windows ended with more than went in. The worst, March 1999 to March 2009, lost 9.4% a year.
- **VT:** 100% of windows ended with more than went in. The worst gained 3.6% a year.
- **SPY over 5-year windows:** only 86% ended ahead.

Halving in a crash is normal on the way. The plan only works if you keep buying through it.

## 2. Trading: demo only, until the trial passes

- **The paper trial** (`paper/PLAN.md`, the pre-registered 3:30 p.m. reversal on US500, USTEC and US30)
  runs every trading day. Tickets arrive at 3:31 p.m. New York time. Place them on the Exness demo,
  then record each result:
  `python3 trader-lab/paper.py record --date YYYY-MM-DD --instrument US500 --side sell --pnl -1.23`.
- **The bar it must clear:**
  - at least 20 trading days and 30 trades
  - net above $0, with t ≥ 2
  - drawdown under $60
  - your demo results no more than 30% behind the simulated ones
- **Costs:** since 2026-11-24 the bar also requires the trial to stay profitable at 5 bp per round
  trip (2.5 times the assumed 2 bp spread).
  - `paper.py report` shows that check and the cost at which the trial breaks even.
  - These trades pay no swap, because each one closes by 15:55 New York, before Exness's rollover.
  - Your recorded demo trades carry Exness's real spread.
- **Rules on the demo:**
  - risk $10 or less per trade
  - stop out for the day after a $30 loss
  - every trade has a stop before it's opened
  - write down why you took each trade
- **Going live is your decision, and only after a PASS.** Even then, start with the smallest size.

## 3. The scans: a watchlist, not buy signals

- The 8:41 pre-market scan, the 9:51 simulated picks, the hourly stock scans (10:17 to 3:17) and
  the 24/7 hourly crypto and forex scan keep running.
- The hourly scans now say one line when nothing new fired and give detail only when something does,
  so they're less noise.
- Their setups have been tested and don't beat luck on their own. Use them to learn and to see what's
  moving, on the demo.

## 4. The lab

- Finish the search across 62 markets, already under way, and log the result.
- After that, no more giant searches. They make passing harder, not easier. New ideas get tested one
  at a time, from published research, with the rule fixed before looking at the data.
- **Review date:** when the paper trial reaches 20 trading days, around 2026-12-21. PASS, FAIL or
  extend, decided by the bar above, not by how it feels.
