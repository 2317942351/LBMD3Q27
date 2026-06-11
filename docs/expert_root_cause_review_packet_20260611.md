# Expert Root-Cause Review Packet

Date: 2026-06-11

Status: `runtime_sanity / exploratory_not_validation`

## Purpose

This packet is the current handoff for independent experts reviewing the TCLB
`d3q27_pf_velocity` spherical wetting failure. The target is not to claim a
validated PRE 2025 reproduction. The target is to identify the boundary-condition
root cause and propose exact source changes that can be audited.

## Short Conclusion To Audit

The current evidence supports this working diagnosis:

```text
The separated theta030 sphere failure is controlled by the curved-wall
profile/unified wall PhaseF reconstruction and its near-wall geometry contract.
It is not primarily caused by bulk phase-field dynamics, zonal radAngle parsing,
bottom outer-wall leakage, special/correction fallback branches, direct storage
of the old raw geometric overrun, or mobility M alone.
```

This is still a diagnosis, not a validated fix.

## Required Reading Order

1. `docs/pre2025_wetting_boundary_tclb_analysis_20260609.md`
2. `docs/tclb_d3q27_pf_velocity_code_compile_audit_20260610.md`
3. `docs/pre2025_sphere_phi_overshoot_solution_plan_audit_20260610.md`
4. `docs/pre2025_sphere_known_bad_geometry_20260611.md`
5. `docs/pre2025_sphere_z48_outer90_zonal_smoke_20260611.md`
6. `docs/wall_profile_unified_special_v5diag_50k_20260611.md`
7. `docs/wall_normal_path_v6diag_smoke_20260611.md`
8. `docs/wall_normal_path_v6diag_50k_20260611.md`
9. `docs/wall_normal_path_v6diag_M0p1_control_50k_20260611.md`
10. `docs/remote_local_file_index.md`

## Most Relevant Evidence Artifacts

Same-binary v6 M-control:

```text
artifacts/pre2025_sphere_theta030_z48_v6_M_control_compare_20260611/
  v6_M_control_selected_metrics.csv
  v6_M_control_summary.json
  v6_M_control_metrics.png
  v6_M_control_morphology_montage.png
  v6_M_control_wall_normal_path_montage.png
```

v6 M0.1 case evidence:

```text
artifacts/pre2025_sphere_theta030_z48_gap24_outer90_sphere11_normal_path_v6diag_M0p1_50k_20260611/
```

v6 M0.2 case evidence:

```text
artifacts/pre2025_sphere_theta030_z48_gap24_outer90_sphere11_normal_path_v6diag_50k_20260611/
```

v5 special/correction branch control:

```text
artifacts/pre2025_sphere_theta030_z48_gap24_outer90_sphere11_unified_special_v5diag_50k_20260611/
```

Flat-wall gate context:

```text
artifacts/flat_wall_cap_v4capdiag_gate_20260611/
```

## Source And Patch Evidence

v6 normal-path diagnostic source patch:

```text
patches/wall_normal_path_v6diag_20260611/
  source_patch.diff
  source_diff_after_build.patch
  generated_symbol_grep.txt
  binary_sha256.txt
third_party/tclb_snapshots/stage6_normal_path_diag/
```

v5 unified special/correction diagnostic source patch:

```text
patches/wall_profile_unified_special_v5diag_20260611/
  source_diff_after_build.patch
  generated_symbol_grep_after_regen.txt
  binary_sha256.txt
  first_make_C_CLB_build_status.txt
third_party/tclb_snapshots/stage5_unified_special_diag/
```

Baseline source snapshots:

```text
third_party/tclb_snapshots/upstream_base/
third_party/tclb_snapshots/stage4_profile_diag/
```

If reviewing the source, prioritize `Boundary.c.Rt`, then `Dynamics.R` for
zonal parameter declarations and VTK field registration.

## Current Key Numbers

Same geometry:

```text
domain = 80 x 80 x 180
VTI cell dims = 96 x 80 x 180
R_drop = 24
R_solid = 24
solid_center_z = 48
bottom_gap = 24 = 4W
default/OuterDomain radAngle = 90d
SolidSphere radAngle = 11d
IntWidth = 6
```

v6 same-binary 50k M-control:

| metric | M0.2 | M0.1 |
|---|---:|---:|
| fitted contact angle | 107.125719 deg | 110.463991 deg |
| H1-H2 relative error | 104.719123% | 107.240435% |
| fluid phase drift | -0.618564% | -0.495228% |
| fluid rho drift | -0.605953% | -0.485131% |
| max Mach | 4.91852e-4 | 4.86702e-4 |
| lower90 phi fraction | 0.0316102 | 0.0133860 |
| bottom120 phi fraction | 0.00812668 | 0.00210920 |
| z-min outside-sphere phi fraction | 0 | 0 |
| normal-path raw WallPhasePred max | 1.448023 | 1.484613 |
| normal-path unified/profile max | 0.9999977 | 0.9999936 |
| normal-path WallActualMinusProfile max | 0 | 0 |
| wall/fluid PhaseField > 1 count | 0 / 0 | 0 / 0 |

Interpretation:

```text
Lower M reduces drift and bottom/lower-hemisphere film, but does not correct
the 30 degree curved-sphere wetting response.
```

## Evidence That Has Narrowed The Failure

1. `z24` global-low-angle geometry is known-bad because the solid sphere touches
   the z-min outer wall and the outer wall also receives `radAngle=11d`.
2. z48/gap24 with outer wall `radAngle=90d` removes the z-min leakage channel
   to numerical-negligible levels, but the curved-sphere morphology remains
   wrong.
3. Zonal `radAngle` works: `DefaultZone/OuterDomain=90d`, `SolidSphere=11d`
   are visible in generated config/CSV and wall diagnostics.
4. v5 unified the special/correction wall reconstruction diagnostics, but
   runtime `NumSpecialPoints=0` in the separated z48 case, so those branches
   are not the controlling path.
5. v6 shows the actual normal-path wall `PhaseF` equals the bounded
   profile/unified write: `WallActualMinusProfile=0`. The old raw geometric
   prediction still exceeds 1, but it is not directly stored in this lane.
6. M0.1 versus M0.2 changes drift and film amount but not the high-angle wrong
   response.

## Main Root-Cause Questions For Review

Please audit these as source-level questions:

1. Is the current profile/unified wall reconstruction formula mathematically
   consistent with a prescribed low contact angle on a curved solid surface?
2. Does the implementation correctly use signed local interface normal,
   geometric wall normal, and wall distance `h`, or does it lose the sign needed
   to distinguish wetting/dewetting response on curved surfaces?
3. Are gradients near solid nodes reading physical `PhaseF`, ghost wall
   `PhaseF`, or sentinel/mixed values consistently?
4. Should `PhaseF=-999` be structurally separated into a solid mask and a wall
   ghost field before further formula work?
5. Does the current wall reconstruction enforce a profile value but not the
   desired contact-angle constraint, explaining bounded fields with wrong
   macroscopic response?
6. Can a single reconstruction helper be defined for normal, further-next
   special, and correction paths after the normal path is fixed?

## Proposed Next Patch Direction

Do not use clamp-only logic as a physical cure. A credible candidate should:

```text
1. keep `PhaseF` as physical fluid phase only;
2. introduce or emulate a distinct wall ghost value and solid/wall mask;
3. reconstruct wall ghost from a signed contact-angle relation using local
   interface normal and wall normal;
4. make boundedness/profile consistency explicit and separately reported;
5. run flat-wall theta030/090/150 first;
6. then run separated z48/gap24 theta030 50k;
7. report branch counts, special fallback counts, predicted-vs-actual wall
   phase, mass drift, Mach, nonfinite, lower/bottom film fractions.
```

## Forbidden Misreadings

Do not interpret the current repository as:

```text
validated physical prediction
publication-ready PRE 2025 reproduction
proof that M0.1 solves the problem
proof that raw geometric overrun is harmless in every lane
permission to hide failure with clipping or unreported damping
```

Current status remains:

```text
runtime_sanity / exploratory_not_validation
```

