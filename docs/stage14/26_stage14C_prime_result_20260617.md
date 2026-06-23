# Stage 14C-prime Result — Stencil Dilution, F_surf, Spurious Current — 2026-06-17

Diagnostic-only deliverable of Stage 14C-prime (runs in parallel with 14C).
Reads EXISTING flat-wall VTI outputs; no wetting-physics change, no recompile,
no new simulation. It answers the three open questions left by Stage 14A
(see `25_stage14A_result_20260617.md`):

```text
Q1  How much of the solver's gradPhi/mu actually comes from the compact ghost,
    given it enters the 26-point stencil at only 1-3 of 26 neighbours?
Q2  Is F_surf = mu*gradPhi, projected on the contact-line tangent, pointing the
    right way (toward the target angle)?
Q3  Is the spurious velocity (circle-fit RMS grows 50-80x over 12k) at the
    contact line or in the bulk?
```

```text
status_label: exploratory_not_validation
claim_limit:  diagnostic post-processing only
```

## 0. Headline

```text
Q1  Stencil dilution is REAL and ~as predicted by doc 23.
    On the contact-line band, only ~16% of the TANGENTIAL gradient magnitude
    is sourced from the wall ghost (mean 0.15-0.18, p95 0.17-0.36 across all
    cases and timesteps). The tangent direction is the one that drives contact-
    line motion. The ghost's normal contribution is large (it sets the angle)
    but the tangential lever is weak.

Q2  F_surf DOES point the right way. Cross-validated against footprint radius:
    60->30 expands footprint (25.5 -> 27.6 cells) with Fs_radial > 0;
    120->150 shrinks footprint (15.8 -> 13.5 cells) with Fs_radial < 0.
    Both match the observed theta motion. The drive is correct in sign.

Q3  Spurious current is BULK, not contact-line.
    |U| at the contact-line band is 3-10x SMALLER than in the bulk interface
    band. The growing RMS comes from the bulk interface (surface-tension /
    phase-field), not from the wetting drive.
```

Net: the compact ghost is healthy (14A) and the force it produces is correctly
directed (Q2), but its tangential lever into gradPhi is diluted ~6x by the
26-point stencil (Q1). This is the leading explanation for the slow decoupled
response and is exactly the scenario in which a Layer-D residual force would
help. Mobility (14C) remains worth measuring but is now secondary.

## 1. Method and reproducibility

New diagnostic script (does not modify any existing file):
`lbm2026/scripts/stage13/stage14c_prime_dilution_audit.py`

Reproduces the solver stencil EXACTLY because the run used no `OutFlow` option,
so `calcGradPhi` / `calcMu` take the plain else-branch:
```text
gradPhi = IsotropicGrad(STAGE13_PHASE_FOR_STENCIL)
lpPhi   = myLaplace(STAGE13_PHASE_FOR_STENCIL)
mu      = 4*(12*sigma/W)*(C-l)*(C-h)*(C-0.5(l+h)) - (1.5*sigma*W)*lpPhi
```
Stencils (verified against `model.R` `IsotropicGrad`/`myLaplace`):
```text
grad component:  axial neighbour coef 16 (/72), face-diag 4 (/72), body-diag 1 (/72)
laplacian:       axial 16, face 4, body 1, center -152, /36
```
`STAGE13_PHASE_FOR_STENCIL(dx,dy,dz)` is reproduced neighbour-by-neighbour:
boundary neighbour with valid ghost -> `WallGhost`; else valid `PhaseField`;
else ghost fallback; else center midpoint. This lets the audit separate each
neighbour's contribution into "sourced from ghost" vs "sourced from real fluid".

VTI fields used (all present in existing outputs): `PhaseField, WallGhost,
IsItBoundary, U, LocalRadAngle`. sigma/IntWidth from case metadata.

Run on server against existing VTI:
```text
python3 /home/yuan/stage14c_prime_dilution_audit.py <root> --steps last
python3 /home/yuan/stage14c_prime_dilution_audit.py <root> --steps 0,4000,8000,12000
```
Outputs: `/home/yuan/stage14c_prime_audit_last.json`,
`/home/yuan/stage14c_prime_audit_traj.json`.
Driver: `lbm2026/scripts/stage13/_stage14c_remote_driver.sh`.

## 2. Q1 result — stencil dilution (the robust metric is the tangent fraction)

All values on the **contact-line band** (boundary-fluid nodes with
0.05 <= q <= 0.95), final timestep.

| case | target | ghost_frac_tan mean | p95 | ghost_frac_total mean | ghost_frac_norm mean |
|---|---|---|---|---|---|
| retry12k_60to30 | 30 | **0.183** | 0.364 | 1.72 | 1.97 |
| retry12k_120to150 | 150 | **0.159** | 0.342 | 0.88 | 1.01 |
| eq1500_t30 | 30 | **0.172** | 0.354 | 1.82 | 2.00 |
| eq1500_t90 | 90 | **0.167** | 0.168 | 1.26 | 38.7 |
| eq1500_t150 | 150 | **0.154** | 0.353 | 0.84 | 0.96 |

### Interpretation

- **`ghost_frac_tan` is the trustworthy metric.** It is bounded (0-0.36) and
  nearly constant across all cases (mean 0.15-0.18). It says: in the
  tangential direction (the one that moves the contact line), only ~16% of the
  gradient magnitude comes from the ghost. The other ~84% comes from the
  real-fluid neighbours. The contact-angle signal carried by the ghost is
  diluted roughly 6x before it reaches F_surf's tangential component.

- **`ghost_frac_total` and `ghost_frac_norm` are >1 and NOT trustworthy.**
  They are `|part|/|total|`, which blows up where `|total|` ~ 0 (equilibrium:
  the normal gradient and mu nearly cancel). These numbers are reported for
  honesty but should NOT be read as "the ghost dominates." They are an artifact
  of the unbounded ratio. The mu_ghost_frac (30-312) is the same artifact and
  is likewise not interpreted.

- The tangential dilution is stable over time (trajectory shows 0.149-0.183 at
  steps 0/4k/8k/12k for the same case), so it is a structural property of the
  flat-wall stencil geometry, not a transient.

### Why this matches doc 23's argument

On a flat wall the only ghost-carrying neighbour of a boundary-fluid node is
the wall cell directly below (dy=-1). That single neighbour enters the
IsotropicGrad y-component with weight 16/72, and it enters the x/z components
only through the body/face diagonals at weight 1/72 or 4/72. So the ghost's
weight in the tangential (x,z) gradient is small by construction. The measured
~16% is consistent with "1-3 of 26 neighbours."

## 3. Q2 result — F_surf direction is correct (cross-validated)

`Fs_radial` = F_surf projected onto the radial-outward direction in the wall
plane (+ = outward = expands footprint). Compared with the measured footprint
radius (max radial extent of liquid q>0.5 at the wall layer):

| case | step | footprint radius | Fs_radial mean | theta motion |
|---|---|---|---|---|
| 60->30 | 0 | 25.50 | +2.38e-06 | 60.0 |
| 60->30 | 12000 | **27.59** | +1.52e-07 | 58.0 |
| 120->150 | 0 | 15.81 | -4.90e-06 | 120.0 |
| 120->150 | 12000 | **13.45** | -1.17e-06 | 125.8 |

```text
60->30:   footprint EXPANDS (25.5 -> 27.6), Fs_radial > 0 (outward).  MATCH.
120->150: footprint SHRINKS (15.8 -> 13.5), Fs_radial < 0 (inward).   MATCH.
```

**The surface-tension force is pushing the contact line the right way in both
cases.** The drive sign is correct. The slowness is not a sign error; it is a
magnitude/dilution problem (Q1) compounded by mobility (14C).

Note: the force magnitude decays over time (60->30: 2.4e-6 -> 1.5e-7) as the
droplet approaches equilibrium, which is physically correct (residual shrinks).

## 4. Q3 result — spurious current is bulk, not contact-line

|U| mean by region, final timestep:

| case | clband mean | clband max | bulk_if mean | all max |
|---|---|---|---|---|
| retry12k_60to30 | 2.7e-06 | 5.1e-06 | **2.6e-05** | 2.9e-05 |
| retry12k_120to150 | 1.9e-05 | 5.0e-05 | **5.9e-05** | 8.8e-05 |

```text
Bulk-interface |U| is 3-10x the contact-line |U|.
The circle-fit RMS growth (50-80x over 12k) is therefore a BULK interface
phenomenon (surface-tension-force / phase-field / pressure-force balance),
NOT a wetting-drive defect at the contact line.
```

This is important for the decision tree: a Layer-D residual force added at the
contact line will NOT fix the bulk RMS. If RMS must be controlled, it is a
phase-field / force-coupling stability issue (sigma, IntWidth, ForceFixedTol,
F_surf vs F_pressure balance), separate from the wetting drive.

## 5. Decision-tree verdict

Applying the tree the user specified:

```text
Q1 ghost_frac_tan ~0.16 (low) AND
Q2 force sign correct AND
Q3 spurious current is bulk not contact-line
  =>  Situation 3 (stencil dilution confirmed; force correct but weak)
  =>  14D (Layer D residual contact-line force) is WARRANTED after 14C,
      as a local compensation for the diluted tangential drive.
      It is NOT a replacement for the compact ghost and NOT a bulk fix.
```

Mobility (14C) should still be run first because it is cheap (case-param
sweep, no code change) and may partially address the speed without any new
force layer. But Q1 strongly suggests mobility alone will not fully close the
gap, because the drive is structurally diluted regardless of M.

The bulk RMS (Q3) is a separate, parallel concern: if it must be controlled
for later publication/dynamic-impact work, it needs its own diagnostic
(F_surf vs F_pressure balance, force-iteration convergence) — do not bundle it
into 14D.

## 6. Updated stage ordering

```text
14A   compact reject audit                         DONE (doc 25)
14B   fix compact solve rejection                  CANCELLED (doc 25)
14C-prime  stencil-dilution / F_surf / current     DONE (this doc)
14C   mobility M sweep {0.1,0.2,0.3,0.4}           NEXT (case-param only)
       gate: does dtheta/dt rise with M without RMS/mass blow-up?
14D   Layer D residual contact-line force          LIKELY NEEDED (per Q1)
       shadow first, sign-calibrated by flat-wall 30/90/150,
       then small-coeff write only if 14C leaves a gap.
14E   Layer C Ju (residual-form)                   last resort
14F   curved surfaces                              after flat-wall closure
(separate) bulk RMS / force-balance diagnostic     parallel, do not bundle
```

## 7. Honest caveats on this audit

1. The `ghost_frac_total`, `ghost_frac_norm`, and `mu_ghost_frac` metrics are
   unbounded ratios (`|part|/|total|`) and exceed 1 wherever the denominator
   is near zero (equilibrium, normal-direction cancellation). They are NOT
   interpreted as dilution. Only `ghost_frac_tan` (bounded, 0-0.36) is used
   for the Q1 conclusion.

2. `mu` reconstruction assumes `PhaseField_l=0, PhaseField_h=1` (TCLB default
   for these flat-wall cases; not explicitly in the case metadata). If a case
   used non-unit phase range, the absolute mu magnitude shifts but the
   ghost-fraction (a ratio) is unaffected.

3. `Fs_radial` sign convention: + = radially outward in the wall plane. The
   "correct direction" was cross-validated against measured footprint-radius
   change, not assumed from the angle target.

4. This is post-processing of already-run cases; it cannot prove what a higher
   M or a Layer-D force will do. It only constrains the hypotheses.
