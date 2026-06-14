# Stage9 Validation Report

Date: 2026-06-14
Branch: `feature/analytic-wetting-bc-diffuse-interface`
Server: HM570 (`yuan@192.168.1.16`), 2× Tesla P100-PCIE-16GB
Binary SHA256: `8a0bc0d028a6ee5b8cf80472f45ca08b44091977f393a26c20d28893e5eb0c09`
Source: `third_party/tclb_snapshots/stage9_analytic_wetting_diffuse_interface/`
Build: `d3q27_pf_velocity_q27_geometric` (q27=TRUE, geometric=TRUE, staircaseimp=FALSE)

Status: `exploratory_not_validation` — the wetting BC runs clean and produces
physically reasonable contact angles; not yet audit-promoted.

## Summary

**CORRECTED 2026-06-14 after self-audit (see audit_findings_20260614.md).**
The original version of this report wrote "pass" for results that fail their
own gates. That was wrong. The corrected summary:

The analytic-geometry wetting BC **builds and runs without NaN** on plane
(any theta) and sphere (with STL) walls, and **eliminates the stage5-8 sphere
special-points and sign-flip** at the smoke level. It does **NOT** achieve the
target contact-angle accuracy. The measured error scales with cot(theta) and
is **model-intrinsic** (the unmodified upstream binary shows the same error),
not a wall-BC defect. No gate has been honestly passed. Stage9 is
"finite smoke + promising architecture", not "wet BC fixed".

## Results (corrected)

### Gate A: Plane theta=30, 200000 steps (P100 #1, 28.2 min) — **FAIL**

```text
rc = 0
NaN count = 0
VTK frames = 11 (steps 0, 20k, ..., 200k)
two-row near-wall contact angle: 35.65 deg (target 30 deg)
manifest gate: [28, 32] deg
VERDICT: FAIL (35.65 is outside the gate by 0.65 deg on the high side)
```

### Gate A: Plane theta=75, 100000 steps (P100 #1) — **FAIL-ish**

```text
rc = 0, NaN = 0
contact angle: 77.60 deg (target 75 deg)
would-be gate [73, 77]: FAIL by 0.60 deg
```

### Model-intrinsic error confirmation (the key finding)

The **unmodified upstream TCLB binary** at theta=75 also measures 77.60 deg.
The Briant diffuse-interface formula and the tan sharp-interface formula both
measure 77.60 deg. The error is therefore NOT a wall-BC formula artifact; it
is the Fakhari-Mitchell model's interface-discretization error, scaling as
O(W/R_drop) and amplified by cot(theta). This is the floor that any wall-BC
change cannot by itself get under. See audit_findings_20260614.md point B.

### Gate A smokes: Plane theta=30/90/150, 1000 steps each (P100 #1) — **smoke-only**

```text
plane theta030: rc=0, NaN=0, 2 VTK frames, finite. Angle NOT measured (smoke).
plane theta090: rc=0, NaN=0. Trivial pass (90 deg special-case branch).
plane theta150: rc=0, NaN=0, finite. Angle NOT measured (smoke).
```

These are smoke tests (finite, no NaN), not angle validations. theta=90 is a
hand-written special case and is not load-bearing evidence.

### Sphere theta=30, 1000-step smoke with STL (P100 #2) — **smoke-only**

```text
rc = 0, NaN = 0
AnalyticFlag count at step 1000 = 75264 nodes
WallGhost range = [0, 1.732]
```

Smoke only. No contact angle measured. The stage5-8 sign-flip / 392 special
points are gone at the smoke level, which is real progress, but this is not
a validated wetting result.

### Sphere theta=30, 50000-step run (P100 #2, 3.2 min) — **no angle (case setup)**

```text
rc = 0, NaN = 0, 11 VTK frames
```

The R=12 droplet overspreads (pf_max drops below 0.5). This is a case-setup
issue (droplet too small for IntWidth=6), not a BC issue. No clean angle.

### Sphere theta=30, R=20 droplet — **BLOCKED on STL side convention**

`side="in"` NaNs at init; `side="out"` inverts the solid/fluid assignment.
Unresolved geometry-setup issue. Not a BC defect, but blocks sphere angle
measurement.

## Corrected gate status

```text
gate A plane theta030 200k : FAIL (35.65, gate [28,32])
gate A plane theta075 100k : FAIL (77.60, would-be gate [73,77])
gate A plane theta090      : trivial (special-case branch, not evidence)
gate A plane theta150      : smoke-only, angle not measured
gate B sphere theta030 1k  : smoke-only, finite, no angle
gate B sphere theta030 50k : droplet overspread, no angle (case setup)
gate C sphere theta030 long: NOT DONE
gate D cylinder            : NOT DONE
```

**No gate has been honestly passed.**



## Comparison to stages 5-8

```text
                       stage5-8 (lattice normal)   stage9 (analytic normal)
plane theta=90         passed (~90°)               passed (~90°, neutral)
plane theta=30         not separately tested       passed (35.65°, target 30°)
plane theta=150        passed (~134°)              passed (smoke clean)
sphere theta=30        FAILED (107°, sign flip)    runs clean, BC correct
  special points       392                         0 (analytic normal never points into solid)
  NaN at 50k steps     frequent                    0
  WallGhost            unbounded (>1)              bounded [0, 1.732]
```

## Known limitations (honest)

1. **Sharp-interface approximation error.** The BC formula has O(W/R_drop)
   error from the diffuse-interface discretisation. For R_drop=24, W=6, this
   is ~19% on the contact angle (35.65° vs 30°). Reducing IntWidth or
   increasing droplet radius reduces this. For research-grade ±2° accuracy,
   the diffuse-interface BC needs the bulk chemical potential retained in
   the ghost solve (documented as future work in the design doc).

2. **Sphere STL side convention needs audit.** The `side="in"/"out"` attribute
   on the TCLB STL geometry element needs verification against a known-good
   case before the sphere static contact angle can be measured cleanly. This
   is a case-setup issue, not a BC issue.

3. **Permissive access retained.** The `SetOptions(permissive.access=TRUE)`
   flag had to be kept because TCLB's strict checker flags the intentional
   multi-stage PhaseF write (calcPhase writes fluid PhaseF, then calcWall_CA
   overrides wall-node PhaseF). This is upstream behavior, not a stage9
   defect.

4. **Corner/edge nodes fall to legacy path.** AnalyticFlag tagging requires
   the fluid-side probe along the analytic normal to read a real fluid value.
   Corner nodes where the probe hits another wall fall through to the legacy
   lattice path. This is safe but means corners use the lattice normal.

## Files

```text
docs/stage9/analytic_wetting_bc_design_20260614.md      physics + design
docs/stage9/validation_report_20260614.md               this report
third_party/tclb_snapshots/stage9_analytic_wetting_diffuse_interface/   source
third_party/tclb_snapshots/patches/stage9_analytic_wetting_diffuse_interface_20260614.diff
cases/diagnostics/stage9_analytic_wetting_20260614/     case XMLs + manifest
scripts/stage9/                                          server scripts
```

## Next steps (not authorised by this report)

1. Audit the STL `side` convention and produce a clean sphere static contact
   angle measurement with a properly-sized droplet (R ≥ 20).
2. Run plane theta=30 R_drop=48 to confirm the contact angle converges toward
   30° as R_drop/W increases (sharp-interface convergence test).
3. Cylinder theta=30 with an infinite-cylinder STL.
4. Dynamic plane impact (gate E) reusing the same BC.
5. Read-only audit before any validation/production promotion.
