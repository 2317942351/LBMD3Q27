#!/usr/bin/env python3
"""Generate Stage8f z48 sphere normal-limiter root-cause cases."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


STATUS = "runtime_sanity"
CASE_DIR = Path("cases") / "diagnostics" / "pre2025_sphere_stage8f_shadow_20260613"
REMOTE_ROOT = "/mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_stage8f_shadow_20260613"
BINARY = (
    "/home/yuan/src/TCLB_stage8f_normal_limiter_root_cause_diag_20260613/"
    "CLB/d3q27_pf_velocity_q27_geometric/main"
)

STAGE8F_VTK = (
    "PhaseField,U,P,Rho,BOUNDARY,Normal,IsItBoundary,GradPhi,ActualNormal,"
    "WallBCPath,SpecialBoundaryPoint,"
    "WallStage8GradMode,WallStage8ActiveWeight,WallStage8NormalGradRaw,"
    "WallStage8NormalGradTarget,WallStage8ContactResidual,"
    "WallStage8TangentGradMag,WallStage8TargetCos,"
    "WallStage8GradWriteDeltaMag,WallStage8LimiterReason,"
    "WallStage8LocalWallAngle,WallStage8LocalWallNormal,"
    "WallStage8FluidWallAngle,WallStage8FluidWallNormal,"
    "WallStage8FluidWallDataCount,WallStage8GradCandidate,"
    "WallStage8GradCandidateUse,WallStage8NormalAgreement,"
    "WallStage8UsedGeomNormal,WallStage8TanCoeffLocal,"
    "WallStage8ThetaLocal,WallStage8PhaseC,WallStage8GradMagRaw,"
    "WallStage8TangentGradRaw,WallStage8TargetNormalGrad,"
    "WallStage8NormalDeltaRaw,WallStage8NormalDeltaLimited,"
    "WallStage8VectorDeltaRawMag,WallStage8VectorDeltaLimitedMag,"
    "WallStage8NormalLimiterHit,WallStage8VectorLimiterHit,"
    "WallStage8LimiterRatio,WallStage8RegionTag,"
    "WallStage8SphereRadialDot,WallStage8ContactBandTag,"
    "WallStage8eDnRaw,WallStage8eDnTry,WallStage8eDnLimited,"
    "WallStage8eAbsCap,WallStage8eRatioCap,WallStage8eEffectiveCap,"
    "WallStage8eCapSource,WallStage8eCapDemandRatio,"
    "WallStage8eNormalRawAbs,WallStage8eTargetNormalAbs,"
    "WallStage8eTargetMinusRawAbs,WallStage8eSmoothWeightC,"
    "WallStage8eSmoothWeightG,WallStage8eSmoothWeightT,"
    "WallStage8eSmoothWeightTotal,WallStage8eTanCoeffTimesTangent,"
    "WallStage8eLimiterClass,WallStage8eWallProfileConflict"
)


@dataclass(frozen=True)
class SphereInit:
    case_id: str
    init_kind: str
    radius_xml: str
    sphere_cap_xml: str
    meta: dict[str, float | str]


def overlap_volume(a: float, b: float, d: float) -> float:
    if d >= a + b:
        return 0.0
    if d <= abs(a - b):
        return 4.0 * math.pi * min(a, b) ** 3 / 3.0
    return math.pi * (a + b - d) ** 2 * (d * d + 2.0 * d * (a + b) - 3.0 * (a - b) ** 2) / (12.0 * d)


def sphere_cap_parent_radius(solid_radius: float, volume_radius: float, theta_deg: float) -> tuple[float, float]:
    target = 4.0 * math.pi * volume_radius ** 3 / 3.0
    theta = math.radians(theta_deg)

    def outside_volume(parent_radius: float) -> float:
        d = math.sqrt(
            solid_radius * solid_radius
            + parent_radius * parent_radius
            - 2.0 * solid_radius * parent_radius * math.cos(theta)
        )
        return 4.0 * math.pi * parent_radius ** 3 / 3.0 - overlap_volume(solid_radius, parent_radius, d)

    lo = 1.0e-9
    hi = max(2.0 * volume_radius, 2.0 * solid_radius)
    while outside_volume(hi) < target:
        hi *= 2.0
    for _ in range(200):
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-dir", type=Path, default=CASE_DIR)
    parser.add_argument("--remote-root", default=REMOTE_ROOT)
    parser.add_argument("--binary", default=BINARY)
    parser.add_argument("--case-set", choices=["shadow_initializers", "free_sphere_only", "cap_on_sphere_only"], default="shadow_initializers")
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--vtk-interval", type=int, default=100)
    parser.add_argument("--log-interval", type=int, default=50)
    parser.add_argument("--failcheck-interval", type=int, default=50)
    parser.add_argument("--mobility", type=float, default=0.1)
    parser.add_argument("--int-width", type=float, default=6.0)
    parser.add_argument("--stage8-max-grad-delta", type=float, default=0.25)
    parser.add_argument("--stage8-max-normal-delta", type=float, default=0.05)
    parser.add_argument("--stage8-max-normal-delta-ratio", type=float, default=0.5)
    parser.add_argument("--stage8-active-c-soft-width", type=float, default=0.05)
    parser.add_argument("--stage8-tangent-soft-min", type=float, default=0.01)
    parser.add_argument("--stage8-curvature-relaxation", type=float, default=1.0)
    parser.add_argument("--stage8-relaxation-tau", type=float, default=1.0)
    parser.add_argument("--sphere-rad-angle-deg", type=float, default=11.0)
    parser.add_argument("--outer-rad-angle-deg", type=float, default=90.0)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def init_cases(args: argparse.Namespace) -> list[SphereInit]:
    solid_center = (40.0, 40.0, 48.0)
    drop_center = (40.0, 40.0, 96.0)
    solid_radius = 24.0
    drop_radius = 24.0
    parent_radius, center_distance = sphere_cap_parent_radius(solid_radius, drop_radius, 30.0)
    cap_center = (solid_center[0], solid_center[1], solid_center[2] + center_distance)
    free = SphereInit(
        case_id="theta030_free_sphere_shadow",
        init_kind="free_sphere",
        radius_xml=f"""    <Param name="Radius" value="{drop_radius:.16g}"/>
    <Param name="CenterX" value="{drop_center[0]:.16g}"/>
    <Param name="CenterY" value="{drop_center[1]:.16g}"/>
    <Param name="CenterZ" value="{drop_center[2]:.16g}"/>""",
        sphere_cap_xml='    <Param name="SphereCapInit" value="0"/>',
        meta={"drop_radius": drop_radius, "drop_center_z": drop_center[2]},
    )
    cap = SphereInit(
        case_id="theta030_cap_on_sphere_shadow",
        init_kind="cap_on_sphere_approx",
        radius_xml="""    <Param name="Radius" value="0"/>
    <Param name="CenterX" value="40"/>
    <Param name="CenterY" value="40"/>
    <Param name="CenterZ" value="96"/>""",
        sphere_cap_xml=f"""    <Param name="SphereCapInit" value="1"/>
    <Param name="SphereCapInitParentRadius" value="{parent_radius:.16g}"/>
    <Param name="SphereCapInitCenterX" value="{cap_center[0]:.16g}"/>
    <Param name="SphereCapInitCenterY" value="{cap_center[1]:.16g}"/>
    <Param name="SphereCapInitCenterZ" value="{cap_center[2]:.16g}"/>
    <Param name="SphereCapInitSolidCenterX" value="{solid_center[0]:.16g}"/>
    <Param name="SphereCapInitSolidCenterY" value="{solid_center[1]:.16g}"/>
    <Param name="SphereCapInitSolidCenterZ" value="{solid_center[2]:.16g}"/>
    <Param name="SphereCapInitSolidRadius" value="{solid_radius:.16g}"/>""",
        meta={
            "diagnostic_note": "approximate parent-sphere cap initializer, not a theoretical equilibrium solution",
            "solid_radius": solid_radius,
            "volume_equivalent_drop_radius": drop_radius,
            "target_theta_deg": 30.0,
            "parent_radius": parent_radius,
            "parent_center_distance": center_distance,
            "parent_center_z": cap_center[2],
        },
    )
    if args.case_set == "free_sphere_only":
        return [free]
    if args.case_set == "cap_on_sphere_only":
        return [cap]
    return [free, cap]


def case_xml(args: argparse.Namespace, init: SphereInit, remote_case: str) -> str:
    return f"""<?xml version="1.0"?>
<!--
  Stage8f z48 sphere normal-limiter root-cause diagnostic.
  Status: {STATUS} / exploratory_not_validation.
  Geometry: 80x80x180, R_drop=24, R_solid=24, solid_center_z=48.
  Stage8OperatorMode=1; mode 1 is shadow-only and does not write gradPhiVal.
  Raw VTI/PVTI should remain remote-only.
-->
<CLBConfig version="2.0" output="{remote_case}/output/" permissive="true">
  <Geometry nx="80" ny="80" nz="180">
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
      <Sphere dx="16" nx="48" dy="16" ny="48" dz="24" nz="48"/>
    </Wall>
  </Geometry>
  <Model>
    <Param name="Density_h" value="1"/>
    <Param name="Density_l" value="0.001"/>
    <Param name="Viscosity_h" value="0.09"/>
    <Param name="Viscosity_l" value="0.1"/>
    <Param name="tauUpdate" value="3"/>
    <Param name="sigma" value="5e-05"/>
    <Param name="M" value="{args.mobility:.16g}"/>
    <Param name="IntWidth" value="{args.int_width:.16g}"/>
{init.radius_xml}
    <Param name="BubbleType" value="1"/>
{init.sphere_cap_xml}
    <Param name="VelocityX" value="0.0"/>
    <Param name="VelocityY" value="0.0"/>
    <Param name="VelocityZ" value="0.0"/>
    <Param name="GravitationX" value="0.0"/>
    <Param name="GravitationY" value="0.0"/>
    <Param name="GravitationZ" value="0.0"/>
    <Param name="BuoyancyX" value="0.0"/>
    <Param name="BuoyancyY" value="0.0"/>
    <Param name="BuoyancyZ" value="0.0"/>
    <Param name="radAngle" value="{args.outer_rad_angle_deg:.16g}d"/>
    <Param name="radAngle" value="{args.outer_rad_angle_deg:.16g}d" zone="OuterDomain"/>
    <Param name="radAngle" value="{args.sphere_rad_angle_deg:.16g}d" zone="SolidSphere"/>
    <Param name="minGradient" value="1e-08"/>
    <Param name="Stage8GradientWettingMode" value="0"/>
    <Param name="Stage8OperatorMode" value="1"/>
    <Param name="Stage8CandidateVersion" value="8.5"/>
    <Param name="Stage8UseLocalWallAngle" value="1"/>
    <Param name="Stage8UseWallGeomNormal" value="1"/>
    <Param name="Stage8NormalDotMin" value="0.25"/>
    <Param name="Stage8MaxGradDelta" value="{args.stage8_max_grad_delta:.16g}"/>
    <Param name="Stage8MaxNormalDelta" value="{args.stage8_max_normal_delta:.16g}"/>
    <Param name="Stage8MaxNormalDeltaRatio" value="{args.stage8_max_normal_delta_ratio:.16g}"/>
    <Param name="Stage8UseSmoothActiveWeight" value="1"/>
    <Param name="Stage8ActiveCMin" value="0.02"/>
    <Param name="Stage8ActiveCSoftWidth" value="{args.stage8_active_c_soft_width:.16g}"/>
    <Param name="Stage8ActiveGradMin" value="1e-06"/>
    <Param name="Stage8ActiveTangentMin" value="1e-08"/>
    <Param name="Stage8TangentSoftMin" value="{args.stage8_tangent_soft_min:.16g}"/>
    <Param name="Stage8RelaxationTau" value="{args.stage8_relaxation_tau:.16g}"/>
    <Param name="Stage8CurvatureRelaxation" value="{args.stage8_curvature_relaxation:.16g}"/>
    <Param name="Stage8DiagSphereCenterX" value="40"/>
    <Param name="Stage8DiagSphereCenterY" value="40"/>
    <Param name="Stage8DiagSphereCenterZ" value="48"/>
    <Param name="Stage8DiagSphereRadius" value="24"/>
  </Model>
  <VTK what="{STAGE8F_VTK}"/>
  <Log Iterations="{args.log_interval}"/>
  <Failcheck Iterations="{args.failcheck_interval}"/>
  <Solve Iterations="{args.steps}">
    <VTK Iterations="{args.vtk_interval}" what="{STAGE8F_VTK}"/>
    <Log Iterations="{args.log_interval}"/>
    <Failcheck Iterations="{args.failcheck_interval}"/>
  </Solve>
</CLBConfig>
"""


def main() -> None:
    args = parse_args()
    generated = []
    for init in init_cases(args):
        case_dir = args.case_dir / init.case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        remote_case = f"{args.remote_root}/{init.case_id}"
        xml_path = case_dir / "case.xml"
        params_path = case_dir / "case_params.json"
        if (xml_path.exists() or params_path.exists()) and not args.force:
            raise SystemExit(f"{case_dir} exists; pass --force")
        xml_path.write_text(case_xml(args, init, remote_case), encoding="utf-8")
        params = {
            "status": STATUS,
            "claim_limit": "runtime_sanity / exploratory_not_validation only",
            "case_id": init.case_id,
            "remote_case": remote_case,
            "case_set": args.case_set,
            "init_kind": init.init_kind,
            "operator_mode": 1.0,
            "operator_mode_note": "1=shadow only; does not write gradPhiVal",
            "candidate_version": 8.5,
            "domain": [80, 80, 180],
            "vtk_cell_dims_expected": [80, 80, 180],
            "solid_center": [40.0, 40.0, 48.0],
            "solid_radius": 24.0,
            "bottom_gap_lu": 24.0,
            "outer_rad_angle_deg": args.outer_rad_angle_deg,
            "sphere_rad_angle_deg": args.sphere_rad_angle_deg,
            "mobility": args.mobility,
            "int_width": args.int_width,
            "stage8_max_grad_delta": args.stage8_max_grad_delta,
            "stage8_max_normal_delta": args.stage8_max_normal_delta,
            "stage8_max_normal_delta_ratio": args.stage8_max_normal_delta_ratio,
            "steps": args.steps,
            "vtk_interval": args.vtk_interval,
            "vtk_expected_steps": [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000],
            "vtk_what": STAGE8F_VTK,
            **init.meta,
        }
        params_path.write_text(json.dumps(params, indent=2), encoding="utf-8")
        generated.append({"case_id": init.case_id, "xml": str(xml_path), **params})
    manifest = {
        "status": STATUS,
        "claim_limit": "runtime_sanity / exploratory_not_validation only",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Stage8f z48 sphere normal-limiter root-cause diagnostic gate",
        "binary": args.binary,
        "remote_root": args.remote_root,
        "case_dir": str(args.case_dir),
        "generated": generated,
    }
    (args.case_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
