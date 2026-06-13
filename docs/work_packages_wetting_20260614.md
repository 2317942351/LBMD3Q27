# Wetting Work Packages

Status: `runtime_sanity / exploratory_not_validation`.

This checklist converts the wetting roadmap into bounded work packages. No
package below authorizes solver physics changes, GPU jobs, write mode,
`sphere11`, 50k runs, or dynamic impact by itself.

## WP1: Flat Wall Closure

Objective:

```text
Close the flat-wall static wetting baseline for middle angles.
```

Primary cases:

```text
plane 30, 60, 90, 120 deg
```

Secondary diagnostics:

```text
plane 20 deg
plane 150 deg
```

Tasks:

- [x] Freeze current flat shadow results and missing metrics.
- [x] Implement or verify spherical-cap contact-angle fitting.
- [x] Report theta_fit, height error, contact radius error, and volume error.
- [x] Report mass drift, max Mach, nonfinite_total, and internal void count.
- [ ] Audit plane 150 as high-angle stiffness, not as middle-angle blocker.
- [x] Draft `plane_static_closure_report.md`.

Pass gate:

```text
abs(theta_fit - theta_target) < 3 deg
height error < 5%
contact radius error < 5%
mass drift < 1%
nonfinite_total = 0
center bubble / internal void count = 0
```

Deliverables:

```text
plane_static_validation_report.md
plane_cap_fit_summary.csv
center_bubble_plane_check.json
```

Blocked outputs:

```text
no cylinder write
no sphere write
no 50k
no validation claim
```

Completion flag:

```text
flat_wall_middle_angle_closed_for_planning
```

Current WP1 decision on 2026-06-14:

```text
flat_wall_middle_angle_closed_for_planning = true
plane030/plane090 100-step write smoke passed
continue to WP2 cylinder blocker attribution
```

## WP2: Cylinder Blocker Attribution

Objective:

```text
Identify whether cylinder normal-limiter blocking is transfer, initializer,
curvature/grid, candidate stiffness, or postprocessing.
```

Primary cases:

```text
theta = 60, 90 deg
R_cyl = 16, 24, 32, 48
Stage8OperatorMode = 1
steps = 0, 100, 1000
```

Tasks:

- [ ] Compare local wall angle against expected cylinder-zone value.
- [ ] Compare gathered wall normal against analytic cylinder radial normal.
- [ ] Report fallback_angle_count in the contact band.
- [ ] Run or define initializer sensitivity: tangent sphere, lifted droplet,
      tangent-plane cap, approximate cap-on-cylinder.
- [ ] Run or define radius sensitivity at fixed angle.
- [ ] Attribute normal_limiter_fraction to one primary branch.
- [ ] Draft `cylinder_blocker_attribution_report.md`.

Pass gate:

```text
local angle transfer is correct
normal transfer is correct
initializer effect is quantified
radius effect is quantified or explicitly deferred
candidate stiffness is classified
```

Deliverables:

```text
cylinder_blocker_attribution_report.md
cylinder_radius_sensitivity.csv
cylinder_initializer_sensitivity.csv
cylinder_normal_transfer_audit.csv
```

Failure routes:

```text
transfer -> repair local angle/normal gather
initializer -> build cap-on-cylinder initializer
curvature -> grid/R/W sensitivity
candidate -> contact-relation/profile-contract audit
postprocess -> WP3
```

Completion flag:

```text
cylinder_blocker_primary_cause_identified
```

## WP3: Cylinder Geometry Postprocessor

Objective:

```text
Measure cylinder local contact angle and symmetry directly.
```

Tasks:

- [ ] Extract the `phi = 0.5` interface or equivalent diffuse interface band.
- [ ] Extract the three-phase contact line.
- [ ] Compute local wall normal at each contact-line point.
- [ ] Compute local interface normal from phase-field gradients.
- [ ] Compute local contact angle along the line.
- [ ] Report mean, p95, and max angle error.
- [ ] Report axial symmetry error.
- [ ] Report azimuthal/circumferential symmetry error.
- [ ] Report internal void count.
- [ ] Draft `cylinder_axisymmetry_report.md`.

Pass gate:

```text
local angle extraction reproducible
mean local angle error < 5 deg where a valid case exists
p95 local angle error < 10 deg where a valid case exists
symmetry metrics reported
internal void metric reported
```

Deliverables:

```text
cylinder_contact_angle_extractor.py
cylinder_local_angle_summary.csv
cylinder_axisymmetry_report.md
```

Blocked outputs:

```text
no cylinder validation claim from limiter alone
no cylinder write promotion without local angle metric
```

Completion flag:

```text
cylinder_local_angle_postprocessor_available
```

## WP4: Cylinder Write Validation Candidate

Objective:

```text
Test whether a shadow-clean cylinder candidate survives actual write
integration.
```

Entry requirements:

```text
WP1 complete
WP2 primary cause understood
WP3 local angle postprocessor available
shadow gate passes for selected cylinder cases
```

Primary cases:

```text
cylinder 60 deg
cylinder 90 deg
```

Expansion cases:

```text
cylinder 30, 45, 120 deg only after 60/90 pass
```

Run ladder:

```text
100 steps -> 1000 steps -> 5000 steps
50k only after separate audit approval
```

Tasks:

- [ ] Generate short-write templates only after gate approval.
- [ ] Run 100-step write and check failfast metrics.
- [ ] Run 1000-step write only if 100-step passes.
- [ ] Run 5000-step write only if 1000-step passes.
- [ ] Report mass drift, max Mach, nonfinite_total, local angle, and voids.
- [ ] Draft `cylinder_short_write_report.md`.

Pass gate:

```text
nonfinite_total = 0
mass drift < 1%
center bubble count = 0
mean local angle error < 5 deg
p95 local angle error < 10 deg
max Mach not elevated
```

Deliverables:

```text
cylinder_short_write_report.md
cylinder_static_50k_report.md only after later approval
```

Stop conditions:

```text
nonfinite appears
mass drift > 1%
center bubble appears
local angle collapses
max Mach spikes
```

Completion flag:

```text
cylinder_60_90_short_write_passed_for_planning
```

## WP5: Sphere Middle-Angle Validation Candidate

Objective:

```text
Evaluate sphere 90/60/45/30 after the cylinder route is understood.
```

Entry requirements:

```text
cylinder 60/90 short-write route passes or the cylinder blocker is explicitly
resolved by audit
sphere local angle and contact-line metrics are defined
```

Cases:

```text
sphere 90
sphere 60
sphere 45
sphere 30
```

Tasks:

- [ ] Audit sphere local wall-angle transfer.
- [ ] Audit sphere local normal transfer against analytic radial normal.
- [ ] Compare free-sphere and cap-on-sphere initializers.
- [ ] Extract contact-line local angle distribution.
- [ ] Report contact-line height variation.
- [ ] Report axisymmetry error.
- [ ] Report lower-side film and outer-wall contamination.
- [ ] Report internal void count.
- [ ] Draft `sphere_middle_angle_shadow_report.md`.

Pass gate:

```text
nonfinite_total = 0
outer90 limiter count = 0
fallback limiter count = 0
normal limiter or equivalent demand below gate
mean local contact-angle error < 5 deg
p95 local contact-angle error < 10 deg
center bubble count = 0
```

Deliverables:

```text
sphere_middle_angle_shadow_report.md
sphere_contact_line_angle_report.md
sphere_short_write_report.md only after separate approval
```

Failure routes:

```text
sphere 90 fails -> two-curvature geometry/normal transfer
90 passes but 30/45 fail -> angle-curvature contact relation
cap-on-sphere improves -> initializer route
larger R improves -> grid/curvature route
```

Completion flag:

```text
sphere_middle_angle_route_attributed
```

## WP6: Low-Angle Special Research

Objective:

```text
Treat 20/15/11/8/5 deg as low-angle wetting research, separate from the usable
middle-angle ladder.
```

Entry requirements:

```text
flat middle angles understood
curved middle-angle blocker is not being hidden by low-angle cases
```

Cases:

```text
flat 11/8/5
cylinder 20/15/11
sphere 20/15/11
```

Tasks:

- [ ] Compare tan residual and cos residual.
- [ ] Report tan(pi/2 - theta) amplification diagnostics.
- [ ] Compare grid/R/W sensitivity.
- [ ] Compare low-angle initializers.
- [ ] Report low-angle-specific center bubbles or leakage.
- [ ] Draft `low_angle_stage8h_report.md`.

Pass gate:

```text
low-angle shadow candidate is not limiter dominated
write gate is separately approved and passes short-run failfast checks
```

Deliverables:

```text
low_angle_stage8h_report.md
low_angle_grid_sensitivity_report.md
low_angle_formula_revision_report.md
```

Allowed conclusions:

```text
low angle appears feasible
low angle needs finer grid
low angle needs regularized relation
current model is not suitable for this low-angle target without further work
```

Completion flag:

```text
low_angle_route_classified
```

## WP7: Center-Bubble Regression

Objective:

```text
Make internal voids and center bubbles explicit failfast metrics.
```

Cases:

```text
free static droplet
flat 90
flat 30
cylinder 90
cylinder 60
sphere 90
sphere 60
impact only after static closure
```

Tasks:

- [ ] Implement liquid-core connected-component count.
- [ ] Implement internal gas void count.
- [ ] Report centerline PhaseField min/max.
- [ ] Report pressure/rho extrema where available.
- [ ] Report mass drift and max Mach.
- [ ] Report interface-thickness statistics.
- [ ] Draft `center_bubble_regression_report.md`.

Pass gate:

```text
no internal void in free droplet or static wetting cases
```

Failure routes:

```text
free droplet bubble -> bulk/initializer issue
flat clean but curved bubble -> curved wall boundary issue
static clean but impact bubble -> dynamic pressure/We/Mobility issue
low-angle only bubble -> low-angle contact-line issue
```

Deliverables:

```text
center_bubble_regression_report.md
center_bubble_metrics.csv
internal_void_component_summary.json
```

Completion flag:

```text
center_bubble_regression_available
```

## WP8: Dynamic Droplet Morphology

Objective:

```text
Start dynamic morphology only after static wetting closure makes results
interpretable.
```

Entry requirements:

```text
G1 flat closure
G2 cylinder route understood
G3 sphere route understood for required geometry and angle
center-bubble regression passes
case definition and metrics fixed
```

Tasks:

- [ ] Define dynamic case geometry and units.
- [ ] Define contact-angle convention.
- [ ] Define droplet-only impact velocity extraction.
- [ ] Define mass conservation report.
- [ ] Define max Mach and nonfinite/failcheck report.
- [ ] Define grid/time-step sensitivity.
- [ ] Define literature comparison if any validation claim is intended.
- [ ] Draft `dynamic_morphology_plan.md`.

Pass gate:

```text
static wetting evidence is sufficient for the target dynamic geometry
audit approves moving beyond exploratory_not_validation
```

Deliverables:

```text
dynamic_morphology_plan.md
dynamic_case_matrix.csv
dynamic_failfast_metrics.json
```

Forbidden outputs:

```text
no high-We claim before case physics is fixed
no publication-ready claim from runtime-only evidence
no dynamic impact before static closure
```

Completion flag:

```text
dynamic_route_ready_for_separate_plan
```

## Repository Output Rules

Allowed public artifacts:

```text
Markdown reports
CSV/JSON summaries
XML templates
source patches
scripts
PNG figures
lightweight logs
```

Forbidden public artifacts:

```text
.vti/.pvti/.pri/.vtk raw fields
binaries
archives
credentials
large files above audit threshold
```

Required status language:

```text
runtime_sanity / exploratory_not_validation
failed_negative_evidence when a case is deliberately negative
validation_candidate only after a separate read-only audit gate
```
