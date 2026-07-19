from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class TrajectoryData:
    timestamps_s: np.ndarray
    positions_m: np.ndarray
    yaw_rad: np.ndarray


@dataclass(frozen=True)
class TimingStats:
    sensor: str
    sample_count: int
    nominal_hz: float
    observed_hz: float
    jitter_rms_ms: float
    max_gap_ms: float
    estimated_dropouts: int
    dropout_rate: float
    out_of_order_count: int


@dataclass(frozen=True)
class TrajectoryMetrics:
    sample_count: int
    ate_rmse_m: float
    ate_p95_m: float
    rpe_rmse_m: float
    final_drift_m: float
    heading_rmse_deg: float
    path_length_error_pct: float


@dataclass(frozen=True)
class GateCheck:
    name: str
    value: float
    threshold: float
    passed: bool
    unit: str


@dataclass(frozen=True)
class AnalysisResult:
    scenario: str
    passed: bool
    timing: list[TimingStats]
    camera_lidar_sync_p95_ms: float
    trajectory: TrajectoryMetrics
    checks: list[GateCheck]
    provenance: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
