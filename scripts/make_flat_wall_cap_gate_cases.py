#!/usr/bin/env python3
"""Generate flat-wall spherical-cap gate cases for TCLB wall diagnostics.

These cases are runtime/contact-response diagnostics only. They initialize a
near-theoretical spherical cap through the default-off CapInit source lane so
the flat wall test is not dominated by a free sphere slowly spreading from a
remote initial condition.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


STATUS = "runtime_sanity"
DEFAULT_OUT = Path("cases") / "diagnostics" / "flat_wall_cap_v3diag_gate_20260611"
DEFAULT_REMOTE_ROOT = (
    "/mnt/8A0E24070E23EAC1/runs/tclb_flat_wall_cap_v3diag_gate_20260611"
)
DEFAULT_BINARY = (
    "/home/yuan/src/TCLB_clean_wall_signed_profile_v3diag_20260611/"
    "CLB/d3q27_pf_velocity_q27_geometric/main"
)
DEFAULT_BINARY_SHA256 = (
    "f585775753ebeee64f64e098d5ae01638ebff447e5370b7aa7b720d6afde9690"
)

VTK_WHAT = (
    "PhaseField,U,P,Rho,BOUNDARY,Normal,IsItBoundary,GradPhi,"
    "SpecialBoundaryPoint,WallPfF,WallGradTangent,WallTanCoeff,"
    "WallPhasePred,WallBCPath,WallPhaseProfilePred,WallProfileDelta,"
    "WallPhaseSignedProfilePred,WallSignedProfileDelta,WallSignedLogitShift"
)
STAGE7_EXTRA_VTK = (
    "WallFluidSampleCount,WallFluidSampleH,WallPhaseRawPred,"
    "WallPhaseSignedPred,WallContactResidual,WallSignedNormalGrad,"
    "WallTangentGradMag,WallSignedDeltaQ,WallSignedQClipped,BoundaryMask,"
    "WallH,WallGeomNormal,WallGrad1,WallGrad2,WallGradTangentVec,"
    "WallNormalCoeff1,WallNormalCoeff2,WallActualMinusProfile,WallActualMinusRaw"
)


@dataclass(frozen=True)
class GateCase:
    name: str
    init_theta_deg: float
    wall_rad_angle_deg: float
    purpose: str


DEFAULT_CASES = [
    GateCase("cap_theta030_wall030", 30.0, 30.0, "flat wall target theta030"),
    GateCase("cap_theta090_wall090", 90.0, 90.0, "flat wall neutral theta090"),
    GateCase("cap_theta150_wall150", 150.0, 150.0, "flat wall target theta150"),
    GateCase(
        "cap_theta030_wall011",
        30.0,
        11.0,
        "theta030 cap with current sphere-case radAngle011 control",
    ),
]


def cap_sphere_radius(volume_radius: float, theta_deg: float) -> float:
    theta = math.radians(theta_deg)
    denom = (1.0 - math.cos(theta)) ** 2 * (2.0 + math.cos(theta))
    if denom <= 0.0:
        raise ValueError(f"invalid cap theta {theta_deg}")
    return volume_radius * (4.0 / denom) ** (1.0 / 3.0)


def model_xml(
    *,
    density_h: float,
    density_l: float,
    viscosity_h: float,
    viscosity_l: float,
    sigma: float,
    mobility: float,
    int_width: float,
    wall_angle: float,
    min_gradient: float,
    use_stage7_signed_wall_ghost: bool,
    cap_radius: float,
    cap_center_x: float,
    cap_center_y: float,
    cap_center_z: float,
    cap_theta_rad: float,
) -> str:
    return f"""  <Model>
    <Param name="Density_h" value="{density_h:.16g}"/>
    <Param name="Density_l" value="{density_l:.16g}"/>
    <Param name="Viscosity_h" value="{viscosity_h:.16g}"/>
    <Param name="Viscosity_l" value="{viscosity_l:.16g}"/>
    <Param name="tauUpdate" value="3"/>
    <Param name="sigma" value="{sigma:.16g}"/>
    <Param name="M" value="{mobility:.16g}"/>
    <Param name="IntWidth" value="{int_width:.16g}"/>
    <Param name="Radius" value="0"/>
    <Param name="BubbleType" value="1"/>
    <Param name="CapInit" value="1"/>
    <Param name="CapInitRadius" value="{cap_radius:.16g}"/>
    <Param name="CapInitTheta" value="{cap_theta_rad:.16g}"/>
    <Param name="CapInitCenterX" value="{cap_center_x:.16g}"/>
    <Param name="CapInitCenterY" value="{cap_center_y:.16g}"/>
    <Param name="CapInitCenterZ" value="{cap_center_z:.16g}"/>
    <Param name="VelocityX" value="0.0"/>
    <Param name="VelocityY" value="0.0"/>
    <Param name="VelocityZ" value="0.0"/>
    <Param name="GravitationX" value="0.0"/>
    <Param name="GravitationY" value="0.0"/>
    <Param name="GravitationZ" value="0.0"/>
    <Param name="BuoyancyX" value="0.0"/>
    <Param name="BuoyancyY" value="0.0"/>
    <Param name="BuoyancyZ" value="0.0"/>
    <Param name="radAngle" value="90d"/>
    <Param name="radAngle" value="90d" zone="OuterDomain"/>
    <Param name="radAngle" value="{wall_angle:.16g}d" zone="FlatLowerY"/>
    <Param name="minGradient" value="{min_gradient:.16g}"/>
{stage7_param_xml(use_stage7_signed_wall_ghost)}
  </Model>"""


def stage7_param_xml(use_stage7_signed_wall_ghost: bool) -> str:
    if not use_stage7_signed_wall_ghost:
        return ""
    return '    <Param name="UseStage7SignedWallGhost" value="1"/>'


def xml_for_case(args: argparse.Namespace, case: GateCase, remote_case: str) -> tuple[str, dict[str, float]]:
    cap_radius = cap_sphere_radius(args.volume_radius, case.init_theta_deg)
    theta_rad = math.radians(case.init_theta_deg)
    cap_center_x = args.nx / 2.0
    cap_center_y = -cap_radius * math.cos(theta_rad)
    cap_center_z = args.nz / 2.0
    cap_height = cap_radius * (1.0 - math.cos(math.radians(case.init_theta_deg)))
    cap_base_radius = cap_radius * math.sin(math.radians(case.init_theta_deg))
    vtk_what = VTK_WHAT
    if args.stage7_signed_wall_ghost:
        vtk_what = f"{VTK_WHAT},{STAGE7_EXTRA_VTK}"
    meta = {
        "volume_equivalent_sphere_radius": args.volume_radius,
        "init_theta_deg": case.init_theta_deg,
        "wall_rad_angle_deg": case.wall_rad_angle_deg,
        "cap_sphere_radius": cap_radius,
        "cap_height": cap_height,
        "cap_base_radius": cap_base_radius,
        "cap_center_x": cap_center_x,
        "cap_center_y": cap_center_y,
        "cap_center_z": cap_center_z,
        "use_stage7_signed_wall_ghost": bool(args.stage7_signed_wall_ghost),
    }
    xml = f"""<?xml version="1.0"?>
<!--
  TCLB flat-wall spherical-cap gate.
  Status: {STATUS}; claim_limit=runtime_sanity_only.
  Purpose: {case.purpose}.
  Initial cap volume equals a free sphere of radius {args.volume_radius:g} lu.
  Requires source lane with default-off CapInit settings.
  Raw VTI/PVTI should remain remote-only.
-->
<CLBConfig version="2.0" output="{remote_case}/output/" permissive="true">
  <Geometry nx="{args.nx}" ny="{args.ny}" nz="{args.nz}">
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
{model_xml(
    density_h=args.density_h,
    density_l=args.density_l,
    viscosity_h=args.viscosity_h,
    viscosity_l=args.viscosity_l,
    sigma=args.sigma,
    mobility=args.mobility,
    int_width=args.int_width,
    wall_angle=case.wall_rad_angle_deg,
    min_gradient=args.min_gradient,
    use_stage7_signed_wall_ghost=args.stage7_signed_wall_ghost,
    cap_radius=cap_radius,
    cap_center_x=cap_center_x,
    cap_center_y=cap_center_y,
    cap_center_z=cap_center_z,
    cap_theta_rad=theta_rad,
)}
  <VTK what="{vtk_what}"/>
  <Log Iterations="{args.log_interval}"/>
  <Failcheck Iterations="{args.failcheck_interval}"/>
  <Solve Iterations="{args.steps}">
    <VTK Iterations="{args.vtk_interval}" what="{vtk_what}"/>
    <Log Iterations="{args.log_interval}"/>
    <Failcheck Iterations="{args.failcheck_interval}"/>
  </Solve>
</CLBConfig>
"""
    return xml, meta


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--remote-root", default=DEFAULT_REMOTE_ROOT)
    parser.add_argument("--steps", type=int, default=50000)
    parser.add_argument("--vtk-interval", type=int, default=10000)
    parser.add_argument("--log-interval", type=int, default=1000)
    parser.add_argument("--failcheck-interval", type=int, default=1000)
    parser.add_argument("--nx", type=int, default=128)
    parser.add_argument("--ny", type=int, default=96)
    parser.add_argument("--nz", type=int, default=128)
    parser.add_argument("--volume-radius", type=float, default=24.0)
    parser.add_argument("--int-width", type=float, default=6.0)
    parser.add_argument("--density-h", type=float, default=1.0)
    parser.add_argument("--density-l", type=float, default=0.001)
    parser.add_argument("--viscosity-h", type=float, default=0.09)
    parser.add_argument("--viscosity-l", type=float, default=0.1)
    parser.add_argument("--sigma", type=float, default=5.0e-5)
    parser.add_argument("--mobility", type=float, default=0.1)
    parser.add_argument("--min-gradient", type=float, default=1.0e-8)
    parser.add_argument("--binary", default=DEFAULT_BINARY)
    parser.add_argument("--binary-sha256", default=DEFAULT_BINARY_SHA256)
    parser.add_argument(
        "--stage7-signed-wall-ghost",
        action="store_true",
        help="write UseStage7SignedWallGhost=1 and request Stage7 diagnostic VTK fields",
    )
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    generated: list[dict[str, object]] = []
    for case in DEFAULT_CASES:
        remote_case = f"{args.remote_root}/{case.name}"
        xml, cap_meta = xml_for_case(args, case, remote_case)
        case_dir = args.out / case.name
        case_dir.mkdir(parents=True, exist_ok=True)
        xml_path = case_dir / "case.xml"
        meta_path = case_dir / "case_params.json"
        if xml_path.exists() and not args.force:
            raise SystemExit(f"{xml_path} exists; pass --force")
        xml_path.write_text(xml, encoding="utf-8")
        case_meta = {
            "status": STATUS,
            "case_id": case.name,
            "purpose": case.purpose,
            "remote_case": remote_case,
            "xml": str(xml_path),
            **cap_meta,
        }
        meta_path.write_text(json.dumps(case_meta, indent=2) + "\n", encoding="utf-8")
        generated.append(case_meta)

    manifest = {
        "status": STATUS,
        "claim_limit": "runtime_sanity and flat-wall diagnostic only; not validation",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "remote_root": args.remote_root,
        "binary": args.binary,
        "binary_sha256": args.binary_sha256,
        "domain": [args.nx, args.ny, args.nz],
        "steps": args.steps,
        "vtk_interval": args.vtk_interval,
        "vtk_what": f"{VTK_WHAT},{STAGE7_EXTRA_VTK}" if args.stage7_signed_wall_ghost else VTK_WHAT,
        "use_stage7_signed_wall_ghost": bool(args.stage7_signed_wall_ghost),
        "shared_parameters": {
            "Density_h": args.density_h,
            "Density_l": args.density_l,
            "Viscosity_h": args.viscosity_h,
            "Viscosity_l": args.viscosity_l,
            "sigma": args.sigma,
            "M": args.mobility,
            "IntWidth": args.int_width,
            "volume_radius": args.volume_radius,
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
