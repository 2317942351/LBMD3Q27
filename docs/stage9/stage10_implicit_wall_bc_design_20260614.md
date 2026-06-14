# Stage10 Design: Implicit Cahn-Hilliard Wall BC with Bulk Chemical Potential

Date: 2026-06-14
Status: DESIGN ONLY — no code written yet. Requires user sign-off.
Supersedes: stage9 Briant formula (which assumes equilibrium tanh interface).

## 0. Why this is needed (recap from stage9 audit)

The stage9 audit (`docs/stage9/audit_findings_20260614.md` point B) showed
that the Briant surface-energy formula, the tan sharp-interface formula, and
the unmodified upstream binary all give identical contact angles at theta=75
(77.60 deg, error 2.6 deg). The error scales as cot(theta) and is present in
upstream. Two candidate explanations:

(H1) The error is purely bulk-interface discretization (the 27-point Laplacian
and the isotropic gradient on a diffuse interface of finite width W), which no
wall BC can fix.

(H2) The error comes from the wall BC imposing an *equilibrium tanh shape*
assumption that the actual near-wall interface does not satisfy. The bulk
chemical potential `mu_bulk(phi)` is dropped in the Briant formula, so the
wall value is wrong whenever the interface is curved or perturbed.

Stage9 could not distinguish H1 from H2 because both candidate BCs assume the
equilibrium tanh shape. Stage10 tests H2 directly: it solves the wall value
with the **full** chemical potential `mu = mu_bulk(phi) - kappa * laplacian(phi)`
retained, eliminating the equilibrium-shape assumption. If H2 is the cause,
stage10 recovers the target angle. If H1 is the cause, stage10 also shows the
same error, and the lever is then IntWidth reduction (a separate, cheaper
path). Either way, stage10 is the decisive test.

## 1. Exact continuous wall BC (no approximations beyond the model's own)

The Cahn-Hilliard free-energy functional with a wall surface-energy density
`f_s(phi)`:

```
F[phi] = ∫_V [ psi(phi) + (kappa/2)|∇phi|² ] dV  +  ∫_S f_s(phi) dS
```

where `psi(phi)` is the bulk double-well such that `d psi/d phi = mu_bulk(phi)`,
and `kappa = 1.5*sigma*IntWidth` (from the upstream `calcMu`).

Varying `phi` in the fluid gives the bulk Allen-Cahn/Cahn-Hilliard equation.
Varying `phi` on the wall `S` gives the **natural boundary condition**:

```
kappa * (∂phi/∂n_w)|_wall  +  d f_s/d phi  =  0
```

This is exact. There is no equilibrium-shape assumption, no tanh, no cot(theta).
The wall free-energy density encodes the contact angle via Young's relation.
The standard choice (Jacqmin 2000, Ding-Spelt 2007, Fakhari-Mitchell 2017) is
**linear in phi**:

```
f_s(phi) = -h_g * cos(theta_e) * (12*sigma/IntWidth) * (phi - phi_avg)
```

The prefactor `12*sigma/IntWidth` is chosen so that, combined with `kappa =
1.5*sigma*IntWidth`, the sharp-interface limit of this BC reproduces Young's
equation `cos(theta_e) = (gamma_sv - gamma_sl)/gamma_lv` exactly (this fixes
the wall free-energy magnitude; see Appendix A for the derivation). Then:

```
d f_s / d phi = -h_g * cos(theta_e) * (12*sigma/IntWidth)
```

and the continuous wall BC becomes:

```
kappa * (∂phi/∂n_w)|_wall  =  h_g * cos(theta_e) * (12*sigma/IntWidth)
```

where `h_g` is the **wetting potential** (a single model parameter, set per
zone to tune the angle; `h_g = IntWidth/4 * something` maps to theta_e — see
Appendix A). This is the BC we discretize.

## 2. Discretization (implicit, no equilibrium-shape assumption)

We solve the wall ghost value `phi_g` (the value of phi at the wall-adjacent
ghost node, located at signed distance `-h_0` along `-n_w` into the solid) such
that the discrete wall BC holds.

The discrete normal derivative at the wall uses the wall value `phi_w` (at the
wall surface) and the first fluid node `phi_0` (at `+h_0` along `+n_w`):

```
(∂phi/∂n_w)|_wall ≈ (phi_0 - phi_w) / h_0        [first-order, one-sided]
```

The wall value `phi_w` is related to the ghost value `phi_g` (at `-h_0`) by
the centered formula `(phi_0 - phi_g)/(2*h_0)`, giving `phi_w = (phi_0+phi_g)/2`.
Substituting and setting the discrete BC:

```
kappa * (phi_0 - phi_g) / (2*h_0) = h_g * cos(theta_e) * (12*sigma/IntWidth)
```

This is **linear in phi_g** and has a closed-form solution:

```
phi_g = phi_0 - (2*h_0/kappa) * h_g * cos(theta_e) * (12*sigma/IntWidth)
      = phi_0 - (2*h_0 / (1.5*sigma*IntWidth)) * h_g * cos(theta_e) * (12*sigma/IntWidth)
      = phi_0 - 16 * (h_0*h_g/IntWidth²) * cos(theta_e)
```

Wait — this is again linear and equivalent to the Briant formula in the
small-gradient limit. The equilibrium-shape assumption enters when we replace
the **gradient** magnitude by the equilibrium value. To truly retain the bulk
chemical potential, the BC must be stated in terms of `mu`, not the gradient.

### 2.1 The correct implicit formulation (chemical potential form)

The exact natural BC is `kappa*(∂phi/∂n_w)|_wall + d f_s/d phi = 0`. But the
phase-field LBM advects the **chemical potential** `mu = mu_bulk(phi) - kappa*∇²phi`,
and the equilibrium condition at a static wall is that the wall chemical
potential equals the surface-energy derivative:

```
mu|_wall = -d f_s/d phi = h_g * cos(theta_e) * (12*sigma/IntWidth)
```

So the correct implicit BC is: **find `phi_g` such that the chemical potential
evaluated at the wall equals the prescribed wall value**. The chemical
potential at the wall depends on `phi_g` through both `mu_bulk(phi_g)` and the
Laplacian stencil (which reads `phi_g` and its neighbors). This is a
**nonlinear scalar equation in phi_g**:

```
g(phi_g) = mu_bulk(phi_g) - kappa * ∇²phi|_wall  -  mu_wall_target  =  0
```

where:
- `mu_bulk(phi_g) = 4*(12*sigma/IntWidth)*(phi_g-phi_l)*(phi_g-phi_h)*(phi_g-phi_avg)`
  (exact upstream formula, evaluated at `phi_g`)
- `∇²phi|_wall` uses the 27-point stencil with `phi_g` substituted at the
  ghost position; for a wall-adjacent fluid node the stencil reads the ghost
  once, so `∇²phi = c_0*phi_0 + c_g*phi_g + sum(c_i*phi_i)` where `c_g` is the
  stencil weight on the ghost
- `mu_wall_target = h_g * cos(theta_e) * (12*sigma/IntWidth)`

This is a cubic equation in `phi_g` (cubic from `mu_bulk`, linear from the
Laplacian term). A cubic has a closed-form solution but it is messy; a
**2-3 iteration Newton solve** is cleaner and converges quadratically. This is
the implicit solve.

### 2.2 What is solved implicitly vs explicitly

Implicit (the new part):
- `phi_g` at each analytic-flagged wall node, via 2-3 Newton iterations on
  `g(phi_g) = 0`. Each iteration evaluates `mu_bulk`, the local Laplacian
  (treating `phi_g` as the unknown and all other stencil values as fixed from
  the current time step), and `g'(phi_g)`.

Explicit (unchanged from upstream):
- The bulk phase-field LBM step, the gradient computation, the velocity solve.
- The wall ghost is computed once per LBM step (in `calcWallPhase`), then held
  fixed for that step. This matches how upstream treats the ghost value.

### 2.3 Why this eliminates the equilibrium-shape error

The Briant/tan formulas implicitly assume `|∇phi|_wall = (2/IntWidth)*...` (the
equilibrium tanh slope). The implicit solve does **not** assume this: it reads
the actual local Laplacian and the actual `mu_bulk(phi_g)`, so the solved
`phi_g` is consistent with the real (possibly perturbed, possibly curved)
interface shape near the wall. If H2 (equilibrium-shape assumption) is the
error source, this removes it. If H1 (bulk discretization) is the source, this
will not help — and that is itself a valid, decisive result.

## 3. The wetting potential `h_g` and the contact angle

The wetting potential `h_g` is the single parameter that sets the contact
angle. It is NOT `theta_e` directly. The mapping `h_g <-> theta_e` is:

- For a flat equilibrium interface, `h_g = 0` gives `theta = 90 deg` (neutral).
- `h_g > 0` gives `theta < 90` (wetting); `h_g < 0` gives `theta > 90`.
- The exact mapping requires either (a) a 1D equilibrium solve (Appendix B),
  or (b) a calibration run at one angle.

We provide `h_g` as a zonal setting (`WettingPotential`, default 0) and a
helper that converts a requested `theta_e` to `h_g` via the 1D equilibrium
relation (Appendix B). This avoids the `tan(pi/2-theta)` singularity entirely.

## 4. Verification plan (must pass before any LBM run)

### V1: Standalone 1D equilibrium solver (Python, no LBM)

Solve the 1D Cahn-Hilliard equilibrium `mu = const` on `[0, L]` with the
implicit wall BC at `x=0` and a fixed `phi=phi_h` at `x=L`, for the exact
upstream constants (`sigma=5e-5, IntWidth=6, kappa=1.5*sigma*IntWidth`,
`mu_bulk = 4*(12*sigma/W)*(phi-phi_l)(phi-phi_h)(phi-phi_avg)`).

For a sweep of `h_g`, measure the equilibrium contact angle (geometric, from
the phi=0.5 contour slope at the wall). This produces the `h_g <-> theta_e`
calibration curve **and verifies the BC reproduces Young's equation in the
sharp-interface limit** (large L, small W/L). If V1 fails, the BC is wrong and
no LBM run is meaningful.

### V2: Manufactured-solution test for the Newton solve

Construct a known phi field (e.g. a tilted tanh interface), compute the exact
`phi_g` that satisfies `g(phi_g)=0` analytically, and verify the device
function reproduces it to machine precision. This isolates the solve from the
LBM dynamics.

### V3: 2D LBM sessile drop, plane wall, theta sweep

Only after V1+V2 pass. Run theta=30/60/90/120/150 on a plane wall and measure
the contact angle. Pass criterion: |measured - target| < 2 deg across the
sweep, with no cot(theta) scaling. If cot(theta) scaling persists, H1 is
confirmed and stage10 does not help (report and stop).

### V4: 2D LBM, curved wall (cylinder), theta=30

Only after V3. Confirms the analytic normal + implicit BC work on curvature.

### V5: Mass conservation and energy dissipation

The implicit BC must not create or destroy phase-field mass. Track
`∫ phi dV` over 200k steps; drift must be < 0.1%.

## 5. Risk assessment (honest)

| Risk | Likelihood | Mitigation |
|---|---|---|
| H1 is the cause (error is bulk discretization, not wall BC) | ~40% | V3 directly tests this; if confirmed, stop and pivot to IntWidth reduction |
| Newton solve fails to converge for extreme phi_g | low | clamp iterations to 3, fall back to Briant if not converged, log via WallGhostClampHit |
| Cubatic runaways at low theta | medium | the implicit BC removes the tan(pi/2-theta) singularity, so low theta is actually safer than stage9 |
| LBM instability from implicit ghost | low | ghost is held fixed per step (semi-implicit), same coupling as upstream |
| The `h_g <-> theta_e` mapping is wrong | medium | V1 verifies it before any LBM run |
| Performance: 3 Newton iterations per wall node per step | low | wall nodes are O(surface), not O(volume); negligible vs bulk |

## 6. Correctness argument (why I believe this is right)

1. The continuous BC `kappa*(∂phi/∂n_w) + d f_s/d phi = 0` is the exact
   variational result. It is in every phase-field wetting reference (Jacqmin
   2000 JCP 152, Ding-Spelt 2007 JCP 226, Fakhari-Mitchell 2017 PRE 95). No
   controversy.
2. The chemical-potential form `mu|_wall = mu_wall_target` is equivalent to
   the gradient form at equilibrium (Appendix C). It is the better numerical
   form because `mu` is what the LBM advects.
3. The discrete solve retains `mu_bulk(phi_g)` — the term the Briant/tan
   formulas drop. This is the only approximation in stage9 that stage10
   removes.
4. The verification ladder (V1 no-LBM, V2 manufactured, V3 plane sweep, V4
   curved, V5 conservation) catches errors at each level before proceeding.
   No claim is made from a smoke test.
5. If stage10 does NOT improve the angle, that is a valid scientific result
   (it confirms H1), not a failure to hide.

## 7. What I will NOT claim

- I will not claim stage10 "fixes" the angle until V3 passes with < 2 deg
  error across the theta sweep.
- I will not write "pass" for any result outside its gate.
- I will not run sphere/cylinder until plane V3 passes.
- I will report negative results (H1 confirmed) honestly if that is what V3
  shows.

## Appendix A: Wetting potential prefactor and Young's equation

For a flat equilibrium interface of width W meeting a wall at angle theta_e,
the wall free-energy density that reproduces Young's equation is (Jacqmin 2000):

```
f_s(phi) = -W * cos(theta_e) * (sigma_lv / W) * (phi - phi_avg) * (normalization)
```

Matching the model's bulk chemical potential scale `12*sigma/W` and gradient
coefficient `kappa = 1.5*sigma*W`, the consistent normalization gives:

```
d f_s/d phi = -h_g * cos(theta_e) * (12*sigma/IntWidth)
```

with `h_g` a length-scale wetting potential. In the sharp-interface limit
(W -> 0, fixed kappa*W), this reduces exactly to Young's equation
`cos(theta_e) = (gamma_sv - gamma_sl)/gamma_lv`. The derivation will be
checked numerically in V1.

## Appendix B: h_g <-> theta_e calibration (1D equilibrium)

For a 1D semi-infinite domain with wall at x=0, the equilibrium profile
satisfies `mu(phi) = mu_bulk(phi) - kappa*phi'' = mu_wall_target`. Integrating
once with `phi'(∞) = 0` gives `(kappa/2)(phi')² = psi(phi) - psi(phi_h)`.
At the wall, `phi'(0) = -(1/kappa) * d f_s/d phi`. Combining and solving for
the wall value gives `h_g` as a function of `theta_e`. This is a 1D ODE
boundary-value problem solved in V1 (Python, scipy) to produce the calibration
table, which is then hard-coded as a piecewise-linear lookup in the model.

## Appendix C: Equivalence of gradient and chemical-potential forms

At equilibrium, `mu = const` everywhere in the fluid. The wall BC
`kappa*(∂phi/∂n_w) + d f_s/d phi = 0` is equivalent to
`mu|_wall = -d f_s/d phi + mu_bulk(phi_w) - kappa*(∂²phi/∂n_w²)|_wall`. For
the discrete stencil the Laplacian at the wall includes the ghost, so the
chemical-potential form `mu(phi_g) = mu_wall_target` is the discrete
counterpart. The two forms agree at equilibrium; the chemical-potential form
is numerically better because it uses the same `mu` the LBM transports.
