# Stage7b Low-Angle Signed Wall Stability Diagnostic

Date: 2026-06-12

## Status

`runtime_sanity / exploratory_not_validation`.

This is a diagnostic packet, not a PRE 2025 reproduction, not a validation
result, and not a production fix. The z48 sphere signed-write gate remains
blocked by the low-angle flat-wall scan decision below.

## Source Lane

- Source lane: `/home/yuan/src/TCLB_stage7b_low_angle_signed_wall_stability_diag_20260612`.
- Based on Stage7 signed wall ghost diagnostic lane.
- Build/source return codes: `0/0`.
- Binary SHA256: `44e99b9375dd6672ddd421bede3ff4f7c2f91f69c1ee3280a120e52df6745f11`.
- Public snapshot: `third_party/tclb_snapshots/stage7b_low_angle_signed_wall_stability_diag`.

## Code Contract

Stage7b keeps Stage7 as a control and adds an explicit mode switch:

- `Stage7SignedMode=0`: profile write, signed diagnostics only.
- `Stage7SignedMode=1`: shadow candidate only; actual write remains profile.
- `Stage7SignedMode=2`: Stage7 full signed write control.
- `Stage7SignedMode=3`: active relaxed signed write candidate.

New settings include `Stage7DeltaQScale`, `Stage7DeltaQAbsCap`,
`Stage7DenomFloor`, `Stage7ActiveCMin`, `Stage7ActiveGradMin`,
`Stage7ActiveTangentMin`, and `Stage7RelaxationTau`.

New diagnostics include `WallStage7Mode`, `WallStage7ActiveWeight`,
`WallStage7DeltaQRaw`, `WallStage7DeltaQLimited`, `WallStage7Denom`,
`WallStage7LimiterReason`, `WallStage7GradMag`, `WallStage7ActualCos`,
`WallStage7TargetCos`, `WallStage7WriteCandidate`, and
`WallStage7WriteMinusProfile`.

The candidate does not silently hide clipping. Denominator floor, delta-q
limit, q limit, active-zone selection, and write-minus-profile are exported for
audit.

## Gate 2 Wall011 Mode Comparison

Run root: `/mnt/8A0E24070E23EAC1/runs/tclb_flat_wall_cap_stage7b_wall011_modes_20260612`.

| Case | Mode | Status | Final step | Apparent angle deg | Phase drift | Rho drift | Max Mach | Nonfinite | First bad |
|---|---:|---|---:|---:|---:|---:|---:|---:|---|
| `cap_theta030_wall011_mode0` | 0 | runtime_sanity | 50000 | 28.9607 | -0.004899 | -0.004763 | 1.626e-05 | 0 | none |
| `cap_theta030_wall011_mode2` | 2 | failed_negative_evidence | 0 | 28.4845 | 0 | 0 | 0 | 0 | CSV NaN at 1000 |
| `cap_theta030_wall011_mode3` | 3 | runtime_sanity | 50000 | 27.3227 | -0.009314 | -0.009057 | 2.641e-05 | 0 | none |

Decision: Stage7b mode3 removes the immediate `wall011` dynamic NaN seen in
Stage7 mode2. This is runtime evidence only; it is not enough to promote the
candidate to sphere signed-write because the wider low-angle scan below does
not pass.

## Gate 1 Low-Angle Flat Scan

Run root: `/mnt/8A0E24070E23EAC1/runs/tclb_flat_wall_cap_stage7b_low_angle_20260612`.

All cases use `Stage7SignedMode=3`.

| Case | Wall angle deg | Status | Final step | Apparent angle deg | Phase drift | Max Mach | First bad |
|---|---:|---|---:|---:|---:|---:|---|
| `cap_theta030_wall005` | 5 | failed_negative_evidence | 0 | 27.5671 | 0 | 0 | CSV NaN at 1000 |
| `cap_theta030_wall008` | 8 | failed_negative_evidence | 0 | 27.9131 | 0 | 0 | CSV NaN at 1000 |
| `cap_theta030_wall011` | 11 | runtime_sanity | 50000 | 27.3227 | -0.009314 | 2.641e-05 | none |
| `cap_theta030_wall015` | 15 | runtime_sanity | 50000 | 28.2223 | -0.006105 | 1.911e-05 | none |
| `cap_theta030_wall020` | 20 | runtime_sanity | 50000 | 29.5093 | -0.003385 | 1.384e-05 | none |
| `cap_theta030_wall025` | 25 | runtime_sanity | 50000 | 30.0845 | -0.001576 | 1.208e-05 | none |
| `cap_theta030_wall030` | 30 | runtime_sanity | 50000 | 30.5803 | -0.000220 | 1.565e-05 | none |

The scan gives a partial-pass result: the current sphere-control input
`radAngle=11d` is stable to 50k, and `11..30d` are stable in this flat setup.
However, `5d` and `8d` still fail by the first failcheck window. Therefore
Stage7b is not a general low-angle signed-wall fix.

## Gate Decision

- Do not run z48 sphere signed-write Gate 5.
- Do not promote Stage7b beyond `runtime_sanity / exploratory_not_validation`.
- z48 sphere may only be run in `Stage7SignedMode=1` shadow mode if the next
  objective is to compare active-zone candidate diagnostics without writing it.
- The appropriate next implementation route is Stage8
  `stage8_boundary_fluid_gradient_wetting`: correct the fluid-boundary
  `gradPhiVal` normal component directly instead of continuing to tune strong
  solid ghost writes.

## Uploaded Evidence

- `artifacts/stage7b_low_angle_provenance_20260612`
- `artifacts/flat_wall_cap_stage7b_wall011_modes_20260612`
- `artifacts/flat_wall_cap_stage7b_low_angle_20260612`
- `cases/diagnostics/flat_wall_cap_stage7b_wall011_modes_20260612`
- `cases/diagnostics/flat_wall_cap_stage7b_low_angle_20260612`
- `third_party/tclb_snapshots/stage7b_low_angle_signed_wall_stability_diag`

Raw `.vti/.pvti/.pri` fields remain on HM570 and are intentionally not included
in the public repository.
