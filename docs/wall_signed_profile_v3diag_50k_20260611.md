# Wall Signed-Profile v3 Diagnostic 50k

Date: 2026-06-11

Status: `exploratory_not_validation`

## Scope

This note records the first finite short gate after the failed signed-profile
write candidates. v3 is intentionally diagnostic-only:

```text
actual wall write = existing stable profile reconstruction
passive diagnostics = raw geometric, profile, signed-logit/profile prediction
```

It is not a wetting-boundary fix and is not validation evidence.

## Source And Build

```text
source = /home/yuan/src/TCLB_clean_wall_signed_profile_v3diag_20260611
binary = /home/yuan/src/TCLB_clean_wall_signed_profile_v3diag_20260611/CLB/d3q27_pf_velocity_q27_geometric/main
binary_sha256 = f585775753ebeee64f64e098d5ae01638ebff447e5370b7aa7b720d6afde9690
provenance = /mnt/8A0E24070E23EAC1/runs/tclb_wall_signed_profile_v3diag_provenance_20260611
```

The generated code confirms the actual write remains profile-based:

```text
PhaseF = wallDiagProfilePhaseValue(pf_f, h)
```

The added passive fields are:

```text
WallPhaseSignedProfilePred
WallSignedProfileDelta
WallSignedLogitShift
```

## 100-Step Smoke

Run:

```text
/mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_theta030_z48_gap24_outer90_sphere11_signed_profile_v3diag_smoke_20260611/theta030
```

Result:

```text
solver rc = 0
postprocess rc = 0
nonfinite_total step 0 = 0
nonfinite_total step 100 = 0
outer radAngle = 90d
SolidSphere radAngle = 11d
step 100 WallPhasePred sphere max = 1.38245
step 100 WallPhaseProfilePred sphere max = 1.0
step 100 WallPhaseSignedProfilePred sphere max = 1.0
step 100 WallSignedLogitShift sphere max = 8.92764
```

This is a runtime sanity result only. The earlier v1/v2 signed-profile write
candidates remain `failed_negative_evidence`.

## 50k Curved z48 Gate

Run:

```text
remote =
  /mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_theta030_z48_gap24_outer90_sphere11_signed_profile_v3diag_50k_20260611/theta030
local =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_z48_gap24_outer90_sphere11_signed_profile_v3diag_50k_20260611
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
zonal wall postprocess = 0
PRE sphere postprocess = 0
surface-film audit = 0
morphology gallery = 0
```

Final 50k metrics:

```text
nonfinite = 0
PhaseField max = 1.0
fluid phase drift = -0.6186%
fluid rho drift = -0.6060%
max Mach fluid = 4.9185e-4
fit contact angle = 107.13 deg
H1-H2 relative error = 104.72%
z-min outside-sphere phi fraction = 0
lower90 phi fraction = 0.03192
bottom120 phi fraction = 0.00786
bottom150 phi fraction = 0.00132
```

Wall diagnostics:

```text
step 0:
  raw WallPhasePred sphere max = 1.79546
  profile pred sphere max = 1.0
  signed-profile pred sphere max = 1.0
  signed logit shift sphere max = 6.04685

step 50000:
  raw WallPhasePred sphere max = 1.44802
  profile pred sphere max = 1.0
  signed-profile pred sphere max = 1.0
  signed logit shift sphere max = 5.22640
```

Morphology:

```text
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_z48_gap24_outer90_sphere11_signed_profile_v3diag_50k_20260611\theta030\analysis_morphology\theta030_frame_gallery.png
```

## Interpretation

Supported findings:

```text
1. The z48/outer-neutral geometry continues to suppress z-min leakage.
2. The stable profile actual write keeps fields finite and bounded through
   50k in this separated geometry.
3. Passive signed-logit diagnostics show large signed shifts but remain finite
   as outputs.
4. The shape is still far from the target theta030 equilibrium at 50k:
   global fit angle is about 107 deg and H1-H2 error is about 105%.
```

Therefore v3 is useful as an audit/diagnostic lane, not as a boundary fix.

## Next Step

Do not extend v1/v2. Do not promote v3 to validation.

The next code path should use passive v3 diagnostics to design a less
aggressive signed reconstruction, for example:

```text
1. derive a local-interface signed tangent direction instead of using only
   |grad_tangent|
2. limit the signed-logit shift by a physically derived profile-distance scale,
   not a hidden clamp
3. test first on flat wall theta030/090/150, then z48 curved 50k
```

Any longer 200k or 600k run should wait until the flat-wall gate and the
curved 50k gate both show improved contact response without nonfinite growth.
