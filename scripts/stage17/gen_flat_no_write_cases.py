#!/usr/bin/env python3
"""Generate Stage17B B3 flat-wall no-write regression cases.

The case deliberately sets Stage17BWriteMode=2 on analytic flat geometry. The
B3 gate must not apply because controlled writes are restricted to curved
analytic solids (AnalyticSolidType >= 1.5). This is not a contact-angle
validation case.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from gen_cyl_shadow_cases import VTK_FIELDS, param


def cap_sphere_radius(volume_radius: float, theta_deg: float) -> float:
    theta = math.radians(theta_deg)
    denom = (1.0 - math.cos(theta)) ** 2 * (2.0 + math.cos(theta))
    if denom <= 0.0:
        raise ValueError(f"invalid theta: {theta_deg}")
    return volume_radius * (4.0 / denom) ** (1.0 / 3.0)


def case_xml(theta_deg: int, iterations: int, vtk_period: int, log_period: int) -> str:
    volume_radius = 16.0
    parent_radius = cap_sphere_radius(volume_radius, theta_deg)
    theta = math.radians(theta_deg)
    cap_center_x = 48.0
    cap_center_y = -parent_radius * math.cos(theta)
    cap_center_z = 48.0
    initial_center_y = max(2.0, parent_radius * (1.0 - math.cos(theta)) * 0.35)
    params = [
        param("Density_h", 1),
        param("Density_l", 0.005),
        param("Viscosity_h", 0.1),
        param("Viscosity_l", 0.1),
        param("tauUpdate", 1),
        param("sigma", "5e-05"),
        param("M", 0.6),
        param("IntWidth", 3),
        param("Radius", 0),
        param("CenterX", cap_center_x),
        param("CenterY", initial_center_y),
        param("CenterZ", cap_center_z),
        param("CapInit", 1),
        param("CapInitRadius", f"{parent_radius:.16g}"),
        param("CapInitTheta", f"{theta:.16g}"),
        param("CapInitCenterX", f"{cap_center_x:.16g}"),
        param("CapInitCenterY", f"{cap_center_y:.16g}"),
        param("CapInitCenterZ", f"{cap_center_z:.16g}"),
        param("BubbleType", 1.0),
        param("VelocityX", 0),
        param("VelocityY", 0),
        param("VelocityZ", 0),
        param("GravitationX", 0),
        param("GravitationY", 0),
        param("GravitationZ", 0),
        param("radAngle", "90d"),
        param("radAngle", "90d", "OuterDomain"),
        param("radAngle", f"{theta_deg}d", "FlatLowerY"),
        param("AnalyticWetting", 1),
        param("AnalyticSolidType", 1),
        param("AnalyticSolidAxis", 1),
        param("AnalyticSolidPlaneOffset", 0.0),
        param("WettingBCMode", 0),
        param("WallCompactStencilMode", 0),
        param("WallCompactStencilWriteAllowedFlag", 0),
        param("Stage17BDiffuseSolidMode", 1),
        param("Stage17BWriteMode", 2),
        param("Stage17BShadowThetaDeg", theta_deg),
        param("Stage17BPsiEps", 1.25),
        param("Stage17BWriteBand", 1.8),
        param("Stage17BGradPsiMin", "1e-4"),
        param("ReplayDiagnosticsMode", 0),
        param("MomentumClosureDiagnosticsMode", 0),
        param("DynamicCLMode", 0),
        param("ForceFixedTol", 0),
        param("ForceFixedMaxIter", 2),
        param("minGradient", "1e-8"),
    ]
    return f"""<?xml version="1.0"?>
<CLBConfig output="output/" permissive="true">
  <Geometry nx="96" ny="80" nz="96">
    <MRT><Box/></MRT>
    <Wall mask="ALL" name="OuterDomain">
      <Box nx="1"/><Box dx="-1"/><Box dy="-1"/><Box nz="1"/><Box dz="-1"/>
    </Wall>
    <Wall mask="ALL" name="FlatLowerY"><Box dx="1" nx="94" ny="1" dz="1" nz="94"/></Wall>
  </Geometry>
  <Model>
{chr(10).join(params)}
  </Model>
  <VTK what="{VTK_FIELDS}"/>
  <Log Iterations="{log_period}"/><Failcheck Iterations="{log_period}"/>
  <Solve Iterations="{iterations}"><VTK Iterations="{vtk_period}" what="{VTK_FIELDS}"/><Log Iterations="{log_period}"/><Failcheck Iterations="{log_period}"/></Solve>
</CLBConfig>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("cases/diagnostics/stage17B_B3_flat_no_write_20260624"))
    parser.add_argument("--theta", type=int, default=90)
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--vtk-period", type=int, default=1000)
    parser.add_argument("--log-period", type=int, default=200)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root
    name = f"flat_theta{args.theta:03d}_nowrite"
    case_dir = root / name
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "case.xml").write_text(
        case_xml(args.theta, args.iterations, args.vtk_period, args.log_period),
        encoding="utf-8",
    )
    manifest = {
        "purpose": "Stage17B B3 flat-wall no-write regression",
        "case": name,
        "theta_deg": args.theta,
        "iterations": args.iterations,
        "vtk_period": args.vtk_period,
        "log_period": args.log_period,
        "stage17b_diffuse_solid_mode": 1,
        "stage17b_write_mode": 2,
        "analytic_solid_type": 1,
        "expected": "PsiWriteAppliedFlag=0 and WettingPathId=170 cells=0",
        "claim_limit": "flat-wall no-write regression only; not contact-angle validation",
    }
    root.mkdir(parents=True, exist_ok=True)
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(case_dir / "case.xml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
