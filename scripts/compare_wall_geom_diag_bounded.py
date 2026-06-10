#!/usr/bin/env python3
"""Compare baseline and bounded TCLB wall geometric diagnostic summaries."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np


CASE_ORDER = [
    "flat_theta011",
    "curved_theta011",
    "flat_theta030",
    "curved_theta030",
    "flat_theta090",
    "curved_theta090",
]


def read_rows(path: Path, variant: str) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for row in rows:
        row["variant"] = variant
        row.setdefault("wall_phase_bounded_pred_gt_1_count", row["wall_phase_pred_gt_1_count"])
        row.setdefault("wall_clamp_delta_nonzero_count", "0")
        row.setdefault("wall_phase_bounded_pred_max", row["wall_phase_pred_max"])
        row.setdefault("wall_clamp_delta_min", "0")
        row.setdefault("wall_clamp_delta_max", "0")
    return rows


def key(row: dict[str, str]) -> tuple[int, int]:
    return CASE_ORDER.index(row["case_id"]), 0 if row["variant"] == "baseline" else 1


def as_float(row: dict[str, str], name: str) -> float:
    return float(row[name])


def write_combined_csv(rows: list[dict[str, str]], path: Path) -> None:
    fields = [
        "variant",
        "case_id",
        "geometry",
        "theta_deg",
        "step",
        "wall_phase_pred_gt_1_count",
        "wall_phase_field_gt_1_count",
        "fluid_phase_field_gt_1_count",
        "wall_phase_bounded_pred_gt_1_count",
        "wall_clamp_delta_nonzero_count",
        "wall_phase_pred_max",
        "wall_phase_bounded_pred_max",
        "wall_clamp_delta_max",
        "phase_wall_max",
        "phase_fluid_max",
        "max_mach",
        "nonfinite_count",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in sorted(rows, key=key):
            writer.writerow(row)


def plot_metrics(rows: list[dict[str, str]], out_path: Path) -> None:
    lookup = {(row["case_id"], row["variant"]): row for row in rows}
    x = np.arange(len(CASE_ORDER))
    width = 0.38
    labels = [case.replace("_theta", "\n") for case in CASE_ORDER]
    panels = [
        ("wall_phase_pred_gt_1_count", "Raw WallPhasePred > 1", "count", True),
        ("wall_phase_field_gt_1_count", "Actual Wall PhaseField > 1", "count", True),
        ("fluid_phase_field_gt_1_count", "Fluid PhaseField > 1", "count", True),
        ("wall_phase_pred_max", "Max Raw WallPhasePred", "value", False),
        ("phase_wall_max", "Max Actual Wall PhaseField", "value", False),
        ("max_mach", "Max Mach", "Ma", False),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(16, 8.5))
    for ax, (field, title, ylabel, logy) in zip(axes.ravel(), panels):
        baseline = [as_float(lookup[(case, "baseline")], field) for case in CASE_ORDER]
        bounded = [as_float(lookup[(case, "bounded")], field) for case in CASE_ORDER]
        ax.bar(x - width / 2, baseline, width, label="baseline", color="#5762d5")
        ax.bar(x + width / 2, bounded, width, label="bounded diagnostic", color="#e08d3c")
        ax.set_title(title)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8)
        ax.set_ylabel(ylabel)
        ax.grid(True, axis="y", alpha=0.25)
        if logy:
            ymax = max(max(baseline), max(bounded), 1.0)
            ax.set_yscale("symlog", linthresh=1.0)
            ax.set_ylim(0, ymax * 1.5)
        if field in {"wall_phase_pred_max", "phase_wall_max"}:
            ax.axhline(1.0, color="black", linewidth=0.9, linestyle="--", alpha=0.7)
    axes[0, 0].legend(loc="upper right", fontsize=9)
    fig.suptitle("TCLB Geometric Wetting Wall Diagnostic: Baseline vs Bounded Control, Step 50")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def plot_rad011_montage(baseline_dir: Path, bounded_dir: Path, out_path: Path) -> None:
    image_specs = [
        (baseline_dir / "flat_theta011_step00000050_diagnostics.png", "baseline flat 11 deg"),
        (bounded_dir / "flat_theta011_step00000050_diagnostics.png", "bounded flat 11 deg"),
        (baseline_dir / "curved_theta011_step00000050_diagnostics.png", "baseline curved 11 deg"),
        (bounded_dir / "curved_theta011_step00000050_diagnostics.png", "bounded curved 11 deg"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(17, 11))
    for ax, (path, title) in zip(axes.ravel(), image_specs):
        ax.imshow(mpimg.imread(path))
        ax.set_title(title)
        ax.axis("off")
    fig.suptitle("radAngle 11 deg Diagnostic Slices: Baseline vs Bounded Control")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-rad011-csv", type=Path, required=True)
    parser.add_argument("--baseline-rad030090-csv", type=Path, required=True)
    parser.add_argument("--bounded-csv", type=Path, required=True)
    parser.add_argument("--baseline-rad011-figures", type=Path, required=True)
    parser.add_argument("--bounded-figures", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    baseline = read_rows(args.baseline_rad011_csv, "baseline")
    baseline.extend(read_rows(args.baseline_rad030090_csv, "baseline"))
    bounded = read_rows(args.bounded_csv, "bounded")
    rows = [
        row
        for row in baseline + bounded
        if int(float(row["step"])) == 50 and row["case_id"] in CASE_ORDER
    ]
    write_combined_csv(rows, args.out_dir / "wall_geom_bounded_vs_baseline_step50.csv")
    plot_metrics(rows, args.out_dir / "wall_geom_bounded_vs_baseline_step50_metrics.png")
    plot_rad011_montage(
        args.baseline_rad011_figures,
        args.bounded_figures,
        args.out_dir / "wall_geom_bounded_vs_baseline_rad011_montage.png",
    )


if __name__ == "__main__":
    main()
