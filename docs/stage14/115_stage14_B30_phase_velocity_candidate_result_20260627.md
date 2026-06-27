# Stage14-B30 Phase Velocity Candidate Result

Date: 2026-06-27

Branch: `work/phasefield-c-reference-20260623`

Status: runtime/analyzer succeeded, but the physical stability gate is still
not passed. B30 resolves the short-run h-equilibrium / phase-advection /
`PhaseFromH` failure path, while a separate force amplification path remains.

## Runtime Evidence

Remote root:

```text
/mnt/usb1t/RUNS/runs/stage14_B30_phase_velocity_candidate_20260627
```

Local light artifacts:

```text
artifacts/stage14_B30_phase_velocity_candidate_20260627/
```

Binary:

```text
sha256 = a621deb2f2576b46e03d7176d808044e6eae5de45052f6badddecc1ae5474486
```

Execution status:

```text
stage14_B30.status = OVERALL_RC=0
B30_020 analyzer = RC=0
B30_100 analyzer = RC=0
```

This means the cases ran and were analyzed. It does not mean the closure gate
passed.

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
Stage14B18VelocityBound = 0.2
```

`PhaseAdvectionVelocityMode=2` means the h-equilibrium consumes the pre-force
`m0` velocity bounded by `Stage14B18VelocityBound`. This is only applied to the
phase-population update. It does not change momentum `U`, the g-population
update, `WallGhost`, or `PhaseF` writes.

## Result

| Probe | h-equilibrium Mach threshold | PhaseFromH threshold | First force/rho threshold | First F_mu threshold | First pressure-force threshold |
|---|---:|---:|---:|---:|---:|
| `B30_020` | none | none | step 15, 8.85e5 | step 15, 4.43e3 | step 16, 1.70e7 |
| `B30_100` | none | none | step 15, 8.85e5 | step 15, 4.43e3 | step 20, 2.46e68 |

The B30 candidate therefore removed the B29 path:

```text
large phase-advection velocity
  -> h-equilibrium Mach violation
  -> PhaseFromH out of bounds
```

However, it did not remove:

```text
F_total / rho
  -> F_mu / pressure amplification
  -> momentum field blow-up
```

## Interpretation

B30 is a useful closure split, not a completed physical fix. It proves that the
phase-population update can be protected from a bad post-force velocity source,
but it also exposes an independent momentum-force closure failure.

The digest marks the remaining primary branch as:

```text
force_over_rho_density_closure
```

The B18 shadow denominators were equal at the first B30 threshold:

```text
raw force/rho       = 8.854349865e5
floor force/rho     = 8.854349865e5
phase-mix force/rho = 8.854349865e5
```

This means a density-denominator candidate must be tested explicitly, but it is
unlikely to be the whole solution. If `ForceDensityClosureMode=2` reproduces the
same onset, the denominator branch should be demoted and B32 planning must move
to force numerator / pressure / F_mu closure.

## Next Step

Run B31A as a controlled force-density denominator candidate:

```text
FmuStressClosureMode = 2
PhaseAdvectionVelocityMode = 2
ForceDensityClosureMode = 2
PressureClosureMode = 1
Density_l = 0.005
wall_60to30_10, 20 and 100 steps
```

`ForceDensityClosureMode=2` should use a bounded phase-mixture density for
`F_total/rho` and MRT forcing denominator. Defaults must remain legacy. No
contact-angle validation or dynamic-impact claim is allowed until this short
momentum-force gate passes.
