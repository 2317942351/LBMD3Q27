# WP1 Flat Wall Closure Report

Status: `runtime_sanity / exploratory_not_validation`.

This is not PRE reproduction, not validation, and not a production fix. This
WP1 pass did not modify solver physics code, did not run GPU jobs, did not run
write mode, did not run 50k, did not run cylinder/sphere/sphere11, and did not
run liquid impact.

## Scope

WP1 reprocessed the existing Track A flat-wall shadow outputs:

```text
runtime_outputs/track_a_overnight_20260613
```

Selected WP1 cases:

```text
plane020
plane030
plane060
plane090
plane120
```

Excluded cases:

```text
plane150
cylinder
sphere
sphere11
liquid impact
50k or longer runs
```

## Commands Run

```powershell
python -m py_compile scripts/postprocess_track_a_shadow_matrix_20260613.py
python scripts/postprocess_track_a_shadow_matrix_20260613.py --input runtime_outputs/track_a_overnight_20260613 --output artifacts/track_a_usable_angle_ladder_summary_20260613 --case-group plane
```

## Outputs

WP1 generated:

```text
artifacts/track_a_usable_angle_ladder_summary_20260613/wp1_plane_geometry_summary.csv
artifacts/track_a_usable_angle_ladder_summary_20260613/wp1_plane_geometry_summary.json
artifacts/track_a_usable_angle_ladder_summary_20260613/wp1_plane_geometry_report.md
```

The standard plane summary was also regenerated:

```text
artifacts/track_a_usable_angle_ladder_summary_20260613/track_a_plane_summary.csv
artifacts/track_a_usable_angle_ladder_summary_20260613/track_a_plane_summary.json
artifacts/track_a_usable_angle_ladder_summary_20260613/track_a_plane_report.md
```

## Geometry Metrics

The current lightweight Track A metrics contain fitted apparent contact angle
for flat cases. WP1 can therefore compute angle error. The local runtime output
tree does not contain raw `.vti/.pvti/.pri/.vtk` fields and does not contain
precomputed `h_sim`, `a_sim`, `height_error`, `contact_radius_error`,
`phase_mass_relative_change`, or `internal_void_count`. Those values are
reported as `unknown`; they are not fabricated.

| case | theta target | theta fit | theta error | h error | a error | mass drift | internal void | recommendation |
| --- | ---: | ---: | ---: | --- | --- | --- | --- | --- |
| plane020 | 20 | 19.5877 | -0.4123 | unknown | unknown | unknown | unknown | geometry_pending |
| plane030 | 30 | 29.4803 | -0.5197 | unknown | unknown | unknown | unknown | geometry_pending |
| plane060 | 60 | 59.2824 | -0.7176 | unknown | unknown | unknown | unknown | geometry_pending |
| plane090 | 90 | 89.0716 | -0.9284 | unknown | unknown | unknown | unknown | geometry_pending |
| plane120 | 120 | 118.7521 | -1.2479 | unknown | unknown | unknown | unknown | geometry_pending |

All selected flat-wall angle errors are below the 3 deg threshold. That is a
useful runtime-sanity signal, but it is not enough for WP1 closure because the
height, contact radius, mass-drift, and internal-void gates remain unresolved.

## Short-Write Eligibility

No WP1 selected case is `eligible_for_short_write`.

Reason:

```text
height_error unknown
contact_radius_error unknown
phase_mass_relative_change unknown
internal_void_count unknown
```

Because no case is eligible, no short-write templates were generated under:

```text
cases/track_a_usable_angle_ladder_20260613/short_write_candidates/plane
```

Because plane030 and plane090 are not both eligible, the 100-step short-write
smoke was not run, and no files were generated under:

```text
runtime_outputs/wp1_plane_short_write_20260614
```

## Internal Bubble / Void

No internal bubble or void can be confirmed from the current local lightweight
outputs. The required raw PhaseField/interface data is absent, so
`internal_void_count` and `center_bubble_count` remain `unknown`.

This is a WP1 stop condition for closure and write-mode promotion.

## Proceed-To-WP2 Decision

It is not safe to proceed to WP2 cylinder blocker attribution as a closed
flat-wall baseline yet.

Current WP1 interpretation:

```text
flat-wall angle response is encouraging
flat-wall geometry closure is incomplete
short-write gate is not passed
WP2 should wait for flat h/a/mass/void closure or an explicit decision to treat
WP2 as transfer-only work without flat closure promotion
```

The next WP1 action should be one of:

```text
recover retained raw flat-wall VTI/PVTI/PRI/VTK fields if they exist remotely
rerun only selected flat-wall shadow cases while retaining raw fields long enough
to compute h_sim, a_sim, mass drift, and internal void count
```

No longer flat run, no cylinder run, no sphere run, and no write run is
authorized by this report.

## Repository Safety

Expected committed artifacts are lightweight only:

```text
scripts/postprocess_track_a_shadow_matrix_20260613.py
artifacts/track_a_usable_angle_ladder_summary_20260613/wp1_plane_geometry_summary.csv
artifacts/track_a_usable_angle_ladder_summary_20260613/wp1_plane_geometry_summary.json
artifacts/track_a_usable_angle_ladder_summary_20260613/wp1_plane_geometry_report.md
docs/wp1_flat_wall_closure_report_20260614.md
```

Raw simulation fields, binaries, archives, credentials, and `runtime_outputs/`
must not be committed.
