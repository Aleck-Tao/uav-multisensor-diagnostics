from __future__ import annotations

import csv
from pathlib import Path

import numpy as np


NOMINAL_HZ = {"camera": 30.0, "lidar": 10.0, "imu": 100.0}


def _reference_trajectory(duration_s: float = 30.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    t = np.arange(0.0, duration_s + 1e-9, 0.05)
    x = 0.36 * t + 0.55 * np.sin(0.31 * t)
    y = 1.65 * np.sin(0.18 * t) + 0.22 * np.cos(0.61 * t)
    z = 1.45 + 0.08 * np.sin(0.27 * t)
    dx = np.gradient(x, t)
    dy = np.gradient(y, t)
    yaw = np.arctan2(dy, dx)
    return t, np.column_stack((x, y, z)), yaw


def _estimated_trajectory(
    t: np.ndarray,
    reference: np.ndarray,
    yaw: np.ndarray,
    scenario: str,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    if scenario == "baseline":
        global_yaw_deg, noise_m, drift_rate = 1.5, 0.018, np.array([0.0020, -0.0010, 0.0004])
        heading_noise_deg, heading_drift_deg_s = 0.35, 0.025
    elif scenario == "degraded":
        global_yaw_deg, noise_m, drift_rate = 3.0, 0.055, np.array([0.0180, -0.0100, 0.0020])
        heading_noise_deg, heading_drift_deg_s = 1.8, 0.16
    else:
        raise ValueError("scenario must be 'baseline' or 'degraded'")

    theta = np.deg2rad(global_yaw_deg)
    rotation = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    xy = reference[:, :2] @ rotation.T + np.array([0.42, -0.27])
    estimate = np.column_stack((xy, reference[:, 2] + 0.06))
    estimate += t[:, None] * drift_rate
    estimate += rng.normal(0.0, noise_m, size=estimate.shape)

    if scenario == "degraded":
        affected = (t >= 12.0) & (t <= 16.0)
        phase = (t[affected] - 12.0) / 4.0 * np.pi
        estimate[affected, 0] += 0.28 * np.sin(phase)
        estimate[affected, 1] -= 0.20 * np.sin(phase)

    estimate_yaw = (
        yaw
        + theta
        + np.deg2rad(heading_drift_deg_s) * t
        + rng.normal(0.0, np.deg2rad(heading_noise_deg), size=t.shape)
    )
    return estimate, estimate_yaw


def _timing_rows(scenario: str, rng: np.random.Generator, duration_s: float = 30.0) -> list[dict[str, object]]:
    if scenario == "baseline":
        jitter_s = {"camera": 0.00035, "lidar": 0.00070, "imu": 0.00008}
        lidar_offset_s = 0.0008
    else:
        jitter_s = {"camera": 0.0032, "lidar": 0.0055, "imu": 0.00075}
        lidar_offset_s = 0.0170

    rows: list[dict[str, object]] = []
    for sensor, hz in NOMINAL_HZ.items():
        sequence = np.arange(int(duration_s * hz), dtype=int)
        timestamps = sequence / hz + rng.normal(0.0, jitter_s[sensor], size=sequence.shape)
        if sensor == "lidar":
            timestamps += lidar_offset_s

        keep = np.ones(sequence.shape, dtype=bool)
        if scenario == "degraded":
            if sensor == "camera":
                keep[(sequence > 0) & (sequence % 109 == 0)] = False
            elif sensor == "lidar":
                keep[(sequence > 0) & (sequence % 37 == 0)] = False
            else:
                keep[(sequence > 0) & (sequence % 197 == 0)] = False
        sequence = sequence[keep]
        timestamps = timestamps[keep]

        if scenario == "degraded" and sensor == "camera" and len(timestamps) > 42:
            timestamps[[40, 41]] = timestamps[[41, 40]]

        for seq, timestamp in zip(sequence, timestamps, strict=True):
            rows.append({"sensor": sensor, "sequence": int(seq), "timestamp_s": float(timestamp)})
    return rows


def _write_trajectory(path: Path, t: np.ndarray, positions: np.ndarray, yaw: np.ndarray) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["timestamp_s", "x_m", "y_m", "z_m", "yaw_rad"])
        for timestamp, position, heading in zip(t, positions, yaw, strict=True):
            writer.writerow(
                [
                    f"{timestamp:.6f}",
                    f"{position[0]:.6f}",
                    f"{position[1]:.6f}",
                    f"{position[2]:.6f}",
                    f"{heading:.8f}",
                ]
            )


def generate_scenario(scenario: str, output_dir: Path, seed: int = 20260706) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    scenario_seed = seed if scenario == "baseline" else seed + 1
    rng = np.random.default_rng(scenario_seed)
    t, reference, yaw = _reference_trajectory()
    estimate, estimate_yaw = _estimated_trajectory(t, reference, yaw, scenario, rng)
    _write_trajectory(output_dir / "reference_trajectory.csv", t, reference, yaw)
    _write_trajectory(output_dir / "estimated_trajectory.csv", t, estimate, estimate_yaw)

    rows = _timing_rows(scenario, rng)
    with (output_dir / "sensor_timestamps.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["sensor", "sequence", "timestamp_s"], lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "timestamp_s": f"{float(row['timestamp_s']):.8f}"})
