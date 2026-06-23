# Stage 17 smoke — cylinder static θ=90 init works (blockers 1&2 cleared) — 2026-06-20

First geometric-extension smoke test following the flat-wall gate closure (doc 43).
The two HANDOFF (2026-06-14) blockers for curved geometry are both CLEARED by the
current binary + analytic-cylinder geometry.

```text
status_label: runtime_sanity (smoke; no angle validation yet)
binary f00f8ff7; cylinder via stage12_cap_static_run.py (AnalyticCylinder zone,
  NOT STL -> sidesteps the STL side-convention blocker)
root: /mnt/usb1t/RUNS/runs/stage17_cyl_smoke_20260620/cyl_t90
params: solid_center (48,48,48), solid_radius 20, axis=z, vol_r=16, M=0.3, W=3,
  target theta=90, 2000 steps
```

## Result
- run_rc=0, **0 NaN, 0 Inf**, PhaseField in [0,1], 2000 steps in ~41 s.
- ASCII map (z-centre slice): droplet cap sits ON TOP of the cylinder
  (cap from y~68..92, cylinder interior reads q=1 via analytic solid-phase mirror).
  Liquid probe initialised at y=72 (above cylinder top y=68). Correct configuration.

## Blocker status (vs HANDOFF.md 2026-06-14)
```text
Blocker 1 (STL side="out" inverts geometry): CLEARED -- analytic cylinder
  (AnalyticCylinder zone) is used, no STL, no side convention.
Blocker 2 (closed-surface NaN at init): CLEARED -- current compact-stencil binary
  f00f8ff7 initialises the analytic cylinder with no NaN (the Stage-9 defect that
  NaN'd closed surfaces is gone).
```

## What this does NOT validate (honest)
- The contact ANGLE on the cylinder is not measured here (the flat-wall bbox
  measurer does not apply to a curved substrate). A curved-wall angle measurer
  (contour + PCA tangent, e.g. stage12_curved_angle.py) must be built and
  self-validated against an analytic cylinder cap, exactly as golden2.py was for
  the flat wall (doc 40), before any cylinder angle claim.
- This smoke used the Stage-12 XML (old wetting-BC params), not necessarily the
  compact-ghost WallCompactStencil write path. The next cylinder runs must enable
  WallCompactStencilMode=2 (the validated flat-wall BC) on the AnalyticCylinder.

## Next (Stage 17 proper)
```text
1. Build + self-validate a curved-wall contact-angle measurer (analytic cylinder
   cap of known theta -> measure -> recover), analogous to golden2.py.
2. Run cylinder static theta = 60 / 90 / 120 with WallCompactStencilMode=2 on the
   AnalyticCylinder, M=0.3 (or 0.6 for faster relaxation), measure with the
   validated curved measurer.
3. Then sphere static, then low-We impact.
```

## Reproducibility
```text
python3 /home/yuan/stage12_cap_static_run.py cyl_t90 cylinder 90 2000 \
  --root /mnt/usb1t/RUNS/runs/stage17_cyl_smoke_20260620 \
  --binary /home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main \
  --mobility 0.3 --int-width 3 --force
```
