# Current Progress And Next Solver Targets

Date: 2026-06-23

Status: `audit_baseline_extension / exploratory_not_validation`.

## What Was Done

### 1. New working branch

```text
work/phasefield-c-reference-20260623
```

This branch starts from:

```text
baseline/phasefield-rebuild-20260623
```

It is intentionally separated from the previously pushed audit baseline.

### 2. Remote server audit

Server:

```text
yuan@192.168.1.16
```

Audit output:

```text
/home/yuan/lbm2026_logs/remote_space_audit_20260623_bg/
/home/yuan/lbm2026_logs/remote_space_audit_20260623_rawfield_pass_v2/
```

Local summaries:

```text
artifacts/remote_space_audit_20260623/
```

Current server facts:

```text
Tesla P100 GPU 1: visible, idle, about 6 MiB used
Tesla P100 GPU 2: visible, idle, about 6 MiB used
/mnt/usb1t/RUNS/runs exists, about 217G
/home/yuan/data_sdb/RUNS/runs exists, about 94G
/home/yuan/runs is a dangling symlink to /media/yuan/DATA500/runs
/mnt/win_sda2/RUNS/runs is currently missing
/home/yuan/src/TCLB_lbm2026_compile_lane exists
```

Raw field cleanup candidate:

```text
1400 VTI/PVTI/PRI files
332139025976 bytes
classification = ARCHIVE_OR_DELETE_RAW_CANDIDATE
```

Grouped review manifest:

```text
artifacts/remote_space_audit_20260623/raw_field_cleanup_by_run.csv
29 run directories
309.33 GiB
approval_status = NEEDS_USER_APPROVAL
```

Largest candidate groups at the time of this audit:

```text
/home/yuan/data_sdb/RUNS/runs/stage13_flat_wall_runtime_20260616 -> 68.72 GiB
/mnt/usb1t/RUNS/runs/stage15C3_cap0p5_20260619 -> 29.05 GiB
/mnt/usb1t/RUNS/runs/stage15FSm1_revalidate_20260619 -> 29.05 GiB
/home/yuan/data_sdb/RUNS/runs/stage12_validation_20260615 -> 22.00 GiB
/mnt/usb1t/RUNS/runs/stage15C4_Msweep_20260619 -> 17.43 GiB
```

No deletion was performed.

### 2b. P100 smoke run

A short run-chain smoke was launched after the audit:

```text
script: scripts/stage18/run_stage18_semantics_smoke_remote.sh
remote script: /home/yuan/run_stage18_semantics_smoke_remote.sh
run root: /mnt/usb1t/RUNS/runs/stage18_semantics_smoke_20260623
follow-up root: /mnt/usb1t/RUNS/runs/stage18_semantics_smoke_zaxis_20260623
cases: plane_theta090_100, cylinder_theta090_old_axis_100, cylinder_theta090_z_axis_100
GPUs: P100 device 1 and P100 device 2
iterations: 100
purpose: runtime chain only
```

This smoke is not contact-angle validation and must not be used as evidence
that the solver physics is fixed.

Result:

```text
flat wall 100-step smoke completed
old stage9 cylinder axis=0 template triggered P NaN
z-axis cylinder template completed 100 steps
```

Detailed record:

```text
docs/stage14/60_stage18_p100_semantics_smoke_20260623.md
artifacts/stage18_semantics_smoke_20260623/
```

### 3. C++ phase-field reference scaffold

Path:

```text
reference_solvers/phasefield_d3q27_c/
```

Verification:

```text
server: yuan@192.168.1.16
compiler: /usr/bin/g++
command: make test
result: checks=96 failures=0
```

Implemented checks:

```text
D3Q27 TCLB velocity order
D3Q27 weights
opposite-link involution
isotropic gradient on manufactured linear field
isotropic Laplace on manufactured quadratic field
plane/cylinder/sphere signed-distance and normals
geometric wall ghost direction for theta 30/90/150
passive ghost blocks solid sentinel from stencil reads
passive ghost does not overwrite solid phi
```

This is not yet a full phase-field LBM solver. It is a replay and semantics
anchor.

### 4. TCLB execution-semantics audit

Script:

```text
scripts/audit_tclb_execution_semantics.py
```

Output:

```text
artifacts/tclb_execution_semantics_audit_20260623/
```

Current extraction:

```text
densities = 54
fields = 88
stages = 20
risks = 13
```

High-risk marker:

```text
SPECIAL_POINT_MAGIC
```

This confirms that special-point magic values still require explicit proof that
they cannot enter phase gradient, Laplace, chemical potential, or force paths.

## Why This Matters For The Solver

The current project failure mode is consistent with a TCLB implementation-layer
problem, not proof that TCLB itself cannot solve wetting:

```text
streaming density groups are not C current arrays
wall ghosts must be passive fields, not active streamed populations
stage save/load order determines the time level of PhaseF, WallGhost, gradPhi, mu
solid sentinel and special-point values must be impossible to read in stencils
per-link bounceback/QIBB semantics must be verified before curved walls are trusted
```

Therefore the next solver edit should not be another isolated wetting formula
swap. It should modify the solver only after the C++ reference and TCLB audit
define the expected field timeline.

## What Has Not Been Done

```text
No new TCLB solver physics was changed in this branch.
No new static contact-angle case was run.
No dynamic impact case was run.
No remote files were deleted.
No C-to-TCLB field replay has been completed.
No diffuse-solid curved-wall implementation has been added yet.
```

## Next Solver Targets

### Target S1: current-field cache and ghost timeline

Audit and, if needed, modify the TCLB model so these are explicit:

```text
PhaseF producer stage
WallGhost producer stage
gradPhi producer stage
mu producer function
force consumer stage
which fields are loaded by BaseIter
which fields are saved after calcWall_CA/calcWall
```

Deliverable:

```text
docs/stage14/60_tclb_field_timeline_audit_20260623.md
```

### Target S2: C-to-TCLB step replay

Use the C++ scaffold to define expected values for:

```text
step 0: phi, wall ghost, gradPhi, lapPhi, mu
step 1: phi, gradPhi, mu, force
step 2/5/10: mass, max|gradPhi|, max|mu|, max|u|
```

Deliverable:

```text
reference_solvers/phasefield_d3q27_c/replay_cases/
scripts/stage18/run_replay_gate.sh
```

### Target S3: passive curved-wall ghost implementation

Only after S1/S2:

```text
implement diffuse-solid or compact-stencil curved-wall ghost as a passive field
keep sharp solid/staircase populations out of the phase stencil
make the write path shadow-only first
block direct q_s writes on curved wall until shadow metrics pass
```

Deliverable:

```text
TCLB source patch plus shadow-only cylinder gate
```

### Target S4: compute gates on P100

Run only after source/audit gates:

```text
flat wall theta 30/90/150 regression
cylinder shadow theta 60/90/120
cylinder write gate only after shadow passes
sphere gate only after cylinder passes
dynamic impact preflight only after static curved gates pass
```

## Cleanup Next Step

Before deleting anything:

```text
download or inspect raw_field_cleanup_candidates.csv
group candidates by run directory
keep final frames and unique failure evidence
confirm docs/artifacts retain JSON/PNG/log/XML proof
ask the user to approve a bounded delete manifest
```

The current candidate size is large enough to matter, but deletion without that
manifest would damage auditability.
