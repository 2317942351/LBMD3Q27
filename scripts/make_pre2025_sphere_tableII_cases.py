#!/usr/bin/env python3
"""Generate TCLB PRE 2025 Table II reduced spherical-surface wetting cases.

The generator prepares XML and reference tables only. It does not launch TCLB.
All generated cases are TCLB analogues, not exact PRE-model reproductions.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


STATUS = "exploratory_not_validation"
DEFAULT_CASE_DIR = Path("cases") / "validation" / "pre2025_sphere_tableII_20260609"
DEFAULT_REMOTE_ROOT = (
    "/media/yuan/8A0E24070E23EAC1/runs/"
    "tclb_pre2025_sphere_tableII_20260609"
)
DEFAULT_REFERENCE_DIR = Path("references") / "pre2025_wetting_boundary"
PRIMARY_BINARY = "/home/yuan/src/TCLB/CLB/d3q27_pf_velocity_q27_geometric_staircaseimp/main"


@dataclass(frozen=True)
class SphereSetup:
    nx: int = 80
    ny: int = 80
    nz: int = 140
    drop_radius: float = 24.0
    solid_radius: float = 24.0
    solid_center_x: float = 40.0
    solid_center_y: float = 40.0
    solid_center_z: float = 24.0

    @property
    def drop_center_x(self) -> float:
        return self.solid_center_x

    @property
    def drop_center_y(self) -> float:
        return self.solid_center_y

    @property
    def drop_center_z(self) -> float:
        return self.solid_center_z + self.solid_radius + self.drop_radius

    @property
    def solid_sphere_dx(self) -> float:
        return self.solid_center_x - self.solid_radius

    @property
    def solid_sphere_dy(self) -> float:
        return self.solid_center_y - self.solid_radius

    @property
    def solid_sphere_dz(self) -> float:
        return self.solid_center_z - self.solid_radius

    @property
    def solid_sphere_diameter(self) -> float:
        return 2.0 * self.solid_radius


def sphere_intersection_volume(radius_a: float, radius_b: float, distance: float) -> float:
    if distance >= radius_a + radius_b:
        return 0.0
    if distance <= abs(radius_a - radius_b):
        return 4.0 / 3.0 * math.pi * min(radius_a, radius_b) ** 3
    return (
        math.pi
        * (radius_a + radius_b - distance) ** 2
        * (
            distance * distance
            + 2.0 * distance * (radius_a + radius_b)
            - 3.0 * (radius_a - radius_b) ** 2
        )
        / (12.0 * distance)
    )


def liquid_volume_outside_solid(
    solid_radius: float, liquid_radius: float, center_distance: float
) -> float:
    return (
        4.0 / 3.0 * math.pi * liquid_radius**3
        - sphere_intersection_volume(solid_radius, liquid_radius, center_distance)
    )


def theoretical_sphere_target(
    solid_radius: float, initial_drop_radius: float, theta_deg: float
) -> dict[str, float]:
    """Return analytic target for a conserved droplet on a solid sphere.

    The geometry uses the branch matching the extracted PRE Table I Hmax values
    for 50-150 degrees. The 30-degree PRE Table I value remains a recorded
    low-angle crosscheck caveat in metadata.
    """

    target_volume = 4.0 / 3.0 * math.pi * initial_drop_radius**3
    cos_theta = math.cos(math.radians(theta_deg))

    def residual(liquid_radius: float) -> float:
        center_distance = math.sqrt(
            solid_radius * solid_radius
            + liquid_radius * liquid_radius
            - 2.0 * solid_radius * liquid_radius * cos_theta
        )
        return (
            liquid_volume_outside_solid(solid_radius, liquid_radius, center_distance)
            - target_volume
        )

    lo = 1.0e-12
    hi = max(1.0, initial_drop_radius)
    while residual(hi) < 0.0:
        hi *= 2.0
        if hi > 1.0e7:
            raise RuntimeError(f"could not bracket theoretical target for theta={theta_deg}")

    for _ in range(180):
        mid = 0.5 * (lo + hi)
        if residual(mid) < 0.0:
            lo = mid
        else:
            hi = mid

    liquid_radius = 0.5 * (lo + hi)
    center_distance = math.sqrt(
        solid_radius * solid_radius
        + liquid_radius * liquid_radius
        - 2.0 * solid_radius * liquid_radius * cos_theta
    )
    hmax = liquid_radius + center_distance
    return {
        "liquid_spherical_cap_radius_lu": liquid_radius,
        "liquid_solid_center_distance_lu": center_distance,
        "expected_Hmax_lu": hmax,
        "expected_H1_minus_H2_lu": hmax - solid_radius,
        "initial_drop_volume_lu3": target_volume,
    }


def parse_angles(text: str) -> list[int]:
    return [int(value.strip()) for value in text.split(",") if value.strip()]


def parse_input_angle_map(text: str) -> dict[int, float]:
    if not text.strip():
        return {}
    mapping: dict[int, float] = {}
    for item in text.split(","):
        if not item.strip():
            continue
        if ":" not in item:
            raise ValueError(
                f"input angle mapping item {item!r} must be TARGET:RADANGLE"
            )
        target_text, input_text = item.split(":", 1)
        mapping[int(target_text.strip())] = float(input_text.strip())
    return mapping


def xml_for(
    setup: SphereSetup,
    theta: int,
    rad_angle_deg: float,
    remote_case_dir: str,
    args: argparse.Namespace,
) -> str:
    vtk_what = "PhaseField,U,P,Rho,BOUNDARY,Normal,IsItBoundary,GradPhi,ActualNormal"
    if args.vtk_extra:
        vtk_what = f"{vtk_what},{args.vtk_extra}"
    return f"""<?xml version="1.0"?>
<!--
  PRE 2025 Table II reduced spherical-surface static wetting TCLB analogue.
  Status: {STATUS}.
  Geometry: 80x80x140, R_drop=24, R_solid=24, target theta={theta} deg.
  TCLB input radAngle={rad_angle_deg:.16g} deg.
  Raw VTI/PVTI should remain remote-only.
-->
<CLBConfig version="2.0" output="{remote_case_dir}/output/" permissive="true">
  <Geometry nx="{setup.nx}" ny="{setup.ny}" nz="{setup.nz}">
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
      <Sphere dx="{setup.solid_sphere_dx:.16g}" nx="{setup.solid_sphere_diameter:.16g}" dy="{setup.solid_sphere_dy:.16g}" ny="{setup.solid_sphere_diameter:.16g}" dz="{setup.solid_sphere_dz:.16g}" nz="{setup.solid_sphere_diameter:.16g}"/>
    </Wall>
  </Geometry>
  <Model>
    <Param name="Density_h" value="{args.density_h:.16g}"/>
    <Param name="Density_l" value="{args.density_l:.16g}"/>
    <Param name="Viscosity_h" value="{args.viscosity_h:.16g}"/>
    <Param name="Viscosity_l" value="{args.viscosity_l:.16g}"/>
    <Param name="tauUpdate" value="{args.tau_update}"/>
    <Param name="sigma" value="{args.sigma:.16g}"/>
    <Param name="M" value="{args.mobility:.16g}"/>
    <Param name="IntWidth" value="{args.int_width:.16g}"/>
    <Param name="Radius" value="{setup.drop_radius:.16g}"/>
    <Param name="BubbleType" value="1"/>
    <Param name="CenterX" value="{setup.drop_center_x:.16g}"/>
    <Param name="CenterY" value="{setup.drop_center_y:.16g}"/>
    <Param name="CenterZ" value="{setup.drop_center_z:.16g}"/>
    <Param name="VelocityX" value="0.0"/>
    <Param name="VelocityY" value="0.0"/>
    <Param name="VelocityZ" value="0.0"/>
    <Param name="DropletOnlyVelocity" value="0.0"/>
    <Param name="DropletVelocityX" value="0.0"/>
    <Param name="DropletVelocityY" value="0.0"/>
    <Param name="DropletVelocityZ" value="0.0"/>
    <Param name="GravitationX" value="0.0"/>
    <Param name="GravitationY" value="0.0"/>
    <Param name="GravitationZ" value="0.0"/>
    <Param name="BuoyancyX" value="0.0"/>
    <Param name="BuoyancyY" value="0.0"/>
    <Param name="BuoyancyZ" value="0.0"/>
    <Param name="radAngle" value="{rad_angle_deg:.16g}d"/>
    <Param name="minGradient" value="{args.min_gradient:.16g}"/>
  </Model>
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


def write_reference_targets(
    reference_dir: Path, setup: SphereSetup, angles: list[int], force: bool
) -> Path:
    reference_dir.mkdir(parents=True, exist_ok=True)
    path = reference_dir / "table_II_sphere_targets.csv"
    if path.exists() and not force:
        return path
    rows = []
    for theta in angles:
        target = theoretical_sphere_target(setup.solid_radius, setup.drop_radius, theta)
        rows.append(
            {
                "theta_deg": theta,
                "domain_nx": setup.nx,
                "domain_ny": setup.ny,
                "domain_nz": setup.nz,
                "R_drop_lu": setup.drop_radius,
                "R_solid_lu": setup.solid_radius,
                **target,
                "target_note": (
                    "H1_minus_H2 = Hmax - R_solid; generated from conserved "
                    "sphere-on-sphere geometry; low-angle exactness pending PDF audit"
                ),
            }
        )
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-dir", type=Path, default=DEFAULT_CASE_DIR)
    parser.add_argument("--reference-dir", type=Path, default=DEFAULT_REFERENCE_DIR)
    parser.add_argument("--remote-root", default=DEFAULT_REMOTE_ROOT)
    parser.add_argument("--nx", type=int, default=80)
    parser.add_argument("--ny", type=int, default=80)
    parser.add_argument("--nz", type=int, default=140)
    parser.add_argument("--drop-radius", type=float, default=24.0)
    parser.add_argument("--solid-radius", type=float, default=24.0)
    parser.add_argument("--solid-center-x", type=float, default=40.0)
    parser.add_argument("--solid-center-y", type=float, default=40.0)
    parser.add_argument("--solid-center-z", type=float, default=24.0)
    parser.add_argument("--angles", default="30,40,50,60,70,80,90,100,110,120,130")
    parser.add_argument(
        "--input-angle-map",
        default="",
        help=(
            "Optional comma-separated TARGET:RADANGLE map. The target angle "
            "selects the analytical Table II target and case tag, while "
            "RADANGLE is written to TCLB radAngle. Example: 90:80,130:113."
        ),
    )
    parser.add_argument("--steps", type=int, default=200000)
    parser.add_argument("--vtk-interval", type=int, default=20000)
    parser.add_argument("--log-interval", type=int, default=1000)
    parser.add_argument("--failcheck-interval", type=int, default=1000)
    parser.add_argument("--density-h", type=float, default=1.0)
    parser.add_argument("--density-l", type=float, default=0.001)
    parser.add_argument("--viscosity-h", type=float, default=0.09)
    parser.add_argument("--viscosity-l", type=float, default=0.1)
    parser.add_argument("--sigma", type=float, default=5.0e-5)
    parser.add_argument(
        "--mobility",
        type=float,
        default=0.2,
        help="TCLB mobility M; PRE 2025 tau_f=1.1 implies M=(1/3)*(1.1-0.5)=0.2.",
    )
    parser.add_argument("--int-width", type=float, default=6.0)
    parser.add_argument(
        "--tau-update",
        type=int,
        default=3,
        help="TCLB viscosity interpolation mode; 3 uses dynamic-viscosity interpolation.",
    )
    parser.add_argument("--min-gradient", type=float, default=1.0e-8)
    parser.add_argument("--binary", default=PRIMARY_BINARY)
    parser.add_argument(
        "--vtk-extra",
        default="",
        help="Optional comma-separated extra VTK quantities for diagnostic binaries.",
    )
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup = SphereSetup(
        nx=args.nx,
        ny=args.ny,
        nz=args.nz,
        drop_radius=args.drop_radius,
        solid_radius=args.solid_radius,
        solid_center_x=args.solid_center_x,
        solid_center_y=args.solid_center_y,
        solid_center_z=args.solid_center_z,
    )
    angles = parse_angles(args.angles)
    input_angle_map = parse_input_angle_map(args.input_angle_map)
    reference_angles = parse_angles("30,40,50,60,70,80,90,100,110,120,130")
    args.case_dir.mkdir(parents=True, exist_ok=True)
    targets_path = write_reference_targets(
        args.reference_dir, setup, reference_angles, args.force
    )

    generated = []
    for theta in angles:
        rad_angle_deg = input_angle_map.get(theta, float(theta))
        case_tag = f"theta{theta:03d}"
        case_dir = args.case_dir / case_tag
        case_dir.mkdir(parents=True, exist_ok=True)
        remote_case_dir = f"{args.remote_root}/{case_tag}"
        xml_path = case_dir / f"pre2025_sphere_tableII_{case_tag}.xml"
        if xml_path.exists() and not args.force:
            raise SystemExit(f"{xml_path} exists; pass --force")
        xml_path.write_text(
            xml_for(setup, theta, rad_angle_deg, remote_case_dir, args),
            encoding="utf-8",
        )
        target = theoretical_sphere_target(setup.solid_radius, setup.drop_radius, theta)
        generated.append(
            {
                "theta_deg": theta,
                "tclb_radAngle_deg": rad_angle_deg,
                "case_tag": case_tag,
                "case_xml": str(xml_path),
                "remote_case_dir": remote_case_dir,
                "remote_output_dir": f"{remote_case_dir}/output",
                "expected_Hmax_lu": target["expected_Hmax_lu"],
                "expected_H1_minus_H2_lu": target["expected_H1_minus_H2_lu"],
                "status": STATUS,
            }
        )

    manifest = {
        "status": STATUS,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "PRE 2025 Table II reduced sphere static wetting TCLB analogue setup",
        "binary": args.binary,
        "remote_root": args.remote_root,
        "case_dir": str(args.case_dir),
        "reference_targets": str(targets_path),
        "reference_target_angles_deg": reference_angles,
        "input_angle_map_deg": {
            str(theta): input_angle_map.get(theta, float(theta)) for theta in angles
        },
        "domain_lu": [setup.nx, setup.ny, setup.nz],
        "cells": setup.nx * setup.ny * setup.nz,
        "solid_sphere": {
            "radius_lu": setup.solid_radius,
            "center_lu": [
                setup.solid_center_x,
                setup.solid_center_y,
                setup.solid_center_z,
            ],
            "xml_sphere": {
                "dx": setup.solid_sphere_dx,
                "dy": setup.solid_sphere_dy,
                "dz": setup.solid_sphere_dz,
                "nx": setup.solid_sphere_diameter,
                "ny": setup.solid_sphere_diameter,
                "nz": setup.solid_sphere_diameter,
            },
        },
        "outer_domain_boundary": {
            "node_type": "Wall",
            "reason": "The article states that no-slip is applied at all computational domain boundaries.",
            "boxes": ["x-min", "x-max", "y-min", "y-max", "z-min", "z-max"],
        },
        "initial_drop": {
            "radius_lu": setup.drop_radius,
            "center_lu": [
                setup.drop_center_x,
                setup.drop_center_y,
                setup.drop_center_z,
            ],
            "initial_relation_to_solid": "initial diffuse sphere tangent to the top of the solid sphere",
        },
        "fluid_parameters": {
            "Density_h": args.density_h,
            "Density_l": args.density_l,
            "density_ratio_h_over_l": args.density_h / args.density_l,
            "Viscosity_h": args.viscosity_h,
            "Viscosity_l": args.viscosity_l,
            "tauUpdate": args.tau_update,
            "dynamic_viscosity_ratio_h_over_l": (
                args.density_h * args.viscosity_h / (args.density_l * args.viscosity_l)
            ),
            "sigma": args.sigma,
            "M": args.mobility,
            "IntWidth": args.int_width,
        },
        "solve": {
            "steps": args.steps,
            "vtk_interval": args.vtk_interval,
            "log_interval": args.log_interval,
            "failcheck_interval": args.failcheck_interval,
            "vtk_extra": args.vtk_extra,
        },
        "metrics_to_report": [
            "H1_minus_H2_relative_error",
            "Hmax_relative_error",
            "global_spherical_cap_contact_angle",
            "spurious_velocity",
            "mass_drift",
            "rho_drift",
            "max_Mach",
            "nonfinite_count",
            "NumSpecialPoints",
            "NumWallBoundaryPoints",
            "NumBoundaryPoints",
        ],
        "generated": generated,
        "claim_limit": (
            "Prepared cases only. Do not call successful execution validation "
            "without read-only audit and formula/metric review."
        ),
    }
    manifest_path = args.case_dir / "manifest.json"
    if manifest_path.exists() and not args.force:
        raise SystemExit(f"{manifest_path} exists; pass --force")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
