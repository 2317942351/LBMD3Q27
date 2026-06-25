#!/usr/bin/env python3
"""Stage17B-B14 mask/operator equivalence audit.

This is an offline diagnostic.  It reads TCLB VTI output from B13, reconstructs
the same cylinder-cap initial field used by B10/B11, and compares several
offline D3Q27 stencil semantics against TCLB initial replay fields.

It does not validate contact angle and does not change solver behavior.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from stage17B_B10_initial_cap_equilibrium import (  # noqa: E402
    LAPLACE_CENTER_WEIGHT,
    LAPLACE_NORMALIZER,
    PHASE_H,
    PHASE_L,
    chemical_potential,
    neighbor_offsets,
    parse_case_xml,
    reconstruct_cylinder_cap,
    sample,
    stencil_weight,
)
from stage17B_B11_replay_compare import load_vti, reshape_scalar, stats  # noqa: E402


FIELDS = [
    "PhaseField",
    "InitialReplayLapPhi",
    "InitialReplayMu",
    "InitialNoGhostReplayLapPhi",
    "InitialNoGhostReplayMu",
    "InitialGhostDeltaLapPhi",
    "InitialGhostDeltaMu",
    "InitialReplayWallGhostUsed",
    "InitialGhostNeighborCount",
    "InitialNoGhostPhaseStencilFallbackCount",
    "IsItBoundary",
    "BOUNDARY",
]


def safe_ratio(num: float | None, den: float | None) -> float | None:
    if num is None or den is None or abs(den) < 1.0e-300:
        return None
    return float(num / den)


def region_field_stats(name: str, arr: np.ndarray | None, masks: dict[str, np.ndarray]) -> dict[str, Any]:
    if arr is None:
        return {"field": name, "present": False}
    out: dict[str, Any] = {"field": name, "present": True, "regions": {}}
    for region, mask in masks.items():
        out["regions"][region] = stats(arr[mask])
    return out


def compare_stats(name: str, candidate: np.ndarray, reference: np.ndarray, masks: dict[str, np.ndarray]) -> dict[str, Any]:
    diff = candidate - reference
    out: dict[str, Any] = {"field": name, "regions": {}}
    for region, mask in masks.items():
        out["regions"][region] = {
            "candidate": stats(candidate[mask]),
            "reference": stats(reference[mask]),
            "diff": stats(diff[mask]),
        }
    return out


def laplace_with_boundary_semantics(
    phase: np.ndarray,
    tclb_boundary: np.ndarray,
    mode: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """D3Q27 Laplace with alternate handling for boundary neighbors.

    Returns laplace, boundary-slot count, fallback count.
    """
    center = phase
    total = LAPLACE_CENTER_WEIGHT * center.copy()
    boundary_slots = np.zeros_like(phase, dtype=float)
    fallback_slots = np.zeros_like(phase, dtype=float)
    for dx, dy, dz in neighbor_offsets():
        pf = sample(phase, dx, dy, dz)
        nb = sample(tclb_boundary.astype(float), dx, dy, dz) > 0.5
        if mode == "periodic":
            selected = pf
        elif mode == "center_on_boundary":
            selected = np.where(nb, center, pf)
            boundary_slots += nb.astype(float)
        elif mode == "midpoint_on_boundary":
            midpoint = 0.5 * (PHASE_L + PHASE_H)
            selected = np.where(nb, midpoint, pf)
            boundary_slots += nb.astype(float)
            fallback_slots += nb.astype(float)
        else:
            raise ValueError(f"unknown stencil mode {mode}")
        total += stencil_weight(dx, dy, dz) * selected
    return total / LAPLACE_NORMALIZER, boundary_slots, fallback_slots


def build_masks(
    phase: np.ndarray,
    offline_solid: np.ndarray,
    signed_distance: np.ndarray,
    tclb_boundary: np.ndarray,
) -> dict[str, np.ndarray]:
    tclb_fluid = ~tclb_boundary
    offline_fluid = ~offline_solid
    interface = offline_fluid & (phase > 0.05) & (phase < 0.95)
    tclb_interface = tclb_fluid & (phase > 0.05) & (phase < 0.95)
    near_wall = offline_fluid & (signed_distance >= 0.0) & (signed_distance <= 3.0)
    near_interface = near_wall & interface
    contact_core = offline_fluid & (signed_distance >= 0.0) & (signed_distance <= 1.5) & (phase > 0.2) & (phase < 0.8)
    tclb_near_interface = near_interface & tclb_fluid
    tclb_contact_core = contact_core & tclb_fluid
    offline_fluid_tclb_boundary = offline_fluid & tclb_boundary
    cylinder_overlap_boundary = offline_fluid_tclb_boundary & (signed_distance <= 3.0)
    outer_boundary = tclb_boundary & (signed_distance > 3.0)
    return {
        "all": np.ones_like(phase, dtype=bool),
        "offline_fluid": offline_fluid,
        "tclb_fluid": tclb_fluid,
        "interface_offline_fluid": interface,
        "interface_tclb_fluid": tclb_interface,
        "near_interface": near_interface,
        "near_interface_tclb_fluid": tclb_near_interface,
        "contact_core": contact_core,
        "contact_core_tclb_fluid": tclb_contact_core,
        "offline_fluid_tclb_boundary": offline_fluid_tclb_boundary,
        "cylinder_overlap_boundary": cylinder_overlap_boundary,
        "outer_boundary": outer_boundary,
    }


def nearest_boundary_distance_hist(
    signed_distance: np.ndarray,
    phase: np.ndarray,
    tclb_boundary: np.ndarray,
    out_csv: Path,
) -> list[dict[str, Any]]:
    bins = [(-10.0, -3.0), (-3.0, -1.0), (-1.0, 0.0), (0.0, 0.5), (0.5, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, 3.0), (3.0, 6.0), (6.0, 1000.0)]
    rows: list[dict[str, Any]] = []
    for lo, hi in bins:
        mask = tclb_boundary & (signed_distance >= lo) & (signed_distance < hi)
        row: dict[str, Any] = {
            "signed_distance_lo": lo,
            "signed_distance_hi": hi,
            "tclb_boundary_cells": int(np.count_nonzero(mask)),
        }
        if row["tclb_boundary_cells"]:
            row["phase_mean"] = float(np.mean(phase[mask]))
            row["phase_min"] = float(np.min(phase[mask]))
            row["phase_max"] = float(np.max(phase[mask]))
        rows.append(row)
    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=sorted({key for row in rows for key in row}))
        writer.writeheader()
        writer.writerows(rows)
    return rows


def write_operator_csv(comparisons: list[dict[str, Any]], out_csv: Path) -> None:
    rows: list[dict[str, Any]] = []
    for comp in comparisons:
        field = comp["field"]
        for region, payload in comp["regions"].items():
            row: dict[str, Any] = {"field": field, "region": region}
            for prefix in ("candidate", "reference", "diff"):
                for key, value in payload[prefix].items():
                    row[f"{prefix}_{key}"] = value
            rows.append(row)
    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=sorted({key for row in rows for key in row}))
        writer.writeheader()
        writer.writerows(rows)


def classify(result: dict[str, Any]) -> dict[str, Any]:
    mask_summary = result["mask_summary"]
    operator = result["operator_summary"]
    current_periodic_mu = operator["current_vs_periodic_mu_near_interface_tclb_fluid_max_abs"]
    current_center_mu = operator["current_vs_center_boundary_mu_near_interface_tclb_fluid_max_abs"]
    ghost_delta_mu = operator["b13_ghost_delta_mu_near_interface_tclb_fluid_max_abs"]
    offline_fluid_boundary = mask_summary["offline_fluid_tclb_boundary_cells"]
    outer_boundary = mask_summary["outer_boundary_cells"]
    cylinder_overlap = mask_summary["cylinder_overlap_boundary_cells"]

    if (
        ghost_delta_mu is not None
        and ghost_delta_mu < 1.0e-14
        and current_periodic_mu is not None
        and current_periodic_mu < 1.0e-14
    ):
        primary = "tclb_replay_matches_periodic_stencil_on_tclb_phase"
    elif ghost_delta_mu is not None and ghost_delta_mu < 1.0e-14 and current_center_mu is not None:
        primary = "boundary_semantics_not_wallghost_value"
    else:
        primary = "wallghost_delta_or_missing_fields_need_followup"

    if offline_fluid_boundary > 0 and outer_boundary >= offline_fluid_boundary * 0.5:
        mask_note = "offline mask does not include TCLB outer/domain walls; boundary mismatch is dominated by non-cylinder walls"
    elif cylinder_overlap > 0:
        mask_note = "offline/TCLB cylinder-wall classification differs near the solid"
    else:
        mask_note = "mask mismatch is small or not localized by current bins"

    return {
        "status": "b14_mask_operator_equivalence_complete",
        "primary_result": primary,
        "claim_limit": "offline mask/operator audit only; not contact-angle validation",
        "mask_note": mask_note,
        "next_gate": "If B14 shows offline operator mismatch, update B10/B11 offline reconstruction to TCLB-compatible stencil/mask before changing solver physics.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--vti0", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--coord-mode", default="cell_center", choices=["cell_center", "node"])
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    params = parse_case_xml(args.case)
    offline_phase, offline_solid, signed_distance, _y, _z = reconstruct_cylinder_cap(params, args.coord_mode)
    dims, arrays = load_vti(args.vti0)
    expected_shape = (dims[2], dims[1], dims[0])
    if offline_phase.shape != expected_shape:
        raise ValueError(f"offline shape {offline_phase.shape} != VTI shape {expected_shape}")

    tclb_phase = reshape_scalar(arrays, "PhaseField", dims)
    if tclb_phase is None:
        raise ValueError("PhaseField missing from VTI")
    boundary_raw = arrays.get("IsItBoundary", arrays.get("BOUNDARY"))
    if boundary_raw is None:
        raise ValueError("IsItBoundary/BOUNDARY missing from VTI")
    tclb_boundary = np.asarray(boundary_raw, dtype=float).reshape(expected_shape) > 0.5
    masks = build_masks(tclb_phase, offline_solid, signed_distance, tclb_boundary)

    current_lap = reshape_scalar(arrays, "InitialReplayLapPhi", dims)
    current_mu = reshape_scalar(arrays, "InitialReplayMu", dims)
    no_ghost_lap = reshape_scalar(arrays, "InitialNoGhostReplayLapPhi", dims)
    no_ghost_mu = reshape_scalar(arrays, "InitialNoGhostReplayMu", dims)
    ghost_delta_mu = reshape_scalar(arrays, "InitialGhostDeltaMu", dims)
    ghost_delta_lap = reshape_scalar(arrays, "InitialGhostDeltaLapPhi", dims)
    wallghost_used = reshape_scalar(arrays, "InitialReplayWallGhostUsed", dims)
    ghost_neighbor_count = reshape_scalar(arrays, "InitialGhostNeighborCount", dims)
    no_ghost_fallback = reshape_scalar(arrays, "InitialNoGhostPhaseStencilFallbackCount", dims)

    periodic_lap, periodic_boundary_slots, _periodic_fallback = laplace_with_boundary_semantics(tclb_phase, tclb_boundary, "periodic")
    center_boundary_lap, center_boundary_slots, center_boundary_fallback = laplace_with_boundary_semantics(tclb_phase, tclb_boundary, "center_on_boundary")
    midpoint_boundary_lap, midpoint_boundary_slots, midpoint_boundary_fallback = laplace_with_boundary_semantics(tclb_phase, tclb_boundary, "midpoint_on_boundary")
    periodic_mu = chemical_potential(params, tclb_phase, periodic_lap)
    center_boundary_mu = chemical_potential(params, tclb_phase, center_boundary_lap)
    midpoint_boundary_mu = chemical_potential(params, tclb_phase, midpoint_boundary_lap)

    comparisons: list[dict[str, Any]] = []
    if current_lap is not None:
        comparisons.extend(
            [
                compare_stats("current_lap_vs_periodic", current_lap, periodic_lap, masks),
                compare_stats("current_lap_vs_center_boundary", current_lap, center_boundary_lap, masks),
                compare_stats("current_lap_vs_midpoint_boundary", current_lap, midpoint_boundary_lap, masks),
            ]
        )
    if current_mu is not None:
        comparisons.extend(
            [
                compare_stats("current_mu_vs_periodic", current_mu, periodic_mu, masks),
                compare_stats("current_mu_vs_center_boundary", current_mu, center_boundary_mu, masks),
                compare_stats("current_mu_vs_midpoint_boundary", current_mu, midpoint_boundary_mu, masks),
            ]
        )
    if no_ghost_mu is not None:
        comparisons.extend(
            [
                compare_stats("no_ghost_mu_vs_periodic", no_ghost_mu, periodic_mu, masks),
                compare_stats("no_ghost_mu_vs_center_boundary", no_ghost_mu, center_boundary_mu, masks),
            ]
        )

    write_operator_csv(comparisons, args.out / "operator_comparison.csv")
    boundary_hist = nearest_boundary_distance_hist(signed_distance, tclb_phase, tclb_boundary, args.out / "boundary_distance_hist.csv")

    diagnostic_fields = [
        region_field_stats("InitialGhostDeltaMu", ghost_delta_mu, masks),
        region_field_stats("InitialGhostDeltaLapPhi", ghost_delta_lap, masks),
        region_field_stats("InitialReplayWallGhostUsed", wallghost_used, masks),
        region_field_stats("InitialGhostNeighborCount", ghost_neighbor_count, masks),
        region_field_stats("InitialNoGhostPhaseStencilFallbackCount", no_ghost_fallback, masks),
        region_field_stats("periodic_boundary_slots", periodic_boundary_slots, masks),
        region_field_stats("center_boundary_slots", center_boundary_slots, masks),
        region_field_stats("center_boundary_fallback", center_boundary_fallback, masks),
        region_field_stats("midpoint_boundary_slots", midpoint_boundary_slots, masks),
        region_field_stats("midpoint_boundary_fallback", midpoint_boundary_fallback, masks),
    ]

    def diff_max(field: str, region: str) -> float | None:
        for comp in comparisons:
            if comp["field"] == field:
                return comp["regions"][region]["diff"].get("max_abs")
        return None

    def field_max(field_name: str, region: str) -> float | None:
        for field in diagnostic_fields:
            if field["field"] == field_name and field.get("present"):
                return field["regions"][region].get("max_abs")
        return None

    mask_summary = {
        "total_cells": int(tclb_phase.size),
        "tclb_boundary_cells": int(np.count_nonzero(tclb_boundary)),
        "offline_solid_cells": int(np.count_nonzero(offline_solid)),
        "offline_fluid_tclb_boundary_cells": int(np.count_nonzero(masks["offline_fluid_tclb_boundary"])),
        "offline_solid_tclb_fluid_cells": int(np.count_nonzero(offline_solid & (~tclb_boundary))),
        "outer_boundary_cells": int(np.count_nonzero(masks["outer_boundary"])),
        "cylinder_overlap_boundary_cells": int(np.count_nonzero(masks["cylinder_overlap_boundary"])),
        "near_interface_tclb_fluid_cells": int(np.count_nonzero(masks["near_interface_tclb_fluid"])),
        "contact_core_tclb_fluid_cells": int(np.count_nonzero(masks["contact_core_tclb_fluid"])),
    }
    operator_summary = {
        "current_vs_periodic_mu_near_interface_tclb_fluid_max_abs": diff_max("current_mu_vs_periodic", "near_interface_tclb_fluid"),
        "current_vs_center_boundary_mu_near_interface_tclb_fluid_max_abs": diff_max("current_mu_vs_center_boundary", "near_interface_tclb_fluid"),
        "current_vs_midpoint_boundary_mu_near_interface_tclb_fluid_max_abs": diff_max("current_mu_vs_midpoint_boundary", "near_interface_tclb_fluid"),
        "current_vs_periodic_lap_near_interface_tclb_fluid_max_abs": diff_max("current_lap_vs_periodic", "near_interface_tclb_fluid"),
        "current_vs_center_boundary_lap_near_interface_tclb_fluid_max_abs": diff_max("current_lap_vs_center_boundary", "near_interface_tclb_fluid"),
        "b13_ghost_delta_mu_near_interface_tclb_fluid_max_abs": field_max("InitialGhostDeltaMu", "near_interface_tclb_fluid"),
        "b13_ghost_delta_lap_near_interface_tclb_fluid_max_abs": field_max("InitialGhostDeltaLapPhi", "near_interface_tclb_fluid"),
        "wallghost_used_near_interface_tclb_fluid_max_abs": field_max("InitialReplayWallGhostUsed", "near_interface_tclb_fluid"),
        "ghost_neighbor_count_near_interface_tclb_fluid_max_abs": field_max("InitialGhostNeighborCount", "near_interface_tclb_fluid"),
        "periodic_boundary_slots_near_interface_tclb_fluid_max_abs": field_max("periodic_boundary_slots", "near_interface_tclb_fluid"),
        "center_boundary_slots_near_interface_tclb_fluid_max_abs": field_max("center_boundary_slots", "near_interface_tclb_fluid"),
    }

    result: dict[str, Any] = {
        "case_xml": str(args.case),
        "vti0": str(args.vti0),
        "coord_mode": args.coord_mode,
        "claim_limit": "offline mask/operator equivalence audit only; not contact-angle validation",
        "mask_summary": mask_summary,
        "operator_summary": operator_summary,
        "boundary_distance_hist": boundary_hist,
        "diagnostic_fields": diagnostic_fields,
        "operator_comparisons": comparisons,
    }
    result["classification"] = classify(result)
    (args.out / "b14_mask_operator_equivalence.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (args.out / "b14_key_summary.json").write_text(
        json.dumps(
            {
                "status": result["classification"]["status"],
                "primary_result": result["classification"]["primary_result"],
                "claim_limit": result["classification"]["claim_limit"],
                "mask_summary": mask_summary,
                "operator_summary": operator_summary,
                "mask_note": result["classification"]["mask_note"],
                "next_gate": result["classification"]["next_gate"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps(result["classification"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
