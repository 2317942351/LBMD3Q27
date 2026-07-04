# Stage18 Contact-Angle LBM Manual Code Audit

Date: 2026-07-04
Branch: `work/phasefield-c-reference-20260623`
Status: `reference_anchor_and_code_audit`

## Reference

Local manual:

```text
C:/Users/yuanz/Downloads/接触角LBM实现方法参考手册.md
SHA256: 2DE13B390E4BCA2351C6804D7BD87612122D83C115127B2BE7E5763D5E2BB1A5
```

Repository metadata:

```text
references/contact_angle_lbm_manual_20260704/metadata.json
```

The full manual text is not copied into the repository.  This document records
the project-specific implications and code mapping.

## Main conclusion for Stage18

The manual supports the current decision to keep Stage18 on a phase-field
wetting route, but it also narrows what is allowed:

```text
Allowed for current model:
  - phase-field surface-free-energy boundary
  - phase-field geometric virtual-order-parameter boundary
  - near-wall gradient / Laplace reconstruction tied to the chosen boundary

Not allowed as direct physics in current model:
  - Shan-Chen wall pseudo-density force
  - MCMP Shan-Chen wall adhesion force
  - color-gradient virtual-density formulas
```

Those other methods are useful for comparison and validation workflow, but they
must not be mixed into the conservative Allen-Cahn `h_i` solver.

## Manual-to-code mapping

Current code:

```text
tools/taichi_phasefield_clean_2026/phasefield_full_solver.py
```

### Young equation and validation meaning

Manual section:

```text
Young equation: cos(theta) = (gamma_SG - gamma_SL) / gamma_LG
```

Current project implication:

```text
Contact angle is an equilibrium surface-energy result.  A short morphology
picture or one angle estimator is not enough.  It must be paired with mass,
velocity/spurious-current and calibrated angle diagnostics.
```

This is now enforced by:

```text
docs/stage18/025_contact_angle_measurement_method_audit_20260704.md
tools/taichi_phasefield_clean_2026/analyze_flat_wall_calibrated_angle.py
```

### Shan-Chen / color-gradient sections

Manual sections:

```text
SCMP/MCMP: wall virtual density or wall adhesion force.
Color-gradient: virtual density or corrected color-gradient normal.
```

Current code decision:

```text
Do not implement these as Stage18 physics.
```

Reason:

```text
Stage18 is a conservative Allen-Cahn phase-field model with order parameter C
and streamed h_i populations.  A pseudo-potential wall density force would act
on a different model family and would obscure whether the phase-field boundary
is mathematically closed.
```

### Free-energy and phase-field wetting sections

Manual sections:

```text
kappa n dot grad(phi) = f(phi_w, theta)
surface free energy H(phi_w)
geometric contact-angle format constructs virtual solid-node order parameter
```

Current code locations:

```text
wetting_kernel(...)
grad_laplace_mu_kernel(...)
c_neighbor_or_center(...)
stream_kernel(...)
boundary_kernel(...)
```

Current implementation state:

```text
wetting_kernel:
  c_wall = clamp01(c_field[x,y,z])
  dCdn = -(4/W) cos(theta) Cwall(1-Cwall)
  Cghost = clamp(Cwall + sign * distance * dCdn)

c_neighbor_or_center:
  if neighbor is solid, replace C with wall_c_ghost_field from adjacent wall.

grad_laplace_mu_kernel:
  computes grad(C), Laplace(C), mu using a 6-point stencil and the neighbor
  replacement above.
```

This matches the manual only at the concept level.  It is not yet a complete
surface-free-energy or geometric wetting implementation.

## Critical gaps exposed by the manual

### G1. `phase_wall_mode=3` does not yet apply wetting per-link reconstruction

Current code:

```text
if solid upstream and phase_wall_mode == 3:
    h_in(q) = h_out(opp(q))
```

This is neutral reflection.  The wall ghost exists as a shadow value and is
used by gradient/Laplace reconstruction, but it is not yet injected into the
missing incoming `h_i` population with a mass-accounted per-link formula.

Implication:

```text
The current solver can test wall ghost effects through mu/gradC, but it cannot
claim a complete phase-field wetting boundary.  Acute-angle failures cannot be
fixed only by tuning ghost sign/distance if the h_i boundary remains neutral.
```

Required next implementation:

```text
for each missing link q from solid to fluid:
  Cghost_link = geometric or surface-free-energy wall value
  h_in(q) = h_reflect(q) + link_weighted_correction(Cghost_link, Cfluid)
  record old mass, new mass, correction mass and clamp count
```

The exact correction must be derived so that the local/global phase mass ledger
is closed.  Late macro `C` overwrite remains forbidden.

### G2. Near-wall `mu` is not yet a book-level wall-gradient boundary

Current code uses:

```text
laplace = C(x+1)+C(x-1)+C(y+1)+C(y-1)+C(z+1)+C(z-1)-6C
```

with solid neighbors replaced by one adjacent `wall_c_ghost_field`.

The manual's free-energy route requires the wall derivative condition to enter
the near-wall gradient and second derivative consistently, not only as a scalar
ghost value.

Required next audit:

```text
flat wall:
  derive dC/dn = -(4/W) cos(theta) Cw(1-Cw)
  derive ghost-cell position relative to wall_y=0.5 and fluid y=1
  implement one-sided or ghost-based grad/Laplace formulas with known order
  verify theta=90 gives no-flux, theta<90 increases liquid affinity, theta>90
  decreases liquid affinity
```

For curved cylinder/sphere, this must later become SDF/per-link normal based,
not a flat y-neighbor special case.

### G3. Acute-angle runs are under-resolved and can mislead the boundary audit

From the calibrated angle audit:

```text
theta90: calibrated bbox about 88 deg, not the circle-fit 113 deg.
theta30/theta60: morphology collapses into a tall/detached cap pattern on
48x32x48, R=10, W=4.
```

The manual does not justify accepting these acute-angle results as physical.
For acute contact angles, the cap height/footprint near the wall must be
resolved relative to interface width.  Current `R=10, W=4` is too coarse for a
decisive 30-degree gate.

Required next gate:

```text
before using theta30/theta60 as failure evidence:
  run a larger-footprint flat-wall acute case, e.g. R >= 18 and W <= 4 if stable
  use calibrated bbox + morphology slice + mass/velocity metrics
```

### G4. Dynamic contact angle is not specified by the manual

The manual only lists advancing/receding contact angles as literature topics.
It does not provide a validated dynamic-contact-angle law.

Implication:

```text
Dynamic impact remains downstream.  First finish static wall/cylinder/sphere
contact-angle closure.  Do not add DynamicCL body-force tuning as a substitute
for static wetting boundary closure.
```

## Revised next implementation priority

This manual changes the next wetting step from "tune ghost distance/sign" to
"complete the phase-field wall boundary in the right population and stencil."

Recommended order:

1. Keep `pressure_model=2`, conservative Allen-Cahn source, and calibrated
   angle diagnostics as the current baseline.
2. Implement a flat-wall wetting boundary that affects missing incoming `h_i`
   populations, not only `wall_c_ghost_field`.
3. Replace near-wall flat-wall `grad/laplace/mu` with a derived ghost/one-sided
   version consistent with `dC/dn`.
4. Run neutral theta90 first; it should remain near 90 and mass-neutral.
5. Run larger-footprint theta60 and theta120 before theta30/150.
6. Only after flat wall passes, extend the same boundary concept to SDF
   cylinder/sphere normals.

## Forbidden shortcuts

Do not:

```text
1. add a Shan-Chen wall adhesion force to the phase-field model;
2. tune `wetting_ghost_distance` as a substitute for h_i boundary closure;
3. overwrite macro C/PhaseF at the wall and call it a wetting boundary;
4. claim dynamic-impact readiness from static morphology;
5. use circle-fit alone as contact-angle evidence.
```

## Current verdict

The manual is useful and directly supports the project, but it does not say
that the present Stage18 wetting implementation is complete.  It shows that the
next real repair is:

```text
phase-field wetting boundary = wall derivative / geometric ghost
                             + near-wall grad/Laplace consistency
                             + missing-link h_i population closure
                             + calibrated contact-angle measurement
```

At present Stage18 has the first and last pieces partially in place, while the
middle two are still incomplete.
