# Stage14 B41-B42 Stress Source and Decomposition Results

Date: 2026-06-28

Branch: `work/phasefield-c-reference-20260623`

Status: B41 and B42 diagnostic gates complete. This is not a solver repair,
not contact-angle validation, and not dynamic-impact readiness.

## Runtime Summary

B41:

```text
remote root = /mnt/usb1t/RUNS/runs/stage14_B41_stress_source_audit_20260628
local artifacts = artifacts/stage14_B41_stress_source_audit_20260628
binary sha256 = de2e77d723f5a52dfb2734e0c8fe9eef15caa092fbc91e1cf6367bdb3bcd4c43
status = OVERALL_RC=0, VERDICT=b41_stress_source_audit_complete
```

B42:

```text
remote root = /mnt/usb1t/RUNS/runs/stage14_B42_stress_decomposition_20260628
local artifacts = artifacts/stage14_B42_stress_decomposition_20260628
binary sha256 = d8e3295335f2c43d9b825e9082f4be7a7cfbf265b48e0d4f15a1a5aaec8a70de
status = OVERALL_RC=0, VERDICT=b42_stress_decomposition_complete
```

Both gates used:

```text
case = wall_60to30_10
Density_h = 1.0
Density_l = 0.005
iterations = 20
vtk_period = 1
gpu = P100, CUDA_VISIBLE_DEVICES=1
PressureClosureMode = 1
ForceDensityClosureMode = 2
ForceFixedPointMode = 2
PhaseAdvectionVelocityMode = 2
```

## B41 Finding

B41 reused B40 stress-source diagnostics and ranked possible stress sources at
the known focus point:

```text
focus step = 13
mask = low_rho
legacy F/rho = 2636.41
```

Primary B41 ranking:

| candidate | stress | F_mu | F/rho | F/rho / legacy | decision |
| --- | ---: | ---: | ---: | ---: | --- |
| incoming_raw_population | 138.671 | n/a | n/a | n/a | not a non-equilibrium stress |
| legacy_relaxed_moment | 383.322 | 14.4924 | 2636.41 | 1.00 | baseline |
| raw_moment_preforce | 17562.5 | 39.9641 | 7596.83 | 2.88 | worse |
| bgk_pop_neq_preforce | 17562.5 | 49.9552 | 9495.99 | 3.60 | worse |
| incoming_neq_preforce | 17562.5 | n/a | n/a | n/a | compare only |
| post_force_shadow | 2.02912e6 | n/a | n/a | n/a | reject |

B41 verdict:

```text
b41_no_better_implementable_candidate
```

Meaning:

```text
Do not directly promote raw_moment_preforce or bgk_pop_neq_preforce as active
B42 stress modes. They amplify the already bad F/rho signal.
```

## B42 Finding

B42 added default-off, shadow-only isotropic/deviatoric decomposition fields:

```text
Stage14B42StressDecompositionMode = 0 by default
```

The active solver path was unchanged. The B42 run enabled:

```text
Stage14B40StressAuditMode = 1
Stage14B42StressDecompositionMode = 1
```

Focus-point decomposition:

| source | isotropic | deviatoric | dev F_mu | dev F/rho | dev F/rho / legacy |
| --- | ---: | ---: | ---: | ---: | ---: |
| legacy | n/a | 362.112 | 11.6735 | 2124.28 | 0.806 |
| raw | n/a | 14322.6 | 71.278 | 13548.0 | 5.139 |
| bgk | n/a | 14322.6 | 89.0975 | 16935.2 | 6.424 |
| post | n/a | 1.76616e6 | n/a | n/a | n/a |

B42 verdict:

```text
b42_no_deviatoric_candidate
```

Meaning:

```text
Removing isotropic trace from the stress is insufficient. The legacy
deviatoric shadow still has F/rho = 2124.28 > 1000, and raw/BGK deviatoric
sources are much worse. Isotropic leakage is not the primary root cause.
```

## Code Changes in B42

Modified:

```text
third_party/tclb_snapshots/stage17B_diffuse_solid_shadow/models/multiphase/d3q27_pf_velocity/Dynamics.R
third_party/tclb_snapshots/stage17B_diffuse_solid_shadow/models/multiphase/d3q27_pf_velocity/Dynamics.c.Rt
scripts/stage14/stage14_s2_replay_smoke.py
scripts/stage14/stage14_b17_onset_mask_argmax.py
```

New scripts:

```text
scripts/stage14/run_stage14_b41_stress_source_audit_remote.sh
scripts/stage14/stage14_b41_stress_source_rank.py
scripts/stage14/compile_stage14_b42_stress_decomposition_remote.sh
scripts/stage14/run_stage14_b42_stress_decomposition_remote.sh
scripts/stage14/stage14_b42_stress_decomposition_rank.py
```

The B42 code is shadow-only:

```text
no change to F_total
no change to h update
no change to g update
no change to WallGhost / PhaseF write
legacy defaults unchanged
```

## Decision for B43

B43 should not continue stress-source swapping. The next branch is:

```text
stress-scale / discrete forcing coefficient / force coupling derivation
```

The specific question is whether the active formula:

```text
F_mu = (0.5 - tau) * (Density_h - Density_l) * stress * gradPhi
```

is consistent with the stress object actually used:

```text
stress = second moment of solve(M) %*% ((m0 - EQ$Req) * Omega)
```

B43 must derive and test, as shadow first:

```text
legacy scale                 = (0.5 - tau)
BGK-like scale               = (0.5 - tau)/tau
moment-wise MRT scale        = derived from the stress moment relaxation rates
force-coupling sign/half-step factor consistency
```

B43 stop rule:

```text
If no coefficient/forcing candidate can reduce step-13 F/rho below threshold
without a limiter, the next root branch must be the force coupling formula
itself, not WallGhost or contact-angle tuning.
```
