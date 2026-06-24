#!/usr/bin/env python3
"""Static source audit for Stage17B diffuse-solid shadow-only wiring.

This gate proves only source-level guardrails:

* Stage17B lives in an independent TCLB snapshot.
* The new diffuse-solid path exports Psi*/NearWall* diagnostics.
* Stage17B B2 remains shadow-only and does not assign WallGhost or PhaseF.
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
    near_wall_write = function_block(dynamics_c, "stage17b_write_near_wall_force_shadow")
    bgk = cuda_function_block(dynamics_c, "CollisionBGK")
    mrt = cuda_function_block(dynamics_c, "CollisionMRT")

    psi_fields = [
        "PsiSolid",
        "PsiGradMag",
        "PsiNormalX",
        "PsiNormalY",
        "PsiNormalZ",
        "PsiWallGhost",
        "PsiThetaImplied",
        "PsiJaggedness",
        "PsiWriteAllowedFlag",
        "PsiNormalAmbiguityFlag",
    ]
    near_wall_fields = [
        "NearWallForceMag",
        "NearWallGradPhiMag",
        "NearWallForceOverRhoShadow",
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
                'AddSetting(name="Stage17BPsiEps", default=1.25',
                'AddSetting(name="Stage17BWriteBand", default=1.8',
                'AddSetting(name="Stage17BGradPsiMin", default=1e-4',
                'AddSetting(name="Stage17BShadowThetaDeg", default=-1.0',
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
                "PsiWallGhost",
                "PsiThetaImplied",
                "PsiJaggedness",
                "PsiWriteAllowedFlag",
                "PsiNormalAmbiguityFlag",
            ]
        )
        and 'AddQuantity(name="PsiNormal", unit=1, vector=T)' in dynamics_r,
        "near_wall_fields_registered": all(
            f'AddField("{field}"' in dynamics_r and f'AddQuantity(name="{field}"' in dynamics_r
            for field in near_wall_fields
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
        "stage17b_compute_shadow_present": all(
            token in compute_shadow
            for token in [
                "stage17b_diffuse_solid_indicator",
                "stage17b_diffuse_solid_grad_analytic",
                "stage13_compute_geometric_tangent_raw",
                "Stage17BShadowThetaDeg",
                "PsiWallGhost = stage13_clamp_phase_value",
                "PsiWriteAllowedFlag = shadow_ready ? 1.0 : 0.0",
                "Stage17BWriteMode > 0.5",
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
        "stage17b_write_mode_disables_readiness": contains(
            compute_shadow,
            r"if\s*\(\s*Stage17BWriteMode\s*>\s*0\.5\s*\)\s*\{[^}]*"
            r"PsiWriteAllowedFlag\s*=\s*0\.0\s*;",
        ),
        "claim_limit_comment_present": (
            "output-only in B2" in dynamics_r
            and "Never write WallGhost or PhaseF" in boundary
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
            "source wiring guardrail only; B2 runtime still must prove Psi* fields "
            "are finite and coherent on P100 curved shadow cases"
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
