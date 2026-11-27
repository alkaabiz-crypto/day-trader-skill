# Pre-registration: "QQQ TREND" / "QQQ OG" style intraday bots (written 2026-11-27, before any run)

Source idea: Instagram reel (nickafischer, "How I built my trading bots in 5 steps"). Its dashboard shows
EMA 9/21/50, session VWAP, RSI14, opening-range break, VWAP cross, EMA50 cross, trend continuation,
trailing stop, chop filter, profit lock, daily loss limit, risk level, scalp/trend/both. Reel P&L is marketing, not evidence.
The reel trades 0DTE QQQ options; Exness has no options, so this tests the same entries on USTEC CFD.

Data: QQQ 5-minute bars, regular hours 9:30-16:00 NY.
- A: trader-lab/data/idx/qqq.json.gz, 2016-01 .. 2022-11 (no volume -> VWAP replaced by session TWAP of typical price).
- B: trader-lab/data/long/QQQ.json.gz, 2022-11 .. 2026-11 (real volume VWAP).  B is the main judgement period.
Exness proxy: 1 QQQ $ ~= 41 NDX points. 0.05 lot USTEC = $0.05/pt => ~$2.05 per $1 QQQ move.
Costs per round trip: 2.5 NDX pts (1.12 spread, wider near open, + slippage); stress 5 pts.

Frozen rules (signals on 5-min bar close, entry at that close; stops checked intrabar, filled at stop or at the open if it gaps through):
- Indicators: EMA9/21/50 on RTH closes (carried across days), session VWAP, RSI14, ATR14, ADX14.
- TREND (continuation): EMA9>EMA21>EMA50, close>VWAP, the bar's low touched EMA9 (pullback) and closed above EMA9,
  RSI14 between 50 and 70. Short = mirror (RSI 30-50).
- ORB: opening range = 9:30-9:45 high/low. Long on first 5-min close above OR high with close>VWAP and EMA9>EMA21;
  short mirror. Max one ORB per side per day.
- VWAP cross: close crosses VWAP (prev close on other side) with EMA9>EMA21>EMA50 (long) / mirror.
- EMA50 cross: close crosses EMA50 with close>VWAP and EMA9>EMA21 (long) / mirror.
- Bot "TREND" = TREND + ORB. Bot "OG" = VWAP cross + EMA50 cross + ORB.
- Chop filter: no entry when ADX14 < 20.
- No entries before 9:45 or after 15:30. Flat by 15:55 close. One position at a time.
- Exit: initial stop 1.0 x ATR14; after +1 ATR open profit, stop to breakeven (profit lock); trailing stop 1.5 x ATR14
  below the highest close since entry (above lowest for shorts). No fixed target.
- Daily loss limit: stop for the day after 2 losing trades. Max 6 trades/day.
Pass bar (all needed): B net > 0 at 2.5 pts with t >= 2 on daily P&L; A net > 0; still > 0 at 5 pts in B;
beats >= 95% of 200 random-entry placebos (same exits, same trades per day, random direction/time) in B;
worst drawdown at 0.05 lot < $200 in B.
Also reported, not used to pass: each signal alone, long-only, 1-min not available (5-min used).

Addendum 10:40 UTC, before any run (Hazza's third clip shows the exit menu: Original / Profit lock / Loss brake /
Profit brake / Quick target, and "a stop, a profit target"): added as reported variants, not pass-judged:
quick target at +1.0 ATR, target at +2.0 ATR, no loss brake. The reel uses 1-minute candles; only 5-minute
history exists for 2016-2026, so 5-minute is used.
