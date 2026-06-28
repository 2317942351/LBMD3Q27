#!/usr/bin/env python3
"""Stage14-B36 force-over-rho limiter gate.

This gate is diagnostic for the default-off B36 write candidate. It reads VTI
frames directly so it can check vector identities that are not visible from
scalar max tables alone.
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

REQUIRED_ALWAYS = [
    "PhaseField",
    "Rho",
    "ReplayPhaseFromH",
    "ReplayForceOverRho",
    "ReplayMF",
    "ReplayMomentumDeltaG",
    "B36ForceOverRhoPreCap",
    "B36ForceOverRhoPostCap",
    "B36ForceOverRhoPreCapMag",
    "B36ForceOverRhoPostCapMag",
    "B36ForceOverRhoCapScale",
    "B36ForceOverRhoCapHit",
]


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


def vector_norm(values: np.ndarray | None) -> np.ndarray | None:
    if values is None:
        return None
    arr = np.asarray(values, dtype=float)
    if arr.ndim == 2:
        return np.linalg.norm(arr, axis=1)
    return np.abs(arr.reshape(-1))


def scalar(values: np.ndarray | None) -> np.ndarray | None:
    if values is None:
        return None
    arr = np.asarray(values, dtype=float)
    if arr.ndim == 2:
        return np.linalg.norm(arr, axis=1)
    return arr.reshape(-1)


def max_finite(values: np.ndarray | None) -> float | None:
    if values is None:
        return None
    arr = np.asarray(values, dtype=float).reshape(-1)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return None
    return float(np.max(finite))


def count_nonfinite(values: np.ndarray | None) -> int:
    if values is None:
        return 0
    arr = np.asarray(values, dtype=float)
    return int(arr.size - np.count_nonzero(np.isfinite(arr)))


def vector_residual_norm(a: np.ndarray | None, b: np.ndarray | None) -> np.ndarray | None:
    if a is None or b is None:
        return None
    av = np.asarray(a, dtype=float)
    bv = np.asarray(b, dtype=float)
    if av.shape != bv.shape or av.ndim != 2 or av.shape[1] != 3:
        return None
    return np.linalg.norm(av - bv, axis=1)


def safe_rel_residual(residual: np.ndarray | None, denom_vec: np.ndarray | None) -> float | None:
    if residual is None or denom_vec is None:
        return None
    denom = vector_norm(denom_vec)
    if denom is None:
        return None
    rel = residual / np.maximum(denom, 1.0e-12)
    finite = rel[np.isfinite(rel)]
    if finite.size == 0:
        return None
    return float(np.max(finite))


def read_metadata(case_dir: Path) -> dict[str, Any]:
    path = case_dir / "case_metadata.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def candidate_case_dirs(root: Path) -> list[Path]:
    if (root / "output").is_dir():
        return [root]
    return sorted(path.parent for path in root.rglob("output") if path.is_dir())


def density_threshold(metadata: dict[str, Any], rho_values: np.ndarray | None) -> float:
    density_h = float(metadata.get("density_h", 1.0) or 1.0)
    density_l = float(metadata.get("density_l", 0.0) or 0.0)
    threshold = 0.1 * density_h
    if density_l > 0.0:
        threshold = max(threshold, 5.0 * density_l)
    if rho_values is not None and rho_values.size:
        finite = rho_values[np.isfinite(rho_values)]
        if finite.size:
            threshold = max(threshold, float(np.nanpercentile(finite, 20.0)))
    return threshold


def summarize_frame(
    case_dir: Path,
    vti_path: Path,
    metadata: dict[str, Any],
    rel_tol: float,
    cap_tol: float,
    high_rho_hit_fraction_limit: float,
) -> dict[str, Any]:
    raw_dims, raw_arrays = load_vti(vti_path)
    physical_grid = metadata.get("physical_grid")
    arrays = {
        name: crop_to_physical(values, raw_dims, physical_grid)
        for name, values in raw_arrays.items()
    }
    missing = [name for name in REQUIRED_ALWAYS if name not in arrays]
    mode = int(metadata.get("b36_force_over_rho_limiter_mode", 0) or 0)
    cap = float(metadata.get("b36_force_over_rho_cap", 0.0) or 0.0)
    phase_l = float(metadata.get("phase_l", 0.0) or 0.0)
    phase_h = float(metadata.get("phase_h", 1.0) or 1.0)
    lo, hi = sorted([phase_l, phase_h])

    replay = arrays.get("ReplayForceOverRho")
    pre = arrays.get("B36ForceOverRhoPreCap")
    post = arrays.get("B36ForceOverRhoPostCap")
    mf = arrays.get("ReplayMF")
    delta_g = arrays.get("ReplayMomentumDeltaG")
    rho = scalar(arrays.get("Rho"))
    phase_from_h = scalar(arrays.get("ReplayPhaseFromH"))
    cap_hit = scalar(arrays.get("B36ForceOverRhoCapHit"))

    replay_norm = vector_norm(replay)
    post_norm = vector_norm(post)
    pre_norm = vector_norm(pre)
    mf_norm = vector_norm(mf)
    delta_norm = vector_norm(delta_g)
    replay_post_res = vector_residual_norm(replay, post)
    replay_pre_res = vector_residual_norm(replay, pre)
    momentum_res = vector_residual_norm(delta_g, mf)

    frame: dict[str, Any] = {
        "case": case_dir.name,
        "step": step_of(vti_path),
        "path": str(vti_path),
        "mode": mode,
        "cap": cap,
        "missing_fields": missing,
        "nonfinite_total": sum(count_nonfinite(arrays.get(name)) for name in REQUIRED_ALWAYS),
        "max_replay_force_over_rho": max_finite(replay_norm),
        "max_pre_cap_force_over_rho": max_finite(pre_norm),
        "max_post_cap_force_over_rho": max_finite(post_norm),
        "max_mf_norm": max_finite(mf_norm),
        "max_delta_g_norm": max_finite(delta_norm),
        "max_replay_minus_post": max_finite(replay_post_res),
        "max_replay_minus_pre": max_finite(replay_pre_res),
        "max_delta_g_minus_mf": max_finite(momentum_res),
        "max_delta_g_minus_mf_rel": safe_rel_residual(momentum_res, mf),
        "phase_from_h_min": None,
        "phase_from_h_max": None,
        "phase_from_h_oob_count": 0,
        "cap_hit_count": 0,
        "cap_hit_high_rho_fraction": 0.0,
        "cap_hit_low_rho_fraction": 1.0,
        "failures": [],
    }
    if phase_from_h is not None and phase_from_h.size:
        finite_phase = phase_from_h[np.isfinite(phase_from_h)]
        if finite_phase.size:
            frame["phase_from_h_min"] = float(np.min(finite_phase))
            frame["phase_from_h_max"] = float(np.max(finite_phase))
            frame["phase_from_h_oob_count"] = int(
                np.count_nonzero((finite_phase < lo - 1.0e-3) | (finite_phase > hi + 1.0e-3))
            )
    if cap_hit is not None and rho is not None and cap_hit.shape[0] == rho.shape[0]:
        hit = np.isfinite(cap_hit) & (cap_hit > 0.5)
        hit_count = int(np.count_nonzero(hit))
        frame["cap_hit_count"] = hit_count
        if hit_count:
            rho_threshold = density_threshold(metadata, rho)
            high = hit & (rho >= rho_threshold)
            high_fraction = float(np.count_nonzero(high) / hit_count)
            frame["cap_hit_high_rho_fraction"] = high_fraction
            frame["cap_hit_low_rho_fraction"] = 1.0 - high_fraction

    if missing:
        frame["failures"].append("missing_fields")
    if frame["nonfinite_total"]:
        frame["failures"].append("nonfinite_fields")
    if frame["phase_from_h_oob_count"]:
        frame["failures"].append("phase_from_h_out_of_bounds")
    if mode > 1 and cap > 0.0:
        max_replay = frame["max_replay_force_over_rho"]
        if max_replay is not None and max_replay > cap * (1.0 + cap_tol) + 1.0e-9:
            frame["failures"].append("mode2_replay_exceeds_cap")
        max_post = frame["max_post_cap_force_over_rho"]
        if max_post is not None and max_post > cap * (1.0 + cap_tol) + 1.0e-9:
            frame["failures"].append("mode2_post_exceeds_cap")
        if frame["max_replay_minus_post"] is not None and frame["max_replay_minus_post"] > 1.0e-6:
            frame["failures"].append("mode2_replay_not_post_cap")
    elif mode == 1:
        if frame["max_replay_minus_pre"] is not None and frame["max_replay_minus_pre"] > 1.0e-6:
            frame["failures"].append("mode1_replay_not_pre_cap")
    if frame["max_delta_g_minus_mf_rel"] is not None and frame["max_delta_g_minus_mf_rel"] > rel_tol:
        frame["failures"].append("momentum_delta_g_not_mf")
    if (
        frame["cap_hit_count"]
        and frame["cap_hit_high_rho_fraction"] > high_rho_hit_fraction_limit
    ):
        frame["failures"].append("cap_hit_not_low_rho_selective")
    return frame


def summarize_case(
    case_dir: Path,
    rel_tol: float,
    cap_tol: float,
    high_rho_hit_fraction_limit: float,
) -> dict[str, Any]:
    metadata = read_metadata(case_dir)
    frames = [
        summarize_frame(case_dir, path, metadata, rel_tol, cap_tol, high_rho_hit_fraction_limit)
        for path in sorted((case_dir / "output").glob("*.vti"), key=step_of)
    ]
    failures = sorted({failure for frame in frames for failure in frame["failures"]})
    return {
        "case": case_dir.name,
        "path": str(case_dir),
        "mode": int(metadata.get("b36_force_over_rho_limiter_mode", 0) or 0),
        "cap": float(metadata.get("b36_force_over_rho_cap", 0.0) or 0.0),
        "frame_count": len(frames),
        "status": "pass" if frames and not failures else "fail",
        "failures": failures,
        "frames": frames,
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
    parser.add_argument("root", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--csv", type=Path, default=None)
    parser.add_argument("--rel-tol", type=float, default=1.0e-2)
    parser.add_argument("--cap-tol", type=float, default=1.0e-3)
    parser.add_argument("--high-rho-hit-fraction-limit", type=float, default=5.0e-2)
    args = parser.parse_args()

    root = args.root.resolve()
    cases = [
        summarize_case(
            case_dir,
            rel_tol=args.rel_tol,
            cap_tol=args.cap_tol,
            high_rho_hit_fraction_limit=args.high_rho_hit_fraction_limit,
        )
        for case_dir in candidate_case_dirs(root)
    ]
    report = {
        "root": str(root),
        "status": "pass" if cases and all(case["status"] == "pass" for case in cases) else "fail",
        "claim_limit": "B36 force/rho limiter gate only; not contact-angle validation",
        "case_count": len(cases),
        "cases": cases,
    }
    out_path = args.out or (root / "stage14_b36_force_cap_gate.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    csv_path = args.csv or (root / "stage14_b36_force_cap_gate_frames.csv")
    write_csv(csv_path, [frame for case in cases for frame in case["frames"]])
    print(json.dumps({"status": report["status"], "out": str(out_path), "csv": str(csv_path)}))
    return 0 if report["status"] == "pass" else 3


if __name__ == "__main__":
    raise SystemExit(main())
