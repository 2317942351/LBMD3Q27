# Stage 17 — old-BC cylinder angles (branch A): runs clean but inaccurate — 2026-06-20

Branch A of doc 46: validate the cylinder with the OLD wetting BC (stage12
WettingBCMode, which does NOT NaN on the cylinder) using the calibrated curved
measurer (doc 45). Result: the old BC runs clean but its cylinder angles are
inaccurate (beyond the measurer's +/-4 deg uncertainty). So branch A is NOT a
usable Stage-17 result; the path remains branch B (fix the compact-stencil curved
NaN) or accept the old BC's limited accuracy.

```text
status_label: exploratory_not_validation (old BC, approximate measurer)
binary f00f8ff7; stage12_cap_static_run.py; M=0.6; IntWidth=3; 10000 steps
root: /mnt/usb1t/RUNS/runs/stage17_cyl_oldbc_20260620
measurer: golden_cyl.py, beta=30 calibration, ~+/-4 deg uncertainty
```

## Calibrated cylinder angle (old BC, final frame, 10000 steps)

| target | calibrated measured | error |
|---|---|---|
| 60  | 66.7  | +6.7  |
| 90  | 98.5  | +8.5  |
| 120 | 105.5 | -14.5 |

Errors exceed the measurer's +/-4 deg uncertainty, so this is NOT a clean
validation. Caveats are layered: (a) the old BC was never the project's intended
final BC (the compact-stencil was built to replace it); (b) the measurer is
approximate (beta=30 calibration, real droplets differ); (c) 10000 steps may
under-settle the obtuse case (doc 41/42 showed obtuse relaxation is slow). Either
way, the old BC does not give a trustworthy cylinder angle.

## Stage 17 consolidated status (docs 44-47)

```text
- Cylinder GEOMETRY works: analytic cylinder, droplet on top, no init NaN (doc 44).
- Curved-wall ANGLE MEASURER built + self-validated, +/-4 deg (doc 45).
- Compact-stencil WRITE BC (the validated flat-wall BC) NaNs on the cylinder at
  ~step 1000 (doc 46) -- the real Stage 17 blocker.
- Old BC runs on the cylinder but is inaccurate (~+7..-15 deg, this doc) -- not the path.
```

## The single remaining Stage 17 work item

```text
Debug the compact-stencil WRITE NaN on curved geometry (branch B, doc 46):
which solid-adjacent node first produces a bad q_s on the AnalyticCylinder mask;
how the 7-plane fluid-node stencil selection + q_s solve behave on a curved wall
vs the flat wall. Source-level TCLB work under the audit rules (AGENTS.md).
Until that is fixed, the cylinder (and sphere) cannot be angle-validated with the
project's chosen BC.
```

## Reproducibility
```text
bash /home/yuan/cyl_oldbc.sh   # old-BC cylinder 60/90/120, M=0.6, 10k steps
python3 /home/yuan/golden_cyl.py measure <final_pvti>
```
