# Track A Usable-Angle Validation Ladder Plan

Status: `runtime_sanity / exploratory_not_validation`.

Track A is a local Windows planning and postprocessing lane for usable
middle-angle wetting cases. It is not a PRE reproduction, not validation, not a
production fix, and not a replacement for the unresolved low-angle Stage8h
research. It does not modify Stage8g or Stage8 physics code.

## Scope

Track A asks a narrower question than the low-angle sphere11 route:

```text
Which middle-angle plane, cylinder, and sphere wetting cases are clean enough
in shadow diagnostics to justify separately approved short-write tests?
```

The current Track A case order is:

```text
plane -> cylinder -> sphere
```

This is the fastest usable ladder because it separates increasing geometric
difficulty:

1. Plane cases test the local contact-angle relation without wall curvature.
2. Cylinder cases add one-direction wall curvature and azimuthal consistency.
3. Sphere cases add two-direction curvature, axisymmetry, and outer-wall
   separation risks.

Low-angle `sphere11` remains excluded from Track A. That case belongs to the
Stage8 low-angle research lane and must not be used to calibrate Track A.

## Case Matrix

All Track A cases start as shadow-only:

```text
Stage8OperatorMode = 1
steps = 0, 100, 1000
status = runtime_sanity / exploratory_not_validation
```

Plane angles:

```text
20, 25, 30, 60, 90, 120, 150 deg
```

Cylinder angles:

```text
30, 45, 60, 90, 120 deg
```

Sphere angles:

```text
30, 45, 60, 90, 120 deg
```

Explicit exclusions:

```text
sphere11 write
liquid impact
high-Weber dynamic spreading
automatic 50k runs
automatic GPU jobs
sphere Stage8OperatorMode=2
Track B files
```

If a case passes shadow screening, only a short-write XML/template may be
generated. It must not be run automatically. The short-write sequence is:

```text
100 steps -> 1000 steps -> 5000 steps
```

A 50k run is a future task only after short-write evidence passes audit.

## Mathematical target shapes and validation metrics

These formulas and geometric tests are for postprocessing and target-shape
comparison only. They do not change the solver, Stage8g physics code, wall
ghost reconstruction, gradient candidate, or TCLB runtime equations.

### Plane droplet theoretical reference

For a droplet on a flat wall, use spherical-cap geometry as the first
theoretical reference. Define:

```text
theta  = prescribed contact angle
V      = droplet volume
R_cap  = spherical-cap radius
h      = cap height
a      = contact radius
D      = 2a, base diameter
```

Standard spherical-cap relations:

```text
a^2 + h^2 = 2 R_cap h
V = pi h (3 a^2 + h^2) / 6
h / a = tan(theta / 2)
```

If `R_cap` is fitted instead:

```text
a = R_cap sin(theta)
h = R_cap (1 - cos(theta))
```

Use the fitted convention consistently when interpreting whether the cap is
measured through the liquid phase and whether theta is the internal liquid
angle. Do not mix the two conventions inside one postprocessing table.

Required plane comparison metrics:

```text
fitted apparent contact angle theta_fit
height error = abs(h_sim - h_theory) / h_theory
contact radius error = abs(a_sim - a_theory) / a_theory
volume or phase-mass drift
max Mach
spurious current estimate if velocity field is available
center-bubble or internal-void connected-component count if PhaseField exists
```

Suggested exploratory Track A thresholds for short-write planning:

```text
abs(theta_fit - theta_target) < 3 deg
height error < 5%
contact radius error < 5%
mass drift < 1%
nonfinite_total = 0
no internal bubble or void connected component inside the liquid core
```

### Cylinder droplet theoretical reference

For a droplet on a cylinder, do not claim closed-form validation unless an
analytical cap-on-cylinder solution is implemented and audited. Cylinder cases
are intermediate curved-boundary feasibility tests. They test one-direction
curvature before sphere cases.

The current Track A cylinder XML is a shadow-only feasibility initializer: a
diffuse spherical droplet is placed tangent to a z-extruded solid cylinder. It
is intended to exercise local wall-angle transfer, wall-normal transfer, and
limiter behavior on one-direction curvature. It is not an equilibrium
cap-on-cylinder shape and cannot be promoted to geometric validation without a
separate cap-on-cylinder initializer or numerical fitting audit.

Primary mathematical quantities:

```text
local contact angle
local wall-normal agreement
azimuthal symmetry
mass conservation
```

Near the contact line, compare the interface against local tangent-plane
spherical-cap estimates only as a first-order reference. Report deviations in
the axial and circumferential directions separately.

Required cylinder metrics:

```text
local apparent contact-angle distribution along the contact line
mean / p95 / max angle error
axial symmetry error
circumferential symmetry error
mass drift
max Mach
normal_limiter_fraction
vector_limiter_fraction
profile_target_mismatch
center-bubble or internal-void count
```

Cylinder pass-for-planning criteria:

```text
nonfinite_total = 0
vector_limiter_fraction = 0
normal_limiter_fraction < 5%
mean local angle error < 5 deg
p95 local angle error < 10 deg
no center bubble or internal void
mass drift < 1%
```

### Sphere droplet theoretical reference

For a droplet on a spherical solid surface, do not claim validation from the
flat spherical-cap formula. The sphere problem requires cap-on-sphere geometry
or numerical geometric fitting.

For Track A middle-angle feasibility, use:

```text
local contact angle along the three-phase contact line
fitted interface surface
comparison to local tangent-plane spherical-cap reference
symmetry around the sphere axis
volume or phase-mass conservation
limiter statistics
```

Required sphere metrics:

```text
local apparent contact-angle distribution
mean / p95 / max angle error
contact-line height variation
axisymmetry error
liquid volume or phase-mass drift
max Mach
lower-side film fraction if applicable
bottom or outer-wall contamination if applicable
normal_limiter_fraction
vector_limiter_fraction
outer90_limiter_count
fallback_angle_limiter_count
center-bubble or internal-void count
```

Sphere pass-for-planning criteria:

```text
nonfinite_total = 0
vector_limiter_fraction = 0
normal_limiter_fraction < 5%
outer90_limiter_count = 0
fallback_angle_limiter_count = 0
mean local contact-angle error < 5 deg
p95 local contact-angle error < 10 deg
no center bubble or internal void
mass drift < 1%
```

## Shadow Metrics Required For Every Case

Every Track A case template requires these metrics before classification can
move beyond `pending`:

```text
nonfinite_total
max_mach
phase_mass_relative_change
rho_relative_change
normal_limiter_fraction
vector_limiter_fraction
outer90_limiter_count
fallback_angle_limiter_count
Stage8FluidWallAngle statistics
Stage8NormalAgreement statistics
profile_target_mismatch p50/p95/p99
active_count
limiter_count
candidate_demand p50/p95/p99
final case recommendation
```

Short-write eligibility requires:

```text
nonfinite_total = 0
vector_limiter_fraction = 0
normal_limiter_fraction < 5%
outer90_limiter_count = 0
fallback_angle_limiter_count = 0
max_mach not elevated
candidate_demand_p50 < 1.2
candidate_demand_p95 < 3.0
required geometric metrics available and within group-specific thresholds
```

## Classification Rules

Each case is classified as one of:

```text
pending: no runtime data, or no lightweight metrics file
blocked: nonfinite, limiter dominated, missing required metrics after runtime,
         or failed geometric criteria
shadow_pass: shadow metrics pass but no write run exists
eligible_for_short_write: shadow pass plus geometric metrics are sufficient to
                          generate 100/1000/5000 short-write templates
short_write_pass: future category only; do not assign without real short-write
                  data
```

No current Track A template is allowed to be labeled `short_write_pass`.

## Postprocessing Plan

`scripts/postprocess_track_a_shadow_matrix_20260613.py` reads only lightweight
CSV or JSON metrics. It never requires raw VTI/PVTI/PRI/VTK files for summary
classification.

The postprocessor provides these future calculation entry points:

```text
fit_plane_spherical_cap()
compute_plane_cap_theory()
estimate_contact_line()
compute_local_contact_angles()
compute_axisymmetry_error()
compute_internal_void_count()
classify_track_a_case()
```

When raw data or required metrics are absent, the output must say `pending` or
`unknown`. It must not fabricate fitted angles, limiter values, void counts, or
pass/fail evidence.

Outputs:

```text
artifacts/track_a_usable_angle_ladder_summary_20260613/track_a_summary.csv
artifacts/track_a_usable_angle_ladder_summary_20260613/track_a_summary.json
```

## Windows Execution Boundary

`scripts/run_track_a_shadow_matrix_20260613.ps1` is a Windows PowerShell
launcher. It must default to dry-run behavior, print commands, and require
explicit confirmation before execution.

Allowed parameters:

```text
-CaseGroup plane/cylinder/sphere/all
-DryRun
-Execute
-GpuId optional
```

The script writes runtime outputs under `runtime_outputs/`, never into tracked
artifact folders. Raw `.vti`, `.pvti`, `.pri`, and `.vtk` outputs must remain
outside tracked artifacts.

## Conclusion

Track A is the usable-angle validation ladder. It is not a replacement for
low-angle Stage8h research. Its goal is to identify which middle-angle
plane/cylinder/sphere cases are mathematically and numerically clean enough for
separately approved short-write tests.

Track A remains isolated in this branch. It does not modify Stage8 low-angle
physics code, does not contaminate Stage8g/Stage8h research, and does not
authorize sphere11 write, Track B, GPU simulations, validation, PRE
reproduction, or production claims.
