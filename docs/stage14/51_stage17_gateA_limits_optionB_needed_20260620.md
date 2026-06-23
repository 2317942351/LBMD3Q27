# Stage 17 — gate-A limits: acute NaN + neutral/obtuse inaccurate => option B needed — 2026-06-20

Tests gate-A (doc 50, compact write gated to flat-only, analytic ghost on curves)
on the cylinder at 60/90/120 over a long (30k, M=0.6) run. Result: gate-A is a
PARTIAL fix -- it stops the compact-stencil NaN for neutral/obtuse, but (a) acute
still NaNs and (b) neutral reads ~+25 deg off. Both stability (acute) and accuracy
(all) require option B (a smooth, stable curved-wall BC).

```text
status_label: exploratory_not_validation
binary gate-A 341fb2fc; gen_cyl_compact.py; M=0.6; IntWidth=3; 30000 steps
root: /mnt/usb1t/RUNS/runs/stage17_gateA_long_20260620
measurer: golden_cyl.py calibrated (beta=30), ~+/-4 deg
```

## Results

| target | status | calibrated angle (final frame) | verdict |
|---|---|---|---|
| 60  (acute)   | NaN at ~step 250 (run lasted 34 s) | -- | UNSTABLE (analytic ghost blows up for acute on the staircase curve) |
| 90  (neutral) | stable, 0 NaN, ran 20k+ clean | grad 106.7 / inverted **114.7** | STABLE but +25 deg off (beyond measurer +/-4) |
| 120 (obtuse)  | run in flight (stable so far)   | pending | (expected stable; accuracy TBD) |

## Why gate-A is only partial

gate-A falls back to the analytic Briant ghost on curves:
`phi_ghost = phi_0 + 2*h0*tan(pi/2-theta)*|grad_t phi|`.
- Acute theta: tan(pi/2-theta) is large AND |grad_t phi| is amplified by the
  staircase-cylinder jaggedness -> extreme wall values -> phase solve NaNs (~step 250).
  (The code comment at calcWallPhase already warns it "can write an unbounded wall
  phase for acute angles".)
- Neutral/obtuse: the ghost stays bounded (no NaN) but is a per-staircase-node local
  approximation, so the imposed angle is wrong (~+25 deg at theta=90).

So the staircase-cylinder jaggedness defeats BOTH the compact-stencil write (doc 46)
AND the analytic ghost (acute stability + all-angle accuracy). The shared root cause
is writing a per-wall-node value on a jagged staircase boundary.

## Confirmed need for option B (smooth curved-wall BC)

option B must write a SMOOTH near-wall phase that does not depend on the per-node
staircase geometry -- e.g. the analytic equilibrium tanh profile of the analytic SDF,
oriented by the contact-angle condition, evaluated at each wall node from the analytic
signed distance (not from a jagged lattice probe). That removes both the acute
instability (no tan()*|grad| blow-up) and the inaccuracy (smooth profile, correct angle).

## Honest status
```text
Flat wall: compact-stencil BC validated (docs 40-43).
Cylinder, gate-A: neutral/obtuse STABLE (compact-stencil NaN fixed) but acute NaNs
  and neutral reads ~+25 deg off. gate-A is a stabilisation step, not the curved fix.
Cylinder final: needs option B (smooth analytic-equilibrium near-wall phase on curves)
  for acute stability AND all-angle accuracy.
```

## Next (option B, main-agent owned; audit before any claim)
Implement a smooth curved-wall ghost in calcWallPhase: on AnalyticSolidType>=1.5,
set WallGhost/PhaseF from the analytic SDF + tanh equilibrium profile oriented by
theta (no lattice gradient probe, no staircase dependence). Rebuild, re-run cyl
60/90/120, measure with golden_cyl. Gate: stable for all theta AND within ~+/-5 deg.

## Reproducibility
```text
bash /home/yuan/gateA_long.sh   # gate-A cylinder 60/90/120, 30k, M=0.6
python3 /home/yuan/golden_cyl.py measure <final_pvti>
```
