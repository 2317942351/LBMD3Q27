#!/usr/bin/env python3
"""Legacy cylinder compact-write case generator.

This script is intentionally blocked by default. Direct compact-stencil writes
on curved analytic solids are a known negative route: cylinder cases produced
NaNs or large angle errors, and the solver now gates compact writes to flat
walls only. Keep this file only to reproduce the historical negative control.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import os
import sys
from pathlib import Path


def load_stage13_runner():
    spec = importlib.util.spec_from_file_location("r", "/home/yuan/stage13_flat_wall_diagnostic_run.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load /home/yuan/stage13_flat_wall_diagnostic_run.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["r"] = module
    spec.loader.exec_module(module)
    return module


def param(name: str, value: object) -> str:
    return f'<Param name="{name}" value="{value}"/>'


def sphere_cap_parent(solid_r: float, vol_r: float, theta_deg: float) -> tuple[float, float]:
    theta = math.radians(theta_deg)

    def outside(radius: float) -> float:
        return (
            math.pi * radius**3 * (2 + math.cos(theta)) * (1 - math.cos(theta)) ** 2 / 3
            - 2 * math.pi * solid_r**2 * radius * (1 - math.cos(theta))
            + 2 * math.pi * solid_r**3 * (math.cos(theta) - math.cos(3 * theta)) / 3
        )

    target = 4 * math.pi * vol_r**3 / 3
    lo, hi = 0.1, 400.0
    while outside(hi) < target:
        hi *= 2
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if outside(mid) < target:
            lo = mid
        else:
            hi = mid
    radius = 0.5 * (lo + hi)
    center_delta = radius * (1 - math.cos(theta))
    return radius, center_delta


def cyl_xml(vtk_fields: str, theta_deg: float, mobility: float = 0.6, iterations: int = 12000) -> str:
    solid_center = (48.0, 48.0, 48.0)
    solid_radius = 20.0
    volume_radius = 16.0
    parent_radius, center_delta = sphere_cap_parent(solid_radius, volume_radius, theta_deg)
    cap_center = (solid_center[0], solid_center[1] + center_delta, solid_center[2])
    probe = (solid_center[0], solid_center[1] + solid_radius + 4.0, solid_center[2])
    init = "\n".join(
        [
            param("Radius", 0),
            param("CenterX", probe[0]),
            param("CenterY", probe[1]),
            param("CenterZ", probe[2]),
            param("CylinderCapInit", 1),
            param("CylinderCapInitParentRadius", parent_radius),
            param("CylinderCapInitCenterX", cap_center[0]),
            param("CylinderCapInitCenterY", cap_center[1]),
            param("CylinderCapInitCenterZ", cap_center[2]),
            param("CylinderCapInitSolidCenterX", solid_center[0]),
            param("CylinderCapInitSolidCenterY", solid_center[1]),
            param("CylinderCapInitSolidCenterZ", solid_center[2]),
            param("CylinderCapInitSolidRadius", solid_radius),
            param("CylinderCapInitSolidAxis", 2),
        ]
    )
    return f"""<?xml version="1.0"?>
<CLBConfig output="output/" permissive="true">
  <Geometry nx="96" ny="96" nz="96">
    <MRT><Box/></MRT>
    <Wall mask="ALL" name="OuterDomain"><Box nx="1"/><Box dx="-1"/><Box ny="1"/><Box dy="-1"/><Box nz="1"/><Box dz="-1"/></Wall>
    <Wall mask="ALL" name="AnalyticCylinder"><Cylinder dx="28" nx="40" dy="28" ny="40" dz="0" nz="96"/></Wall>
  </Geometry>
  <Model>
    <Param name="Density_h" value="1"/><Param name="Density_l" value="0.001"/>
    <Param name="Viscosity_h" value="0.1"/><Param name="Viscosity_l" value="0.1"/>
    <Param name="tauUpdate" value="1"/><Param name="sigma" value="5e-05"/>
    <Param name="M" value="{mobility}"/><Param name="IntWidth" value="3"/>
{init}
    <Param name="BubbleType" value="1.0"/><Param name="VelocityX" value="0"/><Param name="VelocityY" value="0"/><Param name="VelocityZ" value="0"/>
    <Param name="GravitationX" value="0"/><Param name="GravitationY" value="0"/><Param name="GravitationZ" value="0"/>
    <Param name="radAngle" value="90d"/><Param name="radAngle" value="90d" zone="OuterDomain"/>
    <Param name="AnalyticSolidType" value="2"/><Param name="AnalyticSolidAxis" value="2"/>
    <Param name="AnalyticSolidCenterX" value="{solid_center[0]}"/><Param name="AnalyticSolidCenterY" value="{solid_center[1]}"/><Param name="AnalyticSolidCenterZ" value="{solid_center[2]}"/><Param name="AnalyticSolidRadius" value="{solid_radius}"/>
    <Param name="AnalyticWetting" value="1"/><Param name="WettingBCMode" value="0"/>
    <Param name="WallCompactStencilMode" value="2"/><Param name="WallCompactStencilNormalMode" value="1"/><Param name="WallCompactStencilMaxL" value="3"/>
    <Param name="WallCompactStencilBoundEps" value="0"/><Param name="WallCompactStencilMaxBoundedDelta" value="1e-8"/><Param name="WallCompactStencilAppliedResidualTol" value="1e-8"/><Param name="WallCompactStencilWriteAllowedFlag" value="1"/>
    <Param name="ForceFixedTol" value="0"/><Param name="ForceFixedMaxIter" value="2"/>
    <Param name="WallGradMode" value="0"/><Param name="WallGradContactSign" value="1"/><Param name="WallMuMode" value="0"/>
    <Param name="DynamicCLMode" value="2"/><Param name="DynamicCLCosSign" value="-1"/><Param name="DynamicCLForceSign" value="-1"/><Param name="DynamicCLCoeff" value="0"/>
    <Param name="radAngle" value="{theta_deg}d" zone="AnalyticCylinder"/>
    <Param name="minGradient" value="1e-8"/>
  </Model>
  <VTK what="{vtk_fields}"/>
  <Log Iterations="1000"/><Failcheck Iterations="1000"/>
  <Solve Iterations="{iterations}"><VTK Iterations="2000" what="{vtk_fields}"/><Log Iterations="1000"/><Failcheck Iterations="1000"/></Solve>
</CLBConfig>"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument(
        "--legacy-unsafe-curved-compact-write",
        action="store_true",
        help="Generate the historical negative-control cases that request compact writes on a cylinder.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.legacy_unsafe_curved_compact_write:
        raise SystemExit(
            "Refusing to generate curved compact-write cases. This path is deprecated and unsafe. "
            "Use Stage17B diffuse-solid / analytic-SDF shadow cases instead, or pass "
            "--legacy-unsafe-curved-compact-write only to reproduce the historical negative control."
        )
    runner = load_stage13_runner()
    vtk_fields = runner.VTK_FIELDS
    for theta in (60, 90, 120):
        case_dir = args.root / f"cyl_t{theta}"
        os.makedirs(case_dir, exist_ok=True)
        (case_dir / "case.xml").write_text(cyl_xml(vtk_fields, theta), encoding="utf-8")
        print("wrote", case_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
