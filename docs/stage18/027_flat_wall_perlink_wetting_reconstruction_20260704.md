# Stage18 Flat-Wall Per-Link Wetting Reconstruction

Date: 2026-07-04
Branch: `work/phasefield-c-reference-20260623`
Status: `implementation_and_runtime_gate_in_progress`

## Purpose

This stage stops treating `wetting_ghost_distance/sign` as the main repair
knob.  The new repair is architectural:

```text
wall contact angle -> Cghost(theta)
                  -> near-wall grad/laplace/mu stencil
                  -> missing-link h_i per-link reconstruction
                  -> calibrated flat-wall morphology gate
```

The change targets flat wall only.  Cylinder/sphere remain blocked until flat
wall passes.

## Producer-Consumer Timeline

Taichi dataflow:

```text
initialize h/g/C
  -> phase_from_h
  -> rho/pressure
  -> wetting_kernel produces wall_c_ghost_field from dC/dn(theta)
  -> grad_laplace_mu_kernel consumes wall_c_ghost_field for solid neighbors
  -> force/momentum
  -> collide h/g
  -> pull stream h/g
  -> boundary_kernel applies phase_wall_mode=3 missing-link h_i repair
  -> phase_from_h for next step
```

Important storage roles:

```text
h, g: streamed double-buffer populations
C, mu, gradC, laplaceC, wall_c_ghost: non-streaming fields
phase_wall_*: diagnostics/ledger fields
```

## Code Changes

File:

```text
tools/taichi_phasefield_clean_2026/phasefield_full_solver.py
```

### 1. Near-wall stencil uses the owning wall-node ghost first

`c_neighbor_or_center(...)` now uses `wall_c_ghost_field[x,y,z]` when the
current node is the wall-adjacent fluid node and a stencil neighbor is solid.
This binds `gradC/laplaceC/mu` to the same `dC/dn(theta)` condition that later
drives the `h_i` boundary.

### 2. `phase_wall_mode=3` applies post-stream missing-link wetting repair

`stream_kernel(...)` remains a pull-streaming stage.  For missing links from
solid, it writes neutral reflected values first.

`boundary_kernel(...)` then applies wetting repair after all streamed values are
present:

```text
for each missing link q:
  pair_old = h_q + h_opp
  correction = w_q * (Cghost - Cfluid)
  h_q_new = clamp(h_q + correction, 0, pair_old)
  h_opp_new = pair_old - h_q_new
```

This keeps the local pair mass conserved while changing the directional phase
population moment seen by the wall.

### 3. New ledgers

New diagnostics:

```text
phase_wall_wetting_correction_abs
phase_wall_wetting_clamp_cells
```

These are written to `step_metrics.csv`, `metrics.json`, and `final_fields.npz`.

### 4. Flat-wall spherical-cap initialization sentinel bug fixed

The calibrated bbox analyzer and the intended flat-wall cap initialization use
the same convention:

```text
theta = acos((wall_y - cy) / R)
cy = wall_y - R * cos(theta)
```

This means a hydrophilic acute cap can legitimately have `cy < 0`.  The Python
side already resolved this value, but `initialize_fields_kernel(...)` still
treated negative `center_y` as a sentinel and replaced it with the box center.
That silently detached `theta60` droplets from the wall and produced false
acute-angle failures.

The Taichi kernel no longer reinterprets negative centers.  Center defaults are
resolved only in Python before kernel launch.

### 5. Flat-wall y direction is non-periodic

The early Taichi route inherited a fully periodic `wrap_index(...)` helper for
all directions.  That is wrong for flat-wall wetting: at the top gas boundary,
`y+1` wrapped to the bottom solid wall, so the top layer saw a fake missing-link
wall and received wetting reconstruction.  In the no-clip test this produced a
large neutral-wall correction even when `theta=90` and `Cghost=Cfluid`.

The flat-wall implementation now keeps x/z periodic but treats y out-of-domain
neighbors as neutral reflected/open-gradient values.  Missing-link wetting is
applied only when the non-wrapped y-neighbor is an actual solid node.

## Current Limitations

This is not yet a final wetting validation:

```text
1. The per-link correction is a conservative first implementation, not a final
   published formula for curved walls.
2. The flat-wall ghost formula still uses the geometric AC estimate
   dC/dn = -(4/W) cos(theta) C(1-C).
3. Acute angles need larger footprint than the earlier R=10, W=4 runs.
4. Cylinder/sphere SDF normals are intentionally not enabled in this stage.
```

## Runtime Gate

Remote run root:

```text
/mnt/usb1t/RUNS/runs/stage18_flat_wall_perlink_wetting_20260704_r1
```

GPU:

```text
CUDA_VISIBLE_DEVICES=1
```

Cases:

```text
theta90_init90_1000
theta60_init60_1000
theta120_init120_1000
```

Grid:

```text
96 x 48 x 96
R = 18
W = 4
density ratio = 10
```

Acceptance for this first implementation gate:

```text
nonfinite_count = 0
mass_correction_delta near 0
phase_wall_delta_mass near 0
calibrated bbox angle finite
morphology image consistent with angle
theta90 remains near neutral
theta60/theta120 move toward the correct acute/obtuse families
```

If this fails, the next repair should inspect the wall `h_i` moment ledger and
near-wall `mu` extrema before changing contact-angle parameters.

## 2026-07-04 Update: Initialization and 100-Step Medium Gate

Initialization-only gate:

```text
remote: /mnt/usb1t/RUNS/runs/stage18_flat_wall_init_geometry_20260704_r2
local:  artifacts/stage18_flat_wall_init_geometry_20260704_r2
grid:   72 x 40 x 72, R=14, W=4, steps=0
```

Primary calibrated bbox readings:

```text
theta60  -> 62.0 deg
theta90  -> 92.0 deg
theta120 -> 122.0 deg
```

This proves the initial spherical-cap geometry and the calibrated flat-wall
angle analyzer are now using the same convention.

100-step per-link medium gate:

```text
remote: /mnt/usb1t/RUNS/runs/stage18_flat_wall_perlink_medium_20260704_r7
local:  artifacts/stage18_flat_wall_perlink_medium_20260704_r7
grid:   72 x 40 x 72, R=14, W=4, steps=100
```

Primary calibrated bbox readings:

```text
theta60  -> 63.77 deg
theta90  -> 88.70 deg
theta120 -> 122.00 deg
```

Runtime stability:

```text
all cases rc=0
nonfinite_count=0
mass_correction_delta=0
phase_wall_delta_mass ~ 0
u_max ~ 1.1e-3 to 1.4e-3
```

Remaining issue:

```text
phase_wall_wetting_clamp_cells is still high, including theta90.
```

Therefore this is a real forward step for flat-wall morphology and measurement,
but it is not a final wetting validation.  The next checks must confirm whether
the clamp ledger is only a conservative pair-limiter artifact or whether it
drives long-time angle drift.

## 2026-07-04 Update: y-Nonperiodic Per-Link Gate

Run root:

```text
remote: /mnt/usb1t/RUNS/runs/stage18_flat_wall_perlink_medium_20260704_r10
local:  artifacts/stage18_flat_wall_perlink_medium_20260704_r10
grid:   72 x 40 x 72, R=14, W=4, steps=100
```

Primary calibrated bbox readings:

```text
theta60  -> 63.77 deg
theta90  -> 88.70 deg
theta120 -> 122.00 deg
```

Runtime/ledger evidence:

```text
theta90:  phase_wall_wetting_correction_abs = 1.6e-17, shadow clamp = 0
theta60:  phase_wall_wetting_correction_abs = 7.66, shadow clamp = 3183
theta120: phase_wall_wetting_correction_abs = 8.01, shadow clamp = 2935
all:      nonfinite_count = 0, mass_correction_delta = 0, phase_wall_delta_mass ~ 0
```

This identifies the previous huge neutral-wall correction as a y-periodic
boundary bug rather than a physical wetting response.  The main remaining
question is long-time robustness and whether the acute/obtuse shadow clamp
indicates a per-link moment distribution that needs further normalization.

Circle-fit morphology readings remain biased high on this grid:

```text
theta60  circle-fit ~94.5 deg
theta90  circle-fit ~120.2 deg
theta120 circle-fit ~143.5 deg
```

Per `docs/stage18/025_contact_angle_measurement_method_audit_20260704.md`, this
does not override the calibrated bbox result; it is a morphology warning to
recheck on a larger footprint before claiming final validation.

## 2026-07-04 Update: Larger-Footprint R=18 Gate

Run root:

```text
remote: /mnt/usb1t/RUNS/runs/stage18_flat_wall_perlink_large_20260704_r11
local:  artifacts/stage18_flat_wall_perlink_large_20260704_r11
grid:   96 x 52 x 96, R=18, W=4, steps=100
```

Primary calibrated bbox readings:

```text
theta60  -> 61.93 deg
theta90  -> 88.69 deg
theta120 -> 121.00 deg
```

Runtime/ledger evidence:

```text
theta90:  correction_abs = 3.2e-17, shadow clamp = 0
theta60:  correction_abs = 9.90, shadow clamp = 4400
theta120: correction_abs = 10.26, shadow clamp = 3673
all:      rc=0, nonfinite_count=0, mass_correction_delta=0, phase_wall_delta_mass ~ 0
```

This larger-footprint run supports the conclusion that the old acute-angle
failure was not a fundamental inability to represent theta60.  The next gate is
not cylinder/sphere yet; it should be flat-wall longer-time 300/1000 steps and
decoupled response, while tracking whether acute/obtuse shadow clamp causes
slow drift.
