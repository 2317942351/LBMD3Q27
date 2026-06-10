#!/usr/bin/env python3
"""Plot radAngle=11 baseline/bounded wall diagnostic evolution."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt


def read_csv(path: Path, variant: str) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        row["variant"] = variant
    return rows


def value(row: dict[str, str], field: str) -> float:
    return float(row[field])


def plot_evolution(rows: list[dict[str, str]], out_path: Path) -> None:
    cases = ["flat_theta011", "curved_theta011"]
    fields = [
        ("wall_phase_pred_max", "Max Raw WallPhasePred", "value"),
        ("phase_wall_max", "Max Actual Wall PhaseField", "value"),
        ("fluid_phase_field_gt_1_count", "Fluid PhaseField > 1", "count"),
        ("wall_phase_field_gt_1_count", "Actual Wall PhaseField > 1", "count"),
        ("phase_fluid_max", "Max Fluid PhaseField", "value"),
        ("max_mach", "Max Mach", "Ma"),
    ]
    colors = {"baseline": "#5762d5", "bounded": "#e08d3c"}
    linestyles = {"flat_theta011": "-", "curved_theta011": "--"}

    fig, axes = plt.subplots(2, 3, figsize=(16, 8.5), sharex=True)
    for ax, (field, title, ylabel) in zip(axes.ravel(), fields):
        for variant in ["baseline", "bounded"]:
            for case in cases:
                subset = [
                    row
                    for row in rows
                    if row["variant"] == variant and row["case_id"] == case
                ]
                subset.sort(key=lambda row: value(row, "step"))
                ax.plot(
                    [value(row, "step") for row in subset],
                    [value(row, field) for row in subset],
                    label=f"{variant} {case.split('_')[0]}",
                    color=colors[variant],
                    linestyle=linestyles[case],
                    marker="o",
                    markersize=3.5,
                )
        if field in {"wall_phase_pred_max", "phase_wall_max", "phase_fluid_max"}:
            ax.axhline(1.0, color="black", linewidth=0.9, linestyle=":", alpha=0.8)
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.25)
    axes[1, 0].set_xlabel("step")
    axes[1, 1].set_xlabel("step")
    axes[1, 2].set_xlabel("step")
    axes[0, 0].legend(fontsize=8)
    fig.suptitle("radAngle 11 deg Early Evolution: Baseline vs Bounded Diagnostic")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_final_montage(base_figures: Path, bounded_figures: Path, out_path: Path) -> None:
    specs = [
        (base_figures / "flat_theta011_step00001000_diagnostics.png", "baseline flat 1000"),
        (bounded_figures / "flat_theta011_step00001000_diagnostics.png", "bounded flat 1000"),
        (base_figures / "curved_theta011_step00001000_diagnostics.png", "baseline curved 1000"),
        (bounded_figures / "curved_theta011_step00001000_diagnostics.png", "bounded curved 1000"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(17, 11))
    for ax, (path, title) in zip(axes.ravel(), specs):
        ax.imshow(mpimg.imread(path))
        ax.set_title(title)
        ax.axis("off")
    fig.suptitle("radAngle 11 deg Step 1000 Diagnostic Slices")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-csv", type=Path, required=True)
    parser.add_argument("--bounded-csv", type=Path, required=True)
    parser.add_argument("--baseline-figures", type=Path, required=True)
    parser.add_argument("--bounded-figures", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    rows = read_csv(args.baseline_csv, "baseline") + read_csv(args.bounded_csv, "bounded")
    plot_evolution(rows, args.out_dir / "wall_geom_rad011_1000_evolution.png")
    plot_final_montage(
        args.baseline_figures,
        args.bounded_figures,
        args.out_dir / "wall_geom_rad011_1000_final_montage.png",
    )


if __name__ == "__main__":
    main()
