# Stage18 Clean Baseline Implementation Audit

Date: 2026-07-03

## Purpose

The user requested a clean TCLB model baseline instead of continuing to stack patches on the old Stage14/Stage17 solver. This audit records what has been implemented and what remains unresolved.

## Files Changed

Model root:

```text
third_party/tclb_snapshots/stage18_clean_phasefield_model/
```

Key files:

```text
models/multiphase/d3q27_pf_velocity_clean_2026/Dynamics.R
models/multiphase/d3q27_pf_velocity_clean_2026/Dynamics.c.Rt
models/multiphase/d3q27_pf_velocity_clean_2026/conf.mk
models/multiphase/d3q27_pf_velocity_clean_2026/MATH_MODEL.md
models/multiphase/d3q27_pf_velocity_clean_2026/MODEL_CONTRACT.md
models/multiphase/d3q27_pf_velocity_clean_2026/TCLB_MAPPING.md
```

## What Was Fixed At Architecture Level

### 1. Streamed and non-streamed variables are now separated

The old copied model used many zero-offset `AddDensity` variables for non-population state, including velocity and wall normals. That makes reasoning fragile because `AddDensity` is governed by TCLB density load/save and streaming semantics.

Stage18 now keeps:

```text
g_i, h_i -> AddDensity, streamed populations
PhaseF, U/V/W, RhoField, geometry, wetting, gradPhi, mu, forces, diagnostics -> AddField
```

This directly addresses the long-running suspicion that the solver was mixing C-array thinking with TCLB streamed density semantics.

### 2. The action order is now explicit

The old Stage14/Stage17 order was effectively:

```text
Run -> calcPhase -> calcGrad -> calcWall
```

That is structurally wrong for a wetting phase-population solver because wall state is produced after the population update that should consume it.

Stage18 declares:

```text
GeometryBuild
  -> PhaseFromH
  -> GradPhi
  -> Mu
  -> WettingBoundary
  -> WallPhasePopulationSource
  -> ForceClosure
  -> MomentumCollision
  -> PhaseCollision
  -> ConservativeBoundednessCorrection
  -> AuditSlim
```

This makes the producer-consumer path auditable:

```text
h_i -> PhaseF -> grad/mu/wetting/force -> wall h source + collision -> next TCLB streaming
```

### 3. Geometry and wetting no longer rely on `PhaseF=-999` by contract

The new contract uses:

```text
SolidIndicator
SignedDistance
SolidNormalX/Y/Z
NearWallBand
WallPhase
WallPhaseValid
WallLinkMask
```

These are non-streaming fields. The old sentinel route is explicitly disallowed in `MATH_MODEL.md` and `IMPLEMENTATION_GUARDRAILS.md`.

The Stage18 C template has also removed the inherited initialization writes that set wall/solid `PhaseF=-999`. Wall/solid phase is now initialized inside the physical phase interval, and wetting information is represented by `WallPhase` plus the passive wall-source path.

Important caveat:

```text
Boundary.c.Rt still contains inherited sentinel-oriented helper code.
The clean Stage18 action does not call the old calcWallPhase/Init_wallNorm path, but later cleanup should delete or quarantine these helpers after source generation confirms they are unreachable.
```

### 4. Compile matrix no longer exposes old geometric branches

`conf.mk` now uses:

```text
OPT="q27*autosym"
```

The old `thermo/geometric/staircaseimp/isograd/tprec` matrix is intentionally not exposed in the first clean baseline. Curved wetting will be reintroduced through Stage18 settings and explicit stage functions, not inherited compile-time branches.

## Current Code-Level State

`Dynamics.c.Rt` now contains matching `Stage18_*` functions:

```text
Stage18_InitPhaseField
Stage18_GeometryBuild
Stage18_PhaseFromH
Stage18_GradPhi
Stage18_Mu
Stage18_WettingBoundary
Stage18_WallPhasePopulationSource
Stage18_ForceClosure
Stage18_MomentumCollision
Stage18_PhaseCollision
Stage18_ConservativeBoundednessCorrection
Stage18_AuditSlim
```

These functions make TCLB stage ownership explicit. `Stage18_MomentumCollision` and `Stage18_PhaseCollision` are now split: the clean action no longer calls inherited `CollisionMRT()` to update both `g_i` and `h_i` together.

## Remaining Critical Issues

### C1. Momentum and phase collision have been split, but source generation/compile is still required

`Stage18_MomentumCollision` now performs a momentum-only MRT update and saves group `g`. `Stage18_PhaseCollision` performs the phase-only `h_i` update and saves group `h`.

This removes the highest-risk TCLB stage ambiguity:

```text
old: ForceClosure -> CollisionMRT() updates g and h together
new: ForceClosure -> MomentumCollision(g only) -> PhaseCollision(h only)
```

The split still needs source generation and compile validation. It is not yet a numerical validation result.

Current MRT policy:

```text
MomentumMRTMode=1
  all 27 g_i moments are transformed and reconstructed
  shear omega = 1/tau or MRTShearOmegaOverride
  conserved momentum modes follow the force-update convention
  bulk/high-order omega = MRTBulkOmega
  omega values clamped to [MRTMinOmega, MRTMaxOmega]
```

This is a conservative robust full-moment MRT spectrum, not a non-diagonal phase MRT.

### C2. Wall phase population source is not complete

`Stage18_WallPhasePopulationSource` is disabled by default through:

```text
WettingWriteMode = 0
```

This is intentional. The next implementation must convert `WallPhase` into passive per-link `h_i` source values with wall mass audit. It must not collide wall nodes as fluid and must not overwrite fluid `PhaseF` late.

At this stage the old `Boundary.c.Rt` helper code remains present only because the template still includes inherited boundary updates. It must not be treated as the Stage18 wetting implementation.

### C3. Pressure and `F_mu` closures remain legacy-compatible

`Stage18_ForceClosure` stores explicit force fields, but the final pressure closure and stress reconstruction are not yet derived. The inherited code path still uses the legacy pressure/stress ideas unless split and replaced.

Required repair:

```text
derive pressure variable consumed by F_pressure
derive F_mu stress time level
prove force insertion exactly once
```

### C4. Source generation and compile have not yet been run

This work was a local code/document baseline. It still needs official TCLB source regeneration and a compile smoke on the P100 lane before it can be used for numerical tests.

## Meaning Of This Baseline

This is a real step forward because it stops the old patch stack and creates a model directory where:

- the mathematical model is written down;
- TCLB variable ownership is explicit;
- stage order is explicit;
- old high-risk compile-time geometry branches are not enabled;
- future fixes have a clean place to land.

It is not yet evidence that contact angle is correct.

## Next Required Work

Stage18-B1:

```text
run TCLB source generation for d3q27_pf_velocity_clean_2026
fix declaration/template errors
compile q27 autosym target
do not run contact-angle cases
```

Stage18-B2:

```text
source-generate and compile the split collision path
prove PhaseFromH -> PhaseCollision -> next PhaseFromH boundedness in a bulk/static droplet smoke
```

Stage18-B3:

```text
implement passive wall/solid h_i source with WettingWriteMode guarded
run flat t90 boundedness/morphology smoke
```

Only after these should flat 30/150 and decoupled contact-angle validation resume.
