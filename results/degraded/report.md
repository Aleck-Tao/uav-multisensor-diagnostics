# Degraded Scenario Diagnostic Report

**Quality-gate verdict: FAIL**

> This is a deterministic fault-injection benchmark. It validates the analysis pipeline; it is not presented as a real-flight accuracy result.

## Trajectory metrics

| Metric | Value |
|---|---:|
| Samples | 601 |
| ATE RMSE | 0.2119 m |
| ATE 95th percentile | 0.3446 m |
| RPE RMSE (1 s) | 0.1525 m |
| Final drift | 0.2820 m |
| Heading RMSE | 3.971 deg |
| Path-length error | 6.73% |

## Sensor timing

| Sensor | Samples | Observed rate | Jitter RMS | Max gap | Dropouts | Dropout rate | Out-of-order |
|---|---:|---:|---:|---:|---:|---:|---:|
| camera | 892 | 29.99 Hz | 4.716 ms | 74.27 ms | 8 | 0.89% | 1 |
| imu | 2985 | 100.00 Hz | 1.062 ms | 22.24 ms | 15 | 0.50% | 0 |
| lidar | 292 | 10.00 Hz | 7.801 ms | 212.87 ms | 8 | 2.67% | 0 |

Camera–LiDAR nearest-frame synchronization error (95th percentile): **18.314 ms**.

## Quality gates

| Check | Value | Limit | Result |
|---|---:|---:|:---:|
| `trajectory.ate_rmse` | 0.212 m | 0.12 m | FAIL |
| `trajectory.rpe_rmse` | 0.153 m | 0.1 m | FAIL |
| `trajectory.final_drift` | 0.282 m | 0.2 m | FAIL |
| `trajectory.heading_rmse` | 3.971 deg | 3 deg | FAIL |
| `trajectory.path_length_error` | 6.73% | 5 % | FAIL |
| `sync.camera_lidar_p95` | 18.314 ms | 8 ms | FAIL |
| `timing.camera.jitter_rms` | 4.716 ms | 1.5 ms | FAIL |
| `timing.camera.dropout_rate` | 0.89% | 1.50% | PASS |
| `timing.camera.out_of_order` | 1 | 0 count | FAIL |
| `timing.imu.jitter_rms` | 1.062 ms | 0.5 ms | FAIL |
| `timing.imu.dropout_rate` | 0.50% | 1.50% | PASS |
| `timing.imu.out_of_order` | 0 | 0 count | PASS |
| `timing.lidar.jitter_rms` | 7.801 ms | 2.5 ms | FAIL |
| `timing.lidar.dropout_rate` | 2.67% | 1.50% | FAIL |
| `timing.lidar.out_of_order` | 0 | 0 count | PASS |

## Reproducibility

Input file SHA-256 hashes are stored in `metrics.json`. Re-run `python -m uavdiag benchmark` from the project directory to regenerate both scenarios and reports.
