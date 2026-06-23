# Stage14-72: Pressure / Density / Fixed-Point Probe Modes

Date: 2026-06-23

Status: `implemented_p100_probe_completed`

## Claim Boundary

This change is a diagnostic implementation only.

It does not validate contact angle, does not start dynamic impact work, and
does not make `PressureClosureMode`, `ForceDensityClosureMode`, or
`ForceFixedPointMode` a production physics repair.

All new modes default to `0`, so legacy behavior is unchanged unless a probe
case explicitly enables them.

## Why This Was Added

Stage14-70 demoted simple MRT double force injection:

```text
ReplayMomentumDeltaG ~= ReplayMF ~= F_total/rho
```

Stage14-71 showed that the failure is already present on the first force
evaluation and is then amplified by the second fixed-point pass:

```text
force_fixed_iterator = 1:
  ReplayFpressure       O(1e3)
  ReplayFmuRaw          O(1e3)
  ReplayForceOverRho    O(1e6)
  ReplayPhaseFromH      leaves [0,1]

force_fixed_iterator = 2:
  ReplayFmuRaw / stress grows to O(1e89)-O(1e92)
```

The next question is whether short-step stability is controlled mainly by:

```text
pressure input scale
low-density F/rho denominator
fixed-point stress/F_mu amplification
or a combination of those paths
```

## New Settings

```text
PressureClosureMode = 0
  Legacy: calc_Fp uses p = m0[0].

PressureClosureMode = 1
  Diagnostic: calc_Fp uses p * rho * cs2.

PressureClosureMode = 2
  Diagnostic: calc_Fp uses p - PressureClosureReference.

ForceDensityClosureMode = 0
  Legacy: F/rho uses rho(C).

ForceDensityClosureMode = 1
  Diagnostic: F/rho denominator is max(rho(C), ForceDensityRhoFloor).
  If ForceDensityRhoFloor <= 0, Density_l is used.

ForceFixedPointMode = 0
  Legacy: existing force_fixed_iterator / ForceFixedTol behavior.

ForceFixedPointMode = 1
  Diagnostic: use ForceFixedMaxIter and residual tolerance, with a divergence
  guard that rejects a pass when residual exceeds ForceFixedDivergenceGuardFactor.

ForceFixedPointMode = 2
  Diagnostic: single-pass force/stress baseline.
```

## New Diagnostics

```text
ReplayPressureClosureMode
ReplayForceDensityClosureMode
ReplayForceFixedPointMode
ReplayForceRhoRaw
ReplayForceRhoEffective
```

`ReplayPressureMoment` remains the raw MRT zeroth moment. `ReplayPressureInput`
now records the actual pressure-like value supplied to `calc_Fp` in the active
probe mode.

`ReplayForceRhoRaw` records the phase-interpolated density. `ReplayForceRhoEffective`
records the denominator actually used for `F/rho`, `U_half`, and `mF`.

## Code Paths Changed

```text
Dynamics.R
  Adds settings and output fields.

Dynamics.c.Rt
  Adds helper functions:
    stage14_pressure_force_input
    stage14_effective_force_rho
    stage14_inv_force_rho
    stage14_force_iter_limit_from_mode

  MRT path:
    calc_Fp uses pressure_force_input.
    U_half and mF use force_rho_inv.
    fixed-point loop can be legacy, guarded, or single-pass.

scripts/stage14/stage14_s2_replay_smoke.py
  Emits the new XML params and summarizes the new VTI fields.

scripts/stage14/run_stage14_closure_mode_probe_remote.sh
  Runs the short P100 isolation probes.
```

## Probe Set

The remote runner executes six-step `wall_60to30_10` probes on P100:

```text
probe_B0_legacy
probe_B1_pressure_physical
probe_D1_rho_floor_density_l
probe_C2_single_pass
probe_C1_guarded_fp
probe_B1D1_pressure_physical_rho_floor
```

These are not angle-validating cases. They are intended to answer whether the
stage-6 failure chain is cut by pressure scaling, force-density denominator,
fixed-point control, or their combination.

## Expected Decision Use

If `PressureClosureMode=1` reduces `ReplayFpressure` and prevents phase blow-up
without hiding `F_mu`, prioritize pressure moment derivation.

If `ForceDensityClosureMode=1` alone prevents `ReplayForceOverRho` blow-up while
raw force fields remain large, prioritize the low-density force closure.

If `ForceFixedPointMode=2` or guarded mode prevents the O(1e89) amplifier but
first-pass fields still fail, fixed-point control is necessary but not sufficient.

If none of these isolate the failure, return to the TCLB stage/load/save replay
and AddDensity streaming timeline.

## Required Checks

Before using the probe modes:

```text
python -m py_compile scripts/stage14/stage14_s2_replay_smoke.py \
  scripts/stage14/stage14_vti_probe.py \
  scripts/stage14/stage14_momentum_closure_compare.py \
  scripts/audit_tclb_execution_semantics.py

git diff --check
TCLB source generation and CUDA build on /home/yuan/src/TCLB_lbm2026_compile_lane
```

Passing this stage means the probe modes compile and produce interpretable VTI
diagnostics. It does not mean contact-angle behavior is fixed.

## P100 Result

Remote run:

```text
/mnt/usb1t/RUNS/runs/stage14_closure_mode_probe_20260623
```

Local summary artifacts:

```text
artifacts/stage14_closure_mode_probe_20260623/
```

Binary:

```text
/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
sha256 = f8050df8da32292be3173bab40561a3dd562a7a98578e82dd58cf852368c2748
```

GPU:

```text
CUDA_VISIBLE_DEVICES=1
GPU 1 = Tesla P100-PCIE-16GB
```

All six probe cases completed with `RUN_RC=0` and produced seven VTI frames
each. This only means the executable completed; it does not mean the field is
physically stable.

Step-6 max-absolute values:

```text
probe                                  PhaseFromH   Force/rho   p_input    F_mu_raw   F_mu_delta
B0 legacy                              1.318e105    1.944e86    3.121e46   1.720e89   1.720e89
B1 pressure physical                   1.228e31     4.397e35    1.996e15   4.397e32   4.397e32
D1 rho floor Density_l                 1.318e105    8.095e95    3.121e46   8.095e92   8.095e92
C2 single pass                         6.087e3      1.817e6     2.645e4    6.948e2    0
C1 guarded fixed point                 6.252e81     2.187e59    5.167e25   1.045e117  1.994e49
B1D1 pressure physical + rho floor     1.228e31     4.397e35    1.996e15   4.397e32   4.397e32
```

Time-evolution evidence:

```text
B1 pressure physical keeps pressure input small through step 4:
  step 4 p_input = 9.901e-5, Force/rho = 2.603e1, PhaseFromH = 1.0

but by step 5:
  F_mu_raw = 3.475e5, Force/rho = 3.285e8

and by step 6:
  PhaseFromH = 1.228e31
```

`ForceDensityClosureMode=1` with the default `Density_l` floor does not help
because the failure has already driven `PhaseF`/`rho(C)` outside the physical
range. It is not a sufficient closure.

`ForceFixedPointMode=2` confirms that the second fixed-point pass is a major
amplifier, because the blow-up is much smaller than legacy. It still fails by
step 6, so fixed-point control alone is not a sufficient repair.

`ForceFixedPointMode=1` with a simple residual divergence guard is worse than
single-pass in this configuration. The current guard is therefore diagnostic
only and should not be promoted.

## Updated Diagnosis

The pressure input scale is real and contributes early, but it is not sufficient
to explain or fix the failure. The next root-cause branch should prioritize:

```text
1. F_mu stress reconstruction time level and algebra.
2. Phase equation boundedness / anti-diffusive source driving PhaseF outside [0,1].
3. Fixed-point loop acceptance criterion after stress/F_mu is corrected.
4. Only then revisit pressure closure and force-density denominator as formal modes.
```

Do not proceed to contact-angle validation or dynamic impact from this result.
