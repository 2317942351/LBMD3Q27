#!/usr/bin/env python3
"""Digest Stage14-B26 sparse full-field probes.

B26 is diagnostic-only. It compares a legacy force-density denominator probe
with a density-floor shadow/probe run and classifies the earliest supported
instability path as denominator, numerator, stress-time-level, or unresolved.
It does not validate contact angle and does not promote any physics mode.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


SUMMARY_NAME = "b26_key_summary.json"
STATS_NAME = "b26_mask_stats.csv"

ONSET_KEYS = [
    "first_b22_momentum_speed_onset",
    "first_b22_m0_speed_onset",
    "first_b22_phase_adv_speed_onset",
    "first_b21_heq_mach_onset",
    "first_phase_from_h_onset",
    "first_b22_force_over_rho_onset",
    "first_b22_force_total_onset",
    "first_b22_force_mu_onset",
    "first_b22_force_surf_onset",
    "first_b22_force_pressure_onset",
    "first_force_over_rho_onset",
    "first_fmu_raw_onset",
    "first_stress_post_onset",
    "first_stress_input_onset",
    "first_b18_stress_post_onset",
    "first_b18_stress_amp_onset",
    "first_b18_force_raw_onset",
    "first_b18_force_floor_onset",
    "first_b18_force_phase_mix_onset",
]

FIELDS_OF_INTEREST = {
    "ReplayForceRhoRaw",
    "ReplayForceRhoEffective",
    "ReplayRhoForForce",
    "ReplayForceOverRhoNorm",
    "B22ForceRhoRaw",
    "B22ForceRhoEffective",
    "B22ForceOverRhoMag",
    "B22FtotalMag",
    "B22FmuMag",
    "B22FsurfMag",
    "B22FpressureMag",
    "B22MomentumSpeed",
    "B22M0Speed",
    "B22PhaseAdvSpeed",
    "ReplayMu",
    "ReplayGradPhiNorm",
    "ReplayFsurfNorm",
    "FmuRawNorm",
    "StressPreForceNorm",
    "StressPostForceNorm",
    "StressInputNorm",
    "StressIter1Norm",
    "B18StressPostOverPre",
    "B18ForceOverRhoRawNorm",
    "B18ForceOverRhoDensityFloorNorm",
    "B18ForceOverRhoPhaseMixtureNorm",
    "B18RhoDenominatorRaw",
    "B18RhoDenominatorFloor",
    "B18RhoDenominatorPhaseMix",
    "ReplayPhaseFromH",
    "B21HeqVelocityMachShadow",
    "B21HeqMaxAbs",
    "B21HPostMaxAbs",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def onset_step(summary: dict[str, Any], key: str) -> int | None:
    value = summary.get(key)
    if isinstance(value, dict) and value.get("step") is not None:
        return int(value["step"])
    return None


def onset_value(summary: dict[str, Any], key: str) -> Any:
    value = summary.get(key)
    if isinstance(value, dict):
        return value.get("value")
    return None


def onset_mask(summary: dict[str, Any], key: str) -> Any:
    value = summary.get(key)
    if isinstance(value, dict):
        return value.get("mask")
    return None


def read_metadata(probe_dir: Path) -> dict[str, Any]:
    matches = sorted(probe_dir.glob("*/case_metadata.json"))
    if not matches:
        return {}
    return load_json(matches[0])


def read_stats(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def to_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def stats_lookup(rows: list[dict[str, str]], field: str, step: int | None, mask: str | None) -> dict[str, str] | None:
    if step is None:
        return None
    candidates = [
        row for row in rows
        if row.get("field") == field and int(float(row.get("step", "-1"))) == step
    ]
    if mask:
        for row in candidates:
            if row.get("mask") == mask:
                return row
    for fallback in ("low_rho", "near_interface_wall", "all_cells"):
        for row in candidates:
            if row.get("mask") == fallback:
                return row
    return candidates[0] if candidates else None


def stat_value(rows: list[dict[str, str]], field: str, step: int | None, mask: str | None, column: str = "max_abs") -> float | None:
    row = stats_lookup(rows, field, step, mask)
    if row is None:
        return None
    return to_float(row.get(column))


def earliest(*steps: int | None) -> int | None:
    present = [step for step in steps if step is not None]
    return min(present) if present else None


def classify(summary: dict[str, Any], rows: list[dict[str, str]]) -> tuple[str, str]:
    momentum_step = onset_step(summary, "first_b22_momentum_speed_onset")
    m0_step = onset_step(summary, "first_b22_m0_speed_onset")
    force_rho_step = onset_step(summary, "first_b22_force_over_rho_onset")
    fmu_step = onset_step(summary, "first_b22_force_mu_onset")
    fsurf_step = onset_step(summary, "first_b22_force_surf_onset")
    pressure_step = onset_step(summary, "first_b22_force_pressure_onset")
    phase_step = onset_step(summary, "first_phase_from_h_onset")
    stress_post_step = onset_step(summary, "first_stress_post_onset") or onset_step(summary, "first_b18_stress_post_onset")
    stress_amp_step = onset_step(summary, "first_b18_stress_amp_onset")

    force_mask = onset_mask(summary, "first_b22_force_over_rho_onset")
    force_step = force_rho_step or momentum_step
    raw_rho = stat_value(rows, "B22ForceRhoRaw", force_step, force_mask, "min")
    eff_rho = stat_value(rows, "B22ForceRhoEffective", force_step, force_mask, "min")
    ftotal = stat_value(rows, "B22FtotalMag", force_step, force_mask)
    force_over_rho = stat_value(rows, "B22ForceOverRhoMag", force_step, force_mask)

    numerator_first = earliest(fmu_step, fsurf_step, pressure_step)
    stress_first = earliest(stress_post_step, stress_amp_step)
    observable_first = earliest(force_rho_step, momentum_step, m0_step, phase_step, numerator_first)
    denominator_floor_changes = (
        raw_rho is not None and eff_rho is not None and eff_rho > raw_rho * 1.01
    )

    if force_rho_step is not None and momentum_step is not None and force_rho_step <= momentum_step:
        if denominator_floor_changes:
            return (
                "denominator_supported",
                "F/rho crosses no later than momentum speed and effective rho differs from raw rho at onset.",
            )
        if raw_rho is not None and raw_rho <= 0.01 and ftotal is not None and force_over_rho is not None:
            if abs(ftotal) < abs(force_over_rho):
                return (
                    "denominator_supported",
                    "Low raw rho at F/rho onset amplifies a smaller F_total into a large acceleration.",
                )

    if stress_first is not None and observable_first is not None and stress_first <= observable_first:
        return (
            "stress_time_level_supported",
            "B18 stress/stress-amplification crosses before the first force, velocity, or phase onset.",
        )

    if numerator_first is not None and observable_first is not None and numerator_first <= observable_first:
        return (
            "numerator_supported",
            "F_mu/F_surf/F_pressure component crosses before or with the first observed force, velocity, or phase onset.",
        )

    if phase_step is not None and phase_step <= earliest(force_rho_step, momentum_step, numerator_first):
        return (
            "phase_first_unresolved",
            "PhaseFromH exits bounds before configured force/momentum thresholds.",
        )

    return (
        "mixed_or_unresolved",
        "Configured thresholds do not isolate denominator, numerator, or stress time-level first.",
    )


def probe_dirs(root: Path) -> list[Path]:
    return sorted(path for path in root.iterdir() if path.is_dir() and (path / SUMMARY_NAME).exists())


def build_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for probe_dir in probe_dirs(root):
        summary = load_json(probe_dir / SUMMARY_NAME)
        stats = read_stats(probe_dir / STATS_NAME)
        metadata = read_metadata(probe_dir)
        classification, reason = classify(summary, stats)
        row: dict[str, Any] = {
            "probe": probe_dir.name,
            "summary": str(probe_dir / SUMMARY_NAME),
            "classification": classification,
            "classification_reason": reason,
            "primary_branch": summary.get("primary_branch"),
            "b18_primary_branch": summary.get("b18_primary_branch"),
            "b20_primary_branch": summary.get("b20_primary_branch"),
            "b21_primary_branch": summary.get("b21_primary_branch"),
            "b22_primary_branch": summary.get("b22_primary_branch"),
            "binary_sha256": metadata.get("binary_sha256"),
            "iterations": metadata.get("iterations"),
            "density_l": metadata.get("density_l"),
            "momentum_force_mode": metadata.get("momentum_force_mode"),
            "pressure_closure_mode": metadata.get("pressure_closure_mode"),
            "force_density_closure_mode": metadata.get("force_density_closure_mode"),
            "force_fixed_point_mode": metadata.get("force_fixed_point_mode"),
        }
        for key in ONSET_KEYS:
            row[f"{key}_step"] = onset_step(summary, key)
            row[f"{key}_value"] = onset_value(summary, key)
            row[f"{key}_mask"] = onset_mask(summary, key)

        onset = row.get("first_b22_force_over_rho_onset_step") or row.get("first_b22_momentum_speed_onset_step")
        mask = row.get("first_b22_force_over_rho_onset_mask") or row.get("first_b22_momentum_speed_onset_mask")
        for field in sorted(FIELDS_OF_INTEREST):
            row[f"at_onset_{field}_max_abs"] = stat_value(stats, field, onset, mask, "max_abs")
            if field in {"B22ForceRhoRaw", "B22ForceRhoEffective", "B18RhoDenominatorRaw", "B18RhoDenominatorFloor", "B18RhoDenominatorPhaseMix"}:
                row[f"at_onset_{field}_min"] = stat_value(stats, field, onset, mask, "min")
        rows.append(row)
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_probe = {row["probe"]: row["classification"] for row in rows}
    fd0 = next((row for row in rows if row.get("force_density_closure_mode") == 0), None)
    fd1 = next((row for row in rows if row.get("force_density_closure_mode") == 1), None)
    delay = None
    if fd0 and fd1:
        s0 = fd0.get("first_b22_momentum_speed_onset_step")
        s1 = fd1.get("first_b22_momentum_speed_onset_step")
        if isinstance(s0, int) and isinstance(s1, int):
            delay = s1 - s0
    conclusion = "unresolved"
    if any(row["classification"] == "stress_time_level_supported" for row in rows):
        conclusion = "stress_time_level_priority"
    elif any(row["classification"] == "numerator_supported" for row in rows):
        conclusion = "numerator_priority"
    elif any(row["classification"] == "denominator_supported" for row in rows):
        conclusion = "denominator_priority"
    return {
        "claim_limit": "diagnostic-only; not contact-angle validation and not a physics fix",
        "probe_classifications": by_probe,
        "fd1_momentum_delay_steps": delay,
        "b26_conclusion": conclusion,
        "next_required_action": (
            "Design B27 only after reviewing B26 digest and argmax/mask evidence; "
            "do not promote ForceDensityClosureMode or MomentumForceMode as physical fixes."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()

    rows = build_rows(args.root)
    result = {"rows": rows, "aggregate": aggregate(rows)}
    if args.csv:
        write_csv(args.csv, rows)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
