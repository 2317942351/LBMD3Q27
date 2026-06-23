# DynamicCL Residual-Force Plan (Stage 15) — 2026-06-18

This is the agreed plan after doc 30's audit and the user's correction. It
implements the contact-line dynamic residual as a FORCE on F_total, using the
2026 geometry only to construct θ_app / θ_eq / the contact-line tangent. It
does NOT edit PhaseF, gradPhi, or mu. It does NOT use R_csq or q_f−q_w,target
as a source (both proven wrong in doc 30 / the user's correction).

The core residual:

```text
R_θ = cos(θ_eq) - cos(θ_app)
F_CL = λ · σ/IntWidth · R_θ · I_CL · t_CL      (added to F_total)
```

This vanishes at equilibrium (θ_app = θ_eq) by construction, which is the one
property R_csq-as-force and q_f−q_w,target-source both lack in the right way.

```text
status_label: exploratory_not_validation
scope: plan + design; no wetting-physics source change yet
```

## 0. Why this and not the alternatives (final)

| candidate | equilibrium→0? | bypasses stencil dilution? | edits | verdict |
|---|---|---|---|---|
| R_csq (compact residual) | yes but ≈0 where it matters | yes | n/a | USELESS as drive |
| q_f − q_w,target source | **NO** (q_f≠q_w,target at eq. with normal grad) | yes | phase field | wrong |
| **R_θ = cosθ_eq−cosθ_app force** | **yes** | yes (body force) | F_total only | **DO THIS** |

The compact ghost stays as the main static boundary (14A/14C-prime proved it
healthy). DynamicCL ADDS a force to compensate the measured ~6x tangential
dilution (ghost_frac_tan ≈0.16); it does not replace the ghost.

## 1. Code facts confirmed (for the edits)

Verified at current HEAD:
- `calcGradPhi()` (Dynamics.c.Rt:355-363): when `WallGradMode > 1.5` it
  `return gc` (the corrected gradient), replacing the raw gradient in the
  dynamics. This is the path to DISABLE.
- `stage13_select_phase_for_stencil()` (Dynamics.c.Rt:102-124): the
  `WallGradMode < 1.5` guard at line 106 means Layer-1 active SKIPS ghost
  substitution for boundary neighbours. This must be removed so the ghost is
  always consumed.
- F_total assembly: CollisionMRT ~line 1078, BGK ~line 1369
  (`F_total = F_surf + F_pressure + F_body + F_mu`). DynamicCL is the 5th term.
- `calc_Fs()` (Dynamics.c.Rt ~977-979): non-thermo branch is `F_surf = mu*gradPhi`.

## 2. Stage 15A — resolve the t150 static-drift confound FIRST

Run M=0.1 equilibrium 30/90/150 @ 12000 steps (launched 2026-06-18 11:28).
This is NOT optional before any DynamicCL work, because:

```text
if M=0.1 @12000 ALSO drifts on t150:
  the obtuse drift is a long-time static-pin / phase-field-relaxation effect,
  present at all M. DynamicCL will NOT fix it (R_θ≈0 at equilibrium). Do not
  conflate: DynamicCL fixes CHANGED-angle dynamics, not static drift.
if M=0.1 @12000 holds t150:
  there is a mobility threshold in (0.1,0.2); bisect with M=0.15 equilibrium.
```

No DynamicCL code is written until 15A settles.

## 3. Stage 15B-pre — safety cleanup (no new physics)

Two edits, both removing already-disproven paths:

### 3.1 Disable WallGradMode=2 in calcGradPhi
```c
CudaDeviceFunction vector_t calcGradPhi()
{
    vector_t g = calcGradPhiRaw();
    if (WallGradMode > 0.5) {
        vector_t gc = calcGradPhiBoundaryCorrected(g);
        // diagnostic only: record gc-derived fields if needed, NEVER return gc.
        // WallGradMode=2 write is disabled (doc 24 rule; Layer D is the
        // residual-force path, not gradient replacement).
    }
    return g;
}
```

### 3.2 Always consume WallGhost in the stencil
```c
CudaDeviceFunction real_t stage13_select_phase_for_stencil(...) {
    if (is_boundary > 0.5 && stage13_phase_is_valid(ghost)) {
        PhaseStencilGhostUseCount += 1.0;
        return ghost;
    }
    // ... (rest unchanged)
}
```
i.e. remove the `if (WallGradMode < 1.5)` guard around the ghost branch.

Both are reversible and tested by re-running the compact baseline (must
reproduce 14A/14C-prime within noise).

## 4. Stage 15B — DynamicCLMode=1 shadow (diagnostics, no force)

### 4.1 Settings (Dynamics.R)
```r
AddSetting(name="DynamicCLMode", default=0, comment="0 off,1 shadow,2 add force")
AddSetting(name="DynamicCLCoeff", default=0.0, comment="residual CL force coeff")
AddSetting(name="DynamicCLForceCap", default=0.02, comment="cap in sigma/IntWidth")
AddSetting(name="DynamicCLEpsQ", default=0.05, comment="CL band cutoff eps<q<1-eps")
AddSetting(name="DynamicCLGradMin", default=1e-10, comment="min |gradPhi| for theta_app")
AddSetting(name="DynamicCLCosTol", default=1e-3, comment="no force if |R_theta| small")
AddSetting(name="DynamicCLCosSign", default=1, comment="sign convention, calibrate by eq")
AddSetting(name="DynamicCLForceSign", default=1, comment="global sign, calibrate by decoupled")
AddQuantity DynamicCLCosApp
AddQuantity DynamicCLCosResidual
AddQuantity DynamicCLIndicator
AddQuantity DynamicCLForceMag
```

### 4.2 calcContactLineResidual() (device)
- gate: not wall/solid; near wetting wall (flat = lowerY first); contact-line
  band `DynamicCLEpsQ < q < 1-DynamicCLEpsQ`; `|gradPhi| > DynamicCLGradMin`.
- `n_i = gradPhi/|gradPhi|` (interface normal; sign reliable per 14C-prime Q2).
- `n_w` from `stage9_analytic_wall_normal` (already in the model).
- `cos_app = DynamicCLCosSign * (n_i · n_w)`, clamped to [-1,1].
- `cos_eq = cos(radAngle)`; `R_θ = cos_eq - cos_app`.
- `t_cl = n_i - (n_i·n_w) n_w`, normalized (wall-tangent contact-line direction).
- `I_CL = 4 q (1-q)`.

### 4.3 calcDynamicCLForce()
- `mag = DynamicCLForceSign * DynamicCLCoeff * sigma/IntWidth * R_θ * I_CL`.
- cap at `DynamicCLForceCap * sigma/IntWidth`.
- writes diagnostic fields; returns F_CL.
- In CollisionMRT/BGK: `if (DynamicCLMode > 1.5) F_total += F_CL`. Mode=1 only
  writes diagnostics.

### 4.4 Shadow gate (must pass before any write)
```text
equilibrium 30/90/150:  mean|cos_res| ~ 0 (within DynamicCLCosTol)
                         max|F_CL_candidate| small
decoupled 60→30:         F_CL_candidate direction aligns with footprint motion
decoupled 120→150:       F_CL_candidate direction aligns with footprint motion
F_CL nonzero only in contact-line band (0.05<q<0.95)
sign calibration: DynamicCLCosSign / DynamicCLForceSign set by the above.
```

## 5. Stage 15C — small-coeff write (only after shadow passes)

```text
DynamicCLMode=2, DynamicCLCoeff in {0.0025, 0.005, 0.01}, cap 0.01-0.02*sigma/W
short 4000-8000 step runs to confirm direction, then 12000.
gate:
  60→30 faster than compact-only; 120→150 faster than compact-only
  equilibrium 30/90/150 not degraded
  mass drift not worse than baseline; bulk RMS not worse
  contact-line |U| not blown up
```

## 6. What this does NOT do (honest)

- Does NOT fix t150 static drift (15A is the branch for that; they are separate).
- Does NOT fix bulk RMS.
- Does NOT use WallGradMode=2, R_csq, or q_f−q_w,target as a drive.
- Does NOT touch curved surfaces until flat-wall closure (Stage 15F, later).

## 7. Dependency / ordering

```text
15A  M=0.1 @12000 equilibrium         [running] -> settle t150 confound
15B-pre safety cleanup                 -> after 15A, re-baseline compact
15B  DynamicCLMode=1 shadow            -> after cleanup
15C  DynamicCLMode=2 small-coeff write -> after shadow gate passes
```
