# Stage11 — W/R Convergence Audit Design

Date: 2026-06-14
Status: authorized (reviewer 2026-06-14). No code change. Uses existing
stage9 binary (Briant formula, plane wall). Decisive question only.

## The single question Stage11 must answer

**Is the theta=30 -> 35.65 deg contact-angle error dominated by the finite
interface width W relative to the droplet radius R_drop (i.e. does the error
scale as W/R_drop)?**

- If YES: the error is bulk-discretization-dominated. Pivot to IntWidth /
  mesh / radius selection. Wall-surface BC redesign is NOT needed.
- If NO: the error is not explained by W/R scaling. Re-authorize wall-surface
  BC design as the next step.

No other claim is made by Stage11.

## Why two sweeps (not one)

The single ratio W/R can be changed by varying W (at fixed R) or by varying R
(at fixed W). If the error is truly governed by the ratio, BOTH sweeps must
show the same scaling. If only one sweep shows scaling, the error is governed
by something else (e.g. absolute W, or absolute R, or grid resolution). So
Stage11 runs both.

## Test matrix

All cases: plane wall, theta=30 (the load-bearing case), stage9 binary with
AnalyticWetting=1, Briant formula. BubbleType droplet initializer. tauUpdate=1.
100000 steps (sufficient for static-angle convergence at this theta; verified
in stage9 at 200k that the angle is stable by 100k).

### Sweep 1: fixed R=24, vary IntWidth W in {6, 4, 3, 2}

Grid must resolve W: require dx <= W/4, so for W=2 use dx=0.5 (double the
linear resolution). Concretely:

```
W=6: grid 96x64x96, dx=1, R=24   (R/W = 4)    [baseline: 35.65 deg known]
W=4: grid 96x64x96, dx=1, R=24   (R/W = 6)
W=3: grid 96x64x96, dx=1, R=24   (R/W = 8)
W=2: grid 192x128x192, dx=0.5, R=24 (R/W = 12)  [halve dx to resolve W=2]
```

Capillary-number consistency: keep `sigma` and `M` fixed so the physical
surface tension and mobility are unchanged; only the discretized interface
width changes. The droplet equilibrates to the same physical angle (modulo
discretization) in each case.

### Sweep 2: fixed W=6, vary R_drop in {12, 24, 48}

Grid scales with R to keep R/(grid) fixed:

```
R=12: grid 64x48x64,   dx=1, W=6  (R/W = 2)
R=24: grid 96x64x96,   dx=1, W=6  (R/W = 4)    [baseline: 35.65 deg known]
R=48: grid 192x128x192, dx=1, W=6 (R/W = 8)
```

## Pass / redirect criteria

**Expected if H_bulk (W/R scaling) holds:** the measured angle approaches 30
deg as W/R decreases, for BOTH sweeps, and the two sweeps agree at matched
W/R. Specifically, plotting `measured_angle - 30` vs `W/R` should collapse
both sweeps onto a single monotonic curve through the origin.

**REDIRECT to IntWidth/mesh/radius selection (H_bulk confirmed):**
- Both sweeps show the error decreasing as W/R decreases.
- At the smallest W/R tested (W=2 R=24, i.e. R/W=12; and W=6 R=48, i.e. R/W=8),
  the error is < 2 deg OR clearly trending below 2 deg with a quantifiable rate.

**RE-AUTHORIZE wall-surface BC design (H_bulk rejected):**
- The error does NOT decrease as W/R decreases (or decreases much slower
  than linear), in either sweep, OR
- The two sweeps disagree at matched W/R (the ratio is not the governing
  parameter).

**INCONCLUSIVE (rare):** one sweep scales, the other does not. Report and
request direction.

## What is NOT done in Stage11

- No sphere, no cylinder (plane only — the question is about W/R, not curvature).
- No code change to the stage9 binary.
- No theta sweep (theta=30 only — it is the load-bearing case).
- No claim about "the error is fixed" — only about whether it scales as W/R.

## Risk: stability at small W

The Fakhari-Mitchell model can become unstable at small IntWidth (the
interface sharpening increases gradient magnitudes). If W=2 or W=3 cases
diverge (NaN), that is itself a finding (the model cannot reach the W/R needed
for <2 deg at this sigma/M), and is reported as such. No fallback to larger W
to "get a result" — the divergence is reported.
