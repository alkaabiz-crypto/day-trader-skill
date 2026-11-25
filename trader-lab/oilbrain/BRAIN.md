# The oil brain (USOIL / UKOIL)

The oil brain has three parts:
- `KNOWLEDGE.md`: what the published studies say about predicting oil, topic by topic. The papers were
  read from abstracts and citations, and each claim is tagged with how it was checked.
- `brain.py`: the engine. It tests oil's fundamentals and its price signals together on USO (WTI), with
  Brent (BNO) as the check. `oil_data.py` fetches the fundamentals.
- This page: the scorecard.

The older `oil.py` keeps its price-rule search and the two simulated oil tracks (the DCA ladder and the
frozen MA 40/50 cross). Research, not financial advice. Nothing here places an order.

## What it measures, each day at the close

| Feature | Source | Known from |
| --- | --- | --- |
| Crude, Cushing and gasoline stock surprises (this week's change minus the same week's 5-year average) | EIA weekly, 1982+ | the Thursday after the week ends |
| Speculator crowding (managed money net long, 3-year percentile) and its 4-week change | CFTC, 2006+ | the Monday after the report date |
| Backwardation (contract 1 over contract 2) | EIA, 1983 to 2024-04 | the same close |
| Momentum over 21, 63 and 252 days, and 20-day volatility | USO | the same close |
| The dollar (UUP, 21 days); energy stocks against oil (XLE minus USO, 21 days) | daily prices | the same close |

## Scorecard (2026-11-25)

The lab's own test is the result after 2014 (2015 to today), long or short USO, net of costs. The
direction of each feature was taken from 2006-2014 only. The bar is t of 3.

| Idea | What traders believe | What the studies say | Lab, after 2014 (1 day / 5 days) | Verdict |
| --- | --- | --- | --- | --- |
| Inventory surprise | A big draw is bullish | It moves the price within minutes to a day of the release, then nothing more (Halova, Kurov & Kucher 2014) | t −1.14 / −0.13; it worked to 2014, then flipped in 2022 on | No edge |
| Cushing and gasoline stocks | The same | Same-day reaction only | t +0.83 / +0.11 and −0.95 / −0.48 | No edge |
| Speculator positioning (COT) | Crowded longs reverse | Almost no predictive power for crude (Sanders & Irwin) | t +0.39 / +0.51 crowding; −0.47 / −1.62 flows | No edge |
| Backwardation | Long when the curve pays you to hold | The strongest case: roll yield and carry (Gorton, Hayashi & Rouwenhorst 2013; Koijen et al. 2018), mostly across commodities and monthly | t +1.49 / +1.35, positive in every period, placebo 83-84% | Best idea, still far below the bar |
| Momentum | Trends persist | Real in diversified portfolios, weak for one market, faded after 2008 | t +0.94 / +0.65 at 21 days, smaller at 63 and 252 | No edge |
| Volatility | Calm markets trend | Volatility scaling cuts losses, not returns | t +0.38 / −0.13 | No edge |
| The dollar, energy stocks | A weak dollar and strong XLE lead oil | The links are mostly same-day | t −0.69 / +0.40 and −0.89 / −0.34 | No edge |
| OPEC meetings | Cuts are bullish | The price reacts at the decision, with no drift after (Demirer & Kutan 2010) | Not tested: no verified free date list | Untested |
| All 12 combined (the brain) | More signals means better | Forecasts rarely beat "no change" out of sample (Alquist, Kilian & Vigfusson) | t −0.25 / −0.06, after the best fit to 2014 | **Fails** |

Controls after 2014: always long USO t +0.28 (1 day) / +0.36 (5 days); always short −0.91 / −0.99.

## What the oil brain has learned

1. **Oil's public fundamentals are priced at once.** An inventory number moves oil within minutes of
   10:30 on Wednesday. By the next day's open, nothing is left to trade.
2. **Combining weak signals fits noise.** The brain had the best fit to 2014 and nothing after, the same
   lesson as the day-trading brain.
3. **Backwardation is the only idea positive in every period,** in the seventh run and again here. It's
   the one with the strongest theory. It is still well below the bar, and since the EIA curve ends in
   2024-04, its recent years are thin.
4. **Holding oil costs money.** A long USOIL CFD pays the contango roll, which is why USO has trailed spot
   WTI since 2009. Any rule that is often out of oil looks better than holding it, without having an edge.

## How to keep developing it, honestly

- **Rebuild the live curve.** Yahoo's active contract months (`CLF27.NYM` and the next one) give today's
  backwardation. Logging them every day builds the curve history the EIA stopped. In a year,
  backwardation can be judged on fresh data.
- **Add an OPEC date list** only from a source that can be checked, with the rule written first.
- **Do not tune a failed rule until it passes.** `brain.py study` can be rerun with no changes as the data
  grows.
