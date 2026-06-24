# Stage17B-B2 Cylinder Shadow 2000-Step Gate

Date: 2026-06-24

Status: `PASS_STAGE17B_B2_SHADOW_DIAGNOSTICS`. This is a shadow-diagnostics gate only, not contact-angle validation.

## Run

```text
run root = /mnt/usb1t/RUNS/runs/stage17B_shadowtheta_cylinder_2000_20260624
local cases = cases/diagnostics/stage17B_cylinder_shadow_20260624_2000/
local evidence = artifacts/stage17B_B2_shadow_20260624/runtime_shadowtheta_2000/
GPU request = CUDA_VISIBLE_DEVICES=1
binary sha256 = 411d72fb9ff45cb799bfda4b6b33a0761ee5903b1e00c484c7578894be766aee
```

Case settings:

```text
iterations = 2000
vtk-period = 500
log-period = 100
legacy radAngle = 90d
Stage17BShadowThetaDeg = 60 / 90 / 120
Stage17BWriteMode = 0
WallCompactStencilMode = 0
```

The analyzer was rerun with:

```text
--expected-final-step 2000
```

This matters because the older remote launcher defaulted to 1000. The launcher has been updated so future gates pass the expected final step explicitly.

## Result

| case | frames | status | final PhaseField nonfinite | ghost below 0 | ghost above 1 | final max NearWallForceOverRhoShadow |
|---|---:|---|---:|---:|---:|---:|
| `cylinder_theta060_shadow` | 0, 500, 1000, 1500, 2000 | `PASS_SHADOW_DIAGNOSTICS` | 0 | 0 | 0 | 0.0015628839 |
| `cylinder_theta090_shadow` | 0, 500, 1000, 1500, 2000 | `PASS_SHADOW_DIAGNOSTICS` | 0 | 0 | 0 | 2.6084198e-05 |
| `cylinder_theta120_shadow` | 0, 500, 1000, 1500, 2000 | `PASS_SHADOW_DIAGNOSTICS` | 0 | 0 | 0 | 5.3515488e-05 |

Common pass evidence:

```text
done.status = DONE ... rc=0
run logs contain no NaN stop
expected final VTI step 2000 exists for all cases
PsiWallGhost remains bounded
PsiNormalAmbiguityFlag near-band fraction remains zero
```

## Claim Limits

Allowed:

```text
Stage17B-B2 cylinder shadow diagnostics passed to 2000 steps.
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

Run the same cylinder shadow cases to 12000 steps with a lower VTI frequency, then analyze with:

```text
--expected-final-step 12000
```

Do not start sphere shadow or B3 controlled-write planning until the 12000-step cylinder shadow gate passes.
