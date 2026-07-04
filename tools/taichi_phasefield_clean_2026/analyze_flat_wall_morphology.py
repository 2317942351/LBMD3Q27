"""Analyze flat-wall Taichi phase-field droplet morphology.

The reported contact angle is the liquid-side angle measured through the
droplet.  For a circle intersecting a horizontal wall this is

    theta = acos((wall_y - circle_center_y) / radius)

so a semicircle with the circle center on the wall is 90 degrees, a circle
center above the wall is hydrophobic (>90), and a center below the wall is
hydrophilic (<90).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def crossing_x(x0: float, x1: float, c0: float, c1: float, level: float = 0.5) -> float:
    denom = c1 - c0
    if abs(denom) < 1.0e-30:
        return 0.5 * (x0 + x1)
    return x0 + (level - c0) * (x1 - x0) / denom


def interface_points(slice2d: np.ndarray, level: float = 0.5) -> np.ndarray:
    nx, ny = slice2d.shape
    points: list[tuple[float, float]] = []
    for y in range(ny):
        row = slice2d[:, y]
        for x in range(nx - 1):
            c0 = row[x]
            c1 = row[x + 1]
            if (c0 - level) * (c1 - level) <= 0.0 and c0 != c1:
                points.append((crossing_x(float(x), float(x + 1), float(c0), float(c1), level), float(y)))
    for x in range(nx):
        col = slice2d[x, :]
        for y in range(ny - 1):
            c0 = col[y]
            c1 = col[y + 1]
            if (c0 - level) * (c1 - level) <= 0.0 and c0 != c1:
                points.append((float(x), crossing_x(float(y), float(y + 1), float(c0), float(c1), level)))
    if not points:
        return np.empty((0, 2), dtype=np.float64)
    return np.asarray(points, dtype=np.float64)


def fit_circle(points: np.ndarray) -> tuple[float, float, float]:
    x = points[:, 0]
    y = points[:, 1]
    a = np.column_stack([2.0 * x, 2.0 * y, np.ones_like(x)])
    b = x * x + y * y
    cx, cy, c = np.linalg.lstsq(a, b, rcond=None)[0]
    r = math.sqrt(max(c + cx * cx + cy * cy, 0.0))
    return float(cx), float(cy), float(r)


def liquid_side_angle_from_circle(cy: float, radius: float, wall_y: float) -> float:
    if radius <= 0.0:
        return float("nan")
    arg = (wall_y - cy) / radius
    if arg < -1.0 or arg > 1.0:
        return float("nan")
    return math.degrees(math.acos(max(-1.0, min(1.0, arg))))


def contact_angles_from_circle(cx: float, cy: float, radius: float, wall_y: float) -> dict[str, float]:
    dy = wall_y - cy
    disc = radius * radius - dy * dy
    if disc <= 0.0 or radius <= 0.0:
        return {"left_deg": float("nan"), "right_deg": float("nan"), "mean_deg": float("nan")}
    dx = math.sqrt(disc)
    angles = []
    theta = liquid_side_angle_from_circle(cy, radius, wall_y)
    for _x_contact in (cx - dx, cx + dx):
        angles.append(theta)
    return {"left_deg": float(angles[0]), "right_deg": float(angles[1]), "mean_deg": float(np.mean(angles))}


def run_synthetic_checks() -> dict[str, float]:
    checks = {
        "semicircle_90": contact_angles_from_circle(0.0, 0.0, 10.0, 0.0)["mean_deg"],
        "hydrophilic_60": contact_angles_from_circle(0.0, -5.0, 10.0, 0.0)["mean_deg"],
        "hydrophobic_120": contact_angles_from_circle(0.0, 5.0, 10.0, 0.0)["mean_deg"],
        "near_nonwetting_180": contact_angles_from_circle(0.0, 9.0, 10.0, 0.0)["mean_deg"],
    }
    expected = {
        "semicircle_90": 90.0,
        "hydrophilic_60": 60.0,
        "hydrophobic_120": 120.0,
        "near_nonwetting_180": 154.15806723683288,
    }
    for key, value in checks.items():
        if not math.isfinite(value) or abs(value - expected[key]) > 1.0e-10:
            raise AssertionError(f"{key}: expected {expected[key]}, got {value}")
    return checks


def sibling_metrics(npz_path: Path) -> dict[str, object]:
    metrics_path = npz_path.parent / "metrics.json"
    if not metrics_path.exists():
        return {}
    try:
        return json.loads(metrics_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def analyze(npz_path: Path, out_dir: Path, wall_y: float | None) -> dict[str, object]:
    metrics = sibling_metrics(npz_path)
    if wall_y is None:
        wall_y = float(metrics.get("wall_surface_y", 0.5))
    data = np.load(npz_path)
    c = data["c"]
    z_mid = c.shape[2] // 2
    slice2d = c[:, :, z_mid]
    points = interface_points(slice2d)
    if points.shape[0] >= 6:
        band = points[points[:, 1] <= wall_y + 12.0]
        fit_points = band if band.shape[0] >= 6 else points
        cx, cy, radius = fit_circle(fit_points)
        angles = contact_angles_from_circle(cx, cy, radius, wall_y)
    else:
        cx = cy = radius = float("nan")
        angles = {"left_deg": float("nan"), "right_deg": float("nan"), "mean_deg": float("nan")}

    out_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7, 4.5), constrained_layout=True)
    im = ax.imshow(slice2d.T, origin="lower", cmap="viridis", vmin=0.0, vmax=1.0, aspect="equal")
    if points.shape[0]:
        ax.scatter(points[:, 0], points[:, 1], s=2, c="white", alpha=0.8, linewidths=0)
    ax.axhline(wall_y, color="red", linewidth=1.2, label="wall fluid layer")
    ax.set_xlabel("x [lu]")
    ax.set_ylabel("y [lu]")
    ax.set_title(f"C slice z={z_mid}, contact angle={angles['mean_deg']:.2f} deg")
    fig.colorbar(im, ax=ax, label="C")
    ax.legend(loc="upper right")
    fig.savefig(out_dir / "morphology_slice.png", dpi=200, bbox_inches="tight")
    plt.close(fig)

    report = {
        "npz": str(npz_path),
        "angle_convention": "liquid-side angle through droplet; theta=acos((wall_y-circle_center_y)/radius)",
        "target_theta_deg": metrics.get("theta_deg"),
        "init_contact_angle_deg": metrics.get("init_contact_angle_deg"),
        "resolved_center_y": metrics.get("resolved_center_y"),
        "z_mid": z_mid,
        "wall_y": wall_y,
        "interface_points": int(points.shape[0]),
        "fit_center_x": cx,
        "fit_center_y": cy,
        "fit_radius": radius,
        **angles,
    }
    if metrics.get("theta_deg") is not None and math.isfinite(report["mean_deg"]):
        report["target_error_deg"] = float(report["mean_deg"] - float(metrics["theta_deg"]))
    (out_dir / "morphology_metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("npz", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--wall-y", type=float, default=None, help="physical wall y; defaults to metrics.json wall_surface_y or 0.5")
    parser.add_argument("--self-test", action="store_true", help="run synthetic circle contact-angle checks before analysis")
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps({"synthetic_checks": run_synthetic_checks()}, indent=2))
    report = analyze(args.npz, args.out, args.wall_y)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
