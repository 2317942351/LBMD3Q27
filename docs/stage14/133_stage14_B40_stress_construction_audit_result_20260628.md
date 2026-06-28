# Stage14-B40 Stress Construction Audit Result

Date: 2026-06-28

Branch: `work/phasefield-c-reference-20260623`

Status: diagnostic complete. This is not a solver repair, not contact-angle
validation, and not dynamic-impact readiness.

## Runtime

Remote root:

```text
/mnt/usb1t/RUNS/runs/stage14_B40_stress_construction_audit_final_20260628
```

Local artifact root:

```text
artifacts/stage14_B40_stress_construction_audit_20260628
```

Binary:

```text
de2e77d723f5a52dfb2734e0c8fe9eef15caa092fbc91e1cf6367bdb3bcd4c43
/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
```

Run status:

```text
OVERALL_RC=0
VERDICT=b40_stress_construction_audit_complete
```

Case and settings:

```text
case = wall_60to30_10
Density_h = 1.0
Density_l = 0.005
iterations = 20
vtk_period = 1
vtk_field_set = b40stress
PressureClosureMode = 1
ForceFixedPointMode = 2
PhaseAdvectionVelocityMode = 2
ForceDensityClosureMode = 2
ForceDensityRhoFloor = 0.005
Stage14B18ClosureDiagnosticsMode = 1
Stage14B40StressAuditMode = 1
```

The remote run deleted VTI files after analysis. The committed artifact set is
lightweight JSON/CSV/log evidence only.

## Code Path Under Audit

The active stress/F_mu path is in:

```text
third_party/tclb_snapshots/stage17B_diffuse_solid_shadow/models/multiphase/d3q27_pf_velocity/Dynamics.c.Rt
```

The force fixed-point loop constructs stress from the relaxed moment residual:

```text
lines 3687-3703:
  m[selR] = (m0 - EQ$Req)[selR] * Omega
  new_g = solve(M) %*% m
  stress = sum(e_i e_j new_g)
  F_mu = (0.5 - tau) * (Density_h - Density_l) * stress * gradPhi_force
```

The post-force shadow stress is constructed after:

```text
lines 4050-4098:
  U = m0[1:3] + 0.5 * F_total / rho_eff
  stress_post_force_shadow = stress built from the same moment residual while
                             using this post-force velocity in EQ$Req
```

`Dynamics.R` keeps B40 default-off:

```text
Stage14B40StressAuditMode = 0
```

## Primary Finding

B40 narrowed the short-run instability to a stress time-level / fixed-point
feedback branch:

```text
Analyzer branch = stress_timelevel_or_fixed_point_feedback
B40 branch      = post_force_shadow_amplification
```

The selected first bad force-over-rho node is:

```text
case = wall_60to30_10
step = 13
mask = low_rho
ijk  = [93, 1, 5]
```

Co-located values:

```text
PhaseField                  = 0.0005735800909220209
Rho                         = 0.005570712190467411
ReplayForceRhoEffective     = 0.005505073722284272
GradPhiNorm                 = 0.13667178422416873
FsurfNorm                   = 8.358087817285956e-06
FpressureNorm               = 0.022145923403073742
FmuNorm                     = 14.492372866456925
FtotalNorm                  = 14.513657155803632
ForceOverRhoNorm            = 2636.4146763472127
StressPreForceNorm          = 383.3219828909969
StressPostForceNorm         = 2029121.044003016
StressPostMinusPreNorm      = 2028737.722020125
StressPostOverPreRatio      = 5293.515985437302
```

Important timing:

```text
first ForceOverRho threshold crossing = step 13
first large post-force stress          = step 13
first large F_mu                       = step 14
first PhaseFromH out-of-bounds         = step 20
```

Therefore phase loss is downstream in this probe. The earliest actionable
signal is the force/stress chain, not WallGhost or contact-angle response.

## B40 Stress Candidate Evidence

B40 compared several stress constructions in the same run:

```text
B40StressMomentRawNorm
B40StressMomentRelaxedNorm
B40StressIncomingRawNorm
B40StressIncomingNeqPreNorm
B40StressBGKPopNeqPreNorm
B40StressPostForceNorm
```

Key onsets:

```text
first_b40_stress_match_delta_onset = None
```

This means the B40 relaxed-moment shadow matched the legacy stress path well
enough for the audit to be trusted.

Other onsets:

```text
B40StressMomentRawNorm          crosses at step 13, low_rho, 1.756e4
B40StressIncomingNeqPreNorm     crosses at step 13, low_rho, 1.756e4
B40StressBGKPopNeqPreNorm       crosses at step 13, low_rho, 1.756e4
B40StressPostForceNorm          crosses at step 13, low_rho, 2.029e6
B40FmuMomentRelaxedLegacyNorm   crosses at step 14, low_rho, 6.434e4
B40ForceOverRhoMomentRelaxedLegacyNorm crosses at step 13, low_rho, 2.636e3
```

The strongest signal is not a simple missing limiter:

```text
post-force stress = 2.029e6
pre-force stress  = 3.833e2
amplification     = 5.293e3
```

B36 force-over-rho cap and B37 gradPhi cap were already rejected. B39 showed
that existing `FmuStressClosureMode = 0, 1, 2` choices are not sufficient.

## Postprocessing Notes

Two analyzer issues were fixed before the final B40 run:

```text
1. B40 onset variables were added to stage14_b17_onset_mask_argmax.py.
2. TARGET_FIELDS now automatically includes all threshold fields, preventing
   B40 fields from being silently marked not_available.
```

`stage14_s2_replay_smoke.py` was also updated to include fields whose names
begin with `B40`.

One generated digest file still has the historical title:

```text
Stage14-B38 First-Bad Force Ledger Digest
```

The file content and artifact directory are B40 stress-construction evidence.
This title is a naming carryover, not a runtime mismatch.

## Teacher MCP Review

Teacher MCP was used after B40 with direct code anchors and B40 numeric
evidence.

Result:

```text
status = PASS
confidence = 0.90
```

Teacher agreed that B41 should prioritize a default-off pre-force or consistent
non-equilibrium stress candidate for `F_mu`. Teacher also warned that this must
remain a candidate until later contact-angle and dynamic gates are passed.

## Decision

The next branch is B41:

```text
stress time-level / fixed-point ordering repair candidate
```

The next step is not:

```text
curved-wall WallGhost tuning
compact-stencil write enablement
force-over-rho limiter promotion
gradPhi limiter promotion
static contact-angle validation
dynamic impact
```

## Claim Limits

Allowed:

```text
B40 stress construction audit completed.
B40 localized the next actionable branch to stress/F_mu time-level and
fixed-point feedback.
```

Forbidden:

```text
contact-angle validation passed
curved-wall wetting solved
dynamic impact ready
B40 fixed the solver
```
