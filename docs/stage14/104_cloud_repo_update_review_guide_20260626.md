# Cloud Repository Update and Review Guide

Date: 2026-06-26

Branch:

```text
work/phasefield-c-reference-20260623
```

Status:

```text
exploratory_not_validation
failed_negative_evidence for the current high-density-ratio flat-wall onset probe
```

This document is the first review entry for other AI agents or engineers after the Stage14-B18/B19/B20 update. It summarizes what changed, what evidence exists, what is intentionally not uploaded, and what must not be claimed.

## Reviewer Starting Point

Use this file as the cloud repository entry point. It is designed to make the
repository auditable without relying on chat history.

Review context:

```text
repository = 2317942351/LBMD3Q27
branch = work/phasefield-c-reference-20260623
local workspace used for this update = C:\Users\yuanz\Desktop\lbm-new\repo
remote execution host = yuan@192.168.1.16
remote run disk = /mnt/usb1t/RUNS/runs
P100 selector = CUDA_VISIBLE_DEVICES=1
```

Current scientific question:

```text
Why does the density-ratio-200 flat-wall wall_60to30_10 short probe leave the
physical phase range before any static wetting/contact-angle validation can be
trusted?
```

Current narrowed path:

```text
TCLB streamed h populations
  -> PhaseF / tmp1 / Fphi / heq
  -> hpost / PhaseFromH
  -> low-density velocity and stress feedback
  -> pressure and F_mu amplification after onset
```

This packet is therefore about phase-population and momentum-closure
diagnostics. It is not a curved-wall wetting packet.

## Claim Boundary

Allowed claims:

```text
The new diagnostics compile and run on the P100 lane.
The wall_60to30 density-ratio-200 short probe still fails numerically.
The failure path has been narrowed from curved wetting to phase/momentum population closure.
B20 evidence implicates heq/hpost population amplification before Fphi becomes the leading visible source.
```

Forbidden claims:

```text
contact-angle validation passed
static wetting is solved
curved-wall cylinder or sphere wetting is solved
dynamic impact is ready
bounded velocity shadow is a physical limiter
PressureClosureMode=1 is a validated pressure fix
B18/B19/B20 are solver fixes
```

## Files Added Or Updated

Solver snapshot files:

```text
third_party/tclb_snapshots/stage17B_diffuse_solid_shadow/models/multiphase/d3q27_pf_velocity/Dynamics.R
third_party/tclb_snapshots/stage17B_diffuse_solid_shadow/models/multiphase/d3q27_pf_velocity/Dynamics.c.Rt
```

Stage14 scripts:

```text
scripts/stage14/stage14_s2_replay_smoke.py
scripts/stage14/stage14_b17_onset_mask_argmax.py
scripts/stage14/build_stage14_b18_shadow_closure_remote.sh
scripts/stage14/compile_stage14_b18_after_source_remote.sh
scripts/stage14/run_stage14_b18_shadow_closure_remote.sh
```

Reports:

```text
docs/stage14/101_stage14_B18_shadow_closure_20260625.md
docs/stage14/102_stage14_B19_phase_advection_mode_split_20260626.md
docs/stage14/103_stage14_B20_hupdate_shadow_20260626.md
docs/stage14/104_cloud_repo_update_review_guide_20260626.md
```

Artifacts:

```text
artifacts/stage14_B18_shadow_closure_20260625/
artifacts/stage14_B18_shadow_closure_20260625_rerun/
artifacts/stage14_B19_phaseadv_mode0_20260626/
artifacts/stage14_B20_hupdate_shadow_mode0_20260626/
artifacts/stage14_B20_hupdate_shadow_mode1_20260626/
artifacts/stage14_B20_mode0_mode1_compare_20260626.csv
```

The intended cloud upload set is source, scripts, reports, logs, case XML, and
curated JSON/CSV summaries. No raw `*.vti` or `*.pvti` files should be
committed. The remote VTI/PVTI outputs for B20 mode0 and mode1 were deleted
after lightweight evidence was downloaded.

Large detailed trace files named `b18_argmax_trace.json` are useful for local
deep audit but should not be treated as the first-read cloud packet. Prefer:

```text
b18_key_summary.json
b18_first_onset.json
b18_field_presence.json
b18_mask_stats.csv
b20_step12_14_key_metrics.csv
artifacts/stage14_B20_mode0_mode1_compare_20260626.csv
```

If a reviewer needs full argmax traces, regenerate them from retained remote
raw outputs or request the local/offline trace explicitly. Do not infer a
missing trace as missing evidence; the omission is a repository-size and review
hygiene choice.

## What Changed In The Solver

The new solver changes are output-only diagnostics.

New setting:

```text
Stage14B20HUpdateDiagnosticsMode = 0 by default
```

New B20 diagnostic families:

```text
B20Fphi*Sum / B20Fphi*MaxAbs
B20Heq*Sum / B20Heq*MaxAbs
B20HPost*Sum / B20HPost*MaxAbs
B20PhaseFromH*Shadow
B20HPost*OutOfBoundsFlag
```

The compared h-update candidates are:

```text
active solver path
raw post-force velocity
pre-force velocity
bounded velocity shadow
```

These fields are registered with `AddField(..., group="runtime_diagnostics")`, not `AddDensity`. They do not participate in TCLB streaming and must not be interpreted as a new physics path.

The real solver update remains:

```text
C(h, h - omega * (h - heq + 0.5*Fphi) + Fphi)
```

No B20 candidate writes to:

```text
h
PhaseF
g
F_total
U/V/W
WallGhost
```

## Build Notes

Remote compile lane:

```text
/home/yuan/src/TCLB_lbm2026_compile_lane
```

Successful binary:

```text
/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
sha256 = 9d63fa5aa0618c1b5389d1126662f0da6aa7ea01185d72b377f7a5b80693c023
```

Critical build rule:

```text
Changing AddField/AddQuantity/AddSetting requires full source generation:
make d3q27_pf_velocity_q27_geometric/source
```

An RT-only after-source compile failed because `cuda.cu` did not yet have the new B20 field macros. The full generation script succeeded:

```text
scripts/stage14/build_stage14_b18_shadow_closure_remote.sh
```

## Run Evidence

Both B20 runs used:

```text
case = wall_60to30_10
GPU = Tesla P100, CUDA_VISIBLE_DEVICES=1
Density_h = 1.0
Density_l = 0.005
iterations = 20
vtk_period = 1
VTK_FIELD_SET = minimal
MomentumClosureDiagnosticsMode = 1
Stage14B18ClosureDiagnosticsMode = 1
Stage14B20HUpdateDiagnosticsMode = 1
PressureClosureMode = 1
ForceFixedPointMode = 2
```

Mode0:

```text
run root = /mnt/usb1t/RUNS/runs/stage14_B20_hupdate_shadow_mode0_20260626
local artifacts = artifacts/stage14_B20_hupdate_shadow_mode0_20260626/
PhaseAdvectionVelocityMode = 0
RUN_RC = 0
DRIVER_RC = 3
ANALYZER_RC = 0
```

Mode1:

```text
run root = /mnt/usb1t/RUNS/runs/stage14_B20_hupdate_shadow_mode1_20260626
local artifacts = artifacts/stage14_B20_hupdate_shadow_mode1_20260626/
PhaseAdvectionVelocityMode = 1
RUN_RC = 0
DRIVER_RC = 3
ANALYZER_RC = 0
```

`DRIVER_RC=3` is the Python summary guard after numerical overflow/nonfinite diagnostics appear. It is not a TCLB process crash.

## Main Findings

Mode0 analyzer:

```text
primary_branch = phase_update_or_h_advection_first
b18_primary_branch = stress_amplification_shadow
b20_primary_branch = heq_candidate_large_before_hpost
```

Mode1 analyzer:

```text
primary_branch = stress_timelevel_or_fixed_point_feedback
b18_primary_branch = stress_amplification_shadow
b20_primary_branch = heq_candidate_large_before_hpost
```

Important comparison:

```text
mode 0, step 13:
  ReplayPhaseFromH low_rho = 554.6179695990
  B20HeqActiveMaxAbs low_rho = 378.8806453468
  B20HPostActiveMaxAbs low_rho = 270.6079449121
  B20FphiActiveMaxAbs low_rho = 0.0121775683

mode 1, step 13:
  ReplayPhaseFromH low_rho = 2.7912195566
  B20HeqActiveMaxAbs low_rho = 3.1271718089
  B20HPostActiveMaxAbs low_rho = 2.2337060633
  B20FphiActiveMaxAbs low_rho = 0.0018927390
```

Interpretation:

```text
Fphi is not the earliest visible large term.
heq/hpost grow first.
Mode1 reduces the amplitude but does not close the failure.
The next target is h-population history/cancellation, not contact-angle tuning.
```

## Recommended Review Order

1. Read this file and `docs/index_current_stage.md`.
2. Read `docs/stage14/103_stage14_B20_hupdate_shadow_20260626.md`.
3. Read `docs/stage14/102_stage14_B19_phase_advection_mode_split_20260626.md`.
4. Read `docs/stage14/101_stage14_B18_shadow_closure_20260625.md`.
5. Inspect `Dynamics.R` and confirm all B18/B20 outputs are `AddField`, not `AddDensity`.
6. Inspect `Dynamics.c.Rt` around the MRT phase update and confirm B18/B20 candidates are shadow-only.
7. Inspect `scripts/stage14/stage14_s2_replay_smoke.py` for the XML settings and minimal VTK field list.
8. Inspect `scripts/stage14/stage14_b17_onset_mask_argmax.py` for threshold logic and B20 branch classification.
9. Inspect:

```text
artifacts/stage14_B20_mode0_mode1_compare_20260626.csv
artifacts/stage14_B20_hupdate_shadow_mode0_20260626/b20_step12_14_key_metrics.csv
artifacts/stage14_B20_hupdate_shadow_mode1_20260626/b20_step12_14_key_metrics.csv
```

10. Treat `b18_argmax_trace.json` as detailed evidence, not a first-read file.

## Review Checklist For Other Agents

Before drawing any conclusion, verify:

```text
1. Stage14B18ClosureDiagnosticsMode and Stage14B20HUpdateDiagnosticsMode default to 0.
2. B18/B20 diagnostics are AddField outputs under runtime_diagnostics.
3. No B18/B20 candidate writes to h, g, PhaseF, WallGhost, F_total, or U/V/W.
4. The compared mode0/mode1 runs used the same binary hash where documented.
5. DRIVER_RC=3 is the Python summary guard after detected numerical failure,
   not a CUDA/TCLB binary crash.
6. The case is wall_60to30_10, density ratio 200, 20 steps, P100.
7. The evidence is a failure-localization packet, not a validation packet.
```

Possible reviewer objections to test:

```text
1. Are B20 shadows using the same local h_i values as the active h update?
2. Are heq/hpost maxima caused by population cancellation rather than local
   source magnitude?
3. Does PhaseAdvectionVelocityMode alter the time level of velocity consumed by
   h-equilibrium consistently with TCLB streaming semantics?
4. Are low-rho masks physically meaningful near the interface, or are they
   exposing an already invalid density/phase closure?
```

The next B21 work is meant to answer these objections.

## Next Work: B21

The next branch should be B21:

```text
h-population conservation and cancellation audit
```

Recommended B21 shadow fields:

```text
HPreSumAbs
HPostSumAbs
HPreCancellationRatio = sum(abs(h_i)) / max(abs(sum(h_i)), eps)
HPostCancellationRatio
HPreMin / HPreMax
HPostMin / HPostMax
HeqSumAbs
FphiSumAbs
HeqVelocityMachShadow
```

B21 must remain output-only until the producer-consumer path is proven. Do not introduce hard clipping, hidden damping, force cancellation, or pressure shifting as an unreported fix.

Suggested B21 first test:

```text
same wall_60to30_10 case
same density ratio 200
same 20-step P100 short run
same minimal VTK field set
Stage14B21HPopulationAuditMode = 1
```

B21 success means a reviewer can tell whether the `h` population blow-up comes
from large absolute populations with small signed sums, from the equilibrium
projection itself, from the force/source increment, or from streaming history.
It still would not mean static contact angles are solved.
