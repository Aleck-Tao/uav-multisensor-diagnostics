# Diagnostic Methodology

## 1. Input validation

Trajectory files must contain strictly increasing timestamps and at least three samples. Timing files retain acquisition order so timestamp reversals are observable. Numeric conversion errors and missing columns stop the analysis instead of being silently ignored.

## 2. Sensor timing

For sensor sample \(i\), sequence number \(q_i\), timestamp \(t_i\), and nominal period \(T\), the period residual is

\[
e_i = \frac{t_i - t_{i-1}}{q_i - q_{i-1}} - T.
\]

Jitter is reported as \(\sqrt{\mathrm{mean}(e_i^2)}\). Dividing by the sequence gap prevents a known dropped frame from being mistaken for timestamp jitter. The dropout count is the sum of positive sequence gaps minus one. A non-positive timestamp difference in acquisition order is counted as an out-of-order event.

Camera–LiDAR synchronization error is the absolute offset between each LiDAR timestamp and its nearest camera timestamp. The 95th percentile is used instead of the maximum to avoid one isolated sample dominating the decision.

## 3. Trajectory alignment and error

The reference trajectory is linearly interpolated at estimate timestamps. Estimated XY positions are aligned to reference positions with a least-squares rigid transform obtained by singular-value decomposition; Z is aligned with a constant offset. Scale is not adjusted because an incorrect scale is a localization error that should remain visible.

Metrics:

- **ATE RMSE:** root-mean-square Euclidean position error after alignment;
- **ATE p95:** 95th percentile absolute position error;
- **RPE RMSE:** root-mean-square error between one-second relative translations;
- **final drift:** aligned position error at the final sample;
- **heading RMSE:** circular yaw error after applying the alignment rotation;
- **path-length error:** relative distance error sampled at one-second support to avoid noise-induced frame-to-frame distance inflation.

## 4. Controlled fault injection

Both scenarios use the same 30-second smooth 3D reference path and sensor rates of 30 Hz camera, 10 Hz LiDAR and 100 Hz IMU.

The baseline adds small zero-mean pose and timestamp noise plus a fixed coordinate-frame transform. The degraded scenario additionally injects:

- time-dependent translational and heading drift;
- a four-second localized pose disturbance;
- increased per-sensor timestamp jitter;
- deterministic camera, LiDAR and IMU frame drops;
- one camera timestamp-order violation;
- a LiDAR clock offset relative to camera.

The generator seed is fixed. The two scenarios are intended to exercise the detector, not model a specific commercial sensor.

## 5. Quality gates

Thresholds are stored in `config/quality_gates.json`, reviewed like code and included in report provenance. A run passes only when every check is within its limit. This fail-closed rule makes the command suitable as a precondition before model evaluation or map-quality analysis.

Thresholds must be adapted when sensor rates, reference accuracy, platform dynamics or downstream tolerances change.
