from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .gates import evaluate_quality_gates
from .io import load_sensor_timestamps, load_trajectory
from .models import AnalysisResult
from .reporting import write_outputs
from .simulate import generate_scenario
from .timing import analyze_timing, camera_lidar_sync_p95_ms
from .trajectory import analyze_trajectory


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def analyze_scenario(scenario_dir: Path, config_path: Path, output_dir: Path, scenario: str) -> AnalysisResult:
    reference_path = scenario_dir / "reference_trajectory.csv"
    estimate_path = scenario_dir / "estimated_trajectory.csv"
    timing_path = scenario_dir / "sensor_timestamps.csv"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    timing_rows = load_sensor_timestamps(timing_path)
    timing_stats = analyze_timing(timing_rows)
    sync_p95 = camera_lidar_sync_p95_ms(timing_rows)
    trajectory_metrics = analyze_trajectory(load_trajectory(reference_path), load_trajectory(estimate_path))
    checks = evaluate_quality_gates(timing_stats, sync_p95, trajectory_metrics, config)
    result = AnalysisResult(
        scenario=scenario,
        passed=all(check.passed for check in checks),
        timing=timing_stats,
        camera_lidar_sync_p95_ms=sync_p95,
        trajectory=trajectory_metrics,
        checks=checks,
        provenance={
            "generator": "uavdiag 1.0.0 deterministic fault-injection benchmark",
            "files": {
                reference_path.name: _sha256(reference_path),
                estimate_path.name: _sha256(estimate_path),
                timing_path.name: _sha256(timing_path),
                config_path.name: _sha256(config_path),
            },
        },
    )
    write_outputs(result, output_dir)
    return result


def run_benchmark(project_root: Path) -> dict[str, AnalysisResult]:
    config_path = project_root / "config" / "quality_gates.json"
    results: dict[str, AnalysisResult] = {}
    for scenario in ("baseline", "degraded"):
        scenario_dir = project_root / "data" / scenario
        generate_scenario(scenario, scenario_dir)
        results[scenario] = analyze_scenario(
            scenario_dir,
            config_path,
            project_root / "results" / scenario,
            scenario,
        )
    return results
