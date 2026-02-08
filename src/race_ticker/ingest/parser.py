"""CSV parsing and validation into canonical RaceState."""

import csv
import io
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal


@dataclass
class RunnerState:
    """Single runner state from CSV."""
    runner_number: int
    lap_number: int
    lap_time_str: str
    distance_str: str | None


@dataclass
class RaceState:
    """Canonical race state (max 10 runners)."""
    updated_at_utc: datetime
    runners: list[RunnerState]
    distance_label: str | None
    source: Literal["live", "simulate"]


# CSV has no header; columns are always: runner number, lap number, lap time, distance
COL_RUNNER = 0
COL_LAP = 1
COL_LAP_TIME = 2
COL_DISTANCE = 3


def parse_csv(csv_bytes: bytes, config: dict) -> RaceState:
    """Parse CSV bytes into RaceState. Raises ValueError on validation failure.

    CSV has no header row. Column order is fixed: runner number, lap number, lap time, distance.
    Uses display.max_runners for clamp. Dedupes by runner_number (keep highest lap_number).
    Uses display.sort_runners: 'runner' = by runner number, 'csv_order' = order of first appearance in CSV.
    """
    display = config.get("display", {})
    max_runners = int(display.get("max_runners", 10))
    sort_runners = (display.get("sort_runners") or "runner").strip().lower()
    if sort_runners not in ("runner", "csv_order"):
        sort_runners = "runner"

    try:
        text = csv_bytes.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValueError(f"CSV decode failed: {e}") from e

    reader = csv.reader(io.StringIO(text))
    by_runner: dict[int, tuple[int, str, str | None]] = {}
    csv_order: list[int] = []  # runner numbers in order of first appearance

    for i, row in enumerate(reader):
        if len(row) < 3:
            raise ValueError(f"Row {i + 1}: need at least 3 columns (runner, lap, lap_time)")
        try:
            rn = int(row[COL_RUNNER].strip())
            ln = int(row[COL_LAP].strip())
            lt = str(row[COL_LAP_TIME]).strip()
            dist = (row[COL_DISTANCE].strip()) if len(row) > COL_DISTANCE else ""
            dist = dist or None
        except (ValueError, TypeError) as e:
            raise ValueError(f"Row {i + 1}: invalid or missing field: {e}") from e
        if not lt:
            raise ValueError(f"Row {i + 1}: lap_time is empty")
        if rn not in by_runner or ln >= by_runner[rn][0]:
            by_runner[rn] = (ln, lt, dist)
        if rn not in csv_order:
            csv_order.append(rn)

    if sort_runners == "csv_order":
        ordered = [(rn, by_runner[rn]) for rn in csv_order if rn in by_runner][:max_runners]
    else:
        ordered = sorted(by_runner.items(), key=lambda x: x[0])[:max_runners]

    runners = [
        RunnerState(
            runner_number=rn,
            lap_number=lap_number,
            lap_time_str=lap_time_str,
            distance_str=dist,
        )
        for rn, (lap_number, lap_time_str, dist) in ordered
    ]

    return RaceState(
        updated_at_utc=datetime.now(timezone.utc),
        runners=runners,
        distance_label=None,
        source="live",
    )
