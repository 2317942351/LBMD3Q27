# Stage14-B31 Force Density Candidate Result

Date: 2026-06-27

Branch: `work/phasefield-c-reference-20260623`

Status: runtime/analyzer succeeded, but the force-density denominator candidate
failed the physical gate. B31 does not support promoting
`ForceDensityClosureMode=2` as a repair.

## Runtime Evidence

Remote root:

```text
/mnt/usb1t/RUNS/runs/stage14_B31_force_density_candidate_20260627
```

Local light artifacts:

```text
artifacts/stage14_B31_force_density_candidate_20260627/
```

Binary:

```text
sha256 = 263bdd7bfc48e179dcab367f61481814b426682f96a32ddf2a6d96bb47d7d97b
```

Execution status:

```text
stage14_B31.status = OVERALL_RC=0
B31_020 driver/analyzer = RC=0
B31_100 driver/analyzer = RC=0
digest = RC=0
```

This only means execution and analysis completed. It is not a physical pass.

## Case Setup

Both probes used:

```text
case = wall_60to30_10
Density_h = 1.0
Density_l = 0.005
FmuStressClosureMode = 2
PressureClosureMode = 1
ForceFixedPointMode = 2
PhaseAdvectionVelocityMode = 2
ForceDensityClosureMode = 2
```

`ForceDensityClosureMode=2` uses a bounded phase-mixture density for the active
`F_total/rho` and MRT force denominator. It does not change `F_total` itself.

## Result

| Probe | ForceDensityClosureMode | First force/rho threshold | First F_mu threshold | First pressure-force threshold | PhaseFromH threshold |
|---|---:|---:|---:|---:|---:|
| `B31_020` | 2 | step 15, 8.85e5 | step 15, 4.43e3 | step 16, 1.70e7 | none |
| `B31_100` | 2 | step 15, 8.85e5 | step 15, 4.43e3 | step 20, 2.46e68 | none |

B31 reproduces B30's remaining failure:

```text
F_total/rho onset: step 15, 8.854349865e5
F_mu onset:        step 15, 4.427203279e3
pressure force:    step 16 or later
PhaseFromH:        no configured threshold crossing
```

The raw, floored, and phase-mixture denominator shadows remain identical at the
first threshold:

```text
B18ForceOverRhoRawNorm        = 8.854349865e5
B18ForceOverRhoDensityFloor   = 8.854349865e5
B18ForceOverRhoPhaseMixture   = 8.854349865e5
```

## Interpretation

B31 demotes the density-denominator branch. The remaining failure is now more
likely a force numerator and stress/pressure reconstruction problem:

```text
F_surf / F_mu / F_pressure numerator
  -> F_total
  -> F_total / rho
  -> momentum field growth
```

`PhaseAdvectionVelocityMode=2` is still useful because it prevents the h update
from being the first visible failure, but the momentum force path remains
unstable.

## Next Step

B32 must not start dynamic impact. B32 should be a dynamic-impact preflight
blocker plus a short force-numerator split:

```text
FmuStressClosureMode = 2
PhaseAdvectionVelocityMode = 2
ForceDensityClosureMode = 2
PressureClosureMode = 1
MomentumForceMode = 0, 1, 2, 3, 4, 5
wall_60to30_10, 20 steps
```

The goal is to decide whether the first remaining producer is dominated by
`F_mu`, `F_surf`, `F_pressure`, or their coupled reconstruction. Dynamic impact
is blocked until this flat-wall momentum force gate is stable.
