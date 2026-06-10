#!/usr/bin/env python3
"""Compare PRE sphere theta030 controls with the profile wall candidate."""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np


@dataclass(frozen=True)
class CaseSpec:
    label: str
    root: Path
    color: str
    wall_diag: bool = False
    morphology: Path | None = None


def numeric(value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return math.nan
    return out if math.isfinite(out) else math.nan


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def metrics_path(case: CaseSpec) -> Path:
    return case.root / "analysis_pre2025_sphere" / "pre2025_sphere_metrics.csv"


def summary_path(case: CaseSpec) -> Path:
    return case.root / "analysis_pre2025_sphere" / "pre2025_sphere_summary.json"


def wall_path(case: CaseSpec) -> Path:
    return case.root / "analysis_wall_diag" / "pre2025_sphere_wall_diag_summary.json"


def final_row(case: CaseSpec) -> dict[str, Any]:
    summary = read_json(summary_path(case))
    final = summary.get("final", {})
    wall = read_json(wall_path(case))
    wall_final = wall.get("summaries", [{}])[-1] if wall else {}
    return {
        "label": case.label,
        "final_step": summary.get("final_step", ""),
        "H1_minus_H2_error_percent": final.get("H1_minus_H2_relative_error_percent", ""),
        "measured_H1_minus_H2_lu": final.get("measured_H1_minus_H2_lu", ""),
        "fit_contact_angle_deg": final.get("fit_contact_angle_deg", ""),
        "fit_angle_offset_deg": numeric(final.get("fit_contact_angle_deg")) - 30.0,
        "fluid_phase_drift_percent": 100.0 * numeric(final.get("fluid_phase_sum_rel_change")),
        "fluid_rho_drift_percent": 100.0 * numeric(final.get("fluid_rho_sum_rel_change")),
        "phase_max": final.get("phase_max", ""),
        "max_mach": summary.get("max_mach_fluid", ""),
        "max_nonfinite_count": summary.get("max_nonfinite_count", ""),
        "wall_phase_pred_gt_1_count": wall_final.get("wall_phase_pred_gt_1_count", ""),
        "wall_phase_field_gt_1_count": wall_final.get("wall_phase_field_gt_1_count", ""),
        "fluid_phase_field_gt_1_count": wall_final.get("fluid_phase_field_gt_1_count", ""),
        "wall_phase_pred_max": wall_final.get("wall_phase_pred", {}).get("max", ""),
        "wall_phase_profile_pred_max": wall_final.get("wall_phase_profile_pred", {}).get("max", ""),
        "phase_wall_max": wall_final.get("phase_wall", {}).get("max", ""),
        "phase_fluid_max": wall_final.get("phase_fluid", {}).get("max", ""),
    }


def write_summary(cases: list[CaseSpec], out: Path) -> list[dict[str, Any]]:
    rows = [final_row(case) for case in cases]
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return rows


def plot_timeseries(cases: list[CaseSpec], out: Path) -> None:
    panels = [
        ("H1_minus_H2_relative_error_percent", "H1-H2 error", "%"),
        ("fit_contact_angle_deg", "Fitted angle", "deg"),
        ("fluid_phase_sum_rel_change", "Fluid phase drift", "%"),
        ("phase_max", "PhaseField max", "value"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True)
    for case in cases:
        rows = read_csv(metrics_path(case))
        if not rows:
            continue
        step = [numeric(row.get("step")) for row in rows]
        for ax, (field, title, ylabel) in zip(axes.ravel(), panels):
            values = [numeric(row.get(field)) for row in rows]
            if field == "fluid_phase_sum_rel_change":
                values = [100.0 * v for v in values]
            ax.plot(step, values, color=case.color, label=case.label)
            ax.set_title(title)
            ax.set_ylabel(ylabel)
            ax.grid(True, alpha=0.25)
            ax.set_xlabel("step")
    axes[0, 1].axhline(30.0, color="0.2", linestyle="--", linewidth=0.9)
    axes[1, 1].axhline(1.0, color="0.2", linestyle="--", linewidth=0.9)
    axes[0, 0].legend(loc="best", fontsize=8)
    fig.suptitle("PRE sphere theta030: profile candidate vs earlier TCLB controls")
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)


def plot_final_bars(rows: list[dict[str, Any]], out: Path) -> None:
    labels = [row["label"].replace(" ", "\n") for row in rows]
    x = np.arange(len(rows))
    panels = [
        ("H1_minus_H2_error_percent", "H1-H2 error (%)", False),
        ("fit_contact_angle_deg", "Fitted angle (deg)", False),
        ("fluid_phase_drift_percent", "Fluid phase drift (%)", False),
        ("phase_max", "PhaseField max", False),
        ("max_mach", "Max Mach", False),
        ("wall_phase_pred_gt_1_count", "Raw wall pred > 1", True),
    ]
    colors = ["#1f77b4", "#ff7f0e", "#d62728", "#2ca02c"][: len(rows)]
    fig, axes = plt.subplots(2, 3, figsize=(16, 8.5))
    for ax, (field, title, logy) in zip(axes.ravel(), panels):
        values = [numeric(row.get(field)) for row in rows]
        ax.bar(x, values, color=colors)
        ax.set_title(title)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=7)
        ax.grid(True, axis="y", alpha=0.25)
        if logy:
            ymax = max([v for v in values if math.isfinite(v)] + [1.0])
            ax.set_yscale("symlog", linthresh=1.0)
            ax.set_ylim(0, ymax * 1.4)
        if field == "fit_contact_angle_deg":
            ax.axhline(30.0, color="0.2", linestyle="--", linewidth=0.9)
        if field == "phase_max":
            ax.axhline(1.0, color="0.2", linestyle="--", linewidth=0.9)
    fig.suptitle("PRE sphere theta030 final metrics at 200k")
    fig.tight_layout()
    fig.savefig(out, dpi=180)
    plt.close(fig)


def plot_morphology(profile_gallery: Path, out: Path) -> None:
    if not profile_gallery.exists():
        return
    img = mpimg.imread(profile_gallery)
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.imshow(img)
    ax.axis("off")
    ax.set_title("Profile candidate theta030 morphology gallery")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    root = args.artifact_root
    cases = [
        CaseSpec(
            "baseline M0.1 W6",
            root
            / "tclb_pre2025_sphere_tableII_q27_geometric_theta030_radAngle011_param_sensitivity_200k_20260610"
            / "M0p1_W6"
            / "theta030",
            "#1f77b4",
        ),
        CaseSpec(
            "baseline M0.2 W6",
            root
            / "pre2025_sphere_tableII_q27_geometric_theta030_radAngle011_200k_20260610"
            / "theta030",
            "#ff7f0e",
        ),
        CaseSpec(
            "baseline M0.2 W8",
            root
            / "tclb_pre2025_sphere_tableII_q27_geometric_theta030_radAngle011_param_sensitivity_200k_20260610"
            / "M0p2_W8"
            / "theta030",
            "#d62728",
        ),
        CaseSpec(
            "profile M0.1 W6",
            root / "pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_200k_20260610" / "theta030",
            "#2ca02c",
            wall_diag=True,
            morphology=root
            / "pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_200k_20260610"
            / "theta030"
            / "analysis_morphology"
            / "theta030_frame_gallery.png",
        ),
    ]
    rows = write_summary(cases, args.out_dir / "pre2025_sphere_theta030_profile_candidate_summary.csv")
    plot_timeseries(cases, args.out_dir / "pre2025_sphere_theta030_profile_candidate_timeseries.png")
    plot_final_bars(rows, args.out_dir / "pre2025_sphere_theta030_profile_candidate_final_bars.png")
    plot_morphology(
        cases[-1].morphology or Path(),
        args.out_dir / "pre2025_sphere_theta030_profile_candidate_morphology_gallery.png",
    )


if __name__ == "__main__":
    main()
