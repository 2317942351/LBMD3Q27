#!/usr/bin/env python3
"""Generate Stage8f flat-wall low-angle normal-limiter diagnostic cases."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


STATUS = "runtime_sanity"
CASE_DIR = Path("cases") / "diagnostics" / "flat_wall_cap_stage8f_low_angle_20260613"
REMOTE_ROOT = "/mnt/8A0E24070E23EAC1/runs/tclb_flat_wall_cap_stage8f_low_angle_20260613"
BINARY = (
    "/home/yuan/src/TCLB_stage8f_normal_limiter_root_cause_diag_20260613/"
    "CLB/d3q27_pf_velocity_q27_geometric/main"
)

STAGE8F_VTK = (
    "PhaseField,U,P,Rho,BOUNDARY,WallBCPath,"
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
class FlatCase:
    case_id: str
    init_theta_deg: float
    wall_angle_deg: float
    operator_mode: float


def cap_sphere_radius(volume_radius: float, theta_deg: float) -> float:
    theta = math.radians(theta_deg)
    denom = (1.0 - math.cos(theta)) ** 2 * (2.0 + math.cos(theta))
    if denom <= 0.0:
        raise ValueError(f"invalid cap theta {theta_deg}")
    return volume_radius * (4.0 / denom) ** (1.0 / 3.0)


def cases_for_set(case_set: str) -> list[FlatCase]:
    if case_set == "shadow_low_angle":
        return [
            FlatCase(f"cap_theta030_wall{angle:03d}_mode1", 30.0, float(angle), 1.0)
            for angle in [5, 8, 11, 15, 20, 25, 30]
        ]
    raise ValueError(f"unknown case set {case_set}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-dir", type=Path, default=CASE_DIR)
    parser.add_argument("--remote-root", default=REMOTE_ROOT)
    parser.add_argument("--binary", default=BINARY)
    parser.add_argument("--case-set", choices=["shadow_low_angle"], default="shadow_low_angle")
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--vtk-interval", type=int, default=100)
    parser.add_argument("--log-interval", type=int, default=100)
    parser.add_argument("--failcheck-interval", type=int, default=100)
    parser.add_argument("--volume-radius", type=float, default=24.0)
    parser.add_argument("--mobility", type=float, default=0.1)
    parser.add_argument("--int-width", type=float, default=6.0)
    parser.add_argument("--stage8-max-grad-delta", type=float, default=0.25)
    parser.add_argument("--stage8-max-normal-delta", type=float, default=0.05)
    parser.add_argument("--stage8-max-normal-delta-ratio", type=float, default=0.5)
    parser.add_argument("--stage8-active-c-soft-width", type=float, default=0.05)
    parser.add_argument("--stage8-tangent-soft-min", type=float, default=0.01)
    parser.add_argument("--stage8-curvature-relaxation", type=float, default=1.0)
    parser.add_argument("--stage8-relaxation-tau", type=float, default=1.0)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def case_xml(args: argparse.Namespace, case: FlatCase, remote_case: str) -> str:
    cap_radius = cap_sphere_radius(args.volume_radius, case.init_theta_deg)
    theta_rad = math.radians(case.init_theta_deg)
    cap_center_x = 64.0
    cap_center_y = -cap_radius * math.cos(theta_rad)
    cap_center_z = 64.0
    return f"""<?xml version="1.0"?>
<!--
  Stage8f flat-wall low-angle normal-limiter root-cause diagnostic.
  Status: {STATUS} / exploratory_not_validation.
  Stage8CandidateVersion=8.5; Stage8OperatorMode=1 shadow-only.
  Raw VTI/PVTI should remain remote-only.
-->
<CLBConfig version="2.0" output="{remote_case}/output/" permissive="true">
  <Geometry nx="128" ny="96" nz="128">
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
  <Model>
    <Param name="Density_h" value="1"/>
    <Param name="Density_l" value="0.001"/>
    <Param name="Viscosity_h" value="0.09"/>
    <Param name="Viscosity_l" value="0.1"/>
    <Param name="tauUpdate" value="3"/>
    <Param name="sigma" value="5e-05"/>
    <Param name="M" value="{args.mobility:.16g}"/>
    <Param name="IntWidth" value="{args.int_width:.16g}"/>
    <Param name="Radius" value="0"/>
    <Param name="BubbleType" value="1"/>
    <Param name="CapInit" value="1"/>
    <Param name="CapInitRadius" value="{cap_radius:.16g}"/>
    <Param name="CapInitTheta" value="{theta_rad:.16g}"/>
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
    <Param name="radAngle" value="{case.wall_angle_deg:.16g}d" zone="FlatLowerY"/>
    <Param name="minGradient" value="1e-08"/>
    <Param name="Stage8GradientWettingMode" value="0"/>
    <Param name="Stage8OperatorMode" value="{case.operator_mode:.16g}"/>
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
    for case in cases_for_set(args.case_set):
        case_dir = args.case_dir / case.case_id
        case_dir.mkdir(parents=True, exist_ok=True)
        remote_case = f"{args.remote_root}/{case.case_id}"
        xml_path = case_dir / "case.xml"
        params_path = case_dir / "case_params.json"
        if (xml_path.exists() or params_path.exists()) and not args.force:
            raise SystemExit(f"{case_dir} exists; pass --force")
        xml_path.write_text(case_xml(args, case, remote_case), encoding="utf-8")
        params = {
            "status": STATUS,
            "claim_limit": "runtime_sanity / exploratory_not_validation only",
            "case_id": case.case_id,
            "remote_case": remote_case,
            "case_set": args.case_set,
            "operator_mode": case.operator_mode,
            "candidate_version": 8.5,
            "init_theta_deg": case.init_theta_deg,
            "wall_angle_deg": case.wall_angle_deg,
            "volume_radius": args.volume_radius,
            "mobility": args.mobility,
            "int_width": args.int_width,
            "stage8_max_grad_delta": args.stage8_max_grad_delta,
            "stage8_max_normal_delta": args.stage8_max_normal_delta,
            "stage8_max_normal_delta_ratio": args.stage8_max_normal_delta_ratio,
            "steps": args.steps,
            "vtk_interval": args.vtk_interval,
            "vtk_what": STAGE8F_VTK,
        }
        params_path.write_text(json.dumps(params, indent=2), encoding="utf-8")
        generated.append({"case_id": case.case_id, "xml": str(xml_path), **params})
    manifest = {
        "status": STATUS,
        "claim_limit": "runtime_sanity / exploratory_not_validation only",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Stage8f flat-wall low-angle normal-limiter root-cause diagnostic gate",
        "binary": args.binary,
        "remote_root": args.remote_root,
        "case_dir": str(args.case_dir),
        "generated": generated,
    }
    (args.case_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
