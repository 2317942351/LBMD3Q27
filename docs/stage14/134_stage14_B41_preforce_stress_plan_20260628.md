# Stage14-B41 Pre-Force Stress Candidate Plan

Date: 2026-06-28

Branch: `work/phasefield-c-reference-20260623`

Status: implementation plan. B41 is a default-off candidate gate, not a final
physics claim.

## Summary

B40 showed that the first actionable failure in `wall_60to30_10` is not a
contact-angle or WallGhost response. The earliest dangerous chain is:

```text
stress time-level / fixed-point feedback
  -> F_mu
  -> F_total / rho_eff
  -> post-force velocity
  -> amplified post-force stress shadow
  -> later phase out-of-bounds
```

B41 should test a narrowly scoped candidate: compute the active `F_mu` from a
pre-force or consistent incoming non-equilibrium stress source, behind an
explicit default-off mode. The goal is to decide whether removing post-force
stress feedback delays or removes the step-13 force-over-rho onset.

## Why B41 Is the Next Step

The current code path in `Dynamics.c.Rt` does:

```text
1. Build m0 from incoming g.
2. Build stress from (m0 - Req) * Omega.
3. Compute F_mu = stress * gradPhi.
4. Build F_total.
5. Update U = m0 + 0.5 * F_total / rho_eff.
6. Continue fixed-point loop / diagnostics with the force-updated velocity.
```

B40 measured:

```text
step 13:
  ForceOverRhoNorm       = 2.636e3
  FmuNorm                = 1.449e1
  FpressureNorm          = 2.215e-2
  FsurfNorm              = 8.358e-6
  StressPreForceNorm     = 3.833e2
  StressPostForceNorm    = 2.029e6
  StressPostOverPreRatio = 5.294e3

step 20:
  PhaseFromH first exceeds the configured bound.
```

So B41 must test stress time level before returning to curved-wall wetting.

## Teacher MCP Review

Teacher MCP was consulted using direct B40 evidence and code anchors.

Result:

```text
status = PASS
confidence = 0.90
next_action = proceed to B41 implementation
```

Required guardrails from the review:

```text
1. Define the exact pre-force non-equilibrium stress source.
2. Keep B41 default-off.
3. Add B41 shadow diagnostics.
4. Use the 20-step gate only as candidate evidence.
5. Do not treat B41 as contact-angle validation.
```

## Proposed Code Changes

### Settings

Extend the existing setting rather than adding an unrelated flag:

```text
FmuStressClosureMode = 3
```

Meaning:

```text
0 legacy relaxed-stress F_mu
1 freeze first-pass F_mu in multi-pass loops
2 existing incoming non-equilibrium candidate
3 B41 pre-force consistent stress candidate
```

Default remains:

```text
FmuStressClosureMode = 0
```

Optional diagnostic switch:

```text
Stage14B41PreForceStressMode = 0
```

If added, it should only control extra output fields. It must not be required
to keep legacy behavior unchanged.

### Stress Source Candidate

B41 must not use post-force `U` to construct the stress used by active `F_mu`.
The first candidate should use a pre-force velocity state derived from incoming
momentum:

```text
u_pre = m0[1:3]
```

Then construct a consistent pre-force non-equilibrium stress candidate:

```text
stress_b41_pre = stress from incoming population g minus equilibrium built
                 with u_pre and the same pressure/density conventions used
                 by the active MRT path.
```

Implementation location:

```text
Dynamics.c.Rt near the existing b28/b40 pre-force stress blocks:
  lines 3495-3536 for incoming/pre-force stress setup
  lines 3687-3714 for active F_mu selection
```

The write path should be:

```text
if (FmuStressClosureMode > 2.5 && FmuStressClosureMode < 3.5) {
    F_mu = F_mu_from_b41_pre_force_stress;
}
```

No other path should change:

```text
F_pressure unchanged
F_surf unchanged
F_body unchanged
U update unchanged
h update unchanged
g update unchanged except through the chosen F_total
PhaseF write unchanged
WallGhost unchanged
```

### Diagnostics

Add B41 output fields as `AddField`, not `AddDensity`.

Recommended fields:

```text
B41ProbeActive
B41StressSourceId
B41StressPreForceNorm
B41StressLegacyRelaxedNorm
B41StressDeltaLegacyNorm
B41FmuPreForceX/Y/Z
B41FmuPreForceNorm
B41FmuLegacyX/Y/Z
B41FmuLegacyNorm
B41FmuDeltaLegacyNorm
B41ForceOverRhoPreForceX/Y/Z
B41ForceOverRhoPreForceNorm
B41StressPostOverPreShadow
B41PhaseOOBShadow
```

If output volume is too high, keep the vector fields and only summary scalar
norms for the first run.

## B41 Runtime Gate

Remote:

```text
server = yuan@192.168.1.16
gpu = CUDA_VISIBLE_DEVICES=1
run root = /mnt/usb1t/RUNS/runs/stage14_B41_preforce_stress_candidate_20260628
compile lane = /home/yuan/src/TCLB_lbm2026_compile_lane
```

Case:

```text
wall_60to30_10
Density_h = 1.0
Density_l = 0.005
iterations = 20
vtk_period = 1
```

Settings:

```text
ReplayDiagnosticsMode = 1
MomentumClosureDiagnosticsMode = 1
Stage14B18ClosureDiagnosticsMode = 1
Stage14B40StressAuditMode = 1
Stage14B41PreForceStressMode = 1
FmuStressClosureMode = 3
PressureClosureMode = 1
ForceDensityClosureMode = 2
ForceDensityRhoFloor = 0.005
ForceFixedPointMode = 2
PhaseAdvectionVelocityMode = 2
```

B41 must be compared against the B40/B39 legacy baseline:

```text
B40 step-13 ForceOverRhoNorm = 2.636e3
B40 step-13 StressPostForceNorm = 2.029e6
B40 first PhaseFromH OOB = step 20
```

## Acceptance Criteria

B41 is considered a useful candidate only if:

```text
1. Build and run complete with RC=0.
2. No NaN/nonfinite fields by step 20.
3. ForceOverRho threshold crossing is absent by step 20, or delayed with a
   clearly reduced maximum compared with B40.
4. Active F_mu follows the B41 pre-force stress path, verified by diagnostics.
5. PhaseFromH does not leave the configured bounds earlier than B40.
6. Momentum replay remains interpretable.
```

B41 is rejected if:

```text
1. ForceOverRho still crosses near step 13 with comparable magnitude.
2. F_mu is merely moved to another exploding stress definition.
3. PhaseFromH leaves bounds earlier.
4. The candidate requires a hidden limiter or clamp to pass.
5. The mode changes legacy behavior when FmuStressClosureMode=0.
```

## What B41 Cannot Prove

B41 cannot prove:

```text
static contact-angle correctness
sphere/cylinder wetting correctness
compact-stencil write safety
dynamic impact readiness
```

If B41 passes the 20-step gate, the next gates should be:

```text
B42: B41 candidate 100-step flat-wall stability probe.
B43: B41 candidate phase/mass/momentum conservation audit.
B44: density-ratio 1000 short probe.
B45: flat-wall contact-angle direction gate.
B46: return to Stage17B curved-surface shadow/write planning.
```

If B41 fails, the next branch is not another limiter. The next branch should
audit the population/moment definition itself:

```text
incoming g AddDensity streaming time level
MRT equilibrium Req pressure/density convention
stress scaling and tau prefactor
whether stress should be reconstructed from pre-collision non-equilibrium,
post-collision non-equilibrium, or a Guo-force-corrected population.
```
