# ETH Donchian breakout backtest

This entry applies one symmetric, parameter-light trend strategy to the frozen
1,440 one-minute ETH bars in `bars.csv`.

## Strategy

At each bar close, the strategy compares the close with channels built only
from earlier bars:

- Enter or hold long (`+1`) when the close is above the highest high of the
  prior 240 bars.
- Enter or hold short (`-1`) when the close is below the lowest low of the
  prior 240 bars.
- While long, exit to flat (`0`) when the close is below the lowest low of the
  prior 120 bars. While short, use the mirrored highest-high exit.
- Remain in the current position otherwise. Positions are limited to
  `-1`, `0`, and `+1`, with no pyramiding.

The 240/120 entry and exit pair is deliberately simple. It avoids a collection
of fitted filters and thresholds; this matters because the held-out tail
punishes strategies that overfit the earlier bars.

## Backtest and costs

A position decided at close `t` is held over bar `t+1`, earning the additive
close-to-close return `(close[t+1] - close[t]) / close[t]`. A cost of
`abs(position[t] - position[t-1]) * (fee_bps + slip_bps) / 10,000` is charged
on each position change, so a direct reversal costs twice a flat-to-long or
flat-to-short entry. Equity starts at zero and maximum drawdown is the largest
peak-to-trough decline in cumulative net PnL. There is no forced liquidation
at the end of the sample.

The sandbox determines the exact fee schedule, so results are shown across a
7-13 bp total-cost band:

| Fee + slip | Net PnL | Max drawdown | Position changes |
| --- | ---: | ---: | ---: |
| 5 + 2 bp | +3.76% | 1.99% | 3 |
| 10 + 3 bp | +3.58% | 2.11% | 3 |

## Run

Generate `positions.csv` from the bundled bars:

    python3 strategy.py

Run the two cost cases:

    python3 backtest.py --fee-bps 5 --slip-bps 2
    python3 backtest.py --fee-bps 10 --slip-bps 3

Custom paths can be supplied positionally:

    python3 strategy.py path/to/bars.csv --output path/to/positions.csv
    python3 backtest.py path/to/bars.csv path/to/positions.csv --fee-bps 5 --slip-bps 2

`strategy.py` also exposes `positions(closes, highs, lows)` for direct use.
