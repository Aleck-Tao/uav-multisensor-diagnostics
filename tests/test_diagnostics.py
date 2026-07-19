from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from uavdiag.io import load_sensor_timestamps, load_trajectory
from uavdiag.pipeline import analyze_scenario
from uavdiag.reporting import _normalize_floats
from uavdiag.simulate import generate_scenario
from uavdiag.timing import analyze_timing, camera_lidar_sync_p95_ms
from uavdiag.trajectory import analyze_trajectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG = PROJECT_ROOT / "config" / "quality_gates.json"


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DiagnosticsTests(unittest.TestCase):
    def test_committed_metrics_ignore_platform_float_noise(self) -> None:
        windows_result = {
            "ate_rmse_m": 0.03699473286237801,
            "path_length_error_pct": 6.725621413593617,
        }
        linux_result = {
            "ate_rmse_m": 0.03699473286237783,
            "path_length_error_pct": 6.725621413593603,
        }
        self.assertEqual(_normalize_floats(windows_result), _normalize_floats(linux_result))

    def test_generator_is_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_path, second_path = Path(first), Path(second)
            generate_scenario("baseline", first_path)
            generate_scenario("baseline", second_path)
            for filename in ("reference_trajectory.csv", "estimated_trajectory.csv", "sensor_timestamps.csv"):
                self.assertEqual(file_hash(first_path / filename), file_hash(second_path / filename))

    def test_faults_are_detected_in_timing_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            generate_scenario("degraded", root)
            rows = load_sensor_timestamps(root / "sensor_timestamps.csv")
            timing = {item.sensor: item for item in analyze_timing(rows)}
            self.assertGreater(timing["lidar"].estimated_dropouts, 0)
            self.assertGreater(timing["camera"].out_of_order_count, 0)
            self.assertGreater(camera_lidar_sync_p95_ms(rows), 8.0)

    def test_baseline_trajectory_is_more_accurate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline, degraded = root / "baseline", root / "degraded"
            generate_scenario("baseline", baseline)
            generate_scenario("degraded", degraded)
            baseline_metrics = analyze_trajectory(
                load_trajectory(baseline / "reference_trajectory.csv"),
                load_trajectory(baseline / "estimated_trajectory.csv"),
            )
            degraded_metrics = analyze_trajectory(
                load_trajectory(degraded / "reference_trajectory.csv"),
                load_trajectory(degraded / "estimated_trajectory.csv"),
            )
            self.assertLess(baseline_metrics.ate_rmse_m, degraded_metrics.ate_rmse_m)
            self.assertLess(baseline_metrics.rpe_rmse_m, degraded_metrics.rpe_rmse_m)

    def test_quality_gate_separates_baseline_and_degraded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outcomes = {}
            for scenario in ("baseline", "degraded"):
                data_dir, results_dir = root / scenario, root / f"{scenario}-results"
                generate_scenario(scenario, data_dir)
                outcomes[scenario] = analyze_scenario(data_dir, CONFIG, results_dir, scenario)
                self.assertTrue((results_dir / "metrics.json").exists())
                self.assertTrue((results_dir / "report.md").exists())
                self.assertTrue((results_dir / "dashboard.svg").exists())
                json.loads((results_dir / "metrics.json").read_text(encoding="utf-8"))
            self.assertTrue(outcomes["baseline"].passed)
            self.assertFalse(outcomes["degraded"].passed)


if __name__ == "__main__":
    unittest.main()
