# Stage14-B38 First-Bad Force Ledger Plan

Date: 2026-06-28

Branch: `work/phasefield-c-reference-20260623`

Status: execution plan and diagnostic gate.

## Why B38 Replaces The Old B38 Contact-Angle Gate

The old runbook placed flat-wall contact-angle validation at B38. That is no
longer valid because B36 and B37 both failed. The solver still has a short-run
force closure instability in `wall_60to30_10` before any reliable contact-angle
claim can be made.

The new B38 is a first-bad ledger:

```text
Find the earliest producer-consumer edge where fields become unphysical.
Do not modify solver physics.
Do not validate contact angle.
Do not enter curved-wall or dynamic-impact work.
```

## Case

```text
case = wall_60to30_10
Density_h = 1.0
Density_l = 0.005
iterations = 20
vtk_period = 1
vtk_field_set = b33ledger
GPU = P100, CUDA_VISIBLE_DEVICES=1
```

Runtime root:

```text
/mnt/usb1t/RUNS/runs/stage14_B38_first_bad_force_ledger_20260628
```

## Required Settings

```text
ReplayDiagnosticsMode = 1
MomentumClosureDiagnosticsMode = 1
Stage14B18ClosureDiagnosticsMode = 1
MomentumClosureProbeMode = 1
PressureClosureMode = 1
ForceDensityClosureMode = 2
ForceDensityRhoFloor = 0.005
ForceFixedPointMode = 2
PhaseAdvectionVelocityMode = 2
FmuStressClosureMode = 2
```

The important addition relative to some earlier runs is:

```text
Stage14B18ClosureDiagnosticsMode = 1
```

Without it, `B18Stress*` and `B18Fmu*` shadow fields are not a valid
stress-time-level diagnostic.

## Code Path Under Test

In `Dynamics.c.Rt`, the active chain is:

```text
PhaseF
  -> calcMu(C)
  -> calcGradPhi()
  -> calc_Fp(pressure_force_input, gradPhi)
  -> calc_Fs(mu, gradPhi_force)
  -> stress reconstruction from MRT moments
  -> stage14_fmu_from_stress(stress, gradPhi_force, tau)
  -> F_total = F_surf + F_pressure + F_body + F_mu
  -> ForceOverRho = F_total / force_rho_eff
  -> U = m0[1:3] + 0.5 * F_total / force_rho_eff
  -> h update and g update
```

B38 uses the existing `b33ledger` field set and the existing
`stage14_b17_onset_mask_argmax.py` analyzer, then compresses the results with:

```text
scripts/stage14/stage14_b38_first_bad_ledger_digest.py
```

## Acceptance Criteria

B38 passes only as a diagnostic if it produces:

```text
b38_key_summary.json
b38_argmax_trace.json
stage14_B38_first_bad_ledger_digest.json
stage14_B38_first_bad_ledger_digest.md
run.log / run.status / case_metadata.json
binary_sha256.txt
```

It does not need the run to be physically stable. It must instead identify
which branch should be worked next:

```text
mu_or_laplace_branch
grad_or_surface_force_branch
fmu_stress_timelevel_branch
force_density_denominator_branch
force_assembly_or_fmu_numerator_branch
```

## Next Decision

After B38 evidence is downloaded, call Teacher MCP with code anchors and
co-located values before writing B39. B39 must be a single default-off repair
candidate selected from B38 evidence.
