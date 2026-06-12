# Stage8d Sphere Shadow Limiter Attribution

Status: `runtime_sanity / exploratory_not_validation`.

Stage8d is a shadow-only diagnostic lane built from Stage8c. It does not
authorize `Stage8OperatorMode=2`, sphere 50k runs, PRE reproduction claims, or
validation claims.

## Purpose

Stage8c already showed that local wall-angle and wall-normal transfer works on
the z48 sphere case, but the shadow candidate was dominated by
`Stage8MaxGradDelta=0.25`. Stage8d explains where and why that limiter is hit.

## Source

```text
remote source = /home/yuan/src/TCLB_stage8d_sphere_shadow_limiter_attribution_20260612
public snapshot = third_party/tclb_snapshots/stage8d_sphere_shadow_limiter_attribution
binary = CLB/d3q27_pf_velocity_q27_geometric/main
binary sha256 = c8191e8575520cbe5a54886f5ccb0411e100828c711794ae3488b7b1eb1c7a0a
```

## Added Diagnostics

Stage8d adds raw/limited normal and vector candidate fields, local angle and
phase-band tags, sphere-region tags, and limiter-ratio diagnostics. The
candidate construction and write-mode behavior remain Stage8c-compatible.

Important added outputs:

```text
WallStage8VectorDeltaRawMag
WallStage8VectorDeltaLimitedMag
WallStage8NormalDeltaRaw
WallStage8NormalDeltaLimited
WallStage8VectorLimiterHit
WallStage8NormalLimiterHit
WallStage8LimiterRatio
WallStage8RegionTag
WallStage8ContactBandTag
WallStage8TanCoeffLocal
```

## Main Result

The z48 sphere shadow run completed 1000 steps with solver rc 0, finiteness rc
0, attribution rc 0, and `nonfinite_total=0` for all checked frames.

At step 1000:

```text
active_count = 924
limiter_count = 404
limiter_fraction = 43.72 %
sphere11_active_count = 924
sphere11_limiter_count = 404
outer90_limiter_count = 0
fallback_angle_limiter_count = 0
raw_delta_p99 = 0.6471
limited_delta_p99 = 0.25
limiter_ratio_p10 = 0.4621
tangent_mag_p99 = 0.1427
tan_coeff_p50 = 5.1446
max Mach = 3.084e-4
```

The limiter is not caused by outer-wall angle contamination. It is concentrated
entirely in the sphere 11 degree region.

## Attribution

The strongest limiter source is high tangent-gradient magnitude under the low
11 degree wall angle:

```text
tangent 0.05..0.10: active 256, limiter 216, limiter fraction 84.38 %
tangent > 0.10:     active 188, limiter 188, limiter fraction 100 %
```

By phase band at step 1000:

```text
c 0.10..0.30: active 204, limiter 120, limiter fraction 58.82 %
c 0.30..0.70: active 172, limiter 172, limiter fraction 100 %
c 0.70..0.90: active 116, limiter 112, limiter fraction 96.55 %
```

This points to low-angle tan amplification plus curved-wall tangent gradients,
not to incorrect local wall-angle transfer.

## Decision

Keep the current state as:

```text
stage8d_sphere_shadow_limiter_attribution
runtime_sanity / exploratory_not_validation
write_mode_allowed = false
```

Do not run `Stage8OperatorMode=2` sphere write. The next implementation should
be a separate Stage8e candidate using normal-residual-only correction and a
smooth active weight.

