#!/usr/bin/env python3
"""Plot curved radAngle=11 10k baseline/bounded wall diagnostic evolution."""

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


def val(row: dict[str, str], field: str) -> float:
    return float(row[field])


def plot_evolution(rows: list[dict[str, str]], out_path: Path) -> None:
    fields = [
        ("wall_phase_pred_gt_1_count", "Raw WallPhasePred > 1", "count"),
        ("wall_phase_field_gt_1_count", "Actual Wall PhaseField > 1", "count"),
        ("wall_phase_pred_max", "Max Raw WallPhasePred", "value"),
        ("phase_wall_max", "Max Actual Wall PhaseField", "value"),
        ("phase_fluid_max", "Max Fluid PhaseField", "value"),
        ("max_mach", "Max Mach", "Ma"),
    ]
    colors = {"baseline": "#5762d5", "bounded": "#e08d3c"}
    fig, axes = plt.subplots(2, 3, figsize=(16, 8.5), sharex=True)
    for ax, (field, title, ylabel) in zip(axes.ravel(), fields):
        for variant in ["baseline", "bounded"]:
            subset = [row for row in rows if row["variant"] == variant]
            subset.sort(key=lambda row: val(row, "step"))
            ax.plot(
                [val(row, "step") for row in subset],
                [val(row, field) for row in subset],
                color=colors[variant],
                marker="o",
                label=variant,
            )
        if field in {"wall_phase_pred_max", "phase_wall_max", "phase_fluid_max"}:
            ax.axhline(1.0, color="black", linewidth=0.9, linestyle=":", alpha=0.8)
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.25)
    for ax in axes[1, :]:
        ax.set_xlabel("step")
    axes[0, 0].legend(fontsize=9)
    fig.suptitle("Curved radAngle 11 deg 10k Evolution: Baseline vs Bounded Diagnostic")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_final_montage(base_figures: Path, bounded_figures: Path, out_path: Path) -> None:
    specs = [
        (base_figures / "curved_theta011_step00010000_diagnostics.png", "baseline curved 10000"),
        (bounded_figures / "curved_theta011_step00010000_diagnostics.png", "bounded curved 10000"),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(17, 7))
    for ax, (path, title) in zip(axes.ravel(), specs):
        ax.imshow(mpimg.imread(path))
        ax.set_title(title)
        ax.axis("off")
    fig.suptitle("Curved radAngle 11 deg Step 10000 Diagnostic Slices")
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
    plot_evolution(rows, args.out_dir / "wall_geom_curved_rad011_10k_evolution.png")
    plot_final_montage(
        args.baseline_figures,
        args.bounded_figures,
        args.out_dir / "wall_geom_curved_rad011_10k_final_montage.png",
    )


if __name__ == "__main__":
    main()
