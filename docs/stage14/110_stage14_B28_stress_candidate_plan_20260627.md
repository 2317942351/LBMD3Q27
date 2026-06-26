# Stage14-B28 Stress-Closure Candidate Plan

Date: 2026-06-27

Branch: `work/phasefield-c-reference-20260623`

Status: plan only until B27 stress confirmation finishes.

## Scope

B28 is allowed only after B27 confirms the stress-time-level branch. It must not
be implemented from B26 alone. B28 is not a contact-angle validation and not a
dynamic-impact step.

## Current Code Path

The relevant solver path is in:

```text
third_party/tclb_snapshots/stage17B_diffuse_solid_shadow/models/multiphase/d3q27_pf_velocity/Dynamics.c.Rt
```

Current MRT collision sequence:

```text
PhaseF -> C
rho = rho(C)
mu = calcMu(C)
gradPhi = calcGradPhi()
F_surf = mu * gradPhi
p = m0[0]
F_pressure = calc_Fp(pressure_force_input, gradPhi)

do fixed-point loop:
  m = (m0 - EQ$Req) * Omega
  new_g = inv(M) * m
  stress = second moment of new_g
  F_mu = (0.5 - tau) * (rho_h - rho_l) * stress * gradPhi
  F_total = F_surf + F_pressure + F_body + F_mu
  U = m0[1:3] + 0.5 * F_total / rho_eff

h update consumes selected phase-advection velocity
```

The suspicious point is that the stress used by `F_mu` is computed from
`new_g`, while a separate diagnostic shadow recomputes stress after the
half-force velocity has already been applied. B26 shows this post-force stress
shadow amplifies before the velocity/phase markers cross.

## B27 Inputs Required

B27 stress confirmation must produce the five rows:

```text
S0_legacy_stress
S1_density_floor_stress
S2_noFmu_stress
S3_noSurf_stress
S4_noMomentum_stress
```

Decision logic:

| B27 pattern | B28 branch |
|---|---|
| S2 noFmu removes or strongly delays stress/velocity onset | implement an explicit `FmuStressClosureMode` candidate |
| S3 noSurf removes onset while S2 does not | audit `F_surf = mu * gradPhi` / `mu` stencil before stress closure |
| S4 noMomentum removes onset but S2/S3 do not | audit force insertion / post-force velocity coupling |
| S1 density floor removes onset | denominator branch reopens; do not implement stress candidate |
| all probes retain same early stress amplification | audit stress diagnostic algebra/template timing before physics edit |

## Minimal Candidate If Stress Branch Is Confirmed

Add a new solver setting:

```text
FmuStressClosureMode = 0 legacy
FmuStressClosureMode = 1 first-pass stress only
FmuStressClosureMode = 2 incoming non-equilibrium stress shadow promoted
FmuStressClosureMode = 3 force-excluded non-equilibrium stress shadow promoted
```

Only one mode should be promoted from shadow to active in the first B28 commit,
based on B27. The default must remain `0`.

Candidate implementation rules:

- Do not reuse `MomentumForceMode=1` as a physical fix. That switch removes
  `F_mu` and is diagnostic only.
- Do not clamp `PhaseF`, `tmp1`, or `F/rho` to force stability.
- Do not make `ForceDensityClosureMode=1` the default.
- Do not change wetting or curved-wall `WallGhost` paths in the same commit.
- If `AddSetting` or new diagnostics are added, full TCLB source regeneration
  and CUDA rebuild are mandatory.

## Verification Gates After B28

B29 short stability:

```text
wall_60to30_10
Density_h = 1.0
Density_l = 0.005
steps = 20 then 100
P100 only
```

Pass criteria:

```text
PhaseFromH finite and near-bounded
B22MomentumSpeed no early threshold
B18 stress amplification does not precede velocity failure
mass drift and max velocity reported
```

Only after B29 passes:

```text
B30 flat-wall wetting direction
B31 cylinder/sphere static preflight
B32 dynamic impact preflight packet only
```

## Prohibited Claims

Do not claim:

```text
contact angle validation passed
dynamic impact readiness
FmuStressClosureMode is physically validated
```

The strongest allowed B28 claim is:

```text
candidate mode removes or delays the B27-confirmed short-onset mechanism under diagnostic gates
```

