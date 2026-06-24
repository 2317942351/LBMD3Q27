# Stage17B-B3 Controlled-Write Plan

Date: 2026-06-24

Status: `planning_only`. No solver write path has been enabled by this document.

## B2 Basis

The following B2 shadow-only gates are recorded and pushed:

```text
cylinder shadow 12000 = PASS_STAGE17B_B2_SHADOW_DIAGNOSTICS
sphere shadow 12000   = PASS_STAGE17B_B2_SHADOW_DIAGNOSTICS
```

B2 proves only that `Psi*` and near-wall shadow diagnostics are finite, bounded, and coherent on P100 long-run cylinder/sphere cases. It does not prove contact-angle correctness.

## Current Code Path

In `Boundary.c.Rt::calcWallPhase()` the active analytic wetting branch currently does this:

```text
stage17b_compute_diffuse_shadow(...)
  -> fills PsiSolid / PsiNormal / PsiWallGhost / PsiWriteAllowedFlag
  -> does not write WallGhost or PhaseF

if compact_write:
  -> flat-only Stage13 compact write path
else:
  WallGhost = stage13_compute_analytic_wall_ghost(...)
  PhaseF = pf_f
```

The current B2 guardrail is explicit:

```text
Stage17BWriteMode > 0.5 => PsiWriteAllowedFlag = 0
```

Therefore B3 requires a deliberate source change. It must not be achieved by changing case XML alone.

## B3 Objective

Add a controlled curved-surface write path that can replace the legacy analytic `WallGhost` with the Stage17B diffuse-solid shadow value under strict gates.

B3 must still not write `PhaseF`. The wall node `PhaseF` mirror remains:

```text
PhaseF = pf_f
```

This keeps B3 focused on the wetting ghost value only and avoids mixing it with the broader PhaseF/stencil/streaming closure problem.

## Proposed Source Semantics

### Settings

Keep the existing default:

```text
Stage17BWriteMode = 0
```

Define modes:

```text
0 = shadow only, current B2 behavior
1 = write-audit armed but no write; PsiWriteAllowedFlag reports readiness
2 = controlled write to WallGhost on curved analytic geometry only
```

No mode may write `PhaseF`.

### Geometry Gate

B3 controlled write is allowed only for analytic curved geometry:

```text
AnalyticSolidType >= 1.5
```

This covers cylinder and sphere and intentionally excludes flat wall. Flat-wall compact write remains governed by the Stage13 flat-only gate:

```text
stage13_compact_write_requested() && (AnalyticSolidType < 1.5)
```

B3 must not reuse `WallCompactStencilWriteAllowedFlag`.

### Readiness Gate

The write candidate must satisfy all B2 readiness conditions:

```text
dist <= Stage17BWriteBand
PsiGradMag > Stage17BGradPsiMin
PsiJaggedness < 1e-3
stage13_boundary_phase_is_valid(phi_f)
PsiWallGhost in [PhaseField_l, PhaseField_h]
```

The candidate is already clamped by `stage13_clamp_phase_value`, but B3 must record whether a clamp was needed. A large clamp fraction cannot be accepted as a physical response.

### Write Location

The only intended B3 write location is immediately after:

```text
stage17b_compute_diffuse_shadow(n_w_a, sd_a, h_a, pf_f, grad_f_shadow, radAngle);
```

and before:

```text
WallGhost = stage13_compute_analytic_wall_ghost(...);
```

Pseudo-code:

```c
if (stage17b_controlled_write_requested() && PsiWriteAllowedFlag > 0.5) {
    WallGhost = PsiWallGhost;
    WallGhostRaw = PsiWallGhost;          // or add PsiWallGhostRaw in a later diagnostic extension
    WallGhostClamped = PsiWallGhost;
    WallGhostClampHit = 0.0;              // only valid if raw/clamp delta is separately tracked
    WettingPathId = 170.0;
    PhaseF = pf_f;
    return;
}
```

Preferred refinement before implementation:

```text
add PsiWallGhostRaw
add PsiWallGhostClampHit
add PsiWriteAppliedFlag
```

Then set:

```text
WallGhostRaw = PsiWallGhostRaw
WallGhostClamped = PsiWallGhost
WallGhostClampHit = PsiWallGhostClampHit
PsiWriteAppliedFlag = 1
WettingPathId = 170
```

This is more auditable than pretending a clamped value was raw.

## Required New Diagnostics

Add fields:

```text
PsiWallGhostRaw
PsiWallGhostClampHit
PsiWriteAppliedFlag
PsiWriteRejectedReason
```

Suggested `PsiWriteRejectedReason` values:

```text
0 = no rejection / applied or shadow-ready
1 = Stage17BDiffuseSolidMode off
2 = non-curved analytic geometry
3 = outside write band
4 = small PsiGradMag / ambiguous normal
5 = jaggedness too large
6 = invalid fluid probe phase
7 = clamped ghost outside tolerance
8 = Stage17BWriteMode not 2
```

Keep `WettingPathId=170` for applied B3 writes and negative path ids for rejected armed-write diagnostics if useful, e.g. `-170`.

## Source Audit Updates

Extend `scripts/stage17/stage17B_shadow_source_audit.py` or add a new B3 audit script.

B3 source gate must prove:

```text
default Stage17BWriteMode is still 0
B3 write condition requires Stage17BWriteMode > 1.5
B3 write condition requires AnalyticSolidType >= 1.5
B3 does not assign PhaseF except existing mirror PhaseF = pf_f
B3 does not use WallCompactStencilWriteAllowedFlag
B3 sets WettingPathId = 170.0 only in the controlled write block
old flat compact-write gate remains AnalyticSolidType < 1.5
```

## First Runtime Gate

Do not start with 12000 steps. Use short write-audit cases:

```text
cases = cylinder_theta090_writeaudit, sphere_theta090_writeaudit
steps = 100
vtk-period = 100
log-period = 50
Stage17BWriteMode = 2
Stage17BDiffuseSolidMode = 1
WallCompactStencilMode = 0
legacy radAngle = 90d
shadow theta = 90
```

The first write-audit gate is not a contact-angle gate. It asks only:

```text
does B3 write where B2 said it was ready?
does WettingPathId=170 appear only on curved near-wall nodes?
does PhaseF remain finite?
does WallGhost equal PsiWallGhost on applied nodes?
does the run avoid NaN for 100 steps?
```

## Expansion Order

If the 100-step write-audit gate passes:

```text
1. cylinder/sphere theta090 write-audit to 1000
2. cylinder/sphere theta060/theta120 write-audit to 1000
3. flat wall regression with Stage17BWriteMode=2 must show no B3 writes
4. only then static contact-angle morphology cases
```

Static contact-angle validation must still be reported separately from write-path health.

## Failure Handling

If B3 fails:

```text
do not tune theta or mobility
do not enable PhaseF writes
do not enter dynamic impact
compare WallGhost/PsiWallGhost/WettingPathId/PhaseF first-failure step
fall back to B2 shadow values and identify the first polluted consumer
```

## Claim Limits

Allowed after this plan:

```text
B3 controlled-write planning is complete.
```

Forbidden:

```text
B3 is implemented
curved wetting is fixed
contact angle validation passed
dynamic impact is ready
```
