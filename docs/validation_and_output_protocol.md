# Validation And Output Protocol

Date: 2026-06-06

## Required Outputs For Every Impact Run

Each run directory must contain:

```text
case XML
generated TCLB config XML
run.log
TCLB CSV log
postprocess script version
metrics CSV
summary JSON
beta(t) figure
mass/Mach figure
centroid figure
morphology snapshots
README with one allowed status label, e.g. `exploratory_not_validation`,
`runtime_sanity`, `validation_candidate`, `validation_passed`,
`production_candidate`, `publication_ready`, or `failed_negative_evidence`
```

## Metrics

Minimum metrics:

```text
time step
physical time and/or dimensionless time
beta_area
beta_box
beta_max
time_to_beta_max
contact area
all-cell phase_sum and relative change as a wall/ghost diagnostic
fluid-only phase_sum and relative change using BOUNDARY==0 for bulk mass
fluid-only clipped_phase_sum and relative change using BOUNDARY==0
wall_phase_sum and z-min/z-max wall ghost phase report when BOUNDARY exists
rho_sum and relative change
max velocity
max Mach, using c_s = 1/sqrt(3)
centroid x/y/z
phase min/max
nonfinite count
```

## Static Contact-Angle Evaluation

For TCLB static contact-angle cases, report two distinct angle metrics:

```text
primary_contact_angle = local_liquid_side_angle_deg
secondary_shape_angle = global_cap_or_circle_fit_complement_deg
```

The primary static contact-angle metric is the near-contact-line local tangent
angle. For the current lower-y-wall sessile-drop geometry:

```text
extract phi=0.5 contour on x-mid and z-mid slices
map contour coordinates to tangent-normal coordinates
fit local tangent lines near left and right contact lines
use near-wall windows 3-8 lattice cells unless an audit freezes another range
average left/right contact lines and x/z mid-slices
for input angles <= 90 deg, liquid-side angle = tangent-wall acute angle
for input angles > 90 deg, liquid-side angle = 180 deg - tangent-wall acute angle
```

The global whole-cap/circle-fit complement angle is a secondary morphology
metric only. It can include bulk droplet curvature and overestimate the
near-contact-line angle, especially for low-angle theta045 cases. Do not use
the global circle-fit angle alone to reject or accept a wetting model.

### Geometric Two-Metric Candidate

The 2026-06-07 geometric 45/90/135 static audit exposed a local-vs-global
conflict: theta045 is close under the local contact-line metric, while
theta090/theta135 are close under the global cap/circle complement metric but
fail the frozen local tangent window. Until a read-only audit accepts a revised
gate, this remains a candidate protocol only:

```text
microscopic_contact_line_metric =
  local_liquid_side_angle_deg from phi=0.5, true 3-8 lu,
  x/z mid-slices, left/right average

macroscopic_sessile_drop_metric =
  global_cap_or_circle_fit_complement_deg

candidate status =
  protocol_revision_candidate_only
```

Use this two-metric view to diagnose whether a static case shows a microscopic
contact-line angle, a macroscopic apparent sessile-drop angle, or a conflict

Read-only audit of this candidate on 2026-06-07 keeps
`validation_candidate_allowed=false` and does not replace the frozen static
gate. It only permits one narrowly bounded `theta090` dry-wall runtime probe
with `status=exploratory_not_validation` to test impact-chain health. That
probe must explicitly use
`/home/yuan/src/TCLB/CLB/d3q27_pf_velocity_geometric/main`, run under
`/media/yuan/DATA500/runs`, and must not be used as contact-angle validation,
grid convergence, production, publication evidence, Wang 2023 reproduction, a
45/90/135 sweep, an `R0>=32` pilot, or a liquid-film case.
between the two. Do not use it by itself to promote `validation_candidate` or
to launch rho772 impact pilots. A promotion requires a read-only audit that
explicitly accepts which metric is controlling for the intended claim.

Before accepting static contact-angle calibration beyond exploratory status,
also report:

```text
local tangent window range
left/right contact-line angle difference
x-mid/z-mid consistency
threshold sensitivity
fluid-only phase mass drift using BOUNDARY==0
rho drift
max Mach
nonfinite count
visual overlay of contour and local tangent fits
```

## Beta Definition

Default dry-wall definition:

```text
threshold = phi > 0.5
near-wall layers = 4 lattice cells unless grid sensitivity changes it
footprint = union of liquid cells in near-wall layers projected to wall plane
beta_area = 2*sqrt(area/pi) / D0
beta_box = max(projected width) / D0
```

Report both `beta_area` and `beta_box`. Use `beta_area` as the primary smooth
curve and `beta_box` as a conservative bounding metric.

## Morphology Snapshots

For dry wall with wall normal z:

```text
x-mid slice: z vs y
y-mid slice: z vs x
wall footprint: y vs x
optional 3D iso-surface: phi=0.5
```

Use fixed color scale:

```text
phi: 0 to 1
velocity magnitude: normalized consistently within the case set
```

For contact-angle sweeps, snapshots must be taken at identical dimensionless
times and also at event times:

```text
first contact
beta_max
maximum recoil
resting state
```

## Mass Conservation Thresholds

Exploratory:

```text
report all mass drift; no pass/fail claim
when BOUNDARY is available, separate all-cell phase_sum from fluid-only
PhaseField mass because wetting-wall ghost PhaseF is intentionally reconstructed
```

Engineering:

```text
fluid-only phase mass drift preferably < 2%
rho mass drift preferably < 1%
```

Publication target:

```text
fluid-only phase/volume drift target <= 1%, matching the order discussed in
Fei 2019 for complex impact cases
stricter thresholds should be used if the chosen beta or final footprint is
sensitive to volume drift
all-cell phase_sum must not be used as the bulk conservation gate when it
includes TCLB wall/solid BOUNDARY cells; report it alongside wall ghost phase
for wetting-boundary interpretation
```

The previous small-grid `rho_ratio=772` exploration had phase drift about
`+12%`, so it is not acceptable for physical validation.

## Mach Threshold

Use the incompressible LBM guard:

```text
max Mach < 0.1
```

If a case approaches 0.1, refine the lattice scaling or reduce lattice velocity.
Do not hide high Mach by postprocessing.

## Literature Comparison Rules

For a data-level validation case:

```text
state the exact literature case and source
state what was digitized or extracted
match dimensionless numbers before matching raw lattice parameters
report error metric, not only overlays
show mass and Mach for the same run
```

For the user target:

```text
compare contact-angle trends against validated dry-wall literature or accepted
correlations
do not call it high-We unless We is actually high after physical conversion
```
