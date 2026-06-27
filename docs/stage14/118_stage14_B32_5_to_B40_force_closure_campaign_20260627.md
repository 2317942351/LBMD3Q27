# Stage14-B32.5 To B40 Force Closure Campaign

Date: 2026-06-27

Branch: `work/phasefield-c-reference-20260623`

Status: active plan. B32.5 and B33 are diagnostic gates; they must not be
reported as contact-angle validation or dynamic impact readiness.

## Why This Campaign Exists

B32 narrowed the dynamic-impact blocker to the flat-wall force numerator:

```text
F_surf = mu * gradPhi
  -> stress reconstruction / F_mu
  -> F_total
  -> F_total / rho
```

The force split showed:

| Probe | Result |
|---|---|
| full force | momentum threshold at step 12; force/rho and F_mu threshold at step 15 |
| noFmu | no configured threshold in the 20-step gate |
| noPressure | essentially same as full force |
| noSurf | no configured threshold in the 20-step gate |
| zeroForce | no configured threshold |
| surfBodyOnly | no configured threshold |

This means the next work must audit the coupled `F_surf/F_mu` producer path.
It must not return to curved-wall wetting, dynamic contact-line tuning, or
dynamic impact setup until the flat-wall force gate is closed.

## Teacher MCP Pre-Review Adjustment

Teacher MCP session `session-20260627-0f3298` reviewed the first B33-B40 plan
and returned `NEEDS_FIX`. The key objection was valid: before building a
single-node MRT harness or modifying physics, the campaign must explicitly
audit TCLB stage ordering and replay-field semantics. Otherwise a stage/load
or AddDensity/AddField timing issue could be misdiagnosed as a force-formula
error.

Therefore this campaign inserts B32.5 before B33:

```text
B32.5 static TCLB stage/force-ordering audit
  -> B33 first-bad-cell runtime ledger
  -> B34 single-node MRT algebra harness
  -> B35 coupled numerator split
  -> B36 minimal physics candidate
  -> B37 flat-wall stability
  -> B38 flat-wall contact angle and decoupled response
  -> B39 sphere/cylinder regression
  -> B40 dynamic impact preflight
```

## Code Anchors

Primary model:

```text
third_party/tclb_snapshots/stage17B_diffuse_solid_shadow/models/multiphase/d3q27_pf_velocity/Dynamics.R
third_party/tclb_snapshots/stage17B_diffuse_solid_shadow/models/multiphase/d3q27_pf_velocity/Dynamics.c.Rt
third_party/tclb_snapshots/stage17B_diffuse_solid_shadow/models/multiphase/d3q27_pf_velocity/Boundary.c.Rt
```

Important current facts from code:

| Anchor | Meaning |
|---|---|
| `Dynamics.R` `AddDensity` for `pnorm/U/V/W` | momentum populations and macroscopic densities participate in TCLB streaming |
| `Dynamics.R` `Replay*`, `B18*`, `B20*`, `B21*`, `B22*` as `AddField` | diagnostics must not stream |
| `CollisionMRT()` | active MRT path for current Stage14 probes |
| `calcMu(C)` | computes chemical potential from guarded Laplace before force assembly |
| `calcGradPhi()` | computes guarded gradient before `F_surf`, `F_pressure`, and `F_mu` |
| `calc_Fs()` | active surface force is `F_surf = mu * gradPhi` |
| MRT `F_mu` formula | `(0.5-tau) * (Density_h-Density_l) * stress * gradPhi` |
| BGK `F_mu` formula | `(0.5-tau)/tau * (Density_h-Density_l) * stress * gradPhi`; must be recorded as a possible consistency issue |
| half-force velocity | `U = m0[2:4] + 0.5 * F_total / rho_eff` |
| h update | `h = h - omega * (h - heq + 0.5*Fphi) + Fphi` |
| MRT force insertion | `mF[2:4] = F_total/rho_eff`; `m = m0 - (m0 - EQ + 0.5*mF)*Omega + mF` |

## B32.5: Static TCLB Semantics Audit

Purpose:

```text
Prove the code-level producer-consumer order before interpreting B33 runtime
fields.
```

Implementation:

```text
scripts/stage14/stage14_b32_5_semantics_audit.py
artifacts/stage14_B32_5_semantics_audit_20260627/
```

The script parses `Dynamics.R` and `Dynamics.c.Rt` and writes:

```text
stage14_B32_5_semantics_audit.json
stage14_B32_5_semantics_audit.md
```

Checks:

1. `g/h/pnorm/U/V/W` streaming fields are `AddDensity`, not `AddField`.
2. Replay/Bxx diagnostics are `AddField`, not `AddDensity`.
3. `calcMu`, `calcGradPhi`, `F_surf`, `F_mu`, `F_total`, half-force `U`,
   h update, and MRT g update appear in the expected order inside
   `CollisionMRT`.
4. `F_mu` prefactor mismatch between MRT and BGK is explicitly recorded.
5. Stage ordering in `Dynamics.R` is recorded, especially
   `BaseIter -> calcPhase -> calcPhaseGrad -> calcWall_CA -> calcWallPhase_correction`.

Gate outcome:

```text
semantics_audit_pass
semantics_audit_pass_with_warnings
semantics_audit_fail
```

B32.5 does not prove physical correctness. It only prevents obvious TCLB
semantic misreadings before B33/B34.

## B33: First-Bad-Cell Ledger

Purpose:

```text
For step 10-16 of wall_60to30_10, co-locate the first bad node's phase,
chemical potential, gradient, surface force, stress, F_mu, F_total, F/rho,
velocity, and h-update diagnostics.
```

Runtime settings:

```text
case = wall_60to30_10
Density_h = 1.0
Density_l = 0.005
FmuStressClosureMode = 2
PressureClosureMode = 1
ForceFixedPointMode = 2
PhaseAdvectionVelocityMode = 2
ForceDensityClosureMode = 2
iterations = 20
vtk_period = 1
GPU = P100, CUDA_VISIBLE_DEVICES=1
```

Probe matrix:

| Probe | `MomentumForceMode` | Meaning |
|---|---:|---|
| `L0_full` | 0 | full coupled force |
| `L1_noFmu` | 1 | remove `F_mu` from active `F_total` |
| `L2_noSurf` | 3 | remove `F_surf` from active `F_total` |
| `L3_noPressure` | 2 | remove `F_pressure` |
| `L4_zeroForce` | 4 | no momentum force reference |

Required co-located fields:

```text
PhaseField, ReplayPhaseFromH, ReplayPhaseConsumed,
ReplayLapPhi, ReplayMu, ReplayGradPhi, ReplayFsurf,
ReplayFpressure, ReplayFmu, ReplayFmuRaw, ReplayFtotal,
ReplayForceOverRho, ReplayRho, ReplayForceRhoEffective,
ReplayTau, ReplayPressureInput, B18 stress/F_mu candidates,
B21 h-population fields, B22 velocity producer fields
```

Decision:

```text
If mu/lapPhi is abnormal before stress/F_mu, go to wall/near-wall Laplace branch.
If gradPhi/F_surf is abnormal before stress/F_mu, go to surface-force branch.
If stress/F_mu grows first while mu/gradPhi are moderate, go to stress
time-level or prefactor branch.
If MomentumAfterG/MomentumDeltaG mismatches expected mF, go to B34 before any
physics repair.
```

## B34: Single-Node MRT Algebra Harness

Purpose:

```text
Reproduce the generated MRT force insertion algebra for one node and compare
with TCLB replay fields.
```

Harness formula:

```text
mF[2:4] = F_total / rho_eff
m = m0 - (m0 - EQ$Req + 0.5*mF)[selR] * Omega + mF
g = invM %*% m
momentum_after_g = sum(e_i * g_i)
```

Do not use B34 to validate TCLB streaming. It only validates local collision
algebra after B32.5 has recorded the stage semantics.

## B35: Coupled Numerator Split

B35 is shadow-first unless B33/B34 prove an unambiguous low-risk active
candidate. Candidate diagnostics:

1. legacy `F_surf = mu * gradPhi`.
2. `F_surf` using bounded/shadow `mu`.
3. `F_surf` using no-wall-ghost `mu/gradPhi` shadow.
4. `F_mu` from legacy relaxed stress.
5. `F_mu` from incoming non-equilibrium stress.
6. `F_mu` prefactor `(0.5-tau)` versus `(0.5-tau)/tau`.
7. coupled `F_surf + F_mu` consistency check.

## B36: Minimal Physics Candidate

B36 is the first allowed repair stage. It must modify only the branch selected
by B33-B35:

| Evidence branch | Allowed candidate |
|---|---|
| `mu/lapPhi` first | repair near-wall Laplace/ghost reconstruction |
| `gradPhi/F_surf` first | repair near-wall gradient or surface-force scaling |
| stress first | repair `F_mu` time level, non-equilibrium stress, or prefactor |
| MRT algebra mismatch | repair force insertion before touching physics |
| coupled only | implement one explicit coupled closure mode, default off |

No default physics behavior may change before the candidate passes B37.

## B37: Flat-Wall Short Stability Gate

Cases:

```text
wall_60to30_10
Density_l = 0.005
steps = 20, 100, 500
```

Pass criteria:

```text
PhaseField and PhaseFromH finite and bounded enough for diagnostic continuation
No step-15 F_total/rho spike
B34 algebra replay matches selected active mode
No new pressure-force branch becomes primary
```

## B38: Flat-Wall Static Contact-Angle Gate

Only after B37 passes:

```text
flat wall equilibrium: theta 30, 90, 150
flat wall decoupled: 60->30, 120->150
```

Required evidence:

```text
angle metric
2D morphology plot
mass drift / kinetic energy / spurious velocity diagnostics
claim limited to flat-wall static gate
```

## B39: Sphere/Cylinder Regression

Only after B38 passes:

1. reuse Stage17B diffuse-solid/analytic-SDF shadow diagnostics.
2. run cylinder and sphere shadow checks.
3. then controlled write only if shadow fields are continuous and bounded.
4. then static curved contact-angle gates.

## B40: Dynamic Impact Preflight

B40 is still not a production dynamic impact simulation. It is a preflight
packet requiring:

```text
flat wall B37/B38 pass
sphere/cylinder B39 pass
force closure candidate documented and default behavior controlled
short impact setup with force/mass/KE diagnostics
```

Dynamic impact remains blocked until these preflight conditions are met.

## Claim Limits

Forbidden until the relevant gates pass:

```text
contact angle validation passed
curved wetting solved
dynamic impact ready
production solver fixed
```

Allowed wording:

```text
B32.5 semantics audit pass/fail
B33 first-bad-cell ledger pass/fail
B34 local MRT algebra match/mismatch
B35 candidate branch selected
B36 candidate passes/fails flat-wall force gate
```
