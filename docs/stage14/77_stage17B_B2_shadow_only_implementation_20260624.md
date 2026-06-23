# Stage17B-B2 Diffuse-Solid Shadow-Only Implementation

Date: 2026-06-24

Status: `PASS_STAGE17B_B2_SHADOW_DIAGNOSTICS` for the first P100 1000-step cylinder shadow gate. No contact-angle validation is claimed.

## Scope

B2 connects the B1 offline analytic-SDF / diffuse-solid idea into an independent TCLB snapshot as output-only diagnostics:

```text
third_party/tclb_snapshots/stage17B_diffuse_solid_shadow/
```

The implementation does not overwrite historical snapshots and does not change the legacy default solver behavior because every new setting defaults to off. In B2, `Psi*` and `NearWall*` are diagnostic fields only:

```text
No PhaseF write.
No WallGhost write.
No controlled curved-wall write.
No dynamic impact run.
No contact-angle validation claim.
```

## Source Changes

### New Settings

```text
Stage17BDiffuseSolidMode = 0
Stage17BWriteMode = 0
Stage17BPsiEps = 1.25
Stage17BWriteBand = 1.8
Stage17BGradPsiMin = 1e-4
Stage17BShadowThetaDeg = -1
```

`Stage17BWriteMode=0` is the B2 guardrail. If it is set above zero in this snapshot, the code disables `PsiWriteAllowedFlag`; B2 therefore cannot become a hidden write path.

`Stage17BShadowThetaDeg` keeps B2 genuinely shadow-only. The legacy solver `radAngle` can remain at a neutral 90 degrees while `PsiWallGhost` and `PsiThetaImplied` are swept at 60/90/120 degrees. This separates diagnostic target-angle evaluation from the existing curved-wall wetting path.

### New Fields / Quantities

Wall-side diffuse-solid shadow fields:

```text
PsiSolid
PsiGradMag
PsiNormalX/Y/Z
PsiWallGhost
PsiThetaImplied
PsiJaggedness
PsiWriteAllowedFlag
PsiNormalAmbiguityFlag
```

Fluid near-wall force shadow fields:

```text
NearWallForceMag
NearWallGradPhiMag
NearWallForceOverRhoShadow
```

### Boundary Template

`Boundary.c.Rt` now contains:

```text
stage17b_diffuse_solid_indicator
stage17b_diffuse_solid_grad_analytic
stage17b_reset_diffuse_shadow
stage17b_keep_diffuse_shadow
stage17b_compute_diffuse_shadow
getPsi*
```

The normal convention follows B1:

```text
psi_s = 1 in solid, 0 in fluid
grad(psi_s) points inward
PsiNormal = -grad(psi_s)/|grad(psi_s)|, solid-to-fluid
```

The Stage17B block computes `PsiWallGhost` as a shadow value only. It does not assign `WallGhost` and does not assign `PhaseF`.

The historical compact-stencil write gate remains flat-only:

```c
bool compact_write = stage13_compact_write_requested() && (AnalyticSolidType < 1.5);
```

So cylinder/sphere cannot enter the old curved compact-write path through B2.

### Dynamics Template

`Dynamics.c.Rt` now writes near-wall force shadow fields in both MRT and BGK collision paths after the first force assembly:

```text
NearWallForceMag
NearWallGradPhiMag
NearWallForceOverRhoShadow
```

These fields are reset every collision call. They are not consumed by the solver.

## Added Scripts

```text
scripts/stage17/stage17B_shadow_source_audit.py
scripts/stage17/gen_cyl_shadow_cases.py
scripts/stage17/stage17B_remote_build_shadow.sh
scripts/stage17/run_stage17B_shadow_remote.sh
scripts/stage17/stage17B_shadow_analyze.py
```

The source audit checks:

```text
Stage17B snapshot exists
new settings default to shadow-only
Psi*/NearWall* fields and quantities exist
Stage17B compute block does not write PhaseF or WallGhost
old curved compact-write path remains blocked
MRT and BGK both reset/write NearWall* diagnostics
```

The cylinder case generator creates only:

```text
cylinder_theta060_shadow
cylinder_theta090_shadow
cylinder_theta120_shadow
```

Each accepted B2 case uses:

```text
Stage17BDiffuseSolidMode = 1
Stage17BWriteMode = 0
Stage17BShadowThetaDeg = 60 / 90 / 120
legacy AnalyticCylinder radAngle = 90d
WallCompactStencilMode = 0
WallCompactStencilWriteAllowedFlag = 0
DynamicCLMode = 0
```

## Source Guardrail Result

Local static audit:

```text
artifacts/stage17B_B2_shadow_20260624/source_audit.json
status = PASS_STAGE17B_SHADOW_SOURCE_GUARDRAILS
failures = []
```

This proves only source-level guardrails. It does not prove physical correctness or contact-angle response.

## Runtime Gate

B2 runtime was run on the P100 lane:

```text
CUDA_VISIBLE_DEVICES=1
run root = /mnt/usb1t/RUNS/runs/stage17B_shadowtheta_cylinder_20260624
binary = /home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
binary sha256 = 411d72fb9ff45cb799bfda4b6b33a0761ee5903b1e00c484c7578894be766aee
done.status = DONE /mnt/usb1t/RUNS/runs/stage17B_shadowtheta_cylinder_20260624 rc=0
```

Lightweight evidence is stored locally at:

```text
artifacts/stage17B_B2_shadow_20260624/runtime_shadowtheta/
```

Files retained:

```text
stage17B_shadow_analysis.json
stage17B_shadow_frames.csv
binary_sha256.txt
run_manifest.txt
done.status
cylinder_theta060_shadow/run.log, run.stderr, run.status
cylinder_theta090_shadow/run.log, run.stderr, run.status
cylinder_theta120_shadow/run.log, run.stderr, run.status
```

The large VTI files were not downloaded or committed.

## Runtime Result

Analyzer status:

```text
PASS_STAGE17B_B2_SHADOW_DIAGNOSTICS
```

Case summary:

| case | steps | run log NaN | status | final PhaseField nonfinite | final PsiWallGhost range | max NearWallForceOverRhoShadow |
|---|---:|---:|---|---:|---:|---:|
| `cylinder_theta060_shadow` | 0, 500, 1000 | false | `PASS_SHADOW_DIAGNOSTICS` | 0 | [0.0, 1.0] | 0.0024766486 |
| `cylinder_theta090_shadow` | 0, 500, 1000 | false | `PASS_SHADOW_DIAGNOSTICS` | 0 | [0.0, 1.0] | 0.0010872819 |
| `cylinder_theta120_shadow` | 0, 500, 1000 | false | `PASS_SHADOW_DIAGNOSTICS` | 0 | [0.0, 1.0] | 0.0080598404 |

Common runtime observations:

```text
required Psi*/NearWall* arrays present = true
PsiWallGhost below 0 cells = 0
PsiWallGhost above 1 cells = 0
PsiNormalAmbiguityFlag near-band fraction = 0
PsiWriteAllowedFlag near-band fraction = 1.0
final VTI step 1000 exists for all three cases
```

`PhaseField` has small overshoots in the legacy solver output, for example about `[-1.69e-4, 1.00015]` across the accepted frames. This is not caused by B2 shadow writes, because B2 does not write `PhaseF`; it remains part of the separate Stage14 momentum/pressure/phase-closure line.

## Negative Control / Discarded Runtime

An earlier B2 attempt used `radAngle=60/90/120` on `AnalyticCylinder`. That polluted the legacy curved wetting path while trying to test shadow-only diagnostics; `theta060` produced a NaN stop before the expected gate. That run is not accepted as B2 evidence.

The accepted B2 run corrected this by fixing legacy `radAngle=90d` and sweeping only:

```text
Stage17BShadowThetaDeg = 60 / 90 / 120
```

This negative control is useful because it confirms why shadow target angle must be decoupled from legacy solver physics until controlled-write gates are explicitly opened.

## Claim Limits

Allowed:

```text
B2 source wiring implemented.
B2 static guardrail passed.
B2 first P100 cylinder shadow diagnostics passed for 1000 steps.
```

Forbidden:

```text
contact angle validation passed
cylinder/sphere wetting fixed
PhaseF write path authorized
controlled write enabled
dynamic impact basis ready
```

## Next Gates

1. Run the same cylinder shadow cases to 2000 steps.
2. If 2000 steps passes, run the cylinder shadow cases to 12000 steps.
3. Only after cylinder shadow remains coherent should B2 be extended to sphere shadow diagnostics.
4. Only after B2 shadow gates pass should a separate B3 design discuss controlled write, with `PhaseF` write still disabled by default.
5. Keep Stage14 dense-onset `stress/F_mu / ForceOverRho / pressure closure` as a separate solver-closure line. Do not mix it into B2 curved-boundary shadow diagnostics.
