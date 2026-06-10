# Wall Geometric Profile 600k Extension 2026-06-10

Status: `exploratory_not_validation`

This note records the theta030 reduced PRE-sphere profile-lane extension from
200k to 600k. It is a trend and morphology diagnostic only. It does not promote
the profile lane to validation, calibration, production, or publication-ready
status.

## Case

```text
remote_root =
  /mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_600k_20260610
local_artifact =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_600k_20260610
local_live_artifact =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_600k_live_20260610
case_xml =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_600k_20260610\theta030\pre2025_sphere_tableII_theta030.xml
runner =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_run_pre2025_sphere_profile_600k_20260610.sh
binary =
  /home/yuan/src/TCLB_clean_wall_profile_diag_20260610/CLB/d3q27_pf_velocity_q27_geometric/main
binary_sha256 =
  59e03a6233744f00189b6241551fab30d1a53867a90bee582295f9666899159a
```

Parameters:

```text
domain = 80 x 80 x 140
R_drop = 24
R_solid = 24
target theta = 30 deg
TCLB radAngle = 11 deg
M = 0.1
IntWidth = 6
Density_h/l = 1 / 0.001
Viscosity_h/l = 0.09 / 0.1
tauUpdate = 3
sigma = 5e-5
steps = 600000
VTK interval = 50000
diagnostics =
  SpecialBoundaryPoint, WallPfF, WallGradTangent, WallTanCoeff,
  WallPhasePred, WallBCPath, WallPhaseProfilePred, WallProfileDelta
```

The 600k XML is identical in physics parameters to the 200k profile run except
for `Solve Iterations=600000` and `VTK Iterations=50000`.

## Execution

```text
solver rc = 0
PRE postprocess rc = 0
wall diagnostic postprocess rc = 0
morphology gallery rc = 0
run.done = present
nonfinite = 0
raw local .vti/.pvti/.pri count = 0
```

Remote raw VTI/PVTI files remain on HM570. The local curated artifact was
extracted from:

```text
/mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_600k_20260610/curated_profile_600k_theta030.tar.gz
```

## Selected Trend

```text
step     fit angle   H1-H2 error   H1-H2      fluid phase drift   phase max       max Mach
0        163.60 deg  142.13%       47.4898    0.00%               1.0             0
200000    54.87 deg   39.45%       27.3512   -1.53%               1.00000043      2.18e-4
300000    41.84 deg   19.08%       23.3551   -1.95%               1.00000012      1.55e-4
400000    36.11 deg    6.39%       20.8677   -2.27%               1.0             1.19e-4
450000    34.14 deg    1.63%       19.9326   -2.42%               1.0             1.06e-4
500000    32.33 deg    2.46%       19.1309   -2.56%               1.0             9.63e-5
550000    30.66 deg    6.13%       18.4117   -2.69%               1.0             9.10e-5
600000    29.56 deg    9.47%       17.7559   -2.82%               1.0             8.35e-5
```

Best H1-H2 agreement occurs around step `450000`, not at the final frame:

```text
step = 450000
fit angle = 34.14 deg
H1-H2 error = 1.63%
Hmax error = 0.73%
fluid phase/rho drift = -2.42% / -2.38%
max Mach = 1.06e-4
```

The final 600k frame gives the closest fitted contact angle:

```text
step = 600000
fit angle = 29.56 deg
H1-H2 error = 9.47%
Hmax error = 4.26%
fluid phase/rho drift = -2.82% / -2.77%
max Mach = 8.35e-5
```

## Wall Diagnostics

The raw original geometric-wall diagnostic remains overbounded, but the actual
profile wall value stays bounded after the transient window:

```text
step     raw WallPhasePred>1   actual wall phi>1   fluid phi>1   raw pred max   profile max
200000   4478                  52                  132           1.70482        1.00000022
300000   5412                  34                  34            1.71754        1.00000006
350000   5812                  0                   0             1.68207        1.0
400000   6106                  0                   0             1.67186        1.0
500000   6552                  0                   0             1.65681        1.0
600000   7074                  0                   0             1.63463        1.0
```

This supports the earlier causal diagnosis: the original low-angle normal
geometric extrapolation still predicts order-one wall overshoot, while the
profile wall write suppresses actual wall and fluid `PhaseField>1`.

## Interpretation

Supported findings:

```text
1. The 200k profile result was not fully relaxed. From 200k to 400k, H1-H2
   error dropped from 39.45% to 6.39%, and the fitted angle dropped from
   54.87 deg to 36.11 deg.
2. The profile lane remains numerically bounded in the wall-write sense through
   600k: after 350k, actual wall/fluid phi>1 counts are zero, while raw
   WallPhasePred still exceeds one in thousands of wall cells.
3. The final fitted angle near 30 deg is not enough to declare success. H1-H2
   is closest to target around 450k and then crosses below the target as
   fluid phase/rho drift continues to accumulate.
4. The morphology gallery still shows local contact-line/skirt features during
   the relaxation path. The global circle-fit angle and H1-H2 metric must not
   be used alone as validation criteria.
5. A separate near-surface film audit confirms the user-observed post-200k
   downslope migration. This is not a visual-only concern: lower-hemisphere
   and z-min liquid metrics grow monotonically through the saved 600k window.
```

Current diagnosis:

```text
The profile lane fixes the order-one wall ghost and makes the long run stable,
but the wetting response is time-sensitive and coupled to mass drift and a
bottom-film failure mode. The case does not justify treating this exact profile
formula as a calibrated wetting boundary. It is a useful diagnostic baseline
for geometry isolation and the next signed/profile-consistent geometric
reconstruction.
```

## Bottom-Film Audit

The z-min enhanced surface-film audit is stored at:

```text
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_600k_20260610\theta030\analysis_surface_film_zmin
```

Key metrics:

```text
step     lower90 shell fraction   bottom120 fraction   z-min outside-sphere fraction   z-min outside phi sum
200000   0.1048                  0.0566               0.0536                         1263.91
400000   0.2067                  0.1397               0.1508                         4866.80
600000   0.2650                  0.1839               0.2288                         8295.52
```

At 600k, the z-min outside-sphere maximum phase is `0.99986`, and the
theta>=150 deg shell maximum is also `0.99986`. Therefore the late morphology
contains near-pure liquid on the lower/bottom side; this is a quantified
failure mode, not just an unsettled diffuse tail.

Geometry caveat:

```text
The reduced 80x80x140 setup places the solid sphere at center z=24 with
R_solid=24, so the sphere touches the z-min outer-domain wall. Both the outer
domain and the solid sphere are TCLB Wall nodes under one global radAngle=11d.
For a strongly wetting low-angle case, this can contaminate the intended
solid-sphere wetting response by coupling the sphere underside to the bottom
domain wall.
```

Recommended next checks:

```text
1. Run a geometry-isolation control with the same physical parameters but lift
   the solid sphere to center z=32 and the droplet center to z=80. This leaves
   an 8 lu gap between the sphere and z-min wall while preserving initial
   tangency at the sphere top.
2. Re-run or postprocess a late-time window with local contact-angle extraction
   near the contact line, not only global circle fitting.
3. Compare 450k and 600k morphology with a mass-corrected or volume-normalized
   height target to separate wetting response from droplet-volume drift.
4. Test the next signed/contact-angle-consistent geometric reconstruction on
   the same 80x80x140 theta030 case before any full Table-II sweep.
```

## Key Artifacts

```text
trend plot =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_600k_20260610\summary_plots\profile_600k_trends.png
morphology gallery =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_600k_20260610\theta030\analysis_morphology\theta030_frame_gallery.png
selected metrics =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_600k_20260610\summary_plots\profile_600k_selected_metrics.csv
PRE metrics =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_600k_20260610\theta030\analysis_pre2025_sphere\pre2025_sphere_metrics.csv
wall diagnostics =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_600k_20260610\theta030\analysis_wall_diag\pre2025_sphere_wall_diag_summary.csv
surface-film audit =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_600k_20260610\theta030\analysis_surface_film_zmin\surface_film_audit_metrics.csv
surface-film trend plot =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_600k_20260610\theta030\analysis_surface_film_zmin\surface_film_audit_timeseries.png
surface-film polar heatmap =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_600k_20260610\theta030\analysis_surface_film_zmin\surface_film_polar_heatmap.png
```
