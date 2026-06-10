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
3. `docs/tclb_d3q27_pf_velocity_code_compile_audit_20260610.md`
4. `docs/pre2025_sphere_phi_overshoot_solution_plan_audit_20260610.md`
5. `docs/wall_geom_diag_clean_lane_stage2_20260610.md`
6. `docs/wall_geom_bounded_diag_stage3_20260610.md`
7. `docs/wall_geom_profile_diag_stage4_20260610.md`
8. `docs/wall_geom_profile_600k_extension_20260610.md`
9. `docs/pre2025_sphere_theta030_profile_liftZ32_geometry_audit_20260610.md`

## Source Layout

- `third_party/tclb_snapshots/upstream_base/`: minimal TCLB
  `models/multiphase/d3q27_pf_velocity` source snapshot from upstream commit
  `ded67cd768cf7e727bd078af139e3ec7895076e5`.
- `third_party/tclb_snapshots/stage2_clean_diag/`: clean wall diagnostic lane.
- `third_party/tclb_snapshots/stage3_bounded_diag/`: bounded diagnostic lane.
- `third_party/tclb_snapshots/stage4_profile_diag/`: profile diagnostic lane.
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
