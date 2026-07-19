from __future__ import annotations

from collections import defaultdict

import numpy as np

from .models import TimingStats
from .simulate import NOMINAL_HZ


def analyze_timing(rows: list[dict[str, float | int | str]]) -> list[TimingStats]:
    grouped: dict[str, list[dict[str, float | int | str]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["sensor"])].append(row)

    results: list[TimingStats] = []
    for sensor in sorted(grouped):
        samples = grouped[sensor]
        if sensor not in NOMINAL_HZ:
            raise ValueError(f"Unknown sensor '{sensor}'; expected one of {sorted(NOMINAL_HZ)}")
        timestamps = np.asarray([float(row["timestamp_s"]) for row in samples])
        sequences = np.asarray([int(row["sequence"]) for row in samples])
        if len(timestamps) < 3:
            raise ValueError(f"Sensor '{sensor}' needs at least three timestamps")

        time_deltas = np.diff(timestamps)
        sequence_deltas = np.diff(sequences)
        out_of_order = int(np.sum(time_deltas <= 0))
        valid = (time_deltas > 0) & (sequence_deltas > 0)
        normalized_periods = time_deltas[valid] / sequence_deltas[valid]
        nominal_period = 1.0 / NOMINAL_HZ[sensor]
        jitter_rms_ms = float(np.sqrt(np.mean((normalized_periods - nominal_period) ** 2)) * 1000.0)
        dropouts = int(np.sum(np.maximum(sequence_deltas - 1, 0)))
        expected_samples = len(samples) + dropouts
        duration = float(np.max(timestamps) - np.min(timestamps))
        observed_hz = float((int(np.max(sequences)) - int(np.min(sequences))) / duration)
        results.append(
            TimingStats(
                sensor=sensor,
                sample_count=len(samples),
                nominal_hz=NOMINAL_HZ[sensor],
                observed_hz=observed_hz,
                jitter_rms_ms=jitter_rms_ms,
                max_gap_ms=float(np.max(np.abs(time_deltas)) * 1000.0),
                estimated_dropouts=dropouts,
                dropout_rate=float(dropouts / max(expected_samples, 1)),
                out_of_order_count=out_of_order,
            )
        )
    return results


def camera_lidar_sync_p95_ms(rows: list[dict[str, float | int | str]]) -> float:
    by_sensor: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_sensor[str(row["sensor"])].append(float(row["timestamp_s"]))
    if not by_sensor["camera"] or not by_sensor["lidar"]:
        raise ValueError("camera and lidar timestamps are required for synchronization analysis")

    camera = np.sort(np.asarray(by_sensor["camera"]))
    lidar = np.sort(np.asarray(by_sensor["lidar"]))
    indices = np.searchsorted(camera, lidar)
    left = np.clip(indices - 1, 0, len(camera) - 1)
    right = np.clip(indices, 0, len(camera) - 1)
    errors = np.minimum(np.abs(lidar - camera[left]), np.abs(lidar - camera[right]))
    return float(np.percentile(errors, 95) * 1000.0)
