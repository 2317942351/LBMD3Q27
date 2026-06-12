# Stage8f Normal Limiter Root-Cause Diagnostic

Status: `runtime_sanity / exploratory_not_validation`.

Stage8f is a diagnostic-only lane built from Stage8e. It does not change the
Stage8e normal-residual-only wetting candidate, does not authorize sphere
`Stage8OperatorMode=2`, and does not authorize PRE reproduction, validation,
production, or long sphere runs.

## Purpose

Stage8e removed the full-vector limiter as the dominant blocker, but the sphere
shadow gate still showed large normal-limiter fractions:

```text
free-sphere init: normal_limiter_fraction = 85.28 %
cap-on-sphere init: normal_limiter_fraction = 73.04 %
vector_limiter_fraction = 0 for both sphere shadows
outer90_limiter_count = 0 for both sphere shadows
```

Stage8f explains why the normal-only limiter still dominates. The key question
is whether the limiter comes from the absolute cap, the ratio cap around
`normal_raw ~= 0`, low-angle `tan(pi/2-theta)` amplification, high tangent
magnitudes, active-weight behavior, initializer stress, or a normal/tangent
split issue.

## Source

```text
remote source = /home/yuan/src/TCLB_stage8f_normal_limiter_root_cause_diag_20260613
public snapshot = third_party/tclb_snapshots/stage8f_normal_limiter_root_cause_diag
patch = third_party/tclb_snapshots/patches/stage8f_normal_limiter_root_cause_diag_20260613.diff
binary sha256 = 361a721716eed9536ba5b377ed2956600fb4a9ed19d7e3409f8982e60432d783
```

## What Changed

Stage8f only adds attribution diagnostics around the existing Stage8e candidate:

```text
Stage8eDnRaw
Stage8eDnTry
Stage8eDnLimited
Stage8eAbsCap
Stage8eRatioCap
Stage8eEffectiveCap
Stage8eCapSource
Stage8eCapDemandRatio
Stage8eNormalRawAbs
Stage8eTargetNormalAbs
Stage8eTargetMinusRawAbs
Stage8eSmoothWeightC/G/T/Total
Stage8eTanCoeffTimesTangent
Stage8eLimiterClass
Stage8eWallProfileConflict
```

The candidate formula is unchanged:

```text
dn_raw = target_normal - normal_raw
dn_try = alpha * smooth_weight * dn_raw
cap = min(Stage8MaxNormalDelta, Stage8MaxNormalDeltaRatio * abs(normal_raw))
dn_limited = clamp(dn_try, -cap, cap)
grad_candidate = grad + dn_limited * wall_normal
```

`Stage8eWallProfileConflict` is currently a placeholder diagnostic and is
reported as `0/unknown`. It must not be interpreted as evidence that the
profile phase path is or is not opposing the gradient candidate.

## Gates

1. Build/provenance and public repository audit.
2. Flat low-angle shadow attribution for `wall005/008/011/015/020/025/030` at
   steps `0/100/1000` with `Stage8OperatorMode=1`.
3. z48 sphere shadow attribution for free-sphere and approximate cap-on-sphere
   initializers at steps `0/100/1000`, also with `Stage8OperatorMode=1`.
4. Decision: classify the normal limiter source. No write-mode promotion is
   allowed from Stage8f.

## Current Execution Notes

Build/provenance passed on HM570:

```text
make source rc = 0
make build rc = 0
binary sha256 = 361a721716eed9536ba5b377ed2956600fb4a9ed19d7e3409f8982e60432d783
```

Remote provenance directory:

```text
/mnt/8A0E24070E23EAC1/runs/tclb_stage8f_normal_limiter_root_cause_provenance_20260613
```

Flat and sphere diagnostics were intentionally short shadow runs. Raw VTI/PVTI
files were kept remote-only and deleted after finiteness and attribution
outputs were generated. Public artifacts contain only XML, scripts, CSV/JSON,
logs, summaries, and documentation.

Curated local artifacts:

```text
artifacts/flat_wall_cap_stage8f_low_angle_20260613
artifacts/pre2025_sphere_stage8f_shadow_20260613
artifacts/stage8f_normal_limiter_root_cause_provenance_20260613
artifacts/stage8f_normal_limiter_root_cause_summary_20260613
```

Summary files:

```text
artifacts/stage8f_normal_limiter_root_cause_summary_20260613/stage8f_gate_summary.json
artifacts/stage8f_normal_limiter_root_cause_summary_20260613/stage8f_flat_shadow_summary.csv
artifacts/stage8f_normal_limiter_root_cause_summary_20260613/stage8f_sphere_shadow_summary.csv
```

## Gate Results

Flat low-angle shadow cases all completed with solver, finiteness, flat-gate,
and Stage8f attribution return code `0`:

| wall angle | normal limiter fraction | ratio-cap share of normal limiter | cap-demand p50 | target-minus-raw p50 | tangent p95 | max Mach |
|---:|---:|---:|---:|---:|---:|---:|
| 5 deg | 88.78 % | 61.63 % | 9.655 | 0.3103 | 0.07262 | 1.16e-5 |
| 8 deg | 85.21 % | 59.86 % | 5.295 | 0.1702 | 0.07279 | 1.12e-5 |
| 11 deg | 83.18 % | 58.59 % | 3.314 | 0.1061 | 0.07301 | 1.06e-5 |
| 15 deg | 78.11 % | 56.06 % | 1.882 | 0.0602 | 0.07345 | 9.49e-6 |
| 20 deg | 33.30 % | 47.52 % | 0.858 | 0.0282 | 0.07425 | 7.57e-6 |
| 25 deg | 0.00 % | n/a | 0.153 | 0.0070 | 0.07536 | 5.04e-6 |
| 30 deg | 0.00 % | n/a | 0.168 | 0.0040 | 0.07692 | 1.85e-6 |

All flat cases had:

```text
nonfinite_total = 0
vector_limiter_fraction = 0
apparent angle at step 1000 = about 29.48 deg
```

The flat trend is important because the tangent magnitude stays in the same
range while target-minus-raw and cap-demand collapse as the wall angle
increases. This supports low-angle `tan(pi/2-theta)` amplification plus the
current normal-cap contract as the dominant limiter mechanism.

Sphere z48 shadow cases also completed with solver, finiteness, and Stage8f
attribution return code `0`:

| case | active count | normal limiter fraction | ratio-cap share | abs-cap share | cap-demand p50 | target-minus-raw p50 | tangent p95 | outer90 normal hits | max Mach |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| free-sphere init | 924 | 85.28 % | 91.37 % | 8.63 % | 7.396 | 0.2052 | 0.13555 | 0 | 3.08e-4 |
| cap-on-sphere init | 5460 | 73.04 % | 58.68 % | 41.32 % | 2.426 | 0.0861 | 0.08321 | 0 | 1.89e-5 |

The approximate cap-on-sphere initializer reduces Mach, tangent magnitude,
target-minus-raw, cap demand, and normal limiter fraction. It does not reduce
the final normal limiter fraction below the `<5 %` write gate. This means
initial geometry stress is a real contributor, but not a sufficient explanation
or solution.

## Attribution

Stage8f classifies the current blocker as:

```text
sphere11_low_angle_candidate_dominated_normal_limiter_dominated_ratio_cap_contract_dominated
```

The evidence is:

```text
vector_limiter_fraction = 0 in all final flat and sphere frames
outer90_normal_limiter_count = 0 in both sphere shadows
sphere11 contains all active sphere limiter hits
normal agreement p05 is about 0.974-0.981 in sphere shadows
ratio cap is dominant in free-sphere and still largest in cap-on-sphere
normal limiter remains 73-85 % in sphere shadows
```

Current evidence does not point to outer-wall angle contamination or local
wall-normal transfer failure. It points to the combination of low-angle tangent
amplification and the Stage8e normal cap contract, with initial mismatch as a
secondary amplifier.

## Decision Boundary

`Stage8OperatorMode=2` remains forbidden for sphere cases. Stage8f cannot pass
a validation gate because it is designed to explain the limiter source, not to
fix the boundary condition.

The next route should be planned as Stage8g, not hidden inside Stage8f. The
likely Stage8g direction is a cap-contract revision or a low-angle regularized
contact relation. It must remain shadow-first and must not claim PRE
reproduction, validation, or production readiness.
