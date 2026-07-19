from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from .models import TrajectoryData


TRAJECTORY_COLUMNS = ("timestamp_s", "x_m", "y_m", "z_m", "yaw_rad")
TIMING_COLUMNS = ("sensor", "sequence", "timestamp_s")


def _require_columns(fieldnames: list[str] | None, required: tuple[str, ...], path: Path) -> None:
    present = set(fieldnames or [])
    missing = [column for column in required if column not in present]
    if missing:
        raise ValueError(f"{path} is missing required columns: {', '.join(missing)}")


def load_trajectory(path: Path) -> TrajectoryData:
    rows: list[list[float]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        _require_columns(reader.fieldnames, TRAJECTORY_COLUMNS, path)
        for line_number, row in enumerate(reader, start=2):
            try:
                rows.append([float(row[column]) for column in TRAJECTORY_COLUMNS])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid numeric value in {path}:{line_number}") from exc

    if len(rows) < 3:
        raise ValueError(f"{path} must contain at least three trajectory samples")
    values = np.asarray(rows, dtype=float)
    if np.any(np.diff(values[:, 0]) <= 0):
        raise ValueError(f"{path} timestamps must be strictly increasing")
    return TrajectoryData(values[:, 0], values[:, 1:4], values[:, 4])


def load_sensor_timestamps(path: Path) -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        _require_columns(reader.fieldnames, TIMING_COLUMNS, path)
        for line_number, row in enumerate(reader, start=2):
            try:
                rows.append(
                    {
                        "sensor": str(row["sensor"]),
                        "sequence": int(row["sequence"]),
                        "timestamp_s": float(row["timestamp_s"]),
                    }
                )
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid timing value in {path}:{line_number}") from exc
    if not rows:
        raise ValueError(f"{path} contains no timing samples")
    return rows
