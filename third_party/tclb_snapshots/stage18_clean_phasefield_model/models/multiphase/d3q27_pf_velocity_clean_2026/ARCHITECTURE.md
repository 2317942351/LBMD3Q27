# D3Q27 Phase-Field Wetting Solver Architecture

Date: 2026-07-03

This document defines the intended full architecture for `d3q27_pf_velocity_clean_2026`. It is not a minimal model. It is the complete target architecture required for static contact angles on flat, cylindrical, and spherical solids and for later dynamic impact cases.

## Design Principle

The solver has two independent sources of truth:

1. Physics and numerical method:
   - phase-field LBM books and project anchors:
     - `docs/stage14/178_phasefield_lbm_book_ch3_ch7_code_audit_20260703.md`
     - `docs/stage14/180_phasefield_lbm_book_full_solver_patch_audit_20260703.md`
     - `docs/stage14/183_huang_liu_lbm_phase_wetting_context_anchor_20260703.md`
     - `docs/stage14/184_he_li_wang_tong_lbm_theory_phase_wetting_anchor_20260703.md`
   - compact-stencil curved wetting literature, used only for curved boundary reconstruction after the phase equation is closed.

2. Implementation semantics:
   - official TCLB documentation:
     - `references/tclb_official_docs_20260703/README_TCLB_OFFICIAL_DOCS.md`
     - `docs/stage14/187_tclb_official_model_development_anchor_20260703.md`
   - local skill:
     - `C:\Users\yuanz\.codex\skills\tclb-model-development\`

If physics notation conflicts with TCLB staging semantics, the implementation must be redesigned. C-array logic must not be pasted directly into streamed `AddDensity` populations.

## Governing Variables

### Phase field

Use an order parameter:

```text
C = PhaseF
C_l = PhaseField_l
C_h = PhaseField_h
q = (C - C_l) / (C_h - C_l)
```

Required invariant:

```text
C_l <= C <= C_h
```

The solver must distinguish:

- `PhaseF`: non-streaming macroscopic phase field saved as an `AddField`;
- `h_i`: streamed phase distribution populations declared by `AddDensity`;
- `WallPhase`: passive virtual wall phase used to impose wetting;
- `SolidIndicator`: non-streaming geometry indicator;
- `SolidNormal`: non-streaming analytic/diffuse solid normal.

`PhaseF` is produced from `h_i` only at a stage explicitly designed for that purpose. Wall/solid nodes must not produce active phase populations unless the stage contract says so.

### Phase distributions

The phase population update must recover a conservative Allen-Cahn-type equation in lattice units:

```text
partial_t C + div(C u) = div(M * phase_operator) + sharpening/source correction
```

The exact equation used by the solver must be documented in the implementation before code is changed. At minimum the following moment constraints must be enforced:

```text
sum_i h_i^eq = C
sum_i e_i h_i^eq = C u  (to the selected order)
sum_i F_phi_i = prescribed zeroth source moment
sum_i e_i F_phi_i = prescribed first source moment
```

No hard clamp may be treated as the mathematical model. Boundedness protection is allowed only if it is conservative, reported, and separated from the physical phase equation.

### Density and viscosity interpolation

Density:

```text
rho(C) = rho_l + (C - C_l) * (rho_h - rho_l) / (C_h - C_l)
```

Dynamic viscosity and relaxation time must use a named interpolation mode:

```text
TauMode = linear | inverse | dynamic_viscosity | harmonic_dynamic_viscosity
```

Invariant:

```text
rho_for_force > rho_floor
tau > 0.5
```

If `C` leaves the valid interval, density, force, and pressure are invalid. Such a run is a solver failure, not a contact-angle result.

### Chemical potential and gradients

The chemical potential is based on:

```text
mu = dPsi/dC - kappa * laplace(C)
```

The active implementation must provide:

- `GradPhiMode`: bulk isotropic / wall reconstructed / diffuse-solid reconstructed;
- `LaplaceMode`: bulk isotropic / wall reconstructed / diffuse-solid reconstructed;
- `MuWallFluxMode`: no-flux chemical potential wall closure.

Solid sentinel values must never enter `gradPhi` or `mu` as physical phase values.

### Force closure

The momentum force decomposition is:

```text
F_total = F_surf + F_pressure + F_mu + F_body + F_contact_line_optional
```

Each term must have a named closure:

- `F_surf`: chemical-potential/surface-tension force form;
- `F_pressure`: pressure closure derived from the selected phase-field momentum model;
- `F_mu`: viscous/stress reconstruction closure;
- `F_body`: gravity/buoyancy;
- `F_contact_line_optional`: disabled by default; only for dynamic wetting after static gates pass.

The pressure variable cannot be assumed to be `m0[0]` unless the derivation states that `m0[0]` is the required pressure or normalized pressure moment.

Velocity and force insertion must state:

```text
u_macro = momentum/rho + 0.5 F/rho
population force moment injection = exactly one selected forcing scheme
```

The solver must prove that half-force is not injected twice.

## Wetting Boundary Conditions

The wetting boundary must support:

- flat wall;
- analytic cylinder;
- analytic sphere;
- later diffuse-solid/compact-stencil reconstruction for curved surfaces.

Wetting physics options:

```text
WettingModel = geometric_virtual_phase | surface_free_energy
```

For geometric virtual phase:

```text
WallPhase = reconstruct(C_fluid, grad_tangent, n_solid, theta)
```

For surface-free-energy:

```text
n_wall dot grad(C) = boundary_function(C_wall, theta, sigma, interface_width)
```

Implementation rules:

- wall/solid phase information is non-streaming wall state;
- wall/solid `h_i` populations are passive source values, not active collision nodes;
- per-link wall-to-fluid phase population reconstruction must be mass-audited;
- curved surfaces must use analytic signed distance or diffuse-solid normals, not staircase sentinel inference;
- no wetting write path may be enabled by the same flag used for flat diagnostic shadow fields.

## Geometry

Geometry must be represented by explicit non-streaming fields:

```text
SolidIndicator
SignedDistance
SolidNormalX/Y/Z
NearWallBand
WallPhase
WallPhaseValid
WallLinkMask
```

Supported geometry types:

```text
0 fluid-only/bulk
1 flat plane
2 infinite cylinder
3 sphere
4 imported solid/diffuse-solid field, future
```

Cylinder axis must be explicit:

```text
SolidAxis = 0 x | 1 y | 2 z
```

No geometry may rely on `PhaseF=-999` as its primary normal source.

## Dynamic Impact Readiness

The architecture includes dynamic cases from the start, but they remain downstream gates. The dynamic path requires:

- bounded phase equation without frequent limiter activation;
- mass/volume conservation;
- static droplet pressure-jump and spurious-current validation;
- flat-wall static contact angle;
- cylinder/sphere static contact angle;
- only then impact velocity and dynamic contact-line terms.

Dynamic impact must not reuse a static contact-angle correction as an unvalidated forcing term.
