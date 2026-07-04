"""Calibrated bbox contact-angle analysis for flat-wall Taichi phase-field runs.

This ports the Stage15D trusted flat-wall angle measurer to Taichi ``.npz``
artifacts.  The primary reading is the spherical-cap bbox formula

    theta_raw = 2 atan(h / a)

where ``h`` is the height of the ``C > 0.5`` connected droplet footprint in the
wall-center slice and ``a`` is half of its footprint width.  The raw reading is
then inverted through a synthetic tanh-cap calibration curve generated on the
same grid, wall location, interface width, and nominal droplet radius.

The result is a measurement diagnostic only.  It does not validate a wetting
boundary unless paired with mass, velocity, and morphology evidence.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def load_metrics(npz_path: Path) -> dict[str, Any]:
    metrics_path = npz_path.parent / "metrics.json"
    if not metrics_path.exists():
        return {}
    return json.loads(metrics_path.read_text(encoding="utf-8"))


def bbox_angle_from_slice(
    c2: np.ndarray,
    wall_y: float,
    solid2: np.ndarray | None = None,
    level: float = 0.5,
) -> dict[str, float | int | None]:
    nx, ny = c2.shape
    x_coord = np.arange(nx, dtype=np.float64)
    y_coord = np.arange(ny, dtype=np.float64)
    finite = np.isfinite(c2)
    mask = finite & (c2 > level)
    if solid2 is not None:
        mask &= solid2 <= 0
    # Keep the same wall convention as the Taichi solver: solid y=0, fluid
    # wall-adjacent layer y=1, physical wall surface y=0.5.
    mask &= y_coord[np.newaxis, :] > wall_y
    xs, ys = np.where(mask)
    if xs.size == 0:
        return {
            "theta_bbox_raw_deg": math.nan,
            "height": math.nan,
            "half_width": math.nan,
            "liquid_cells": 0,
            "x_min": None,
            "x_max": None,
            "y_min": None,
            "y_max": None,
        }
    xp = x_coord[xs]
    yp = y_coord[ys]
    height = float(yp.max() - yp.min())
    half_width = float((xp.max() - xp.min()) * 0.5)
    theta = 2.0 * math.degrees(math.atan(height / half_width)) if half_width > 0.0 else math.nan
    return {
        "theta_bbox_raw_deg": float(theta),
        "height": height,
        "half_width": half_width,
        "liquid_cells": int(xs.size),
        "x_min": float(xp.min()),
        "x_max": float(xp.max()),
        "y_min": float(yp.min()),
        "y_max": float(yp.max()),
    }


def synthetic_cap(
    nx: int,
    ny: int,
    nz: int,
    theta_deg: float,
    radius: float,
    width: float,
    wall_y: float,
    center_x: float,
    center_z: float,
    z_indices: list[int],
) -> list[np.ndarray]:
    theta = math.radians(theta_deg)
    center_y = wall_y - radius * math.cos(theta)
    x = np.arange(nx, dtype=np.float64)[:, None]
    y = np.arange(ny, dtype=np.float64)[None, :]
    slices: list[np.ndarray] = []
    for z_idx in z_indices:
        dz2 = (float(z_idx) - center_z) ** 2
        dist = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2 + dz2) - radius
        c2 = 0.5 * (1.0 - np.tanh(2.0 * dist / width))
        c2[:, np.arange(ny) <= wall_y] = 0.0
        slices.append(c2)
    return slices


def build_calibration(
    nx: int,
    ny: int,
    nz: int,
    radius: float,
    width: float,
    wall_y: float,
    center_x: float,
    center_z: float,
    z_indices: list[int],
    theta_min: int = 15,
    theta_max: int = 165,
    theta_step: int = 1,
) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    for theta in range(theta_min, theta_max + 1, theta_step):
        readings = []
        for c2 in synthetic_cap(nx, ny, nz, theta, radius, width, wall_y, center_x, center_z, z_indices):
            result = bbox_angle_from_slice(c2, wall_y)
            readings.append(float(result["theta_bbox_raw_deg"]))
        finite = [value for value in readings if math.isfinite(value)]
        rows.append(
            {
                "theta_true_deg": float(theta),
                "theta_bbox_raw_deg": float(np.mean(finite)) if finite else math.nan,
            }
        )
    return rows


def invert_calibration(reading: float, calibration: list[dict[str, float]]) -> tuple[float, bool]:
    finite = [
        (row["theta_bbox_raw_deg"], row["theta_true_deg"])
        for row in calibration
        if math.isfinite(row["theta_bbox_raw_deg"])
    ]
    finite.sort(key=lambda item: item[0])
    raw = np.asarray([item[0] for item in finite], dtype=np.float64)
    true = np.asarray([item[1] for item in finite], dtype=np.float64)
    if not math.isfinite(reading) or raw.size < 2:
        return math.nan, True
    outside = bool(reading < raw.min() or reading > raw.max())
    return float(np.interp(reading, raw, true)), outside


def selected_z_indices(nz: int, n_slices: int) -> list[int]:
    n_slices = max(1, n_slices)
    mid = nz // 2
    half = n_slices // 2
    indices = list(range(mid - half, mid - half + n_slices))
    return [int(np.clip(idx, 0, nz - 1)) for idx in indices]


def analyze(npz_path: Path, out_dir: Path, radius: float | None, width: float | None, z_slices: int) -> dict[str, Any]:
    metrics = load_metrics(npz_path)
    data = np.load(npz_path)
    c = data["c"].astype(np.float64)
    solid = data["solid"].astype(np.int32) if "solid" in data.files else None
    nx, ny, nz = c.shape
    wall_y = float(metrics.get("wall_surface_y", 0.5))
    radius = float(radius if radius is not None else metrics.get("radius", 10.0))
    width = float(width if width is not None else metrics.get("width", 4.0))
    center_x = float(metrics.get("resolved_center_x", 0.5 * (nx - 1)))
    center_z = float(metrics.get("resolved_center_z", 0.5 * (nz - 1)))
    z_indices = selected_z_indices(nz, z_slices)

    slice_results = []
    for z_idx in z_indices:
        c2 = c[:, :, z_idx]
        solid2 = solid[:, :, z_idx] if solid is not None else None
        row = bbox_angle_from_slice(c2, wall_y, solid2)
        row["z_index"] = z_idx
        slice_results.append(row)
    raw_values = [float(row["theta_bbox_raw_deg"]) for row in slice_results]
    raw_mean = float(np.nanmean(raw_values)) if raw_values else math.nan

    calibration = build_calibration(nx, ny, nz, radius, width, wall_y, center_x, center_z, z_indices)
    calibrated, outside = invert_calibration(raw_mean, calibration)

    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "calibrated_bbox_curve.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["theta_true_deg", "theta_bbox_raw_deg"])
        writer.writeheader()
        writer.writerows(calibration)

    fig, ax = plt.subplots(figsize=(7.0, 4.5), constrained_layout=True)
    raw_curve = [row["theta_bbox_raw_deg"] for row in calibration]
    true_curve = [row["theta_true_deg"] for row in calibration]
    ax.plot(true_curve, raw_curve, color="#1f77b4", lw=1.6, label="synthetic tanh-cap bbox reading")
    ax.plot([15, 165], [15, 165], color="0.55", ls="--", lw=1.0, label="identity")
    if math.isfinite(raw_mean) and math.isfinite(calibrated):
        ax.scatter([calibrated], [raw_mean], color="#d62728", s=35, zorder=5, label="measured, inverted")
    ax.set_xlabel("True synthetic contact angle (deg)")
    ax.set_ylabel("Raw bbox reading (deg)")
    ax.set_xlim(15, 165)
    ax.set_ylim(0, 180)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best", fontsize=8)
    ax.set_title("Flat-wall calibrated bbox contact-angle curve")
    fig.savefig(out_dir / "calibrated_bbox_curve.png", dpi=200)
    plt.close(fig)

    z_mid = z_indices[len(z_indices) // 2]
    c2 = c[:, :, z_mid]
    bbox_mid = bbox_angle_from_slice(c2, wall_y, solid[:, :, z_mid] if solid is not None else None)
    fig, ax = plt.subplots(figsize=(7.0, 4.5), constrained_layout=True)
    im = ax.imshow(c2.T, origin="lower", cmap="viridis", vmin=0.0, vmax=1.0, aspect="equal")
    ax.axhline(wall_y, color="red", lw=1.2, label="wall surface")
    if bbox_mid["liquid_cells"]:
        ax.add_patch(
            plt.Rectangle(
                (float(bbox_mid["x_min"]), float(bbox_mid["y_min"])),
                float(bbox_mid["x_max"]) - float(bbox_mid["x_min"]),
                float(bbox_mid["y_max"]) - float(bbox_mid["y_min"]),
                fill=False,
                edgecolor="white",
                linewidth=1.2,
                label="C>0.5 bbox",
            )
        )
    ax.set_xlabel("x [lu]")
    ax.set_ylabel("y [lu]")
    ax.set_title(f"z={z_mid}, calibrated bbox angle={calibrated:.2f} deg")
    ax.legend(loc="upper right", fontsize=8)
    fig.colorbar(im, ax=ax, label="C")
    fig.savefig(out_dir / "calibrated_bbox_slice.png", dpi=200)
    plt.close(fig)

    report = {
        "npz": str(npz_path),
        "method": "Stage15D calibrated bbox h/a adapted to Taichi NPZ",
        "claim_limit": "flat-wall measurement diagnostic only; not validation_passed",
        "target_theta_deg": metrics.get("theta_deg"),
        "init_contact_angle_deg": metrics.get("init_contact_angle_deg"),
        "grid": [nx, ny, nz],
        "wall_y": wall_y,
        "radius_used_for_calibration": radius,
        "width_used_for_calibration": width,
        "center_x": center_x,
        "center_z": center_z,
        "z_indices": z_indices,
        "theta_bbox_raw_mean_deg": raw_mean,
        "theta_calibrated_bbox_deg": calibrated,
        "calibration_outside_range": outside,
        "slice_results": slice_results,
        "calibration_samples": {
            str(theta): next(
                (row["theta_bbox_raw_deg"] for row in calibration if row["theta_true_deg"] == float(theta)),
                math.nan,
            )
            for theta in (30, 60, 90, 120, 150)
        },
    }
    if metrics.get("theta_deg") is not None and math.isfinite(calibrated):
        report["target_error_calibrated_deg"] = calibrated - float(metrics["theta_deg"])
    (out_dir / "calibrated_bbox_metrics.json").write_text(
        json.dumps(report, indent=2, allow_nan=True),
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("npz", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--radius", type=float, default=None, help="nominal droplet radius used to regenerate synthetic calibration")
    parser.add_argument("--width", type=float, default=None, help="interface width used to regenerate synthetic calibration")
    parser.add_argument("--z-slices", type=int, default=3, help="number of center z-slices to average, matching Stage15D practice")
    args = parser.parse_args()
    report = analyze(args.npz, args.out, args.radius, args.width, args.z_slices)
    print(json.dumps(report, indent=2, allow_nan=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
