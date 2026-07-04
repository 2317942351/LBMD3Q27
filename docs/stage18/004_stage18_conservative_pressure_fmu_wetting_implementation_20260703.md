# Stage18 Conservative Phase, Pressure/Fmu, And Wetting Source Implementation

Date: 2026-07-03

Branch: `work/phasefield-c-reference-20260623`

Model:

```text
third_party/tclb_snapshots/stage18_clean_phasefield_model/models/multiphase/d3q27_pf_velocity_clean_2026
```

Status:

```text
implementation_compiles
contact_angle_not_validated
dynamic_impact_blocked
```

## Purpose

This change implements the first real Stage18 physical-write baseline requested
after the clean architecture split:

1. make the phase equation conservative at the source-moment level;
2. replace implicit pressure/F_mu behavior with explicit closure modes;
3. make wetting write through passive streamed `h_i` wall sources, not by late
   `PhaseF` overwrite.

It is not a claim that static contact angle is solved. It is the first compiled
solver baseline where the three main repair paths live in named TCLB stages and
settings.

## TCLB Producer-Consumer Timeline

The active `Iteration` action is now:

```text
IterationInput
  -> PhaseFromH
  -> GeometryBuild
  -> GradPhi
  -> Mu
  -> WettingBoundary
  -> ForceClosure
  -> MomentumCollision
  -> PhaseCollision
  -> ConservativeBoundednessCorrection
  -> WallPhasePopulationSource
  -> AuditSlim
  -> TCLB framework streaming
```

Key ownership rules:

- `h0..h26` remain `AddDensity` streamed populations.
- `PhaseF` is an `AddField` produced only by `PhaseFromH` or boundedness
  correction after an explicit `h_i` projection.
- `WallPhase` is an `AddField`; it is not streamed.
- `WallPhasePopulationSource` is now the final writer of wall/solid `h_i` in
  the action, so next-step streaming consumes a passive wall source.
- `ForceClosure` loads current `g_i` and reconstructs `PressureMoment=sum(g)`
  in the same stage before computing pressure force.

## Implemented Work 1: Conservative Phase Equation

Changed files:

```text
Dynamics.R
Dynamics.c.Rt
```

New non-streaming audit fields:

```text
PhaseHPreSum
PhaseHeqSum
PhaseFphiSum
PhaseHPostSum
PhaseCorrectionDelta
```

Settings:

```text
PhaseEquationMode = 0 legacy-compatible
PhaseEquationMode = 1 normalized source
PhaseEquationMode = 2 conservative Allen-Cahn source  [default]

PhaseBoundednessMode = 0 off
PhaseBoundednessMode = 1 shadow ledger               [default]
PhaseBoundednessMode = 2 local bounded h projection
```

Implementation:

- `Stage18_PhaseCollision()` now records:

```text
sum(h_i before collision)
sum(h_i^eq)
sum(F_phi_i)
sum(h_i after collision)
```

- In `PhaseEquationMode=2`, the code projects:

```text
sum(h_i^eq) -> C
sum(F_phi_i) -> 0
sum(h_i after update) -> C
```

using phase-lattice weights. This makes the local phase collision step
zeroth-moment conservative.

- `Stage18_ConservativeBoundednessCorrection()` now has a real write path:

```text
PhaseBoundednessMode=1:
  only records the correction needed to bring sum(h_i) into [PhaseField_l, PhaseField_h]

PhaseBoundednessMode=2:
  projects sum(h_i) locally into [PhaseField_l, PhaseField_h]
  distributes the local correction with phase-lattice weights
  updates PhaseF/RhoField consistently
```

Important limitation:

This is not a global mass-redistribution conservative limiter. A strict global
mass-conservative correction requires a reduction of total clipped mass and a
second distribution pass over eligible interface cells. TCLB does not provide
that inside a single local device stage. The current mode is a local bounded
projection with explicit mass ledger, intended as a safety gate and debugging
path.

## Implemented Work 2: Pressure And F_mu Closure

New fields:

```text
PressureInput
PressureReference
StressXX
StressXY
StressXZ
StressYY
StressYZ
StressZZ
```

Settings:

```text
PressureClosureMode = 0 legacy m0[0] / pstar
PressureClosureMode = 1 physical pressure pstar*rho*cs2        [default]
PressureClosureMode = 2 physical pressure minus reference
PressureReferenceValue = 0

ForceClosureMode = 1 clean F_surf + F_pressure + F_body        [default]
ForceClosureMode = 2 clean plus F_mu
FmuStressMode = 0 off                                           [default]
FmuStressMode = 1 non-equilibrium pre-collision stress
```

Implementation:

- `Stage18_ForceClosure()` now reconstructs the current pressure-like moment
  from current loaded `g_i`:

```text
pnorm = sum(g_i)
PressureMoment = pnorm
PhysicalPressure = PressureMoment * rho * cs2
```

- `stage18_pressure_input()` chooses the actual pressure consumed by
  `stage18_calc_Fp()`:

```text
mode 0: PressureMoment
mode 1: PhysicalPressure
mode 2: PhysicalPressure - PressureReferenceValue
```

- `F_mu` is no longer a stale placeholder. If enabled with
  `ForceClosureMode=2` and `FmuStressMode=1`, it is reconstructed from
  pre-collision non-equilibrium momentum populations in `ForceClosure`, before
  `MomentumCollision`.

Important limitation:

`F_mu` remains disabled by default. The implementation makes the time level
auditable, but it still requires a static droplet pressure-jump/spurious-current
gate before it can be called physically validated.

## Implemented Work 3: Wetting BC Write Path

Changed TCLB action order:

```text
... PhaseCollision
    ConservativeBoundednessCorrection
    WallPhasePopulationSource
```

`WallPhasePopulationSource` was also moved after `InitDistributions` in `Init`
and `InitFields`.

Reason:

The first RT attempt failed because `WallPhasePopulationSource` read `h_i`
before `InitDistributions` had written them. That error confirmed the previous
stage-order suspicion: in TCLB, a wall source stage must be placed after a valid
`h_i` producer and must save group `h`.

Implementation:

- `WallPhasePopulationSource` now loads group `h`, `Wetting`, and `SolidGeom`.
- It saves group `h` and wall-source audit fields.
- When:

```text
(IamWall || IamSolid)
WettingWriteMode > 0
WallPhaseValid > 0
```

it writes:

```text
h_i = WallPhase * Gamma_i(u=0)
```

and records:

```text
WallHIncomingMass = old sum(h_i)
WallHOutgoingMass = WallPhase
WallHNetMass = WallPhase - old sum(h_i)
```

Default remains:

```text
WettingWriteMode = 0
```

so contact-angle write is still off unless explicitly enabled in a gate case.

## Compile Result

Remote server:

```text
yuan@192.168.1.16
```

Compile lane:

```text
/home/yuan/src/TCLB_lbm2026_compile_lane
```

Target:

```text
d3q27_pf_velocity_clean_2026_q27_stage18closure
```

Binary:

```text
/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_clean_2026_q27_stage18closure/main
```

Log:

```text
/home/yuan/lbm2026_stage18_closure_compile_20260703.log
```

Result:

```text
STAGE18_SPLIT_SOURCE_AUDIT_OK=1
BUILD_RC=0
sha256=c59a44ec5e5a816f9b113e66813e7934afbe7cc8587c5bffc4a170a541f9e0c3
```

The first compile attempt found a real TCLB action-order bug:

```text
WallPhasePopulationSource read h_i before InitDistributions wrote h_i in Init.
```

That was fixed by moving wall-source writes after `InitDistributions` and after
`ConservativeBoundednessCorrection`.

The second compile attempt found a template-symbol bug:

```text
omega was emitted literally instead of omega_phi.
```

That was fixed by explicitly using `omega_phi` in the generated phase update.

## What This Proves

This proves:

- the three requested repair paths now have concrete code locations;
- TCLB source generation accepts the stage load/save ownership;
- CUDA build succeeds for the Stage18 closure target;
- wetting write is no longer only a dead function; when enabled it is a saved
  `h_i` passive source stage.

This does not prove:

- static contact angle correctness;
- pressure closure physical correctness;
- F_mu stress correctness;
- global mass-conservative boundedness;
- cylinder/sphere wetting correctness;
- dynamic impact readiness.

## Next Gate

Run only minimal smoke cases first:

```text
bulk neutral, 1-20 steps
flat wall theta=90, WettingWriteMode=0, 1-20 steps
flat wall theta=90, WettingWriteMode=1, 1-20 steps
```

Required outputs:

```text
PhaseField finite and within bounds
PhaseHPreSum / PhaseHeqSum / PhaseFphiSum / PhaseHPostSum
MassCorrectionApplied
PressureInput
ForceOverRho
Stage18Violation
WallHIncomingMass / WallHOutgoingMass / WallHNetMass
```

Only after those pass should flat-wall 30/150 morphology and decoupled response
be run.
