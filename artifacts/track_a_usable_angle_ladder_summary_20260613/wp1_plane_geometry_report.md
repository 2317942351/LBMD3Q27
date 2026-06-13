# WP1 Plane Geometry Summary

Status: `runtime_sanity / exploratory_not_validation`.

This is not PRE reproduction, not validation, and not a production fix.
No solver physics code was modified and no solver run is launched by this report.

## Scope

Selected flat-wall cases: plane020, plane030, plane060, plane090, plane120.
Plane150, cylinder, sphere, sphere11, liquid impact, write mode, and 50k runs are excluded.

## Result

Eligible for short write:
- `track_a_plane_theta020_shadow`
- `track_a_plane_theta030_shadow`
- `track_a_plane_theta060_shadow`
- `track_a_plane_theta090_shadow`
- `track_a_plane_theta120_shadow`

## Cases

- `track_a_plane_theta020_shadow`: `eligible_for_short_write`; theta_fit=19.52739006480535; theta_error=-0.4726099351946509; h_error=0.04783438656527848; a_error=0.02432060891103927; internal_void=0; normal_limiter=0.024431625381744145; reason=shadow and geometric metrics meet Track A planning gates
- `track_a_plane_theta030_shadow`: `eligible_for_short_write`; theta_fit=29.458158463653998; theta_error=-0.5418415363460021; h_error=0.03629187899555706; a_error=0.017736884531857063; internal_void=0; normal_limiter=0.0; reason=shadow and geometric metrics meet Track A planning gates
- `track_a_plane_theta060_shadow`: `eligible_for_short_write`; theta_fit=59.25440044959029; theta_error=-0.7455995504097075; h_error=0.02260960230506943; a_error=0.007755417898413806; internal_void=0; normal_limiter=0.0; reason=shadow and geometric metrics meet Track A planning gates
- `track_a_plane_theta090_shadow`: `eligible_for_short_write`; theta_fit=89.04242824425802; theta_error=-0.9575717557419807; h_error=0.016784315281038804; a_error=0.00021318736172948539; internal_void=0; normal_limiter=0.0; reason=shadow and geometric metrics meet Track A planning gates
- `track_a_plane_theta120_shadow`: `eligible_for_short_write`; theta_fit=118.69644164613136; theta_error=-1.3035583538686382; h_error=0.013368369606272544; a_error=0.012723959932024615; internal_void=0; normal_limiter=0.0; reason=shadow and geometric metrics meet Track A planning gates

## Interpretation

The raw-retained WP1 flat-wall rerun provides PhaseField/VTI-derived
`theta_fit`, `h_sim`, `a_sim`, mass drift, and internal-void metrics for
the selected flat-wall cases. These are planning-gate metrics only, not
validation or publication-ready evidence.

## Short Write Decision

Plane030 and plane090 are eligible, and the 100-step short-write smoke summary is present under `wp1_write100/`.

No validation claim is made; this remains `runtime_sanity / exploratory_not_validation`.