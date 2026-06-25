#!/usr/bin/env python3
"""Offline Stage17B-B10 audit for the initial cylinder-cap phase field.

This script does not run TCLB and does not validate a contact angle.  It
reconstructs the TCLB CylinderCapInit field from a case.xml file and evaluates
the same D3Q27 isotropic gradient/Laplace closure used by calcMu.  The purpose
is to test whether the initial cap is already a discrete non-equilibrium state
near the curved wall.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


PHASE_L = 0.0
PHASE_H = 1.0
LAPLACE_FACE_WEIGHT = 16.0
LAPLACE_EDGE_WEIGHT = 4.0
LAPLACE_CORNER_WEIGHT = 1.0
LAPLACE_CENTER_WEIGHT = -152.0
LAPLACE_NORMALIZER = 36.0
GRAD_NORMALIZER = 72.0


@dataclass(frozen=True)
class CaseParams:
    nx: int
    ny: int
    nz: int
    density_l: float
    density_h: float
    sigma: float
    int_width: float
    cap_parent_radius: float
    cap_center: tuple[float, float, float]
    solid_center: tuple[float, float, float]
    solid_radius: float
    solid_axis: int
    rad_angle_deg: float


def _float_param(params: dict[str, str], name: str, default: float | None = None) -> float:
    if name not in params:
        if default is None:
            raise KeyError(f"Missing Param {name}")
        return default
    value = params[name].strip()
    if value.endswith("d"):
        value = value[:-1]
    return float(value)


def parse_case_xml(path: Path) -> CaseParams:
    tree = ET.parse(path)
    root = tree.getroot()
    geom = root.find("Geometry")
    if geom is None:
        raise ValueError(f"{path} has no Geometry node")
    params: dict[str, str] = {}
    model = root.find("Model")
    if model is None:
        raise ValueError(f"{path} has no Model node")
    for node in model.findall("Param"):
        name = node.attrib.get("name")
        value = node.attrib.get("value")
        zone = node.attrib.get("zone")
        if name and value is not None and zone is None:
            params[name] = value
    return CaseParams(
        nx=int(float(geom.attrib["nx"])),
        ny=int(float(geom.attrib["ny"])),
        nz=int(float(geom.attrib["nz"])),
        density_l=_float_param(params, "Density_l"),
        density_h=_float_param(params, "Density_h"),
        sigma=_float_param(params, "sigma"),
        int_width=_float_param(params, "IntWidth"),
        cap_parent_radius=_float_param(params, "CylinderCapInitParentRadius"),
        cap_center=(
            _float_param(params, "CylinderCapInitCenterX"),
            _float_param(params, "CylinderCapInitCenterY"),
            _float_param(params, "CylinderCapInitCenterZ"),
        ),
        solid_center=(
            _float_param(params, "CylinderCapInitSolidCenterX"),
            _float_param(params, "CylinderCapInitSolidCenterY"),
            _float_param(params, "CylinderCapInitSolidCenterZ"),
        ),
        solid_radius=_float_param(params, "CylinderCapInitSolidRadius"),
        solid_axis=int(round(_float_param(params, "CylinderCapInitSolidAxis"))),
        rad_angle_deg=_float_param(params, "radAngle", 90.0),
    )


def coordinate_arrays(params: CaseParams, mode: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if mode == "cell_center":
        offset = 0.5
    elif mode == "node":
        offset = 0.0
    else:
        raise ValueError(f"unknown coordinate mode {mode}")
    x = np.arange(params.nx, dtype=float)[None, None, :] + offset
    y = np.arange(params.ny, dtype=float)[None, :, None] + offset
    z = np.arange(params.nz, dtype=float)[:, None, None] + offset
    return x, y, z


def reconstruct_cylinder_cap(
    params: CaseParams,
    coord_mode: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    x, y, z = coordinate_arrays(params, coord_mode)
    cx, cy, cz = params.cap_center
    sx, sy, sz = params.solid_center
    ri = np.sqrt((x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2)
    dxs = x - sx
    dys = y - sy
    dzs = z - sz
    if params.solid_axis == 0:
        radial = np.sqrt(dys * dys + dzs * dzs)
    elif params.solid_axis == 1:
        radial = np.sqrt(dxs * dxs + dzs * dzs)
    else:
        radial = np.sqrt(dxs * dxs + dys * dys)
    signed_distance = np.broadcast_to(radial - params.solid_radius, (params.nz, params.ny, params.nx))
    solid = signed_distance < 0.0
    cap_pf = PHASE_L + 0.5 * (PHASE_H - PHASE_L) * (
        1.0 - np.tanh(2.0 * (ri - params.cap_parent_radius) / params.int_width)
    )
    phase = np.where(solid, PHASE_L, cap_pf)
    y_full = np.broadcast_to(y, phase.shape)
    z_full = np.broadcast_to(z, phase.shape)
    return phase.astype(float), solid, signed_distance, y_full, z_full


def sample(arr: np.ndarray, dx: int, dy: int, dz: int) -> np.ndarray:
    """Periodic sample matching TCLB field(dx,dy,dz) neighbor semantics."""
    return np.roll(np.roll(np.roll(arr, -dz, axis=0), -dy, axis=1), -dx, axis=2)


def laplace_d3q27_periodic(phase: np.ndarray) -> np.ndarray:
    out = LAPLACE_CENTER_WEIGHT * phase.copy()
    for dx, dy, dz in neighbor_offsets():
        weight = stencil_weight(dx, dy, dz)
        out += weight * sample(phase, dx, dy, dz)
    return out / LAPLACE_NORMALIZER


def grad_d3q27_periodic(phase: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    gx = np.zeros_like(phase)
    gy = np.zeros_like(phase)
    gz = np.zeros_like(phase)
    for dx, dy, dz in neighbor_offsets():
        weight = stencil_weight(dx, dy, dz)
        shifted = sample(phase, dx, dy, dz)
        gx += weight * dx * shifted
        gy += weight * dy * shifted
        gz += weight * dz * shifted
    return gx / GRAD_NORMALIZER, gy / GRAD_NORMALIZER, gz / GRAD_NORMALIZER


def neighbor_offsets() -> list[tuple[int, int, int]]:
    return [
        (dx, dy, dz)
        for dz in (-1, 0, 1)
        for dy in (-1, 0, 1)
        for dx in (-1, 0, 1)
        if not (dx == 0 and dy == 0 and dz == 0)
    ]


def stencil_weight(dx: int, dy: int, dz: int) -> float:
    nnz = int(dx != 0) + int(dy != 0) + int(dz != 0)
    if nnz == 1:
        return LAPLACE_FACE_WEIGHT
    if nnz == 2:
        return LAPLACE_EDGE_WEIGHT
    if nnz == 3:
        return LAPLACE_CORNER_WEIGHT
    raise ValueError((dx, dy, dz))


def chemical_potential(params: CaseParams, phase: np.ndarray, lap: np.ndarray) -> np.ndarray:
    pfavg = 0.5 * (PHASE_L + PHASE_H)
    bulk = 4.0 * (12.0 * params.sigma / params.int_width) * (phase - PHASE_L) * (phase - PHASE_H) * (phase - pfavg)
    capillary = (1.5 * params.sigma * params.int_width) * lap
    return bulk - capillary


def finite_stats(values: np.ndarray) -> dict[str, Any]:
    vals = np.asarray(values, dtype=float).ravel()
    finite = np.isfinite(vals)
    out: dict[str, Any] = {"count": int(vals.size), "nonfinite": int(vals.size - np.count_nonzero(finite))}
    vals = vals[finite]
    if vals.size == 0:
        out.update({"min": None, "max": None, "mean": None, "std": None, "p95_abs": None, "max_abs": None})
        return out
    out.update(
        {
            "min": float(np.min(vals)),
            "max": float(np.max(vals)),
            "mean": float(np.mean(vals)),
            "std": float(np.std(vals)),
            "p95_abs": float(np.percentile(np.abs(vals), 95.0)),
            "max_abs": float(np.max(np.abs(vals))),
        }
    )
    return out


def summarize_region(
    name: str,
    mask: np.ndarray,
    phase: np.ndarray,
    lap: np.ndarray,
    grad_mag: np.ndarray,
    mu: np.ndarray,
) -> dict[str, Any]:
    count = int(np.count_nonzero(mask))
    out: dict[str, Any] = {"region": name, "cell_count": count}
    if count == 0:
        out.update({"phase": finite_stats(np.array([])), "laplace": finite_stats(np.array([])), "grad_mag": finite_stats(np.array([])), "mu": finite_stats(np.array([]))})
        return out
    mu_values = mu[mask]
    mu_mean = float(np.mean(mu_values[np.isfinite(mu_values)])) if np.count_nonzero(np.isfinite(mu_values)) else float("nan")
    out.update(
        {
            "phase": finite_stats(phase[mask]),
            "laplace": finite_stats(lap[mask]),
            "grad_mag": finite_stats(grad_mag[mask]),
            "mu": finite_stats(mu_values),
            "mu_deviation_from_region_mean": finite_stats(mu_values - mu_mean),
        }
    )
    return out


def radial_profiles(
    signed_distance: np.ndarray,
    phase: np.ndarray,
    mu: np.ndarray,
    grad_mag: np.ndarray,
    solid: np.ndarray,
    out_csv: Path,
) -> list[dict[str, Any]]:
    fluid = ~solid
    bins = np.arange(0.0, 12.5, 0.5)
    rows: list[dict[str, Any]] = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = fluid & (signed_distance >= lo) & (signed_distance < hi)
        row: dict[str, Any] = {"sd_lo": float(lo), "sd_hi": float(hi), "cell_count": int(np.count_nonzero(mask))}
        if row["cell_count"]:
            for name, arr in [("phase", phase), ("mu", mu), ("grad_mag", grad_mag)]:
                vals = arr[mask]
                row[f"{name}_mean"] = float(np.mean(vals))
                row[f"{name}_std"] = float(np.std(vals))
                row[f"{name}_max_abs"] = float(np.max(np.abs(vals)))
        rows.append(row)
    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=sorted({key for row in rows for key in row}))
        writer.writeheader()
        writer.writerows(rows)
    return rows


def angle_profiles(
    phase: np.ndarray,
    mu: np.ndarray,
    grad_mag: np.ndarray,
    signed_distance: np.ndarray,
    solid: np.ndarray,
    params: CaseParams,
    coord_mode: str,
    out_csv: Path,
) -> list[dict[str, Any]]:
    x, y, _z = coordinate_arrays(params, coord_mode)
    sx, sy, _sz = params.solid_center
    alpha = np.degrees(np.arctan2(np.broadcast_to(x - sx, phase.shape), np.broadcast_to(y - sy, phase.shape)))
    contact = (~solid) & (signed_distance >= 0.0) & (signed_distance <= 3.0) & (phase > 0.05) & (phase < 0.95)
    bins = np.arange(-180.0, 181.0, 10.0)
    rows: list[dict[str, Any]] = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = contact & (alpha >= lo) & (alpha < hi)
        row: dict[str, Any] = {"angle_lo_deg": float(lo), "angle_hi_deg": float(hi), "cell_count": int(np.count_nonzero(mask))}
        if row["cell_count"]:
            row["phase_mean"] = float(np.mean(phase[mask]))
            row["mu_mean"] = float(np.mean(mu[mask]))
            row["mu_std"] = float(np.std(mu[mask]))
            row["mu_max_abs"] = float(np.max(np.abs(mu[mask])))
            row["grad_mag_mean"] = float(np.mean(grad_mag[mask]))
        rows.append(row)
    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=sorted({key for row in rows for key in row}))
        writer.writeheader()
        writer.writerows(rows)
    return rows


def plot_midplane(
    phase: np.ndarray,
    solid: np.ndarray,
    mu: np.ndarray,
    grad_mag: np.ndarray,
    signed_distance: np.ndarray,
    params: CaseParams,
    coord_mode: str,
    out_png: Path,
) -> None:
    iz = int(np.clip(round(params.solid_center[2] - (0.5 if coord_mode == "cell_center" else 0.0)), 0, params.nz - 1))
    phase2 = np.where(solid[iz], np.nan, phase[iz])
    mu2 = np.where(solid[iz], np.nan, mu[iz])
    grad2 = np.where(solid[iz], np.nan, grad_mag[iz])
    sd2 = signed_distance[iz]
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.2), constrained_layout=True)
    panels = [
        (phase2, "Initial phase", "viridis"),
        (mu2, "Discrete chemical potential", "coolwarm"),
        (grad2, "|grad phi|", "magma"),
    ]
    for ax, (data, title, cmap) in zip(axes, panels):
        im = ax.imshow(data, origin="lower", cmap=cmap)
        ax.contour(sd2, levels=[0.0, 3.0], colors=["white", "cyan"], linewidths=[1.0, 0.6])
        ax.contour(phase2, levels=[0.05, 0.5, 0.95], colors=["black", "white", "black"], linewidths=[0.5, 1.0, 0.5])
        ax.set_title(title)
        ax.set_xlabel("x index")
        ax.set_ylabel("y index")
        fig.colorbar(im, ax=ax, shrink=0.82)
    fig.suptitle(f"B10 offline initial cylinder-cap audit ({coord_mode}, z slice {iz})")
    fig.savefig(out_png, dpi=180)
    plt.close(fig)


def plot_histograms(mu: np.ndarray, grad_mag: np.ndarray, masks: dict[str, np.ndarray], out_png: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.0), constrained_layout=True)
    for name, mask in masks.items():
        vals = mu[mask]
        vals = vals[np.isfinite(vals)]
        if vals.size:
            axes[0].hist(vals, bins=80, histtype="step", linewidth=1.2, label=name)
    axes[0].set_title("mu distribution")
    axes[0].set_xlabel("mu")
    axes[0].set_ylabel("cells")
    axes[0].legend(fontsize=8)
    for name, mask in masks.items():
        vals = grad_mag[mask]
        vals = vals[np.isfinite(vals)]
        if vals.size:
            axes[1].hist(vals, bins=80, histtype="step", linewidth=1.2, label=name)
    axes[1].set_title("|grad phi| distribution")
    axes[1].set_xlabel("|grad phi|")
    axes[1].legend(fontsize=8)
    fig.savefig(out_png, dpi=180)
    plt.close(fig)


def run_mode(params: CaseParams, coord_mode: str, out_dir: Path) -> dict[str, Any]:
    phase, solid, signed_distance, _y, _z = reconstruct_cylinder_cap(params, coord_mode)
    lap = laplace_d3q27_periodic(phase)
    gx, gy, gz = grad_d3q27_periodic(phase)
    grad_mag = np.sqrt(gx * gx + gy * gy + gz * gz)
    mu = chemical_potential(params, phase, lap)
    fluid = ~solid
    interface = fluid & (phase > 0.05) & (phase < 0.95)
    near_wall = fluid & (signed_distance >= 0.0) & (signed_distance <= 3.0)
    near_interface = near_wall & interface
    contact_core = fluid & (signed_distance >= 0.0) & (signed_distance <= 1.5) & (phase > 0.2) & (phase < 0.8)
    bulk_liquid = fluid & (phase >= 0.99)
    bulk_gas = fluid & (phase <= 0.01)
    masks = {
        "fluid": fluid,
        "interface": interface,
        "near_wall": near_wall,
        "near_interface": near_interface,
        "contact_core": contact_core,
        "bulk_liquid": bulk_liquid,
        "bulk_gas": bulk_gas,
    }
    regions = {
        name: summarize_region(name, mask, phase, lap, grad_mag, mu)
        for name, mask in masks.items()
    }
    interface_mu = mu[interface]
    interface_mu_mean = float(np.mean(interface_mu[np.isfinite(interface_mu)])) if np.count_nonzero(interface) else None
    if interface_mu_mean is None:
        mu_dev = np.full_like(mu, np.nan)
    else:
        mu_dev = np.abs(mu - interface_mu_mean)
    max_mu_dev_idx = np.unravel_index(int(np.nanargmax(np.where(fluid, mu_dev, np.nan))), mu.shape)
    max_grad_idx = np.unravel_index(int(np.nanargmax(np.where(fluid, grad_mag, np.nan))), grad_mag.shape)
    radial_rows = radial_profiles(
        signed_distance,
        phase,
        mu,
        grad_mag,
        solid,
        out_dir / f"radial_profile_{coord_mode}.csv",
    )
    angle_rows = angle_profiles(
        phase,
        mu,
        grad_mag,
        signed_distance,
        solid,
        params,
        coord_mode,
        out_dir / f"contact_angle_profile_{coord_mode}.csv",
    )
    plot_midplane(
        phase,
        solid,
        mu,
        grad_mag,
        signed_distance,
        params,
        coord_mode,
        out_dir / f"midplane_phase_mu_grad_{coord_mode}.png",
    )
    plot_histograms(
        mu,
        grad_mag,
        {key: masks[key] for key in ("interface", "near_interface", "contact_core")},
        out_dir / f"mu_grad_hist_{coord_mode}.png",
    )
    return {
        "coord_mode": coord_mode,
        "regions": regions,
        "interface_mu_mean": interface_mu_mean,
        "max_abs_mu_deviation_from_interface_mean": None
        if interface_mu_mean is None
        else float(np.nanmax(np.where(fluid, mu_dev, np.nan))),
        "max_mu_deviation_location_zyx": [int(v) for v in max_mu_dev_idx],
        "max_mu_deviation_signed_distance": float(signed_distance[max_mu_dev_idx]),
        "max_mu_deviation_phase": float(phase[max_mu_dev_idx]),
        "max_mu_deviation_mu": float(mu[max_mu_dev_idx]),
        "max_grad_location_zyx": [int(v) for v in max_grad_idx],
        "max_grad_signed_distance": float(signed_distance[max_grad_idx]),
        "max_grad_phase": float(phase[max_grad_idx]),
        "max_grad_mu": float(mu[max_grad_idx]),
        "radial_profile_csv": f"radial_profile_{coord_mode}.csv",
        "contact_angle_profile_csv": f"contact_angle_profile_{coord_mode}.csv",
        "midplane_png": f"midplane_phase_mu_grad_{coord_mode}.png",
        "hist_png": f"mu_grad_hist_{coord_mode}.png",
        "radial_profile_preview": radial_rows[:8],
        "angle_nonempty_bins": int(sum(1 for row in angle_rows if int(row["cell_count"]) > 0)),
    }


def classify(mode_results: list[dict[str, Any]]) -> dict[str, Any]:
    preferred = next((item for item in mode_results if item["coord_mode"] == "cell_center"), mode_results[0])
    near_interface = preferred["regions"]["near_interface"]
    contact_core = preferred["regions"]["contact_core"]
    interface = preferred["regions"]["interface"]
    near_count = int(near_interface["cell_count"])
    contact_count = int(contact_core["cell_count"])
    mu_dev = preferred["max_abs_mu_deviation_from_interface_mean"]
    near_mu_std = near_interface["mu"].get("std")
    interface_mu_std = interface["mu"].get("std")
    contact_mu_max_abs = contact_core["mu"].get("max_abs")
    status = "b10_offline_initial_cap_audit_complete"
    if near_count == 0 or contact_count == 0:
        primary = "insufficient_nearwall_interface_cells"
    elif mu_dev is not None and near_mu_std is not None and interface_mu_std is not None and near_mu_std > 1.25 * max(interface_mu_std, 1.0e-20):
        primary = "initial_cap_nearwall_discrete_mu_nonuniformity"
    elif contact_mu_max_abs is not None and contact_mu_max_abs > 1.0e-6:
        primary = "initial_cap_contact_core_has_nonzero_mu"
    else:
        primary = "initial_cap_not_cleared_but_no_large_offline_mu_spike"
    return {
        "status": status,
        "claim_limit": "offline initial-condition audit only; not contact-angle validation",
        "primary_suspect": primary,
        "preferred_coord_mode": preferred["coord_mode"],
        "near_interface_cell_count": near_count,
        "contact_core_cell_count": contact_count,
        "max_abs_mu_deviation_from_interface_mean": mu_dev,
        "near_interface_mu_std": near_mu_std,
        "interface_mu_std": interface_mu_std,
        "contact_core_mu_max_abs": contact_mu_max_abs,
        "next_recommended_gate": "compare TCLB step-0/step-1 VTI PhaseField and ReplayMu against this offline reconstruction before changing solver physics",
    }


def write_region_csv(mode_results: list[dict[str, Any]], out_csv: Path) -> None:
    rows: list[dict[str, Any]] = []
    for result in mode_results:
        for region, payload in result["regions"].items():
            row: dict[str, Any] = {"coord_mode": result["coord_mode"], "region": region, "cell_count": payload["cell_count"]}
            for field in ("phase", "laplace", "grad_mag", "mu", "mu_deviation_from_region_mean"):
                for key, value in payload[field].items():
                    row[f"{field}_{key}"] = value
            rows.append(row)
    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=sorted({key for row in rows for key in row}))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=Path, required=True, help="B9/B17 case.xml containing CylinderCapInit parameters")
    parser.add_argument("--out", type=Path, required=True, help="Output artifact directory")
    parser.add_argument(
        "--coord-modes",
        default="cell_center,node",
        help="Comma-separated coordinate modes to audit: cell_center,node",
    )
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    params = parse_case_xml(args.case)
    modes = [item.strip() for item in args.coord_modes.split(",") if item.strip()]
    mode_results = [run_mode(params, mode, args.out) for mode in modes]
    write_region_csv(mode_results, args.out / "region_metrics.csv")
    result = {
        "case_xml": str(args.case),
        "params": {
            "nx": params.nx,
            "ny": params.ny,
            "nz": params.nz,
            "density_ratio": params.density_h / params.density_l,
            "density_l": params.density_l,
            "density_h": params.density_h,
            "sigma": params.sigma,
            "int_width": params.int_width,
            "cap_parent_radius": params.cap_parent_radius,
            "cap_center": list(params.cap_center),
            "solid_center": list(params.solid_center),
            "solid_radius": params.solid_radius,
            "solid_axis": params.solid_axis,
            "rad_angle_deg": params.rad_angle_deg,
        },
        "stencil": {
            "laplace": "D3Q27 weights face=16 edge=4 corner=1 center=-152 divided by 36, matching myLaplace",
            "gradient": "D3Q27 isotropic first derivative weights divided by 72, matching IsotropicGrad",
            "phase_stencil_limit": "offline periodic phase stencil; no TCLB WallGhost streaming or boundary update is applied",
        },
        "mode_results": mode_results,
    }
    result["classification"] = classify(mode_results)
    (args.out / "metrics.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    (args.out / "classification.json").write_text(
        json.dumps(result["classification"], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(result["classification"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
