#!/usr/bin/env python3
"""Stage14-B17 mask and argmax onset diagnostics.

This script is diagnostic-only. It reads TCLB VTI frames from a short
wall_60to30_10 onset run and answers where the first large values occur:
interface, near-wall, low-density gas, liquid bulk, or their overlap. It does
not validate a contact angle and does not modify any solver state.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np


SCALAR_FIELDS = [
    "PhaseField",
    "Rho",
    "P",
    "BOUNDARY",
    "IsItBoundary",
    "WallGhost",
    "ReplayPhaseConsumed",
    "ReplayPhaseFromH",
    "ReplayPhaseOutOfBoundsFlag",
    "ReplayLapPhi",
    "ReplayMu",
    "ReplayRho",
    "ReplayTau",
    "ReplayPressureMoment",
    "ReplayPressureInput",
    "ReplayPressureForceScale",
    "ReplayPressurePhysicalInput",
    "ReplayTauUsed",
    "ReplayRhoForForce",
    "ReplayForceRhoRaw",
    "ReplayForceRhoEffective",
    "ReplayForceInjectionMode",
    "ReplayPressureClosureMode",
    "ReplayForceDensityClosureMode",
    "ReplayForceFixedPointMode",
    "ReplayHPreSum",
    "ReplayHPostSum",
    "ReplayHeqSum",
    "ReplayHPreMaxAbs",
    "ReplayHPostMaxAbs",
    "ReplayHeqMaxAbs",
    "ReplayFphiSum",
    "ReplayFphiMaxAbs",
    "ReplayTmp1",
    "ReplayTmp1BoundedShadow",
    "ForceIterCount",
    "ForceIterResidual",
]

VECTOR_FIELDS = [
    "U",
    "GradPhi",
    "ReplayGradPhi",
    "ReplayFsurf",
    "ReplayFpressure",
    "ReplayFbody",
    "ReplayFmu",
    "ReplayFtotal",
    "ReplayForceOverRho",
    "ReplayFmuRaw",
    "ReplayFmuDelta",
    "ReplayFmuIter1",
    "ReplayFtotalIter1",
    "ReplayUPreForce",
    "ReplayUPostForce",
    "ReplayUPostIter1",
    "ReplayPhaseAdvVelocity",
    "ReplayM0",
    "ReplayVelocityHalfForce",
    "ReplayMF",
    "ReplayMomentumAfterG",
    "ReplayMomentumDeltaG",
    "ReplayFpressureNoThird",
    "ReplayFpressurePhysical",
]

STRESS_GROUPS = {
    "StressInputNorm": [
        "ReplayStressInputXX",
        "ReplayStressInputXY",
        "ReplayStressInputXZ",
        "ReplayStressInputYY",
        "ReplayStressInputYZ",
        "ReplayStressInputZZ",
    ],
    "StressIter1Norm": [
        "ReplayStressIter1XX",
        "ReplayStressIter1XY",
        "ReplayStressIter1XZ",
        "ReplayStressIter1YY",
        "ReplayStressIter1YZ",
        "ReplayStressIter1ZZ",
    ],
    "StressPreForceNorm": [
        "ReplayStressPreForceShadowXX",
        "ReplayStressPreForceShadowXY",
        "ReplayStressPreForceShadowXZ",
        "ReplayStressPreForceShadowYY",
        "ReplayStressPreForceShadowYZ",
        "ReplayStressPreForceShadowZZ",
    ],
    "StressPostForceNorm": [
        "ReplayStressPostForceShadowXX",
        "ReplayStressPostForceShadowXY",
        "ReplayStressPostForceShadowXZ",
        "ReplayStressPostForceShadowYY",
        "ReplayStressPostForceShadowYZ",
        "ReplayStressPostForceShadowZZ",
    ],
    "StressLegacyNorm": [
        "ReplayStressXX",
        "ReplayStressXY",
        "ReplayStressXZ",
        "ReplayStressYY",
        "ReplayStressYZ",
        "ReplayStressZZ",
    ],
}

DERIVED_VECTOR_MAG_FIELDS = {
    "GradPhiNorm": "ReplayGradPhi",
    "FsurfNorm": "ReplayFsurf",
    "FpressureNorm": "ReplayFpressure",
    "FpressureNoThirdNorm": "ReplayFpressureNoThird",
    "FpressurePhysicalNorm": "ReplayFpressurePhysical",
    "FmuNorm": "ReplayFmu",
    "FmuRawNorm": "ReplayFmuRaw",
    "FmuDeltaNorm": "ReplayFmuDelta",
    "FmuIter1Norm": "ReplayFmuIter1",
    "FtotalNorm": "ReplayFtotal",
    "FtotalIter1Norm": "ReplayFtotalIter1",
    "ForceOverRhoNorm": "ReplayForceOverRho",
    "UPreForceNorm": "ReplayUPreForce",
    "UPostForceNorm": "ReplayUPostForce",
    "UPostIter1Norm": "ReplayUPostIter1",
    "PhaseAdvVelocityNorm": "ReplayPhaseAdvVelocity",
    "VelocityNorm": "U",
    "MomentumAfterGNorm": "ReplayMomentumAfterG",
    "MomentumDeltaGNorm": "ReplayMomentumDeltaG",
}

TARGET_FIELDS = [
    "PhaseField",
    "ReplayPhaseFromH",
    "ReplayPhaseOutOfBoundsFlag",
    "ReplayHPostMaxAbs",
    "ReplayHeqMaxAbs",
    "ReplayFphiMaxAbs",
    "ReplayTmp1",
    "ReplayPressureInput",
    "FpressureNorm",
    "FpressurePhysicalNorm",
    "FmuRawNorm",
    "FmuDeltaNorm",
    "FtotalNorm",
    "ForceOverRhoNorm",
    "StressInputNorm",
    "StressIter1Norm",
    "StressPreForceNorm",
    "StressPostForceNorm",
    "StressPostMinusPreNorm",
    "StressPostOverPreRatio",
    "UPostForceNorm",
    "PhaseAdvVelocityNorm",
]

COLOCATE_FIELDS = [
    "PhaseField",
    "ReplayPhaseFromH",
    "ReplayPhaseConsumed",
    "Rho",
    "ReplayRho",
    "ReplayRhoForForce",
    "ReplayForceRhoRaw",
    "ReplayForceRhoEffective",
    "ReplayTau",
    "ReplayTauUsed",
    "ReplayMu",
    "GradPhiNorm",
    "P",
    "ReplayPressureInput",
    "ReplayPressurePhysicalInput",
    "FpressureNorm",
    "FpressurePhysicalNorm",
    "FmuRawNorm",
    "FmuDeltaNorm",
    "FtotalNorm",
    "ForceOverRhoNorm",
    "StressInputNorm",
    "StressIter1Norm",
    "StressPreForceNorm",
    "StressPostForceNorm",
    "StressPostMinusPreNorm",
    "StressPostOverPreRatio",
    "UPreForceNorm",
    "UPostForceNorm",
    "PhaseAdvVelocityNorm",
    "ReplayHPreMaxAbs",
    "ReplayHPostMaxAbs",
    "ReplayHeqMaxAbs",
    "ReplayTmp1",
    "ReplayFphiMaxAbs",
    "ForceIterCount",
    "ForceIterResidual",
]

THRESHOLDS = {
    "force_over_rho_large": ("ForceOverRhoNorm", 1.0e3),
    "fmu_raw_large": ("FmuRawNorm", 1.0e3),
    "stress_input_large": ("StressInputNorm", 1.0e3),
    "stress_post_large": ("StressPostForceNorm", 1.0e3),
    "pressure_input_large": ("ReplayPressureInput", 1.0e3),
    "pressure_force_large": ("FpressureNorm", 1.0e3),
    "phase_from_h_out_of_bounds": ("ReplayPhaseFromH", 1.0 + 1.0e-3),
    "phase_output_out_of_bounds": ("PhaseField", 1.0 + 1.0e-3),
    "tmp1_large": ("ReplayTmp1", 1.0),
    "fphi_large": ("ReplayFphiMaxAbs", 1.0),
    "hpost_large": ("ReplayHPostMaxAbs", 1.0),
}


def step_of(path: Path) -> int:
    match = re.search(r"P00_(\d+)\.vti$", path.name)
    return int(match.group(1)) if match else -1


def load_vti(path: Path) -> tuple[tuple[int, int, int], dict[str, np.ndarray]]:
    import vtk  # type: ignore
    from vtk.util.numpy_support import vtk_to_numpy  # type: ignore

    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(str(path))
    reader.Update()
    image = reader.GetOutput()
    dims = tuple(int(v) - 1 for v in image.GetDimensions())
    cell_data = image.GetCellData()
    arrays: dict[str, np.ndarray] = {}
    for idx in range(cell_data.GetNumberOfArrays()):
        arr = cell_data.GetArray(idx)
        if arr is not None:
            arrays[arr.GetName() or f"array_{idx}"] = vtk_to_numpy(arr).copy()
    return dims, arrays


def crop_to_physical(
    arr: np.ndarray, local_dims: tuple[int, int, int], physical_grid: list[int] | None
) -> np.ndarray:
    if not physical_grid:
        return np.asarray(arr)
    px, py, pz = [int(v) for v in physical_grid]
    nx, ny, nz = local_dims
    values = np.asarray(arr)
    if px > nx or py > ny or pz > nz:
        return values
    if values.shape[0] != nx * ny * nz:
        return values
    if values.ndim == 1:
        return values.reshape((nx, ny, nz))[:px, :py, :pz].reshape(-1)
    return values.reshape((nx, ny, nz, values.shape[1]))[:px, :py, :pz, :].reshape(
        -1, values.shape[1]
    )


def index_to_ijk(index: int, dims: tuple[int, int, int]) -> list[int]:
    nx, ny, _nz = dims
    i = int(index % nx)
    j = int((index // nx) % ny)
    k = int(index // (nx * ny))
    return [i, j, k]


def scalarize(arr: np.ndarray | None) -> np.ndarray | None:
    if arr is None:
        return None
    values = np.asarray(arr, dtype=float)
    if values.ndim == 2:
        return np.linalg.norm(values, axis=1)
    return values.reshape(-1)


def vector_norm(arr: np.ndarray | None) -> np.ndarray | None:
    return scalarize(arr)


def stress_norm(arrays: dict[str, np.ndarray], names: list[str]) -> np.ndarray | None:
    comps = [scalarize(arrays.get(name)) for name in names]
    if any(comp is None for comp in comps):
        return None
    stacked = np.column_stack([comp for comp in comps if comp is not None])
    weights = np.array([1.0, 2.0, 2.0, 1.0, 2.0, 1.0], dtype=float)
    return np.sqrt(np.sum(weights[None, :] * stacked * stacked, axis=1))


def add_derived_fields(arrays: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    out = dict(arrays)
    for name, source in DERIVED_VECTOR_MAG_FIELDS.items():
        values = vector_norm(arrays.get(source))
        if values is not None:
            out[name] = values
    for name, sources in STRESS_GROUPS.items():
        values = stress_norm(arrays, sources)
        if values is not None:
            out[name] = values
    pre = scalarize(out.get("StressPreForceNorm"))
    post = scalarize(out.get("StressPostForceNorm"))
    if pre is not None and post is not None:
        out["StressPostMinusPreNorm"] = np.abs(post - pre)
        out["StressPostOverPreRatio"] = post / (pre + 1.0e-300)
    return out


def read_metadata(case_dir: Path) -> dict[str, Any]:
    path = case_dir / "case_metadata.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def candidate_case_dirs(root: Path) -> list[Path]:
    if (root / "output").is_dir():
        return [root]
    case_dirs = [
        path for path in sorted(root.iterdir()) if path.is_dir() and (path / "output").is_dir()
    ]
    return case_dirs


def boundary_mask(arrays: dict[str, np.ndarray], n: int) -> np.ndarray:
    for name in ["BOUNDARY", "IsItBoundary"]:
        values = scalarize(arrays.get(name))
        if values is not None and values.size == n:
            return np.asarray(values, dtype=float) > 0.5
    return np.zeros(n, dtype=bool)


def adjacent_to_mask(mask: np.ndarray, dims: tuple[int, int, int]) -> np.ndarray:
    nx, ny, nz = dims
    grid = np.asarray(mask, dtype=bool).reshape((nx, ny, nz))
    adj = np.zeros_like(grid, dtype=bool)
    for dx, dy, dz in [
        (1, 0, 0),
        (-1, 0, 0),
        (0, 1, 0),
        (0, -1, 0),
        (0, 0, 1),
        (0, 0, -1),
    ]:
        src = [
            slice(max(0, -dx), nx - max(0, dx)),
            slice(max(0, -dy), ny - max(0, dy)),
            slice(max(0, -dz), nz - max(0, dz)),
        ]
        dst = [
            slice(max(0, dx), nx - max(0, -dx)),
            slice(max(0, dy), ny - max(0, -dy)),
            slice(max(0, dz), nz - max(0, -dz)),
        ]
        adj[tuple(dst)] |= grid[tuple(src)]
    return adj.reshape(-1)


def low_rho_mask(rho: np.ndarray | None, fluid: np.ndarray, density_l: float | None) -> np.ndarray:
    if rho is None:
        return np.zeros_like(fluid, dtype=bool)
    values = np.asarray(rho, dtype=float)
    good = fluid & np.isfinite(values)
    if not np.count_nonzero(good):
        return np.zeros_like(fluid, dtype=bool)
    threshold = float(np.nanpercentile(values[good], 0.1))
    if density_l is not None and density_l > 0:
        threshold = max(threshold, 5.0 * float(density_l))
    return good & (values <= threshold)


def make_masks(
    arrays: dict[str, np.ndarray], dims: tuple[int, int, int], metadata: dict[str, Any]
) -> dict[str, np.ndarray]:
    phase = scalarize(arrays.get("PhaseField"))
    n = dims[0] * dims[1] * dims[2]
    if phase is None:
        phase = np.full(n, np.nan)
    boundary = boundary_mask(arrays, n)
    fluid = ~boundary
    near_wall = fluid & adjacent_to_mask(boundary, dims)
    interface_strict = fluid & np.isfinite(phase) & (phase > 0.05) & (phase < 0.95)
    interface_wide = fluid & np.isfinite(phase) & (phase > 0.01) & (phase < 0.99)
    liquid_bulk = fluid & np.isfinite(phase) & (phase >= 0.95)
    gas_bulk = fluid & np.isfinite(phase) & (phase <= 0.05)
    density_l = metadata.get("density_l")
    try:
        density_l_value = float(density_l) if density_l is not None else None
    except (TypeError, ValueError):
        density_l_value = None
    rho = scalarize(arrays.get("Rho"))
    return {
        "all_cells": np.ones(n, dtype=bool),
        "fluid_all": fluid,
        "near_wall": near_wall,
        "interface_strict": interface_strict,
        "interface_wide": interface_wide,
        "near_interface_wall": near_wall & interface_wide,
        "liquid_bulk": liquid_bulk,
        "gas_bulk": gas_bulk,
        "low_rho": low_rho_mask(rho, fluid, density_l_value),
        "solid": boundary,
    }


def finite_stats(values: np.ndarray | None, mask: np.ndarray) -> dict[str, Any]:
    if values is None:
        return {
            "present": False,
            "count": int(np.count_nonzero(mask)),
            "finite_count": 0,
            "nonfinite_count": None,
            "min": None,
            "max": None,
            "mean": None,
            "p99_abs": None,
            "p999_abs": None,
            "max_abs": None,
        }
    vals = np.asarray(values, dtype=float).reshape(-1)[mask]
    finite = np.isfinite(vals)
    finite_vals = vals[finite]
    out: dict[str, Any] = {
        "present": True,
        "count": int(vals.size),
        "finite_count": int(np.count_nonzero(finite)),
        "nonfinite_count": int(vals.size - np.count_nonzero(finite)),
        "min": None,
        "max": None,
        "mean": None,
        "p99_abs": None,
        "p999_abs": None,
        "max_abs": None,
    }
    if finite_vals.size:
        abs_vals = np.abs(finite_vals)
        out.update(
            {
                "min": float(np.min(finite_vals)),
                "max": float(np.max(finite_vals)),
                "mean": float(np.mean(finite_vals)),
                "p99_abs": float(np.percentile(abs_vals, 99.0)),
                "p999_abs": float(np.percentile(abs_vals, 99.9)),
                "max_abs": float(np.max(abs_vals)),
            }
        )
    return out


def clean_value(value: Any) -> Any:
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return value
    if math.isfinite(v):
        return v
    return str(v)


def value_at(arrays: dict[str, np.ndarray], field: str, index: int) -> Any:
    arr = arrays.get(field)
    if arr is None:
        return None
    values = np.asarray(arr)
    if values.ndim == 1:
        return clean_value(values[index])
    return [clean_value(v) for v in values[index].ravel()]


def argmax_record(
    arrays: dict[str, np.ndarray],
    field: str,
    mask: np.ndarray,
    dims: tuple[int, int, int],
    masks: dict[str, np.ndarray],
) -> dict[str, Any] | None:
    values = scalarize(arrays.get(field))
    if values is None or not np.count_nonzero(mask):
        return None
    vals = np.asarray(values, dtype=float).reshape(-1)
    candidate = mask & np.isfinite(vals)
    if not np.count_nonzero(candidate):
        bad = np.flatnonzero(mask & ~np.isfinite(vals))
        if bad.size == 0:
            return None
        index = int(bad[0])
        max_abs = None
    else:
        candidate_indices = np.flatnonzero(candidate)
        local_index = int(np.argmax(np.abs(vals[candidate])))
        index = int(candidate_indices[local_index])
        max_abs = float(abs(vals[index]))
    record: dict[str, Any] = {
        "field": field,
        "flat_index": index,
        "ijk": index_to_ijk(index, dims),
        "max_abs": max_abs,
        "value": value_at(arrays, field, index),
        "mask_membership": {name: bool(mask_values[index]) for name, mask_values in masks.items()},
        "colocated": {},
    }
    for name in COLOCATE_FIELDS:
        if name in arrays:
            record["colocated"][name] = value_at(arrays, name, index)
    return record


def summarize_frame(
    case_dir: Path,
    vti_path: Path,
    metadata: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    raw_dims, raw_arrays = load_vti(vti_path)
    physical_grid = metadata.get("physical_grid")
    arrays = {
        name: crop_to_physical(values, raw_dims, physical_grid)
        for name, values in raw_arrays.items()
    }
    dims = tuple(int(v) for v in physical_grid) if physical_grid else raw_dims
    arrays = add_derived_fields(arrays)
    masks = make_masks(arrays, dims, metadata)
    step = step_of(vti_path)
    stats_rows: list[dict[str, Any]] = []
    argmax_rows: list[dict[str, Any]] = []
    for field in TARGET_FIELDS:
        values = scalarize(arrays.get(field))
        for mask_name, mask in masks.items():
            stats = finite_stats(values, mask)
            row = {
                "case": case_dir.name,
                "step": step,
                "field": field,
                "mask": mask_name,
                **stats,
            }
            stats_rows.append(row)
            record = argmax_record(arrays, field, mask, dims, masks)
            if record is not None:
                argmax_rows.append(
                    {
                        "case": case_dir.name,
                        "step": step,
                        "mask": mask_name,
                        **record,
                    }
                )
    field_presence = {
        name: name in arrays
        for name in sorted(set(SCALAR_FIELDS + VECTOR_FIELDS + TARGET_FIELDS + COLOCATE_FIELDS))
    }
    frame_summary = {
        "case": case_dir.name,
        "step": step,
        "path": str(vti_path),
        "dims": list(dims),
        "raw_dims": list(raw_dims),
        "mask_counts": {name: int(np.count_nonzero(mask)) for name, mask in masks.items()},
        "field_presence": field_presence,
    }
    return stats_rows, argmax_rows, frame_summary


def first_onsets(stats_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    onsets: list[dict[str, Any]] = []
    by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    sorted_rows = sorted(stats_rows, key=lambda row: (int(row["step"]), row["case"], row["mask"]))
    for row in sorted_rows:
        if row.get("present") and row.get("nonfinite_count") not in (None, 0):
            key = (f"nonfinite_{row['field']}", row["field"], row["mask"])
            if key not in by_key:
                by_key[key] = {
                    "trigger": key[0],
                    "field": row["field"],
                    "mask": row["mask"],
                    "case": row["case"],
                    "step": row["step"],
                    "value": row.get("nonfinite_count"),
                }
        for trigger, (field, threshold) in THRESHOLDS.items():
            if row["field"] != field or row.get("max_abs") is None:
                continue
            value = float(row["max_abs"])
            if value > threshold:
                key = (f"threshold_{trigger}", field, row["mask"])
                if key not in by_key:
                    by_key[key] = {
                        "trigger": key[0],
                        "field": field,
                        "mask": row["mask"],
                        "case": row["case"],
                        "step": row["step"],
                        "value": value,
                        "threshold": threshold,
                    }
    onsets = list(by_key.values())
    return sorted(onsets, key=lambda item: (int(item["step"]), item["trigger"], item["mask"]))


def key_summary(
    root: Path,
    stats_rows: list[dict[str, Any]],
    argmax_rows: list[dict[str, Any]],
    frame_summaries: list[dict[str, Any]],
    onsets: list[dict[str, Any]],
) -> dict[str, Any]:
    def first(trigger_prefix: str) -> dict[str, Any] | None:
        matches = [item for item in onsets if str(item["trigger"]).startswith(trigger_prefix)]
        if not matches:
            return None
        priority_masks = ["near_interface_wall", "interface_wide", "low_rho", "near_wall", "fluid_all"]
        matches = sorted(
            matches,
            key=lambda item: (
                int(item["step"]),
                priority_masks.index(item["mask"]) if item["mask"] in priority_masks else 99,
            ),
        )
        return matches[0]

    force = first("threshold_force_over_rho_large")
    fmu = first("threshold_fmu_raw_large")
    stress_post = first("threshold_stress_post_large")
    stress_input = first("threshold_stress_input_large")
    pressure = first("threshold_pressure_input_large")
    phase = first("threshold_phase_from_h_out_of_bounds")
    hpost = first("threshold_hpost_large")

    branch = "undetermined"
    reason = "No configured onset threshold was crossed."
    if force and (phase is None or int(force["step"]) <= int(phase["step"])):
        if fmu and int(fmu["step"]) <= int(force["step"]):
            branch = "fmu_force_over_rho_feedback"
            reason = "F_mu grows no later than F/rho and before or with phase loss."
        elif stress_post and int(stress_post["step"]) <= int(force["step"]):
            branch = "stress_timelevel_or_fixed_point_feedback"
            reason = "Post-force stress grows no later than F/rho and before or with phase loss."
        else:
            branch = "force_over_rho_density_closure"
            reason = "F/rho crosses its threshold before or with phase loss without an earlier F_mu marker."
    elif phase and (force is None or int(phase["step"]) < int(force["step"])):
        branch = "phase_update_or_h_advection_first"
        reason = "PhaseFromH leaves bounds before configured force-over-rho onset."
    if pressure and force and int(pressure["step"]) < int(force["step"]):
        branch = "pressure_closure_first"
        reason = "Pressure input crosses threshold before force-over-rho onset."
    if hpost and phase and int(hpost["step"]) < int(phase["step"]):
        branch = "h_population_update_first"
        reason = "HPost magnitude crosses threshold before PhaseFromH leaves bounds."

    return {
        "root": str(root),
        "status": "B17_DIAGNOSTIC_COMPLETE",
        "claim_limit": "diagnostic-only; not contact-angle validation and not a solver fix",
        "frame_count": len(frame_summaries),
        "stat_row_count": len(stats_rows),
        "argmax_record_count": len(argmax_rows),
        "first_force_over_rho_onset": force,
        "first_fmu_raw_onset": fmu,
        "first_stress_post_onset": stress_post,
        "first_stress_input_onset": stress_input,
        "first_pressure_input_onset": pressure,
        "first_phase_from_h_onset": phase,
        "first_hpost_onset": hpost,
        "primary_branch": branch,
        "primary_branch_reason": reason,
        "notes": [
            "Use mask-specific argmax records before changing solver physics.",
            "If high values localize in low_rho/gas_bulk, force-density closure is implicated.",
            "If stress_post exceeds stress_pre at the same argmax before phase loss, stress time-level is implicated.",
            "If phase/h fields lead force diagnostics, return to h update and phase-advection timeline.",
        ],
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Case directory or root containing case directories.")
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--case-glob", default="*")
    args = parser.parse_args()

    root = args.root.resolve()
    out_dir = (args.out_dir or root).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    case_dirs = [path for path in candidate_case_dirs(root) if path.match(args.case_glob)]
    if not case_dirs:
        raise SystemExit(f"No case directories with output/ found under {root}")

    all_stats: list[dict[str, Any]] = []
    all_argmax: list[dict[str, Any]] = []
    frame_summaries: list[dict[str, Any]] = []
    pvti_only: list[str] = []
    for case_dir in case_dirs:
        metadata = read_metadata(case_dir)
        output = case_dir / "output"
        vtis = sorted(output.glob("case_VTK_P00_*.vti"), key=step_of)
        if not vtis and list(output.glob("case_VTK_P00_*.pvti")):
            pvti_only.append(str(case_dir))
            continue
        for vti_path in vtis:
            stats_rows, argmax_rows, frame_summary = summarize_frame(case_dir, vti_path, metadata)
            all_stats.extend(stats_rows)
            all_argmax.extend(argmax_rows)
            frame_summaries.append(frame_summary)

    if pvti_only and not frame_summaries:
        raise SystemExit(
            "Only .pvti shells were found; .vti pieces are required for B17 argmax diagnostics: "
            + ", ".join(pvti_only)
        )

    onsets = first_onsets(all_stats)
    summary = key_summary(root, all_stats, all_argmax, frame_summaries, onsets)
    summary["pvti_only_cases_skipped"] = pvti_only
    summary["frame_summaries"] = frame_summaries

    write_csv(out_dir / "b17_mask_stats.csv", all_stats)
    (out_dir / "b17_argmax_trace.json").write_text(
        json.dumps(all_argmax, indent=2, sort_keys=True), encoding="utf-8"
    )
    (out_dir / "b17_first_onset.json").write_text(
        json.dumps(onsets, indent=2, sort_keys=True), encoding="utf-8"
    )
    (out_dir / "b17_field_presence.json").write_text(
        json.dumps(frame_summaries, indent=2, sort_keys=True), encoding="utf-8"
    )
    (out_dir / "b17_key_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in summary.items() if k != "frame_summaries"}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
