# PRE 2025 Sphere Stage8d Shadow Limiter Attribution Case

Status: `runtime_sanity / exploratory_not_validation`.

This directory contains the public XML and metadata for the Stage8d z48 sphere
shadow-only limiter attribution case. It is not a PRE reproduction case and
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
Stage8MaxGradDelta = 0.25
Stage8DiagSphereCenter = (40, 40, 48)
Stage8DiagSphereRadius = 24
```

`Stage8OperatorMode=1` is shadow-only. It calculates attribution diagnostics
without writing corrected gradients into the solver state.

## Files

```text
manifest.json
theta030_shadow/case.xml
theta030_shadow/case_params.json
```

The matching public artifact is:

```text
artifacts/pre2025_sphere_stage8d_shadow_limiter_attribution_20260612
```

Raw solver fields remain on HM570 under:

```text
/mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_stage8d_shadow_limiter_attribution_20260612
```

