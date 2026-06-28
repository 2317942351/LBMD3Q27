#!/usr/bin/env python3
"""Digest Stage14-B38 first-bad force ledger outputs.

This script is intentionally post-processing only. It reads the B38 analyzer
outputs produced by stage14_b17_onset_mask_argmax.py and extracts the earliest
large ForceOverRho co-located values so the next solver edit can be chosen from
evidence, not from another local patch attempt.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


IMPORTANT_COLOCATED = [
    "PhaseField",
    "ReplayPhaseFromH",
    "ReplayPhaseConsumed",
    "Rho",
    "ReplayRho",
    "ReplayRhoForForce",
    "ReplayForceRhoRaw",
    "ReplayForceRhoEffective",
    "ReplayTau",
    "ReplayTauUsed",
    "ReplayLapPhi",
    "ReplayMu",
    "GradPhiNorm",
    "FsurfNorm",
    "FbodyNorm",
    "FmuNorm",
    "FpressureNorm",
    "FpressurePhysicalNorm",
    "FmuRawNorm",
    "FmuDeltaNorm",
    "FtotalNorm",
    "ForceOverRhoNorm",
    "StressInputNorm",
    "StressIter1Norm",
    "StressPreForceNorm",
    "StressPostForceNorm",
    "StressPostMinusPreNorm",
    "StressPostOverPreRatio",
    "B18ProbeActive",
    "B18StressPreForceNorm",
    "B18StressPostForceNorm",
    "B18StressForceExcludedNorm",
    "B18StressIncomingNorm",
    "B18StressPostMinusPreNorm",
    "B18StressPostOverPre",
    "B18StressAmplificationFlag",
    "B18FmuPreForceNorm",
    "B18FmuPostForceNorm",
    "B18FmuForceExcludedNorm",
    "B18FmuCandidateDeltaNorm",
    "B18ForceOverRhoRawNorm",
    "B18ForceOverRhoDensityFloorNorm",
    "B18ForceOverRhoPhaseMixtureNorm",
    "B18RhoDenominatorRaw",
    "B18RhoDenominatorFloor",
    "B18RhoDenominatorPhaseMix",
    "ReplayM0",
    "ReplayVelocityHalfForce",
    "ReplayMF",
    "ReplayMomentumAfterG",
    "ReplayMomentumDeltaG",
    "UPreForceNorm",
    "UPostForceNorm",
    "PhaseAdvVelocityNorm",
    "ReplayHPreMaxAbs",
    "ReplayHPostMaxAbs",
    "ReplayHeqMaxAbs",
    "ReplayTmp1",
    "ReplayFphiMaxAbs",
    "ForceIterCount",
    "ForceIterResidual",
    "B40ProbeActive",
    "B40FmuLegacyScale",
    "B40FmuBGKScale",
    "B40StressLegacyMatchDeltaNorm",
    "B40StressMomentRawNorm",
    "B40StressMomentRelaxedNorm",
    "B40StressIncomingRawNorm",
    "B40StressIncomingNeqPreNorm",
    "B40StressBGKPopNeqPreNorm",
    "B40StressPostForceNorm",
    "B40StressRawOverRelaxed",
    "B40StressPostOverRelaxed",
    "B40FmuMomentRawLegacyNorm",
    "B40FmuMomentRawBGKNorm",
    "B40FmuMomentRelaxedLegacyNorm",
    "B40FmuMomentRelaxedBGKNorm",
    "B40FmuIncomingRawLegacyNorm",
    "B40FmuIncomingNeqPreLegacyNorm",
    "B40FmuBGKPopNeqPreLegacyNorm",
    "B40FmuBGKPopNeqPreBGKNorm",
    "B40FmuPostForceLegacyNorm",
    "B40ForceOverRhoMomentRawLegacyNorm",
    "B40ForceOverRhoMomentRelaxedLegacyNorm",
    "B40ForceOverRhoBGKPopNeqPreBGKNorm",
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def is_number(value: Any) -> bool:
    return isinstance(value, int | float) and math.isfinite(float(value))


def as_float(value: Any) -> float | None:
    if is_number(value):
        return float(value)
    return None


def norm_from_vector(value: Any) -> float | None:
    if isinstance(value, list) and value and all(is_number(v) for v in value):
        return math.sqrt(sum(float(v) * float(v) for v in value))
    return as_float(value)


def first_onset(summary: dict[str, Any], key: str) -> dict[str, Any] | None:
    value = summary.get(key)
    return value if isinstance(value, dict) else None


def choose_force_argmax(argmax_rows: list[dict[str, Any]], onset: dict[str, Any] | None) -> dict[str, Any] | None:
    candidates = [
        row
        for row in argmax_rows
        if row.get("field") == "ForceOverRhoNorm"
        and row.get("mask") in {"low_rho", "near_interface_wall", "interface_wide", "fluid_all"}
    ]
    if onset is not None:
        step = onset.get("step")
        mask = onset.get("mask")
        exact = [row for row in candidates if row.get("step") == step and row.get("mask") == mask]
        if exact:
            return max(exact, key=lambda row: float(row.get("max_abs") or 0.0))
        same_step = [row for row in candidates if row.get("step") == step]
        if same_step:
            return max(same_step, key=lambda row: float(row.get("max_abs") or 0.0))
    if not candidates:
        return None
    return max(candidates, key=lambda row: (int(row.get("step") or 10**9), float(row.get("max_abs") or 0.0)))


def extract_colocated(record: dict[str, Any] | None) -> dict[str, Any]:
    if not record:
        return {}
    colocated = record.get("colocated")
    if not isinstance(colocated, dict):
        return {}
    out: dict[str, Any] = {}
    for key in IMPORTANT_COLOCATED:
        if key in colocated:
            out[key] = colocated[key]
    return out


def classify(summary: dict[str, Any], colocated: dict[str, Any]) -> tuple[str, list[str]]:
    force = first_onset(summary, "first_force_over_rho_onset")
    mu = first_onset(summary, "first_mu_onset")
    lap = first_onset(summary, "first_lap_phi_onset")
    grad = first_onset(summary, "first_grad_phi_onset")
    fsurf = first_onset(summary, "first_fsurf_onset")
    fmu_raw = first_onset(summary, "first_fmu_raw_onset")
    fmu_actual_onset = first_onset(summary, "first_fmu_onset")
    stress_post = first_onset(summary, "first_stress_post_onset")
    b18_stress_post = first_onset(summary, "first_b18_stress_post_onset")
    b18_force_floor = first_onset(summary, "first_b18_force_floor_onset")
    b18_force_phase = first_onset(summary, "first_b18_force_phase_mix_onset")
    phase = first_onset(summary, "first_phase_from_h_onset")

    notes: list[str] = []
    verdict = "undetermined"
    force_step = int(force["step"]) if force and force.get("step") is not None else None

    if force_step is not None:
        notes.append(f"ForceOverRho first crosses threshold at step {force_step}.")
    if phase is None:
        notes.append("PhaseFromH does not cross the configured out-of-bounds threshold before the force ledger failure.")
    if mu is None and lap is None:
        notes.append("ReplayMu and ReplayLapPhi do not lead the failure under current thresholds.")
    if grad is None and fsurf is None:
        notes.append("ReplayGradPhi and Fsurf do not lead the failure under current thresholds.")

    ftotal = norm_from_vector(colocated.get("FtotalNorm"))
    force_over_rho = norm_from_vector(colocated.get("ForceOverRhoNorm"))
    rho_eff = as_float(colocated.get("ReplayForceRhoEffective"))
    fmu = norm_from_vector(colocated.get("FmuNorm"))
    fmu_raw = norm_from_vector(colocated.get("FmuRawNorm"))
    fsurf_value = norm_from_vector(colocated.get("FsurfNorm"))
    stress_pre = norm_from_vector(colocated.get("B18StressPreForceNorm"))
    stress_post_value = norm_from_vector(colocated.get("B18StressPostForceNorm"))
    b18_ratio = as_float(colocated.get("B18StressPostOverPre"))

    if ftotal is not None and force_over_rho is not None and rho_eff is not None:
        notes.append(
            f"At the selected argmax, |Ftotal|={ftotal:.6g}, "
            f"|F/rho|={force_over_rho:.6g}, rho_eff={rho_eff:.6g}."
        )
    if fmu is not None and fsurf_value is not None:
        notes.append(f"At the selected argmax, |Fmu|={fmu:.6g}, |Fsurf|={fsurf_value:.6g}.")
    if fmu_raw is not None:
        notes.append(f"At the selected argmax, |Fmu_raw_before_mode|={fmu_raw:.6g}.")
    if stress_pre is not None and stress_post_value is not None:
        notes.append(
            f"B18 stress shadow at argmax: pre={stress_pre:.6g}, "
            f"post={stress_post_value:.6g}, post/pre={b18_ratio if b18_ratio is not None else 'n/a'}."
        )

    if lap or mu:
        verdict = "mu_or_laplace_branch"
    elif grad or fsurf:
        verdict = "grad_or_surface_force_branch"
    elif fmu_actual_onset or fmu_raw or stress_post or b18_stress_post:
        verdict = "fmu_stress_timelevel_branch"
    elif force and b18_force_floor is None and b18_force_phase is None:
        verdict = "force_density_denominator_branch"
    elif force:
        verdict = "force_assembly_or_fmu_numerator_branch"

    return verdict, notes


def build_digest(root: Path, prefix: str) -> dict[str, Any]:
    summary_path = root / f"{prefix}_key_summary.json"
    argmax_path = root / f"{prefix}_argmax_trace.json"
    metadata_paths = sorted(root.glob("*/case_metadata.json"))
    summary = load_json(summary_path)
    argmax_rows = load_json(argmax_path)
    metadata = load_json(metadata_paths[0]) if metadata_paths else {}
    force_onset = first_onset(summary, "first_force_over_rho_onset")
    force_record = choose_force_argmax(argmax_rows, force_onset)
    colocated = extract_colocated(force_record)
    verdict, notes = classify(summary, colocated)
    return {
        "status": "B38_FIRST_BAD_LEDGER_DIGEST_COMPLETE",
        "claim_limit": "diagnostic-only; not contact-angle validation and not a solver fix",
        "root": str(root),
        "metadata": {
            key: metadata.get(key)
            for key in [
                "binary_sha256",
                "iterations",
                "density_h",
                "density_l",
                "vtk_field_set",
                "phase_advection_velocity_mode",
                "momentum_force_mode",
                "fmu_stress_closure_mode",
                "momentum_closure_diagnostics_mode",
                "b18_closure_diagnostics_mode",
                "pressure_closure_mode",
                "force_density_closure_mode",
                "force_density_rho_floor",
                "force_fixed_point_mode",
                "b40_stress_audit_mode",
            ]
        },
        "primary_branch_from_analyzer": summary.get("primary_branch"),
        "primary_branch_reason_from_analyzer": summary.get("primary_branch_reason"),
        "b18_branch_from_analyzer": summary.get("b18_primary_branch"),
        "b18_branch_reason_from_analyzer": summary.get("b18_primary_branch_reason"),
        "b40_branch_from_analyzer": summary.get("b40_primary_branch"),
        "b40_branch_reason_from_analyzer": summary.get("b40_primary_branch_reason"),
        "b38_digest_verdict": verdict,
        "first_onsets": {
            key: summary.get(key)
            for key in [
                "first_force_over_rho_onset",
                "first_fmu_onset",
                "first_fmu_raw_onset",
                "first_stress_post_onset",
                "first_b18_stress_post_onset",
                "first_b18_fmu_post_onset",
                "first_b18_force_raw_onset",
                "first_b18_force_floor_onset",
                "first_b18_force_phase_mix_onset",
                "first_lap_phi_onset",
                "first_mu_onset",
                "first_grad_phi_onset",
                "first_fsurf_onset",
                "first_pressure_input_onset",
                "first_phase_from_h_onset",
                "first_hpost_onset",
                "first_b40_stress_match_delta_onset",
                "first_b40_stress_moment_raw_onset",
                "first_b40_stress_moment_relaxed_onset",
                "first_b40_stress_incoming_raw_onset",
                "first_b40_stress_incoming_neq_pre_onset",
                "first_b40_stress_bgk_pop_neq_pre_onset",
                "first_b40_stress_post_onset",
                "first_b40_stress_post_over_relaxed_onset",
                "first_b40_fmu_moment_raw_legacy_onset",
                "first_b40_fmu_moment_relaxed_legacy_onset",
                "first_b40_fmu_bgk_pop_neq_pre_bgk_onset",
                "first_b40_force_moment_raw_legacy_onset",
                "first_b40_force_moment_relaxed_legacy_onset",
                "first_b40_force_bgk_pop_neq_pre_bgk_onset",
            ]
        },
        "selected_force_argmax": {
            "case": force_record.get("case") if force_record else None,
            "step": force_record.get("step") if force_record else None,
            "mask": force_record.get("mask") if force_record else None,
            "field": force_record.get("field") if force_record else None,
            "ijk": force_record.get("ijk") if force_record else None,
            "flat_index": force_record.get("flat_index") if force_record else None,
            "max_abs": force_record.get("max_abs") if force_record else None,
            "mask_membership": force_record.get("mask_membership") if force_record else None,
            "colocated": colocated,
        },
        "interpretation_notes": notes,
        "next_decision_rule": [
            "If mu/lapPhi leads, inspect calcMu and stencil reconstruction before changing force insertion.",
            "If gradPhi/Fsurf leads, inspect calcGradPhi and surface-force scaling.",
            "If stress/Fmu leads while mu/gradPhi/Fsurf stay moderate, implement a default-off F_mu stress time-level/prefactor candidate.",
            "If only Ftotal/rho is large and denominator shadows relieve it, implement a derived force-density closure candidate.",
            "If all components are moderate but momentum replay fails, return to TCLB stage/AddDensity streaming and MRT insertion semantics.",
        ],
    }


def write_markdown(path: Path, digest: dict[str, Any]) -> None:
    arg = digest["selected_force_argmax"]
    colocated = arg.get("colocated") or {}
    lines = [
        "# Stage14-B38 First-Bad Force Ledger Digest",
        "",
        "This is diagnostic-only. It is not contact-angle validation and not a solver fix.",
        "",
        f"- Root: `{digest['root']}`",
        f"- Verdict: `{digest['b38_digest_verdict']}`",
        f"- Analyzer branch: `{digest['primary_branch_from_analyzer']}`",
        f"- B18 branch: `{digest['b18_branch_from_analyzer']}`",
        f"- B40 branch: `{digest.get('b40_branch_from_analyzer')}`",
        "",
        "## Selected ForceOverRho Argmax",
        "",
        f"- Step: `{arg.get('step')}`",
        f"- Mask: `{arg.get('mask')}`",
        f"- ijk: `{arg.get('ijk')}`",
        f"- max_abs: `{arg.get('max_abs')}`",
        "",
        "## Co-Located Values",
        "",
    ]
    for key in IMPORTANT_COLOCATED:
        if key in colocated:
            lines.append(f"- `{key}`: `{colocated[key]}`")
    lines.extend(["", "## Interpretation Notes", ""])
    for note in digest["interpretation_notes"]:
        lines.append(f"- {note}")
    lines.extend(["", "## First Onsets", ""])
    for key, value in digest["first_onsets"].items():
        lines.append(f"- `{key}`: `{value}`")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="B38 probe root containing b38_key_summary.json.")
    parser.add_argument("--prefix", default="b38", help="Analyzer output prefix, e.g. b38 or b39.")
    parser.add_argument("--out-json", type=Path)
    parser.add_argument("--out-md", type=Path)
    args = parser.parse_args()
    digest = build_digest(args.root.resolve(), args.prefix)
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(digest, indent=2, sort_keys=True), encoding="utf-8")
    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        write_markdown(args.out_md, digest)
    print(json.dumps(digest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
