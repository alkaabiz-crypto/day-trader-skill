# Oil brain: what the studies say

Research, not financial advice.

Scope: predicting returns on crude oil (WTI, Brent) and on long-held oil exposures that pay the futures roll (USO, BNO, a USOIL CFD) over 1 day to about 1 month.

## How to read this file

- Every citation below was found by web search in November 2026. In this session full-text PDFs could not be opened (the network blocked eia.gov, nber.org, ssrn, repec, university sites). So most findings come from **abstracts, publisher records and how other papers quote them**, not from reading the tables.
- Tags used:
  - **[abstract]**: the claim is in the paper's own abstract or publisher summary.
  - **[second-hand]**: the claim comes from another paper, a presentation or a summary describing the work.
  - **[unverified]**: from memory or a weak source; check before relying on it.
- Before anything here drives a trade rule, read the original paper and re-test it on your own data.

## The big picture in five lines

1. Oil returns over days to weeks are close to unpredictable out of sample. The no-change forecast is very hard to beat.
2. The most robust evidence is about *who earns what over months* (term structure / carry, inventories), and it is mostly cross-sectional (oil versus other commodities), not a timing signal for oil alone.
3. News events (EIA inventory reports, OPEC decisions) move prices, but the move happens within minutes to a day. There is little evidence of drift you can trade afterwards.
4. Positioning data (CFTC) has, in most careful tests, no reliable forecasting power for crude.
5. For a long-held USO or CFD position, the roll cost in contango is a certain, measurable drag. It often matters more than any signal.

---

## 1. Weekly EIA inventory surprises (crude, Cushing, gasoline)

**What traders believe.** A bigger-than-expected crude build is bearish, a draw is bullish. Cushing draws matter most for WTI. Some go further and believe the move carries on for days.

**What the evidence says.**

- **The announcement-day reaction is real and in the expected direction.** Futures returns fall after positive (build) surprises and rise after negative (draw) surprises. Wolfe, Kurov and Kucher find "a strong announcement day effect" on both futures and options, plus price moves *before* the release that anticipate the surprise (possible informed trading or better private forecasts). No asymmetry between builds and draws was found. **[second-hand, via an EIA 2017 workshop presentation and search summaries]**
- **Measurement matters.** Halova, Kurov and Kucher (2014) argue earlier estimates were biased toward zero because analyst survey forecasts measure expectations with noise. Corrected, energy futures respond *more strongly* to inventory news than earlier studies found. **[abstract]**
- **Speed: minutes, not days.** An intraday study in the *Journal of Energy Markets* finds activity responds to the shock "very quickly", with effects lasting about 25 minutes and the price reverting quickly after the initial jump. **[abstract / second-hand]** An EIA presentation reports **no persistence of the futures price effect beyond the announcement day** (options showed some persistence up to two days). **[second-hand]**
- **Partial reversal of the surprise itself.** Ederington and co-authors report that storage numbers that surprise analysts tend to partially reverse in the following week's report (noise in the weekly data). This is about the *data*, which hints that chasing the first-day move can be a mistake. **[second-hand; seen for natural gas storage, not confirmed for crude]**
- **EIA versus API.** The EIA release is the main market mover; the API report the evening before carries some information but less. **[second-hand, Rousse and Sévi, IAEE]**
- **Cushing.** Ederington, Fernando and Holland find that Cushing stocks (not other regions) relate to the WTI futures spread, consistent with Cushing as the delivery hub. So Cushing mainly moves **calendar spreads and the curve shape**, which matter for roll yield, more than the outright price. Büyükşahin, Lee, Moser and Robe (2012, EIA-hosted paper) link the WTI-Brent spread to Cushing conditions. **[second-hand]** No direct effect size for Cushing on outright WTI returns was found.
- **Gasoline.** Gasoline and distillate surprises move their own futures; the spill-over into crude is reported as smaller. **[unverified: no paper with numbers confirmed]**

**Surprise versus the 5-year seasonal average (no consensus data).** This is the key question for a free-data build, and the honest answer is: **no published study was found that tests it directly.**

- The theory says markets react to the *unexpected* part. A seasonal-average benchmark is a much noisier proxy for expectations than an analyst survey, and Halova et al. show that noisy expectation measures bias the measured effect toward zero.
- The *level* of stocks versus the 5-year average is a different thing: it is a slow state variable, closely related to the inventory and term-structure evidence in section 3 (low stocks go with backwardation and higher expected futures returns). That is a monthly signal, not a Wednesday trade.
- Practical reading: a seasonal surprise may show a weak same-day correlation, but expect it to be small, and expect no post-release drift. **[my inference, not a published result]**

**Citations.**
- Halova, M. W., Kurov, A., Kucher, O. (2014). "Noisy Inventory Announcements and Energy Prices." *Journal of Futures Markets* 34(10), 911-933. https://econpapers.repec.org/RePEc:wly:jfutmk:v:34:y:2014:i:10:p:911-933
- "The impact of crude oil inventory announcements on prices: Evidence from derivatives markets." *Journal of Futures Markets* 38(1), 38-65 (2018) (Wolfe, Kurov and co-authors; author list not confirmed). https://ideas.repec.org/a/wly/jfutmk/v38y2018i1p38-65.html
- "The informational content of inventory announcements: Intraday evidence from crude oil futures market." *Energy Economics* 59 (2016), 349-364. https://ideas.repec.org/a/eee/eneeco/v59y2016icp349-364.html
- "An analysis of intraday market response to crude oil inventory shocks." *Journal of Energy Markets*. https://www.risk.net/journal-of-energy-markets/5728636/an-analysis-of-intraday-market-response-to-crude-oil-inventory-shocks
- EIA workshop presentation (2017) on inventory announcements: https://www.eia.gov/finance/markets/reports_presentations/2017/yang.pdf (could not open; summarised from search)
- Büyükşahin, B., Lee, T., Moser, J., Robe, M. (2012). WTI-Brent spread paper, EIA: https://www.eia.gov/finance/markets/reports_presentations/2012PaperBrentWTI.pdf

---

## 2. CFTC Commitments of Traders: speculator positioning

**What traders believe.** Extreme managed-money net longs are "crowded" and precede drops; extreme shorts precede squeezes. Following hedgers (or fading them) gives an edge.

**What the evidence says.**

- **Time-series tests on crude: mostly nothing.** Sanders, Irwin and Merrin (2007 and related work) used Granger causality tests on CFTC large-trader data and found "very little evidence" that positions forecast returns. Sanders and Irwin, using fund-level position data in energy markets, "generally fail to reject" that position changes are unrelated to later returns, and find no link between index positions and WTI moves. Where a link exists, prices tend to lead positions (trend followers buy after prices rise), not the other way round. **[second-hand / abstract]**
- **Gorton, Hayashi and Rouwenhorst (2013)** find "no evidence that the positions of participants in futures markets predict risk premiums", while inventory and price signals do. **[abstract]**
- **Rouwenhorst and Tang (2012)** review the theory of normal backwardation: the link between hedging pressure and expected returns is weak and mixed. **[second-hand]**
- **Cross-sectional hedging pressure does work, in a different setting.** De Roon, Nijman and Veld (2000), 20 futures markets: own and cross hedging pressure help explain returns after controlling for market risk. Basu and Miffre (2013) build long-short portfolios sorted on hedging pressure across many commodities and find positive, significant premiums, larger in volatile periods, and separate from momentum and term structure. **[abstract]** These are *ranking commodities against each other* over months, not timing crude by itself.
- **Hedgers versus speculators over short horizons.** Kang, Rouwenhorst and Tang (2020) split the premium in two: hedgers pay an insurance premium, but short-term speculators earn a *liquidity* premium that pushes in the opposite direction. That is one reason simple "follow the speculators" rules fail: the two effects offset. **[abstract]**
- **The dissent.** Singleton (2014) finds that investor flows (growth in index positions and managed-money spread positions over intermediate horizons) had significant effects on oil futures prices around 2008, after controls. This is the main paper supporting predictability from flows; it covers an unusual boom/bust period and has been debated. **[abstract]**
- **Crowding.** Recent work with holdings-based crowding measures finds crowding predicts weaker momentum and carry payoffs across commodities. **[second-hand, working papers]**

**Practical notes.** COT data is as of Tuesday and released Friday afternoon, a 3-day lag. Any test must use the release date, not the "as of" date, or it will cheat.

**Verdict:** weak for crude timing at 1 day to 1 month. Mild support as a cross-sectional or regime filter.

**Citations.**
- de Roon, F. A., Nijman, T. E., Veld, C. (2000). "Hedging Pressure Effects in Futures Markets." *Journal of Finance* 55(3), 1437-1456. https://econpapers.repec.org/RePEc:bla:jfinan:v:55:y:2000:i:3:p:1437-1456
- Basu, D., Miffre, J. (2013). "Capturing the risk premium of commodity futures: The role of hedging pressure." *Journal of Banking & Finance* 37(7), 2652-2664. https://econpapers.repec.org/RePEc:eee:jbfina:v:37:y:2013:i:7:p:2652-2664
- Sanders, D. R., Irwin, S. H., Merrin, R. P. (2007, working paper; later journal versions). Granger tests on CFTC positions. Related: Irwin and Sanders, NBER chapter https://www.nber.org/chapters/c12814.pdf and NBER WP 19065 https://www.nber.org/papers/w19065.pdf (exact title and venue of each version not verified)
- Rouwenhorst, K. G., Tang, K. (2012). "Commodity Investing." *Annual Review of Financial Economics* 4, 447-467. https://papers.ssrn.com/abstract=2170919
- Kang, W., Rouwenhorst, K. G., Tang, K. (2020). "A Tale of Two Premiums." *Journal of Finance* 75(1), 377-417. https://econpapers.repec.org/RePEc:bla:jfinan:v:75:y:2020:i:1:p:377-417
- Singleton, K. J. (2014). "Investor Flows and the 2008 Boom/Bust in Oil Prices." *Management Science* 60(2), 300-318. https://pubsonline.informs.org/doi/10.1287/mnsc.2013.1756

---

## 3. Term structure, roll yield, backwardation, carry

**What traders believe.** Backwardation pays you to hold long; contango bleeds. A steepening backwardation is bullish.

**What the evidence says.** This is the best-supported area in the whole file, with one big caveat: most of it is cross-sectional and monthly.

- **Gorton, Hayashi and Rouwenhorst (2013)**, 31 commodities, 1971-2010: risk premiums vary with physical inventories, as the theory of storage predicts. Low inventories mean high convenience yield, backwardation and higher subsequent futures returns. The futures basis, prior futures returns and spot returns all reflect the inventory state and carry information about premiums. **[abstract]**
- **Erb and Harvey (2006)**, *Financial Analysts Journal*: single commodity futures have historically earned close to zero average excess return; the attractive long-run return of indexes came mainly from rebalancing a diversified basket. Commodities with better term structure (more backwardated) earned more than those in contango, and term-structure and momentum strategies beat long-only. **[abstract]** I could not open the paper to get crude-specific roll numbers. **[unverified detail]**
- **Koijen, Moskowitz, Pedersen and Vrugt (2018)**, "Carry", *JFE*: carry (for commodities, basically the roll yield implied by the curve) predicts returns both in the cross-section and **over time**, across asset classes including commodities. Carry strategies do badly in global recessions and liquidity crunches. **[abstract]** The time-series part is the one most relevant to timing crude alone.
- **Szymanowska, de Roon, Nijman and van den Goorbergh (2014)**, *Journal of Finance*: split returns into a spot premium and a term premium. Sorting on basis, momentum, volatility, inflation, hedging pressure and liquidity gives spot premia of roughly **5% to 14% a year** and term premia of **1% to 3% a year**. A single basis factor explains the spot premia. **[abstract]**
- **Boons and Porras Prado (2019)**, "Basis-Momentum", *Journal of Finance*: the *change* in the curve slope (momentum in the nearby contract minus momentum in a deferred contract) predicts returns across commodities and in individual commodities over time, and beats basis and plain momentum. They attribute it to supply/demand imbalances when speculators and intermediaries cannot clear the market. **[abstract]**
- **Levine, Ooi, Richardson and Sasseville (2018)**, *FAJ*, data from 1877: long-run returns positive on average; they differ a lot between backwardation and contango regimes; most variation comes from spot moves, not carry. **[abstract]** AQR authors; disclosed conflict.
- **Alquist and Kilian (2010)**: the futures-spot spread reflects precautionary demand; when supply fears rise, the spread falls and spot rises. This is an *explanation* of the curve, not a trading signal. **[abstract]**

**How it applies to USO / a CFD.** The roll yield is the part you collect or pay for simply by holding. In steep contango it is a known negative carry; in backwardation it is a tailwind. Even if the spot price is unpredictable, the carry part of your return is partly known in advance from today's curve.

**Out of sample.** The basis/carry factor has survived many samples and asset classes, which is better than most ideas here. But the effect sizes are monthly and modest, there is evidence that commodity factor returns weakened after financialisation (post-2000s) and after publication, and carry crashes in recessions (for oil: 2008, 2014-15, 2020).

**Citations.**
- Gorton, G. B., Hayashi, F., Rouwenhorst, K. G. (2013). "The Fundamentals of Commodity Futures Returns." *Review of Finance* 17(1), 35-105. NBER WP 13249: https://www.nber.org/papers/w13249
- Erb, C. B., Harvey, C. R. (2006). "The Strategic and Tactical Value of Commodity Futures." *Financial Analysts Journal* 62(2), 69-97. https://people.duke.edu/~charvey/Research/Published_Papers/P91_The_strategic_and.pdf
- Koijen, R., Moskowitz, T., Pedersen, L. H., Vrugt, E. (2018). "Carry." *Journal of Financial Economics* 127(2), 197-225. https://www.nber.org/papers/w19325
- Szymanowska, M., de Roon, F., Nijman, T., van den Goorbergh, R. (2014). "An Anatomy of Commodity Futures Risk Premia." *Journal of Finance* 69(1), 453-482. https://econpapers.repec.org/RePEc:bla:jfinan:v:69:y:2014:i:1:p:453-482
- Boons, M., Porras Prado, M. (2019). "Basis-Momentum." *Journal of Finance* 74(1), 239-279. https://econpapers.repec.org/RePEc:bla:jfinan:v:74:y:2019:i:1:p:239-279
- Levine, A., Ooi, Y. H., Richardson, M., Sasseville, C. (2018). "Commodities for the Long Run." *FAJ* 74(2), 55-68. https://www.nber.org/papers/w22793
- Alquist, R., Kilian, L. (2010). "What do we learn from the price of crude oil futures?" *Journal of Applied Econometrics* 25(4), 539-573. https://econpapers.repec.org/RePEc:jae:japmet:v:25:y:2010:i:4:p:539-573

---

## 4. OPEC and OPEC+ meeting announcements

**What traders believe.** Cuts are bullish, hikes bearish; "buy the rumour, sell the news" around Vienna meetings.

**What the evidence says.**

- **Demirer and Kutan (2010)**, *Energy Economics*, OPEC conferences and US SPR announcements, 1983-2008, event study on spot and futures. Cited by later work (including an IMF working paper) as finding an **asymmetry: production cuts move prices, increases and "no change" much less**. **[second-hand; the asymmetry is not in the abstract I saw]**
- **Loutia, Mellios and Andriosopoulos (2016)**, *Energy Policy*, WTI and Brent, 1991-2015: the effect varies over time and by decision type; it is more significant for cuts and for "maintain" decisions; it differs between WTI and Brent and depends on the benchmark used. **[abstract]**
- **Känzig (2021)**, *American Economic Review*: uses the price jump in oil futures in a tight window around OPEC announcements as "oil supply news". The jumps are real and shift the futures curve, with lasting macro effects. **[abstract]** This shows announcements contain news; it does not show a trading edge after the announcement. A Dallas Fed working paper (2023) argues the early years of Känzig's daily surprise series use unsuitable data and the results are sensitive to the sample. **[abstract]**
- **Pre-announcement drift / post-announcement drift:** no robust published evidence found either way for OPEC+ (2016 onward). Meetings are heavily leaked through "sources" stories, so much of the move happens before the official decision. **[unverified for OPEC+ era]**

**Verdict:** the price reaction is well documented, mixed in sign and size, and fast. No reliable evidence of a tradable drift after the decision. Event study samples are small (a few dozen meetings per decade), so any rule fitted on them is easy to overfit.

**Citations.**
- Demirer, R., Kutan, A. M. (2010). "The behavior of crude oil spot and futures prices around OPEC and SPR announcements: An event study perspective." *Energy Economics* 32(6), 1467-1476. https://econpapers.repec.org/RePEc:eee:eneeco:v:32:y:2010:i:6:p:1467-1476
- Loutia, A., Mellios, C., Andriosopoulos, K. (2016). "Do OPEC announcements influence oil prices?" *Energy Policy* 90, 262-272. https://econpapers.repec.org/RePEc:eee:enepol:v:90:y:2016:i:c:p:262-272
- Känzig, D. R. (2021). "The Macroeconomic Effects of Oil Supply News: Evidence from OPEC Announcements." *AER* 111(4), 1092-1125. https://www.aeaweb.org/doi/10.1257/aer.20190964
- Dallas Fed Working Paper 2310 (2023), critique of OPEC surprise series: https://www.dallasfed.org/-/media/documents/research/papers/2023/wp2310.pdf
- Related: "Agreement matters: OPEC announcement effects on WTI term structure," *Energy Economics* 80 (2019), 589-609. https://ideas.repec.org/a/eee/eneeco/v80y2019icp589-609.html (not read)

---

## 5. The US dollar, stocks and oil, energy equities

**What traders believe.** A weaker dollar lifts oil. Energy stocks (XLE) lead crude. Oil and stocks move together.

**What the evidence says.**

- **Dollar.** Fratzscher, Schneider and Van Robays (CESifo WP 2013 / ECB WP 1689, 2014): a **negative correlation between oil and the dollar since the early 2000s**, with no systematic correlation in the three decades before. Causality runs both ways: a 1% dollar weakening raises oil about **0.73%**, a 10% oil rise weakens the dollar about **0.28%** on impact. They attribute the stronger link to risk shocks and financialisation. **[abstract]** This is a *contemporaneous* relation; it does not say yesterday's dollar predicts today's oil. Later work (Coudert and Mignon 2016, not read) reassesses the relation. The sign has flipped at times since (for example when the US became a net oil exporter). **[unverified for recent years]**
- **Oil predicts stocks, not the other way.** Driesprong, Jacobsen and Maat (2008), *JFE*: oil price changes predict **lower subsequent stock returns** in many developed markets (the working paper reports 12 of 18 countries plus a world index, monthly, about 30 years). The effect strengthens with a lag of several trading days, consistent with slow diffusion of oil news into equities, and is not explained by time-varying risk premia. **[abstract / working paper]** Note the direction: this is a signal for *trading stocks after oil moves*, not for trading oil.
- **Energy equities leading oil.** Some working papers report that stock indices, especially energy sector indices, help predict crude prices at short horizons, and Calomiris, Cakir Melek and Mamaysky (Kansas City Fed WP, 1998-2020 sample) use oil-major equity returns with text measures to forecast oil futures returns. **[second-hand; working papers, mixed]** No strong peer-reviewed evidence that XLE reliably leads WTI by a day or more was found. Both trade in the same US session, so any lead is likely intraday and arbitraged.

**Verdict:** dollar and stocks are useful as *context* (risk-on/off regime, explaining moves). As next-day predictors of oil, evidence is weak or untested.

**Citations.**
- Fratzscher, M., Schneider, D., Van Robays, I. (2014). "Oil Prices, Exchange Rates and Asset Prices." ECB WP 1689. https://www.ecb.europa.eu/pub/pdf/scpwps/ecbwp1689.pdf ; CESifo WP 4264: https://www.cesifo.org/DocDL/cesifo1_wp4264.pdf
- Driesprong, G., Jacobsen, B., Maat, B. (2008). "Striking oil: Another puzzle?" *Journal of Financial Economics* 89(2), 307-327. https://econpapers.repec.org/RePEc:eee:jfinec:v:89:y:2008:i:2:p:307-327
- Calomiris, C., Cakir Melek, N., Mamaysky, H. Kansas City Fed RWP 20-20: https://www.kansascityfed.org/documents/9269/rwp20-20calomiriscakirmelekmamaysky-v2.pdf
- "Do oil futures prices predict stock returns?" *Journal of Banking & Finance* 79 (2017), 129-141. https://ideas.repec.org/a/eee/jbfina/v79y2017icp129-141.html (not read)

---

## 6. Seasonality and calendar effects

**What traders believe.** Crude rallies into the US driving season (spring to early summer) and weakens in autumn; refinery maintenance in spring and autumn cuts crude demand; certain weekdays are better.

**What the evidence says.**

- **The physical seasonality is real.** EIA explains that gasoline stocks draw in summer and rebuild in autumn and winter; refinery runs dip during spring and autumn maintenance. These patterns are in the *quantities* and are well known.
- **Seasonality in crude *returns* is weak.** Most "seasonal" return claims come from brokers and seasonal-chart vendors, not peer-reviewed work. StoneX (1986-2018) describes spring/summer strength and autumn/winter weakness but notes it does not hold every year; a Moore Research pattern cited by Barchart worked in only 6 of 15 years; a ThinkMarkets review finds monthly mean and median returns differ a lot (outliers dominate). **[practitioner sources]**
- **Why it should not be strong:** a predictable seasonal demand swing is priced into the futures curve (summer contracts already trade at a premium). The seasonal premium is therefore in the curve shape, not in a free return. A cleaner test of the driving-season idea is the gasoline crack spread (RBOB minus crude), where seasonality is a known feature, not crude itself. **[inference]**
- **Day of week.** A 2023 study of energy futures finds day-of-week effects vary by contract (for example a Friday effect in WTI, Wednesday in Brent and heating oil); a 2025 study of Chinese crude futures finds a Monday effect before COVID but nothing in the full sample. Older work reports a weekend effect in energy futures. Pattern: unstable, appears and disappears by sample. **[abstract]** Wednesday is EIA day, so any Wednesday effect may be the inventory release in disguise.

**Verdict:** weak. Treat calendar effects as noise unless they survive a long sample, an out-of-sample split and costs.

**Citations.**
- Meek, A. C., Hoelscher, S. A. (2023). Day-of-week effects in energy futures. *Cogent Economics & Finance* 11(1). https://doaj.org/article/0eb0c617d4dd420da38b95aadafe74ed
- "Risky short positions and investor sentiment: Evidence from the weekend effect in futures markets" (journal and year not verified). https://law-journals-books.vlex.com/vid/risky-short-positions-and-855670779
- University of Glasgow working paper on seasonal patterns in energy futures prices: https://eprints.gla.ac.uk/281581/1/281581.pdf (not read)
- StoneX, "Summer seasonality and WTI crude oil pricing" (practitioner): https://futures.stonex.com/blog/summer-seasonality-and-wti-crude-oil-pricing

---

## 7. Time-series momentum and trend following

**What traders believe.** "The trend is your friend": go long crude after it has risen over the past months, short after it has fallen.

**What the evidence says.**

- **Moskowitz, Ooi and Pedersen (2012)**, *JFE*: significant time-series momentum in all 58 liquid futures they study (equity indices, currencies, commodities, bonds), with the classic rule being a 12-month look-back and 1-month holding, volatility-scaled. A diversified portfolio earns large abnormal returns. **[abstract]** I could not confirm the crude-specific Sharpe ratio. A third-party replication (Quantopian notebook, 1984-2009) shows roughly **0.36 for WTI and 0.49 for Brent** as single-market Sharpe ratios. **[second-hand replication; treat with caution]**
- **Hurst, Ooi and Pedersen (2017)**, *Journal of Portfolio Management*: trend following across 67 markets with a long history (back to the late 1800s / early 1900s), positive in each decade, net of estimated costs, and good in large equity crises. **[abstract / second-hand]** Written by AQR; strong for *diversified* trend, says little about crude alone.
- **The challenge.** Huang, Li, Wang and Zhou (2020), *JFE*, "Time series momentum: Is it there?": asset-by-asset regressions show **little evidence of TSM, in and out of sample**; the pooled t-stat fails against bootstrap critical values; TSM profits are virtually the same as a strategy based on each asset's historical mean return, with no predictability needed. **[abstract]** For a single market like crude this matters a lot: the portfolio result does not mean crude itself is predictable.
- **Post-2008 decay.** Trend/CTA returns fell sharply after 2008 (Newedge Trend Index about -0.8% a year from 2009 to mid-2013 versus 8% in the five years before). Explanations offered: post-crisis periods trend less (O'Brien, UCC 2014), central bank intervention, and (Kurth, Eisler, Rej, Bouchaud) short-term trend failing mainly in small-tick markets. **[second-hand]** Commodity momentum profits are reported to have declined substantially in the post-financialisation period. **[second-hand]** Generic factor research (McLean and Pontiff 2016) finds published anomalies lose a large part of their return after publication.
- **Short horizons.** For 1 day to 1 month holding periods the relevant thing is a trend filter (for example sign of the 1, 3 or 12 month return). The evidence for crude alone is positive but weak, and depends heavily on a few big trends (2008, 2014-15, 2020, 2022).

**Verdict:** mixed. Real in diversified portfolios over a century; weak and fragile for crude as a single market, and weaker after 2008.

**Citations.**
- Moskowitz, T. J., Ooi, Y. H., Pedersen, L. H. (2012). "Time series momentum." *Journal of Financial Economics* 104(2), 228-250. https://econpapers.repec.org/RePEc:eee:jfinec:v:104:y:2012:i:2:p:228-250
- Hurst, B., Ooi, Y. H., Pedersen, L. H. (2017). "A Century of Evidence on Trend-Following Investing." *Journal of Portfolio Management*. https://www.aqr.com/Insights/Research/Journal-Article/A-Century-of-Evidence-on-Trend-Following-Investing
- Huang, D., Li, J., Wang, L., Zhou, G. (2020). "Time series momentum: Is it there?" *Journal of Financial Economics* 135(3), 774-794. https://econpapers.repec.org/RePEc:eee:jfinec:v:135:y:2020:i:3:p:774-794
- Quantopian TSMOM replication notebook (second-hand numbers): https://nbviewer.jupyter.org/github/quantopian/research_public/blob/master/advanced_sample_analyses/TSMOM/TS%20MOM.ipynb
- O'Brien, J. (2014). "Is this time different? Trend-following and financial crises." UCC working paper. https://www.ucc.ie/en/media/research/centreforinvestmentresearch/wp/TrendFollowingFeb2014.pdf
- McLean, R. D., Pontiff, J. (2016). "Does Academic Research Destroy Stock Return Predictability?" *Journal of Finance* 71(1). (cited from memory; equity evidence, not commodity) **[unverified link]**

---

## 8. Volatility and risk: volatility-managed exposure

**What traders believe.** Scale position size down when volatility is high and up when it is low, and returns per unit of risk improve.

**What the evidence says.**

- **Moreira and Muir (2017)**, *Journal of Finance*: scaling by inverse past variance produced large alphas, mainly for equity factors. **[abstract]**
- **Kang and Kwon (2021)**, *Journal of Futures Markets*, "Volatility-managed commodity futures portfolios": volatility management looks good **in sample** for 12-month momentum and the commodity market portfolio, but **out of sample it fails to improve real-time performance**. **[abstract]**
- **Harvey et al. (2018)**, *Journal of Portfolio Management*, "The Impact of Volatility Targeting", 60+ assets: for bonds, currencies and **commodities, volatility scaling has a negligible effect on Sharpe ratios**, but it consistently **reduces extreme returns (fat tails)** across assets. **[second-hand summary]**
- Cederburg et al. (2020, *JFE*) criticise volatility-managed portfolios more generally out of sample. **[not read]**

**Verdict:** do not expect higher Sharpe from vol-scaling crude. Do expect smaller blow-ups, which for a leveraged CFD is the point. Sizing by recent volatility (for example 20-day realised vol or ATR) is a risk tool, not an alpha source.

**Citations.**
- Moreira, A., Muir, T. (2017). "Volatility-Managed Portfolios." *Journal of Finance* 72(4). NBER WP 22208: https://www.nber.org/papers/w22208
- Kang, Kwon (2021). "Volatility-managed commodity futures portfolios." *Journal of Futures Markets* 41(2), 159-178. https://econpapers.repec.org/RePEc:wly:jfutmk:v:41:y:2021:i:2:p:159-178 (author first names not verified)
- Harvey, C. R., Hoyle, E., Korgaonkar, R., Rattray, S., Sargaison, M., Van Hemert, O. (2018). "The Impact of Volatility Targeting." *Journal of Portfolio Management*. https://people.duke.edu/~charvey/Research/Published_Papers/P135_The_impact_of.pdf

---

## 9. What fails

### Technical trading rules after data-snooping corrections

- **Psaradellis, Laws, Pantelous and Sermpinis (2019)**, *European Journal of Finance* 25(17), 1793-1815: test about 7,846 rules (the Sullivan, Timmermann and White universe: moving averages, filters, support/resistance, channel breakouts, on-balance volume) on **WTI futures and USO**, from 2006, with false discovery rate and familywise error controls. Strong in-sample results, but **performance is not persistent over time**; only small, intermittent profits in some periods. **[abstract]**
- Lesson: if you try many rules, some will look great by luck. Count how many variants you tried and correct for it.

### Out-of-sample forecasting of oil returns

- **Alquist, Kilian and Vigfusson (2013)**, *Handbook of Economic Forecasting* vol. 2, ch. 8, 427-507: the reference survey on forecasting oil prices. Main theme: in-sample predictability rarely turns into better out-of-sample forecasts than a **no-change (random walk) forecast** at short horizons. **[second-hand / known theme; full chapter not opened]**
- **Alquist and Kilian (2010)**: oil futures prices are **less accurate than the no-change forecast** in mean-squared error terms (though better than professional surveys). **[second-hand, replication data summary]**
- The EDHEC-linked study on commodity factor prediction models concludes that dynamic strategies built on return-prediction models "provide little value added". **[second-hand]**

### Costs

- Daily or weekly rules in crude trade often. Futures costs are small (one tick plus commissions), but CFD spreads and overnight financing are much larger, and ETF bid/ask plus spread on USO/BNO adds up. A rule with a 0.05% daily edge can be wiped out by costs. Always test net of a realistic round-trip cost for the actual instrument. **[general; no single paper]**

### Contango roll drag on USO and CFDs

- A study in *Applied Economics Letters* (2022, DOI 10.1080/13504851.2022.2082363) attributes USO's large underperformance against spot WTI after 2009 to **prolonged contango and a steep curve**; expense ratio about 0.76% a year. **[abstract]**
- In April 2020 front-month WTI went negative for the first time (since trading began in 1983). USO had already left the May contract but was exposed to super-contango in later months; it then moved to spreading its holdings across months. Fernandez-Perez, Fuertes and Miffre argue USO was unlikely to be the main cause of the negative print. **[second-hand / news]**
- A long-held USO or rolled CFD earns spot change **plus roll yield minus fees and financing**. In contango, the roll yield is negative and largely known in advance from the curve. A "right on direction, wrong on carry" trade can still lose money.

**Citations.**
- Psaradellis, I., Laws, J., Pantelous, A. A., Sermpinis, G. (2019). "Performance of technical trading rules: evidence from the crude oil market." *European Journal of Finance* 25(17), 1793-1815. https://econpapers.repec.org/RePEc:taf:eurjfi:v:25:y:2019:i:17:p:1793-1815 ; accepted manuscript: https://livrepository.liverpool.ac.uk/3069791/
- Alquist, R., Kilian, L., Vigfusson, R. J. (2013). "Forecasting the Price of Oil." *Handbook of Economic Forecasting* vol. 2, 427-507. Fed IFDP 1022: https://www.federalreserve.gov/econres/ifdp/forecasting-the-price-of-oil.htm
- Alquist, R., Kilian, L. (2010), see section 3.
- USO contango study, *Applied Economics Letters* (2022): https://doi.org/10.1080/13504851.2022.2082363 (title and authors not verified)
- Fernandez-Perez, A., Fuertes, A.-M., Miffre, J., working paper on negative WTI prices: https://acfr.aut.ac.nz/__data/assets/pdf_file/0004/541903/WTI-crude-oil-prices_Adrian-2021DMC.pdf

---

## Scorecard

| Idea | Horizon | Strength of evidence | Held out of sample / after publication? |
|---|---|---|---|
| EIA surprise, same-day reaction | minutes to 1 day | Strong (with survey consensus) | Reaction yes; no drift to trade |
| EIA surprise vs 5-year average | 1 day | Untested in literature | Unknown |
| CFTC positioning, crude timing | 1 week to 1 month | Weak / none | Mostly fails |
| Hedging pressure, cross-section | 1 month | Moderate | Partly |
| Carry / basis / backwardation | 1 month | Strongest here | Mostly yes, smaller, crash risk |
| Basis-momentum | 1 month | Moderate (one main paper) | Post-2019 evidence thin |
| OPEC announcements | event window | Reaction real, sign mixed | No tradable drift shown |
| Dollar / stocks predicting oil | 1 day to 1 month | Weak (relations are contemporaneous) | Unstable |
| Seasonality, day of week | 1 day to 1 month | Weak | Unstable |
| Time-series momentum, crude alone | 1 month | Mixed | Weaker after 2008 |
| Vol-managed sizing | any | No Sharpe gain; fewer tail losses | Tail benefit holds |
| Technical rules | 1 day | Fails after snooping control | No |

---

## Testable with free data

**EIA weekly stocks** (EIA API or weekly spreadsheets: crude ex-SPR, Cushing, gasoline, distillate, refinery runs):
- Seasonal surprise: weekly change minus the 5-year average change for the same week. Test its correlation with the Wednesday return of WTI front month or USO, and with Thursday to Friday returns (to check for drift or reversal).
- Stock level versus 5-year average as a slow state variable: does it predict next-month USO return, or next-month roll yield?
- Cushing level and change versus the WTI 1st to 2nd month spread.

**CFTC COT** (disaggregated futures-only, crude oil NYMEX code 067651; weekly CSV/ZIP):
- Managed-money net position as % of open interest, its 52-week z-score and its weekly change. Test against the next 1 to 4 week returns, **aligned to the Friday release date**.
- Producer/merchant net short (hedging pressure) against next-month returns.

**EIA or Yahoo futures prices** (EIA daily spot and futures contracts 1 to 4 for WTI; Yahoo CL=F and BZ=F front month only):
- Carry / roll yield: (F1 minus F2) / F2 annualised, or F1 versus F4. Test as a time-series signal for next-month returns and for USO's tracking gap.
- Basis-momentum: 12-month return on contract 1 minus contract 2 (needs EIA contract series; Yahoo continuous series mix in the roll and are not enough).
- Time-series momentum: sign of the 1, 3, 12 month return, volatility-scaled, with a Huang et al. style check (compare with a "historical mean" benchmark).
- Calendar: month-of-year and day-of-week averages with medians, a pre/post split and a cost deduction.

**USO / BNO / UUP / XLE / SPY daily prices** (Yahoo):
- USO minus WTI spot gap versus the curve slope: measures the real roll drag you would pay.
- UUP and SPY: same-day versus next-day correlation with USO (expect contemporaneous yes, predictive weak).
- XLE leading USO: regress next-day USO return on today's XLE return, controlling for today's USO return.
- Reverse check (Driesprong et al.): does today's USO return predict SPY or XLE returns over the next 1 to 4 weeks?
- Vol-managed sizing: USO return scaled by inverse 20-day realised variance versus unscaled; compare Sharpe and worst months.

**Not testable with free data:** analyst consensus inventory surprises (Bloomberg/Reuters surveys), intraday reaction windows, OPEC "sources" headlines timing, and full CFD financing costs (broker specific).

Rules for any test: split the sample (for example fit to 2006-2018, check on 2019 onward), count every variant tried, deduct realistic costs, and use only data that was public at the decision time.
