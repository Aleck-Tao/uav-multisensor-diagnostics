from __future__ import annotations

import numpy as np

from .models import TrajectoryData, TrajectoryMetrics


def _wrap_angle(angle: np.ndarray) -> np.ndarray:
    return (angle + np.pi) % (2.0 * np.pi) - np.pi


def _rigid_align_xy(source: np.ndarray, target: np.ndarray) -> tuple[np.ndarray, float]:
    source_mean = np.mean(source, axis=0)
    target_mean = np.mean(target, axis=0)
    source_centered = source - source_mean
    target_centered = target - target_mean
    covariance = source_centered.T @ target_centered
    u, _, vt = np.linalg.svd(covariance)
    rotation = u @ vt
    if np.linalg.det(rotation) < 0:
        u[:, -1] *= -1
        rotation = u @ vt
    aligned = source_centered @ rotation + target_mean
    row_rotation_angle = float(np.arctan2(rotation[0, 1], rotation[0, 0]))
    return aligned, row_rotation_angle


def analyze_trajectory(reference: TrajectoryData, estimate: TrajectoryData, rpe_horizon_s: float = 1.0) -> TrajectoryMetrics:
    start = max(float(reference.timestamps_s[0]), float(estimate.timestamps_s[0]))
    end = min(float(reference.timestamps_s[-1]), float(estimate.timestamps_s[-1]))
    mask = (estimate.timestamps_s >= start) & (estimate.timestamps_s <= end)
    timestamps = estimate.timestamps_s[mask]
    estimated_positions = estimate.positions_m[mask]
    estimated_yaw = estimate.yaw_rad[mask]
    if len(timestamps) < 10:
        raise ValueError("Trajectories do not have enough overlapping samples")

    reference_positions = np.column_stack(
        [np.interp(timestamps, reference.timestamps_s, reference.positions_m[:, axis]) for axis in range(3)]
    )
    reference_yaw = np.interp(timestamps, reference.timestamps_s, np.unwrap(reference.yaw_rad))

    aligned_xy, yaw_correction = _rigid_align_xy(estimated_positions[:, :2], reference_positions[:, :2])
    aligned_z = estimated_positions[:, 2] - np.mean(estimated_positions[:, 2] - reference_positions[:, 2])
    aligned_positions = np.column_stack((aligned_xy, aligned_z))
    errors = np.linalg.norm(aligned_positions - reference_positions, axis=1)

    median_period = float(np.median(np.diff(timestamps)))
    horizon_steps = max(1, int(round(rpe_horizon_s / median_period)))
    estimate_motion = aligned_positions[horizon_steps:] - aligned_positions[:-horizon_steps]
    reference_motion = reference_positions[horizon_steps:] - reference_positions[:-horizon_steps]
    relative_errors = np.linalg.norm(estimate_motion - reference_motion, axis=1)

    heading_errors = _wrap_angle(estimated_yaw + yaw_correction - reference_yaw)
    # Estimate path length at the same one-second support used for RPE.  Summing
    # frame-to-frame motion would turn zero-mean localization noise into a large
    # positive distance bias and would not reflect travelled distance.
    coarse_estimate = aligned_positions[::horizon_steps]
    coarse_reference = reference_positions[::horizon_steps]
    estimate_length = float(np.sum(np.linalg.norm(np.diff(coarse_estimate, axis=0), axis=1)))
    reference_length = float(np.sum(np.linalg.norm(np.diff(coarse_reference, axis=0), axis=1)))

    return TrajectoryMetrics(
        sample_count=len(timestamps),
        ate_rmse_m=float(np.sqrt(np.mean(errors**2))),
        ate_p95_m=float(np.percentile(errors, 95)),
        rpe_rmse_m=float(np.sqrt(np.mean(relative_errors**2))),
        final_drift_m=float(errors[-1]),
        heading_rmse_deg=float(np.rad2deg(np.sqrt(np.mean(heading_errors**2)))),
        path_length_error_pct=float(abs(estimate_length - reference_length) / reference_length * 100.0),
    )
