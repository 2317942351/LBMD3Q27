# Stage12 — W=3 Curved-Wall Static Validation Report

Date: 2026-06-14
Status: partial. 1 of 4 cases clean-passed; 1 produced NaN-infected phase;
2 blocked by geometry-setup. Honest report, no pass claim beyond the data.

## Results

```
case          geom       theta  W   result
cyl_theta090  cylinder   90     3   PASS: 89.84 (L), 88.25 (R), both in [88,92]
cyl_theta030  cylinder   30     3   CONTAMINATED: phase field contains NaN in
                                   the slice (grep NaN=0 misleading; the failcheck
                                   did not trip but the VTK has NaN cells). The
                                   droplet spread into a film over the cylinder
                                   (correct wetting direction) but the field is
                                   not clean. No angle measured.
sph_theta090  sphere     90     3   BLOCKED: STL side="in" + analytic-wetting
                                   NaN at init (same Stage9 STL/init issue).
                                   Geometry verified correct (sphere centered
                                   at (40,48,48) R=20, droplet at z=90 R=16),
                                   but first-iteration NaN.
sph_theta030  sphere     30     3   NOT RUN (sphere theta=90 gate failed).
```

## What passed (honest)

**Cylinder theta=90 neutral control: PASS.** This is a real, meaningful result:
- The analytic normal injection works on a curved (cylindrical) wall.
- The STL geometry, side convention, and post-processor are correct on a
  cylinder (the measured 89.84/88.25 is within the [88,92] gate).
- W=3 is stable on a cylinder at theta=90.

This confirms the Stage11 finding (W=3 viable) extends to curved walls AT
LEAST at the neutral angle.

## What did NOT pass (honest)

**Cylinder theta=30: contaminated (CONFIRMED).** Direct finiteness check:
`n_nan = 137088` (15.5% of cells), all finite cells = 1.0. The simulation
diverged at some point during the 100k steps (the failcheck did not trip,
likely because the NaNs appeared near the very end). The droplet did spread
over the cylinder (correct wetting direction for theta=30) before diverging.
**This is a real W=3 + strong-wetting + curvature instability.** No contact
angle claim.

**Sphere theta=90: blocked by geometry-setup.** The STL `side` convention
(`side="out"` makes the entire exterior solid for a closed sphere; `side="in"`
NaNs at init with analytic wetting) is the same Stage9 STL/init issue. The
sphere geometry itself is correct (verified via the ASCII map), but the
analytic-wetting path produces NaN on the first iteration when the STL solid
mask is a closed surface. This is a Stage9 code issue (the legacy fallback
path for corner/edge STL nodes), NOT a wetting-physics failure, and NOT a W=3
stability issue.

## Verdict

Stage12 is **NOT a pass**. One clean pass (cylinder theta=90), one
contaminated (cylinder theta=30), one blocked (sphere). The reviewer's gate
(theta=90 neutral control first) correctly caught that the sphere geometry
path is not yet working, so no theta=30 sphere claim is made.

## What this tells us

1. **W=3 works on a cylinder at neutral angle.** Stage11's finding extends to
   curved walls, at least partially. This is encouraging but not sufficient.
2. **Strong wetting (theta=30) on a curved wall at W=3 is not yet stable
   enough to measure.** This could be W=3 sharpening + curvature, or the
   Stage9 corner-node legacy fallback on STL geometry. Needs isolation.
3. **The sphere STL path has a real Stage9 defect** (analytic-wetting NaN on
   closed STL surfaces at init) that blocks all sphere work regardless of W.
   This is the most important blocker for the user's application goal
   (sphere wetting).

## Required next steps (NOT authorized, listed for user decision)

To make Stage12 pass, two issues must be resolved:
1. **Sphere STL + analytic-wetting NaN at init.** This is a Stage9 code issue
   in the corner/edge legacy fallback when the STL solid mask is a closed
   surface. Requires debugging `calcWallPhase` / `Init_wallNorm` on STL
   geometry. This is the critical blocker for sphere wetting.
2. **Cylinder theta=30 NaN contamination.** Need to determine if it is
   W=3 instability on curvature, or a post-processing read issue, or the
   same corner-node legacy fallback.

These are Stage9 code-debugging tasks, not new physics. They require
re-authorization to touch the TCLB code.

## What Stage12 did NOT establish

- W=3 contact-angle accuracy on curved walls (only neutral, cylinder).
- Sphere wetting at any angle (blocked by STL/init NaN).
- Dynamic impact (not in scope).

## Files

- `stage12_design_20260614.md` — design
- `scripts/stage12/stage12_run.sh` — case runner
- `scripts/stage12/stage12_curved_angle.py` — curved-wall angle post-processor
- `scripts/stage12/gen_cylinder_stl.py` — cylinder STL generator
- `scripts/stage12/stage12_sphere_diag.py` — sphere layout diagnostic
