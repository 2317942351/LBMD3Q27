# Stage17B-B2 Sphere Shadow 1000-Step Gate

Date: 2026-06-24

Status: `PASS_STAGE17B_B2_SHADOW_DIAGNOSTICS`. This is a sphere shadow-diagnostics gate only. It is not contact-angle validation and does not authorize any `PhaseF` or `WallGhost` write path.

## Run

```text
run root = /mnt/usb1t/RUNS/runs/stage17B_shadowtheta_sphere_1000_20260624
local cases = cases/diagnostics/stage17B_sphere_shadow_20260624_1000/
local evidence = artifacts/stage17B_B2_shadow_20260624/runtime_spheretheta_1000/
GPU request = CUDA_VISIBLE_DEVICES=1
binary sha256 = 411d72fb9ff45cb799bfda4b6b33a0761ee5903b1e00c484c7578894be766aee
```

Case settings:

```text
iterations = 1000
vtk-period = 500
log-period = 100
legacy sphere radAngle = 90d
Stage17BShadowThetaDeg = 90 / 60 / 120
Stage17BWriteMode = 0
WallCompactStencilMode = 0
```

Sphere geometry:

```text
case.xml global Geometry = 80 x 80 x 120
solid sphere center = (40, 40, 48)
solid sphere radius = 20
SphereCapInit enabled
volume-equivalent liquid radius = 16
```

## Result

| case | frames | status | final near-band cells | final PhaseField nonfinite | ghost below 0 | ghost above 1 | final max NearWallForceOverRhoShadow |
|---|---:|---|---:|---:|---:|---:|---:|
| `sphere_theta090_shadow` | 0, 500, 1000 | `PASS_SHADOW_DIAGNOSTICS` | 7208 | 0 | 0 | 0 | 1.2704281e-05 |
| `sphere_theta060_shadow` | 0, 500, 1000 | `PASS_SHADOW_DIAGNOSTICS` | 7208 | 0 | 0 | 0 | 1.3296177e-05 |
| `sphere_theta120_shadow` | 0, 500, 1000 | `PASS_SHADOW_DIAGNOSTICS` | 7208 | 0 | 0 | 0 | 1.3250519e-05 |

Common pass evidence:

```text
done.status = DONE /mnt/usb1t/RUNS/runs/stage17B_shadowtheta_sphere_1000_20260624 rc=0
all three cases RC=0
expected final VTI step 1000 exists for all cases
analyzer status = PASS_STAGE17B_B2_SHADOW_DIAGNOSTICS
PsiWallGhost remains bounded
PsiNormalAmbiguityFlag near-band fraction remains zero
NearWallForceOverRhoShadow remains below the analyzer limit
```

Remote disk state:

```text
before = /mnt/usb1t free 62G
after  = /mnt/usb1t free 60G
```

No cleanup was required because free space stayed above the 50G threshold.

## TCLB Output-Dimension Note

The generated sphere `case.xml` and run log both confirm the physical/global domain:

```text
Global lattice size: 80x80x120
```

The same run log reports:

```text
Local lattice size: 96x80x120
```

The analyzer reads VTI cell dimensions from the local VTI piece, so `stage17B_shadow_analysis.json` records `dims = [96, 80, 120]`. This is a TCLB local-lattice/output-padding detail, not evidence that the requested physical sphere case became `96x80x120`. Future post-processing must use the case XML or run-log global lattice size for physical geometry, and must not infer physical domain size from VTI local padded dimensions alone.

## Interpretation

This gate shows that Stage17B diffuse-solid sphere shadow fields remain finite and bounded through a 1000-step legacy solver run on P100. The shadow theta sweep does not write back to the physical solver state, so this result only validates diagnostic-field stability and sphere near-wall field coherence for the first short sphere gate.

The result does not prove that the contact angle is correct. It only supports extending the same sphere shadow-only cases to 2000 steps and, if stable, to 12000 steps.

## Claim Limits

Allowed:

```text
Stage17B-B2 sphere shadow diagnostics passed to 1000 steps.
The next permitted step is sphere shadow-only 2000 steps.
```

Forbidden:

```text
contact angle validation passed
sphere wetting fixed
PhaseF write path authorized
controlled write enabled
dynamic impact basis ready
```

## Next Gate

Run the same sphere shadow-only cases to 2000 steps:

```text
theta sequence = 90, 60, 120
Stage17BWriteMode = 0
WallCompactStencilMode = 0
legacy sphere radAngle = 90d
```

Do not plan B3 controlled-write until cylinder 12000 and sphere 2000/12000 shadow gates are both recorded.
