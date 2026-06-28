#!/usr/bin/env python3
"""Create Stage14-B46/B47 gate-decision artifacts from B43-B45 evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def low_rho_row(report: dict[str, Any], candidate: str) -> dict[str, Any] | None:
    return next(
        (
            row for row in report.get("rows", [])
            if row.get("mask") == "low_rho" and row.get("candidate") == candidate
        ),
        None,
    )


def build_decision(b43: dict[str, Any], b44: dict[str, Any], b45: dict[str, Any]) -> dict[str, Any]:
    b45_case = b45["cases"][0] if b45.get("cases") else {}
    first = b45_case.get("first_events", {})
    b43_legacy = low_rho_row(b43, "legacy") or {}
    b43_hundredth = low_rho_row(b43, "legacy_hundredth") or {}
    b44_hundredth = low_rho_row(b44, "legacy_hundredth") or {}
    b44_legacy = low_rho_row(b44, "legacy") or {}
    blocked = b45.get("verdict") != "b45_phase_gate_passed_window_only"
    verdict_b46 = "b46_blocked_by_b45_phase_boundedness" if blocked else "b46_ready_to_plan_flat_wall_gate"
    verdict_b47 = "b47_blocked_by_b45_phase_boundedness" if blocked else "b47_ready_after_b46_passes"
    return {
        "claim_limit": "B46/B47 gate decision only; no contact-angle or curved-wall validation claim",
        "b43": {
            "verdict": b43.get("verdict"),
            "legacy_low_rho_force_over_rho": b43.get("legacy_low_rho_force_over_rho"),
            "legacy_force_over_rho": b43_legacy.get("force_over_rho_norm_max"),
            "legacy_hundredth_force_over_rho": b43_hundredth.get("force_over_rho_norm_max"),
            "legacy_hundredth_note": "postprocess scale only; not a solver repair",
        },
        "b44": {
            "verdict": b44.get("verdict"),
            "legacy_net_over_term": b44_legacy.get("net_over_term_sum"),
            "legacy_hundredth_net_over_term": b44_hundredth.get("net_over_term_sum"),
            "legacy_hundredth_fmu_fraction": b44_hundredth.get("fmu_fraction_sum_mag"),
        },
        "b45": {
            "verdict": b45.get("verdict"),
            "case_verdict": b45_case.get("verdict"),
            "first_events": first,
        },
        "b46": {
            "verdict": verdict_b46,
            "not_executed": blocked,
            "reason": "PhaseFromH leaves [0,1] before force-over-rho explosion, so flat-wall contact angle morphology is not physically interpretable.",
            "minimum_reopen_gate": "B45 must run at least 100 steps with PhaseField and PhaseFromH bounded, no NaN, and force/rho finite without hard clamp.",
        },
        "b47": {
            "verdict": verdict_b47,
            "not_executed": blocked,
            "reason": "Curved-wall shadow/controlled-write gates depend on a bounded phase-field transport baseline. B45 failed before flat-wall physical validation.",
            "minimum_reopen_gate": "B46 flat-wall static and decoupled direction gates must pass before curved-wall shadow/write can be interpreted physically.",
        },
        "next_branch": {
            "name": "B48_h_population_phasefromh_timelevel_closure",
            "primary_target": "PhaseF -> h populations -> h update -> streaming -> PhaseFromH",
            "required_probe": "steps 0-4 full h population producer-consumer audit at first OOB cells",
            "do_not_do": [
                "do not promote F_mu scale-down as physical repair",
                "do not run contact-angle validation while B45 fails",
                "do not enter dynamic impact",
                "do not write curved-wall PhaseF",
            ],
        },
    }


def write_md(path: Path, report: dict[str, Any]) -> None:
    first = report["b45"]["first_events"]
    lines = [
        "# Stage14-B46/B47 Gate Decision",
        "",
        "Status: blocked gate decision. This is not contact-angle validation and not curved-wall validation.",
        "",
        "## Evidence Chain",
        "",
        f"- B43 verdict: `{report['b43']['verdict']}`.",
        f"- B43 legacy low-rho F/rho: `{fmt(report['b43']['legacy_force_over_rho'])}`.",
        f"- B43 legacy_hundredth low-rho F/rho: `{fmt(report['b43']['legacy_hundredth_force_over_rho'])}` (postprocess only).",
        f"- B44 verdict: `{report['b44']['verdict']}`.",
        f"- B44 legacy_hundredth net/term: `{fmt(report['b44']['legacy_hundredth_net_over_term'])}`.",
        f"- B44 legacy_hundredth F_mu fraction: `{fmt(report['b44']['legacy_hundredth_fmu_fraction'])}`.",
        f"- B45 verdict: `{report['b45']['verdict']}` / `{report['b45']['case_verdict']}`.",
        f"- B45 first PhaseFromH OOB step: `{fmt(first.get('phase_from_h_oob'))}`.",
        f"- B45 first HPost OOB step: `{fmt(first.get('hpost_oob'))}`.",
        f"- B45 first F/rho > 1000 step: `{fmt(first.get('force_over_rho_gt_1000'))}`.",
        "",
        "## B46 Decision",
        "",
        f"Verdict: `{report['b46']['verdict']}`",
        "",
        report["b46"]["reason"],
        "",
        f"Minimum reopen gate: {report['b46']['minimum_reopen_gate']}",
        "",
        "## B47 Decision",
        "",
        f"Verdict: `{report['b47']['verdict']}`",
        "",
        report["b47"]["reason"],
        "",
        f"Minimum reopen gate: {report['b47']['minimum_reopen_gate']}",
        "",
        "## Next Branch",
        "",
        f"Next: `{report['next_branch']['name']}`.",
        "",
        f"Primary target: `{report['next_branch']['primary_target']}`.",
        "",
        f"Required probe: {report['next_branch']['required_probe']}.",
        "",
        "Do not:",
    ]
    lines.extend(f"- {item}" for item in report["next_branch"]["do_not_do"])
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--b43", type=Path, required=True)
    parser.add_argument("--b44", type=Path, required=True)
    parser.add_argument("--b45", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--prefix", default="b46_b47")
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    report = build_decision(load(args.b43), load(args.b44), load(args.b45))
    (args.out_dir / f"{args.prefix}_gate_decision.json").write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )
    write_md(args.out_dir / f"{args.prefix}_gate_decision.md", report)
    print(json.dumps({"b46": report["b46"]["verdict"], "b47": report["b47"]["verdict"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
