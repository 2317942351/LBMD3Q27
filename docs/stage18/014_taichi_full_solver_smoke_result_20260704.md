# Stage18 Taichi Full Solver Smoke Result

Date: 2026-07-04
Branch: `work/phasefield-c-reference-20260623`
Status: `full_stack_skeleton_smoke`

## What Was Implemented

The Taichi route now has a full-stack first solver skeleton:

`tools/taichi_phasefield_clean_2026/phasefield_full_solver.py`

It includes:

- D3Q27 `h_i` phase populations;
- D3Q27 `g_i` momentum populations;
- `C`, `rho(C)`, `tau(C)`, pressure, velocity;
- `gradC`, `laplaceC`, `mu`;
- pressure/surface/`F_mu`/body/total force fields;
- flat-wall geometry, SDF, wall normal, target theta, wall ghost fields;
- phase and momentum boundary hooks;
- diagnostics for mass, bounds, velocity, force-over-rho, wall cells, and
  nonfinite count.

This follows the system plan in:

`docs/stage18/013_taichi_full_phasefield_solver_system_plan_20260704.md`

## P100 Run

Remote root:

`/mnt/usb1t/RUNS/runs/stage18_taichi_full_solver_20260704_r3`

Local evidence:

`artifacts/stage18_taichi_full_solver_20260704_r3/`

Environment:

```text
GPU: Tesla P100-PCIE-16GB, CUDA_VISIBLE_DEVICES=1
Taichi: 1.7.4
Python: 3.11.15
precision: f64
grid: 24 x 24 x 24
steps: 20
density ratio: 10
```

## Results

### periodic_droplet_ratio10_passive

Modes:

```text
force_mode=0
momentum_mode=0
phase_advection_mode=0
```

Result:

```text
status: pass
max_abs_mass_drift: 1.1368683772161603e-12
C final min/max: 3.9929749086410694e-07 / 0.9959226329896159
u_max: 0
force_over_rho_max: 0
nonfinite_count: 0
```

Interpretation:

The complete field allocation and kernel sequence can run on P100 and the
phase-population lifecycle remains mass-conservative when force, momentum
feedback, and phase advection are frozen.

### flat_wall_theta90_ratio10_shadow

Modes:

```text
force_mode=0
momentum_mode=0
phase_advection_mode=0
wetting_mode=0
phase_wall_mode=0
```

Result:

```text
status: fail
max_abs_mass_drift: 1.2395409091941474
C final min/max: 0 / 0.995922642348188
wall_cells: 576
nonfinite_count: 0
```

Interpretation:

The flat-wall geometry path runs without nonfinite values, but the current
solid/wall treatment still loses phase mass. This is the same class of issue
seen in TCLB: wall/solid streaming cannot be treated as a passive scalar patch.
The next wall repair must use per-link incoming/outgoing `h_i` mass accounting.

### periodic_droplet_ratio10_coupled

Modes:

```text
force_mode=1
momentum_mode=1
phase_advection_mode=1
```

Result:

```text
status: fail
max_abs_mass_drift: 310.22086745408865
u_max: 9830.675121004895
force_over_rho_max: 0.05
nonfinite_count: 0
```

Interpretation:

The coupled force/momentum path is executable but not stable. Instability
starts after the phase bound correction clamps cells to 0/1, then velocity and
phase advection amplify the morphology. This does not invalidate the full
skeleton; it identifies pressure/force/momentum closure as the next major
physics repair.

## Current Diagnosis

The full-stack-first strategy is working: instead of hiding in isolated modules,
the solver now exposes three system states:

```text
periodic passive phase skeleton: pass
flat wall shadow skeleton: mass loss at wall
coupled force/momentum skeleton: unstable
```

Therefore the next implementation should not return to tiny single-module
tests. It should keep the full solver and add two robust closure upgrades:

1. wall per-link `h_i` mass ledger and boundary reconstruction;
2. pressure/force/momentum closure mode with stable low-density handling.

## Claim Limit

This is not contact-angle validation and not high-density-ratio validation. It
is the first full Taichi multiphase phase-field skeleton that runs on P100 and
locates the next two system-level blockers.

