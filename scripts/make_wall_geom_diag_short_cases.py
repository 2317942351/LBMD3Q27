#!/usr/bin/env python3
"""Generate short flat/curved wall diagnostics for TCLB geometric wetting."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


STATUS = "runtime_sanity"
DEFAULT_OUT = Path("cases") / "diagnostics" / "wall_geom_diag_flat_curved_20260610"
DEFAULT_REMOTE_ROOT = (
    "/mnt/8A0E24070E23EAC1/runs/tclb_wall_geom_diag_flat_curved_20260610"
)
DIAG_BINARY = (
    "/home/yuan/src/TCLB_clean_wall_diag_20260610/"
    "CLB/d3q27_pf_velocity_q27_geometric/main"
)
DIAG_BINARY_SHA256 = "20be154bff84c1c4e29a37b7c422d85c279364076254ae2fb6caf68cf1f5573d"

VTK_WHAT = (
    "PhaseField,U,P,Rho,BOUNDARY,Normal,IsItBoundary,GradPhi,"
    "SpecialBoundaryPoint,WallPfF,WallGradTangent,WallTanCoeff,"
    "WallPhasePred,WallBCPath"
)
BOUNDED_VTK_EXTRA = "WallPhaseBoundedPred,WallClampDelta"
PROFILE_VTK_EXTRA = "WallPhaseProfilePred,WallProfileDelta"


def common_model(theta: int, center: tuple[float, float, float]) -> str:
    cx, cy, cz = center
    return f"""  <Model>
    <Param name="Density_h" value="1"/>
    <Param name="Density_l" value="0.001"/>
    <Param name="Viscosity_h" value="0.09"/>
    <Param name="Viscosity_l" value="0.1"/>
    <Param name="tauUpdate" value="3"/>
    <Param name="sigma" value="5e-05"/>
    <Param name="M" value="0.1"/>
    <Param name="IntWidth" value="6"/>
    <Param name="Radius" value="24"/>
    <Param name="BubbleType" value="1"/>
    <Param name="CenterX" value="{cx:.16g}"/>
    <Param name="CenterY" value="{cy:.16g}"/>
    <Param name="CenterZ" value="{cz:.16g}"/>
    <Param name="VelocityX" value="0.0"/>
    <Param name="VelocityY" value="0.0"/>
    <Param name="VelocityZ" value="0.0"/>
    <Param name="GravitationX" value="0.0"/>
    <Param name="GravitationY" value="0.0"/>
    <Param name="GravitationZ" value="0.0"/>
    <Param name="BuoyancyX" value="0.0"/>
    <Param name="BuoyancyY" value="0.0"/>
    <Param name="BuoyancyZ" value="0.0"/>
    <Param name="radAngle" value="{theta}d"/>
    <Param name="minGradient" value="1e-08"/>
  </Model>"""


def xml_flat(theta: int, remote_case: str, steps: int, vtk_interval: int, vtk_what: str) -> str:
    return f"""<?xml version="1.0"?>
<!--
  TCLB geometric wetting wall diagnostic, flat wall.
  Status: {STATUS}.
  Purpose: compare WallPfF/WallGradTangent/WallTanCoeff/WallPhasePred/WallBCPath.
-->
<CLBConfig version="2.0" output="{remote_case}/output/" permissive="true">
  <Geometry nx="80" ny="80" nz="80">
    <MRT><Box/></MRT>
    <Wall mask="ALL" name="OuterDomain">
      <Box nx="1"/>
      <Box dx="-1"/>
      <Box dy="-1"/>
      <Box nz="1"/>
      <Box dz="-1"/>
    </Wall>
    <Wall mask="ALL" name="FlatLowerY">
      <Box ny="1"/>
    </Wall>
  </Geometry>
{common_model(theta, (40.0, 0.0, 40.0))}
  <VTK what="{vtk_what}"/>
  <Log Iterations="10"/>
  <Failcheck Iterations="10"/>
  <Solve Iterations="{steps}">
    <VTK Iterations="{vtk_interval}" what="{vtk_what}"/>
    <Log Iterations="10"/>
    <Failcheck Iterations="10"/>
  </Solve>
</CLBConfig>
"""


def xml_curved(theta: int, remote_case: str, steps: int, vtk_interval: int, vtk_what: str) -> str:
    return f"""<?xml version="1.0"?>
<!--
  TCLB geometric wetting wall diagnostic, curved spherical wall.
  Status: {STATUS}.
  Geometry follows the reduced PRE Table II analogue: 80x80x140, R_drop=24, R_solid=24.
-->
<CLBConfig version="2.0" output="{remote_case}/output/" permissive="true">
  <Geometry nx="80" ny="80" nz="140">
    <MRT><Box/></MRT>
    <Wall mask="ALL" name="OuterDomain">
      <Box nx="1"/>
      <Box dx="-1"/>
      <Box ny="1"/>
      <Box dy="-1"/>
      <Box nz="1"/>
      <Box dz="-1"/>
    </Wall>
    <Wall mask="ALL" name="SolidSphere">
      <Sphere dx="16" nx="48" dy="16" ny="48" dz="0" nz="48"/>
    </Wall>
  </Geometry>
{common_model(theta, (40.0, 40.0, 72.0))}
  <VTK what="{vtk_what}"/>
  <Log Iterations="10"/>
  <Failcheck Iterations="10"/>
  <Solve Iterations="{steps}">
    <VTK Iterations="{vtk_interval}" what="{vtk_what}"/>
    <Log Iterations="10"/>
    <Failcheck Iterations="10"/>
  </Solve>
</CLBConfig>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--remote-root", default=DEFAULT_REMOTE_ROOT)
    parser.add_argument("--steps", type=int, default=50)
    parser.add_argument("--vtk-interval", type=int, default=50)
    parser.add_argument("--angles", default="30,90")
    parser.add_argument("--geometries", default="flat,curved")
    parser.add_argument("--binary", default=DIAG_BINARY)
    parser.add_argument("--binary-sha256", default=DIAG_BINARY_SHA256)
    parser.add_argument(
        "--include-bounded-fields",
        action="store_true",
        help="Add WallPhaseBoundedPred and WallClampDelta to VTK output.",
    )
    parser.add_argument(
        "--include-profile-fields",
        action="store_true",
        help="Add WallPhaseProfilePred and WallProfileDelta to VTK output.",
    )
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    angles = [int(v.strip()) for v in args.angles.split(",") if v.strip()]
    geometries = [v.strip() for v in args.geometries.split(",") if v.strip()]
    invalid = sorted(set(geometries) - {"flat", "curved"})
    if invalid:
        raise SystemExit(f"invalid geometries: {', '.join(invalid)}")
    vtk_what = VTK_WHAT
    if args.include_bounded_fields:
        vtk_what = f"{VTK_WHAT},{BOUNDED_VTK_EXTRA}"
    if args.include_profile_fields:
        vtk_what = f"{vtk_what},{PROFILE_VTK_EXTRA}"
    generated = []
    for geometry in geometries:
        for theta in angles:
            case_id = f"{geometry}_theta{theta:03d}"
            remote_case = f"{args.remote_root}/{case_id}"
            path = args.out / f"{case_id}.xml"
            if path.exists() and not args.force:
                raise SystemExit(f"{path} exists; pass --force")
            text = (
                xml_flat(theta, remote_case, args.steps, args.vtk_interval, vtk_what)
                if geometry == "flat"
                else xml_curved(theta, remote_case, args.steps, args.vtk_interval, vtk_what)
            )
            path.write_text(text, encoding="utf-8")
            generated.append(
                {
                    "case_id": case_id,
                    "geometry": geometry,
                    "theta_deg": theta,
                    "case_xml": str(path),
                    "remote_case": remote_case,
                }
            )

    manifest = {
        "status": STATUS,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "short flat/curved wall formula diagnostics, not validation",
        "diagnostic_binary": args.binary,
        "diagnostic_binary_sha256": args.binary_sha256,
        "remote_root": args.remote_root,
        "steps": args.steps,
        "vtk_interval": args.vtk_interval,
        "vtk_what": vtk_what,
        "shared_parameters": {
            "Density_h": 1.0,
            "Density_l": 0.001,
            "Viscosity_h": 0.09,
            "Viscosity_l": 0.1,
            "sigma": 5.0e-5,
            "M": 0.1,
            "IntWidth": 6,
            "Radius": 24,
        },
        "generated": generated,
    }
    manifest_path = args.out / "manifest.json"
    if manifest_path.exists() and not args.force:
        raise SystemExit(f"{manifest_path} exists; pass --force")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
