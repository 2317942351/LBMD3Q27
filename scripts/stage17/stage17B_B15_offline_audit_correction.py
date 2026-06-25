#!/usr/bin/env python3
"""Stage17B-B15 corrected offline-audit mask analysis.

B14 showed TCLB InitialReplayMu/LapPhi match a periodic D3Q27 stencil when the
stencil is applied to TCLB's own PhaseField and the comparison region is
restricted to TCLB fluid nodes.  This script quantifies why the older B10/B11
offline comparison looked wrong: it mixed offline-fluid masks with TCLB
boundary cells.

This script is read-only and does not validate contact angle.
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
    chemical_potential,
    laplace_d3q27_periodic,
    parse_case_xml,
    reconstruct_cylinder_cap,
)
from stage17B_B11_replay_compare import load_vti, reshape_scalar, stats  # noqa: E402


def compare_region(
    name: str,
    candidate: np.ndarray,
    reference: np.ndarray,
    mask: np.ndarray,
) -> dict[str, Any]:
    diff = candidate - reference
    return {
        "region": name,
        "cell_count": int(np.count_nonzero(mask)),
        "candidate": stats(candidate[mask]),
        "reference": stats(reference[mask]),
        "diff": stats(diff[mask]),
    }


def write_rows(rows: list[dict[str, Any]], out_csv: Path) -> None:
    flat_rows: list[dict[str, Any]] = []
    for row in rows:
        flat: dict[str, Any] = {"region": row["region"], "cell_count": row["cell_count"]}
        for prefix in ("candidate", "reference", "diff"):
            for key, value in row[prefix].items():
                flat[f"{prefix}_{key}"] = value
        flat_rows.append(flat)
    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=sorted({key for row in flat_rows for key in row}))
        writer.writeheader()
        writer.writerows(flat_rows)


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
    shape = (dims[2], dims[1], dims[0])
    if offline_phase.shape != shape:
        raise ValueError(f"offline shape {offline_phase.shape} != VTI shape {shape}")

    tclb_phase = reshape_scalar(arrays, "PhaseField", dims)
    current_mu = reshape_scalar(arrays, "InitialReplayMu", dims)
    current_lap = reshape_scalar(arrays, "InitialReplayLapPhi", dims)
    if tclb_phase is None or current_mu is None or current_lap is None:
        raise ValueError("B15 requires PhaseField, InitialReplayMu, and InitialReplayLapPhi")
    boundary_raw = arrays.get("IsItBoundary", arrays.get("BOUNDARY"))
    if boundary_raw is None:
        raise ValueError("B15 requires IsItBoundary or BOUNDARY")
    tclb_boundary = np.asarray(boundary_raw, dtype=float).reshape(shape) > 0.5
    tclb_fluid = ~tclb_boundary
    offline_fluid = ~offline_solid
    phase_interface = (tclb_phase > 0.05) & (tclb_phase < 0.95)
    near_wall = (signed_distance >= 0.0) & (signed_distance <= 3.0)
    contact_band = (signed_distance >= 0.0) & (signed_distance <= 1.5) & (tclb_phase > 0.2) & (tclb_phase < 0.8)

    tclb_lap_periodic = laplace_d3q27_periodic(tclb_phase)
    tclb_mu_periodic = chemical_potential(params, tclb_phase, tclb_lap_periodic)
    offline_lap_periodic = laplace_d3q27_periodic(offline_phase)
    offline_mu_periodic = chemical_potential(params, offline_phase, offline_lap_periodic)

    masks = {
        "b10_near_interface_offline_fluid": offline_fluid & near_wall & phase_interface,
        "b11_near_interface_tclb_fluid": offline_fluid & tclb_fluid & near_wall & phase_interface,
        "corrected_near_interface_tclb_phase_fluid": tclb_fluid & near_wall & phase_interface,
        "b10_contact_core_offline_fluid": offline_fluid & contact_band,
        "b11_contact_core_tclb_fluid": offline_fluid & tclb_fluid & contact_band,
        "corrected_contact_core_tclb_phase_fluid": tclb_fluid & contact_band,
        "offline_fluid_tclb_boundary": offline_fluid & tclb_boundary,
        "cylinder_overlap_boundary": offline_fluid & tclb_boundary & (signed_distance <= 3.0),
        "outer_boundary": tclb_boundary & (signed_distance > 3.0),
    }

    mu_rows = [
        compare_region(name, current_mu, tclb_mu_periodic, mask)
        for name, mask in masks.items()
    ]
    lap_rows = [
        compare_region(name, current_lap, tclb_lap_periodic, mask)
        for name, mask in masks.items()
    ]
    offline_reconstruction_rows = [
        compare_region(name, offline_mu_periodic, tclb_mu_periodic, mask)
        for name, mask in masks.items()
    ]

    write_rows(mu_rows, args.out / "current_vs_tclb_periodic_mu_by_region.csv")
    write_rows(lap_rows, args.out / "current_vs_tclb_periodic_lap_by_region.csv")
    write_rows(offline_reconstruction_rows, args.out / "offline_vs_tclb_phase_mu_by_region.csv")

    def row_lookup(rows: list[dict[str, Any]], region: str) -> dict[str, Any]:
        for row in rows:
            if row["region"] == region:
                return row
        raise KeyError(region)

    b10_mu = row_lookup(mu_rows, "b10_near_interface_offline_fluid")["diff"]["max_abs"]
    corrected_mu = row_lookup(mu_rows, "b11_near_interface_tclb_fluid")["diff"]["max_abs"]
    b10_lap = row_lookup(lap_rows, "b10_near_interface_offline_fluid")["diff"]["max_abs"]
    corrected_lap = row_lookup(lap_rows, "b11_near_interface_tclb_fluid")["diff"]["max_abs"]
    offline_phase_mu = row_lookup(offline_reconstruction_rows, "b11_near_interface_tclb_fluid")["diff"]["max_abs"]

    summary = {
        "status": "b15_offline_audit_correction_complete",
        "claim_limit": "offline comparison correction only; not contact-angle validation",
        "primary_result": "b10_b11_error_removed_by_tclb_fluid_mask_and_tclb_phase_reference"
        if corrected_mu is not None and corrected_mu < 1.0e-14
        else "corrected_mask_still_has_nonroundoff_error",
        "key_metrics": {
            "b10_near_interface_current_vs_tclb_periodic_mu_max_abs": b10_mu,
            "b11_tclb_fluid_current_vs_tclb_periodic_mu_max_abs": corrected_mu,
            "b10_near_interface_current_vs_tclb_periodic_lap_max_abs": b10_lap,
            "b11_tclb_fluid_current_vs_tclb_periodic_lap_max_abs": corrected_lap,
            "offline_phase_vs_tclb_phase_mu_near_interface_tclb_fluid_max_abs": offline_phase_mu,
            "offline_fluid_tclb_boundary_cells": int(np.count_nonzero(masks["offline_fluid_tclb_boundary"])),
            "cylinder_overlap_boundary_cells": int(np.count_nonzero(masks["cylinder_overlap_boundary"])),
            "outer_boundary_cells": int(np.count_nonzero(masks["outer_boundary"])),
        },
        "interpretation": [
            "TCLB InitialReplayMu/LapPhi matches a periodic D3Q27 stencil applied to TCLB PhaseField on TCLB fluid nodes.",
            "The old B10-style offline-fluid mask included TCLB boundary nodes, which created apparent large errors.",
            "Remaining offline-vs-TCLB differences should be audited as reconstruction/mask issues before any solver physics change.",
        ],
        "next_gate": "Patch B10/B11 reports or add a corrected comparison mode so future gates default to TCLB-fluid masks and TCLB PhaseField reference.",
    }
    result = {
        "case_xml": str(args.case),
        "vti0": str(args.vti0),
        "coord_mode": args.coord_mode,
        "summary": summary,
        "mu_rows": mu_rows,
        "lap_rows": lap_rows,
        "offline_reconstruction_rows": offline_reconstruction_rows,
    }
    (args.out / "b15_offline_audit_correction.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (args.out / "b15_key_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
