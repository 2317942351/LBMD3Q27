# Wall Normal-Path v6 M0.1 Control 50k

Date: 2026-06-11

Status: `runtime_sanity / exploratory_not_validation`

## Scope

This note records a same-binary mobility-control run for the separated PRE
sphere theta030 case. The only intended numerical-setup delta from the v6/M0.2
50k gate is:

```text
M = 0.2 -> 0.1
output path changed
```

This is not validation and not a source fix. It tests whether the previous
v6/M0.2 50k discrepancy was mainly a mobility/time-scale artifact.

## Source And Case

```text
source =
  /home/yuan/src/TCLB_clean_wall_normal_path_v6diag_20260611
binary =
  /home/yuan/src/TCLB_clean_wall_normal_path_v6diag_20260611/CLB/d3q27_pf_velocity_q27_geometric/main
binary_sha256 =
  bef819acdf0101bb2f109e1f5cfb225c81339e3aa7df48c3a03a59fe0119b06f
remote =
  /mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_theta030_z48_gap24_outer90_sphere11_normal_path_v6diag_M0p1_50k_20260611/theta030
local =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_z48_gap24_outer90_sphere11_normal_path_v6diag_M0p1_50k_20260611
compare =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_z48_v6_M_control_compare_20260611
```

Case settings:

```text
domain = 80 x 80 x 180
VTI cell dims = 96 x 80 x 180
R_drop = 24
R_solid = 24
solid_center_z = 48
bottom_gap = 24 = 4W
default/OuterDomain radAngle = 90d
SolidSphere radAngle = 11d
M = 0.1
IntWidth = 6
steps = 50000
VTK = 0, 50000
```

## Execution

```text
solver rc = 0
finiteness gate rc = 0
PRE sphere postprocess rc = 0
wall diagnostic v6 postprocess rc = 0
surface-film audit rc = 0
morphology gallery rc = 0
run.stderr = empty
solver duration = 314.78 s
remote raw VTI/PVTI/PRI count = 4
local raw VTI/PVTI/PRI count = 0
curated tar sha256 =
  17e500fcc592c89b747718d39b3ebee7cf8cf8218753d23262609bb6b9c452bb
```

## Same-Binary M Control

| metric at 50k | v6 M0.2 | v6 M0.1 |
|---|---:|---:|
| fitted contact angle | 107.125719 deg | 110.463991 deg |
| H1-H2 relative error | 104.719123% | 107.240435% |
| Hmax relative error | 47.093718% | 48.227589% |
| measured H1-H2 | 40.153060 lu | 40.647584 lu |
| fluid phase drift | -0.618564% | -0.495228% |
| fluid rho drift | -0.605953% | -0.485131% |
| max Mach | 4.91852e-4 | 4.86702e-4 |
| nonfinite counts | 0 | 0 |
| lower90 phi fraction | 0.0316102 | 0.0133860 |
| bottom120 phi fraction | 0.00812668 | 0.00210920 |
| z-min outside-sphere phi fraction | 0 | 0 |
| normal-path raw `WallPhasePred` max | 1.448023 | 1.484613 |
| normal-path unified/profile max | 0.9999977 | 0.9999936 |
| normal-path `WallActualMinusProfile` max | 0 | 0 |
| wall `PhaseField > 1` count | 0 | 0 |
| fluid `PhaseField > 1` count | 0 | 0 |

The comparison table is also saved as:

```text
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_z48_v6_M_control_compare_20260611\v6_M_control_selected_metrics.csv
```

## Figures

```text
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_z48_v6_M_control_compare_20260611\v6_M_control_metrics.png
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_z48_v6_M_control_compare_20260611\v6_M_control_morphology_montage.png
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_z48_v6_M_control_compare_20260611\v6_M_control_wall_normal_path_montage.png
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_z48_v6_M_control_compare_20260611\profile_reference_vs_v6_50k_context.png
```

## Interpretation

Supported findings:

```text
1. Reducing M from 0.2 to 0.1 improves numerical drift and reduces the lower
   hemisphere/bottom film fractions at 50k.
2. The macroscopic curved-sphere wetting response remains wrong. Both same
   v6 binary runs stay around 107-110 deg apparent angle and above 100% H1-H2
   error for a theta030 target.
3. M0.1 does not remove the normal-path wall reconstruction issue. The actual
   wall value still equals the bounded profile/unified value, while the raw
   geometric diagnostic still predicts values above 1.
4. Therefore the main 50k discrepancy is not explained by using M=0.2 instead
   of M=0.1. Lower mobility changes relaxation rate and film amount, but not
   the failure mode.
```

The existing z48/profile M0.1 200k run is useful background only. It uses the
same geometry and M, but it is not the same v6 passive-diagnostic binary/output
lane, and its postprocess angle extraction differed at early frames. It must
not be treated as a direct continuation of this v6 M0.1 50k run.

## Next Step

Do not extend the v6 M-control lane as a fix. The next source work should
return to the curved-wall reconstruction contract:

```text
1. derive a signed, contact-angle-consistent wall ghost relation using local
   interface normal and wall normal
2. keep profile boundedness explicit but not as a hidden clamp-only cure
3. verify with flat-wall theta030/090/150 first
4. then run the separated z48/gap24 theta030 50k gate
```

Claim remains `runtime_sanity / exploratory_not_validation`.
