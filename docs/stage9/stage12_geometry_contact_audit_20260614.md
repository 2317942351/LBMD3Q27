# Stage12 Geometry and Static-Contact Audit

Date: 2026-06-14

Status: geometry-domain fix confirmed; cap-initialized static contact is `runtime_sanity` only for wall, sphere, and cylinder. These are 200-step smoke calculations that verify finite execution, the solid/fluid-domain gate, real contact-line initialization, and post-processing continuity; they are not `validation_candidate` evidence for equilibrium contact angle.

Server state note: as of 2026-06-15 00:51-00:59 CST, the historical remote
run roots are not currently reachable because the data disks are unmounted.
See `docs/stage9/server_operational_state_20260615.md`.

## Root Cause Path

The solid/fluid-domain confusion had two separate causes.

1. The Stage12 native cylinder runner assumed a cylinder axis along `x` and used analytic wetting parameters with `AnalyticSolidAxis=0`. TCLB's generated `Geometry.cpp` native `<Cylinder>` primitive actually fills a circle in normalized `(x,y)` and extends it along `z`. Therefore the native cylinder mask and the analytic wetting model described different solids.

2. Earlier audits treated `BOUNDARY` as a clean 0/1 solid mask. In this model it can be a node-type bit field. The corrected audit uses `IsItBoundary` first and falls back to `BOUNDARY` only when necessary.

The relevant code paths are:

- `scripts/stage12/stage12_native_static_run.sh`: native cylinder changed to z-axis geometry, with `<Cylinder dx="28" nx="40" dy="28" ny="40" dz="0" nz="96"/>` and `AnalyticSolidAxis=2`.
- `scripts/stage12/stage12_static_audit.py`: geometric audit now supports cylinder axes 0/1/2 and uses `IsItBoundary`.
- `scripts/stage12/stage12_geometry_gate.py`: same axis-aware signed-distance gate.
- `third_party/tclb_snapshots/stage9_analytic_wetting_diffuse_interface/models/multiphase/d3q27_pf_velocity/Dynamics.R` and `Dynamics.c.Rt`: default-off cap initializers were added for wall, sphere, and cylinder contact-line tests.

## Rebuilt Binary

The Stage9 analytic-wetting binary was rebuilt on `192.168.1.16`.

```
BUILD_RC=0
main sha256 = c046eb99e33192b379aad855fb2ab0222b72a9c7a1e63cc7d69389246e7eecd8
```

Build script: `scripts/stage12/build_stage9_capinit_remote.sh`.

## Native Geometry Axis-Fix Audit

Remote root:

```
/home/yuan/data_sda/RUNS/runs/stage12_native_static_axisfix_20260614
```

Local archived outputs:

```
artifacts/stage12_native_static_axisfix_20260614
```

Key result: the corrected native cylinder now passes the geometry-domain gate.

| case | status | axis | inside solid fraction | outside fluid fraction | nonfinite phase | contact |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| native_cylinder_theta030 | PASS_RUNTIME_GEOMETRY_CONTACT_DIAGNOSTIC | 2 | 1.000 | 1.000 | 0 | contacted |
| native_cylinder_theta090 | PASS_RUNTIME_GEOMETRY_CONTACT_DIAGNOSTIC | 2 | 1.000 | 1.000 | 0 | contacted |
| native_sphere_theta030 | PASS_RUNTIME_GEOMETRY_NO_CONTACT | n/a | 1.000 | 1.000 | 0 | not_contacted |
| native_sphere_theta090 | PASS_RUNTIME_GEOMETRY_NO_CONTACT | n/a | 1.000 | 1.000 | 0 | not_contacted |

This fixes the prior cylinder-domain failure (`inside_core_solid_fraction ~= 0.91`) and removes the prior theta030 native-cylinder nonfinite phase failure. The native sphere domain remains correct, but the free spherical droplet still does not contact the solid; therefore it is not a contact-angle validation.

## Cap-Initialized Static Smoke Audit

Remote root:

```
/home/yuan/data_sda/RUNS/runs/stage12_cap_static_smoke_20260614
```

Local archived outputs:

```
artifacts/stage12_cap_static_smoke_20260614
```

The cap initializer creates a real contact line. The contact angle reported below is `theta_circle_intersection_abs_deg`: fit the `phi=0.5` interface circle, intersect it with the analytic wall/cylinder/sphere surface, then measure the tangent angle at that continuous intersection. This avoids measuring at a grid contour point that can sit about 1 lu away from the analytic surface.

| case | class | target | measured | error | nonfinite phase | solid/domain gate |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| cap_wall_theta030 | runtime_sanity | 30 | 29.641 | -0.359 | 0 | outside fluid 1.000 |
| cap_wall_theta090 | runtime_sanity | 90 | 89.996 | -0.004 | 0 | outside fluid 1.000 |
| cap_sphere_theta030 | runtime_sanity | 30 | 29.814 | -0.186 | 0 | inside/outside 1.000/1.000 |
| cap_sphere_theta090 | runtime_sanity | 90 | 89.998 | -0.002 | 0 | inside/outside 1.000/1.000 |
| cap_cylinder_theta030 | runtime_sanity | 30 | 29.640 | -0.360 | 0 | inside/outside 1.000/1.000 |
| cap_cylinder_theta090 | runtime_sanity | 90 | 89.985 | -0.015 | 0 | inside/outside 1.000/1.000 |

All cap-initialized smoke cases are intentionally classified as `runtime_sanity`. The close `theta_circle_intersection_abs_deg` values prove the initialization and post-processing geometry chain, not the equilibrium response of the wetting boundary condition. Cylinder has the additional limitation that the current cap initializer uses a local convex-sphere construction on the cylinder cross-section; it proves the corrected cylinder domain and post-processor can support contact-line calculations, but it should not be presented as a final cylinder equilibrium validation.

## Figure Artifacts

Representative local PNGs:

- `artifacts/stage12_native_static_axisfix_20260614/native_cylinder_theta090/native_cylinder_theta090_audit.png`
- `artifacts/stage12_cap_static_smoke_20260614/cap_wall_theta030/cap_wall_theta030_audit.png`
- `artifacts/stage12_cap_static_smoke_20260614/cap_sphere_theta090/cap_sphere_theta090_audit.png`
- `artifacts/stage12_cap_static_smoke_20260614/cap_cylinder_theta090/cap_cylinder_theta090_audit.png`

No raw `.vti`, `.pvti`, `.pri`, binary, or SSH key files were archived locally.

## Current Verdict

The cylinder solid/fluid-domain confusion is fixed at the geometry/runtime level. The earlier claim that the old native cylinder was a valid benchmark is superseded by this axis-aware audit.

Flat wall and sphere now have a real-contact-line static smoke path with angles near 30 and 90 degrees, so the workflow is suitable for longer equilibrium validation. The present 200-step outputs themselves remain `runtime_sanity / exploratory_not_validation` for physical contact-angle claims because they do not demonstrate mass convergence, low-velocity equilibrium, or contact-angle drift convergence. Cylinder is ready for the next gate, but its cap initializer should be upgraded from local cross-section approximation to a documented cylinder-cap construction before claiming full static cylinder validation.

## Next Gate Before Dynamic Impact

1. Run longer static equilibrium cases for wall and sphere with the same cap initialization, monitoring mass, maximum velocity, and contact angle drift.
2. Upgrade the cylinder cap initializer or document the current cross-section construction rigorously, then run the same longer static gate.
3. Only after static wall, sphere, and cylinder pass the long gate should dynamic impact cases be started.
