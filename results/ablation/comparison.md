# Paired single-fault analysis

5 seeds, six isolated faults and their paired baselines (35 runs). Each sensor and the trajectory use separate random streams. All changed cases reuse the corresponding standard-normal draws; the legacy combined-fault benchmark is unchanged.

| Fault | Mean ATE (m) | Mean RPE (m) | Mean sync p95 (ms) | Rejected runs | Failed gates (count) |
|---|---:|---:|---:|---:|---|
| baseline | 0.0364 | 0.0441 | 2.024 | 0/5 | none |
| timing_jitter | 0.0364 | 0.0441 | 12.085 | 5/5 | `sync.camera_lidar_p95` (5/5); `timing.camera.jitter_rms` (5/5); `timing.imu.jitter_rms` (5/5); `timing.lidar.jitter_rms` (5/5) |
| lidar_offset | 0.0364 | 0.0441 | 16.785 | 5/5 | `sync.camera_lidar_p95` (5/5) |
| lidar_dropout | 0.0364 | 0.0441 | 2.037 | 5/5 | `timing.lidar.dropout_rate` (5/5) |
| camera_reversal | 0.0364 | 0.0441 | 2.024 | 5/5 | `timing.camera.jitter_rms` (5/5); `timing.camera.out_of_order` (5/5) |
| trajectory_drift | 0.1782 | 0.0483 | 2.024 | 5/5 | `trajectory.ate_rmse` (5/5); `trajectory.final_drift` (5/5) |
| trajectory_bump | 0.0907 | 0.0771 | 2.024 | 0/5 | none |

The table reports actual gate decisions, including faults that do not cross a threshold. Input hashes verify that timing interventions leave both trajectories unchanged and trajectory interventions leave all sensor timestamps unchanged. Paired metric deltas and every threshold are in [comparison.json](comparison.json).

A timestamp swap preserves the sorted camera timestamps, so nearest-frame synchronization can stay unchanged while timestamp-order and jitter checks respond. Removing LiDAR samples can leave synchronization p95 near baseline because it measures proximity for surviving samples. Dropout and ordering therefore require separate diagnostics.

These cases probe the stated simulator and fixed policy; they do not estimate detection probability for flight logs. Five seeds describe sensitivity to the chosen noise draws, not broad operating-condition coverage.

Reproduce with `python -m uavdiag ablation`. Raw inputs are in `data/ablation/<seed>/<fault>/`; each record includes their SHA-256 hashes.
