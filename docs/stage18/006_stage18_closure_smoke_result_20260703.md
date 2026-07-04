# Stage18 Closure Smoke Result 2026-07-03

## Scope

This note records the current Stage18 clean phase-field smoke gate status. It is not a contact-angle validation and does not claim dynamic-impact readiness.

## Model Path

`third_party/tclb_snapshots/stage18_clean_phasefield_model/models/multiphase/d3q27_pf_velocity_clean_2026`

## TCLB Timeline Under Test

`IterationInput -> PhaseFromH -> GeometryBuild -> GradPhi -> Mu -> WettingBoundary -> ForceClosure -> MomentumCollision -> PhaseCollision -> ConservativeBoundednessCorrection -> WallPhasePopulationSource -> AuditSlim -> TCLB streaming`

## Findings

1. `closure7` showed `PhaseHPostSum` finite at step 1 while `PhaseField/Rho` output was NaN.
   - Root cause: `getPhaseField()`, `getRho()`, and `getPhaseFValid()` used bare `PhaseHPostSum` instead of `PhaseHPostSum(0,0,0)`.
   - Fix: all three getters now read the saved `AddField` with explicit TCLB field accessor syntax.

2. `closure8` passed the old analyzer at 1 step, but short runs were false positives because the analyzer ignored TCLB Failcheck log lines.
   - Root cause: `stage18_smoke_analyze.py` only inspected VTI fields, not `run.log` / `run.status`.
   - Fix: analyzer now records `run_rc`, scans `run.log` for `discovered NaN`, `NaN value discovered`, and `Stopping due to Nan`, and fails the smoke if TCLB Failcheck failed.

3. `closure9` fixed `P/Pstar` quantity NaNs by replacing direct `sum(g)` output reads with saved macro fields.
   - `getPstar()` now returns `PressureMoment(0,0,0)`.
   - `getP()` now returns finite-guarded `PhysicalPressure(0,0,0)`.

4. `closure10` moved remaining first-step Failcheck failure to diagnostic quantities.
   - `Normal` was fixed to read `SolidNormalX/Y/Z(0,0,0)` with finite guards.
   - `U`, `GradPhi`, `ForceTotal`, `WallPhase`, `PressureInput`, and `ForceOverRho` getters now use explicit field accessors and finite guards.
   - Current remaining Failcheck field from closure10: `ForceHalfVelocity`, which is a ForceAudit diagnostic not guaranteed to be initialized on every output node at step 1.

## Binary Evidence

- `closure8`: `d0121ab4d09de2a9a05b7d018caca1d39276a44818d78add490564dc5f753095`
- `closure9`: `d7ee3088eeada4bbbd059858b9ce4064a5920f21389fe9c94d7e9d75d15c86cf`
- `closure10`: `43f7b11ed394052468933c6209d0f1fb7151b65d22da1122c8e709c4ff0c0661`

## Run Evidence

- `/mnt/usb1t/RUNS/runs/stage18_closure8_smoke_1step_20260703`
- `/mnt/usb1t/RUNS/runs/stage18_closure8_smoke_20step_20260703`
- `/mnt/usb1t/RUNS/runs/stage18_closure9_smoke_1step_20260703`
- `/mnt/usb1t/RUNS/runs/stage18_closure10_smoke_1step_20260703`

## Current Interpretation

The immediate blocker is still Stage18 TCLB quantity/audit-field exposure, not contact-angle physics. The conservative phase update can produce finite `PhaseHPostSum` at step 1, but a valid smoke gate requires all exported quantities and TCLB Failcheck fields to be finite.

## Next Gate

Compile `closure11` after finite-guarding remaining vector ForceAudit getters:

- `ForceHalfVelocity`
- `ForceMomentumBefore`
- `ForceMomentumAfter`
- `ForceEquivalentInjected`
- `PhaseFphiFirstMoment`

Then run:

1. `stage18_closure11_smoke_1step_20260703`
2. if pass, `stage18_closure11_smoke_20step_20260703`

Passing these gates proves only first-step and short-step stage/quantity closure for bulk, flat-wall shadow, and flat-wall per-link smoke cases.
