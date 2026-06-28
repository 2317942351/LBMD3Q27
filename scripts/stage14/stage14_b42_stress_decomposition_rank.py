#!/usr/bin/env python3
"""Summarize Stage14-B42 isotropic/deviatoric stress diagnostics."""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any


SOURCES = [
    ("legacy", "B42LegacyIsotropicNorm", "B42LegacyDeviatoricNorm", "B42FmuLegacyDeviatoricNorm", "B42ForceOverRhoLegacyDeviatoricNorm"),
    ("raw", "B42RawIsotropicNorm", "B42RawDeviatoricNorm", "B42FmuRawDeviatoricNorm", "B42ForceOverRhoRawDeviatoricNorm"),
    ("bgk", "B42BGKIsotropicNorm", "B42BGKDeviatoricNorm", "B42FmuBGKDeviatoricNorm", "B42ForceOverRhoBGKDeviatoricNorm"),
    ("post", "B42PostIsotropicNorm", "B42PostDeviatoricNorm", None, None),
]


def fnum(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        out = float(value)
    except ValueError:
        return None
    return out if math.isfinite(out) else None


def load(path: Path) -> list[dict[str, Any]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["step"] = int(row["step"])
        row["max_abs"] = fnum(row.get("max_abs"))
        row["present"] = str(row.get("present", "")).lower() == "true"
    return rows


def idx(rows: list[dict[str, Any]]) -> dict[tuple[str, str, int], dict[str, Any]]:
    return {
        (str(row["field"]), str(row["mask"]), int(row["step"])): row
        for row in rows
        if row.get("present")
    }


def val(index: dict[tuple[str, str, int], dict[str, Any]], field: str | None, mask: str, step: int) -> float | None:
    if field is None:
        return None
    row = index.get((field, mask, step))
    return None if row is None else row.get("max_abs")


def focus_step(rows: list[dict[str, Any]], preferred: int | None) -> int:
    steps = sorted({int(row["step"]) for row in rows})
    if preferred is not None and preferred in steps:
        return preferred
    for row in rows:
        if row["field"] == "ForceOverRhoNorm" and row["mask"] == "low_rho" and row.get("max_abs") and row["max_abs"] > 1.0e3:
            return int(row["step"])
    return steps[-1]


def summarize(mask_stats: Path, preferred_step: int | None) -> dict[str, Any]:
    rows = load(mask_stats)
    index = idx(rows)
    step = focus_step(rows, preferred_step)
    mask = "low_rho"
    legacy_force = val(index, "B40ForceOverRhoMomentRelaxedLegacyNorm", mask, step)
    source_rows: list[dict[str, Any]] = []
    for name, iso_field, dev_field, fmu_field, force_field in SOURCES:
        iso = val(index, iso_field, mask, step)
        dev = val(index, dev_field, mask, step)
        fmu = val(index, fmu_field, mask, step)
        force = val(index, force_field, mask, step)
        source_rows.append(
            {
                "source": name,
                "isotropic_norm": iso,
                "deviatoric_norm": dev,
                "iso_over_dev": (iso / dev) if iso is not None and dev not in (None, 0.0) else None,
                "fmu_deviatoric_norm": fmu,
                "force_over_rho_deviatoric_norm": force,
                "force_vs_legacy": (force / legacy_force) if force is not None and legacy_force not in (None, 0.0) else None,
            }
        )
    candidates = [row for row in source_rows if row["source"] in {"legacy", "raw", "bgk"} and row["force_over_rho_deviatoric_norm"] is not None]
    better = [row for row in candidates if row["force_over_rho_deviatoric_norm"] < 1000.0]
    if better:
        verdict = "b42_deviatoric_candidate_found"
        recommendation = "Use the best deviatoric stress candidate as a default-off active B43/B44 candidate after coefficient derivation."
    else:
        verdict = "b42_no_deviatoric_candidate"
        recommendation = "Deviatoric projection does not reduce the force-over-rho shadow below threshold; escalate to B43 stress-scale/forcing derivation."
    return {
        "claim_limit": "B42 shadow-only stress decomposition; not a solver repair",
        "input_mask_stats": str(mask_stats),
        "focus_step": step,
        "mask": mask,
        "legacy_force_over_rho": legacy_force,
        "sources": source_rows,
        "verdict": verdict,
        "recommendation": recommendation,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = ["source", "isotropic_norm", "deviatoric_norm", "iso_over_dev", "fmu_deviatoric_norm", "force_over_rho_deviatoric_norm", "force_vs_legacy"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fields})


def fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def write_md(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Stage14-B42 Stress Decomposition Audit",
        "",
        "Status: shadow-only diagnostic. This is not a solver repair or contact-angle validation.",
        "",
        f"Input stats: `{summary['input_mask_stats']}`",
        f"Focus step: `{summary['focus_step']}`",
        f"Mask: `{summary['mask']}`",
        f"Legacy F/rho: `{fmt(summary['legacy_force_over_rho'])}`",
        f"Verdict: `{summary['verdict']}`",
        "",
        "| source | isotropic | deviatoric | iso/dev | dev F_mu | dev F/rho | dev F/rho / legacy |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["sources"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    row["source"],
                    fmt(row["isotropic_norm"]),
                    fmt(row["deviatoric_norm"]),
                    fmt(row["iso_over_dev"]),
                    fmt(row["fmu_deviatoric_norm"]),
                    fmt(row["force_over_rho_deviatoric_norm"]),
                    fmt(row["force_vs_legacy"]),
                ]
            )
            + " |"
        )
    lines.extend(["", "## Recommendation", "", summary["recommendation"], ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mask_stats", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--focus-step", type=int, default=None)
    parser.add_argument("--prefix", default="b42")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    summary = summarize(args.mask_stats, args.focus_step)
    (args.out_dir / f"{args.prefix}_stress_decomposition_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    write_csv(args.out_dir / f"{args.prefix}_stress_decomposition_summary.csv", summary["sources"])
    write_md(args.out_dir / f"{args.prefix}_stress_decomposition_summary.md", summary)
    print(json.dumps({"verdict": summary["verdict"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
