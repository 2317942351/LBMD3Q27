# Stage8c Local Wall-Angle Boundary-Gradient Candidate

Date: 2026-06-12

## Status

`runtime_sanity / exploratory_not_validation`.

This packet is a boundary-geometry diagnostic and candidate implementation. It
is not a PRE reproduction, not validation, and not a production fix.

## Source Lane

- Remote source lane:
  `/home/yuan/src/TCLB_stage8c_local_angle_boundary_gradient_candidate_20260612`
- Public snapshot:
  `third_party/tclb_snapshots/stage8c_local_angle_boundary_gradient_candidate_diag`
- Based on Stage8 boundary-fluid-gradient diagnostic, not clean upstream.
- Build target: `CLB/d3q27_pf_velocity_q27_geometric/main`
- Source generation return code: `0`
- Build return code: `0`
- Binary SHA256:
  `df9bb0a9f465daf72170e50ff13d37beeb832b36876e8dc60f653d1ea2c17182`

Provenance is stored under:

```text
artifacts/stage8c_local_angle_boundary_gradient_provenance_20260612
```

## Code Contract

Stage8c keeps the Stage8 fluid-boundary gradient route, but replaces the
flat-wall-only global angle assumption with boundary-to-fluid local transfer.

New wall-side fields:

- `Stage8LocalWallAngle`
- `Stage8LocalWallNormal_x/y/z`

New fluid-side fields:

- `Stage8FluidWallAngle`
- `Stage8FluidWallNormal_x/y/z`
- `Stage8FluidWallDataCount`

New candidate/diagnostic fields:

- `Stage8GradCandidate_x/y/z`
- `Stage8GradCandidateUse`
- `Stage8NormalAgreement`
- `Stage8UsedGeomNormal`

New settings:

- `Stage8UseLocalWallAngle`
- `Stage8UseWallGeomNormal`
- `Stage8NormalDotMin`
- `Stage8MaxGradDelta`
- `Stage8OperatorMode`

Mode semantics:

| Mode | Meaning |
|---:|---|
| 0 | off |
| 1 | shadow only; compute candidate and diagnostics, do not write `gradPhiVal_*` |
| 2 | write corrected `gradPhiVal_*` |
| 3 | reserved no-op; does not map to old Stage8 direct `calcGradPhi()` rewrite |

The old Stage8 `calcGradPhi()` direct rewrite path remains
`failed_negative_evidence` and is disabled in this lane.

## Gate 1 Input

Before modifying Stage8c source, current Stage8 mode2 `wall011` was extended to
50k:

- run root:
  `/mnt/8A0E24070E23EAC1/runs/tclb_flat_wall_cap_stage8_wall011_mode2_50k_light_20260612`
- result: solver rc `0`, finiteness rc `0`, postprocess rc `0`
- final angle: `28.9607 deg`
- final phase drift: `-0.4899%`
- final rho drift: `-0.4763%`
- max Mach: `1.626e-5`
- nonfinite: `0`

This passed the primary runtime thresholds and justified implementing Stage8c.

## Gate 2 Flat Low-Angle Scan

Run root:

```text
/mnt/8A0E24070E23EAC1/runs/tclb_flat_wall_cap_stage8c_low_angle_50k_light_20260612
```

Local curated artifact:

```text
artifacts/stage8c_local_angle_boundary_gradient_20260612/tclb_flat_wall_cap_stage8c_low_angle_50k_light_20260612
```

Case matrix:

```text
cap_theta030_wall005/008/011/015/020/025/030
```

All seven 50k cases completed with solver rc `0`, finiteness rc `0`, and
postprocess rc `0`.

Final 50k summary:

| Case | Apparent angle deg | Phase drift | Rho drift | Max Mach | Nonfinite | Delta limiter count | Active wall angle p50 rad | Active data count p50 | Active normal p05 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| wall005 | 28.9587 | -0.005375 | -0.005226 | 1.760e-5 | 0 | 3808 | 0.087266 | 9 | 1 |
| wall008 | 28.9596 | -0.005183 | -0.005040 | 1.708e-5 | 0 | 0 | 0.139626 | 9 | 1 |
| wall011 | 28.9607 | -0.004899 | -0.004763 | 1.626e-5 | 0 | 0 | 0.191986 | 9 | 1 |
| wall015 | 29.1202 | -0.004369 | -0.004248 | 1.467e-5 | 0 | 0 | 0.261799 | 9 | 1 |
| wall020 | 29.2384 | -0.003476 | -0.003380 | 1.160e-5 | 0 | 0 | 0.349066 | 9 | 1 |
| wall025 | 29.3605 | -0.002421 | -0.002354 | 7.025e-6 | 0 | 0 | 0.436332 | 9 | 1 |
| wall030 | 29.5721 | -0.001357 | -0.001320 | 2.461e-6 | 0 | 0 | 0.523599 | 9 | 1 |

## Decision

Stage8c passes the basic runtime-sanity part of Gate 2:

- all low-angle flat cases remain finite through 50k;
- max Mach is far below `1e-4`;
- phase and rho drift are below `1%`;
- active-region local wall-angle transfer is correct;
- active-region normal agreement is `1.0` in the flat-wall case.

Stage8c does not fully pass the original Gate 2 limiter criterion because
`wall005` triggers `Stage8MaxGradDelta=0.25` on 3808 active cells. The
`wall008-wall030` cases do not trigger the delta limiter.

Current decision:

```text
runtime_sanity / exploratory_not_validation
do_not_promote_to_validation
do_not_run_sphere_write_yet
```

Recommended next step is a z48 sphere local-transfer step0 audit and then
Stage8c `Stage8OperatorMode=1` sphere shadow only. Sphere write mode should wait
until the sphere shadow shows acceptable limiter and normal-orientation
behavior.

## Uploaded Evidence

- Source snapshot:
  `third_party/tclb_snapshots/stage8c_local_angle_boundary_gradient_candidate_diag`
- Patch:
  `third_party/tclb_snapshots/patches/stage8c_local_angle_boundary_gradient_candidate_20260612.diff`
- Flat cases:
  `cases/diagnostics/flat_wall_cap_stage8c_low_angle_50k_light_20260612`
- Runner:
  `scripts/hm570_run_flat_wall_cap_stage8c_low_angle_20260612.sh`
- Postprocess updates:
  `scripts/make_flat_wall_cap_gate_cases.py`
  `scripts/flat_wall_cap_gate_postprocess.py`
- Curated metrics/provenance:
  `artifacts/stage8c_local_angle_boundary_gradient_20260612`
  `artifacts/stage8c_local_angle_boundary_gradient_provenance_20260612`

Raw `.vti/.pvti/.pri` files remain remote-only and are not part of the public
repository packet.
