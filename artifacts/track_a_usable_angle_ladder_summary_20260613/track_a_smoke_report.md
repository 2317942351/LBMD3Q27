# Track A Overnight Summary

Status: `runtime_sanity / exploratory_not_validation`.

This is not PRE reproduction, not validation, and not a production fix.

Start time: unknown
End time: unknown
GPU used: P100 A
Metrics root: `C:\Users\yuanz\Desktop\LBMD3Q27\runtime_outputs\track_a_overnight_20260613`

## Classification Counts

- `pending`: 0
- `incomplete`: 0
- `blocked`: 0
- `shadow_pass`: 2
- `eligible_for_short_write`: 0
- `short_write_pass`: 0

## Cases Ran

- `track_a_plane_theta030_shadow`: `shadow_pass`; solver_rc=0; post_rc=0; nonfinite=0; Mach=1.845836766554813e-06; normal_limiter=0.0; vector_limiter=0.0
- `track_a_plane_theta090_shadow`: `shadow_pass`; solver_rc=0; post_rc=0; nonfinite=0; Mach=6.283466237500005e-06; normal_limiter=0.0; vector_limiter=0.0

## Cases Not Run

- none

## Shadow Pass

- `track_a_plane_theta030_shadow`
- `track_a_plane_theta090_shadow`

## Eligible For Short Write

- none

## Blocked

- none

## Metrics Included

Each CSV/JSON row includes available values for nonfinite_total, max_mach,
phase/rho drift, limiter fractions, wall-angle/normal statistics,
profile-target mismatch, active and limiter counts, candidate demand,
fitted apparent angle when available, mass drift when available, and
internal void count when available.

No validation claim is made; this remains `runtime_sanity / exploratory_not_validation`.
