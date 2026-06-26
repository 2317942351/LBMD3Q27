# Stage14-B22 Velocity Producer Audit

Date: 2026-06-26

Branch: `work/phasefield-c-reference-20260623`

Scope: diagnostic-only TCLB audit. This is not a contact-angle validation, not a solver fix, and not a dynamic-impact preflight.

## Purpose

B21 showed that the immediate phase-population failure is tied to oversized phase equilibrium and post-update `h` populations. B22 answers the next producer question:

```text
Which velocity source first becomes large enough to make h-equilibrium nonphysical?

m0 velocity from streamed g populations
post-force momentum velocity U/V/W
F_total / rho half-force correction
or a bounded shadow velocity that would keep heq algebra finite
```

This audit is required before B23-B25. If B22 says `m0` is already large, the next target is g-population history and MRT force insertion. If B22 says only the post-force velocity is large, the next target is `F/rho`, force split, stress reconstruction, and pressure closure.

## Current Important Finding

The first B22 smoke run must not be used as physical evidence.

Remote root:

```text
/mnt/usb1t/RUNS/runs/stage14_B22_velocity_producer_probe_20260626_smoke
```

The run itself recognized the setting:

```text
Stage14B22VelocityProducerAuditMode = 1
```

However, generated TCLB code was only partially refreshed. `Dynamics.c`, `Dynamics.h`, `Lists.cpp`, and `cuda.cu` contained B22 symbols, but the generated accessor/output layer was stale:

```text
Lattice.cu
Lattice.h
LatticeAccess.inc.cpp
LatticeContainer.h
LatticeContainer.inc.cpp
Solver.cpp
Solver.h
SUMMARY / SUMMARY.Rdata
```

The stale accessor layer lacked B22 quantity/getter paths such as:

```text
GetB22ProbeActive
load_B22ProbeActive
```

This explains the impossible VTI pattern:

```text
B22ProbeActive, B22M0Speed, B22MomentumSpeed, B22PhaseAdvSpeed,
B22ForceOverRhoMag, B22FmuMag, B22HeqFromM0MaxAbs, ...
```

all copied the same values as nearby B21 fields, especially `B21HPostMaxAbs`.

Therefore the temporary local files:

```text
artifacts/b22_smoke_key_summary_tmp.json
artifacts/b22_smoke_mask_stats_tmp.csv
```

are invalid for physical interpretation. They are retained only as compile-chain failure evidence until replaced by a valid B22 run.

## Compile Chain Fix

The compile script now forces a complete TCLB source regeneration before build:

```text
scripts/stage14/compile_stage14_b18_after_source_remote.sh
```

It now regenerates:

```text
SUMMARY
Consts.h
Dynamics.h
Dynamics.c
Global.h
Global.cpp
Lists.cpp
cuda.cu
Lattice.cu
Lattice.h
LatticeAccess.inc.cpp
LatticeContainer.h
LatticeContainer.inc.cpp
Solver.cpp
Solver.h
```

It also deletes stale top-level object files before `make`, so a new binary cannot link a mixed old/new object set.

Required post-generation checks:

```text
GetB22ProbeActive in Lattice.cu
load_B22ProbeActive in LatticeAccess.inc.cpp
GetB22ProbeActive in Solver.cpp
Stage14B22VelocityProducerAuditMode in Lists.cpp / Consts.h / cuda.cu
```

The fixed binary used for the valid B22 runs is:

```text
2a5729a8041dcd3db150149b623764862778d799cd657b55ab43fc2cab47cef6
/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
```

## Fixed Smoke Result

Remote root:

```text
/mnt/usb1t/RUNS/runs/stage14_B22_velocity_producer_probe_20260626_fixed
```

Local artifact mirror:

```text
artifacts/stage14_B22_velocity_producer_audit_20260626/fixed_step3/
```

The fixed 3-step smoke passed the B22 field-validity gate:

```text
DRIVER_RC=0
ANALYZER_RC=0
B22ProbeActive is 0/1, not a copied B21 scalar.
B22 fields are no longer all identical.
```

Representative step-2 maxima:

```text
B22M0Speed = 9.39e-4
B22MomentumSpeed = 9.39e-4
B22ForceOverRhoMag = 1.61e-3
B22HeqFromM0MaxAbs = 0.296
```

This run is a field-validity smoke only. It does not reach the onset window.

## Fixed 20-Step Result

Remote root:

```text
/mnt/usb1t/RUNS/runs/stage14_B22_velocity_producer_probe_20260626_step20_fixed
```

Local artifact mirror:

```text
artifacts/stage14_B22_velocity_producer_audit_20260626/fixed_step20/
```

Run status:

```text
DRIVER_RC=3
ANALYZER_RC=0
```

`DRIVER_RC=3` is the expected diagnostics-failure code from threshold crossings, not a binary crash.

Key onset evidence:

| field | first step | mask | value |
|---|---:|---|---:|
| `B22MomentumSpeed` | 11 | `low_rho` | 2.8205 |
| `B22M0Speed` | 12 | `low_rho` | 1.9236 |
| `B22PhaseAdvSpeed` | 12 | `low_rho` | 1.9236 |
| `B21HeqVelocityMachShadow` | 12 | `low_rho` | 3.3317 |
| `ReplayPhaseFromH` out of bounds | 13 | `low_rho` | 2.7912 |
| `B22ForceOverRhoMag` | 13 | `near_interface_wall` | 2092.38 |
| `B22FpressureMag` | 14 | `low_rho` | 94703.74 |
| `B22FmuMag` | 14 | `low_rho` | 100723.55 |

The analyzer branch is:

```text
b21_primary_branch = phase_advection_velocity_mach_first
b22_primary_branch = post_force_momentum_velocity_first
```

Current supported chain:

```text
post-force momentum velocity grows first
  -> streamed/pre-force m0 and selected phase-advection velocity grow next
  -> h-equilibrium becomes Mach-like
  -> h update / PhaseFromH exits [0,1]
  -> F/rho, pressure force, and F_mu amplify after the phase loss begins
```

This revises the earlier B21-only interpretation: after full source regeneration, the first visible B22 producer is the post-force momentum velocity, not a direct PhaseF/WallGhost write-path issue.

## B22 Diagnostic Fields

Mode switch:

```text
Stage14B22VelocityProducerAuditMode = 0  default, legacy behavior
Stage14B22VelocityProducerAuditMode = 1  output B22 audit fields
```

Core outputs:

```text
B22ProbeActive
B22M0U / B22M0Speed
B22MomentumU / B22MomentumSpeed
B22PhaseAdvU / B22PhaseAdvSpeed
B22ForceOverRho / B22ForceOverRhoMag
B22ForceRhoRaw
B22ForceRhoEffective
B22HalfForceU
B22FpressureMag
B22FsurfMag
B22FmuMag
B22FtotalMag
B22HeqFromM0MaxAbs
B22HeqFromMomentumMaxAbs
B22HeqFromBoundedShadowMaxAbs
B22VelocitySourceId
B22VelocityMachExceededFlag
```

All B22 fields are diagnostics. They must not write back to `g`, `h`, `PhaseF`, `WallGhost`, `F_total`, or `U/V/W`.

## Acceptance Rules

A valid B22 run must satisfy:

```text
B22ProbeActive is 0 or 1, not a copied large physical field.
B22 scalar fields are not all identical.
B22VelocitySourceId matches PhaseAdvectionVelocityMode.
Generated code contains B22 getter/accessor paths in Lattice.cu, Lattice.h, LatticeAccess.inc.cpp, Solver.cpp.
run.log contains no unknown-setting warnings.
```

Only after these checks pass may B22 be used to choose:

```text
B23: g-population / MRT force insertion audit
B24: force split and F/rho closure matrix
B25: pressure closure derivation and evidence packet
```

## Claim Boundary

Allowed claims:

```text
B22 is an output-only velocity producer audit.
The first B22 smoke run exposed a TCLB source-regeneration problem.
The old B22 smoke metrics are invalid for physics.
```

Forbidden claims:

```text
contact-angle validation passed
static wetting is solved
curved-wall cylinder or sphere wetting is solved
dynamic impact is ready
B22 is a solver fix
pressure closure is physically validated
```
