# Stage17B-B1 Offline Analytic-SDF / Diffuse-Solid Unit Gate

Date: 2026-06-23

Status: `b1_offline_geometry_gate_passed`

This is an offline geometry and shadow-ghost audit only. It is not a TCLB run, not a contact-angle validation, and not a dynamic-impact preflight.

## Inputs

```text
artifact_dir = C:/Users/yuanz/Desktop/lbm-new/repo/artifacts/stage17B_B1_diffuse_solid_sdf_20260623
geometries = plane, z-axis cylinder, sphere
theta sweep = 60, 90, 120 deg
PhaseF write = disabled
TCLB solver source edit = none
```

## B1 Summary

| case | B1 pass | grad std improvement | grad max improvement | jump p99 improvement | min diffuse normal alignment | max ghost clamp fraction |
|---|---:|---:|---:|---:|---:|---:|
| plane | True | 5.67 | 2.07 | 0 | 1 | 0.390625 |
| cylinder_z | True | 5.84 | 2.64 | 12.8 | 0.999683 | 0.387839 |
| sphere | True | 6.37 | 3.17 | 15.6 | 0.999567 | 0.0808081 |

## Interpretation

The diffuse-solid field is generated from the analytic signed distance function, so its wall normal is smooth and tied to the intended curved geometry rather than to the staircase mask topology.

A pass means only that B1 can support a later TCLB shadow-only implementation. It does not authorize writing `PhaseF` and does not prove cylinder or sphere contact angles.

The normal convention in this script is solid-to-fluid: because `psi_s` is one in the solid and zero in the fluid, `grad(psi_s)` points inward and the exported Stage17B normal is `-grad(psi_s)/|grad(psi_s)|`.

The clamp fraction is interpreted together with clamp excess. The default synthetic phase field touches the 0/1 bounds, so some 60/120 degree shadow ghosts are clipped, but the maximum excess must remain below `1e-2` for B1.

## Radius / Eps Sensitivity Sweep

Sweep rows: 60; passed rows: 60; failed rows: 0. The full sweep is recorded in `sweep_metrics.csv`, `sweep_normal_jaggedness.csv`, and `sweep_ghost_bounds.csv`.

## Ghost Shadow Bounds

| case | theta | raw min | raw max | clamped min | clamped max | clamp fraction | max excess | bounded |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| plane | 60 | 2.02248e-15 | 1.0002 | 2.02248e-15 | 1 | 0.385417 | 0.000202404 | True |
| plane | 90 | 1.11022e-15 | 1 | 1.11022e-15 | 1 | 0 | 0 | True |
| plane | 120 | -0.000205775 | 1 | 0 | 1 | 0.390625 | 0.000205775 | True |
| cylinder_z | 60 | 1.88708e-15 | 1.0002 | 1.88708e-15 | 1 | 0.385417 | 0.000203764 | True |
| cylinder_z | 90 | 1.16573e-15 | 1 | 1.16573e-15 | 1 | 0 | 0 | True |
| cylinder_z | 120 | -0.00020569 | 1 | 0 | 1 | 0.387839 | 0.00020569 | True |
| sphere | 60 | 8.15329e-08 | 0.999987 | 8.15329e-08 | 0.999987 | 0 | 0 | True |
| sphere | 90 | 7.45742e-08 | 0.999983 | 7.45742e-08 | 0.999983 | 0 | 0 | True |
| sphere | 120 | -0.000138616 | 0.999982 | 0 | 0.999982 | 0.0808081 | 0.000138616 | True |

## Artifacts

```text
metrics.json
metrics.csv
normal_jaggedness.csv
ghost_bounds.csv
cylinder_psi_normal.png
sphere_psi_normal_midplane.png
ghost_theta_sweep.png
sweep_metrics.csv
sweep_normal_jaggedness.csv
sweep_ghost_bounds.csv
```

## Next Gate

If B1 remains passed after review, the next step is B2 TCLB shadow-only fields: `PsiSolid`, `PsiGradMag`, `PsiNormalX/Y/Z`, `PsiWallGhost`, `PsiThetaImplied`, `PsiJaggedness`, `PsiWriteAllowedFlag`, `NearWallForceMag`, and `NearWallGradPhiMag`. B2 must still not write `PhaseF`.
