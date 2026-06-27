# Stage14-B28 F_mu Stress Candidate Implementation

Date: 2026-06-27

Branch: `work/phasefield-c-reference-20260623`

Status: implementation and runtime gate plan. This is not contact-angle
validation.

## Why This Change Exists

B27 showed that:

```text
S2 noFmu removes downstream force/velocity/phase thresholds.
S3 noSurf also removes thresholds.
S1 density floor does not materially change onset.
```

Therefore the next test must not simply remove `F_mu`. It must preserve the
surface-force pathway and test whether the stress consumed by `F_mu` is the
wrong time level or algebraic object under TCLB MRT staging.

## Code Changes

Files:

```text
third_party/tclb_snapshots/stage17B_diffuse_solid_shadow/models/multiphase/d3q27_pf_velocity/Dynamics.R
third_party/tclb_snapshots/stage17B_diffuse_solid_shadow/models/multiphase/d3q27_pf_velocity/Dynamics.c.Rt
scripts/stage14/stage14_s2_replay_smoke.py
scripts/stage14/stage14_b23_b24_matrix_digest.py
scripts/stage14/compile_stage14_b18_after_source_remote.sh
scripts/stage14/run_stage14_b28_fmu_stress_candidate_remote.sh
scripts/stage14/run_stage14_b29_short_stability_remote.sh
```

New setting:

```text
FmuStressClosureMode = 0
```

Modes:

| Mode | Meaning | Claim limit |
|---|---|---|
| 0 | legacy relaxed-stress `F_mu` | current behavior |
| 1 | freeze `F_mu` after first fixed-point pass | candidate only |
| 2 | compute `F_mu` from incoming non-equilibrium stress using pre-force `m0` | candidate only |

The default is `0`, so existing cases are unchanged unless the case XML opts
in.

New diagnostic quantity:

```text
ReplayFmuStressClosureMode
```

This field lets VTI/summary artifacts prove which mode was actually used.

## TCLB Semantics Guard

The implementation respects the current TCLB split:

```text
g/h are AddDensity and stream.
Replay* and B18/B21/B22 fields are AddField/AddQuantity diagnostics and do not stream.
```

`FmuStressClosureMode` changes only the local MRT collision force construction
when explicitly set. It does not alter `PhaseF`, `WallGhost`, compact-stencil
wetting, or the `h` streaming semantics.

## B28 Runtime Matrix

Script:

```text
scripts/stage14/run_stage14_b28_fmu_stress_candidate_remote.sh
```

Remote root:

```text
/mnt/usb1t/RUNS/runs/stage14_B28_fmu_stress_candidate_20260627
```

Probes:

| Probe | `FmuStressClosureMode` | `MomentumForceMode` |
|---|---:|---:|
| `C0_legacy_fmu_stress` | 0 | 0 |
| `C1_freeze_iter1_fmu_stress` | 1 | 0 |
| `C2_incoming_neq_fmu_stress` | 2 | 0 |
| `C9_noFmu_reference` | 0 | 1 |

All use:

```text
case = wall_60to30_10
Density_h = 1.0
Density_l = 0.005
PressureClosureMode = 1
ForceFixedPointMode = 2
PhaseAdvectionVelocityMode = 1
vtk_field_set = b27stress
P100 = CUDA_VISIBLE_DEVICES=1
```

## B29 Gate

Only a B28 candidate that removes or delays the B27 short-onset mechanism can
enter B29.

B29 script:

```text
scripts/stage14/run_stage14_b29_short_stability_remote.sh
```

It runs:

```text
wall_60to30_10, density ratio 200, 20 steps then 100 steps
```

Passing B29 means short stability evidence only. It is not contact-angle
validation and does not authorize dynamic impact.
