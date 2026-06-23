#!/usr/bin/env python3
"""Stage12 unified validation runner: decoupled-relaxation + long-equilibrium.

This replaces the circular-verification 200-step cap smoke (where init theta ==
BC theta, so the reported circle_intersection angle just re-reads the
initialization). Two modes, same geometry engine:

  * equilibrium: init_theta == bc_theta, but run LONG (>=10k steps) with
    periodic VTK + globals CSV. The contact angle is then read from the
    local phase gradient (theta_grad_deg), which reflects the actual BC
    equilibrium response, not the initialization shape.

  * decouple:   init_theta != bc_theta. The cap initializer builds a droplet
    at init_theta; the BC radAngle is set to bc_theta. If the BC is working,
    the interface MUST relax from init_theta toward bc_theta (plus the known
    model-intrinsic O(W/R) cot(theta) offset). A flat angle == init_theta
    would prove the BC is NOT driving the contact line.

Geometry: wall / sphere / cylinder, axis-aware (cylinder disk in x-y, axis=z),
matching the stage12 geometry-contact audit fix.

Key difference vs stage12_cap_static_run.py: init_theta and bc_theta are
INDEPENDENT arguments. CapInitTheta (metadata only in C code) records the
init geometry angle; radAngle (the actual wetting law) records the BC angle.
The C solver never reads CapInitTheta -- the shape is set by CapInitRadius /
*ParentRadius / *Center, which are computed here from init_theta.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_BIN = (
    "/mnt/win_sda2/RUNS/runs/stage9/src/"
    "TCLB_stage9_analytic_wetting_20260614/"
    "CLB/d3q27_pf_velocity_q27_geometric/main"
)
DEFAULT_ROOT = "/mnt/usb1t/RUNS/runs/stage12_validation_20260615"
VTK_FIELDS = ",".join([
    "PhaseField",
    "Rho",
    "U",
    "P",
    "BOUNDARY",
    "IsItBoundary",
    "WallGhost",
    "WallH",
    "AnalyticWallNormal",
    "AnalyticFlag",
    "WallCSQMode",
    "WallCSQValid",
    "WallCSQThetaDeg",
    "WallCSQNormalX",
    "WallCSQNormalY",
    "WallCSQNormalZ",
    "WallCSQDs",
    "WallCSQDf",
    "WallCSQQf",
    "WallCSQQsRaw",
    "WallCSQQsBounded",
    "WallCSQQw",
    "WallCSQResidual",
    "WallCSQDiscriminant",
    "WallCSQRootChoice",
    "WallCSQStencilCase",
    "WallCSQStencilL",
    "WallCSQFallbackReason",
    "WallCSQBoundedDelta",
    "WallCSQAppliedWeight",
    "WallCSQWriteAllowedFlag",
    "WallCSQCandidateCount",
    "WallCSQFluidVertexCount",
    "WallCSQTriangleInside",
    "WallCSQPlaneId",
    "WallCSQBaryMin",
    "WallCSQBaryMax",
    "WallCSQMethodComplete",
    "WallCSQVertexMaskBits",
    "WallCSQVertexPhaseCleanBits",
    "WallCSQVertexQMin",
    "WallCSQVertexQMax",
    "WallCSQRejectedSolidVertexCount",
    "WallCSQRejectedSentinelCount",
])


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
    claim_limit: str
    plane_axis: int | None = None
    plane_offset: float | None = None


# ---- cap geometry: parent sphere radius from a target cap contact angle ----
# These formulas are the SAME as stage12_cap_static_run.py so the init shape is
# identical when init_theta == bc_theta (backward compatible). Only the driver
# angle changes: we feed init_theta here, the caller feeds bc_theta to radAngle.

def cap_sphere_radius(volume_radius: float, theta_deg: float) -> float:
    """Flat-wall cap: parent-sphere radius giving volume 4/3 pi volume_radius^3."""
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
    """Sphere/cylinder cap: solve parent-sphere radius + center distance so the
    cap outside the solid sphere has the requested volume at cap angle theta."""
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


def case_spec(geom: str, init_theta_deg: float, volume_radius: float) -> CaseSpec:
    """Build geometry from init_theta (the INITIALIZATION angle only).
    bc_theta is applied separately in render_xml via radAngle."""
    theta_rad = math.radians(init_theta_deg)
    if geom == "wall":
        parent_radius = cap_sphere_radius(volume_radius, init_theta_deg)
        cap_center = (48.0, -parent_radius * math.cos(theta_rad), 48.0)
        init_params = "\n".join([
            param("Radius", 0),
            param("CenterX", cap_center[0]),
            param("CenterY", max(2.0, parent_radius * (1.0 - math.cos(theta_rad)) * 0.35)),
            param("CenterZ", cap_center[2]),
            param("CapInit", 1),
            param("CapInitRadius", f"{parent_radius:.16g}"),
            param("CapInitTheta", f"{theta_rad:.16g}"),  # metadata only; C code ignores it
            param("CapInitCenterX", f"{cap_center[0]:.16g}"),
            param("CapInitCenterY", f"{cap_center[1]:.16g}"),
            param("CapInitCenterZ", f"{cap_center[2]:.16g}"),
        ])
        return CaseSpec(
            geom=geom, grid=(96, 80, 96),
            geometry_block=(
                '    <Wall mask="ALL" name="OuterDomain">\n'
                '      <Box nx="1"/><Box dx="-1"/><Box dy="-1"/><Box nz="1"/><Box dz="-1"/>\n'
                '    </Wall>\n'
                '    <Wall mask="ALL" name="FlatLowerY"><Box ny="1"/></Wall>'
            ),
            solid_params="\n".join([
                param("AnalyticSolidType", 1),
                param("AnalyticSolidAxis", 1),
                param("AnalyticSolidPlaneOffset", 0.0),
            ]),
            init_params=init_params,
            solid_center=(48.0, 0.0, 48.0), solid_radius=0.0, cylinder_axis=0,
            liquid_probe=(48.0, 2.0, 48.0),
            claim_limit="validation_decouple_or_equilibrium",
            plane_axis=1, plane_offset=0.0,
        )

    if geom == "sphere":
        solid_center = (40.0, 40.0, 48.0)
        solid_radius = 20.0
        parent_radius, center_distance = sphere_cap_parent_radius(solid_radius, volume_radius, init_theta_deg)
        cap_center = (solid_center[0], solid_center[1], solid_center[2] + center_distance)
        liquid_probe = (solid_center[0], solid_center[1], solid_center[2] + solid_radius + 4.0)
        init_params = "\n".join([
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
        ])
        return CaseSpec(
            geom=geom, grid=(80, 80, 120),
            geometry_block=(
                '    <Wall mask="ALL" name="OuterDomain">\n'
                '      <Box nx="1"/><Box dx="-1"/><Box ny="1"/><Box dy="-1"/><Box nz="1"/><Box dz="-1"/>\n'
                '    </Wall>\n'
                '    <Wall mask="ALL" name="AnalyticSphere">\n'
                '      <Sphere dx="20" nx="40" dy="20" ny="40" dz="28" nz="40"/>\n'
                '    </Wall>'
            ),
            solid_params="\n".join([
                param("AnalyticSolidType", 3),
                param("AnalyticSolidCenterX", solid_center[0]),
                param("AnalyticSolidCenterY", solid_center[1]),
                param("AnalyticSolidCenterZ", solid_center[2]),
                param("AnalyticSolidRadius", solid_radius),
            ]),
            init_params=init_params,
            solid_center=solid_center, solid_radius=solid_radius, cylinder_axis=0,
            liquid_probe=liquid_probe,
            claim_limit="validation_decouple_or_equilibrium",
        )

    if geom == "cylinder":
        solid_center = (48.0, 48.0, 48.0)
        solid_radius = 20.0
        parent_radius, center_distance = sphere_cap_parent_radius(solid_radius, volume_radius, init_theta_deg)
        cap_center = (solid_center[0], solid_center[1] + center_distance, solid_center[2])
        liquid_probe = (solid_center[0], solid_center[1] + solid_radius + 4.0, solid_center[2])
        init_params = "\n".join([
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
        ])
        return CaseSpec(
            geom=geom, grid=(96, 96, 96),
            geometry_block=(
                '    <Wall mask="ALL" name="OuterDomain">\n'
                '      <Box nx="1"/><Box dx="-1"/><Box ny="1"/><Box dy="-1"/><Box nz="1"/><Box dz="-1"/>\n'
                '    </Wall>\n'
                '    <Wall mask="ALL" name="AnalyticCylinder">\n'
                '      <Cylinder dx="28" nx="40" dy="28" ny="40" dz="0" nz="96"/>\n'
                '    </Wall>'
            ),
            solid_params="\n".join([
                param("AnalyticSolidType", 2),
                param("AnalyticSolidAxis", 2),
                param("AnalyticSolidCenterX", solid_center[0]),
                param("AnalyticSolidCenterY", solid_center[1]),
                param("AnalyticSolidCenterZ", solid_center[2]),
                param("AnalyticSolidRadius", solid_radius),
            ]),
            init_params=init_params,
            solid_center=solid_center, solid_radius=solid_radius, cylinder_axis=2,
            liquid_probe=liquid_probe,
            claim_limit="validation_cylinder_cap_uses_local_convex_approx",
        )

    raise ValueError(f"unknown geometry: {geom}")


def render_xml(
    spec: CaseSpec,
    init_theta_deg: float,
    bc_theta_deg: float,
    iterations: int,
    mobility: float,
    int_width: float,
    vtk_period: int,
    log_period: int,
) -> str:
    """Render case.xml. bc_theta drives radAngle (the wetting law);
    init_theta was already baked into spec.init_params (the cap shape)."""
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
    <Param name="WallCompactStencilMode" value="1"/>
    <Param name="WallCompactStencilNormalMode" value="1"/>
    <Param name="WallCompactStencilMaxL" value="3"/>
    <Param name="WallCompactStencilWriteAllowedFlag" value="0"/>
    <Param name="radAngle" value="{bc_theta_deg:.16g}d" zone="{target_zone}"/>
    <Param name="minGradient" value="1e-08"/>
  </Model>
  <VTK what="{VTK_FIELDS}"/>
  <Log Iterations="{log_period}"/>
  <Failcheck Iterations="{log_period}"/>
  <Solve Iterations="{iterations}">
    <VTK Iterations="{vtk_period}" what="{VTK_FIELDS}"/>
    <Log Iterations="{log_period}"/>
    <Failcheck Iterations="{log_period}"/>
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
    spec = case_spec(args.geom, args.init_theta, args.volume_radius)
    root = Path(args.root)
    case_dir = root / args.name
    if case_dir.exists() and args.force:
        subprocess.run(["rm", "-rf", str(case_dir)], check=True)
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "output").mkdir(exist_ok=True)

    xml = render_xml(
        spec, args.init_theta, args.bc_theta, args.iterations,
        args.mobility, args.int_width, args.vtk_period, args.log_period,
    )
    (case_dir / "case.xml").write_text(xml, encoding="utf-8")

    metadata: dict[str, Any] = {
        "case": args.name,
        "geometry": spec.geom,
        "init_theta_deg": args.init_theta,          # cap initializer angle (shape driver)
        "bc_theta_deg": args.bc_theta,              # radAngle = wetting law angle
        "decoupled": abs(args.init_theta - args.bc_theta) > 1e-9,
        "iterations": args.iterations,
        "vtk_period": args.vtk_period,
        "log_period": args.log_period,
        "grid": list(spec.grid),
        "volume_equivalent_radius": args.volume_radius,
        "interface_width": args.int_width,
        "mobility": args.mobility,
        "solid_center": list(spec.solid_center),
        "solid_radius": spec.solid_radius,
        "cylinder_axis": spec.cylinder_axis if spec.geom == "cylinder" else None,
        "liquid_probe": list(spec.liquid_probe),
        "claim_limit": spec.claim_limit,
        "classification_before_audit": "validation_candidate",
        "binary": args.binary,
        "binary_sha256": binary_hash(args.binary),
        "note": (
            "init_theta drives cap shape (CapInitRadius/ParentRadius/Center); "
            "bc_theta drives radAngle (wetting law). When decoupled==true, a "
            "correct BC must relax the interface from init_theta toward bc_theta."
        ),
    }
    if spec.plane_axis is not None:
        metadata["plane_axis"] = spec.plane_axis
        metadata["plane_offset"] = spec.plane_offset
    (case_dir / "case_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")

    env = os.environ.copy()
    env["PATH"] = "/usr/local/cuda-12.6/bin:/usr/bin:/bin:/usr/local/bin"
    env["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
    env["CUDA_VISIBLE_DEVICES"] = str(args.gpu)
    env["OMPI_MCA_plm_rsh_agent"] = "/usr/bin/ssh"
    env["LD_LIBRARY_PATH"] = "/usr/local/cuda-12.6/lib64:" + env.get("LD_LIBRARY_PATH", "")

    with (case_dir / "run.log").open("w", encoding="utf-8", errors="replace") as log:
        log.write(
            f"=== validation {args.name} geom={args.geom} "
            f"init_theta={args.init_theta} bc_theta={args.bc_theta} "
            f"grid={spec.grid} iterations={args.iterations} gpu={args.gpu} ===\n"
        )
        log.flush()
        completed = subprocess.run(
            ["timeout", str(args.timeout), args.binary, "case.xml"],
            cwd=case_dir, stdout=log, stderr=subprocess.STDOUT, env=env,
        )
        log.write(f"\nRUN_RC={completed.returncode}\n")

    vtis = sorted((case_dir / "output").glob("case_VTK_P00_*.vti"))
    result = {
        "case_dir": str(case_dir),
        "run_rc": completed.returncode,
        "final_vti": str(vtis[-1]) if vtis else None,
        "n_vti": len(vtis),
        "metadata": metadata,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return completed.returncode if completed.returncode != 124 else 124


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("name", help="case subdirectory name")
    p.add_argument("geom", choices=["wall", "sphere", "cylinder"])
    p.add_argument("--init-theta", type=float, required=True, help="cap initializer angle (deg), drives shape")
    p.add_argument("--bc-theta", type=float, required=True, help="BC radAngle (deg), drives wetting law")
    p.add_argument("--iterations", type=int, default=30000)
    p.add_argument("--vtk-period", type=int, default=2000, help="VTK dump period inside <Solve>")
    p.add_argument("--log-period", type=int, default=500, help="globals Log period")
    p.add_argument("--root", default=DEFAULT_ROOT)
    p.add_argument("--binary", default=DEFAULT_BIN)
    p.add_argument("--gpu", type=int, default=1, help="CUDA_VISIBLE_DEVICES")
    p.add_argument("--volume-radius", type=float, default=16.0)
    p.add_argument("--int-width", type=float, default=3.0)
    p.add_argument("--mobility", type=float, default=0.1)
    p.add_argument("--timeout", type=int, default=7200)
    p.add_argument("--force", action="store_true")
    return p.parse_args()


def main() -> int:
    return run_case(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
