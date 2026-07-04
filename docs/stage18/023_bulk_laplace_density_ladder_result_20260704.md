# Stage18 Bulk Density Ladder and Laplace Pressure Gate Result

Date: 2026-07-04
Branch: `work/phasefield-c-reference-20260623`
Status: `bulk_reference_pressure_velocity_gate_passed`

## Scope

This stage implements and validates the bulk side of the complete Taichi
phase-field model before reopening wetting/contact-angle work.

It is not contact-angle validation.

Main files:

- `tools/taichi_phasefield_clean_2026/phasefield_full_solver.py`
- `tools/taichi_phasefield_clean_2026/run_hm570_full_phasefield_bulk_ladder.sh`
- `tools/taichi_phasefield_clean_2026/run_hm570_laplace_radius_gate.sh`
- `tools/taichi_phasefield_clean_2026/summarize_bulk_laplace.py`

## Code Changes

New metrics in `StepMetrics`:

```text
droplet_volume_radius
pressure_inside_mean
pressure_outside_mean
laplace_delta_p
sigma_theory = sqrt(kappa * beta) / 6
laplace_delta_p_target = 2 sigma / R
laplace_delta_p_relative_error
spurious_u_rms_interface
interface_cells
```

New setting:

```text
velocity_density_mode
```

Modes:

```text
0 reference density for velocity denominator
1 local rho(C)
2 max(rho(C), rho_force_floor)
```

The main validated branch in this report is:

```text
phase_equation_mode = 2
phase_source_scale_mode = 3
phase_mobility = M_lattice
pressure_model = 2
momentum_density_mode = 1
velocity_density_mode = 0
force_closure_mode = 1
force_insertion_mode = 1
phase_bound_mode = 2
```

## Bulk Density Ladder

Remote:

```text
server: yuan@192.168.1.16
GPU: P100, CUDA_VISIBLE_DEVICES=1
run root: /mnt/usb1t/RUNS/runs/stage18_full_phasefield_bulk_ladder_20260704_r1
```

Local artifact:

```text
artifacts/stage18_full_phasefield_bulk_ladder_20260704_r1/
```

Parameters:

```text
grid = 24^3
R = 6
W = 4
steps = 1000
rho_l = 1.0
rho_g = 0.1, 0.02, 0.005, 0.001
```

Results:

| case | density ratio | status | mass drift | mass correction delta | u_max | Laplace relative error |
|---|---:|---|---:|---:|---:|---:|
| `ratio0010_bulk_1000` | 10 | pass | `6.18e-11` | `0.0` | `7.86e-5` | `4.47e-2` |
| `ratio0050_bulk_1000` | 50 | pass | `6.18e-11` | `0.0` | `7.86e-5` | `4.47e-2` |
| `ratio0200_bulk_1000` | 200 | pass | `6.18e-11` | `0.0` | `7.86e-5` | `4.47e-2` |
| `ratio1000_bulk_1000` | 1000 | pass | `6.18e-11` | `0.0` | `7.86e-5` | `4.47e-2` |

Interpretation:

The reference-density pressure-velocity branch is stable through density ratio
1000. The identical velocity and Laplace values across density ratios are
expected for this branch because the momentum inertia is deliberately
reference-density based. This is a stable pressure-velocity phase-field branch,
not proof that a local-`rho(C)` inertia formulation is closed.

## Local-Rho Velocity Branch

Two short diagnostic runs were added:

```text
ratio1000_velocity_density_mode1_100
ratio1000_velocity_density_mode2_100
```

Both failed with:

```text
u = NaN
pressure = NaN
g_min/g_max = NaN
nonfinite_count = 428544
```

while:

```text
C remains bounded
mass_correction_delta = 0.0
mass drift remains near roundoff
```

Conclusion:

The local-rho velocity branch fails in the momentum/pressure population path,
not in the phase equation. It is a separate momentum-closure problem and must
not be hidden by moving to wetting claims.

## Laplace Radius Gate

Remote:

```text
GPU: P100, CUDA_VISIBLE_DEVICES=2
run root: /mnt/usb1t/RUNS/runs/stage18_full_phasefield_laplace_radius_20260704_r2
```

Local artifact:

```text
artifacts/stage18_full_phasefield_laplace_radius_20260704_r2/
```

Parameters:

```text
grid = 32^3
rho_l/rho_g = 1.0 / 0.1
R = 5, 6, 7
W = 4
steps = 3000
```

Results:

| case | volume radius | delta_p | target | relative error | u_max | mass correction delta |
|---|---:|---:|---:|---:|---:|---:|
| `radius5_ratio10_3000` | `5.5869` | `6.469e-4` | `5.966e-4` | `8.43e-2` | `1.22e-4` | `0.0` |
| `radius6_ratio10_3000` | `6.5047` | `5.358e-4` | `5.124e-4` | `4.55e-2` | `9.15e-5` | `0.0` |
| `radius7_ratio10_3000` | `7.4415` | `4.537e-4` | `4.479e-4` | `1.28e-2` | `5.90e-5` | `0.0` |

Fitted slope:

```text
delta_p = 0.00351448 / R
sigma_fit = 0.00175724
sigma_theory = sqrt(0.01 * 0.01) / 6 = 0.00166667
```

This satisfies the current Laplace gate: pressure jump sign and inverse-radius
trend are correct, errors are below 30%, and mass correction is not being used
to hide phase instability.

## Current Verdict

Passed:

```text
bulk density ladder up to ratio 1000, reference-density pressure-velocity branch
Laplace pressure radius trend at ratio 10
spurious velocity below 1e-3 in Laplace cases
phase mass correction delta = 0 in accepted gates
```

Not passed:

```text
local rho(C) velocity/inertia branch
flat wall wetting
cylinder/sphere wetting
dynamic impact
```

Next work:

Proceed to flat-wall wetting only on the validated reference-density branch.
Keep the local-rho branch as an explicit unresolved momentum-closure line.
