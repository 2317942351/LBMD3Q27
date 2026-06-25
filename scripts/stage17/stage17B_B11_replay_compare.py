#!/usr/bin/env python3
"""Compare B10 offline reconstruction with TCLB step-0/step-1 replay fields.

This script is diagnostic-only.  It reads TCLB VTI files, reconstructs the
initial CylinderCapInit field using the B10 helper, and compares PhaseField,
ReplayLapPhi, and ReplayMu against offline D3Q27 stencil values.

B15 showed that the legacy offline-fluid comparison can include TCLB boundary
cells.  This script therefore also emits corrected replay comparisons against
a periodic D3Q27 stencil applied to TCLB's own PhaseField on TCLB-fluid masks.
"""
from __future__ import annotations

import argparse
import base64
import csv
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from stage17B_B10_initial_cap_equilibrium import (  # noqa: E402
    chemical_potential,
    grad_d3q27_periodic,
    laplace_d3q27_periodic,
    parse_case_xml,
    reconstruct_cylinder_cap,
)


VTI_ARRAYS_TO_READ = {
    "PhaseField",
    "ReplayLapPhi",
    "ReplayMu",
    "InitialReplayLapPhi",
    "InitialReplayMu",
    "InitialReplayGradPhi",
    "InitialReplayWallGhostUsed",
    "InitialReplayPhaseStencilFallbackCount",
    "InitialNoGhostReplayLapPhi",
    "InitialNoGhostReplayMu",
    "InitialNoGhostReplayGradPhi",
    "InitialGhostDeltaLapPhi",
    "InitialGhostDeltaMu",
    "InitialGhostDeltaGradPhi",
    "InitialGhostStencilTouched",
    "InitialGhostNeighborCount",
    "InitialNoGhostPhaseStencilFallbackCount",
    "IsItBoundary",
    "BOUNDARY",
}


def decode_vti_binary_payload(text: str, dtype: np.dtype, header_type: str, components: int) -> np.ndarray:
    clean = "".join(text.split())
    header_nbytes = 8 if header_type == "UInt64" else 4
    header_chars = 12 if header_type == "UInt64" else 8
    if len(clean) < header_chars:
        raise ValueError("short VTI binary payload")
    header_raw = base64.b64decode(clean[:header_chars])
    nbytes = int.from_bytes(header_raw[:header_nbytes], byteorder="little", signed=False)
    data = base64.b64decode(clean[header_chars:])[:nbytes]
    if len(data) != nbytes or (nbytes % dtype.itemsize) != 0:
        raise ValueError(f"decoded VTI payload has {len(data)} bytes, expected {nbytes}")
    arr = np.frombuffer(data, dtype=dtype).copy()
    if components > 1:
        arr = arr.reshape((-1, components))
    return arr


def load_vti_xml_binary(path: Path) -> tuple[tuple[int, int, int], dict[str, np.ndarray]]:
    dtype_map = {
        "UInt8": np.dtype("u1"),
        "Int8": np.dtype("i1"),
        "UInt16": np.dtype("<u2"),
        "Int16": np.dtype("<i2"),
        "UInt32": np.dtype("<u4"),
        "Int32": np.dtype("<i4"),
        "UInt64": np.dtype("<u8"),
        "Int64": np.dtype("<i8"),
        "Float32": np.dtype("<f4"),
        "Float64": np.dtype("<f8"),
    }
    dims: tuple[int, int, int] | None = None
    arrays: dict[str, np.ndarray] = {}
    header_type = "UInt32"
    for event, elem in ET.iterparse(path, events=("start", "end")):
        if event == "start" and elem.tag == "VTKFile":
            header_type = elem.attrib.get("header_type", header_type)
        elif event == "start" and elem.tag == "ImageData":
            extent = [int(v) for v in elem.attrib["WholeExtent"].split()]
            dims = (
                extent[1] - extent[0],
                extent[3] - extent[2],
                extent[5] - extent[4],
            )
        elif event == "end" and elem.tag == "DataArray":
            name = elem.attrib.get("Name")
            if name in VTI_ARRAYS_TO_READ:
                dtype = dtype_map[elem.attrib["type"]]
                components = int(elem.attrib.get("NumberOfComponents", "1"))
                fmt = elem.attrib.get("format", "")
                if fmt != "binary" or elem.attrib.get("encoding", "base64") != "base64":
                    raise ValueError(f"unsupported VTI DataArray encoding for {name}: format={fmt}")
                arrays[name] = decode_vti_binary_payload(elem.text or "", dtype, header_type, components)
            elem.clear()
    if dims is None:
        raise ValueError(f"could not find ImageData WholeExtent in {path}")
    return dims, arrays


def load_vti(path: Path) -> tuple[tuple[int, int, int], dict[str, np.ndarray]]:
    try:
        import vtk  # type: ignore
        from vtk.util.numpy_support import vtk_to_numpy  # type: ignore
    except ModuleNotFoundError:
        return load_vti_xml_binary(path)

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


def reshape_scalar(arrays: dict[str, np.ndarray], field: str, dims: tuple[int, int, int]) -> np.ndarray | None:
    values = arrays.get(field)
    if values is None:
        return None
    arr = np.asarray(values, dtype=float)
    if arr.ndim == 2:
        arr = np.linalg.norm(arr, axis=1)
    nx, ny, nz = dims
    return arr.reshape((nz, ny, nx))


def stats(values: np.ndarray) -> dict[str, Any]:
    vals = np.asarray(values, dtype=float).ravel()
    finite = np.isfinite(vals)
    out: dict[str, Any] = {"count": int(vals.size), "nonfinite": int(vals.size - np.count_nonzero(finite))}
    vals = vals[finite]
    if vals.size == 0:
        out.update({"min": None, "max": None, "mean": None, "std": None, "max_abs": None, "p95_abs": None})
        return out
    out.update(
        {
            "min": float(np.min(vals)),
            "max": float(np.max(vals)),
            "mean": float(np.mean(vals)),
            "std": float(np.std(vals)),
            "max_abs": float(np.max(np.abs(vals))),
            "p95_abs": float(np.percentile(np.abs(vals), 95.0)),
        }
    )
    return out


def compare_field(
    name: str,
    offline: np.ndarray,
    tclb: np.ndarray | None,
    masks: dict[str, np.ndarray],
) -> dict[str, Any]:
    if tclb is None:
        return {"field": name, "present": False}
    diff = tclb - offline
    out: dict[str, Any] = {
        "field": name,
        "present": True,
        "tclb": {},
        "offline": {},
        "diff": {},
    }
    for region, mask in masks.items():
        out["tclb"][region] = stats(tclb[mask])
        out["offline"][region] = stats(offline[mask])
        out["diff"][region] = stats(diff[mask])
    return out


def write_summary_csv(frames: list[dict[str, Any]], out_csv: Path) -> None:
    rows: list[dict[str, Any]] = []
    for frame in frames:
        step = frame["step"]
        for field in frame["fields"]:
            if not field.get("present"):
                rows.append({"step": step, "field": field["field"], "present": False})
                continue
            for region, payload in field["diff"].items():
                row: dict[str, Any] = {
                    "step": step,
                    "field": field["field"],
                    "region": region,
                    "present": True,
                }
                for prefix in ("diff", "tclb", "offline"):
                    for key, value in field[prefix][region].items():
                        row[f"{prefix}_{key}"] = value
                rows.append(row)
    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=sorted({key for row in rows for key in row}))
        writer.writeheader()
        writer.writerows(rows)


def analyze_frame(
    vti: Path,
    step: int,
    params: Any,
    offline_phase: np.ndarray,
    offline_lap: np.ndarray,
    offline_mu: np.ndarray,
    signed_distance: np.ndarray,
    masks: dict[str, np.ndarray],
) -> dict[str, Any]:
    dims, arrays = load_vti(vti)
    if offline_phase.shape != (dims[2], dims[1], dims[0]):
        raise ValueError(f"VTI dims {dims} do not match offline shape {offline_phase.shape}")
    tclb_phase = reshape_scalar(arrays, "PhaseField", dims)
    tclb_lap = reshape_scalar(arrays, "ReplayLapPhi", dims)
    tclb_mu = reshape_scalar(arrays, "ReplayMu", dims)
    initial_lap = reshape_scalar(arrays, "InitialReplayLapPhi", dims)
    initial_mu = reshape_scalar(arrays, "InitialReplayMu", dims)
    initial_grad = reshape_scalar(arrays, "InitialReplayGradPhi", dims)
    initial_wallghost_used = reshape_scalar(arrays, "InitialReplayWallGhostUsed", dims)
    initial_fallback = reshape_scalar(arrays, "InitialReplayPhaseStencilFallbackCount", dims)
    no_ghost_lap = reshape_scalar(arrays, "InitialNoGhostReplayLapPhi", dims)
    no_ghost_mu = reshape_scalar(arrays, "InitialNoGhostReplayMu", dims)
    no_ghost_grad = reshape_scalar(arrays, "InitialNoGhostReplayGradPhi", dims)
    ghost_delta_lap = reshape_scalar(arrays, "InitialGhostDeltaLapPhi", dims)
    ghost_delta_mu = reshape_scalar(arrays, "InitialGhostDeltaMu", dims)
    ghost_delta_grad = reshape_scalar(arrays, "InitialGhostDeltaGradPhi", dims)
    ghost_stencil_touched = reshape_scalar(arrays, "InitialGhostStencilTouched", dims)
    ghost_neighbor_count = reshape_scalar(arrays, "InitialGhostNeighborCount", dims)
    no_ghost_fallback = reshape_scalar(arrays, "InitialNoGhostPhaseStencilFallbackCount", dims)
    boundary_source = arrays.get("IsItBoundary", arrays.get("BOUNDARY"))
    boundary = None if boundary_source is None else np.asarray(boundary_source, dtype=float).reshape((dims[2], dims[1], dims[0]))
    frame_masks = dict(masks)
    boundary_summary: dict[str, Any] = {"present": boundary is not None}
    tclb_lap_periodic = None
    tclb_mu_periodic = None
    if tclb_phase is not None:
        tclb_lap_periodic = laplace_d3q27_periodic(tclb_phase)
        tclb_mu_periodic = chemical_potential(params, tclb_phase, tclb_lap_periodic)

    if boundary is not None:
        tclb_fluid = boundary <= 0.5
        offline_fluid = masks["fluid"]
        tclb_interface = (
            np.zeros_like(tclb_fluid, dtype=bool)
            if tclb_phase is None
            else ((tclb_phase > 0.05) & (tclb_phase < 0.95))
        )
        near_wall_sdf = (signed_distance >= 0.0) & (signed_distance <= 3.0)
        contact_band_tclb_phase = (
            near_wall_sdf
            & (signed_distance <= 1.5)
            & tclb_interface
            & (np.zeros_like(tclb_fluid, dtype=bool) if tclb_phase is None else ((tclb_phase > 0.2) & (tclb_phase < 0.8)))
        )
        frame_masks.update(
            {
                "fluid_tclb_fluid": masks["fluid"] & tclb_fluid,
                "near_wall_tclb_fluid": masks["near_wall"] & tclb_fluid,
                "near_interface_tclb_fluid": masks["near_interface"] & tclb_fluid,
                "contact_core_tclb_fluid": masks["contact_core"] & tclb_fluid,
                "corrected_near_interface_tclb_phase_fluid": tclb_fluid & near_wall_sdf & tclb_interface,
                "corrected_contact_core_tclb_phase_fluid": tclb_fluid & contact_band_tclb_phase,
                "offline_fluid_tclb_boundary": offline_fluid & (~tclb_fluid),
                "cylinder_overlap_boundary": offline_fluid & (~tclb_fluid) & (signed_distance <= 3.0),
                "outer_boundary": (~tclb_fluid) & (signed_distance > 3.0),
            }
        )
        boundary_summary.update(
            {
                "tclb_boundary_cells": int(np.count_nonzero(~tclb_fluid)),
                "offline_fluid_tclb_boundary_cells": int(np.count_nonzero(offline_fluid & (~tclb_fluid))),
                "offline_solid_tclb_fluid_cells": int(np.count_nonzero((~offline_fluid) & tclb_fluid)),
            }
        )
    fields = [
        compare_field("PhaseField", offline_phase, tclb_phase, frame_masks),
        compare_field("ReplayLapPhi", offline_lap, tclb_lap, frame_masks),
        compare_field("ReplayMu", offline_mu, tclb_mu, frame_masks),
        compare_field("InitialReplayLapPhi", offline_lap, initial_lap, frame_masks),
        compare_field("InitialReplayMu", offline_mu, initial_mu, frame_masks),
        compare_field("InitialReplayGradPhi", np.zeros_like(offline_phase), initial_grad, frame_masks),
        compare_field("InitialReplayWallGhostUsed", np.zeros_like(offline_phase), initial_wallghost_used, frame_masks),
        compare_field("InitialReplayPhaseStencilFallbackCount", np.zeros_like(offline_phase), initial_fallback, frame_masks),
        compare_field("InitialNoGhostReplayLapPhi", offline_lap, no_ghost_lap, frame_masks),
        compare_field("InitialNoGhostReplayMu", offline_mu, no_ghost_mu, frame_masks),
        compare_field("InitialNoGhostReplayGradPhi", np.zeros_like(offline_phase), no_ghost_grad, frame_masks),
        compare_field("InitialGhostDeltaLapPhi", np.zeros_like(offline_phase), ghost_delta_lap, frame_masks),
        compare_field("InitialGhostDeltaMu", np.zeros_like(offline_phase), ghost_delta_mu, frame_masks),
        compare_field("InitialGhostDeltaGradPhi", np.zeros_like(offline_phase), ghost_delta_grad, frame_masks),
        compare_field("InitialGhostStencilTouched", np.zeros_like(offline_phase), ghost_stencil_touched, frame_masks),
        compare_field("InitialGhostNeighborCount", np.zeros_like(offline_phase), ghost_neighbor_count, frame_masks),
        compare_field("InitialNoGhostPhaseStencilFallbackCount", np.zeros_like(offline_phase), no_ghost_fallback, frame_masks),
    ]
    if tclb_lap_periodic is not None and tclb_mu_periodic is not None:
        fields.extend(
            [
                compare_field("CorrectedReplayLapPhiOnTclbPhase", tclb_lap_periodic, tclb_lap, frame_masks),
                compare_field("CorrectedReplayMuOnTclbPhase", tclb_mu_periodic, tclb_mu, frame_masks),
                compare_field("CorrectedInitialReplayLapPhiOnTclbPhase", tclb_lap_periodic, initial_lap, frame_masks),
                compare_field("CorrectedInitialReplayMuOnTclbPhase", tclb_mu_periodic, initial_mu, frame_masks),
                compare_field("CorrectedInitialNoGhostReplayLapPhiOnTclbPhase", tclb_lap_periodic, no_ghost_lap, frame_masks),
                compare_field("CorrectedInitialNoGhostReplayMuOnTclbPhase", tclb_mu_periodic, no_ghost_mu, frame_masks),
            ]
        )
    return {
        "step": step,
        "vti": str(vti),
        "available_arrays": sorted(arrays.keys()),
        "boundary_summary": boundary_summary,
        "corrected_reference": {
            "enabled": tclb_lap_periodic is not None and tclb_mu_periodic is not None,
            "reference_phase": "TCLB PhaseField",
            "reference_operator": "periodic D3Q27 stencil",
            "mask_rule": "prefer corrected_*_tclb_phase_fluid regions for solver replay audits",
        },
        "fields": fields,
    }


def classify(frames: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "status": "b11_replay_compare_complete",
        "claim_limit": "TCLB replay comparison only; not contact-angle validation",
    }
    step0 = next((frame for frame in frames if int(frame["step"]) == 0), None)
    if step0 is None:
        out["primary_result"] = "missing_step0"
        return out

    def field_diff(frame: dict[str, Any], field_name: str, region: str) -> float | None:
        for field in frame["fields"]:
            if field["field"] == field_name and field.get("present"):
                region_payload = field["diff"].get(region)
                if region_payload is None:
                    return None
                value = region_payload.get("max_abs")
                return None if value is None else float(value)
        return None

    phase_diff = field_diff(step0, "PhaseField", "fluid")
    phase_diff_core = field_diff(step0, "PhaseField", "contact_core_tclb_fluid")
    phase_diff_near = field_diff(step0, "PhaseField", "near_interface_tclb_fluid")
    lap_diff = field_diff(step0, "ReplayLapPhi", "near_interface_tclb_fluid")
    mu_diff = field_diff(step0, "ReplayMu", "near_interface_tclb_fluid")
    init_lap_diff = field_diff(step0, "InitialReplayLapPhi", "near_interface_tclb_fluid")
    init_mu_diff = field_diff(step0, "InitialReplayMu", "near_interface_tclb_fluid")
    no_ghost_lap_diff = field_diff(step0, "InitialNoGhostReplayLapPhi", "near_interface_tclb_fluid")
    no_ghost_mu_diff = field_diff(step0, "InitialNoGhostReplayMu", "near_interface_tclb_fluid")
    corrected_init_lap_diff = field_diff(
        step0,
        "CorrectedInitialReplayLapPhiOnTclbPhase",
        "corrected_near_interface_tclb_phase_fluid",
    )
    corrected_init_mu_diff = field_diff(
        step0,
        "CorrectedInitialReplayMuOnTclbPhase",
        "corrected_near_interface_tclb_phase_fluid",
    )
    corrected_no_ghost_lap_diff = field_diff(
        step0,
        "CorrectedInitialNoGhostReplayLapPhiOnTclbPhase",
        "corrected_near_interface_tclb_phase_fluid",
    )
    corrected_no_ghost_mu_diff = field_diff(
        step0,
        "CorrectedInitialNoGhostReplayMuOnTclbPhase",
        "corrected_near_interface_tclb_phase_fluid",
    )
    ghost_delta_lap = field_diff(step0, "InitialGhostDeltaLapPhi", "near_interface_tclb_fluid")
    ghost_delta_mu = field_diff(step0, "InitialGhostDeltaMu", "near_interface_tclb_fluid")
    ghost_delta_mu_core = field_diff(step0, "InitialGhostDeltaMu", "contact_core_tclb_fluid")
    ghost_neighbor_count = None
    ghost_touched = None
    no_ghost_fallback = None
    init_wallghost_used = None
    for field in step0["fields"]:
        if field["field"] == "InitialReplayWallGhostUsed" and field.get("present"):
            init_wallghost_used = field["tclb"]["near_interface_tclb_fluid"].get("max_abs")
        elif field["field"] == "InitialGhostNeighborCount" and field.get("present"):
            ghost_neighbor_count = field["tclb"]["near_interface_tclb_fluid"].get("max_abs")
        elif field["field"] == "InitialGhostStencilTouched" and field.get("present"):
            ghost_touched = field["tclb"]["near_interface_tclb_fluid"].get("max_abs")
        elif field["field"] == "InitialNoGhostPhaseStencilFallbackCount" and field.get("present"):
            no_ghost_fallback = field["tclb"]["near_interface_tclb_fluid"].get("max_abs")
    b13_present = no_ghost_mu_diff is not None and ghost_delta_mu is not None
    no_ghost_mu_improvement = None
    no_ghost_lap_improvement = None
    if b13_present and init_mu_diff is not None and no_ghost_mu_diff is not None:
        no_ghost_mu_improvement = float(init_mu_diff) - float(no_ghost_mu_diff)
    if b13_present and init_lap_diff is not None and no_ghost_lap_diff is not None:
        no_ghost_lap_improvement = float(init_lap_diff) - float(no_ghost_lap_diff)
    out.update(
        {
            "step0_phase_fluid_max_abs_diff": phase_diff,
            "step0_phase_near_interface_tclb_fluid_max_abs_diff": phase_diff_near,
            "step0_phase_contact_core_tclb_fluid_max_abs_diff": phase_diff_core,
            "step0_lap_near_interface_max_abs_diff": lap_diff,
            "step0_mu_near_interface_max_abs_diff": mu_diff,
            "step0_initial_lap_near_interface_max_abs_diff": init_lap_diff,
            "step0_initial_mu_near_interface_max_abs_diff": init_mu_diff,
            "step0_initial_wallghost_used_near_interface_max_abs": init_wallghost_used,
            "b13_present": b13_present,
            "step0_no_ghost_lap_near_interface_max_abs_diff": no_ghost_lap_diff,
            "step0_no_ghost_mu_near_interface_max_abs_diff": no_ghost_mu_diff,
            "step0_corrected_initial_lap_near_interface_max_abs_diff": corrected_init_lap_diff,
            "step0_corrected_initial_mu_near_interface_max_abs_diff": corrected_init_mu_diff,
            "step0_corrected_no_ghost_lap_near_interface_max_abs_diff": corrected_no_ghost_lap_diff,
            "step0_corrected_no_ghost_mu_near_interface_max_abs_diff": corrected_no_ghost_mu_diff,
            "step0_ghost_delta_lap_near_interface_max_abs": ghost_delta_lap,
            "step0_ghost_delta_mu_near_interface_max_abs": ghost_delta_mu,
            "step0_ghost_delta_mu_contact_core_max_abs": ghost_delta_mu_core,
            "step0_initial_ghost_neighbor_count_near_interface_max_abs": ghost_neighbor_count,
            "step0_initial_ghost_stencil_touched_near_interface_max_abs": ghost_touched,
            "step0_no_ghost_fallback_near_interface_max_abs": no_ghost_fallback,
            "step0_no_ghost_mu_improvement_vs_current": no_ghost_mu_improvement,
            "step0_no_ghost_lap_improvement_vs_current": no_ghost_lap_improvement,
            "step0_boundary_summary": step0.get("boundary_summary", {}),
            "corrected_reference_note": (
                "Corrected* fields compare TCLB replay fields against a periodic D3Q27 stencil "
                "applied to TCLB PhaseField on TCLB-fluid masks. Prefer these over legacy "
                "offline-fluid-mask errors when judging solver replay correctness."
            ),
        }
    )
    if corrected_init_mu_diff is not None and corrected_init_lap_diff is not None:
        if corrected_init_mu_diff <= 1.0e-12 and corrected_init_lap_diff <= 1.0e-12:
            out["primary_result"] = "corrected_initial_replay_matches_tclb_phase_periodic_stencil"
            out["legacy_offline_diff_status"] = "retired_as_solver_bug_evidence"
        else:
            out["primary_result"] = "corrected_initial_replay_has_nonroundoff_residual"
            out["legacy_offline_diff_status"] = "do_not_use_legacy_diff_until_corrected_residual_is_explained"
    elif b13_present:
        if (
            no_ghost_mu_improvement is not None
            and no_ghost_lap_improvement is not None
            and no_ghost_mu_improvement > 1.0e-10
            and no_ghost_lap_improvement > 1.0e-10
        ):
            out["primary_result"] = "b13_no_ghost_shadow_reduces_initial_replay_error"
        elif ghost_delta_mu is not None and ghost_delta_mu > 1.0e-12:
            out["primary_result"] = "b13_wallghost_delta_present_but_no_ghost_does_not_match_offline"
        else:
            out["primary_result"] = "b13_no_significant_wallghost_delta_detected"
    elif init_mu_diff is not None and init_mu_diff <= 1.0e-10:
        out["primary_result"] = "initial_replay_mu_matches_offline_reconstruction"
    elif init_mu_diff is not None:
        out["primary_result"] = "initial_replay_mu_differs_from_offline_reconstruction"
    elif phase_diff_near is not None and phase_diff_near <= 1.0e-10 and phase_diff_core is not None and phase_diff_core <= 1.0e-10:
        out["primary_result"] = "step0_phase_matches_offline_cap_in_nearwall_interface_and_contact_core"
        out["replay_field_note"] = (
            "ReplayLapPhi/ReplayMu at step0 are zero-valued diagnostics in the initial VTI; "
            "use step1+ or a dedicated pre-collision replay to compare those fields."
        )
    elif phase_diff is not None and phase_diff > 1.0e-10:
        out["primary_result"] = "offline_reconstruction_does_not_match_tclb_step0_phase_in_selected_masks"
    elif mu_diff is not None and mu_diff > 1.0e-10:
        out["primary_result"] = "phase_matches_but_replay_mu_differs_from_offline_periodic_stencil"
    elif phase_diff is None:
        out["primary_result"] = "missing_phasefield"
    else:
        out["primary_result"] = "offline_reconstruction_matches_step0_available_replay_fields"
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--vti0", type=Path, required=True)
    parser.add_argument("--vti1", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--coord-mode", default="cell_center", choices=["cell_center", "node"])
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    params = parse_case_xml(args.case)
    phase, solid, signed_distance, _y, _z = reconstruct_cylinder_cap(params, args.coord_mode)
    lap = laplace_d3q27_periodic(phase)
    _gx, _gy, _gz = grad_d3q27_periodic(phase)
    mu = chemical_potential(params, phase, lap)
    fluid = ~solid
    interface = fluid & (phase > 0.05) & (phase < 0.95)
    near_wall = fluid & (signed_distance >= 0.0) & (signed_distance <= 3.0)
    near_interface = near_wall & interface
    contact_core = fluid & (signed_distance >= 0.0) & (signed_distance <= 1.5) & (phase > 0.2) & (phase < 0.8)
    masks = {
        "fluid": fluid,
        "interface": interface,
        "near_wall": near_wall,
        "near_interface": near_interface,
        "contact_core": contact_core,
    }
    frame_specs = [(0, args.vti0)]
    if args.vti1 is not None:
        frame_specs.append((1, args.vti1))
    frames = [analyze_frame(vti, step, params, phase, lap, mu, signed_distance, masks) for step, vti in frame_specs]
    result = {
        "case_xml": str(args.case),
        "coord_mode": args.coord_mode,
        "frames": frames,
    }
    result["classification"] = classify(frames)
    (args.out / "b11_replay_compare.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_summary_csv(frames, args.out / "b11_replay_compare_summary.csv")
    print(json.dumps(result["classification"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
