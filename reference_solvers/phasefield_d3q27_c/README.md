# Phase-Field D3Q27 C Reference Solver

Status: executable baseline scaffold with formula/operator self-tests.

This directory contains the first minimal explicit-array C++ reference scaffold
for the TCLB D3Q27 phase-field wetting route.

The purpose is not performance. The purpose is time-level clarity and
C-to-TCLB replay.

## Why This Exists

The mature MCMP pseudopotential C++ codes supplied outside this repository are
useful because they expose:

```text
stage order
flag taxonomy
passive ghost handling
boundary-fluid bounceback source semantics
diagnostic output
benchmark sequence
```

They should not be copied as phase-field physics. This reference solver must
implement phase-field variables directly:

```text
phi
mu
gradPhi
lapPhi
surface-tension force
phase evolution
wetting ghost / boundary gradient
mu no-flux
```

## Minimum Scope

Implemented first scope:

```text
D3Q27 q ordering and weights
opposite-link table
explicit scalar field storage
solid sentinel separated from passive wall ghost
isotropic gradient manufactured-field test
isotropic Laplace manufactured-field test
flat wall signed distance
analytic cylinder signed distance and normal
analytic sphere signed distance and normal
geometric wall ghost sign checks for theta 30/90/150
TCLB calcMu formula check against planar tanh equilibrium
surface-force residual check
Allen-Cahn source moment check
VTK demo output
CSV self-test diagnostics
```

Run:

```text
make test
```

Verified on `yuan@192.168.1.16` with `/usr/bin/g++`:

```text
checks=108 failures=0
```

The formula-level diagnostics are written to:

```text
math_validation_diagnostics.csv
```

Representative 2026-06-23 values:

```text
planar_mu_exact_laplace_max_abs = 4.06e-16
planar_mu_discrete_max_abs      = 5.72e-02
planar_surface_force_max_abs    = 1.09e-02
allen_cahn_first_moment_error   = 7.76e-18
```

Interpretation: the continuous tanh profile closes the current TCLB chemical
potential formula to roundoff, while the finite D3Q27 stencil has a measurable
but bounded residual at `IntWidth=4`.

## Required Stages

The production reference solver still needs to grow toward this full stage list:

```text
initialize_geometry()
initialize_phi()
initialize_populations()
compute_phi()
compute_grad_phi()
apply_phi_wetting_ghost()
compute_lap_phi()
compute_mu()
apply_mu_no_flux()
compute_surface_force()
compute_velocity()
collide_phase()
stream_phase()
collide_flow()
stream_flow()
apply_boundary()
diagnostics()
write_vtk()
```

## Required Diagnostics

The current self-test writes:

```text
selftest_diagnostics.csv
math_validation_diagnostics.csv
selftest_fields.vtk
```

The later time-marching reference should write:

```text
step
sum_phi_fluid
sum_rho_fluid
min_phi
max_phi
max_abs_u
max_abs_mu
max_abs_grad_phi
near_wall_phi_mass
solid_ghost_phi_mass
mu_no_flux_residual
contact_angle_mean
contact_angle_std
nonfinite_count
```

## Non-Goals

Not in the first version:

```text
high density ratio production tuning
full LBM collide/stream loop
full Allen-Cahn or Cahn-Hilliard update
GPU acceleration
MPI
STL geometry
dynamic impact
cylinder array detachment
```

Those are later gates after the flat/cylinder/sphere static wetting ladder is
closed.
