# TCLB Stage Mapping

Date: 2026-07-03

This is the stage architecture for `d3q27_pf_velocity_clean_2026`.

Current status on 2026-07-03:

- `Dynamics.R` implements this stage/action skeleton.
- `Dynamics.c.Rt` contains matching `Stage18_*` device functions.
- `Stage18_MomentumCollision` and `Stage18_PhaseCollision` are split. The clean action no longer calls legacy `CollisionMRT()`.
- Several closure details are still legacy-compatible or conservative internally. They establish TCLB ownership and order; they are not final physical validation.
- Contact-angle validation is not claimed from this mapping.

## Required Actions

### Init action

```text
InitFields
  -> GeometryBuild
  -> InitPhaseField
  -> InitMacro
  -> WettingBoundary
  -> WallPhasePopulationSource
  -> InitDistributions
  -> PhaseFromH
```

Purpose:

- build geometry and normals before wall phase is needed;
- initialize `PhaseF` and macro fields;
- initialize wall passive `h_i` consistently with wetting;
- initialize `g_i/h_i`;
- verify that `PhaseFromH` equals initialized `PhaseF`.

### Iteration action

```text
GeometryRefreshIfMoving
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

Important ordering decisions:

- `PhaseFromH` happens before force and phase collision.
- `WettingBoundary` happens before `WallPhasePopulationSource`.
- `WallPhasePopulationSource` runs before the next streaming access and is saved with group `h`.
- `PhaseCollision` uses the current `PhaseF`, `gradPhi`, `mu`, `F_total`, and selected advection velocity.
- `ConservativeBoundednessCorrection` may only apply derived conservative correction; it must not hide failed physics.

## Stage Load/Save Contract

| Stage | Loads | Saves | Must not do |
|---|---|---|---|
| `GeometryBuild` | settings, coordinates | `SolidGeom` | read `PhaseF` for normal inference |
| `PhaseFromH` | group `h`, `SolidGeom`, optional `WallLinkMask` | `PF`, `PFState`, slim audit | collide or write wall physics |
| `GradPhi` | `PF`, `SolidGeom`, `Wetting` | `GradPhi` | read solid sentinels as phase |
| `Mu` | `PF`, `GradPhi`, `SolidGeom`, `Wetting` | `Mu` | impose wetting by direct `PhaseF` overwrite |
| `WettingBoundary` | `PF`, `GradPhi`, `SolidGeom`, settings | `Wetting` | write `h_i` or `PhaseF` directly |
| `WallPhasePopulationSource` | `Wetting`, `SolidGeom`, group `h` if preserving non-equilibrium | group `h`, wall mass audit | collide wall nodes as fluid |
| `ForceClosure` | `PF`, `GradPhi`, `Mu`, macro pressure/momentum | `Force` | modify `g_i/h_i` |
| `MomentumCollision` | group `g`, `PF`, `Force`, macro | group `g`, macro | recompute wall phase |
| `PhaseCollision` | group `h`, `PF`, `GradPhi`, macro velocity, `Force` if coupled | group `h` | use stale `WallGhost` |
| `ConservativeBoundednessCorrection` | `PF`, group `h`, audit | group `h`, `Audit` | hard clamp without mass ledger |
| `AuditSlim` | contracted outputs | `Audit`/quantities | change physics |

## Producer-Consumer Paths

### Phase path

```text
h_i streamed by TCLB
  -> PhaseFromH
  -> PhaseF
  -> GradPhi/Mu/Wetting/Force/PhaseCollision
  -> PhaseCollision writes h_i
  -> WallPhasePopulationSource replaces passive wall/solid source h_i
  -> next TCLB streaming
```

### Wetting path

```text
GeometryBuild
  -> SolidNormal/SignedDistance
  -> WettingBoundary computes WallPhase from theta
  -> WallPhasePopulationSource maps WallPhase to passive per-link h_i
  -> PhaseFromH consumes streamed h_i at fluid nodes
```

### Force path

```text
PhaseF + GradPhi + Mu + pressure representation
  -> ForceClosure computes F_total
  -> MomentumCollision reads F_total
  -> one and only one force insertion scheme updates g_i
  -> macro velocity saved for phase advection and output
```

## Why This Differs From Current Stage14

Current Stage14 order is effectively:

```text
BaseIter/Run
  -> calcPhase
  -> calcGrad
  -> calcWall
```

That lets `Run()` update phase populations before current wetting state is produced. Stage18 moves wetting and wall phase population source into an explicit producer-consumer path instead of relying on a later wall-field correction.

## Current Scaffold Caveats

The Stage18 implementation keeps some inherited formulas only as temporary compatibility:

- `Stage18_MomentumCollision` is a momentum-only full-27-moment MRT update and saves group `g`.
- `Stage18_PhaseCollision` is a phase-only `h_i` update and saves group `h`.
- `Stage18_WallPhasePopulationSource` has write mode disabled by default through `WettingWriteMode=0`.
- `Stage18_ForceClosure` stores force fields, but the final pressure/F_mu derivation is not yet complete. `F_mu` remains disabled by default unless promoted by a derived mode.
- `MomentumMRTMode=1` uses a bounded full-moment relaxation spectrum for robustness. This is not the same as a non-diagonal phase MRT.

The next implementation step must source-generate and compile this split path, then run a small boundedness smoke before any contact-angle validation.
