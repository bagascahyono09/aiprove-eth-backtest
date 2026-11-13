#!/usr/bin/env python3
"""Backtest close-decided positions against the following bar."""

from __future__ import annotations

import argparse
import csv
from collections.abc import Sequence
from pathlib import Path


def backtest(
    closes: Sequence[float],
    position_values: Sequence[float],
    fee_bps: float = 5.0,
    slip_bps: float = 2.0,
) -> tuple[float, float]:
    """Return additive net PnL and maximum drawdown, both in percent.

    A position selected at close t earns the close-to-close return from t to
    t+1. Trading cost is charged at t on the absolute position change.
    """
    if len(closes) != len(position_values):
        raise ValueError("closes and positions must have equal lengths")
    if fee_bps < 0 or slip_bps < 0:
        raise ValueError("fee and slippage must be non-negative")
    if any(position not in (-1, 0, 1) for position in position_values):
        raise ValueError("positions must contain only -1, 0, or 1")

    pnl = 0.0
    equity = [0.0]
    previous_position = 0.0
    cost_rate = (fee_bps + slip_bps) / 10_000.0

    for index in range(len(closes) - 1):
        if closes[index] == 0:
            raise ValueError(f"close at index {index} is zero")
        position = position_values[index]
        pnl += position * (closes[index + 1] - closes[index]) / closes[index]
        pnl -= abs(position - previous_position) * cost_rate
        previous_position = position
        equity.append(pnl)

    peak = float("-inf")
    max_drawdown = 0.0
    for value in equity:
        peak = max(peak, value)
        max_drawdown = max(max_drawdown, peak - value)

    return pnl * 100.0, max_drawdown * 100.0


def read_closes(path: Path) -> tuple[list[str], list[float]]:
    """Read minute and close columns from an OHLC bars CSV."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"minute", "close"}
        missing = required.difference(reader.fieldnames or ())
        if missing:
            raise ValueError(f"missing required columns: {', '.join(sorted(missing))}")

        minutes: list[str] = []
        closes: list[float] = []
        for line_number, row in enumerate(reader, start=2):
            try:
                minutes.append(row["minute"])
                closes.append(float(row["close"]))
            except (TypeError, ValueError) as error:
                raise ValueError(f"invalid close on CSV line {line_number}") from error

    if not minutes:
        raise ValueError("bars CSV contains no data rows")
    return minutes, closes


def read_positions(path: Path) -> tuple[list[str], list[int]]:
    """Read minute and position columns from a positions CSV."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"minute", "position"}
        missing = required.difference(reader.fieldnames or ())
        if missing:
            raise ValueError(f"missing required columns: {', '.join(sorted(missing))}")

        minutes: list[str] = []
        values: list[int] = []
        for line_number, row in enumerate(reader, start=2):
            try:
                minutes.append(row["minute"])
                value = int(row["position"])
            except (TypeError, ValueError) as error:
                raise ValueError(f"invalid position on CSV line {line_number}") from error
            if value not in (-1, 0, 1):
                raise ValueError(f"position on CSV line {line_number} is not -1, 0, or 1")
            values.append(value)

    if not minutes:
        raise ValueError("positions CSV contains no data rows")
    return minutes, values


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "bars",
        nargs="?",
        type=Path,
        default=Path("bars.csv"),
        help="OHLC bars CSV (default: ./bars.csv)",
    )
    parser.add_argument(
        "positions",
        nargs="?",
        type=Path,
        default=Path("positions.csv"),
        help="positions CSV (default: ./positions.csv)",
    )
    parser.add_argument("--fee-bps", type=float, default=5.0)
    parser.add_argument("--slip-bps", type=float, default=2.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    bar_minutes, closes = read_closes(args.bars)
    position_minutes, values = read_positions(args.positions)
    if bar_minutes != position_minutes:
        raise ValueError("bars and positions minutes do not align")

    net_pnl, max_drawdown = backtest(closes, values, args.fee_bps, args.slip_bps)
    print(f"net PnL: {net_pnl:+.2f}%")
    print(f"max drawdown: {max_drawdown:.2f}%")


if __name__ == "__main__":
    main()
