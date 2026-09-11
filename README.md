# UAV Multi-Sensor Diagnostics

[![CI](https://github.com/Aleck-Tao/uav-multisensor-diagnostics/actions/workflows/ci.yml/badge.svg)](https://github.com/Aleck-Tao/uav-multisensor-diagnostics/actions/workflows/ci.yml)

A Python tool for checking camera, LiDAR and IMU timing alongside trajectory error. The central question is whether a log is suitable for a downstream mapping or perception experiment when its average sampling rate still looks normal.

The included benchmark uses a generated 30-second trajectory with baseline and fault-injected sensor logs. Camera, LiDAR and IMU nominal rates are 30, 10 and 100 Hz.

## What the comparison shows

| Scenario | ATE RMSE | RPE RMSE (1 s) | Camera–LiDAR mismatch p95 | LiDAR dropout rate | Decision |
|---|---:|---:|---:|---:|:---:|
| Baseline | 0.0370 m | 0.0440 m | 2.206 ms | 0.00% | PASS |
| Degraded | 0.2119 m | 0.1525 m | 18.314 ms | 2.67% | FAIL |

<p>
  <img src="results/baseline/dashboard.svg" alt="Baseline diagnostic dashboard" width="49%">
  <img src="results/degraded/dashboard.svg" alt="Degraded diagnostic dashboard" width="49%">
</p>

In the degraded run, the reported rates remain approximately 30, 10 and 100 Hz. Yet camera jitter rises to 4.716 ms, LiDAR jitter to 7.801 ms, and one camera timestamp reversal is present. A rate averaged over the whole recording therefore misses faults that matter when matching individual measurements.

Camera dropout is 0.89%, below the configured 1.5% limit, while its jitter and timestamp-order checks fail. These checks answer different questions: sequence gaps identify missing samples; timestamp differences identify irregular timing. Dividing the time gap by the sequence gap prevents a known missing frame from automatically being counted as jitter.

Trajectory alignment removes a fixed XY rotation/translation and vertical offset. Scale and time-varying error remain in the residual. ATE describes the aligned position discrepancy; one-second RPE describes errors in local motion. Both increase in the degraded run, which combines drift, a temporary pose disturbance and observation noise. This combined case checks detection, but does not isolate each fault's contribution.

Read the [baseline report](results/baseline/report.md) and [degraded report](results/degraded/report.md) for every threshold and decision. The corresponding [baseline](results/baseline/metrics.json) and [degraded](results/degraded/metrics.json) JSON files contain the values and input hashes.

## Run it

From a checkout, with Python 3.12:

```bash
python -m pip install -e .
uavdiag benchmark
```

The expected output is `baseline: PASS (0 failed gates)` and `degraded: FAIL (11 failed gates)`. CI regenerates the data and reports and compares them with the committed files. To run the tests locally:

```bash
python -m unittest discover -s tests -v
```

## Use your own logs

Provide `sensor_timestamps.csv`, `reference_trajectory.csv` and `estimated_trajectory.csv` in one directory:

```bash
uavdiag analyze path/to/log path/to/report --label flight-07
```

Timing columns are `sensor,sequence,timestamp_s`; both trajectory files use `timestamp_s,x_m,y_m,z_m,yaw_rad`. The current implementation expects the three sensor names and nominal rates listed above. Trajectories need increasing timestamps and sufficient overlap. Exit code `0` means all configured checks passed; `2` requests review.

The nearest-frame camera–LiDAR metric measures temporal proximity, not a unique clock offset: a periodic camera stream can match a shifted LiDAR sample to the next frame. Its p95 also leaves the worst 5% outside that summary. Interpret it together with order, dropout and gap statistics.

The committed results are synthetic fault-injection results. Applying the tool to flight logs requires a documented reference trajectory and thresholds suited to that experiment; the defaults in [quality_gates.json](config/quality_gates.json) are a starting policy. Equations and generator assumptions are in [methodology.md](docs/methodology.md).

Related: [real flight-video audit](https://github.com/Aleck-Tao/uav-flight-video-quality-audit) · [mission interface](https://github.com/Aleck-Tao/safety-constrained-uav-mission-interface) · [portfolio](https://github.com/Aleck-Tao/computer-vision-autonomous-systems-portfolio). Code: [MIT](LICENSE).
