#!/usr/bin/env python3
"""Convergence triplet plot for a Stage12 validation case.

Reads the TCLB globals CSV (case_Log_P00_*.csv) and plots three panels:
  (a) TotalDensity vs Iteration  -- mass conservation (should be flat)
  (b) KineticEnergy vs Iteration  -- log-y, decay toward equilibrium plateau
  (c) LiqTotalVelocity vs Iteration -- spurious-current proxy (should decay)

A flat TotalDensity + decaying-and-plateauing KE is the primary evidence that
the case has reached static equilibrium (so the measured contact angle is
meaningful, not a transient).

Usage: python3 stage12_convergence_plot.py <case_dir> [--out png]
       <case_dir> contains output/case_Log_P00_*.csv and case_metadata.json
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def read_globals_csv(csv_path: Path) -> dict[str, np.ndarray]:
    """Read TCLB globals CSV. Returns dict of column-name -> float array.
    Columns are quoted in the header; values are bare."""
    with csv_path.open("r", encoding="utf-8", errors="replace") as f:
        reader = csv.reader(f)
        header = [h.strip().strip('"') for h in next(reader)]
        rows = []
        for row in reader:
            if not row or all(c == "" for c in row):
                continue
            rows.append(row)
    if not rows:
        return {}
    data = np.array(rows, dtype=float)
    # pad short rows with NaN
    if data.shape[1] < len(header):
        pad = np.full((data.shape[0], len(header) - data.shape[1]), np.nan)
        data = np.hstack([data, pad])
    return {header[i]: data[:, i] for i in range(min(len(header), data.shape[1]))}


def find_log_csv(case_dir: Path) -> Path | None:
    candidates = sorted((case_dir / "output").glob("case_Log_P00_*.csv"))
    return candidates[-1] if candidates else None


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("case_dir", type=Path, help="case directory with output/ subdir")
    p.add_argument("--out", type=Path, default=None, help="output PNG path")
    p.add_argument("--title", default="")
    args = p.parse_args()

    csv_path = find_log_csv(args.case_dir)
    if csv_path is None:
        print(f"ERROR: no case_Log_P00_*.csv in {args.case_dir}/output/", file=sys.stderr)
        return 1

    meta_path = args.case_dir / "case_metadata.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}

    g = read_globals_csv(csv_path)
    if "Iteration" not in g:
        print(f"ERROR: no Iteration column in {csv_path}", file=sys.stderr)
        return 1

    it = g["Iteration"]
    td = g.get("TotalDensity", np.full_like(it, np.nan))
    ke = g.get("KineticEnergy", np.full_like(it, np.nan))
    lv = g.get("LiqTotalVelocity", np.full_like(it, np.nan))

    # convergence assessment
    n = len(it)
    last10 = slice(max(0, n - max(1, n // 10)), n)
    td_drift = (np.nanmax(td[last10]) - np.nanmin(td[last10])) / max(abs(np.nanmean(td[last10])), 1e-30)
    ke_init = np.nanmax(ke[np.isfinite(ke)]) if np.any(np.isfinite(ke)) else 1.0
    ke_end = np.nanmean(ke[last10]) if np.any(np.isfinite(ke[last10])) else float("nan")
    ke_ratio = ke_end / ke_init if ke_init > 0 else float("nan")

    geom = meta.get("geometry", "?")
    init_t = meta.get("init_theta_deg", "?")
    bc_t = meta.get("bc_theta_deg", "?")
    decoupled = bool(meta.get("decoupled", False))
    mode = "DECOUPLE" if decoupled else "EQUILIBRIUM"

    mass_ok = td_drift < 1e-4
    # Convergence criteria differ by mode:
    #   EQUILIBRIUM: KE must decay toward a plateau (interface disturbance dies
    #     out) -> ke_ratio (end/peak) should be small once peak is past.
    #   DECOUPLE: the interface is DRIVEN from init to bc, so KE necessarily
    #     rises during relaxation and may plateau high. KE decay is NOT a valid
    #     convergence signal here. Instead require KE to have stabilized in the
    #     last 10% (low end-to-end relative change), which means the relaxation
    #     motion has settled.
    if mode == "EQUILIBRIUM":
        ke_ok = ke_ratio < 0.10
    else:
        ke_last = ke[np.isfinite(ke)]
        if len(ke_last) >= 4:
            q = len(ke_last) // 2
            late = ke_last[q:]
            ke_end_drift = (np.nanmax(late) - np.nanmin(late)) / max(abs(np.nanmean(late)), 1e-30)
            ke_ok = ke_end_drift < 0.30  # KE plateaued (relative variation < 30%)
        else:
            ke_ok = False
    converged = mass_ok and ke_ok

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2), constrained_layout=True)
    base = f"{geom} {mode} init={init_t} bc={bc_t}"
    status = "CONVERGED" if converged else "NOT_CONVERGED"
    fig.suptitle(f"{base}\n{status}: mass_drift={td_drift:.2e}  KE_ratio={ke_ratio:.3f}", fontsize=11, fontweight="bold")

    axes[0].plot(it, td, color="#1f77b4", lw=1.2)
    axes[0].set_xlabel("Iteration")
    axes[0].set_ylabel("TotalDensity")
    axes[0].set_title(f"Mass (drift={td_drift:.1e})")
    axes[0].ticklabel_format(axis="y", style="scientific", scilimits=(0, 0))

    ke_pos = np.where(np.isfinite(ke) & (ke > 0))
    axes[1].semilogy(it[np.isfinite(ke)], np.where(ke[np.isfinite(ke)] > 0, ke[np.isfinite(ke)], np.nan), color="#d62728", lw=1.2)
    axes[1].set_xlabel("Iteration")
    axes[1].set_ylabel("KineticEnergy (log)")
    axes[1].set_title(f"KE decay (end/init={ke_ratio:.3f})")

    lv_pos = lv[np.isfinite(lv) & (lv > 0)]
    axes[2].semilogy(it[np.isfinite(lv) & (lv > 0)], lv_pos, color="#2ca02c", lw=1.2)
    axes[2].set_xlabel("Iteration")
    axes[2].set_ylabel("LiqTotalVelocity (log)")
    axes[2].set_title("Spurious currents")

    for ax in axes:
        ax.grid(True, alpha=0.3)

    out = args.out or (args.case_dir / f"{args.case_dir.name}_convergence.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=180)
    plt.close(fig)

    summary = {
        "case": args.case_dir.name,
        "mode": mode,
        "geometry": geom,
        "init_theta_deg": init_t,
        "bc_theta_deg": bc_t,
        "n_log_rows": int(n),
        "iterations_covered": [float(it[0]), float(it[-1])],
        "total_density_drift_rel": float(td_drift),
        "kinetic_energy_end_over_peak": float(ke_ratio),
        "mass_converged": bool(mass_ok),
        "ke_converged": bool(ke_ok),
        "converged": bool(converged),
        "figure": str(out),
    }
    (args.case_dir / f"{args.case_dir.name}_convergence.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
