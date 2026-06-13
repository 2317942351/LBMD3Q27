# LBMD3Q27

Public audit package for the TCLB `d3q27_pf_velocity` phase-field LBM route,
focused on spherical wetting-boundary diagnostics and PRE 2025 Table II style
static droplet-on-sphere comparisons.

## Status

Current claim status: `exploratory_not_validation`.

This repository is intended for independent code review and reproducibility
triage. It is not a validated reproduction of PRE 2025, Wang 2023, or a
publication-ready solver package.

## Start Here

Read in this order:

1. `AGENTS.md`
2. `UPLOAD_RULES.md`
3. `docs/expert_root_cause_review_packet_20260611.md`
4. `docs/tclb_d3q27_pf_velocity_code_compile_audit_20260610.md`
5. `docs/pre2025_sphere_phi_overshoot_solution_plan_audit_20260610.md`
6. `docs/wall_geom_diag_clean_lane_stage2_20260610.md`
7. `docs/wall_geom_bounded_diag_stage3_20260610.md`
8. `docs/wall_geom_profile_diag_stage4_20260610.md`
9. `docs/wall_geom_profile_600k_extension_20260610.md`
10. `docs/pre2025_sphere_theta030_profile_liftZ32_geometry_audit_20260610.md`
11. `docs/wall_normal_path_v6diag_M0p1_control_50k_20260611.md`
12. `docs/stage7_signed_wall_ghost_diagnostic_20260612.md`
13. `docs/stage7b_low_angle_signed_wall_stability_diagnostic_20260612.md`
14. `docs/stage8_boundary_fluid_gradient_wetting_diagnostic_20260612.md`
15. `docs/stage8c_local_angle_boundary_gradient_candidate_20260612.md`
16. `docs/stage8d_sphere_shadow_limiter_attribution_20260612.md`
17. `docs/stage8e_normal_residual_only_wetting_candidate_20260613.md`
18. `docs/stage8f_normal_limiter_root_cause_diag_20260613.md`
19. `docs/stage8g_cap_contract_revision_diag_20260613.md`
20. `docs/index_current_stage.md`

## Source Layout

- `third_party/tclb_snapshots/upstream_base/`: minimal TCLB
  `models/multiphase/d3q27_pf_velocity` source snapshot from upstream commit
  `ded67cd768cf7e727bd078af139e3ec7895076e5`.
- `third_party/tclb_snapshots/stage2_clean_diag/`: clean wall diagnostic lane.
- `third_party/tclb_snapshots/stage3_bounded_diag/`: bounded diagnostic lane.
- `third_party/tclb_snapshots/stage4_profile_diag/`: profile diagnostic lane.
- `third_party/tclb_snapshots/stage5_unified_special_diag/`: v5 unified special/correction diagnostic lane.
- `third_party/tclb_snapshots/stage6_normal_path_diag/`: v6 normal-path diagnostic lane.
- `third_party/tclb_snapshots/stage7_signed_wall_ghost_diag/`: Stage7 signed wall-ghost diagnostic lane.
- `third_party/tclb_snapshots/stage7b_low_angle_signed_wall_stability_diag/`: Stage7b active relaxed signed-wall diagnostic lane.
- `third_party/tclb_snapshots/stage8_boundary_fluid_gradient_wetting_diag/`: Stage8 boundary-gradient wetting diagnostic lane.
- `third_party/tclb_snapshots/stage8c_local_angle_boundary_gradient_candidate_diag/`: Stage8c local wall-angle gradient candidate lane.
- `third_party/tclb_snapshots/stage8d_sphere_shadow_limiter_attribution/`: Stage8d sphere shadow limiter attribution lane.
- `third_party/tclb_snapshots/stage8e_normal_residual_only_wetting_candidate/`: Stage8e normal-residual-only candidate lane.
- `third_party/tclb_snapshots/stage8f_normal_limiter_root_cause_diag/`: Stage8f normal-limiter root-cause diagnostic lane.
- `third_party/tclb_snapshots/stage8g_cap_contract_revision_diag/`: Stage8g cap-contract and low-angle regularization shadow diagnostic lane.
- `third_party/tclb_snapshots/patches/`: diffs against the upstream snapshot.
- `scripts/`: local generators, postprocessors, audits, and HM570 runners.
- `cases/`: XML case definitions and manifests.
- `references/`: public metadata, extracted numerical tables, and reference
  data. Copyrighted paper PDFs are intentionally not included.
- `artifacts/`: curated CSV/JSON/PNG/XML/log evidence only. Raw VTI/PVTI/PRI
  fields and binaries are intentionally excluded.

## Review Targets

The main review questions are:

- Whether TCLB wall `PhaseF` construction on curved/special solid boundaries
  is mathematically consistent for low wetting angles.
- Whether the bounded/profile diagnostic changes are causal controls or
  physically justified boundary improvements.
- Whether bottom-wall contamination and lower-hemisphere surface film explain
  the long-time drift in the `theta030/radAngle011/M0.1/W6` spherical case.
- What exact code changes should be made before any validation promotion.

## Modification Policy

This is a public read-only audit repository in intent. External users may read
and review it, but this project does not accept unsolicited commits, pull
requests, or direct write access.

Important legal boundary: TCLB source files are GPLv3-licensed upstream
materials. GPLv3 rights are preserved for those files. Repository governance can
prevent direct modification of this canonical GitHub repository, but it cannot
remove GPLv3 rights from upstream TCLB code.

