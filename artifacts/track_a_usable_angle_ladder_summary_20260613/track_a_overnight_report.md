# Track A Overnight Summary

Status: `runtime_sanity / exploratory_not_validation`.

This is not PRE reproduction, not validation, and not a production fix.

Stage8 physics code was not modified by Track A execution. All cases are
Stage8OperatorMode=1 shadow diagnostics; no sphere11 case, write mode,
50k run, liquid-impact run, or high-Weber dynamic run is included.

Start time: 2026-06-14T00:08:42+08:00
End time: 2026-06-14T01:05:57+08:00
GPU used: P100 A/B; Quadro P4000 avoided
Metrics root: `C:\Users\yuanz\Desktop\LBMD3Q27\runtime_outputs\track_a_overnight_20260613`

## Classification Counts

- `pending`: 0
- `incomplete`: 0
- `blocked`: 11
- `shadow_pass`: 6
- `eligible_for_short_write`: 0
- `short_write_pass`: 0

## Cases Ran

- `track_a_plane_theta020_shadow`: `shadow_pass`; solver_rc=0; post_rc=0; nonfinite=0; Mach=1.0911780999993463e-05; normal_limiter=0.024431625381744145; vector_limiter=0.0; demand_p50=0.6396090156309671; demand_p95=0.9580475960097865; profile_mismatch_p95=0.010834945687240142; theta_fit=unknown; reason=runtime shadow gates pass; geometry metrics pending: theta_fit_error_deg,height_error,contact_radius_error,internal_void_count
- `track_a_plane_theta025_shadow`: `shadow_pass`; solver_rc=0; post_rc=0; nonfinite=0; Mach=5.0420053603730275e-06; normal_limiter=0.0; vector_limiter=0.0; demand_p50=0.3848228313355958; demand_p95=0.7385218944460731; profile_mismatch_p95=0.01902471207961194; theta_fit=unknown; reason=runtime shadow gates pass; geometry metrics pending: theta_fit_error_deg,height_error,contact_radius_error,internal_void_count
- `track_a_plane_theta030_shadow`: `shadow_pass`; solver_rc=0; post_rc=0; nonfinite=0; Mach=1.845836766554813e-06; normal_limiter=0.0; vector_limiter=0.0; demand_p50=0.2521981895541087; demand_p95=0.5884620070077589; profile_mismatch_p95=0.024009242960460937; theta_fit=unknown; reason=runtime shadow gates pass; geometry metrics pending: theta_fit_error_deg,height_error,contact_radius_error,internal_void_count
- `track_a_plane_theta060_shadow`: `shadow_pass`; solver_rc=0; post_rc=0; nonfinite=0; Mach=3.663064568138091e-06; normal_limiter=0.0; vector_limiter=0.0; demand_p50=0.1115216371695232; demand_p95=0.23422545639901596; profile_mismatch_p95=0.023221510864591833; theta_fit=unknown; reason=runtime shadow gates pass; geometry metrics pending: theta_fit_error_deg,height_error,contact_radius_error,internal_void_count
- `track_a_plane_theta090_shadow`: `shadow_pass`; solver_rc=0; post_rc=0; nonfinite=0; Mach=6.283466237500005e-06; normal_limiter=0.0; vector_limiter=0.0; demand_p50=0.08241335283213849; demand_p95=0.09012392898446972; profile_mismatch_p95=0.007231858075036386; theta_fit=unknown; reason=runtime shadow gates pass; geometry metrics pending: theta_fit_error_deg,height_error,contact_radius_error,internal_void_count
- `track_a_plane_theta120_shadow`: `shadow_pass`; solver_rc=0; post_rc=0; nonfinite=0; Mach=1.1986576543858989e-05; normal_limiter=0.0; vector_limiter=0.0; demand_p50=0.11192102837667514; demand_p95=0.4049051875343599; profile_mismatch_p95=0.0005208288299375615; theta_fit=unknown; reason=runtime shadow gates pass; geometry metrics pending: theta_fit_error_deg,height_error,contact_radius_error,internal_void_count
- `track_a_plane_theta150_shadow`: `blocked`; solver_rc=0; post_rc=0; nonfinite=0; Mach=1.6389724915510823e-05; normal_limiter=0.12378640776699029; vector_limiter=0.0; demand_p50=0.3336299965578745; demand_p95=1.1684922649821818; profile_mismatch_p95=0.010446565683282791; theta_fit=unknown; reason=normal limiter fraction is >= 5%
- `track_a_cylinder_theta030_shadow`: `blocked`; solver_rc=0; post_rc=0; nonfinite=0; Mach=0.00035851870931226533; normal_limiter=0.7012448132780082; vector_limiter=0.0; demand_p50=1.7604168099976722; demand_p95=2.976725979392017; profile_mismatch_p95=0.13006566584921217; theta_fit=unknown; reason=normal limiter fraction is >= 5%
- `track_a_cylinder_theta045_shadow`: `blocked`; solver_rc=0; post_rc=0; nonfinite=0; Mach=0.00034069847600698406; normal_limiter=0.5066079295154186; vector_limiter=0.0; demand_p50=1.0405338286087888; demand_p95=2.4555008150089974; profile_mismatch_p95=0.06847859913832277; theta_fit=unknown; reason=normal limiter fraction is >= 5%
- `track_a_cylinder_theta060_shadow`: `blocked`; solver_rc=0; post_rc=0; nonfinite=0; Mach=0.0003064738012339041; normal_limiter=0.36666666666666664; vector_limiter=0.0; demand_p50=0.8020702759923177; demand_p95=1.519903662935152; profile_mismatch_p95=0.03886362924485677; theta_fit=unknown; reason=normal limiter fraction is >= 5%
- `track_a_cylinder_theta090_shadow`: `blocked`; solver_rc=0; post_rc=0; nonfinite=0; Mach=0.00018166492596243596; normal_limiter=0.3192488262910798; vector_limiter=0.0; demand_p50=0.7310559402658386; demand_p95=1.9999999934343258; profile_mismatch_p95=0.014264934613940898; theta_fit=unknown; reason=normal limiter fraction is >= 5%
- `track_a_cylinder_theta120_shadow`: `blocked`; solver_rc=0; post_rc=0; nonfinite=0; Mach=3.86959776745543e-05; normal_limiter=0.3700440528634361; vector_limiter=0.0; demand_p50=0.8066823196062725; demand_p95=1.8471154831857557; profile_mismatch_p95=0.021856743292136178; theta_fit=unknown; reason=normal limiter fraction is >= 5%
- `track_a_sphere_theta030_shadow`: `blocked`; solver_rc=0; post_rc=0; nonfinite=0; Mach=0.000297026348885968; normal_limiter=0.6103286384976526; vector_limiter=0.0; demand_p50=1.3636202622252087; demand_p95=3.0710293583690547; profile_mismatch_p95=0.14305575567646267; theta_fit=unknown; reason=normal limiter fraction is >= 5%
- `track_a_sphere_theta045_shadow`: `blocked`; solver_rc=0; post_rc=0; nonfinite=0; Mach=0.00027805543749489836; normal_limiter=0.3869346733668342; vector_limiter=0.0; demand_p50=0.6752276411053167; demand_p95=2.528299319931715; profile_mismatch_p95=0.07887769157388022; theta_fit=unknown; reason=normal limiter fraction is >= 5%
- `track_a_sphere_theta060_shadow`: `blocked`; solver_rc=0; post_rc=0; nonfinite=0; Mach=0.0002472753519308827; normal_limiter=0.2727272727272727; vector_limiter=0.0; demand_p50=0.5335721454965655; demand_p95=1.5437355299606477; profile_mismatch_p95=0.040631715591699806; theta_fit=unknown; reason=normal limiter fraction is >= 5%
- `track_a_sphere_theta090_shadow`: `blocked`; solver_rc=0; post_rc=0; nonfinite=0; Mach=0.0001469059939116217; normal_limiter=0.3258426966292135; vector_limiter=0.0; demand_p50=0.6879318903077114; demand_p95=1.570437945057872; profile_mismatch_p95=0.019511333009966436; theta_fit=unknown; reason=normal limiter fraction is >= 5%
- `track_a_sphere_theta120_shadow`: `blocked`; solver_rc=0; post_rc=0; nonfinite=0; Mach=2.3800495222913332e-05; normal_limiter=0.29533678756476683; vector_limiter=0.0; demand_p50=0.6934761245686905; demand_p95=1.6814345513288698; profile_mismatch_p95=0.02076421441834178; theta_fit=unknown; reason=normal limiter fraction is >= 5%

## Cases Not Run

- none

## Shadow Pass

- `track_a_plane_theta020_shadow`
- `track_a_plane_theta025_shadow`
- `track_a_plane_theta030_shadow`
- `track_a_plane_theta060_shadow`
- `track_a_plane_theta090_shadow`
- `track_a_plane_theta120_shadow`

## Eligible For Short Write

- none

No 100/1000/5000 short-write templates were generated because no case
reached `eligible_for_short_write`.

## Blocked

- `track_a_plane_theta150_shadow`: normal limiter fraction is >= 5%
- `track_a_cylinder_theta030_shadow`: normal limiter fraction is >= 5%
- `track_a_cylinder_theta045_shadow`: normal limiter fraction is >= 5%
- `track_a_cylinder_theta060_shadow`: normal limiter fraction is >= 5%
- `track_a_cylinder_theta090_shadow`: normal limiter fraction is >= 5%
- `track_a_cylinder_theta120_shadow`: normal limiter fraction is >= 5%
- `track_a_sphere_theta030_shadow`: normal limiter fraction is >= 5%
- `track_a_sphere_theta045_shadow`: normal limiter fraction is >= 5%
- `track_a_sphere_theta060_shadow`: normal limiter fraction is >= 5%
- `track_a_sphere_theta090_shadow`: normal limiter fraction is >= 5%
- `track_a_sphere_theta120_shadow`: normal limiter fraction is >= 5%

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
