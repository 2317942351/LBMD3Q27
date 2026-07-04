# Stage18 Taichi Pressure/Velocity And Wall Per-Link Gate Result

Date: 2026-07-04
Branch: `work/phasefield-c-reference-20260623`
Status: `bulk_pressure_velocity_candidate_and_neutral_wall_h_perlink_passed`

## Scope

This stage continued from the F1/F8/F9 result:

```text
F1 rho(C)-based momentum distribution failed with no force.
F8 constant reference momentum density passed with no force.
F9 constant reference momentum density plus F_surf/Guo passed without phase advection.
```

The work implemented two repairs:

1. promote the constant reference momentum density path into the current
   pressure/velocity candidate gate;
2. repair flat-wall `h_i` mass loss with a per-link missing-population boundary.

This is still not contact-angle validation and not a final high-density-ratio
model.

## Code Changes

Main solver:

`tools/taichi_phasefield_clean_2026/phasefield_full_solver.py`

Runner:

`tools/taichi_phasefield_clean_2026/run_hm570_pressure_velocity_wall_gates.sh`

Key implementation points:

- `stream_kernel()` now detects incoming links whose pull source is solid.
- For `phase_wall_mode=2`, missing incoming `h_i` populations are reconstructed
  from the same fluid cell's opposite post-collision population:

```text
h_in(q from solid) = h_post(opp(q)) at the fluid cell
```

- The boundary stage records per-link ledgers instead of writing the phase
  again:

```text
phase_wall_missing_links
phase_wall_stream_mass_before
phase_wall_reflect_mass
phase_wall_delta_mass
```

- `grad_laplace_mu_kernel()` uses a no-flux center substitute for solid
  neighbors so solid `C=0` is not directly read by the near-wall stencil.

- `collide_phase_kernel()` removes wall-normal advection velocity at flat wall
  cells when `phase_wall_mode=2`. This did not solve the long advective drift,
  but keeps the near-wall velocity semantics explicit.

## Run Roots

Remote:

```text
/mnt/usb1t/RUNS/runs/stage18_taichi_pressure_wall_20260704_r1
/mnt/usb1t/RUNS/runs/stage18_taichi_pressure_wall_20260704_r2
/mnt/usb1t/RUNS/runs/stage18_taichi_pressure_wall_20260704_r3
/mnt/usb1t/RUNS/runs/stage18_taichi_pressure_wall_20260704_r4
/mnt/usb1t/RUNS/runs/stage18_taichi_pressure_wall_20260704_r5
/mnt/usb1t/RUNS/runs/stage18_taichi_pressure_wall_20260704_r6
```

Local artifacts:

```text
artifacts/stage18_taichi_pressure_wall_20260704_r1/
artifacts/stage18_taichi_pressure_wall_20260704_r2/
artifacts/stage18_taichi_pressure_wall_20260704_r3/
artifacts/stage18_taichi_pressure_wall_20260704_r4/
artifacts/stage18_taichi_pressure_wall_20260704_r5/
artifacts/stage18_taichi_pressure_wall_20260704_r6/
```

Environment:

```text
server: yuan@192.168.1.16
GPU: Tesla P100-PCIE-16GB, CUDA_VISIBLE_DEVICES=1
Taichi: 1.7.4
Python: 3.11.15
NumPy: 1.26.4
precision: f64
fast_math: false
grid: 24x24x24
density ratio: 10
```

## Final Gate Results From r6

### Bulk pressure/velocity candidate

| Case | Description | Result |
|---|---|---|
| P1 | no force, no phase advection, 20 steps | pass, mass drift `1.14e-12` |
| P2 | surface force + Guo, no phase advection, 20 steps | pass, mass drift `1.14e-12`, `u_max=0.00152` |
| P3 | surface force + Guo + phase advection, 20 steps | pass, mass drift `1.14e-12`, `Cmax=0.998822` |
| P4 | surface force + Guo + phase advection, 100 steps | fail, mass drift `0.50966`, `Cmax=1` |

Interpretation:

The pressure/velocity candidate removes the immediate `g_i` blow-up seen in
the old `rho(C)` momentum path. The remaining 100-step failure is not wall
specific; it also happens in periodic bulk flow.

### Flat-wall per-link `h_i` boundary

| Case | Description | Result |
|---|---|---|
| W1 | no per-link phase wall boundary, 20 steps | fail, mass drift `1.27` |
| W2 | per-link neutral wall, no force, 20 steps | pass, mass drift `1.36e-12` |
| W3 | per-link neutral wall + surface force, no phase advection, 20 steps | pass, mass drift `1.36e-12` |
| W4 | per-link neutral wall, no force, 100 steps | pass, mass drift `6.37e-12` |
| W5 | per-link neutral wall + surface force + phase advection, 100 steps | fail, mass drift `0.50721`, `Cmax=1` |
| W6 | per-link neutral wall, no force, 1000 steps | pass, mass drift `6.39e-11` |

Important wall result:

```text
W2/W3/W4/W6 all have phase_wall_delta_mass = 0.
```

The neutral flat-wall `h_i` per-link missing-population boundary is therefore
fixed for no-force and no-phase-advection gates. It changes wall mass loss from
order-one drift to machine precision.

## Remaining Failure Is Not The Wall Ledger

W5 and P4 fail in the same way:

```text
surface force + Guo + phase advection, 100 steps
C reaches 1
boundedness correction removes about 0.5 total mass
```

Since P4 has no wall, this is a bulk conservative Allen-Cahn / boundedness /
source-strength issue, not a wall per-link mass boundary issue.

The next target must therefore be:

```text
conservative phase equation under nonzero velocity and surface force
```

not another wall `h_i` patch.

## Next Required Work

Implement a literature-derived phase boundedness/source correction gate:

```text
PhaseEquationMode:
  legacy current F_phi
  conservative normalized source
  bounded but mass-conservative redistribution candidate
```

Minimum gates:

```text
P4 repeat to 100 steps without order-one mass loss.
W5 repeat to 100 steps without order-one mass loss.
Then ratio 50/200.
```

Only after P4/W5 pass should wetting contact angle writes or geometric wall
ghosts be reintroduced.

