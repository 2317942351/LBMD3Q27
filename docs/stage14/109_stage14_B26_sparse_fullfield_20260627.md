# Stage14-B26 Sparse Full-Field Closure Audit

Date: 2026-06-27

Branch: `work/phasefield-c-reference-20260623`

Run root: `/mnt/usb1t/RUNS/runs/stage14_B26_sparse_fullfield_v2_20260627`

Local light artifacts: `artifacts/stage14_B26_sparse_fullfield_v2_20260627/`

Binary:

```text
2a5729a8041dcd3db150149b623764862778d799cd657b55ab43fc2cab47cef6
/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
```

## Scope

B26 is a diagnostic-only sparse full-field audit for the `wall_60to30_10`
short-onset problem at density ratio 200:

```text
Density_h = 1.0
Density_l = 0.005
PressureClosureMode = 1
ForceFixedPointMode = 2
PhaseAdvectionVelocityMode = 1
iterations = 12
GPU = P100, CUDA_VISIBLE_DEVICES=1
```

This is not a contact-angle validation, not a curved-wall validation, and not a
physics fix.

## Why B26 Was Re-Run

The first B26 attempt used `--vtk-field-set full`. That field set did not
include all B22 velocity-producer fields, so the analyzer could only report:

```text
b22_primary_branch = not_available
b26_conclusion = unresolved
```

That was a field-selection failure, not physics evidence. B26 v2 adds
`--vtk-field-set b26`, which combines full replay fields with the complete B22
field set and enforces required-field presence.

## Execution Status

Final status:

```text
stage14_B26.status: OVERALL_RC=0
digest.status: DIGEST_RC=0
M0_FD0_full_analyzer.status: ANALYZER_RC=0
M0_FD1_full_rescue_analyzer.status: ANALYZER_RC=0
```

The original `M0_FD1_full` analyzer path failed after the heavy summary/analyzer
workflow was killed and VTI files were deleted by the old wrapper. This path is
retained in the artifacts as failure history only. The valid FD1 evidence is
from `M0_FD1_full_rescue`, which reran the case and used the optimized array
selection analyzer before deleting regenerable VTI/PVTI files.

## Main Result

`b26_sparse_digest.json` now classifies both FD0 and FD1 as stress-time-level
supported:

```text
b26_conclusion = stress_time_level_priority
M0_FD0_full classification = stress_time_level_supported
M0_FD1_full classification = stress_time_level_supported
fd1_momentum_delay_steps = 0
```

Key numbers:

| probe | ForceDensityClosureMode | B18 stress amp onset | B22 momentum onset | B22 m0 onset | B21 heq Mach onset |
|---|---:|---:|---:|---:|---:|
| M0_FD0_full | 0 | step 1 | step 11 | step 12 | step 12 |
| M0_FD1_full | 1 | step 1 | step 11 | step 12 | step 12 |

At the B22 momentum onset, both probes show nearly identical force and stress
levels:

| probe | StressPostOverPre | StressPostForceNorm | StressPreForceNorm | Ftotal | ForceOverRho | rho_eff_min |
|---|---:|---:|---:|---:|---:|---:|
| M0_FD0_full | 13.2708 | 9.30005 | 0.715044 | 0.028592 | 5.31818 | 0.004994 |
| M0_FD1_full | 13.2708 | 9.30005 | 0.715044 | 0.028592 | 5.31818 | 0.005000 |

The density-floor probe does not delay the velocity onset. Therefore B26 does
not support a denominator-first repair as the next priority. The earliest
diagnostic signature is the post-force stress shadow becoming much larger than
the pre-force stress shadow before the velocity and phase-advection markers
cross.

## Code Path Implicated

The implicated TCLB path remains:

```text
Dynamics.c.Rt
  calc_Fs(mu, gradPhi)
  fixed-point stress reconstruction from new_g
  F_mu = (0.5 - tau) * (Density_h - Density_l) * stress * gradPhi
  F_total = F_surf + F_pressure + F_body + F_mu
  U = m0 + 0.5 * F_total / rho_eff
  h equilibrium/update consumes selected phase-advection velocity
```

B26 specifically points to the stress reconstruction / post-force shadow path,
not to a standalone low-density denominator clamp.

## Changes Made For B26

- `scripts/stage14/stage14_s2_replay_smoke.py`
  - Added `b26` VTK field set.
  - Added required-field gate for B26.
- `scripts/stage14/stage14_b17_onset_mask_argmax.py`
  - Added VTK cell-data array selection to avoid loading unused huge arrays.
- `scripts/stage14/stage14_b26_sparse_digest.py`
  - Added B26-specific sparse digest and classification.
  - Compares B18 stress onset against the earliest force, velocity, or phase
    onset instead of requiring a B22 force-over-rho threshold.
- `scripts/stage14/run_stage14_b26_sparse_fullfield_remote.sh`
  - Runs FD0/FD1 with `--vtk-field-set b26`.
- `scripts/stage14/run_stage14_b26_fd1_rescue_remote.sh`
  - Reruns FD1 without the heavy summary bottleneck and only deletes VTI after
    analyzer success.

No solver physics was changed for B26.

## Next Gate

B27 must run the `stress` branch, not the `denominator` branch.

Required B27 stress probes:

```text
S0_legacy_stress
S1_density_floor_stress
S2_noFmu_stress
S3_noSurf_stress
S4_noMomentum_stress
```

Purpose:

```text
Confirm whether the stress amplification is tied to post-force velocity,
F_mu feedback, surface-force input, or generic force insertion.
```

B28 must not be implemented until B27 selects a single repair branch.

