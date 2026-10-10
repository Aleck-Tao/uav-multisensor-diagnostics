import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path

from uavdiag.ablation import FAULTS, TIMING_FAULTS, generate_ablation_scenario, run_ablation


ROOT = Path(__file__).resolve().parents[1]


class AblationTests(unittest.TestCase):
    def test_each_fault_preserves_unaffected_inputs_for_multiple_seeds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for seed in (7, 20261010):
                baseline = root / str(seed) / "baseline"
                generate_ablation_scenario("baseline", baseline, seed)
                for fault in FAULTS:
                    destination = root / str(seed) / fault
                    generate_ablation_scenario(fault, destination, seed)
                    for name in ("reference_trajectory.csv", "estimated_trajectory.csv", "sensor_timestamps.csv"):
                        same = (baseline / name).read_bytes() == (destination / name).read_bytes()
                        expected = (fault == "baseline" or name == "reference_trajectory.csv"
                                    or (fault in TIMING_FAULTS and name == "estimated_trajectory.csv")
                                    or (fault not in TIMING_FAULTS and name == "sensor_timestamps.csv"))
                        self.assertEqual(same, expected, (seed, fault, name))

    def test_metrics_and_gate_responses_match_injected_faults(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "config").mkdir()
            shutil.copyfile(ROOT / "config/quality_gates.json", root / "config/quality_gates.json")
            result = run_ablation(root, seeds=(20261010,))
            records = {record["fault"]: record for record in result["runs"]}
            base = records["baseline"]
            self.assertEqual(len(records), 7)
            for fault, record in records.items():
                if fault in TIMING_FAULTS:
                    self.assertEqual(record["trajectory"], base["trajectory"])
                else:
                    self.assertEqual(record["timing"], base["timing"])
                    self.assertEqual(record["camera_lidar_sync_p95_ms"], base["camera_lidar_sync_p95_ms"])
                for name, digest in record["input_sha256"].items():
                    path = root / record["input_directory"] / name
                    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
            self.assertIn("timing.lidar.dropout_rate", records["lidar_dropout"]["failed_gates"])
            self.assertIn("timing.camera.out_of_order", records["camera_reversal"]["failed_gates"])
            self.assertEqual(records["camera_reversal"]["camera_lidar_sync_p95_ms"], base["camera_lidar_sync_p95_ms"])
            self.assertIn("sync.camera_lidar_p95", records["lidar_offset"]["failed_gates"])
            output = root / "results/ablation/comparison.json"
            previous = output.read_bytes()
            run_ablation(root, seeds=(20261010,))
            self.assertEqual(previous, output.read_bytes())

    def test_unknown_fault_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                generate_ablation_scenario("not-a-fault", Path(directory), 7)
