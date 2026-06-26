# Stage14-B18 Shadow Closure Diagnostics

Date: 2026-06-25 / updated 2026-06-26

Status: B18-B diagnostic evidence collected. This is diagnostic-only. It is not contact-angle validation, not a solver fix, and not a dynamic-impact preflight.

## Purpose

B17 localized the earliest large producer in `wall_60to30_10` to:

```text
post-force stress / low-density force-over-rho feedback
    -> oversized velocity input
    -> h update / PhaseFromH leaves [0, 1]
    -> pressure and F_mu amplify later
```

B18 does not change the legacy solver path. It adds shadow-only fields to split the same onset into:

1. stress reconstruction time level,
2. `F_mu` candidate source,
3. `F_total/rho` denominator closure,
4. h-equilibrium velocity input.

## Code Changes

Snapshot:

```text
third_party/tclb_snapshots/stage17B_diffuse_solid_shadow/models/multiphase/d3q27_pf_velocity/
```

Changed files:

- `Dynamics.R`
  - Adds `Stage14B18ClosureDiagnosticsMode = 0` and `Stage14B18VelocityBound = 0.2`.
  - Adds only `AddField(..., group="runtime_diagnostics")` and `AddQuantity(...)` for `B18*` outputs.
  - No `AddDensity` fields were added.

- `Dynamics.c.Rt`
  - Adds B18 helper gates and reset logic.
  - Writes shadow-only stress tensors:
    - `B18StressIncoming*`
    - `B18StressPreForce*`
    - `B18StressPostForce*`
    - `B18StressForceExcluded*`
  - Writes `F_mu` candidates computed from the same coefficient and `gradPhi`.
  - Writes raw/floor/phase-mixture `F_total/rho` shadow vectors.
  - Writes h-equilibrium velocity and `heq` max shadows.
  - Does not write these candidates back to `F_total`, `U`, `h`, or `g`.

- `scripts/stage14/stage14_s2_replay_smoke.py`
  - Adds B18 fields to VTI output.
  - Adds `--b18-closure-diagnostics-mode` and `--b18-velocity-bound`.

- `scripts/stage14/stage14_b17_onset_mask_argmax.py`
  - Extends the B17 mask/argmax analyzer with B18 fields and branch classification.
  - Adds `--prefix`, so B18 output files are written as `b18_*.json/csv`.

- `scripts/stage14/build_stage14_b18_shadow_closure_remote.sh`
  - Reproducible remote RT generation and CUDA build wrapper.

- `scripts/stage14/run_stage14_b18_shadow_closure_remote.sh`
  - Reproducible P100 short-run wrapper for the B18 diagnostic case.

## Run Plan

Server:

```text
yuan@192.168.1.16
GPU: CUDA_VISIBLE_DEVICES=1
compile lane: /home/yuan/src/TCLB_lbm2026_compile_lane
run root: /mnt/usb1t/RUNS/runs/stage14_B18_shadow_closure_20260625
```

Case:

```text
wall_60to30_10
Density_h = 1.0
Density_l = 0.005
PressureClosureMode = 1
ForceFixedPointMode = 2
PhaseAdvectionVelocityMode = 1
MomentumForceMode = 0
MomentumClosureDiagnosticsMode = 1
Stage14B18ClosureDiagnosticsMode = 1
iterations = 20
vtk_period = 1
```

## Build Notes

The B18 fields change `Dynamics.R`, so the target must regenerate TCLB field and setting declarations before CUDA compilation.

Required build order:

```text
make d3q27_pf_velocity_q27_geometric/source
tools/RT ... Dynamics.c.Rt ... -o CLB/d3q27_pf_velocity_q27_geometric/Dynamics.c
tools/RT ... src/cuda.cu.Rt ... -o CLB/d3q27_pf_velocity_q27_geometric/cuda.cu
make -C CLB/d3q27_pf_velocity_q27_geometric -j 8
```

An earlier attempt that ran only `tools/RT` generated `Dynamics.c` but did not regenerate field declarations, causing CUDA errors such as:

```text
identifier "Stage14B18ClosureDiagnosticsMode" is undefined
identifier "B18ProbeActive" is undefined
```

That is a build-order error, not a physical solver result.

Additional TCLB generation note:

- After adding B18 settings and fields, `Global.h`, `LatticeContainer.inc.cpp`, and `Lists.cpp` can refresh while `cuda.cu` remains stale.
- A stale `cuda.cu` omitted:
  - `CudaConstantMemory real_t Stage14B18ClosureDiagnosticsMode`
  - `CudaConstantMemory real_t Stage14B18VelocityBound`
  - B18 field access macros such as `#define B18FmuLegacyX(...)`
- The build wrappers now force-regenerate `cuda.cu` and grep for these symbols before CUDA compilation.

## B18-A Runtime Result

Run root:

```text
/mnt/usb1t/RUNS/runs/stage14_B18_shadow_closure_20260625
```

Downloaded lightweight artifacts:

```text
artifacts/stage14_B18_shadow_closure_20260625/
```

Runtime summary:

```text
binary_sha256 = d25da79643e866587c9cd568bb39aa60fd81ce780198b2e261bcfda1343db721
DRIVER_RC = 3
ANALYZER_RC = 0
VTI_COUNT = 21
run.log RUN_RC = 0
```

Important limitation:

`Stage14B18ClosureDiagnosticsMode=1` was accepted by the solver, and the analyzer found all B18 fields in VTI, but all B18 diagnostic values remained zero. Therefore B18-A is a diagnostic plumbing failure, not a physics verdict.

The likely cause is that B18 `AddQuantity` getters were temporarily changed to return bare node-field variables to avoid a stale-`cuda.cu` compile error. For TCLB VTI quantity output these getters must use the lattice accessor form, e.g.:

```c
B18FmuLegacyX(0,0,0)
```

not:

```c
B18FmuLegacyX
```

B18-A can still be used as a legacy/B17 replay consistency run. It reproduces the previous onset ordering:

- step 13: `ForceOverRhoNorm` large in `near_interface_wall`, value about `2.09e3`.
- step 13: `StressPostForceNorm` large in `near_interface_wall`, value about `1.28e6`.
- step 13: `ReplayHPostMaxAbs` large in `low_rho`, value about `2.23`.
- step 13: `ReplayPhaseFromH` leaves bounds in `low_rho`, value about `2.79`.
- step 14: pressure, raw `F_mu`, and stress-input blow up after phase/H failure.

The analyzer classified the legacy replay branch as:

```text
stress_timelevel_or_fixed_point_feedback
```

But it also reported:

```text
b18_primary_branch = not_available
```

because B18 fields did not carry nonzero values. Do not use B18-A to decide between B18 force-density, stress-candidate, or h-velocity branches.

## B18-B Runtime Plan

B18-B fixes the diagnostic plumbing:

- B18 getters use `B18*(0,0,0)` field accessors.
- Remote compile wrappers force-regenerate `cuda.cu`.
- Compile log must contain:

```text
CUDA_RT_RC=0
CUDA_B18_ACCESSORS_OK=1
BUILD_RC=0
```

The second run must use a new root, for example:

```text
/mnt/usb1t/RUNS/runs/stage14_B18_shadow_closure_20260625_rerun
```

Acceptance for B18-B is not stability and not contact angle. It is:

- B18 fields are present.
- `B18ProbeActive` is nonzero in collision cells.
- At least one of `B18StressPreForceNorm`, `B18StressPostForceNorm`, `B18ForceOverRhoRawNorm`, or `B18HVelocityRawPostForceNorm` is nonzero before onset.
- Only then may B18 branch classification be used.

## B18-B Runtime Result

Run root:

```text
/mnt/usb1t/RUNS/runs/stage14_B18_shadow_closure_20260625_rerun
```

Downloaded lightweight artifacts:

```text
artifacts/stage14_B18_shadow_closure_20260625_rerun/
```

Runtime summary:

```text
binary_sha256 = 01b18e2e84bd82078c079bf7446acda3cfc72a4d37b83dd7477c183c148ca9b1
run.log RUN_RC = 0
DRIVER_RC = 3
ANALYZER_RC = 0
VTI before cleanup = 21
remote cleanup = output/*.vti and output/*.pvti removed after lightweight artifacts were downloaded
remote run size after cleanup = 35M
/mnt/usb1t free after cleanup = 75G
```

`DRIVER_RC=3` is a Python post-processing/summarization failure caused by extreme values and overflow warnings. It is not a TCLB runtime failure: the solver wrote all 21 VTI frames and `run.log` contains `RUN_RC=0`. Because the wrapper did not complete normal analyzer handoff, `stage14_b17_onset_mask_argmax.py` was run manually against the same VTI set. The manual analyzer completed with `ANALYZER_RC=0`.

B18-B fixed the B18-A VTI getter failure:

- All 115 expected replay/B18 fields were present for frames 0-12.
- `B18ProbeActive` became nonzero from step 1 onward.
- `B18ForceOverRho*`, `B18StressPostForce*`, `B18HVelocityRawPostForce*`, and `B18Heq*` fields carried nonzero values before the onset window.
- Frames 13-20 are physically beyond the blow-up window; some analyzer field-presence summaries are false there because nonfinite/overflow values make derived norms unusable. The useful diagnosis is therefore step 1-12 plus the first-onset records.

Key low-density trace from `b18_mask_stats.csv`:

```text
step  B18ForceOverRhoRawNorm  B18HVelocityRawPostForceNorm  B18HVelocityBoundedShadowNorm  StressPostForceNorm  ReplayPhaseFromH
8     2.112e-1                1.225e-1                      1.225e-1                       7.092e-2            2.006e-2
9     7.302e-1                4.129e-1                      2.000e-1                       1.082e-1            2.008e-2
10    1.482e+0                7.938e-1                      2.000e-1                       8.242e-1            2.002e-2
11    5.318e+0                2.821e+0                      2.000e-1                       9.300e+0            2.007e-2
12    4.141e+1                2.002e+1                      2.000e-1                       4.663e+2            1.990e-2
13    first legacy threshold records: ForceOverRho, HPost, PhaseFromH, and post-force stress cross together
```

First-onset records:

```text
step 13: B18StressPostForceNorm near_interface_wall = 1.275366e6
step 13: ForceOverRhoNorm near_interface_wall = 2.092377e3
step 13: ReplayHPostMaxAbs low_rho = 2.233706
step 13: ReplayPhaseFromH low_rho = 2.791220
step 14: FmuRawNorm low_rho = 1.007235e5
step 14: ReplayPressureInput low_rho = 6.779061e5
step 14: StressInputNorm low_rho = 1.646657e6
```

The analyzer reports:

```text
primary_branch = undetermined
primary_branch_reason = No configured onset threshold was crossed.
b18_primary_branch = stress_amplification_shadow
b18_primary_branch_reason = B18 post/pre stress amplification crosses first.
```

Interpretation:

- The `b18_primary_branch` result is useful but must be read conservatively. `B18StressPostOverPre` crosses at step 1 because the pre-force stress denominator is close to zero, so that ratio alone is not a solver-failure proof.
- The stronger evidence is the step 10-13 low-density feedback chain: post-force stress and `F_total/rho` grow rapidly, the raw post-force velocity entering the phase update grows from sub-lattice values to `O(10)`, and then `h`/`PhaseFromH` leaves the physical interval at step 13.
- The floor and phase-mixture denominator shadows equal the raw denominator path in this run before step 13. Therefore this exact B18-B probe does not yet prove that a simple density-floor denominator fixes the root cause.
- `B18HVelocityBoundedShadowNorm` stays capped at 0.2 while the raw post-force velocity grows to 20.0 by step 12. This is strong evidence that the phase update is receiving an unbounded advective velocity, but the bounded value is only a shadow diagnostic, not an accepted physical limiter.
- Pressure and raw `F_mu` become large after `h`/`PhaseFromH` has already failed. They remain important for closure, but B18-B does not support treating pressure closure as the first producer in this case.

Current B18-B verdict:

```text
diagnostic_pass_for_plumbing = true
physics_validation = false
most_likely_next_branch = stress/F_total-to-phase-velocity feedback in low-density cells
do_not_claim = contact angle validation, solver fix, dynamic impact readiness
```

Immediate next action should be a B19 split probe, not a wetting/curved-wall run:

1. Re-run the same 20-step case with `PhaseAdvectionVelocityMode=0` and `PhaseAdvectionVelocityMode=1` in separate roots, because B18-B used mode 1 and this affects the meaning of `B18HeqLegacy*`.
2. Add one more shadow set for `heq` generated from raw post-force velocity, pre-force velocity, and bounded velocity without relying on the run mode name.
3. Add a numerator/denominator split for `F_total/rho`: store `|F_total|`, raw `rho`, floor `rho`, and phase-mixture `rho` at the same argmax point.
4. Only after that, introduce optional physics modes. Do not turn the bounded shadow into a solver fix directly.

## Decision Criteria

- If `B18StressPostForceNorm` or `B18StressPostOverPre` leads the onset, prioritize stress time-level reconstruction.
- If raw `B18ForceOverRhoRawNorm` crosses but floor/phase-mixture shadows do not, prioritize force-density denominator closure.
- If `B18HeqLegacyMaxAbs` leads while `B18HeqPreForceMaxAbs` does not, prioritize h velocity input closure.
- If none explains the B17 argmax locations, return to TCLB stage/load/save and AddDensity streaming timeline.

## Prohibited Claims

Do not claim:

- contact-angle validation passed,
- dynamic-impact readiness,
- B18 is a physics fix,
- B18 force-excluded stress is a validated replacement formula.
