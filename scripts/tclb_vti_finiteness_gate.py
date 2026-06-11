#!/usr/bin/env python3
"""Gate TCLB VTI output by raw-field finiteness before morphology use.

This is a stability-control tool, not a validation script. It fails a run when
required raw VTI fields contain NaN/Inf in fluid cells, or when TCLB CSV logs
already contain NaN/Inf observables. VTK cell-data order is x fastest, then y,
then z, matching the project postprocessing scripts.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np


STEP_RE = re.compile(r"_VTK_P\d+_(\d{8})\.vti$")
BAD_TEXT_RE = re.compile(r"(?<![A-Za-z])[-+]?(?:nan|inf)(?![A-Za-z])", re.I)


@dataclass
class CsvBadValue:
    path: str
    line: int
    row_index: int
    iteration: str | None
    columns: list[str]
    values: list[str]


def step_from_vti(path: Path) -> int:
    match = STEP_RE.search(path.name)
    return int(match.group(1)) if match else -1


def parse_steps(text: str) -> set[int] | None:
    if not text:
        return None
    out: set[int] = set()
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        out.add(int(item))
    return out


def read_vti(path: Path) -> tuple[tuple[int, int, int], dict[str, np.ndarray]]:
    import vtk
    from vtk.util.numpy_support import vtk_to_numpy

    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(str(path))
    reader.Update()
    image = reader.GetOutput()
    dims = tuple(int(v) - 1 for v in image.GetDimensions())
    cell_data = image.GetCellData()
    arrays: dict[str, np.ndarray] = {}
    for i in range(cell_data.GetNumberOfArrays()):
        arr = cell_data.GetArray(i)
        if arr is not None:
            arrays[arr.GetName() or f"array{i}"] = vtk_to_numpy(arr)
    return dims, arrays


def finite_min_max(values: np.ndarray) -> tuple[float | None, float | None]:
    flat = np.asarray(values).reshape(-1)
    finite = flat[np.isfinite(flat)]
    if finite.size == 0:
        return None, None
    return float(finite.min()), float(finite.max())


def vector_speed_stats(values: np.ndarray) -> dict[str, float | None]:
    arr = np.asarray(values)
    if arr.ndim != 2 or arr.shape[1] < 3:
        return {"speed_max": None, "speed_mean": None}
    finite_vec = np.isfinite(arr[:, :3]).all(axis=1)
    if not finite_vec.any():
        return {"speed_max": None, "speed_mean": None}
    speed = np.linalg.norm(arr[finite_vec, :3], axis=1)
    return {"speed_max": float(speed.max()), "speed_mean": float(speed.mean())}


def boundary_to_fluid_mask(boundary: np.ndarray | None, n_cells: int) -> tuple[np.ndarray, dict[str, int | bool]]:
    if boundary is None:
        return np.ones(n_cells, dtype=bool), {
            "boundary_available": False,
            "boundary_nonfinite_count": 0,
            "boundary_cell_count": 0,
            "fluid_cell_count": n_cells,
        }
    arr = np.asarray(boundary)
    if arr.ndim > 1:
        arr = arr[:, 0]
    arr = arr.astype(float, copy=False)
    finite = np.isfinite(arr)
    wall = finite & (arr != 0.0)
    fluid = finite & ~wall
    return fluid, {
        "boundary_available": True,
        "boundary_nonfinite_count": int((~finite).sum()),
        "boundary_cell_count": int(wall.sum()),
        "fluid_cell_count": int(fluid.sum()),
    }


def bbox_from_cell_mask(mask: np.ndarray, dims: tuple[int, int, int]) -> dict[str, int] | None:
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        return None
    nx, ny, _nz = dims
    ix = idx % nx
    iy = (idx // nx) % ny
    iz = idx // (nx * ny)
    return {
        "x_min": int(ix.min()),
        "x_max": int(ix.max()),
        "y_min": int(iy.min()),
        "y_max": int(iy.max()),
        "z_min": int(iz.min()),
        "z_max": int(iz.max()),
    }


def cell_bad_mask(values: np.ndarray) -> np.ndarray:
    arr = np.asarray(values)
    if arr.ndim == 1:
        return ~np.isfinite(arr)
    return ~np.isfinite(arr).all(axis=1)


def count_bad_values_in_cells(values: np.ndarray, cells: np.ndarray) -> int:
    arr = np.asarray(values)
    if arr.ndim == 1:
        return int((~np.isfinite(arr[cells])).sum())
    return int((~np.isfinite(arr[cells])).sum())


def inspect_vti_file(
    path: Path,
    *,
    required_arrays: list[str],
    phase_threshold: float,
) -> tuple[list[dict[str, object]], dict[str, object] | None]:
    dims, arrays = read_vti(path)
    n_cells = math.prod(dims)
    step = step_from_vti(path)
    fluid_mask, boundary_info = boundary_to_fluid_mask(arrays.get("BOUNDARY"), n_cells)
    rows: list[dict[str, object]] = []
    first_bad: dict[str, object] | None = None
    missing = [name for name in required_arrays if name not in arrays]
    for name in missing:
        bad = {
            "source": "vti",
            "reason": "missing_required_array",
            "step": step,
            "file": str(path),
            "array": name,
        }
        if first_bad is None:
            first_bad = bad
        rows.append(
            {
                "step": step,
                "file": str(path),
                "dims": "x".join(str(v) for v in dims),
                "array": name,
                "missing": True,
                "nonfinite_count": "",
                "fluid_nonfinite_count": "",
                "finite_min": "",
                "finite_max": "",
                "speed_max": "",
                "phi_gt_threshold_fluid": "",
                **boundary_info,
            }
        )

    for name in required_arrays:
        if name not in arrays:
            continue
        values = arrays[name]
        bad_cells = cell_bad_mask(values)
        bad_values = int((~np.isfinite(values)).sum())
        fluid_bad_cells = bad_cells & fluid_mask
        fluid_bad_values = count_bad_values_in_cells(values, fluid_mask)
        mn, mx = finite_min_max(values)
        speed = vector_speed_stats(values) if name == "U" else {}
        phi_gt = ""
        if name == "PhaseField":
            phase = np.asarray(values).reshape(-1)
            finite_fluid = fluid_mask & np.isfinite(phase)
            phi_gt = int((phase[finite_fluid] > phase_threshold).sum())
        row: dict[str, object] = {
            "step": step,
            "file": str(path),
            "dims": "x".join(str(v) for v in dims),
            "array": name,
            "missing": False,
            "nonfinite_count": bad_values,
            "fluid_nonfinite_count": fluid_bad_values,
            "nonfinite_cell_count": int(bad_cells.sum()),
            "fluid_nonfinite_cell_count": int(fluid_bad_cells.sum()),
            "finite_min": "" if mn is None else mn,
            "finite_max": "" if mx is None else mx,
            "bad_bbox": bbox_from_cell_mask(bad_cells, dims),
            "fluid_bad_bbox": bbox_from_cell_mask(fluid_bad_cells, dims),
            "phi_gt_threshold_fluid": phi_gt,
            **speed,
            **boundary_info,
        }
        rows.append(row)
        if fluid_bad_values > 0 and first_bad is None:
            first_bad = {
                "source": "vti",
                "reason": "nonfinite_required_array_in_fluid",
                "step": step,
                "file": str(path),
                "array": name,
                "fluid_nonfinite_count": fluid_bad_values,
                "fluid_nonfinite_cell_count": int(fluid_bad_cells.sum()),
                "fluid_bad_bbox": bbox_from_cell_mask(fluid_bad_cells, dims),
                "total_nonfinite_count": bad_values,
                "total_bad_bbox": bbox_from_cell_mask(bad_cells, dims),
            }
    if boundary_info["boundary_nonfinite_count"] and first_bad is None:
        first_bad = {
            "source": "vti",
            "reason": "nonfinite_boundary_mask",
            "step": step,
            "file": str(path),
            "array": "BOUNDARY",
            "nonfinite_count": boundary_info["boundary_nonfinite_count"],
        }
    return rows, first_bad


def token_is_bad_number(token: str) -> bool:
    text = token.strip().strip('"').lower()
    if not text:
        return False
    if text in {"nan", "+nan", "-nan", "inf", "+inf", "-inf", "infinity", "+infinity", "-infinity"}:
        return True
    try:
        return not math.isfinite(float(text))
    except ValueError:
        return False


def inspect_csv(path: Path, *, max_bad_columns: int = 16) -> CsvBadValue | None:
    with path.open("r", newline="", encoding="utf-8", errors="replace") as fh:
        reader = csv.reader(fh)
        try:
            header = next(reader)
        except StopIteration:
            return None
        iteration_idx = 0 if header else None
        for row_idx, row in enumerate(reader, start=1):
            bad_cols: list[str] = []
            bad_vals: list[str] = []
            for col_idx, value in enumerate(row):
                if token_is_bad_number(value):
                    bad_cols.append(header[col_idx] if col_idx < len(header) else f"col{col_idx}")
                    bad_vals.append(value)
                    if len(bad_cols) >= max_bad_columns:
                        break
            if bad_cols:
                iteration = row[iteration_idx] if iteration_idx is not None and iteration_idx < len(row) else None
                return CsvBadValue(
                    path=str(path),
                    line=row_idx + 1,
                    row_index=row_idx,
                    iteration=iteration,
                    columns=bad_cols,
                    values=bad_vals,
                )
    return None


def inspect_text_log(path: Path) -> dict[str, object] | None:
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line_no, line in enumerate(fh, start=1):
            if "discovered NaN" in line or "Stopping due" in line or BAD_TEXT_RE.search(line):
                return {
                    "source": "text_log",
                    "path": str(path),
                    "line": line_no,
                    "text": line.strip()[:500],
                }
    return None


def find_files(output_dir: Path, glob_pattern: str, steps: set[int] | None) -> list[Path]:
    files = sorted(output_dir.glob(glob_pattern), key=step_from_vti)
    if steps is None:
        return files
    return [path for path in files if step_from_vti(path) in steps]


def write_metrics_csv(rows: list[dict[str, object]], path: Path) -> None:
    if not rows:
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            cleaned = {
                key: json.dumps(value, sort_keys=True) if isinstance(value, dict) else value
                for key, value in row.items()
            }
            writer.writerow(cleaned)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, help="TCLB run root containing output/")
    ap.add_argument("--output-dir", type=Path, help="raw VTI output directory")
    ap.add_argument("--out-dir", type=Path, help="directory for gate JSON/CSV")
    ap.add_argument("--glob", default="*VTK_P00_*.vti")
    ap.add_argument("--steps", default="", help="comma-separated VTI steps to inspect")
    ap.add_argument("--arrays", default="PhaseField,U,P,Rho")
    ap.add_argument("--phase-threshold", type=float, default=0.5)
    ap.add_argument("--log-csv-glob", default="case_Log_P00_*.csv")
    ap.add_argument("--skip-csv", action="store_true")
    ap.add_argument("--skip-text-log", action="store_true")
    ap.add_argument("--exit-zero", action="store_true")
    args = ap.parse_args()

    root = args.root
    output_dir = args.output_dir
    if output_dir is None:
        if root is None:
            raise SystemExit("pass --root or --output-dir")
        output_dir = root / "output"
    if root is None:
        root = output_dir.parent
    out_dir = args.out_dir or (root / "analysis_finiteness_gate")
    out_dir.mkdir(parents=True, exist_ok=True)

    required_arrays = [name.strip() for name in args.arrays.split(",") if name.strip()]
    steps = parse_steps(args.steps)
    vti_files = find_files(output_dir, args.glob, steps)
    if not vti_files:
        raise SystemExit(f"no VTI files matched {output_dir / args.glob}")

    all_rows: list[dict[str, object]] = []
    first_vti_bad: dict[str, object] | None = None
    for path in vti_files:
        rows, bad = inspect_vti_file(
            path,
            required_arrays=required_arrays,
            phase_threshold=args.phase_threshold,
        )
        all_rows.extend(rows)
        if bad is not None and first_vti_bad is None:
            first_vti_bad = bad

    first_csv_bad = None
    csv_files: list[str] = []
    if not args.skip_csv:
        for path in sorted(output_dir.glob(args.log_csv_glob)):
            csv_files.append(str(path))
            bad = inspect_csv(path)
            if bad is not None and first_csv_bad is None:
                first_csv_bad = {
                    "source": "log_csv",
                    "path": bad.path,
                    "line": bad.line,
                    "row_index": bad.row_index,
                    "iteration": bad.iteration,
                    "columns": bad.columns,
                    "values": bad.values,
                }

    first_text_bad = None
    text_logs: list[str] = []
    if not args.skip_text_log:
        for path in [root / "run.log", root / "run.stderr"]:
            if path.exists():
                text_logs.append(str(path))
                bad = inspect_text_log(path)
                if bad is not None and first_text_bad is None:
                    first_text_bad = bad

    bad_sources = [bad for bad in [first_csv_bad, first_text_bad, first_vti_bad] if bad]
    gate_passed = not bad_sources
    first_bad = bad_sources[0] if bad_sources else None
    summary = {
        "status": "runtime_sanity" if gate_passed else "failed_negative_evidence",
        "gate_passed": gate_passed,
        "root": str(root),
        "output_dir": str(output_dir),
        "out_dir": str(out_dir),
        "required_arrays": required_arrays,
        "phase_threshold": args.phase_threshold,
        "vti_files_checked": len(vti_files),
        "vti_steps_checked": [step_from_vti(path) for path in vti_files],
        "csv_files_checked": csv_files,
        "text_logs_checked": text_logs,
        "first_bad": first_bad,
        "first_csv_bad": first_csv_bad,
        "first_text_log_bad": first_text_bad,
        "first_vti_bad": first_vti_bad,
        "max_fluid_nonfinite_count_by_array": {
            name: max(
                (
                    int(row["fluid_nonfinite_count"])
                    for row in all_rows
                    if row.get("array") == name and row.get("fluid_nonfinite_count") != ""
                ),
                default=0,
            )
            for name in required_arrays
        },
        "claim_limit": "stability gate only; passing this does not validate physical prediction",
    }
    write_metrics_csv(all_rows, out_dir / "vti_finiteness_metrics.csv")
    (out_dir / "finiteness_gate_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    if args.exit_zero:
        return 0
    return 0 if gate_passed else 2


if __name__ == "__main__":
    sys.exit(main())
