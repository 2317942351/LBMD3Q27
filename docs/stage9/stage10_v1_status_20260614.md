# Stage10 V1 Status — HONEST, partial result

Date: 2026-06-14
Authorization: V1/V2 only (per reviewer).

## What V1 was supposed to do

Per the corrected design (`stage10_implicit_wall_bc_design_20260614.md`), V1
solves the 1D Cahn-Hilliard equilibrium on `[0, L]` with the candidate wall
BC, sweeps `h_g`/theta, and verifies that BOTH the natural-BC residual and the
chemical-potential-candidate residual converge to ~0, establishing that the
candidate is consistent with the exact NBC.

## What V1 actually found

### Positive: theta=90 consistency (machine precision)

At theta=90 (neutral, `dfs_dphi=0`), the solver converges and both residuals
are essentially zero:

```
natural_BC_residual          = 1.79e-25
chemical_potential_residual  = 2.01e-16
```

This confirms that **at the neutral limit, the candidate chemical-potential
form is consistent with the exact NBC to machine precision**. This is a real,
narrow positive result.

### Negative: theta != 90 does NOT converge (structural 1D failure)

For theta = 30/45/60/75/105/120/135/150 the Newton solver does not converge,
regardless of `h_g` (scanned h_g from 1.0 down to 0.01 — all fail).

Newton trace for theta=30 (h_g=1.0) shows the mechanism:

```
iter 0: NBC_resid=-8.66e-05, phi[0]=0.02,  phi_g=0.02
iter 2: NBC_resid=-1.7e-14,  phi[0]=-0.08, phi_g=-0.16   <- NBC satisfied
iter 3+: rmax stuck at 1.3e-5 in the BULK equilibrium equation
```

The NBC is satisfied, but to produce the wall slope it demands, the solver
pushes `phi[0]` and `phi_g` **negative** (below `phi_l=0`), which breaks the
bulk equilibrium (`mu_bulk` of a negative phi is far from `mu_eq=0`).

### Root cause: the 1D test is structurally degenerate for theta != 90

A 1D wall-normal profile has no horizontal interface, so there is no contact
line and no geometric contact angle. The NBC `kappa*slope = -dfs_dphi` imposes
a wall slope, but in 1D that slope just sets the position of the single
tanh interface, which the bulk coexistence (`mu_eq=0`) wants at a specific
location. These two constraints are compatible only when the NBC demands zero
slope (theta=90). For theta != 90 they fight, and the solver cannot find a
physical solution.

**This is a flaw in the V1 test design, not (yet) a flaw in the candidate BC.**
The 1D test cannot validate the candidate for non-neutral angles. A real
contact-angle test requires a 2D geometry (a contact line where a horizontal
interface meets the wall).

## What this means

V1 as designed cannot pass for theta != 90, by construction. The single
positive data point (theta=90 consistency) is real but narrow. It does NOT
establish that the candidate realizes a specified non-90 contact angle.

## Required V1 redesign (proposed, NOT executed without re-authorization)

Two options to make V1 meaningful for theta != 90:

**Option A: 2D static sessile drop, no LBM (Python finite-difference
Cahn-Hilliard equilibrium solver).** Solve the 2D equilibrium
`mu = const` on a rectangle with the candidate wall BC on the bottom wall and
a fixed droplet region, relax to equilibrium, measure the geometric contact
angle. This is the proper test but is substantially more code (2D nonlinear
elliptic solve).

**Option B: reformulate 1D as an imposed-wall-value problem.** Instead of
imposing the NBC slope and solving for the profile, impose `phi[0] = phi_w`
(for a sweep of phi_w) and solve the bulk equilibrium; then check whether the
candidate chemical-potential residual and the NBC residual agree at that
`phi_w`. This tests candidate-vs-NBC consistency without requiring a contact
angle, and works in 1D. It does not produce the `h_g <-> theta` calibration
(that still needs 2D), but it does answer the V1 consistency question.

## Honest verdict

V1 has NOT passed. One narrow positive (theta=90 machine-precision
consistency) and a structural failure for theta != 90 that is traced to the
test design, not the BC. Per the reviewer's rule, Stage10 does NOT proceed to
V2 or to TCLB code on this basis.

I am requesting re-authorization for one of the V1 redesign options (A or B)
above before writing more code.
