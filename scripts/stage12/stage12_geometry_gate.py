#!/usr/bin/env python3
"""Verify Stage12 solid/fluid domain assignment against analytic geometry.

The gate is intentionally geometric, not a contact-angle validation.  It checks
that TCLB's boundary mask agrees with the declared cylinder/sphere signed
distance away from the triangulated surface, and that the droplet centre starts
in the fluid domain.  It uses IsItBoundary when present; BOUNDARY is only a
fallback because in this TCLB model it is a node-type bit field, not a clean
0/1 diagnostic quantity.

Usage:
  python3 stage12_geometry_gate.py <vti> <cylinder|sphere> \
      <cx> <cy> <cz> <R_solid> <drop_x> <drop_y> <drop_z>
"""
import json
import math
import sys

import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy


def fail(message, payload):
    payload["status"] = "FAIL"
    payload["message"] = message
    print(json.dumps(payload, indent=2, sort_keys=True))
    sys.exit(1)


def phase_stats(phase, mask):
    values = phase[mask & np.isfinite(phase)]
    if values.size == 0:
        return {"cells": 0, "min": math.nan, "max": math.nan}
    return {
        "cells": int(values.size),
        "min": float(values.min()),
        "max": float(values.max()),
    }


def out_of_range_count(phase, mask, lo=-0.1, hi=1.1):
    values = phase[mask & np.isfinite(phase)]
    if values.size == 0:
        return 0
    return int(((values < lo) | (values > hi)).sum())


def outlier_samples(phase, signed_distance, boundary, mask, max_samples=8):
    bad = mask & np.isfinite(phase) & ((phase < -0.1) | (phase > 1.1))
    coords = np.argwhere(bad)
    if coords.size == 0:
        return []

    values = phase[bad]
    order = np.argsort(np.abs(values - 0.5))[::-1][:max_samples]
    samples = []
    for row in order:
        z, y, x = coords[row]
        samples.append({
            "index": [int(x), int(y), int(z)],
            "phase": float(phase[z, y, x]),
            "signed_distance": float(signed_distance[z, y, x]),
            "boundary": float(boundary[z, y, x]),
        })
    return samples


def main():
    if len(sys.argv) != 10:
        raise SystemExit(__doc__)

    vti, geom = sys.argv[1], sys.argv[2]
    cx, cy, cz = (float(x) for x in sys.argv[3:6])
    radius = float(sys.argv[6])
    drop_x, drop_y, drop_z = (float(x) for x in sys.argv[7:10])

    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(vti)
    reader.Update()
    data = reader.GetOutput()
    dims = data.GetDimensions()
    nx, ny, nz = dims[0] - 1, dims[1] - 1, dims[2] - 1

    cell_data = data.GetCellData()
    phase = vtk_to_numpy(cell_data.GetArray("PhaseField")).copy()
    boundary_arr = cell_data.GetArray("IsItBoundary")
    boundary_source = "IsItBoundary"
    if boundary_arr is None:
        boundary_arr = cell_data.GetArray("BOUNDARY")
        boundary_source = "BOUNDARY"
    if boundary_arr is None:
        raise RuntimeError("neither IsItBoundary nor BOUNDARY exists in VTI")
    boundary = vtk_to_numpy(boundary_arr).copy()
    analytic_arr = cell_data.GetArray("AnalyticFlag")
    analytic = vtk_to_numpy(analytic_arr).copy() if analytic_arr is not None else None

    phase3 = phase.reshape((nz, ny, nx))
    bd3 = boundary.reshape((nz, ny, nx))
    af3 = analytic.reshape((nz, ny, nx)) if analytic is not None else None

    iz, iy, ix = np.indices((nz, ny, nx), dtype=float)
    if geom == "cylinder":
        signed_distance = np.sqrt((iy - cy) ** 2 + (iz - cz) ** 2) - radius
    elif geom == "sphere":
        signed_distance = np.sqrt((ix - cx) ** 2 + (iy - cy) ** 2 + (iz - cz) ** 2) - radius
    else:
        raise SystemExit(f"unknown geometry: {geom}")

    # Exclude outer-domain walls from the analytic-object checks. TCLB keeps
    # some outer-domain finite-difference artefacts in the fluid mask; those
    # are reported separately so they cannot hide object-domain regressions.
    interior = (
        (ix > 1) & (ix < nx - 2) &
        (iy > 1) & (iy < ny - 2) &
        (iz > 1) & (iz < nz - 2)
    )
    outer_domain = ~interior
    inside_core = interior & (signed_distance < -2.0)
    outside_far = interior & (signed_distance > 2.0)
    near_surface = interior & (np.abs(signed_distance) <= 1.5)
    object_near_fluid = interior & (bd3 < 0.5) & (np.abs(signed_distance) <= 3.0)
    object_band_fluid = interior & (bd3 < 0.5) & (signed_distance > -2.0) & (signed_distance < 8.0)
    far_field_fluid = interior & (bd3 < 0.5) & (signed_distance >= 8.0)
    outer_fluid = outer_domain & (bd3 < 0.5)

    if not inside_core.any():
        raise RuntimeError("inside_core mask is empty; check geometry parameters")
    if not outside_far.any():
        raise RuntimeError("outside_far mask is empty; check geometry parameters")

    inside_solid_fraction = float((bd3[inside_core] > 0.5).mean())
    outside_fluid_fraction = float((bd3[outside_far] < 0.5).mean())
    nonfinite_phase = int((~np.isfinite(phase3)).sum())
    fluid_mask = bd3 < 0.5

    dx_i = int(round(drop_x))
    dy_i = int(round(drop_y))
    dz_i = int(round(drop_z))
    drop_in_bounds = (0 <= dx_i < nx) and (0 <= dy_i < ny) and (0 <= dz_i < nz)
    if drop_in_bounds:
        drop_boundary = float(bd3[dz_i, dy_i, dx_i])
        drop_phase = float(phase3[dz_i, dy_i, dx_i])
        drop_is_fluid = bool(drop_boundary < 0.5)
    else:
        drop_boundary = math.nan
        drop_phase = math.nan
        drop_is_fluid = False

    analytic_count = int((af3[near_surface] > 0.5).sum()) if af3 is not None else None
    object_near_phase = phase_stats(phase3, object_near_fluid)
    object_band_phase = phase_stats(phase3, object_band_fluid)
    phase_ranges = {
        "fluid_global": phase_stats(phase3, fluid_mask),
        "fluid_outer_domain": phase_stats(phase3, outer_fluid),
        "fluid_interior_far_from_object": phase_stats(phase3, far_field_fluid),
        "fluid_object_band_sd_minus2_to_8": object_band_phase,
        "fluid_object_near_surface_abs_sd_le_3": object_near_phase,
    }
    phase_out_of_range_counts = {
        "fluid_global": out_of_range_count(phase3, fluid_mask),
        "fluid_outer_domain": out_of_range_count(phase3, outer_fluid),
        "fluid_interior_far_from_object": out_of_range_count(phase3, far_field_fluid),
        "fluid_object_band_sd_minus2_to_8": out_of_range_count(phase3, object_band_fluid),
        "fluid_object_near_surface_abs_sd_le_3": out_of_range_count(phase3, object_near_fluid),
    }

    payload = {
        "vti": vti,
        "geom": geom,
        "grid": [int(nx), int(ny), int(nz)],
        "center": [cx, cy, cz],
        "radius": radius,
        "boundary_source": boundary_source,
        "inside_core_cells": int(inside_core.sum()),
        "outside_far_cells": int(outside_far.sum()),
        "inside_solid_fraction": inside_solid_fraction,
        "outside_fluid_fraction": outside_fluid_fraction,
        "nonfinite_phase": nonfinite_phase,
        "phase_ranges": phase_ranges,
        "phase_out_of_range_counts": phase_out_of_range_counts,
        "global_phase_outlier_samples": outlier_samples(
            phase3, signed_distance, bd3, fluid_mask
        ),
        "droplet_center_index": [dx_i, dy_i, dz_i],
        "droplet_center_boundary": drop_boundary,
        "droplet_center_phase": drop_phase,
        "droplet_center_is_fluid": drop_is_fluid,
        "near_surface_analytic_flag_count": analytic_count,
        "warnings": [],
    }

    if nonfinite_phase:
        fail("PhaseField contains non-finite values", payload)
    if inside_solid_fraction < 0.98:
        fail("analytic solid interior is not marked solid", payload)
    if outside_fluid_fraction < 0.98:
        fail("analytic exterior is not marked fluid", payload)
    if not drop_is_fluid:
        fail("droplet center is not in fluid domain", payload)
    if phase_out_of_range_counts["fluid_object_near_surface_abs_sd_le_3"]:
        fail("object near-surface fluid PhaseField is outside the expected range", payload)
    if phase_out_of_range_counts["fluid_object_band_sd_minus2_to_8"]:
        fail("object-band fluid PhaseField is outside the expected range", payload)
    if phase_out_of_range_counts["fluid_global"]:
        payload["warnings"].append(
            "global fluid PhaseField has out-of-range values away from the analytic object"
        )

    payload["status"] = "PASS"
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
