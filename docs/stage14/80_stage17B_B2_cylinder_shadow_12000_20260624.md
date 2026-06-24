# Stage17B-B2 Cylinder Shadow 12000-Step Gate

Date: 2026-06-24

Status: `PASS_STAGE17B_B2_SHADOW_DIAGNOSTICS`. This is a long-run shadow-diagnostics gate only. It is not contact-angle validation and does not authorize any `PhaseF` or `WallGhost` write path.

## Run

```text
run root = /mnt/usb1t/RUNS/runs/stage17B_shadowtheta_cylinder_12000_20260624
local cases = cases/diagnostics/stage17B_cylinder_shadow_20260624_12000/
local evidence = artifacts/stage17B_B2_shadow_20260624/runtime_shadowtheta_12000/
GPU request = CUDA_VISIBLE_DEVICES=1
binary sha256 = 411d72fb9ff45cb799bfda4b6b33a0761ee5903b1e00c484c7578894be766aee
```

Case settings:

```text
iterations = 12000
vtk-period = 3000
log-period = 500
legacy radAngle = 90d
Stage17BShadowThetaDeg = 60 / 90 / 120
Stage17BWriteMode = 0
WallCompactStencilMode = 0
```

Analyzer:

```text
python3 stage17B_shadow_analyze.py ... --expected-final-step 12000
```

## Result

| case | frames | status | final PhaseField nonfinite | ghost below 0 | ghost above 1 | final max NearWallForceOverRhoShadow |
|---|---:|---|---:|---:|---:|---:|
| `cylinder_theta060_shadow` | 0, 3000, 6000, 9000, 12000 | `PASS_SHADOW_DIAGNOSTICS` | 0 | 0 | 0 | 0.0001056577 |
| `cylinder_theta090_shadow` | 0, 3000, 6000, 9000, 12000 | `PASS_SHADOW_DIAGNOSTICS` | 0 | 0 | 0 | 2.2023817e-05 |
| `cylinder_theta120_shadow` | 0, 3000, 6000, 9000, 12000 | `PASS_SHADOW_DIAGNOSTICS` | 0 | 0 | 0 | 2.1757932e-05 |

Common pass evidence:

```text
done.status = DONE /mnt/usb1t/RUNS/runs/stage17B_shadowtheta_cylinder_12000_20260624 rc=0
all three cases RC=0
expected final VTI step 12000 exists for all cases
analyzer status = PASS_STAGE17B_B2_SHADOW_DIAGNOSTICS
PsiWallGhost remains bounded
PsiNormalAmbiguityFlag near-band fraction remains zero
NearWallForceOverRhoShadow remains below the analyzer limit
```

Remote disk state:

```text
before = /mnt/usb1t free 66G
after  = /mnt/usb1t free 62G
```

No cleanup was required because free space stayed above the 50G threshold.

## Interpretation

This gate shows that the Stage17B diffuse-solid cylinder shadow fields remain finite and bounded through a 12000-step legacy solver run on P100. The shadow theta sweep does not write back to the physical solver state, so this result only validates diagnostic-field stability and geometry/near-wall field coherence for the cylinder case family.

The result does not prove that the contact angle is correct. It only supports moving from cylinder shadow-only to sphere shadow-only.

## Claim Limits

Allowed:

```text
Stage17B-B2 cylinder shadow diagnostics passed to 12000 steps.
The next permitted step is sphere shadow-only diagnostics.
```

Forbidden:

```text
contact angle validation passed
cylinder wetting fixed
PhaseF write path authorized
controlled write enabled
dynamic impact basis ready
```

## Next Gate

Add sphere shadow-only cases using the same B2 guardrails:

```text
initial theta sequence = 90, 60, 120
initial steps = 1000
Stage17BWriteMode = 0
WallCompactStencilMode = 0
legacy sphere radAngle = 90d
```

Do not plan B3 controlled-write until cylinder 12000 and sphere shadow gates are both recorded.
