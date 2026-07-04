# Stage18 Clean Phase-Field TCLB Model Architecture

Date: 2026-07-03

## Purpose

Stage18 is a clean baseline for rebuilding the D3Q27 phase-field wetting solver according to official TCLB model-development semantics and the phase-field LBM literature anchors already added to this repository.

It is intentionally not a minimal smoke-test model. It is a full architecture baseline that must be capable of supporting:

- static flat wall contact angle;
- static cylinder contact angle;
- static sphere contact angle;
- later dynamic droplet impact on flat and curved solids.

Validation is not claimed. This is an architecture node.

## New Model Directory

```text
third_party/tclb_snapshots/stage18_clean_phasefield_model/
```

Model:

```text
third_party/tclb_snapshots/stage18_clean_phasefield_model/models/multiphase/d3q27_pf_velocity_clean_2026/
```

The directory was copied from upstream base:

```text
third_party/tclb_snapshots/upstream_base/models/multiphase/d3q27_pf_velocity/
```

Stage14 and Stage17 remain evidence/history lines. Stage18 is the clean architecture line.

## Architecture Documents

Inside the model directory:

- `ARCHITECTURE.md`
  - mathematical model, phase equation, force closure, wetting, geometry, dynamic readiness.
- `MATH_MODEL.md`
  - explicit formulas and invariants for `PhaseF`, `h_i`, `F_phi`, `rho(C)`, `mu`, `gradPhi`, force closure, and wetting BC.
- `MODEL_CONTRACT.md`
  - every important variable mapped to TCLB declaration type, streaming behavior, producer, consumer, and save stage.
- `TCLB_MAPPING.md`
  - intended `AddStage`/`AddAction` producer-consumer order.
- `IMPLEMENTATION_GUARDRAILS.md`
  - rules future code edits must obey.

## Implementation Update

The first clean baseline implementation now includes:

- rewritten `Dynamics.R` declarations following official TCLB semantics;
- `g_i/h_i` as the only physical streamed `AddDensity` population groups;
- `PhaseF`, macro state, geometry, wetting, gradient, `mu`, force, and audit state as `AddField`;
- explicit `Stage18_*` C device functions matching the clean action chain.

The implementation is still a scaffold in several physics internals:

- `Stage18_MomentumCollision` still calls legacy `CollisionMRT()`/`CollisionBGK()`;
- phase population update is not yet separated from momentum collision;
- final pressure closure and `F_mu` stress reconstruction remain to be derived;
- wall-source writes are disabled by default via `WettingWriteMode=0`.

This means Stage18 is now suitable as the code baseline for the rebuild, but it is not yet a validated solver.

## Main Architectural Decision

The current Stage14 pattern:

```text
BaseIter/Run -> calcPhase -> calcGrad -> calcWall
```

is not acceptable as the final clean architecture because wetting and wall state are produced after the phase population update that should consume them.

The Stage18 target stage order is:

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

This is the key correction: wall phase and passive wall/solid `h_i` source values must be explicit producers in the phase-population path, not late diagnostic fields.

## Literature And TCLB Sources

Physics sources:

- `docs/stage14/178_phasefield_lbm_book_ch3_ch7_code_audit_20260703.md`
- `docs/stage14/180_phasefield_lbm_book_full_solver_patch_audit_20260703.md`
- `docs/stage14/183_huang_liu_lbm_phase_wetting_context_anchor_20260703.md`
- `docs/stage14/184_he_li_wang_tong_lbm_theory_phase_wetting_anchor_20260703.md`

Implementation sources:

- `references/tclb_official_docs_20260703/README_TCLB_OFFICIAL_DOCS.md`
- `docs/stage14/187_tclb_official_model_development_anchor_20260703.md`
- local Codex skill: `C:\Users\yuanz\.codex\skills\tclb-model-development\`

## No Validation Claim

This stage creates the clean architecture and model directory. It does not yet prove:

- contact angle is correct;
- wall/solid phase source is implemented;
- force closure is fixed;
- dynamic impact is ready.

Those are downstream implementation and validation tasks under this architecture.
