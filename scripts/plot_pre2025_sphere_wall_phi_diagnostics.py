#!/usr/bin/env python3
"""Plot wall PhaseField diagnostics for the PRE sphere theta030 audit."""

from __future__ import annotations

import json
import pathlib

import matplotlib.pyplot as plt
import pandas as pd


ROOT = pathlib.Path(
    r"C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts"
    r"\pre2025_sphere_theta030_radAngle011_M0p1_W6_600k_interrupted_20260610"
    r"\source_audit"
)
OUT = ROOT / "figures"


def plot_phi_split() -> None:
    phi_rows = json.loads((ROOT / "phi_overshoot_audit.json").read_text(encoding="utf-8"))
    ctx = pd.read_csv(ROOT / "boundary_phi_context" / "boundary_phi_context_summary.csv")
    df = pd.DataFrame(phi_rows)

    fig, ax1 = plt.subplots(figsize=(7.4, 4.5), dpi=180)
    ax1.plot(df["step"], df["phi_max_fluid"], marker="o", label="fluid phi max")
    ax1.plot(df["step"], df["phi_max_boundary"], marker="o", label="boundary phi max")
    ax1.axhline(1.0, color="0.25", linestyle="--", linewidth=1.0, label="phi=1")
    ax1.set_xlabel("Step")
    ax1.set_ylabel("PhaseField max")
    ax1.set_title("PRE sphere theta030: fluid/boundary PhaseField split")
    ax1.grid(True, alpha=0.25)

    ax2 = ax1.twinx()
    ax2.bar(ctx["step"], ctx["boundary_over1_count"], width=12000, alpha=0.18, color="tab:red", label="boundary phi>1 count")
    ax2.set_ylabel("boundary phi>1 count")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "theta030_wall_phi_fluid_boundary_split.png")
    plt.close(fig)


def plot_formula_reproduction() -> None:
    df = pd.read_csv(ROOT / "geometric_wall_formula" / "geometric_wall_formula_summary.csv")

    fig, ax1 = plt.subplots(figsize=(7.4, 4.5), dpi=180)
    ax1.plot(df["step"], df["wall_phi_max"], marker="o", label="actual boundary phi max")
    ax1.plot(df["step"], df["predicted_wall_phi_max"], marker="x", linestyle="--", label="formula predicted phi max")
    ax1.set_xlabel("Step")
    ax1.set_ylabel("Boundary PhaseField")
    ax1.set_title("Geometric wall formula reproduces boundary overshoot")
    ax1.grid(True, alpha=0.25)

    ax2 = ax1.twinx()
    ax2.semilogy(df["step"], df["abs_prediction_error_max"], marker="s", color="tab:green", label="max abs prediction error")
    ax2.set_ylabel("max abs error")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "theta030_geometric_wall_formula_reproduction.png")
    plt.close(fig)


def plot_angle_sensitivity() -> None:
    df = pd.read_csv(ROOT / "geometric_wall_angle_sensitivity" / "geometric_wall_angle_sensitivity_summary.csv")
    pivot_count = df.pivot(index="step", columns="angle_deg", values="pred_over1_count")
    pivot_max = df.pivot(index="step", columns="angle_deg", values="pred_phi_max")

    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.4), dpi=180)
    for angle in pivot_count.columns:
        axes[0].plot(pivot_count.index, pivot_count[angle], marker="o", label=f"{angle:g} deg")
        axes[1].plot(pivot_max.index, pivot_max[angle], marker="o", label=f"{angle:g} deg")

    axes[0].set_xlabel("Step")
    axes[0].set_ylabel("Predicted boundary phi>1 count")
    axes[0].set_title("Formula replay: overshoot count")
    axes[0].grid(True, alpha=0.25)

    axes[1].set_xlabel("Step")
    axes[1].set_ylabel("Predicted boundary phi max")
    axes[1].axhline(1.0, color="0.25", linestyle="--", linewidth=1.0)
    axes[1].set_title("Formula replay: maximum boundary phi")
    axes[1].grid(True, alpha=0.25)
    axes[1].legend(loc="upper right", fontsize=7, ncol=2)

    fig.tight_layout()
    fig.savefig(OUT / "theta030_geometric_wall_angle_sensitivity.png")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    plot_phi_split()
    plot_formula_reproduction()
    plot_angle_sensitivity()
    print(OUT)


if __name__ == "__main__":
    main()
