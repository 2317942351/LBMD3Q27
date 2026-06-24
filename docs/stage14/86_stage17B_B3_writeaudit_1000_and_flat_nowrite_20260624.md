# Stage17B-B3 Controlled WallGhost Write Audit 1000 and Flat No-Write Regression

Date: 2026-06-24

Status:

```text
curved write audit: PASS_STAGE17B_B3_WRITE_AUDIT
flat no-write regression: PASS_STAGE17B_B3_NO_WRITE_REGRESSION
```

This is a controlled write-path audit only. It is not a contact-angle validation. It does not prove that static curved contact angles or dynamic impact cases are solved.

## Purpose

The previous B3 100-step gate verified that the controlled Stage17B path can write `WallGhost` from the diffuse-solid `PsiWallGhost` field on curved analytic solids.

This gate extends the evidence in two directions:

```text
1. Run cylinder and sphere curved write-audit cases to 1000 steps for theta = 60, 90, 120.
2. Run a flat-wall regression with Stage17BWriteMode=2 to prove that the curved-only guard does not accidentally write on flat analytic walls.
```

The audited invariant remains narrow:

```text
applied cells must exactly match WettingPathId=170 cells
WallGhost must equal PsiWallGhost on applied nodes
WallGhostRaw must equal PsiWallGhostRaw on applied nodes
WallGhostClampHit must equal PsiWallGhostClampHit on applied nodes
flat analytic walls must have zero Stage17B writes
PhaseField must remain finite during this audit window
```

## Runtime Setup

Curved write-audit run:

```text
server = yuan@192.168.1.16
run root = /mnt/usb1t/RUNS/runs/stage17B_B3_writeaudit_1000_20260624
GPU = CUDA_VISIBLE_DEVICES=1
binary = /home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
binary sha256 = 2c61762bcfbf2e4955b4e0fff84ba2c746d698e1ba267c31a1dbb6d8558c226c
analyzer = stage17B_shadow_analyze.py --write-audit --expected-final-step 1000
```

Flat no-write regression run:

```text
server = yuan@192.168.1.16
run root = /mnt/usb1t/RUNS/runs/stage17B_B3_flat_no_write_1000_20260624
GPU = CUDA_VISIBLE_DEVICES=1
binary = /home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
binary sha256 = 2c61762bcfbf2e4955b4e0fff84ba2c746d698e1ba267c31a1dbb6d8558c226c
analyzer = stage17B_shadow_analyze.py --no-write-regression --expected-final-step 1000
```

## Cases

Curved write-audit cases:

```text
cylinder_theta060_writeaudit
cylinder_theta090_writeaudit
cylinder_theta120_writeaudit
sphere_theta060_writeaudit
sphere_theta090_writeaudit
sphere_theta120_writeaudit
iterations = 1000
vtk period = 1000
Stage17BDiffuseSolidMode = 1
Stage17BWriteMode = 2
WallCompactStencilMode = 0
legacy radAngle = 90d
Stage17BShadowThetaDeg = 60 / 90 / 120
```

Flat no-write regression:

```text
flat_theta090_nowrite
iterations = 1000
vtk period = 1000
Stage17BDiffuseSolidMode = 1
Stage17BWriteMode = 2
AnalyticSolidType = 1
expected: PsiWriteAppliedFlag = 0 and WettingPathId=170 cells = 0
```

## Curved Results

Overall result:

```text
stage17B_shadow_analysis.json status = PASS_STAGE17B_B3_WRITE_AUDIT
done.status = DONE /mnt/usb1t/RUNS/runs/stage17B_B3_writeaudit_1000_20260624 rc=0
source_audit.json status = PASS_STAGE17B_SHADOW_SOURCE_GUARDRAILS
```

Final frame metrics at step 1000:

| case | applied cells | path170 cells | WallGhost-Psi max diff | PhaseField min/max | PhaseField nonfinite | NearWallForceOverRho max | PsiWallGhostRaw min/max |
|---|---:|---:|---:|---:|---:|---:|---:|
| cylinder_theta060_writeaudit | 19928 | 19928 | 0.0 | -0.00013071921407832305 / 1.0001491184600104 | 0 | 1.5647600133525636e-05 | -7.105204607450659e-05 / 1.3156856976916524 |
| cylinder_theta090_writeaudit | 19928 | 19928 | 0.0 | -0.00011338327927497234 / 1.000134804573532 | 0 | 2.459679163065559e-05 | -9.062857970694696e-05 / 1.000134804573532 |
| cylinder_theta120_writeaudit | 19928 | 19928 | 0.0 | -0.00011018054342220579 / 1.0001731457977647 | 0 | 4.366582012481872e-05 | -0.09204737019494799 / 1.0000026607332066 |
| sphere_theta060_writeaudit | 7208 | 7208 | 0.0 | -7.451923034973174e-05 / 1.0001620748569346 | 0 | 1.5917674500175412e-05 | -3.8598930815742984e-05 / 1.232561684111865 |
| sphere_theta090_writeaudit | 7208 | 7208 | 0.0 | -6.770285021003578e-05 / 1.0001815037111947 | 0 | 1.2704078778100216e-05 | -6.110677988464392e-05 / 1.000143874493625 |
| sphere_theta120_writeaudit | 7208 | 7208 | 0.0 | -8.659586127288356e-05 / 1.000187754224306 | 0 | 2.1996863000325035e-05 | -0.13473678123362517 / 1.0000418472811243 |

Important observations:

```text
applied_without_path170_cells = 0 for all reported frames
path170_without_applied_cells = 0 for all reported frames
WallGhost/Psi mismatch on applied nodes = 0 for all reported frames
WallGhostRaw/PsiWallGhostRaw mismatch on applied nodes = 0 for all reported frames
PsiWallGhost below 0 cells = 0
PsiWallGhost above 1 cells = 0
PsiNormalAmbiguityFlag near-band fraction = 0.0
PhaseField nonfinite = 0
```

The raw ghost shadows can exceed the bounded interval before clamping, especially for the 120-degree cases. This is expected for the audit because the write path is designed to write the clamped bounded `PsiWallGhost` while retaining `PsiWallGhostRaw` and clamp diagnostics for review. This result should not be interpreted as physical contact-angle accuracy.

## Flat No-Write Regression

Overall result:

```text
stage17B_shadow_analysis.json status = PASS_STAGE17B_B3_NO_WRITE_REGRESSION
done.status = DONE /mnt/usb1t/RUNS/runs/stage17B_B3_flat_no_write_1000_20260624 rc=0
```

Final frame metrics at step 1000:

| case | applied cells | path170 cells | write allowed cells | PhaseField min/max | PhaseField nonfinite | NearWallForceOverRho max |
|---|---:|---:|---:|---:|---:|---:|
| flat_theta090_nowrite | 0 | 0 | 0 | -6.923627962354212e-05 / 1.0001343982825857 | 0 | 0.0 |

This confirms that `Stage17BWriteMode=2` does not bypass the curved-only guard. Flat analytic walls keep the legacy path and do not receive `WettingPathId=170`.

## Storage Note

During the flat no-write regression, the run script detected that `/mnt/usb1t` had less than the 50 GB free-space threshold and removed regenerable old `output/*.vti` files. The committed evidence is the lightweight audit set: JSON, CSV, run logs, status files, manifests, case XML, binary hash, and source audit.

The cleanup does not affect the B3 verdict because the analyzer had already consumed the relevant VTI frames and the derived evidence was downloaded before committing.

## Artifacts

Committed lightweight artifacts:

```text
artifacts/stage17B_B3_writeaudit_1000_20260624/stage17B_shadow_analysis.json
artifacts/stage17B_B3_writeaudit_1000_20260624/stage17B_shadow_frames.csv
artifacts/stage17B_B3_writeaudit_1000_20260624/source_audit.json
artifacts/stage17B_B3_writeaudit_1000_20260624/run_manifest.txt
artifacts/stage17B_B3_writeaudit_1000_20260624/binary_sha256.txt
artifacts/stage17B_B3_writeaudit_1000_20260624/done.status
artifacts/stage17B_B3_writeaudit_1000_20260624/*/case.xml
artifacts/stage17B_B3_writeaudit_1000_20260624/*/run.log
artifacts/stage17B_B3_writeaudit_1000_20260624/*/run.status
artifacts/stage17B_B3_writeaudit_1000_20260624/*/run.stderr

artifacts/stage17B_B3_flat_no_write_1000_20260624/stage17B_shadow_analysis.json
artifacts/stage17B_B3_flat_no_write_1000_20260624/stage17B_shadow_frames.csv
artifacts/stage17B_B3_flat_no_write_1000_20260624/run_manifest.txt
artifacts/stage17B_B3_flat_no_write_1000_20260624/binary_sha256.txt
artifacts/stage17B_B3_flat_no_write_1000_20260624/done.status
artifacts/stage17B_B3_flat_no_write_1000_20260624/flat_theta090_nowrite/case.xml
artifacts/stage17B_B3_flat_no_write_1000_20260624/flat_theta090_nowrite/run.log
artifacts/stage17B_B3_flat_no_write_1000_20260624/flat_theta090_nowrite/run.status
artifacts/stage17B_B3_flat_no_write_1000_20260624/flat_theta090_nowrite/run.stderr
```

Large VTI outputs are not committed.

## Verdict

B3 controlled `WallGhost` write passed the 1000-step P100 write-audit gate for cylinder and sphere at shadow theta 60, 90, and 120 degrees. The flat-wall no-write regression also passed, proving the curved-only gate did not accidentally activate on `AnalyticSolidType=1`.

This is a meaningful implementation checkpoint because it proves the new curved diffuse-solid write path can be activated, measured, and blocked where intended.

It is still not a contact-angle validation. The next physical gate should be static morphology and angle response, and it must remain conservative:

```text
1. Run short static curved morphology cases with B3 enabled and explicit 2D droplet-shape plots.
2. Compare 60/90/120 target direction against observed interface motion, not just field finiteness.
3. If B3 destabilizes the solver, separate the cause into ghost formula, PhaseF/h update boundedness, or force/stress/pressure closure.
4. Do not enter dynamic impact before flat, cylinder, and sphere static cases show correct direction and acceptable stability.
```
