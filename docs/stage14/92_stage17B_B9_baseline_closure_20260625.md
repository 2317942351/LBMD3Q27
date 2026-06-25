# Stage17B-B9 Baseline Closure Dense Replay

Date: 2026-06-25

Status:

```text
lite gate: PASS_STAGE17B_B9_BASELINE_TRIAGE
momentum A probe: PASS_STAGE17B_B9_BASELINE_TRIAGE
claim limit: root-cause diagnostic only; not contact-angle validation
```

This stage does not validate static contact angle and does not justify dynamic impact cases.

## Purpose

B8 proved that the neutral 90-degree cylinder drift is already present in the pure legacy write-off baseline and is unchanged by Stage17B shadow or controlled curved WallGhost write paths. B9 therefore moves the root-cause question to the baseline closure:

```text
cylinder-cap initialization equilibrium
PhaseF -> Fphi/tmp1 -> h update -> PhaseFromH boundedness
near-wall gradPhi/mu consumption
pressure/stress/F_mu/force feedback
diagnostic metric sensitivity
```

The immediate B9 question is:

```text
At which producer-consumer boundary does the 90-degree baseline cylinder drift first appear?
```

## Execution Constraint

Standalone `Solve Iterations="0"` is not used in B9. In the current headless TCLB server lane, a zero-step case does not exit reliably and produces no useful VTI. Step 1 is therefore the earliest executable frame.

## B9-Lite Run

```text
server = yuan@192.168.1.16
GPU request = CUDA_VISIBLE_DEVICES=1
run root = /mnt/usb1t/RUNS/runs/stage17B_B9_lite_20260625
case source = /home/yuan/stage17B_B9_lite_cases
binary = /home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
binary sha256 = 8e88228d38c4e10e7d84bf32738b8490bd8ab9a263e672ddcf6a033eed80a3b5
done.status = DONE ... rc=0
```

B9-lite uses two zero-write groups:

| group | path | purpose |
|---|---|---|
| A | legacy zero-write | pure baseline with Stage17B disabled |
| B | shadow zero-write | Stage17B shadow fields enabled, no write |

Steps:

```text
1, 2, 5, 10, 20, 50, 100, 200, 400, 600, 1000, 2000
```

## Lite Result

All 24 B9-lite cases completed with `RC=0` on P100. Each case writes an initial and final VTI, and a single VTI is about 668 MB for the current field tier. The remote run directory is about 32 GB, so only lightweight evidence was downloaded:

```text
stage17B_B9_baseline_analysis.json
stage17B_B9_baseline_frames.csv
stage17B_B9_baseline_timeseries.png
run_manifest.txt
binary_sha256.txt
done.status
run.status / run.log / run.stderr
case_metadata.json
```

Raw VTI/PVTI files are not intended for git.

Downloaded local evidence:

```text
artifacts/stage17B_B9_baseline_20260625/runtime_lite/stage17B_B9_baseline_analysis.json
artifacts/stage17B_B9_baseline_20260625/runtime_lite/stage17B_B9_baseline_frames.csv
artifacts/stage17B_B9_baseline_20260625/runtime_lite/stage17B_B9_baseline_timeseries.png
```

The analyzer status is:

```text
status = PASS_STAGE17B_B9_BASELINE_TRIAGE
primary_suspect = phase_boundedness_or_initialization_release
first_liquid_volume_delta_step = 2
first_phase_out_of_bounds_step = 5
first_contact_ymin_motion_step = 10
first_contact_half_width_drift_step = 50
```

The most important result is that groups A and B are numerically identical in the reported morphology timeline:

| step | A half-width delta | B half-width delta | A/B comment |
|---:|---:|---:|---|
| 1 | 0.000000 | 0.000000 | identical |
| 2 | 0.000000 | 0.000000 | identical |
| 5 | 0.000000 | 0.000000 | identical; phase out-of-bounds flag already appears |
| 10 | 0.000000 | 0.000000 | identical; contact `y_min` has moved by 1 lu |
| 20 | 0.000000 | 0.000000 | identical |
| 50 | -0.732813 | -0.732813 | first half-width drift |
| 400 | -1.803049 | -1.803049 | matches B8 600-scale drift onset |
| 600 | -1.803049 | -1.803049 | identical |
| 1000 | -2.574064 | -2.574064 | identical |
| 2000 | -3.416588 | -3.416588 | identical B8-scale drift |

This confirms the B8 conclusion with a denser time axis:

```text
The neutral cylinder drift is not caused by Stage17B shadow-only diagnostics.
It is already present in the pure legacy zero-write baseline.
```

## Phase Chain Evidence

B9-lite does not show a catastrophic blow-up. Instead, it shows a small but very early phase boundedness/release effect that precedes the visible contact-width metric drift:

| step | phase min/max | phase OOB flag | contact y-min delta | half-width delta |
|---:|---:|---:|---:|---:|
| 1 | 0 / 1 | 0 | 0 | 0 |
| 2 | -5.2376e-4 / 1.0000002 | 0 | 0 | 0 |
| 5 | -4.2991e-4 / 1.0000148 | 1 | 0 | 0 |
| 10 | -4.5161e-4 / 1.0006509 | 1 | 1 | 0 |
| 50 | -8.2744e-5 / 1.0001126 | 1 | 1 | -0.732813 |
| 2000 | -1.1421e-4 / 1.0001238 | 1 | 2 | -3.416588 |

Near-wall phase-update diagnostics remain finite and smooth in scale:

```text
ReplayFphiMaxAbs_near_max_abs ~= 0.024
ReplayTmp1_near_max_abs ~= 0.33333
ReplayHPostMaxAbs_near_max_abs ~= 0.29632
ReplayMu_near_max_abs decays from about 1.13e-4 to about 2.1e-5
ReplayLapPhi_near_max_abs decays from about 0.50 to about 0.167
```

Interpretation:

```text
The current evidence points less to an explosive -999/stencil pollution failure
and more to a non-equilibrium initial cap / phase boundedness / discrete
geometry-release mechanism near the cylinder wall.
```

## Important Limitation

The B9-lite tier intentionally omits momentum fields to keep the output volume manageable. Therefore it cannot clear:

```text
pressure closure
F_mu stress time level
force-over-rho feedback
MRT force insertion
```

The original analyzer incorrectly treated missing momentum fields as zero. That classification bug was fixed so absent fields are now reported as unavailable, not as evidence of zero force.

## Momentum Follow-Up Result

A reduced B9-momentum A-group probe was run to fill this gap without rerunning the full 24-case matrix:

```text
run root = /mnt/usb1t/RUNS/runs/stage17B_B9_momentum_A_20260625
case source = /home/yuan/stage17B_B9_momentum_A_cases
steps = 1, 2, 5, 10, 20, 50, 2000
groups = A only, pure legacy zero-write
done.status = DONE ... rc=0
status = PASS_STAGE17B_B9_BASELINE_TRIAGE
```

Downloaded local evidence:

```text
artifacts/stage17B_B9_baseline_20260625/runtime_momentum_A/stage17B_B9_baseline_analysis.json
artifacts/stage17B_B9_baseline_20260625/runtime_momentum_A/stage17B_B9_baseline_frames.csv
artifacts/stage17B_B9_baseline_20260625/runtime_momentum_A/stage17B_B9_baseline_timeseries.png
```

Momentum candidate scales:

| step | half-width delta | y-min delta | max near-wall `F_pressure` | max near-wall `F_mu` | max near-wall `F_total` | max near-wall `F/rho` |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.000000 | 0 | 0 | 6.89e-7 | 2.74e-5 | 5.49e-3 |
| 2 | 0.000000 | 0 | 3.74e-6 | 1.57e-6 | 1.85e-5 | 1.69e-4 |
| 5 | 0.000000 | 0 | 2.21e-4 | 1.18e-4 | 3.18e-4 | 1.85e-2 |
| 10 | 0.000000 | 1 | 5.73e-6 | 3.68e-6 | 8.85e-6 | 5.37e-4 |
| 20 | 0.000000 | 1 | 3.15e-6 | 1.19e-6 | 8.11e-6 | 3.36e-5 |
| 50 | -0.732813 | 1 | 3.18e-6 | 1.15e-6 | 6.82e-6 | 2.51e-5 |
| 2000 | -3.416588 | 2 | 2.57e-6 | 8.14e-7 | 4.90e-6 | 2.61e-5 |

Interpretation:

```text
The momentum probe shows a finite early force transient, especially at step 5,
but not a sustained pressure/F_mu/force-over-rho explosion. The force terms
decay by step 10-20, while the morphology drift persists and accumulates.
```

This does not prove the momentum model is fully correct. It does lower the priority of pressure/F_mu as the dominant B9 neutral-drift source compared with the initialization/phase-boundedness branch.

## Current Verdict

B9 narrows the root cause to:

```text
primary: phase_boundedness_or_initialization_release
secondary: early force transient responding to the same release
not supported as primary here: sustained pressure/F_mu/force-over-rho blow-up
```

No B3 controlled-write or dynamic-impact work is allowed from this stage alone. The next technical branch should be:

```text
1. audit CylinderCapInit geometry and the 90-degree cylinder cap discrete equilibrium;
2. build an offline reconstructed initial cap diagnostic against the actual cylinder surface;
3. add a bounded-phase shadow diagnostic around h update, not a hard clamp as validation;
4. test alternative neutral-cap initialization or short relaxation-precondition case;
5. only after neutral 90-degree drift is controlled, return to 60/120 controlled write response.
```

## External Review

A Teacher MCP runtime-diagnostic review was run on the B9 evidence summary. It returned `PASS` with confidence `0.92`. The review agreed that:

```text
initialization release is the primary supported suspect;
sustained pressure/F_mu/force-over-rho blow-up is not supported as primary here;
contact-angle validation and dynamic impact remain premature.
```

The most evidence-efficient next probe recommended by the review is:

```text
compute the discrete chemical-potential field from the initial cylinder cap,
then report mu deviation from the mean in the interfacial/near-wall region.
```

This can be done offline first, without changing solver physics.

## Local Artifact Scope

The committed artifact scope should include scripts, case XML/metadata, reports, and lightweight runtime evidence. It should not include VTI/PVTI files.

Local lightweight runtime evidence includes `novti_logs/` directories under:

```text
artifacts/stage17B_B9_baseline_20260625/runtime_lite/
artifacts/stage17B_B9_baseline_20260625/runtime_momentum_A/
```
