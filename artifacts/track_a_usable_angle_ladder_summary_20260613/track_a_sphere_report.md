# Track A Overnight Summary

Status: `runtime_sanity / exploratory_not_validation`.

This is not PRE reproduction, not validation, and not a production fix.

Stage8 physics code was not modified by Track A execution. All cases are
Stage8OperatorMode=1 shadow diagnostics; no sphere11 case, write mode,
50k run, liquid-impact run, or high-Weber dynamic run is included.

Start time: 2026-06-14T00:57:46+08:00
End time: 2026-06-14T01:05:57+08:00
GPU used: P100 A/B
Metrics root: `C:\Users\yuanz\Desktop\LBMD3Q27\runtime_outputs\track_a_overnight_20260613`

## Classification Counts

- `pending`: 0
- `incomplete`: 0
- `blocked`: 5
- `shadow_pass`: 0
- `eligible_for_short_write`: 0
- `short_write_pass`: 0

## Cases Ran

- `track_a_sphere_theta030_shadow`: `blocked`; solver_rc=0; post_rc=0; nonfinite=0; Mach=0.000297026348885968; normal_limiter=0.6103286384976526; vector_limiter=0.0; demand_p50=1.3636202622252087; demand_p95=3.0710293583690547; profile_mismatch_p95=0.14305575567646267; theta_fit=unknown; reason=normal limiter fraction is >= 5%
- `track_a_sphere_theta045_shadow`: `blocked`; solver_rc=0; post_rc=0; nonfinite=0; Mach=0.00027805543749489836; normal_limiter=0.3869346733668342; vector_limiter=0.0; demand_p50=0.6752276411053167; demand_p95=2.528299319931715; profile_mismatch_p95=0.07887769157388022; theta_fit=unknown; reason=normal limiter fraction is >= 5%
- `track_a_sphere_theta060_shadow`: `blocked`; solver_rc=0; post_rc=0; nonfinite=0; Mach=0.0002472753519308827; normal_limiter=0.2727272727272727; vector_limiter=0.0; demand_p50=0.5335721454965655; demand_p95=1.5437355299606477; profile_mismatch_p95=0.040631715591699806; theta_fit=unknown; reason=normal limiter fraction is >= 5%
- `track_a_sphere_theta090_shadow`: `blocked`; solver_rc=0; post_rc=0; nonfinite=0; Mach=0.0001469059939116217; normal_limiter=0.3258426966292135; vector_limiter=0.0; demand_p50=0.6879318903077114; demand_p95=1.570437945057872; profile_mismatch_p95=0.019511333009966436; theta_fit=unknown; reason=normal limiter fraction is >= 5%
- `track_a_sphere_theta120_shadow`: `blocked`; solver_rc=0; post_rc=0; nonfinite=0; Mach=2.3800495222913332e-05; normal_limiter=0.29533678756476683; vector_limiter=0.0; demand_p50=0.6934761245686905; demand_p95=1.6814345513288698; profile_mismatch_p95=0.02076421441834178; theta_fit=unknown; reason=normal limiter fraction is >= 5%

## Cases Not Run

- none

## Shadow Pass

- none

## Eligible For Short Write

- none

No 100/1000/5000 short-write templates were generated because no case
reached `eligible_for_short_write`.

## Blocked

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
