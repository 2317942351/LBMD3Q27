# Stage14-69: Momentum Closure Diagnostics Implementation

Date: 2026-06-23

Status: `implemented_p100_probe_completed`

## Claim Boundary

This change is a diagnostic implementation only.

It does not validate contact angle, does not start dynamic impact work, and
does not claim that the wetting boundary condition is fixed. `MomentumForceMode`
and `MomentumClosureProbeMode` are diagnostic switches, not physical repairs.

## Why This Was Added

Stage14-68 narrowed the short-step failure path to:

```text
F_surf seed
  -> F_pressure / F_mu feedback
  -> F_total / rho in gas
  -> UPostForce grows to nonphysical magnitude
  -> g update corrupts later h / PhaseF
```

The remaining question is whether the MRT momentum update injects `F_total/rho`
once, twice, with a wrong sign, or with a pressure/stress input that is already
inconsistent with the TCLB stage timing.

## TCLB Timing Being Audited

The audited producer-consumer line is:

```text
g/h AddDensity streaming
  -> calcPhaseF produces PhaseF from h
  -> BaseIter CollisionMRT reads g/h/PhaseF
  -> m0 = M*g
  -> p = m0[0]
  -> rho = rho(PhaseF)
  -> gradPhi / mu
  -> F_pressure / F_surf / F_mu
  -> F_total
  -> U_half = m0[1:3] + 0.5 * F_total/rho
  -> h update
  -> mF[1:3] = injection_scale * F_total/rho
  -> g update
  -> ReplayMomentumAfterG = sum(e_i g_i)
  -> TCLB streaming
```

All new `Replay*` fields are `AddField(..., group="runtime_diagnostics")`, so
they do not stream. The populations `g` and `h` remain `AddDensity` fields and
must be interpreted after TCLB streaming.

## Code Changes

Model files:

```text
third_party/tclb_snapshots/stage9_analytic_wetting_diffuse_interface/models/multiphase/d3q27_pf_velocity/Dynamics.R
third_party/tclb_snapshots/stage9_analytic_wetting_diffuse_interface/models/multiphase/d3q27_pf_velocity/Dynamics.c.Rt
```

New settings:

```text
MomentumClosureDiagnosticsMode = 0 by default
MomentumClosureProbeMode = 0 by default
```

New diagnostic fields:

```text
ReplayM0
ReplayVelocityHalfForce
ReplayMF
ReplayMomentumAfterG
ReplayMomentumDeltaG
ReplayPressureInput
ReplayPressureForceScale
ReplayPressurePhysicalInput
ReplayFpressureNoThird
ReplayFpressurePhysical
ReplayStressInputXX/XY/XZ/YY/YZ/ZZ
ReplayStressIter1XX/XY/XZ/YY/YZ/ZZ
ReplayFmuRaw
ReplayFmuDelta
ReplayTauUsed
ReplayRhoForForce
ReplayForceInjectionMode
```

Legacy behavior is unchanged when `MomentumClosureDiagnosticsMode=0` and
`MomentumClosureProbeMode=0`.

## Probe Modes

```text
0: legacy behavior, diagnostics may be off
1: record-only legacy behavior
2: diagnostic no-half-force velocity for g-equilibrium
3: diagnostic no mF population injection
4: diagnostic half mF population injection
```

Modes 2-4 deliberately alter the diagnostic run. They are not physical modes
and must not be used as validation evidence.

## Helper Scripts

Updated:

```text
scripts/stage14/stage14_s2_replay_smoke.py
scripts/stage14/stage14_vti_probe.py
```

Added:

```text
scripts/stage14/run_stage14_momentum_closure_probe_remote.sh
scripts/stage14/stage14_momentum_closure_compare.py
reference_solvers/phasefield_d3q27_c/momentum_closure_single_node.cpp
```

The C++ single-node harness checks only local algebra:

```text
U_half = m0 + 0.5 * F_total/rho
expected momentum delta = injection_scale * F_total/rho
```

It does not test TCLB streaming, save/load timing, walls, or contact angle.

The pressure/stress shadow fields are output-only:

```text
ReplayFpressureNoThird  = -p * (rho_h-rho_l) * gradPhi
ReplayFpressurePhysical = -(p*rho*cs2)/3 * (rho_h-rho_l) * gradPhi
ReplayStressIter1*      = stress tensor from fixed-point iteration 1
ReplayStressInput*      = final stress tensor used by final F_mu
ReplayFmuDelta          = final F_mu - first-iteration F_mu
```

They are intended to decide whether the next repair branch is pressure-scale,
stress time-level, fixed-point convergence, or low-density closure.

## P100 Run Command

On `yuan@192.168.1.16` after rebuilding the TCLB lane:

```bash
ROOT=/mnt/usb1t/RUNS/runs/stage14_momentum_closure_probe_20260623 \
GPU=1 \
bash /home/yuan/run_stage14_momentum_closure_probe_remote.sh
```

The script runs `wall_60to30_10` for six iterations with:

```text
CUDA_VISIBLE_DEVICES=1
ReplayDiagnosticsMode=1
MomentumClosureDiagnosticsMode=1
PhaseAdvectionVelocityMode=1
force_fixed_iterator=1
MomentumForceMode=0
MomentumClosureProbeMode=0,1,2,3,4
```

VTI snapshots are preserved when `/mnt/usb1t` has more than 50 GiB free. If it
falls below that threshold, only regenerable `output/*.vti` files are deleted.

## Pass Criterion For This Stage

This stage passes only if the probe lets us explain the six-step failure at the
collision producer-consumer level:

```text
ReplayMF
ReplayVelocityHalfForce
ReplayMomentumAfterG
ReplayMomentumDeltaG
ReplayPressureInput
ReplayFmuRaw
ReplayRhoForForce
```

The intended question is:

```text
Does ReplayMomentumDeltaG match F_total/rho, 0.5*F_total/rho, 0, or another
quantity?
```

Only after this is answered should the next branch be selected:

```text
force insertion repair
pressure closure repair
stress/fixed-point repair
low-density closure repair
stage/load/save replay audit
```

No contact-angle gate is opened by this implementation alone.

## P100 Result Link

The follow-up probe result is documented in:

```text
docs/stage14/70_momentum_closure_probe_result_20260623.md
```
