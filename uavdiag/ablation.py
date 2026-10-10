"""Single-fault comparisons with paired noise and independent sensor streams."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np

from .gates import evaluate_quality_gates
from .io import load_sensor_timestamps, load_trajectory
from .reporting import _normalize_floats
from .simulate import NOMINAL_HZ, _estimated_trajectory, _reference_trajectory, _write_trajectory
from .timing import analyze_timing, camera_lidar_sync_p95_ms
from .trajectory import analyze_trajectory
from dataclasses import asdict


SEEDS = (20261010, 20261011, 20261012, 20261013, 20261014)
FAULTS = {
    "baseline": "Unchanged baseline model with paired independent streams",
    "timing_jitter": "Timestamp noise SD: camera 3.2 ms, lidar 5.5 ms, imu 0.75 ms; same standard-normal draws",
    "lidar_offset": "LiDAR fixed offset raised from 0.8 ms to 17 ms",
    "lidar_dropout": "Remove positive LiDAR sequence numbers divisible by 37",
    "camera_reversal": "Swap camera timestamps at sequence 40 and 41; retain sequence order",
    "trajectory_drift": "Add [0.016, -0.009, 0.0016] m/s position drift; heading unchanged",
    "trajectory_bump": "Add one 12–16 s half-sine position disturbance: x +0.28 m, y -0.20 m",
}
TIMING_FAULTS = {"timing_jitter", "lidar_offset", "lidar_dropout", "camera_reversal"}


def generate_ablation_scenario(fault: str, directory: Path, seed: int) -> None:
    if fault not in FAULTS:
        raise ValueError(f"Unknown ablation fault: {fault}")
    directory.mkdir(parents=True, exist_ok=True)
    streams = np.random.SeedSequence(seed).spawn(4)
    t, reference, yaw = _reference_trajectory()
    estimate, estimate_yaw = _estimated_trajectory(t, reference, yaw, "baseline", np.random.default_rng(streams[0]))
    if fault == "trajectory_drift":
        estimate += t[:, None] * np.array([0.016, -0.009, 0.0016])
    elif fault == "trajectory_bump":
        selected = (t >= 12) & (t <= 16)
        phase = (t[selected] - 12) / 4 * np.pi
        estimate[selected, 0] += 0.28 * np.sin(phase)
        estimate[selected, 1] -= 0.20 * np.sin(phase)
    _write_trajectory(directory / "reference_trajectory.csv", t, reference, yaw)
    _write_trajectory(directory / "estimated_trajectory.csv", t, estimate, estimate_yaw)
    rows = []
    base_jitter = {"camera": 0.00035, "lidar": 0.00070, "imu": 0.00008}
    changed_jitter = {"camera": 0.0032, "lidar": 0.0055, "imu": 0.00075}
    for stream, (sensor, hz) in zip(streams[1:], NOMINAL_HZ.items(), strict=True):
        sequence = np.arange(int(30 * hz))
        noise = np.random.default_rng(stream).standard_normal(sequence.shape)
        sigma = (changed_jitter if fault == "timing_jitter" else base_jitter)[sensor]
        timestamps = sequence / hz + sigma * noise
        if sensor == "lidar":
            timestamps += 0.017 if fault == "lidar_offset" else 0.0008
        if fault == "camera_reversal" and sensor == "camera":
            timestamps[[40, 41]] = timestamps[[41, 40]]
        keep = np.ones(len(sequence), dtype=bool)
        if fault == "lidar_dropout" and sensor == "lidar":
            keep[(sequence > 0) & (sequence % 37 == 0)] = False
        rows.extend((sensor, int(seq), f"{timestamp:.8f}") for seq, timestamp in zip(sequence[keep], timestamps[keep], strict=True))
    with (directory / "sensor_timestamps.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["sensor", "sequence", "timestamp_s"])
        writer.writerows(rows)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_ablation(root: Path, seeds: tuple[int, ...] = SEEDS) -> dict:
    config_path = root / "config/quality_gates.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    records = []
    for seed in seeds:
        baseline = None
        for fault in FAULTS:
            directory = root / "data/ablation" / str(seed) / fault
            generate_ablation_scenario(fault, directory, seed)
            timing_rows = load_sensor_timestamps(directory / "sensor_timestamps.csv")
            timing = analyze_timing(timing_rows)
            sync = camera_lidar_sync_p95_ms(timing_rows)
            trajectory = analyze_trajectory(load_trajectory(directory / "reference_trajectory.csv"), load_trajectory(directory / "estimated_trajectory.csv"))
            gates = evaluate_quality_gates(timing, sync, trajectory, config)
            record = {
                "seed": seed, "fault": fault,
                "input_directory": directory.relative_to(root).as_posix(),
                "input_sha256": {name: _hash(directory / name) for name in ("reference_trajectory.csv", "estimated_trajectory.csv", "sensor_timestamps.csv")},
                "trajectory": asdict(trajectory), "timing": [asdict(item) for item in timing],
                "camera_lidar_sync_p95_ms": sync,
                "checks": [asdict(gate) for gate in gates],
                "failed_gates": [gate.name for gate in gates if not gate.passed],
            }
            if baseline is None:
                baseline = record
            record["paired_delta"] = {
                "ate_rmse_m": trajectory.ate_rmse_m - baseline["trajectory"]["ate_rmse_m"],
                "rpe_rmse_m": trajectory.rpe_rmse_m - baseline["trajectory"]["rpe_rmse_m"],
                "sync_p95_ms": sync - baseline["camera_lidar_sync_p95_ms"],
            }
            record["unchanged_inputs"] = {name: digest == baseline["input_sha256"][name] for name, digest in record["input_sha256"].items()}
            # Pairing is a required experimental invariant, not merely a reported observation.
            protected = "estimated_trajectory.csv" if fault in TIMING_FAULTS else "sensor_timestamps.csv"
            if not record["unchanged_inputs"][protected] or not record["unchanged_inputs"]["reference_trajectory.csv"]:
                raise RuntimeError(f"Fault isolation failed: {seed}/{fault}")
            records.append(record)
    summary = _normalize_floats({
        "method": "One fault per paired seed; independent SeedSequence streams for trajectory/camera/lidar/imu; old baseline/degraded benchmark unchanged",
        "seeds": list(seeds), "fault_definitions": FAULTS,
        "config_sha256": _hash(config_path), "runs": records,
    }, decimal_places=9)
    output = root / "results/ablation"
    output.mkdir(parents=True, exist_ok=True)
    (output / "comparison.json").write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
    lines = ["# Paired single-fault analysis", "",
             f"{len(seeds)} seeds, six isolated faults and their paired baselines ({len(records)} runs). Each sensor and the trajectory use separate random streams. All changed cases reuse the corresponding standard-normal draws; the legacy combined-fault benchmark is unchanged.", "",
             "| Fault | Mean ATE (m) | Mean RPE (m) | Mean sync p95 (ms) | Rejected runs | Failed gates (count) |",
             "|---|---:|---:|---:|---:|---|"]
    for fault in FAULTS:
        group = [record for record in records if record["fault"] == fault]
        frequencies = Counter(gate for record in group for gate in record["failed_gates"])
        names = "; ".join(f"`{name}` ({count}/{len(group)})" for name, count in sorted(frequencies.items())) or "none"
        avg = lambda values: sum(values) / len(group)
        lines.append(f"| {fault} | {avg([r['trajectory']['ate_rmse_m'] for r in group]):.4f} | {avg([r['trajectory']['rpe_rmse_m'] for r in group]):.4f} | {avg([r['camera_lidar_sync_p95_ms'] for r in group]):.3f} | {sum(bool(r['failed_gates']) for r in group)}/{len(group)} | {names} |")
    lines.extend(["", "The table reports actual gate decisions, including faults that do not cross a threshold. Input hashes verify that timing interventions leave both trajectories unchanged and trajectory interventions leave all sensor timestamps unchanged. Paired metric deltas and every threshold are in [comparison.json](comparison.json).", "",
                  "A timestamp swap preserves the sorted camera timestamps, so nearest-frame synchronization can stay unchanged while timestamp-order and jitter checks respond. Removing LiDAR samples can leave synchronization p95 near baseline because it measures proximity for surviving samples. Dropout and ordering therefore require separate diagnostics.", "",
                  "These cases probe the stated simulator and fixed policy; they do not estimate detection probability for flight logs. Five seeds describe sensitivity to the chosen noise draws, not broad operating-condition coverage.", "",
                  "Reproduce with `python -m uavdiag ablation`. Raw inputs are in `data/ablation/<seed>/<fault>/`; each record includes their SHA-256 hashes."])
    (output / "comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return summary
