# Wall Normal-Path v6 Diagnostic Smoke

Date: 2026-06-11

Status: `runtime_sanity / exploratory_not_validation`

## Scope

This note records the v6 passive diagnostic lane for the separated PRE sphere
theta030/z48 case. v6 does not change the actual wall `PhaseF` write. It only
adds normal-path geometry and gradient outputs so the dominant curved-wall path
can be audited directly.

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

The first compile attempt without the CUDA path failed with `nvcc: not found`;
the successful build used the explicit CUDA path above.

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

These quantities are diagnostic outputs only. They do not enter
`calcWallPhase()` and do not alter the solver update.

## 100-Step Smoke

Run:

```text
remote =
  /mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_theta030_z48_gap24_outer90_sphere11_normal_path_v6diag_smoke_20260611/theta030
local =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_z48_gap24_outer90_sphere11_normal_path_v6diag_smoke_20260611
```

Case:

```text
domain = 80 x 80 x 180
R_drop = 24
R_solid = 24
solid_center_z = 48
bottom_gap = 24 = 4W
default/OuterDomain radAngle = 90d
SolidSphere radAngle = 11d
M = 0.2
IntWidth = 6
steps = 100
VTK = 0, 100
```

Return codes:

```text
solver = 0
finiteness gate = 0
wall diagnostic postprocess = 0
run.stderr = empty
nonfinite = 0
```

Curated artifact:

```text
remote tar =
  /mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_theta030_z48_gap24_outer90_sphere11_normal_path_v6diag_smoke_20260611/curated_pre2025_sphere_normal_path_v6diag_smoke_no_raw.tar.gz
remote tar sha256 =
  44834aa19c631e0600bfae87cb8b7436fef37dec143d30ff3374056b4adb6872
local raw .vti/.pvti/.pri count = 0
remote raw VTI = 2 files, about 1.27 GiB total because v6 outputs several new vector diagnostics
```

## Key Metrics

| metric | step 0 | step 100 |
|---|---:|---:|
| wall count | 135160 | 135160 |
| fluid count | 1247240 | 1247240 |
| normal-path wall count | 10256 | 10256 |
| wall raw `WallPhasePred > 1` count | 64 | 180 |
| wall profile/unified `> 1` count | 0 | 0 |
| actual wall `PhaseField > 1` count | 0 | 0 |
| fluid `PhaseField > 1` count | 0 | 0 |
| normal-path raw `WallPhasePred` max | 1.7954629 | 1.3824500 |
| normal-path unified-profile max | 0.7406001 | 0.9769706 |
| normal-path `|WallGradTangentVec|` max | 0.1487766 | 0.1515973 |
| normal-path `WallNormalCoeff1` min | -4.2769e-5 | -0.1039935 |
| normal-path `WallNormalCoeff1` max | 0.1714348 | 4.0124e-10 |
| normal-path `WallActualMinusProfile` max | 1.11e-16 | 0 |
| normal-path `WallActualMinusRaw` min | -1.0548628 | -0.6199535 |
| normal-path `WallActualMinusRaw` max | 0.1208893 | 0.1312806 |
| max Mach | 0 | 1.9545e-4 |
| nonfinite count | 0 | 0 |

Figures:

```text
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_z48_gap24_outer90_sphere11_normal_path_v6diag_smoke_20260611\pre2025_sphere_wall_diag_step00000100.png
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_z48_gap24_outer90_sphere11_normal_path_v6diag_smoke_20260611\pre2025_sphere_v6_normal_path_step00000100.png
```

## Interpretation

Supported findings:

```text
1. v6 is a valid passive diagnostic build and the 100-step separated-geometry
   smoke is finite.
2. In this build, actual wall PhaseF equals the profile/unified-profile
   reconstruction on the normal curved-wall path: WallActualMinusProfile is
   zero to roundoff.
3. The raw geometric prediction is still strongly different from the actual
   wall write. At step 100, normal-path raw WallPhasePred reaches 1.38245,
   while the actual/profile wall value is bounded and the normal-path unified
   profile max is 0.97697.
4. Therefore the current z48 morphology error is not caused by raw geometric
   overrun being directly written to wall PhaseF. The next formula problem is
   that the bounded/profile write does not impose the desired low-angle curved
   wetting response.
```

## Next Step

Run a 50k passive v6 gate with only `VTK=0,50000` to see whether the normal-path
raw/profile gap and local gradient signs persist after early interface
relaxation. This remains diagnostic only and should not be promoted beyond
`runtime_sanity / exploratory_not_validation`.
