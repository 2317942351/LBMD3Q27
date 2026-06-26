# Stage14-B21 H Population Audit

Date: 2026-06-26

Branch: `work/phasefield-c-reference-20260623`

Scope: diagnostic-only TCLB audit. This is not a contact-angle validation, not a solver fix, and not a dynamic-impact preflight.

## Purpose

B20 narrowed the earliest visible failure path to the phase distribution update:

```text
low-density force/stress feedback
  -> oversized phase-advection velocity
  -> oversized heq
  -> oversized hpost
  -> streamed h produces PhaseFromH outside [0,1]
  -> tmp1/Fphi/mu/pressure/F_mu later explode
```

B21 answers the next question at population level:

```text
Do individual h_i populations become large with near-cancelling sums,
or does the local heq/hpost formula directly push the signed sum outside [0,1]?
```

The answer decides whether the next repair target is TCLB AddDensity streaming/history, phase-advection velocity closure, h-equilibrium construction, or template/indexing consistency.

## Code Locations

Primary TCLB snapshot:

```text
third_party/tclb_snapshots/stage17B_diffuse_solid_shadow/models/multiphase/d3q27_pf_velocity/Dynamics.R
third_party/tclb_snapshots/stage17B_diffuse_solid_shadow/models/multiphase/d3q27_pf_velocity/Dynamics.c.Rt
```

Driver and analyzer:

```text
scripts/stage14/stage14_s2_replay_smoke.py
scripts/stage14/stage14_b17_onset_mask_argmax.py
scripts/stage14/build_stage14_b18_shadow_closure_remote.sh
scripts/stage14/compile_stage14_b18_after_source_remote.sh
scripts/stage14/run_stage14_b18_shadow_closure_remote.sh
```

Remote execution:

```text
server: yuan@192.168.1.16
GPU: CUDA_VISIBLE_DEVICES=1
compile lane: /home/yuan/src/TCLB_lbm2026_compile_lane
binary: /home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
run root base: /mnt/usb1t/RUNS/runs
```

## B21 Fields

All B21 fields are `AddField(..., group="runtime_diagnostics")`. They are not `AddDensity`, do not stream, and do not write back to `h`, `PhaseF`, `g`, `F_total`, `U/V/W`, or `WallGhost`.

Mode switch:

```text
Stage14B21HPopulationAuditMode = 0  default, legacy behavior
Stage14B21HPopulationAuditMode = 1  output B21 audit fields
```

Probe activation:

```text
B21ProbeActive
```

Incoming h population diagnostics:

```text
B21HPreSum
B21HPreSumAbs
B21HPreL2
B21HPreMin / B21HPreMax / B21HPreMaxAbs / B21HPreMaxAbsIndex
B21HPrePosSum / B21HPreNegSumAbs
B21HPreCancellationRatio = sum(abs(h_i)) / max(abs(sum(h_i)), 1e-30)
B21HPreSignedRange
```

Equilibrium diagnostics:

```text
B21HeqSum
B21HeqSumMinusC
B21HeqSumAbs
B21HeqL2
B21HeqMin / B21HeqMax / B21HeqMaxAbs / B21HeqMaxAbsIndex
B21HeqCancellationRatio
B21HeqVelocitySquared
B21HeqVelocityMachShadow = sqrt(3 * |u_phase|^2)
```

Source diagnostics:

```text
B21FphiSum
B21FphiSumAbs
B21FphiL2
B21FphiMin / B21FphiMax / B21FphiMaxAbs / B21FphiMaxAbsIndex
B21FphiCancellationRatio
B21Tmp1
B21NormalMag
```

Post-update shadow diagnostics:

```text
B21HPostSum
B21HPostSumAbs
B21HPostL2
B21HPostMin / B21HPostMax / B21HPostMaxAbs / B21HPostMaxAbsIndex
B21HPostPosSum / B21HPostNegSumAbs
B21HPostCancellationRatio
B21HPostOutOfBoundsFlag
B21HPostSumMinusFormula
```

The local shadow formula is the same algebra as the active h update:

```text
hpost_i = hpre_i - omega * (hpre_i - heq_i + 0.5 * Fphi_i) + Fphi_i
```

In this model `models/multiphase/d3q27_pf_velocity/model.R` defines:

```text
omega = PV("omega_phi")
```

so the B21 shadow path uses the same phase relaxation symbol as the active
generated h-update. B21 is still output-only: it computes additional local
diagnostics before the active `C(h, ...)` write, and it does not change
streaming or collision.

`B21HPostSumMinusFormula` must stay near roundoff. If it is the first large marker, the next action is to audit generated TCLB indexing/template expansion before changing the physical model.

## Analyzer Branches

`scripts/stage14/stage14_b17_onset_mask_argmax.py` now reports `b21_primary_branch`.

Decision tree:

```text
hpost_formula_consistency_or_template_indexing
  B21HPostSumMinusFormula crosses first.

incoming_h_population_streaming_history_contamination
  B21HPreMaxAbs is already large before or with heq/hpost.

incoming_h_population_cancellation
  B21HPreCancellationRatio is already large before or with heq/hpost.

phase_advection_velocity_mach_first
  B21HeqVelocityMachShadow crosses before heq/hpost amplitude.

heq_population_large_before_hpost
  B21HeqMaxAbs crosses before or with hpost.

hpost_population_update_amplification
  B21HPostMaxAbs crosses before or with hpost sum out-of-bounds.

hpost_sum_out_of_bounds_without_large_population_marker
  B21HPostSum or B21HPostOutOfBoundsFlag fails without earlier population-amplitude onset.
```

## First Run Gate

Run B21-A before any wider matrix:

```text
case: wall_60to30_10
Density_h = 1.0
Density_l = 0.005
iterations = 20
vtk_period = 1
VTK_FIELD_SET = b21
PressureClosureMode = 1
ForceFixedPointMode = 2
PhaseAdvectionVelocityMode = 1
MomentumClosureDiagnosticsMode = 1
Stage14B18ClosureDiagnosticsMode = 1
Stage14B20HUpdateDiagnosticsMode = 0 or 1
Stage14B21HPopulationAuditMode = 1
```

Recommended wrapper environment:

```bash
ROOT=/mnt/usb1t/RUNS/runs/stage14_B21_hpopulation_audit_M11_20260626
PHASE_ADV_MODE=1
B20_MODE=0
B21_MODE=1
VTK_FIELD_SET=b21
ITERATIONS=20
bash /home/yuan/run_stage14_b18_shadow_closure_remote.sh
```

## Execution Result

### Build-chain issue found and fixed

The first B21 run was invalid because B21 fields were requested in `case.xml`
but absent from VTI. The run log showed:

```text
WARNING ! Unknown setting Stage14B21HPopulationAuditMode
```

Root cause:

```text
src/Lists.cpp.Rt had not been regenerated.
```

Generated CUDA files contained B21 constants and quantity accessors, but the
host-side `model->settings.by_name()` table in `Lists.cpp` did not contain
`Stage14B21HPopulationAuditMode`. Therefore XML `<Param>` parsing could not
activate the B21 branch.

Fix applied:

```text
scripts/stage14/build_stage14_b18_shadow_closure_remote.sh
scripts/stage14/compile_stage14_b18_after_source_remote.sh
```

now explicitly regenerate/check:

```text
Consts.h
Dynamics.h
Dynamics.c
Global.h
Global.cpp
Lists.cpp
cuda.cu
```

and verify both CUDA accessors and host setting registration:

```text
SETTINGS_Stage14B21HPopulationAuditMode in Consts.h
"Stage14B21HPopulationAuditMode" in Lists.cpp
B21HPostSumMinusFormula in Dynamics.h/cuda.cu
```

Successful binary:

```text
sha256: bf9e6e043ce8ebe5161667d3890c1a28c5480ecbaed1531ae3d54cd6ee3469a4
compile log: /home/yuan/lbm2026_stage14_B21_compile_lists_20260626.log
```

### Runtime evidence

Run root:

```text
/mnt/usb1t/RUNS/runs/stage14_B21_hpopulation_audit_M11_fixed_20260626
```

Local light artifacts:

```text
artifacts/stage14_B21_hpopulation_audit_20260626/
```

Run configuration:

```text
case: wall_60to30_10
Density_h = 1.0
Density_l = 0.005
iterations = 20
GPU = 1 (P100)
VTK_FIELD_SET = b21
PressureClosureMode = 1
ForceFixedPointMode = 2
PhaseAdvectionVelocityMode = 1
Stage14B21HPopulationAuditMode = 1
```

Status:

```text
solver RUN_RC=0
driver.status = DRIVER_RC=3
analyzer.status = ANALYZER_RC=0
run.log unknown setting count = 0
VTI count during run = 21
```

`DRIVER_RC=3` is expected for this diagnostic window because the smoke summary
detects nonphysical field growth. It is not a compile/runtime crash.

After light artifacts were downloaded, remote B21 `output/*.vti` files were
deleted as regenerable data because `/mnt/usb1t` dropped below the 50 GB free
space threshold. Logs, JSON, CSV, case XML, and compile evidence were preserved.

### B21 finding

The valid B21-A run supports:

```text
b21_primary_branch = phase_advection_velocity_mach_first
```

Key onsets from `b18_key_summary.json`:

```text
step 2, near_interface_wall:
  B21HeqVelocityMachShadow = 908.4411806545031
  B21HeqMaxAbs             = 114.40250189377312
  B21HPostMaxAbs           = 81.71269826549953
  ReplayHPostMaxAbs        = 81.71269826549953
  ForceOverRhoNorm         = 4250.150805283527

step 2, low_rho:
  ReplayPhaseFromH         = 36125.34177846528

step 3:
  B21HPreMaxAbs            = 18112.19758347184
  B21HPreCancellationRatio = 460925.9514810717
  B21HPostSum              = 19488.0
```

Interpretation:

```text
HPre is not the first visible trigger.
The phase-advection velocity feeding heq is already unphysical at step 2.
heq becomes huge before the incoming h population is polluted at step 3.
The active hpost diagnostic agrees with ReplayHPostMaxAbs at the first onset.
```

This pushes the next audit away from incoming `h` AddDensity streaming as the
first trigger, and toward:

```text
phase_adv_U/V/W producer chain
ForceOverRho denominator and velocity selection
m0/U half-force timing used by h equilibrium
```

### Caveats

`B21HPostSumMinusFormula` crosses the absolute threshold at step 3 in the
20-step run, but this happens after the step-2 Mach/heq/hpost blow-up. A 2-step
visibility run showed the formula residual near roundoff, and `model.R` confirms
`omega = omega_phi`. Therefore the residual is not the earliest supported branch.

The current report must not be read as:

```text
contact-angle validation
static wetting solved
curved wall solved
dynamic-impact readiness
```

It is only a population-level localization of the early flat-wall instability.

## Minimal Matrix After B21-A

Use the same binary and B21 fields:

```text
M00: PressureClosureMode=0, ForceFixedPointMode=0, PhaseAdvectionVelocityMode=0
M01: PressureClosureMode=0, ForceFixedPointMode=2, PhaseAdvectionVelocityMode=1
M10: PressureClosureMode=1, ForceFixedPointMode=0, PhaseAdvectionVelocityMode=1
M11: PressureClosureMode=1, ForceFixedPointMode=2, PhaseAdvectionVelocityMode=1
```

M11 corresponds to the current diagnostic closure lane. M00 keeps the legacy-like comparison. The matrix is not a validation set; it is a closure-localization set.

Given the current B21-A result, the full matrix is lower priority than a narrow
B22 producer audit of `phase_adv_U/V/W`. If a matrix is still run, it should use
the `b21` VTK field set to keep B21 fields visible and reduce VTI size.

## B22 Direction

Next stage should audit the producer-consumer timeline for the velocity used by
the h-equilibrium:

```text
m0[1:3]
  -> ForceOverRho / force_rho_inv
  -> momentum_U/V/W
  -> phase_adv_U/V/W
  -> heq
  -> hpost
  -> PhaseFromH after streaming
```

Required B22 additions should remain diagnostic-only:

```text
B22PhaseAdvUx/Uy/Uz
B22PhaseAdvSpeed
B22M0Ux/Uy/Uz
B22MomentumUx/Uy/Uz
B22ForceOverRhoX/Y/Z
B22ForceRhoRaw
B22ForceRhoEffective
B22HeqFromM0MaxAbs
B22HeqFromMomentumMaxAbs
B22HeqFromBoundedShadowMaxAbs
B22VelocitySourceId
```

Acceptance criteria for B22:

```text
1. Identify which velocity source first exceeds Mach-like bounds.
2. Confirm whether ForceOverRho or velocity selection feeds the huge heq.
3. Keep all new fields AddField/runtime_diagnostics only.
4. Do not introduce clamps, pressure shifts, or solver fixes in the same commit.
5. Do not return to WallGhost/curved wetting until flat-wall h-equilibrium velocity closure is understood.
```

## Guardrails

- Do not claim contact-angle validation.
- Do not claim static wetting is solved.
- Do not enter sphere/cylinder wetting write path or dynamic impact.
- Do not introduce hidden clamp, damping, force cancellation, pressure shift, or bounded velocity as a solver fix.
- Do not interpret `B20` or `B21` shadow fields as streamed physics.
- Do not commit raw `*.vti`, `*.pvti`, `*.pri`, binaries, archives, credentials, pycache, or large `*_argmax_trace.json`.

## Acceptance Criteria For B21 Evidence

A useful B21 result must include:

```text
compiled binary sha256
run root
run_config.txt
driver.status
analyzer.status
b18_key_summary.json
b18_first_onset.json
b18_mask_stats.csv
case run.log/run.stderr/run.status
```

The report must state only which branch is supported by the evidence and what next code audit follows from that branch.
