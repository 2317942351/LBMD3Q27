# Stage14 B35-B41 GitHub Review Handoff

Date: 2026-06-28

Branch: `work/phasefield-c-reference-20260623`

Purpose: give the next AI or engineer a narrow review entry point after the
B35-B40 force/stress closure campaign.

## Current Conclusion

The active root-cause branch is:

```text
stress/F_mu time-level and fixed-point feedback
```

The current evidence does not support returning to:

```text
WallGhost tuning
curved compact-stencil write enablement
force-over-rho limiter promotion
gradPhi limiter promotion
static contact-angle validation
dynamic impact
```

## Evidence Chain

Read in this order:

```text
docs/stage14/125_stage14_B35_coupled_numerator_split_20260628.md
docs/stage14/126_stage14_B36_force_over_rho_cap_rejected_20260628.md
docs/stage14/127_stage14_B37_grad_phi_cap_rejected_20260628.md
docs/stage14/129_stage14_B38_first_bad_force_ledger_result_20260628.md
docs/stage14/131_stage14_B39_fmu_stress_mode_matrix_result_20260628.md
docs/stage14/133_stage14_B40_stress_construction_audit_result_20260628.md
docs/stage14/134_stage14_B41_preforce_stress_plan_20260628.md
```

The B40 result is the current narrowest evidence:

```text
case = wall_60to30_10
step = 13
mask = low_rho
ijk = [93, 1, 5]
ForceOverRhoNorm = 2636.4146763472127
FmuNorm = 14.492372866456925
FpressureNorm = 0.022145923403073742
FsurfNorm = 8.358087817285956e-06
StressPreForceNorm = 383.3219828909969
StressPostForceNorm = 2029121.044003016
StressPostOverPreRatio = 5293.515985437302
first PhaseFromH out-of-bounds = step 20
```

Interpretation:

```text
force/stress becomes nonphysical before phase leaves bounds.
```

## Code Review Anchors

Main source snapshot:

```text
third_party/tclb_snapshots/stage17B_diffuse_solid_shadow/models/multiphase/d3q27_pf_velocity/
```

Important files:

```text
Dynamics.R
Dynamics.c.Rt
```

Important code areas:

```text
Dynamics.R:
  FmuStressClosureMode
  Stage14B18ClosureDiagnosticsMode
  Stage14B35CoupledNumeratorDiagnosticsMode
  Stage14B36ForceOverRhoLimiterMode
  Stage14B37GradPhiCapMode
  Stage14B40StressAuditMode

Dynamics.c.Rt:
  stage14_b40_stress_audit_active()
  stage14_fmu_from_stress_scaled()
  incoming/pre-force stress setup around the b28/b40 blocks
  force fixed-point stress -> F_mu loop
  post-force stress shadow construction
```

The code changes are diagnostic-heavy and default-off unless a stage script
explicitly enables the probe settings.

## Runtime Artifact Layout

Committed artifact roots:

```text
artifacts/stage14_B35_coupled_numerator_split_20260628/
artifacts/stage14_B36_force_over_rho_cap_20260628/
artifacts/stage14_B37_grad_phi_cap_20260628/
artifacts/stage14_B38_first_bad_force_ledger_20260628/
artifacts/stage14_B38_first_bad_force_ledger_retry_20260628/
artifacts/stage14_B39_fmu_stress_mode_matrix_20260628/
artifacts/stage14_B40_stress_construction_audit_20260628/
```

These contain lightweight logs, status files, summaries, mask statistics, and
digest outputs.

Large raw per-node trace files named:

```text
*_argmax_trace.json
```

are intentionally ignored by `.gitignore` and are not forced into Git. The
remote run roots and committed summaries preserve the review path without
turning the branch into a raw VTI/trace archive.

## Server State After Reboot

Checked on 2026-06-28 after server reboot:

```text
host = HM570
ssh = yuan@192.168.1.16 via C:\Users\yuanz\Desktop\lbm-new\.ssh\id_ed25519
/mnt/usb1t available = about 248G
P100 GPU 1 memory used = 6 MiB
P100 GPU 2 memory used = 6 MiB
current binary sha256 = de2e77d723f5a52dfb2734e0c8fe9eef15caa092fbc91e1cf6367bdb3bcd4c43
```

B40 final remote root:

```text
/mnt/usb1t/RUNS/runs/stage14_B40_stress_construction_audit_final_20260628
```

## Next Work

Implement B41:

```text
FmuStressClosureMode = 3
```

as a default-off candidate that computes active `F_mu` from a pre-force or
consistent incoming non-equilibrium stress source.

First gate:

```text
wall_60to30_10
Density_h = 1.0
Density_l = 0.005
iterations = 20
vtk_period = 1
P100 only: CUDA_VISIBLE_DEVICES=1
```

Success means:

```text
the step-13 ForceOverRho/stress amplification is removed or substantially
delayed without earlier PhaseFromH failure.
```

Success does not mean:

```text
contact-angle validation passed
curved-wall wetting solved
dynamic impact ready
```
