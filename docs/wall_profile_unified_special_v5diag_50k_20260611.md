# Wall Profile Unified-Special v5 Diagnostic 50k

Date: 2026-06-11

Status: `runtime_sanity / exploratory_not_validation`

## Scope

This note records the v5 source candidate for the separated PRE sphere
theta030/z48 diagnostic. The goal was narrow:

```text
unify special/correction wall ghost reconstruction
add passive diagnostics for nearby fluid sampling and unified profile prediction
compare against v3 at 50k
```

This is not validation evidence and not a completed wetting-boundary fix.

## Source And Build

```text
source = /home/yuan/src/TCLB_clean_wall_profile_unified_special_v5diag_20260611
binary = /home/yuan/src/TCLB_clean_wall_profile_unified_special_v5diag_20260611/CLB/d3q27_pf_velocity_q27_geometric/main
valid_binary_sha256 = f23fc0809c2cdaa1845f843fc81442bcf9614c8bb7b957bf47d95c662bf48e09
provenance = /mnt/8A0E24070E23EAC1/runs/tclb_wall_profile_unified_special_v5diag_provenance_20260611
local_patch = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\patches\wall_profile_unified_special_v5diag_20260611\source_diff_after_build.patch
```

Important build audit:

```text
first make -C CLB/d3q27_pf_velocity_q27_geometric build = superseded_invalid_no_regeneration
invalid first hash = 895f9bc3bdd8fbf2c6a9324bef8a152fee5a02388c4a48f74541ace9ca2f0ae7
valid build route = make d3q27_pf_velocity_q27_geometric/source, then make -C CLB/d3q27_pf_velocity_q27_geometric
source_regen.returncode = 0
build_v5.returncode = 0
```

Generated-code grep confirms the v5 symbols are present in `Dynamics.c`,
`Dynamics_sp.c`, `Lattice.cu`, `Lists.cpp`, and `SUMMARY`.

## Source Changes

Actual write changes:

```text
NORMAL_POINTING_INTO_SOLID_ON_NEXT_NODE:
  old = huge magic value, then correction copied PhaseF_dyn(nw_x,nw_y,nw_z)
  v5  = wallDiagUnifiedProfilePhaseValue()

NORMAL_POINTING_INTO_SOLID_ON_FURTHER_NEXT_NODE:
  old = surface-energy profile expression directly
  v5  = wallDiagUnifiedProfilePhaseValue()

calcWallPhase_correction:
  old = PhaseF_dyn(nw_x,nw_y,nw_z)
  v5  = wallDiagUnifiedProfilePhaseValue()
```

New passive diagnostics:

```text
WallFluidSampleCount
WallFluidSampleH
WallPhaseUnifiedProfilePred
WallUnifiedProfileDelta
```

`calcWallPhase_correction` now loads `PF` because the unified reconstruction
samples nearby physical fluid `PhaseF`.

## 100-Step Smoke

Run:

```text
/mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_theta030_z48_gap24_outer90_sphere11_unified_special_v5diag_smoke_20260611/theta030
```

Result:

```text
solver rc = 0
zonal wall postprocess rc = 0
nonfinite_total step 0 = 0
nonfinite_total step 100 = 0
outer/default radAngle = 90d
SolidSphere radAngle = 11d
step 100 raw WallPhasePred sphere max = 1.38245
step 100 WallPhaseUnifiedProfilePred sphere max = 1.0
step 100 actual PhaseField physical max = 1.0
step 100 wall fluid sample count sphere mean = 38.07
```

## 50k Curved z48 Gate

Run:

```text
remote =
  /mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_theta030_z48_gap24_outer90_sphere11_unified_special_v5diag_50k_20260611/theta030
local =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_z48_gap24_outer90_sphere11_unified_special_v5diag_50k_20260611
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
PRE sphere postprocess = 0
zonal wall postprocess = 0
surface-film audit = 0
morphology gallery = 0
wall diagnostic plots = 0
```

Curated artifact:

```text
remote tar =
  /mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_theta030_z48_gap24_outer90_sphere11_unified_special_v5diag_50k_20260611/curated_pre2025_sphere_unified_special_v5diag_50k_no_raw.tar.gz
remote tar sha256 =
  e1c8e994c4703643b0489cd031b918af0ee0b0b5dcfc07a795855668bed8f021
local raw .vti/.pvti/.pri count = 0
```

## v3 vs v5

The final 50k global and morphology metrics are numerically identical to v3:

| metric | v3 | v5 |
|---|---:|---:|
| fit contact angle deg | 107.125719 | 107.125719 |
| H1-H2 error percent | 104.719123 | 104.719123 |
| fluid phase drift percent | -0.618564 | -0.618564 |
| fluid rho drift percent | -0.605953 | -0.605953 |
| max Mach | 4.91852e-4 | 4.91852e-4 |
| nonfinite | 0 | 0 |
| lower90 phi fraction | 0.0319182 | 0.0319182 |
| bottom120 phi fraction | 0.0078629 | 0.0078629 |
| z-min outside-sphere fraction | 0 | 0 |
| raw WallPhasePred sphere max | 1.44802 | 1.44802 |
| unified profile sphere max | n/a | 1.0 |
| raw wall pred > 1 count | n/a | 1920 |
| unified pred > 1 count | n/a | 0 |

Comparison figure:

```text
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_z48_gap24_outer90_sphere11_unified_special_v5diag_50k_20260611\v3_v5_morphology_wall_diag_comparison.png
```

## Interpretation

Supported findings:

```text
1. v5 is finite and bounded in this 50k separated-geometry gate.
2. v5 diagnostics work: raw geometric wall prediction still exceeds 1, while
   unified profile prediction is bounded and actual wall/fluid PhaseField stays
   bounded.
3. v5 does not change the 50k macroscopic morphology or contact response.
4. The reason is structural: this case has NumSpecialPoints = 0 at runtime, so
   the modified special/correction branches do not control the dominant
   spherical-wall response.
```

Therefore v5 is useful diagnostic evidence, but it is not a successful fix for
the curved-wall contact-angle error.

## Next Step

The next source candidate should not spend more effort on special/correction
fallback for this z48 case. The audit should move to the normal curved-wall
path:

```text
1. instrument normal-path terms near the sphere:
   pf_f, h, grad_tangent vector, projected-gradient sign, wall normal,
   liquid-interface normal, local contact-line tangent angle
2. separate actual wall ghost from diagnostic wall prediction:
   introduce WallPhaseF or a two-pass near-wall gradient read path
3. test whether normal-path profile reconstruction is physically imposing
   the intended angle on a curved wall, rather than merely bounding PhaseField
4. use existing v3/v5 z48 50k and the older 200k z48 run as diagnostic inputs
   before any new long extension
```

Claim remains `exploratory_not_validation`.
