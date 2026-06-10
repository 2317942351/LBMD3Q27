# PRE Sphere Theta030 Profile LiftZ32 Geometry Audit 2026-06-10

Status: `exploratory_not_validation`

This report records the geometry-isolation control after the profile-lane
600k run showed liquid moving down the solid sphere and into the bottom region
after about 200k. It is not a validation or calibration claim.

## Question

The original reduced PRE analogue places the solid sphere at:

```text
domain = 80 x 80 x 140
R_solid = 24
solid center z = 24
```

Therefore the solid sphere touches the z-min outer-domain wall. Since TCLB uses
one global `radAngle=11d` for both the outer-domain wall and the solid sphere,
the original geometry can create a strong-wetting connection between the
sphere underside and the bottom wall.

The control changed only the geometry placement:

```text
solid center z: 24 -> 32
initial droplet center z: 72 -> 80
bottom gap from sphere to z-min wall: 0 -> 8 lu
```

All physics parameters remained unchanged:

```text
target theta = 30 deg
TCLB radAngle = 11 deg
M = 0.1
IntWidth = 6
Density_h/l = 1 / 0.001
Viscosity_h/l = 0.09 / 0.1
sigma = 5e-5
steps = 400000
VTK interval = 50000
```

## Execution

```text
remote_root =
  /mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_liftZ32_400k_20260610
local_artifact =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_liftZ32_400k_20260610
comparison_artifact =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_profile_z24_vs_liftZ32_compare_20260610
case =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_liftZ32_400k_20260610
runner =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_run_pre2025_sphere_profile_liftZ32_400k_20260610.sh
binary =
  /home/yuan/src/TCLB_clean_wall_profile_diag_20260610/CLB/d3q27_pf_velocity_q27_geometric/main
binary_sha256 =
  59e03a6233744f00189b6241551fab30d1a53867a90bee582295f9666899159a
```

Execution health:

```text
solver rc = 0
PRE postprocess rc = 0
wall diagnostic rc = 0
morphology rc = 0
surface-film/z-min audit rc = 0
run.done = present
run.stderr = empty
NaN/Inf/error scan = no numerical pattern
local raw .vti/.pvti/.pri count = 0
```

## Main Comparison

Same 0-400k window, original z=24 geometry versus lifted z=32 geometry:

```text
step    case                  angle deg   H1-H2 error %   fluid phase drift %   lower90 frac   bottom120 frac   z-min outside frac
200k    z24 touching bottom    54.87       39.45           -1.53                 0.1048         0.0566           0.0536
200k    liftZ32 gap8           52.48       39.29           -1.38                 0.0970         0.0339           0.0069
400k    z24 touching bottom    36.11        6.39           -2.27                 0.2067         0.1397           0.1508
400k    liftZ32 gap8           34.30        5.13           -1.84                 0.1681         0.0731           0.0406
```

Interpretation:

```text
1. The global relaxation path is preserved. The fitted angle and H1-H2 error
   are similar between z24 and liftZ32, and liftZ32 is slightly better by 400k.
2. The bottom-wall contamination metric changes strongly. At 400k,
   z-min outside-sphere liquid fraction drops from 0.1508 to 0.0406 after
   lifting the sphere, and z-min liquid phi sum drops from 4866.8 to 1320.1.
3. Geometry/bottom-wall contamination is therefore strongly supported as a
   major source of the post-200k bottom film in the original setup.
4. The problem is not fully eliminated. At 400k the lifted case still has
   lower90 fraction 0.1681 and bottom120 fraction 0.0731, so the profile
   reconstruction itself still needs audit for residual lower-hemisphere film.
```

## Current Technical Diagnosis

The earlier profile candidate was meaningful because it suppressed the
order-one wall ghost `PhaseField>1` from the low-angle geometric wall formula.
However, the current evidence separates two remaining effects:

```text
geometry effect:
  sphere touching z-min wall plus global radAngle=11d creates a strong-wetting
  lower-wall pathway and amplifies bottom liquid accumulation.

formula effect:
  profile wall reconstruction remains surface-energy/profile-like and may
  still sustain an adsorption film on strongly wetting curved surfaces.
```

Therefore the original z=24 reduced geometry is not a clean calibration case
for the wetting model. It can still be used as a negative/diagnostic case, but
not as the main comparison geometry for tuning the model response.

## Next Action

Recommended next sequence:

```text
1. Use liftZ32 or an equivalent separated-domain geometry for subsequent
   theta030 profile/signed-geometric tests.
2. Add a second geometry control if needed: keep the sphere at z=24 but set the
   outer z-min boundary to a neutral/non-wetting treatment if TCLB supports
   wall-specific wetting. This directly separates solid-sphere wetting from
   outer-domain-wall wetting.
3. Implement the next wall candidate only after this geometry separation:
   a signed/profile-consistent geometric reconstruction that preserves the
   contact-angle relation without applying the surface-energy fallback to all
   normal geometric wall nodes.
4. Gate any new candidate through flat-wall, curved-wall, theta030 200k, and
   theta030 liftZ32 400k checks with the same metrics:
   H1-H2/Hmax, fitted and local contact angle, mass drift, Mach, nonfinite,
   wall ghost counts, lower90/bottom120/z-min film metrics.
```

## Key Artifacts

```text
comparison CSV =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_profile_z24_vs_liftZ32_compare_20260610\z24_vs_liftZ32_400k_comparison.csv
comparison summary =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_profile_z24_vs_liftZ32_compare_20260610\z24_vs_liftZ32_400k_summary.json
comparison trend plot =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_profile_z24_vs_liftZ32_compare_20260610\z24_vs_liftZ32_400k_trends.png
gallery/heatmap montage =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_profile_z24_vs_liftZ32_compare_20260610\z24_vs_liftZ32_gallery_heatmap_montage.png
liftZ32 morphology gallery =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_liftZ32_400k_20260610\theta030\analysis_morphology\theta030_frame_gallery.png
liftZ32 surface-film trend =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_liftZ32_400k_20260610\theta030\analysis_surface_film_zmin\surface_film_audit_timeseries.png
```
