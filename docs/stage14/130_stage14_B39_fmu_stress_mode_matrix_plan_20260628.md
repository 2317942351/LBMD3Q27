# Stage14-B39 Fmu Stress Mode Matrix Plan

Date: 2026-06-28

Branch: `work/phasefield-c-reference-20260623`

Status: plan approved by B38 evidence and Teacher MCP review.

## Rationale

B38 localized the first short-run failure to the stress/F_mu closure path:

```text
first_stress_post_onset: step 14
first_force_over_rho_onset: step 15
first_fmu_onset: step 15
```

At the step-15 low-rho argmax:

```text
FtotalNorm = 4427.178927524575
FmuNorm = 4427.203279090591
FmuRawNorm = 11.380036184253331
FsurfNorm = 8.077141293655088e-06
FpressureNorm = 0.02434348887518085
ReplayMu = -6.0288585078271357e-05
GradPhiNorm = 0.13397463687642877
```

So actual `F_mu` dominates `F_total`, while the raw relaxed-stress `F_mu`
is small. This specifically implicates the `FmuStressClosureMode=2` path.

Teacher MCP session:

```text
session-20260628-83ed25
status = PASS
confidence = 0.92
next_action = Create B39 and run FmuStressClosureMode matrix.
```

Teacher explicitly agreed that B39 should not return to contact-angle,
curved-wall wetting, force/rho cap, or gradPhi cap.

## Code Path Under Test

`Dynamics.c.Rt`:

```text
stage14_fmu_from_stress(...)
stage14_b28_incoming_neq_active()
FmuStressClosureMode
F_mu raw from relaxed stress
F_mu replacement from b28_stress_incoming_neq when FmuStressClosureMode=2
F_total = F_surf + F_pressure + F_body + F_mu
ReplayForceOverRho = F_total / force_rho_eff
```

Existing modes:

```text
FmuStressClosureMode = 0
  legacy relaxed-stress F_mu

FmuStressClosureMode = 1
  freeze first-pass F_mu in multi-pass loops

FmuStressClosureMode = 2
  incoming nonequilibrium stress candidate
```

B39 does not add a new physics mode. It compares the existing modes under the
same B38 first-bad ledger.

## Runtime Matrix

Run root:

```text
/mnt/usb1t/RUNS/runs/stage14_B39_fmu_stress_mode_matrix_20260628
```

Common settings:

```text
case = wall_60to30_10
Density_h = 1.0
Density_l = 0.005
iterations = 20
vtk_period = 1
vtk_field_set = b33ledger
ReplayDiagnosticsMode = 1
MomentumClosureDiagnosticsMode = 1
Stage14B18ClosureDiagnosticsMode = 1
MomentumClosureProbeMode = 1
PressureClosureMode = 1
ForceDensityClosureMode = 2
ForceDensityRhoFloor = 0.005
ForceFixedPointMode = 2
PhaseAdvectionVelocityMode = 2
```

Cases:

```text
M0_legacy_stress: FmuStressClosureMode = 0
M1_freeze_iter1: FmuStressClosureMode = 1
M2_incoming_neq: FmuStressClosureMode = 2
```

## Acceptance Criteria

B39 is still diagnostic/candidate selection, not contact-angle validation.

A mode is considered better only if:

```text
no nonfinite fields by step 20
first_force_over_rho_onset is absent or delayed beyond step 20
first_fmu_onset is absent or delayed beyond step 20
StressPostOverPreRatio no longer predicts the active F_mu path
ReplayMomentumDeltaG remains interpretable against ReplayMF
PhaseFromH remains bounded in diagnostic fields
```

If mode 0 or mode 1 removes the B38 failure while mode 2 reproduces it, B40 can
test the selected mode at 100 steps. If all modes fail, the next branch is not
another limiter; it is a direct audit of stress construction and equilibrium
subtraction in TCLB moment space.

## Forbidden Claims

```text
Do not claim contact-angle validation passed.
Do not claim dynamic impact readiness.
Do not claim curved-wall wetting solved.
Do not treat mode selection as a final physical derivation.
```
