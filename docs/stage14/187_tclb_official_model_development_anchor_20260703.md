# TCLB Official Model-Development Anchor

Date: 2026-07-03

## Purpose

This document fixes the TCLB official-development material into the LBMD3Q27 project so future AI agents and engineers do not continue patching the solver as if it were a plain C array code.

The immediate motivation is the current phase-field failure chain:

```text
wall/solid source-side h population
  -> TCLB AddDensity streaming
  -> calcPhaseF consumes streamed h
  -> PhaseFromH leaves [0,1] or becomes nonfinite
  -> rho(C), tau(C), F/rho, pressure and stress closure explode
```

This is a TCLB implementation-semantics problem until proven otherwise.

## Downloaded Official Material

Local anchor:

```text
C:\Users\yuanz\Desktop\lbm-new\repo\references\tclb_official_docs_20260703\
```

Contents:

- Official documentation source:
  - `references/tclb_official_docs_20260703/TCLB_docs/`
  - Public site: https://docs.tclb.io/
  - Source: https://github.com/CFD-GO/TCLB_docs

- Official TCLB source snapshot:
  - `references/tclb_official_docs_20260703/TCLB/`
  - Source: https://github.com/CFD-GO/TCLB
  - Commit recorded in `references/tclb_official_docs_20260703/TCLB_COMMIT.txt`

- Project index:
  - `references/tclb_official_docs_20260703/README_TCLB_OFFICIAL_DOCS.md`

## Official Semantics That Must Control Our Repairs

### 1. Dynamics.R Is The Model Contract

`Dynamics.R` declares what exists in the generated solver:

- `AddDensity`: streamed lattice populations loaded with offset semantics.
- `AddField`: non-streaming per-node fields, accessed explicitly and persisted only when saved.
- `AddSetting`: XML-configurable constants, optionally zonal.
- `AddQuantity`: output quantities, each backed by a `get*()` function in C/C++.
- `AddNodeType`: boundary/collision/object node classifications.
- `AddStage`: explicit load/save set for a callable device function.
- `AddAction`: ordered stage sequence such as `Init` and `Iteration`.

Any repair that ignores these declarations is not a reliable TCLB repair.

### 2. AddDensity Is Not A Plain Array

The official basics page states that `AddDensity` variables are loaded from fields with predefined offsets. The examples make the key point:

```text
f_100 == f_100(-1,0,0)
```

This means the local variable seen inside a node is already a streamed/offset value. For this project, the consequence is direct:

```text
h0..h26 cannot be reasoned about like C current-step h[i][x][y][z] arrays.
```

If a wall or solid node writes a bad `h_q`, that value may be consumed by a neighbor after TCLB streaming even if the receiving fluid node later applies a local correction. Therefore B115-style receiving-side repair is insufficient if source-side wall/solid populations remain active.

### 3. AddField Is Explicit Storage, Not Automatic Streaming

`AddField` values are accessed explicitly with offsets and must be saved by a stage. This is the correct category for replay diagnostics, wall/solid indicators, local scalar caches, and non-streaming reconstructed fields.

For this project:

- `Replay*`, `Psi*`, `PhaseFromH`, and wall ledger fields should be `AddField`/`AddQuantity`, not `AddDensity`.
- A field written in C code is not guaranteed to persist unless its stage saves it.
- A diagnostic quantity can be computed and output without proving that the solver used that same value in the next iteration.

### 4. Stages Define Persistence

Official TCLB model development uses:

```R
AddStage("BaseIteration", "Run", save=..., load=...)
AddAction("Iteration", c("BaseIteration", ...))
```

For the current solver, this is the first thing to audit before any new physical formula:

```text
which stage loads h?
which stage saves h?
where is calcPhaseF called?
where is wall/solid h modified?
does the modification occur before the save used by next streaming?
```

Adding a new pre/post stage may be correct, but it changes generated access layout and can make RT generation costly. Reusing an existing stage is acceptable only if its load/save set actually persists the intended fields.

### 5. Boundary And Collision Ordering Matters

Official examples place boundary work before collision/streaming in `Run()`. The current phase-field issue must therefore be audited in the actual order:

```text
load streamed g/h
  -> boundary/wall/solid branch
  -> phase reconstruction
  -> force/stress/pressure use
  -> h and g update
  -> stage save
  -> next TCLB streaming access
```

It is not enough to patch the formula for `WallGhost`; the producer-consumer path must show where `WallGhost` becomes a passive source value or a streamed `h` population.

## Required Review Checklist Before Editing Solver Physics

For any future modification under `third_party/tclb_snapshots/.../models/multiphase/d3q27_pf_velocity/`:

1. Identify every changed `AddDensity`, `AddField`, `AddSetting`, `AddQuantity`, `AddStage`, and `AddAction`.
2. Draw the producer-consumer timeline for affected variables.
3. State whether each variable streams or does not stream.
4. State which stage saves each modified field/population.
5. Verify that diagnostics are not used as proof of persisted state unless the save path is proven.
6. Regenerate TCLB sources after declaration changes.
7. Compile a distinct binary target and record its SHA256.
8. Run the smallest gate that can falsify the hypothesis.

## Current Priority After This Anchor

The next useful code audit is not another contact-angle run. It is:

```text
source-side wall/solid h population semantics
```

Specifically:

- inspect `Run()` and boundary functions for `IamWall || IamSolid` handling of `h0..h26`;
- identify whether wall/solid nodes emit active `h` populations through `AddDensity` streaming;
- if they do, design a passive wall/solid source-side reconstruction that is saved before the next streaming access;
- validate only `wall_t90_10` first, with no contact-angle claim.

## Skill Guardrail

A Codex skill was created at:

```text
C:\Users\yuanz\.codex\skills\tclb-model-development\
```

Future agents should invoke `$tclb-model-development` for any TCLB model/snapshot edit, especially edits to `Dynamics.R`, `Dynamics.c.Rt`, `Boundary.c.Rt`, stage declarations, density populations, wall/solid handling, or force/phase closure.
