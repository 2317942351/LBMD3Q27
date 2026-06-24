# Stage17B-B7 Cylinder Long-Response Gate at 2000 Steps

Date: 2026-06-24

Status:

```text
remote solver: RC=0 for all 3 cylinder cases
B3 write audit: PASS_STAGE17B_B3_WRITE_AUDIT
B5 consumption: PASS_STAGE17B_B5_CONSUMPTION_PROBE
B6 contact-line lag: PASS_STAGE17B_B6_ANALYSIS
claim limit: long-response diagnostic only; not contact-angle validation
```

This is not static contact-angle validation and does not justify dynamic impact cases.

## Runtime Setup

```text
server = yuan@192.168.1.16
GPU request = CUDA_VISIBLE_DEVICES=1
visible GPU 1 = Tesla P100-PCIE-16GB
run root = /mnt/usb1t/RUNS/runs/stage17B_B7_long_response_2000_20260624
binary = /home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
binary sha256 = afdff38a0afba98ca74a8408ba1c8a4fbf151f558eb3a2f3f7899349c32fa07f
iterations = 2000
vtk period = 500
log period = 200
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

## Result

All three solver cases completed:

```text
cylinder_init090_to060_b5consume RC=0
cylinder_init090_to090_b5consume RC=0
cylinder_init090_to120_b5consume RC=0
done.status = DONE ... rc=0
```

No raw VTI/PVTI files are committed.

## Diagnostic Summary

Final step 2000:

| case | expected | B5FphiNormalProxy mean | contact half-width delta | near-wall mean abs phase delta | phase min/max | verdict |
|---|---|---:|---:|---:|---:|---|
| cylinder_init090_to060_b5consume | spread | -0.1039276659 | +2.637603702 deg | 0.0219645973 | -1.152e-4 / 1.000275 | toward target |
| cylinder_init090_to090_b5consume | control | +0.0154647973 | -3.416588192 deg | 0.0118560757 | -1.163e-4 / 1.000130 | control drift |
| cylinder_init090_to120_b5consume | retract | +0.1071926353 | -5.076870561 deg | 0.0181490347 | -1.105e-4 / 1.000104 | toward target |

The pair classification remains:

```text
driver_opposite_sign_60_120 = true
geometry_pair_direction = toward_targets
interpretation = driver_and_geometry_direction_consistent_short_run
```

This confirms that the 600-step B6 finding was not a one-frame artifact. The controlled curved wetting signal still produces opposite contact-line trends at 2000 steps.

## Important Problem

The `90 -> 90` control drift grew from about `-1.80 deg` at 600 steps to about `-3.42 deg` at 2000 steps.

That is now the main blocker. A neutral curved 90-degree target should not show a persistent retraction trend of this magnitude if the baseline initialization, neutral WallGhost formula, phase equation, and force closure are all unbiased.

The likely explanations are:

```text
1. The initial cylinder cap is not an equilibrium state for the current phase-field solver, even at nominal 90 degrees.
2. The curved 90-degree WallGhost formula is not exactly neutral in the current TCLB stencil/time-level semantics.
3. The phase equation has a baseline diffusion/mobility bias near curved walls.
4. The Stage14 force/stress/pressure closure injects a weak retraction bias.
5. The contact-line half-width metric is more sensitive than the visual morphology and should be cross-checked against fitted angle and mass/area metrics.
```

## Interpretation

B7 moves the project forward, but it does not close validation.

Less likely as dominant causes:

```text
WallGhost write missing
WallGhost ignored by the stencil
short-run contact-line response absent
P100 runtime instability for these 2000-step cases
```

Still open and now higher priority:

```text
neutral-angle baseline drift
long-run equilibrium angle convergence
mass/phase drift influence
pressure/stress/force closure feedback
sphere transferability
```

## Next Required Gate

Do not proceed to dynamic impact.

The next gate should be a neutral-control audit before 12000-step production:

```text
B8-neutral:
  run/init variants with Stage17BShadowThetaDeg=90
  compare Stage17BWriteMode=0 vs Stage17BWriteMode=2
  compare controlled curved WallGhost active vs legacy analytic WallGhost
  track contact half-width, fitted angle, mass/area, B5FphiNormalProxy, WallGhostMinusCenter
```

The central question:

```text
Does the 90-degree drift exist without the controlled write path?
```

If yes, the problem is baseline phase/force/initialization closure. If no, the problem is the curved controlled WallGhost neutral formula or its stencil consumption semantics.

Only after the neutral baseline is bounded should the project run 12000-step cylinder and then sphere B5/B6.

## Artifacts

Committed lightweight evidence:

```text
cases/diagnostics/stage17B_B7_long_response_2000_20260624/
artifacts/stage17B_B7_long_response_2000_20260624/stage17B_shadow_analysis.json
artifacts/stage17B_B7_long_response_2000_20260624/stage17B_shadow_frames.csv
artifacts/stage17B_B7_long_response_2000_20260624/stage17B_B5_consumption_analysis.json
artifacts/stage17B_B7_long_response_2000_20260624/stage17B_B5_consumption_frames.csv
artifacts/stage17B_B7_long_response_2000_20260624/B6_contactline_lag/stage17B_B6_contactline_lag_analysis.json
artifacts/stage17B_B7_long_response_2000_20260624/B6_contactline_lag/stage17B_B6_contactline_lag_frames.csv
artifacts/stage17B_B7_long_response_2000_20260624/B6_contactline_lag/stage17B_B6_contactline_initial_final_panel.png
artifacts/stage17B_B7_long_response_2000_20260624/B6_contactline_lag/stage17B_B6_contactline_timeseries.png
artifacts/stage17B_B7_long_response_2000_20260624/*/case.xml
artifacts/stage17B_B7_long_response_2000_20260624/*/case_metadata.json
artifacts/stage17B_B7_long_response_2000_20260624/*/run.log
artifacts/stage17B_B7_long_response_2000_20260624/*/run.status
artifacts/stage17B_B7_long_response_2000_20260624/*/run.stderr
```

## Verdict

Stage17B-B7 passes as a 2000-step long-response diagnostic. The cylinder 60 and 120 degree targets continue to move in the expected opposite directions, and the controlled WallGhost/Fphi signal remains active and bounded.

The current root problem is now sharper: the 90-degree neutral control drifts. The next work should isolate whether that drift comes from the controlled curved WallGhost path or from the baseline phase/force/initialization closure.
