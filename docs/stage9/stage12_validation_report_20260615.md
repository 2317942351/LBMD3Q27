# Stage12 Wetting-BC Validation Report

Date: 2026-06-15
Branch: `feature/analytic-wetting-bc-diffuse-interface`
Status: `exploratory_not_validation` / `runtime_sanity`; equilibrium shape direction is encouraging, but the full wetting-BC validation gate is not passed.

## 1. Problem This Run Tests

The prior Stage12 cap-static smoke report showed near-perfect contact angles
after only 200 steps. That result was useful for geometry and post-processing
sanity, but it was circular as a wetting-BC validation: the cap initializer and
the wetting boundary used the same angle, and the circle-intersection metric
could simply recover the initial cap geometry.

This 2026-06-15 run was designed to break that circularity:

- 12 cases: wall, sphere, and cylinder, each with two equilibrium cases and two
  decoupled cases.
- Equilibrium cases: `init_theta == bc_theta` at 30 and 150 degrees, run for
  30000 steps.
- Decoupled cases: `init_theta != bc_theta`, with 60 to 30 and 120 to 150.
- The load-bearing shape metric is `theta_shape_end_deg` from
  `stage12_shape_angle_analysis.py`.
- The single-cell gradient angle is retained as a diagnostic only because it is
  noisy and can jump between local branches, especially on curved geometry.

## 2. Server and Paths

Current Linux execution paths:

```text
run root:
  /mnt/usb1t/RUNS/runs/stage12_validation_20260615/

binary:
  /mnt/win_sda2/RUNS/runs/stage9/src/TCLB_stage9_analytic_wetting_20260614/CLB/d3q27_pf_velocity_q27_geometric/main

stage9 source:
  /mnt/win_sda2/RUNS/runs/stage9/src/TCLB_stage9_analytic_wetting_20260614/

scripts:
  /home/yuan/stage12_validation_run.py
  /home/yuan/stage12_shape_angle_analysis.py
  /home/yuan/stage12_convergence_plot.py
  /home/yuan/stage12_angle_timeseries.py
  /home/yuan/run_stage12_validation_20260615.sh

global logs:
  /home/yuan/validation_12cases.log
  /home/yuan/relaunch_cyl.log
```

Current mount evidence from HM570:

```text
/mnt/usb1t    /dev/sdd1  fuseblk  932G total, 596G free
/mnt/win_sda2 /dev/sda2  fuseblk  2.8T total, 296G free
```

## 3. Runtime Health

All 12 validation cases completed with `RUN_RC=0`, zero NaN lines in `run.log`,
and 16 periodic VTI frames on the server. Local curated artifacts include case
XML, metadata, run logs, JSON summaries, and PNG figures; raw VTI fields remain
remote-only.

| case | rc | NaN lines | mass drift | KE ratio | gradient end | gradient drift |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| decouple_wall_60to30 | 0 | 0 | 1.52e-04 | 0.776 | 43.0 | 6.6 |
| decouple_wall_120to150 | 0 | 0 | 9.85e-05 | 0.636 | 43.3 | 1.6 |
| equil_wall_t30 | 0 | 0 | 3.96e-04 | 0.973 | 47.4 | 5.5 |
| equil_wall_t150 | 0 | 0 | 1.82e-04 | 0.643 | 49.6 | 3.0 |
| decouple_sphere_60to30 | 0 | 0 | 1.02e-04 | 0.989 | 26.3 | 0.7 |
| decouple_sphere_120to150 | 0 | 0 | 5.31e-05 | 0.336 | 85.2 | 30.4 |
| equil_sphere_t30 | 0 | 0 | 1.47e-04 | 0.675 | 34.8 | 25.7 |
| equil_sphere_t150 | 0 | 0 | 9.76e-05 | 0.410 | 8.2 | 0.9 |
| decouple_cyl_60to30 | 0 | 0 | 6.94e-05 | 0.958 | 62.7 | 34.4 |
| decouple_cyl_120to150 | 0 | 0 | 1.07e-04 | 0.154 | 88.6 | 0.0 |
| equil_cyl_t30 | 0 | 0 | 1.83e-04 | 0.683 | 34.6 | 1.1 |
| equil_cyl_t150 | 0 | 0 | 9.99e-05 | 0.026 | 102.0 | 0.3 |

The runtime evidence is good enough for `runtime_sanity`. It is not sufficient
for `validation_passed` because convergence is false for most equilibrium
cases and the decoupled response test fails under the shape metric.

## 4. Equilibrium Shape Results

The equilibrium cases show the expected qualitative direction for all three
geometries: theta 30 remains acute and theta 150 remains obtuse.

| case | geometry | target | theta_shape_end | error | shape drift | converged | direction |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| equil_wall_t30 | wall | 30 | 42.6 | +12.6 | 1.6 | false | acute |
| equil_wall_t150 | wall | 150 | 132.0 | -18.0 | 1.4 | false | obtuse |
| equil_sphere_t30 | sphere | 30 | 36.9 | +6.9 | 1.0 | false | acute |
| equil_sphere_t150 | sphere | 150 | 121.2 | -28.8 | 1.5 | false | obtuse |
| equil_cyl_t30 | cylinder | 30 | 37.8 | +7.8 | 1.0 | false | acute |
| equil_cyl_t150 | cylinder | 150 | 144.7 | -5.3 | 0.5 | true | obtuse |

Interpretation:

- This is meaningful evidence that the corrected wall, sphere, and cylinder
  solid/fluid-domain setup can produce the expected static acute/obtuse
  morphology.
- Cylinder theta 150 is the strongest case in this batch: it is converged by
  the current convergence script and is only -5.3 degrees from target.
- The overall data still cannot be called `validation_passed`: five of six
  equilibrium convergence gates are false, and the theta 150 sphere error is
  large.

## 5. Decoupled Response Results

The decoupled cases were intended as the decisive non-circular test: if the cap
starts at one angle and the BC prescribes another, the shape should move closer
to the BC target. Under the shape metric, none of the six decoupled cases moved
closer to the target by the end of 30000 steps.

| case | geometry | init | BC | theta_shape_end | moved closer to BC | converged | note |
| --- | --- | ---: | ---: | ---: | --- | --- | --- |
| decouple_wall_60to30 | wall | 60 | 30 | 69.3 | false | false | not toward target by shape metric |
| decouple_wall_120to150 | wall | 120 | 150 | 111.8 | false | false | not toward target by shape metric |
| decouple_sphere_60to30 | sphere | 60 | 30 | 65.0 | false | false | not toward target by shape metric |
| decouple_sphere_120to150 | sphere | 120 | 150 | 108.4 | false | false | not toward target by shape metric |
| decouple_cyl_60to30 | cylinder | 60 | 30 | 65.5 | false | true | not toward target by shape metric |
| decouple_cyl_120to150 | cylinder | 120 | 150 | 123.5 | false | false | not toward target by shape metric |

This is unresolved negative evidence. It may reflect the definition of the
global shape metric, slow cap-volume relaxation, or an implementation issue in
the imposed wetting response. It cannot be described as proof that the BC drives
the contact angle.

## 6. Current Verdict

The project should treat this batch as:

```text
status = exploratory_not_validation / runtime_sanity
```

Supported claims:

- The server can run the 12-case Stage12 validation matrix from the mounted
  `/mnt/usb1t` and `/mnt/win_sda2` paths.
- All 12 cases completed without solver NaNs and produced full periodic VTI
  output on the server.
- The corrected geometric domains support wall, sphere, and cylinder static
  calculations.
- Equilibrium shape results have the correct qualitative direction for all
  three geometries: theta 30 is acute and theta 150 is obtuse.

Unsupported claims:

- Do not claim `validation_passed`.
- Do not claim publication-ready static contact-angle validation.
- Do not claim dynamic impact cases are cleared.
- Do not claim the decoupled response test passed.

The next technical blocker is not raw runtime stability. It is the non-circular
BC-response evidence: the decoupled cases need to move toward the prescribed BC
target under a defensible metric, and the equilibrium cases need stricter mass,
kinetic-energy, and angle-drift convergence.

## 7. Required Next Gate

1. Re-audit `stage12_shape_angle_analysis.py` on decoupled cases: confirm the
   circle-arc branch, angle convention, and whether the reported global angle is
   appropriate for transient cap relaxation.
2. Add a local near-contact metric that is less noisy than single-cell gradient
   but less global than whole-cap circle fitting.
3. Extend or refine a smaller diagnostic matrix before dynamic impact:
   wall/sphere/cylinder, theta 30 and 150, with explicit acceptance thresholds
   for mass drift, kinetic energy decay or plateau, and angle drift.
4. Only after the decoupled response and equilibrium gates pass should dynamic
   wall, cylinder, and sphere impact cases be launched.

## 8. Reproducibility

Repository scripts:

```text
scripts/stage12/stage12_validation_run.py
scripts/stage12/run_stage12_validation_20260615.sh
scripts/stage12/postprocess_stage12_validation_20260615.sh
scripts/stage12/stage12_shape_angle_analysis.py
scripts/stage12/stage12_convergence_plot.py
scripts/stage12/stage12_angle_timeseries.py
```

Curated local artifacts:

```text
artifacts/stage12_validation_20260615/<case_name>/
```

Representative figures:

```text
artifacts/stage12_validation_20260615/equil_wall_t30/equil_wall_t30_shape_angle.png
artifacts/stage12_validation_20260615/equil_sphere_t30/equil_sphere_t30_shape_angle.png
artifacts/stage12_validation_20260615/equil_cyl_t150/equil_cyl_t150_shape_angle.png
```
