from __future__ import annotations

from typing import Any

from .models import GateCheck, TimingStats, TrajectoryMetrics


def _check(name: str, value: float, threshold: float, unit: str) -> GateCheck:
    return GateCheck(name=name, value=value, threshold=threshold, passed=value <= threshold, unit=unit)


def evaluate_quality_gates(
    timing: list[TimingStats],
    sync_p95_ms: float,
    trajectory: TrajectoryMetrics,
    config: dict[str, Any],
) -> list[GateCheck]:
    checks = [
        _check("trajectory.ate_rmse", trajectory.ate_rmse_m, float(config["max_ate_rmse_m"]), "m"),
        _check("trajectory.rpe_rmse", trajectory.rpe_rmse_m, float(config["max_rpe_rmse_m"]), "m"),
        _check("trajectory.final_drift", trajectory.final_drift_m, float(config["max_final_drift_m"]), "m"),
        _check("trajectory.heading_rmse", trajectory.heading_rmse_deg, float(config["max_heading_rmse_deg"]), "deg"),
        _check(
            "trajectory.path_length_error",
            trajectory.path_length_error_pct,
            float(config["max_path_length_error_pct"]),
            "%",
        ),
        _check("sync.camera_lidar_p95", sync_p95_ms, float(config["max_camera_lidar_sync_p95_ms"]), "ms"),
    ]
    jitter_limits = config["max_jitter_rms_ms"]
    for stats in timing:
        checks.extend(
            [
                _check(f"timing.{stats.sensor}.jitter_rms", stats.jitter_rms_ms, float(jitter_limits[stats.sensor]), "ms"),
                _check(f"timing.{stats.sensor}.dropout_rate", stats.dropout_rate, float(config["max_dropout_rate"]), "ratio"),
                _check(
                    f"timing.{stats.sensor}.out_of_order",
                    float(stats.out_of_order_count),
                    float(config["max_out_of_order_count"]),
                    "count",
                ),
            ]
        )
    return checks
