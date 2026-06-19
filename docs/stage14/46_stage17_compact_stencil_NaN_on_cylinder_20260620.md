# Stage 17 finding — compact-stencil WRITE BC NaNs on AnalyticCylinder — 2026-06-20

The compact-ghost wetting BC validated on the flat wall (docs 40-43, WallCompact-
StencilMode=2) does NOT yet run on a curved substrate: it NaNs on the
AnalyticCylinder around step ~1000. This is the real Stage 17 blocker (a BC code
defect on curved geometry), not the angle measurement (doc 45).

```text
status_label: failed_negative_evidence (compact-stencil write diverges on cylinder)
binary f00f8ff7
root (NaN runs): /mnt/usb1t/RUNS/runs/stage17_cyl_compact_20260620/{cyl_t60,cyl_t90,cyl_t120}
```

## What was run
Cylinder cases generated with the compact-stencil Model params merged onto the
stage12 AnalyticCylinder geometry (gen_cyl_compact.py): WallCompactStencilMode=2,
WriteAllowedFlag=1, NormalMode=1, MaxL=3, AnalyticSolidType=2 (cylinder, axis=z,
center 48,48,48, radius 20), CylinderCapInit, radAngle=target on the
AnalyticCylinder zone, M=0.6, IntWidth=3, 12000 steps.

## Result: NaN at ~step 1000, all three angles
```
cyl_t60 / cyl_t90 / cyl_t120 : "Checking P discovered NaN ... Stopping due to Nan value"
each produced only the step-0 (init) VTK; NaN before the step-2000 periodic VTK.
Run lasted ~34 s => NaN around step ~1000-1400 (Failcheck at 1000 caught it).
```

## Control: the OLD wetting BC (stage12, WettingBCMode, NOT compact-stencil) does NOT NaN
The doc-44 smoke (stage12_cap_static_run.py, theta=90, 2000 steps) ran clean
(rc=0, 0 NaN) on the same AnalyticCylinder geometry. So the NaN is specific to
the compact-stencil WRITE path on the curved geometry, not the geometry/init itself.

## Interpretation
The compact-stencil q_s reconstruction (3 fluid nodes on the 7-plane families,
wall-normal projection) is validated on the flat wall but fails on the curved
cylinder mask: some solid-adjacent nodes get a bad q_s (or a degenerate stencil
selection on the curved mask) that accumulates and diverges by ~step 1000. This
is the curved-wall compact-stencil defect -- the same frontier the 2026-06-14
HANDOFF flagged (curved-wall profile/reconstruction). The flat-wall validation did
not exercise it.

## Two branch options for Stage 17

```text
A. Validate the cylinder with the OLD BC first (does NOT NaN). Run theta 60/90/120
   with stage12_cap_static_run.py, measure with golden_cyl (doc 45). If the old BC
   gives correct cylinder angles, that is a usable Stage-17 result NOW, and the
   compact-stencil curved-NaN becomes a separate robustness/quality task.
   [in flight: /mnt/usb1t/RUNS/runs/stage17_cyl_oldbc_20260620]
B. Debug the compact-stencil write NaN on curves (source-level: which solid-
   adjacent node produces the first bad q_s on the cylinder mask; 7-plane stencil
   selection + q_s solve on curved geometry). This is the real fix but requires
   touching TCLB code under the audit rules.
```

## Honest status
The flat-wall wetting BC is validated (docs 40-43). The cylinder GEOMETRY works
(doc 44, old BC). The compact-stencil WRITE path has a curved-wall NaN defect
(this doc). The cylinder ANGLE is measurable (doc 45 calibrated curved measurer).
Next data point: old-BC cylinder angles (branch A, in flight).

## Reproducibility
```text
python3 /home/yuan/gen_cyl_compact.py <root>      # compact-stencil cylinder cases (NaN)
bash /home/yuan/run_cyl17.sh                       # runs them -> NaN ~step 1000
bash /home/yuan/cyl_oldbc.sh                       # old-BC cylinder 60/90/120 (no NaN)
scripts mirrored: repo/scripts/stage13/{gen_cyl_compact.py, run_cyl17.sh, cyl_oldbc.sh}
```
