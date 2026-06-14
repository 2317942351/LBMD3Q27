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

## 1. Continuous natural BC and the Stage10 discrete candidate

**NAMING CORRECTION (per reviewer 2026-06-14):** Stage10 is an *implicit
chemical-potential wall **candidate*** derived from the free-energy natural
BC. It is NOT a proven-exact BC. The continuous natural BC is exact; the
chemical-potential discrete form we implement is a candidate whose correctness
must be established by V1. Until V1 passes, nothing here is called "exact",
"proven", or "necessarily correct".

### 1.1 The continuous natural BC (this IS the exact variational result)

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
kappa * (∂phi/∂n_w)|_wall  +  d f_s/d phi  =  0          ... (NBC)
```

This (NBC) is the exact variational result. It contains no equilibrium-shape
assumption. **Important caveat (Ding & Spelt 2007, JCP 226, sec. 2.3):** the
surface-energy / natural-BC formulation does *not* in general impose the
*specified* contact-angle slope directly — it imposes a wall free-energy whose
sharp-interface limit recovers Young's equation, but for finite interface
width the realized angle can deviate. The geometric formulation (tan/cot)
constrains the angle directly but assumes the equilibrium tanh shape. Stage10
tests whether the chemical-potential form of the NBC realizes the target angle
more accurately than the equilibrium-shape-assuming formulas. This is a
research question, not a settled result.

The wall free-energy density is taken **linear in phi** (Jacqmin 2000, the
standard choice for phase-field wetting):

```
f_s(phi) = -h_g * cos(theta_e) * (12*sigma/IntWidth) * (phi - phi_avg)
```

so that

```
d f_s / d phi = -h_g * cos(theta_e) * (12*sigma/IntWidth)
```

where `h_g` is the **wetting potential** (a length-scale parameter; see
Appendix A for the sharp-interface-limit normalization and Appendix B for the
`h_g <-> theta_e` calibration). The continuous NBC then reads:

```
kappa * (∂phi/∂n_w)|_wall  =  h_g * cos(theta_e) * (12*sigma/IntWidth)      ... (NBC)
```

### 1.2 Stage10 discrete candidate (what we actually implement)

Stage10 implements a **chemical-potential form** of the NBC as a discrete
candidate BC. It is NOT the NBC itself, and it is NOT claimed to be exact. Its
correctness is what V1 must establish.

The candidate arises from observing that the phase-field LBM transports the
chemical potential `mu = mu_bulk(phi) - kappa*∇²phi`, and that at a static
equilibrium wall the chemical potential is constant. The candidate BC is:

```
find phi_g  such that   mu(phi_g)|_wall = mu_wall_target
i.e.   g(phi_g) = mu_bulk(phi_g) - kappa*∇²phi|_wall - mu_wall_target = 0     ... (CANDIDATE)
```

where:
- `mu_bulk(phi_g) = 4*(12*sigma/IntWidth)*(phi_g-phi_l)*(phi_g-phi_h)*(phi_g-phi_avg)`
  (the upstream bulk chemical-potential formula, evaluated at the unknown `phi_g`)
- `∇²phi|_wall` uses the 27-point stencil with `phi_g` substituted at the
  ghost position; for a wall-adjacent fluid node the stencil reads the ghost
  once, so `∇²phi = c_0*phi_0 + c_g*phi_g + sum(c_i*phi_i)` where `c_g` is the
  stencil weight on the ghost
- `mu_wall_target = h_g * cos(theta_e) * (12*sigma/IntWidth)`

This is a nonlinear (cubic in `phi_g` from `mu_bulk`, linear from the
Laplacian) scalar equation, solved by 2-3 Newton iterations.

### 1.3 Why this is a candidate worth testing, not a proven BC

The (NBC) and the (CANDIDATE) agree at continuous equilibrium, but the
discrete (CANDIDATE) is not guaranteed to realize a specified contact angle
for finite interface width. Ding & Spelt (2007 JCP 226, sec. 2.3) explicitly
note that surface-energy formulations do not in general impose the specified
contact-angle slope directly; the geometric formulation does, but assumes the
equilibrium tanh shape. Stage10's (CANDIDATE) is a third option that, like
the surface-energy form, does not assume tanh shape, but, unlike prior
surface-energy implementations, retains `mu_bulk(phi_g)` in the wall solve
rather than dropping it.

**Whether this reduces the cot(theta) contact-angle error is the open question
V1-V3 are designed to answer.** Until V1 passes (the candidate reproduces
Young's equation in the 1D sharp-interface limit), the candidate must not be
described as "exact", "correct", or "proven".

## 2. Discretization (the candidate)

We solve the wall ghost value `phi_g` (the value of phi at the wall-adjacent
ghost node, located at signed distance `-h_0` along `-n_w` into the solid)
from the (CANDIDATE) equation `g(phi_g) = 0` defined in section 1.2.

The Laplacian `∇²phi|_wall` is evaluated with the 27-point stencil at the
wall-adjacent fluid node, treating `phi_g` as the unknown at the ghost
position and all other stencil entries as fixed from the current time step.
The Newton iteration uses the analytic derivative:

```
g'(phi_g) = d mu_bulk/d phi|_{phi_g}  -  kappa * c_g
           = 4*(12*sigma/IntWidth) * [ (phi_g-phi_h)(phi_g-phi_avg)
                                     + (phi_g-phi_l)(phi_g-phi_avg)
                                     + (phi_g-phi_l)(phi_g-phi_h) ]  -  kappa*c_g
```

### 2.1 What is solved implicitly vs explicitly

Implicit (the new part):
- `phi_g` at each analytic-flagged wall node, via 2-3 Newton iterations on
  `g(phi_g) = 0`. Each iteration evaluates `mu_bulk`, the local Laplacian
  (treating `phi_g` as the unknown and all other stencil values as fixed from
  the current time step), and `g'(phi_g)`.

Explicit (unchanged from upstream):
- The bulk phase-field LBM step, the gradient computation, the velocity solve.
- The wall ghost is computed once per LBM step (in `calcWallPhase`), then held
  fixed for that step. This matches how upstream treats the ghost value.

### 2.2 Why this might reduce the equilibrium-shape error (hypothesis, not claim)

The Briant/tan formulas implicitly assume `|∇phi|_wall = (2/IntWidth)*...` (the
equilibrium tanh slope). The candidate solve does **not** assume this: it reads
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
- The exact mapping is produced by the V1 1D equilibrium solve (Appendix B).

### 3.1 h_g calibration interface (per reviewer decision 2026-06-14)

The reviewer selected: **(a) Python offline 1D ODE calibration lookup table
as the primary path**, **(c) direct `h_g` specification retained as an audit
override**, and **rejected (b) the linear approximation `h_g ≈ (W/4)cos(theta)`
as a main path**. The linear approximation may appear only as a sanity check,
never in the production interface or in any low/mid/high-angle or curved-wall
validation. Rationale: the problem Stage10 solves is precisely "an unverified
formula assumption caused the error", so an unverified linear approximation
must not be re-introduced into the main path.

Concretely:

- **Primary interface** (case XML): user specifies `theta_target` (degrees).
  The model calls `h_g = h_g_lookup(theta_target, W, sigma, phi_l, phi_h)`,
  where `h_g_lookup` reads a versioned lookup table produced by V1 and
  committed to the repo (e.g. `data/stage10/hg_calibration_W6.json`).
- **Audit override** (case XML, optional): `OverrideHg` (a real number). When
  set, the model uses `OverrideHg` directly instead of `h_g_lookup`, and logs
  a warning. This is for calibrating the lookup table itself and for
  sensitivity sweeps. It is NOT used in any validation gate.
- **NOT a main path**: the linear approximation
  `h_g ≈ (IntWidth/4)*cos(theta_target)` is implemented only inside V1 as a
  sanity check against the ODE solution, and is never exposed to case XML.

### 3.2 Per-case metadata requirement (per reviewer)

Every Stage10 case record must include:

```
theta_target           (deg, the requested angle)
h_g                    (the wetting potential actually used)
hg_source              ("lookup_v1" | "override")
hg_lookup_version      (sha256 of the lookup table file, if lookup used)
hg_lookup_residual     (max interpolation residual at theta_target, if lookup)
ode_residual           (max natural-BC + chemical-potential residual on the
                        1D equilibrium at this h_g, from V1)
young_residual         (|cos(theta_realized) - cos(theta_target)| in the
                        sharp-interface limit, from V1)
wall_ghost_clamp_fraction  (fraction of wall nodes where the ghost was
                        clipped; must be 0 for a case to pass)
```

Cases missing any of these fields cannot be promoted past
`exploratory_not_validation`.

## 4. Verification plan (must pass before any LBM run)

### V1: Standalone 1D equilibrium solver (Python, no LBM)

Solve the 1D Cahn-Hilliard equilibrium `mu = const` on `[0, L]` with the
candidate wall BC at `x=0` and a fixed `phi=phi_h` at `x=L`, for the exact
upstream constants (`sigma=5e-5, IntWidth=6, kappa=1.5*sigma*IntWidth`,
`mu_bulk = 4*(12*sigma/W)*(phi-phi_l)(phi-phi_h)(phi-phi_avg)`).

**V1 must report TWO residuals on the converged 1D equilibrium profile, per
reviewer requirement:**

```
natural_BC_residual          = kappa * (d phi/d x)|_wall  +  d f_s/d phi
chemical_potential_residual  = mu_bulk(phi_g) - kappa * nabla2_phi_wall - mu_wall_target
```

**V1 PASS criterion (all three required):**
1. Both residuals converge to < 1e-8 (relative) as the 1D grid refines.
2. The geometric contact angle from the converged profile matches the
   `h_g <-> theta_e` calibration to < 0.5 deg.
3. In the sharp-interface limit (L -> large, W/L -> 0), the realized angle
   converges to Young's equation `cos(theta) = h_g / h_g_young_ref` to < 0.5 deg.

**V1 STOP condition:** if the two residuals cannot BOTH converge on the 1D
equilibrium solution, the candidate BC is internally inconsistent with the
continuous NBC. Stage10 stops; no TCLB code is written. This is the gate the
reviewer insisted on.

For a sweep of `h_g`, V1 also produces the `h_g <-> theta_e` calibration
table that the LBM model will consume (Appendix B).

### V2: Manufactured-solution test for the Newton solve

Construct a known phi field (e.g. a tilted tanh interface), compute the exact
`phi_g` that satisfies `g(phi_g)=0` analytically (by construction), and verify
the device function reproduces it to machine precision. This isolates the
Newton solve from the LBM dynamics. **V2 PASS: max|phi_g_solved - phi_g_exact|
< 1e-10 across the manufactured cases.**

**V2 STOP on Newton non-convergence:** per reviewer, Newton failure does NOT
fall back to Briant and pass. If Newton fails to converge on any manufactured
case, the case is **blocked**. A Briant fallback may be recorded as a negative
control but does NOT participate in any pass claim.

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
| H1 is the cause (error is bulk discretization, not wall BC) | ~40% | V3 directly tests this; if confirmed, report negative result and stop |
| Newton solve fails to converge for extreme phi_g | low | **NOT** a fallback-to-Briant-and-pass. NewtonFail -> case blocked. Briant may be recorded as negative control only. |
| Low-theta instability | medium | the candidate removes the tan(pi/2-theta) singularity, so low theta is plausibly safer than stage9; V3 verifies |
| LBM instability from implicit ghost | low | ghost is held fixed per step (semi-implicit), same coupling as upstream |
| The `h_g <-> theta_e` mapping is wrong | medium | V1 verifies it before any LBM run |
| Clamp fraction hides a wrong angle | medium | WallGhostClampHit is a safety diagnostic; if clamp fraction >0 AND affects the angle, the case cannot pass |
| Performance: 3 Newton iterations per wall node per step | low | wall nodes are O(surface), not O(volume); negligible vs bulk |

## 6. Correctness argument (what is and is not established)

**Established (no controversy):**
1. The continuous NBC `kappa*(∂phi/∂n_w) + d f_s/d phi = 0` is the exact
   variational result (Jacqmin 2000 JCP 152, Ding-Spelt 2007 JCP 226,
   Fakhari-Mitchell 2017 PRE 95).
2. The candidate discrete form `g(phi_g) = 0` is a legitimate discretization
   choice that retains `mu_bulk(phi_g)`.

**NOT established (what V1-V3 must test):**
3. Whether the candidate discrete form realizes a *specified* contact angle
   for finite interface width. Ding & Spelt (2007) explicitly warn that
   surface-energy formulations do not in general impose the specified angle
   slope directly. V1 tests this in 1D; V3 tests it in 2D LBM.
4. Whether retaining `mu_bulk(phi_g)` actually reduces the cot(theta) error
   vs the Briant/tan formulas. This is the H2 hypothesis; V3 is decisive.

**The verification ladder catches errors at each level before proceeding. No
claim is made from a smoke test. If stage10 does NOT improve the angle, that
is a valid scientific result (it confirms H1), not a failure to hide.**

## 7. What I will NOT claim

- I will not claim stage10 "fixes" the angle until V3 passes with < 2 deg
  error across the theta sweep.
- I will not write "pass" for any result outside its gate.
- I will not run sphere/cylinder until plane V3 passes.
- I will report negative results (H1 confirmed) honestly if that is what V3
  shows.
- I will not describe the candidate as "exact", "proven", or "the correct BC"
  until V1 establishes the two-residual consistency and the Young-equation
  limit.


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
