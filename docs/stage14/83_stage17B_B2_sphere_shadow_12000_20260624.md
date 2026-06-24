# Stage17B-B2 Sphere Shadow 12000-Step Gate

Date: 2026-06-24

Status: `PASS_STAGE17B_B2_SHADOW_DIAGNOSTICS`. This is a long-run sphere shadow-diagnostics gate only. It is not contact-angle validation and does not authorize any `PhaseF` or `WallGhost` write path.

## Run

```text
run root = /mnt/usb1t/RUNS/runs/stage17B_shadowtheta_sphere_12000_20260624
local cases = cases/diagnostics/stage17B_sphere_shadow_20260624_12000/
local evidence = artifacts/stage17B_B2_shadow_20260624/runtime_spheretheta_12000/
GPU request = CUDA_VISIBLE_DEVICES=1
binary sha256 = 411d72fb9ff45cb799bfda4b6b33a0761ee5903b1e00c484c7578894be766aee
```

Case settings:

```text
iterations = 12000
vtk-period = 3000
log-period = 500
legacy sphere radAngle = 90d
Stage17BShadowThetaDeg = 90 / 60 / 120
Stage17BWriteMode = 0
WallCompactStencilMode = 0
```

## Result

| case | frames | status | final near-band cells | final PhaseField nonfinite | ghost below 0 | ghost above 1 | final max NearWallForceOverRhoShadow |
|---|---:|---|---:|---:|---:|---:|---:|
| `sphere_theta090_shadow` | 0, 3000, 6000, 9000, 12000 | `PASS_SHADOW_DIAGNOSTICS` | 7208 | 0 | 0 | 0 | 1.3405982e-05 |
| `sphere_theta060_shadow` | 0, 3000, 6000, 9000, 12000 | `PASS_SHADOW_DIAGNOSTICS` | 7208 | 0 | 0 | 0 | 1.7366549e-05 |
| `sphere_theta120_shadow` | 0, 3000, 6000, 9000, 12000 | `PASS_SHADOW_DIAGNOSTICS` | 7208 | 0 | 0 | 0 | 1.1012066e-05 |

Common pass evidence:

```text
done.status = DONE /mnt/usb1t/RUNS/runs/stage17B_shadowtheta_sphere_12000_20260624 rc=0
all three cases RC=0
expected final VTI step 12000 exists for all cases
analyzer status = PASS_STAGE17B_B2_SHADOW_DIAGNOSTICS
PsiWallGhost remains bounded
PsiNormalAmbiguityFlag near-band fraction remains zero
NearWallForceOverRhoShadow remains below the analyzer limit
```

Remote disk state:

```text
before = /mnt/usb1t free 57G
after  = /mnt/usb1t free 54G
```

No cleanup was required because free space stayed above the 50G threshold.

## TCLB Output-Dimension Note

The physical/global case geometry remains `80x80x120`, while VTI analysis records the local padded lattice as `96x80x120`. This is the same TCLB local-lattice/output-padding detail observed in the 1000-step sphere gate. Use case XML or run-log global lattice size for physical geometry.

## Interpretation

This gate completes the Stage17B-B2 sphere long-run shadow-only evidence. Together with the cylinder 12000-step gate, the diffuse-solid curved-geometry shadow fields have now been exercised on both cylinder and sphere through the required long-run diagnostic threshold.

This still does not prove contact-angle correctness. It only establishes that the diagnostic geometry, smooth normal, shadow ghost, and near-wall force/rho shadow fields are finite, bounded, and stable enough to support B3 controlled-write planning.

## Claim Limits

Allowed:

```text
Stage17B-B2 cylinder and sphere shadow diagnostics passed to 12000 steps.
B3 controlled-write planning may begin.
```

Forbidden:

```text
contact angle validation passed
curved wetting fixed
PhaseF write path authorized by default
dynamic impact basis ready
```

## Next Gate

Plan B3 controlled-write, without enabling it by default:

```text
new explicit path id, e.g. WettingPathId = 170
default Stage17BWriteMode = 0
controlled write must not reuse flat compact-write permission
first B3 run must be short, shadow-plus-write-audit, and reversible
```

Stage14-74 `stress/F_mu / ForceOverRho` closure remains a separate line and must not be mixed into the B3 curved wetting write path.
