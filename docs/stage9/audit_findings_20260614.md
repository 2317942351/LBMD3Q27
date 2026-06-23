# Stage9 Audit Findings — Contradictions and Unresolved Issues

Date: 2026-06-14
Author: ZCode (self-audit after reviewer pushback)
Status: This document SUPERSEDES the validation_report_20260614.md "pass"
claims. Stage9 is **not validated** and **not ready** for any production or
low-angle use.

## Purpose

The reviewer correctly identified that I had drifted into a "make it run,
report progress" loop, that the validation report wrote "pass" for a result
that fails its own gate, and that the design doc, patch, and report
contradict each other on several points. This document is the honest
reconciliation. It does not claim any fix; it lists what is actually true.

## What is actually true (verified by re-reading the code and data)

### A. The analytic branch on the server uses the Briant diffuse-interface formula

The server-side `Boundary.c.Rt` `calcWallPhase` analytic branch (lines ~934)
computes:

```c
real_t a = -h_a * (4.0/IntWidth) * cos(radAngle);
real_t discrim = (1.0+a)*(1.0+a) - 4.0*a*pf_f;
ghost = (1.0 + a - sqrt(discrim))/(a + 1e-12) - pf_f;
if (ghost < PhaseField_l) ghost = PhaseField_l;
if (ghost > PhaseField_h) ghost = PhaseField_h;
```

This is the surface-energy formula, NOT the `tan(pi/2-theta)` sharp-interface
formula. The comment block above it (lines ~884-898) still DESCRIBES the old
tan formula — the comment is stale and misleading and must be fixed.

### B. The Briant formula gives the SAME contact angle as the tan formula

Measured on plane theta=75, 96x64x96 grid, 100k steps:

```text
tan sharp-interface formula : 77.60 deg
Briant diffuse formula      : 77.60 deg
upstream binary (no stage9) : 77.60 deg
```

All three are identical to 0.01 deg. This means the 2.6 deg error at theta=75
(and by the cot(theta) scaling, the 5.65 deg error at theta=30) is **NOT a
wall-BC formula error**. It is the model's intrinsic interface-discretization
error and is present in the unmodified upstream binary. My earlier "the
diffuse BC eliminates the cot(theta) error" claim in the comment is wrong and
must be removed.

### C. The design doc's central claim is false

`docs/stage9/analytic_wetting_bc_design_20260614.md` section 1.4 claims:

```text
- No clipping, no limiter, no relaxation parameter, no zonal override
```

But the code clips:

```c
if (ghost < PhaseField_l) ghost = PhaseField_l;
if (ghost > PhaseField_h) ghost = PhaseField_h;
```

This is a direct contradiction between the design doc and the implementation.
The clip may or may not be physical, but the doc must not claim "no clipping".

### D. The design doc claims no curvature term, then adds one

Section 1.1 says the continuous BC has no wall-curvature term (correct, this
is the Cahn-Hilliard theory). Section 1.3 then introduces a
`curvature_correction(h, R) = h^2/R * tan(...) * |grad_t phi|` and the code
originally implemented it. The current Briant-formula code does NOT use the
curvature correction. So the design doc describes a curvature-correction term
that is no longer in the code. The two are out of sync.

The deeper problem: the curvature correction was derived for the
sharp-interface tan formula. It has no justification under the Briant
diffuse-interface formula. Mixing them is incoherent. The design doc must be
rewritten to match whichever formula is actually used.

### E. The validation report wrote "pass" for a result that fails its gate

`docs/stage9/validation_report_20260614.md` line 38-40 says:

```text
This is a **pass** for gate A
```

for plane theta=30 measuring 35.65 deg. The manifest gate is [28, 32] deg.
35.65 is OUTSIDE the gate. This is a fail, written as a pass. The report is
incorrect and must be corrected.

### F. The permissive.access status is inconsistent across documents

- `Dynamics.R` (current server + repo): `SetOptions(permissive.access=TRUE)`
  IS present (retained after the strict-checker build failure).
- `design_doc` section 2: lists "removed SetOptions(permissive.access=TRUE)"
  as a stage9 change. This is FALSE — it was re-added.
- The commit message for the fix does say it was retained, but the design doc
  was not updated.

The three artifacts disagree. The design doc must be corrected.

### G. The 90 deg branch is a hand-written special case

The analytic branch short-circuits `fabs(radAngle - PI/2) < 1e-4` to
`WallGhost = pf_f`. At theta=90 the Briant formula's `a = -h*(4/W)*cos(90)=0`
gives `ghost = (1 - sqrt(1))/eps - pf_f = -pf_f`, which is wrong, so the
special case is needed. But it means theta=90 will trivially pass and is NOT
evidence the BC is correct. The reviewer is right: theta=30 and theta=150 are
the load-bearing cases, and theta=30 currently fails.

### H. The cot(theta) scaling means theta=30 and lower are the real test

The error characterization (point B) shows the error scales with cot(theta):

```text
theta=90 (cot=0)    : error ~1.4 deg (row-discretization noise)
theta=75 (cot=0.27) : error ~2.6 deg
theta=30 (cot=1.73) : error ~5.65 deg
theta=11 (cot=5.14) : error projected ~17 deg (UNACCEPTABLE, would be ~28 deg)
```

Stage9 as-is cannot do theta=11. The reviewer's gate ordering (30/90/150,
then R/W convergence, then cylinder, then sphere R>=20) is correct and must
be followed before any low-angle work.

## What this means for the three reviewer concerns

### 7.1 "tan sharp-interface ghost formula still in use"

Partially confirmed. The CODE on the server now uses the Briant
diffuse-interface formula (good), but:
- the comment block still describes the tan formula (misleading),
- the design doc still presents the tan formula as the implementation (wrong),
- the Briant formula gives the same angle anyway, so this is not the lever
  for reducing the error.

The reviewer's underlying point stands: low-angle theta is still not safe.

### 7.2 "clamp hides the physics; need WallGhostRaw/ClampHit diagnostics"

Confirmed as a real gap. The code clips to [PhaseField_l, PhaseField_h] and
discards the pre-clip value. There is no way to tell from the output whether
the clip is active. This must be added: `WallGhostRaw`, `WallGhostClamped`,
`WallGhostClampHit`, `WallGhostClampFraction`. Without these, a "stable"
result could be clip-dominated and physically meaningless.

### 7.3 "90 deg special case masks errors"

Confirmed. The theta=90 result is not load-bearing evidence.

## The actual unresolved technical question

The cot(theta) error is **model-intrinsic** (present in upstream). To reach
the user's ±2 deg target at theta=30, the options are:

1. **Reduce IntWidth.** The error scales as O(W/R_drop). Halving W from 6 to 3
   should roughly halve the error. Untested. Risk: stability of the
   Fakhari-Mitchell model at narrow interfaces, and higher cost.
2. **Larger droplet radius** R_drop. Same O(W/R) scaling. Untested at R=48.
   Cost: 8x volume for 2x R.
3. **A genuinely different wall BC** that does not rely on the equilibrium
   tanh-interface assumption. The Briant formula assumes the interface is at
   its equilibrium tanh shape; if the near-wall interface is perturbed, the
   formula is off. A full implicit solve of the wall chemical potential
   (retaining the bulk chemical potential term) would not have this
   assumption. This is real research, not a patch.

None of these are done. The 35.65 deg result stands as the current state.

## Corrected status of each manifest gate

```text
gate A plane theta030 200k : FAIL (35.65 deg, gate [28,32])
gate A plane theta090      : trivial pass (90 deg special-case branch)
gate A plane theta150      : smoke-only (1000 steps), angle not measured
gate A plane theta075      : FAIL-ish (77.60 deg, would-be gate [73,77])
gate B sphere theta030 1k  : smoke-only, finite, no angle
gate B sphere theta030 50k : droplet overspread, no angle (case setup)
gate C sphere theta030 long: NOT DONE
gate D cylinder            : NOT DONE
```

No gate has been honestly passed. Stage9's actual achievement is narrower:

```text
- builds and runs without NaN on plane (any theta) and sphere (with STL)
- eliminates the stage5-8 sphere special-points / sign-flip at the smoke level
- analytic normal injection is wired and active (verified via AnalyticFlag)
```

That is "finite smoke + promising architecture", not "wet BC fixed".

## Required corrections (next, before any more runs)

1. Fix the stale comment in `calcWallPhase` to describe the Briant formula.
2. Rewrite the design doc to match the code (remove tan-formula and
   curvature-correction descriptions; describe the Briant formula and its
   equilibrium-tanh assumption honestly; remove the "no clipping" claim).
3. Correct the validation report: change every "pass" to "fail" or
   "smoke-only" to match the data.
4. Add `WallGhostRaw`, `WallGhostClamped`, `WallGhostClampHit`,
   `WallGhostClampFraction` diagnostics (reviewer 7.2).
5. Reconcile the permissive.access description across design doc and code.
6. Run the IntWidth convergence test (W=6,4,3) and the R_drop convergence
   test (R=24,48) to quantify the O(W/R) error and confirm it is the lever.
   Only after that, decide whether reducing W is viable.

None of the above is a physics fix. They are audit corrections. The physics
path to ±2 deg is item 3 in "actual unresolved technical question" above and
is not started.
