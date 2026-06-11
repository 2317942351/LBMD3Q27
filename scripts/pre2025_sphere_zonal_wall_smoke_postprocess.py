#!/usr/bin/env python3
"""Postprocess PRE sphere zonal wetting wall-smoke VTI fields.

This script is intentionally narrow: it checks whether TCLB zonal radAngle
settings reach wall reconstruction diagnostics. It is not a morphology or
contact-angle validation postprocessor.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy


STATUS = "runtime_sanity"
STEP_RE = re.compile(r"_VTK_P\d+_(\d{8})\.vti$")


def step_of(path: Path) -> int:
    match = STEP_RE.search(path.name)
    return int(match.group(1)) if match else -1


def read_vti(path: Path) -> tuple[tuple[int, int, int], dict[str, np.ndarray]]:
    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(str(path))
    reader.Update()
    image = reader.GetOutput()
    dims = tuple(int(value) - 1 for value in image.GetDimensions())
    arrays: dict[str, np.ndarray] = {}
    cell_data = image.GetCellData()
    for i in range(cell_data.GetNumberOfArrays()):
        arr = cell_data.GetArray(i)
        if arr is not None:
            arrays[arr.GetName() or f"array{i}"] = vtk_to_numpy(arr)
    return dims, arrays


def scalar(values: np.ndarray | None) -> np.ndarray | None:
    if values is None:
        return None
    out = np.asarray(values, dtype=float)
    if out.ndim > 1:
        out = out[:, 0]
    return out


def vector_mag(values: np.ndarray | None) -> np.ndarray | None:
    if values is None:
        return None
    out = np.asarray(values, dtype=float)
    if out.ndim == 1:
        return np.abs(out)
    return np.linalg.norm(out[:, :3], axis=1)


def stats(values: np.ndarray, mask: np.ndarray | None = None) -> dict[str, float | int]:
    arr = np.asarray(values, dtype=float)
    if mask is not None:
        arr = arr[mask]
    if arr.size == 0:
        return {"count": 0, "nonfinite": 0}
    finite = np.isfinite(arr)
    result: dict[str, float | int] = {
        "count": int(arr.size),
        "nonfinite": int(arr.size - np.count_nonzero(finite)),
    }
    if np.any(finite):
        x = arr[finite]
        result.update(
            {
                "min": float(np.min(x)),
                "mean": float(np.mean(x)),
                "p01": float(np.percentile(x, 1)),
                "p50": float(np.percentile(x, 50)),
                "p99": float(np.percentile(x, 99)),
                "max": float(np.max(x)),
            }
        )
    return result


def parse_config_radangles(config_xml: Path) -> list[dict[str, str]]:
    if not config_xml.exists():
        return []
    root = ET.parse(config_xml).getroot()
    rows: list[dict[str, str]] = []
    for param in root.findall(".//Param[@name='radAngle']"):
        rows.append(
            {
                "value": param.attrib.get("value", ""),
                "zone": param.attrib.get("zone", "DefaultZone"),
            }
        )
    return rows


def parse_csv_radangles(csv_path: Path) -> dict[str, float]:
    if not csv_path.exists():
        return {}
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        row = next(reader, None)
    if row is None:
        return {}
    out: dict[str, float] = {}
    for key, value in row.items():
        if key.startswith("radAngle-") and not key.endswith("_si"):
            try:
                out[key] = float(value)
            except (TypeError, ValueError):
                continue
    return out


def geometry_masks(
    dims: tuple[int, int, int],
    physical_dims: tuple[int, int, int],
    solid_center: tuple[float, float, float],
    solid_radius: float,
    shell_width: float,
    wall_mask: np.ndarray,
) -> dict[str, np.ndarray]:
    nx, ny, nz = dims
    px, py, pz = physical_dims
    idx = np.arange(nx * ny * nz)
    x = idx % nx
    y = (idx // nx) % ny
    z = idx // (nx * ny)
    physical = (x < px) & (y < py) & (z < pz)
    padding = ~physical
    outer = physical & (
        (x == 0)
        | (x == px - 1)
        | (y == 0)
        | (y == py - 1)
        | (z == 0)
        | (z == pz - 1)
    )
    cx, cy, cz = solid_center
    rr = np.sqrt((x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 + (z + 0.5 - cz) ** 2)
    sphere_shell = physical & (np.abs(rr - solid_radius) <= shell_width)
    sphere_inside = physical & (rr <= solid_radius)
    return {
        "all": np.ones_like(physical, dtype=bool),
        "physical": physical,
        "padding": padding,
        "fluid_physical": physical & (~wall_mask),
        "outer_geom": outer,
        "sphere_shell_geom": sphere_shell,
        "sphere_inside_geom": sphere_inside,
        "wall_all": wall_mask,
        "wall_physical": wall_mask & physical,
        "wall_padding": wall_mask & padding,
        "wall_outer_geom": wall_mask & outer,
        "wall_sphere_shell_geom": wall_mask & sphere_shell,
        "wall_sphere_inside_geom": wall_mask & sphere_inside,
        "wall_nonouter_physical": wall_mask & physical & (~outer),
    }


def summarize_frame(path: Path, args: argparse.Namespace) -> dict[str, Any]:
    dims, arrays = read_vti(path)
    phase = scalar(arrays.get("PhaseField"))
    if phase is None:
        raise RuntimeError(f"{path} has no PhaseField array")
    boundary = scalar(arrays.get("BOUNDARY"))
    if boundary is None:
        boundary = scalar(arrays.get("IsItBoundary"))
    wall_mask = np.zeros_like(phase, dtype=bool) if boundary is None else np.isfinite(boundary) & (boundary != 0.0)
    masks = geometry_masks(
        dims=dims,
        physical_dims=(args.physical_nx, args.physical_ny, args.physical_nz),
        solid_center=(args.solid_center_x, args.solid_center_y, args.solid_center_z),
        solid_radius=args.solid_radius,
        shell_width=args.sphere_shell_width,
        wall_mask=wall_mask,
    )

    fields: dict[str, np.ndarray] = {"PhaseField": phase}
    rho = scalar(arrays.get("Rho"))
    if rho is not None:
        fields["Rho"] = rho
    for name in [
        "WallPfF",
        "WallGradTangent",
        "WallTanCoeff",
        "WallPhasePred",
        "WallPhaseProfilePred",
        "WallProfileDelta",
        "WallPhaseSignedProfilePred",
        "WallSignedProfileDelta",
        "WallSignedLogitShift",
        "WallFluidSampleCount",
        "WallFluidSampleH",
        "WallPhaseUnifiedProfilePred",
        "WallUnifiedProfileDelta",
        "WallBCPath",
        "SpecialBoundaryPoint",
    ]:
        arr = scalar(arrays.get(name))
        if arr is not None:
            fields[name] = arr
    u_mag = vector_mag(arrays.get("U"))
    if u_mag is not None:
        fields["UMag"] = u_mag

    expected_outer_tan = math.tan(math.pi / 2.0 - math.radians(args.outer_rad_angle_deg))
    expected_sphere_tan = math.tan(math.pi / 2.0 - math.radians(args.sphere_rad_angle_deg))

    rec: dict[str, Any] = {
        "status": STATUS,
        "step": step_of(path),
        "file": str(path),
        "vti_cell_dims": list(dims),
        "physical_dims": [args.physical_nx, args.physical_ny, args.physical_nz],
        "mask_counts": {name: int(np.count_nonzero(mask)) for name, mask in masks.items()},
        "expected_outer_tan_coeff": expected_outer_tan,
        "expected_sphere_tan_coeff": expected_sphere_tan,
        "nonfinite_total": int(sum(np.count_nonzero(~np.isfinite(v)) for v in fields.values())),
        "field_stats": {},
    }
    for name, values in fields.items():
        rec["field_stats"][name] = {mask_name: stats(values, mask) for mask_name, mask in masks.items()}

    if "WallTanCoeff" in fields:
        wall_tan = fields["WallTanCoeff"]
        finite = np.isfinite(wall_tan)
        nonzero = finite & (np.abs(wall_tan) > args.tan_zero_tolerance)
        near_outer = finite & (np.abs(wall_tan - expected_outer_tan) <= args.outer_tan_tolerance)
        near_sphere = finite & (np.abs(wall_tan - expected_sphere_tan) <= args.sphere_tan_tolerance)
        rec["tan_coeff_check"] = {
            "nonzero_all": int(np.count_nonzero(nonzero)),
            "nonzero_wall_outer_geom": int(np.count_nonzero(nonzero & masks["wall_outer_geom"])),
            "nonzero_wall_sphere_shell_geom": int(np.count_nonzero(nonzero & masks["wall_sphere_shell_geom"])),
            "near_outer_expected_wall_outer_geom": int(np.count_nonzero(near_outer & masks["wall_outer_geom"])),
            "near_sphere_expected_wall_sphere_shell_geom": int(np.count_nonzero(near_sphere & masks["wall_sphere_shell_geom"])),
            "wall_outer_geom_count": int(np.count_nonzero(masks["wall_outer_geom"])),
            "wall_sphere_shell_geom_count": int(np.count_nonzero(masks["wall_sphere_shell_geom"])),
        }
    return rec


def flat_row(rec: dict[str, Any]) -> dict[str, Any]:
    def max_field(field: str, mask: str) -> Any:
        return rec.get("field_stats", {}).get(field, {}).get(mask, {}).get("max", math.nan)

    def mean_field(field: str, mask: str) -> Any:
        return rec.get("field_stats", {}).get(field, {}).get(mask, {}).get("mean", math.nan)

    def sum_field(field: str, mask: str) -> Any:
        stat = rec.get("field_stats", {}).get(field, {}).get(mask, {})
        mean = stat.get("mean", math.nan)
        count = stat.get("count", 0)
        try:
            return float(mean) * int(count)
        except (TypeError, ValueError):
            return math.nan

    tan = rec.get("tan_coeff_check", {})
    return {
        "step": rec["step"],
        "vti_cell_dims": "x".join(str(v) for v in rec["vti_cell_dims"]),
        "physical_dims": "x".join(str(v) for v in rec["physical_dims"]),
        "nonfinite_total": rec["nonfinite_total"],
        "wall_outer_count": rec["mask_counts"].get("wall_outer_geom", 0),
        "wall_sphere_shell_count": rec["mask_counts"].get("wall_sphere_shell_geom", 0),
        "wall_padding_count": rec["mask_counts"].get("wall_padding", 0),
        "outer_tan_nonzero_count": tan.get("nonzero_wall_outer_geom", math.nan),
        "outer_tan_expected_count": tan.get("near_outer_expected_wall_outer_geom", math.nan),
        "sphere_tan_expected_count": tan.get("near_sphere_expected_wall_sphere_shell_geom", math.nan),
        "wall_tan_outer_mean": mean_field("WallTanCoeff", "wall_outer_geom"),
        "wall_tan_sphere_mean": mean_field("WallTanCoeff", "wall_sphere_shell_geom"),
        "wall_phase_pred_outer_max": max_field("WallPhasePred", "wall_outer_geom"),
        "wall_phase_pred_sphere_max": max_field("WallPhasePred", "wall_sphere_shell_geom"),
        "wall_phase_unified_pred_outer_max": max_field("WallPhaseUnifiedProfilePred", "wall_outer_geom"),
        "wall_phase_unified_pred_sphere_max": max_field("WallPhaseUnifiedProfilePred", "wall_sphere_shell_geom"),
        "wall_unified_delta_outer_max": max_field("WallUnifiedProfileDelta", "wall_outer_geom"),
        "wall_unified_delta_sphere_max": max_field("WallUnifiedProfileDelta", "wall_sphere_shell_geom"),
        "wall_fluid_sample_count_sphere_mean": mean_field("WallFluidSampleCount", "wall_sphere_shell_geom"),
        "wall_fluid_sample_h_sphere_mean": mean_field("WallFluidSampleH", "wall_sphere_shell_geom"),
        "phase_physical_max": max_field("PhaseField", "physical"),
        "phase_padding_max": max_field("PhaseField", "padding"),
        "phase_sum_physical": sum_field("PhaseField", "physical"),
        "phase_sum_fluid_physical": sum_field("PhaseField", "fluid_physical"),
        "phase_sum_wall_physical": sum_field("PhaseField", "wall_physical"),
        "rho_sum_physical": sum_field("Rho", "physical"),
        "rho_sum_fluid_physical": sum_field("Rho", "fluid_physical"),
        "max_mach": max_field("UMag", "physical") / math.sqrt(1.0 / 3.0)
        if not math.isnan(max_field("UMag", "physical"))
        else math.nan,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--physical-nx", type=int, default=80)
    parser.add_argument("--physical-ny", type=int, default=80)
    parser.add_argument("--physical-nz", type=int, default=180)
    parser.add_argument("--solid-center-x", type=float, default=40.0)
    parser.add_argument("--solid-center-y", type=float, default=40.0)
    parser.add_argument("--solid-center-z", type=float, default=48.0)
    parser.add_argument("--solid-radius", type=float, default=24.0)
    parser.add_argument("--sphere-shell-width", type=float, default=2.0)
    parser.add_argument("--outer-rad-angle-deg", type=float, default=90.0)
    parser.add_argument("--sphere-rad-angle-deg", type=float, default=11.0)
    parser.add_argument("--tan-zero-tolerance", type=float, default=1.0e-9)
    parser.add_argument("--outer-tan-tolerance", type=float, default=1.0e-6)
    parser.add_argument("--sphere-tan-tolerance", type=float, default=1.0e-3)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    frames = sorted((args.case_root / "output").glob("*_VTK_P00_*.vti"), key=step_of)
    if not frames:
        raise SystemExit(f"no VTI frames under {args.case_root / 'output'}")
    rows = [summarize_frame(frame, args) for frame in frames]
    config_radangles = parse_config_radangles(args.case_root / "output" / "case_config_P00_00000000.xml")
    csvs = sorted((args.case_root / "output").glob("*_Log_P00_*.csv"))
    csv_radangles = parse_csv_radangles(csvs[0]) if csvs else {}

    payload = {
        "status": STATUS,
        "case_root": str(args.case_root),
        "config_radangles": config_radangles,
        "csv_radangles": csv_radangles,
        "expected": {
            "outer_rad_angle_deg": args.outer_rad_angle_deg,
            "sphere_rad_angle_deg": args.sphere_rad_angle_deg,
            "outer_tan_coeff": math.tan(math.pi / 2.0 - math.radians(args.outer_rad_angle_deg)),
            "sphere_tan_coeff": math.tan(math.pi / 2.0 - math.radians(args.sphere_rad_angle_deg)),
        },
        "frames": rows,
    }
    (args.out_dir / "zonal_wall_smoke_summary.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )

    flat_rows = [flat_row(row) for row in rows]
    if flat_rows:
        first = flat_rows[0]
        for row in flat_rows:
            for field in [
                "phase_sum_physical",
                "phase_sum_fluid_physical",
                "phase_sum_wall_physical",
                "rho_sum_physical",
                "rho_sum_fluid_physical",
            ]:
                base = first.get(field, math.nan)
                value = row.get(field, math.nan)
                try:
                    row[f"{field}_rel_change"] = (float(value) - float(base)) / float(base)
                except (TypeError, ValueError, ZeroDivisionError):
                    row[f"{field}_rel_change"] = math.nan
    with (args.out_dir / "zonal_wall_smoke_summary.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(flat_rows[0].keys()))
        writer.writeheader()
        writer.writerows(flat_rows)
    print(json.dumps({"status": STATUS, "rows": flat_rows, "out_dir": str(args.out_dir)}, indent=2))


if __name__ == "__main__":
    main()
