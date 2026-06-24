# Stage17B-B3 Controlled WallGhost Write Audit 100

Date: 2026-06-24

Status: `PASS_STAGE17B_B3_WRITE_AUDIT`

This is a controlled write-path audit only. It is not a contact-angle validation and does not show that curved wetting, static contact angle, or dynamic impact is solved.

## Purpose

Stage17B-B2 proved that the diffuse-solid `Psi*` shadow diagnostics remained finite and coherent for long cylinder/sphere runs. B3 adds a gated path that can replace the legacy curved analytic `WallGhost` with `PsiWallGhost` on curved analytic wall nodes.

The first gate asks only:

```text
does the controlled write activate where the B2 readiness gate says it is safe?
does WettingPathId=170 appear exactly on applied nodes?
does WallGhost equal PsiWallGhost on applied nodes?
does WallGhostRaw equal PsiWallGhostRaw on applied nodes?
does WallGhostClampHit equal PsiWallGhostClampHit on applied nodes?
does PhaseField remain finite for 100 steps?
```

## Source Changes Audited

The Stage17B snapshot now includes:

```text
Stage17BWriteMode = 0 default, unchanged
Stage17BWriteMode > 1.5 required for controlled write
AnalyticSolidType >= 1.5 required, so flat walls are excluded
WallCompactStencilWriteAllowedFlag is not used by the B3 gate
WettingPathId = 170.0 marks applied B3 writes
PsiWriteAppliedFlag marks the same applied cells
```

The controlled path writes only `WallGhost` and related diagnostics:

```text
WallGhost = PsiWallGhost
WallGhostRaw = PsiWallGhostRaw
WallGhostClamped = PsiWallGhost
WallGhostClampHit = PsiWallGhostClampHit
WettingPathId = 170
PsiWriteAppliedFlag = 1
```

The code still sets `PhaseF = pf_f` before return. This is the pre-existing analytic-wall mirror behavior: wall-node `PhaseF` is set to the adjacent fluid value so stencils do not read a solid sentinel. B3 does not write the new ghost value into `PhaseF`.

Source audit:

```text
artifacts/stage17B_B3_writeaudit_100_20260624/source_audit.json
status = PASS_STAGE17B_SHADOW_SOURCE_GUARDRAILS
```

## Runtime Setup

```text
server = yuan@192.168.1.16
run root = /mnt/usb1t/RUNS/runs/stage17B_B3_writeaudit_100_20260624
GPU = CUDA_VISIBLE_DEVICES=1
binary = /home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
binary sha256 = 2c61762bcfbf2e4955b4e0fff84ba2c746d698e1ba267c31a1dbb6d8558c226c
analyzer = stage17B_shadow_analyze.py --write-audit --expected-final-step 100
```

Cases:

```text
cylinder_theta090_writeaudit
sphere_theta090_writeaudit
iterations = 100
vtk period = 100
Stage17BDiffuseSolidMode = 1
Stage17BWriteMode = 2
WallCompactStencilMode = 0
legacy radAngle = 90d
Stage17BShadowThetaDeg = 90
```

## Results

Overall:

```text
stage17B_shadow_analysis.json status = PASS_STAGE17B_B3_WRITE_AUDIT
done.status = DONE ... rc=0
```

Key frame metrics:

| case | step | applied cells | path170 cells | WallGhost-Psi max diff | raw max diff | clamp-hit max diff | PhaseField nonfinite | PsiWallGhost min/max | NearWallForceOverRho max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cylinder_theta090_writeaudit | 0 | 12428 | 12428 | 0.0 | 0.0 | 0.0 | 0 | 0.0 / 0.9999999999986269 | 0.0 |
| cylinder_theta090_writeaudit | 100 | 19928 | 19928 | 0.0 | 0.0 | 0.0 | 0 | 0.0 / 1.0 | 2.340137510991671e-05 |
| sphere_theta090_writeaudit | 0 | 5312 | 5312 | 0.0 | 0.0 | 0.0 | 0 | 0.0 / 0.9999996561665934 | 0.0 |
| sphere_theta090_writeaudit | 100 | 7208 | 7208 | 0.0 | 0.0 | 0.0 | 0 | 0.0 / 1.0 | 9.314484480386457e-06 |

There were no analyzer failures. `applied_without_path170_cells = 0`, `path170_without_applied_cells = 0`, and all applied-node WallGhost/Psi consistency checks were exactly zero in the reported frames.

## Artifacts

Committed lightweight artifacts:

```text
artifacts/stage17B_B3_writeaudit_100_20260624/stage17B_shadow_analysis.json
artifacts/stage17B_B3_writeaudit_100_20260624/stage17B_shadow_frames.csv
artifacts/stage17B_B3_writeaudit_100_20260624/source_audit.json
artifacts/stage17B_B3_writeaudit_100_20260624/run_manifest.txt
artifacts/stage17B_B3_writeaudit_100_20260624/binary_sha256.txt
artifacts/stage17B_B3_writeaudit_100_20260624/done.status
artifacts/stage17B_B3_writeaudit_100_20260624/*/case.xml
artifacts/stage17B_B3_writeaudit_100_20260624/*/run.log
artifacts/stage17B_B3_writeaudit_100_20260624/*/run.status
artifacts/stage17B_B3_writeaudit_100_20260624/*/run.stderr
```

Large VTI outputs remain only on the server and are not committed.

## Verdict

B3 controlled `WallGhost` write is implemented and passes the first 100-step cylinder/sphere 90-degree write-audit gate on P100.

This does not validate contact angle. The next gate should remain narrow:

```text
1. cylinder/sphere theta090 write-audit to 1000
2. cylinder/sphere theta060/theta120 write-audit to 1000
3. flat-wall regression with Stage17BWriteMode=2 must show no B3 writes
4. only then static contact-angle morphology cases
```

Do not enter dynamic impact from this result.
