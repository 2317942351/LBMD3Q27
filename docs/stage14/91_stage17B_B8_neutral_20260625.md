# Stage17B-B8 Neutral Drift Isolation

Date: 2026-06-25

Status:

```text
local source audit: PASS_STAGE17B_SHADOW_SOURCE_GUARDRAILS
local B8 case generation: PASS
remote CUDA build: PASS
B8 600-step P100 smoke: PASS_STAGE17B_B8_NEUTRAL_CLASSIFICATION
B8 2000-step P100 gate: PASS_STAGE17B_B8_NEUTRAL_CLASSIFICATION
claim limit: neutral drift root-cause diagnostic only; not contact-angle validation
```

This stage does not validate static contact angle and does not justify dynamic impact cases.

## Purpose

B7 showed that the cylinder 60 and 120 degree targets still move in opposite expected directions at 2000 steps, but the neutral 90 to 90 control drifted by about -3.42 degrees. B8 isolates whether that neutral drift comes from:

```text
1. baseline phase/force/initialization closure;
2. controlled diffuse-solid PsiWallGhost neutral formula;
3. controlled curved write mechanism / stencil consumption semantics; or
4. diagnostic metric sensitivity.
```

The central question is:

```text
Does the 90-degree drift exist without the controlled write path?
```

## Code Change

A default-off diagnostic setting was added:

```text
Stage17BWriteSourceMode = 0
```

Meaning:

```text
0: current controlled write behavior, WallGhost = PsiWallGhost, WettingPathId = 170
1: B8 diagnostic only, same controlled curved write gate writes legacy analytic WallGhost, WettingPathId = 171
```

Default behavior is unchanged. The new branch is reachable only when a case explicitly sets:

```text
Stage17BDiffuseSolidMode = 1
Stage17BWriteMode = 2
Stage17BWriteSourceMode = 1
```

## B8 Matrix

All cases use a 90-degree cylinder cap initialization and legacy `radAngle = 90d`.

| group | case | diffuse mode | write mode | write source | purpose |
|---|---|---:|---:|---:|---|
| A | `cylinder_init090_neutral_A_legacy_baseline` | 0 | 0 | 0 | pure legacy analytic baseline |
| B | `cylinder_init090_neutral_B_shadow_only` | 1 | 0 | 0 | shadow-only side-effect check |
| C | `cylinder_init090_neutral_C_controlled_psi` | 1 | 2 | 0 | current controlled PsiWallGhost write |
| D | `cylinder_init090_neutral_D_controlled_legacy` | 1 | 2 | 1 | same write gate, legacy analytic WallGhost |

## Verdict Logic

```text
A drifts:
  baseline phase/force/initialization bias is suspected.

A stable, B stable, C drifts, D stable:
  controlled PsiWallGhost neutral formula is suspected.

A stable, B stable, C drifts, D drifts:
  controlled write gate or stencil consumption semantics are suspected.

A stable, B drifts:
  shadow-only side effect or metric sensitivity is suspected.
```

## Local Checks

```text
python -m py_compile scripts/stage17/gen_stage17B_B8_neutral_cases.py scripts/stage17/stage17B_B8_neutral_analyze.py scripts/stage17/stage17B_shadow_source_audit.py
python scripts/stage17/stage17B_shadow_source_audit.py --out artifacts/stage17B_B8_neutral_20260625/source_audit.json
python scripts/stage17/gen_stage17B_B8_neutral_cases.py --root cases/diagnostics/stage17B_B8_neutral_20260625_600 --iterations 600 --vtk-period 200 --log-period 100
git diff --check
```

Result:

```text
source audit status = PASS_STAGE17B_SHADOW_SOURCE_GUARDRAILS
generated cases = 4
git diff --check = pass
```

## Remote Setup

```text
server = yuan@192.168.1.16
GPU request = CUDA_VISIBLE_DEVICES=1
visible GPU 1 = Tesla P100-PCIE-16GB
run root smoke = /mnt/usb1t/RUNS/runs/stage17B_B8_neutral_20260625_600
run root 2000 = /mnt/usb1t/RUNS/runs/stage17B_B8_neutral_20260625_2000
USB free before run = about 254G
compile lane = /home/yuan/src/TCLB_lbm2026_compile_lane
binary sha256 = 8e88228d38c4e10e7d84bf32738b8490bd8ab9a263e672ddcf6a033eed80a3b5
```

The Stage17B source changed, so B7's binary must not be reused. Remote build must regenerate source and rebuild CUDA.

## B8 600-Step Result

All four solver cases completed with `RC=0` on P100. The B8-specific analyzer passed:

```text
status = PASS_STAGE17B_B8_NEUTRAL_CLASSIFICATION
primary_suspect = baseline_phase_force_initialization_bias
```

Final 600-step summary:

| group | write path | contact half-width delta | phase min/max | write-path audit |
|---|---|---:|---:|---|
| A | legacy baseline write off | -1.803049 deg | -1.0687e-4 / 1.000114 | no Stage17B write |
| B | diffuse shadow write off | -1.803049 deg | -1.0687e-4 / 1.000114 | 19928 allowed, 0 applied |
| C | controlled `PsiWallGhost` write | -1.803049 deg | -1.0724e-4 / 1.000126 | 19928 applied, all `WettingPathId=170`, `WallGhost=PsiWallGhost` |
| D | controlled legacy analytic write | -1.803049 deg | -1.0687e-4 / 1.000114 | 19928 applied, all non-170 with max `WettingPathId=171` |

This is the key B8 evidence: the 600-step neutral drift is identical even when Stage17B is fully disabled in group A. It is also identical when the controlled write gate writes the current diffuse-solid `PsiWallGhost` in group C or the legacy analytic neutral ghost in group D.

Therefore the 600-step neutral drift is not primarily caused by:

```text
controlled curved WallGhost write missing
controlled PsiWallGhost formula alone
controlled write gate alone
shadow-only diagnostic fields
```

The dominant suspect moves to:

```text
baseline phase/force/initialization closure for the cylinder neutral cap
```

The old generic shadow/B5 analyzers may report failures for group A because group A intentionally disables Stage17B diffuse-solid fields. B8 classification uses the dedicated analyzer and path audit instead.

## 2000-Step Gate

The 600-step result was enough to redirect root-cause priority, but the 2000-step gate was run to check whether the same all-path drift reproduces the B7 long-response scale.

```text
ROOT = /mnt/usb1t/RUNS/runs/stage17B_B8_neutral_20260625_2000
CASE_SRC = /home/yuan/stage17B_B8_neutral_cases_2000
EXPECTED_FINAL_STEP = 2000
GPU = 1
binary sha256 = 8e88228d38c4e10e7d84bf32738b8490bd8ab9a263e672ddcf6a033eed80a3b5
done.status = DONE ... rc=0
B8 analyzer = PASS_STAGE17B_B8_NEUTRAL_CLASSIFICATION
```

All four 2000-step solver cases completed with `RC=0`.

Final 2000-step summary:

| group | write path | contact half-width delta | phase min/max | write-path audit |
|---|---|---:|---:|---|
| A | legacy baseline write off | -3.416588 deg | -1.1419e-4 / 1.000125 | no Stage17B write |
| B | diffuse shadow write off | -3.416588 deg | -1.1421e-4 / 1.000125 | 19928 allowed, 0 applied |
| C | controlled `PsiWallGhost` write | -3.416588 deg | -1.1634e-4 / 1.000130 | 19928 applied, all `WettingPathId=170`, `WallGhost=PsiWallGhost` |
| D | controlled legacy analytic write | -3.416588 deg | -1.1421e-4 / 1.000125 | 19928 applied, all non-170 with max `WettingPathId=171` |

The 2000-step drift exactly reproduces the B7 neutral-control scale and remains identical across all B8 groups. That is the decisive result of this gate.

## B8 Verdict

B8 does not validate contact angle. It does close one root-cause branch:

```text
The 90-degree neutral cylinder drift is already present in the pure legacy
write-off baseline. It is unchanged by enabling Stage17B shadow fields,
unchanged by controlled PsiWallGhost writes, and unchanged by controlled legacy
analytic WallGhost writes.
```

Therefore, for the neutral-drift blocker, the project should stop treating the controlled curved `WallGhost` formula as the primary suspect. The next root-cause line should be:

```text
B9 baseline closure:
  cylinder-cap initialization equilibrium
  baseline phase equation near curved solid
  stress/F_mu/pressure/force feedback near curved wall
  mass/area drift and metric cross-check
```

The older B5/B7 evidence that 60 and 120 degree targets move in opposite expected directions still stands. B8 only says the 90-degree neutral drift is not caused mainly by the Stage17B controlled write path.

## Artifacts

Planned committed lightweight evidence:

```text
cases/diagnostics/stage17B_B8_neutral_20260625_600/
cases/diagnostics/stage17B_B8_neutral_20260625_2000/
artifacts/stage17B_B8_neutral_20260625/source_audit.json
artifacts/stage17B_B8_neutral_20260625/runtime_probe_600/
artifacts/stage17B_B8_neutral_20260625/runtime_probe_2000/
scripts/stage17/gen_stage17B_B8_neutral_cases.py
scripts/stage17/stage17B_B8_neutral_analyze.py
scripts/stage17/run_stage17B_B8_neutral_remote.sh
scripts/stage17/stage17B_B8_remote_build_resume.sh
scripts/stage17/stage17B_B8_remote_postprocess.sh
```

Do not commit raw VTI/PVTI files or archives.

## Current Limitation

At the time this report was created, the remote TCLB RT source-generation step was still running:

```text
tools/RT ... src/LatticeAccess.inc.cpp.Rt
```

The process was consuming CPU and the generated `LatticeAccess.inc.cpp` was still growing, so it was treated as long-running generation rather than a failed build.

That limitation is now resolved. The final build passed and produced the binary hash listed above.
