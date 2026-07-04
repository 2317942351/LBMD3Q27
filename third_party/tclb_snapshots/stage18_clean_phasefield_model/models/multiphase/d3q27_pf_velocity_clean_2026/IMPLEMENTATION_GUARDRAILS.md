# Implementation Guardrails

Date: 2026-07-03

These rules are mandatory for `d3q27_pf_velocity_clean_2026`.

## Hard Rules

1. Do not add a physics write without updating `MODEL_CONTRACT.md`.
2. Do not add or change `AddDensity`, `AddField`, `AddStage`, or `AddAction` without updating `TCLB_MAPPING.md`.
3. Do not use `PhaseF=-999` or any sentinel value as a physical stencil input.
4. Do not treat `h_i` or `g_i` as ordinary C arrays. They are streamed `AddDensity` populations.
5. Do not use wall/solid nodes as active phase-population reservoirs unless the wall source stage explicitly defines the passive source values.
6. Do not implement wetting by overwriting fluid `PhaseF` after phase collision.
7. Do not claim contact-angle validation if boundedness or mass correction is frequently active.
8. Do not use pseudo-potential or color-gradient wetting formulas as phase-field physics without derivation.
9. Do not enter dynamic impact before static phase, force, and wetting gates pass.
10. Do not enable curved-wall write paths through flat-wall diagnostic flags.

## Required Validation Families

The architecture must support these from the start:

1. Bulk phase advection and static droplet.
2. Flat wall static contact angle: 30, 90, 150 degrees.
3. Decoupled flat wall response: initialized angle different from target angle.
4. Cylinder static contact angle.
5. Sphere static contact angle.
6. Static droplet pressure jump and spurious velocity.
7. Mass/volume conservation.
8. Dynamic impact preflight.

The implementation does not need to run all gates on every edit, but the code architecture must not make any gate impossible or ambiguous.

## Diagnostics Policy

Two builds/modes are required:

```text
fast mode:
  only essential fields and quantities

audit mode:
  replay fields, per-link wall mass, force closure diagnostics
```

Audit fields must be `AddField`/`AddQuantity`, not streamed `AddDensity`, unless the field is deliberately part of the physical solver.

## Commit Policy

Each major physical closure must be separate:

- phase equation;
- wall/solid passive `h_i` source;
- gradient/laplace/mu wall reconstruction;
- pressure and force closure;
- flat wetting;
- curved wetting;
- dynamic impact.

No commit may mix wetting formula changes with pressure/force closure changes unless the report proves they are inseparable.
