# Stage 17 — gate-A fix APPLIED: compact-stencil write gated to flat-only; cylinder STABILISED — 2026-06-20

Applied fix option A from doc 49. One-line gate in calcWallPhase (Boundary.c.Rt):
the compact-stencil q_s write now only happens on FLAT walls (AnalyticSolidType==1);
on curved geometry (cylinder/sphere, type 2/3) it falls back to the existing
analytic (Briant) ghost. Result: the cylinder NaN is FIXED (stability restored);
accuracy on curves is still the analytic-ghost level (needs option B). This is a
real source change, built and tested.

```text
status_label: exploratory_not_validation (cylinder STABILITY restored; angle accuracy pending option B)
binary (gate-A): sha256 341fb2fcff451c6b628e4389dc28cf1868b1326ffb0daacab0eb2db25382ab62
previous binary: f00f8ff7... (NaN on cylinder)
source change: Boundary.c.Rt line 1702, +1 condition; mirrored to the stage9 git
  snapshot; patch at scripts/stage13/patches/stage17_gateA_flat_only_write.patch
```

## The change
```c
// before
bool compact_write = stage13_compact_write_requested();
// after (gate-A)
bool compact_write = stage13_compact_write_requested() && (AnalyticSolidType < 1.5);
```
On flat (type 1) the gate is true -> compact write active (validated path, docs 40-43).
On cylinder/sphere (type 2/3) the gate is false -> calcWallPhase falls through to the
analytic ghost (the stable path confirmed by the WriteAllowedFlag=0 control, doc 49).

## Verification (server compile lane, build_rc=0)

### Cylinder (was NaN at step 250 with f00f8ff7)
cyl_t90, compact-stencil, M=0.6, 12000 steps, gate-A binary 341fb2fc:
- ran the FULL 12000 steps, 965 s, **0 NaN**, PhaseF in [0,1] (nan=0, inf=0).
- (was: PhaseF 80% NaN by step 250 on the old binary.)
- calibrated angle (golden_cyl): grad 107.3 / inverted 115.4 deg (target 90) -- the
  analytic-ghost accuracy on the curve, not a regression of the BC math. Expected;
  option B is needed for accuracy.

### Flat wall regression (gate is a no-op on type 1)
The gate evaluates `requested() && (1 < 1.5)` = `requested() && true` = original
value, so the flat-wall code path is byte-identical. Validated flat-wall results
stand (eq30 32.3, eq90 89.8, eq150 149.8 deg, doc 40/43). Safe by construction.

## What this closes / opens
```text
CLOSED: compact-stencil q_s write crashes the phase solve on curved geometry (doc 46).
        Cylinder runs are now STABLE end-to-end with the compact-stencil binary.
OPEN:   cylinder/sphere ANGLE ACCURACY is still analytic-ghost level (~+/-10..25 deg,
        doc 47 + this doc's 115 vs 90). Needs option B: on curved walls, write the
        analytic EQUILIBRIUM near-wall phase (tanh of the SDF, contact-angle oriented)
        instead of a per-staircase-node analytic ghost -> smooth + accurate.
```

## Next (option B, the accuracy fix; main-agent owned, audit before claim)
Implement the analytic-equilibrium near-wall phase write for curved walls in
calcWallPhase (a new helper that sets WallGhost/PhaseF on cylinder/sphere wall
nodes from the analytic SDF + tanh profile oriented by the contact-angle condition).
Rebuild, re-run cyl 60/90/120, measure with golden_cyl; gate within ~5 deg.

## Reproducibility
```text
# the fix is in the compile tree Boundary.c.Rt (line 1702) and mirrored in the repo
# stage9 snapshot; patch: repo/scripts/stage13/patches/stage17_gateA_flat_only_write.patch
cd /home/yuan/src/TCLB_lbm2026_compile_lane && make d3q27_pf_velocity_q27_geometric
# cylinder stable run:
python3 /home/yuan/gen_cyl_compact.py <root>   # then run cyl_t90 with binary 341fb2fc
```
