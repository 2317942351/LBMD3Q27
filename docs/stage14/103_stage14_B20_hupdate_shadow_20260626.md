# Stage14-B20 Phase H-Update Shadow Split

Date: 2026-06-26

Status: exploratory_not_validation. This is diagnostic-only evidence. It is not contact-angle validation, not a solver fix, and not a dynamic-impact preflight.

## Purpose

B19 showed that `PhaseAdvectionVelocityMode=0` makes the earliest failure easier to classify:

```text
PhaseF / h update leaves bounds before the configured force-over-rho threshold.
```

B20 splits the phase population update without writing any candidate value back to the solver:

```text
PhaseF -> tmp1/Fphi -> heq -> hpost -> PhaseFromH shadow
```

The diagnostic compares four candidates inside the MRT phase update block:

```text
active solver path
raw post-force velocity
pre-force velocity
bounded velocity shadow
```

All B20 fields are `AddField(..., group="runtime_diagnostics")`. They do not stream and do not alter `h`, `PhaseF`, `g`, `F_total`, or `U`.

## Code Changes

Main TCLB files:

```text
third_party/tclb_snapshots/stage17B_diffuse_solid_shadow/models/multiphase/d3q27_pf_velocity/Dynamics.R
third_party/tclb_snapshots/stage17B_diffuse_solid_shadow/models/multiphase/d3q27_pf_velocity/Dynamics.c.Rt
```

Added setting:

```text
Stage14B20HUpdateDiagnosticsMode = 0 by default
```

Added B20 fields include:

```text
B20Fphi*Sum / B20Fphi*MaxAbs
B20Heq*Sum / B20Heq*MaxAbs
B20HPost*Sum / B20HPost*MaxAbs
B20PhaseFromH*Shadow
B20HPost*OutOfBoundsFlag
```

Script support:

```text
scripts/stage14/stage14_s2_replay_smoke.py
scripts/stage14/stage14_b17_onset_mask_argmax.py
scripts/stage14/run_stage14_b18_shadow_closure_remote.sh
scripts/stage14/build_stage14_b18_shadow_closure_remote.sh
scripts/stage14/compile_stage14_b18_after_source_remote.sh
```

Important implementation note: when adding new `AddField` or `AddSetting`, `make d3q27_pf_velocity_q27_geometric/source` is required before RT/build. A first after-source-only compile failed because generated `cuda.cu` did not yet contain B20 field macros. The full source-generation build succeeded.

## Build

Remote compile lane:

```text
/home/yuan/src/TCLB_lbm2026_compile_lane
```

Build command:

```text
LOG=/home/yuan/lbm2026_stage14_B20_build_20260626.log /home/yuan/build_stage14_b18_shadow_closure_remote.sh
```

Build result:

```text
SOURCE_RC = 0
RT_RC = 0
CUDA_RT_RC = 0
CUDA_B18_B20_ACCESSORS_OK = 1
BUILD_RC = 0
binary_sha256 = 9d63fa5aa0618c1b5389d1126662f0da6aa7ea01185d72b377f7a5b80693c023
```

The `fatal: not a git repository` message in the build log occurs during TCLB `SUMMARY` generation in this compile lane. It did not stop source generation or compilation.

## Run

Mode-0 remote run root:

```text
/mnt/usb1t/RUNS/runs/stage14_B20_hupdate_shadow_mode0_20260626
```

Mode-0 local artifacts:

```text
artifacts/stage14_B20_hupdate_shadow_mode0_20260626/
```

Mode-1 comparison was also run after the mode-0 result:

```text
remote run root = /mnt/usb1t/RUNS/runs/stage14_B20_hupdate_shadow_mode1_20260626
local artifacts = artifacts/stage14_B20_hupdate_shadow_mode1_20260626/
comparison table = artifacts/stage14_B20_mode0_mode1_compare_20260626.csv
```

Run configuration:

```text
case = wall_60to30_10
GPU = 1, Tesla P100
Density_h = 1.0
Density_l = 0.005
iterations = 20
vtk_period = 1
VTK_FIELD_SET = minimal
PhaseAdvectionVelocityMode = 0 for the first run, 1 for the comparison run
PressureClosureMode = 1
ForceFixedPointMode = 2
MomentumClosureDiagnosticsMode = 1
Stage14B18ClosureDiagnosticsMode = 1
Stage14B20HUpdateDiagnosticsMode = 1
```

Mode-0 run status:

```text
TCLB run.log: RUN_RC=0
driver.status: DRIVER_RC=3
analyzer.status: ANALYZER_RC=0
VTI_COUNT=21
```

Mode-1 run status:

```text
TCLB run.log: RUN_RC=0
driver.status: DRIVER_RC=3
analyzer.status: ANALYZER_RC=0
VTI_COUNT=21
```

`DRIVER_RC=3` is the Python summary guard reporting post-failure overflow/nonfinite diagnostics. The TCLB executable completed the requested 20 steps. After downloading lightweight evidence, 42 VTI/PVTI files were deleted from the remote run root and `/mnt/usb1t` returned to about 77G free.

## Key Evidence

Mode-0 analyzer classification:

```text
primary_branch = phase_update_or_h_advection_first
primary_branch_reason = PhaseFromH leaves bounds before configured force-over-rho onset.

b18_primary_branch = stress_amplification_shadow
b18_primary_branch_reason = B18 post/pre stress amplification crosses first.

b20_primary_branch = heq_candidate_large_before_hpost
b20_primary_branch_reason = B20 active heq shadow crosses before or with hpost.
```

Mode-1 analyzer classification:

```text
primary_branch = stress_timelevel_or_fixed_point_feedback
b18_primary_branch = stress_amplification_shadow
b20_primary_branch = heq_candidate_large_before_hpost
```

First onset records:

```text
ReplayPhaseFromH low_rho leaves bounds at step 13:
  value = 554.6179695990377

ReplayHPostMaxAbs near_interface_wall crosses 1.0 at step 13:
  value = 1.9148838246017725

B20HeqActiveMaxAbs near_interface_wall crosses 1.0 at step 13:
  value = 2.6814315084217064

B20HPostActiveMaxAbs near_interface_wall crosses 1.0 at step 13:
  value = 1.9148838246017725

B20PhaseFromHActiveShadow low_rho leaves bounds at step 14:
  value = 1060.607388496399
```

Mode-1 first onset records:

```text
B20HeqActiveMaxAbs low_rho crosses 1.0 at step 13:
  value = 3.127171808902775

B20HPostActiveMaxAbs low_rho crosses 1.0 at step 13:
  value = 2.233706063315237

B20PhaseFromHActiveShadow low_rho leaves bounds at step 14:
  value = 1.9877476692199707
```

The compact table is:

```text
artifacts/stage14_B20_hupdate_shadow_mode0_20260626/b20_step12_14_key_metrics.csv
```

Important step trace:

```text
step 12:
  ReplayPhaseFromH low_rho = 0.0645998881
  ReplayHPostMaxAbs low_rho = 0.0105103406
  B20FphiActiveMaxAbs low_rho = 0.0019185160
  B20HeqActiveMaxAbs low_rho = 0.0148260059
  B18HVelocityRawPostForceNorm low_rho = 13.7022037078

step 13:
  ReplayPhaseFromH low_rho = 554.6179695990
  ReplayHPostMaxAbs low_rho = 270.6079449121
  B20FphiActiveMaxAbs low_rho = 0.0121775683
  B20HeqActiveMaxAbs low_rho = 378.8806453468
  B20HPostActiveMaxAbs low_rho = 270.6079449121
  B20HPostBoundedMaxAbs low_rho = 0.0590850254

step 14:
  ReplayPhaseFromH low_rho = 2.2693301312485114e11
  ReplayHPostMaxAbs low_rho = 1.1749647371782227e11
  B20FphiActiveMaxAbs low_rho = 72445.9591247767
  B20HeqActiveMaxAbs low_rho = 1.6449506320528162e11
  B20HPostActiveMaxAbs low_rho = 1.1749647371782227e11
```

Mode comparison:

```text
mode 0, step 13:
  ReplayPhaseFromH low_rho = 554.6179695990
  B20HeqActiveMaxAbs low_rho = 378.8806453468
  B20HPostActiveMaxAbs low_rho = 270.6079449121
  B20FphiActiveMaxAbs low_rho = 0.0121775683

mode 1, step 13:
  ReplayPhaseFromH low_rho = 2.7912195566
  B20HeqActiveMaxAbs low_rho = 3.1271718089
  B20HPostActiveMaxAbs low_rho = 2.2337060633
  B20FphiActiveMaxAbs low_rho = 0.0018927390

mode 0, step 14:
  ReplayPhaseFromH low_rho = 2.2693301312485114e11
  B20PhaseFromHActiveShadow low_rho = 1060.6073884964
  B20HeqActiveMaxAbs low_rho = 1.6449506320528162e11

mode 1, step 14:
  ReplayPhaseFromH low_rho = 1.479182737715828e11
  B20PhaseFromHActiveShadow low_rho = 1.9877476692
  B20HeqActiveMaxAbs low_rho = 2.5991602652548466e10
```

## Interpretation

B20 makes four points clearer than B19:

1. `Fphi` is not the earliest visible source. At step 13, `B20FphiActiveMaxAbs` is still `O(10^-2)` while `B20HeqActiveMaxAbs` and `B20HPostActiveMaxAbs` are already `O(10^2)`.

2. The active and raw post-force candidates are identical in mode 0, as expected. The pre-force candidate is smaller at the near-wall onset but still becomes large. Therefore a simple switch from post-force velocity to pre-force velocity is unlikely to be a complete fix.

3. The bounded-velocity shadow suppresses the step-13 hpost blow-up in this one diagnostic frame, but it is not a physical model. By step 14, after the population history is already contaminated, even the bounded shadow has large values. This supports a producer-consumer interpretation: once `h` populations have been driven into a large cancelling/nonphysical state, later local velocity limiting cannot repair the streamed population field.

4. `PhaseAdvectionVelocityMode=1` significantly reduces the local shadow amplitude at step 13 and the `B20PhaseFromHActiveShadow` amplitude at step 14, but it does not remove the step-13 `heq/hpost > 1` onset. Therefore the current evidence does not support a one-line fix that only swaps the active h-equilibrium velocity. The h population history and cancellation must be inspected directly.

The working root-cause path is now:

```text
low-density force/stress feedback
  -> very large phase-advection velocity input
  -> oversized heq
  -> oversized hpost populations
  -> streamed h populations produce PhaseFromH outside [0,1]
  -> tmp1/Fphi/mu/force terms enter exponential amplification
```

This does not prove the final physics repair. It does rule out treating curved-wall wetting or contact-angle measurement as the next primary target.

## Caveats

- B20 shadow fields are non-streaming diagnostics. They are useful for local producer-consumer evidence but do not replace a full streamed fork.
- The `minimal` VTK field set intentionally omits some legacy required replay fields, so `s2_replay_smoke_summary.json` reports `missing_replay_fields_*`. This is expected for B20 and does not indicate missing B20 output.
- The run is already nonphysical after step 13. Steps 17-20 contain many nonfinite diagnostics and should only be used as failure evidence.

## Next Step

B20 mode 0 and mode 1 have now both been run. The next stage should be B21:

```text
H-population conservation and cancellation audit
```

B21 should add population-level h diagnostics:

```text
HPreSumAbs
HPostSumAbs
HPreCancellationRatio = sum(abs(h_i)) / max(abs(sum(h_i)), eps)
HPostCancellationRatio
HeqVelocityMachShadow
HPreMin/HPreMax
HPostMin/HPostMax
HeqSumAbs
FphiSumAbs
```

These fields should remain shadow-only. The immediate question is whether the phase field leaves `[0,1]` because individual `h_i` populations become large with near-cancelling sums, or because their actual sum is locally transported/streamed into a nonphysical value. No `PhaseF` writeback, contact-angle claim, dynamic impact, or hidden limiter is allowed at this stage.
