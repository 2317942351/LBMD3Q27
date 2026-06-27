# Stage14-B29 Short Stability Result

Date: 2026-06-27

Branch: `work/phasefield-c-reference-20260623`

Status: short stability gate failed. Analyzer execution succeeded, but the
candidate did not satisfy the B29 physical gate.

## Runtime Evidence

Remote root:

```text
/mnt/usb1t/RUNS/runs/stage14_B29_short_stability_20260627
```

Local light artifacts:

```text
artifacts/stage14_B29_short_stability_20260627/
```

Binary:

```text
sha256 = 7ebe7053bdcb4a88468f58b9f4f0bd30e189fd589709c9849e357c4d0fedd74f
```

Execution status:

```text
stage14_B29.status = OVERALL_RC=0
B29_020 analyzer = RC=0
B29_100 analyzer = RC=0
```

This means the cases ran and were analyzed. It does not mean the B29 gate
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
PhaseAdvectionVelocityMode = 1
```

## Result

| Probe | First momentum threshold | First heq Mach threshold | First PhaseFromH threshold | First force/rho threshold |
|---|---:|---:|---:|---:|
| `B29_020` | step 12, 1.577 | step 13, 4.906 | step 15, 8039.9 | step 15, 8.86e5 |
| `B29_100` | step 15, 4.43e5 | step 15, 576.9 | step 15, 8039.9 | step 15, 8.86e5 |

The B28 candidate did interrupt the 14-step force/phase blow-up, but the same
chain reappears at step 15 in the longer gate.

## Interpretation

`FmuStressClosureMode=2` is a useful diagnostic candidate, not a sufficient
stabilization or physics closure.

The next unresolved producer is no longer only `F_mu` stress. The B21/B22
history and B29 show that the phase-advection velocity consumed by the h
equilibrium can become supersonic/large before or at the same time as the phase
population leaves the physical interval:

```text
B22MomentumSpeed / B22PhaseAdvSpeed
  -> B21HeqVelocityMachShadow
  -> h update
  -> PhaseFromH out of bounds
  -> force/rho and pressure/F_mu amplification
```

Therefore B30 cannot be flat-wall contact-angle validation yet. It must first
be a phase-advection velocity closure candidate gate.

## Next Step

Implement a default-off explicit candidate:

```text
PhaseAdvectionVelocityMode = 2
```

Proposed meaning:

```text
use pre-force m0 velocity, bounded by Stage14B18VelocityBound, only for h
equilibrium/Fphi construction; do not change momentum U, g update, WallGhost,
or PhaseF writes.
```

Then rerun the short gate with:

```text
FmuStressClosureMode = 2
PhaseAdvectionVelocityMode = 2
wall_60to30_10, density ratio 200, 20 then 100 steps
```

No contact-angle or dynamic-impact claim is allowed until this short stability
gate passes.
