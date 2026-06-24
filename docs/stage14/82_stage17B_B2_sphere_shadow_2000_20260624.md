# Stage17B-B2 Sphere Shadow 2000-Step Gate

Date: 2026-06-24

Status: `PASS_STAGE17B_B2_SHADOW_DIAGNOSTICS`. This is a sphere shadow-diagnostics gate only. It is not contact-angle validation and does not authorize any `PhaseF` or `WallGhost` write path.

## Run

```text
run root = /mnt/usb1t/RUNS/runs/stage17B_shadowtheta_sphere_2000_20260624
local cases = cases/diagnostics/stage17B_sphere_shadow_20260624_2000/
local evidence = artifacts/stage17B_B2_shadow_20260624/runtime_spheretheta_2000/
GPU request = CUDA_VISIBLE_DEVICES=1
binary sha256 = 411d72fb9ff45cb799bfda4b6b33a0761ee5903b1e00c484c7578894be766aee
```

Case settings:

```text
iterations = 2000
vtk-period = 500
log-period = 100
legacy sphere radAngle = 90d
Stage17BShadowThetaDeg = 90 / 60 / 120
Stage17BWriteMode = 0
WallCompactStencilMode = 0
```

## Result

| case | frames | status | final near-band cells | final PhaseField nonfinite | ghost below 0 | ghost above 1 | final max NearWallForceOverRhoShadow |
|---|---:|---|---:|---:|---:|---:|---:|
| `sphere_theta090_shadow` | 0, 500, 1000, 1500, 2000 | `PASS_SHADOW_DIAGNOSTICS` | 7208 | 0 | 0 | 0 | 1.3222198e-05 |
| `sphere_theta060_shadow` | 0, 500, 1000, 1500, 2000 | `PASS_SHADOW_DIAGNOSTICS` | 7208 | 0 | 0 | 0 | 1.3596235e-05 |
| `sphere_theta120_shadow` | 0, 500, 1000, 1500, 2000 | `PASS_SHADOW_DIAGNOSTICS` | 7208 | 0 | 0 | 0 | 1.0865492e-05 |

Common pass evidence:

```text
done.status = DONE /mnt/usb1t/RUNS/runs/stage17B_shadowtheta_sphere_2000_20260624 rc=0
all three cases RC=0
expected final VTI step 2000 exists for all cases
analyzer status = PASS_STAGE17B_B2_SHADOW_DIAGNOSTICS
PsiWallGhost remains bounded
PsiNormalAmbiguityFlag near-band fraction remains zero
NearWallForceOverRhoShadow remains below the analyzer limit
```

Remote disk state:

```text
before = /mnt/usb1t free 60G
after  = /mnt/usb1t free 57G
```

No cleanup was required because free space stayed above the 50G threshold.

## TCLB Output-Dimension Note

As in the 1000-step sphere gate, the physical/global case geometry remains `80x80x120`, while VTI analysis records the local padded lattice as `96x80x120`. This is a TCLB output/local-lattice detail. Use case XML or run-log global lattice size for physical geometry.

## Interpretation

This gate extends the sphere B2 shadow-only evidence from 1000 to 2000 steps. The diagnostic fields remain finite and bounded, with no `PsiWallGhost` out-of-bound cells and no near-band normal ambiguity.

The result does not prove sphere contact-angle correctness. It supports one further B2 sphere long-run gate at 12000 steps before any B3 controlled-write planning.

## Claim Limits

Allowed:

```text
Stage17B-B2 sphere shadow diagnostics passed to 2000 steps.
The next permitted step is sphere shadow-only 12000 steps.
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

Run the same sphere shadow-only cases to 12000 steps with lower VTI frequency:

```text
theta sequence = 90, 60, 120
suggested vtk-period = 3000
suggested log-period = 500
Stage17BWriteMode = 0
WallCompactStencilMode = 0
legacy sphere radAngle = 90d
```

Do not plan B3 controlled-write until cylinder 12000 and sphere 12000 shadow gates are both recorded.
