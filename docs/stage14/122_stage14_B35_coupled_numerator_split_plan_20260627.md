# Stage14-B35 Coupled Numerator Split Plan

Date: 2026-06-27

Branch: `work/phasefield-c-reference-20260623`

Status: plan only. B35 must wait for B33 runtime ledger and B34 replay
comparison unless the next work is purely shadow diagnostics.

## Current Input Evidence

B32 selected the active blocker:

```text
dynamic_preflight_blocked_by_stress_fmu_and_surface_force_coupled_numerator
```

B32.5 then confirmed the source-level order:

```text
PhaseF
  -> calcMu(C)
  -> m0 from streamed g
  -> pressure input
  -> calcGradPhi()
  -> F_pressure/F_surf
  -> stress reconstruction / F_mu
  -> F_total
  -> half-force velocity
  -> h update
  -> MRT mF/g update
```

B34 local smoke showed the current MRT algebra predicts:

```text
ReplayMomentumDeltaG ~= 0.5 * ReplayMF
```

The B33 runtime ledger is still required because the first B33 run was
interrupted by remote storage I/O errors.

## Why B35 Must Be Shadow-First

The B32 force split proves both of these statements:

1. Removing `F_mu` removes the short-gate failure.
2. Removing `F_surf` also removes the short-gate failure.

But it does not prove either standalone formula is wrong. It more likely means
the active numerator is a coupled feedback:

```text
F_surf = mu * gradPhi
  -> post/relaxed stress reconstruction
  -> F_mu = prefactor * stress * gradPhi
  -> F_total/rho
```

Therefore B35 cannot simply disable one term and call that a repair. It must
separate the numerator into shadow candidates and ask which candidate explains
the first bad cell found by B33.

## Existing Code Assets

`Dynamics.c.Rt` already contains several B35-relevant paths:

| Code path | Lines | Use in B35 |
|---|---:|---|
| `stage14_fmu_from_stress(...)` | around 214 | reusable `F_mu = prefactor * stress * gradPhi` helper |
| `calcGradPhiRawNoGhostShadow()` | around 2198 | no-ghost gradient candidate |
| `calcMuNoGhostShadow(...)` | around 2336 | no-ghost chemical-potential candidate |
| `B18FmuLegacy/PreForce/PostForce/ForceExcluded/Incoming` | around 3445-3459 | existing stress-time-level candidates |
| `FmuStressClosureMode=2` | around 3185 | active incoming non-equilibrium candidate used in B28-B32 |
| MRT `F_mu` prefactor | around 3176 | `(0.5-tau)` |
| BGK `F_mu` prefactor | around 4290 | `(0.5-tau)/tau`, recorded as mismatch |

## B35 Candidate Matrix

The first B35 matrix should be diagnostic-only unless B33/B34 already force a
specific active branch.

| Candidate | Purpose | Requires new TCLB fields? | Active write allowed? |
|---|---|---:|---:|
| legacy `F_surf` | baseline `mu * gradPhi` | no | already active |
| no-ghost `mu` / no-ghost `gradPhi` | test wall/ghost contribution to surface force | partly existing | no |
| bounded `mu` shadow | test whether rare `mu` spikes control `F_surf` | yes | no |
| legacy relaxed-stress `F_mu` | baseline stress path | existing | active only in legacy |
| incoming non-equilibrium `F_mu` | B28 candidate | existing | active via `FmuStressClosureMode=2` |
| force-excluded stress `F_mu` | removes force-induced equilibrium stress component | existing B18 shadow | no |
| prefactor `(0.5-tau)/tau` shadow | compare MRT against BGK convention | yes | no |
| coupled candidate total | compare `F_surf_candidate + F_mu_candidate` at B33 first-bad nodes | yes if new fields are needed | no |

## Required New Fields If B33/B34 Require Them

Only add these if existing B18/B33 fields are insufficient:

```text
B35ProbeActive
B35MuNoGhost
B35LapPhiNoGhost
B35GradPhiNoGhost
B35FsurfNoGhost
B35MuBounded
B35FsurfMuBounded
B35FmuPrefactorTau
B35FtotalCandidateNoGhost
B35FtotalCandidatePrefactorTau
B35CandidateForceOverRhoNoGhost
B35CandidateForceOverRhoPrefactorTau
```

Default settings:

```text
Stage14B35CoupledNumeratorDiagnosticsMode = 0
Stage14B35MuAbsCap = 0.0
Stage14B35PrefactorMode = 0
```

All defaults must preserve current behavior.

## Decision Rules

B35 should be interpreted using B33 first-bad nodes:

| B33/B34 observation | B35 branch |
|---|---|
| `ReplayLapPhi` or `ReplayMu` spikes before `F_mu` | prioritize `calcMu` / near-wall Laplace / ghost reconstruction |
| `ReplayGradPhi` or `ReplayFsurf` spikes first | prioritize gradient or surface-force formula |
| `B18FmuPostForce` is huge but incoming/force-excluded stress is moderate | stress time-level / post-force reconstruction branch |
| `(0.5-tau)/tau` prefactor shadow matches stable scale better | prefactor consistency branch |
| `ReplayMomentumDeltaG` fails B34 relation | do not change `F_surf/F_mu`; repair MRT force insertion or replay timing |
| no shadow explains first bad node | return to TCLB stage/load/save or population streaming audit |

## Implementation Order

1. Complete B33 on a non-USB run root.
2. Run B34 replay comparison on B33 argmax traces.
3. If B34 fails, branch to MRT insertion audit before B35 physics.
4. If B34 passes and B33 identifies the numerator layer, run existing B18/B33
   fields through a B35 digest first.
5. Only then add new B35 shadow fields if the existing fields cannot separate
   `mu/gradPhi/Fsurf/stress/Fmu`.

## Claim Limits

Allowed:

```text
B35 branch candidate selected
B35 shadow candidate explains/does not explain B33 first-bad node
```

Forbidden:

```text
F_mu fixed
surface tension force fixed
contact angle validation passed
dynamic impact ready
```
