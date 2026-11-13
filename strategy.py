#!/usr/bin/env python3
"""Generate Donchian breakout positions from OHLC bars."""

from __future__ import annotations

import argparse
import csv
from collections.abc import Sequence
from pathlib import Path

ENTRY_LOOKBACK = 240
EXIT_LOOKBACK = 120


def positions(
    closes: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
) -> list[int]:
    """Return positions decided at each close: short, flat, or long.

    Entry channels use the prior 240 bars and exit channels use the prior
    120 bars. The current bar is excluded from every channel.
    """
    if not (len(closes) == len(highs) == len(lows)):
        raise ValueError("closes, highs, and lows must have equal lengths")

    result = [0] * len(closes)
    current = 0

    for index, close in enumerate(closes):
        if index < ENTRY_LOOKBACK:
            continue

        entry_high = max(highs[index - ENTRY_LOOKBACK : index])
        entry_low = min(lows[index - ENTRY_LOOKBACK : index])

        if close > entry_high:
            current = 1
        elif close < entry_low:
            current = -1
        elif current == 1 and close < min(lows[index - EXIT_LOOKBACK : index]):
            current = 0
        elif current == -1 and close > max(highs[index - EXIT_LOOKBACK : index]):
            current = 0

        result[index] = current

    return result


def read_bars(path: Path) -> tuple[list[str], list[float], list[float], list[float]]:
    """Read minute, close, high, and low columns from a bars CSV."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"minute", "close", "high", "low"}
        missing = required.difference(reader.fieldnames or ())
        if missing:
            raise ValueError(f"missing required columns: {', '.join(sorted(missing))}")

        minutes: list[str] = []
        closes: list[float] = []
        highs: list[float] = []
        lows: list[float] = []
        for line_number, row in enumerate(reader, start=2):
            try:
                minutes.append(row["minute"])
                closes.append(float(row["close"]))
                highs.append(float(row["high"]))
                lows.append(float(row["low"]))
            except (TypeError, ValueError) as error:
                raise ValueError(f"invalid numeric value on CSV line {line_number}") from error

    if not minutes:
        raise ValueError("bars CSV contains no data rows")
    return minutes, closes, highs, lows


def write_positions(path: Path, minutes: Sequence[str], values: Sequence[int]) -> None:
    """Write minute-aligned positions to CSV."""
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("minute", "position"))
        writer.writerows(zip(minutes, values, strict=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "bars",
        nargs="?",
        type=Path,
        default=Path("bars.csv"),
        help="input OHLC CSV (default: ./bars.csv)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("positions.csv"),
        help="output positions CSV (default: ./positions.csv)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    minutes, closes, highs, lows = read_bars(args.bars)
    values = positions(closes, highs, lows)
    write_positions(args.output, minutes, values)

    changes = sum(previous != current for previous, current in zip(values, values[1:]))
    print(f"final position: {values[-1]}; changes: {changes}")


if __name__ == "__main__":
    main()
