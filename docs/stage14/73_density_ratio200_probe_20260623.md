# Stage14-73: Density Ratio 200 Probe

Date: 2026-06-23

Status: `p100_probe_completed_not_converged`

## Claim Boundary

This probe answers one narrow question:

```text
Does lowering the density ratio from 1000 to 200 make the current TCLB
phase-field wall_60to30_10 case converge?
```

It does not validate contact angle, does not enter dynamic impact, and does not
promote `PressureClosureMode` or `ForceFixedPointMode` to a physical repair.

## Runtime Context

```text
Remote root:
  /mnt/usb1t/RUNS/runs/stage14_density_ratio200_probe_20260623

Long-probe root:
  /mnt/usb1t/RUNS/runs/stage14_density_ratio200_probe_20260623_long50

Local artifacts:
  artifacts/stage14_density_ratio200_probe_20260623/

Binary:
  /home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main

Binary SHA256:
  f8050df8da32292be3173bab40561a3dd562a7a98578e82dd58cf852368c2748

GPU:
  CUDA_VISIBLE_DEVICES=1, Tesla P100-PCIE-16GB

Case:
  wall_60to30_10

Density:
  Density_h = 1.0
  Density_l = 0.005
  density ratio = 200
```

## Short 8-Step Probe

Four branches were run for 8 steps:

```text
probe_R200_B0_legacy
probe_R200_C2_single_pass
probe_R200_B1_pressure_physical
probe_R200_B1C2_pressure_physical_single_pass
```

The 8-step result is not a convergence result. It only shows that density ratio
200 delays the immediate blow-up seen at density ratio 1000.

Selected step-8 maxima:

| probe | PhaseFromH max_abs | F_mu raw max_abs | Force/rho max_abs | Force iter residual max_abs |
| --- | ---: | ---: | ---: | ---: |
| `probe_R200_B0_legacy` | 1.000005 | 36.4336 | 7.323e3 | 130.115 |
| `probe_R200_C2_single_pass` | 1.000005 | 2.348e-2 | 13.653 | 0 |
| `probe_R200_B1_pressure_physical` | 1.000005 | 8.325e-4 | 1.584e-1 | 129.346 |
| `probe_R200_B1C2_pressure_physical_single_pass` | 1.000005 | 1.261e-3 | 2.112e-1 | 0 |

Interpretation:

```text
Density ratio 200 reduces the initial low-density force feedback.
Pressure-physical input and single-pass force/stress evaluation further delay
growth.

However, the legacy branch is already numerically unhealthy at step 8:
Force/rho is O(1e3) and fixed-point residual is O(1e2).
```

## 50-Step Best-Branch Probe

The most stable short-step branch was extended to 50 steps:

```text
probe_R200_B1C2_pressure_physical_single_pass_50
PressureClosureMode = 1
ForceFixedPointMode = 2
vtk_period = 5
```

This branch remains bounded to step 10, but fails by step 20.

Selected key-frame maxima:

| step | PhaseFromH max_abs | PhaseField nonfinite | F_mu raw max_abs | F_mu raw nonfinite | Force/rho max_abs | Fphi max_abs |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 1.000015 | 0 | 7.947e-3 | 0 | 1.482 | 2.441e-2 |
| 20 | 3.908e297 | 73000 | 6.001e299 | 190920 | 1.090e192 | 3.899e305 |
| 30 | 1.000075 | 181572 | 7.139e-4 | 514020 | 1.437e-1 | 2.441e-2 |
| 40 | 2.564e-7 | 273916 | 1.698e-1 | 795240 | 34.04 | 3.197e-8 |
| 50 | 2.379e90 | 362928 | 5.845e26 | 1061976 | 9.458e64 | 6.201e67 |

The apparent return to smaller finite maxima at later frames is not recovery.
Those frames contain large nonfinite counts, so remaining finite extrema are no
longer physically meaningful.

## Answer

The current code cannot be called convergent at density ratio 200.

The correct conclusion is:

```text
Density ratio 200 delays the instability from the 6-step catastrophic regime
seen at density ratio 1000, but even the most stable diagnostic branch fails
by step 20 in a 50-step probe.
```

Therefore, density-ratio reduction is a useful diagnostic lever, not a root
fix.

## Implication For Root Cause

This result shifts priority away from simple density-ratio tuning.

The next root-cause target remains:

```text
phase equation boundedness
F_phi / tmp1 anti-diffusive source behavior as C leaves [0,1]
F_mu stress reconstruction time level and algebra
fixed-point acceptance after stress/F_mu correction
```

The probe also keeps pressure scaling in the candidate list:

```text
PressureClosureMode=1 greatly improves the short-step branch, but it does not
survive to step 20. It should remain a diagnostic switch until the phase and
stress closures are audited.
```

## Next Diagnostic Gate

Do not run more contact-angle cases yet.

The next minimum gate should be a dense onset probe on the best branch:

```text
case:
  wall_60to30_10

params:
  Density_h = 1.0
  Density_l = 0.005
  PressureClosureMode = 1
  ForceFixedPointMode = 2

range:
  output every step from 10 to 20

fields:
  PhaseFromH
  PhaseField
  ReplayTmp1
  ReplayFphiMaxAbs
  ReplayMu
  ReplayGradPhi
  ReplayFmuRaw
  ReplayStressInput*
  ReplayForceOverRho
  ReplayPressureInput
```

The purpose is to identify whether the first failure is:

```text
phase-source boundedness loss
stress/F_mu reconstruction explosion
pressure input growth
or a TCLB time-level / streaming mismatch before those fields are consumed
```

## Teacher Review

Teacher runtime-diagnostic review returned `NEEDS_FIX` with high confidence.
It agreed that density ratio 200 cannot be considered converged because the
long probe diverges severely by step 20, despite promising 8-step behavior.

Teacher recommended dense every-step diagnostics between steps 10 and 20 to
pinpoint the onset and location of divergence.
