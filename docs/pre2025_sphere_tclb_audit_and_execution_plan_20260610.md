# PRE 2025 Sphere TCLB Audit And Execution Plan

Status: `exploratory_not_validation`

Date: 2026-06-10

## User Goal Clarification

The current goal is not to reproduce the PRE 2025 model exactly. The goal is
to run the current TCLB phase-field routes under the same spherical static
wetting geometry and comparable metrics, then use the differences to calibrate
the route and diagnose errors.

Therefore, failed cases are diagnostic evidence for the current TCLB route,
not failed proof of the PRE 2025 article.

## Literature-Aligned Setup

The reduced Table II setup used here follows the article's reduced spherical
static wetting case:

```text
domain = 80 x 80 x 140 lu
R_drop = 24 lu
R_solid = 24 lu
theta = 30,40,50,60,70,80,90,100,110,120,130 deg
density ratio = 1000
dynamic viscosity ratio = 900
no gravity
static equilibrium metric = relative error of H1-H2
```

TCLB parameters used for the current comparison:

```text
Density_h = 1
Density_l = 0.001
Viscosity_h = 0.09
Viscosity_l = 0.1
tauUpdate = 3
M = 0.2
IntWidth = 6
sigma = 5e-5
```

The dynamic viscosity ratio is computed as:

```text
(Density_h * Viscosity_h) / (Density_l * Viscosity_l) = 900
```

## Intentional Model Differences

The PRE 2025 model is a D3Q19/D3Q19 conservative Allen-Cahn MRT route with its
own wetting boundary reconstruction. The current TCLB route is
`d3q27_pf_velocity` with q27 phase-field populations and optional geometric
wetting/staircase-improvement compile options.

This means the current results are TCLB analogue comparisons, not formula
equivalent PRE reproductions.

## Audit Findings Before The Next Run

1. The full `q27_geometric_staircaseimp` 200000-step batch produced negative
   evidence: theta030-080 and theta100-130 stopped at the first failcheck with
   PhaseField NaN messages while returning process code `0`; only theta090
   completed.

2. A short diagnostic matrix isolated the early NaN trigger to the
   `staircaseimp` route on the spherical boundary. Lowering `M` from 0.2 to
   0.05 or 0.025 did not prevent theta030/theta100 NaN, and changing
   `tauUpdate` from 3 to 1 did not prevent it. The `q27_geometric` route
   completed theta030/theta090/theta100 for 2000 steps.

3. A settings bug was found and fixed: `table_II_sphere_targets.csv` had been
   overwritten by a 3-angle diagnostic subset. The generator now always writes
   the full 11-angle reference target table even when generating a diagnostic
   subset.

4. A runner bug was found and fixed: `MODE=wait-run` used a broad `pgrep -f`
   pattern that could match the monitoring command itself. It now uses a
   stricter `ps | awk` filter for real TCLB `main` processes.

5. The runner now scans existing `run.log` before honoring an old `run.done`,
   so historical NaN-stopped cases cannot be skipped as clean completions.

## Current Execution Decision

Do not spend more time on long `q27_geometric_staircaseimp` runs for non-90
wetting angles until its spherical-boundary NaN trigger is understood.

The next useful run is a full-angle medium screen with the same geometry and
metrics using:

```text
binary = /home/yuan/src/TCLB/CLB/d3q27_pf_velocity_q27_geometric/main
binary sha256 = 3373620d4c4c8ba952a239bde02030d55ad5b8c5e0b637988bfcd05c111c58ba
steps = 20000
vtk interval = 10000
log/failcheck interval = 1000
remote root =
  /media/yuan/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_tableII_q27_geometric_screen_20260610
```

Acceptance for this screen is not a validation pass. It is a screening gate:

```text
all angles should avoid NaN/nonfinite stop
max Mach should remain far below 0.1
bulk fluid phase/rho drift should be reported
H1-H2 and fitted contact angle should show whether the route trends toward
the requested wetting response
```

If the 20000-step screen passes finite-field and Mach checks, the next step is
a 200000-step `q27_geometric` full-angle run. If the screen fails at non-90
angles, use the failure pattern to choose a smaller parameter matrix instead
of launching the long run.

## Completed q27_geometric 200000-Step Result

The full-angle `q27_geometric` 200000-step run completed after the 20000-step
screen:

```text
remote root =
  /media/yuan/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_tableII_q27_geometric_200k_20260610
local artifact =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_tableII_q27_geometric_200k_20260610
binary =
  /home/yuan/src/TCLB/CLB/d3q27_pf_velocity_q27_geometric/main
```

Finite-field and runtime findings:

```text
all 11 angles reached 200000 steps
run.returncode = 0 for every case
postprocess_returncode = 0 for every case
run-log NaN hits = 0
max_nonfinite_count = 0
max Mach over batch = 6.218e-4
NumSpecialPoints = 392 for every case
```

Quantitative comparison against Table II:

```text
mean TCLB H1-H2 relative error = 12.4967 %
max TCLB H1-H2 relative error = 32.5064 % at theta030
mean PRE scheme H1-H2 relative error = 1.9455 %
max fitted apparent-angle offset = 30.2527 deg at theta130
max fluid-only phase drift = 1.2683 %
max fluid-only rho drift = 1.2484 %
```

Representative results:

```text
theta030: H1-H2 error 32.5064 %, fit angle 45.0698 deg
theta090: H1-H2 error 7.7076 %, fit angle 101.4220 deg
theta130: H1-H2 error 8.1489 %, fit angle 160.2527 deg
```

Interpretation:

```text
q27_geometric is numerically stable for the reduced spherical Table II setup,
but it is not quantitatively matched to the PRE 2025 Table II result.
The dominant signal is a systematic wetting-response offset rather than a
finite-field failure.
```

This result remains `exploratory_not_validation`.

## Current Next Action

The next run is not another same-parameter extension. It is an inverse
`radAngle` screen that keeps the same Table II target geometry but writes a
different TCLB `radAngle` into each XML, estimated from the completed 200000
fitted-angle response:

```text
target theta -> TCLB radAngle
30  -> 10.6
40  -> 23.4
50  -> 36.4
60  -> 49.1
70  -> 60.0
80  -> 70.2
90  -> 79.9
100 -> 88.8
110 -> 96.6
120 -> 105.1
130 -> 112.5
```

Run currently launched:

```text
remote root =
  /media/yuan/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_tableII_q27_geometric_anglemap_screen_20260610
steps = 20000
vtk interval = 10000
status = exploratory_not_validation
purpose = decide whether input-angle remapping can reduce H1-H2 error before
          spending a full 200000-step batch
```

## Full 230 x 230 x 400 Note

The full article grid has 21,160,000 cells, about 23.6 times the reduced grid.
Two P100 16GB GPUs might be enough only if the TCLB binary is verified to use
multi-GPU decomposition correctly. A separate two-GPU allocation smoke test is
required before launching the full grid. Aggregate memory alone is not enough
evidence.

## Theta030 Low-Angle Stability Threshold Screens

The inverse-angle screen showed that the originally estimated theta030 mapping

```text
target theta030 -> TCLB radAngle 10.6 deg
```

is not usable even for a 20000-step screen. The TCLB solver returned `0` and
the run log did not contain NaN messages, but raw VTI postprocess found
widespread nonfinite fluid fields:

```text
phase_nonfinite_count = 1027328
u_nonfinite_count = 954036
rho_nonfinite_count = 954036
max_nonfinite_count = 2935400
fluid_phase_sum_rel_change = -100 %
fluid_rho_sum_rel_change = -100 %
status = failed_negative_evidence
```

A targeted theta030 radAngle threshold screen was therefore run at 20000 steps
with the same geometry and model settings:

```text
remote root =
  /media/yuan/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_tableII_q27_geometric_theta030_radangle_threshold_20260610
local artifact =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_tableII_q27_geometric_theta030_radangle_threshold_20260610
tested radAngle = 14,16,18,20,22,24,26,28,30 deg
```

A lower bracket was then run:

```text
remote root =
  /media/yuan/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_tableII_q27_geometric_theta030_radangle_lower_bracket_20260610
local artifact =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_tableII_q27_geometric_theta030_radangle_lower_bracket_20260610
tested radAngle = 11,12,13,13.5 deg
```

All 13 additional cases completed to 20000 steps with solver return code `0`,
postprocess return code `0`, no run-log NaN messages, and no VTI nonfinite
counts. The combined local table is:

```text
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_tableII_q27_geometric_theta030_radangle_threshold_combined_20260610\theta030_radangle_20k_combined_summary.csv
```

Combined health summary:

```text
known failed radAngle = 10.6 deg
lowest finite tested radAngle = 11.0 deg
finite threshold bracket = 10.6 failed, 11.0 passed at 20000 steps
max nonfinite count among passed cases = 0
max Mach among passed cases = 6.68e-4
fluid phase drift range among passed cases = -0.5638 % to -0.2617 %
```

Important interpretation:

```text
The 20000-step screens are finite-field stability screens only.
They are not equilibrium wetting calibration results.
For direct radAngle030, H1-H2 error changed from 130.5 % at 20000 steps to
32.5 % at 200000 steps, and the fitted angle changed from 132.7 deg to
45.1 deg. Therefore 20k contact angle/H1-H2 values must not be used to choose
the final calibration mapping.
```

Next execution decision:

```text
Do not launch a full 11-angle 200000-step inverse-angle batch yet.
Run one theta030 200000-step pilot at a finite low input angle first. The most
informative first pilot is radAngle011 because it is closest to the failed
radAngle010.6 estimate while remaining finite in the 20k screen.
```

## Theta030 radAngle011 200000-Step Pilot

The theta030 long pilot requested above has completed:

```text
remote root =
  /media/yuan/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_tableII_q27_geometric_theta030_radAngle011_200k_20260610
local artifact =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_tableII_q27_geometric_theta030_radAngle011_200k_20260610
target theta = 30 deg
TCLB input radAngle = 11 deg
steps = 200000
vtk interval = 20000
```

Health:

```text
run.returncode = 0
postprocess_returncode = 0
run-log NaN hits = 0
max_nonfinite_count = 0
NumSpecialPoints = 392
max Mach over frames = 6.68e-4
final Mach = 2.01e-4
```

Final comparison against direct theta030/radAngle030:

```text
radAngle011, 200000:
  H1-H2 relative error = 19.3178 %
  fitted angle = 43.7649 deg
  final fluid phase drift = -3.5093 %
  final fluid rho drift = -3.4543 %

radAngle030, 200000:
  H1-H2 relative error = 32.5064 %
  fitted angle = 45.0698 deg
  final fluid phase drift = -1.2683 %
  final fluid rho drift = -1.2484 %
```

Interpretation:

```text
radAngle011 remains finite for 200000 steps and improves the theta030 H1-H2
height error relative to direct radAngle030, but it worsens mass/rho drift.
The apparent fitted angle is still far above the target 30 deg. This is useful
calibration evidence but not validation_candidate evidence.
```

Next decision:

```text
Do not run the full inverse 11-angle 200000 batch yet.
For theta030, run a small 200000-step response bracket in the stable interval,
for example radAngle016, radAngle022, and optionally radAngle026. Compare
H1-H2, fitted angle, mass/rho drift, max Mach, and nonfinite together. Use that
to decide whether inverse-angle calibration is a viable route or whether the
dominant issue is deeper wetting-response/mass-conservation coupling.
```

## Theta030 200000-Step radAngle Response Bracket

The requested small 200000-step response bracket also completed:

```text
remote root =
  /media/yuan/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_tableII_q27_geometric_theta030_radangle_200k_bracket_20260610
local artifact =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_tableII_q27_geometric_theta030_radangle_200k_bracket_20260610
combined local response table =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_tableII_q27_geometric_theta030_200k_response_combined_20260610\theta030_200k_radangle_response_combined.csv
tested radAngle = 16,22,26 deg
```

All bracket cases completed with:

```text
run.returncode = 0
postprocess_returncode = 0
run-log NaN hits = 0
max_nonfinite_count = 0
NumSpecialPoints = 392
```

Combined 200000-step theta030 response:

```text
radAngle  H1-H2 error %  fit angle deg  final fluid phase drift %
11        19.3178        43.7649        -3.5093
16        24.1835        44.0491        -2.8899
22        27.9929        44.3784        -2.0692
26        30.0053        44.0746        -1.6275
30        32.5064        45.0698        -1.2683
```

Interpretation:

```text
Lowering radAngle monotonically improves the H1-H2 height error over the
tested 11-30 range, but it worsens phase/rho drift. The fitted contact angle
remains around 43.8-45.1 deg, still about 14-15 deg above the target 30 deg.
Therefore the current q27_geometric wetting response is only partly adjustable
by radAngle; a simple full inverse-angle map would not be a sound next step.
```

Next execution decision:

```text
Before any full theta sweep, test whether the mass-drift/H1-H2 tradeoff can be
improved at theta030 by phase-field parameters. The smallest useful 200000-step
matrix is:
  radAngle011, M=0.1, IntWidth=6
  radAngle011, M=0.05, IntWidth=6
  radAngle011, M=0.2, IntWidth=8
Use the same density/viscosity/tauUpdate/sigma and report H1-H2, fitted angle,
mass/rho drift, Mach, nonfinite, and NumSpecialPoints.
```

## Theta030 radAngle011 200000-Step M/IntWidth Sensitivity

The next minimal phase-field-parameter matrix has completed:

```text
remote root =
  /media/yuan/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_tableII_q27_geometric_theta030_radAngle011_param_sensitivity_200k_20260610
local artifact =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_pre2025_sphere_tableII_q27_geometric_theta030_radAngle011_param_sensitivity_200k_20260610
combined table with baselines =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_pre2025_sphere_tableII_q27_geometric_theta030_radAngle011_param_sensitivity_200k_20260610\summary\theta030_radAngle011_param_sensitivity_with_baselines.csv
status = exploratory_not_validation, with one failed_negative_evidence case
```

Execution and artifact policy:

```text
case count = 3
target theta = 30 deg
TCLB input radAngle = 11 deg for all three new cases
unchanged settings = 80x80x140, R_drop=24, R_solid=24,
  Density_h/l=1/0.001, Viscosity_h/l=0.09/0.1, tauUpdate=3,
  sigma=5e-5, steps=200000, VTK interval=20000
local raw VTI/PVTI/checkpoint count = 0
remote raw retained = 46 VTI/PVTI/PRI files, about 3.46 GB
```

Runner audit note:

```text
The runner was patched before launch so that a run-log NaN failure exits
nonzero even when TCLB itself returns rc=0. This matters here because
M0p05_W6 produced PhaseField NaN messages at Failcheck while still writing
run.returncode=0.
```

Combined theta030 200000-step response:

```text
case                         H1-H2 err %  fit angle deg  phase drift %  rho drift %  max Mach frames  nonfinite  status
direct radAngle030 M0.2 W6   32.5064      45.0698        -1.2683        -1.2484      6.218e-4        0          exploratory_not_validation
radAngle011 M0.2 W6          19.3178      43.7649        -3.5093        -3.4543      6.678e-4        0          exploratory_not_validation
radAngle011 M0.05 W6         failed at Failcheck with PhaseField NaN; step-0 geometry is not an equilibrium metric
radAngle011 M0.1 W6          28.3017      46.0825        -2.7866        -2.7429      5.960e-4        0          exploratory_not_validation
radAngle011 M0.2 W8          17.4676      42.9514        -3.2268        -3.1776      7.727e-4        0          exploratory_not_validation
```

Interpretation:

```text
Reducing M from 0.2 to 0.1 at W6 reduces mass/rho drift relative to the
radAngle011 baseline, but it worsens H1-H2 error and fitted angle. Reducing M
further to 0.05 is not usable at this low-angle setting because the solver
hits PhaseField NaN despite rc=0. Increasing IntWidth from 6 to 8 at M=0.2
gives the best H1-H2 result in this theta030 set, but it still has about
-3.23% fluid phase drift and a fitted angle about 12.95 deg above target.
```

Next decision:

```text
Do not promote to validation_candidate.
Do not run the full 11-angle inverse map yet.
The most useful next diagnostic is a bounded theta030 W8 response check,
for example radAngle=10.8, 11.0, 11.5, 12.0 at M=0.2/W8, or one mass-control
variant near W8. The objective should be to determine whether W8 can reduce
H1-H2 error without further worsening mass drift, not to claim Table II
reproduction.
```

## Theta030 radAngle011 M0.1 W6 Interrupted 600000-Step Attempt

The requested extension of `theta030, radAngle011, M=0.1, IntWidth=6` toward
600000 steps was launched as a fresh 0-to-600000 run because the previous
200000-step run did not have a usable checkpoint for a true restart.
The run was stopped on request after writing the 200000-step VTK frame.

```text
status = exploratory_not_validation
remote root =
  /mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_tableII_q27_geometric_theta030_radAngle011_M0p1_W6_600k_vtk50k_20260610
local artifact =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_radAngle011_M0p1_W6_600k_interrupted_20260610
target theta = 30 deg
TCLB input radAngle = 11 deg
M = 0.1
IntWidth = 6
requested solve iterations = 600000
actual log final iteration = about 202000
written VTK frames = 0, 50000, 100000, 150000, 200000
```

The run used the same reduced Table II analogue settings as the previous
theta030 cases:

```text
domain = 80 x 80 x 140 requested, VTI cell dims reported as 96 x 80 x 140
R_drop = 24
R_solid = 24
Density_h/l = 1 / 0.001
Viscosity_h/l = 0.09 / 0.1
tauUpdate = 3
sigma = 5e-5
gravity = 0
VTK interval = 50000
```

Run health and artifact policy:

```text
related solver/batch processes after stop = none observed
GPU after stop = Tesla P100, 0% utilization, 266 MiB used
run-log NaN/nonfinite evidence = none observed through the written frames
max_nonfinite_count in postprocess = 0
local raw VTI/PVTI/PRI count = 0
remote raw VTI/PVTI/PRI count = 10
remote raw bytes = 752651780
```

Frame metrics:

```text
step     H1-H2 err %  Hmax err %  fit angle deg  fluid phase drift %  rho drift %  max Mach   phi max
0        142.1251     63.9157     163.5973       0.0000               0.0000       0.000000   1.7955
50000    105.3787     47.3903     106.8160       -0.9361              -0.9214      0.000568   3.2782
100000   71.3251      32.0759     67.3385        -1.7148              -1.6879      0.000425   3.1063
150000   46.7479      21.0232     54.2115        -2.3127              -2.2764      0.000314   1.7227
200000   28.3017      12.7277     46.0825        -2.7866              -2.7429      0.000242   1.4319
```

Interpretation:

```text
This is a static-wetting relaxation test, but the interrupted 0-200000 segment
is not a static equilibrium result. The morphology still evolves strongly from
50000 to 200000 steps. The apparent global fitted angle decreases from about
106.82 deg at 50000 to 46.08 deg at 200000, while the H1-H2 error decreases
from 105.38% to 28.30%. At the same time, fluid phase/rho drift grows
monotonically to about -2.79%/-2.74%. Therefore the large discrepancy is not
only a contact-line-angle issue; the current TCLB analogue is still relaxing
and losing liquid-phase/rho mass relative to the target cap geometry.
```

Next rule:

```text
Do not label this as a completed 600000-step run.
Do not promote it beyond exploratory_not_validation.
If a future long relaxation is needed, include SaveCheckpoint at 50000 or
100000 intervals so the run can be stopped and resumed without restarting from
step 0.
```
