# Wall Geometric Profile Diagnostic Stage 4 2026-06-10

Status: `runtime_sanity`

This note records the profile-consistent diagnostic candidate for TCLB
`d3q27_pf_velocity_q27_geometric`. It is not validation evidence and does not
authorize publication-facing claims.

## Profile Lane

```text
source =
  /home/yuan/src/TCLB_clean_wall_profile_diag_20260610
base =
  copied from /home/yuan/src/TCLB_clean_wall_diag_20260610
base_commit =
  ded67cd768cf7e727bd078af139e3ec7895076e5
binary =
  /home/yuan/src/TCLB_clean_wall_profile_diag_20260610/CLB/d3q27_pf_velocity_q27_geometric/main
binary_sha256 =
  59e03a6233744f00189b6241551fab30d1a53867a90bee582295f9666899159a
options =
  q27=TRUE, geometric=TRUE, staircaseimp=FALSE, isograd=FALSE, tprec=FALSE
provenance =
  /mnt/8A0E24070E23EAC1/runs/tclb_wall_profile_diag_provenance_20260610
```

The profile lane preserves the raw diagnostic `WallPhasePred` from the original
normal geometric branch:

```text
PhaseF_wall_raw = pf_f + tan(pi/2 - radAngle) * grad_tangent * 2h
```

The actual normal geometric wall write is replaced by the same
free-energy/profile-like quadratic reconstruction already used by TCLB's
surface-energy fallback branch:

```text
a = -h * (4.0/IntWidth) * cos(radAngle)
PhaseF_wall_profile =
  (1 + a - sqrt((1+a)*(1+a) - 4*a*pf_f))/(a+1e-12) - pf_f
```

Additional diagnostics:

```text
WallPhaseProfilePred
WallProfileDelta
```

No hard bounded clamp was added in this lane.

## Flat/Curved Health Gate

Run roots:

```text
/mnt/8A0E24070E23EAC1/runs/tclb_wall_geom_diag_profile_flat_curved_20260610
/mnt/8A0E24070E23EAC1/runs/tclb_wall_geom_diag_profile_rad011_1000_20260610
/mnt/8A0E24070E23EAC1/runs/tclb_wall_geom_diag_profile_curved_rad011_10k_20260610
```

Local artifacts:

```text
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\wall_geom_diag_profile_flat_curved_20260610
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\wall_geom_diag_profile_rad011_1000_20260610
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\wall_geom_diag_profile_curved_rad011_10k_20260610
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\wall_geom_diag_profile_summary_20260610
```

All solver and postprocess return codes were `0`, with `nonfinite_count=0`.
Raw `.vti/.pvti/.pri` files were kept remote; local artifacts are curated.

Step-50 profile values:

```text
case              raw pred>1  actual wall phi>1  profile pred>1  fluid phi>1  raw pred max  profile max   max Mach
flat_theta011     2032        188                188             860          1.33772       1.00001165   1.15e-4
curved_theta011   120         0                  0               2204         1.28892       1.0          1.81e-4
flat_theta030     1272        192                192             872          1.00234       1.00001273   1.03e-4
curved_theta030   0           0                  0               2228         1.0           1.0          1.72e-4
flat_theta090     208         208                208             940          1.00002131    1.00002131   1.68e-5
curved_theta090   0           0                  0               2324         1.0           1.0          6.78e-5
```

The flat-wall `~1e-5` exceedance also appears for `theta090`, so it is not the
same low-angle tangent-gradient amplification. In the 1000-step profile run,
both flat and curved `radAngle=11` had actual wall and fluid `PhaseField>1`
counts equal to zero after the initial frame. In the 10000-step curved
`radAngle=11` run, actual wall and fluid `PhaseField>1` remained zero through
step `10000`, while raw `WallPhasePred` continued to exceed one.

## PRE Sphere Theta030 Comparison

The profile candidate was then tested on the reduced PRE Table II sphere
geometry with the same diagnostic setup that previously exposed the wall ghost:

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
```

Run roots:

```text
/mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_50k_20260610
/mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_200k_20260610
```

Local artifacts:

```text
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_50k_20260610
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_200k_20260610
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_profile_candidate_summary_20260610
```

The 50k and 200k sphere runs completed with solver, PRE postprocess, and wall
diagnostic return code `0`, no NaN stop, and `max_nonfinite_count=0`.

Final 200k comparison:

```text
case              H1-H2 err  fit angle  fluid phase drift  fluid rho drift  phase_max   max Mach
baseline M0.1 W6  28.30%     46.08 deg  -2.79%             -2.74%           1.43189     5.96e-4
baseline M0.2 W6  19.32%     43.76 deg  -3.51%             -3.45%           1.42738     6.68e-4
baseline M0.2 W8  17.47%     42.95 deg  -3.23%             -3.18%           1.25402     7.73e-4
profile  M0.1 W6  39.45%     54.87 deg  -1.53%             -1.51%           1.00000043  5.72e-4
```

Profile final wall diagnostics at step `200000`:

```text
raw WallPhasePred>1 count      = 4478
actual wall PhaseField>1 count = 52
fluid PhaseField>1 count       = 132
raw WallPhasePred max          = 1.70482044
WallPhaseProfilePred max       = 1.00000022
actual wall PhaseField max     = 1.00000022
fluid PhaseField max           = 1.00000043
```

The remaining `>1` counts are `~1e-7`-level numerical exceedances, not the
previous order-one wall ghost overrun.

## Interpretation

Supported findings:

```text
1. The profile candidate is a real wall-write change, not a postprocess
   artifact: raw WallPhasePred stays overbounded while actual wall PhaseField
   stays near one.
2. It passes the flat/curved low-angle health gate as a runtime-sanity
   candidate.
3. It strongly reduces global PhaseField overshoot and improves 200k bulk
   fluid phase/rho drift for the theta030 M0.1 W6 sphere case.
4. It does not improve the theta030 sphere morphology or fitted contact angle.
   At 200k, H1-H2 error and fitted angle are worse than the earlier baseline
   M0.1 W6 and M0.2 W6/W8 controls.
```

Therefore the current profile lane is not a sufficient wetting-boundary fix.
It isolates the wall-ghost problem, but it changes the effective wetting
response toward a more hydrophobic apparent state in this reduced sphere case.

## Next Step

Do not extend this exact profile formula to longer or full Table-II runs as a
calibration solution.

The next defensible implementation direction is a signed/profile-consistent
geometric reconstruction that preserves the target contact-angle relation more
directly instead of replacing the normal geometric branch wholesale with the
surface-energy fallback expression. A useful next diagnostic should compare:

```text
1. profile lane from this stage,
2. baseline raw geometric lane,
3. a signed contact-angle profile reconstruction,
4. optionally the bounded clamp only as a localization control,
```

on the same flat/curved health gate and the theta030 sphere 50k/200k metrics.

Claim limit:

```text
runtime_sanity / exploratory_not_validation only.
Not PRE reproduction, not validation_candidate, and not publication-ready.
```
