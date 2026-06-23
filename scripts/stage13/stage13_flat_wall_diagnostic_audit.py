#!/usr/bin/env python3
"""Audit Stage13 flat-wall diagnostic VTI outputs.

The script checks field presence and summarizes wall diagnostic arrays. It does
not decide publication validation; its output is a gate diagnostic.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np


REQUIRED_FIELDS = [
    "PhaseField",
    "IsItBoundary",
    "WallGhostRaw",
    "WallGhostClamped",
    "WallGhostClampHit",
    "WettingPathId",
    "LocalRadAngle",
    "ForceIterResidual",
    "ForceIterCount",
    "MassCorrectionApplied",
    "PhaseStencilGhostUseCount",
    "PhaseStencilFallbackCount",
    "PhaseStencilMidpointFallbackCount",
    "WallCSQMode",
    "WallCSQNormalMode",
    "WallCSQValid",
    "WallCSQResidual",
    "WallCSQAppliedResidual",
    "WallCSQFallbackReason",
    "WallCSQBoundedDelta",
    "WallCSQWriteAllowedFlag",
    "WallCSQCandidateCount",
    "WallCSQFluidVertexCount",
    "WallCSQTriangleInside",
    "WallCSQPlaneId",
    "WallCSQBaryMin",
    "WallCSQBaryMax",
    "WallCSQMethodComplete",
    "WallCSQVertexMaskBits",
    "WallCSQVertexRealFluidBits",
    "WallCSQVertexPhaseCleanBits",
    "WallCSQVertexQMin",
    "WallCSQVertexQMax",
    "WallCSQRejectedSolidVertexCount",
    "WallCSQRejectedSentinelCount",
    "WallCSQStrictWriteReady",
]


def parse_run_log(case_dir: Path) -> dict[str, Any]:
    path = case_dir / "run.log"
    if not path.exists():
        return {"exists": False, "run_rc": None, "nan_detected": None, "tail": []}
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    run_rc = None
    for line in reversed(lines):
        if line.startswith("RUN_RC="):
            try:
                run_rc = int(line.split("=", 1)[1].strip())
            except ValueError:
                run_rc = None
            break
    nan_patterns = [
        "discovered NaN",
        "NaN value discovered",
        "Stopping due to Nan value",
        "Stopping due to NaN value",
    ]
    return {
        "exists": True,
        "run_rc": run_rc,
        "nan_detected": any(any(pattern in line for pattern in nan_patterns) for line in lines),
        "failcheck_stop": any("Stopping due to" in line for line in lines),
        "tail": lines[-30:],
    }


def step_of(path: Path) -> int:
    match = re.search(r"P00_(\d+)\.vti$", path.name)
    return int(match.group(1)) if match else -1


def load_vti(path: Path) -> tuple[tuple[int, int, int], dict[str, np.ndarray]]:
    try:
        import vtk
        from vtk.util.numpy_support import vtk_to_numpy
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "The vtk Python package is required to read VTI files. Run this "
            "script in the TCLB post-processing environment on the server."
        ) from exc

    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(str(path))
    reader.Update()
    image = reader.GetOutput()
    dims = tuple(int(v) - 1 for v in image.GetDimensions())
    data = image.GetCellData()
    arrays: dict[str, np.ndarray] = {}
    for idx in range(data.GetNumberOfArrays()):
        array = data.GetArray(idx)
        arrays[array.GetName() or f"array_{idx}"] = vtk_to_numpy(array).copy()
    return dims, arrays


def finite_stats(values: np.ndarray) -> dict[str, Any]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {
            "count": int(values.size),
            "finite": 0,
            "min": None,
            "max": None,
            "max_abs": None,
            "mean": None,
        }
    return {
        "count": int(values.size),
        "finite": int(finite.size),
        "min": float(np.min(finite)),
        "max": float(np.max(finite)),
        "max_abs": float(np.max(np.abs(finite))),
        "mean": float(np.mean(finite)),
    }


def mask_stats(mask: np.ndarray, values: np.ndarray) -> dict[str, Any] | None:
    if not np.any(mask):
        return None
    return finite_stats(values[mask])


def histogram(values: np.ndarray) -> dict[str, int]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {}
    hist_values, hist_counts = np.unique(finite, return_counts=True)
    return {str(float(value)): int(count) for value, count in zip(hist_values, hist_counts)}


def flat_patch_mask(metadata: dict[str, Any], dims: tuple[int, int, int]) -> np.ndarray | None:
    patch = metadata.get("target_wall_patch")
    if not isinstance(patch, dict):
        return None
    nx, ny, nz = dims
    mask3 = np.zeros((nz, ny, nx), dtype=bool)
    x0 = int(patch.get("x_start", 0))
    y0 = int(patch.get("y_start", 0))
    z0 = int(patch.get("z_start", 0))
    xc = int(patch.get("x_count", nx))
    yc = int(patch.get("y_count", 1))
    zc = int(patch.get("z_count", nz))
    x1 = max(0, min(nx, x0 + xc))
    y1 = max(0, min(ny, y0 + yc))
    z1 = max(0, min(nz, z0 + zc))
    x0 = max(0, min(nx, x0))
    y0 = max(0, min(ny, y0))
    z0 = max(0, min(nz, z0))
    if x0 >= x1 or y0 >= y1 or z0 >= z1:
        return None
    mask3[z0:z1, y0:y1, x0:x1] = True
    return mask3.reshape(-1)


def audit_case(case_dir: Path) -> dict[str, Any]:
    meta_path = case_dir / "case_metadata.json"
    metadata = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    run_log = parse_run_log(case_dir)
    vtis = sorted((case_dir / "output").glob("case_VTK_P00_*.vti"), key=step_of)
    if not vtis:
        return {
            "case": case_dir.name,
            "case_dir": str(case_dir),
            "ok": False,
            "failure": "no_vti_outputs",
            "metadata": metadata,
            "run_log": run_log,
        }
    dims, arrays = load_vti(vtis[-1])
    missing = [name for name in REQUIRED_FIELDS if name not in arrays]
    boundary = arrays.get("IsItBoundary")
    wall_mask = boundary > 0.5 if boundary is not None else np.zeros(0, dtype=bool)
    wall_count = int(np.count_nonzero(wall_mask))
    result: dict[str, Any] = {
        "case": case_dir.name,
        "case_dir": str(case_dir),
        "final_vti": str(vtis[-1]),
        "dims": dims,
        "n_vti": len(vtis),
        "ok": not missing,
        "missing_fields": missing,
        "metadata": metadata,
        "run_log": run_log,
        "wall_count": wall_count,
    }
    if missing:
        return result
    wall_path = arrays["WettingPathId"][wall_mask] if wall_count else np.array([])
    wall_angle = arrays["LocalRadAngle"][wall_mask] if wall_count else np.array([])
    wall_clamp = arrays["WallGhostClampHit"][wall_mask] if wall_count else np.array([])
    local_angle = arrays["LocalRadAngle"]
    target_wall_source = "metadata_patch"
    patch_mask = flat_patch_mask(metadata, dims)
    if patch_mask is not None:
        target_wall_mask = wall_mask & patch_mask
    else:
        target_wall_source = "angle_fallback"
        bc_theta = metadata.get("bc_theta_deg")
        if bc_theta is None:
            target_wall_mask = np.zeros_like(wall_mask, dtype=bool)
        else:
            target_angle = float(bc_theta) * math.pi / 180.0
            target_wall_mask = (
                wall_mask
                & np.isfinite(local_angle)
                & (np.abs(local_angle - target_angle) < 1.0e-6)
            )
    target_wall_count = int(np.count_nonzero(target_wall_mask))
    force_res = arrays["ForceIterResidual"]
    stencil_fallback = arrays["PhaseStencilFallbackCount"]
    stencil_midpoint_fallback = arrays["PhaseStencilMidpointFallbackCount"]
    phase = arrays["PhaseField"]
    wall_csq_valid = arrays["WallCSQValid"][wall_mask] if wall_count else np.array([])
    wall_csq_residual = arrays["WallCSQResidual"][wall_mask] if wall_count else np.array([])
    wall_csq_fallback = arrays["WallCSQFallbackReason"][wall_mask] if wall_count else np.array([])
    wall_csq_bounded_delta = arrays["WallCSQBoundedDelta"][wall_mask] if wall_count else np.array([])
    wall_csq_method_complete = arrays["WallCSQMethodComplete"][wall_mask] if wall_count else np.array([])
    wall_csq_candidate_count = arrays["WallCSQCandidateCount"][wall_mask] if wall_count else np.array([])
    wall_csq_fluid_vertex_count = arrays["WallCSQFluidVertexCount"][wall_mask] if wall_count else np.array([])
    wall_csq_triangle_inside = arrays["WallCSQTriangleInside"][wall_mask] if wall_count else np.array([])
    path_values, path_counts = (
        np.unique(wall_path[np.isfinite(wall_path)], return_counts=True)
        if wall_path.size
        else (np.array([]), np.array([]))
    )
    target_complete_fraction = (
        float(np.mean(arrays["WallCSQMethodComplete"][target_wall_mask] > 0.5))
        if target_wall_count
        else None
    )
    target_three_vertex_fraction = (
        float(np.mean(arrays["WallCSQFluidVertexCount"][target_wall_mask] >= 2.5))
        if target_wall_count
        else None
    )
    target_triangle_inside_fraction = (
        float(np.mean(arrays["WallCSQTriangleInside"][target_wall_mask] > 0.5))
        if target_wall_count
        else None
    )
    target_vertex_mask_fraction = (
        float(np.mean(arrays["WallCSQVertexMaskBits"][target_wall_mask] == 7.0))
        if target_wall_count
        else None
    )
    target_vertex_real_fluid_fraction = (
        float(np.mean(arrays["WallCSQVertexRealFluidBits"][target_wall_mask] == 7.0))
        if target_wall_count
        else None
    )
    target_vertex_phase_clean_fraction = (
        float(np.mean(arrays["WallCSQVertexPhaseCleanBits"][target_wall_mask] == 7.0))
        if target_wall_count
        else None
    )
    target_candidate_stats = mask_stats(target_wall_mask, arrays["WallCSQCandidateCount"])
    requested_write_flag = int(metadata.get("wall_compact_stencil_write_allowed_flag", 0) or 0)
    requested_compact_mode = metadata.get("compact_mode", "unknown")
    compact_write_requested = (
        requested_write_flag > 0
        or int(metadata.get("wall_compact_stencil_mode", 0) or 0) >= 2
        or requested_compact_mode == "write"
    )
    target_write_allowed_fraction = (
        float(np.mean(arrays["WallCSQWriteAllowedFlag"][target_wall_mask] > 0.5))
        if target_wall_count
        else None
    )
    target_compact_write_path_fraction = (
        float(np.mean(arrays["WettingPathId"][target_wall_mask] == 30.0))
        if target_wall_count
        else None
    )
    target_incomplete_write_path_fraction = (
        float(np.mean(arrays["WettingPathId"][target_wall_mask] == -30.0))
        if target_wall_count
        else None
    )
    target_legacy_path_fraction = (
        float(
            np.mean(
                np.isin(
                    arrays["WettingPathId"][target_wall_mask],
                    np.array([1.0, 2.0, 11.0, 12.0, 13.0, 14.0, 20.0]),
                )
            )
        )
        if target_wall_count
        else None
    )
    c1b_shadow_ready = (
        target_wall_count > 0
        and target_complete_fraction is not None
        and target_complete_fraction >= 0.95
        and target_three_vertex_fraction is not None
        and target_three_vertex_fraction >= 0.95
        and target_triangle_inside_fraction is not None
        and target_triangle_inside_fraction >= 0.95
        and target_vertex_mask_fraction is not None
        and target_vertex_mask_fraction >= 0.95
        and target_vertex_real_fluid_fraction is not None
        and target_vertex_real_fluid_fraction >= 0.95
        and target_vertex_phase_clean_fraction is not None
        and target_vertex_phase_clean_fraction >= 0.95
        and target_candidate_stats is not None
        and target_candidate_stats.get("min") is not None
        and float(target_candidate_stats["min"]) > 0.0
    )
    compact_stencil_gate = (
        "PASS_C2_COMPACT_WRITE_PATH"
        if compact_write_requested
        and c1b_shadow_ready
        and target_compact_write_path_fraction is not None
        and target_compact_write_path_fraction >= 0.95
        and target_write_allowed_fraction is not None
        and target_write_allowed_fraction >= 0.95
        else (
            "PASS_C1B_TRUE_COMPACT_STENCIL_SHADOW"
            if (not compact_write_requested) and c1b_shadow_ready
            else "PASS_C1A_SCAFFOLD_ONLY"
        )
    )
    c1b_blockers = []
    if not c1b_shadow_ready:
        c1b_blockers = [
            "target-wall WallCSQMethodComplete fraction must be >=0.95 for C1b",
            "accepted compact-stencil candidates must use three fluid vertices",
            "accepted compact-stencil candidates must be inside the selected triangle",
            "accepted compact-stencil vertices must be geometrically fluid (mask bits=7)",
            "accepted compact-stencil vertices must be real non-boundary fluid nodes",
            "accepted compact-stencil vertices must have clean phase values (phase bits=7)",
            "first-ring normal-probe shadow output must not be used for write mode",
        ]

    result.update(
        {
            "phase_stats": finite_stats(phase),
            "force_iter_residual_stats": finite_stats(force_res),
            "phase_stencil_fallback_stats": finite_stats(stencil_fallback),
            "phase_stencil_midpoint_fallback_stats": finite_stats(
                stencil_midpoint_fallback
            ),
            "wall_path_histogram": {
                str(float(value)): int(count) for value, count in zip(path_values, path_counts)
            },
            "wall_local_angle_deg_stats": finite_stats(wall_angle * 180.0 / math.pi),
            "wall_ghost_clamp_fraction": (
                float(np.mean(wall_clamp > 0.5)) if wall_clamp.size else None
            ),
            "wall_csq_valid_fraction": (
                float(np.mean(wall_csq_valid > 0.5)) if wall_csq_valid.size else None
            ),
            "wall_csq_residual_stats": finite_stats(wall_csq_residual) if wall_count else None,
            "wall_csq_applied_residual_stats": (
                finite_stats(arrays["WallCSQAppliedResidual"][wall_mask])
                if wall_count
                else None
            ),
            "wall_csq_fallback_histogram": histogram(wall_csq_fallback) if wall_count else {},
            "wall_csq_bounded_delta_stats": finite_stats(wall_csq_bounded_delta) if wall_count else None,
            "wall_csq_method_complete_fraction": (
                float(np.mean(wall_csq_method_complete > 0.5))
                if wall_csq_method_complete.size
                else None
            ),
            "wall_csq_candidate_count_stats": (
                finite_stats(wall_csq_candidate_count) if wall_count else None
            ),
            "wall_csq_fluid_vertex_count_stats": (
                finite_stats(wall_csq_fluid_vertex_count) if wall_count else None
            ),
            "wall_csq_triangle_inside_fraction": (
                float(np.mean(wall_csq_triangle_inside > 0.5))
                if wall_csq_triangle_inside.size
                else None
            ),
            "target_wall_count": target_wall_count,
            "target_wall_source": target_wall_source,
            "target_wall_path_histogram": histogram(arrays["WettingPathId"][target_wall_mask]),
            "target_wall_csq_valid_fraction": (
                float(np.mean(arrays["WallCSQValid"][target_wall_mask] > 0.5))
                if target_wall_count
                else None
            ),
            "target_wall_csq_residual_stats": (
                mask_stats(target_wall_mask, arrays["WallCSQResidual"])
            ),
            "target_wall_csq_applied_residual_stats": (
                mask_stats(target_wall_mask, arrays["WallCSQAppliedResidual"])
            ),
            "target_wall_csq_fallback_histogram": histogram(
                arrays["WallCSQFallbackReason"][target_wall_mask]
            ),
            "target_wall_csq_bounded_delta_stats": (
                mask_stats(target_wall_mask, arrays["WallCSQBoundedDelta"])
            ),
            "target_wall_csq_method_complete_fraction": (
                target_complete_fraction
            ),
            "compact_write_requested": compact_write_requested,
            "target_wall_csq_write_allowed_fraction": target_write_allowed_fraction,
            "target_wall_compact_write_path_fraction": (
                target_compact_write_path_fraction
            ),
            "target_wall_incomplete_write_path_fraction": (
                target_incomplete_write_path_fraction
            ),
            "target_wall_legacy_path_fraction": target_legacy_path_fraction,
            "target_wall_csq_candidate_count_stats": (
                target_candidate_stats
            ),
            "target_wall_csq_fluid_vertex_count_stats": (
                mask_stats(target_wall_mask, arrays["WallCSQFluidVertexCount"])
            ),
            "target_wall_csq_triangle_inside_fraction": (
                target_triangle_inside_fraction
            ),
            "target_wall_csq_three_vertex_fraction": target_three_vertex_fraction,
            "target_wall_csq_vertex_mask_fraction": target_vertex_mask_fraction,
            "target_wall_csq_vertex_real_fluid_fraction": (
                target_vertex_real_fluid_fraction
            ),
            "target_wall_csq_vertex_phase_clean_fraction": target_vertex_phase_clean_fraction,
            "target_wall_csq_strict_write_ready_fraction": (
                float(np.mean(arrays["WallCSQStrictWriteReady"][target_wall_mask] > 0.5))
                if target_wall_count
                else None
            ),
            "target_wall_csq_rejected_solid_stats": (
                mask_stats(target_wall_mask, arrays["WallCSQRejectedSolidVertexCount"])
            ),
            "target_wall_csq_rejected_sentinel_stats": (
                mask_stats(target_wall_mask, arrays["WallCSQRejectedSentinelCount"])
            ),
            "target_wall_csq_vertex_qmin_stats": (
                mask_stats(target_wall_mask, arrays["WallCSQVertexQMin"])
            ),
            "target_wall_csq_vertex_qmax_stats": (
                mask_stats(target_wall_mask, arrays["WallCSQVertexQMax"])
            ),
            "target_wall_ghost_clamp_fraction": (
                float(np.mean(arrays["WallGhostClampHit"][target_wall_mask] > 0.5))
                if target_wall_count
                else None
            ),
            "target_wall_local_angle_deg_stats": (
                mask_stats(target_wall_mask, local_angle * 180.0 / math.pi)
            ),
            "target_wall_nonanalytic_count": int(
                np.count_nonzero(
                    target_wall_mask
                    & np.isfinite(arrays["WettingPathId"])
                    & (arrays["WettingPathId"] != 1.0)
                    & (arrays["WettingPathId"] != 2.0)
                )
            ),
            "nonfinite_phase_count": int(np.count_nonzero(~np.isfinite(phase))),
            "nonfinite_force_residual_count": int(np.count_nonzero(~np.isfinite(force_res))),
            "claim_limit": "diagnostic evidence only; not validation_passed",
            "compact_stencil_gate": compact_stencil_gate,
            "c1b_blockers": c1b_blockers,
        }
    )
    failures = []
    if missing:
        failures.append("missing_fields")
    if run_log.get("nan_detected"):
        failures.append("run_log_nan_detected")
    if run_log.get("failcheck_stop"):
        failures.append("run_log_failcheck_stop")
    if run_log.get("run_rc") not in (0, None):
        failures.append(f"run_rc_{run_log.get('run_rc')}")
    if result["nonfinite_phase_count"] > 0:
        failures.append("nonfinite_phase_in_final_vti")
    if result["nonfinite_force_residual_count"] > 0:
        failures.append("nonfinite_force_residual_in_final_vti")
    if np.count_nonzero(~np.isfinite(stencil_fallback)) > 0:
        failures.append("nonfinite_phase_stencil_fallback_count")
    if np.count_nonzero(~np.isfinite(stencil_midpoint_fallback)) > 0:
        failures.append("nonfinite_phase_stencil_midpoint_fallback_count")
    if target_wall_count and result["target_wall_nonanalytic_count"] > 0:
        if not compact_write_requested:
            failures.append("target_wall_nonanalytic_wetting_path")
    if target_wall_count and result["target_wall_csq_valid_fraction"] is not None:
        if result["target_wall_csq_valid_fraction"] < 0.95:
            failures.append("target_wall_csq_valid_fraction_below_0p95")
    if compact_write_requested:
        if target_wall_count == 0:
            failures.append("compact_write_no_target_wall")
        if target_write_allowed_fraction is None or target_write_allowed_fraction < 0.95:
            failures.append("compact_write_flag_not_active_on_target_wall")
        if (
            target_compact_write_path_fraction is None
            or target_compact_write_path_fraction < 0.95
        ):
            failures.append("compact_write_target_path_not_wetting_path_30")
        if (
            target_incomplete_write_path_fraction is not None
            and target_incomplete_write_path_fraction > 0.0
        ):
            failures.append("compact_write_incomplete_path_minus30_present")
        if target_legacy_path_fraction is not None and target_legacy_path_fraction > 0.0:
            failures.append("compact_write_legacy_wetting_path_present")
        if not c1b_shadow_ready:
            failures.append("compact_write_without_true_three_vertex_stencil")
        strict_ready_fraction = result["target_wall_csq_strict_write_ready_fraction"]
        if strict_ready_fraction is None or strict_ready_fraction < 0.95:
            failures.append("compact_write_strict_ready_fraction_below_0p95")
        bounded_delta_stats = result["target_wall_csq_bounded_delta_stats"]
        if bounded_delta_stats and bounded_delta_stats.get("max") is not None:
            if float(bounded_delta_stats["max"]) > 1.0e-8:
                failures.append("compact_write_bounded_delta_above_1e-8")
        applied_res_stats = result["target_wall_csq_applied_residual_stats"]
        if applied_res_stats and applied_res_stats.get("max_abs") is not None:
            if float(applied_res_stats["max_abs"]) > 1.0e-8:
                failures.append("compact_write_applied_residual_above_1e-8")
        if (
            target_vertex_real_fluid_fraction is None
            or target_vertex_real_fluid_fraction < 0.95
        ):
            failures.append("compact_write_without_real_fluid_vertices")
    result["failures"] = failures
    result["ok"] = not failures
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Stage13 flat-wall diagnostic root")
    parser.add_argument("--out", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    case_dirs = sorted(path for path in args.root.iterdir() if (path / "case_metadata.json").exists())
    report = {
        "stage": "stage13_flat_wall_diagnostic_audit",
        "root": str(args.root),
        "claim_limit": "exploratory_not_validation only",
        "cases": [audit_case(path) for path in case_dirs],
    }
    out_path = args.out or (args.root / "stage13_flat_wall_diagnostic_audit.json")
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if all(case.get("ok") for case in report["cases"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
