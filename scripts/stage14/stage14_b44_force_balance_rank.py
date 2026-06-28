#!/usr/bin/env python3
"""Stage14-B44 force-balance and force-component postprocess gate.

B44 is diagnostic-only. It reads existing TCLB VTI fields and checks whether
the low-density force spike is a local component spike, a global force-balance
failure, or a scale-only artifact. It does not modify solver state and does
not validate contact angle.
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


CANDIDATES = {
    "legacy": "current active scale",
    "zero": "sanity check only; not physical",
    "no_density_diff": "remove density-difference multiplier",
    "negative_legacy": "sign check",
    "bgk_style": "opposite sign of B40FmuBGKScale",
    "bgk_legacy_sign": "B40FmuBGKScale",
    "legacy_tenth": "diagnostic magnitude sweep",
    "legacy_hundredth": "diagnostic magnitude sweep",
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


def crop(arr: np.ndarray, dims: tuple[int, int, int], physical_grid: list[int] | None) -> np.ndarray:
    values = np.asarray(arr)
    if not physical_grid:
        return values
    px, py, pz = [int(v) for v in physical_grid]
    nx, ny, nz = dims
    if px > nx or py > ny or pz > nz or values.shape[0] != nx * ny * nz:
        return values
    if values.ndim == 1:
        return values.reshape((nx, ny, nz))[:px, :py, :pz].reshape(-1)
    return values.reshape((nx, ny, nz, values.shape[1]))[:px, :py, :pz, :].reshape(-1, values.shape[1])


def read_metadata(case_dir: Path) -> dict[str, Any]:
    path = case_dir / "case_metadata.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def case_dirs(root: Path) -> list[Path]:
    if (root / "output").is_dir():
        return [root]
    return sorted(path.parent for path in root.rglob("output") if path.is_dir())


def norm_vec(values: np.ndarray) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    return np.linalg.norm(arr, axis=1) if arr.ndim == 2 else np.abs(arr.reshape(-1))


def finite_max(values: np.ndarray) -> float | None:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    return float(np.max(arr)) if arr.size else None


def finite_sum(values: np.ndarray) -> float | None:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    return float(np.sum(arr)) if arr.size else None


def vec_sum(values: np.ndarray) -> list[float] | None:
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 2 or arr.shape[1] != 3:
        return None
    finite = np.all(np.isfinite(arr), axis=1)
    if not np.any(finite):
        return None
    return [float(v) for v in np.sum(arr[finite], axis=0)]


def vec_norm_list(values: list[float] | None) -> float | None:
    if values is None:
        return None
    return float(math.sqrt(sum(v * v for v in values)))


def masks(arrays: dict[str, np.ndarray], metadata: dict[str, Any]) -> dict[str, np.ndarray]:
    rho = np.asarray(arrays["Rho"], dtype=float).reshape(-1)
    phase = np.asarray(arrays["PhaseField"], dtype=float).reshape(-1)
    boundary = np.asarray(arrays.get("BOUNDARY", np.zeros_like(rho)), dtype=float).reshape(-1)
    fluid = np.isfinite(rho) & np.isfinite(phase) & (boundary <= 0.5)
    density_l = float(metadata.get("density_l", 0.005) or 0.005)
    density_h = float(metadata.get("density_h", 1.0) or 1.0)
    out = {
        "fluid_all": fluid,
        "low_rho": fluid & (rho <= max(5.0 * density_l, 0.05 * density_h)),
        "interface_wide": fluid & (phase > 0.05) & (phase < 0.95),
        "near_wall": fluid & (np.abs(np.asarray(arrays.get("WallGhost", np.zeros_like(rho)), dtype=float).reshape(-1)) > 0.0),
    }
    out["near_interface_wall"] = out["near_wall"] & out["interface_wide"]
    return out


def scale_arrays(arrays: dict[str, np.ndarray], metadata: dict[str, Any]) -> dict[str, np.ndarray]:
    legacy = np.asarray(arrays["B40FmuLegacyScale"], dtype=float).reshape(-1)
    bgk = np.asarray(arrays["B40FmuBGKScale"], dtype=float).reshape(-1)
    density_diff = float(metadata.get("density_h", 1.0) or 1.0) - float(metadata.get("density_l", 0.005) or 0.005)
    denom = np.full_like(legacy, density_diff)
    return {
        "legacy": legacy,
        "zero": np.zeros_like(legacy),
        "no_density_diff": np.divide(legacy, denom, out=np.zeros_like(legacy), where=np.abs(denom) > 1.0e-300),
        "negative_legacy": -legacy,
        "bgk_style": -bgk,
        "bgk_legacy_sign": bgk,
        "legacy_tenth": 0.1 * legacy,
        "legacy_hundredth": 0.01 * legacy,
    }


def summarize_candidate(
    case: str,
    step: int,
    mask_name: str,
    mask: np.ndarray,
    arrays: dict[str, np.ndarray],
    fmu: np.ndarray,
    candidate: str,
) -> dict[str, Any]:
    fsurf = np.asarray(arrays["ReplayFsurf"], dtype=float)
    fpressure = np.asarray(arrays["ReplayFpressure"], dtype=float)
    fbody = np.asarray(arrays["ReplayFbody"], dtype=float)
    rho_eff = np.asarray(arrays["ReplayForceRhoEffective"], dtype=float).reshape(-1)
    total = fsurf + fpressure + fbody + fmu
    force_over_rho = total / np.maximum(rho_eff[:, None], 1.0e-300)
    term_norm_sums = {
        "fsurf_sum_mag": finite_sum(norm_vec(fsurf[mask])),
        "fpressure_sum_mag": finite_sum(norm_vec(fpressure[mask])),
        "fbody_sum_mag": finite_sum(norm_vec(fbody[mask])),
        "fmu_sum_mag": finite_sum(norm_vec(fmu[mask])),
        "total_sum_mag": finite_sum(norm_vec(total[mask])),
    }
    total_term_mag = sum(v or 0.0 for k, v in term_norm_sums.items() if k.endswith("_sum_mag") and k != "total_sum_mag")
    net = vec_sum(total[mask])
    net_norm = vec_norm_list(net)
    max_idx_local = int(np.nanargmax(norm_vec(force_over_rho[mask]))) if np.count_nonzero(mask) else -1
    global_indices = np.flatnonzero(mask)
    global_idx = int(global_indices[max_idx_local]) if max_idx_local >= 0 and global_indices.size else -1
    local_terms: dict[str, float] = {}
    if global_idx >= 0:
        local_terms = {
            "argmax_fsurf": float(norm_vec(fsurf[[global_idx]])[0]),
            "argmax_fpressure": float(norm_vec(fpressure[[global_idx]])[0]),
            "argmax_fbody": float(norm_vec(fbody[[global_idx]])[0]),
            "argmax_fmu": float(norm_vec(fmu[[global_idx]])[0]),
            "argmax_total": float(norm_vec(total[[global_idx]])[0]),
            "argmax_force_over_rho": float(norm_vec(force_over_rho[[global_idx]])[0]),
            "argmax_rho_eff": float(rho_eff[global_idx]),
        }
    return {
        "case": case,
        "step": step,
        "mask": mask_name,
        "candidate": candidate,
        "cell_count": int(np.count_nonzero(mask)),
        "net_force": net,
        "net_force_norm": net_norm,
        "net_over_term_sum": (net_norm / total_term_mag) if net_norm is not None and total_term_mag > 0 else None,
        "force_over_rho_max": finite_max(norm_vec(force_over_rho[mask])),
        "force_over_rho_p99": float(np.nanpercentile(norm_vec(force_over_rho[mask]), 99.0)) if np.count_nonzero(mask) else None,
        "fmu_fraction_sum_mag": (term_norm_sums["fmu_sum_mag"] / total_term_mag) if total_term_mag > 0 and term_norm_sums["fmu_sum_mag"] is not None else None,
        "note": CANDIDATES[candidate],
        **term_norm_sums,
        **local_terms,
    }


def summarize_frame(case_dir: Path, vti: Path, focus_masks: list[str]) -> dict[str, Any]:
    metadata = read_metadata(case_dir)
    dims, raw = load_vti(vti)
    arrays = {name: crop(values, dims, metadata.get("physical_grid")) for name, values in raw.items()}
    required = [
        "PhaseField",
        "Rho",
        "BOUNDARY",
        "ReplayFsurf",
        "ReplayFpressure",
        "ReplayFbody",
        "ReplayForceRhoEffective",
        "B40FmuMomentRelaxedLegacy",
        "B40FmuLegacyScale",
        "B40FmuBGKScale",
    ]
    missing = [name for name in required if name not in arrays]
    if missing:
        return {"case": case_dir.name, "step": step_of(vti), "missing_fields": missing, "rows": []}
    legacy_scale = np.asarray(arrays["B40FmuLegacyScale"], dtype=float).reshape(-1)
    legacy_fmu = np.asarray(arrays["B40FmuMomentRelaxedLegacy"], dtype=float)
    base = np.divide(
        legacy_fmu,
        legacy_scale[:, None],
        out=np.zeros_like(legacy_fmu, dtype=float),
        where=(np.abs(legacy_scale[:, None]) > 1.0e-300) & np.isfinite(legacy_fmu),
    )
    scale_by_name = scale_arrays(arrays, metadata)
    mask_by_name = masks(arrays, metadata)
    rows: list[dict[str, Any]] = []
    for mask_name in focus_masks:
        if mask_name not in mask_by_name:
            continue
        mask = mask_by_name[mask_name]
        if not np.count_nonzero(mask):
            continue
        for candidate, scale in scale_by_name.items():
            rows.append(summarize_candidate(case_dir.name, step_of(vti), mask_name, mask, arrays, base * scale[:, None], candidate))
    return {"case": case_dir.name, "step": step_of(vti), "missing_fields": [], "rows": rows}


def summarize(root: Path, focus_step: int, focus_masks: list[str]) -> dict[str, Any]:
    frames = []
    rows: list[dict[str, Any]] = []
    for case_dir in case_dirs(root):
        vtis = sorted((case_dir / "output").glob("case_VTK_P00_*.vti"), key=step_of)
        vtis = [path for path in vtis if step_of(path) == focus_step]
        if not vtis:
            frames.append({"case": case_dir.name, "step": focus_step, "missing_vti": True, "rows": []})
            continue
        frame = summarize_frame(case_dir, vtis[-1], focus_masks)
        frames.append(frame)
        rows.extend(frame["rows"])
    low_legacy = next((row for row in rows if row["mask"] == "low_rho" and row["candidate"] == "legacy"), None)
    legacy_force = low_legacy.get("force_over_rho_max") if low_legacy else None
    physical_nonzero = [
        row for row in rows
        if row["mask"] == "low_rho" and row["candidate"] not in {"zero"} and (row.get("force_over_rho_max") or 1.0e300) < 1000.0
    ]
    if physical_nonzero:
        verdict = "b44_force_balance_candidate_found"
    elif legacy_force is not None and legacy_force > 1000.0:
        verdict = "b44_no_force_balance_candidate"
    else:
        verdict = "b44_force_balance_inconclusive"
    return {
        "claim_limit": "B44 postprocess force-balance gate only; no solver writeback or contact-angle claim",
        "root": str(root),
        "focus_step": focus_step,
        "frames": frames,
        "rows": sorted(rows, key=lambda row: (row["mask"], row.get("force_over_rho_max") or 1.0e300)),
        "legacy_low_rho_force_over_rho_max": legacy_force,
        "verdict": verdict,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "case",
        "step",
        "mask",
        "candidate",
        "cell_count",
        "force_over_rho_max",
        "force_over_rho_p99",
        "net_force_norm",
        "net_over_term_sum",
        "fmu_fraction_sum_mag",
        "fsurf_sum_mag",
        "fpressure_sum_mag",
        "fbody_sum_mag",
        "fmu_sum_mag",
        "total_sum_mag",
        "argmax_fsurf",
        "argmax_fpressure",
        "argmax_fbody",
        "argmax_fmu",
        "argmax_total",
        "argmax_force_over_rho",
        "argmax_rho_eff",
        "note",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fields})


def fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def write_md(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Stage14-B44 Force Balance Gate",
        "",
        "Status: post-processing diagnostic only. No TCLB solver path is changed.",
        "",
        f"Root: `{report['root']}`",
        f"Focus step: `{report['focus_step']}`",
        f"Legacy low-rho max F/rho: `{fmt(report['legacy_low_rho_force_over_rho_max'])}`",
        f"Verdict: `{report['verdict']}`",
        "",
        "| mask | candidate | max F/rho | p99 F/rho | net/term | F_mu fraction | argmax rho_eff | note |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in report["rows"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("mask")),
                    str(row.get("candidate")),
                    fmt(row.get("force_over_rho_max")),
                    fmt(row.get("force_over_rho_p99")),
                    fmt(row.get("net_over_term_sum")),
                    fmt(row.get("fmu_fraction_sum_mag")),
                    fmt(row.get("argmax_rho_eff")),
                    str(row.get("note", "")),
                ]
            )
            + " |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "A low net/term ratio alone is not a pass: local F/rho spikes can still destabilize h even when the global force nearly cancels.",
        "A non-zero candidate must reduce local low-rho F/rho below threshold before it can move to an active default-off solver branch.",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--focus-step", type=int, default=13)
    parser.add_argument("--prefix", default="b44")
    parser.add_argument("--masks", default="low_rho,interface_wide,near_wall,near_interface_wall,fluid_all")
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    focus_masks = [part.strip() for part in args.masks.split(",") if part.strip()]
    report = summarize(args.root.resolve(), args.focus_step, focus_masks)
    (args.out_dir / f"{args.prefix}_force_balance_summary.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    write_csv(args.out_dir / f"{args.prefix}_force_balance_summary.csv", report["rows"])
    write_md(args.out_dir / f"{args.prefix}_force_balance_summary.md", report)
    print(json.dumps({"verdict": report["verdict"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
