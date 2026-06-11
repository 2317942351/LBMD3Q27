# PRE 2025 Sphere z48 Zonal Wetting Smoke

Date: 2026-06-11

Status: `exploratory_not_validation`

## Scope

This note records the first separated-geometry spherical wetting smoke after
freezing the old z24/global-low-angle setup as `failed_negative_evidence`.
The goal is diagnostic: separate geometry/outer-wall leakage from the curved
sphere wall reconstruction problem.

## Case

```text
domain = 80 x 80 x 180
VTI cell dims = 96 x 80 x 180 because TCLB pads x
R_drop = 24 lu
R_solid = 24 lu
solid_center_z = 48 lu
drop_center_z = 96 lu
bottom_gap = 24 lu = 4 * IntWidth for IntWidth=6
target theta = 30 deg
default/OuterDomain radAngle = 90d
SolidSphere radAngle = 11d
binary = /home/yuan/src/TCLB_clean_wall_profile_diag_20260610/CLB/d3q27_pf_velocity_q27_geometric/main
binary_sha256 = 59e03a6233744f00189b6241551fab30d1a53867a90bee582295f9666899159a
```

Remote runs:

```text
/mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_theta030_z48_gap24_outer90_sphere11_smoke_20260611
/mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_theta030_z48_gap24_outer90_sphere11_200k_vtk50k_20260611
```

Local curated artifact:

```text
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_z48_gap24_outer90_sphere11_200k_vtk50k_20260611
```

## Parser Smoke

The generated XML and TCLB CSV confirm that zonal `radAngle` works:

```text
case_config radAngle:
  DefaultZone = 90d
  OuterDomain = 90d
  SolidSphere = 11d

CSV radAngle:
  radAngle-DefaultZone = 1.5707963267949
  radAngle-OuterDomain = 1.5707963267949
  radAngle-SolidSphere = 0.19198621771938
```

The wall diagnostic also separates the zones:

```text
expected outer tan(pi/2-angle) = 0
expected sphere tan(pi/2-angle) = 5.144554015970307
outer WallTanCoeff mean = -1.794896e-09
sphere WallTanCoeff mean = 5.1445539667
```

Therefore no immediate `WallKind/localRadAngle` source patch is needed solely
to decouple the outer wall from the spherical solid wall.

## 200k Metrics

```text
solver return code = 0
run.done = present
run.stderr = empty
nonfinite_total = 0
max Mach over frames = 4.867e-4
final max Mach fluid = 1.7605e-4
final fluid phase drift = -1.3795%
final fluid rho drift = -1.3514%
final wall phase drift = +13.7227%
final global fitted angle = 131.9204 deg
final H1-H2 relative error = 161.5889%
```

Surface-film audit:

```text
z-min outside-sphere phi sum = 2.1837e-4
z-min outside-sphere phi fraction of shell = 8.8186e-9
lower90 phi fraction = 0.09708
bottom120 phi fraction = 0.03240
bottom150 phi fraction = 0.00741
```

## Interpretation

Supported findings:

```text
1. z24/global radAngle=11d was a known-bad geometry/outer-wall coupling.
2. Moving the sphere to z48 and setting the outer wall to neutral removes the
   bottom z-min wall leakage channel to numerical-negligible levels.
3. The same run still shows wrong curved-sphere morphology and large wall
   phase growth.
4. The profile lane bounds the order-one wall ghost better than the raw
   geometric branch, but it is not a sufficient contact-angle solution.
```

The remaining error is therefore not primarily an outer-domain parser problem
or a bottom-wall contact problem. The next source step should be an isolated
wall reconstruction candidate, not further `radAngle/M/W` fitting or a 600k
extension of this exact lane.

## Next Candidate

Use a new isolated source lane:

```text
/home/yuan/src/TCLB_clean_wall_signed_profile_diag_20260611
```

Minimum requirements:

```text
1. preserve raw WallPhasePred and profile WallPhaseProfilePred diagnostics
2. add signed/profile-consistent prediction fields
3. route normal, further-next special, and correction paths through the same
   reconstruction helper
4. run only smoke/short gates first:
   - 0-100 step z48 zonal parser smoke
   - 50k curved separated theta030 gate
   - flat theta030/090/150 gate before any longer claim
```

Claim limit remains:

```text
exploratory_not_validation
```
