# MCMP C++ Reference Bridge For The Phase-Field Route

Date: 2026-06-23

This document records how the three external MCMP pseudopotential C++ codes
should influence the next phase-field baseline. They are valuable as program
structure and validation scaffolding, not as phase-field physics.

External files reviewed:

```text
D:/20260620-ur-sorry-1000/MCMP_三维稳态液滴_OMP.cpp
D:/20260620-ur-sorry-1000/MCMP_三维虚拟密度接触角_OMP.cpp
D:/20260620-ur-sorry-1000/MCMP_三维几何接触角_OMP.cpp
```

The files are not copied into the repository by this baseline. Their provenance
and intended redistribution status are not part of this audit. Only structural
lessons are recorded here.

## What The C++ Codes Do Well

### 1. Explicit stage order

The mature C++ loop is readable and debuggable because each physical operation
is split into a separate function.

Observed MCMP order:

```text
compute_rho()
compute_pressure()
compute_interaction_force()
compute_velocity()
compute_C()
compute_S()
collide()
stream()
boundary()
outputvtk()
display_results()
```

The phase-field reference solver should be equally explicit:

```text
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
boundary()
diagnostics()
output_vtk()
```

The point is not to copy formulas. The point is to expose time levels.

### 2. Clear node taxonomy

The contact-angle C++ codes use a `pointsflag` concept:

```text
solid / ghost
boundary
fluid
```

The phase-field route needs a more explicit taxonomy:

```text
solid_interior
solid_ghost_passive
boundary_fluid
near_wall_fluid
bulk_fluid
contact_line_candidate
outer_domain_boundary
```

This is directly relevant to TCLB because a ghost node in a C array is passive,
while a TCLB wall/solid node can still affect the streamed density field unless
the stage and population semantics are audited.

### 3. Passive ghost as a programming pattern

The virtual-density C++ code computes solid-node ghost `psi` values from nearby
fluid `psi` values and clamps them to the current fluid range. The geometric
contact-angle code computes a wall virtual value from near-wall gradients and
the target angle.

For phase-field work, the transferable pattern is:

```text
fluid-side current field
-> boundary reconstruction
-> passive ghost value
-> ghost consumed only by near-wall stencils
```

The non-transferable part is the actual `psi` formula.

Phase-field replacement variables:

```text
phi
gradPhi
lapPhi
mu
wall normal
solid indicator
contact-angle residual
```

### 4. Bounceback source semantics

The C++ boundary function uses the boundary-fluid node's own outgoing opposite
population when the incoming link crosses a solid neighbor:

```text
fin[q] = fout[opp[q]]
```

This is an important semantic detail. A TCLB implementation that reads a ghost
node population is not equivalent unless proven per link.

This should become a C-to-TCLB comparison gate:

```text
incoming link q
opposite link opp(q)
source node
source time level
destination node
mass before/after boundary update
```

### 5. Diagnostics as first-class outputs

The C++ codes output VTK data and total mass. The phase-field baseline needs a
much richer diagnostic set, but the same principle applies: every run must
produce machine-readable diagnostics, not only images.

Minimum phase-field diagnostics:

```text
sum(phi) over fluid
sum(rho) over fluid
min/max phi
max|u|
max|mu|
max|gradPhi|
near_wall_phi_mass
solid_ghost_phi_mass
mu_no_flux_residual
solid-neighbor stencil count
contact-line angle mean/std
```

## What Must Not Be Transferred

Do not transfer these as phase-field physics:

```text
psi = sqrt(...)
Peng-Robinson EOS pressure closure
Shan-Chen interaction force
MCMP virtual-density contact-angle formula
MCMP geometric psi contact-angle formula
MCMP density-ratio parameter set
flat k-index wall ghost formula for curved surfaces
```

They are pseudopotential model ingredients. The TCLB target is a conservative
phase-field LBM with:

```text
phi
chemical potential mu
grad(phi)
laplacian(phi)
free-energy / surface-tension force
Allen-Cahn or Cahn-Hilliard style phase evolution
wetting boundary and mu no-flux closure
```

## How To Use The C++ Codes Correctly

### Step 1: Build a minimal phase-field C/C++ reference solver

Target location:

```text
reference_solvers/phasefield_d3q27_c/
```

Initial scope:

```text
D3Q27 velocity set
explicit arrays, no TCLB streaming
periodic bulk
flat wall
analytic cylinder signed distance
analytic sphere signed distance
phi, mu, gradPhi, lapPhi, force, mass diagnostics
VTK output
```

Recommended cell structure:

```text
phi
rho
mu
gradPhi[3]
force[3]
u[3]
f[27], f_tmp[27]
g[27], g_tmp[27]
flag
solid_indicator
wall_normal[3]
```

### Step 2: Establish scalar/stencil tests before LBM runs

Before collision/streaming:

```text
test D3Q27 weights and opposite links
test gradPhi on manufactured fields
test lapPhi on manufactured fields
test signed-distance normals for plane/cylinder/sphere
test contact-angle ghost reconstruction on synthetic tanh interfaces
test mu no-flux residual on flat wall
```

### Step 3: Build a benchmark ladder

Minimum order:

```text
1. no-wall planar interface
2. no-wall static droplet
3. Laplace law
4. flat wall theta 90
5. flat wall theta 60 / 120
6. flat wall theta 45 / 135
7. analytic cylinder static contact angle
8. analytic sphere static contact angle
9. two-droplet merge
10. bridge between cylinders
11. gas-driven detachment
12. dynamic impact only after all above pass
```

### Step 4: C-to-TCLB replay

The C++ reference is useful only if it enables short-step replay against TCLB:

```text
same initial phi
same geometry mask
same signed-distance convention
same D3Q27 q ordering
same opp[q]
same wall flag taxonomy
same stage order
same parameters
```

Compare:

```text
step 0: phi, gradPhi, lapPhi, mu
step 1: phi, mu, force, u
step 2: phi, mu, force, u
step 5: mass, max|u|, min/max phi
step 10: same
```

If the first 10 steps do not agree, no 1000-step morphology result should be
interpreted physically.

## Immediate Decision

The C++ codes do not require new simulation before the baseline is declared.
They require a new implementation artifact: a phase-field C/C++ reference
solver or, at minimum, a source-level TCLB semantics map that provides the same
time-level clarity.

The recommended next engineering branch is:

```text
work/phasefield-c-reference-20260623
```

