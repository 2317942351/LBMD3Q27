# WP1 Flat Wall Closure Report

Status: `runtime_sanity / exploratory_not_validation`.

This is not PRE reproduction, not validation, not a production fix, and not a
publication-ready result. Solver physics code was not modified. WP1 only closes
the flat-wall planning gate needed before WP2 cylinder blocker attribution.

## Scope

Selected flat-wall shadow cases:

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

WP1 first checked whether old Track A raw fields could be recovered. Remote
`track_a_overnight_20260613` contained no retained flat-wall raw VTI/PVTI/PRI
fields, so the selected flat-wall shadow cases were rerun with raw retention.

Remote retained raw:

```text
/media/yuan/新加卷1/RUNS/runs/track_a_wp1_flat_raw_20260614
raw field files: 30
remote size: 28G
```

The public repository contains only lightweight CSV/JSON/Markdown/log summaries,
not raw fields.

## Shadow Results

All five selected flat-wall shadow cases completed with:

```text
solver_returncode = 0
postprocess_returncode = 0
nonfinite_total = 0
internal_void_count = 0
center_bubble_count = 0
```

| case | theta fit error deg | h error | a error | phase mass drift | max Mach | normal limiter |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| plane020 | -0.4726 | 0.0478 | 0.0243 | -0.00234 | 1.09e-05 | 0.0244 |
| plane030 | -0.5418 | 0.0363 | 0.0177 | -0.00131 | 1.85e-06 | 0 |
| plane060 | -0.7456 | 0.0226 | 0.00776 | -0.000296 | 3.66e-06 | 0 |
| plane090 | -0.9576 | 0.0168 | 0.000213 | 1.78e-05 | 6.28e-06 | 0 |
| plane120 | -1.3036 | 0.0134 | 0.0127 | 0.000184 | 1.20e-05 | 0 |

All selected cases meet the WP1 planning gate:

```text
abs(theta_fit - theta_target) < 3 deg
height error < 5%
contact radius error < 5%
mass drift < 1%
nonfinite_total = 0
internal void count = 0
```

## Write Smoke

Because `plane030` and `plane090` passed the shadow geometry gate, WP1 ran only
the approved 100-step flat-wall write smoke:

```text
/media/yuan/新加卷1/RUNS/runs/wp1_plane_short_write_100_20260614
Stage8OperatorMode = 2
iterations = 100
raw field files: 8
```

| case | theta fit error deg | h error | a error | phase mass drift | max Mach | internal void |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| plane030 write100 | -0.5501 | 0.0364 | 0.0176 | -0.00129 | 1.18e-05 | 0 |
| plane090 write100 | -0.9531 | 0.0168 | 0.000282 | 2.32e-06 | 6.60e-06 | 0 |

Both write-smoke cases completed with solver and postprocess return code 0 and
`nonfinite_total = 0`.

## Artifacts

Shadow summaries:

```text
artifacts/track_a_usable_angle_ladder_summary_20260613/wp1_plane_geometry_summary.csv
artifacts/track_a_usable_angle_ladder_summary_20260613/wp1_plane_geometry_summary.json
artifacts/track_a_usable_angle_ladder_summary_20260613/wp1_plane_geometry_report.md
artifacts/track_a_usable_angle_ladder_summary_20260613/wp1_flat_raw_plane_summary.csv
artifacts/track_a_usable_angle_ladder_summary_20260613/wp1_flat_raw_plane_summary.json
artifacts/track_a_usable_angle_ladder_summary_20260613/wp1_flat_raw_plane_report.md
```

Write-smoke summaries:

```text
artifacts/track_a_usable_angle_ladder_summary_20260613/wp1_write100/wp1_write100_summary.csv
artifacts/track_a_usable_angle_ladder_summary_20260613/wp1_write100/wp1_write100_summary.json
artifacts/track_a_usable_angle_ladder_summary_20260613/wp1_write100/solver.log
artifacts/track_a_usable_angle_ladder_summary_20260613/wp1_write100/postprocess.log
```

## Decision

WP1 is closed for planning:

```text
flat_wall_middle_angle_closed_for_planning
```

It is now reasonable to proceed to WP2 cylinder blocker attribution, still under
`runtime_sanity / exploratory_not_validation`.

This does not authorize cylinder write mode, sphere write mode, sphere11, 50k,
dynamic impact, validation claims, or publication claims.
