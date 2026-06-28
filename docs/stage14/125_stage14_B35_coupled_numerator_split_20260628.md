# Stage14-B35 Coupled Numerator Split Result

Date: 2026-06-28

Branch: `work/phasefield-c-reference-20260623`

Status: diagnostic evidence, not a solver fix.

## Purpose

B35 tested whether the step-15 `ForceOverRho` spike in `wall_60to30_10`
comes from pressure, surface force, viscous/stress force, or denominator
closure. It used shadow-only coupled numerator fields. No contact-angle claim
is allowed from this stage.

## Runtime

Remote root:

```text
/mnt/usb1t/RUNS/runs/stage14_B35_coupled_numerator_split_20260628
```

Local artifact root:

```text
artifacts/stage14_B35_coupled_numerator_split_20260628
```

Binary:

```text
2ede1dbb1459fd014c9b7a9c2ad67023becdcfb549c6c7a49960508da0acfe2a
```

Key runtime settings:

```text
case = wall_60to30_10
Density_h = 1.0
Density_l = 0.005
PressureClosureMode = 1
ForceFixedPointMode = 2
PhaseAdvectionVelocityMode = 2
ForceDensityClosureMode = 2
FmuStressClosureMode = 2
vtk_field_set = b35split
```

## Evidence

`L0_full` still produced the first force/rho spike at step 15:

```text
ForceOverRhoNorm = 8.854349865443383e5
```

`L3_noPressure` retained essentially the same onset:

```text
ForceOverRhoNorm = 8.690e5 class, step 15
```

`L1_noFmu` and `L2_noSurf` did not show the same 20-step onset. This means
the failure is not explained by pressure alone. It also means the unstable
numerator needs both the stress/viscous contribution and the surface-force
chain, or a coupled term that depends on both.

The co-located step-15 `L0_full` evidence showed:

```text
FtotalNorm = 4427.178927524575
GradPhiNorm = 0.13397463687642877
ReplayMu = -6.0288585078271357e-05
FsurfNorm = 8.077141293655088e-06
```

So the large `ForceOverRho` value was not caused by a large `mu`, a large
`gradPhi`, or a large `Fsurf` at that location. The likely branch moved toward
stress/F_mu numerator construction, force assembly, or a denominator/time-level
interaction.

## Code Anchors

The relevant current path in
`third_party/tclb_snapshots/stage17B_diffuse_solid_shadow/models/multiphase/d3q27_pf_velocity/Dynamics.c.Rt`
is:

```text
calcMu(C)
calcGradPhi()
calc_Fp(...)
calc_Fs(mu, gradPhi_force)
stage14_fmu_from_stress(...)
F_total = F_surf + F_pressure + F_body + F_mu
ReplayForceOverRho = F_total / force_rho_eff
```

B35 did not modify this write path. It only emitted shadow fields under:

```text
Stage14B35CoupledNumeratorDiagnosticsMode
```

## Decision

B35 is useful as a branch-selection diagnostic, but it is not a repair.

Next implication:

```text
Do not tune contact angle or curved-wall wetting.
Do not promote pressure removal as a fix.
Do not promote zero-F_mu or zero-Fsurf as a physical fix.
Proceed to a first-bad ledger with full stress/F_mu co-located fields.
```
