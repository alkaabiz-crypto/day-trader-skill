# ReversalTrial: install on Exness MetaTrader 5 (DEMO)

This Expert Advisor trades the pre-registered 15:30 New York reversal (`../paper/PLAN.md`) by itself:
it fades moves of 1%+ in US500, USTEC and US30 at 15:30 New York, with a stop 0.5% from the fill,
and closes everything by 15:55. It ships in **dry-run** mode, which only writes what it would do to
the log. Use it on a **demo** account; the plan says no real money until the trial's pass bar is met.

## Steps (MT5 desktop: Windows, or Mac with the Exness MT5 app)

1. In MT5, log in to your **Exness demo** account.
2. **File > Open Data Folder**, then go to `MQL5/Experts/`. Copy `ReversalTrial.mq5` there.
3. Open **MetaEditor** (F4), open `ReversalTrial.mq5` and press **Compile** (F7). The status must
   say "0 errors". If not, send me the error lines.
4. In **Market Watch**, check the exact names of the three indices. Exness sometimes adds a
   suffix, for example `US500m`.
5. Drag **ReversalTrial** from the Navigator onto any chart. In **Inputs**:
   - `Symbols`: the exact names from step 4, comma-separated.
   - Leave `DryRun = true` for the first days.
   - Tick **Allow Algo Trading** in the Common tab.
6. Turn on the **Algo Trading** button in the toolbar. MT5 must stay open (or run on a VPS).
7. Each weekday at about 15:30 New York, check the **Experts** tab. It prints each index's move
   and what it *would* buy or sell.
8. When the dry-run lines look right for a few days, set `DryRun = false` on the **demo** account.

## Limits it enforces in code

- Position value at most `MaxNotionalUSD` ($1,000), which also limits risk to $5 at a 0.5% stop.
- At most `MaxTradesPerDay` (3) entries, and none once the day's closed loss reaches
  `MaxDailyLossUSD` ($30).
- No entries after 15:35 New York; everything is closed at 15:55.
- It only manages its own positions (magic number 153015).
- It warns in the log if the account is not a demo.

Going live is your decision, in your MT5. Exness index CFDs are leveraged products. Research,
not financial advice.
