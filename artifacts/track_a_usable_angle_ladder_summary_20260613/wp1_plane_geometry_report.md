# WP1 Plane Geometry Summary

Status: `runtime_sanity / exploratory_not_validation`.

This is not PRE reproduction, not validation, and not a production fix.
No solver physics code was modified and no solver run is launched by this report.

## Scope

Selected flat-wall cases: plane020, plane030, plane060, plane090, plane120.
Plane150, cylinder, sphere, sphere11, liquid impact, write mode, and 50k runs are excluded.

## Result

No selected flat-wall case is eligible for short write yet.

## Cases

- `track_a_plane_theta020_shadow`: `geometry_pending`; theta_fit=19.58769239431891; theta_error=-0.4123076056810895; h_error=unknown; a_error=unknown; internal_void=unknown; normal_limiter=0.024431625381744145; reason=runtime shadow gates pass; geometry metrics pending: height_error,contact_radius_error,phase_mass_relative_change,internal_void_count
- `track_a_plane_theta030_shadow`: `geometry_pending`; theta_fit=29.480253287791694; theta_error=-0.5197467122083061; h_error=unknown; a_error=unknown; internal_void=unknown; normal_limiter=0.0; reason=runtime shadow gates pass; geometry metrics pending: height_error,contact_radius_error,phase_mass_relative_change,internal_void_count
- `track_a_plane_theta060_shadow`: `geometry_pending`; theta_fit=59.28239371527601; theta_error=-0.7176062847239919; h_error=unknown; a_error=unknown; internal_void=unknown; normal_limiter=0.0; reason=runtime shadow gates pass; geometry metrics pending: height_error,contact_radius_error,phase_mass_relative_change,internal_void_count
- `track_a_plane_theta090_shadow`: `geometry_pending`; theta_fit=89.07161210372264; theta_error=-0.9283878962773571; h_error=unknown; a_error=unknown; internal_void=unknown; normal_limiter=0.0; reason=runtime shadow gates pass; geometry metrics pending: height_error,contact_radius_error,phase_mass_relative_change,internal_void_count
- `track_a_plane_theta120_shadow`: `geometry_pending`; theta_fit=118.75206151754159; theta_error=-1.2479384824584088; h_error=unknown; a_error=unknown; internal_void=unknown; normal_limiter=0.0; reason=runtime shadow gates pass; geometry metrics pending: height_error,contact_radius_error,phase_mass_relative_change,internal_void_count

## Interpretation

The lightweight Track A metrics include fitted apparent contact angle for the
flat-wall shadow cases, so WP1 can compute `theta_fit_error_deg`.
However, the local `runtime_outputs/track_a_overnight_20260613` tree does not
contain raw VTI/PVTI/PRI/VTK fields or precomputed `h_sim`, `a_sim`,
`height_error`, `contact_radius_error`, or internal-void metrics.
Those values are therefore reported as `unknown` and the cases remain
`geometry_pending` rather than `eligible_for_short_write`.

## Short Write Decision

Plane030 and plane090 are not both eligible because required geometry metrics are pending. No 100-step short-write is run.

No validation claim is made; this remains `runtime_sanity / exploratory_not_validation`.