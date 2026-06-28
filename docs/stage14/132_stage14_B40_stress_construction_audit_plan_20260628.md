# Stage14-B40 Stress Construction Audit Plan

Date: 2026-06-28

Branch: `work/phasefield-c-reference-20260623`

Status: implementation plan. This is a diagnostic gate, not a solver repair and
not contact-angle validation.

## Why B40 Exists

B36 and B37 ruled out two tempting local patches:

```text
B36 force/rho cap: rejected. Upstream pre-cap force still grows to enormous values.
B37 gradPhi cap: rejected. cap_hit_fraction = 0.0 at first onset.
```

B38 and B39 then narrowed the failure:

```text
B38: actual F_mu dominates F_total at the first bad node.
B39: FmuStressClosureMode = 0, 1, 2 all fail.
```

Therefore the next target is not wetting, wall ghost, contact-angle response,
dynamic impact, or another limiter. The next target is the stress tensor used
by `F_mu`.

## Code Evidence

The active MRT path in
`third_party/tclb_snapshots/stage17B_diffuse_solid_shadow/models/multiphase/d3q27_pf_velocity/Dynamics.c.Rt`
currently constructs stress as:

```c
m[selR] = (m0 - EQ$Req)[selR] * Omega;
new_g = solve(M) %*% m;
stress = sum(e_i e_j new_g);
F_mu = (0.5 - tau) * (Density_h - Density_l) * stress * gradPhi;
```

Key risk:

```text
`new_g` is a transformed, relaxed moment residual. It is not obviously the same
object as the non-equilibrium population used by the BGK branch.
```

The BGK path uses a different algebra:

```c
geq = g - geq;
stress = sum(e_i e_j geq);
F_mu = (0.5 - tau) / tau * (Density_h - Density_l) * stress * gradPhi;
```

Key risk:

```text
MRT and BGK use different stress normalization and different tau prefactors.
B40 must compare these definitions in the same run, at the same cells and time
steps, before any write-mode repair is attempted.
```

## B40 Implementation

Add a default-off setting:

```text
Stage14B40StressAuditMode = 0
```

When enabled, B40 writes shadow-only fields. It must not modify:

```text
F_mu
F_total
U
h
g
PhaseF
WallGhost
```

Stress candidates:

```text
B40StressMomentRaw          = stress from solve(M) %*% (m0 - Req)
B40StressMomentRelaxed      = stress from solve(M) %*% ((m0 - Req) * Omega)
B40StressIncomingRaw        = stress from incoming g
B40StressIncomingNeqPre     = incoming raw stress - pre-force equilibrium stress
B40StressBGKPopNeqPre       = stress from direct population residual g - geq_pre
B40StressPostForce          = current post-force shadow stress
```

Force candidates:

```text
B40FmuMomentRawLegacy
B40FmuMomentRawBGK
B40FmuMomentRelaxedLegacy
B40FmuMomentRelaxedBGK
B40FmuIncomingRawLegacy
B40FmuIncomingNeqPreLegacy
B40FmuBGKPopNeqPreLegacy
B40FmuBGKPopNeqPreBGK
B40FmuPostForceLegacy
```

Force-over-rho shadow candidates:

```text
B40ForceOverRhoMomentRawLegacy
B40ForceOverRhoMomentRelaxedLegacy
B40ForceOverRhoBGKPopNeqPreBGK
```

Scalar consistency checks:

```text
B40ProbeActive
B40FmuLegacyScale
B40FmuBGKScale
B40StressLegacyMatchDeltaNorm
B40StressRawOverRelaxed
B40StressPostOverRelaxed
```

The most important internal gate is:

```text
B40StressMomentRelaxed must match the current legacy stress path.
```

If it does not, the B40 instrumentation is wrong and the runtime result cannot
be used.

## Runtime Gate

Case:

```text
wall_60to30_10
Density_h = 1.0
Density_l = 0.005
iterations = 20
vtk_period = 1
vtk_field_set = b40stress
ReplayDiagnosticsMode = 1
MomentumClosureDiagnosticsMode = 1
Stage14B18ClosureDiagnosticsMode = 1
Stage14B40StressAuditMode = 1
PressureClosureMode = 1
ForceDensityClosureMode = 2
ForceFixedPointMode = 2
PhaseAdvectionVelocityMode = 2
```

Run location:

```text
server = yuan@192.168.1.16
gpu = CUDA_VISIBLE_DEVICES=1
root = /mnt/usb1t/RUNS/runs/stage14_B40_stress_construction_audit_20260628
binary = /home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
```

## Decision Rules

If `B40StressMomentRelaxed` equals legacy and is the only exploding stress:

```text
Audit MRT relaxation and whether `(m0 - Req) * Omega` is the right stress
object for `F_mu`.
```

If raw moment and relaxed moment both explode:

```text
The incoming moment residual is already contaminated before relaxation.
Return to g streaming/history and equilibrium subtraction.
```

If BGK-style population non-equilibrium stays bounded while MRT residuals
explode:

```text
Design a default-off MRT stress reconstruction candidate based on a population
non-equilibrium or corrected moment-space projection.
```

If BGK tau-scale alone changes the force scale enough to remove the onset:

```text
Do a literature-backed prefactor derivation before making any write-mode change.
```

If every stress definition produces the same large force:

```text
The issue is upstream of stress construction. Return to incoming g, pressure
moment, and TCLB AddDensity/stage semantics.
```

## Claim Limits

Allowed:

```text
B40 stress algebra audit complete/pass/fail.
```

Forbidden:

```text
contact-angle validation passed
curved-wall wetting solved
dynamic impact ready
F_mu repaired
```
