# Baseline Scenario Diagnostic Report

**Quality-gate verdict: PASS**

> This is a deterministic fault-injection benchmark. It validates the analysis pipeline; it is not presented as a real-flight accuracy result.

## Trajectory metrics

| Metric | Value |
|---|---:|
| Samples | 601 |
| ATE RMSE | 0.0370 m |
| ATE 95th percentile | 0.0577 m |
| RPE RMSE (1 s) | 0.0440 m |
| Final drift | 0.0182 m |
| Heading RMSE | 0.593 deg |
| Path-length error | 0.83% |

## Sensor timing

| Sensor | Samples | Observed rate | Jitter RMS | Max gap | Dropouts | Dropout rate | Out-of-order |
|---|---:|---:|---:|---:|---:|---:|---:|
| camera | 900 | 30.00 Hz | 0.501 ms | 34.74 ms | 0 | 0.00% | 0 |
| imu | 3000 | 100.00 Hz | 0.115 ms | 10.38 ms | 0 | 0.00% | 0 |
| lidar | 300 | 10.00 Hz | 1.002 ms | 102.50 ms | 0 | 0.00% | 0 |

Camera–LiDAR nearest-frame synchronization error (95th percentile): **2.206 ms**.

## Quality gates

| Check | Value | Limit | Result |
|---|---:|---:|:---:|
| `trajectory.ate_rmse` | 0.037 m | 0.12 m | PASS |
| `trajectory.rpe_rmse` | 0.044 m | 0.1 m | PASS |
| `trajectory.final_drift` | 0.018 m | 0.2 m | PASS |
| `trajectory.heading_rmse` | 0.593 deg | 3 deg | PASS |
| `trajectory.path_length_error` | 0.83% | 5 % | PASS |
| `sync.camera_lidar_p95` | 2.206 ms | 8 ms | PASS |
| `timing.camera.jitter_rms` | 0.501 ms | 1.5 ms | PASS |
| `timing.camera.dropout_rate` | 0.00% | 1.50% | PASS |
| `timing.camera.out_of_order` | 0 | 0 count | PASS |
| `timing.imu.jitter_rms` | 0.115 ms | 0.5 ms | PASS |
| `timing.imu.dropout_rate` | 0.00% | 1.50% | PASS |
| `timing.imu.out_of_order` | 0 | 0 count | PASS |
| `timing.lidar.jitter_rms` | 1.002 ms | 2.5 ms | PASS |
| `timing.lidar.dropout_rate` | 0.00% | 1.50% | PASS |
| `timing.lidar.out_of_order` | 0 | 0 count | PASS |

## Reproducibility

Input file SHA-256 hashes are stored in `metrics.json`. Re-run `python -m uavdiag benchmark` from the project directory to regenerate both scenarios and reports.
