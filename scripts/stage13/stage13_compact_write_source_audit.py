#!/usr/bin/env python3
"""Static source audit for the Stage13 compact-stencil write path.

This is a regression guard for the wetting-closure work. It proves only that
the source is wired so compact-stencil q_s can enter WallGhost and the near-wall
phase stencils. It does not validate contact angles; runtime gates must do that.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def contains(text: str, pattern: str) -> bool:
    return re.search(pattern, text, flags=re.MULTILINE | re.DOTALL) is not None


def function_block(text: str, name: str) -> str:
    start = text.find(name)
    if start < 0:
        return ""
    end = text.find("\nCudaDeviceFunction", start + 1)
    return text[start:] if end < 0 else text[start:end]


def outflow_blocks_avoid_raw_phase_neighbors(text: str) -> bool:
    for function_name in ("calcGradPhiRaw", "calcMu"):
        start = text.find(function_name)
        if start < 0:
            return False
        end = text.find("\nCudaDeviceFunction", start + 1)
        block = text[start:] if end < 0 else text[start:end]
        match = re.search(
            r"#ifdef\s+OPTIONS_OutFlow(?P<body>.*?)#else",
            block,
            flags=re.MULTILINE | re.DOTALL,
        )
        if match is None:
            return False
        raw_reads = re.findall(r"PhaseF\(([^)]*)\)", match.group("body"))
        for args in raw_reads:
            if args.replace(" ", "") != "0,0,0":
                return False
    return True


def find_model_dir(root: Path) -> Path:
    candidates = [
        root / "tclb" / "models" / "multiphase" / "d3q27_pf_velocity",
        root
        / "third_party"
        / "tclb_snapshots"
        / "stage9_analytic_wetting_diffuse_interface"
        / "models"
        / "multiphase"
        / "d3q27_pf_velocity",
    ]
    for candidate in candidates:
        if (candidate / "Boundary.c.Rt").exists():
            return candidate
    raise FileNotFoundError(
        "cannot find d3q27_pf_velocity model under tclb/ or repo third_party snapshot"
    )


def audit(root: Path) -> dict[str, Any]:
    model_dir = find_model_dir(root)
    boundary_path = model_dir / "Boundary.c.Rt"
    dynamics_c_path = model_dir / "Dynamics.c.Rt"
    dynamics_r_path = model_dir / "Dynamics.R"
    run_script_path = root / "scripts" / "stage13" / "stage13_flat_wall_diagnostic_run.py"
    audit_script_path = root / "scripts" / "stage13" / "stage13_flat_wall_diagnostic_audit.py"

    boundary = read(boundary_path)
    dynamics_c = read(dynamics_c_path)
    dynamics_r = read(dynamics_r_path)
    run_script = read(run_script_path)
    audit_script = read(audit_script_path)
    can_write_block = function_block(boundary, "stage13_compact_solution_can_write")
    fallback_gate_block = function_block(boundary, "stage13_csq_fallback_allows_write")
    real_fluid_block = function_block(boundary, "stage13_compact_vertex_is_real_fluid")
    triangle_block = function_block(boundary, "stage13_try_compact_triangle")
    compute_block = function_block(boundary, "stage13_compute_compact_stencil_solution")

    checks: dict[str, bool] = {
        "q_mapping_present": all(
            token in boundary
            for token in ["stage13_phase_to_q", "stage13_q_to_phase", "PhaseField_h - PhaseField_l"]
        ),
        "compact_write_request_gate_present": contains(
            boundary,
            r"stage13_compact_write_requested\s*\([^)]*\).*?"
            r"WallCompactStencilMode\s*>\s*1\.5.*?"
            r"WallCompactStencilWriteAllowedFlag\s*>\s*0\.5",
        ),
        "compact_solution_can_write_requires_complete": contains(
            boundary,
            r"stage13_compact_solution_can_write\s*\([^)]*\).*?"
            r"WallCSQValid\s*>\s*0\.5.*?"
            r"WallCSQMethodComplete\s*>\s*0\.5",
        ),
        "compact_solution_can_write_requires_strict_gates": all(
            token in can_write_block
            for token in [
                "stage13_compact_normal_mode_allows_write",
                "stage13_csq_fallback_allows_write",
                "WallCSQBoundedDelta <= max_bounded_delta",
                "fabs(WallCSQAppliedResidual) <= max_applied_residual",
                "WallCSQStrictWriteReady = ready ? 1.0 : 0.0",
            ]
        ),
        "compact_fallback_reason_gate_is_only_ok_or_neutral": all(
            token in fallback_gate_block
            for token in [
                "fabs(WallCSQFallbackReason) < 0.5",
                "fabs(WallCSQFallbackReason - 4.0) < 0.5",
            ]
        )
        and "WallCSQFallbackReason - 90.0" not in fallback_gate_block,
        "compact_solution_writes_wallghost": contains(
            boundary,
            r"WallGhost\s*=\s*stage13_compact_solution_wall_ghost\s*\(",
        ),
        "compact_write_success_path_id_30": "WettingPathId = 30.0" in boundary,
        "compact_write_incomplete_path_id_minus30": "WettingPathId = -30.0" in boundary,
        "compact_write_branch_precedes_legacy_analytic": (
            boundary.find("if (compact_write)") >= 0
            and boundary.find("WallGhost = stage13_compute_analytic_wall_ghost") >= 0
            and boundary.find("if (compact_write)")
            < boundary.find("WallGhost = stage13_compute_analytic_wall_ghost")
        ),
        "true_compact_three_vertex_search_present": all(
            token in boundary
            for token in [
                "stage13_try_compact_triangle",
                "stage13_barycentric_3d",
                "WallCSQFluidVertexCount = 3.0",
                "WallCSQVertexRealFluidBits",
                "WallCSQVertexPhaseCleanBits",
                "stage13_compact_vertex_is_real_fluid",
            ]
        ),
        "compact_vertices_require_real_fluid_mask_not_only_signed_distance": all(
            token in real_fluid_block
            for token in [
                "stage13_boundary_phase_is_valid(pf)",
                "IsBoundary_dyn(ox, oy, oz)",
            ]
        )
        and "stage13_analytic_signed_distance" not in real_fluid_block
        and all(
            token in triangle_block
            for token in [
                "a_geom_fluid = stage13_compact_vertex_is_geometric_fluid",
                "a_real_fluid = stage13_compact_vertex_is_real_fluid",
                "a_fluid = a_geom_fluid && a_real_fluid",
                "WallCSQVertexRealFluidBits",
            ]
        ),
        "compact_solution_tracks_applied_residual": all(
            token in boundary
            for token in [
                "WallCSQAppliedResidual = stage13_wall_csq_residual(q_s_bounded",
                "getWallCSQAppliedResidual",
            ]
        ),
        "normal_mode_is_active_and_unsupported_modes_reject_write": all(
            token in boundary
            for token in [
                "stage13_compact_normal_mode_allows_write",
                "return (WallCompactStencilNormalMode > 0.5 && WallCompactStencilNormalMode < 1.5)",
                "WallCSQFallbackReason = 11.0",
            ]
        )
        and 'AddSetting(name="WallCompactStencilNormalMode"' in dynamics_r
        and "stage13_compact_normal_mode_allows_write" in can_write_block
        and "stage13_compact_normal_mode_allows_write" in compute_block,
        "old_shadow_blocker_removed": "WallCSQFallbackReason = 90.0" not in boundary,
        "huge_special_sentinel_removed": "2342e10" not in boundary,
        "special_sentinel_is_negative": "SPECIAL_POINT_HUGE_MAGIC_NUMBER = -999.0" in boundary,
        "phase_stencil_macro_prefers_wallghost": contains(
            dynamics_c,
            r"#define\s+STAGE13_PHASE_FOR_STENCIL.*?"
            r"stage13_select_phase_for_stencil\s*\(\s*PhaseF\(dx,dy,dz\).*?"
            r"WallGhost\(dx,dy,dz\)",
        ),
        "phase_stencil_fallback_diagnostics_present": all(
            token in dynamics_c
            for token in [
                "PhaseStencilGhostUseCount = PhaseStencilGhostUseCount + 1.0",
                "PhaseStencilFallbackCount = PhaseStencilFallbackCount + 1.0",
                "PhaseStencilMidpointFallbackCount = PhaseStencilMidpointFallbackCount + 1.0",
            ]
        ),
        "phase_stencil_quantity_getters_present": all(
            token in dynamics_c
            for token in [
                "getPhaseStencilGhostUseCount",
                "getPhaseStencilFallbackCount",
                "getPhaseStencilMidpointFallbackCount",
            ]
        ),
        "phase_stencil_diagnostics_have_field_quantity_getter_closure": all(
            field_token in dynamics_r
            and quantity_token in dynamics_r
            and getter_token in dynamics_c
            for field_token, quantity_token, getter_token in [
                (
                    'AddField("PhaseStencilGhostUseCount"',
                    'AddQuantity(name="PhaseStencilGhostUseCount"',
                    "getPhaseStencilGhostUseCount",
                ),
                (
                    'AddField("PhaseStencilFallbackCount"',
                    'AddQuantity(name="PhaseStencilFallbackCount"',
                    "getPhaseStencilFallbackCount",
                ),
                (
                    'AddField("PhaseStencilMidpointFallbackCount"',
                    'AddQuantity(name="PhaseStencilMidpointFallbackCount"',
                    "getPhaseStencilMidpointFallbackCount",
                ),
            ]
        ),
        "calcgradphi_uses_stage13_macro": contains(
            dynamics_c,
            r"calcGradPhiRaw\s*\([^)]*\).*?IsotropicGrad\('gradPhi', 'STAGE13_PHASE_FOR_STENCIL'\)",
        ),
        "calcmu_laplace_uses_stage13_macro": contains(
            dynamics_c,
            r"calcMu\s*\([^)]*\).*?myLaplace\('lpPhi', 'STAGE13_PHASE_FOR_STENCIL'\)",
        ),
        "outflow_grad_mu_do_not_read_raw_phase_neighbors": (
            outflow_blocks_avoid_raw_phase_neighbors(dynamics_c)
        ),
        "diagnostic_fields_registered": all(
            token in dynamics_r
            for token in [
                'AddField("WallCSQValid"',
                'AddField("WallCSQMethodComplete"',
                'AddQuantity(name="WallCSQResidual"',
                'AddField("WallCSQAppliedResidual"',
                'AddField("WallCSQVertexRealFluidBits"',
                'AddField("WallCSQStrictWriteReady"',
                'AddField("PhaseStencilFallbackCount"',
                'AddSetting(name="WallCompactStencilWriteAllowedFlag"',
                'AddSetting(name="WallCompactStencilMaxBoundedDelta"',
                'AddSetting(name="WallCompactStencilAppliedResidualTol"',
            ]
        ),
        "flat_wall_runner_defaults_to_write": all(
            token in run_script
            for token in [
                'default="write"',
                "WallCompactStencilWriteAllowedFlag",
                "expected_target_wetting_path_id",
            ]
        ),
        "flat_wall_audit_requires_path30": all(
            token in audit_script
            for token in [
                "compact_write_target_path_not_wetting_path_30",
                "compact_write_legacy_wetting_path_present",
                "compact_write_strict_ready_fraction_below_0p95",
                "compact_write_applied_residual_above_1e-8",
                "compact_write_without_real_fluid_vertices",
                "target_wall_compact_write_path_fraction",
            ]
        ),
    }
    failures = [name for name, ok in checks.items() if not ok]
    return {
        "status": "PASS_COMPACT_WRITE_SOURCE_CLOSURE" if not failures else "FAIL",
        "root": str(root),
        "files": {
            "Boundary.c.Rt": str(boundary_path),
            "Dynamics.c.Rt": str(dynamics_c_path),
            "Dynamics.R": str(dynamics_r_path),
            "stage13_flat_wall_diagnostic_run.py": str(run_script_path),
            "stage13_flat_wall_diagnostic_audit.py": str(audit_script_path),
        },
        "checks": checks,
        "failures": failures,
        "claim_limit": (
            "source wiring audit only; contact angle validation still requires "
            "flat-wall, cylinder, and sphere runtime gates"
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="lbm2026 root containing tclb/ and scripts/",
    )
    parser.add_argument("--out", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = audit(args.root)
    text = json.dumps(summary, indent=2, sort_keys=True)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text)
    return 0 if summary["status"].startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
