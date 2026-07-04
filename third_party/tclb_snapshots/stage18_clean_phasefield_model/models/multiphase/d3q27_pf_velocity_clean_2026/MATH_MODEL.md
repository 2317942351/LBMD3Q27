# Mathematical Model Baseline

Date: 2026-07-03

This file fixes the mathematical contract for `d3q27_pf_velocity_clean_2026`. It is the starting point for rebuilding the TCLB model, not a validation claim.

## Variables

The order parameter is

```text
C = PhaseF
C_l = PhaseField_l
C_h = PhaseField_h
q = (C - C_l) / (C_h - C_l)
```

The physical admissible interval is

```text
C_l <= C <= C_h
```

Any departure from this interval is a phase-equation or wall-source failure. It must not be hidden by contact-angle post-processing.

## Phase Population

The streamed phase populations are `h_i`. In TCLB they are `AddDensity` entries and therefore participate in framework streaming. They are not ordinary current-cell C arrays.

The macroscopic phase is reconstructed only in the `PhaseFromH` stage:

```text
C = sum_i h_i
```

The phase population update must satisfy the moment contract:

```text
sum_i h_i^eq = C
sum_i e_i h_i^eq = C u
sum_i F_phi_i = S_0
sum_i e_i F_phi_i = S_1
```

For the legacy Allen-Cahn-like source form inherited by this project:

```text
tmp1 = (1 - 4 (C - 0.5)^2) / IntWidth
F_phi_i = w_i tmp1 (e_i dot n_phi)
n_phi = grad(C) / (|grad(C)| + eps)
```

This formula is not allowed to consume unbounded `C`, solid sentinels, or stale wall values. If `tmp1` is modified, the zeroth and first moments above must be re-audited.

## Density And Viscosity

The density interpolation is

```text
rho(C) = rho_l + (C - C_l) (rho_h - rho_l) / (C_h - C_l)
```

with the mandatory implementation invariant

```text
rho_for_force >= RhoFloor
```

Relaxation time is selected by `TauMode`:

```text
linear
inverse_kinematic
linear_dynamic_viscosity
harmonic_dynamic_viscosity
```

The active mode must keep

```text
tau > 0.5
```

Low-density force closure must use `rho_for_force`, not an unchecked density computed from an invalid phase value.

## Gradient, Laplace, And Chemical Potential

The active chemical potential has the form

```text
mu = beta (C - C_l) (C - C_h) (2 C - C_l - C_h) - kappa laplace(C)
```

where `beta` and `kappa` must be derived from `sigma` and `IntWidth` for the selected phase-field model. The legacy upstream expression may be kept only under a named compatibility mode.

The stencil contract is:

```text
gradPhi = GradPhiMode(C, SolidGeom, WallPhase)
lapPhi  = LaplaceMode(C, SolidGeom, WallPhase)
```

`gradPhi` and `lapPhi` must never read `PhaseF=-999` or any other sentinel as a physical value. Near-wall values must be reconstructed from fluid values, analytic signed distance, diffuse-solid normal, or a documented ghost value.

## Momentum Force Closure

The total force is decomposed as

```text
F_total = F_surf + F_pressure + F_mu + F_body
```

with:

```text
F_surf     = mu grad(C)                     legacy compatible form
F_pressure = pressure_closure * grad(rho)   pressure mode dependent
F_mu       = stress_reconstruction dot grad(rho)
F_body     = gravity/buoyancy
```

The pressure closure must explicitly define whether the consumed scalar is:

```text
m0[0]
sum_i g_i
pstar
physical pressure p
p - p_ref
```

No implementation may silently treat `m0[0]` as physical pressure without this derivation.

Force insertion must obey:

```text
u_macro = momentum / rho + 0.5 F_total / rho
```

and the population update must inject the force exactly once. Any MRT forcing mode must provide an equivalent-force audit before it is used for contact-angle validation.

## Stage18 Momentum MRT Policy

The clean baseline uses MRT for the momentum population `g_i`, but the phase population `h_i` is intentionally kept as a separate Allen-Cahn-type source/update path until its moments are fully audited.

Current policy:

```text
MomentumMRTMode = 1:
  use full 27-moment relaxation rates
  shear relaxation = 1/tau unless MRTShearOmegaOverride > 0
  conserved momentum modes = 1.0 in the forcing update convention
  bulk/energy and high-order ghost relaxation = MRTBulkOmega
  clamp all configurable omega values to [MRTMinOmega, MRTMaxOmega]
```

The implementation must transform all 27 `g_i` populations to moment space,
not only the first ten low-order moments. Updating only a truncated moment set
is not a robust MRT scheme because uninitialized high-order moments can be
silently dropped or reconstructed from undefined state after `invM`.

This follows the book-guided repair order:

```text
first: split TCLB stages and close heq/F_phi moments
then: stabilize momentum MRT spectrum
later: consider non-diagonal phase MRT only if corrected source modes fail
```

Non-diagonal phase MRT is therefore not enabled in this baseline. It remains a later design branch, not a quick replacement for the phase source closure.

## Wetting Boundary

Wetting state is non-streaming wall state:

```text
WallPhase
WallPhaseValid
WallNormal
WallDistance
WallLinkMask
```

The geometric virtual-phase boundary may be written as:

```text
WallPhase = C_f + 2 h tan(pi/2 - theta) |grad_t C|
```

where:

```text
C_f      = reconstructed adjacent fluid phase
h        = wall-fluid distance along the solid normal
grad_t C = tangential phase gradient at the wall
theta    = target contact angle
```

For surface-free-energy wetting, the boundary condition must instead be expressed as a wall-normal derivative relation:

```text
n_wall dot grad(C) = g(C_wall, theta, sigma, IntWidth)
```

The two formulations may coexist only behind an explicit `WettingModel` switch. They must not be mixed implicitly in the same path.

## Wall Phase Population Source

The central TCLB implementation rule is:

```text
wall/solid h_i source values are passive streamed sources, not active phase reservoirs
```

Therefore:

```text
WettingBoundary -> WallPhase
WallPhasePopulationSource -> bounded source h_i on wall/solid links
next framework streaming -> fluid PhaseFromH consumes incoming h_i
```

It is forbidden to impose wetting by late overwriting of fluid `PhaseF` after phase collision. Wall source writes must be mass-audited:

```text
WallHOutgoingMass
WallHIncomingMass
WallHNetMass
MassCorrectionApplied
```

## Geometry

The geometry contract is:

```text
GeometryMode = 0 bulk | 1 plane | 2 cylinder | 3 sphere | 4 diffuse-solid/imported
SolidIndicator = non-streaming
SignedDistance = non-streaming
SolidNormal = non-streaming
NearWallBand = non-streaming
```

Cylinder axis is explicit:

```text
SolidAxis = 0 x | 1 y | 2 z
```

Analytic plane, cylinder, and sphere normals must come from signed distance or diffuse-solid gradients, not from `PhaseF=-999` inference.

## Validation Meaning

This model is considered physically usable only after these gates pass in order:

```text
bulk phase boundedness
flat wall 90 deg neutral
flat wall 30/150 deg static morphology
flat wall decoupled response
cylinder static contact angle
sphere static contact angle
pressure jump and spurious velocity
dynamic impact preflight
```

Morphology plots and contact-angle fitting are required, but they are not sufficient unless boundedness, mass conservation, and force closure are also credible.
