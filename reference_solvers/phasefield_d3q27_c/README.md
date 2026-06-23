# Phase-Field D3Q27 C Reference Solver

Status: planned baseline scaffold.

This directory is the intended location for a minimal explicit-array C/C++
reference solver for the TCLB D3Q27 phase-field wetting route.

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

First implementation target:

```text
D3Q27 q ordering and weights
explicit f/g population arrays
explicit non-streaming phi/mu/gradPhi/lapPhi/force caches
flat wall
analytic cylinder signed distance
analytic sphere signed distance
VTK output
CSV diagnostics
```

## Required Stages

The first version should make time levels visible:

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

Every run should write:

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
GPU acceleration
MPI
STL geometry
dynamic impact
cylinder array detachment
```

Those are later gates after the flat/cylinder/sphere static wetting ladder is
closed.

