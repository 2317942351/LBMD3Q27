# Stage7 Signed Wall Ghost Diagnostic Report

Date: 2026-06-12

## Status

`runtime_sanity / exploratory_not_validation`. This is a diagnostic packet, not a PRE 2025 reproduction, not a validation result, and not a production fix.

## Source Lanes

- `clean_upstream`: `/home/yuan/src/TCLB_clean_upstream_ded67cd_20260612`, upstream commit `ded67cd768cf7e727bd078af139e3ec7895076e5`.
- `clean_upstream` configure/source/build return codes were `0/0/0`; binary SHA: `5ce72dbafb32cc830584a33a0300a7636070e2cdeb2b31c1fa5bb9d01c467e1a  CLB/d3q27_pf_velocity_q27_geometric/main`.
- `experimental_stage7_signed_wall_ghost`: `/home/yuan/src/TCLB_clean_wall_signed_ghost_stage7diag_20260611`, based on the v6 normal-path diagnostic lane.
- Stage7 source/build return codes were `0/0`; binary SHA: `5f03a84189e0136a73aa9a8f33d079c148079f8eb5335f33ce485964fef48a94  CLB/d3q27_pf_velocity_q27_geometric/main`.

## Stage7 Code Contract

The Stage7 lane adds diagnostic fields and a guarded signed-write switch. The default `UseStage7SignedWallGhost=0` preserves v6 profile write behavior; Gate 2 explicitly sets `UseStage7SignedWallGhost=1`.

New/important fields include `WallPhaseRawPred`, `WallPhaseSignedPred`, `WallContactResidual`, `WallSignedNormalGrad`, `WallTangentGradMag`, `WallSignedDeltaQ`, `WallSignedQClipped`, `BoundaryMask`, and retained v6 fields such as `WallH`, `WallGeomNormal`, `WallGrad1`, `WallGrad2`, `WallGradTangentVec`, `WallActualMinusProfile`, and `WallActualMinusRaw`.

The signed candidate uses a logit-space bounded reconstruction. It only limits q numerically; it does not silently clamp the resulting wall phase as a physical fix. `WallSignedQClipped` is exported for audit.

## Gate 1 Offline Replay

Replay used saved v6 and flat-wall fields without running TCLB. All reported replay paths were finite and did not trigger q clipping. The theta090 flat case is a path-classification caveat because neutral wall angle uses path 2 and has normal-path count 0.

- `replay_v6_M0p2_steps0_50k`: pass_gate1=`True`, normal_path_count=`10256`, nonfinite_total_normal=`0`, q_clip_count_normal=`0`, signed_pred=`0.0116256..1`, raw_pred_gt_1=`1920`, contact_residual_mean=`0.106136`.
- `replay_v6_M0p1_steps0_50k`: pass_gate1=`True`, normal_path_count=`10256`, nonfinite_total_normal=`0`, q_clip_count_normal=`0`, signed_pred=`0.00153215..0.999999`, raw_pred_gt_1=`1628`, contact_residual_mean=`0.11031`.
- `replay_flat_cap_theta030_wall030`: pass_gate1=`True`, normal_path_count=`16384`, nonfinite_total_normal=`0`, q_clip_count_normal=`0`, signed_pred=`2.96499e-06..0.999767`, raw_pred_gt_1=`0`, contact_residual_mean=`nan`.
- `replay_flat_cap_theta090_wall090`: pass_gate1=`False`, normal_path_count=`0`, nonfinite_total_normal=`0`, q_clip_count_normal=`0`, signed_pred=`nan..nan`, raw_pred_gt_1=`0`, contact_residual_mean=`nan`.
- `replay_flat_cap_theta150_wall150`: pass_gate1=`True`, normal_path_count=`16384`, nonfinite_total_normal=`0`, q_clip_count_normal=`0`, signed_pred=`1.60919e-08..0.966421`, raw_pred_gt_1=`0`, contact_residual_mean=`nan`.
- `replay_flat_cap_theta030_wall011`: pass_gate1=`True`, normal_path_count=`16384`, nonfinite_total_normal=`0`, q_clip_count_normal=`0`, signed_pred=`0.00309797..0.999774`, raw_pred_gt_1=`0`, contact_residual_mean=`nan`.

## Gate 2 Flat Wall Signed-Write Results

Run root: `/mnt/8A0E24070E23EAC1/runs/tclb_flat_wall_cap_stage7_signedwrite_gate_20260612`. Raw VTI/PVTI/PRI remain remote-only. Curated local artifact: `artifacts/flat_wall_cap_stage7_signedwrite_gate_20260612`.

| Case | Status | Final step | Apparent angle deg | Angle error deg | Phase drift | Rho drift | Max Mach | Nonfinite | Signed wall max | Residual mean | q clip sum |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cap_theta030_wall030 | runtime_sanity | 50000 | 30.6593 | 0.659333 | -0.000277998 | -0.00027032 | 1.31907e-05 | 0 | 0.999772 | -0.00594876 | 0 |
| cap_theta090_wall090 | runtime_sanity | 50000 | 89.6762 | -0.323785 | 0.000126439 | 0.000123177 | 4.99324e-06 | 0 | 0 | 0 | 0 |
| cap_theta150_wall150 | runtime_sanity | 50000 | 151.296 | 1.29619 | 0.000605806 | 0.000590843 | 2.61336e-05 | 0 | 0.958181 | -0.0208466 | 0 |
| cap_theta030_wall011 | failed_negative_evidence | 0 | 28.4845 | -1.51551 | 0 | 0 | 0 | 0 | 0.999719 | 0.0286638 | 0 |

The three direct flat-wall gates `wall030`, `wall090`, and `wall150` pass the runtime checks: nonfinite=0, max Mach below `3e-5`, monotonic apparent angles, and no q clipping. The apparent-angle errors at 50k are about `+0.66 deg`, `-0.32 deg`, and `+1.30 deg`.

## Negative Evidence: theta030/wall011

`cap_theta030_wall011` is `failed_negative_evidence` for Stage7 signed-write. The solver wrapper returned 0 but the run log reported `Checking PhaseField discovered NaN` and `Stopping due to Nan value`; the TCLB CSV first contains `-nan` at iteration 1000. Only the initial VTI exists.

The initial step-0 VTI is finite: apparent angle `28.4845` deg, `WallPhaseSignedPred` max `0.999719`, `WallSignedQClipped` sum `0`, and nonfinite_total `0`. Therefore the failure is not an immediate NaN in the initial write; it is a low-input-angle signed-write dynamic instability by the first failcheck window.

## Gate Decision

Gate 3 z48 sphere theta030 is intentionally blocked in this run. The planned sphere input uses `sphere radAngle=11d`, and the matching flat-wall control `theta030/wall011` failed under signed-write. Running the z48 sphere with the same signed-write candidate would mix a known low-angle instability into the curved-wall root-cause question.

## Current Interpretation

- Stage7 signed reconstruction can reproduce stable flat-wall `30/90/150 deg` contact response under direct wall-angle inputs.
- Stage7 signed-write is not yet safe for the `radAngle=11d` sphere-mapping control; this blocks any claim that the candidate fixes the z48 sphere `107-110 deg` failure.
- The earlier v6 evidence still stands: actual wall `PhaseF` equaled the bounded profile write, yet z48 sphere theta030 remained near `107-110 deg`. Stage7 adds a promising but not production-safe signed normal-path candidate.
- Next code iteration should diagnose why low `radAngle=11d` signed-write destabilizes dynamically despite finite bounded step-0 fields. Likely audit targets are residual sign convention, normal orientation on path 5 lower-wall cells, q-delta scaling, and consistency between normal path and special/correction branches.

## Uploaded Evidence

- `artifacts/stage7_signed_wall_ghost_provenance_20260612`: Stage7 source/build provenance and offline replay summaries.
- `artifacts/clean_upstream_ded67cd_provenance_20260612`: clean upstream configure/source/build provenance.
- `artifacts/flat_wall_cap_stage7_signedwrite_gate_20260612`: Gate 2 curated XML/log/CSV/JSON/PNG evidence.
- `cases/diagnostics/flat_wall_cap_stage7_signedwrite_gate_20260612`: generated Gate 2 XMLs and manifest.
- `third_party/tclb_snapshots/stage7_signed_wall_ghost_diag`: source snapshot for the modified TCLB model.
- `patches/wall_signed_ghost_stage7diag_20260612` and `third_party/tclb_snapshots/patches/stage7_signed_wall_ghost_diag_20260612.diff`: patch evidence against upstream.
