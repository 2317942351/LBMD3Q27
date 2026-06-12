# Stage8e Normal-Residual-Only Wetting Candidate

Status: `runtime_sanity / exploratory_not_validation`.

Stage8e is a diagnostic candidate built after Stage8d. It does not authorize
PRE reproduction claims, validation claims, production use, or long sphere
runs.

## Purpose

Stage8d showed that the Stage8c sphere shadow candidate was dominated by the
full vector delta limiter. Stage8e changes the candidate contract so only the
wall-normal contact-angle residual is corrected:

```text
dn = target_normal - normal_raw
candidate = grad + dn_limited * wall_normal
```

The tangential gradient is left unchanged. `Stage8MaxGradDelta` is retained as
a secondary safety diagnostic only; the primary limiter is now the normal-only
pair `Stage8MaxNormalDelta` and `Stage8MaxNormalDeltaRatio`.

## Source

```text
remote source = /home/yuan/src/TCLB_stage8e_normal_residual_only_wetting_candidate_20260613
public snapshot = third_party/tclb_snapshots/stage8e_normal_residual_only_wetting_candidate
patch = third_party/tclb_snapshots/patches/stage8e_normal_residual_only_wetting_candidate_20260613.diff
```

## Main Settings

```text
Stage8CandidateVersion = 8.5
Stage8MaxNormalDelta = 0.05
Stage8MaxNormalDeltaRatio = 0.5
Stage8UseSmoothActiveWeight = 1
Stage8ActiveCSoftWidth = 0.05
Stage8TangentSoftMin = 0.01
Stage8CurvatureRelaxation = 1
```

`Stage8CandidateVersion < 8.5` keeps the Stage8d vector-candidate path for
compatibility.

## Gates

1. Build/provenance and public repository audit.
2. Flat-wall low-angle shadow scan, then flat-wall short write only if shadow
   remains finite and interpretable.
3. z48 sphere shadow only, with free-sphere and approximate cap-on-sphere
   initializers.
4. Sphere write mode remains blocked unless shadow limiter fraction, outer-wall
   contamination, and limiter-ratio gates pass.

## Gate Results

Build/provenance passed:

```text
make source rc = 0
make build rc = 0
binary sha256 = db8af1bcf2da18a7373f2d29573499963e83de28beecf9bbafb1a0207102f880
```

Flat-wall shadow `wall005/008/011/015/020/025/030` passed the runtime sanity
checks through 1000 steps:

```text
nonfinite_total = 0 for all cases
max Mach <= 1.17e-5
apparent angle at step 1000 = 29.48-29.49 deg
vector_limiter_fraction = 0 for all cases
```

The low-angle normal-only limiter remains active:

```text
wall005 normal_limiter_fraction = 88.78 %
wall008 normal_limiter_fraction = 85.21 %
wall011 normal_limiter_fraction = 83.18 %
wall015 normal_limiter_fraction = 78.11 %
wall020 normal_limiter_fraction = 33.30 %
wall025/wall030 normal_limiter_fraction = 0 %
```

Sphere shadow through 1000 steps passed finiteness, but failed the write gate:

```text
free-sphere init: active=924, normal_limiter_fraction=85.28 %, vector_limiter_fraction=0, outer90_limiter_count=0, max Mach=3.084e-4
cap-on-sphere init: active=5460, normal_limiter_fraction=73.04 %, vector_limiter_fraction=0, outer90_limiter_count=0, max Mach=1.893e-5
```

The cap-on-sphere diagnostic initializer reduces Mach and normal limiter
fraction, but not enough to pass the `<5 %` shadow gate. `Stage8OperatorMode=2`
for sphere cases remains forbidden.

## Claim Boundary

The approximate cap-on-sphere initializer is a diagnostic control for initial
stress. It is not a theoretical equilibrium cap and must not be used as
validation evidence.
