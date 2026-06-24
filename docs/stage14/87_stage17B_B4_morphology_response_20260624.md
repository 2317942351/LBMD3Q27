# Stage17B-B4 Static Morphology Response Smoke

Date: 2026-06-24

Status:

```text
runtime/write audit: PASS_STAGE17B_B3_WRITE_AUDIT
morphology smoke: PASS_STAGE17B_B4_MORPHOLOGY_SMOKE
response assessment: B4_RESPONSE_NOT_VALIDATED
```

This is not contact-angle validation. It is a short-run morphology response smoke test designed to check whether the B3 controlled `WallGhost` write path produces an obvious interface-shape response on curved solids.

## Purpose

B3 proved that the controlled curved write path can replace `WallGhost` with bounded `PsiWallGhost` on analytic cylinder/sphere nodes, while remaining blocked on flat analytic walls.

B4 asks the next, more physical question:

```text
if the initial cap is 90 degrees, and Stage17BShadowThetaDeg is set to 60 or 120,
does the droplet visibly move in the expected direction within a short run?
```

Expected qualitative response:

```text
90 -> 60: spread / lower apparent angle / larger footprint
90 -> 90: near-stationary control
90 -> 120: retract / higher apparent angle / smaller footprint or taller cap
```

## Runtime Setup

```text
server = yuan@192.168.1.16
run root = /mnt/usb1t/RUNS/runs/stage17B_B4_morphology_20260624
GPU request = CUDA_VISIBLE_DEVICES=1
binary = /home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
binary sha256 = 2c61762bcfbf2e4955b4e0fff84ba2c746d698e1ba267c31a1dbb6d8558c226c
iterations = 3000
vtk period = 1000
done.status = DONE /mnt/usb1t/RUNS/runs/stage17B_B4_morphology_20260624 rc=0
```

All six solver cases finished with `RC=0`.

Cases:

```text
cylinder_init090_to060_b3morph
cylinder_init090_to090_b3morph
cylinder_init090_to120_b3morph
sphere_init090_to060_b3morph
sphere_init090_to090_b3morph
sphere_init090_to120_b3morph
```

All cases use:

```text
Stage17BDiffuseSolidMode = 1
Stage17BWriteMode = 2
WallCompactStencilMode = 0
legacy radAngle = 90d
Stage17BShadowThetaDeg = 60 / 90 / 120
```

Thus the target-angle perturbation is isolated to the Stage17B controlled write path, not the old `radAngle` ghost path.

## Write-Audit Result

The existing B3 analyzer was also run on the B4 cases:

```text
stage17B_shadow_analysis.json status = PASS_STAGE17B_B3_WRITE_AUDIT
failures = {}
```

Final frame at step 3000:

| case | applied cells | path170 cells | WallGhost-Psi max diff | PhaseField min/max | PhaseField nonfinite | NearWallForceOverRho max | PsiWallGhostRaw min/max |
|---|---:|---:|---:|---:|---:|---:|---:|
| cylinder_init090_to060_b3morph | 19928 | 19928 | 0.0 | -0.00011852862559132314 / 1.0002648828475182 | 0 | 1.9870973169558343e-05 | -9.280563623684673e-05 / 1.264775255651797 |
| cylinder_init090_to090_b3morph | 19928 | 19928 | 0.0 | -0.00011722933071387274 / 1.0001202136084795 | 0 | 2.6500013575518582e-05 | -0.00011467227280665619 / 1.0001202136084795 |
| cylinder_init090_to120_b3morph | 19928 | 19928 | 0.0 | -0.00011119376357769187 / 1.0001059081102712 | 0 | 9.423956930572041e-05 | -0.3539864067699733 / 1.0000831698598756 |
| sphere_init090_to060_b3morph | 7208 | 7208 | 0.0 | -6.664209886979925e-05 / 1.0001471287474017 | 0 | 1.1807172797184433e-05 | -4.055917833377658e-05 / 1.2872630538852978 |
| sphere_init090_to090_b3morph | 7208 | 7208 | 0.0 | -7.570857527622031e-05 / 1.0001829528271111 | 0 | 1.3371411819855921e-05 | -7.57085752762203e-05 / 1.000124856648422 |
| sphere_init090_to120_b3morph | 7208 | 7208 | 0.0 | -8.073323022833741e-05 / 1.0001584057836381 | 0 | 9.437325903851186e-05 | -0.21777564706300231 / 1.0000754900314837 |

This confirms that the B3 write path still works during the morphology smoke. It does not confirm that the physical response is correct.

## Morphology Figures

Main panel:

```text
artifacts/stage17B_B4_morphology_20260624/post/morphology/stage17B_B4_morphology_initial_final_panel.png
```

Per-case figures are under:

```text
artifacts/stage17B_B4_morphology_20260624/post/morphology/<case>/<case>_initial_final.png
```

The figures show the center-plane `PhaseField`, the `phi=0.5` interface contour, and the analytic solid cross-section. They are morphology diagnostics, not final measured contact-angle figures.

## Response Assessment

Response assessment:

```text
artifacts/stage17B_B4_morphology_20260624/post/morphology/stage17B_B4_response_assessment.json
status = B4_RESPONSE_NOT_VALIDATED
```

Summary from first to final frame:

| case | expected response | verdict | area delta | footprint delta | height delta | acute-angle delta |
|---|---|---|---:|---:|---:|---:|
| cylinder_init090_to060_b3morph | spread | direction_opposite_or_not_coupled | -24 | -2 | +1 | +0.385 |
| cylinder_init090_to090_b3morph | control | control_drift | -8 | 0 | -2 | +0.460 |
| cylinder_init090_to120_b3morph | retract | direction_opposite_or_not_coupled | -2 | 0 | -3 | +0.978 |
| sphere_init090_to060_b3morph | spread | direction_opposite_or_not_coupled | -8 | -2 | +1 | -1.271 |
| sphere_init090_to090_b3morph | control | control_stable | -2 | 0 | 0 | -0.540 |
| sphere_init090_to120_b3morph | retract | weak_or_mixed_response | -2 | 0 | -1 | -2.602 |

Interpretation:

```text
runtime stability: good
B3 write activation: good
bounded PsiWallGhost write: good
short-run morphology direction: not validated
```

The negative/weak response is important. It means the project should not proceed to dynamic impact or claim curved contact-angle correctness from B3 alone.

## What This Means Mechanistically

B3 answered:

```text
Can the diffuse-solid shadow value be written into WallGhost at the intended curved nodes?
Yes.
```

B4 shows the next link is still not closed:

```text
WallGhost/PsiWallGhost -> near-wall gradient/mu/Fphi -> h update -> PhaseFromH -> interface motion
```

The likely problem has moved downstream of write activation. Plausible next failure points are:

```text
1. The ghost value is written but diluted or overwritten before calcGradPhi/calcMu/h update consumes it.
2. The written WallGhost changes diagnostics but does not enter the stencil path that drives Fphi strongly enough.
3. The B3 ghost sign/convention is still opposite for one or more curved geometries.
4. Curved init/measurement geometry is not yet aligned with the intended apparent-angle convention.
5. The phase advection / force closure still damps or reverses the expected contact-line response.
```

The raw ghost shadow also shows large unclamped excursions in 120-degree cases. The solver writes the bounded `PsiWallGhost`, but the raw values suggest the compact formula is being clipped substantially at obtuse targets. That can weaken or distort the response and must be quantified before tuning.

## Next Required Gate

Do not continue to dynamic impact.

The next gate should be Stage17B-B5 focused on the producer-consumer path:

```text
1. Add or extract per-frame near-wall consumption diagnostics:
   WallGhost, PhaseF, calcGradPhi input, calcMu input, Fphi, h pre/post, PhaseFromH.

2. Run a shorter 90->60 and 90->120 pair with VTI every 250-500 steps.

3. For contact-line band cells only, report:
   ghost minus fluid phase,
   ghost clamp fraction,
   gradPhi normal component,
   Fphi contribution sign,
   PhaseFromH delta near the contact line.

4. Decide whether the failure is:
   sign convention,
   clamp-dominated ghost,
   ghost not consumed by the stencil,
   phase equation damping,
   or force/pressure/stress closure.
```

Only after B5 shows the target-angle signal enters `PhaseFromH` with the correct sign should longer static contact-angle cases be run.

## Artifacts

Committed lightweight evidence:

```text
artifacts/stage17B_B4_morphology_20260624/stage17B_shadow_analysis.json
artifacts/stage17B_B4_morphology_20260624/stage17B_shadow_frames.csv
artifacts/stage17B_B4_morphology_20260624/post/morphology/stage17B_B4_morphology_summary.json
artifacts/stage17B_B4_morphology_20260624/post/morphology/stage17B_B4_morphology_frames.csv
artifacts/stage17B_B4_morphology_20260624/post/morphology/stage17B_B4_response_assessment.json
artifacts/stage17B_B4_morphology_20260624/post/morphology/stage17B_B4_response_assessment.csv
artifacts/stage17B_B4_morphology_20260624/post/morphology/*.png
artifacts/stage17B_B4_morphology_20260624/*/case.xml
artifacts/stage17B_B4_morphology_20260624/*/case_metadata.json
artifacts/stage17B_B4_morphology_20260624/*/run.log
artifacts/stage17B_B4_morphology_20260624/*/run.status
artifacts/stage17B_B4_morphology_20260624/*/run.stderr
```

Large VTI/PVTI files are not committed.

## Verdict

Stage17B-B4 is a successful diagnostic gate but a failed/insufficient physical response gate.

The project made a real step forward because the failure is now localized more tightly:

```text
not blocked at GPU runtime
not blocked at curved write activation
not blocked by flat-wall accidental writes
not blocked by immediate nonfinite instability
blocked at physical response transfer from WallGhost to interface motion
```

The next work must trace that transfer path directly instead of tuning target angles, grid size, or dynamic impact parameters.
