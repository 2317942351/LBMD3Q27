#!/usr/bin/env python3
"""Generate Stage17B-B9 baseline-closure dense replay cases.

B9 is a root-cause diagnostic for the 90-degree cylinder neutral drift seen in
B8. It does not validate contact angle and it does not change solver physics.

The generated matrix keeps all write paths off and enables only existing
Replay/Momentum diagnostic quantities. The shadow-diagnostics group is included
because B8 proved it is side-effect identical to the pure legacy baseline while
also exposing near-wall producer-consumer fields.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import gen_cyl_shadow_cases
import gen_stage17B_B5_consumption_cases


# A standalone TCLB case with <Solve Iterations="0"> does not exit reliably in
# the current headless server lane. Use step 1 as the earliest executable frame.
STEPS = [1, 2, 5, 10, 20, 50, 100, 200, 400, 600, 1000, 2000]

GROUPS = [
    {
        "group": "A",
        "label": "legacy_zero_write",
        "case_prefix": "cylinder_init090_b9_A_legacy",
        "stage17b_diffuse_solid_mode": 0,
        "stage17b_write_mode": 0,
        "stage17b_write_source_mode": 0,
        "purpose": "pure legacy zero-write baseline with Replay/Momentum diagnostics",
    },
    {
        "group": "B",
        "label": "shadow_zero_write",
        "case_prefix": "cylinder_init090_b9_B_shadow",
        "stage17b_diffuse_solid_mode": 1,
        "stage17b_write_mode": 0,
        "stage17b_write_source_mode": 0,
        "purpose": (
            "zero-write baseline plus Stage17B shadow diagnostics; B8 showed this "
            "has the same neutral drift as pure legacy"
        ),
    },
]


COMMON_FIELDS = [
    "PhaseField",
    "Rho",
    "U",
    "P",
    "BOUNDARY",
    "IsItBoundary",
    "WallGhost",
    "WallGhostRaw",
    "WallGhostClamped",
    "WallGhostClampHit",
    "WettingPathId",
    "WallH",
    "AnalyticFlag",
    "LocalRadAngle",
    "PsiSolid",
    "PsiGradMag",
    "PsiNormal",
    "PsiWallGhostRaw",
    "PsiWallGhost",
    "PsiWallGhostClampHit",
    "PsiThetaImplied",
    "PsiJaggedness",
    "PsiWriteAllowedFlag",
    "PsiNormalAmbiguityFlag",
    "PsiWriteAppliedFlag",
    "PsiWriteRejectedReason",
    "NearWallForceMag",
    "NearWallGradPhiMag",
    "NearWallForceOverRhoShadow",
]


LITE_REPLAY_FIELDS = [
    "PhaseStencilGhostUseCount",
    "PhaseStencilFallbackCount",
    "PhaseStencilMidpointFallbackCount",
    "ReplayPhaseConsumed",
    "ReplayPhaseFromH",
    "ReplayLapPhi",
    "ReplayMu",
    "ReplayGradPhi",
    "ReplayPhaseAdvVelocity",
    "ReplayNormal",
    "ReplayHPreSum",
    "ReplayHPostSum",
    "ReplayHeqSum",
    "ReplayHPreMaxAbs",
    "ReplayHPostMaxAbs",
    "ReplayHeqMaxAbs",
    "ReplayFphiSum",
    "ReplayFphiMaxAbs",
    "ReplayTmp1",
    "ReplayTmp1BoundedShadow",
    "ReplayPhaseOutOfBoundsFlag",
]


MOMENTUM_REPLAY_FIELDS = [
    "ReplayGradPhi",
    "ReplayFsurf",
    "ReplayFpressure",
    "ReplayFbody",
    "ReplayFmu",
    "ReplayFtotal",
    "ReplayRho",
    "ReplayTau",
    "ReplayPressureMoment",
    "ReplayUPreForce",
    "ReplayUPostForce",
    "ReplayForceOverRho",
    "ReplayFmuIter1",
    "ReplayFtotalIter1",
    "ReplayUPostIter1",
    "ReplayNormal",
    "ReplayM0",
    "ReplayVelocityHalfForce",
    "ReplayMF",
    "ReplayMomentumAfterG",
    "ReplayMomentumDeltaG",
    "ReplayPressureInput",
    "ReplayPressureForceScale",
    "ReplayPressurePhysicalInput",
    "ReplayFpressureNoThird",
    "ReplayFpressurePhysical",
    "ReplayStressInputXX",
    "ReplayStressInputXY",
    "ReplayStressInputXZ",
    "ReplayStressInputYY",
    "ReplayStressInputYZ",
    "ReplayStressInputZZ",
    "ReplayStressIter1XX",
    "ReplayStressIter1XY",
    "ReplayStressIter1XZ",
    "ReplayStressIter1YY",
    "ReplayStressIter1YZ",
    "ReplayStressIter1ZZ",
    "ReplayStressPreForceShadowXX",
    "ReplayStressPreForceShadowXY",
    "ReplayStressPreForceShadowXZ",
    "ReplayStressPreForceShadowYY",
    "ReplayStressPreForceShadowYZ",
    "ReplayStressPreForceShadowZZ",
    "ReplayStressPostForceShadowXX",
    "ReplayStressPostForceShadowXY",
    "ReplayStressPostForceShadowXZ",
    "ReplayStressPostForceShadowYY",
    "ReplayStressPostForceShadowYZ",
    "ReplayStressPostForceShadowZZ",
    "ReplayFmuRaw",
    "ReplayFmuDelta",
    "ReplayTauUsed",
    "ReplayRhoForForce",
    "ReplayForceInjectionMode",
    "ReplayPressureClosureMode",
    "ReplayForceDensityClosureMode",
    "ReplayForceFixedPointMode",
    "ReplayForceRhoRaw",
    "ReplayForceRhoEffective",
    "ForceIterCount",
    "ForceIterResidual",
]


FIELD_TIERS = {
    "lite": COMMON_FIELDS + LITE_REPLAY_FIELDS + gen_stage17B_B5_consumption_cases.B5_FIELDS,
    "momentum": COMMON_FIELDS + MOMENTUM_REPLAY_FIELDS,
    "full": COMMON_FIELDS
    + LITE_REPLAY_FIELDS
    + MOMENTUM_REPLAY_FIELDS
    + gen_stage17B_B5_consumption_cases.B5_FIELDS,
}


def replace_param(xml: str, name: str, value: object) -> str:
    pattern = rf'(<Param name="{re.escape(name)}" value=")[^"]*(")'
    updated, count = re.subn(pattern, rf"\g<1>{value}\2", xml, count=1)
    if count:
        return updated
    marker = '    <Param name="DynamicCLMode"'
    if marker in xml:
        return xml.replace(marker, f'    <Param name="{name}" value="{value}"/>\n{marker}', 1)
    raise ValueError(f"cannot replace or insert Param {name}")


def replace_vtk_fields(xml: str, fields: list[str]) -> str:
    field_text = ",".join(dict.fromkeys(fields))
    xml = re.sub(r'<VTK what="[^"]*"', f'<VTK what="{field_text}"', xml)
    xml = re.sub(
        r'<VTK Iterations="([^"]+)" what="[^"]*"',
        lambda match: f'<VTK Iterations="{match.group(1)}" what="{field_text}"',
        xml,
    )
    return xml


def build_case_xml(group: dict[str, object], final_step: int, tier: str) -> str:
    vtk_period = max(final_step, 1)
    xml = gen_cyl_shadow_cases.case_xml(
        theta_deg=90,
        iterations=final_step,
        vtk_period=vtk_period,
        log_period=max(min(vtk_period, 100), 1),
        write_mode=0,
    )
    xml = gen_stage17B_B5_consumption_cases.enable_b5(xml)
    params = {
        "Stage17BDiffuseSolidMode": group["stage17b_diffuse_solid_mode"],
        "Stage17BWriteMode": group["stage17b_write_mode"],
        "Stage17BWriteSourceMode": group["stage17b_write_source_mode"],
        "Stage17BShadowThetaDeg": 90,
        "Stage17BConsumptionDiagnosticsMode": 1,
        "ReplayDiagnosticsMode": 1,
        "MomentumClosureDiagnosticsMode": 1 if tier in {"momentum", "full"} else 0,
        "MomentumClosureProbeMode": 0,
        "MomentumForceMode": 0,
        "PressureClosureMode": 0,
        "ForceDensityClosureMode": 0,
        "ForceFixedPointMode": 0,
        "PhaseAdvectionVelocityMode": 0,
        "ForceFixedTol": 0,
        "ForceFixedMaxIter": 2,
        "WallCompactStencilMode": 0,
        "WallCompactStencilWriteAllowedFlag": 0,
        "DynamicCLMode": 0,
    }
    for name, value in params.items():
        xml = replace_param(xml, name, value)
    return replace_vtk_fields(xml, FIELD_TIERS[tier])


def write_case(root: Path, group: dict[str, object], final_step: int, tier: str) -> dict[str, object]:
    case = f"{group['case_prefix']}_{tier}_s{final_step:04d}"
    case_dir = root / case
    case_dir.mkdir(parents=True, exist_ok=True)
    xml = build_case_xml(group, final_step, tier)
    (case_dir / "case.xml").write_text(xml, encoding="utf-8")
    metadata = {
        "case": case,
        "geometry": "cylinder",
        "stage": "Stage17B-B9",
        "purpose": f"B9 baseline closure dense replay: {group['purpose']}",
        "claim_limit": "baseline drift root-cause diagnostic only; not contact-angle validation",
        "b9_group": group["group"],
        "b9_label": group["label"],
        "b9_tier": tier,
        "init_theta_deg": 90,
        "target_theta_deg": 90,
        "legacy_rad_angle_deg": 90,
        "final_step": final_step,
        "iterations": final_step,
        "vtk_period": max(final_step, 1),
        "log_period": max(min(max(final_step, 1), 100), 1),
        "stage17b_diffuse_solid_mode": group["stage17b_diffuse_solid_mode"],
        "stage17b_write_mode": group["stage17b_write_mode"],
        "stage17b_write_source_mode": group["stage17b_write_source_mode"],
        "stage17b_consumption_diagnostics_mode": 1,
        "replay_diagnostics_mode": 1,
        "momentum_closure_diagnostics_mode": 1 if tier in {"momentum", "full"} else 0,
        "momentum_force_mode": 0,
        "pressure_closure_mode": 0,
        "force_density_closure_mode": 0,
        "force_fixed_point_mode": 0,
        "phase_advection_velocity_mode": 0,
        "wall_compact_stencil_mode": 0,
        "solid_center": [48.0, 48.0, 48.0],
        "solid_radius": 20.0,
        "slice_axis": "z",
        "slice_index": 48,
        "liquid_axis": "+y",
        "diagnostic_question": (
            "At which producer-consumer boundary does the 90-degree baseline "
            "cylinder drift first appear?"
        ),
        "zero_step_limitation": (
            "Standalone Solve Iterations=0 is not used in B9 because it does "
            "not exit reliably in the current headless TCLB server lane; step 1 "
            "is the earliest executable frame."
        ),
    }
    (case_dir / "case_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8"
    )
    return metadata | {"case_xml": str(case_dir / "case.xml")}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("cases/diagnostics/stage17B_B9_baseline_20260625"),
    )
    parser.add_argument("--steps", type=int, nargs="+", default=STEPS)
    parser.add_argument(
        "--groups",
        choices=["A", "B"],
        nargs="+",
        default=["A", "B"],
        help="A=pure legacy zero-write, B=shadow diagnostics zero-write",
    )
    parser.add_argument(
        "--tier",
        choices=sorted(FIELD_TIERS),
        default="lite",
        help="Output tier: lite=phase/morphology, momentum=pressure/stress/MRT, full=all fields.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.root.mkdir(parents=True, exist_ok=True)
    groups = [group for group in GROUPS if group["group"] in set(args.groups)]
    cases = [write_case(args.root, group, step, args.tier) for group in groups for step in args.steps]
    manifest = {
        "purpose": "Stage17B-B9 baseline closure dense replay matrix",
        "claim_limit": "root-cause diagnostic only; not contact-angle validation",
        "groups": groups,
        "steps": args.steps,
        "tier": args.tier,
        "cases": cases,
        "field_count": len(dict.fromkeys(FIELD_TIERS[args.tier])),
    }
    (args.root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    for case in cases:
        print(case["case_xml"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
