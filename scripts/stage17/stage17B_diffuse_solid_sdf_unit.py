#!/usr/bin/env python3
"""Offline Stage17B-B1 analytic-SDF / diffuse-solid audit.

This script does not run TCLB and does not write PhaseF. It builds analytic
plane/cylinder/sphere geometry fields, compares diffuse-solid normals against
sharp staircase normals, and records bounded shadow wall-ghost diagnostics for
theta = 60, 90, 120 degrees.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


EPS_NORM = 1.0e-12
THETAS_DEG = (60.0, 90.0, 120.0)


@dataclass(frozen=True)
class CaseData:
    name: str
    sdf: np.ndarray
    analytic_normal_out: tuple[np.ndarray, np.ndarray, np.ndarray]
    axes: tuple[np.ndarray, np.ndarray, np.ndarray]
    slice_axis: int
    slice_index: int


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    root = repo_root_from_script()
    default_out = root / "artifacts" / "stage17B_B1_diffuse_solid_sdf_20260623"
    parser = argparse.ArgumentParser(
        description="Run offline Stage17B-B1 diffuse-solid SDF unit audit."
    )
    parser.add_argument("--out", type=Path, default=default_out)
    parser.add_argument("--n", type=int, default=96)
    parser.add_argument("--radius", type=float, default=20.0)
    parser.add_argument("--sweep", action="store_true", help="Also run the B1 radius/eps sensitivity matrix.")
    parser.add_argument("--radii", nargs="+", type=float, default=[12.0, 16.0, 20.0, 24.0])
    parser.add_argument("--eps-values", nargs="+", type=float, default=[0.8, 1.0, 1.2, 1.25, 1.5])
    parser.add_argument("--eps-solid", type=float, default=1.25)
    parser.add_argument("--near-band", type=float, default=2.0)
    parser.add_argument("--ghost-band", type=float, default=1.5)
    parser.add_argument("--phi-lo", type=float, default=0.0)
    parser.add_argument("--phi-hi", type=float, default=1.0)
    return parser.parse_args()


def coords(n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    a = np.arange(n, dtype=np.float64)
    x, y, z = np.meshgrid(a, a, a, indexing="ij")
    return x, y, z


def normalize(nx: np.ndarray, ny: np.ndarray, nz: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mag = np.sqrt(nx * nx + ny * ny + nz * nz)
    safe = np.where(mag > EPS_NORM, mag, 1.0)
    return nx / safe, ny / safe, nz / safe


def gradient_centered(a: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return tuple(np.gradient(a, 1.0, edge_order=2))  # type: ignore[return-value]


def make_cases(n: int, radius: float) -> list[CaseData]:
    x, y, z = coords(n)
    center = 0.5 * (n - 1)

    plane_sdf = y - center
    plane_normal = (np.zeros_like(x), np.ones_like(y), np.zeros_like(z))

    cylinder_sdf = np.sqrt((x - center) ** 2 + (y - center) ** 2) - radius
    cylinder_normal = normalize(x - center, y - center, np.zeros_like(z))

    sphere_sdf = np.sqrt((x - center) ** 2 + (y - center) ** 2 + (z - center) ** 2) - radius
    sphere_normal = normalize(x - center, y - center, z - center)

    return [
        CaseData("plane", plane_sdf, plane_normal, (x, y, z), 2, n // 2),
        CaseData("cylinder_z", cylinder_sdf, cylinder_normal, (x, y, z), 2, n // 2),
        CaseData("sphere", sphere_sdf, sphere_normal, (x, y, z), 2, n // 2),
    ]


def diffuse_solid(sdf: np.ndarray, eps_solid: float) -> np.ndarray:
    return 0.5 * (1.0 - np.tanh(sdf / (math.sqrt(2.0) * eps_solid)))


def sharp_solid(sdf: np.ndarray) -> np.ndarray:
    return (sdf < 0.0).astype(np.float64)


def normal_from_indicator(psi_s: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    gx, gy, gz = gradient_centered(psi_s)
    grad_mag = np.sqrt(gx * gx + gy * gy + gz * gz)
    safe = np.where(grad_mag > EPS_NORM, grad_mag, 1.0)
    # grad(psi_s) points inward because psi_s is one in solid and zero in fluid.
    # The Stage17B wall normal convention used here is solid -> fluid.
    return -gx / safe, -gy / safe, -gz / safe, grad_mag


def tangent_grad_magnitude(
    grad_x: np.ndarray,
    grad_y: np.ndarray,
    grad_z: np.ndarray,
    nx: np.ndarray,
    ny: np.ndarray,
    nz: np.ndarray,
) -> np.ndarray:
    dot = grad_x * nx + grad_y * ny + grad_z * nz
    tx = grad_x - dot * nx
    ty = grad_y - dot * ny
    tz = grad_z - dot * nz
    return np.sqrt(tx * tx + ty * ty + tz * tz)


def synthetic_phi(case: CaseData, interface_offset: float = 4.0, width: float = 3.0) -> np.ndarray:
    x, y, z = case.axes
    cx = 0.5 * (x.shape[0] - 1)
    if case.name == "plane":
        tangential = x - cx
    elif case.name == "cylinder_z":
        tangential = z - cx
    else:
        tangential = z - cx
    interface = tangential + 0.08 * case.sdf + interface_offset
    return 0.5 * (1.0 - np.tanh(interface / width))


def shadow_ghost(
    phi_f: np.ndarray,
    tangent_grad: np.ndarray,
    theta_deg: float,
    h: float,
    phi_lo: float,
    phi_hi: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    theta = math.radians(theta_deg)
    raw = phi_f + 2.0 * h * math.tan(0.5 * math.pi - theta) * tangent_grad
    clamped = np.clip(raw, phi_lo, phi_hi)
    clamp_hit = np.abs(raw - clamped) > 1.0e-14
    return raw, clamped, clamp_hit


def finite_stats(values: np.ndarray) -> dict[str, float | int]:
    flat = np.asarray(values, dtype=np.float64).ravel()
    finite = np.isfinite(flat)
    out: dict[str, float | int] = {
        "count": int(flat.size),
        "finite_count": int(finite.sum()),
        "nonfinite_count": int((~finite).sum()),
    }
    if finite.any():
        f = flat[finite]
        out.update(
            {
                "min": float(np.min(f)),
                "max": float(np.max(f)),
                "mean": float(np.mean(f)),
                "std": float(np.std(f)),
                "p95": float(np.percentile(f, 95.0)),
                "p99": float(np.percentile(f, 99.0)),
            }
        )
    else:
        out.update({"min": math.nan, "max": math.nan, "mean": math.nan, "std": math.nan, "p95": math.nan, "p99": math.nan})
    return out


def masked(values: np.ndarray, mask: np.ndarray) -> np.ndarray:
    return np.asarray(values[mask], dtype=np.float64)


def vector_alignment(
    ax: np.ndarray,
    ay: np.ndarray,
    az: np.ndarray,
    bx: np.ndarray,
    by: np.ndarray,
    bz: np.ndarray,
) -> np.ndarray:
    return ax * bx + ay * by + az * bz


def normal_jump_metric(nx: np.ndarray, ny: np.ndarray, nz: np.ndarray, mask: np.ndarray) -> np.ndarray:
    jumps: list[np.ndarray] = []
    for axis in range(3):
        nx0 = np.take(nx, indices=range(nx.shape[axis] - 1), axis=axis)
        nx1 = np.take(nx, indices=range(1, nx.shape[axis]), axis=axis)
        ny0 = np.take(ny, indices=range(ny.shape[axis] - 1), axis=axis)
        ny1 = np.take(ny, indices=range(1, ny.shape[axis]), axis=axis)
        nz0 = np.take(nz, indices=range(nz.shape[axis] - 1), axis=axis)
        nz1 = np.take(nz, indices=range(1, nz.shape[axis]), axis=axis)
        m0 = np.take(mask, indices=range(mask.shape[axis] - 1), axis=axis)
        m1 = np.take(mask, indices=range(1, mask.shape[axis]), axis=axis)
        pair_mask = m0 & m1
        jump = np.sqrt((nx1 - nx0) ** 2 + (ny1 - ny0) ** 2 + (nz1 - nz0) ** 2)
        if np.any(pair_mask):
            jumps.append(jump[pair_mask])
    if not jumps:
        return np.array([], dtype=np.float64)
    return np.concatenate(jumps)


def case_metrics(
    case: CaseData,
    radius: float,
    eps_solid: float,
    near_band: float,
    ghost_band: float,
    phi_lo: float,
    phi_hi: float,
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], dict[str, np.ndarray]]:
    psi = diffuse_solid(case.sdf, eps_solid)
    sharp = sharp_solid(case.sdf)
    dn_x, dn_y, dn_z, dgrad_mag = normal_from_indicator(psi)
    sn_x, sn_y, sn_z, sgrad_mag = normal_from_indicator(sharp)
    an_x, an_y, an_z = case.analytic_normal_out

    near_mask = np.abs(case.sdf) <= near_band
    ghost_mask = (case.sdf >= 0.0) & (case.sdf <= ghost_band)

    align_diffuse = vector_alignment(dn_x, dn_y, dn_z, an_x, an_y, an_z)
    align_sharp = vector_alignment(sn_x, sn_y, sn_z, an_x, an_y, an_z)
    jump_diffuse = normal_jump_metric(dn_x, dn_y, dn_z, near_mask & (dgrad_mag > 1.0e-8))
    jump_sharp = normal_jump_metric(sn_x, sn_y, sn_z, near_mask & (sgrad_mag > 1.0e-8))

    jagged_rows: list[dict[str, object]] = []
    for label, grad_mag, align, jumps in [
        ("diffuse", dgrad_mag, align_diffuse, jump_diffuse),
        ("sharp", sgrad_mag, align_sharp, jump_sharp),
    ]:
        gstats = finite_stats(masked(grad_mag, near_mask))
        astats = finite_stats(masked(align, near_mask & (grad_mag > 1.0e-8)))
        jstats = finite_stats(jumps)
        jagged_rows.append(
            {
                "case": case.name,
                "radius": radius,
                "eps_solid": eps_solid,
                "indicator": label,
                "near_count": int(np.count_nonzero(near_mask)),
                "grad_mean": gstats["mean"],
                "grad_std": gstats["std"],
                "grad_max": gstats["max"],
                "grad_p99": gstats["p99"],
                "normal_alignment_min": astats["min"],
                "normal_alignment_mean": astats["mean"],
                "normal_jump_mean": jstats["mean"],
                "normal_jump_max": jstats["max"],
                "normal_jump_p99": jstats["p99"],
            }
        )

    phi = synthetic_phi(case)
    pgx, pgy, pgz = gradient_centered(phi)
    tangent_grad = tangent_grad_magnitude(pgx, pgy, pgz, dn_x, dn_y, dn_z)

    ghost_rows: list[dict[str, object]] = []
    raw_ranges: dict[float, tuple[float, float]] = {}
    for theta in THETAS_DEG:
        raw, clamped, clamp_hit = shadow_ghost(phi, tangent_grad, theta, eps_solid, phi_lo, phi_hi)
        raw_m = masked(raw, ghost_mask)
        clamped_m = masked(clamped, ghost_mask)
        hit_m = clamp_hit[ghost_mask]
        excess_m = np.abs(raw_m - clamped_m)
        raw_stats = finite_stats(raw_m)
        clamped_stats = finite_stats(clamped_m)
        excess_stats = finite_stats(excess_m)
        raw_ranges[theta] = (float(raw_stats["min"]), float(raw_stats["max"]))
        ghost_rows.append(
            {
                "case": case.name,
                "radius": radius,
                "eps_solid": eps_solid,
                "theta_deg": theta,
                "ghost_count": int(np.count_nonzero(ghost_mask)),
                "raw_min": raw_stats["min"],
                "raw_max": raw_stats["max"],
                "raw_mean": raw_stats["mean"],
                "clamped_min": clamped_stats["min"],
                "clamped_max": clamped_stats["max"],
                "clamped_mean": clamped_stats["mean"],
                "clamp_fraction": float(np.mean(hit_m)) if hit_m.size else 0.0,
                "max_clamp_excess": excess_stats["max"],
                "mean_clamp_excess": excess_stats["mean"],
                "bounded": bool(np.all(np.isfinite(clamped_m)) and np.all(clamped_m >= phi_lo) and np.all(clamped_m <= phi_hi)),
            }
        )

    summary_rows: list[dict[str, object]] = []
    diffuse_row = next(row for row in jagged_rows if row["indicator"] == "diffuse")
    sharp_row = next(row for row in jagged_rows if row["indicator"] == "sharp")
    diffuse_grad_std = float(diffuse_row["grad_std"])
    sharp_grad_std = float(sharp_row["grad_std"])
    diffuse_grad_max = float(diffuse_row["grad_max"])
    sharp_grad_max = float(sharp_row["grad_max"])
    diffuse_jump_p99 = float(diffuse_row["normal_jump_p99"])
    sharp_jump_p99 = float(sharp_row["normal_jump_p99"])
    all_ghost_bounded = all(bool(row["bounded"]) for row in ghost_rows)
    max_clamp = max(float(row["clamp_fraction"]) for row in ghost_rows)
    max_clamp_excess = max(float(row["max_clamp_excess"]) for row in ghost_rows)
    min_alignment = float(diffuse_row["normal_alignment_min"])
    curved_case = case.name != "plane"
    jump_ok = diffuse_jump_p99 < sharp_jump_p99 if curved_case else diffuse_jump_p99 < 1.0e-12
    summary_rows.append(
        {
            "case": case.name,
            "radius": radius,
            "near_band": near_band,
            "ghost_band": ghost_band,
            "eps_solid": eps_solid,
            "diffuse_grad_std": diffuse_grad_std,
            "sharp_grad_std": sharp_grad_std,
            "diffuse_grad_max": diffuse_grad_max,
            "sharp_grad_max": sharp_grad_max,
            "grad_std_improvement": sharp_grad_std / max(diffuse_grad_std, EPS_NORM),
            "grad_max_improvement": sharp_grad_max / max(diffuse_grad_max, EPS_NORM),
            "diffuse_jump_p99": diffuse_jump_p99,
            "sharp_jump_p99": sharp_jump_p99,
            "jump_p99_improvement": sharp_jump_p99 / max(diffuse_jump_p99, EPS_NORM),
            "diffuse_alignment_min": min_alignment,
            "max_ghost_clamp_fraction": max_clamp,
            "max_ghost_clamp_excess": max_clamp_excess,
            "all_shadow_ghost_bounded": all_ghost_bounded,
            "b1_pass": bool(
                diffuse_grad_std < sharp_grad_std
                and diffuse_grad_max < sharp_grad_max
                and jump_ok
                and min_alignment > 0.90
                and all_ghost_bounded
                and max_clamp < 0.50
                and max_clamp_excess < 1.0e-2
            ),
        }
    )

    arrays = {
        "psi": psi,
        "sharp": sharp,
        "diffuse_grad_mag": dgrad_mag,
        "sharp_grad_mag": sgrad_mag,
        "diffuse_nx": dn_x,
        "diffuse_ny": dn_y,
        "diffuse_nz": dn_z,
        "phi": phi,
        "tangent_grad": tangent_grad,
        "near_mask": near_mask,
        "ghost_mask": ghost_mask,
    }
    return summary_rows, jagged_rows, ghost_rows, arrays


def write_csv(path: Path, rows: Iterable[dict[str, object]]) -> None:
    rows = list(rows)
    if not rows:
        raise ValueError(f"no rows for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def slice2d(a: np.ndarray, axis: int, index: int) -> np.ndarray:
    return np.take(a, index, axis=axis)


def plot_case(case: CaseData, arrays: dict[str, np.ndarray], out: Path) -> None:
    psi = slice2d(arrays["psi"], case.slice_axis, case.slice_index)
    grad = slice2d(arrays["diffuse_grad_mag"], case.slice_axis, case.slice_index)
    sharp_grad = slice2d(arrays["sharp_grad_mag"], case.slice_axis, case.slice_index)
    nx = slice2d(arrays["diffuse_nx"], case.slice_axis, case.slice_index)
    ny = slice2d(arrays["diffuse_ny"], case.slice_axis, case.slice_index)

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), constrained_layout=True)
    im0 = axes[0].imshow(psi.T, origin="lower", cmap="viridis", vmin=0.0, vmax=1.0)
    axes[0].set_title(f"{case.name}: diffuse solid psi")
    fig.colorbar(im0, ax=axes[0], fraction=0.046)

    im1 = axes[1].imshow(grad.T, origin="lower", cmap="magma")
    axes[1].set_title("|grad psi| diffuse")
    fig.colorbar(im1, ax=axes[1], fraction=0.046)

    im2 = axes[2].imshow(sharp_grad.T, origin="lower", cmap="magma")
    step = max(1, psi.shape[0] // 24)
    yy, xx = np.mgrid[0 : psi.shape[1] : step, 0 : psi.shape[0] : step]
    axes[2].quiver(xx, yy, nx[::step, ::step].T, ny[::step, ::step].T, color="white", scale=28)
    axes[2].set_title("|grad I| sharp + diffuse normal")
    fig.colorbar(im2, ax=axes[2], fraction=0.046)

    for ax in axes:
        ax.set_xlabel("i")
        ax.set_ylabel("j")
    fig.savefig(out, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_ghost_sweep(rows: list[dict[str, object]], out: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.5, 5.0), constrained_layout=True)
    cases = sorted({str(row["case"]) for row in rows})
    offsets = np.linspace(-0.18, 0.18, len(cases))
    theta = np.array(THETAS_DEG)
    width = 0.12
    for offset, case in zip(offsets, cases):
        cr = [row for row in rows if row["case"] == case]
        cr.sort(key=lambda r: float(r["theta_deg"]))
        clamp = np.array([float(row["clamp_fraction"]) for row in cr])
        raw_span = np.array([float(row["raw_max"]) - float(row["raw_min"]) for row in cr])
        ax.bar(theta + offset * 20.0, clamp, width=width * 20.0, label=f"{case} clamp")
        ax.plot(theta, np.minimum(raw_span, 2.0), marker="o", linewidth=1.4, label=f"{case} raw span capped")
    ax.set_xlabel("theta (deg)")
    ax.set_ylabel("fraction / raw span")
    ax.set_title("Stage17B-B1 shadow ghost boundedness sweep")
    ax.grid(True, alpha=0.3)
    ax.legend(ncol=2, fontsize=8)
    fig.savefig(out, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def write_report(
    out_dir: Path,
    metrics: list[dict[str, object]],
    jagged: list[dict[str, object]],
    ghost: list[dict[str, object]],
    sweep_metrics: list[dict[str, object]],
    doc_path: Path,
) -> None:
    overall_pass = all(bool(row["b1_pass"]) for row in metrics)
    sweep_pass_count = sum(1 for row in sweep_metrics if bool(row["b1_pass"]))
    sweep_fail_count = len(sweep_metrics) - sweep_pass_count
    lines = [
        "# Stage17B-B1 Offline Analytic-SDF / Diffuse-Solid Unit Gate",
        "",
        "Date: 2026-06-23",
        "",
        "Status: `b1_offline_geometry_gate_passed`" if overall_pass else "Status: `b1_offline_geometry_gate_failed`",
        "",
        "This is an offline geometry and shadow-ghost audit only. It is not a TCLB run, not a contact-angle validation, and not a dynamic-impact preflight.",
        "",
        "## Inputs",
        "",
        "```text",
        f"artifact_dir = {out_dir.as_posix()}",
        "geometries = plane, z-axis cylinder, sphere",
        "theta sweep = 60, 90, 120 deg",
        "PhaseF write = disabled",
        "TCLB solver source edit = none",
        "```",
        "",
        "## B1 Summary",
        "",
        "| case | B1 pass | grad std improvement | grad max improvement | jump p99 improvement | min diffuse normal alignment | max ghost clamp fraction |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in metrics:
        lines.append(
            "| {case} | {b1_pass} | {grad_std_improvement:.3g} | {grad_max_improvement:.3g} | {jump_p99_improvement:.3g} | {diffuse_alignment_min:.6g} | {max_ghost_clamp_fraction:.6g} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The diffuse-solid field is generated from the analytic signed distance function, so its wall normal is smooth and tied to the intended curved geometry rather than to the staircase mask topology.",
            "",
            "A pass means only that B1 can support a later TCLB shadow-only implementation. It does not authorize writing `PhaseF` and does not prove cylinder or sphere contact angles.",
            "",
            "The normal convention in this script is solid-to-fluid: because `psi_s` is one in the solid and zero in the fluid, `grad(psi_s)` points inward and the exported Stage17B normal is `-grad(psi_s)/|grad(psi_s)|`.",
            "",
            "The clamp fraction is interpreted together with clamp excess. The default synthetic phase field touches the 0/1 bounds, so some 60/120 degree shadow ghosts are clipped, but the maximum excess must remain below `1e-2` for B1.",
            "",
            "## Radius / Eps Sensitivity Sweep",
            "",
            f"Sweep rows: {len(sweep_metrics)}; passed rows: {sweep_pass_count}; failed rows: {sweep_fail_count}. The full sweep is recorded in `sweep_metrics.csv`, `sweep_normal_jaggedness.csv`, and `sweep_ghost_bounds.csv`.",
            "",
            "## Ghost Shadow Bounds",
            "",
            "| case | theta | raw min | raw max | clamped min | clamped max | clamp fraction | max excess | bounded |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in ghost:
        lines.append(
            "| {case} | {theta_deg:.0f} | {raw_min:.6g} | {raw_max:.6g} | {clamped_min:.6g} | {clamped_max:.6g} | {clamp_fraction:.6g} | {max_clamp_excess:.6g} | {bounded} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "```text",
            "metrics.json",
            "metrics.csv",
            "normal_jaggedness.csv",
            "ghost_bounds.csv",
            "cylinder_psi_normal.png",
            "sphere_psi_normal_midplane.png",
            "ghost_theta_sweep.png",
            "sweep_metrics.csv",
            "sweep_normal_jaggedness.csv",
            "sweep_ghost_bounds.csv",
            "```",
            "",
            "## Next Gate",
            "",
            "If B1 remains passed after review, the next step is B2 TCLB shadow-only fields: `PsiSolid`, `PsiGradMag`, `PsiNormalX/Y/Z`, `PsiWallGhost`, `PsiThetaImplied`, `PsiJaggedness`, `PsiWriteAllowedFlag`, `NearWallForceMag`, and `NearWallGradPhiMag`. B2 must still not write `PhaseF`.",
            "",
        ]
    )
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    all_metrics: list[dict[str, object]] = []
    all_jagged: list[dict[str, object]] = []
    all_ghost: list[dict[str, object]] = []
    plot_arrays: dict[str, tuple[CaseData, dict[str, np.ndarray]]] = {}

    for case in make_cases(args.n, args.radius):
        metrics, jagged, ghost, arrays = case_metrics(
            case,
            args.radius,
            args.eps_solid,
            args.near_band,
            args.ghost_band,
            args.phi_lo,
            args.phi_hi,
        )
        all_metrics.extend(metrics)
        all_jagged.extend(jagged)
        all_ghost.extend(ghost)
        plot_arrays[case.name] = (case, arrays)

    sweep_metrics: list[dict[str, object]] = []
    sweep_jagged: list[dict[str, object]] = []
    sweep_ghost: list[dict[str, object]] = []
    if args.sweep:
        for radius in args.radii:
            for eps_solid in args.eps_values:
                for case in make_cases(args.n, radius):
                    metrics, jagged, ghost, _arrays = case_metrics(
                        case,
                        radius,
                        eps_solid,
                        args.near_band,
                        args.ghost_band,
                        args.phi_lo,
                        args.phi_hi,
                    )
                    sweep_metrics.extend(metrics)
                    sweep_jagged.extend(jagged)
                    sweep_ghost.extend(ghost)

    metrics_json = {
        "status": "b1_offline_geometry_gate_passed" if all(bool(row["b1_pass"]) for row in all_metrics) else "b1_offline_geometry_gate_failed",
        "parameters": {
            "n": args.n,
            "radius": args.radius,
            "eps_solid": args.eps_solid,
            "sweep": args.sweep,
            "radii": args.radii,
            "eps_values": args.eps_values,
            "near_band": args.near_band,
            "ghost_band": args.ghost_band,
            "thetas_deg": list(THETAS_DEG),
            "phi_lo": args.phi_lo,
            "phi_hi": args.phi_hi,
        },
        "metrics": all_metrics,
        "sweep_summary": {
            "rows": len(sweep_metrics),
            "pass_count": sum(1 for row in sweep_metrics if bool(row["b1_pass"])),
            "fail_count": sum(1 for row in sweep_metrics if not bool(row["b1_pass"])),
        },
        "claim_limit": "offline geometry and shadow ghost only; no TCLB run; no contact-angle validation",
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics_json, indent=2), encoding="utf-8")
    write_csv(out_dir / "metrics.csv", all_metrics)
    write_csv(out_dir / "normal_jaggedness.csv", all_jagged)
    write_csv(out_dir / "ghost_bounds.csv", all_ghost)
    if args.sweep:
        write_csv(out_dir / "sweep_metrics.csv", sweep_metrics)
        write_csv(out_dir / "sweep_normal_jaggedness.csv", sweep_jagged)
        write_csv(out_dir / "sweep_ghost_bounds.csv", sweep_ghost)

    plot_case(*plot_arrays["cylinder_z"], out_dir / "cylinder_psi_normal.png")
    plot_case(*plot_arrays["sphere"], out_dir / "sphere_psi_normal_midplane.png")
    plot_ghost_sweep(all_ghost, out_dir / "ghost_theta_sweep.png")

    doc_path = repo_root_from_script() / "docs" / "stage14" / "76_stage17B_B1_diffuse_solid_sdf_unit_20260623.md"
    write_report(out_dir, all_metrics, all_jagged, all_ghost, sweep_metrics, doc_path)

    print(json.dumps({"status": metrics_json["status"], "out_dir": str(out_dir), "doc": str(doc_path)}, indent=2))
    return 0 if metrics_json["status"] == "b1_offline_geometry_gate_passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
