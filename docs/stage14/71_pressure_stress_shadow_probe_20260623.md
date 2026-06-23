# Stage14-71: Pressure / Stress Shadow Probe Result

Date: 2026-06-23

Status: `first_iteration_pressure_low_density_failure_fixed_point_amplifier`

## Claim Boundary

This is still a short-step diagnostic. It is not contact-angle validation, not
dynamic-impact readiness, and not a physical repair.

## Build And Runs

Binary:

```text
/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
sha256 = cf8034ade76d1593798f595874d63d13a4fdc46c5a2e92a18fd5d379f65fdf33
```

GPU:

```text
CUDA_VISIBLE_DEVICES=1
GPU 1 = Tesla P100-PCIE-16GB
```

Runs:

```text
/mnt/usb1t/RUNS/runs/stage14_momentum_closure_bc_shadow_smoke_20260623
  force_fixed_iterator = 2

/mnt/usb1t/RUNS/runs/stage14_momentum_closure_bc_shadow_iter1_20260623
  force_fixed_iterator = 1
```

Local artifacts:

```text
artifacts/stage14_momentum_closure_bc_shadow_smoke_20260623/
artifacts/stage14_momentum_closure_bc_shadow_iter1_20260623/
```

Both runs used:

```text
wall_60to30_10
iterations = 6
ReplayDiagnosticsMode = 1
MomentumClosureDiagnosticsMode = 1
MomentumClosureProbeMode = 1
PhaseAdvectionVelocityMode = 1
MomentumForceMode = 0
```

## New Shadow Fields

The added fields are output-only:

```text
ReplayFpressureNoThird    = -p * (rho_h-rho_l) * gradPhi
ReplayFpressurePhysical   = -(p*rho*cs2)/3 * (rho_h-rho_l) * gradPhi
ReplayStressIter1*        = stress tensor at fixed-point iteration 1
ReplayStressInput*        = final stress tensor used by final F_mu
ReplayFmuDelta            = final F_mu - first-iteration F_mu
```

## force_fixed_iterator = 1

Step-6 max-absolute values:

```text
ReplayPhaseFromH          6.087e3
ReplayPressureInput       2.645e4
ReplayFpressure           1.180e3
ReplayFpressurePhysical   3.941e-1
ReplayFmuRaw              6.948e2
ReplayFmuDelta            0
ReplayStressInputYY       1.728e4
ReplayStressIter1YY       1.728e4
ReplayForceOverRho        1.817e6
ReplayRhoForForce         1.000e0 max, 0 min
ForceIterCount            1
ForceIterResidual         0
```

Interpretation:

```text
The first force evaluation already reproduces the Stage14-68 failure:
PhaseFromH leaves [0,1], F/rho reaches 1.817e6, and U_half is nonphysical.
```

The pressure-physical shadow is small compared with the current pressure force:

```text
ReplayFpressure           1.180e3
ReplayFpressurePhysical   3.941e-1
```

That confirms pressure input/scale remains a major candidate, but it is not the
only candidate because `F_muRaw` is also large at `6.948e2`.

## force_fixed_iterator = 2

Step-6 max-absolute values:

```text
ReplayPhaseFromH             1.318e105
ReplayPressureInput          3.121e46
ReplayFpressure              2.598e45
ReplayFpressurePhysical      1.112e58
ReplayFmuRaw                 1.720e89
ReplayFmuDelta               1.720e89
ReplayStressInputYY          2.841e92
ReplayStressIter1YY          1.963e46
ReplayForceOverRho           1.944e86
ReplayRhoForForce            3.166e13
```

Top `ReplayFmuRaw` nodes at step 6 show the second fixed-point pass dominates:

```text
ijk [5,1,5]:
  PhaseFromH      -7.657e104
  FmuRaw_y         1.720e89
  FmuDelta_y       1.720e89
  StressInputYY    2.296e90
  StressIter1YY   -1.471e46

ijk [7,1,88] by ForceOverRho:
  FmuRaw_y        -2.366e87
  ForceOverRho_y  -1.944e86
  rho              1.217e1
  StressInputYY   -3.158e88
  StressIter1YY   -1.884e46
```

Interpretation:

```text
The second fixed-point iteration is not the initial root of the failure, but it
is a severe amplifier once the first iteration has already corrupted the field.
```

## Updated Root-Cause Ranking

1. First-pass pressure / low-density closure remains the immediate failure:

```text
p = m0[0] grows large enough that F_pressure is O(1e3)
F_mu is also O(1e3)
rho near gas/interface makes F_total/rho O(1e6)
PhaseFromH leaves [0,1] by step 6
```

2. Fixed-point iteration is a high-priority amplifier:

```text
force_fixed_iterator=2 turns an already-bad step into stress/F_mu fields of
order 1e89-1e92 by step 6.
```

3. Simple MRT double injection is demoted by Stage14-70:

```text
DeltaG ~= F/rho in legacy, not 2*F/rho.
```

## Next Work

Do not tune wetting angle and do not start dynamic impact.

Next implementation should be a controlled closure branch with explicit modes:

```text
PressureClosureMode:
  0 legacy p=m0[0]
  1 shadow/diagnostic p*rho*cs2
  2 reference-subtracted pressure candidate

ForceDensityClosureMode:
  0 legacy divide by rho(C)
  1 bounded rho floor for diagnostic only
  2 mixture-density or phase-limited candidate, after derivation

ForceFixedPointMode:
  0 legacy fixed count
  1 residual-gated fixed point with divergence guard
  2 single-pass diagnostic baseline
```

These modes must remain off by default until each one is separately validated
against the Stage14-70 and Stage14-71 baselines.
