# Wetting Pipeline README

Status: `runtime_sanity / exploratory_not_validation`.

This README describes how future wetting scripts should be organized. It does
not run cases, authorize GPU work, modify solver physics, enable write mode, or
promote any result to validation.

## Pipeline Principle

Every script in the wetting pipeline must answer one explicit question:

```text
what is being tested?
what metrics decide pass/fail?
what artifact is written?
what branch is taken if the test fails?
```

Scripts must not be written as "run more cases and inspect later" utilities.

## Pipeline Stages

### 0. Evidence Freeze

Purpose:

```text
collect existing Track A / Stage8 evidence and enforce claim boundaries
```

Allowed script behavior:

```text
read CSV/JSON/Markdown artifacts
summarize case status
report missing metrics as unknown
```

Forbidden behavior:

```text
no solver launch
no raw-field upload
no validation claim
```

### 1. Flat Closure

Purpose:

```text
fit flat-wall spherical caps and check mass/Mach/nonfinite/void metrics
```

Expected script family:

```text
postprocess_plane_static_closure_YYYYMMDD.py
run_plane_short_write_gate_YYYYMMDD.ps1 or .sh only after explicit approval
```

Required outputs:

```text
plane_cap_fit_summary.csv
plane_static_closure_summary.json
plane_static_closure_report.md
```

### 2. Cylinder Attribution

Purpose:

```text
attribute cylinder blocker to transfer, initializer, curvature/grid,
candidate stiffness, profile conflict, or postprocessing
```

Expected script family:

```text
make_cylinder_transfer_audit_cases_YYYYMMDD.py
postprocess_cylinder_transfer_audit_YYYYMMDD.py
postprocess_cylinder_initializer_sensitivity_YYYYMMDD.py
postprocess_cylinder_radius_sensitivity_YYYYMMDD.py
```

Required outputs:

```text
cylinder_normal_transfer_audit.csv
cylinder_initializer_sensitivity.csv
cylinder_radius_sensitivity.csv
cylinder_blocker_attribution_report.md
```

### 3. Cylinder Geometry Postprocessing

Purpose:

```text
extract contact line, local wall normal, interface normal, local contact angle,
and symmetry metrics
```

Expected script family:

```text
cylinder_contact_angle_extractor.py
postprocess_cylinder_axisymmetry_YYYYMMDD.py
```

Required outputs:

```text
cylinder_local_angle_summary.csv
cylinder_axisymmetry_summary.json
cylinder_axisymmetry_report.md
```

### 4. Cylinder Write Gate

Purpose:

```text
only after shadow + geometry gates pass, test short write integration
```

Run ladder:

```text
100 -> 1000 -> 5000
```

Forbidden default:

```text
scripts must default to dry-run
scripts must not launch 50k by default
scripts must require explicit execute flag
```

Required outputs:

```text
cylinder_short_write_summary.csv
cylinder_short_write_report.md
first_bad_cell_packet.json if failure occurs
```

### 5. Sphere Middle-Angle Route

Purpose:

```text
apply the cylinder-proven logic to two-curvature sphere cases
```

Expected script family:

```text
make_sphere_middle_angle_shadow_cases_YYYYMMDD.py
postprocess_sphere_contact_line_angle_YYYYMMDD.py
postprocess_sphere_axisymmetry_and_film_YYYYMMDD.py
```

Required outputs:

```text
sphere_middle_angle_shadow_summary.csv
sphere_contact_line_angle_report.md
sphere_axisymmetry_film_summary.json
```

### 6. Low-Angle Special Track

Purpose:

```text
handle 20/15/11/8/5 deg as a separate low-angle research route
```

Expected script family:

```text
postprocess_low_angle_tan_cos_residual_YYYYMMDD.py
postprocess_low_angle_grid_sensitivity_YYYYMMDD.py
```

Required outputs:

```text
low_angle_formula_comparison.csv
low_angle_grid_sensitivity_report.md
low_angle_route_classification.json
```

### 7. Center-Bubble Regression

Purpose:

```text
detect internal voids and center bubbles as failfast metrics
```

Expected script family:

```text
postprocess_internal_void_components_YYYYMMDD.py
postprocess_centerline_phasefield_YYYYMMDD.py
```

Required outputs:

```text
internal_void_component_summary.json
centerline_phasefield_summary.csv
center_bubble_regression_report.md
```

### 8. Dynamic Morphology

Purpose:

```text
only after static closure, define dynamic droplet morphology or impact cases
```

Expected script family:

```text
make_dynamic_morphology_cases_YYYYMMDD.py
postprocess_dynamic_spreading_metrics_YYYYMMDD.py
```

Required outputs:

```text
dynamic_case_matrix.csv
dynamic_failfast_summary.json
dynamic_morphology_report.md
```

## Script Safety Rules

All run scripts must default to dry-run:

```text
DryRun = true
Execute requires an explicit flag
GPU selection is printed before execution
case root and output root are printed before execution
```

All scripts must keep raw fields out of tracked artifacts:

```text
runtime outputs -> runtime_outputs/ or remote run root
public artifacts -> artifacts/, docs/, cases/, scripts/
raw .vti/.pvti/.pri/.vtk -> never committed
```

All postprocessors must report unknown values honestly:

```text
unknown if raw field missing
unknown if metric not implemented
blocked if required metric is missing after the gate requires it
```

No script may silently clamp, smooth, filter, or discard failure evidence.
If a limiter, cap, damping, or smoothing operation is used, it must be reported
as a diagnostic field.

## GPU And CPU Policy

For HM570-style execution:

```text
use the two Tesla P100 GPUs for independent small-case queues
avoid Quadro P4000 for solver compute unless explicitly requested
for one large case, use both P100s only after multi-GPU binding is verified
postprocess with multicore CPU workers after solver completion
start around 28 workers and tune within 28-36 physical cores
use 40 workers only as a controlled saturation test
```

This policy is runtime-sanity guidance only. It does not upgrade any physical
claim.

## Naming Convention

Use date-stamped names:

```text
make_<geometry>_<purpose>_YYYYMMDD.py
postprocess_<geometry>_<metric>_YYYYMMDD.py
run_<geometry>_<gate>_YYYYMMDD.ps1
hm570_run_<geometry>_<gate>_YYYYMMDD.sh
```

Use explicit case tags:

```text
plane_theta090_shadow
cylinder_theta060_R24_transfer_shadow
cylinder_theta090_capinit_shadow
sphere_theta060_middle_shadow
low_angle_sphere_theta011_shadow
```

## Required Report Header

Every generated Markdown report should start with:

```text
Status: runtime_sanity / exploratory_not_validation
This is not PRE reproduction, not validation, and not a production fix.
No write mode, long run, dynamic case, or publication claim is authorized by
this report unless explicitly stated by a later audited gate.
```

## Forbidden Actions

Pipeline scripts must not:

```text
launch blind 50k runs
enable write mode before shadow + geometry gates
run sphere11 inside the usable-angle ladder
run dynamic impact before static closure
upload raw fields or binaries
claim validation from shadow metrics alone
hide numerical failure with unreported clipping or damping
```

## Current Entry Point

The next implementation work should start with:

```text
WP1 flat wall closure postprocessing
WP2 cylinder blocker attribution case design
WP3 cylinder local contact-angle extractor design
```

Do not start with more curved 50k runs. A longer run is useful only after the
branching question and stop condition are already documented.
