#!/usr/bin/env python3
"""Generate Stage17B-B8 neutral drift isolation cases.

B8 is a narrow diagnostic matrix for the 90-degree cylinder control drift. It
does not validate contact angle. The four generated cases separate baseline,
shadow-only, controlled diffuse-solid write, and controlled legacy write paths.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import gen_cyl_shadow_cases
import gen_stage17B_B5_consumption_cases


GROUPS = [
    {
        "group": "A",
        "case": "cylinder_init090_neutral_A_legacy_baseline",
        "label": "legacy_baseline_write_off",
        "diffuse_mode": 0,
        "write_mode": 0,
        "write_source_mode": 0,
        "purpose": "pure legacy analytic wetting baseline with Stage17B diffuse-solid disabled",
    },
    {
        "group": "B",
        "case": "cylinder_init090_neutral_B_shadow_only",
        "label": "diffuse_shadow_write_off",
        "diffuse_mode": 1,
        "write_mode": 0,
        "write_source_mode": 0,
        "purpose": "Stage17B diffuse-solid shadow fields enabled but no solver write",
    },
    {
        "group": "C",
        "case": "cylinder_init090_neutral_C_controlled_psi",
        "label": "controlled_psiwallghost_write",
        "diffuse_mode": 1,
        "write_mode": 2,
        "write_source_mode": 0,
        "purpose": "current controlled curved write path using PsiWallGhost",
    },
    {
        "group": "D",
        "case": "cylinder_init090_neutral_D_controlled_legacy",
        "label": "controlled_legacywallghost_write",
        "diffuse_mode": 1,
        "write_mode": 2,
        "write_source_mode": 1,
        "purpose": "same controlled curved write gate, but writing legacy analytic WallGhost",
    },
]


def replace_param(xml: str, name: str, value: object) -> str:
    pattern = rf'(<Param name="{re.escape(name)}" value=")[^"]*(")'
    updated, count = re.subn(pattern, rf"\g<1>{value}\2", xml, count=1)
    if count == 1:
        return updated
    insert = f'        <Param name="{name}" value="{value}"/>\n'
    for marker in [
        '    <Param name="Stage17BPsiEps"',
        '    <Param name="ReplayDiagnosticsMode"',
        '        <Param name="Stage17BPsiEps"',
        '        <Param name="ReplayDiagnosticsMode"',
    ]:
        if marker in xml:
            return xml.replace(marker, insert + marker, 1)
    raise ValueError(f"cannot replace or insert Param {name}")


def write_case(
    root: Path,
    group: dict[str, object],
    iterations: int,
    vtk_period: int,
    log_period: int,
) -> dict[str, object]:
    case_dir = root / str(group["case"])
    case_dir.mkdir(parents=True, exist_ok=True)
    xml = gen_cyl_shadow_cases.case_xml(
        theta_deg=90,
        iterations=iterations,
        vtk_period=vtk_period,
        log_period=log_period,
        write_mode=int(group["write_mode"]),
    )
    for name, value in [
        ("Stage17BDiffuseSolidMode", group["diffuse_mode"]),
        ("Stage17BWriteMode", group["write_mode"]),
        ("Stage17BWriteSourceMode", group["write_source_mode"]),
        ("Stage17BShadowThetaDeg", 90),
        ("ReplayDiagnosticsMode", 1),
        ("Stage17BConsumptionDiagnosticsMode", 1),
        ("MomentumClosureDiagnosticsMode", 0),
        ("WallCompactStencilMode", 0),
        ("WallCompactStencilWriteAllowedFlag", 0),
        ("DynamicCLMode", 0),
    ]:
        xml = replace_param(xml, name, value)
    xml = gen_stage17B_B5_consumption_cases.enable_b5(xml)
    (case_dir / "case.xml").write_text(xml, encoding="utf-8")

    metadata = {
        "case": group["case"],
        "geometry": "cylinder",
        "purpose": f"Stage17B-B8 neutral drift isolation: {group['purpose']}",
        "claim_limit": "neutral drift root-cause diagnostic only; not contact-angle validation",
        "b8_group": group["group"],
        "b8_label": group["label"],
        "init_theta_deg": 90,
        "target_theta_deg": 90,
        "legacy_rad_angle_deg": 90,
        "stage17b_diffuse_solid_mode": group["diffuse_mode"],
        "stage17b_write_mode": group["write_mode"],
        "stage17b_write_source_mode": group["write_source_mode"],
        "stage17b_shadow_theta_deg": 90,
        "stage17b_consumption_diagnostics_mode": 1,
        "replay_diagnostics_mode": 1,
        "wall_compact_stencil_mode": 0,
        "iterations": iterations,
        "vtk_period": vtk_period,
        "log_period": log_period,
        "solid_center": [48.0, 48.0, 48.0],
        "solid_radius": 20.0,
        "slice_axis": "z",
        "slice_index": 48,
        "liquid_axis": "+y",
        "expected_response": "90-degree neutral control should stay near stationary",
        "diagnostic_question": (
            "Does 90-degree drift appear in write-off baseline, controlled Psi write, "
            "or controlled legacy write?"
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
        default=Path("cases/diagnostics/stage17B_B8_neutral_20260625_600"),
    )
    parser.add_argument("--iterations", type=int, default=600)
    parser.add_argument("--vtk-period", type=int, default=200)
    parser.add_argument("--log-period", type=int, default=100)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.root.mkdir(parents=True, exist_ok=True)
    cases = [
        write_case(args.root, group, args.iterations, args.vtk_period, args.log_period)
        for group in GROUPS
    ]
    manifest = {
        "purpose": "Stage17B-B8 90-degree neutral drift isolation matrix",
        "claim_limit": "root-cause diagnostic only; not contact-angle validation",
        "iterations": args.iterations,
        "vtk_period": args.vtk_period,
        "log_period": args.log_period,
        "groups": GROUPS,
        "cases": cases,
        "verdict_logic": {
            "A_drift": "baseline phase/force/initialization bias suspected",
            "A_stable_C_drift_D_stable": "controlled PsiWallGhost neutral formula suspected",
            "A_stable_C_and_D_drift": "controlled write gate or stencil consumption suspected",
            "A_B_difference": "shadow-only side effect or diagnostic metric sensitivity suspected",
        },
    }
    (args.root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    for case in cases:
        print(case["case_xml"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
