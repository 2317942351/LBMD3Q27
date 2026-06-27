#!/usr/bin/env python3
"""Static TCLB stage/force-ordering audit for Stage14-B32.5.

This script is read-only. It does not compile or run TCLB. It parses the local
Stage17B snapshot and records whether the force-closure diagnostics are being
interpreted with the correct TCLB AddDensity/AddField and CollisionMRT ordering
semantics.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_MODEL = Path(
    "third_party/tclb_snapshots/stage17B_diffuse_solid_shadow/"
    "models/multiphase/d3q27_pf_velocity"
)


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str
    evidence: dict[str, Any]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def line_of(text: str, needle: str) -> int | None:
    index = text.find(needle)
    if index < 0:
        return None
    return text.count("\n", 0, index) + 1


def find_all_lines(text: str, pattern: str) -> list[int]:
    lines: list[int] = []
    regex = re.compile(pattern)
    for line_no, line in enumerate(text.splitlines(), start=1):
        if regex.search(line):
            lines.append(line_no)
    return lines


def add_kind_lines(dynamics_r: str, kind: str, names: list[str]) -> dict[str, list[int]]:
    out: dict[str, list[int]] = {}
    for name in names:
        pattern = rf'{kind}\(\s*(?:name\s*=\s*)?["\']{re.escape(name)}["\']'
        out[name] = find_all_lines(dynamics_r, pattern)
    return out


def first_line_matching(text: str, pattern: str) -> int | None:
    lines = find_all_lines(text, pattern)
    return lines[0] if lines else None


def status_for_all_present(mapping: dict[str, list[int]]) -> str:
    missing = [name for name, lines in mapping.items() if not lines]
    return "pass" if not missing else "fail"


def streamed_macro_status(add_density: dict[str, list[int]], add_field: dict[str, list[int]]) -> str:
    if status_for_all_present(add_density) == "fail":
        return "fail"
    # The TCLB model may define conditional OutFlow helper fields for U. Those
    # do not replace the primary Vel AddDensity streaming state, so keep them
    # visible as a warning rather than failing the semantics audit.
    return "warning" if any(add_field.values()) else "pass"


def order_check(dynamics_c: str, anchors: list[tuple[str, str]]) -> Check:
    positions: list[dict[str, Any]] = []
    last_pos = -1
    problems: list[str] = []
    for label, needle in anchors:
        pos = dynamics_c.find(needle, last_pos + 1)
        line = None if pos < 0 else dynamics_c.count("\n", 0, pos) + 1
        positions.append({"label": label, "needle": needle, "line": line})
        if line is None:
            problems.append(f"missing {label}")
            continue
        last_pos = pos
    status = "pass" if not problems else "fail"
    return Check(
        "collision_mrt_force_order",
        status,
        "CollisionMRT producer-consumer anchors appear in expected source order."
        if status == "pass"
        else "; ".join(problems),
        {"anchors": positions},
    )


def extract_stage_order(dynamics_r: str) -> dict[str, Any]:
    stage_lines = []
    for line_no, line in enumerate(dynamics_r.splitlines(), start=1):
        if "AddStage" in line or "AddAction" in line:
            stage_lines.append({"line": line_no, "text": line.strip()})
    stage_markers = {
        "BaseIter": first_line_matching(dynamics_r, r'AddStage\(\s*(?:name\s*=\s*)?["\']BaseIter["\']'),
        "calcPhase": first_line_matching(dynamics_r, r'AddStage\(\s*(?:name\s*=\s*)?["\']calcPhase["\']'),
        "calcPhaseGrad": first_line_matching(dynamics_r, r'AddStage\(\s*(?:name\s*=\s*)?["\']calcPhaseGrad["\']'),
        "calcWall_CA": first_line_matching(dynamics_r, r'AddStage\(\s*(?:name\s*=\s*)?["\']calcWall_CA["\']'),
        "calcWallPhase_correction": first_line_matching(dynamics_r, r'AddStage\(\s*(?:name\s*=\s*)?["\']calcWallPhase_correction["\']'),
        "geometric_iteration_action": first_line_matching(
            dynamics_r,
            r'AddAction\(\s*["\']Iteration["\']\s*,\s*c\(["\']BaseIter["\']\s*,\s*["\']calcPhase["\']\s*,\s*calcGrad',
        ),
    }
    return {"stage_lines": stage_lines, "stage_markers": stage_markers}


def run_audit(repo_root: Path, model: Path) -> dict[str, Any]:
    model_dir = (repo_root / model).resolve() if not model.is_absolute() else model
    dynamics_r_path = model_dir / "Dynamics.R"
    dynamics_c_path = model_dir / "Dynamics.c.Rt"
    boundary_c_path = model_dir / "Boundary.c.Rt"

    dynamics_r = read_text(dynamics_r_path)
    dynamics_c = read_text(dynamics_c_path)
    boundary_c = read_text(boundary_c_path)

    checks: list[Check] = []

    streamed = ["pnorm", "U", "V", "W"]
    streamed_density = add_kind_lines(dynamics_r, "AddDensity", streamed)
    streamed_field = add_kind_lines(dynamics_r, "AddField", streamed)
    checks.append(
        Check(
            "streamed_macros_are_adddensity",
            streamed_macro_status(streamed_density, streamed_field),
            "`pnorm/U/V/W` primary state should be AddDensity streaming state. Conditional OutFlow AddField helpers are recorded as warnings.",
            {"AddDensity": streamed_density, "AddField": streamed_field},
        )
    )

    replay_names = [
        "ReplayMu",
        "ReplayLapPhi",
        "ReplayGradPhiX",
        "ReplayFsurfX",
        "ReplayFmuX",
        "ReplayFtotalX",
        "ReplayForceOverRhoX",
        "B18ProbeActive",
        "B21ProbeActive",
        "B22ProbeActive",
    ]
    replay_field = add_kind_lines(dynamics_r, "AddField", replay_names)
    replay_density = add_kind_lines(dynamics_r, "AddDensity", replay_names)
    checks.append(
        Check(
            "replay_fields_are_addfield",
            status_for_all_present(replay_field)
            if all(not lines for lines in replay_density.values())
            else "fail",
            "Replay/Bxx diagnostics should be AddField and must not participate in TCLB streaming.",
            {"AddField": replay_field, "AddDensity": replay_density},
        )
    )

    settings = [
        "ReplayDiagnosticsMode",
        "MomentumClosureDiagnosticsMode",
        "Stage14B18ClosureDiagnosticsMode",
        "Stage14B21HPopulationAuditMode",
        "Stage14B22VelocityProducerAuditMode",
        "MomentumForceMode",
        "FmuStressClosureMode",
        "PressureClosureMode",
        "ForceDensityClosureMode",
        "ForceFixedPointMode",
    ]
    setting_lines = add_kind_lines(dynamics_r, "AddSetting", settings)
    checks.append(
        Check(
            "diagnostic_and_candidate_settings_exist",
            status_for_all_present(setting_lines),
            "Stage14 diagnostic settings are available in model XML.",
            {"AddSetting": setting_lines},
        )
    )

    checks.append(
        order_check(
            dynamics_c,
            [
                ("CollisionMRT start", "CudaDeviceFunction void CollisionMRT()"),
                ("PhaseF consumed", "PhaseF = PhaseF(0,0,0);"),
                ("calcMu", "real_t mu = calcMu( C );"),
                ("m0 from streamed g", "C(m0[selR], (M %*% g)[selR])"),
                ("pressure input", "pressure_force_input = stage14_pressure_force_input"),
                ("calcGradPhi", "gradPhi = calcGradPhi();"),
                ("calc_Fp", "calc_Fp(&F_pressure[0]"),
                ("calc_Fs", "calc_Fs(&F_surf[0]"),
                ("F_mu MRT", "F_mu[0] = (0.5-tau) *"),
                ("F_total assembly", "F_total[0] = F_surf[0] + F_pressure[0]"),
                ("force mode split", "stage14_apply_momentum_force_mode"),
                ("half-force velocity", "m0[2:4] + 0.5 * F_total"),
                ("h update", "C(h, h - omega * (h - heq + 0.5*Fphi) + Fphi)"),
                ("MRT mF insertion", "mF[2:4] = PV(\"momentum_force_injection_scale\")"),
                ("g update", "C(g, invM %*% m)"),
                ("momentum after g replay", "ReplayMomentumAfterGX = momentum_after_g[0];"),
            ],
        )
    )

    mrt_prefactor_lines = find_all_lines(dynamics_c, r"F_mu\[0\]\s*=\s*\(0\.5-tau\) \*")
    bgk_prefactor_lines = find_all_lines(dynamics_c, r"F_mu\[0\]\s*=\s*\(0\.5-tau\)/tau \*")
    prefactor_status = "warning" if mrt_prefactor_lines and bgk_prefactor_lines else "fail"
    checks.append(
        Check(
            "fmu_prefactor_mrt_bgk_recorded",
            prefactor_status,
            "MRT and BGK F_mu prefactors differ; this is recorded as a B35 branch, not changed in B32.5/B33.",
            {"mrt_lines": mrt_prefactor_lines, "bgk_lines": bgk_prefactor_lines},
        )
    )

    checks.append(
        Check(
            "boundary_sentinel_guard_recorded",
            "pass" if "SPECIAL_POINT_HUGE_MAGIC_NUMBER = -999.0" in boundary_c else "warning",
            "Boundary sentinel should be -999.0 after prior Stage13 audit.",
            {"line": line_of(boundary_c, "SPECIAL_POINT_HUGE_MAGIC_NUMBER = -999.0")},
        )
    )

    stage_order = extract_stage_order(dynamics_r)
    failed = [check.name for check in checks if check.status == "fail"]
    warnings = [check.name for check in checks if check.status == "warning"]
    if failed:
        verdict = "semantics_audit_fail"
    elif warnings:
        verdict = "semantics_audit_pass_with_warnings"
    else:
        verdict = "semantics_audit_pass"

    return {
        "verdict": verdict,
        "claim_limit": "static source semantics audit only; not runtime validation",
        "repo_root": str(repo_root),
        "model_dir": str(model_dir),
        "files": {
            "Dynamics.R": str(dynamics_r_path),
            "Dynamics.c.Rt": str(dynamics_c_path),
            "Boundary.c.Rt": str(boundary_c_path),
        },
        "checks": [check.__dict__ for check in checks],
        "stage_order": stage_order,
        "next_gate": "B33 first-bad-cell ledger if no fail status",
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Stage14-B32.5 TCLB Semantics Audit",
        "",
        f"Verdict: `{report['verdict']}`",
        "",
        "Claim limit: static source semantics audit only. This is not a runtime",
        "stability result, contact-angle validation, or dynamic-impact preflight.",
        "",
        "## Checks",
        "",
        "| check | status | detail |",
        "|---|---|---|",
    ]
    for check in report["checks"]:
        detail = str(check["detail"]).replace("|", "\\|")
        lines.append(f"| `{check['name']}` | `{check['status']}` | {detail} |")
    lines.extend(
        [
            "",
            "## Stage Markers",
            "",
            "| marker | line |",
            "|---|---:|",
        ]
    )
    for name, line in report["stage_order"]["stage_markers"].items():
        lines.append(f"| `{name}` | {'' if line is None else line} |")
    lines.extend(
        [
            "",
            "## Next Gate",
            "",
            report["next_gate"],
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    report = run_audit(repo_root, args.model)
    json_path = out_dir / "stage14_B32_5_semantics_audit.json"
    md_path = out_dir / "stage14_B32_5_semantics_audit.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    write_markdown(report, md_path)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if report["verdict"] == "semantics_audit_fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
