# Day-trading knowledge file: what the evidence says

Compiled 2026-11-24. Scope: intraday trading of US stocks (and the index ETFs most of the
intraday literature uses). Each section gives a plain-language explanation, a table of studies,
and what a day trader should take from it. The last section lists features that can be computed
from 5-minute OHLCV bars at 9:35 or 10:00 New York time.

## How to read this file (and its limits)

- **Verification level.** This file was built from web search results (abstracts, publisher and
  repository listings, author PDFs' snippets, and a few practitioner write-ups). Direct page
  fetching of SSRN, RePEc and similar hosts was blocked in the session that built it, so most
  numbers come from abstracts or summaries, not from reading full papers. Where a number comes
  from a secondary source (a blog, a summary site, a forum), it is marked **[secondary]**. Where
  something could not be verified at all, it is marked **[unverified]**.
- **"Holds up?"** means: was the effect seen out of sample, after realistic costs, and after the
  paper was published, and has anyone failed to replicate it. "Not tested" means the search did
  not find such a test, not that the effect fails.
- **Author-run backtests are not independent evidence.** Several of the most-cited day-trading
  papers (Zarattini, Aziz, Barbon) come from authors who also sell trading education or run a
  trading firm. Their results are reported as claims, with independent checks noted where found.
- Nothing here is advice to trade. The base rate for retail day traders is losing money (Section 8).

---

## 1. The first 5-minute candle and the opening range breakout (ORB)

**What it is.** The *opening range* is the high and low of the first N minutes after the 9:30 open
(N = 5, 15, 30 or 60). An *opening range breakout* goes long when price trades above the range high
(or short below the range low), usually with a stop at the other side of the range or a fraction of
ATR, and exits by the close. Toby Crabel's 1990 book popularised the idea and the related "narrow
range" (NR4/NR7) filters: a day whose range is the narrowest of the last 4 or 7 days is expected
to be followed by range expansion. "Stocks in play" are stocks trading unusually heavy volume that
day, usually because of news.

| Study | Sample | Finding | Holds up? |
|---|---|---|---|
| Crabel (1990), *Day Trading with Short Term Price Patterns and Opening Range Breakout*, Traders Press ([description](https://www.trendfollowing.com/2010/02/21/day-trading-with-short-term-price-patterns-and-opening-range-breakout/)) | Futures, 1980s (book) | Practitioner rules: ORB, NR4/NR7 contraction-expansion. | Book, not a peer-reviewed test. Content seen only via secondary descriptions [secondary]. |
| Holmberg, Lönnbark & Lundström (2013), "Assessing the profitability of intraday opening range breakout strategies", *Finance Research Letters* 10(1):27-33 ([RePEc](https://econpapers.repec.org/RePEc:eee:finlet:v:10:y:2013:i:1:p:27-33)) | US crude oil futures, 1983-2011 | A volatility-based ORB was significantly profitable (bootstrap tests), but most profit came in the last decade of the sample [secondary summary]. | Cost treatment not verified. Not stocks. |
| Zarattini & Aziz (2023), "Can Day Trading Really Be Profitable?" SSRN 4416622 ([SSRN](https://papers.ssrn.com/abstract=4416622)) | QQQ / TQQQ, 2016-2023 | 5-minute ORB on QQQ; with leverage (TQQQ) the authors report returns well above buy-and-hold. | Author-run backtest. An independent blog replication on 5 index futures (2015-2026) reports the gross edge reproduces but nets to about zero after costs ([MQL5 blog](https://www.mql5.com/en/blogs/post/776235)) [secondary, not peer reviewed; page could not be opened, only the search snippet]. |
| Zarattini, Barbon & Aziz (2024), "A Profitable Day Trading Strategy For The U.S. Equity Market", SSRN 4729284 / Swiss Finance Institute RP 24-98 ([SSRN](https://papers.ssrn.com/abstract=4729284), [St. Gallen repository](https://alexandria.unisg.ch/handle/20.500.14171/122125)) | 7,000+ US stocks, 2016-2023 | 5-minute ORB restricted to "Stocks in Play" (top 20 by opening-range relative volume). Abstract reports >1,600% total net return, Sharpe 2.81, annual alpha 36%, vs about 198% for the S&P 500. 5-minute ranges beat 15/30/60-minute ones. | Net of the authors' cost assumptions (not verified). Stock filters reported by a third party: price > $5, average daily volume >= 1M shares, then the top 20 by opening-range relative volume [secondary, not checked against the paper; [CXO](https://www.cxoadvisory.com/individual-investing/intraday-trading-of-overactive-stocks-via-opening-range-breakout/)]. QuantConnect re-implementation reported Sharpe about 2.4 [secondary, [QuantConnect](https://www.quantconnect.com/research/18444/opening-range-breakout-for-stocks-in-play/)]. No post-publication or peer-reviewed replication found. |

**What a day trader should take from it.**
- The single most-cited stock ORB result is an author backtest over one period (2016-2023, a
  strong, high-retail-participation market). Its edge is concentrated in **high relative volume**
  names; on ordinary stocks the 5-minute ORB was much weaker in the same paper.
- The one independent check found (index futures) says the raw edge is real but small enough that
  costs eat it. On individual small and mid caps, spreads and slippage at the open are larger, so
  cost assumptions decide the result. Test with conservative costs (Section 8).
- Peer-reviewed ORB evidence is thin and mostly in futures.

---

## 2. Candle anatomy, wicks and candlestick patterns

**What it is.** A candle has a body (open to close) and wicks (the high and low beyond the body).
Long lower wicks ("hammer") or long upper wicks ("shooting star") are read as rejection of a price
level. *Close location value* (CLV) measures where the close sits inside the bar's range:
CLV = ((C - L) - (H - C)) / (H - L), from -1 (close at the low) to +1 (close at the high).

| Study | Sample | Finding | Holds up? |
|---|---|---|---|
| Caginalp & Laurent (1998), "The predictive power of price patterns", *Applied Mathematical Finance* 5(3-4):181-205 ([RePEc](https://econpapers.repec.org/RePEc:taf:apmtfi:v:5:y:1998:i:3-4:p:181-205)) | Daily OHLC, all S&P 500 stocks, 1992-1996 | Three-day reversal patterns: out-of-sample significance and almost 1% profit over a 2-day hold (abstract). | Short, single sample; later US large-cap studies did not find value (below). |
| Marshall, Young & Rose (2006), "Candlestick technical trading strategies: Can they create value for investors?", *J. Banking & Finance* 30(8):2303-2323 ([RePEc](https://econpapers.repec.org/RePEc:eee:jbfina:v:30:y:2006:i:8:p:2303-2323)) | Daily, DJIA stocks, 1992-2002 | Candlestick strategies did not have value for these US large caps (bootstrap). Companion paper: "not generally profitable when applied to large U.S. stocks". | Negative result; consistent with later work. Full text not read. |
| Lu, Shiu & Liu (2012), "Profitable candlestick trading strategies—The evidence from a new perspective", *Review of Financial Economics* 21(2):63-68 ([RePEc](https://econpapers.repec.org/RePEc:eee:revfin:v:21:y:2012:i:2:p:63-68)) | Daily, Taiwan Top 50 stocks, 2002-2008 | Three two-day bullish reversal patterns profitable, with out-of-sample test and bootstrap. | Emerging market, daily bars; cost and post-publication tests not verified. |
| Duvinage, Mazza & Petitjean (2013), "The intra-day performance of market timing strategies and trading systems based on Japanese candlesticks", *Quantitative Finance* 13(7):1059-1070 ([RePEc](https://econpapers.repec.org/RePEc:taf:quantf:v:13:y:2013:i:7:p:1059-1070), [working paper](https://dial.uclouvain.be/pr/boreal/en/object/boreal%3A136070/datastream/PDF_02/view)) | **5-minute bars**, 30 DJIA stocks, 83 rules | About a third of rules beat buy-and-hold before costs; after costs only a few remain; after a data-snooping correction (SSPA) **no rule beats buy-and-hold after costs**; combined systems also fail. | The most relevant study for intraday use, and it is negative. |
| Jamaloodeen, Heinz & Pollacia (2018), "A statistical analysis of the predictive power of Japanese candlesticks", *J. Int'l & Interdisciplinary Business Research* 5:62-94 ([PDF](https://core.ac.uk/download/214528289.pdf)) | Daily S&P 500 index, 60+ years | Hammer / shooting star: little reliability measured on closes; reported reliable when measured on the low (hammer) / high (shooting star). | Small journal; index only; no costs. Treat as weak. |

No peer-reviewed study was found that tests CLV or wick length on 5-minute bars of the whole US
market [gap in evidence].

**What a day trader should take from it.** On US large caps, candlestick patterns have shown at most
weak predictive power, and the one large 5-minute study found none that survives costs and a
multiple-testing correction. Wick and close-location measures are reasonable *features* to test
(Section 10), but there is no good evidence that classic named patterns are an edge by themselves.

---

## 3. Gaps, and overnight versus intraday returns

**What it is.** A *gap* is the difference between today's open and yesterday's close. "Gap and go"
trades in the gap's direction; a "gap fade" bets on a move back toward yesterday's close ("gap fill").
More broadly, a stock's daily return splits into the *overnight* part (close to open) and the
*intraday* part (open to close), which behave differently.

| Study | Sample | Finding | Holds up? |
|---|---|---|---|
| Cliff, Cooper & Gulen (2008), "Return differences between trading and non-trading hours: Like night and day", SSRN 1004081 ([SSRN](https://papers.ssrn.com/abstract=1004081), [CXO summary](https://www.cxoadvisory.com/calendar-effects/buy-at-the-close-and-sell-at-the-open)) | US stocks/ETFs, 1993-2006 | The US equity premium over the period came almost entirely overnight; intraday returns near zero or negative. | Follow-ups found the effect weaker in some ETF samples after 2006 [secondary]. Working paper. |
| Berkman, Koch, Tuttle & Zhang (2012), "Paying attention: Overnight returns and the hidden cost of buying at the open", *JFQA* 47(4):715-741 ([Cambridge](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/paying-attention-overnight-returns-and-the-hidden-cost-of-buying-at-the-open/F9AAD159B512C651F09D5D52011D88E0), [PDF](https://kuscholarworks.ku.edu/bitstream/1808/10965/1/Koch_Paying%20Attention.pdf)) | US stocks | Overnight returns tend to be positive then reverse during the day; the open is priced high, concentrated in stocks that recently drew retail attention. The hidden cost of buying high-attention stocks at the open often exceeds the effective half-spread. | Peer reviewed; consistent with Lou-Polk-Skouras and Barber et al. (2022). |
| Lou, Polk & Skouras (2019), "A tug of war: Overnight versus intraday expected returns", *JFE* 134(1):192-213 ([PDF](https://personal.lse.ac.uk/polk/research/TugOfWar.pdf), [RePEc](https://econpapers.repec.org/RePEc:eee:jfinec:v:134:y:2019:i:1:p:192-213)) | US stocks, 1993-2013, 14 strategies | Momentum profits accrue overnight; many other anomaly profits accrue intraday; persistent continuation within each component and reversal across them. Authors note costs make direct exploitation much less attractive. | Published; widely cited. Not a direct trading strategy. |
| Caporale & Plastun (2017), price gaps, *Investment Analysts Journal* ([PDF](https://bura.brunel.ac.uk/bitstream/2438/25828/3/FullText.pdf)) | Daily; Dow index + IBM, also FX and commodities, 2000-2015 | Abnormal moves after gaps; gap-based strategy reported profitable. | Narrow US sample; costs not verified. |
| Plastun, Sibande, Gupta & Wohar (2020), "Price gap anomaly in the US stock market: The whole story", *North American J. of Economics & Finance* 52:101177 ([repository](https://repository.up.ac.za/handle/2263/78336)) | Daily DJI, S&P 500, NASDAQ indices, 1928-2018 | On a gap day, prices tend to keep moving **in the gap's direction**; the momentum effect is temporary; results "contrary to the myth that price gaps tend to get filled". | Indices, not single stocks. Cost treatment not verified. |
| Chan (2003), "Stock price reaction to news and no-news: drift and reversal after headlines", *JFE* 70(2):223-260 ([RePEc](https://econpapers.repec.org/RePEc:eee:jfinec:v:70:y:2003:i:2:p:223-260)) | US stocks, monthly | Drift after bad news; reversal after big moves with no news; mainly in small, illiquid stocks. | Monthly horizon. |
| Boudoukh, Feldman, Kogan & Richardson (2012), "Which news moves stock prices? A textual analysis", NBER WP 18725 ([NBER](https://www.nber.org/papers/w18725.pdf)) | US stocks, daily | Reversals happen on no-news days; identified-news days show continuation. | Daily horizon; consistent with Chan (2003). |

Individual-stock *intraday* gap-fade evidence found was a thesis and a paywalled practitioner note
(both say large gap-ups give back part of the gap intraday, strongest in small, illiquid stocks)
[unverified; see [Turku thesis](https://www.utupub.fi/bitstreams/88057d2a-1ee8-4c05-9592-c535a21b502c/download)].

**What a day trader should take from it.**
- "Gaps always fill" is not supported; index-level evidence says gap days tend to continue.
- For single stocks, whether a gap continues or reverses seems to depend on **news**: news-driven
  moves tend to continue, no-news moves tend to reverse. Attention-driven retail buying at the open
  makes the open price of hot stocks too high on average (Berkman et al.).
- Buying a hot stock at the open has a hidden cost beyond the spread.

---

## 4. Relative volume, "stocks in play" and attention

**What it is.** *Relative volume* (RVOL) compares today's volume, at a given time of day, with the
normal volume for that time. High RVOL marks a stock that the market is paying attention to.

| Study | Sample | Finding | Holds up? |
|---|---|---|---|
| Gervais, Kaniel & Mingelgrin (2001), "The high-volume return premium", *J. Finance* 56(3):877-919 ([author page](https://sites.duke.edu/sgervais/?p=64)) | NYSE stocks, daily/weekly | Stocks with unusually high (low) volume over a day or week tend to rise (fall) over the **following month**; stronger when the volume is not accompanied by an extreme return. | Multi-week horizon, not intraday. Later work ties it to fundamentals ([JFE 2021](https://ideas.repec.org/a/eee/jfinec/v140y2021i1p325-345.html)). |
| Barber & Odean (2008), "All that glitters: The effect of attention and news on the buying behavior of individual and institutional investors", *RFS* 21(2):785-818 ([RePEc](https://econpapers.repec.org/RePEc:oup:rfinst:v:21:y:2008:i:2:p:785-818)) | US brokerage data | Individuals are net **buyers** of attention-grabbing stocks (news, abnormal volume, extreme one-day returns). | Robust and widely replicated. |
| Barber, Huang, Odean & Schwarz (2022), "Attention-induced trading and returns: Evidence from Robinhood users", *J. Finance* 77(6):3141-3190 ([RePEc](https://econpapers.repec.org/RePEc:bla:jfinan:v:77:y:2022:i:6:p:3141-3190)) | Robinhood holdings, 2018-2020 | Intense Robinhood herding into a stock forecasts **negative** returns: top stocks bought each day average -4.7% abnormal return over 20 days. | Peer reviewed; recent. |
| Zarattini, Barbon & Aziz (2024) (Section 1) | 7,000+ US stocks | ORB worked far better on top relative-volume names. | Author backtest. |

No peer-reviewed US study was found that tests whether abnormal *opening* stock volume predicts
the rest-of-day return in the cross-section [gap in evidence]. A study of option volume in the
first 30 minutes (Bergsma, Fodor, Singal & Tayal 2020, *J. Financial Research*) reports it predicts
rest-of-day stock returns, more strongly after overnight earnings ([vLex listing](https://law-journals-books.vlex.com/vid/option-trading-after-the-855622256)) [abstract only].

**What a day trader should take from it.** High relative volume tells you *where* the action is,
not which *direction* it will go. Attention pulls in retail buyers and can push prices too high
(negative returns afterwards in Robinhood data). RVOL is best used as a filter, with direction
coming from something else, and its sign needs to be tested.

---

## 5. VWAP (volume-weighted average price)

**What it is.** VWAP = sum(price x volume) / sum(volume) since the open. Institutions use it mainly
as an **execution benchmark**: a broker asked to fill an order "at VWAP" slices it across the day in
proportion to expected volume. Berkowitz, Logue & Noser (1988) proposed it as the benchmark price a
passive trader would get. Traders read price above VWAP as buyers in control and below as sellers.

| Study | Sample | Finding | Holds up? |
|---|---|---|---|
| Berkowitz, Logue & Noser (1988), "The total cost of transactions on the NYSE", *J. Finance* 43:97-112 (cited via [Madhavan 2002](https://www.smallake.kr/wp-content/uploads/2014/07/TP_Spring_2002_Madhavan.pdf)) | NYSE institutional trades | Introduced VWAP as an execution-cost benchmark; total costs (commission + impact) averaged about 23 bps. | Foundational; benchmark use is universal. |
| Madhavan (2002), "VWAP strategies", *Investment Guides / Transaction Performance* ([PDF](https://www.smallake.kr/wp-content/uploads/2014/07/TP_Spring_2002_Madhavan.pdf)) | Review | VWAP is simple but harder to execute than believed, and understates costs when the stock is trending. | Review, not a signal test. |
| Zarattini & Aziz (2023), VWAP trend rule on QQQ/TQQQ ([Concretum summary](https://concretumgroup.com/volume-weighted-average-price-vwap-the-holy-grail-for-day-trading-systems/)) | QQQ/TQQQ 1-minute, 2018-2023 | Long above VWAP, short below; large reported returns on TQQQ. | Author backtest. QuantConnect users report much lower returns once spreads are modelled [secondary, forum]. Not peer reviewed. |

No peer-reviewed study was found showing that "price above/below VWAP" predicts returns for
individual US stocks after costs [gap in evidence].

**What a day trader should take from it.** VWAP is real in the sense that big orders are worked
against it, so it is a meaningful reference price. Evidence that crossing VWAP is a profitable signal
is limited to author backtests on index ETFs. Distance from VWAP is a useful feature to test.

---

## 6. Time-of-day patterns, market intraday momentum and end-of-day effects

**What it is.** Volume and volatility are high at the open, low at midday, and high again into the
close (a "U shape"). Several studies find that returns in some parts of the day predict returns
later in the day, at the market level (momentum) and across stocks (reversal or periodicity).

| Study | Sample | Finding | Holds up? |
|---|---|---|---|
| Wood, McInish & Ord (1985), "An investigation of transactions data for NYSE stocks", *J. Finance* 40(3):723-739 [unverified: citation from memory; search found it only as a citation] | NYSE minute data | Returns and volatility higher at the open and close (U-shaped). | U-shape is one of the most replicated facts in microstructure. |
| Admati & Pfleiderer (1988), "A theory of intraday patterns: Volume and price variability", *RFS* 1(1):3-40 ([listing](https://academicnewsletter.sufe.edu.cn/info/355980)) | Theory | Discretionary liquidity traders and informed traders cluster at the same times, producing concentrated volume and volatility. | Theory. |
| Heston, Korajczyk & Sadka (2010), "Intraday patterns in the cross-section of stock returns", *J. Finance* 65(4):1369-1407 ([arXiv](https://arxiv.org/pdf/1005.3535.pdf), [RePEc](https://econpapers.repec.org/RePEc:bla:jfinan:v:65:y:2010:i:4:p:1369-1407)) | US stocks, 13 half-hour intervals | A stock's return in a half-hour slot predicts its return **in the same slot on following days**, for at least 40 trading days; strongest in first and last half hours. Short-term reversal at sub-hour horizons is driven by liquidity imbalances and bid-ask bounce. | Published; not explained by size, risk or S&P membership. |
| Gao, Han, Li & Zhou (2018), "Market intraday momentum", *JFE* 129(2):394-414 ([RePEc](https://econpapers.repec.org/RePEc:eee:jfinec:v:129:y:2018:i:2:p:394-414)) | SPY, 1993-2013; 10 other ETFs | The first half-hour return (from prior close) predicts the **last half-hour** return; out-of-sample R² about 1.2%; stronger on volatile, high-volume, recession and macro-news days; authors say it survives reasonable costs. | Mixed after publication: Rosa (2022) finds the overnight-return version's predictability **disappears out of sample** ([RePEc](https://econpapers.repec.org/RePEc:wly:jfutmk:v:42:y:2022:i:12:p:2218-2234)) [abstract fragments]. QuantConnect replication reports lower returns [secondary, [QuantConnect](https://www.quantconnect.com/research/15348/intraday-etf-momentum/)]. |
| Li, Sakkas & Urquhart (2022), "Intraday time series momentum: Global evidence and links to market characteristics", *J. Financial Markets* 57:100619 ([accepted version](https://centaur.reading.ac.uk/95566)) | 16 developed markets | First-half-hour return predicts last half hour; a working-paper version reports positive returns in 13 markets and Sharpe above buy-and-hold in 12. | International replication, mostly positive. |
| Baltussen, Da, Lammers & Martens (2021), "Hedging demand and market intraday momentum", *JFE* 142(1):377-403 ([PDF](https://www3.nd.edu/~zda/intramom.pdf)) | 60+ futures, 1974-2020 | Market intraday momentum everywhere; driven by short-gamma hedging (options dealers, leveraged ETFs) that trades with the move late in the day. | Long sample; mechanism documented. |
| Soebhag, Baltussen & Da, "End-of-day reversal" (working paper, about 2025) ([PDF](https://www3.nd.edu/~zda/EOD.pdf), [OptionMetrics](https://optionmetrics.com/research/a-soebhag-g-baltussen-and-z-da-end-of-day-reversal/)) | US stocks | Across **individual stocks**, the return earlier in the day negatively predicts the last-30-minute return (a reversal), opposite to the market-level momentum; strongest for intraday losers; linked to retail attention buying and short-seller risk management. | Working paper; 2nd place Quantpedia Awards 2025. Not yet peer reviewed. |
| Bogousslavsky (2021), "The cross-section of intraday and overnight returns", *JFE* 141(1):172-194 ([RePEc](https://econpapers.repec.org/RePEc:eee:jfinec:v:141:y:2021:i:1:p:172-194)) | US stocks, 1985-2015, half-hour returns | A mispricing factor earns positive returns during the day but does poorly in the last half hour, as arbitrageurs cut positions before the close (overnight margin, lending fees); stronger in later years. | Published. |

**What a day trader should take from it.**
- The open and the last half hour are when volume, volatility and most documented effects concentrate.
  Midday is quieter and costs are relatively higher per unit of movement.
- **Market (index) level:** morning direction tends to continue into the close, more so on volatile
  days and when dealers are short gamma. Evidence after 2013 is mixed for the simplest version.
- **Single stocks:** the opposite at the close: intraday winners/losers tend to *reverse* in the last
  30 minutes. Do not assume an index pattern applies to individual names.

---

## 7. Short-term reversal and momentum at intraday horizons (cross-section)

**What it is.** Comparing stocks with each other: do the biggest gainers of the last few minutes or
hours keep going (momentum) or give some back (reversal)? A key trap is *bid-ask bounce*: if the last
trade was at the ask, the next is equally likely at the bid, which creates fake reversals in
trade-price data.

| Study | Sample | Finding | Holds up? |
|---|---|---|---|
| Heston, Korajczyk & Sadka (2010) (Section 6) | US stocks | Sub-hour reversal is driven by temporary liquidity imbalances lasting under an hour and by bid-ask bounce. | Published. |
| Komarov (2017), "Intra-day momentum", SSRN 2905713 [ID from a Scribd copy, unverified] ([thesis PDF](https://core.ac.uk/download/110622491.pdf), [CXO summary](https://www.cxoadvisory.com/momentum-investing/intraday-stock-price-momentum-and-reversal-trading/)) | All US common stocks, 1993-2010 | Statistical predictability did not translate into profits; morning extreme winners and losers both earned above-average afternoon returns (U-shape). | Gross returns only; frictions likely erase it [secondary]. |
| Soebhag, Baltussen & Da (Section 6) | US stocks | End-of-day cross-sectional reversal. | Working paper. |
| Barbon & Buraschi, "Gamma fragility" (working paper, about 2020) ([author page](https://abarbon.com/papers/gamma-fragility)) | US stocks and options | Negative dealer gamma plus illiquidity goes with intraday momentum; positive gamma with reversal; strongest in illiquid stocks. | Working paper. |
| Barbon, Beckmeyer, Buraschi & Moerke (2021), "Liquidity provision to leveraged ETFs and equity options rebalancing flows: Evidence from end-of-day stock prices", SSRN 3925725 ([SSRN](https://papers.ssrn.com/abstract=3925725)) | US stocks | Large negative (positive) gamma imbalance relative to dollar volume gives end-of-day momentum (reversal), which reverts at the next open [secondary]. | Working paper. |

**What a day trader should take from it.** Short-horizon reversals in a single stock are real but
are largely the price of liquidity (bid-ask bounce, temporary imbalances) — i.e. they are the market
maker's income, not easily captured by someone paying the spread. Use bar closes with care: a
signal based on the last trade of a bar inherits bounce. Midpoint prices or volume-weighted bar
prices reduce this.

---

## 8. Day trader performance, costs, spreads, slippage and the PDT rule

**What it is.** How do real day traders do? And what does it cost to trade?

| Study | Sample | Finding | Holds up? |
|---|---|---|---|
| Barber, Lee, Liu & Odean (2014), "The cross-section of speculator skill: Evidence from day trading", *J. Financial Markets* 18:1-24 ([RePEc](https://econpapers.repec.org/RePEc:eee:finmar:v:18:y:2014:i:c:p:1-24), [working paper](https://faculty.haas.berkeley.edu/odean/papers/day%20traders/Day%20Trading%20Skill%20110523.pdf)) | All Taiwan day traders, 1992-2006 | About 360,000 day traders a year; working paper: about 1,000 a year predictably outperform; large cross-sectional differences before and after fees. | Complete-market data; robust. |
| Barber, Lee, Liu, Odean & Zhang (2020), "Learning, fast or slow", *Review of Asset Pricing Studies* 10(1):61-93 (earlier "Do day traders rationally learn about their ability?") ([RePEc](https://econpapers.repec.org/RePEc:oup:rasset:v:10:y:2020:i:1:p:61-93.), [working paper](https://faculty.haas.berkeley.edu/odean/papers/day%20traders/day%20trading%20and%20learning%20110217.pdf)) | Taiwan | Aggregate day-trader performance net of fees negative in every one of 15 years; most lose; only the prior year's top performers (under 1%) earn reliably positive net returns; losers keep trading. | Robust. The often-quoted "fewer than 1% profitable" is roughly this; exact % not verified. |
| Chague, De-Losso & Giovannetti (2020), "Day trading for a living?", SSRN 3423101 / FGV EESP TD 525 ([RePEc](https://econpapers.repec.org/RePEc:fgv:eesptd:525)) | All Brazilian individuals who day traded mini-index futures 300+ days, 2013-2015 | Most lost money; only 1.1% earned more than the Brazilian minimum wage, 0.5% more than a bank teller's starting salary. "Virtually impossible" to day trade for a living. | Widely cited. "97% lose money" figure is commonly quoted but was **not verified** here. |
| Jordan & Diltz (2003), "The profitability of day traders", *Financial Analysts Journal* 59(6):85-94 ([RePEc](https://econpapers.repec.org/RePEc:taf:ufajxx:v:59:y:2003:i:6:p:85-94)) | 7 offices of a US day-trading firm, 1998-1999 | About twice as many lost as made money; roughly 1 in 5 more than marginally profitable; profits tracked the Nasdaq. | Small US sample in a bubble. |
| Frazzini, Israel & Moskowitz (2018), "Trading costs", SSRN 3229719 ([SSRN](https://papers.ssrn.com/abstract=3229719), [summary](https://alphaarchitect.com/the-best-research-paper-ever-written-on-trading-costs/)) | $1.7T of AQR institutional trades, 21 markets | Market impact averages about 9 bps (large caps) vs about 19 bps (small caps) for trades completed within a day [secondary figures]. | Institutional, patient execution; a retail market order into a fast-moving open is not cheaper. |
| Berkman et al. (2012) (Section 3) | US | Buying high-attention stocks at the open costs more than the half-spread. | Published. |

**Pattern day trader (PDT) rule.** Under FINRA Rule 4210, four or more day trades in five business
days in a margin account (if they are more than 6% of trades) make you a pattern day trader, who
must keep $25,000 equity. FINRA filed SR-FINRA-2025-017 (Dec 2025) to replace the $25,000 minimum
with intraday margin standards ([FINRA filing](https://www.finra.org/sites/default/files/2025-12/SR-FINRA-2025-017.pdf),
[Federal Register, Apr 2026](https://www.federalregister.gov/documents/2026/04/17/2026-07485/self-regulatory-organizations-financial-industry-regulatory-authority-inc-notice-of-filing-of)).
A Schwab page is titled "SEC Approves Scrapping $25,000 Day Trader Minimum" ([Schwab](https://advisorservices.schwab.com/story/introduction-to-pattern-day-trader-rules)),
but final approval and the effective date were **not verified** here; check your broker.

**What a day trader should take from it.** The base rate is losing money, after costs, in every
complete-population dataset (Taiwan, Brazil). A small, persistent minority wins. Costs (spread,
slippage, commissions, fees) are the main reason gross edges disappear. Any backtest must charge
at least the quoted half-spread on each side plus slippage, and more for small caps at the open.

---

## 9. Other things with real evidence

| Topic | Study | Finding | Holds up? |
|---|---|---|---|
| Leveraged ETF rebalancing at the close | Cheng & Madhavan (2009), "The dynamics of leveraged and inverse exchange-traded funds", *J. Investment Management* 7(4) ([JOIM](https://joim.com/dynamics-leveraged-inverse-exchange-traded-funds)) | Daily re-leveraging means LETFs buy after up days and sell after down days near the close, which can add to volatility toward the close. | Mechanical; widely accepted. |
| | Shum, Hejazi, Haryanto & Rodier (2016), "Intraday share price volatility and leveraged ETF rebalancing", *Review of Finance* 20(6):2379-2409 ([RePEc](https://econpapers.repec.org/RePEc:oup:revfin:v:20:y:2016:i:6:p:2379-2409.)) | 2006-2011: end-of-day volatility tracks LETF rebalancing demand relative to volume; significant but not always economically large; strongest on volatile days. | Published. |
| Options hedging / gamma | Ni, Pearson, Poteshman & White (2021), "Does option trading have a pervasive impact on underlying stock prices?", *RFS* 34(4):1952-1986 ([RePEc](https://econpapers.repec.org/RePEc:oup:rfinst:v:34:y:2021:i:4:p:1952-1986.)) | When delta-hedgers are net long gamma, stock volatility is lower; net short gamma, higher; affects the probability of large moves. | Published. Earlier: Ni, Pearson & Poteshman (2005) find optioned stocks cluster at strikes on expiration dates ([NBER WP](https://www.nber.org/papers/w11843.pdf)) [NBER number from search; title not verified]. |
| | Baltussen et al. (2021) (Section 6) | Short gamma hedging creates market intraday momentum. | Published. |
| Earnings / news days | Lee (1992), *J. Accounting & Economics* (via [search summary](https://deepblue.lib.umich.edu/bitstream/2027.42/30006/1/0000374.pdf)) | Large-trade imbalance and price adjust to earnings news mostly within the first hour. | Old sample. |
| | Christensen, Timmermann & Veliyev (2023), CEPR DP18032 ([PDF](https://repec.cepr.org/repec/cpr/ceprdp/DP18032.pdf)) | Prices almost always jump at earnings announcements and absorb the news quickly; a post-announcement strategy is consistent with efficient pricing after 2016 [abstract]. | Working paper. |
| | Boudoukh et al. (2012), Chan (2003) (Section 3) | News moves continue; no-news moves reverse. | Published / NBER. |
| Closing auction | 2021 AEA paper ([link](https://aeaweb.org/conference/2021/preliminary/paper/H9T4hef7)); BlackRock (2020) ([PDF](https://BlackRock.com/corporate/literature/whitepaper/viewpoint-a-global-perspective-on-market-on-close-activity-july-2020.pdf)) | Closing auction share rose (about 3% of volume in 2010 to 7.5% in 2018; about 11.6% in Jan 2020); closing price pressure largely reverses overnight, fully for large caps [abstract/secondary]. | Descriptive. |
| Index reconstitution | Madhavan (2003), "The Russell reconstitution effect", *FAJ* 59(4):51-64 ([RePEc](https://econpapers.repec.org/RePEc:taf:ufajxx:v:59:y:2003:i:4:p:51-64)) | 1996-2002: returns around Russell reconstitution from temporary price pressure plus permanent effects. Later work: the reversal shrank or vanished in 2002-2005 ([EFMA 2007](https://efmaefm.org/0EFMAMEETINGS/EFMA%20ANNUAL%20MEETINGS/2007-Austria/papers/0693.pdf)); still visible but smaller 2014-2023 ([Dimensional](https://www.dimensional.com/us-en/insights/even-migrating-stocks-face-index-reconstitution-costs)). | Decayed after publication. |
| Short-sale restriction (Rule 201) | SEC Rule 201 ([adopting release](https://sec.gov/files/rules/final/2010/34-61595.pdf)) | When a stock falls 10% or more from the prior close, short sales at or below the national best bid are barred for the rest of that day and the next. | Rule; parameters current as of the sources found, re-check. |
| Halts (LULD) | SEC DERA LULD white paper ([SEC](https://www.sec.gov/file/dera-luld-white-paperpdf)) | If a stock cannot trade inside its price band for 15 seconds, a 5-minute pause follows, reopening by auction (may extend). | Rule; band percentages not verified here. |
| Intraday trend on SPY | Zarattini, Aziz & Barbon (2024), "Beat the market: An effective intraday momentum strategy for S&P500 ETF (SPY)", SSRN 4824172 / SFI RP 24-97 ([SFI](https://www.sfi.ch/de/publications/n-24-97-beat-the-market-an-effective-intraday-momentum-strategy-for-s-p500-etf-spy)) | "Noise area" band from the past 14 days' average intraday moves; trade breakouts with trailing stops; 2007-2024 reported Sharpe 1.33 net. | Author backtest; no independent replication found. |

**What a day trader should take from it.** The close is crowded with mechanical flows (LETF
rebalancing, index funds, option hedgers) whose direction can be partly predicted from the day's
move; the open is crowded with attention-driven retail flow. On short-sale-restricted, halted or
earnings-day stocks, normal assumptions about fills and spreads do not hold.

---

## 10. Testable features for a whole-market 5-minute study

Bars are regular-session 5-minute bars stamped by their **start** time, New York time: bar 1 =
09:30-09:35, bar 6 = 09:55-10:00. "At 9:35" means only bar 1 is known; "at 10:00" means bars 1-6.
Let `O_t, H_t, L_t, C_t, V_t` be bar t's values. `PC` = previous regular-session close. Use only
data available at the decision time (no look-ahead). The suggested outcome to predict: return from
the decision time to a fixed exit (e.g. 10:30, 12:00, 15:55 close of last bar), measured on
**next-bar open** entry, net of a cost charge. Each feature's grounding is given; "untested" means
no direct evidence found for that exact feature.

### Gap and overnight

| Feature | Definition | Grounding |
|---|---|---|
| `gap` | `O_1 / PC - 1` | Sections 3 (Plastun 2020; Berkman 2012; Lou-Polk-Skouras 2019) |
| `abs_gap_atr` | `abs(O_1 - PC) / ATR14_daily` (ATR from prior 14 daily bars) | Normalised gap; untested at stock level |
| `gap_fill_frac` (at 10:00) | if gap > 0: `(O_1 - min(L_1..L_6)) / (O_1 - PC)`; mirror for gap < 0; capped to [0, 1+] | Gap-fill question, Section 3 |

### Opening range (first candle, first 30 minutes)

| Feature | Definition | Grounding |
|---|---|---|
| `or5_high`, `or5_low` | `H_1`, `L_1` | Zarattini et al. 2024 |
| `or5_range_pct` | `(H_1 - L_1) / O_1` | ORB papers |
| `or5_range_atr` | `(H_1 - L_1) / ATR14_daily` | Crabel contraction/expansion; untested in stocks |
| `or5_dir` | `sign(C_1 - O_1)` (ORB trades in this direction in Zarattini et al.) | Zarattini & Aziz 2023; Zarattini et al. 2024 |
| `or30_high/low` (at 10:00) | `max(H_1..H_6)`, `min(L_1..L_6)` | ORB variants |
| `break_or5` (at 10:00) | +1 if any `C_t > H_1` for t in 2..6, -1 if any `C_t < L_1`, 0 otherwise (first break wins) | ORB |
| `nr7_daily` | 1 if yesterday's daily range is the smallest of the last 7 days | Crabel (book; untested here) |

### Candle anatomy (per bar; aggregate over bars 1..k)

| Feature | Definition | Grounding |
|---|---|---|
| `body_frac` | `abs(C - O) / (H - L)`; 0 if `H = L` | Candlestick literature (Section 2) |
| `upper_wick_frac` | `(H - max(O, C)) / (H - L)` | Shooting star / rejection |
| `lower_wick_frac` | `(min(O, C) - L) / (H - L)` | Hammer / rejection |
| `clv` | `((C - L) - (H - C)) / (H - L)` in [-1, 1] | Close location value |
| `clv_30` (at 10:00) | CLV of the combined 09:30-10:00 bar: `O=O_1, H=max H, L=min L, C=C_6` | Same |

Note (Section 2): the only large 5-minute candlestick study found no rule surviving costs. Treat
these as features, and correct for multiple testing.

### Volume and attention

| Feature | Definition | Grounding |
|---|---|---|
| `rvol_open` | `sum(V_1..V_k) / mean over the prior 14 sessions of sum(V_1..V_k)` (same bars, same time of day) | Zarattini et al. 2024 (uses opening-range relative volume over 14 days); Barber & Odean 2008 |
| `rvol_bar1` | `V_1 / mean of V_1 over prior 14 sessions` | Same |
| `dollar_vol_open` | `sum(C_t * V_t)` for t = 1..k | Liquidity / cost filter (Section 8) |
| `avg_daily_vol_14` | mean daily share volume over prior 14 sessions | Zarattini filter (>= 1M shares) [secondary] |
| `vol_share_bar1` | `V_1 / sum(V_1..V_6)` (at 10:00) | U-shape (Section 6); untested |

### VWAP

| Feature | Definition | Grounding |
|---|---|---|
| `vwap_k` | `sum(TP_t * V_t) / sum(V_t)` over t = 1..k, `TP = (H + L + C) / 3` (5-minute approximation of true VWAP) | Berkowitz et al. 1988; Madhavan 2002 |
| `dist_vwap` | `C_k / vwap_k - 1` | Zarattini & Aziz VWAP rule (author backtest only) |
| `above_vwap_count` | number of bars t <= k with `C_t > vwap_t` | Untested |

### Returns, trend and volatility so far

| Feature | Definition | Grounding |
|---|---|---|
| `ret_open` | `C_k / O_1 - 1` (open to decision time) | Gao et al. 2018 (market level); EOD reversal (stock level) |
| `ret_from_pc` | `C_k / PC - 1` | Gao et al. 2018 use return since prior close |
| `ret_open_rank` | cross-sectional percentile of `ret_open` among all stocks at the same time | Heston et al. 2010; Komarov 2017; Soebhag et al. |
| `mkt_ret_open` | `ret_open` of SPY (or equal-weighted universe) | Market intraday momentum (Section 6) |
| `rel_ret_open` | `ret_open - beta * mkt_ret_open` (beta from prior 60 days of daily returns; or beta = 1) | Cross-sectional vs market split |
| `rv_open` | `sqrt(sum over t=2..k of ln(C_t / C_{t-1})^2)` plus `ln(C_1/O_1)^2` | Gao et al.: effect stronger on volatile days |
| `hl_range_open_atr` | `(max H - min L over 1..k) / ATR14_daily` | Range expansion |
| `same_slot_hist` | stock's mean return in the same 5- or 30-minute slot over prior 20-40 days | Heston, Korajczyk & Sadka 2010 periodicity |
| `prior_day_ret` | `PC / prior-prior close - 1` | Short-term reversal / attention |

### Context and cost flags (from daily data or calendars, known before the open)

| Feature | Definition | Grounding |
|---|---|---|
| `price` | `O_1`; filter e.g. > $5 | Zarattini filter [secondary]; costs |
| `spread_proxy` | if quotes unavailable, Corwin-Schultz high-low estimator over bars 1..k, or `(H_1 - L_1)` as an upper bound | Costs (Section 8) — estimator choice is a modelling decision |
| `earnings_day` | 1 if the company reported after the prior close or before today's open | News continuation (Section 3, 9) |
| `ssr_active` | 1 if prior-day close <= 0.9 x close two days earlier, or SSR triggered yesterday | Rule 201 |
| `opex_day`, `rebalance_day`, `month_end` | calendar flags (monthly options expiry Friday; Russell reconstitution; last trading day of month) | Section 9 |
| `halted_open` | 1 if any bar in 1..k has zero volume or a missing bar (proxy for LULD pause or late open) | LULD |

### Study hygiene (needed for any result to be believable)

1. Split by time: develop on one period, test once on a later held-out period.
2. Charge costs: at least half the quoted spread per side plus slippage; larger for price < $10 and
   for bar 1–2 entries.
3. Survivorship: include delisted stocks; use point-in-time universes.
4. Multiple testing: many features x horizons x thresholds will produce false winners; use a
   correction (e.g. White's reality check / SPA, as in Duvinage et al. 2013) or a hold-out.
5. Do not mix the market-level and stock-level signs: index momentum and stock-level reversal can
   both be true.
6. Report results by year; edges that live only in 2020-2021 are regime effects.
