# Stage18 Taichi Phase Mass Correction Long Gate Result

Date: 2026-07-04
Branch: `work/phasefield-c-reference-20260623`
Status: `bulk_phase_mass_correction_and_wall_perlink_long_gate_passed`

## Scope

This stage continued after the flat-wall neutral `h_i` per-link boundary was
fixed. The remaining failure was:

```text
P4 periodic bulk, surface force + Guo + phase advection, 100 steps:
  mass drift about 0.51

W5 flat wall, per-link h_i + surface force + Guo + phase advection, 100 steps:
  mass drift about 0.51
```

Since P4 has no wall, the residual failure is not the wall per-link boundary.
It is a bulk phase-equation boundedness/mass-conservation issue under nonzero
velocity and surface force.

## Code Changes

Main solver:

`tools/taichi_phasefield_clean_2026/phasefield_full_solver.py`

New `phase_bound_mode=2` path:

```text
mass_correction_clip_kernel
  clip C to [0,1]
  update h_i zeroth moment consistently
  accumulate clipped mass delta
  accumulate interface redistribution weight C(1-C)

mass_correction_redistribute_kernel
  redistribute clipped mass delta to fluid interface cells
  weights proportional to C(1-C)
  update h_i zeroth moment consistently
```

New diagnostics:

```text
mass_correction_delta
mass_correction_weight
mass_correction_count
```

This is a global mass-correction gate, not a final publishable conservative
Allen-Cahn derivation. It prevents local boundedness projection from silently
removing mass while preserving the explicit `h_i -> C` population lifecycle.

## Run Roots

Remote:

```text
/mnt/usb1t/RUNS/runs/stage18_taichi_pressure_wall_20260704_r7
/mnt/usb1t/RUNS/runs/stage18_taichi_pressure_wall_20260704_r8
```

Local artifacts:

```text
artifacts/stage18_taichi_pressure_wall_20260704_r7/
artifacts/stage18_taichi_pressure_wall_20260704_r8/
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

## Key Results

### Periodic bulk

| Case | Phase bound mode | Steps | Result |
|---|---:|---:|---|
| P4 surface + Guo + phase advection | 1 local clamp | 100 | fail, mass drift `0.50966016` |
| P5 surface + Guo + phase advection | 2 global correction | 100 | pass, mass drift `6.37e-12` |
| P6 surface + Guo + phase advection | 2 global correction | 1000 | pass, mass drift `6.34e-11` |

### Flat wall with neutral per-link `h_i`

| Case | Phase wall mode | Phase bound mode | Steps | Result |
|---|---:|---:|---:|---|
| W5 per-link wall + surface + Guo + phase advection | 2 | 1 | 100 | fail, mass drift `0.50721003` |
| W7 per-link wall + surface + Guo + phase advection | 2 | 2 | 100 | pass, mass drift `6.37e-12` |
| W8 per-link wall + surface + Guo + phase advection | 2 | 2 | 1000 | pass, mass drift `6.48e-11` |

Wall ledger:

```text
W7/W8 phase_wall_delta_mass = 0
```

Therefore the neutral flat-wall per-link `h_i` boundary remains mass closed
while the global phase mass-correction handles boundedness under coupled
surface-force advection.

## Interpretation

The work has separated three issues that were previously entangled:

1. `rho(C)` as the momentum distribution density caused no-force `g_i` blow-up.
   The pressure/velocity candidate removed that early failure.
2. Missing wall `h_i` incoming links caused order-one flat-wall mass loss.
   Per-link reflection fixed no-force wall mass conservation through 1000
   steps.
3. Local boundedness clamp caused order-one mass loss under surface force and
   phase advection in both bulk and wall cases.
   Global interface redistribution fixed the 1000-step mass drift to machine
   precision.

## Claim Limits

Allowed:

```text
pressure_velocity_candidate_bulk_gate_passed_at_ratio10
neutral_flat_wall_h_i_perlink_mass_gate_passed
phase_mass_correction_long_gate_passed_at_ratio10
```

Forbidden:

```text
contact angle validated
wetting angle solved
high-density-ratio solved
dynamic impact ready
final conservative Allen-Cahn model proven
```

## Next Work

The next stage should finally re-open wetting/contact-angle logic, but only
under these constraints:

```text
use phase_wall_mode=2
use phase_bound_mode=2
use pressure/velocity candidate momentum path
start with flat wall theta 90/30/150 morphology
do not enter sphere/cylinder until flat wall contact angle morphology is sane
```

Before contact-angle claims, add morphology plots and angle extraction for:

```text
flat wall 90 neutral
flat wall target 30
flat wall target 150
decoupled 60 -> 30
decoupled 120 -> 150
```

