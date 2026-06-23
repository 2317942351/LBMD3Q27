# Stage 15D Result — calibrated contact-angle measurement REVERSES the WallGhostV2 pivot — 2026-06-20

D1 (measurement cross-validation) was performed with a self-calibrated angle
measurer. The result OVERTURNS the premise of doc 39: **the compact-ghost
static WallGhost BC is CORRECT.** The "eq30=24 deg / static BC broken" finding
was an artefact of the un-calibrated DynamicCLThetaApp band-average diagnostic.
WallGhostV2 is NOT needed. The DynamicCL force (sign fixed in doc 38) has zero
net macroscopic effect on contact-line relaxation.

```text
status_label: exploratory_not_validation
scope: read-only post-processing of existing VTIs + synthetic self-validation;
       no new runs, no source change, no push.
significance: reverses doc 39's pivot-to-WallGhostV2 decision. Saves a major
              unnecessary refactor. Vindicates the D1 measurement-check gate.
```

## 1. The measurement problem D1 caught

Four angle estimators disagree by up to ~38 deg at the angle extremes:

| target | DynamicCLThetaApp (band-mean) | bbox h/a (uncalibrated) | local tangent | q=0.5 circle fit |
|---|---|---|---|---|
| 30 | 23.6 | 32.4 | 22-35 | 61.8 (ill-conditioned, 9 pts) |
| 90 | 88.4 | 88.5 | 79-88 | 0 (broken) |
| 150 | 149.0 | 123.9 | 45 (quadrant-broken) | 101.6 |

At theta=90 all sane estimators agree (~88-90). At the extremes they diverge.
DynamicCLThetaApp and bbox h/a are both biased but in opposite directions at
opposite ends. None was validated against ground truth.

## 2. Trusted measurer: bbox h/a calibrated against analytic tanh caps

Method: bbox sphere-cap theta = 2*atan(h/a), where h = droplet height, a =
contact radius (q>0.5 cells on a vertical centre z-slice). Self-validated by
generating synthetic tanh spherical caps of KNOWN theta (W=3, a=24, 96^3 grid,
the project's actual parameters) and reading them back.

Calibration (true theta -> bbox reading), averaged over 3 z-slices:

```text
true  30 -> reads 25.1      true  90 -> reads 88.8      true 150 -> reads 123.8
true  60 -> reads 57.9      true 120 -> reads 112.3
synth true=30 reads 25.1  =>  invert-back gives 30.0  (self-consistent)
```

The bbox method systematically UNDER-reads at the extremes due to lattice
discretisation. Inverting the real reading through this calibration curve gives
the true angle. (The circle-fit estimator is broken at low point counts and was
discarded.)

## 3. Equilibrium (init=target) -- STATIC BC IS CORRECT

Calibrated TRUE angle at step 4000:

| case | target | bbox reading | TRUE (calibrated) | error |
|---|---|---|---|---|
| eq30  | 30  | 29.4 | **32.3** | +2.3 |
| eq90  | 90  | 88.5 | **89.8** | -0.2 |
| eq150 | 150 | 123.8 | **149.8** | -0.2 |

All three equilibrium droplets settle at their prescribed contact angle within
+/-2.3 deg. **The compact-ghost static WallGhost wetting boundary works.**

=> The doc 39 conclusion "static WallGhost maps 30->24, must be refactored"
   was a measurement artefact. **WallGhostV2 (Stage 16A-C) is NOT needed.**

## 4. Changed-angle (init != target) -- slow relaxation, DynamicCL zero net effect

Calibrated TRUE angle trajectory (step 0 -> 4000). All three DynamicCL
conditions OVERLAY exactly (base Coeff=0 == cap=0.2 == cap=0.5):

| case | target | step0 TRUE | step4000 TRUE | direction |
|---|---|---|---|---|
| 60->30  | 30  | 62.2 | 58.6 | toward 30 (slow, ~3.6 deg / 4000 steps) |
| 120->150 | 150 | 115.5 | 121.4 | toward 150 (slow, ~5.9 deg / 4000 steps) |

Findings:
- Relaxation is in the CORRECT direction but SLOW (~3-6 deg per 4000 steps).
- DynamicCL force (FS=-1, cap=0.2 or 0.5) produces a trajectory INDISTINGUISHABLE
  from the Coeff=0 baseline. The force stirs the contact-line band (|U| rises,
  confirmed in doc 38/39) but does NOT translate into net contact-line advance.

## 5. What STANDS vs FALLS after this measurement correction

```text
STANDS:
  doc 38 DynamicCLForceSign=-1, CosSign=-1. The sign was established by the
         INDEPENDENT radial projection of ForceCandidateX/Z (gate_c1_force_dir.py),
         not by DynamicCLThetaApp. That evidence is measurement-independent.
  The DynamicCL hook (47a6d22, binary f00f8ff7) is code-verified and direction-correct.
FALLS (measurement artefacts of un-calibrated DynamicCLThetaApp / bbox):
  "eq30 settles at 24 deg"               -> actually ~32 deg (at target).
  "60->30 over-relaxes to 28 deg"        -> actually relaxes 62 -> 58.6 (slow, correct way).
  "120->150 regresses / wrong direction" -> actually 115 -> 121 (toward 150, slow).
  "obtuse sign problem (doc 37 issue)"   -> the doc-38 sign fix is still valid, but the
                                             *dynamic* effect it was meant to produce is nil.
  doc 39 "pivot to WallGhostV2"          -> REVERSED. Static BC is correct.
```

## 6. Revised problem statement

```text
The compact-ghost static wetting BC is correct (equilibrium at target).
The real behaviour: changed-angle relaxation is slow but in the correct
direction. The DynamicCL body force, even with the correct sign, has NO net
macroscopic effect on contact-line relaxation.
```

Two honest possibilities for the slow relaxation, to be distinguished next:
(a) The system is relaxing on its natural (slow) contact-line timescale; longer
    runs would reach target. I.e. nothing is broken, just under-resolved in time.
(b) Contact-line relaxation is genuinely under-driven (low effective contact-line
    mobility / the phase-field BC pins the line), and DynamicCL as a band body
    force cannot couple to net line advance.

DynamicCL as currently designed is NOT the lever: it stirs fluid but does not
move the pinned contact line. If faster relaxation is required, the approach
must change (e.g. a wall-level condition rather than a band body force), not
just its sign or magnitude.

## 7. Discipline note

This is exactly the failure mode the V&V discipline exists to catch: a major
refactor (WallGhostV2) was about to be undertaken on the basis of an un-validated
diagnostic (DynamicCLThetaApp band-mean). The D1 self-calibration gate -- measuring
the measurer against analytic truth -- reversed the decision with ~1 hour of work.
Code verification (the measurer) had to precede solution verification (the angle)
and validation (the BC).

## 8. Reproducibility

```text
# trusted, self-calibrating angle measurer (bbox h/a vs synthetic tanh caps):
/home/yuan/golden2.py eq                          # equilibrium calibrated table
/home/yuan/golden2.py traj <label> <target> <case_dir>   # calibrated trajectory
/home/yuan/golden_angle.py                       # the D1 cross-check + ASCII (earlier)
scripts mirrored locally: repo/scripts/stage13/{golden2.py, golden_angle.py,
  d1_angle_crosscheck.py, d1_ascii.py, d1_local_tangent.py}
calibration is self-contained (synthetic caps at W=3, a=24, 96^3 -- the run params).
```
