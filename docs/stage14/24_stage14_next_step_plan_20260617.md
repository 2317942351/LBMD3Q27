# Stage 14 Next-Step Plan — 2026-06-17

> **SUPERSEDED in part by `25_stage14A_result_20260617.md`.**
> Stage 14A ran and overturned the §2.4-2.5 / §3 "compact solve rejected on
> 25-81% of the target wall" premise: those rejections are entirely in the
> pure-phase wall region; the contact-line band (0.05 <= q_f <= 0.95) is
> **100% path=30, csq_valid=1** on every case. Stage 14B is therefore
> **cancelled** and 14C promoted to next. See doc 25 §5 for the revised
> ordering. The gate discipline, claim policy, and "never use WallGradMode=2
> to bypass" rules below remain in force.

This document is the next-step guidance produced after a full re-read of the
current project. It supersedes the *ordering* of `23_contact_line_drive_repair_plan_20260616.md`
(whose Layer 1/2/3 ordering it corrects with runtime evidence) while keeping
the `21_compact_stencil_authority_plan_v4` gate discipline intact.

Project status remains:

```text
exploratory_not_validation
```

Read this file together with:

```text
21_compact_stencil_authority_plan_v4_20260616.md   (gate discipline, claim policy)
22_current_code_audit_20260616.md                  (source-level state, R1-R4)
23_contact_line_drive_repair_plan_20260616.md      (Wang/Ju/Brown literature mapping)
SCIENTIFIC_METHOD_NOTE.md                          (why compact-stencil matters)
```

---

## 0. How this plan was produced (method)

Every quantitative claim below comes from reading the actual source and the
actual runtime artifacts on disk, not from the prose of the prior handoffs:

```text
Source audited (line-level):
  repo/third_party/.../d3q27_pf_velocity/Dynamics.c.Rt   (48 KB, 1430+ lines)
  repo/third_party/.../d3q27_pf_velocity/Boundary.c.Rt    (85 KB, path-id dispatch)
  repo/third_party/.../d3q27_pf_velocity/Dynamics.R       (settings, line 347-389)

Runtime artifacts audited (JSON, not prose):
  stage13_flat_wall_runtime_20260616/decoupled_2000_audit.json
  stage13_flat_wall_runtime_20260616/equilibrium_1500_audit.json
  p100_gpu2_clean_20260616/{equilibrium_1500,decoupled_4000}/post/shape_angle/*.json
  p100_gpu2_clean_20260616/decoupled_4000/post/morphology/*.json
  p100_gpu2_decoupled_12000_t30_retry_20260616/.../shape_angle/*.json
  p100_gpu2_decoupled_12000_t150_retry_20260616/.../shape_angle/*.json
```

Binary used for all P100 runs:

```text
/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
sha256: 872d922651433d02071fa77a2d64fe21704ade7d4b63ea60d8a28dea492f1b78
```

---

## 1. What the code actually contains (verified)

The three "layers" described in doc 23 are **partially implemented**, not all
present. The exact state, verified line-by-line:

| Layer | Code symbol | Status in code |
|---|---|---|
| **A. Compact-stencil ghost** (Sugimoto) | `WallCompactStencilMode`, `stage13_compute_compact_stencil_solution`, `STAGE13_PHASE_FOR_STENCIL` | **Implemented and active** (Boundary.c.Rt:1710-1737, Dynamics.c.Rt:102-127) |
| **B. Wang corrected gradient** (Layer 1) | `WallGradMode`, `calcGradPhiBoundaryCorrected`, `calcGradPhiRaw` | **Implemented, default OFF** (Dynamics.c.Rt:184-258, 355-363; Dynamics.R:383-386) |
| **C. Ju wall free-energy** (Layer 2) | `WallMuMode`, `calcWallMuSource` | **Implemented, default OFF** (Dynamics.c.Rt:266-300, 443-449; Dynamics.R:387-389) |
| **D. GNBC dynamic contact line** (Layer 3 / Brown) | `DynamicCLMode`, `calcDynamicCLForce` | **NOT IMPLEMENTED.** No `DynamicCL*` symbol exists in `Dynamics.R` or `Dynamics.c.Rt`. |

### Force chain as currently wired (Dynamics.c.Rt:1078-1080 MRT, 1369-1371 BGK)

```text
F_total = F_surf + F_pressure + F_body + F_mu
F_surf  = mu * gradPhi                          (calc_Fs, line 977-979)
mu      = calcMu(C)  = 4βφ(φ-1)(φ-½) - κ∇²φ     (line 439-440)
           [+ mu_wall if WallMuMode >= 2]       (line 443-449)
gradPhi = calcGradPhi() = calcGradPhiRaw()      (line 355-363)
           [replaced by corrected gc if WallGradMode >= 2]
```

There is **no F_CL term and no slot for one**. Adding Layer 3 means inserting a
fifth force term, not rewiring an existing one.

### Mobility (Dynamics.R:349)

```text
M default = 0.02,  omega_phi = 1.0/(3*M+0.5)
```

The *case XML* used by the P100 runs sets M = 0.1, W = IntWidth = 3. Doc 23's
text ("M=0.1") refers to the run config, not the code default. Both are real;
do not assume the default when interpreting a run.

---

## 2. What the runtime evidence actually shows (verified)

### 2.1 Equilibrium shape-angle (init = bc, 1500 steps, clean run)

| Case | target | measured θ_shape_end | tail_std | circle RMS |
|---|---|---|---|---|
| t30  | 30°  | **30.14°** | 0.000 | 0.017 |
| t90  | 90°  | **90.02°** | 0.000 | 0.016 |
| t150 | 150° | **150.09°** | 0.000 | 0.044 |

Equilibrium is essentially exact (<0.15° error, zero drift). This confirms the
**static contact-angle geometry is correct** (compact-stencil ghost produces the
right angle when the droplet is already at the target).

### 2.2 Decoupled shape-angle (init ≠ bc, 12000 steps, P100 retry)

| Case | init → target | trajectory | end (12000) | Δ in 12k steps |
|---|---|---|---|---|
| 60→30  | 60→30  | 60.01 → 59.91 → 59.65 → 59.37 → 58.61 → 58.31 → **58.0** | 57.99° | **−2.0°** |
| 120→150 | 120→150 | 120.0 → 120.9 → 121.7 → 122.6 → 124.0 → 124.9 → **125.8** | 125.76° | **+5.8°** |

Both cases:
- move **in the correct direction** (toward target);
- are **monotonic**;
- are **not yet plateaued** — the last interval still moves 0.2-0.3°.

So the prior one-line characterization ("decoupled weak / barely responds") is
**incomplete**. The response is slow but real and still advancing at 12000
steps. The slowness is consistent with M = 0.1 limiting the contact-line
diffusion speed, not with a dead drive.

### 2.3 Circle-fit RMS grows over time (a real concern)

```
60→30:  RMS 0.006 (t=0) → 0.48 (t=12000)   — grows 80x
120→150: RMS 0.007 (t=0) → 0.37 (t=12000)  — grows 50x
```

The droplet contour departs from a clean circle as it evolves. This is the
signature of either spurious currents, interface oscillation, or mass
redistribution. It is **not** captured by the angle alone and must be tracked.

### 2.4 Compact-write gate — the real blocker

The flat-wall diagnostic audit (`decoupled_2000_audit.json`,
`equilibrium_1500_audit.json`) reports **`ok=false`** for every case, with
`compact_stencil_gate = PASS_C1A_SCAFFOLD_ONLY`. The target-wall metrics on the
actual FlatLowerY patch:

| Case | target_wall csq_valid_fraction | strict_write_ready_fraction | compact_write_path (id=30) | incomplete (id=-30) |
|---|---|---|---|---|
| eq t30  | 0.889 | 0.878 | 0.878 | 0.122 |
| eq t90  | 1.000 | 0.314 | 0.314 | 0.686 |
| eq t150 | **0.188** | 0.188 | 0.188 | 0.812 |
| dec 60→30 | 0.654 | 0.654 | 0.654 | 0.346 |
| dec 120→150 | **0.254** | 0.254 | 0.254 | 0.746 |

Failure flags hit every run:
```text
target_wall_csq_valid_fraction_below_0p95
compact_write_target_path_not_wetting_path_30
compact_write_incomplete_path_minus30_present
compact_write_strict_ready_fraction_below_0p95
compact_write_bounded_delta_above_1e-8
compact_write_applied_residual_above_1e-8
```

So **on 25-81% of the target wall the compact solve is rejected and the node
falls back to a neutral ghost (WettingPathId = -30).** This is the dominant
explanation for the slow decoupled response: the contact-angle drive is only
being applied on a fraction of the wall.

### 2.5 wall_ghost_clamp_fraction ≈ 0.71 (decoupled_4000 morphology)

71% of wall ghosts are being clamped to the `[−eps, 1+eps]` bound. Combined with
2.4, this says the compact `q_s` quadratic is producing out-of-range roots on
most target-wall nodes, which then either clamp (path 30 with bounded delta) or
get rejected entirely (path -30). The rejection/clamp is the load-bearing
problem, **ahead of** the dynamic-drive question.

### 2.6 Path-id decoding (Boundary.c.Rt:1715-1857)

```text
 30  = compact write SUCCESS (q_s valid, written)            [the only pass path]
-30  = compact write REQUESTED but solution rejected -> neutral ghost
 11  = legacy 90° special-case branch (radAngle≈90°)         [outer-domain walls]
 13  = legacy Briant geometric ghost
-10/-11/-12/-20 = fallback / edge-overlap / surrounded paths
```

The `11.0` spike (252/348 nodes in decoupled_4000) is **expected and correct**:
those are the outer domain walls, which are deliberately neutral (90°). The
audit's `target_wall_*` subset correctly excludes them. Do not "fix" path 11.

---

## 3. Correction to the prior reframe

The incoming reframe proposed this layering:

```text
A = compact-stencil ghost            (keep, geometry)
B = Wang corrected gradient          (demote to residual diagnostic, never write)
C = Ju wall free energy              (residual-form shadow only)
D = Brown/GNBC dynamic contact line  (the real dynamic driver)
```

with the load-bearing claim: **"compact ghost only controls static geometry;
the dynamic drive must come from Layer D, and Layer 1 (Wang) should never
write."**

The runtime evidence in §2 **partly supports and partly contradicts** this:

| Reframe claim | Evidence verdict |
|---|---|
| Equilibrium is correct, so static geometry is closed | **TRUE** (§2.1: <0.15° error) |
| Decoupled response is structurally too weak because the drive is diluted | **PARTIALLY TRUE but mis-diagnosed.** The bigger cause (§2.4-2.5) is that the compact solve is **rejected/clamped on 25-81% of the target wall**, so the drive is only applied on a fraction of nodes. The "1/26 stencil dilution" argument from doc 23 is real but secondary. |
| Layer 1 (Wang) should never write | **AGREE as policy** — it is safer to keep `WallGradMode` ≤ 1. But note: it is currently the *only* mechanism that could bypass the broken compact solve, because it operates on boundary fluid nodes directly. This is a trap to avoid, see §6. |
| Layer D (GNBC) is the real dynamic driver and should be built first | **DISAGREE on ordering.** Layer D's `θ_app` depends on a trustworthy near-wall gradient. With the compact solve 25-81% rejected, `θ_app` is itself unreliable on most of the wall. Building Layer D on top of an unreliable `θ_app` will compound errors. |

### Net corrected diagnosis

```text
Root cause #1 (BLOCKING): the compact-stencil q_s solve is rejected or
  clamped on a large fraction of target-wall nodes (WettingPathId=-30,
  clamp_fraction≈0.71). The drive is not weak; it is only applied on a
  minority of the wall.

Root cause #2 (AMPLIFYING): M = 0.1 is low, so even where the drive is
  applied, the contact line moves slowly.

Root cause #3 (COSMETIC/DECEPTIVE): growing circle-fit RMS means the
  droplet is distorting/oscillating; angle-only metrics will mislead.

The dynamic-drive layers (B/C/D) are NOT yet the bottleneck.
They become relevant only after root cause #1 is fixed.
```

---

## 4. Recommended Stage 14 sequence

The ordering below is forced by the dependency chain. Each stage has a single
gate. Do not advance on prose; advance only on the stated metric.

### Stage 14A — Diagnose WHY the compact solve is rejected (no physics change)

Goal: turn "csq_valid_fraction = 0.25" into a known cause per node.

Do **not** change wetting physics. Only add diagnostics and re-run the existing
short cases.

Work items:
1. Extend the flat-wall audit to bin each `WettingPathId = -30` node by its
   `WallCSQFallbackReason` and the quadratic's discriminant / root values.
2. For each rejected node, record:
   - `q_f` (interpolated fluid value) and the three vertex positions;
   - `d_s`, `d_f`, `d_s+d_f`;
   - the two quadratic roots `q_s^{(1,2)}` and whether either lies in
     `[-eps, 1+eps]`;
   - the signed-distance `h` and the analytic normal at that node;
   - whether `stage13_compact_vertex_is_real_fluid()` rejected any vertex.
3. Produce a histogram: rejection-by-discriminant vs rejection-by-root-range
   vs rejection-by-vertex-mask vs rejection-by-residual-tol.

Gate (14A):
```text
A single dominant rejection cause is identified, OR the rejection is shown
to be spread evenly across causes. Either way, the cause(s) are named and
quantified, not "unknown".
```

Why first: §2.4-2.5 show the rejection rate is the dominant effect. Every later
layer inherits this defect. This stage is pure measurement and is risk-free.

### Stage 14B — Repair the compact solve rejection (physics change, flat-wall only)

Apply the fix indicated by 14A. Likely candidates, to be chosen by 14A's
evidence, not by preference:

- If roots are out of range because `q_f` is sampled from the wrong side of the
  interface → fix the three-vertex stencil selection (R1 in doc 22).
- If `stage13_compact_vertex_is_real_fluid()` over-rejects because
  `IsBoundary_dyn` is unreliable → replace with a generated geometry mask
  (doc 22 R1 fallback).
- If the discriminant is negative at low angles → the quadratic formulation
  needs the safeguarded-Newton branch from the task book (§3.4), not silent
  clamp.
- If `d_f` is large (poor stencil locality) → raise `WallCompactStencilMaxL`
  and re-search.

Gate (14B), flat-wall short write (2000 steps), compact-mode write:
```text
target_wall csq_valid_fraction        >= 0.95
target_wall strict_write_ready_fraction >= 0.95
target_wall WettingPathId == 30 fraction >= 0.95
wall_ghost_clamp_fraction             <= 0.10
bounded_delta p95                     <= 1e-8
applied_residual p95                  <= 1e-8
nonfinite_phase_count                 == 0
```
These are exactly the gates the current audit already checks; they must turn
from FAIL to PASS.

Do not touch M, WallGradMode, WallMuMode, or any dynamic layer in this stage.

### Stage 14C — Mobility sweep on the repaired compact solve

Now that the drive is applied on ≥95% of the wall, re-measure the decoupled
response as a function of M, with all dynamic layers OFF:

```text
M ∈ {0.1, 0.2, 0.3, 0.4},  W = 3,  compact-mode write
cases: 60→30, 120→150, equilibrium 30/90/150
steps: 12000 (or to plateau)
```

Gate (14C):
```text
60→30  reaches <= 35° within the run, direction correct, no plateau short of 35°
120→150 reaches >= 145° within the run, direction correct
equilibrium error stays < 0.5° for all M
circle-fit RMS(t) does not grow more than 2x its t=0 value   (controls §2.3)
mass drift < 1%
```

This isolates "is mobility the remaining limiter?" from "is the drive broken?".
It directly tests doc 23's M-sweep recommendation on a *working* drive.

Only if 14C still shows inadequate response do we proceed to the dynamic
layers.

### Stage 14D — Dynamic contact-line residual force (Layer D), shadow first

Built **only if 14C plateau is short of target**. This is where the incoming
reframe's Layer D enters, but in residual form.

Order:
1. Add `DynamicCLMode` and the helper `calcContactLineResidual()` /
   `calcDynamicCLForce()` exactly as the reframe specifies, but **default OFF**
   and with `DynamicCLMode=1` = shadow only.
2. The residual MUST be `cos(θ_eq) - cos(θ_app)`, computed from the
   compact-stencil-driven gradient (now reliable post-14B).
3. Insert `F_CL` as the **fifth** term in `F_total` (MRT line 1078, BGK line
   1369), behind an `if (DynamicCLMode >= 2)` guard.
4. Sign calibration (`DynamicCLCosSign`, `DynamicCLForceSign`) MUST be set by
   the flat-wall 30/90/150 equilibrium test, never by guessing.

Gate (14D-shadow, mode=1):
```text
equilibrium 30/90/150:  |F_CL| summed over wall ~ 0  (within DynamicCLCosTol)
60→30:  F_CL direction aligns with contact-line motion toward 30°
120→150: F_CL direction aligns with contact-line motion toward 150°
F_CL nonzero only inside the contact-line band (eps < q < 1-eps)
```

Gate (14D-write, mode=2, small coeff):
```text
DynamicCLCoeff ∈ {0.0025, 0.005, 0.01, 0.02}, cap = 0.02 * sigma/IntWidth
60→30 response rate > 14C baseline
equilibrium error stays < 1°
mass drift <= 2x 14C baseline
```

### Stage 14E — Ju residual-form wall-mu (Layer C), shadow only, last resort

Only if 14D is still insufficient. Convert `calcWallMuSource` from its current
**non-residual** form (which does not vanish at equilibrium — a real defect) to
the residual form:

```text
R_mu = κ n_w·∇q + 6σ cos(θ_eq) q(1-q)            (vanishes at equilibrium)
mu_wall_res = -WallMuResidualScale * a_v * R_mu
```

Keep `WallMuMode=1` (shadow) until 14D is exhausted. Never run Layer C write
and Layer D write simultaneously — both inject contact-angle drive and would
double-count (doc 23 §4 Layer-2 constraint).

### Stage 14F — Curved surfaces (sphere/cylinder), only after flat-wall closure

```text
C4 sphere/cylinder compact-stencil shadow
C5 sphere/cylinder short write
```
Reuse the V4 gate order from doc 21. Add the curved-surface zone checks from
doc 21 §5 and the task book §5. Do not start before 14B passes on flat wall.

---

## 5. What NOT to do in Stage 14

```text
Do not enable WallGradMode=2 (Layer 1 write) to "rescue" the broken compact
  solve. It bypasses the bug instead of fixing it, and it changes the
  consumer chain (STAGE13_PHASE_FOR_STENCIL) in a way that masks the root
  cause. The reframe is right to demote it; keep it <= 1.

Do not build Layer D (DynamicCL) before 14B. θ_app would be computed from a
  gradient whose underlying ghost is rejected 25-81% of the time.

Do not run Layer C (Ju mu_wall) and Layer D together in write mode.

Do not change MRT relaxation, pressure-force formula, or the phase equation
  in the same patch as any wetting change (doc 21 §8).

Do not claim validation_passed at any point in Stage 14. Status stays
  exploratory_not_validation until flat-wall equilibrium AND decoupled both
  pass with mass/RMS gates, and curved surfaces are separately closed.

Do not interpret the audit JSON "angle_stats" field as a measured contact
  angle. In the current audit it echoes the prescribed radAngle (constant
  min=mean=max). The measured angle is theta_shape_end_deg in the
  shape_angle JSONs.
```

---

## 6. Open question to resolve before coding (14A)

Before writing any Stage 14A diagnostic code, the dominant rejection cause must
be pinned down, because it decides whether 14B is a *stencil fix*, a
*mask fix*, or a *quadratic-solver fix*. The three live hypotheses, with the
evidence that would confirm each:

```text
H1 (stencil/vertex): q_f comes from a vertex on the wrong side of the
    interface or from a masked-solid vertex.
    Confirm if: 14A shows WallCSQVertexRealFluidFraction < 1 on rejected
    nodes, or vertex q_min/q_max straddle 0.5 erroneously.

H2 (mask): stage13_compact_vertex_is_real_fluid() over-rejects because
    IsBoundary_dyn is stale.
    Confirm if: 14A shows vertices are geometrically fluid but flagged solid.

H3 (quadratic): the contact-relation quadratic has no in-range root at low
    W / extreme angles, so every candidate is clamped or rejected.
    Confirm if: 14A shows discriminant < 0 or both roots out of [-eps,1+eps]
    on rejected nodes, with valid vertices and valid q_f.

These are mutually non-exclusive. 14A must distinguish them.
```

---

## 7. Minimal first action (when approved)

The first executable step is Stage 14A, item 1-3 only — pure diagnostics, no
physics change, no recompile of wetting logic:

```text
1. Edit scripts/stage13/stage13_flat_wall_diagnostic_audit.py to also emit,
   per WettingPathId=-30 target-wall node, the fallback-reason histogram and
   the quadratic (q_f, d_s, d_f, discriminant, roots, root-in-range flag).
2. Re-run the audit against the EXISTING VTI outputs already on disk
   (p100_gpu2_clean_20260616 and the 12000-step retries) — no new simulation
   needed for the first pass.
3. Decide H1/H2/H3 from the histogram.
```

No source generation, no compile, no simulation in step 1-2. This is the
lowest-risk way to convert the current "25-81% rejected" into a named cause.

---

## 8. Summary

```text
Settled:
  - Static contact-angle geometry is correct (equilibrium < 0.15° error).
  - Compact-stencil ghost is the right static boundary layer (Layer A).
  - Decoupled response is directionally correct and still advancing at 12k.

Blocking (must fix first):
  - Compact q_s solve is rejected/clamped on 25-81% of the target wall.
  - wall_ghost_clamp_fraction ≈ 0.71.

Amplifying:
  - M = 0.1 is low; will be swept in 14C after the solve is fixed.
  - Circle-fit RMS grows 50-80x over 12k steps — must be tracked.

Not yet relevant:
  - Layer D (GNBC dynamic force) — depends on a reliable θ_app, which depends
    on 14B. Build only if 14C plateaus short of target.
  - Layer C (Ju mu_wall) — current form does not vanish at equilibrium and
    must be converted to residual form before any write use.

Stage 14 order: 14A (diagnose) → 14B (fix solve) → 14C (M sweep) →
                14D (Layer D shadow→write, if needed) → 14E (Layer C, last resort)
                → 14F (curved surfaces).
```
