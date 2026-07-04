# Stage18 Contact-Angle Measurement Method Audit

Date: 2026-07-04

Status: measurement-method gate only.  No solver physics was changed in this
step.

## Why this audit was needed

The current Taichi flat-wall morphology analyzer uses a `C=0.5` contour
circle fit.  That is useful for visual shape checking, but the project already
hit a serious failure mode in Stage15D: an unvalidated angle diagnostic drove a
wrong physical conclusion and nearly triggered an unnecessary wall-boundary
refactor.  Therefore the contact-angle measurer must be fixed before further
wetting-boundary modifications.

## Historical methods found in the repository

### 1. Stage15D calibrated bbox h/a method, trusted for flat wall

Primary files:

- `scripts/stage13/golden2_calibrated_angle.py`
- `scripts/stage13/golden_angle_crosscheck.py`
- `docs/stage14/40_stage15D_calibrated_angle_reverses_pivot_20260620.md`
- `docs/stage14/43_stage15D4_static_map_gate_closed_20260620.md`

Method:

```text
mask = PhaseField > 0.5
h = droplet height above wall on center z-slice
a = half footprint width
theta_bbox_raw = 2 atan(h / a)
theta_true = inverse_calibration(theta_bbox_raw)
```

The calibration curve is generated from synthetic tanh spherical caps of known
contact angle.  Stage15D used this self-calibrated measurement to overturn a
wrong earlier diagnosis.  The same report explicitly says the uncalibrated
DynamicCL band angle and some circle-fit readings were misleading at the
extreme angles.

Important historical calibration evidence:

```text
true 30  -> raw bbox reads about 25.1
true 60  -> raw bbox reads about 57.9
true 90  -> raw bbox reads about 88.8
true 120 -> raw bbox reads about 112.3
true 150 -> raw bbox reads about 123.8
```

After inversion, the old flat-wall static map closed at roughly:

```text
30 -> 32.3
45 -> 45.0
60 -> 62.2
90 -> 89.8
120 -> 121.4
135 -> 137.6
150 -> 149.8
```

This is the strongest historical evidence for flat-wall static contact-angle
measurement in the repository.

### 2. Stage13/Stage18 circle-fit method, useful but not primary for flat wall

Primary files:

- `scripts/stage13/stage13_flat_wall_shape_angle.py`
- `tools/taichi_phasefield_clean_2026/analyze_flat_wall_morphology.py`

Method:

```text
extract C = 0.5 contour
fit interface circle
measure liquid-side tangent angle at the wall
```

This method is geometrically meaningful and should remain as a morphology
cross-check.  However, Stage15D found circle-fit failure modes at low point
count and at angle extremes.  Therefore it must not be the only flat-wall
acceptance metric.

### 3. Stage12 analytic circle-intersection method, relevant for curved solids

Primary files:

- `scripts/stage12/stage12_shape_angle_analysis.py`
- `docs/stage9/stage12_geometry_contact_audit_20260614.md`

Method:

```text
fit the phi=0.5 interface circle
intersect it with analytic wall/cylinder/sphere surface
measure tangent angle at the continuous intersection
```

This avoids measuring at a grid contour point that may sit about one lattice
unit away from the analytic solid surface.  It is the right historical starting
point for cylinder/sphere geometry, but the Stage12 smoke results were
classified as runtime sanity, not equilibrium validation.

## Decision for the current Taichi line

For flat-wall equilibrium and decoupled-response gates:

```text
primary angle metric  = calibrated bbox h/a, regenerated for current grid
secondary metric      = circle-fit morphology angle and visual slice
validation condition  = primary angle + morphology + mass + velocity agree
```

The old Stage15D calibration table must not be applied directly to the current
Taichi runs because the grid and interface parameters changed.  Current Taichi
cases commonly use:

```text
grid = 48 x 32 x 48
radius = 10
interface width = 4
wall surface y = 0.5
cell-centered NPZ fields, C stored as c[x,y,z]
```

Therefore the calibration curve must be regenerated per run geometry.  This is
implemented in:

- `tools/taichi_phasefield_clean_2026/analyze_flat_wall_calibrated_angle.py`
- `tools/taichi_phasefield_clean_2026/summarize_flat_wall_calibrated_angle.py`

For cylinder/sphere gates:

```text
primary candidate = Stage12 analytic interface/solid intersection
do not use flat-wall bbox h/a as the curved-geometry metric
```

## Immediate implication for current Stage18 results

The existing Taichi flat-wall results in these artifact roots must be remeasured
before using them to drive solver changes:

- `artifacts/stage18_flat_wall_wetting_contact_20260704_r2/`
- `artifacts/stage18_flat_wall_closure_matrix_20260704_r1/`

The previous circle-fit-only readings suggested `theta90` drifted to about
113 deg after 300 steps.  That may still be true, but it must be confirmed
against the calibrated bbox method.  Solver modifications should remain paused
until this remeasurement is complete.

## Remeasurement of existing Taichi artifacts

The Stage18 Taichi artifacts were remeasured with the new NPZ calibrated bbox
tool:

```text
python tools/taichi_phasefield_clean_2026/summarize_flat_wall_calibrated_angle.py \
  artifacts/stage18_flat_wall_wetting_contact_20260704_r2 --radius 10 --width 4 --z-slices 3

python tools/taichi_phasefield_clean_2026/summarize_flat_wall_calibrated_angle.py \
  artifacts/stage18_flat_wall_closure_matrix_20260704_r1 --radius 10 --width 4 --z-slices 3
```

Summary:

| case | target | circle-fit prior | calibrated bbox | interpretation |
| --- | ---: | ---: | ---: | --- |
| `theta90_init90_300` | 90 | 113.0 | 87.7 | circle-fit overstates drift; bbox says neutral wall is near 90 |
| `theta150_init150_300` | 150 | 157.3 | 162.0 | both indicate obtuse morphology; bbox slightly overreads on this small grid |
| `theta30_init30_300` | 30 | NaN | 165.0 | morphology is not a resolved hydrophilic cap; angle number is a failure symptom, not a valid 30-degree reading |
| `theta90_adv*` matrix | 90 | 113.0-113.3 | 87.6-87.7 | ghost distance/sign/advection do not move neutral bbox result |
| `theta120_adv1_gd05_signm1` | 120 | 137.0 | 123.0 | calibrated bbox is close to target; circle-fit biased high |
| `theta60_adv1_gd05_signm1` | 60 | NaN | 165.0 | same unresolved/failed acute morphology pattern as theta30 |

This changes the immediate diagnosis:

```text
The neutral 90-degree flat-wall case is not proven broken by the old circle-fit
113-degree reading.  The primary bbox method reads about 88 degrees.

The severe current failure is the acute hydrophilic side: theta30/theta60
produce a tall/detached-looking morphology on the 48x32x48, R=10, W=4 setup.
This may combine a solver/wall-boundary issue with under-resolution of thin
acute caps, so future acute-angle runs need larger grids or a larger footprint
before being used as decisive evidence.
```

Generated result files:

- `artifacts/stage18_flat_wall_wetting_contact_20260704_r2/flat_wall_calibrated_bbox_summary.csv`
- `artifacts/stage18_flat_wall_wetting_contact_20260704_r2/flat_wall_calibrated_bbox_summary.json`
- `artifacts/stage18_flat_wall_closure_matrix_20260704_r1/flat_wall_calibrated_bbox_summary.csv`
- `artifacts/stage18_flat_wall_closure_matrix_20260704_r1/flat_wall_calibrated_bbox_summary.json`
- Per-case `analysis_calibrated_bbox/` directories with calibration curves,
  slice overlays, and JSON metrics.

## Acceptance standard for future wetting claims

A flat-wall static contact-angle result can be discussed as physical evidence
only when all of the following are reported together:

```text
1. calibrated bbox angle and calibration curve
2. circle-fit morphology cross-check
3. center-slice morphology image
4. mass drift and any mass correction
5. maximum velocity / spurious-current metric
6. run parameters: grid, radius, width, wall_y, density ratio, mobility
```

No single angle number is sufficient.
