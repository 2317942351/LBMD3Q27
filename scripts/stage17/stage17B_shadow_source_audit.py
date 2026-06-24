#!/usr/bin/env python3
"""Static source audit for Stage17B diffuse-solid shadow/B3 wiring.

This gate proves only source-level guardrails:

* Stage17B lives in an independent TCLB snapshot.
* The new diffuse-solid path exports Psi*/NearWall* diagnostics.
* Stage17B defaults remain shadow-only.
* Stage17B B3 controlled write is explicitly gated and does not write PhaseF.
* The historical compact-stencil direct write remains flat-wall only.

It does not validate contact angle, stability, or runtime geometry fields.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


SNAPSHOT = Path(
    "third_party/tclb_snapshots/stage17B_diffuse_solid_shadow/"
    "models/multiphase/d3q27_pf_velocity"
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def contains(text: str, pattern: str) -> bool:
    return re.search(pattern, text, flags=re.MULTILINE | re.DOTALL) is not None


def function_block(text: str, name: str) -> str:
    start = text.find(name)
    if start < 0:
        return ""
    next_func = text.find("\nCudaDeviceFunction", start + 1)
    return text[start:] if next_func < 0 else text[start:next_func]


def cuda_function_block(text: str, name: str) -> str:
    start = text.find(f"CudaDeviceFunction void {name}")
    if start < 0:
        start = text.find(name)
    if start < 0:
        return ""
    next_func = text.find("\nCudaDeviceFunction", start + 1)
    return text[start:] if next_func < 0 else text[start:next_func]


def stage17b_block_has_no_solver_write(block: str) -> bool:
    no_phase_write = re.search(r"(?<![A-Za-z0-9_])PhaseF\s*=", block) is None
    no_wallghost_write = re.search(r"(?<![A-Za-z0-9_])WallGhost\s*=", block) is None
    return no_phase_write and no_wallghost_write


def stage17b_controlled_write_block(boundary: str) -> str:
    marker = "if (stage17b_controlled_write_requested() && PsiWriteAllowedFlag > 0.5)"
    start = boundary.find(marker)
    if start < 0:
        return ""
    open_brace = boundary.find("{", start)
    if open_brace < 0:
        return ""
    depth = 0
    for idx in range(open_brace, len(boundary)):
        if boundary[idx] == "{":
            depth += 1
        elif boundary[idx] == "}":
            depth -= 1
            if depth == 0:
                return boundary[open_brace + 1 : idx]
    return ""


def audit(root: Path) -> dict[str, Any]:
    model_dir = root / SNAPSHOT
    boundary_path = model_dir / "Boundary.c.Rt"
    dynamics_c_path = model_dir / "Dynamics.c.Rt"
    dynamics_r_path = model_dir / "Dynamics.R"

    boundary = read(boundary_path)
    dynamics_c = read(dynamics_c_path)
    dynamics_r = read(dynamics_r_path)

    compute_shadow = function_block(boundary, "stage17b_compute_diffuse_shadow")
    reset_shadow = function_block(boundary, "stage17b_reset_diffuse_shadow")
    keep_shadow = function_block(boundary, "stage17b_keep_diffuse_shadow")
    controlled_write = function_block(boundary, "stage17b_controlled_write_requested")
    controlled_write_body = stage17b_controlled_write_block(boundary)
    near_wall_write = function_block(dynamics_c, "stage17b_write_near_wall_force_shadow")
    b5_write = function_block(dynamics_c, "stage17b_write_consumption_diagnostics")
    bgk = cuda_function_block(dynamics_c, "CollisionBGK")
    mrt = cuda_function_block(dynamics_c, "CollisionMRT")

    psi_fields = [
        "PsiSolid",
        "PsiGradMag",
        "PsiNormalX",
        "PsiNormalY",
        "PsiNormalZ",
        "PsiWallGhostRaw",
        "PsiWallGhost",
        "PsiWallGhostClampHit",
        "PsiThetaImplied",
        "PsiJaggedness",
        "PsiWriteAllowedFlag",
        "PsiNormalAmbiguityFlag",
        "PsiWriteAppliedFlag",
        "PsiWriteRejectedReason",
    ]
    near_wall_fields = [
        "NearWallForceMag",
        "NearWallGradPhiMag",
        "NearWallForceOverRhoShadow",
    ]
    b5_fields = [
        "B5SignedDistance",
        "B5NearWallBandFlag",
        "B5ContactLineBandFlag",
        "B5WallGhostConsumedFlag",
        "B5GhostUseCount",
        "B5WallGhostMinusCenter",
        "B5WallGhostMinusFluidProbe",
        "B5WallGhostClampHitNeighbor",
        "B5GradPhiNormal",
        "B5GradPhiTangentialMag",
        "B5FphiSum",
        "B5FphiNormalProxy",
        "B5PhaseFromHDelta",
        "B5ExpectedResponseSign",
        "B5SignalSignOK",
    ]

    checks: dict[str, bool] = {
        "stage17b_snapshot_exists": all(
            path.exists() for path in (boundary_path, dynamics_c_path, dynamics_r_path)
        ),
        "stage17b_settings_default_shadow_only": all(
            token in dynamics_r
            for token in [
                'AddSetting(name="Stage17BDiffuseSolidMode", default=0',
                'AddSetting(name="Stage17BWriteMode", default=0',
                'AddSetting(name="Stage17BWriteSourceMode", default=0',
                'AddSetting(name="Stage17BPsiEps", default=1.25',
                'AddSetting(name="Stage17BWriteBand", default=1.8',
                'AddSetting(name="Stage17BGradPsiMin", default=1e-4',
                'AddSetting(name="Stage17BShadowThetaDeg", default=-1.0',
                'AddSetting(name="Stage17BConsumptionDiagnosticsMode", default=0',
            ]
        ),
        "psi_fields_registered": all(
            f'AddField("{field}"' in dynamics_r for field in psi_fields
        ),
        "psi_quantities_registered": all(
            f'AddQuantity(name="{field}"' in dynamics_r
            for field in [
                "PsiSolid",
                "PsiGradMag",
                "PsiWallGhostRaw",
                "PsiWallGhost",
                "PsiWallGhostClampHit",
                "PsiThetaImplied",
                "PsiJaggedness",
                "PsiWriteAllowedFlag",
                "PsiNormalAmbiguityFlag",
                "PsiWriteAppliedFlag",
                "PsiWriteRejectedReason",
            ]
        )
        and 'AddQuantity(name="PsiNormal", unit=1, vector=T)' in dynamics_r,
        "near_wall_fields_registered": all(
            f'AddField("{field}"' in dynamics_r and f'AddQuantity(name="{field}"' in dynamics_r
            for field in near_wall_fields
        ),
        "b5_consumption_fields_registered": all(
            f'AddField("{field}"' in dynamics_r and f'AddQuantity(name="{field}"' in dynamics_r
            for field in b5_fields
        ),
        "psi_getters_present": all(
            f"get{field}" in boundary
            for field in [
                "PsiSolid",
                "PsiGradMag",
                "PsiWallGhost",
                "PsiThetaImplied",
                "PsiJaggedness",
                "PsiWriteAllowedFlag",
                "PsiNormalAmbiguityFlag",
            ]
        )
        and "getPsiNormal" in boundary,
        "near_wall_getters_present": all(f"get{field}" in dynamics_c for field in near_wall_fields),
        "b5_getters_present": all(f"get{field}" in dynamics_c for field in b5_fields),
        "b5_writer_default_off_and_output_only": (
            "stage17b_write_consumption_diagnostics" in dynamics_c
            and "Stage17BConsumptionDiagnosticsMode > 0.5" in dynamics_c
            and "stage17b_write_consumption_diagnostics(C, gradPhi, tmp1" in dynamics_c
            and stage17b_block_has_no_solver_write(
                b5_write
            )
        ),
        "b5_writer_uses_tclb_safe_neighbor_access": (
            "STAGE17B_STATIC_NEIGHBOR(WallGhost, probe_dx, probe_dy, probe_dz)" in b5_write
            and "STAGE17B_STATIC_NEIGHBOR(WallGhostClampHit, probe_dx, probe_dy, probe_dz)"
            in b5_write
            and "PhaseF_dyn(-probe_dx, -probe_dy, -probe_dz)" in b5_write
            and "WallGhost(probe_dx" not in b5_write
            and "WallGhostClampHit(probe_dx" not in b5_write
            and "PhaseF(-probe_dx" not in b5_write
        ),
        "stage17b_compute_shadow_present": all(
            token in compute_shadow
            for token in [
                "stage17b_diffuse_solid_indicator",
                "stage17b_diffuse_solid_grad_analytic",
                "stage13_compute_geometric_tangent_raw",
                "Stage17BShadowThetaDeg",
                "PsiWallGhostRaw = raw",
                "PsiWallGhost = stage13_clamp_phase_value",
                "PsiWallGhostClampHit = clamp_hit",
                "PsiWriteAllowedFlag = shadow_ready ? 1.0 : 0.0",
                "PsiWriteRejectedReason",
            ]
        ),
        "stage17b_compute_shadow_has_no_solver_write": stage17b_block_has_no_solver_write(
            compute_shadow
        ),
        "stage17b_reset_keep_only_shadow_fields": (
            stage17b_block_has_no_solver_write(reset_shadow)
            and stage17b_block_has_no_solver_write(keep_shadow)
            and all(field in reset_shadow and field in keep_shadow for field in psi_fields)
        ),
        "old_curved_compact_write_still_flat_only": contains(
            boundary,
            r"compact_write\s*=\s*stage13_compact_write_requested\s*\(\s*\)\s*&&\s*"
            r"\(\s*AnalyticSolidType\s*<\s*1\.5\s*\)",
        ),
        "stage17b_shadow_called_before_legacy_analytic_wallghost": (
            boundary.find("stage17b_compute_diffuse_shadow") >= 0
            and boundary.find("WallGhost = stage13_compute_analytic_wall_ghost") >= 0
            and boundary.find("stage17b_compute_diffuse_shadow")
            < boundary.find("WallGhost = stage13_compute_analytic_wall_ghost")
        ),
        "near_wall_writer_has_no_solver_write": stage17b_block_has_no_solver_write(
            near_wall_write
        ),
        "near_wall_mrt_reset_and_write": (
            "stage17b_reset_near_wall_force_shadow();" in mrt
            and "stage17b_write_near_wall_force_shadow(gradPhi, force_rho_eff, F_total);" in mrt
        ),
        "near_wall_bgk_reset_and_write": (
            "stage17b_reset_near_wall_force_shadow();" in bgk
            and "stage17b_write_near_wall_force_shadow(gradPhi, rho, F_total);" in bgk
        ),
        "stage17b_controlled_write_gate_present": all(
            token in controlled_write
            for token in [
                "Stage17BDiffuseSolidMode > 0.5",
                "Stage17BWriteMode > 1.5",
                "AnalyticWetting > 0.5",
                "AnalyticSolidType >= 1.5",
            ]
        ),
        "stage17b_controlled_write_block_curved_only": (
            "stage17b_controlled_write_requested()" in boundary
            and "PsiWriteAllowedFlag > 0.5" in boundary
            and "WettingPathId = 170.0" in controlled_write_body
            and "WallGhost = PsiWallGhost" in controlled_write_body
            and "WallGhostRaw = PsiWallGhostRaw" in controlled_write_body
            and "WallGhostClampHit = PsiWallGhostClampHit" in controlled_write_body
            and "PsiWriteAppliedFlag = 1.0" in controlled_write_body
        ),
        "stage17b_b8_legacy_write_source_default_off": (
            "Stage17BWriteSourceMode > 0.5 && Stage17BWriteSourceMode < 1.5"
            in controlled_write_body
            and "stage13_compute_analytic_wall_ghost(" in controlled_write_body
            and "WettingPathId = 171.0" in controlled_write_body
            and "WettingPathId = 170.0" in controlled_write_body
            and 'AddSetting(name="Stage17BWriteSourceMode", default=0' in dynamics_r
        ),
        "stage17b_controlled_write_no_compact_gate": (
            "WallCompactStencilWriteAllowedFlag" not in controlled_write
            and "WallCompactStencilWriteAllowedFlag" not in controlled_write_body
        ),
        "stage17b_controlled_write_no_phase_override": contains(
            controlled_write_body,
            r"PhaseF\s*=\s*pf_f\s*;"
        ),
        "claim_limit_comment_present": (
            "output-only in B2" in dynamics_r
            and "controlled WallGhost write" in dynamics_r
        ),
    }
    failures = [name for name, ok in checks.items() if not ok]
    return {
        "status": "PASS_STAGE17B_SHADOW_SOURCE_GUARDRAILS" if not failures else "FAIL",
        "root": str(root),
        "snapshot": str(model_dir),
        "files": {
            "Boundary.c.Rt": str(boundary_path),
            "Dynamics.c.Rt": str(dynamics_c_path),
            "Dynamics.R": str(dynamics_r_path),
        },
        "checks": checks,
        "failures": failures,
        "claim_limit": (
            "source wiring guardrail only; runtime gates still must prove Psi* "
            "fields and controlled writes are finite and coherent on P100 curved cases"
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="repository root",
    )
    parser.add_argument("--out", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = audit(args.root)
    text = json.dumps(summary, indent=2, sort_keys=True)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text)
    return 0 if summary["status"].startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
