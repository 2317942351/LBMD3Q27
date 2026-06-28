#!/usr/bin/env python3
"""Post-process Stage14-B43 F_mu scale candidates from B40 VTI fields.

B43 intentionally avoids adding new TCLB fields. It reads the existing B40
stress audit output and reconstructs scale candidates from
``B40FmuMomentRelaxedLegacy`` plus ``B40FmuLegacyScale``. This keeps B43 as a
post-processing gate and avoids another expensive TCLB accessor regeneration.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class Candidate:
    name: str
    physical_candidate: bool
    note: str


CANDIDATES = [
    Candidate("legacy", True, "current active scale"),
    Candidate("zero", False, "sanity check only; not a physical closure"),
    Candidate("no_density_diff", True, "remove density-difference multiplier"),
    Candidate("negative_legacy", True, "sign check"),
    Candidate("bgk_style", True, "opposite sign of existing stage14_fmu_bgk_scale"),
    Candidate("bgk_legacy_sign", True, "existing stage14_fmu_bgk_scale: (0.5-tau)/tau"),
    Candidate("legacy_tenth", True, "diagnostic magnitude sweep"),
    Candidate("legacy_hundredth", True, "diagnostic magnitude sweep"),
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
    arr: np.ndarray, dims: tuple[int, int, int], physical_grid: list[int] | None
) -> np.ndarray:
    if not physical_grid:
        return np.asarray(arr)
    px, py, pz = [int(v) for v in physical_grid]
    nx, ny, nz = dims
    values = np.asarray(arr)
    if px > nx or py > ny or pz > nz or values.shape[0] != nx * ny * nz:
        return values
    if values.ndim == 1:
        return values.reshape((nx, ny, nz))[:px, :py, :pz].reshape(-1)
    return values.reshape((nx, ny, nz, values.shape[1]))[:px, :py, :pz, :].reshape(
        -1, values.shape[1]
    )


def read_metadata(case_dir: Path) -> dict[str, Any]:
    path = case_dir / "case_metadata.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def case_dirs(root: Path) -> list[Path]:
    if (root / "output").is_dir():
        return [root]
    return sorted(path.parent for path in root.rglob("output") if path.is_dir())


def vector_norm(arr: np.ndarray) -> np.ndarray:
    values = np.asarray(arr, dtype=float)
    if values.ndim == 2:
        return np.linalg.norm(values, axis=1)
    return np.abs(values.reshape(-1))


def finite_max(values: np.ndarray) -> float | None:
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return None
    return float(np.max(finite))


def mask_values(name: str, arrays: dict[str, np.ndarray], metadata: dict[str, Any]) -> np.ndarray:
    rho = np.asarray(arrays["Rho"], dtype=float).reshape(-1)
    phase = np.asarray(arrays["PhaseField"], dtype=float).reshape(-1)
    boundary = np.asarray(arrays.get("BOUNDARY", np.zeros_like(rho)), dtype=float).reshape(-1)
    fluid = np.isfinite(rho) & np.isfinite(phase) & (boundary <= 0.5)
    density_l = float(metadata.get("density_l", 0.005) or 0.005)
    density_h = float(metadata.get("density_h", 1.0) or 1.0)
    if name == "all_cells":
        return np.ones_like(rho, dtype=bool)
    if name == "fluid_all":
        return fluid
    if name == "low_rho":
        return fluid & (rho <= max(5.0 * density_l, 0.05 * density_h))
    if name == "interface_wide":
        return fluid & (phase > 0.05) & (phase < 0.95)
    if name == "near_wall":
        wall_ghost = np.asarray(arrays.get("WallGhost", np.zeros_like(rho)), dtype=float).reshape(-1)
        return fluid & (np.abs(wall_ghost) > 0.0)
    return fluid


def scale_map(arrays: dict[str, np.ndarray], metadata: dict[str, Any]) -> dict[str, np.ndarray]:
    legacy = np.asarray(arrays["B40FmuLegacyScale"], dtype=float).reshape(-1)
    bgk = np.asarray(arrays["B40FmuBGKScale"], dtype=float).reshape(-1)
    density_diff = float(metadata.get("density_h", 1.0) or 1.0) - float(
        metadata.get("density_l", 0.005) or 0.005
    )
    if "ReplayPressureForceScale" in arrays:
        pressure_scale = np.asarray(arrays["ReplayPressureForceScale"], dtype=float).reshape(-1)
        density_diff_factor = pressure_scale * -3.0
    else:
        density_diff_factor = np.full_like(legacy, density_diff)
    return {
        "legacy": legacy,
        "zero": np.zeros_like(legacy),
        "no_density_diff": np.divide(
            legacy,
            density_diff_factor,
            out=np.zeros_like(legacy),
            where=(np.abs(density_diff_factor) > 1.0e-300) & np.isfinite(legacy),
        ),
        "negative_legacy": -legacy,
        "bgk_style": -bgk,
        "bgk_legacy_sign": bgk,
        "legacy_tenth": 0.1 * legacy,
        "legacy_hundredth": 0.01 * legacy,
    }


def summarize_frame(case_dir: Path, vti: Path, focus_masks: list[str]) -> list[dict[str, Any]]:
    metadata = read_metadata(case_dir)
    dims, raw_arrays = load_vti(vti)
    physical_grid = metadata.get("physical_grid")
    arrays = {
        name: crop_to_physical(values, dims, physical_grid)
        for name, values in raw_arrays.items()
    }
    required = [
        "PhaseField",
        "Rho",
        "B40FmuMomentRelaxedLegacy",
        "B40FmuLegacyScale",
        "B40FmuBGKScale",
        "ReplayFsurf",
        "ReplayFpressure",
        "ReplayFbody",
        "ReplayForceRhoEffective",
    ]
    missing = [name for name in required if name not in arrays]
    if missing:
        return [
            {
                "case": case_dir.name,
                "step": step_of(vti),
                "candidate": "missing_fields",
                "mask": "all_cells",
                "missing_fields": ";".join(missing),
            }
        ]
    legacy_scale = np.asarray(arrays["B40FmuLegacyScale"], dtype=float).reshape(-1)
    legacy_fmu = np.asarray(arrays["B40FmuMomentRelaxedLegacy"], dtype=float)
    base = np.divide(
        legacy_fmu,
        legacy_scale[:, None],
        out=np.zeros_like(legacy_fmu, dtype=float),
        where=(np.abs(legacy_scale[:, None]) > 1.0e-300) & np.isfinite(legacy_fmu),
    )
    scales = scale_map(arrays, metadata)
    fsurf = np.asarray(arrays["ReplayFsurf"], dtype=float)
    fpressure = np.asarray(arrays["ReplayFpressure"], dtype=float)
    fbody = np.asarray(arrays["ReplayFbody"], dtype=float)
    rho_eff = np.asarray(arrays["ReplayForceRhoEffective"], dtype=float).reshape(-1)
    rows: list[dict[str, Any]] = []
    for mask_name in focus_masks:
        mask = mask_values(mask_name, arrays, metadata)
        if not np.count_nonzero(mask):
            continue
        for cand in CANDIDATES:
            scale = scales[cand.name]
            fmu = base * scale[:, None]
            force = (fsurf + fpressure + fbody + fmu) / np.maximum(rho_eff[:, None], 1.0e-300)
            rows.append(
                {
                    "case": case_dir.name,
                    "step": step_of(vti),
                    "mask": mask_name,
                    "candidate": cand.name,
                    "physical_candidate": cand.physical_candidate,
                    "scale_max_abs": finite_max(np.abs(scale[mask])),
                    "fmu_norm_max": finite_max(vector_norm(fmu[mask])),
                    "force_over_rho_norm_max": finite_max(vector_norm(force[mask])),
                    "note": cand.note,
                }
            )
    return rows


def summarize(root: Path, focus_step: int | None, focus_masks: list[str]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for case_dir in case_dirs(root):
        vtis = sorted((case_dir / "output").glob("case_VTK_P00_*.vti"), key=step_of)
        if focus_step is not None:
            vtis = [path for path in vtis if step_of(path) == focus_step]
        if not vtis:
            continue
        rows.extend(summarize_frame(case_dir, vtis[-1], focus_masks))
    low_rows = [row for row in rows if row.get("mask") == "low_rho"]
    legacy = next((row for row in low_rows if row.get("candidate") == "legacy"), None)
    legacy_force = legacy.get("force_over_rho_norm_max") if legacy else None
    for row in rows:
        force = row.get("force_over_rho_norm_max")
        row["force_vs_legacy"] = (
            force / legacy_force
            if isinstance(force, (float, int)) and isinstance(legacy_force, (float, int)) and legacy_force
            else None
        )
    physical = [row for row in low_rows if row.get("physical_candidate")]
    below_100 = [row for row in physical if (row.get("force_over_rho_norm_max") or 1.0e300) < 100.0]
    below_1000 = [row for row in physical if (row.get("force_over_rho_norm_max") or 1.0e300) < 1000.0]
    zero = next((row for row in low_rows if row.get("candidate") == "zero"), None)
    if below_100:
        verdict = "b43_postprocess_scale_candidate_strong"
    elif below_1000:
        verdict = "b43_postprocess_scale_candidate_marginal"
    elif zero and (zero.get("force_over_rho_norm_max") or 1.0e300) < 1000.0:
        verdict = "b43_zero_only_controls_force"
    else:
        verdict = "b43_no_scale_candidate"
    return {
        "claim_limit": "B43 postprocess scale probe only; no solver writeback",
        "root": str(root),
        "focus_step": focus_step,
        "rows": sorted(rows, key=lambda r: (str(r.get("mask")), float(r.get("force_over_rho_norm_max") or 1.0e300))),
        "legacy_low_rho_force_over_rho": legacy_force,
        "verdict": verdict,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "case",
        "step",
        "mask",
        "candidate",
        "physical_candidate",
        "scale_max_abs",
        "fmu_norm_max",
        "force_over_rho_norm_max",
        "force_vs_legacy",
        "note",
        "missing_fields",
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
        "# Stage14-B43 Postprocess F_mu Scale Probe",
        "",
        "Status: post-processing diagnostic. No TCLB field or active solver path is changed.",
        "",
        f"Root: `{report['root']}`",
        f"Focus step: `{report['focus_step']}`",
        f"Legacy low-rho F/rho: `{fmt(report['legacy_low_rho_force_over_rho'])}`",
        f"Verdict: `{report['verdict']}`",
        "",
        "| mask | candidate | physical | scale | F_mu | F/rho | F/rho / legacy | note |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in report["rows"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("mask")),
                    str(row.get("candidate")),
                    "yes" if row.get("physical_candidate") else "no",
                    fmt(row.get("scale_max_abs")),
                    fmt(row.get("fmu_norm_max")),
                    fmt(row.get("force_over_rho_norm_max")),
                    fmt(row.get("force_vs_legacy")),
                    str(row.get("note", "")),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "`zero` is a sanity check only. A passable physical candidate must be non-zero and later justified by force-balance and benchmark gates.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--focus-step", type=int, default=None)
    parser.add_argument("--prefix", default="b43")
    parser.add_argument("--masks", default="low_rho,interface_wide,near_wall,fluid_all")
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    masks = [part.strip() for part in args.masks.split(",") if part.strip()]
    report = summarize(args.root.resolve(), args.focus_step, masks)
    (args.out_dir / f"{args.prefix}_scale_probe_summary.json").write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )
    write_csv(args.out_dir / f"{args.prefix}_scale_probe_summary.csv", report["rows"])
    write_md(args.out_dir / f"{args.prefix}_scale_probe_summary.md", report)
    print(json.dumps({"verdict": report["verdict"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
