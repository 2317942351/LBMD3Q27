# Stage10 V1 Option B — FAIL (decisive negative result)

Date: 2026-06-14
Authorization: Option B (then A if B passes). B FAILED. Stage10 STOPS.

## Result

Option B (1D imposed-wall-value consistency test) FAILED.

All imposed wall values `phi_w` in [0.05, 0.95] converged to bulk equilibrium,
but the candidate chemical-potential residual `R_cand` was ~7 orders of
magnitude above the 1e-8 pass threshold:

```
max|R_cand| over phi_w sweep = 3.4e-5    (threshold 1e-8)
```

## Root cause (decisive)

The diagnostic (`v1b_diag.py`) shows the mechanism cleanly. At every converged
`phi_w`:

```
mu_bulk(phi_g)  ≈  kappa * lap_wall       (both near zero, bulk equilibrium)
=>  mu_bulk(phi_g) - kappa*lap_wall  ≈  0
```

The candidate BC demands `mu_bulk(phi_g) - kappa*lap_wall = mwt_implied`, where
`mwt_implied` is the (nonzero) wall target implied by the natural BC. So:

```
R_cand = mu_bulk(phi_g) - kappa*lap_wall - mwt  ≈  0 - mwt  =  -mwt
```

This is exactly what the data shows (R_cand/mwt ranges -1.13 to -0.91, NOT
constant -1.0, so it is not a sign error — it is the bulk-equilibrium
constraint forcing mu(phi_g) ≈ 0 while the candidate demands mu(phi_g) = mwt).

## What this means physically

The candidate chemical-potential wall BC
`mu(phi_g)|_wall = mu_wall_target` is **fundamentally incompatible** with the
bulk chemical-potential equilibrium `mu = const` everywhere in the fluid,
*unless* `mu_wall_target = mu_eq` (which for a symmetric double well is 0,
giving only theta=90).

The ghost node `phi_g` is in the fluid domain (it is read by the Laplacian
stencil of the wall-adjacent fluid node). The bulk equilibrium therefore
constrains `mu(phi_g) ≈ mu_eq = 0`. Imposing `mu(phi_g) = mwt != 0` at the same
node over-determines the system. The only self-consistent value is `mwt = 0`,
i.e. theta=90.

This is the SAME finding as the original V1 (theta!=90 non-convergence), now
confirmed by an independent method (imposed-wall-value) that does not suffer
from the original V1's 1D structural degeneracy. The conclusion is robust.

## Is this a flaw in the candidate, or in my derivation?

It is a flaw in the candidate **as I formulated it**. The error in the
design doc (section 1.2) was treating the ghost node as a place where the
chemical potential can be independently set. In reality, the ghost is part of
the fluid Laplacian stencil, so its chemical potential is tied to the bulk
equilibrium. The chemical-potential form of the wall BC must be applied at the
**wall surface** (a boundary, not a fluid node), not at the ghost node.

The CORRECT formulation (which I did NOT implement and which is NOT authorized)
would be to apply the natural BC `kappa * (d phi/d n_w) + d f_s/d phi = 0`
directly as a one-sided derivative at the wall-adjacent fluid node, WITHOUT
introducing a ghost whose chemical potential is independently constrained.
That is essentially what the upstream Briant/tan formulas do (they impose the
gradient condition, not a chemical-potential condition). The implication is
that the chemical-potential candidate, as a *ghost-value* BC, is the wrong
abstraction.

## Honest verdict

Stage10's candidate BC (chemical-potential form imposed at the ghost node) is
**internally inconsistent** with bulk equilibrium for theta != 90. It cannot
be salvaged as formulated. Per the authorization rule:

- Option B FAILED -> Stage10 STOPS.
- Option A is NOT done.
- V2 is NOT redefined.
- No TCLB code is written.

## What this means for the original problem (cot(theta) contact-angle error)

The stage9 audit already established that the cot(theta) error is model-
intrinsic (present in upstream, identical for Briant/tan/implicit-candidate).
Stage10's failure to find a working chemical-potential candidate does NOT
make the error worse — it confirms that the error is not fixable by a
ghost-node chemical-potential BC. The remaining levers for reducing the
cot(theta) error are:

1. Reduce IntWidth (the O(W/R) scaling). Untested.
2. Increase droplet radius. Untested.
3. A wall BC formulated at the wall surface (not the ghost), e.g. a proper
   one-sided natural-BC discretization. This is NOT the stage10 candidate and
   is NOT authorized.

Stage10 is reported as a negative result. The cot(theta) error remains at
~5.6 deg for theta=30, and is model-intrinsic per the stage9 audit.
