# Phase-Field Rebuild Execution Plan

Date: 2026-06-23

This note records the first implementation work after the rebuild baseline tag.
The goal is to create a clean, auditable starting point before any new TCLB
solver physics edit.

## Current Branch

```text
work/phasefield-c-reference-20260623
```

Parent baseline:

```text
baseline/phasefield-rebuild-20260623
```

## Why This Branch Exists

The immediate risk is not only the wetting formula. The larger risk is a
semantic mismatch between explicit C-array LBM logic and TCLB's generated GPU
execution model:

```text
AddDensity streams automatically
AddStage load/save controls time level
wall and solid fields are not passive unless explicitly isolated
periodic paths can transport biased ghost values
postprocessed field mass is not automatically population mass
```

Therefore the first branch creates two independent anchors:

```text
1. explicit-array C++ phase-field reference scaffold
2. source-level TCLB execution-semantics audit script
```

These are prerequisites for changing the TCLB solver again.

## Implemented In This Branch

### C++ reference scaffold

Path:

```text
reference_solvers/phasefield_d3q27_c/
```

Files:

```text
phasefield_reference.cpp
Makefile
README.md
```

Current scope:

```text
D3Q27 TCLB velocity order
D3Q27 weights and opposite-link table
explicit scalar field storage
solid sentinel kept separate from passive wall ghost
isotropic gradient manufactured-field test
isotropic Laplace manufactured-field test
plane/cylinder/sphere signed-distance and normal tests
geometric wall ghost sign tests for theta 30/90/150
VTK demo output
CSV self-test diagnostics
```

Current non-scope:

```text
no production LBM collision yet
no Cahn-Hilliard replacement yet
no high-density-ratio tuning
no dynamic impact
```

### TCLB semantics audit

Path:

```text
scripts/audit_tclb_execution_semantics.py
```

It extracts:

```text
AddDensity names, groups, dx/dy/dz, streaming status
AddField names, groups, stencil depth
AddStage order and function names
AddSetting names
key wetting/ghost/sentinel source occurrences
risk checklist entries
```

Expected output:

```text
artifacts/tclb_execution_semantics_audit_20260623/
```

## Remote Background Audit

A non-destructive remote audit script was added:

```text
scripts/remote/remote_space_audit.sh
```

Started on:

```text
yuan@192.168.1.16
```

Output:

```text
/home/yuan/lbm2026_logs/remote_space_audit_20260623_bg/
/home/yuan/lbm2026_logs/remote_space_audit_20260623_bg.tar.gz
```

Immediate evidence from the audit:

```text
P100 GPU 1 and 2 are visible and idle
/mnt/usb1t is mounted and contains /mnt/usb1t/RUNS/runs
/mnt/usb1t usage is high, about 87%
/mnt/usb1t/RUNS/runs uses about 217G
/home/yuan/data_sdb/RUNS/runs uses about 94G
```

The cleanup manifest is intentionally conservative. It labels directories with
case logs, XML, summary JSON, or shape-angle JSON as `KEEP`. It does not delete
anything.

## Cleanup Policy

Do not delete a whole run directory unless all three are true:

```text
1. its raw fields are replaced by committed or archived metrics/figures/logs
2. it is not referenced by docs, reports, or a current gate
3. the user explicitly approves the candidate-delete manifest
```

The next cleanup pass should classify large raw field files:

```text
KEEP: current gate evidence, unique failure evidence, final frames, logs, XML
ARCHIVE: reproducible but expensive outputs worth compressing
DELETE_CANDIDATE: duplicate raw VTI/PVTI/PRI with retained JSON/PNG/log evidence
```

The script now writes:

```text
raw_field_cleanup_candidates.csv
raw_field_cleanup_summary.csv
```

These files are still not deletion authorization. They are the evidence needed
to ask for approval with a bounded list of raw fields and expected recovered
space.

## Next Code Step

Do not edit the TCLB solver physics until these checks pass:

```text
make test in reference_solvers/phasefield_d3q27_c
python scripts/audit_tclb_execution_semantics.py on the active model snapshot
review the stage order and passive ghost evidence
decide the exact C-to-TCLB replay fields for step 0, 1, 2, 5, 10
```

Only after this should the solver branch implement diffuse-solid or compact
stencil changes.
