# Stage17B-B6 Contact-Line Lag Diagnostic

Date: 2026-06-24

Status:

```text
B5 evidence source: /mnt/usb1t/RUNS/runs/stage17B_B5_consumption_probe_20260624
B6 analyzer: PASS_STAGE17B_B6_ANALYSIS
driver pair classification: driver_and_geometry_direction_consistent_short_run
claim limit: contact-line lag/response diagnostic only; not contact-angle validation
```

This is not static contact-angle validation and does not justify dynamic impact cases.

## Purpose

B5 proved that the controlled curved `WallGhost` value is written and consumed by the near-wall/contact-line stencil. B6 checks the next question:

```text
Does that consumed WallGhost/Fphi signal produce measurable short-run contact-line motion,
or is the signal lost/damped after the source term?
```

B6 reuses the existing B5 run. It does not rerun TCLB and does not modify solver physics.

## Method

The offline analyzer reads the existing cylinder B5 VTI frames:

```text
cases:
  cylinder_init090_to060_b5consume
  cylinder_init090_to090_b5consume
  cylinder_init090_to120_b5consume
steps: 0, 200, 400, 600
run root: /mnt/usb1t/RUNS/runs/stage17B_B5_consumption_probe_20260624
```

It computes:

```text
analytic cylinder signed distance
near-wall interface/contact cells using 0.05 < PhaseField < 0.95
contact half-width around the cylinder top, measured from the +y liquid axis
near-wall PhaseField delta from step 0
2D mid-plane morphology metrics
B5 WallGhost/Fphi producer-consumer statistics
```

The primary response metric is:

```text
contact_half_width_w95_deg
```

For `90 -> 60`, spreading should increase this half-width. For `90 -> 120`, retraction should decrease it. The `90 -> 90` case is a control and should stay approximately stationary.

## Result

B6 passed as an offline analysis gate:

```text
status = PASS_STAGE17B_B6_ANALYSIS
driver_opposite_sign_60_120 = true
geometry_pair_direction = toward_targets
interpretation = driver_and_geometry_direction_consistent_short_run
```

Final step 600:

| case | expected | B5FphiNormalProxy mean | contact half-width delta | near-wall mean abs phase delta | verdict |
|---|---|---:|---:|---:|---|
| cylinder_init090_to060_b5consume | spread | -0.0951548114 | +2.023743839 deg | 0.0123887997 | toward target |
| cylinder_init090_to090_b5consume | control | +0.0147212605 | -1.803049259 deg | 0.0068822762 | control drift |
| cylinder_init090_to120_b5consume | retract | +0.1017935819 | -3.416588192 deg | 0.0107005609 | toward target |

The key improvement over B4 is that the response metric is now contact-line based instead of only global area/height. With this metric, 60 and 120 show the expected opposite-direction response over 600 steps.

## Figures

Committed figures:

```text
artifacts/stage17B_B6_contactline_lag_20260624/stage17B_B6_contactline_initial_final_panel.png
artifacts/stage17B_B6_contactline_lag_20260624/stage17B_B6_contactline_timeseries.png
```

The initial/final panel visually confirms that the change is small but measurable. The time-series panel shows:

```text
theta 60: contact half-width increases from 74.98 to 77.01 deg
theta 120: contact half-width decreases from 74.98 to 71.57 deg
theta 90: contact half-width drifts down to 73.18 deg
```

## Interpretation

B6 changes the current root-cause ranking.

Less likely as the primary failure path:

```text
controlled curved WallGhost not written
WallGhost ignored by gradient/Fphi stencil
source signal present but no contact-line response at all
```

More likely remaining issues:

```text
1. The contact-line response exists but is weak/slow and must be tested over longer runs.
2. The 90 degree control drifts, so there is still baseline numerical bias even without a target angle change.
3. The response metric is sensitive to contact-band and threshold definitions; it is diagnostic evidence, not a final angle measurement.
4. Long-run convergence may still fail because of Stage14 pressure/stress/force closure or mass/phase drift.
5. Cylinder success over 600 steps does not imply sphere success or dynamic-impact readiness.
```

The strongest scientific conclusion is:

```text
B5+B6 establish a functioning local curved wetting signal path for cylinder:
WallGhost write -> stencil consumption -> opposite-sign Fphi proxy -> measurable short-run contact-line response.
```

This is a meaningful step forward, but it is still below validation level.

## Remaining Problems

The `90 -> 90` control drift is not acceptable for validation. It means a neutral target still changes the contact half-width by about `-1.8 deg` over 600 steps. This can come from:

```text
legacy curvature/cap relaxation after initialization
baseline phase equation diffusion/mobility bias
force/stress/pressure closure feedback
contact-line metric sensitivity
WallGhost formula not exactly neutral at curved 90 deg
```

The `120` case also has a suspicious `contact_y_min_delta = -23` in the analytic contact-band metric. The visual panel and half-width trend are plausible, but this value means threshold-based near-wall contact detection is sensitive and should not be overinterpreted.

## Next Required Gate

Do not proceed to dynamic impact.

The next useful step is not another blind solver edit. Run a controlled B7 long-response gate:

```text
1. Repeat cylinder 90 -> 60 / 90 / 120 with B5/B6 diagnostics at 2000 and 12000 steps.
2. Keep Stage17BWriteMode=2 but do not modify PhaseF directly.
3. Track contact half-width, 2D fitted angle, mass/phase extrema, B5FphiNormalProxy, and 90-degree control drift.
4. If 60/120 continue toward targets and 90 drift remains bounded, proceed to sphere B5/B6.
5. If 90 drift grows or 60/120 reverse, return to neutral-angle WallGhost formula and Stage14 pressure/stress/force closure.
```

Suggested acceptance criteria for B7:

```text
PhaseField nonfinite = 0
PhaseField overshoot remains small and bounded
60 half-width trend stays positive relative to 90 control
120 half-width trend stays negative relative to 90 control
90 control drift is quantified and below a declared tolerance
no claim of contact-angle validation until final fitted angles converge
```

## Artifacts

Committed lightweight evidence:

```text
scripts/stage17/stage17B_B6_contactline_lag_analyze.py
artifacts/stage17B_B6_contactline_lag_20260624/stage17B_B6_contactline_lag_analysis.json
artifacts/stage17B_B6_contactline_lag_20260624/stage17B_B6_contactline_lag_frames.csv
artifacts/stage17B_B6_contactline_lag_20260624/stage17B_B6_contactline_initial_final_panel.png
artifacts/stage17B_B6_contactline_lag_20260624/stage17B_B6_contactline_timeseries.png
artifacts/stage17B_B6_contactline_lag_20260624/*/*_B6_contactline_lag.json
```

Raw VTI/PVTI files are not committed.

## Verdict

Stage17B-B6 passes as a contact-line lag diagnostic. The controlled curved wetting signal is not only consumed; over 600 steps it produces measurable and target-consistent short-run cylinder contact-line motion for 60 and 120 degrees.

The current blocker is no longer "WallGhost does nothing." The blocker is whether this local response converges into a stable, unbiased static contact angle, especially given the 90-degree control drift.
