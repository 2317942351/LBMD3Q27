# TCLB Project Handoff

Date: 2026-06-06

## Objective

Use TCLB as the main solver candidate for high-density-ratio droplet-wall
impact studies. The final user target is:

```text
rho_ratio = 772
droplet diameter = 1 mm
release height = 10 mm
gravity = -z
dry wall and liquid-film impact
contact angles = 45, 90, 135 deg
run until static/resting state
outputs = beta(t), beta_max, morphology snapshots, mass conservation, Mach
```

## Current State

TCLB is deployed on HM570 and can run `d3q27_pf_velocity` on the Tesla P100.

```text
source = /home/yuan/src/TCLB
commit = ded67cd768cf7e727bd078af139e3ec7895076e5
binary = /home/yuan/src/TCLB/CLB/d3q27_pf_velocity/main
```

Standard TCLB sanity cases already completed before this folder was split:

```text
bubbleRise_1: completed 12000 steps
ContactAngle_45_full: completed 200000 steps
```

The first `rho_ratio=772` small-grid dry-wall exploration completed, but is
not validation:

```text
grid = 96 x 96 x 96
R0 = 14 lu
wall = x=0 in that exploratory run
VelocityX = -0.025
GravitationX = -1e-6
contact angle = 90 deg
steps = 2500
status = exploratory_not_validation
reason = phase-field mass drift about +12%
```

Corrected postprocessing established that the previous axis confusion was a
postprocessing `reshape` error. VTK cell data should be interpreted with x as
the fastest index, then y, then z.

An initial z-wall smoke has also completed, but it is still only
`exploratory_not_validation`:

```text
run_id = tclb_z_wall_rho772_pilot_20260607
remote = /home/yuan/runs/tclb_z_wall_rho772_pilot_20260607/theta090
local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_pilot_20260607_theta090
grid = 96 x 96 x 96
R0 = 14 lu
wall = z=0
VelocityZ = -0.025 global, exploratory only
GravitationZ = -1e-6
contact angle = 90 deg
steps = 500
status = exploratory_not_validation
reason = no wall contact by 500 steps; max Mach about 0.0979 near the 0.1 guard
```

A lower-Mach z-wall contact pilot then completed, still only
`exploratory_not_validation`:

```text
run_id = tclb_z_wall_rho772_lowmach_contact_20260607
remote = /home/yuan/runs/tclb_z_wall_rho772_lowmach_contact_20260607/theta090
local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_lowmach_contact_20260607_theta090
grid = 96 x 96 x 96
R0 = 14 lu
wall = z=0
VelocityZ = -0.012 global, exploratory only
GravitationZ = -1e-6
contact angle = 90 deg
steps = 1200
beta_area max = 0.476827
beta_box max = 0.5
phase mass drift max = 0.00455
rho drift last = -0.000523
max Mach = 0.04264
nonfinite = 0
status = exploratory_not_validation
reason = global VelocityZ, small grid, theta=90 only, not run to rest, no validation comparison
```

The HM570 TCLB source now has a local exploratory droplet-only initialization
patch in `d3q27_pf_velocity`:

```text
files = /home/yuan/src/TCLB/models/multiphase/d3q27_pf_velocity/Dynamics.R
        /home/yuan/src/TCLB/models/multiphase/d3q27_pf_velocity/Dynamics.c.Rt
backup = *.pre_droplet_velocity_20260607
new XML settings = DropletOnlyVelocity, DropletVelocityX/Y/Z
DropletOnlyVelocity modes = 0 off, 1 hard phase mask, 2 smooth phase-fraction weighting
default behavior = unchanged when DropletOnlyVelocity=0
status = exploratory_not_validation
```

A droplet-only near-wall contact pilot completed, but it is negative evidence
for the current small-grid/scaling setup rather than validation:

```text
run_id = tclb_z_wall_rho772_dropletonly_nearwall_20260607
remote = /home/yuan/runs/tclb_z_wall_rho772_dropletonly_nearwall_20260607/theta090
local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_dropletonly_nearwall_20260607_theta090
grid = 96 x 96 x 96
R0 = 14 lu
wall = z=0
VelocityZ = 0 global
DropletOnlyVelocity = 1
DropletVelocityZ = -0.012
GravitationZ = -1e-6
contact angle = 90 deg
steps = 1600
beta_area max = 1.153995
beta_box max = 1.142857
phase mass drift max = 0.0328
rho drift last = -0.00495
max Mach = 0.02659
nonfinite = 0
status = exploratory_not_validation
reason = phase mass drift about 3.28%, small grid, theta=90 only, not run to rest, no validation comparison
```

A smooth phase-fraction droplet-velocity A/B run used the same geometry and
velocity as the hard-mask near-wall pilot. It improved the transient only
slightly and is still not acceptable for validation:

```text
run_id = tclb_z_wall_rho772_dropletsmooth_nearwall_20260607
remote = /home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_nearwall_20260607/theta090
local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_nearwall_20260607_theta090
grid = 96 x 96 x 96
R0 = 14 lu
wall = z=0
VelocityZ = 0 global
DropletOnlyVelocity = 2
DropletVelocityZ = -0.012
GravitationZ = -1e-6
contact angle = 90 deg
steps = 1600
beta_area max = 1.119710
beta_box max = 1.142857
phase mass drift max = 0.02965
rho drift last = -0.00438
max Mach = 0.02522
nonfinite = 0
status = exploratory_not_validation
reason = phase mass drift still about 2.96%, small grid, theta=90 only, not run to rest, no validation comparison
```

Lowering the smooth droplet velocity from `-0.012` to `-0.008` produced the
first small-grid z-wall rho772 pilot in this branch with engineering-direction
mass metrics below phase `2%` and rho `1%`, but it is still not validation:

```text
run_id = tclb_z_wall_rho772_dropletsmooth_u008_nearwall_20260607
remote = /home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_nearwall_20260607/theta090
local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_nearwall_20260607_theta090
grid = 96 x 96 x 96
R0 = 14 lu
wall = z=0
VelocityZ = 0 global
DropletOnlyVelocity = 2
DropletVelocityZ = -0.008
GravitationZ = -1e-6
contact angle = 90 deg
steps = 1600
beta_area max = 0.837604
beta_box max = 0.857143
phase mass drift max = 0.01336
rho drift last = -0.00177
max Mach = 0.01771
nonfinite = 0
status = exploratory_not_validation
reason = small grid, theta=90 only, lower spreading by 1600 steps, not run to rest, no validation comparison
```

Extending the same `DropletVelocityZ=-0.008` case to 3200 steps identified
first contact but contradicted the short-window mass-conservation trend:

```text
run_id = tclb_z_wall_rho772_dropletsmooth_u008_ext3200_20260607
remote = /home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_ext3200_20260607/theta090
local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_ext3200_20260607_theta090
grid = 96 x 96 x 96
R0 = 14 lu
wall = z=0
VelocityZ = 0 global
DropletOnlyVelocity = 2
DropletVelocityZ = -0.008
GravitationZ = -1e-6
contact angle = 90 deg
steps = 3200
first_contact_step = 1000
beta_area max = 1.208978 at step 3200
beta_box max = 1.214286 at step 3000
late beta still increasing
phase mass drift max = 0.0502
rho drift last = -0.00894
max Mach = 0.01750
nonfinite = 0
resting_candidate = false
status = exploratory_not_validation
reason = phase mass drift grows to about 5.02%, beta still growing, not run to rest, no validation comparison
```

An M-only sensitivity lowered the same long-window phase drift but did not pass
the mass/resting gate:

```text
run_id = tclb_z_wall_rho772_dropletsmooth_u008_ext3200_M0025_20260607
remote = /home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_ext3200_M0025_20260607/theta090
local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_ext3200_M0025_20260607_theta090
grid = 96 x 96 x 96
R0 = 14 lu
wall = z=0
VelocityZ = 0 global
DropletOnlyVelocity = 2
DropletVelocityZ = -0.008
GravitationZ = -1e-6
contact angle = 90 deg
M = 0.025
IntWidth = 5
steps = 3200
first_contact_step = 1000
beta_area max = 1.206288 at step 3200
beta_box max = 1.214286 at step 3000
late beta still increasing
phase mass drift max = 0.04137
clipped phase mass drift max = 0.04137
rho drift last = -0.00686
max Mach = 0.017996
nonfinite = 0
resting_candidate = false
status = exploratory_not_validation
reason = M-only tuning improves phase drift from about 5.02% to about 4.14%, but still fails the long-window mass gate and is not run to rest
```

An IntWidth-only sensitivity in the opposite direction worsened the
long-window mass behavior:

```text
run_id = tclb_z_wall_rho772_dropletsmooth_u008_ext3200_W4_20260607
remote = /home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_ext3200_W4_20260607/theta090
local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_ext3200_W4_20260607_theta090
grid = 96 x 96 x 96
R0 = 14 lu
wall = z=0
VelocityZ = 0 global
DropletOnlyVelocity = 2
DropletVelocityZ = -0.008
GravitationZ = -1e-6
contact angle = 90 deg
M = 0.05
IntWidth = 4
steps = 3200
first_contact_step = 800
beta_area max = 1.246023 at step 3200
beta_box max = 1.285714 at step 3200
late beta still increasing
phase mass drift max = 0.05924
clipped phase mass drift max = 0.05924
rho drift last = -0.01066
max Mach = 0.021688
nonfinite = 0
resting_candidate = false
status = exploratory_not_validation
reason = reducing IntWidth from 5 to 4 worsens phase drift to about 5.92% and rho drift to about -1.07%; not run to rest and not validation
```

A wider-interface IntWidth-only sensitivity improved the baseline directionally
but still did not pass the long-window phase gate:

```text
run_id = tclb_z_wall_rho772_dropletsmooth_u008_ext3200_W6_20260607
remote = /home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_ext3200_W6_20260607/theta090
local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_ext3200_W6_20260607_theta090
grid = 96 x 96 x 96
R0 = 14 lu
wall = z=0
VelocityZ = 0 global
DropletOnlyVelocity = 2
DropletVelocityZ = -0.008
GravitationZ = -1e-6
contact angle = 90 deg
M = 0.05
IntWidth = 6
steps = 3200
first_contact_step = 1000
beta_area max = 1.162408 at step 3200
beta_box max = 1.142857 at step 2800
late beta_area still increasing
phase mass drift max = 0.04335
clipped phase mass drift max = 0.04335
rho drift last = -0.00761
max Mach = 0.014932
nonfinite = 0
resting_candidate = false
status = exploratory_not_validation
reason = widening IntWidth from 5 to 6 improves phase drift to about 4.33% and rho drift to about -0.76%, but still fails the long-window phase gate and is not run to rest
```

A coupled `M=0.025, IntWidth=6` diagnostic is the best current direction, but
still does not pass the long-window phase gate:

```text
run_id = tclb_z_wall_rho772_dropletsmooth_u008_ext3200_M0025_W6_20260607
remote = /home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_ext3200_M0025_W6_20260607/theta090
local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_ext3200_M0025_W6_20260607_theta090
grid = 96 x 96 x 96
R0 = 14 lu
wall = z=0
VelocityZ = 0 global
DropletOnlyVelocity = 2
DropletVelocityZ = -0.008
GravitationZ = -1e-6
contact angle = 90 deg
M = 0.025
IntWidth = 6
steps = 3200
first_contact_step = 1000
beta_area max = 1.167983 at step 3200
beta_box max = 1.142857 at step 2800
late beta_area still increasing
phase mass drift max = 0.03652
clipped phase mass drift max = 0.03652
rho drift last = -0.00587
max Mach = 0.015387
nonfinite = 0
resting_candidate = false
status = exploratory_not_validation
run completion note = run.log reaches 3200 VTK output and raw counts are complete; postprocess return code was not captured by wrapper, but summary JSON and metrics CSV were produced
reason = coupled M/IntWidth improves phase drift to about 3.65%, best current direction, but still fails engineering/publication mass gates and is not run to rest
```

The long-window phase gate was then re-audited with BOUNDARY-aware mass
accounting. The earlier all-cell `phase_sum` values include wetting-wall ghost
`PhaseF`, so they must not be used as the bulk mass-conservation gate. The
corrected `analysis_fluidmass` results use `BOUNDARY==0` fluid cells for
bulk phase mass and report wall ghost phase separately:

```text
summary CSV = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\ext3200_fluidmass_summary.csv
postprocess script = scripts\tclb_impact_drywall_postprocess.py with fluid_phase_* and wall_phase_* metrics

case        all-cell phase   fluid-only phase   rho drift    max Mach   resting
W5_base     5.02%            0.98%              -0.89%       0.01750    false
M0025       4.14%            0.75%              -0.69%       0.01800    false
W4          5.92%            1.17%              -1.07%       0.02169    false
W6          4.33%            0.83%              -0.76%       0.01493    false
M0025_W6    3.65%            0.64%              -0.59%       0.01539    false

interpretation = corrected fluid-only mass removes the earlier apparent
large bulk phase-drift objection for most variants, but no 3200-step case is
run to rest; beta_area still peaks at the final step in every case
status = exploratory_not_validation
```

The conservative best small-grid candidate was extended to 6400 steps and
audited read-only. It remains useful exploratory evidence but does not justify
promotion:

```text
run_id = tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext6400_20260607
remote = /home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext6400_20260607/theta090
local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext6400_20260607_theta090
grid = 96 x 96 x 96
R0 = 14
wall = z=0
VelocityZ = 0 global
DropletOnlyVelocity = 2
DropletVelocityZ = -0.008
GravitationZ = -1e-6
contact angle = 90 deg
M = 0.025
IntWidth = 6
steps = 6400
first_contact_step = 1200
beta_area max = 1.232920 at step 6400
beta_box max = 1.214286 at step 3600
late beta_area change = 0.010583 over steps 5600,6000,6400
all-cell phase drift = +5.724%, diagnostic only because it includes BOUNDARY cells
fluid-only phase drift = -1.1369%
fluid clipped phase drift = -1.1368%
rho drift = -1.0451%
max Mach = 0.014789
nonfinite = 0
wall ghost phase last = 880.6069
resting_candidate = false
status = exploratory_not_validation
audit decision = no promotion; no R0>=32 pilot and no 45/90/135 contact-angle sweep should be launched from this result alone
reason = Mach and nonfinite checks are healthy, but fluid-only phase and rho drift slightly exceed preferred gates, beta_area still reaches its maximum at the final frame, and the case is not run to rest
```

The first postprocess requested morphology at step 1000, but the VTK interval
was 400 so no step-1000 field exists. Event-aligned re-postprocessing now
includes step 1200 as the first available post-contact morphology frame. Future
runs should include contact, beta-max, late-window, and candidate-rest frames
that actually exist in the VTK output sequence.

Extending the same small-grid candidate to 9600 steps provided negative
evidence for the current theta=90 route rather than a better baseline:

```text
run_id = tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext9600_20260607
remote = /home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext9600_20260607/theta090
local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext9600_20260607_theta090
grid = 96 x 96 x 96
R0 = 14
wall = z=0
VelocityZ = 0 global
DropletOnlyVelocity = 2
DropletVelocityZ = -0.008
GravitationZ = -1e-6
contact angle = 90 deg
M = 0.025
IntWidth = 6
steps = 9600
first_contact_step = 1200
beta_area max = 1.3021088099456783 at step 9600
beta_box max = 1.2857142857142858 at step 7200
late_beta_area_change = 0.015053786964550397 over steps 8800,9200,9600
all-cell phase drift = +6.688467977723006%, diagnostic only because it includes BOUNDARY cells
fluid-only phase drift = -1.3354949822091176%
fluid clipped phase drift = -1.3354227420845041%
rho drift = -1.2276700620208972%
max Mach = 0.014789263592322023
nonfinite = 0
wall ghost phase last = 1029.4048096189983
resting_candidate = false
status = exploratory_not_validation
audit decision = no promotion; treat as negative evidence for the current small-grid theta=90 candidate
reason = clean runtime and healthy Mach/nonfinite checks, but beta_area still peaks at the final frame, late-window change exceeds the resting tolerance, and fluid-only phase/rho drift worsened versus ext6400
```

The curated local artifact contains the case XML, generated config XML,
`run.log`, TCLB CSV log, summary JSON, metrics CSV, postprocess logs/script,
and morphology images for steps 0, 1200, 3600, 6400, 7600, 8400, 9200, and
9600. Raw VTI/PVTI remain remote-only: 25 VTI and 25 PVTI under the remote
`output/` directory, about 1.4G; local raw VTI/PVTI count is 0.

Following audit advice, the next bounded execution step moved to TCLB's own
static contact-angle calibration instead of extending or scaling the impact
case. Official `ContactAngle_45.xml`-derived theta=45/90/135 cases completed
on HM570, but the calibration is not accepted yet:

```text
run_id = tclb_static_contact_angle_calib_20260607
remote = /home/yuan/runs/tclb_static_contact_angle_calib_20260607/theta045
         /home/yuan/runs/tclb_static_contact_angle_calib_20260607/theta090
         /home/yuan/runs/tclb_static_contact_angle_calib_20260607/theta135
local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_static_contact_angle_calib_20260607_theta045
        C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_static_contact_angle_calib_20260607_theta090
        C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_static_contact_angle_calib_20260607_theta135
summary = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_calib_20260607_summary.json
v3 summary = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_calib_20260607_v3_summary.json
v3 analysis = analysis_contact_angle_v3 under each local/remote theta directory
convention audit remote = /home/yuan/runs/tclb_static_contact_angle_calib_20260607/analysis_contact_angle_convention_audit
convention audit local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_convention_audit_20260607
case XMLs = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\static_contact_angle\contact_angle_theta*.xml
script = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_static_contact_angle_postprocess.py
convention audit script = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_static_contact_angle_convention_audit.py
grid = 128 x 64 x 128
steps = 200000
VTK interval = 10000
raw VTI/PVTI = 21/21 per angle, remote-only
status = exploratory_not_validation

theta045: apparent angle 122.3379 deg, complement 57.6621 deg, complement error +12.6621 deg, phase drift +4.1804%, rho drift -0.9026%, max Mach 9.53e-5, nonfinite 0
theta090: apparent angle 89.1689 deg, complement 90.8311 deg, complement error +0.8311 deg, phase drift -0.1825%, rho drift +0.0364%, max Mach 1.16e-5, nonfinite 0
theta135: apparent angle 44.7137 deg, complement 135.2863 deg, complement error +0.2863 deg, phase drift -3.3408%, rho drift +0.7698%, max Mach 1.67e-4, nonfinite 0

convention audit return code = 0
convention audit method = existing-output-only fit sensitivity; 24 variants per angle across x/z mid-slices, wall location 0/0.5/1.0, and min-wall-distance 0/1/2/4
angle definition = lower_wall_liquid_side_angle_deg = 180 - angle_from_circle_deg
coordinate convention = x-mid slice contour plot x is y wall-normal; z-mid slice contour plot y is y wall-normal
theta045 convention audit = liquid-side angle 55.7808-60.7211 deg, error +10.7808 to +15.7211 deg, best abs error 10.7808 deg
theta090 convention audit = liquid-side angle 88.3287-90.8311 deg, best abs error 0.3851 deg
theta135 convention audit = liquid-side angle 129.3640-135.2863 deg, best abs error 0.2398 deg
```

Interpretation:

```text
theta090 is plausible as a static wetting calibration point.
theta135 strongly suggests a contact-angle complement/convention issue in the
current lower-y-wall postprocess interpretation because its complement is close
to the input angle.
theta045 does not pass even with the complement interpretation: complement
error remains about 12.66 deg, with larger phase/rho drift.
Do not treat the 45/90/135 wetting calibration as passed, and do not start an
impact contact-angle sweep until the convention and low-angle mass behavior are
audited and fixed.
Read-only audit after v3 kept the run at exploratory_not_validation with no
promotion and no impact sweep. Build-state inspection found the current HM570
`d3q27_pf_velocity/main` binary has `geometric`, `staircaseimp`, `isograd`, and
`tprec` disabled (`options.R=FALSE`, `Consts.h=#undef`), even though `conf.mk`
lists them as possible build variants. This static run set therefore used the
non-geometric/default surface-energy wetting path in `Boundary.c.Rt`; do not
explain the complement behavior as a confirmed geometric-BC convention.
The convention audit confirmed that the theta045 mismatch persists across the
tested fit conventions, slice axes, wall-location assumptions, and near-wall
filters. This strengthens the no-go decision for the 45/90/135 impact sweep:
theta045 is a wetting/calibration blocker, not just a plotting-axis artifact.
```

A low-angle surface-energy response sweep was then postprocessed and indexed.
It is negative evidence for the simple idea that `radAngle=30-35` can replace
the requested liquid-side 45 deg static contact angle:

```text
run_id = tclb_static_contact_angle_response_surface_energy_20260607
remote = /home/yuan/runs/tclb_static_contact_angle_response_surface_energy_20260607
local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_response_surface_energy_20260607
cases = theta030, theta035, theta040, theta045, theta050, theta060
case XML root = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\static_contact_angle_response_surface_energy_20260607
script = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_static_contact_angle_postprocess.py
convention audit script = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_static_contact_angle_convention_audit.py
grid = 128 x 64 x 128
steps = 200000
VTK interval = 10000
raw VTI/PVTI = 21/21 per angle, remote-only
remote size = about 8.1G
local raw VTI/PVTI count = 0
status = exploratory_not_validation
build state = non-geometric/default surface-energy wetting path; geometric,
              staircaseimp, isograd, and tprec are FALSE/#undef
```

Execution and postprocess status:

```text
all six run_return_code files = 0
convention audit return code = 0
convention audit stderr = empty
corrected convention audit summary run_id =
  tclb_static_contact_angle_response_surface_energy_20260607
claim limit = existing-output fit-convention sensitivity only; no validation
              promotion and no impact sweep authorization
```

Response-sweep results:

```text
theta030: liquid-side audit range 48.8321-57.2313 deg; postprocess complement
          50.5814 deg; phase drift 7.9924%; rho drift -1.5230%;
          max Mach 1.20e-4; nonfinite 0
theta035: liquid-side audit range 51.0164-57.7338 deg; complement 52.8261 deg;
          phase drift 6.0308%; rho drift -1.2333%; max Mach 1.14e-4;
          nonfinite 0
theta040: liquid-side audit range 53.2827-59.0198 deg; complement 55.1045 deg;
          phase drift 4.9787%; rho drift -1.0521%; max Mach 1.05e-4;
          nonfinite 0
theta045: liquid-side audit range 55.7808-60.7211 deg; complement 57.6621 deg;
          phase drift 4.1804%; rho drift -0.9026%; max Mach 9.53e-5;
          nonfinite 0
theta050: liquid-side audit range 58.6713-62.9543 deg; complement 60.6172 deg;
          phase drift 3.5144%; rho drift -0.7715%; max Mach 8.56e-5;
          nonfinite 0
theta060: liquid-side audit range 65.3152-68.5590 deg; complement 67.3294 deg;
          phase drift 2.3867%; rho drift -0.5379%; max Mach 6.38e-5;
          nonfinite 0
```

Interpretation:

```text
radAngle=30 already produces a best liquid-side angle around 48.83 deg and the
low-angle cases have the largest phase/rho drift. radAngle=35 produces about
51.02 deg best liquid-side angle. This sweep does not provide a stable,
auditable substitute input for liquid-side 45 deg and does not clear the
theta045 wetting blocker. Do not launch 45/90/135 impact sweeps from this
evidence. The response is useful only as exploratory diagnostic evidence for
the default surface-energy path.
```

Two lower-angle static bracket runs were then completed and audited:

```text
run_id = tclb_static_contact_angle_bracket_lowangle_20260607
remote = /home/yuan/runs/tclb_static_contact_angle_bracket_lowangle_20260607
local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_bracket_lowangle_20260607
angles = 15, 18, 20, 22, 25, 28 deg
status = exploratory_not_validation
raw VTI/PVTI = 21/21 per angle, remote-only
local raw VTI/PVTI count = 0

run_id = tclb_static_contact_angle_bracket_lower_20260607
remote = /home/yuan/runs/tclb_static_contact_angle_bracket_lower_20260607
local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_bracket_lower_20260607
angles = 5, 10, 12 deg
status = exploratory_not_validation
raw VTI/PVTI = 21/21 per angle, remote-only
local raw VTI/PVTI count = 0

combined artifact =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_bracket_combined_20260607
```

Combined low-angle bracket result:

```text
radAngle 5:  audit liquid-side 43.8741-60.0582 deg; complement 45.5354 deg;
             phase drift 18.3009%; rho drift -2.8428%; max Mach 1.36e-4;
             nonfinite 0
radAngle 10: liquid-side 44.6668-59.8532 deg; complement 46.3477 deg;
             phase drift 17.5727%; rho drift -2.7472%; max Mach 1.35e-4;
             nonfinite 0
radAngle 12: liquid-side 44.7333-59.7167 deg; complement 46.4137 deg;
             phase drift 17.1268%; rho drift -2.6889%; max Mach 1.34e-4;
             nonfinite 0
radAngle 15: liquid-side 45.5173-59.1006 deg; complement 47.2164 deg;
             phase drift 16.2726%; rho drift -2.5780%; max Mach 1.33e-4;
             nonfinite 0
radAngle 18-28: liquid-side lower bound rises from 46.3092 to 48.6100 deg;
                phase drift remains 9.2934-15.1672%; rho drift remains
                -1.6926% to -2.4359%
```

Read-only audit interpretation:

```text
liquid-side 45 is bracketed only in an exploratory fit-sensitivity sense.
theta045 is partially cleared only for a single exploratory 45 impact pilot,
not for validation, production, or publication.
The mass/rho behavior is poor: phase drift reaches 17-18% near the candidate
input range and rho drift is about -2.7% to -2.8%, exceeding engineering
preferences. The fit ranges also remain broad.
Allowed next step: one dry-wall theta045 exploratory pilot using the candidate
low-angle input, with full beta_area/beta_box, mass/rho/Mach/nonfinite,
morphology, case XML, run.log, summary JSON, and artifact-path reporting.
Not allowed: 45/90/135 impact sweep, validation claim, production claim,
publication figure/table, Wang 2023 reproduction claim, or grid-converged
claim.
```

The allowed single dry-wall exploratory pilot was run with `radAngle=5d` as
the target-45 input. It is useful negative/diagnostic impact evidence, not
promotion evidence:

```text
run_id = tclb_z_wall_rho772_rad005_target45_dropletsmooth_u008_M0025_W6_ext6400_20260607
remote = /home/yuan/runs/tclb_z_wall_rho772_rad005_target45_dropletsmooth_u008_M0025_W6_ext6400_20260607/rad005_target45
local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_rad005_target45_dropletsmooth_u008_M0025_W6_ext6400_20260607_rad005_target45
case XML = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\dry_wall\user_1mm_10mm_contact_angle_sweep\pilot_rad005_target45_20260607\impact_zwall_rad005_target45_dropletsmooth_u008_M0025_W6_ext6400.xml
status = exploratory_not_validation
grid = 96 x 96 x 96
R0 = 14
wall = z=0
gravity = -z
input radAngle = 5d
DropletOnlyVelocity = 2
DropletVelocityZ = -0.008
M = 0.025
IntWidth = 6
steps = 6400
VTK interval = 400
raw VTI/PVTI = 17/17 remote-only
local raw VTI/PVTI count = 0
```

Pilot metrics:

```text
TCLB return code = 0
postprocess return code = 0
postprocess stderr = Matplotlib no-contour warning for early morphology frame
first_contact_step = 1200
beta_area_max = 1.734273 at step 6400
beta_box_max = 1.714286 at step 6000
late_beta_area_change = 0.064891
late_beta_box_change = 0.071429
resting_candidate = false
all-cell phase drift max = 12.4209%
fluid-only phase drift max = 2.2720%
fluid-only clipped phase drift max = 2.2718%
rho drift last = -2.0886%
max Mach = 0.0146116
nonfinite = 0
wall ghost phase last = 1885.7082
```

Interpretation:

```text
Runtime, Mach, finite checks, beta extraction, and morphology output chain work.
However, beta_area is maximal at the final frame and late beta still changes
substantially. Fluid-only phase drift and rho drift exceed engineering
preferences. This confirms that the low-angle target-45 route remains
exploratory and cannot be promoted or expanded to a 45/90/135 sweep.
```

A follow-up static low-angle sensitivity tested whether the impact-style
`M=0.025`, `IntWidth=6` choice improves low-angle static wetting behavior. It
completed cleanly but did not clear the calibration blocker:

```text
run_id = tclb_static_contact_angle_bracket_lowangle_M0025_W6_20260607
remote = /home/yuan/runs/tclb_static_contact_angle_bracket_lowangle_M0025_W6_20260607
local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_bracket_lowangle_M0025_W6_20260607
case XML root = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\static_contact_angle_bracket_lowangle_M0025_W6_20260607
status = exploratory_not_validation
geometry = lower-y wall, 128 x 64 x 128
steps = 200000
VTK interval = 10000
input radAngle = 5, 10, 15 deg
M = 0.025
IntWidth = 6
TCLB/postprocess/audit return codes = 0
raw VTI/PVTI = 21/21 per angle, 63/63 total, remote-only
local raw VTI/PVTI count = 0
remote size = about 4.1G
BOUNDARY-aware reanalysis = analysis_contact_angle_bracket_M0025_W6_boundarymass
BOUNDARY-aware reanalysis return codes = 0, stderr empty
```

Static M0025/W6 metrics after BOUNDARY-aware mass accounting:

```text
radAngle 5:  complement 52.7401 deg; audit liquid-side 50.9341-59.9471 deg;
             all-cell phase drift 8.5176%; fluid-only phase drift 1.6495%;
             wall/ghost phase drift 153.3568%; rho drift 1.5921%;
             max Mach 1.4126e-4; nonfinite 0
radAngle 10: complement 52.8157 deg; audit liquid-side 51.0110-59.8931 deg;
             all-cell phase drift 8.2010%; fluid-only phase drift 1.6046%;
             wall/ghost phase drift 148.0239%; rho drift 1.5488%;
             max Mach 1.4010e-4; nonfinite 0
radAngle 15: complement 52.9568 deg; audit liquid-side 51.1540-59.8179 deg;
             all-cell phase drift 7.6811%; fluid-only phase drift 1.5296%;
             wall/ghost phase drift 139.2290%; rho drift 1.4764%;
             max Mach 1.3811e-4; nonfinite 0
```

Interpretation:

```text
The coupled M0025/W6 setting reduced bulk fluid-only phase drift to about
1.53-1.65%, while the previous 7.68-8.52% all-cell phase drift is mainly a
wall/ghost-inclusive diagnostic. This improves the mass-accounting
interpretation, but it does not preserve the exploratory liquid-side 45 deg
bracket. The measured/complement angles cluster near 52.7-53.0 deg and the
audit ranges stay near 51-60 deg. Rho drift remains about 1.5%, above the
preferred engineering target for calibration. This is mixed evidence for
M0025/W6: better bulk phase mass, failed target angle. It does not authorize
another target-45 impact pilot, any 45/90/135 sweep, or
validation/production/publication claims.
```

A1 formalized the existing TCLB built-in `bubbleRise_1` output as a curated
runtime sanity artifact without launching a new TCLB simulation:

```text
run_id = tclb_bubbleRise_A1_20260607
remote = /home/yuan/runs/tclb_standard_d3q27_20260606_231035/bubbleRise_short
remote analysis = /home/yuan/runs/tclb_standard_d3q27_20260606_231035/bubbleRise_short/analysis_bubbleRise_A1_20260607
local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_bubbleRise_A1_20260607
status = runtime_sanity
remote raw VTI/PVTI = 7/7, about 468M, remote-only
local raw VTI/PVTI count = 0
postprocess return code = 0
postprocess stderr = one Matplotlib no-contour warning for morphology; record as a visualization limitation, not a fatal numerical failure
bubble proxy = clipped 1 - PhaseField because BubbleType=-1
rise direction = positive_y_by_largest_bubble_proxy_centroid_displacement
y-centroid displacement = 55.3067 cells
max Mach = 0.0223546
max nonfinite = 0
max all-cell/fluid-only phase drift = 9.719e-5 / 2.939e-5
max all-cell/fluid-only rho drift = 2.635e-5 / 2.635e-5
```

Interpretation:

```text
This initial artifact supported TCLB runtime/postprocessing sanity only. At
the time of that formalization, no digitized Safi et al. or TCLB benchmark
reference data were applied. Later updates added Safi bitmap digitization and
Bonn/INS Adelsberger 2014 TC1 ASCII provenance, but A1 still is not
validation_passed or publication_ready because the comparison route has not
passed read-only audit, explicit acceptance thresholds are not frozen,
independent observable mapping remains unresolved, and no grid/time-step
sensitivity has been performed.
```

A1 reference-data preparation and a first pre-audit comparison have been
completed, but the result is not promoted:

```text
Safi PDF/preprint = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\references\papers\safi2017_camwa_3d_bubble_preprint.pdf
reference/spec note = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\references\a1_bubbleRise_reference_gap_20260607.md
digitization notes = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\references\data\a1_bubbleRise_safi2017_digitization_notes.md
reference CSV template = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\references\data\a1_bubbleRise_safi2017_reference_template.csv
digitized reference CSV = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\references\data\a1_bubbleRise_safi2017_reference.csv
comparison script = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\a1_bubbleRise_compare_safi2017.py
comparison artifact = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_bubbleRise_A1_safi_compare_20260607
definition evidence = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_bubbleRise_A1_safi_compare_20260607\definition_evidence.md
artifact marker = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_bubbleRise_A1_reference_gap_20260607
Safi DOI = 10.1016/j.camwa.2016.12.014
existing A1 mapping = bubbleRise_1.xml -> Safi 2017 TC1, Re=35, Eo=10, rho ratio=10, viscosity ratio=10
time conversion = T = t_lb * sqrt(g_lb / (g * L0)); Safi text defines L0=1/h and the TCLB RT generator sets L0=64; current 12000-step A1 reaches T about 2.9303
digitization = Safi TC1 Fig. 4 center of mass and Fig. 5 rise velocity FeatFlow red curves from rendered page-09 bitmap; legend swatches excluded
observable mapping = center_of_mass uses (centroid_y + 0.5)/L0 from A1 VTI metrics; rise_velocity uses TCLB CSV GasTotalVelocityY/GasTotalPhase divided by L0*T_per_step
TCLB source evidence = HM570 Dynamics.c.Rt updateMyGlobals uses tmpPF=1-pf; for pf<0.5 it adds tmpPF*V to GasTotalVelocityY and tmpPF to GasTotalPhase; Dynamics.R comments label these as average bubble-velocity terms
comparison metrics = center_of_mass L2 abs error 0.0587, max abs error 0.0940; rise_velocity L2 abs error 0.0145, max abs error 0.0380
health metrics = max Mach 0.0223546; max nonfinite 0; max all-cell/fluid-only phase drift 9.719e-5/2.939e-5; max all-cell/fluid-only rho drift 2.635e-5/2.635e-5
local raw VTI/PVTI count remains 0
status = runtime_sanity remains unchanged
```

The A1 Safi comparison read-only audit is now recorded at:

```text
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_bubbleRise_A1_safi_compare_20260607\read_only_audit_20260607.md
```

Audit decision:

```text
status remains runtime_sanity
do not promote to validation_candidate
script SHA256 = 5AB50D3266131C382DD6573BEE01008150A19A17A1101E055264778238FF1CC8
reference rows = 225 total: 110 center_of_mass + 115 rise_velocity
comparison rows = 223 total: 108 center_of_mass + 115 rise_velocity
local raw VTI/PVTI count = 0
```

Audit rationale:

```text
The reference data are bitmap-derived and not independently calibrated.
The recorded point uncertainty is about +/-0.006 for center_of_mass and
+/-0.003 for rise_velocity, while the observed errors are larger:
center_of_mass L2/max abs error 0.0587/0.0940 and rise_velocity L2/max abs
error 0.0145/0.0380. The center/time mapping is plausible, and the TCLB CSV
GasTotalVelocityY/GasTotalPhase velocity mapping is source-supported, but it
remains a diffuse-interface Omega2 proxy rather than an independently verified
sharp-region observable. Grid/time-step sensitivity is still absent.
```

Existing-output velocity-observable cross-check:

```text
script = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\a1_bubbleRise_velocity_crosscheck.py
outputs = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_bubbleRise_A1_safi_compare_20260607\a1_velocity_observable_crosscheck*.*
method = compare saved-frame centroid finite-difference velocity against TCLB
         CSV GasTotalVelocityY/GasTotalPhase over the same intervals
result = same positive rise direction, but max interval nondimensional velocity
         difference 0.0461, max relative difference 14.7%, and cumulative
         centroid prediction from CSV velocity is 6.94 cells high by step 12000
interpretation = internal observable-risk evidence; does not lock the velocity
                 mapping and does not support validation_candidate promotion
```

Reference provenance update:

```text
new paper = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\references\papers\adelsberger2014_3d_rising_bubble_benchmark.pdf
paper SHA256 = 4153884D0A884A91EF176CB69F9138700E6C4B5993A7DEC460EC1C90FA48DB14
paper data URL = http://wissrech.ins.uni-bonn.de/research/projects/risingbubblebenchmark
archive data retrieved = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\references\data\bonn_3d_rising_bubble_tc1
curated CSV = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\references\data\bonn_3d_rising_bubble_tc1\bonn_3d_rising_bubble_tc1_reference.csv
summary JSON = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\references\data\bonn_3d_rising_bubble_tc1\bonn_3d_rising_bubble_tc1_reference_summary.json
curated rows = 5388 total: center_of_mass DROPS/NaSt3D/OpenFOAM
               601/595/301 and rise_velocity DROPS/NaSt3D/OpenFOAM
               3001/589/301
center zip SHA256 = db617631d966df349549b729c44c216f6ae056f15c37171231de9e709c7f6842
velocity zip SHA256 = 37cb998a692dccd0440d00fa3dc991f083e9258f2b4e02377f76a632d9585a68
provenance note = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\references\data\a1_bubbleRise_reference_provenance_20260607.md
independent digitization script = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\a1_bubbleRise_independent_digitization.py
independent digitization output = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_bubbleRise_A1_safi_compare_20260607\a1_safi_independent_digitization_600dpi_summary.json
independent digitization result = primary bitmap curve is reproducible at about
                                  L2 difference 0.00244 for center_of_mass and
                                  0.00137 for rise_velocity, but still not
                                  author-tabulated data
Bonn comparison vs Safi bitmap = center_of_mass L2/max abs difference:
                                 DROPS 0.01040/0.01221,
                                 NaSt3D 0.01380/0.01591,
                                 OpenFOAM 0.02904/0.04549;
                                 rise_velocity L2/max abs difference:
                                 DROPS 0.00337/0.01377,
                                 NaSt3D 0.00339/0.01395,
                                 OpenFOAM 0.01382/0.02296
claim limit = Bonn archive data are Adelsberger 2014 TC1 DROPS/NaSt3D/
              OpenFOAM series; do not rename as Safi 2017 FeatFlow without a
              separate mapping audit
```

A direct Bonn/INS TC1 comparison against existing TCLB A1 output was also
created:

```text
artifact = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_bubbleRise_A1_bonn_compare_20260607
script = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\a1_bubbleRise_compare_bonn_reference.py
status = runtime_sanity audit input only; no validation promotion
read-only audit = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_bubbleRise_A1_bonn_compare_20260607\read_only_audit_20260607.md
inputs = existing A1 metrics CSV, existing A1 TCLB CSV log,
         curated Bonn/INS TC1 reference CSV
outputs = a1_bonn_pointwise_comparison.csv,
          a1_bonn_interval_velocity_comparison.csv,
          a1_bonn_comparison_summary.json,
          figures/a1_bonn_center_of_mass_comparison.png,
          figures/a1_bonn_rise_velocity_comparison.png
local raw VTI/PVTI count = 0

center_of_mass pointwise L2/max abs error:
  DROPS = 0.04758 / 0.08268
  NaSt3D = 0.04471 / 0.07970
  OpenFOAM = 0.02981 / 0.04918

rise_velocity TCLB CSV proxy pointwise L2/max abs error:
  DROPS = 0.01490 / 0.03255
  NaSt3D = 0.01337 / 0.03134
  OpenFOAM = 0.02366 / 0.03582

rise_velocity saved-frame centroid interval L2/max abs error:
  DROPS = 0.02783 / 0.03549
  NaSt3D = 0.02968 / 0.03685
  OpenFOAM = 0.01805 / 0.02990

interpretation = the Bonn data route is stronger provenance than bitmap-only
                 curves, but the A1 comparison still exposes nontrivial
                 center-of-mass error and unresolved velocity-observable
                 mapping; it does not support validation_candidate without
                 read-only audit, acceptance thresholds, independent
                 observable mapping, and grid/time-step sensitivity
audit decision = keep runtime_sanity; do not promote to validation_candidate
                 because accepted thresholds are not frozen, Bonn series are
                 not audited as Safi FeatFlow equivalents, velocity
                 observable mapping remains unresolved, centroid interval
                 velocity has only six coarse intervals, only one L0=64 run
                 is available, center-of-mass errors remain nontrivial, and
                 grid/time-step sensitivity is absent
```

Next A1 validation-chain requirements are explicit acceptance thresholds, an
audit decision on which Bonn `DROPS`/`NaSt3D`/`OpenFOAM` series is the
comparison target, an independent VTI-derived velocity-observable check, and
grid/time-step sensitivity before any promotion beyond `runtime_sanity`.

An A1 acceptance-gate protocol and evaluator have now been added to turn this
boundary into a machine-readable failure report:

```text
protocol = docs/a1_bubbleRise_acceptance_protocol.md
script = scripts/a1_bubbleRise_acceptance_gate.py
artifact = artifacts/tclb_bubbleRise_A1_acceptance_gate_20260607
outputs = README.md, a1_acceptance_gate_summary.json,
          read_only_audit_20260607.md
script_check = python -m py_compile returned 0
run_check = python scripts/a1_bubbleRise_acceptance_gate.py returned 0
status_decision = runtime_sanity
local_raw_vti_pvti_count = 0
```

The gate passes runtime health checks but blocks `validation_candidate`
because thresholds are still provisional, no Bonn target series has been
accepted, Bonn ASCII data are not accepted as Safi FeatFlow equivalents, the
rise-velocity observable remains unresolved, no grid/time-step sensitivity
exists, and even the best available Bonn errors exceed the provisional strict
thresholds: center-of-mass L2/max abs `0.02981/0.04918`, rise-velocity CSV
proxy L2/max abs `0.01337/0.03134`, velocity cross-check max absolute
nondimensional difference `0.04609`, and max relative difference `14.7%`.

A bounded A1 grid/time sensitivity chain has now been executed on HM570 and
curated locally:

```text
case_dir = cases/validation/a1_bubbleRise_grid_time_20260607
case_generator = scripts/make_a1_bubbleRise_sensitivity_cases.py
summary_script = scripts/a1_bubbleRise_grid_time_summary.py
run_id = tclb_bubbleRise_A1_grid_time_20260607
completed_cases = coarse_L48, base_L64, fine_L80
remote_run_root = /home/yuan/runs/tclb_bubbleRise_A1_grid_time_20260607
local_summary_artifact = artifacts/tclb_bubbleRise_A1_grid_time_20260607
per-case comparison artifacts =
  artifacts/tclb_bubbleRise_A1_grid_time_20260607_coarse_L48_bonn_compare
  artifacts/tclb_bubbleRise_A1_grid_time_20260607_base_L64_bonn_compare
  artifacts/tclb_bubbleRise_A1_grid_time_20260607_fine_L80_bonn_compare
status = runtime_sanity
local_raw_vti_pvti_count = 0
```

The cases preserve A1 TC1 controls (`Re=35`, `Eo=10`,
`rho_ratio=10`, `viscosity_ratio=10`, `M=0.1`, `IntWidth=5`) and align the
final nondimensional time to the existing A1 comparison window
`T≈2.9303`. All three cases completed with 7 VTI and 7 PVTI each on HM570,
with raw VTI/PVTI left remote-only. Remote sizes are about `131M` for L48,
`231M` for L64, and `538M` for L80. Runtime health is clean for a
runtime-sanity chain:

```text
coarse_L48: max Mach 0.0317124, nonfinite 0,
            fluid phase drift 4.07186e-5, fluid rho drift 3.65341e-5
base_L64:   max Mach 0.0223497, nonfinite 0,
            fluid phase drift 2.93937e-5, fluid rho drift 2.63515e-5
fine_L80:   max Mach 0.0179932, nonfinite 0,
            fluid phase drift 1.69536e-5, fluid rho drift 1.52111e-5
```

Each postprocess stderr has a Matplotlib no-contour warning for an early
morphology frame; record it as a visualization limitation, not a numerical
failure. `coarse_L48/run.returncode` is empty because the first Windows
PowerShell/Bash wrapper lost return-code expansion, but the TCLB `run.log`
reaches the total-duration line and the raw 7/7 VTI/PVTI output is complete.

The completed grid/time comparison does not promote A1. Best per-case Bonn
errors are:

```text
coarse_L48:
  center L2/max = 0.00924309 / 0.0203932 against OpenFOAM
  velocity CSV proxy L2/max = 0.0483373 / 0.0741011 against NaSt3D
base_L64:
  center L2/max = 0.0298448 / 0.0492049 against OpenFOAM
  velocity CSV proxy L2/max = 0.0133679 / 0.0313635 against NaSt3D
fine_L80:
  center L2/max = 0.00776736 / 0.0199537 against DROPS
  velocity CSV proxy L2/max = 0.0347686 / 0.0507230 against NaSt3D
```

Grid/time spreads remain above the provisional gate:

```text
center_of_mass_l2_abs_error_spread = 0.0220774
rise_velocity_l2_abs_error_spread = 0.0349694
```

The A1 acceptance gate was rerun with the grid/time summary and still returns
`runtime_sanity`. It fails because thresholds are provisional, no Bonn target
series has been accepted by audit, Bonn/Safi FeatFlow mapping is unaccepted,
the velocity observable remains unresolved, grid/time spread exceeds the
provisional gate, and the prior L64 Bonn errors/velocity cross-check still
exceed strict thresholds. This is useful diagnostic evidence, not A1
validation.

A bounded A2 geometric-wetting build and theta045 static diagnostic has now
been completed. The independent TCLB target was built on HM570:

```text
build_target = d3q27_pf_velocity_geometric
binary = /home/yuan/src/TCLB/CLB/d3q27_pf_velocity_geometric/main
build_log_remote = /home/yuan/runs/tclb_build_audit_20260607/d3q27_pf_velocity_geometric_build.log
build_artifact_local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_build_audit_20260607
option_state = geometric TRUE; staircaseimp/isograd/tprec FALSE
original_binary_state = /home/yuan/src/TCLB/CLB/d3q27_pf_velocity/main remained geometric FALSE
```

The first local SSH wrapper timed out at 120 s during target generation; no
make/nvcc process remained afterward, and a longer retry completed with return
code 0. This is a wrapper/runtime note, not a failed build.

Only theta045 was run with the geometric binary because the HM570 root
filesystem had limited free space after the single case:

```text
run_id = tclb_static_contact_angle_geometric_calib_20260607
remote = /home/yuan/runs/tclb_static_contact_angle_geometric_calib_20260607/theta045
local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_geometric_calib_20260607
case_xml = cases\validation\static_contact_angle_geometric_calib_20260607\contact_angle_theta045.xml
steps = 200000
raw VTI/PVTI = 21/21 remote-only
local raw VTI/PVTI count = 0
run return code = 0
postprocess return code = 0
convention audit return code = 0
```

Metrics:

```text
input angle = 45 deg
postprocess complement angle = 59.5114 deg
convention-audit liquid-side range = 57.6207-61.8962 deg
best liquid-side error = +12.6207 deg
fluid-only phase drift = -0.8552%
rho drift = -0.8249%
max Mach = 9.398e-5
nonfinite = 0
remote case size = about 1.4G
HM570 free disk after case = about 3.4G
```

Read-only audit keeps this at `exploratory_not_validation`. The geometric-only
route runs cleanly, but it still misses the liquid-side 45 deg calibration and
does not authorize theta090/theta135 continuation, a rho772 impact sweep, or
any validation/production/publication claim.

A follow-up geometric-only low-angle response diagnostic with `radAngle=5d`
was attempted with minimal output to control disk use:

```text
run_id = tclb_static_contact_angle_geometric_rad005_minout_20260607
remote = /home/yuan/runs/tclb_static_contact_angle_geometric_rad005_minout_20260607/theta005
local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_geometric_rad005_minout_20260607
binary = /home/yuan/src/TCLB/CLB/d3q27_pf_velocity_geometric/main
requested steps = 200000
VTK interval = 200000
raw VTI/PVTI = initial 1/1 only, remote-only
local raw VTI/PVTI count = 0
```

This run is `failed_negative_evidence`: the TCLB wrapper wrote return code
`0`, but `run.log` reports `Checking PhaseField discovered NaN` and
`Stopping due to Nan value`. No final field exists, so no valid contact-angle
postprocess was run. This means the geometric-only low-angle route cannot be
blindly inverse-swept under the current `M=0.05`, `IntWidth=4` static setup.
Future low-angle work should change/audit the route first, for example by
reviewing stability parameters or testing a different wetting build variant;
it still does not authorize any impact run.

A bounded A2 `geometric_staircaseimp` build and theta045 diagnostic has now
also been completed. The independent TCLB target was built on HM570:

```text
build_target = d3q27_pf_velocity_geometric_staircaseimp
binary = /home/yuan/src/TCLB/CLB/d3q27_pf_velocity_geometric_staircaseimp/main
build_log_remote = /home/yuan/runs/tclb_build_geometric_staircaseimp_audit_20260607/d3q27_pf_velocity_geometric_staircaseimp_build.log
build_artifact_local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_build_geometric_staircaseimp_audit_20260607
option_state = geometric TRUE; staircaseimp TRUE; isograd/tprec FALSE
original_binary_state = /home/yuan/src/TCLB/CLB/d3q27_pf_velocity/main remained geometric FALSE and staircaseimp FALSE
geometric_only_state = /home/yuan/src/TCLB/CLB/d3q27_pf_velocity_geometric/main remained geometric TRUE and staircaseimp FALSE
```

Only theta045 was run, with minimal VTK output to control HM570 disk use:

```text
run_id = tclb_static_contact_angle_geometric_staircaseimp_20260607
remote = /home/yuan/runs/tclb_static_contact_angle_geometric_staircaseimp_20260607/theta045
local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_geometric_staircaseimp_20260607
case_xml = cases\validation\static_contact_angle_geometric_staircaseimp_20260607\contact_angle_theta045.xml
steps = 200000
VTK interval = 200000
raw VTI/PVTI = 2/2 remote-only
local raw VTI/PVTI count = 0
run return code = 0
postprocess return code = 0
convention audit return code = 0
run.log NaN/failcheck stop lines = 0
```

Metrics:

```text
input angle = 45 deg
postprocess complement angle = 59.511398 deg
convention-audit liquid-side range = 57.620709-61.896170 deg
best liquid-side error = +12.620709 deg
fluid-only phase drift = -0.855225%
rho drift = -0.824869%
max Mach = 3.044e-5
nonfinite = 0
remote case size = about 133M
HM570 free disk after case = about 3.2G
```

Read-only audit keeps this at `exploratory_not_validation`. The geometric plus
staircase-improvement route runs cleanly but gives essentially the same
theta045 mismatch as geometric-only; it is negative evidence for that build
variant as the immediate wetting fix and does not authorize theta090/theta135
continuation, rho772 impact sweeps, or validation/production/publication
claims.

The static contact-angle evaluation protocol was then revised using existing
HM570 output only. No new TCLB simulation was launched. The new artifact is:

```text
artifact = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_revised_eval_20260607
script = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_static_contact_angle_local_tangent_audit.py
summary = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_revised_eval_20260607\static_contact_angle_revised_eval_summary.json
status = exploratory_not_validation
local_raw_vti_pvti_count = 0
```

Revised protocol:

```text
primary static contact angle = local_liquid_side_angle_deg from near-contact-line tangent fits
preferred local windows = 3-8 lattice cells from the lower wall
average = left/right contact lines and x/z mid-slices
secondary shape metric = global whole-cap/circle-fit complement angle
for lower-wall obtuse cases, local liquid-side angle = 180 - tangent-wall acute angle
```

Key revised results:

```text
surface theta045: global complement 57.662 deg; local liquid-side 39.882 +/- 0.330 deg
surface theta090: global complement 90.831 deg; local liquid-side 84.048 +/- 2.262 deg
surface theta135: global complement 135.286 deg; local liquid-side 133.623 +/- 2.974 deg
geometric theta045: global complement 59.511 deg; local liquid-side 43.150 +/- 0.100 deg
geometric_staircase theta045: global complement 59.511 deg; local liquid-side 43.150 +/- 0.100 deg
```

Updated interpretation: the previous theta045 blocker was mainly a
postprocessing/evaluation-definition problem. The geometric and
geometric_staircase theta045 cases show plausible local contact-line behavior
near 45 deg, so current evidence does not prove the geometric wetting model is
wrong. However, this does not authorize impact sweeps or validation promotion:
the local tangent protocol still needs frozen window/threshold choices, visual
audit, static grid sensitivity, and mass/rho/Mach/nonfinite gates.

The geometric static protocol was then tightened into a true wall-distance
window audit:

```text
artifact = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_geometric_protocol_20260607
remote = /home/yuan/runs/tclb_static_contact_angle_geometric_protocol_20260607
source_case = /home/yuan/runs/tclb_static_contact_angle_geometric_calib_20260607/theta045
status = exploratory_not_validation
raw VTI/PVTI = remote-only; local raw count 0
```

Frozen primary protocol:

```text
metric = local_liquid_side_angle_deg
phi = 0.5
wall-distance window = true 3-8 lu, not cumulative 0-w
slices = x-mid and z-mid
average = left/right contact lines and x/z mid-slices
secondary metric = global whole-cap/circle-fit complement angle only
```

Important correction: the first local-tangent artifact used cumulative
maximum-distance fits such as `0-3`, `0-4`, and `0-8`. The frozen protocol
now uses true ranges such as `2-6`, `3-8`, and `4-10 lu`. With this corrected
definition, geometric theta045 gives:

```text
phi=0.50, true 3-8 lu: local angle = 43.2468 deg
angle error = -1.7532 deg
phi/window sensitivity: mean angles 42.0284-43.5174 deg
4-10 lu windows trend lower, near 42 deg
fluid-only phase drift = -0.8552%
rho drift = -0.8249%
max Mach = 9.398e-5
nonfinite = 0
```

Visual overlay shows the tangent lines attach to the near-contact-line region,
not the whole cap. The lower `4-10 lu` results confirm a contact-line/cap
transition trend and must be reported, but they do not by themselves reject
the geometric route. Geometric theta090/theta135 static cases remain required
before any `validation_candidate` request.

The geometric theta090/theta135 minimal-output static cases were then executed
and curated without copying raw VTI/PVTI locally:

```text
run_id = tclb_static_contact_angle_geometric_theta090_theta135_minout_20260607
remote = /home/yuan/runs/tclb_static_contact_angle_geometric_theta090_theta135_minout_20260607
local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_geometric_theta090_theta135_minout_20260607
binary = /home/yuan/src/TCLB/CLB/d3q27_pf_velocity_geometric/main
status = exploratory_not_validation
raw VTI/PVTI = 2 VTI and 2 PVTI per angle, remote-only
local raw VTI/PVTI count = 0
```

Both theta090 and theta135 reached final VTK and total-duration lines. The
same frozen local-tangent protocol and sensitivity were applied:

```text
primary = phi=0.5, true 3-8 lu, x/z mid-slices, left/right average,
          local_liquid_side_angle_deg
sensitivity = phi=0.45/0.50/0.55 and windows 2-6/3-8/4-10 lu
```

Preferred local-tangent results are:

```text
theta045: 43.2468 deg, error -1.7532 deg
theta090: 77.2764 deg, error -12.7236 deg
theta135: 118.1133 deg, error -16.8867 deg
```

The global/circle complement metric gives near-target theta090/theta135 values
(`90.8311 deg` and `133.8511 deg`), so the current result is a local-vs-global
evaluation conflict, not a clean validation pass. Runtime health is finite and
low-Mach:

```text
theta090: fluid phase drift +0.0378%, rho drift +0.0364%,
          max Mach 9.43e-6, nonfinite 0
theta135: fluid phase drift +0.7903%, rho drift +0.7622%,
          max Mach 4.18e-5, nonfinite 0
```

Current gate decision:

```text
static_geometric_gate_not_passed_currently
```

Reason: theta090 and theta135 fail the `<=5 deg` local-angle operational gate
under the frozen protocol. A read-only audit must decide whether this is a
local-tangent protocol failure, an angle-convention/window problem, or a
wetting/parameter issue. Do not start the rho772 dry-wall bounded pilot from
this evidence. HM570 disk was about `1.3G` free after theta135, so no new runs
should start before raw-only cleanup.

Local visual inspection of the `theta090` and `theta135` `phi=0.5`, `3-8 lu`
overlay figures shows that the fit segments sit on visibly curved near-wall
interface portions. The window trend is systematic: theta090 drops from about
`81.22 deg` at `2-6 lu` to `73.36 deg` at `4-10 lu`, and theta135 drops from
about `125.39 deg` to `112.72 deg`. Therefore the current evidence should be
treated as an unresolved local-tangent protocol/macroscopic-vs-microscopic
angle conflict. It is not enough to promote the route, but it is also not a
final proof that the geometric wetting model itself is wrong.

A read-only local-vs-global integration audit was added at:

```text
artifact = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_geometric_local_vs_global_audit_20260607
summary = local_vs_global_audit_summary.json
status = exploratory_not_validation
decision = static_geometric_gate_not_passed_currently
route_decision = geometric_route_unresolved_not_rejected
local_raw_vti_pvti_count = 0
```

This audit confirms that the current frozen local-tangent gate cannot promote
geometric static wetting because theta090/theta135 miss by about `12.72` and
`16.89 deg`. It also confirms that this is not clean evidence of wetting-model
failure because global/circle complements remain close to the theta090/theta135
inputs and the local fits lie on curved near-wall interface regions. The next
static-angle step is not another impact run; it is a revised protocol that
explicitly separates microscopic contact-line tangent angle from macroscopic
sessile-drop apparent angle, followed by read-only audit.

A candidate two-metric static gate has been generated from existing artifacts:

```text
artifact = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_geometric_revised_gate_candidate_20260607
script = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\geometric_static_revised_gate_candidate.py
summary = geometric_static_revised_gate_candidate_summary.json
status = exploratory_not_validation
candidate_gate_status = protocol_revision_candidate_only
validation_candidate_allowed = false
rho772_pilot_allowed_as_validation = false
rho772_pilot_allowed_as_bounded_runtime_probe = true
```

The candidate protocol keeps two metrics separate:

```text
microscopic_contact_line_metric =
  local_liquid_side_angle_deg from phi=0.5, true 3-8 lu

macroscopic_sessile_drop_metric =
  global_cap_or_circle_fit_complement_deg
```

Current evidence under this candidate: theta045 passes the local microscopic
metric; theta090/theta135 fail the local microscopic metric but pass the
macroscopic complement metric; all health checks are finite and low-Mach.
This supports protocol revision, not validation promotion. The candidate cannot
replace the frozen gate until a read-only audit accepts the
microscopic-vs-macroscopic angle convention.

The 2026-06-07 read-only audit narrowly allows one `theta090` dry-wall bounded
runtime probe only as `exploratory_not_validation`. It must use the geometric
binary explicitly, run under `/media/yuan/DATA500/runs`, and report the full
beta/mass/rho/Mach/nonfinite/morphology artifact set. It does not allow
validation, production, a 45/90/135 sweep, an `R0>=32` pilot, or a liquid-film
case.

The failed `/mnt/data500/yuan/runs` route has been replaced by the actual
DATA500 mount under `/media/yuan/DATA500`:

A single geometric theta090 dry-wall bounded runtime probe was then executed
under the narrow 2026-06-07 read-only audit permission:

```text
run_id = tclb_z_wall_rho772_geometric_theta090_bounded_u008_M0025_W6_20260607
remote = /media/yuan/DATA500/runs/tclb_z_wall_rho772_geometric_theta090_bounded_u008_M0025_W6_20260607/theta090
local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_geometric_theta090_bounded_u008_M0025_W6_20260607_theta090
binary = /home/yuan/src/TCLB/CLB/d3q27_pf_velocity_geometric/main
status = exploratory_not_validation
grid = 96 x 96 x 96
R0 = 14
wall = z=0
contact angle = theta090
VelocityZ = 0
DropletOnlyVelocity = 2
DropletVelocityZ = -0.008
GravitationZ = -1e-6
M = 0.025
IntWidth = 6
steps = 3200
VTK interval = 400
TCLB return code = 0
postprocess return code = 0
raw output = 9 VTI and 9 PVTI, remote-only
local raw VTI/PVTI count = 0
first_contact_step = 1200
beta_area max = 1.1679834016380368 at step 3200
beta_box max = 1.1428571428571428 at step 2800
late_beta_area_change = 0.11094382730490548 over steps 2400, 2800, 3200
resting_candidate = false
fluid-only phase drift max = 0.6385566902335673%
rho drift last = -0.5870010310380805%
max Mach = 0.014789263592322023
nonfinite = 0
morphology = frames at 0,400,800,1200,1600,2000,2400,2800,3200
postprocess limitation = one Matplotlib no-contour warning in morphology output
claim limit = runtime health only; no validation, no R0>=32, no 45/90/135 sweep,
              no liquid-film case, no production/publication claim
```

Interpretation: the geometric impact chain runs cleanly for this bounded
theta090 case, with healthy Mach and no nonfinite values. It is not near rest:
`beta_area` reaches its maximum at the final frame and the late-window change
is much larger than the resting tolerance. This result requires read-only audit
before any next step.

Read-only audit of this bounded probe is recorded in the local artifact as
`read_only_audit_20260607.md/json`. The audit decision is:

```text
runtime_probe_condition_satisfied = true
runtime_health = passed_for_bounded_probe
validation_candidate_allowed = false
R0>=32_allowed = false
45/90/135_sweep_allowed = false
liquid_film_allowed = false
production_candidate_allowed = false
publication_ready_allowed = false
```

Therefore the current goal phase has reached bounded runtime health evidence,
but no larger, longer, sweep, or film execution is unlocked without a separate
read-only gate.

```text
old failed candidate = /mnt/data500/yuan/runs
command attempted = rsync -aH --info=progress2 /home/yuan/runs/ /mnt/data500/yuan/runs/
failure = receiver-side Input/output error (5) while writing a VTI file
post-failure = HM570 SSH timed out, then TCP 22 became unreachable
user_followup = remote server is frozen/unresponsive
current physical run root = /media/yuan/DATA500/runs
compatibility run root = /home/yuan/runs -> /media/yuan/DATA500/runs
mount = /media/yuan/DATA500
filesystem = ntfs3 on /dev/sdc1
capacity = 466G total, 49G used, 418G available, 11% used
health check = small write/read/delete under /media/yuan/DATA500/runs passed
representative files = geometric theta090 run.log and final VTI readable
raw counts under DATA500 = 786 VTI and 786 PVTI
run tree size = 49G
```

Local case generators now default future run directories to
`/media/yuan/DATA500/runs`. Historical paths using `/home/yuan/runs` are
readable through the symlink. `dmesg` could not be read as the unprivileged
SSH user, so kernel-level storage diagnostics still require sudo/local console
if the disk misbehaves again.

The geometric static contact-angle fitting route is now being retested with a
contact-line anchored arclength tangent protocol and a grid/interface-width
matrix, because the old wall-distance window underfit theta090/theta135 near
curved contact-line regions:

```text
run_id = tclb_static_contact_angle_geometric_grid_density_20260607
remote = /media/yuan/DATA500/runs/tclb_static_contact_angle_geometric_grid_density_20260607
compatibility = /home/yuan/runs/tclb_static_contact_angle_geometric_grid_density_20260607
local_cases = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\static_contact_angle_geometric_grid_density_20260607
generator = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_tclb_static_contact_angle_geometric_grid_density_cases.py
runner = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_run_static_contact_angle_grid_density_batch.sh
arclength_audit = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_static_contact_angle_arclength_audit.py
binary = /home/yuan/src/TCLB/CLB/d3q27_pf_velocity_geometric/main
status = exploratory_not_validation
steps = 200000
VTK interval = 200000
raw policy = remote-only VTI/PVTI
```

Matrix:

```text
R24_W4_N128x96x128 at theta045/theta090/theta135
R32_W5_N160x128x160 at theta045/theta090/theta135
R32_W6_N160x128x160 at theta045/theta090/theta135
R48_W6_N224x192x224 at theta045/theta090/theta135
R48_W8_N224x192x224 at theta045/theta090/theta135
```

The first launch was stopped early because the runner stored per-case logs at
the shared grid-tag level, which would have overwritten theta045 logs when
theta090/theta135 ran. The runner was fixed to derive the per-theta case
directory from each XML `output` attribute. Interrupted pre-fix output is
preserved under:

```text
/media/yuan/DATA500/runs/tclb_static_contact_angle_geometric_grid_density_20260607/interrupted_pre_per_angle_log_fix_20260607_2230_per_angle_log_fix
```

The restarted batch began at 2026-06-07 22:30 +08. This batch can only answer
whether higher R/IntWidth and arclength fitting reduce the static contact-angle
evaluation conflict. It does not validate TCLB, does not prove grid
convergence, and does not authorize rho772 impact sweeps without read-only
audit.

Current execution caveat, 2026-06-07 late evening:

```text
last_confirmed_state =
  batch PID 14368 running
  active TCLB PID 14396 running R24_W4_N128x96x128 theta045
  R24 theta045 progress reached at least 81000 / 200000 steps
  per-theta log path was confirmed:
    /media/yuan/DATA500/runs/tclb_static_contact_angle_geometric_grid_density_20260607/R24_W4_N128x96x128/theta045/run.log
  postprocess watcher PID 15369 was waiting for BATCH_END
subsequent_state_check =
  repeated SSH checks timed out, including banner exchange to 192.168.1.250:22
  Windows-side HM570 name resolution also failed
interpretation =
  remote execution status is unknown until HM570 is reachable again
  do not classify the TCLB case as completed, failed, or validated from this
  connectivity symptom
next_recovery_action =
  after HM570 returns, first run health-only inspection: date, ps, batch.log,
  run.returncode/run.done, tail run.log, df/findmnt/dmesg if available, and
  only then decide whether to resume, postprocess, or mark failed
```

Recovery/update, 2026-06-08:

```text
new_active_run_root = /media/yuan/8A0E24070E23EAC1/runs
new_active_batch =
  /media/yuan/8A0E24070E23EAC1/runs/tclb_static_contact_angle_geometric_grid_density_20260607
capacity = 894G total, 560G used, 334G available, 63% used
health_check = small write/read/delete under new_active_run_root passed
copied_DATA500_batch =
  /media/yuan/8A0E24070E23EAC1/runs/tclb_static_contact_angle_geometric_grid_density_20260607
problem_found =
  copied XML files still had output="/media/yuan/DATA500/runs/..."
  copied R24_W4 theta045 run.log had NUL/corrupted tail and no completion files
action =
  archived copied partial state under
  copied_partial_before_20260608_0005_retarget_to_8A0E
  retargeted active XML/manifest/scripts from /media/yuan/DATA500/runs to
  /media/yuan/8A0E24070E23EAC1/runs
  restarted the 15-case batch from R24_W4 theta045 at 2026-06-08 00:03 +08
  restarted postprocess watcher for BATCH_END
last_confirmed_new_state =
  batch PID 4787
  active TCLB PID 4813
  watcher PID 4823
  current case R24_W4_N128x96x128 theta045
status = exploratory_not_validation
claim_limit =
  no numerical result is recovered from the copied partial run; treat the new
  8A0E run as the active execution source
```

## Next Work

1. Use `/media/yuan/8A0E24070E23EAC1/runs` for future HM570 run directories
   unless a later disk audit changes the active root. Treat DATA500 as
   historical/unstable for new writes. If
   storage errors recur, stop runs and inspect kernel logs from sudo/local
   console before retrying.
2. Let the geometric static grid-density/arclength batch finish before making
   another wetting-route claim. After completion, run arclength postprocess on
   all final frames, copy only curated artifacts locally, and perform a
   read-only audit of angle, mass/rho, Mach, nonfinite, sensitivity, and
   provenance. Do not promote beyond `exploratory_not_validation` from the raw
   execution alone.
3. Do not continue the same `R0=14`, `theta=90`, `M=0.025`, `IntWidth=6`,
   `DropletVelocityZ=-0.008` sequence as a validation or production candidate.
   The 9600-step extension remains `exploratory_not_validation` and is negative
   evidence for simple time-extension of this small-grid setup.
4. The two-metric geometric static gate audit narrowly allowed one theta090
   dry-wall bounded runtime probe, and that probe has completed with runtime
   health passed for `exploratory_not_validation` only. The frozen local-tangent
   static gate still fails theta090/theta135, so no `validation_candidate`,
   R0>=32 pilot, 45/90/135 impact sweep, longer run-to-rest campaign, or
   liquid-film case is authorized without a new read-only gate.
5. Do not repeat or extend the same `radAngle=5d`, `R0=14`, 6400-step dry-wall
   pilot as if time extension will fix the gate. The first target-45 pilot
   already shows clean runtime but poor mass/rho and no resting state. The next
   useful work should address the wetting implementation/build-option route,
   static mass accounting, or run a standard TCLB validation case before
   another target-45 impact attempt. The static `M=0.025/IntWidth=6` check is
   not a sufficient fix because even after BOUNDARY-aware mass accounting it
   moves the low-angle cases away from the liquid-side 45 bracket and leaves
   rho drift around `1.5%`.
6. Before another longer or larger impact run, perform a bounded read/write
   execution task that reviews the phase-field/wetting setup and target
   scaling choices: mass gate should use `fluid_phase_*` with `BOUNDARY==0`,
   wall ghost phase must be reported, and the output cadence must include
   contact, beta-max, recoil/late-window, and candidate-rest frames.
7. The next impact run should change a justified setup variable rather than
   only extending the same case. Candidate directions include audited
   phase-field/wetting parameter choices, near-wall gap/scaling, or a standard
   TCLB validation case from `docs/literature_case_matrix.md`.
8. Only after theta=90 long-window mass behavior and resting criteria pass a
   read-only audit should a single `R0>=32` theta=90 exploratory pilot be
   attempted; still not a full 45/90/135 sweep.
9. Run validation cases from `docs/literature_case_matrix.md` before treating
   the target 1 mm case as a physical result, and use the fixed metrics from
   `docs/validation_and_output_protocol.md` for any later contact-angle sweep.
10. For A1 bubbleRise specifically, the read-only audit of
   `artifacts\tclb_bubbleRise_A1_safi_compare_20260607` is complete and keeps
   the case at `runtime_sanity`. Bonn/INS archived Adelsberger 2014 TC1 ASCII
   data have been retrieved under
   `references\data\bonn_3d_rising_bubble_tc1`, but they are
   `DROPS`/`NaSt3D`/`OpenFOAM` series and must not be relabeled as Safi 2017
   `FeatFlow` without audit. A direct Bonn-vs-TCLB A1 comparison now exists at
   `artifacts\tclb_bubbleRise_A1_bonn_compare_20260607`, but it remains
   `runtime_sanity` audit input only after read-only audit. Before any
   `validation_candidate` statement, set explicit acceptance thresholds, choose
   the Bonn comparison target by audit, and resolve the velocity observable.
   The L0=48/64/80 grid/time cases have now been executed, but the spread
   metrics and velocity proxy behavior fail the provisional gate, so A1 remains
   `runtime_sanity`. The current A1 acceptance gate is executable at
   `scripts\a1_bubbleRise_acceptance_gate.py` and currently fails promotion
   by design, with output under
   `artifacts\tclb_bubbleRise_A1_acceptance_gate_20260607`.

## Do Not Claim Yet

```text
publication-ready dry-wall result
grid-converged contact-angle trend
mass-conservative rho_ratio=772 impact
Wang 2023 reproduction
high-We result for the 1 mm / 10 mm free-fall target
```
