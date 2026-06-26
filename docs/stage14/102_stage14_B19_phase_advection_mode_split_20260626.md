# Stage14-B19 Phase-Advection Mode Split

Date: 2026-06-26

Status: diagnostic-only. This is not contact-angle validation, not a solver fix, and not a dynamic-impact preflight.

## Purpose

B18-B made the `B18*` shadow diagnostics readable and showed that the low-density force/stress/velocity chain grows before the catastrophic `h`/`PhaseFromH` failure. B19 asks a narrower question:

```text
Does the velocity used by the phase-field h-equilibrium change the earliest failure classification?
```

This matters because TCLB `AddDensity` populations stream, while `PhaseF`, `Replay*`, and `B18*` fields are non-streaming diagnostics. A C-style "current array" interpretation is not sufficient here; the actual producer-consumer order in `CollisionMRT` determines what velocity reaches the phase update.

## Compared Runs

Both runs used the same compiled TCLB binary:

```text
binary_sha256 = 01b18e2e84bd82078c079bf7446acda3cfc72a4d37b83dd7477c183c148ca9b1
GPU = P100, CUDA_VISIBLE_DEVICES=1
case = wall_60to30_10
Density_h = 1.0
Density_l = 0.005
iterations = 20
vtk_period = 1
PressureClosureMode = 1
ForceFixedPointMode = 2
MomentumForceMode = 0
MomentumClosureDiagnosticsMode = 1
Stage14B18ClosureDiagnosticsMode = 1
```

Mode-1 baseline:

```text
run root = /mnt/usb1t/RUNS/runs/stage14_B18_shadow_closure_20260625_rerun
local artifacts = artifacts/stage14_B18_shadow_closure_20260625_rerun/
PhaseAdvectionVelocityMode = 1
DRIVER_RC = 3
ANALYZER_RC = 0
```

Mode-0 split:

```text
run root = /mnt/usb1t/RUNS/runs/stage14_B19_phaseadv_mode0_20260626
local artifacts = artifacts/stage14_B19_phaseadv_mode0_20260626/
PhaseAdvectionVelocityMode = 0
DRIVER_RC = 3
ANALYZER_RC = 0
```

`DRIVER_RC=3` is the Python summary guard reporting post-failure overflow/nonfinite diagnostics. In both runs, the TCLB solver itself wrote `RUN_RC=0` in `run.log`. The analyzer output is usable.

After download, large VTI/PVTI outputs were removed from the remote run root. `/mnt/usb1t` recovered to about 77G free.

## Key Result

Analyzer branch classification changed:

```text
Mode 1:
primary_branch = undetermined
b18_primary_branch = stress_amplification_shadow

Mode 0:
primary_branch = phase_update_or_h_advection_first
b18_primary_branch = stress_amplification_shadow
```

The common `b18_primary_branch = stress_amplification_shadow` must be treated carefully because `B18StressPostOverPre` can be enormous at step 1 when the pre-force stress denominator is near zero. The more robust result is the different legacy first-failure ordering under `PhaseAdvectionVelocityMode`.

## Low-Density Trace

Mode 1, low-rho mask:

```text
step  ReplayPhaseFromH  ForceOverRhoNorm  StressPostForceNorm  B18HVelocityRawPostForceNorm  B18HVelocityLegacyNorm
8     2.006e-2          2.112e-1          7.092e-2             1.225e-1                       7.178e-2
9     2.008e-2          7.302e-1          1.082e-1             4.129e-1                       8.056e-2
10    2.002e-2          1.482e+0          8.242e-1             7.938e-1                       4.820e-1
11    2.007e-2          5.318e+0          9.300e+0             2.821e+0                       4.403e-1
12    1.990e-2          4.141e+1          4.663e+2             2.002e+1                       1.924e+0
```

Mode 0, low-rho mask:

```text
step  ReplayPhaseFromH  ForceOverRhoNorm  StressPostForceNorm  B18HVelocityRawPostForceNorm  B18HVelocityLegacyNorm
8     2.006e-2          2.112e-1          7.092e-2             1.225e-1                       1.225e-1
9     2.008e-2          7.302e-1          1.082e-1             4.129e-1                       4.129e-1
10    2.002e-2          1.487e+0          8.290e-1             7.963e-1                       7.963e-1
11    2.009e-2          5.476e+0          9.827e+0             2.899e+0                       2.899e+0
12    6.460e-2          2.879e+1          2.158e+2             1.370e+1                       1.370e+1
13    5.546e+2          9.048e+2          2.338e+5             4.466e+2                       4.466e+2
```

Mode 0 first records:

```text
step 13: ReplayPhaseFromH low_rho = 554.6179695990377
step 14: ForceOverRhoNorm low_rho = 4527.415146843487
```

This is the clearest B19 result: with mode 0, the phase field leaves bounds before the configured force-over-rho threshold. With mode 1, the analyzer could not assign the legacy branch before the fields became unusable, although the low-density force/stress/velocity growth is already visible.

## Interpretation

The current failure is not yet a wetting-angle or curved-wall problem. B19 says the next code work should focus on:

```text
PhaseF -> tmp1/Fphi -> heq velocity -> h update -> PhaseFromH
```

and how the post-force momentum state feeds that chain.

Specific implications:

- `B18HVelocityRawPostForceNorm` reaches `O(10)` by step 12 and `O(10^2)` by step 13 in low-density cells.
- `B18HVelocityBoundedShadowNorm` stays capped at 0.2, but it is only a diagnostic candidate. It must not be treated as a validated physical limiter.
- Mode 0 makes the h-update failure more explicit. This does not prove mode 0 is wrong by itself; it proves that phase advection velocity selection is part of the root-cause path.
- Pressure and raw `F_mu` remain downstream amplifiers in this probe. They should not be the first physics path modified without a separate derivation.

## Code Note

`scripts/stage14/stage14_s2_replay_smoke.py` now supports:

```text
--vtk-field-set full|minimal
```

Default remains `full`, so existing B18/B19 reproduction behavior is unchanged. The new `minimal` set exists only to reduce B20 VTI size by retaining the phase/force/stress/B18 fields needed for the next split. It does not alter XML model parameters or solver physics.

## Next Step

B20 should not run a new contact-angle case. It should add or use diagnostics that directly split:

1. raw post-force velocity used by phase `heq`,
2. pre-force velocity shadow,
3. bounded-velocity shadow,
4. corresponding `Fphi` max/sum for each candidate,
5. corresponding `h_post` and `PhaseFromH` shadow, if feasible without writing solver state.

If full shadow `h_post` is too invasive, B20 should at minimum run the same 20-step case with `--vtk-field-set minimal` and compare mode 0/mode 1 at steps 10-14 to keep disk usage controlled.

Forbidden claims remain:

```text
contact angle validation passed
dynamic impact readiness
B18/B19 is a solver fix
bounded velocity is a validated physical model
```
