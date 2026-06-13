# Stage8g Cap-Contract Revision Diagnostic

Status: `runtime_sanity / exploratory_not_validation`.

Stage8g is a shadow-only diagnostic lane built from Stage8f. It does not
change the Stage8f conclusion, does not authorize sphere `Stage8OperatorMode=2`,
and does not authorize PRE reproduction, validation, production, or long sphere
runs.

## Purpose

Stage8f showed that Stage8e removed the full-vector limiter, but sphere
shadow diagnostics still had normal-limiter fractions of about `73-85 %`.
Stage8g tests whether that blocker is mainly caused by:

```text
1. Stage8e ratio-cap scale based only on abs(normal_raw)
2. low-angle tan(pi/2 - theta) amplification
3. wall/profile phase path opposing the gradient candidate
```

The test remains shadow-only. The candidate is computed and written to
diagnostic fields, but it is not written back to `gradPhiVal_*`.

## Source

```text
remote source = /home/yuan/src/TCLB_stage8g_cap_contract_revision_diag_20260613
public snapshot = third_party/tclb_snapshots/stage8g_cap_contract_revision_diag
patch = third_party/tclb_snapshots/patches/stage8g_cap_contract_revision_diag_20260613.diff
run root = /media/yuan/新加卷1/RUNS/runs/stage8/stage8g_cap_contract_revision_diag_20260613
binary sha256 = b7eab126c94a9a17e8ae83265b27ef7cf385350be9ef1719f4bd514f25ff19a4
```

The run environment is loaded with:

```bash
source "/media/yuan/新加卷1/RUNS/scripts/tclb_runs_env.sh"
```

## Stage8g Modes

```text
Stage8gMode=0: Stage8e/Stage8f baseline
Stage8gMode=1: revised normal-cap scale
Stage8gMode=2: low-angle tan regularization
Stage8gMode=3: combined revised cap scale and tan regularization
```

Mode 1 replaces the ratio-cap scale with:

```text
scale = max(abs(normal_raw),
            Stage8gKTarget * abs(target_normal),
            Stage8gKTangent * tangent_mag,
            Stage8gNormalFloor)

ratio_cap = Stage8MaxNormalDeltaRatio * scale
cap = min(Stage8MaxNormalDelta, ratio_cap)
```

Mode 2 replaces the raw low-angle tangent coefficient with:

```text
tan_raw = tan(pi/2 - theta_local)
tan_eff = tan_raw / sqrt(1 + (tan_raw / Stage8gTanCap)^2)
target_normal = -tan_eff * tangent_mag
```

Mode 3 applies both changes. All modes keep the Stage8e normal-residual-only
structure: only the wall-normal component of the gradient candidate is changed
in diagnostics, and the tangential gradient is left unchanged.

## Write Boundary

Stage8g explicitly keeps sphere write disabled:

```text
Stage8OperatorMode=1 is the intended mode for all Stage8g cases.
Stage8gWriteAllowedFlag is fixed at 0.
The Stage8g source does not write corrected gradients for normal mode values.
Stage8OperatorMode=2 sphere runs remain forbidden until a later separate plan.
```

No Stage8g evidence may be described as a fix, validation pass, PRE
reproduction, production candidate, or publication-ready result.

## New Diagnostics

Stage8g adds these quantities on top of Stage8f:

```text
WallStage8gMode
WallStage8gScaleRawNormal
WallStage8gScaleTarget
WallStage8gScaleTangent
WallStage8gScaleFloor
WallStage8gEffectiveScale
WallStage8gTanRaw
WallStage8gTanEff
WallStage8gRegularizationRatio
WallStage8gCapSource
WallStage8gCapDemandRatio
WallStage8gProfileTargetMismatch
WallStage8gProfileConflictSign
WallStage8gWriteAllowedFlag
```

The postprocessor reports normal-limiter and vector-limiter fractions
separately. In Stage8e and later, the old `limiter_fraction` field means the
secondary vector limiter only; the blocking quantity is
`normal_limiter_fraction`.

## Cases

Flat low-angle shadow cases:

```text
cases/diagnostics/flat_wall_cap_stage8g_low_angle_20260613
wall angles = 5, 8, 11, 15, 20, 25, 30 deg
Stage8gMode = 0, 1, 2, 3
steps = 0, 100, 1000
Stage8OperatorMode = 1
```

Sphere shadow cases:

```text
cases/diagnostics/pre2025_sphere_stage8g_shadow_20260613
geometry = 80 x 80 x 180
R_drop = 24
R_solid = 24
solid_center = (40, 40, 48)
drop_center_z = 96 for free-sphere initializer
outer radAngle = 90 deg
sphere radAngle = 11 deg
M = 0.1
IntWidth = 6
initializers = free-sphere, approximate cap-on-sphere
Stage8gMode = 0, 1, 2, 3
steps = 0, 100, 1000
Stage8OperatorMode = 1
```

The approximate cap-on-sphere initializer is diagnostic only. It is not a
theoretical equilibrium initializer.

## Gates

Gate 0 requires build/provenance and public repository audit:

```text
source generation rc = 0
build rc = 0
binary SHA256 archived as metadata only
raw field, binary, archive, credential, and >100 MB public audit counts = 0
```

Gate 1 runs flat low-angle shadow diagnostics:

```text
nonfinite_total = 0
vector_limiter_fraction = 0
wall025/wall030 do not regress
low-angle normal limiter decreases compared with Stage8f
```

Gate 2 runs z48 sphere shadow diagnostics:

```text
nonfinite_total = 0
outer90_normal_limiter_count = 0
fallback_angle_normal_limiter_count = 0
vector_limiter_fraction = 0
final normal_limiter_fraction < 5-10 %
limiter_ratio_p50 > 0.8
cap_demand_p50 < 1.2
Mach not above Stage8f order
```

Gate 3 is attribution only:

```text
mode 1 passes: cap-contract scale was the main blocker
mode 2 passes: low-angle tan relation was the main blocker
mode 3 passes: cap contract and tan regularization jointly matter
all fail with profile mismatch: unify wall profile path and gradient candidate
all fail without profile mismatch: keep Stage8g as negative evidence and audit
                                 a weaker low-angle contact relation
```

## Execution Notes

Stage8g was run on HM570 using the new run root on the added volume:

```text
/media/yuan/新加卷1/RUNS/runs/stage8/stage8g_cap_contract_revision_diag_20260613
```

The build/provenance gate passed:

```text
make source rc = 0
make build rc = 0
binary sha256 = b7eab126c94a9a17e8ae83265b27ef7cf385350be9ef1719f4bd514f25ff19a4
```

GPU execution policy used for the short case matrix:

```text
small independent cases = two P100 queues in parallel
P100 A UUID = GPU-f650e558-d920-2fcb-0a8e-45cbc17c1ca2
P100 B UUID = GPU-2abee638-4460-b364-cd98-08cb6eaf11f7
CUDA_DEVICE_ORDER = PCI_BUS_ID
CUDA_VISIBLE_DEVICES = GPU UUID, not numeric index
```

Numeric `CUDA_VISIBLE_DEVICES=2` was found to map to the Quadro P4000 under the
default CUDA order, so the final queues use P100 UUID binding. The Quadro P4000
was not used for the accepted Stage8g flat/sphere queue results.

Raw `.vti/.pvti/.pri/.vtk` outputs were deleted after analysis. Public local
artifacts contain curated XML, JSON, CSV, logs, and provenance only.

Curated artifacts:

```text
artifacts/flat_wall_cap_stage8g_low_angle_20260613
artifacts/pre2025_sphere_stage8g_shadow_20260613
artifacts/stage8g_cap_contract_revision_provenance_20260613
artifacts/stage8g_cap_contract_revision_summary_20260613
```

Summary files:

```text
artifacts/stage8g_cap_contract_revision_summary_20260613/stage8g_gate_summary.json
artifacts/stage8g_cap_contract_revision_summary_20260613/stage8g_flat_shadow_summary.csv
artifacts/stage8g_cap_contract_revision_summary_20260613/stage8g_sphere_shadow_summary.csv
```

## Gate Results

All Stage8g flat and sphere shadow cases completed with:

```text
solver return code = 0
nonfinite_total = 0
vector_limiter_fraction = 0
raw local VTI/PVTI count after curation = 0
```

Flat low-angle shadow final-frame summary:

| wall angle | mode0 normal limiter | mode1 normal limiter | mode2 normal limiter | mode3 normal limiter |
|---:|---:|---:|---:|---:|
| 5 deg | 88.78 % | 82.67 % | 77.56 % | 77.45 % |
| 8 deg | 85.21 % | 81.39 % | 76.26 % | 76.26 % |
| 11 deg | 83.18 % | 80.24 % | 73.30 % | 73.30 % |
| 15 deg | 78.11 % | 77.60 % | 9.16 % | 9.16 % |
| 20 deg | 33.30 % | 33.30 % | 0.00 % | 0.00 % |
| 25 deg | 0.00 % | 0.00 % | 0.00 % | 0.00 % |
| 30 deg | 0.00 % | 0.00 % | 0.00 % | 0.00 % |

Flat interpretation:

```text
mode 1 cap-contract scale revision helps only weakly at very low angles.
mode 2 tan regularization gives the dominant improvement.
mode 3 is almost identical to mode 2 for flat cases.
wall005/wall008/wall011 still fail the normal-limiter gate.
wall015 becomes a borderline shadow pass under mode2/mode3.
wall020 and higher pass under mode2/mode3.
```

Sphere z48 shadow final-frame summary:

| case | mode | normal limiter | limiter ratio p50 | cap demand p50 | max Mach |
|---|---:|---:|---:|---:|---:|
| cap-on-sphere | 0 | 73.04 % | 0.4123 | 2.4257 | 1.89e-5 |
| cap-on-sphere | 1 | 71.50 % | 0.4718 | 2.1195 | 1.89e-5 |
| cap-on-sphere | 2 | 46.81 % | 1.0000 | 0.8224 | 1.89e-5 |
| cap-on-sphere | 3 | 45.64 % | 1.0000 | 0.7500 | 1.89e-5 |
| free-sphere | 0 | 85.28 % | 0.1352 | 7.3964 | 3.08e-4 |
| free-sphere | 1 | 80.52 % | 0.2463 | 4.0602 | 3.08e-4 |
| free-sphere | 2 | 81.39 % | 0.2640 | 3.7883 | 3.08e-4 |
| free-sphere | 3 | 77.06 % | 0.3723 | 2.6864 | 3.08e-4 |

Sphere interpretation:

```text
outer90_normal_limiter_count = 0 in all sphere cases
fallback_angle_normal_limiter_count = 0 in all sphere cases
profile_conflict_p50 = 0 in all sphere cases
mode 3 is the best sphere shadow result, but still far above the <5-10% gate
cap-on-sphere initializer remains much healthier than free-sphere initializer
```

## Current Result

Stage8g does not pass the sphere shadow gate. The valid conclusion is:

```text
Stage8g confirms that low-angle tan regularization is directionally important.
Stage8g does not reduce sphere normal_limiter_fraction enough for write mode.
Stage8OperatorMode=2 sphere write remains forbidden.
No sphere 50k, 200k, 400k, or 600k run is authorized from Stage8g.
```

The current root-cause interpretation is:

```text
cap-contract revision alone is insufficient.
low-angle tan regularization is the dominant improvement mechanism.
initial geometry stress is important because cap-on-sphere improves strongly
relative to free-sphere, but it is not sufficient to pass the gate.
outer-wall angle transfer and fallback angle contamination are not supported
by the Stage8g data.
profile conflict is not detected by the current p50 diagnostic, but the
profile/gradient candidate contract still remains a possible next audit route.
```

The likely next route is a separate Stage8h plan, not a hidden Stage8g write:

```text
diagnose why cap-on-sphere mode3 still leaves about 45.6% normal limiter hits;
separate active-band residuals from remaining contact-relation stiffness;
audit wall profile path versus fluid-gradient candidate at the cell/stencil level;
only after a new shadow gate passes should short write tests be planned.
```
