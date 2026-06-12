# Stage8 Boundary-Fluid Gradient Wetting Diagnostic

Date: 2026-06-12

## Status

`runtime_sanity / exploratory_not_validation`.

This is a diagnostic packet, not a PRE 2025 reproduction, not a validation
result, and not a production fix. The z48 sphere gate remains blocked until the
flat-wall Stage8 mode2 path is extended and audited. The Stage8 mode3 path is
already `failed_negative_evidence`.

## Source Lane

- Source lane: `/home/yuan/src/TCLB_stage8_boundary_fluid_gradient_wetting_diag_20260612`.
- Public snapshot: `third_party/tclb_snapshots/stage8_boundary_fluid_gradient_wetting_diag`.
- Based on Stage7b low-angle signed-wall diagnostic lane.
- Source generation return code: `0`.
- Build return code: `0`.
- Binary SHA256: `387f5c1dd78e1b7cef1807060407bfed55dac039aac8ca3d98a28c2d710c3e84`.
- Build target: `CLB/d3q27_pf_velocity_q27_geometric/main`.

Provenance is stored under
`artifacts/stage8_boundary_fluid_gradient_provenance_20260612`.

## Code Contract

Stage8 stops trying to solve the low-angle case by stronger solid-wall ghost
writes. Instead it tests a fluid-boundary gradient correction route.

New settings:

- `Stage8GradientWettingMode`
- `Stage8ActiveCMin`
- `Stage8ActiveGradMin`
- `Stage8ActiveTangentMin`
- `Stage8RelaxationTau`

New diagnostic fields / quantities:

- `WallStage8GradMode`
- `WallStage8ActiveWeight`
- `WallStage8NormalGradRaw`
- `WallStage8NormalGradTarget`
- `WallStage8ContactResidual`
- `WallStage8TangentGradMag`
- `WallStage8TargetCos`
- `WallStage8GradWriteDeltaMag`
- `WallStage8LimiterReason`

Mode semantics used in this packet:

| Mode | Meaning | Current decision |
|---:|---|---|
| 0 | Stage8 off; profile wall path control | `runtime_sanity` control |
| 1 | shadow diagnostics only | `runtime_sanity` control |
| 2 | write corrected `gradPhiVal_*` after boundary gradient calculation | active candidate |
| 3 | also correct `calcGradPhi()` result used by collision/force path | `failed_negative_evidence` |

Important limitation: flat-wall tests set the global `radAngle` to the flat-wall
target so fluid nodes can read the desired angle. This is valid for the flat
wall gate only. Sphere cases still need a local wall-angle transfer/diagnostic
before Stage8 can be used as a sphere candidate.

## Disk Incident And Cleanup

Before the valid Stage8 smoke, the remote run root was full:

```text
/mnt/8A0E24070E23EAC1: 894G used, 0 available, 100% full
inode usage: 99%
```

The first Stage8 10k attempt wrote about 1.2 GB per VTI frame because Stage8
case generation accidentally included the full Stage7 diagnostic field set. The
final VTI was truncated, so VTK parsing failed. This was a storage/output
failure, not a solver numerical failure.

Cleanup removed only raw `.vti/.pvti/.pri` files from selected diagnostic and
old dynamic run directories while preserving XML, logs, CSV, JSON, PNG, and
analysis folders. After cleanup:

```text
/mnt/8A0E24070E23EAC1: 729G used, 166G available, 82% full
inode usage: 2%
```

Cleanup logs are stored under
`artifacts/stage8_boundary_fluid_gradient_wetting_20260612/cleanup_logs`.

The generator was then changed so Stage8 smoke defaults to this light VTK list:

```text
PhaseField,U,P,Rho,BOUNDARY,WallBCPath,WallStage8*
```

Full pre-Stage8 wall diagnostics now require `--full-wall-diagnostics`.

## Gate: Wall011 Four-Mode 2000-Step Smoke

Run root:
`/mnt/8A0E24070E23EAC1/runs/tclb_flat_wall_cap_stage8_wall011_modes_light_20260612`.

Domain: `128 x 96 x 128`; cap initializer: theta030; wall `radAngle=11d`;
`IntWidth=6`; `M=0.1`; VTK steps `0,1000,2000`; no plot generation.

| Case | Mode | Solver rc | Finiteness rc | Post rc | Final status | Key result |
|---|---:|---:|---:|---:|---|---|
| `cap_theta030_wall011_mode0` | 0 | 0 | 0 | 0 | `runtime_sanity` | nonfinite 0; final angle 29.5076 deg; max Mach 1.04e-5 |
| `cap_theta030_wall011_mode1` | 1 | 0 | 0 | 0 | `runtime_sanity` | shadow diagnostics finite; same physical result as mode0 |
| `cap_theta030_wall011_mode2` | 2 | 0 | 0 | 0 | `runtime_sanity` | finite and same physical result as mode1 at 2000 step |
| `cap_theta030_wall011_mode3` | 3 | 0 | 2 | 0 | `failed_negative_evidence` | CSV NaN starts at 1400; by 2000 physical fields are nonfinite |

Mode3 details:

- At 1000 step, max Mach is already about `0.484`, far above the intended
  static gate scale.
- At 1400 step, CSV contains NaN in density, kinetic energy, liquid velocity,
  and liquid phase columns.
- At 2000 step, `PhaseField`, `U`, `P`, and `Rho` contain large nonfinite counts
  in fluid cells.

Decision: do not use mode3 for sphere or longer flat-wall runs.

## Gate: Mode2 10000-Step Light Extension

Run root:
`/mnt/8A0E24070E23EAC1/runs/tclb_flat_wall_cap_stage8_wall011_mode2_10k_light_20260612`.

Only `cap_theta030_wall011_mode2` was executed.

| Step | Apparent angle deg | Phase drift | Rho drift | Max Mach | Nonfinite | Stage8 active sum | p99 residual | Max grad write delta |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 29.3973 | 0 | 0 | 0 | 0 | 7536 | 0.1358 | 0.2540 |
| 5000 | 29.5573 | -0.002102 | -0.002044 | 1.196e-5 | 0 | 9068 | 0.07033 | 0.1822 |
| 10000 | 29.5883 | -0.002602 | -0.002530 | 1.346e-5 | 0 | 9752 | 0.05802 | 0.1567 |

Decision: Stage8 mode2 passes the 10k flat-wall runtime sanity check. It is not
yet a fix. It needs a 50k flat-wall extension and angle sweep before any sphere
shadow test.

## Uploaded Evidence

- `third_party/tclb_snapshots/stage8_boundary_fluid_gradient_wetting_diag`
- `patches/stage8_boundary_fluid_gradient_wetting_20260612`
- `artifacts/stage8_boundary_fluid_gradient_provenance_20260612`
- `artifacts/stage8_boundary_fluid_gradient_wetting_20260612`
- `cases/diagnostics/flat_wall_cap_stage8_wall011_modes_light_20260612`
- `cases/diagnostics/flat_wall_cap_stage8_wall011_mode2_10k_light_20260612`
- `scripts/hm570_run_flat_wall_cap_stage8_wall011_modes_20260612.sh`

Raw `.vti/.pvti/.pri` fields remain remote-only and are intentionally not
included in the public repository.

## Next Gate

1. Do not run z48 sphere yet.
2. Run Stage8 mode2 to 50k for `wall011`; keep VTK cadence sparse and light.
3. If 50k passes, run low-angle flat scan for mode2: `wall005/008/011/015/020/025/030`.
4. Only after flat scan passes, implement sphere local wall-angle transfer or
   diagnostic proof that the fluid boundary reads the sphere target angle.
5. Then run z48 sphere in shadow mode before any Stage8 sphere write.
