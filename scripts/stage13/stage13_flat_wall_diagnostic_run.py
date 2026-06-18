#!/usr/bin/env python3
"""Generate and optionally run the Stage13 flat-wall wetting diagnostic gate.

This script is intentionally wall-only. It is the first runtime gate after the
Stage13 stencil/sentinel/wetting-path closure work and must pass before
sphere, cylinder, or impact cases are interpreted.

Default behavior writes case directories only. Use --run explicitly to launch
TCLB on the target machine.
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
    "/home/yuan/src/TCLB_lbm2026_compile_lane/"
    "CLB/d3q27_pf_velocity_q27_geometric/main"
)
DEFAULT_ROOT = "/mnt/usb1t/RUNS/runs/stage13_flat_wall_diag_20260615"
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
        "LocalRadAngle",
        "WallH",
        "AnalyticWallNormal",
        "AnalyticFlag",
        "ForceIterResidual",
        "ForceIterCount",
        "MassCorrectionApplied",
        "PhaseStencilGhostUseCount",
        "PhaseStencilFallbackCount",
        "PhaseStencilMidpointFallbackCount",
        "WallCSQMode",
        "WallCSQNormalMode",
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
        "WallCSQAppliedResidual",
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
        "WallCSQVertexRealFluidBits",
        "WallCSQVertexPhaseCleanBits",
        "WallCSQVertexQMin",
        "WallCSQVertexQMax",
        "WallCSQRejectedSolidVertexCount",
        "WallCSQRejectedSentinelCount",
        "WallCSQStrictWriteReady",
        "WallGradDeltaMag",
        "WallGradThetaApp",
        "WallMuCandidate",
        "DynamicCLActive",
        "DynamicCLIndicator",
        "DynamicCLCosApp",
        "DynamicCLThetaApp",
        "DynamicCLCosEq",
        "DynamicCLCosResidual",
        "DynamicCLForceCandidateX",
        "DynamicCLForceCandidateY",
        "DynamicCLForceCandidateZ",
        "DynamicCLForceCandidateMag",
        "DynamicCLTangentialX",
        "DynamicCLTangentialY",
        "DynamicCLTangentialZ",
        "DynamicCLWallNormalX",
        "DynamicCLWallNormalY",
        "DynamicCLWallNormalZ",
        "DynamicCLRejectedReason",
        # Stage 15B fix fields: record how theta_eq was sourced (from the
        # adjacent wetting wall's LocalRadAngle, not this node's zonal
        # radAngle) and why a node is blocked. Needed to verify the fix.
        "DynamicCLThetaEq",
        "DynamicCLWallContextFound",
        "DynamicCLBlockedReason",
        "DynamicCLWallDx",
        "DynamicCLWallDy",
        "DynamicCLWallDz",
    ]
)


@dataclass(frozen=True)
class CaseDef:
    name: str
    init_theta: float
    bc_theta: float
    purpose: str


EQUILIBRIUM_CASES = [
    CaseDef("diag_wall_t30", 30.0, 30.0, "equilibrium acute response"),
    CaseDef("diag_wall_t90", 90.0, 90.0, "neutral path sanity"),
    CaseDef("diag_wall_t150", 150.0, 150.0, "equilibrium obtuse response"),
]
DECOUPLED_CASES = [
    CaseDef("decouple_wall_60to30", 60.0, 30.0, "acute target direction check"),
    CaseDef("decouple_wall_120to150", 120.0, 150.0, "obtuse target direction check"),
]


def cap_sphere_radius(volume_radius: float, theta_deg: float) -> float:
    theta = math.radians(theta_deg)
    denom = (1.0 - math.cos(theta)) ** 2 * (2.0 + math.cos(theta))
    if denom <= 0.0:
        raise ValueError(f"invalid cap theta: {theta_deg}")
    return volume_radius * (4.0 / denom) ** (1.0 / 3.0)


def param(name: str, value: str | float | int, zone: str | None = None) -> str:
    zone_attr = f' zone="{zone}"' if zone else ""
    return f'    <Param name="{name}" value="{value}"{zone_attr}/>'


def binary_hash(binary: str) -> str | None:
    try:
        output = subprocess.check_output(["sha256sum", binary], text=True)
    except Exception:
        return None
    parts = output.split()
    return parts[0] if parts else None


def parse_run_log(case_dir: Path) -> dict[str, Any]:
    path = case_dir / "run.log"
    if not path.exists():
        return {"exists": False, "run_rc": None, "nan_detected": None, "failcheck_stop": None}
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    run_rc = None
    for line in reversed(lines):
        if line.startswith("RUN_RC="):
            try:
                run_rc = int(line.split("=", 1)[1].strip())
            except ValueError:
                run_rc = None
            break
    nan_patterns = [
        "discovered NaN",
        "NaN value discovered",
        "Stopping due to Nan value",
        "Stopping due to NaN value",
    ]
    return {
        "exists": True,
        "run_rc": run_rc,
        "nan_detected": any(any(pattern in line for pattern in nan_patterns) for line in lines),
        "failcheck_stop": any("Stopping due to" in line for line in lines),
    }


def render_xml(
    case: CaseDef,
    *,
    iterations: int,
    vtk_period: int,
    log_period: int,
    volume_radius: float,
    int_width: float,
    mobility: float,
    wetting_bc_mode: int,
    force_fixed_tol: float,
    force_fixed_max_iter: int,
    wall_compact_stencil_mode: int,
    wall_compact_stencil_write_allowed_flag: int,
    wall_grad_mode: int,
    wall_grad_contact_sign: float,
    wall_mu_mode: int,
    dynamic_cl_mode: int,
) -> str:
    parent_radius = cap_sphere_radius(volume_radius, case.init_theta)
    theta = math.radians(case.init_theta)
    cap_center_x = 48.0
    cap_center_y = -parent_radius * math.cos(theta)
    cap_center_z = 48.0
    initial_center_y = max(2.0, parent_radius * (1.0 - math.cos(theta)) * 0.35)
    init_params = "\n".join(
        [
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
        ]
    )
    return f"""<?xml version="1.0"?>
<CLBConfig version="2.0" output="output/" permissive="true">
  <Geometry nx="96" ny="80" nz="96">
    <MRT><Box/></MRT>
    <Wall mask="ALL" name="OuterDomain">
      <Box nx="1"/><Box dx="-1"/><Box dy="-1"/><Box nz="1"/><Box dz="-1"/>
    </Wall>
    <Wall mask="ALL" name="FlatLowerY"><Box dx="1" nx="94" ny="1" dz="1" nz="94"/></Wall>
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
{init_params}
    <Param name="BubbleType" value="1.0"/>
    <Param name="VelocityX" value="0.0"/>
    <Param name="VelocityY" value="0.0"/>
    <Param name="VelocityZ" value="0.0"/>
    <Param name="GravitationX" value="0.0"/>
    <Param name="GravitationY" value="0.0"/>
    <Param name="GravitationZ" value="0.0"/>
    <Param name="radAngle" value="90d"/>
    <Param name="radAngle" value="90d" zone="OuterDomain"/>
    <Param name="AnalyticSolidType" value="1"/>
    <Param name="AnalyticSolidAxis" value="1"/>
    <Param name="AnalyticSolidPlaneOffset" value="0.0"/>
    <Param name="AnalyticWetting" value="1"/>
    <Param name="WettingBCMode" value="{wetting_bc_mode}"/>
    <Param name="WallCompactStencilMode" value="{wall_compact_stencil_mode}"/>
    <Param name="WallCompactStencilNormalMode" value="1"/>
    <Param name="WallCompactStencilMaxL" value="3"/>
    <Param name="WallCompactStencilBoundEps" value="0.0"/>
    <Param name="WallCompactStencilMaxBoundedDelta" value="1e-08"/>
    <Param name="WallCompactStencilAppliedResidualTol" value="1e-08"/>
    <Param name="WallCompactStencilWriteAllowedFlag" value="{wall_compact_stencil_write_allowed_flag}"/>
    <Param name="ForceFixedTol" value="{force_fixed_tol:.16g}"/>
    <Param name="ForceFixedMaxIter" value="{force_fixed_max_iter}"/>
    <Param name="WallGradMode" value="{wall_grad_mode}"/>
    <Param name="WallGradContactSign" value="{wall_grad_contact_sign:.16g}"/>
    <Param name="WallMuMode" value="{wall_mu_mode}"/>
    <Param name="DynamicCLMode" value="{dynamic_cl_mode}"/>
    <Param name="radAngle" value="{case.bc_theta:.16g}d" zone="FlatLowerY"/>
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


def write_case(case: CaseDef, args: argparse.Namespace) -> Path:
    case_dir = Path(args.root) / case.name
    if case_dir.exists() and args.force:
        subprocess.run(["rm", "-rf", str(case_dir)], check=True)
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "output").mkdir(exist_ok=True)
    xml = render_xml(
        case,
        iterations=args.iterations,
        vtk_period=args.vtk_period,
        log_period=args.log_period,
        volume_radius=args.volume_radius,
        int_width=args.int_width,
        mobility=args.mobility,
        wetting_bc_mode=args.wetting_bc_mode,
        force_fixed_tol=args.force_fixed_tol,
        force_fixed_max_iter=args.force_fixed_max_iter,
        wall_compact_stencil_mode=args.wall_compact_stencil_mode,
        wall_compact_stencil_write_allowed_flag=args.wall_compact_stencil_write_allowed_flag,
        wall_grad_mode=args.wall_grad_mode,
        wall_grad_contact_sign=args.wall_grad_contact_sign,
        wall_mu_mode=args.wall_mu_mode,
        dynamic_cl_mode=args.dynamic_cl_mode,
    )
    (case_dir / "case.xml").write_text(xml, encoding="utf-8")
    metadata: dict[str, Any] = {
        "stage": "stage13_flat_wall_diagnostic",
        "case": case.name,
        "geometry": "wall",
        "purpose": case.purpose,
        "init_theta_deg": case.init_theta,
        "bc_theta_deg": case.bc_theta,
        "decoupled": abs(case.init_theta - case.bc_theta) > 1e-9,
        "iterations": args.iterations,
        "vtk_period": args.vtk_period,
        "log_period": args.log_period,
        "vtk_fields": VTK_FIELDS.split(","),
        "wetting_bc_mode": args.wetting_bc_mode,
        "target_wall_zone": "FlatLowerY",
        "target_wall_patch": {
            "x_start": 1,
            "x_count": 94,
            "y_start": 0,
            "y_count": 1,
            "z_start": 1,
            "z_count": 94,
            "reason": (
                "exclude outer-domain edge/corner overlaps from the flat-wall "
                "contact-angle gate"
            ),
        },
        "force_fixed_tol": args.force_fixed_tol,
        "force_fixed_max_iter": args.force_fixed_max_iter,
        "compact_mode": args.compact_mode,
        "wall_compact_stencil_mode": args.wall_compact_stencil_mode,
        "wall_compact_stencil_write_allowed_flag": args.wall_compact_stencil_write_allowed_flag,
        "expected_target_wetting_path_id": (
            30.0 if args.wall_compact_stencil_write_allowed_flag > 0 else [1.0, 2.0]
        ),
        "volume_equivalent_radius": args.volume_radius,
        "interface_width": args.int_width,
        "mobility": args.mobility,
        "wall_grad_mode": args.wall_grad_mode,
        "wall_grad_contact_sign": args.wall_grad_contact_sign,
        "wall_mu_mode": args.wall_mu_mode,
        "dynamic_cl_mode": args.dynamic_cl_mode,
        "binary": args.binary,
        "binary_sha256": binary_hash(args.binary),
        "classification_before_audit": "exploratory_not_validation",
        "claim_limit": "flat-wall diagnostic gate only; not validation_passed",
        "required_diagnostics": [
            "WallGhostRaw",
            "WallGhostClamped",
            "WallGhostClampHit",
            "WettingPathId",
            "LocalRadAngle",
            "ForceIterResidual",
            "ForceIterCount",
            "MassCorrectionApplied",
            "PhaseStencilGhostUseCount",
            "PhaseStencilFallbackCount",
            "PhaseStencilMidpointFallbackCount",
            "WallCSQMode",
            "WallCSQNormalMode",
            "WallCSQValid",
            "WallCSQResidual",
            "WallCSQAppliedResidual",
            "WallCSQFallbackReason",
            "WallCSQBoundedDelta",
            "WallCSQMethodComplete",
            "WallCSQCandidateCount",
            "WallCSQFluidVertexCount",
            "WallCSQTriangleInside",
            "WallCSQStrictWriteReady",
        ],
        "pass_intent": (
            "equilibrium cases check path fields and acute/neutral/obtuse response; "
            "decoupled cases must move from init_theta toward bc_theta before "
            "sphere/cylinder gates are allowed"
        ),
    }
    (case_dir / "case_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8"
    )
    return case_dir


def run_case(case_dir: Path, args: argparse.Namespace) -> int:
    env = os.environ.copy()
    env["PATH"] = "/usr/local/cuda-12.6/bin:/usr/bin:/bin:/usr/local/bin"
    env["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
    env["CUDA_VISIBLE_DEVICES"] = str(args.gpu)
    env["OMPI_MCA_plm_rsh_agent"] = "/usr/bin/ssh"
    env["LD_LIBRARY_PATH"] = "/usr/local/cuda-12.6/lib64:" + env.get("LD_LIBRARY_PATH", "")
    with (case_dir / "run.log").open("w", encoding="utf-8", errors="replace") as log:
        log.write(f"stage13 flat-wall diagnostic run: {case_dir.name}\n")
        log.write(f"binary={args.binary}\n")
        log.flush()
        completed = subprocess.run(
            ["timeout", str(args.timeout), args.binary, "case.xml"],
            cwd=case_dir,
            stdout=log,
            stderr=subprocess.STDOUT,
            env=env,
        )
        log.write(f"\nRUN_RC={completed.returncode}\n")
    parsed = parse_run_log(case_dir)
    if parsed.get("nan_detected") or parsed.get("failcheck_stop"):
        return 70
    return completed.returncode


def selected_cases(matrix: str) -> list[CaseDef]:
    if matrix == "equilibrium":
        return EQUILIBRIUM_CASES
    if matrix == "decoupled":
        return DECOUPLED_CASES
    if matrix == "all":
        return EQUILIBRIUM_CASES + DECOUPLED_CASES
    raise ValueError(f"unknown matrix: {matrix}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", choices=["equilibrium", "decoupled", "all"], default="equilibrium")
    parser.add_argument(
        "--case",
        choices=[case.name for case in EQUILIBRIUM_CASES + DECOUPLED_CASES],
        default=None,
        help="run/write one named case from the selected Stage13 matrix",
    )
    parser.add_argument("--root", default=DEFAULT_ROOT)
    parser.add_argument("--binary", default=DEFAULT_BIN)
    parser.add_argument("--iterations", type=int, default=6000)
    parser.add_argument("--vtk-period", type=int, default=1000)
    parser.add_argument("--log-period", type=int, default=500)
    parser.add_argument("--volume-radius", type=float, default=16.0)
    parser.add_argument("--int-width", type=float, default=3.0)
    parser.add_argument("--mobility", type=float, default=0.3)
    parser.add_argument("--wetting-bc-mode", type=int, default=0)
    parser.add_argument("--wall-grad-mode", type=int, default=0, help="Layer1 Wang corrected gradient: 0 off, 1 shadow (diagnostic only). NOTE: mode=2 (write) is DISABLED since Stage 15B-pre; the corrected gradient is diagnostic-only and never enters the dynamics.")
    parser.add_argument("--wall-grad-contact-sign", type=float, default=1.0)
    parser.add_argument("--wall-mu-mode", type=int, default=0, help="Layer2 Ju wall-mu: 0 off, 1 shadow, 2 write")
    parser.add_argument("--dynamic-cl-mode", type=int, default=0, help="Layer3 DynamicCL: 0 off, 1 shadow (diagnostics only). NOTE: mode=2 (write to F_total) is reserved for Stage 15C and refused by this runner until 15C.")
    parser.add_argument("--force-fixed-tol", type=float, default=0.0)
    parser.add_argument("--force-fixed-max-iter", type=int, default=2)
    parser.add_argument(
        "--compact-mode",
        choices=["write", "shadow"],
        default="write",
        help=(
            "write: exercise compact q_s -> WallGhost path; shadow: compute "
            "WallCSQ diagnostics while retaining the legacy analytic ghost"
        ),
    )
    parser.add_argument(
        "--wall-compact-stencil-mode",
        type=int,
        default=None,
        help="manual override; normally 2 for --compact-mode write and 1 for shadow",
    )
    parser.add_argument(
        "--wall-compact-stencil-write-allowed-flag",
        type=int,
        default=None,
        help="manual override; normally 1 for --compact-mode write and 0 for shadow",
    )
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument("--force", action="store_true", help="replace existing case dirs")
    parser.add_argument("--run", action="store_true", help="launch TCLB after writing cases")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    # Stage 15B-pre safety guard: WallGradMode=2 (corrected-gradient write) is
    # disabled. It replaces gradPhi with the static equilibrium contact-angle
    # gradient and erases the non-equilibrium residual that drives contact-line
    # motion; this was disproven by the decoupled direction tests (docs 24/27).
    # The corrected gradient is now diagnostic-only (mode<=1); the compact ghost
    # is the sole wall-phase source. Refuse rather than silently clamp so no run
    # can silently use the wrong physics.
    if args.wall_grad_mode >= 2:
        raise ValueError(
            "WallGradMode=2 (corrected-gradient write) is disabled since "
            "Stage 15B-pre. The corrected gradient is diagnostic-only "
            "(use --wall-grad-mode 0 or 1). The compact ghost remains the "
            "sole wall-phase physics channel."
        )
    # Stage 15B: DynamicCL write (mode>=2, adding F_CL to F_total) is reserved
    # for Stage 15C. 15B only allows shadow (mode<=1, diagnostics, no force).
    if args.dynamic_cl_mode >= 2:
        raise ValueError(
            "DynamicCLMode=2 (add residual contact-line force to F_total) is "
            "reserved for Stage 15C. Current stage (15B) is shadow-only: use "
            "--dynamic-cl-mode 0 or 1."
        )
    if args.wall_compact_stencil_mode is None:
        args.wall_compact_stencil_mode = 2 if args.compact_mode == "write" else 1
    if args.wall_compact_stencil_write_allowed_flag is None:
        args.wall_compact_stencil_write_allowed_flag = (
            1 if args.compact_mode == "write" else 0
        )
    if args.compact_mode == "write":
        if args.wall_compact_stencil_mode < 2:
            raise ValueError("--compact-mode write requires WallCompactStencilMode >= 2")
        if args.wall_compact_stencil_write_allowed_flag < 1:
            raise ValueError(
                "--compact-mode write requires WallCompactStencilWriteAllowedFlag >= 1"
            )
    if args.compact_mode == "shadow" and args.wall_compact_stencil_write_allowed_flag > 0:
        raise ValueError("--compact-mode shadow must not enable compact writes")
    results = []
    rc = 0
    cases = selected_cases(args.matrix)
    if args.case is not None:
        cases = [case for case in EQUILIBRIUM_CASES + DECOUPLED_CASES if case.name == args.case]
        if not cases:
            raise ValueError(f"unknown case: {args.case}")
    for case in cases:
        case_dir = write_case(case, args)
        item: dict[str, Any] = {"case": case.name, "case_dir": str(case_dir), "written": True}
        if args.run:
            run_rc = run_case(case_dir, args)
            item["run_rc"] = run_rc
            rc = rc or run_rc
        results.append(item)
    manifest = {
        "stage": "stage13_flat_wall_diagnostic",
        "root": args.root,
        "matrix": args.matrix,
        "compact_mode": args.compact_mode,
        "wall_compact_stencil_mode": args.wall_compact_stencil_mode,
        "wall_compact_stencil_write_allowed_flag": (
            args.wall_compact_stencil_write_allowed_flag
        ),
        "run_requested": args.run,
        "claim_limit": "exploratory_not_validation only",
        "results": results,
    }
    Path(args.root).mkdir(parents=True, exist_ok=True)
    (Path(args.root) / "stage13_flat_wall_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
