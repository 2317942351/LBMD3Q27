# Stage10 V1 Option B — Design (imposed-wall-value consistency test)

Date: 2026-06-14
Authorization: Option B (then Option A if B passes). No TCLB, no V2 until A passes.

## What Option B tests (and what it does NOT)

**Tests:** for a fixed wall value `phi_w`, do the natural BC and the chemical-
potential candidate determine the *same* ghost value `phi_g`?

**Does NOT test:** whether a specified contact angle is realized (no contact
line in 1D). Does NOT produce `h_g <-> theta` calibration.

**Purpose:** cheap gate. If the two BCs disagree on `phi_g` at any `phi_w`,
the candidate is inconsistent with the NBC and Stage10 stops. If they agree,
the candidate is *locally* consistent and Option A (the real angle test) is
worth doing.

## Setup

1D grid `x[0..N-1]`, wall at `x=0`, `dx` uniform. Fix:
- `phi[N-1] = PHI_H` (deep-liquid Dirichlet, far from wall)
- `phi[0] = phi_w` (imposed wall value, swept over `[phi_l, phi_h]`)
- `mu_eq = 0` (bulk coexistence, symmetric double well)

Solve the bulk equilibrium `mu_bulk(phi[i]) - kappa*phi''[i] = 0` for
`i = 1..N-2`, with `phi''[0]` using a ghost `phi_g` (so node 0's equilibrium
also reads the ghost). This gives a well-posed 1D BVP for `phi[1..N-2]` and
`phi_g`, with `phi[0]=phi_w` and `phi[N-1]=PHI_H` fixed.

After convergence, `phi_g` is determined by the bulk equilibrium (node 0's
equation reads it). Then compute the two residuals separately:

```
natural_BC_residual:
    slope_centered = (phi_w - phi_g)/(2*dx)
    R_nbc = kappa * slope_centered + dfs_dphi(h_g, theta)

chemical_potential_candidate_residual:
    lap_wall = phi_g - 2*phi_w + phi[1]
    R_cand = mu_bulk(phi_g) - kappa*lap_wall - mu_wall_target(h_g, theta)
```

But `h_g` and `theta` are not both free. For a *consistency* test we pick the
convention: the NBC defines the wall free-energy slope `dfs_dphi` that the
imposed `phi_w` implies. Specifically, at the converged solution, the NBC
residual is zero when `dfs_dphi = -kappa*slope_centered`. This fixes
`h_g*cos(theta) = kappa*slope_centered / MU_SCALE`. We then ask: does the
candidate residual also vanish for this same `h_g*cos(theta)`?

Equivalently: define
```
mwt_implied = h_g*cos(theta)*MU_SCALE = kappa*slope_centered   (from NBC=0)
```
and test
```
R_cand = mu_bulk(phi_g) - kappa*lap_wall - mwt_implied
```
If `R_cand ~ 0`, the candidate is consistent with the NBC at this `phi_w`.

## Pass / stop criteria

**PASS (all required):**
1. Bulk equilibrium converges (`max|mu_bulk(phi)-kappa*phi''| < 1e-10`) for
   every `phi_w` in a sweep over `[0.05, 0.95]` (interior, away from the bulk
   phases where the double-well is flat).
2. For every converged `phi_w`, `|R_cand| < 1e-8` (candidate consistent with
   NBC to near machine precision).
3. The implied `h_g*cos(theta)` varies smoothly with `phi_w` (no jumps,
   monotone where expected).

**STOP (any triggers):**
- Bulk equilibrium fails to converge for any interior `phi_w`.
- `|R_cand| > 1e-6` for any converged `phi_w` -> candidate inconsistent.
- `h_g*cos(theta)` vs `phi_w` is non-smooth -> numerical pathology.

If STOP triggers, Stage10 halts. No Option A, no V2, no TCLB.

## What "consistency" means physically

The NBC and the candidate are two discretizations of the same continuous
condition. At a 1D equilibrium with an *imposed* `phi_w`, both should
determine the same `phi_g` if they are discretizations of the same physics.
Disagreement means the candidate's `mu_bulk(phi_g)` term introduces a
discretization inconsistency that the NBC (which uses only the gradient) does
not have. That would be a real defect worth stopping on.

Note: this test does NOT distinguish H1 from H2. Even if the candidate is
consistent here, it may still not realize the target angle in 2D (Option A
tests that). Option B only blocks a clearly-wrong candidate from reaching
Option A.
