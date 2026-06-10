#!/usr/bin/env python3
"""Plot profile-candidate wall diagnostic evolution."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def as_float(row: dict[str, str], field: str) -> float:
    return float(row[field])


def plot_case(rows: list[dict[str, str]], case_id: str, out_path: Path) -> None:
    rows = sorted([r for r in rows if r["case_id"] == case_id], key=lambda r: as_float(r, "step"))
    if not rows:
        raise SystemExit(f"missing rows for {case_id}")
    step = [as_float(r, "step") for r in rows]
    panels = [
        ("wall_phase_pred_gt_1_count", "Raw WallPhasePred > 1", "count", True),
        ("wall_phase_field_gt_1_count", "Actual Wall PhaseField > 1", "count", True),
        ("fluid_phase_field_gt_1_count", "Fluid PhaseField > 1", "count", True),
        ("wall_phase_pred_max", "Max Raw WallPhasePred", "value", False),
        ("wall_phase_profile_pred_max", "Max Profile Pred / Actual Wall", "value", False),
        ("max_mach", "Max Mach", "Ma", False),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    for ax, (field, title, ylabel, logy) in zip(axes.ravel(), panels):
        values = [as_float(r, field) for r in rows]
        ax.plot(step, values, marker="o", color="#2a9d68")
        ax.set_title(title)
        ax.set_xlabel("step")
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.25)
        if logy:
            ymax = max(max(values), 1.0)
            ax.set_yscale("symlog", linthresh=1.0)
            ax.set_ylim(0, ymax * 1.4)
        if field in {"wall_phase_pred_max", "wall_phase_profile_pred_max"}:
            ax.axhline(1.0, color="black", linewidth=0.9, linestyle="--", alpha=0.7)
    fig.suptitle(f"Profile Wall Diagnostic Evolution: {case_id}")
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    rows = read_rows(args.csv)
    for case_id in sorted({r["case_id"] for r in rows}):
        plot_case(rows, case_id, args.out_dir / f"{case_id}_profile_evolution.png")


if __name__ == "__main__":
    main()
