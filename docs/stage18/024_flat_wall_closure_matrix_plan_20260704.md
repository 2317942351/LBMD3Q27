# Stage18 Flat-Wall Closure Matrix Plan

Date: 2026-07-04

This note records the next controlled gate for the Taichi clean phase-field
solver. It is not a contact-angle validation claim.

## Current Evidence

The reference-density bulk and Laplace gates are already usable enough to enter
flat-wall closure work. The first corrected flat-wall contact smoke used:

- `phase_equation_mode=2`
- `phase_source_scale_mode=3`
- `pressure_model=2`
- `momentum_density_mode=1`
- `velocity_density_mode=0`
- `phase_wall_mode=3`
- `wetting_mode=0`
- half-way wall surface at `y=0.5`
- automatic spherical-cap initial center from `init_contact_angle_deg`

The 300-step flat-wall smoke at ratio 10 gave:

| case | target | measured angle | interpretation |
|---|---:|---:|---|
| `theta90_init90_300` | 90 | 112.97 | stable, mass-neutral, but drifts hydrophobic |
| `theta150_init150_300` | 150 | 157.35 | direction broadly consistent in short run |
| `theta30_init30_300` | 30 | NaN | not resolved at `R=10,W=4`; cap height is smaller than interface width |

Therefore the next task is not cylinder/sphere or 30/150 tuning. The next task
is to isolate why neutral 90-degree morphology drifts.

## Producer-Consumer Timeline Under Test

```text
h_src -> phase_from_h -> C
  -> bounded mass correction
  -> rho/tau/pressure
  -> wetting ghost from C_wall and theta
  -> gradC/laplaceC/mu with solid-neighbor ghost reconstruction
  -> F_surf = mu gradC
  -> momentum macro with half force
  -> h collision with CAC source
  -> pull streaming and per-link neutral reflection
  -> C_from_h for next step
```

The matrix focuses on three suspected links:

1. `phase_advection_mode`: whether the phase population equilibrium consumes
   the velocity field.
2. `wetting_ghost_distance`: whether the ghost point should be half-link or
   full-link relative to the fluid wall node.
3. `wetting_ghost_sign`: whether the current wall-normal convention is
   reversed in the ghost reconstruction.

## Matrix

Run root:

`/mnt/usb1t/RUNS/runs/stage18_flat_wall_closure_matrix_20260704_r1`

Script:

`tools/taichi_phasefield_clean_2026/run_hm570_flat_wall_closure_matrix.sh`

Cases:

| case | theta | phase advection | ghost distance | ghost sign |
|---|---:|---:|---:|---:|
| `theta90_adv0_gd1_signm1` | 90 | 0 | 1.0 | -1 |
| `theta90_adv1_gd1_signm1` | 90 | 1 | 1.0 | -1 |
| `theta90_adv1_gd05_signm1` | 90 | 1 | 0.5 | -1 |
| `theta90_adv1_gd05_signp1` | 90 | 1 | 0.5 | +1 |
| `theta60_adv1_gd05_signm1` | 60 | 1 | 0.5 | -1 |
| `theta120_adv1_gd05_signm1` | 120 | 1 | 0.5 | -1 |

## Decision Rules

- If `phase_advection=1` improves theta90, reopen the phase-equilibrium
  advection closure before changing wetting physics.
- If `ghost_distance=0.5` improves theta90, keep the half-link ghost geometry.
- If `ghost_sign=+1` improves theta90, the wall-normal sign convention is
  currently reversed.
- If none improve theta90, add chemical-potential no-flux reconstruction before
  tuning any target angle.
- Do not use `theta30` at `R=10,W=4` as a decisive gate.

## Acceptance For This Diagnostic Gate

This gate passes only if it identifies the dominant failure branch. It does not
validate static contact angle. Required outputs are:

- per-case `metrics.json`
- per-case `step_metrics.csv`
- per-case `final_fields.npz`
- local morphology image and JSON
- summary CSV/JSON

## Result

Run root completed with `overall_rc=0`.

Local artifact:

`artifacts/stage18_flat_wall_closure_matrix_20260704_r1/`

Merged summary:

`artifacts/stage18_flat_wall_closure_matrix_20260704_r1/flat_wall_runtime_morphology_merged.csv`

Key results:

| case | measured angle | runtime status | interpretation |
|---|---:|---|---|
| `theta90_adv0_gd1_signm1` | 112.97 | stable, mass-neutral | baseline neutral wall drifts hydrophobic |
| `theta90_adv1_gd1_signm1` | 113.30 | stable, mass-neutral | phase advection does not repair neutral drift |
| `theta90_adv1_gd05_signm1` | 113.30 | stable, mass-neutral | half-link ghost distance does not repair neutral drift |
| `theta90_adv1_gd05_signp1` | 113.30 | stable, mass-neutral | ghost sign does not repair neutral drift |
| `theta60_adv1_gd05_signm1` | NaN | stable, mass-neutral | this grid/interface width does not resolve the 60-degree cap robustly |
| `theta120_adv1_gd05_signm1` | 137.02 | stable, mass-neutral | hydrophobic direction persists but overshoots |

All six cases had:

- `nonfinite_count = 0`
- `mass_correction_delta = 0`
- `phase_wall_delta_mass = 0`

The important negative result is that the 90-degree drift is insensitive to
`phase_advection_mode`, ghost distance, and ghost sign. This is expected for the
ghost terms at 90 degrees because `cos(90 deg) = 0`; the neutral case has no
contact-angle bias to tune.

## Updated Diagnosis

The dominant current branch is no longer the target-angle ghost formula. The
neutral wall itself is not a correct phase-field wall:

```text
neutral h_i reflection
  + near-wall grad/laplace/mu stencil
  + F_surf = mu gradC
  -> hydrophobic drift even for theta=90
```

The next implementation should focus on the neutral wall phase-field boundary:

1. add a wider near-wall band diagnostic, not only the `wall_field == 1` layer;
2. implement a `MuWallFluxMode` or equivalent neutral chemical-potential
   no-flux reconstruction;
3. audit whether the solid-neighbor `c_neighbor_or_center()` path should use
   `C_wall`, mirrored `C`, or a ghost value for theta 90;
4. only after neutral 90-degree morphology is stable should the code tune
   non-90 wetting.

Do not move to cylinder/sphere from this result.
