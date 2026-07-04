# Stage18 Clean Phase-Field TCLB Model

Date: 2026-07-03

This snapshot is the clean architecture baseline for rebuilding the D3Q27 phase-field wetting solver according to official TCLB model-development semantics.

Model directory:

```text
models/multiphase/d3q27_pf_velocity_clean_2026/
```

The directory was copied from:

```text
third_party/tclb_snapshots/upstream_base/models/multiphase/d3q27_pf_velocity/
```

It is not meant to inherit the Stage14/Stage17 patch stack. Stage14 and Stage17 remain evidence/history branches. Stage18 is the architecture branch that must reintroduce physics only when the TCLB variable and stage contracts are explicit.

## Current Implementation State

As of 2026-07-03 this snapshot is no longer only a copied upstream directory:

- `Dynamics.R` declares a clean streamed/non-streamed variable contract.
- `g_i` and `h_i` are the only physical streamed population groups.
- `PhaseF`, macro state, geometry, wetting state, gradients, chemical potential, forces, and audits are non-streaming `AddField` state.
- `Iteration` is split into explicit producer-consumer stages:

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

Important limitation:

```text
Stage18 C-stage functions are currently a clean scaffold with legacy-compatible internals in several places.
They establish ownership and TCLB stage order; they do not yet prove the final phase equation, force closure, or wetting write path.
```

## Required Documents

- `ARCHITECTURE.md`
  - complete mathematical model and solver responsibilities.
- `MATH_MODEL.md`
  - explicit formulas and invariants for `PhaseF`, `h_i`, `F_phi`, `rho(C)`, `mu`, `gradPhi`, force closure, and wetting BC.
- `MODEL_CONTRACT.md`
  - variable-by-variable TCLB declaration contract.
- `TCLB_MAPPING.md`
  - stage producer-consumer mapping.
- `IMPLEMENTATION_GUARDRAILS.md`
  - rules that future edits must satisfy.

## Scope

Stage18 is designed from the start to support:

- static flat-wall contact angle;
- static cylinder contact angle;
- static sphere contact angle;
- dynamic droplet impact on flat wall;
- dynamic droplet impact on cylinder/sphere after static gates pass;
- high-density-ratio phase-field simulations after boundedness and force closure gates pass.

This does not mean these are validated today. It means the architecture must not create a dead end for these targets.
