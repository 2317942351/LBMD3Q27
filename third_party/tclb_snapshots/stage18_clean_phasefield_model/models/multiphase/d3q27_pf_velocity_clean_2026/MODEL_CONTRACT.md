# TCLB Model Contract

Date: 2026-07-03

This file is the variable-level contract for `d3q27_pf_velocity_clean_2026`. Every future code change must update this document if it changes declarations, streaming behavior, or stage ownership.

## Variable Contract Table

| Variable | TCLB declaration | Streaming | Producer stage | Consumer stage | Saved by | Notes |
|---|---|---:|---|---|---|---|
| `g0..g26` | `AddDensity`, group `g` | yes | `MomentumCollision` / `Run` | next `MomentumCollision`, boundary update | momentum update stage saving group `g` | Momentum populations. Never use as ordinary C arrays outside staged timeline. |
| `h0..h26` | `AddDensity`, group `h` | yes | `PhaseCollision` and `WallPhasePopulationSource` | `PhaseFromH`, next `PhaseCollision` | phase update stage saving group `h` | Phase populations. Wall/solid source values must be passive and bounded before streaming. |
| `PhaseF` | `AddField`, group `PF` | no | `PhaseFromH` | `GradPhi`, `Mu`, `MomentumCollision`, output | `PhaseFromH` stage | Macroscopic order parameter. No sentinel values. |
| `PhaseFValid` | `AddField`, group `PFState` | no | `PhaseFromH` | diagnostics/gates | `PhaseFromH` stage | 1 when finite and inside configured tolerance. |
| `rho` or `RhoField` | `AddField`, group `Macro` | no | `MacroFromPhase` | momentum collision, output | `MacroFromPhase` stage | Derived from bounded `PhaseF`. |
| `U,V,W` | Prefer `AddField`, group `Macro`; legacy may use `AddDensity(dx=0)` only if justified | no intended streaming | `MomentumCollision` | phase advection, output, next collision | macro save stage | Must not be confused with streamed population variables. |
| `pnorm` / pressure field | `AddField`, group `Macro` | no | `MomentumCollision` | pressure force/output | macro save stage | Must define whether it is pressure, pstar, or normalized moment. |
| `gradPhiVal_x/y/z` | `AddField`, group `GradPhi` | no | `GradPhi` | `Mu`, force closure, wetting diagnostics | `GradPhi` stage | Must not consume solid sentinel values. |
| `lapPhi` | `AddField`, group `GradPhi` or `Mu` | no | `Mu` or stencil stage | `Mu`, diagnostics | stencil/mu stage | Required for audit if chemical potential is active. |
| `mu` | `AddField`, group `Mu` | no | `Mu` | force closure | `Mu` stage | Wall no-flux closure required for wetting. |
| `F_surf` | `AddField`, group `Force` | no | `ForceClosure` | momentum collision, diagnostics | `ForceClosure` stage | Physical force component. |
| `F_pressure` | `AddField`, group `Force` | no | `ForceClosure` | momentum collision, diagnostics | `ForceClosure` stage | Requires pressure derivation. |
| `F_mu` | `AddField`, group `Force` | no | `ForceClosure` | momentum collision, diagnostics | `ForceClosure` stage | Requires stress time-level derivation. |
| `F_total` | `AddField`, group `Force` | no | `ForceClosure` | momentum population update | `ForceClosure` or collision stage | Inject exactly once. |
| `SolidIndicator` | `AddField`, group `SolidGeom` | no | `GeometryBuild` | all wall/stencil stages | `GeometryBuild` | 0 fluid, 1 solid, diffuse values allowed in diffuse mode. |
| `SignedDistance` | `AddField`, group `SolidGeom` | no | `GeometryBuild` | wall phase, normals, diagnostics | `GeometryBuild` | Positive/negative sign must be documented. |
| `SolidNormalX/Y/Z` | `AddField`, group `SolidGeom` | no | `GeometryBuild` | wetting, wall h source | `GeometryBuild` | Analytic or diffuse-solid normal. |
| `WallPhase` | `AddField`, group `Wetting` | no | `WettingBoundary` | `WallPhasePopulationSource`, stencil reconstruction | `WettingBoundary` | Virtual order parameter. |
| `WallPhaseValid` | `AddField`, group `Wetting` | no | `WettingBoundary` | wall h source, diagnostics | `WettingBoundary` | Prevents invalid writes. |
| `WallLinkMask` | `AddField`, group `Wetting` | no | `WallLinkBuild` | wall h source | `WallLinkBuild` | Per-link mask can be encoded in compact fields if TCLB field count is a concern. |
| `WallHOutgoingMass` | `AddField`, group `Audit` | no | `WallPhasePopulationSource` | diagnostics | audit stage | Required for wall mass budget. |
| `WallHIncomingMass` | `AddField`, group `Audit` | no | `PhaseFromH` or wall source | diagnostics | audit stage | Required for wall mass budget. |
| `MassCorrectionApplied` | `AddField`, group `Audit` | no | bounded correction stage | diagnostics | audit stage | Cannot be used as hidden physical proof. |

## Required Setting Contract

| Setting | Purpose | Default policy |
|---|---|---|
| `PhaseEquationMode` | selects phase LBE equation | default `legacy_upstream` until clean mode is implemented and validated |
| `PhaseBoundednessMode` | conservative boundedness correction | default off or shadow; write requires derivation |
| `GeometryMode` | none/plane/cylinder/sphere/diffuse-solid | case explicit |
| `WettingModel` | geometric virtual phase or surface-free-energy | case explicit |
| `WettingWriteMode` | shadow/write gate for wall phase population | default shadow/off |
| `GradPhiMode` | bulk/wall reconstructed/diffuse-solid | case explicit |
| `MuWallFluxMode` | chemical potential wall no-flux closure | required for wetting write |
| `PressureClosureMode` | pressure moment/physical pressure/reference pressure | must be derived before write validation |
| `ForceClosureMode` | selected force decomposition | must match pressure closure |
| `ForceInsertionMode` | Guo/MRT equivalent forcing/inherited legacy | must prove no double half-force |
| `DiagnosticsLevel` | none/slim/audit | production runs must use slim or none |

## Declaration Rules

1. Only physical populations that must stream may use `AddDensity` with nonzero offsets.
2. Non-streaming macroscopic fields must be `AddField`.
3. `AddDensity(dx=0)` is allowed only with a documented reason; it is still governed by stage load/save semantics.
4. Any wall or solid phase state must be non-streaming. If a wall value is converted to `h_i`, that conversion must happen in a named wall source stage saved before streaming.
5. Diagnostic fields must never be used as hidden physics inputs unless promoted into the contract.
