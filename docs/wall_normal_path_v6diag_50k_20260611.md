# Wall Normal-Path v6 Diagnostic 50k

Date: 2026-06-11

Status: `runtime_sanity / exploratory_not_validation`

## Scope

This note records the 50k gate for the v6 passive normal-path diagnostic lane
in the separated PRE sphere theta030/z48 case. v6 does not change the actual
wall `PhaseF` write. It only adds normal-path geometry and gradient outputs so
the dominant curved-wall path can be audited directly.

This is not a wetting-boundary fix and not validation evidence.

## Source And Build

```text
source = /home/yuan/src/TCLB_clean_wall_normal_path_v6diag_20260611
binary = /home/yuan/src/TCLB_clean_wall_normal_path_v6diag_20260611/CLB/d3q27_pf_velocity_q27_geometric/main
binary_sha256 = bef819acdf0101bb2f109e1f5cfb225c81339e3aa7df48c3a03a59fe0119b06f
provenance = /mnt/8A0E24070E23EAC1/runs/tclb_wall_normal_path_v6diag_provenance_20260611
local_patch = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\patches\wall_normal_path_v6diag_20260611\source_diff_after_build.patch
```

Build route:

```text
make d3q27_pf_velocity_q27_geometric/source
export PATH=/usr/local/cuda-12.6/bin:$PATH
make -C CLB/d3q27_pf_velocity_q27_geometric
```

## Added Passive Quantities

```text
WallH
WallGeomNormal
WallGrad1
WallGrad2
WallGradTangentVec
WallNormalCoeff1
WallNormalCoeff2
WallActualMinusProfile
WallActualMinusRaw
```

These quantities are diagnostic outputs only. They do not alter the wall write
or solver update.

## 50k Curved z48 Gate

Run:

```text
remote =
  /mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_theta030_z48_gap24_outer90_sphere11_normal_path_v6diag_50k_20260611/theta030
local =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_z48_gap24_outer90_sphere11_normal_path_v6diag_50k_20260611
```

Case:

```text
domain = 80 x 80 x 180
VTI cell dims = 96 x 80 x 180
R_drop = 24
R_solid = 24
solid_center_z = 48
bottom_gap = 24 = 4W
default/OuterDomain radAngle = 90d
SolidSphere radAngle = 11d
M = 0.2
IntWidth = 6
steps = 50000
VTK = 0, 50000
```

Return codes:

```text
solver = 0
finiteness gate = 0
PRE sphere postprocess = 0
wall diagnostic v6 postprocess = 0
surface-film audit = 0
morphology gallery = 0
run.stderr = empty
```

Curated artifact:

```text
remote tar =
  /mnt/8A0E24070E23EAC1/runs/curated_pre2025_sphere_normal_path_v6diag_50k_no_raw.tar.gz
remote tar sha256 =
  1f95c081cb66120c1f7918f969f66e16e369e64c82c66b6c23d051e7978f27a9
local raw .vti/.pvti/.pri count = 0
remote raw VTI/PVTI/PRI count = 4
remote run size = about 1.3 GiB
```

## Final 50k Metrics

| metric | value |
|---|---:|
| fit contact angle | 107.125719 deg |
| H1-H2 relative error | 104.719123% |
| measured Hmax | 64.153060 lu |
| measured H1-H2 | 40.153060 lu |
| target Hmax | 43.613732 lu |
| target H1-H2 | 19.613732 lu |
| fluid phase drift | -0.618564% |
| fluid rho drift | -0.605953% |
| max Mach | 4.91852e-4 |
| PhaseField nonfinite | 0 |
| U nonfinite | 0 |
| Rho nonfinite | 0 |
| z-min outside-sphere phi fraction | 0 |
| lower90 phi fraction | 0.0316102 |
| bottom120 phi fraction | 0.00812668 |

## Wall Diagnostics

| metric | step 0 | step 50000 |
|---|---:|---:|
| wall count | 135160 | 135160 |
| fluid count | 1247240 | 1247240 |
| normal-path wall count | 10256 | 10256 |
| raw `WallPhasePred > 1` count | 64 | 1920 |
| profile/unified `> 1` count | 0 | 0 |
| actual wall `PhaseField > 1` count | 0 | 0 |
| fluid `PhaseField > 1` count | 0 | 0 |
| normal-path raw `WallPhasePred` max | 1.7954629 | 1.4480228 |
| normal-path unified-profile max | 0.7406001 | 0.9999977 |
| normal-path `|WallGradTangentVec|` max | 0.1487766 | 0.1354157 |
| normal-path `WallNormalCoeff1` min | -4.2769e-5 | -0.1573572 |
| normal-path `WallNormalCoeff1` max | 0.1714348 | -3.3740e-6 |
| normal-path `WallActualMinusProfile` max | 1.11e-16 | 0 |
| normal-path `WallActualMinusRaw` min | -1.0548628 | -0.6881894 |
| normal-path `WallActualMinusRaw` max | 0.1208893 | 0.1096296 |

## Figures

```text
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_z48_gap24_outer90_sphere11_normal_path_v6diag_50k_20260611\theta030\analysis_morphology\theta030_frame_gallery.png
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_z48_gap24_outer90_sphere11_normal_path_v6diag_50k_20260611\theta030\analysis_wall_diag_v6\figures\pre2025_sphere_v6_normal_path_step00050000.png
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_z48_gap24_outer90_sphere11_normal_path_v6diag_50k_20260611\theta030\analysis_wall_diag_v6\figures\pre2025_sphere_wall_diag_step00050000.png
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_z48_gap24_outer90_sphere11_normal_path_v6diag_50k_20260611\theta030\analysis_surface_film\surface_film_audit_timeseries.png
```

## Interpretation

Supported findings:

```text
1. v6 is a valid passive diagnostic build for the separated z48 case through
   50k steps. Solver and postprocess return codes are all 0, nonfinite counts
   are 0, and max Mach remains small.
2. The actual wall PhaseF still equals the profile/unified-profile write on
   the normal curved-wall path: WallActualMinusProfile is zero to roundoff.
3. The raw geometric formula still predicts overbounded wall values, but those
   raw values are not the stored wall PhaseF in this lane.
4. The macroscopic low-angle wetting response is still wrong at 50k:
   fitted angle is 107.13 deg and H1-H2 error is 104.72%.
5. Therefore the remaining failure should be framed as a profile/unified
   curved-wall reconstruction problem, not as direct raw geometric overrun
   contaminating PhaseF.
```

## Next Step

Do not extend v6 as a fix. The next source candidate should be preceded by a
read-only formula audit of the profile/unified curved-wall reconstruction:

```text
1. derive the wall ghost from a signed, contact-angle-consistent relation using
   local interface normal and wall normal
2. keep boundedness/profile consistency explicit, not hidden by clamp-only logic
3. make normal, special, and correction branches share one reconstruction
   contract only after the normal path is correct
4. gate any write-candidate first on flat-wall theta030/090/150, then on the
   separated z48 theta030 50k case
```

Claim remains `runtime_sanity / exploratory_not_validation`.
