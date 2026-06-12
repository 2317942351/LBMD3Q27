#!/usr/bin/env python3
"""Generate Stage8d z48 sphere shadow limiter-attribution case."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path


STATUS = "runtime_sanity"
CASE_DIR = Path("cases") / "diagnostics" / "pre2025_sphere_stage8d_shadow_limiter_attribution_20260612"
REMOTE_ROOT = (
    "/mnt/8A0E24070E23EAC1/runs/"
    "tclb_pre2025_sphere_stage8d_shadow_limiter_attribution_20260612"
)
BINARY = (
    "/home/yuan/src/TCLB_stage8d_sphere_shadow_limiter_attribution_20260612/"
    "CLB/d3q27_pf_velocity_q27_geometric/main"
)

STAGE8D_VTK = (
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
    "WallStage8UsedGeomNormal,"
    "WallStage8TanCoeffLocal,WallStage8ThetaLocal,WallStage8PhaseC,"
    "WallStage8GradMagRaw,WallStage8TangentGradRaw,"
    "WallStage8TargetNormalGrad,WallStage8NormalDeltaRaw,"
    "WallStage8NormalDeltaLimited,WallStage8VectorDeltaRawMag,"
    "WallStage8VectorDeltaLimitedMag,WallStage8NormalLimiterHit,"
    "WallStage8VectorLimiterHit,WallStage8LimiterRatio,"
    "WallStage8RegionTag,WallStage8SphereRadialDot,WallStage8ContactBandTag"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-dir", type=Path, default=CASE_DIR)
    parser.add_argument("--remote-root", default=REMOTE_ROOT)
    parser.add_argument("--binary", default=BINARY)
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--vtk-interval", type=int, default=100)
    parser.add_argument("--log-interval", type=int, default=50)
    parser.add_argument("--failcheck-interval", type=int, default=50)
    parser.add_argument("--operator-mode", type=float, default=1.0)
    parser.add_argument("--mobility", type=float, default=0.1)
    parser.add_argument("--int-width", type=float, default=6.0)
    parser.add_argument("--stage8-max-grad-delta", type=float, default=0.25)
    parser.add_argument("--stage8-normal-dot-min", type=float, default=0.25)
    parser.add_argument("--stage8-relaxation-tau", type=float, default=1.0)
    parser.add_argument("--sphere-rad-angle-deg", type=float, default=11.0)
    parser.add_argument("--outer-rad-angle-deg", type=float, default=90.0)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def case_xml(args: argparse.Namespace, case_root: str) -> str:
    return f"""<?xml version="1.0"?>
<!--
  Stage8d z48 sphere shadow limiter-attribution diagnostic.
  Status: {STATUS} / exploratory_not_validation.
  Geometry: 80x80x180, R_drop=24, R_solid=24, solid_center_z=48.
  Stage8OperatorMode={args.operator_mode:g}; mode 1 is shadow-only and does not write gradPhiVal.
  Raw VTI/PVTI should remain remote-only.
-->
<CLBConfig version="2.0" output="{case_root}/output/" permissive="true">
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
    <Param name="Radius" value="24"/>
    <Param name="BubbleType" value="1"/>
    <Param name="CenterX" value="40"/>
    <Param name="CenterY" value="40"/>
    <Param name="CenterZ" value="96"/>
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
    <Param name="Stage8OperatorMode" value="{args.operator_mode:.16g}"/>
    <Param name="Stage8UseLocalWallAngle" value="1"/>
    <Param name="Stage8UseWallGeomNormal" value="1"/>
    <Param name="Stage8NormalDotMin" value="{args.stage8_normal_dot_min:.16g}"/>
    <Param name="Stage8MaxGradDelta" value="{args.stage8_max_grad_delta:.16g}"/>
    <Param name="Stage8ActiveCMin" value="0.02"/>
    <Param name="Stage8ActiveGradMin" value="1e-06"/>
    <Param name="Stage8ActiveTangentMin" value="1e-08"/>
    <Param name="Stage8RelaxationTau" value="{args.stage8_relaxation_tau:.16g}"/>
    <Param name="Stage8DiagSphereCenterX" value="40"/>
    <Param name="Stage8DiagSphereCenterY" value="40"/>
    <Param name="Stage8DiagSphereCenterZ" value="48"/>
    <Param name="Stage8DiagSphereRadius" value="24"/>
  </Model>
  <VTK what="{STAGE8D_VTK}"/>
  <Log Iterations="{args.log_interval}"/>
  <Failcheck Iterations="{args.failcheck_interval}"/>
  <Solve Iterations="{args.steps}">
    <VTK Iterations="{args.vtk_interval}" what="{STAGE8D_VTK}"/>
    <Log Iterations="{args.log_interval}"/>
    <Failcheck Iterations="{args.failcheck_interval}"/>
  </Solve>
</CLBConfig>
"""


def main() -> None:
    args = parse_args()
    case_id = "theta030_shadow"
    case_dir = args.case_dir / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    remote_case = f"{args.remote_root}/{case_id}"
    xml_path = case_dir / "case.xml"
    params_path = case_dir / "case_params.json"
    if (xml_path.exists() or params_path.exists()) and not args.force:
        raise SystemExit(f"{case_dir} exists; pass --force")
    xml_path.write_text(case_xml(args, remote_case), encoding="utf-8")
    params = {
        "status": STATUS,
        "claim_limit": "runtime_sanity / exploratory_not_validation only",
        "case_id": case_id,
        "remote_case": remote_case,
        "operator_mode": args.operator_mode,
        "operator_mode_note": "1=shadow only; does not write gradPhiVal",
        "domain": [80, 80, 180],
        "vtk_cell_dims_expected": [96, 80, 180],
        "solid_center": [40.0, 40.0, 48.0],
        "solid_radius": 24.0,
        "drop_center": [40.0, 40.0, 96.0],
        "drop_radius": 24.0,
        "bottom_gap_lu": 24.0,
        "outer_rad_angle_deg": args.outer_rad_angle_deg,
        "sphere_rad_angle_deg": args.sphere_rad_angle_deg,
        "sphere_rad_angle_rad": math.radians(args.sphere_rad_angle_deg),
        "mobility": args.mobility,
        "int_width": args.int_width,
        "stage8_normal_dot_min": args.stage8_normal_dot_min,
        "stage8_max_grad_delta": args.stage8_max_grad_delta,
        "stage8_relaxation_tau": args.stage8_relaxation_tau,
        "stage8_diag_sphere_center": [40.0, 40.0, 48.0],
        "stage8_diag_sphere_radius": 24.0,
        "steps": args.steps,
        "vtk_interval": args.vtk_interval,
        "vtk_expected_steps": [0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000],
        "vtk_what": STAGE8D_VTK,
    }
    params_path.write_text(json.dumps(params, indent=2), encoding="utf-8")
    manifest = {
        "status": STATUS,
        "claim_limit": "runtime_sanity / exploratory_not_validation only",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Stage8d z48 sphere shadow limiter-attribution gate",
        "binary": args.binary,
        "remote_root": args.remote_root,
        "case_dir": str(args.case_dir),
        "generated": [{"case_id": case_id, "xml": str(xml_path), **params}],
    }
    manifest_path = args.case_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
