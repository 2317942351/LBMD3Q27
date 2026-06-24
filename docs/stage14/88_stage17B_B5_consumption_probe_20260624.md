# Stage17B-B5 WallGhost Consumption Probe

Date: 2026-06-24

Status:

```text
source audit: PASS_STAGE17B_SHADOW_SOURCE_GUARDRAILS
remote source generation: PASS
remote CUDA build: PASS
B3 write audit on B5 cases: PASS_STAGE17B_B3_WRITE_AUDIT
B5 consumption reanalysis: PASS_STAGE17B_B5_CONSUMPTION_PROBE
claim limit: WallGhost consumption diagnostics only; not contact-angle validation
```

This is not static contact-angle validation and does not justify dynamic impact cases.

## Purpose

B4 showed that the controlled Stage17B write path was stable but short-run morphology response was not validated. B5 checks the next producer-consumer link:

```text
PsiWallGhost / WallGhost
  -> STAGE13_PHASE_FOR_STENCIL
  -> gradPhi / mu / Fphi
  -> h update
  -> PhaseFromH
```

The question is narrow:

```text
Does the controlled curved WallGhost value enter the downstream phase stencil near the contact line, and does the diagnostic sign differ between theta=60 and theta=120?
```

## Code Changes

Implemented default-off consumption diagnostics:

```text
Stage17BConsumptionDiagnosticsMode = 0 by default
```

New B5 fields are output-only runtime diagnostics:

```text
B5SignedDistance
B5NearWallBandFlag
B5ContactLineBandFlag
B5WallGhostConsumedFlag
B5GhostUseCount
B5WallGhostMinusCenter
B5WallGhostMinusFluidProbe
B5WallGhostClampHitNeighbor
B5GradPhiNormal
B5GradPhiTangentialMag
B5FphiSum
B5FphiNormalProxy
B5PhaseFromHDelta
B5ExpectedResponseSign
B5SignalSignOK
```

Important TCLB-specific fix:

```text
Field(dx,dy,dz) template-style access cannot consume runtime variables.
```

The first remote compile failed because B5 used dynamic offsets in static field access:

```text
WallGhost(probe_dx, probe_dy, probe_dz)
WallGhostClampHit(probe_dx, probe_dy, probe_dz)
PhaseF(-probe_dx, -probe_dy, -probe_dz)
```

This was fixed by using a constant-branch wrapper for static `WallGhost` fields and `PhaseF_dyn` for the dynamic fluid probe:

```text
STAGE17B_STATIC_NEIGHBOR(WallGhost, probe_dx, probe_dy, probe_dz)
STAGE17B_STATIC_NEIGHBOR(WallGhostClampHit, probe_dx, probe_dy, probe_dz)
PhaseF_dyn(-probe_dx, -probe_dy, -probe_dz)
```

The source audit was extended so this TCLB access-semantics mistake is now caught before remote compile:

```text
b5_writer_uses_tclb_safe_neighbor_access = true
```

The case generator was also made repeatable. It now overwrites the generated `case.xml` and `case_metadata.json` instead of failing when a previous `_b5consume` directory already exists.

## Runtime Setup

```text
server = yuan@192.168.1.16
GPU request = CUDA_VISIBLE_DEVICES=1
visible GPU list includes GPU 1 = Tesla P100-PCIE-16GB
run root = /mnt/usb1t/RUNS/runs/stage17B_B5_consumption_probe_20260624
local artifact root = artifacts/stage17B_B5_consumption_20260624/runtime_probe_600
binary = /home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
binary sha256 = afdff38a0afba98ca74a8408ba1c8a4fbf151f558eb3a2f3f7899349c32fa07f
iterations = 600
vtk period = 200
log period = 100
```

Cases:

```text
cylinder_init090_to060_b5consume
cylinder_init090_to090_b5consume
cylinder_init090_to120_b5consume
```

All cases use:

```text
Stage17BDiffuseSolidMode = 1
Stage17BWriteMode = 2
Stage17BConsumptionDiagnosticsMode = 1
ReplayDiagnosticsMode = 1
WallCompactStencilMode = 0
legacy radAngle = 90d
Stage17BShadowThetaDeg = 60 / 90 / 120
```

All three solver cases finished:

```text
cylinder_init090_to060_b5consume RC=0
cylinder_init090_to090_b5consume RC=0
cylinder_init090_to120_b5consume RC=0
```

## Analyzer Note

The first runner ended with:

```text
done.status = DONE ... rc=1
```

This was not a solver failure. It was an analyzer-rule error: the original B5 analyzer treated the neutral `theta=90` control case as a directional sign failure. In the solver diagnostics, `B5ExpectedResponseSign=0` for theta 90, so `B5SignalSignOK=0` means "not applicable", not "wrong direction".

The analyzer was corrected to apply the signal-direction gate only when:

```text
abs(B5ExpectedResponseSign) > 0.5
```

After reanalysis on the same VTI outputs:

```text
stage17B_B5_consumption_analysis.json status = PASS_STAGE17B_B5_CONSUMPTION_PROBE
failures = []
```

## B3 Write Audit During B5

The existing B3 write-audit analyzer also passes on the B5 cases:

```text
stage17B_shadow_analysis.json status = PASS_STAGE17B_B3_WRITE_AUDIT
failures = {}
```

Final frame at step 600:

| case | applied cells | path170 cells | WallGhost-Psi mismatch | PsiWallGhost OOB cells | NearWallForceOverRho max |
|---|---:|---:|---:|---:|---:|
| cylinder_init090_to060_b5consume | 19928 | 19928 | 0 | 0 | 1.9745632692983438e-05 |
| cylinder_init090_to090_b5consume | 19928 | 19928 | 0 | 0 | 2.3010146335748696e-05 |
| cylinder_init090_to120_b5consume | 19928 | 19928 | 0 | 0 | 9.665455046285307e-05 |

This confirms that the B3 controlled write path remains active and bounded during B5.

## B5 Consumption Result

Final frame at step 600:

| case | contact-line cells | consumed cells | consumed fraction | expected sign | signal OK fraction | PhaseField min/max | nonfinite |
|---|---:|---:|---:|---:|---:|---:|---:|
| cylinder_init090_to060_b5consume | 2770 | 1306 | 0.471480 | +1 | 0.794793 | -1.0808570205751096e-04 / 1.0002993238488238 | 0 |
| cylinder_init090_to090_b5consume | 2448 | 1112 | 0.454248 | 0 | n/a | -1.0724334668333894e-04 / 1.0001262483583762 | 0 |
| cylinder_init090_to120_b5consume | 2669 | 1233 | 0.461971 | -1 | 0.980535 | -1.0935461166732161e-04 / 1.0001054456874825 | 0 |

The central evidence:

```text
WallGhost is being consumed by the contact-line stencil in about 45-47 percent
of contact-line band cells at the final frame.
```

Directional diagnostic:

```text
theta 60: B5GradPhiNormal mean = -0.0939079887
theta 120: B5GradPhiNormal mean = +0.0998772745

theta 60: B5FphiNormalProxy mean = -0.0951548114
theta 120: B5FphiNormalProxy mean = +0.1017935819
```

This means B5 successfully proves that the controlled `WallGhost` signal is not merely written; it reaches the downstream gradient/Fphi diagnostic path with opposite signs for 60 and 120 degree targets.

## Important Limitation

B5 also shows:

```text
B5PhaseFromHDelta max_abs ~= 3.3e-16
```

This is not evidence that contact-line motion is physically correct. It means the specific same-step diagnostic `phase_from_h_after - C` is nearly zero at the sampled point in the current call location. The useful B5 evidence is therefore:

```text
write path works
stencil consumption occurs
gradPhi/Fphi sign changes with target theta
no nonfinite PhaseField appears over 600 steps
```

It does not yet prove:

```text
static apparent contact angle converges correctly
curved morphology response is correct
mass/force/stress closure is physically closed
dynamic impact is ready
```

## Interpretation

B4 raised a downstream-coupling concern because morphology did not respond cleanly despite successful writes. B5 narrows the failure path:

```text
not primarily: controlled WallGhost write missing
not primarily: WallGhost completely ignored by the stencil
not primarily: immediate NaN/nonfinite failure
```

The remaining likely problem is further downstream or in metric interpretation:

```text
1. The consumed ghost signal affects gradPhi/Fphi but the phase update is too weak, delayed, or damped to move morphology over B4 timescales.
2. The phase equation / h population update may not convert the local wetting signal into robust contact-line displacement.
3. The morphology metric used in B4 may be too crude for curved geometry and should be replaced by a contact-line/interface-distance metric.
4. The raw ghost/clamp behavior may still distort the response, especially for obtuse targets.
5. The older Stage14 force/stress/pressure closure line remains relevant, but B5 does not by itself prove it is the dominant cause.
```

## Next Required Gate

Do not proceed to dynamic impact.

The next useful step is Stage17B-B6, not another blind morphology run:

```text
1. Add time-lag diagnostics:
   compare WallGhost at step n with gradPhi/Fphi and PhaseFromH at step n+1.

2. Add contact-line integrated response metrics:
   integrated normal Fphi proxy,
   integrated gradPhi normal,
   contact-line displacement relative to analytic SDF,
   phi=0.5 interface displacement along the wall normal.

3. Repeat the same cylinder 90->60 / 90 / 120 cases at 600-3000 steps.

4. Decide whether failure is:
   phase-update damping,
   one-step lag measurement issue,
   clamp-dominated ghost,
   sign convention at morphology level,
   or force/stress closure feedback.
```

Only after B6 demonstrates that the consumed signal produces coherent contact-line displacement should the project return to static contact-angle convergence on cylinder/sphere.

## Artifacts

Committed lightweight evidence:

```text
artifacts/stage17B_B5_consumption_20260624/source_audit.json
artifacts/stage17B_B5_consumption_20260624/runtime_probe_600/stage17B_B5_consumption_analysis.json
artifacts/stage17B_B5_consumption_20260624/runtime_probe_600/stage17B_B5_consumption_frames.csv
artifacts/stage17B_B5_consumption_20260624/runtime_probe_600/stage17B_B5_consumption_reanalysis_stdout.json
artifacts/stage17B_B5_consumption_20260624/runtime_probe_600/stage17B_shadow_analysis.json
artifacts/stage17B_B5_consumption_20260624/runtime_probe_600/stage17B_shadow_frames.csv
artifacts/stage17B_B5_consumption_20260624/runtime_probe_600/run_manifest.txt
artifacts/stage17B_B5_consumption_20260624/runtime_probe_600/binary_sha256.txt
artifacts/stage17B_B5_consumption_20260624/runtime_probe_600/done.status
artifacts/stage17B_B5_consumption_20260624/runtime_probe_600/*/case.xml
artifacts/stage17B_B5_consumption_20260624/runtime_probe_600/*/case_metadata.json
artifacts/stage17B_B5_consumption_20260624/runtime_probe_600/*/run.log
artifacts/stage17B_B5_consumption_20260624/runtime_probe_600/*/run.status
artifacts/stage17B_B5_consumption_20260624/runtime_probe_600/*/run.stderr
```

Large VTI/PVTI files are not committed.

## Verdict

Stage17B-B5 passes as a producer-consumer diagnostic gate. The controlled curved `WallGhost` value is written, consumed by the near-wall/contact-line stencil, and produces opposite-sign gradient/Fphi diagnostics for 60 and 120 degree targets.

This closes one important suspected failure path from B4, but it does not validate curved contact angles. The next root-cause step is B6 time-lag/contact-line displacement diagnostics.
