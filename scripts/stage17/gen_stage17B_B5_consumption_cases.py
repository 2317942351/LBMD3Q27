#!/usr/bin/env python3
"""Generate Stage17B-B5 WallGhost consumption probe cases.

These cases are short producer-consumer diagnostics. They keep the Stage17B
controlled WallGhost write enabled, but do not claim contact-angle validation.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

import gen_stage17B_B4_morphology_cases


B5_FIELDS = [
    "PhaseStencilGhostUseCount",
    "PhaseStencilFallbackCount",
    "ReplayPhaseConsumed",
    "ReplayPhaseFromH",
    "ReplayLapPhi",
    "ReplayMu",
    "ReplayGradPhi",
    "ReplayFphiSum",
    "ReplayFphiMaxAbs",
    "ReplayTmp1",
    "ReplayHPreSum",
    "ReplayHPostSum",
    "B5SignedDistance",
    "B5NearWallBandFlag",
    "B5ContactLineBandFlag",
    "B5WallGhostConsumedFlag",
    "B5GhostUseCount",
    "B5WallGhostMinusCenter",
    "B5WallGhostMinusFluidProbe",
    "B5WallGhostClampHitNeighbor",
    "B5GradPhiNormal",
    "B5GradPhiTangentialMag",
    "B5FphiSum",
    "B5FphiNormalProxy",
    "B5PhaseFromHDelta",
    "B5ExpectedResponseSign",
    "B5SignalSignOK",
]


def enable_b5(xml: str) -> str:
    replacements = {
        "ReplayDiagnosticsMode": 1,
        "Stage17BConsumptionDiagnosticsMode": 1,
        "MomentumClosureDiagnosticsMode": 0,
    }
    for name, value in replacements.items():
        if f'name="{name}"' in xml:
            xml = gen_stage17B_B4_morphology_cases.replace_param_value(xml, name, value)
        else:
            xml = xml.replace(
                "    <Param name=\"DynamicCLMode\"",
                f"    <Param name=\"{name}\" value=\"{value}\"/>\n    <Param name=\"DynamicCLMode\"",
                1,
            )

    field_match = re.search(r'<VTK what="([^"]*)"', xml)
    if not field_match:
        raise ValueError("case xml has no VTK what attribute")
    fields = [item for item in field_match.group(1).split(",") if item]
    for field in B5_FIELDS:
        if field not in fields:
            fields.append(field)
    xml = re.sub(r'<VTK what="[^"]*"', f'<VTK what="{",".join(fields)}"', xml)
    xml = re.sub(
        r'<VTK Iterations="([^"]+)" what="[^"]*"',
        lambda match: f'<VTK Iterations="{match.group(1)}" what="{",".join(fields)}"',
        xml,
    )
    return xml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("cases/diagnostics/stage17B_B5_consumption_20260624"),
    )
    parser.add_argument("--init-theta", type=int, default=90)
    parser.add_argument("--target-thetas", type=int, nargs="+", default=[60, 90, 120])
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--vtk-period", type=int, default=250)
    parser.add_argument("--log-period", type=int, default=100)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.root.mkdir(parents=True, exist_ok=True)
    cases: list[dict[str, object]] = []
    for theta in args.target_thetas:
        base = gen_stage17B_B4_morphology_cases.write_case(
            args.root,
            geometry="cylinder",
            target_theta=theta,
            init_theta=args.init_theta,
            iterations=args.iterations,
            vtk_period=args.vtk_period,
            log_period=args.log_period,
            write_mode=2,
        )
        old_name = str(base["case"])
        new_name = old_name.replace("_b3morph", "_b5consume")
        old_dir = args.root / old_name
        new_dir = args.root / new_name
        if old_dir != new_dir:
            new_dir.mkdir(parents=True, exist_ok=True)
            for filename in ("case.xml", "case_metadata.json"):
                shutil.move(str(old_dir / filename), str(new_dir / filename))
            shutil.rmtree(old_dir)
        xml_path = new_dir / "case.xml"
        xml_path.write_text(enable_b5(xml_path.read_text(encoding="utf-8")), encoding="utf-8")
        metadata_path = new_dir / "case_metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata.update(
            {
                "case": new_name,
                "purpose": "Stage17B-B5 WallGhost consumption producer-consumer probe",
                "claim_limit": "consumption diagnostics only; not contact-angle validation",
                "stage17b_consumption_diagnostics_mode": 1,
                "replay_diagnostics_mode": 1,
                "expected_diagnostic": (
                    "WallGhost written by B3 should be consumed on the next "
                    "BaseIter through STAGE13_PHASE_FOR_STENCIL"
                ),
            }
        )
        metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
        base["case"] = new_name
        base["case_xml"] = str(xml_path)
        base["purpose"] = metadata["purpose"]
        cases.append(base)

    manifest = {
        "purpose": "Stage17B-B5 WallGhost consumption producer-consumer probe",
        "claim_limit": "short-run consumption diagnostics only; not contact-angle validation",
        "init_theta_deg": args.init_theta,
        "target_thetas": args.target_thetas,
        "iterations": args.iterations,
        "vtk_period": args.vtk_period,
        "log_period": args.log_period,
        "stage17b_write_mode": 2,
        "stage17b_consumption_diagnostics_mode": 1,
        "replay_diagnostics_mode": 1,
        "cases": cases,
    }
    (args.root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    for case in cases:
        print(case["case_xml"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
