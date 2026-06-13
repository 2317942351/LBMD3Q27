# Track A Overnight Summary

Status: `runtime_sanity / exploratory_not_validation`.

This is not PRE reproduction, not validation, and not a production fix.

Stage8 physics code was not modified by Track A execution. All cases are
Stage8OperatorMode=1 shadow diagnostics; no sphere11 case, write mode,
50k run, liquid-impact run, or high-Weber dynamic run is included.

Start time: unknown
End time: unknown
GPU used: unknown
Metrics root: `C:\Users\yuanz\Desktop\LBMD3Q27\runtime_outputs\track_a_overnight_20260613`

## Classification Counts

- `pending`: 0
- `incomplete`: 0
- `blocked`: 1
- `geometry_pending`: 6
- `shadow_pass`: 0
- `eligible_for_short_write`: 0
- `short_write_pass`: 0

## Cases Ran

- `track_a_plane_theta020_shadow`: `geometry_pending`; solver_rc=0; post_rc=0; nonfinite=0; Mach=1.0911780999993463e-05; normal_limiter=0.024431625381744145; vector_limiter=0.0; demand_p50=0.6396090156309671; demand_p95=0.9580475960097865; profile_mismatch_p95=0.010834945687240142; theta_fit=unknown; reason=runtime shadow gates pass; geometry metrics pending: height_error,contact_radius_error,phase_mass_relative_change,internal_void_count
- `track_a_plane_theta025_shadow`: `geometry_pending`; solver_rc=0; post_rc=0; nonfinite=0; Mach=5.0420053603730275e-06; normal_limiter=0.0; vector_limiter=0.0; demand_p50=0.3848228313355958; demand_p95=0.7385218944460731; profile_mismatch_p95=0.01902471207961194; theta_fit=unknown; reason=runtime shadow gates pass; geometry metrics pending: height_error,contact_radius_error,phase_mass_relative_change,internal_void_count
- `track_a_plane_theta030_shadow`: `geometry_pending`; solver_rc=0; post_rc=0; nonfinite=0; Mach=1.845836766554813e-06; normal_limiter=0.0; vector_limiter=0.0; demand_p50=0.2521981895541087; demand_p95=0.5884620070077589; profile_mismatch_p95=0.024009242960460937; theta_fit=unknown; reason=runtime shadow gates pass; geometry metrics pending: height_error,contact_radius_error,phase_mass_relative_change,internal_void_count
- `track_a_plane_theta060_shadow`: `geometry_pending`; solver_rc=0; post_rc=0; nonfinite=0; Mach=3.663064568138091e-06; normal_limiter=0.0; vector_limiter=0.0; demand_p50=0.1115216371695232; demand_p95=0.23422545639901596; profile_mismatch_p95=0.023221510864591833; theta_fit=unknown; reason=runtime shadow gates pass; geometry metrics pending: height_error,contact_radius_error,phase_mass_relative_change,internal_void_count
- `track_a_plane_theta090_shadow`: `geometry_pending`; solver_rc=0; post_rc=0; nonfinite=0; Mach=6.283466237500005e-06; normal_limiter=0.0; vector_limiter=0.0; demand_p50=0.08241335283213849; demand_p95=0.09012392898446972; profile_mismatch_p95=0.007231858075036386; theta_fit=unknown; reason=runtime shadow gates pass; geometry metrics pending: height_error,contact_radius_error,phase_mass_relative_change,internal_void_count
- `track_a_plane_theta120_shadow`: `geometry_pending`; solver_rc=0; post_rc=0; nonfinite=0; Mach=1.1986576543858989e-05; normal_limiter=0.0; vector_limiter=0.0; demand_p50=0.11192102837667514; demand_p95=0.4049051875343599; profile_mismatch_p95=0.0005208288299375615; theta_fit=unknown; reason=runtime shadow gates pass; geometry metrics pending: height_error,contact_radius_error,phase_mass_relative_change,internal_void_count
- `track_a_plane_theta150_shadow`: `blocked`; solver_rc=0; post_rc=0; nonfinite=0; Mach=1.6389724915510823e-05; normal_limiter=0.12378640776699029; vector_limiter=0.0; demand_p50=0.3336299965578745; demand_p95=1.1684922649821818; profile_mismatch_p95=0.010446565683282791; theta_fit=unknown; reason=normal limiter fraction is >= 5%

## Cases Not Run

- none

## Shadow Pass

- none

## Geometry Pending

- `track_a_plane_theta020_shadow`: runtime shadow gates pass; geometry metrics pending: height_error,contact_radius_error,phase_mass_relative_change,internal_void_count
- `track_a_plane_theta025_shadow`: runtime shadow gates pass; geometry metrics pending: height_error,contact_radius_error,phase_mass_relative_change,internal_void_count
- `track_a_plane_theta030_shadow`: runtime shadow gates pass; geometry metrics pending: height_error,contact_radius_error,phase_mass_relative_change,internal_void_count
- `track_a_plane_theta060_shadow`: runtime shadow gates pass; geometry metrics pending: height_error,contact_radius_error,phase_mass_relative_change,internal_void_count
- `track_a_plane_theta090_shadow`: runtime shadow gates pass; geometry metrics pending: height_error,contact_radius_error,phase_mass_relative_change,internal_void_count
- `track_a_plane_theta120_shadow`: runtime shadow gates pass; geometry metrics pending: height_error,contact_radius_error,phase_mass_relative_change,internal_void_count

## Eligible For Short Write

- none

No 100/1000/5000 short-write templates were generated because no case
reached `eligible_for_short_write`.

## Blocked

- `track_a_plane_theta150_shadow`: normal limiter fraction is >= 5%

## Execution Notes

- Plane cases use a spherical-cap initializer and provide fitted apparent
  contact angle when the flat-wall postprocessor succeeds.
- Cylinder cases use a z-extruded solid cylinder with a tangent diffuse
  spherical droplet. This is a one-direction-curvature runtime-feasibility
  diagnostic, not cap-on-cylinder validation.
- Cylinder and sphere classifications are driven by shadow limiter metrics
  because full local angle, axisymmetry, and internal-void geometry metrics
  remain pending.
- In the remote queue logs, solver runtime was tens of seconds per case;
  the main wall-time cost was Python/VTI postprocessing and raw-field
  cleanup after each case.

## Metrics Included

Each CSV/JSON row includes available values for nonfinite_total, max_mach,
phase/rho drift, limiter fractions, wall-angle/normal statistics,
profile-target mismatch, active and limiter counts, candidate demand,
fitted apparent angle when available, mass drift when available, and
internal void count when available.

No validation claim is made; this remains `runtime_sanity / exploratory_not_validation`.
