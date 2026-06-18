# Code Audit — Does the Geometric Contact-Angle Relation Enter as a Residual? — 2026-06-18

This answers the user's question: **does the 2026-paper geometric contact-angle
relation enter the solver as a residual drive, or only as post-processing?**
And: **can it be put into the live dynamics path instead of the diluted ghost
substitution?**

All line references are to
`repo/third_party/.../d3q27_pf_velocity/{Boundary.c.Rt, Dynamics.c.Rt}`.

```text
status_label: exploratory_not_validation
scope: code audit + feasibility analysis; no code changed
```

## 1. What the 2026 geometric relation IS (the target physics)

The compact-stencil method encodes the contact-angle condition as a relation
between the wall ghost phase `q_s`, the fluid-side interpolated phase `q_f`,
and the signed distances `d_s` (wall→ghost) and `d_f` (wall→fluid probe):

```text
∇φ · n_w  =  -(4/W) cos(θ_eq) q_w (1 - q_w)            ... (geometric contact angle)
q_w       =  (d_s q_f + d_f q_s) / D ,   D = d_s + d_f  ... (linear interpolation at wall)
```

Eliminating q_w gives a quadratic `a q_s^2 + b q_s + c = 0` solved in
`stage13_fill_compact_stencil_solution` (Boundary.c.Rt:795-849). This is
**exactly the 2026 paper's relation**. The residual form is:

```text
R_csq(q_s) = (q_f - q_s)/D + (4/W) q_w(1-q_w) cos(θ_eq)      ... (Boundary.c.Rt:617-626)
```

`R_csq = 0` at the geometric contact angle. This is a real, signed residual
that measures how far the wall phase is from satisfying the contact-angle
geometry. **It is computed on every boundary node, every timestep.**

## 2. Where does R_csq / q_s currently go? (the actual data flow)

Tracing every consumer of the compact solve:

```text
stage13_fill_compact_stencil_solution()        [Boundary.c.Rt:775]
  computes: q_s (raw + bounded), q_w, R_csq (WallCSQResidual),
            WallCSQAppliedResidual, discriminant, root_choice
        |
        +--> stage13_compact_solution_wall_ghost()  [573]
        |       returns q_s_bounded as the WallGhost value
        |       (this is the ONLY entry into dynamics)
        |
        +--> stage13_compact_solution_can_write()   [556]
        |       gates the ghost write on R_csq and bounded-delta
        |       (R_csq used only as a BOOLEAN GATE here, not a force)
        |
        +--> WallCSQ* diagnostic fields              [written to VTI]
                (R_csq, q_s, discriminant, etc. — POST-PROCESSING ONLY)
```

Then the ghost enters the dynamics through exactly one channel:

```text
STAGE13_PHASE_FOR_STENCIL(dx,dy,dz)            [Dynamics.c.Rt:126-127]
  = stage13_select_phase_for_stencil(PhaseF, IsBoundary, WallGhost, center)
  --> returns WallGhost for boundary neighbours, PhaseF otherwise
        |
        v
  gradPhi = IsotropicGrad(STAGE13_PHASE_FOR_STENCIL)   [Dynamics.c.Rt:317-329]
  lapPhi  = myLaplace(STAGE13_PHASE_FOR_STENCIL)
        |
        v
  mu = 4βφ(φ-1)(φ-½) - κ lapPhi
  F_surf = mu * gradPhi
  F_total = F_surf + F_pressure + F_body + F_mu
```

## 3. The verdict: the geometric relation enters dynamics INDIRECTLY and DILUTED

```text
The 2026 relation IS solved live (every timestep, every boundary node).
BUT it enters the dynamics ONLY through q_s -> WallGhost -> stencil substitution.
The residual R_csq itself is NOT used as a force. It is used only as a write-gate
and as a diagnostic field for post-processing.
```

And Stage 14C-prime measured the cost of that indirect channel: the ghost
substitution enters the 26-point isotropic gradient at only the boundary
neighbours (1-3 of 26), so on the contact-line band the **tangential**
contribution of the ghost to gradPhi is only **~16%** (ghost_frac_tan mean
0.15-0.18). The geometric contact-angle signal is correct but arrives at
`F_surf` diluted ~6x in the tangential direction — the direction that drives
contact-line motion.

So the current architecture is:

```text
geometric relation -> q_s (scalar) -> ghost substitution -> diluted gradPhi -> F_surf
                \-> R_csq  -> gate + diagnostic  (NOT a force)
```

## 4. The opportunity: put R_csq directly into the dynamics as a force

The user's question is exactly right: the geometric relation is computed
correctly, but it is wired into the dynamics through a lossy channel. The
natural object to promote into a live force is the **residual between the
current near-wall phase field and the contact-angle target**, because:

1. The compact geometry is already solved live (q_s every timestep).
2. A residual is signed — it points the way the contact line should move.
3. A correctly-defined residual vanishes at equilibrium.
4. It is local to the contact-line geometry, not bulk.

The 14C-prime result (ghost_frac_tan ~0.16) is the evidence that the current
ghost channel under-delivers the tangential drive. A direct residual force
would NOT be subject to stencil dilution because it is applied as a body force,
not through the 26-point stencil.

### 4a. CRITICAL CORRECTION — which residual?

A naive first thought is "use `WallCSQAppliedResidual` as the drive." **This is
wrong**, and the correction matters, so it is stated explicitly:

```text
stage13_fill_compact_stencil_solution solves a·q_s² + b·q_s + c = 0 such that
R_csq(q_s) = 0. On every path=30 node (WallCSQValid=1) the solver FOUND THE
ROOT, so WallCSQResidual (raw) is ~0 by construction. WallCSQAppliedResidual
may be small-but-nonzero only due to bound clamping, and the can_write gate
already forces |WallCSQAppliedResidual| <= tol on written ghosts.
```

So `R_csq` measures *"does the wall ghost value q_s satisfy the geometric
relation?"* — and on the contact-line band the answer is always yes (the
solver guaranteed it). **Promoting R_csq into a force would add ~zero drive
on exactly the nodes that matter**, because the ghost there is already
geometrically correct. The dilution happens AFTER q_s, in the 26-point
stencil; it is not captured by R_csq.

(Verification attempt: the decoupled step-12000 VTI that would confirm
|WallCSQAppliedResidual|≈0 on path=30 were lost in the 14C-2 disk cleanup.
But the conclusion does not depend on the data: it follows from
R_csq(q_s)=0 at the solver's own root.)

### 4b. The residual that DOES carry the dynamic signal

The drive must come from the **momentum/phase imbalance at the contact line**,
not the compact-solve residual. The correct residual is the unbalanced-Young /
apparent-vs-equilibrium form:

```text
R_θ = cos(θ_eq) - cos(θ_app)
```

where θ_app is the *measured* apparent angle from the current near-wall
gradient (n_w·∇φ / |∇φ|), NOT the geometrically-imposed angle. This is what
doc 24/27 Layer D specified. The catch, flagged in doc 26 §7 caveat 5: θ_app
computed from gradPhi inherits the ~6x tangential dilution (ghost_frac_tan
0.16), so its *magnitude* is noisy — though its *sign* is still reliable
(14C-prime Q2 showed the sign is correct).

So the honest feasibility picture is:

```text
R_csq (compact-solve residual)        -> ~0 on path=30, USELESS as a drive.
R_θ (apparent-vs-equilibrium angle)   -> correct sign, noisy magnitude,
                                          THIS is the viable residual drive.
```

### 4c. A better idea — drive the PHASE FIELD, not the momentum

There is a third option that uses the geometric relation more directly and
sidesteps the θ_app noise: instead of a momentum force, add a **chemical-
potential / phase source** at the wall that nudges q_w toward the contact-angle
value the compact solve already computed. The compact solve gives the *target*
q_w (= q_s_bounded, satisfying R_csq=0). The *current* q at the wall-fluid
node is q_f. The mismatch is:

```text
R_phase = q_f - q_w,target        (q_w,target = the value R_csq=0 demands)
```

This residual is NOT ~0 on the contact-line band, because q_f is the evolving
field and only the GHOST was set to satisfy the relation; the fluid cell's own
phase lags. Feeding R_phase back as a small phase source (or equivalently a mu
perturbation) would drive the fluid phase toward the geometric target without
going through the diluted gradient stencil. This is closer in spirit to the
2026 paper's intent than a Young-stress force. It is also riskier (it edits
the phase field directly), so it would need a shadow-first mode.

```text
Three candidate residuals, ranked by how directly they reuse the 2026 geometry:
  R_phase = q_f - q_w,target        -- reuses compact solve's target; bypasses
                                      stencil dilution; edits phase (risky)
  R_θ     = cos(θ_eq) - cos(θ_app)  -- Young-stress form; sign-correct but
                                      magnitude inherits gradPhi dilution
  R_csq   = compact-solve residual  -- ~0 where it matters; USELESS as drive
```

## 5. Concrete feasibility: a `calcDynamicCLForce()` from the CORRECT residual

Given §4b/4c, the viable implementations are R_θ (Young-stress, doc 24/27) or
R_phase (phase-source, §4c). The R_θ form is sketched in doc 24 §4 Step 3-4
and not repeated here. The R_phase form (more direct use of the 2026 geometry):

```c
CudaDeviceFunction void calcDynamicCLPhaseSource(real_t *src_out)
{
    *src_out = 0.0;
    if (DynamicCLMode < 0.5) return;
    // q_w,target already satisfies the 2026 relation (R_csq=0); q_f is the
    // current fluid cell phase. The mismatch is the genuine dynamic residual.
    real_t qf = WallCSQQf(0,0,0);
    real_t qw_target = WallCSQQw(0,0,0);   // = (d_s q_f + d_f q_s)/D at the root
    if (!isfinite(qf) || !isfinite(qw_target)) return;
    if (qf < DynamicCLEpsQ || qf > 1.0 - DynamicCLEpsQ) return;
    real_t R_phase = qf - qw_target;
    real_t I_cl = 4.0 * qf * (1.0 - qf);   // contact-line indicator
    *src_out = DynamicCLForceSign * DynamicCLCoeff * R_phase * I_cl;
}
```

This would enter the phase-field equation (not momentum), nudging q_f toward
the geometry's target. It bypasses the 26-point stencil dilution entirely
because it acts on the phase field at the cell, not through gradPhi. The same
gate discipline applies: `DynamicCLMode=1` shadow first (verify R_phase->0 at
equilibrium, correct sign in motion direction, contact-line-band-only), then
small-coeff write.

### Why each option does/doesn't reuse the 2026 geometry

| formulation | reuses compact solve? | bypasses stencil dilution? | edits | equilibrium->0? |
|---|---|---|---|---|
| R_csq (compact residual) | yes | yes | n/a | yes — but **~0 where it matters** |
| R_phase = q_f − q_w,target | **yes** (uses q_w,target) | **yes** | phase field | yes |
| R_θ = cos θ_eq − cos θ_app | no (recomputes θ_app from diluted gradPhi) | **no** (magnitude diluted) | momentum | only if θ_app clean |

R_phase is the option that most directly puts the 2026 geometric relation into
the live dynamics at the right place: it takes the relation's *output*
(q_w,target) and feeds the *mismatch with the evolving field* back as a source.

## 6. What this does NOT solve (be honest)

1. **The t150 obtuse drift (14C-2/2b).** That drift occurs at equilibrium where
   `R_csq ≈ 0` and `WettingPathId = 0` (ghost idle, doc 29 §4). A residual force
   that is ∝ R_csq will also be ≈0 there. So **Layer D will NOT fix the t150
   equilibrium drift** — that drift is a static-pin / phase-field issue, not a
   dynamic-drive issue. (This is consistent: Layer D adds drive to make a
   *moving* line move faster; it cannot pin a *static* line.)

2. **The bulk RMS (14C-prime Q3).** A contact-line-local force does not touch
   the bulk interface.

3. **The contact-line speed at low M.** If 14C-3 shows M is the binding limiter
   even after the dilution is compensated, Layer D may be unnecessary. But
   14C-prime's ghost_frac_tan=0.16 strongly suggests dilution IS binding, so
   Layer D is the principled fix for *speed*, not for *pinning*.

## 7. Recommendation / ordering

```text
The geometric contact-angle relation currently enters dynamics ONLY via the
diluted ghost channel. Promoting R_csq into a live force is feasible, low-risk
(reuses existing compute, vanishes at equilibrium), and directly targets the
measured ~6x tangential dilution.

Order:
  1. Resolve the t150 pinning question first (14C-2c-CONFIRM: M=0.1 @ 12000).
     Layer D will not fix it; do not conflate the two.
  2. Run 14C-3 (decoupled long run at the equilibrium-safe M).
  3. If decoupled still plateaus short of target (expected, given dilution),
     implement Layer D as calcDynamicCLForce(R_csq) above:
       - DynamicCLMode=1 shadow: verify R_csq->0 at equilibrium, correct sign
         in motion direction, only in contact-line band.
       - DynamicCLMode=2 small-coeff write.
  4. Keep WallGradMode <= 1 (never use the corrected-gradient write to bypass
     the compact ghost — doc 24 rule). Layer D ADDS to the compact ghost; it
     does not replace it.
```

## 8. One-line answer to the user's question

```text
The 2026 geometric relation IS solved live (q_s every timestep) and the ghost
is geometrically correct — but it enters the dynamics ONLY through a ~6x-diluted
stencil substitution. The residual R_csq the solver computes is ~0 wherever
the ghost is written (it found the root), so R_csq itself is USELESS as a drive.

The relation CAN be put into the live dynamics at the right place, but NOT via
R_csq — via the mismatch between the evolving fluid phase and the relation's
target: R_phase = q_f - q_w,target (a phase source that bypasses the stencil
dilution), OR via the Young-stress R_θ = cos θ_eq - cos θ_app (momentum force,
correct sign but diluted magnitude). The R_phase form most directly reuses the
2026 geometry's output. This is feasible and targets the measured dilution.
It will NOT fix the t150 static drift (that is a separate pinning problem).
```
