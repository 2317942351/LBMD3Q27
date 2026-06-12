# PRE 2025 Sphere Stage8c Local-Transfer Shadow Case

Status: `runtime_sanity / exploratory_not_validation`.

This directory contains the public XML and metadata for the Stage8c z48 sphere
local-transfer and shadow diagnostic. It is not a PRE reproduction case and
does not claim validation.

## Geometry And Settings

```text
domain = 80 x 80 x 180
solid sphere center = (40, 40, 48)
solid sphere radius = 24
drop center = (40, 40, 96)
drop radius = 24
bottom gap = 24 lu
outer/default radAngle = 90 deg
SolidSphere radAngle = 11 deg
M = 0.1
IntWidth = 6
Stage8OperatorMode = 1
Stage8UseLocalWallAngle = 1
Stage8UseWallGeomNormal = 1
Stage8NormalDotMin = 0.25
Stage8MaxGradDelta = 0.25
```

`Stage8OperatorMode=1` is shadow-only. It calculates the Stage8c candidate and
diagnostics without writing the corrected gradient into the solver state.

## Files

```text
manifest.json
theta030_shadow/case.xml
theta030_shadow/case_params.json
```

The matching public artifact is:

```text
artifacts/pre2025_sphere_stage8c_local_transfer_shadow_20260612
```

Raw solver fields remain on HM570 under:

```text
/mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_stage8c_local_transfer_shadow_20260612
```

## Regeneration

The case can be regenerated with:

```bash
python scripts/make_pre2025_sphere_stage8c_gate_cases.py --force
```

The local-transfer audit script is:

```bash
python scripts/pre2025_sphere_stage8c_local_transfer_audit.py --case-root <remote_case_root> --out-dir <analysis_dir>
```

The HM570 batch helper is:

```bash
scripts/hm570_run_pre2025_sphere_stage8c_shadow_20260612.sh
```

