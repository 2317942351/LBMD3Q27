# Track A Overnight Summary

Status: `runtime_sanity / exploratory_not_validation`.

This is not PRE reproduction, not validation, and not a production fix.

Stage8 physics code was not modified by Track A execution. All cases are
Stage8OperatorMode=1 shadow diagnostics; no sphere11 case, write mode,
50k run, liquid-impact run, or high-Weber dynamic run is included.

Start time: 2026-06-14T00:35:39+08:00
End time: 2026-06-14T00:53:04+08:00
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

- `track_a_cylinder_theta030_shadow`: `blocked`; solver_rc=0; post_rc=0; nonfinite=0; Mach=0.00035851870931226533; normal_limiter=0.7012448132780082; vector_limiter=0.0; demand_p50=1.7604168099976722; demand_p95=2.976725979392017; profile_mismatch_p95=0.13006566584921217; theta_fit=unknown; reason=normal limiter fraction is >= 5%
- `track_a_cylinder_theta045_shadow`: `blocked`; solver_rc=0; post_rc=0; nonfinite=0; Mach=0.00034069847600698406; normal_limiter=0.5066079295154186; vector_limiter=0.0; demand_p50=1.0405338286087888; demand_p95=2.4555008150089974; profile_mismatch_p95=0.06847859913832277; theta_fit=unknown; reason=normal limiter fraction is >= 5%
- `track_a_cylinder_theta060_shadow`: `blocked`; solver_rc=0; post_rc=0; nonfinite=0; Mach=0.0003064738012339041; normal_limiter=0.36666666666666664; vector_limiter=0.0; demand_p50=0.8020702759923177; demand_p95=1.519903662935152; profile_mismatch_p95=0.03886362924485677; theta_fit=unknown; reason=normal limiter fraction is >= 5%
- `track_a_cylinder_theta090_shadow`: `blocked`; solver_rc=0; post_rc=0; nonfinite=0; Mach=0.00018166492596243596; normal_limiter=0.3192488262910798; vector_limiter=0.0; demand_p50=0.7310559402658386; demand_p95=1.9999999934343258; profile_mismatch_p95=0.014264934613940898; theta_fit=unknown; reason=normal limiter fraction is >= 5%
- `track_a_cylinder_theta120_shadow`: `blocked`; solver_rc=0; post_rc=0; nonfinite=0; Mach=3.86959776745543e-05; normal_limiter=0.3700440528634361; vector_limiter=0.0; demand_p50=0.8066823196062725; demand_p95=1.8471154831857557; profile_mismatch_p95=0.021856743292136178; theta_fit=unknown; reason=normal limiter fraction is >= 5%

## Cases Not Run

- none

## Shadow Pass

- none

## Eligible For Short Write

- none

No 100/1000/5000 short-write templates were generated because no case
reached `eligible_for_short_write`.

## Blocked

- `track_a_cylinder_theta030_shadow`: normal limiter fraction is >= 5%
- `track_a_cylinder_theta045_shadow`: normal limiter fraction is >= 5%
- `track_a_cylinder_theta060_shadow`: normal limiter fraction is >= 5%
- `track_a_cylinder_theta090_shadow`: normal limiter fraction is >= 5%
- `track_a_cylinder_theta120_shadow`: normal limiter fraction is >= 5%

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
