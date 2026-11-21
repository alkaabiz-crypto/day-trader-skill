# Paper simulator

An automatic, fully simulated day-trading account. It runs the pack's own
rules end to end with fake money, so you can see how they would have done
before any real money, or even a real paper brokerage account, is involved.

There is no broker, no order and no API key here. "Fills" are Yahoo's free
5-minute bars, written to `trader/paper/account.json` and `trader/paper/log.jsonl`.
It is not a skill (it has no `SKILL.md`), so it never runs unless you start it.

```bash
python3 trader-scanner/scan.py universe   # once: the stock list
python3 paper/paper.py prepare            # today's 100 most traded stocks
python3 paper/paper.py run                # ticks after every 5-minute bar until the close
python3 paper/paper.py status             # cash, open position, trades, profit and loss
python3 paper/paper.py tick --offline tests/fixtures/trader-timemachine/TSLA-60d5m.json.gz --now "2026-10-19 10:15"
python3 paper/paper.py reset              # start over
```

## The rules (edit `trader/paper/config.json`)

| step | rule | default |
| --- | --- | --- |
| scan | opening-range breakouts on the most traded stocks (trader-scanner's `scan_orb`) | 100 stocks, $5 and up |
| entry | a fresh trigger only: the breakout bar closed in the last 2 bars and price is still above the range | 9:50 AM to 3:30 PM ET |
| stop and target | opening-range midpoint, 1R target (trader-exit's `compute`, to the cent) | `target_r` 1.0 |
| size | max loss per trade / risk a share, capped by cash | $50 a trade, $5,000 start |
| limits | trades a day, daily loss limit, one position at a time | 3 trades, $150 |
| exit | stop, target, or flat by 3:55 PM | 12:55 PM on a 1:00 PM close |

The most traded fresh breakout wins when several fire at once.

## Honest fills

An entry fills at the close of the last completed bar. A stop fills at the
stop, or at the bar's open if the price gapped through it. A target fills at
the target or a better open. When one bar touches both, the stop is assumed
to come first. Real fills have spreads and slippage; these do not, so real
results would be somewhat worse.

On the reel's day (TSLA, Mon 2026-10-19) it buys 8 shares at $364.18 at 10:15
AM, stop $358.32, target $370.04, the same numbers as the README's example.

Not financial advice. A simulated profit is not a promise of a real one, and
most people who day trade lose money.

## Momentum forward test

`paper/momentum.py` is a second, slower test: one decision a month instead of
day trading. It holds the 10 stocks of a frozen 100-stock list
(`paper/forward/universe.json`, the most traded on 2026-11-20) with the best
return from 12 months ago to 1 month ago, equal weight, rebalanced at the
close of each month's first trading day, with 0.05 % costs. A simulated
$5,000 in SPY bought the same day is the benchmark.

```bash
python3 paper/momentum.py backtest   # the same rule on 10 years of history
python3 paper/momentum.py daily      # mark to market; rebalances when a new month begins
python3 paper/momentum.py status     # holdings and the score against SPY
```

The ledger, `paper/forward/momentum.json`, is committed so the test survives
a wiped machine. The backtest uses today's most traded stocks, the last
decade's winners, so it flatters the rule; only the forward record is free of
that bias, and it needs many months before it means anything.
