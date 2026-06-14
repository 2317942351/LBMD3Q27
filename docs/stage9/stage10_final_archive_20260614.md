# Stage10 — Final Archive (rejected)

Date: 2026-06-14
Status: **REJECTED**. No further Stage10 work authorized.

## Verdict (strict wording, per reviewer 2026-06-14)

**Stage10 ghost-node chemical-potential wall BC: REJECTED.**

### What is rejected (and only this)

The specific candidate BC that imposes a chemical-potential target at the
**ghost node**:

```
find phi_g  such that  mu(phi_g)|_wall = mu_wall_target
i.e.  mu_bulk(phi_g) - kappa * lap_wall = mu_wall_target
```

This candidate is rejected because the ghost node is part of the fluid
Laplacian stencil, so its chemical potential is already constrained by the
bulk equilibrium `mu = const`. Imposing a second, independent
chemical-potential condition at the same node over-determines the system.
The only self-consistent value is `mu_wall_target = mu_eq = 0`, giving only
theta=90.

Evidence (two independent methods):
- Original V1 (NBC-imposed 1D equilibrium): non-convergence for theta != 90.
- Option B (imposed-wall-value consistency): `max|R_cand| = 3.4e-5` for theta
  implied across phi_w in [0.05, 0.95], with `R_cand/mwt` in [-1.13, -0.91]
  (not constant -1, so not a sign error).

### Consequence of rejection

- No Option A (2D sessile-drop equilibrium).
- No V2 (Newton manufactured solution).
- No TCLB implementation of this candidate.
- No production claim based on this candidate.

### What is NOT claimed (strict wording boundary)

This rejection does **NOT** establish that:

- "all wall BCs are unfixable" — NOT established.
- "wall-surface natural BC cannot fix the error" — NOT tested.
- "the cot(theta) contact-angle error is unfixable" — NOT established.

What IS established:

- The **ghost-node chemical-potential** form specifically cannot work.
- Whether a **wall-surface** natural-BC discretization (one-sided derivative
  at the wall-adjacent fluid node, no ghost chemical-potential constraint)
  would work is **untested** and is a distinct question.
- Whether the cot(theta) error is dominated by finite interface width
  (W/R scaling) vs by the wall BC formula is **untested** and is the subject
  of Stage11.

## Why this is a valid scientific outcome

The negative result is informative: it rules out a class of BC formulations
(those imposing chemical-potential conditions at ghost nodes) and clarifies
that any future wall-BC work must apply the natural BC at the wall surface,
not at a ghost. It does not waste the work — it narrows the design space.

## Pointers

- Design (superseded for the candidate, but the continuous NBC derivation
  remains valid): `stage10_implicit_wall_bc_design_20260614.md`
- V1 original status: `stage10_v1_status_20260614.md`
- V1 Option B status: `stage10_v1b_status_20260614.md`
- Diagnostic scripts: `scripts/stage10/v1b_imposed_wall.py`,
  `scripts/stage10/v1b_diagnostic.py`, `scripts/stage10/v1_1d_equilibrium.py`

## Next stage

Stage11: W/R convergence audit. Decisive question — is the theta=30 -> 35.65
deg error dominated by finite interface width (W/R scaling)? If yes, pivot to
IntWidth/mesh/radius selection. If no, re-authorize wall-surface BC design.
