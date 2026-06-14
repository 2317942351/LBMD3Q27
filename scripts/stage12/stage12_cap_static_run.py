#!/usr/bin/env python3
"""Generate and run one Stage12 cap-initialized static wetting case.

The generated cases are short static-contact smoke tests unless the downstream
audit and longer equilibrium gates explicitly promote them. The key purpose is
to start from a real contact-line initial condition instead of a free sphere
that never touches the wall.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_BIN = (
    "/home/yuan/data_sda/RUNS/runs/stage9/src/"
    "TCLB_stage9_analytic_wetting_20260614/"
    "CLB/d3q27_pf_velocity_q27_geometric/main"
)
DEFAULT_ROOT = "/home/yuan/data_sda/RUNS/runs/stage12_cap_static_smoke_20260614"
VTK_FIELDS = "PhaseField,Rho,U,P,BOUNDARY,IsItBoundary,WallGhost,WallH,AnalyticWallNormal,AnalyticFlag"


@dataclass(frozen=True)
class CaseSpec:
    geom: str
    grid: tuple[int, int, int]
    geometry_block: str
    solid_params: str
    init_params: str
    solid_center: tuple[float, float, float]
    solid_radius: float
    cylinder_axis: int
    liquid_probe: tuple[float, float, float]
    cap_parent_radius: float
    cap_center: tuple[float, float, float]
    claim_limit: str
    plane_axis: int | None = None
    plane_offset: float | None = None


def cap_sphere_radius(volume_radius: float, theta_deg: float) -> float:
    theta = math.radians(theta_deg)
    denom = (1.0 - math.cos(theta)) ** 2 * (2.0 + math.cos(theta))
    if denom <= 0.0:
        raise ValueError(f"invalid cap theta: {theta_deg}")
    return volume_radius * (4.0 / denom) ** (1.0 / 3.0)


def overlap_volume(a: float, b: float, d: float) -> float:
    if d >= a + b:
        return 0.0
    if d <= abs(a - b):
        return 4.0 * math.pi * min(a, b) ** 3 / 3.0
    return math.pi * (a + b - d) ** 2 * (
        d * d + 2.0 * d * (a + b) - 3.0 * (a - b) ** 2
    ) / (12.0 * d)


def sphere_cap_parent_radius(solid_radius: float, volume_radius: float, theta_deg: float) -> tuple[float, float]:
    target = 4.0 * math.pi * volume_radius ** 3 / 3.0
    theta = math.radians(theta_deg)

    def outside_volume(parent_radius: float) -> float:
        d = math.sqrt(
            solid_radius * solid_radius
            + parent_radius * parent_radius
            - 2.0 * solid_radius * parent_radius * math.cos(theta)
        )
        return 4.0 * math.pi * parent_radius ** 3 / 3.0 - overlap_volume(
            solid_radius, parent_radius, d
        )

    lo = 1.0e-9
    hi = max(2.0 * volume_radius, 2.0 * solid_radius)
    while outside_volume(hi) < target:
        hi *= 2.0
    for _ in range(180):
        mid = 0.5 * (lo + hi)
        if outside_volume(mid) < target:
            lo = mid
        else:
            hi = mid
    parent = 0.5 * (lo + hi)
    center_distance = math.sqrt(
        solid_radius * solid_radius
        + parent * parent
        - 2.0 * solid_radius * parent * math.cos(theta)
    )
    return parent, center_distance


def param(name: str, value: str | float | int) -> str:
    return f'    <Param name="{name}" value="{value}"/>'


def case_spec(geom: str, theta_deg: float, volume_radius: float, int_width: float) -> CaseSpec:
    theta_rad = math.radians(theta_deg)
    if geom == "wall":
        parent_radius = cap_sphere_radius(volume_radius, theta_deg)
        cap_center = (48.0, -parent_radius * math.cos(theta_rad), 48.0)
        init_params = "\n".join(
            [
                param("Radius", 0),
                param("CenterX", cap_center[0]),
                param("CenterY", max(2.0, parent_radius * (1.0 - math.cos(theta_rad)) * 0.35)),
                param("CenterZ", cap_center[2]),
                param("CapInit", 1),
                param("CapInitRadius", f"{parent_radius:.16g}"),
                param("CapInitTheta", f"{theta_rad:.16g}"),
                param("CapInitCenterX", f"{cap_center[0]:.16g}"),
                param("CapInitCenterY", f"{cap_center[1]:.16g}"),
                param("CapInitCenterZ", f"{cap_center[2]:.16g}"),
            ]
        )
        return CaseSpec(
            geom=geom,
            grid=(96, 80, 96),
            geometry_block="""    <Wall mask="ALL" name="OuterDomain">
      <Box nx="1"/><Box dx="-1"/><Box dy="-1"/><Box nz="1"/><Box dz="-1"/>
    </Wall>
    <Wall mask="ALL" name="FlatLowerY"><Box ny="1"/></Wall>""",
            solid_params="\n".join(
                [
                    param("AnalyticSolidType", 1),
                    param("AnalyticSolidAxis", 1),
                    param("AnalyticSolidPlaneOffset", 0.0),
                ]
            ),
            init_params=init_params,
            solid_center=(48.0, 0.0, 48.0),
            solid_radius=0.0,
            cylinder_axis=0,
            liquid_probe=(48.0, 2.0, 48.0),
            cap_parent_radius=parent_radius,
            cap_center=cap_center,
            claim_limit="validation_candidate_only_after_contact_audit_and_equilibrium_run",
            plane_axis=1,
            plane_offset=0.0,
        )

    if geom == "sphere":
        solid_center = (40.0, 40.0, 48.0)
        solid_radius = 20.0
        parent_radius, center_distance = sphere_cap_parent_radius(solid_radius, volume_radius, theta_deg)
        cap_center = (solid_center[0], solid_center[1], solid_center[2] + center_distance)
        liquid_probe = (solid_center[0], solid_center[1], solid_center[2] + solid_radius + 4.0)
        init_params = "\n".join(
            [
                param("Radius", 0),
                param("CenterX", liquid_probe[0]),
                param("CenterY", liquid_probe[1]),
                param("CenterZ", liquid_probe[2]),
                param("SphereCapInit", 1),
                param("SphereCapInitParentRadius", f"{parent_radius:.16g}"),
                param("SphereCapInitCenterX", f"{cap_center[0]:.16g}"),
                param("SphereCapInitCenterY", f"{cap_center[1]:.16g}"),
                param("SphereCapInitCenterZ", f"{cap_center[2]:.16g}"),
                param("SphereCapInitSolidCenterX", f"{solid_center[0]:.16g}"),
                param("SphereCapInitSolidCenterY", f"{solid_center[1]:.16g}"),
                param("SphereCapInitSolidCenterZ", f"{solid_center[2]:.16g}"),
                param("SphereCapInitSolidRadius", f"{solid_radius:.16g}"),
            ]
        )
        return CaseSpec(
            geom=geom,
            grid=(80, 80, 120),
            geometry_block="""    <Wall mask="ALL" name="OuterDomain">
      <Box nx="1"/><Box dx="-1"/><Box ny="1"/><Box dy="-1"/><Box nz="1"/><Box dz="-1"/>
    </Wall>
    <Wall mask="ALL" name="AnalyticSphere">
      <Sphere dx="20" nx="40" dy="20" ny="40" dz="28" nz="40"/>
    </Wall>""",
            solid_params="\n".join(
                [
                    param("AnalyticSolidType", 3),
                    param("AnalyticSolidCenterX", solid_center[0]),
                    param("AnalyticSolidCenterY", solid_center[1]),
                    param("AnalyticSolidCenterZ", solid_center[2]),
                    param("AnalyticSolidRadius", solid_radius),
                ]
            ),
            init_params=init_params,
            solid_center=solid_center,
            solid_radius=solid_radius,
            cylinder_axis=0,
            liquid_probe=liquid_probe,
            cap_parent_radius=parent_radius,
            cap_center=cap_center,
            claim_limit="validation_candidate_only_after_contact_audit_and_equilibrium_run",
        )

    if geom == "cylinder":
        solid_center = (48.0, 48.0, 48.0)
        solid_radius = 20.0
        parent_radius, center_distance = sphere_cap_parent_radius(solid_radius, volume_radius, theta_deg)
        cap_center = (solid_center[0], solid_center[1] + center_distance, solid_center[2])
        liquid_probe = (solid_center[0], solid_center[1] + solid_radius + 4.0, solid_center[2])
        init_params = "\n".join(
            [
                param("Radius", 0),
                param("CenterX", liquid_probe[0]),
                param("CenterY", liquid_probe[1]),
                param("CenterZ", liquid_probe[2]),
                param("CylinderCapInit", 1),
                param("CylinderCapInitParentRadius", f"{parent_radius:.16g}"),
                param("CylinderCapInitCenterX", f"{cap_center[0]:.16g}"),
                param("CylinderCapInitCenterY", f"{cap_center[1]:.16g}"),
                param("CylinderCapInitCenterZ", f"{cap_center[2]:.16g}"),
                param("CylinderCapInitSolidCenterX", f"{solid_center[0]:.16g}"),
                param("CylinderCapInitSolidCenterY", f"{solid_center[1]:.16g}"),
                param("CylinderCapInitSolidCenterZ", f"{solid_center[2]:.16g}"),
                param("CylinderCapInitSolidRadius", f"{solid_radius:.16g}"),
                param("CylinderCapInitSolidAxis", 2),
            ]
        )
        return CaseSpec(
            geom=geom,
            grid=(96, 96, 96),
            geometry_block="""    <Wall mask="ALL" name="OuterDomain">
      <Box nx="1"/><Box dx="-1"/><Box ny="1"/><Box dy="-1"/><Box nz="1"/><Box dz="-1"/>
    </Wall>
    <Wall mask="ALL" name="AnalyticCylinder">
      <Cylinder dx="28" nx="40" dy="28" ny="40" dz="0" nz="96"/>
    </Wall>""",
            solid_params="\n".join(
                [
                    param("AnalyticSolidType", 2),
                    param("AnalyticSolidAxis", 2),
                    param("AnalyticSolidCenterX", solid_center[0]),
                    param("AnalyticSolidCenterY", solid_center[1]),
                    param("AnalyticSolidCenterZ", solid_center[2]),
                    param("AnalyticSolidRadius", solid_radius),
                ]
            ),
            init_params=init_params,
            solid_center=solid_center,
            solid_radius=solid_radius,
            cylinder_axis=2,
            liquid_probe=liquid_probe,
            cap_parent_radius=parent_radius,
            cap_center=cap_center,
            claim_limit="runtime_sanity_cylinder_cap_initializer_uses_local_convex_approximation",
        )

    raise ValueError(f"unknown geometry: {geom}")


def render_xml(spec: CaseSpec, theta_deg: float, iterations: int, mobility: float, int_width: float) -> str:
    nx, ny, nz = spec.grid
    target_zone = {"wall": "FlatLowerY", "sphere": "AnalyticSphere", "cylinder": "AnalyticCylinder"}[spec.geom]
    return f"""<?xml version="1.0"?>
<CLBConfig version="2.0" output="output/" permissive="true">
  <Geometry nx="{nx}" ny="{ny}" nz="{nz}">
    <MRT><Box/></MRT>
{spec.geometry_block}
  </Geometry>
  <Model>
    <Param name="Density_h" value="1"/>
    <Param name="Density_l" value="0.001"/>
    <Param name="Viscosity_h" value="0.1"/>
    <Param name="Viscosity_l" value="0.1"/>
    <Param name="tauUpdate" value="1"/>
    <Param name="sigma" value="5e-05"/>
    <Param name="M" value="{mobility:.16g}"/>
    <Param name="IntWidth" value="{int_width:.16g}"/>
{spec.init_params}
    <Param name="BubbleType" value="1.0"/>
    <Param name="VelocityX" value="0.0"/>
    <Param name="VelocityY" value="0.0"/>
    <Param name="VelocityZ" value="0.0"/>
    <Param name="GravitationX" value="0.0"/>
    <Param name="GravitationY" value="0.0"/>
    <Param name="GravitationZ" value="0.0"/>
    <Param name="radAngle" value="90d"/>
    <Param name="radAngle" value="90d" zone="OuterDomain"/>
{spec.solid_params}
    <Param name="AnalyticWetting" value="1"/>
    <Param name="radAngle" value="{theta_deg:.16g}d" zone="{target_zone}"/>
    <Param name="minGradient" value="1e-08"/>
  </Model>
  <VTK what="{VTK_FIELDS}"/>
  <Log Iterations="50"/>
  <Failcheck Iterations="50"/>
  <Solve Iterations="{iterations}">
    <VTK Iterations="{iterations}" what="{VTK_FIELDS}"/>
    <Log Iterations="50"/>
    <Failcheck Iterations="50"/>
  </Solve>
</CLBConfig>
"""


def binary_hash(binary: str) -> str | None:
    try:
        out = subprocess.check_output(["sha256sum", binary], text=True)
    except Exception:
        return None
    return out.split()[0] if out.split() else None


def run_case(args: argparse.Namespace) -> int:
    spec = case_spec(args.geom, args.theta, args.volume_radius, args.int_width)
    root = Path(args.root)
    case_dir = root / args.name
    if case_dir.exists() and args.force:
        subprocess.run(["rm", "-rf", str(case_dir)], check=True)
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "output").mkdir(exist_ok=True)

    xml = render_xml(spec, args.theta, args.iterations, args.mobility, args.int_width)
    (case_dir / "case.xml").write_text(xml, encoding="utf-8")

    metadata: dict[str, Any] = {
        "case": args.name,
        "geometry": spec.geom,
        "target_theta_deg": args.theta,
        "iterations": args.iterations,
        "grid": list(spec.grid),
        "volume_equivalent_radius": args.volume_radius,
        "interface_width": args.int_width,
        "mobility": args.mobility,
        "solid_center": list(spec.solid_center),
        "solid_radius": spec.solid_radius,
        "cylinder_axis": spec.cylinder_axis if spec.geom == "cylinder" else None,
        "liquid_probe": list(spec.liquid_probe),
        "cap_parent_radius": spec.cap_parent_radius,
        "cap_center": list(spec.cap_center),
        "claim_limit": spec.claim_limit,
        "classification_before_audit": "runtime_sanity",
        "binary": args.binary,
        "binary_sha256": binary_hash(args.binary),
    }
    if spec.plane_axis is not None:
        metadata["plane_axis"] = spec.plane_axis
        metadata["plane_offset"] = spec.plane_offset
    (case_dir / "case_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")

    env = os.environ.copy()
    env["PATH"] = "/usr/local/cuda-12.6/bin:/usr/bin:/bin:/usr/local/bin"
    env["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
    env["CUDA_VISIBLE_DEVICES"] = env.get("CUDA_VISIBLE_DEVICES", "1")
    env["OMPI_MCA_plm_rsh_agent"] = "/usr/bin/ssh"

    with (case_dir / "run.log").open("w", encoding="utf-8", errors="replace") as log:
        log.write(
            f"=== cap-static {args.name} geom={args.geom} theta={args.theta} "
            f"grid={spec.grid} iterations={args.iterations} ===\n"
        )
        log.flush()
        completed = subprocess.run(
            ["timeout", str(args.timeout), args.binary, "case.xml"],
            cwd=case_dir,
            stdout=log,
            stderr=subprocess.STDOUT,
            env=env,
        )
        log.write(f"\nRUN_RC={completed.returncode}\n")

    vtis = sorted((case_dir / "output").glob("case_VTK_P00_*.vti"))
    result = {
        "case_dir": str(case_dir),
        "run_rc": completed.returncode,
        "final_vti": str(vtis[-1]) if vtis else None,
        "metadata": metadata,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return completed.returncode if completed.returncode != 124 else 124


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("name")
    parser.add_argument("geom", choices=["wall", "sphere", "cylinder"])
    parser.add_argument("theta", type=float)
    parser.add_argument("iterations", type=int)
    parser.add_argument("--root", default=DEFAULT_ROOT)
    parser.add_argument("--binary", default=DEFAULT_BIN)
    parser.add_argument("--volume-radius", type=float, default=16.0)
    parser.add_argument("--int-width", type=float, default=3.0)
    parser.add_argument("--mobility", type=float, default=0.1)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    return run_case(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
