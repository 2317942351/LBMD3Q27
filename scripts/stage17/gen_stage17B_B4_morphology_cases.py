#!/usr/bin/env python3
"""Generate Stage17B-B4 static morphology response smoke cases.

These cases deliberately initialize the liquid cap at 90 degrees, then set the
Stage17B controlled WallGhost target to 60, 90, or 120 degrees. They are a
short morphology-response smoke test, not contact-angle validation.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Callable

import gen_cyl_shadow_cases
import gen_sphere_shadow_cases


def replace_param_value(xml: str, name: str, value: object) -> str:
    pattern = rf'(<Param name="{re.escape(name)}" value=")[^"]*(")'
    updated, count = re.subn(pattern, rf"\g<1>{value}\2", xml, count=1)
    if count != 1:
        raise ValueError(f"expected exactly one {name} param, found {count}")
    return updated


def write_case(
    root: Path,
    geometry: str,
    target_theta: int,
    init_theta: int,
    iterations: int,
    vtk_period: int,
    log_period: int,
    write_mode: int,
) -> dict[str, object]:
    if geometry == "cylinder":
        case_xml: Callable[[int, int, int, int, int], str] = gen_cyl_shadow_cases.case_xml
        solid_center = [48.0, 48.0, 48.0]
        solid_radius = 20.0
        slice_axis = "z"
        slice_index = 48
        liquid_axis = "+y"
    elif geometry == "sphere":
        case_xml = gen_sphere_shadow_cases.case_xml
        solid_center = [40.0, 40.0, 48.0]
        solid_radius = 20.0
        slice_axis = "y"
        slice_index = 40
        liquid_axis = "+z"
    else:
        raise ValueError(f"unsupported geometry: {geometry}")

    name = f"{geometry}_init{init_theta:03d}_to{target_theta:03d}_b3morph"
    case_dir = root / name
    case_dir.mkdir(parents=True, exist_ok=True)
    xml = case_xml(init_theta, iterations, vtk_period, log_period, write_mode)
    xml = replace_param_value(xml, "Stage17BShadowThetaDeg", target_theta)
    (case_dir / "case.xml").write_text(xml, encoding="utf-8")

    metadata = {
        "case": name,
        "geometry": geometry,
        "purpose": "Stage17B-B4 static morphology response smoke",
        "claim_limit": "morphology response smoke only; not contact-angle validation",
        "init_theta_deg": init_theta,
        "target_theta_deg": target_theta,
        "legacy_rad_angle_deg": 90,
        "stage17b_diffuse_solid_mode": 1,
        "stage17b_write_mode": write_mode,
        "wall_compact_stencil_mode": 0,
        "iterations": iterations,
        "vtk_period": vtk_period,
        "log_period": log_period,
        "solid_center": solid_center,
        "solid_radius": solid_radius,
        "slice_axis": slice_axis,
        "slice_index": slice_index,
        "liquid_axis": liquid_axis,
        "expected_response": (
            "target<init should spread; target>init should retract/stand taller; "
            "target=init is a stability/control case"
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
        default=Path("cases/diagnostics/stage17B_B4_morphology_20260624"),
    )
    parser.add_argument("--init-theta", type=int, default=90)
    parser.add_argument("--target-thetas", type=int, nargs="+", default=[60, 90, 120])
    parser.add_argument("--geometries", nargs="+", default=["cylinder", "sphere"])
    parser.add_argument("--iterations", type=int, default=3000)
    parser.add_argument("--vtk-period", type=int, default=1000)
    parser.add_argument("--log-period", type=int, default=200)
    parser.add_argument("--write-mode", type=int, default=2)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.root.mkdir(parents=True, exist_ok=True)
    cases: list[dict[str, object]] = []
    for geometry in args.geometries:
        for theta in args.target_thetas:
            cases.append(
                write_case(
                    args.root,
                    geometry=geometry,
                    target_theta=theta,
                    init_theta=args.init_theta,
                    iterations=args.iterations,
                    vtk_period=args.vtk_period,
                    log_period=args.log_period,
                    write_mode=args.write_mode,
                )
            )
    manifest = {
        "purpose": "Stage17B-B4 static morphology response smoke",
        "claim_limit": "morphology response smoke only; not contact-angle validation",
        "init_theta_deg": args.init_theta,
        "target_thetas": args.target_thetas,
        "geometries": args.geometries,
        "iterations": args.iterations,
        "vtk_period": args.vtk_period,
        "log_period": args.log_period,
        "stage17b_write_mode": args.write_mode,
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
