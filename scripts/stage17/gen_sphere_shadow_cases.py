#!/usr/bin/env python3
"""Generate Stage17B sphere diffuse-solid shadow-only cases.

These cases are not contact-angle validation cases. They only exercise the
Stage17B Psi*/NearWall* diagnostic fields on an analytic solid sphere while the
solver continues to use the legacy wall ghost path.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Iterable


VTK_FIELDS = ",".join(
    [
        "PhaseField",
        "Rho",
        "U",
        "P",
        "BOUNDARY",
        "IsItBoundary",
        "WallGhost",
        "WallGhostRaw",
        "WallGhostClamped",
        "WallGhostClampHit",
        "WettingPathId",
        "WallH",
        "AnalyticFlag",
        "LocalRadAngle",
        "PsiSolid",
        "PsiGradMag",
        "PsiNormal",
        "PsiWallGhostRaw",
        "PsiWallGhost",
        "PsiWallGhostClampHit",
        "PsiThetaImplied",
        "PsiJaggedness",
        "PsiWriteAllowedFlag",
        "PsiNormalAmbiguityFlag",
        "PsiWriteAppliedFlag",
        "PsiWriteRejectedReason",
        "NearWallForceMag",
        "NearWallGradPhiMag",
        "NearWallForceOverRhoShadow",
    ]
)


def param(name: str, value: object, zone: str | None = None) -> str:
    zone_attr = "" if zone is None else f' zone="{zone}"'
    return f'    <Param name="{name}" value="{value}"{zone_attr}/>'


def overlap_volume(radius_a: float, radius_b: float, distance: float) -> float:
    if distance >= radius_a + radius_b:
        return 0.0
    if distance <= abs(radius_a - radius_b):
        return 4.0 * math.pi * min(radius_a, radius_b) ** 3 / 3.0
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


def sphere_cap_parent(solid_r: float, vol_r: float, theta_deg: float) -> tuple[float, float]:
    """Return parent liquid-sphere radius and solid-parent center distance.

    The initializer stores liquid as the part of the parent sphere that lies
    outside the solid sphere. The solved volume equals a free sphere of radius
    vol_r, and the sphere-sphere intersection angle follows theta_deg.
    """

    target = 4.0 * math.pi * vol_r**3 / 3.0
    theta = math.radians(theta_deg)

    def outside(parent_r: float) -> float:
        distance = math.sqrt(
            solid_r * solid_r
            + parent_r * parent_r
            - 2.0 * solid_r * parent_r * math.cos(theta)
        )
        return 4.0 * math.pi * parent_r**3 / 3.0 - overlap_volume(
            solid_r, parent_r, distance
        )

    lo = 1.0e-9
    hi = max(2.0 * vol_r, 2.0 * solid_r)
    while outside(hi) < target:
        hi *= 2.0
    for _ in range(180):
        mid = 0.5 * (lo + hi)
        if outside(mid) < target:
            lo = mid
        else:
            hi = mid
    parent = 0.5 * (lo + hi)
    center_distance = math.sqrt(
        solid_r * solid_r
        + parent * parent
        - 2.0 * solid_r * parent * math.cos(theta)
    )
    return parent, center_distance


def case_xml(
    theta_deg: int,
    iterations: int,
    vtk_period: int,
    log_period: int,
    write_mode: int,
) -> str:
    solid_center = (40.0, 40.0, 48.0)
    solid_radius = 20.0
    volume_radius = 16.0
    parent_radius, center_distance = sphere_cap_parent(solid_radius, volume_radius, theta_deg)
    cap_center = (solid_center[0], solid_center[1], solid_center[2] + center_distance)
    probe = (solid_center[0], solid_center[1], solid_center[2] + solid_radius + 4.0)

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
        param("CenterX", probe[0]),
        param("CenterY", probe[1]),
        param("CenterZ", probe[2]),
        param("SphereCapInit", 1),
        param("SphereCapInitParentRadius", parent_radius),
        param("SphereCapInitCenterX", cap_center[0]),
        param("SphereCapInitCenterY", cap_center[1]),
        param("SphereCapInitCenterZ", cap_center[2]),
        param("SphereCapInitSolidCenterX", solid_center[0]),
        param("SphereCapInitSolidCenterY", solid_center[1]),
        param("SphereCapInitSolidCenterZ", solid_center[2]),
        param("SphereCapInitSolidRadius", solid_radius),
        param("BubbleType", 1.0),
        param("VelocityX", 0),
        param("VelocityY", 0),
        param("VelocityZ", 0),
        param("GravitationX", 0),
        param("GravitationY", 0),
        param("GravitationZ", 0),
        param("radAngle", "90d"),
        param("radAngle", "90d", "OuterDomain"),
        param("radAngle", "90d", "AnalyticSphere"),
        param("AnalyticWetting", 1),
        param("AnalyticSolidType", 3),
        param("AnalyticSolidCenterX", solid_center[0]),
        param("AnalyticSolidCenterY", solid_center[1]),
        param("AnalyticSolidCenterZ", solid_center[2]),
        param("AnalyticSolidRadius", solid_radius),
        param("WettingBCMode", 0),
        param("WallCompactStencilMode", 0),
        param("WallCompactStencilWriteAllowedFlag", 0),
        param("Stage17BDiffuseSolidMode", 1),
        param("Stage17BWriteMode", write_mode),
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
    param_text = "\n".join(params)
    return f"""<?xml version="1.0"?>
<CLBConfig output="output/" permissive="true">
  <Geometry nx="80" ny="80" nz="120">
    <MRT><Box/></MRT>
    <Wall mask="ALL" name="OuterDomain"><Box nx="1"/><Box dx="-1"/><Box ny="1"/><Box dy="-1"/><Box nz="1"/><Box dz="-1"/></Wall>
    <Wall mask="ALL" name="AnalyticSphere"><Sphere dx="20" nx="40" dy="20" ny="40" dz="28" nz="40"/></Wall>
  </Geometry>
  <Model>
{param_text}
  </Model>
  <VTK what="{VTK_FIELDS}"/>
  <Log Iterations="{log_period}"/><Failcheck Iterations="{log_period}"/>
  <Solve Iterations="{iterations}"><VTK Iterations="{vtk_period}" what="{VTK_FIELDS}"/><Log Iterations="{log_period}"/><Failcheck Iterations="{log_period}"/></Solve>
</CLBConfig>
"""


def write_cases(
    root: Path,
    thetas: Iterable[int],
    iterations: int,
    vtk_period: int,
    log_period: int,
    write_mode: int,
    case_suffix: str,
) -> list[dict[str, object]]:
    root.mkdir(parents=True, exist_ok=True)
    cases: list[dict[str, object]] = []
    for theta in thetas:
        name = f"sphere_theta{theta:03d}_{case_suffix}"
        case_dir = root / name
        case_dir.mkdir(parents=True, exist_ok=True)
        xml = case_xml(theta, iterations, vtk_period, log_period, write_mode)
        (case_dir / "case.xml").write_text(xml, encoding="utf-8")
        cases.append(
            {
                "case": name,
                "theta_deg": theta,
                "case_xml": str(case_dir / "case.xml"),
                "stage17b_diffuse_solid_mode": 1,
                "stage17b_write_mode": write_mode,
                "legacy_rad_angle_deg": 90,
                "stage17b_shadow_theta_deg": theta,
                "wall_compact_stencil_mode": 0,
                "claim_limit": (
                    "controlled WallGhost write audit; not contact-angle validation"
                    if write_mode >= 2
                    else "shadow-only geometry/near-wall diagnostics; not contact-angle validation"
                ),
            }
        )
    manifest = {
        "purpose": (
            "Stage17B B3 sphere controlled WallGhost write audit"
            if write_mode >= 2
            else "Stage17B B2 sphere diffuse-solid shadow-only gate"
        ),
        "iterations": iterations,
        "vtk_period": vtk_period,
        "log_period": log_period,
        "stage17b_write_mode": write_mode,
        "case_suffix": case_suffix,
        "vtk_fields": VTK_FIELDS,
        "cases": cases,
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return cases


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("cases/diagnostics/stage17B_sphere_shadow_20260624"),
    )
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--vtk-period", type=int, default=500)
    parser.add_argument("--log-period", type=int, default=100)
    parser.add_argument("--thetas", type=int, nargs="+", default=[90, 60, 120])
    parser.add_argument("--write-mode", type=int, default=0)
    parser.add_argument("--case-suffix", default="shadow")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cases = write_cases(
        args.root,
        args.thetas,
        args.iterations,
        args.vtk_period,
        args.log_period,
        args.write_mode,
        args.case_suffix,
    )
    for case in cases:
        print(case["case_xml"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
