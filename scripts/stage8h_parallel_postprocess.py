#!/usr/bin/env python3
"""Parallel CPU postprocess pool for Stage8h solver outputs.

This script does not run TCLB and does not enable any write-mode physics. It
only consumes completed Stage8h shadow solver directories, runs the finiteness
gate, flat-wall gate when applicable, and Stage8h attribution in parallel.
Status: runtime_sanity / exploratory_not_validation.
"""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any


STATUS = "runtime_sanity"

DEFAULT_FINITE_ARRAYS = ",".join(
    [
        "PhaseField",
        "U",
        "P",
        "Rho",
        "BOUNDARY",
        "WallStage8GradMode",
        "WallStage8ActiveWeight",
        "WallStage8NormalGradRaw",
        "WallStage8NormalGradTarget",
        "WallStage8ContactResidual",
        "WallStage8TangentGradMag",
        "WallStage8TargetCos",
        "WallStage8GradWriteDeltaMag",
        "WallStage8LimiterReason",
        "WallStage8LocalWallAngle",
        "WallStage8FluidWallAngle",
        "WallStage8FluidWallDataCount",
        "WallStage8GradCandidateUse",
        "WallStage8NormalAgreement",
        "WallStage8UsedGeomNormal",
        "WallStage8TanCoeffLocal",
        "WallStage8ThetaLocal",
        "WallStage8PhaseC",
        "WallStage8GradMagRaw",
        "WallStage8TangentGradRaw",
        "WallStage8TargetNormalGrad",
        "WallStage8NormalDeltaRaw",
        "WallStage8NormalDeltaLimited",
        "WallStage8VectorDeltaRawMag",
        "WallStage8VectorDeltaLimitedMag",
        "WallStage8NormalLimiterHit",
        "WallStage8VectorLimiterHit",
        "WallStage8LimiterRatio",
        "WallStage8RegionTag",
        "WallStage8SphereRadialDot",
        "WallStage8ContactBandTag",
        "WallStage8eDnRaw",
        "WallStage8eDnTry",
        "WallStage8eDnLimited",
        "WallStage8eAbsCap",
        "WallStage8eRatioCap",
        "WallStage8eEffectiveCap",
        "WallStage8eCapSource",
        "WallStage8eCapDemandRatio",
        "WallStage8eNormalRawAbs",
        "WallStage8eTargetNormalAbs",
        "WallStage8eTargetMinusRawAbs",
        "WallStage8eSmoothWeightC",
        "WallStage8eSmoothWeightG",
        "WallStage8eSmoothWeightT",
        "WallStage8eSmoothWeightTotal",
        "WallStage8eTanCoeffTimesTangent",
        "WallStage8eLimiterClass",
        "WallStage8eWallProfileConflict",
        "WallStage8gMode",
        "WallStage8gScaleRawNormal",
        "WallStage8gScaleTarget",
        "WallStage8gScaleTangent",
        "WallStage8gScaleFloor",
        "WallStage8gEffectiveScale",
        "WallStage8gTanRaw",
        "WallStage8gTanEff",
        "WallStage8gRegularizationRatio",
        "WallStage8gCapSource",
        "WallStage8gCapDemandRatio",
        "WallStage8gProfileTargetMismatch",
        "WallStage8gProfileConflictSign",
        "WallStage8gWriteAllowedFlag",
        "WallStage8hMode",
        "WallStage8hActualCos",
        "WallStage8hTargetCos",
        "WallStage8hResidualCos",
        "WallStage8hDnTanRaw",
        "WallStage8hDnCosRaw",
        "WallStage8hDnRelaxed",
        "WallStage8hBetaRelaxation",
        "WallStage8hBetaSource",
        "WallStage8hProfileNormal",
        "WallStage8hProfileTargetMismatch",
        "WallStage8hProfileConsistencyWeight",
        "WallStage8hCandidateDemandRatio",
        "WallStage8hCandidateNormalDelta",
        "WallStage8hLimiterEquivalent",
        "WallStage8hCosToTanRatio",
        "WallStage8hEffectiveCap",
        "WallStage8hWriteAllowedFlag",
    ]
)

RAW_SUFFIXES = (".vti", ".pvti", ".pri", ".vtk")


@dataclass(frozen=True)
class WorkerConfig:
    run_root: Path
    case_kind: str
    finiteness: Path
    cap_post: Path
    attribution: Path
    finite_arrays: str
    delete_raw_after_analysis: bool
    force: bool
    strict_flat_gate: bool
    python: str


def read_rc(path: Path) -> int | None:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def has_raw_fields(case_dir: Path) -> bool:
    output = case_dir / "output"
    if not output.is_dir():
        return False
    for suffix in RAW_SUFFIXES:
        if next(output.glob(f"*{suffix}"), None) is not None:
            return True
    return False


def atomic_lock(lock_dir: Path) -> bool:
    try:
        lock_dir.mkdir()
        return True
    except FileExistsError:
        return False


def run_subprocess(cmd: list[str], stdout_path: Path, stderr_path: Path) -> int:
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    with stdout_path.open("w", encoding="utf-8", errors="replace") as out, stderr_path.open(
        "w", encoding="utf-8", errors="replace"
    ) as err:
        proc = subprocess.run(cmd, stdout=out, stderr=err, check=False)
    return int(proc.returncode)


def delete_raw_fields(case_dir: Path) -> int:
    deleted = 0
    for path in case_dir.rglob("*"):
        if path.is_file() and path.suffix in RAW_SUFFIXES:
            path.unlink()
            deleted += 1
    return deleted


def case_dirs(run_root: Path) -> list[Path]:
    if not run_root.is_dir():
        return []
    return sorted(
        p
        for p in run_root.iterdir()
        if p.is_dir()
        and not p.name.startswith(".")
        and not p.name.startswith("analysis_")
        and p.name not in {"provenance"}
    )


def eligible_cases(run_root: Path, *, force: bool) -> list[Path]:
    out: list[Path] = []
    for case_dir in case_dirs(run_root):
        if (case_dir / ".stage8h.lock").exists() or (case_dir / ".stage8h.post.lock").exists():
            continue
        if read_rc(case_dir / "run.returncode") != 0:
            continue
        if (case_dir / "run.done").exists() and not force:
            continue
        if not has_raw_fields(case_dir):
            if (case_dir / "analysis_stage8h_attribution" / "stage8h_shadow_attribution_summary.json").exists():
                (case_dir / "run.done").touch()
            continue
        out.append(case_dir)
    return out


def process_case(case_dir: Path, cfg: WorkerConfig) -> dict[str, Any]:
    lock_dir = case_dir / ".stage8h.post.lock"
    result: dict[str, Any] = {
        "case": case_dir.name,
        "status": STATUS,
        "claim_limit": "runtime_sanity / exploratory_not_validation only",
        "processed": False,
        "error": "",
        "deleted_raw_count": 0,
    }
    if not atomic_lock(lock_dir):
        result["error"] = "postprocess lock already exists"
        return result
    try:
        if (case_dir / ".stage8h.lock").exists():
            result["error"] = "solver queue lock still exists"
            return result
        if read_rc(case_dir / "run.returncode") != 0:
            result["error"] = "missing or nonzero run.returncode"
            return result
        if not has_raw_fields(case_dir) and not cfg.force:
            if (case_dir / "analysis_stage8h_attribution" / "stage8h_shadow_attribution_summary.json").exists():
                (case_dir / "run.done").touch()
                result["processed"] = True
            else:
                result["error"] = "no raw VTI/PVTI/PRI/VTK fields to process"
            return result

        finite_json = case_dir / "analysis_finiteness_gate" / "finiteness_gate_summary.json"
        if cfg.force or not finite_json.exists():
            out_dir = case_dir / "analysis_finiteness_gate"
            out_dir.mkdir(parents=True, exist_ok=True)
            cmd = [
                cfg.python,
                str(cfg.finiteness),
                "--root",
                str(case_dir),
                "--out-dir",
                str(out_dir),
                "--arrays",
                cfg.finite_arrays,
            ]
            rc = run_subprocess(
                cmd,
                case_dir / "analysis_finiteness_gate_stdout.log",
                case_dir / "analysis_finiteness_gate_stderr.log",
            )
            (case_dir / "analysis_finiteness_gate.returncode").write_text(f"{rc}\n", encoding="utf-8")
            if rc != 0:
                result["error"] = f"finiteness gate rc={rc}"
                return result

        if cfg.case_kind == "flat":
            flat_json = case_dir / "analysis_flat_cap_gate" / "flat_wall_cap_gate_summary.json"
            if cfg.force or not flat_json.exists():
                out_dir = case_dir / "analysis_flat_cap_gate"
                out_dir.mkdir(parents=True, exist_ok=True)
                cmd = [
                    cfg.python,
                    str(cfg.cap_post),
                    "--run-root",
                    str(cfg.run_root),
                    "--case-root",
                    str(case_dir),
                    "--out-dir",
                    str(out_dir),
                ]
                rc = run_subprocess(
                    cmd,
                    case_dir / "analysis_flat_cap_gate_stdout.log",
                    case_dir / "analysis_flat_cap_gate_stderr.log",
                )
                (case_dir / "analysis_flat_cap_gate.returncode").write_text(f"{rc}\n", encoding="utf-8")
                if rc != 0 and cfg.strict_flat_gate:
                    result["error"] = f"flat gate rc={rc}"
                    return result

        attr_json = case_dir / "analysis_stage8h_attribution" / "stage8h_shadow_attribution_summary.json"
        if cfg.force or not attr_json.exists():
            out_dir = case_dir / "analysis_stage8h_attribution"
            out_dir.mkdir(parents=True, exist_ok=True)
            cmd = [
                cfg.python,
                str(cfg.attribution),
                "--case-root",
                str(case_dir),
                "--out-dir",
                str(out_dir),
            ]
            rc = run_subprocess(
                cmd,
                case_dir / "analysis_stage8h_attribution_stdout.log",
                case_dir / "analysis_stage8h_attribution_stderr.log",
            )
            (case_dir / "analysis_stage8h_attribution.returncode").write_text(f"{rc}\n", encoding="utf-8")
            if rc != 0:
                result["error"] = f"stage8h attribution rc={rc}"
                return result

        (case_dir / "run.done").touch()
        if cfg.delete_raw_after_analysis:
            result["deleted_raw_count"] = delete_raw_fields(case_dir)
        (case_dir / "stage8h_parallel_postprocess.returncode").write_text("0\n", encoding="utf-8")
        result["processed"] = True
        return result
    except Exception as exc:  # pragma: no cover - diagnostic path
        result["error"] = f"{type(exc).__name__}: {exc}"
        (case_dir / "stage8h_parallel_postprocess.traceback.txt").write_text(
            traceback.format_exc(), encoding="utf-8"
        )
        return result
    finally:
        if result.get("error"):
            (case_dir / "stage8h_parallel_postprocess.returncode").write_text("1\n", encoding="utf-8")
        shutil.rmtree(lock_dir, ignore_errors=True)


def count_done(run_root: Path) -> int:
    return sum(1 for p in case_dirs(run_root) if (p / "run.done").exists())


def count_solver_done(run_root: Path) -> int:
    return sum(1 for p in case_dirs(run_root) if read_rc(p / "run.returncode") == 0)


def run_round(cases: list[Path], cfg: WorkerConfig, workers: int) -> list[dict[str, Any]]:
    if not cases:
        return []
    results: list[dict[str, Any]] = []
    with futures.ThreadPoolExecutor(max_workers=workers) as pool:
        submitted = {pool.submit(process_case, case_dir, cfg): case_dir for case_dir in cases}
        for fut in futures.as_completed(submitted):
            try:
                results.append(fut.result())
            except Exception as exc:  # pragma: no cover - defensive
                results.append(
                    {
                        "case": submitted[fut].name,
                        "status": STATUS,
                        "processed": False,
                        "error": f"worker exception: {type(exc).__name__}: {exc}",
                    }
                )
    return results


def write_status(run_root: Path, payload: dict[str, Any]) -> None:
    (run_root / "stage8h_parallel_postprocess_status.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--case-kind", choices=["flat", "sphere"], required=True)
    parser.add_argument("--workers", type=int, default=min(max((os.cpu_count() or 4) // 2, 1), 20))
    parser.add_argument("--finiteness", type=Path, default=Path("/tmp/tclb_vti_finiteness_gate.py"))
    parser.add_argument("--cap-post", type=Path, default=Path("/tmp/flat_wall_cap_gate_postprocess.py"))
    parser.add_argument("--attribution", type=Path, default=Path("/tmp/stage8h_shadow_attribution.py"))
    parser.add_argument("--finite-arrays", default=os.environ.get("FINITE_ARRAYS", DEFAULT_FINITE_ARRAYS))
    parser.add_argument("--python", default=sys.executable or "python3")
    parser.add_argument("--delete-raw-after-analysis", type=int, default=1)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--strict-flat-gate", action="store_true")
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--expected-count", type=int, default=0)
    parser.add_argument("--poll-seconds", type=float, default=15.0)
    parser.add_argument("--max-idle-polls", type=int, default=0)
    args = parser.parse_args()

    workers = max(1, int(args.workers))
    cfg = WorkerConfig(
        run_root=args.run_root,
        case_kind=args.case_kind,
        finiteness=args.finiteness,
        cap_post=args.cap_post,
        attribution=args.attribution,
        finite_arrays=args.finite_arrays,
        delete_raw_after_analysis=bool(args.delete_raw_after_analysis),
        force=bool(args.force),
        strict_flat_gate=bool(args.strict_flat_gate),
        python=args.python,
    )

    args.run_root.mkdir(parents=True, exist_ok=True)
    all_results: list[dict[str, Any]] = []
    idle_polls = 0
    started = time.time()
    while True:
        pending = eligible_cases(args.run_root, force=bool(args.force))
        results = run_round(pending, cfg, workers)
        all_results.extend(results)
        processed = sum(1 for r in results if r.get("processed"))
        errors = [r for r in results if r.get("error")]
        solver_done = count_solver_done(args.run_root)
        done = count_done(args.run_root)
        payload = {
            "status": STATUS,
            "claim_limit": "runtime_sanity / exploratory_not_validation only",
            "run_root": str(args.run_root),
            "case_kind": args.case_kind,
            "workers": workers,
            "watch": bool(args.watch),
            "expected_count": int(args.expected_count),
            "solver_done_count": solver_done,
            "run_done_count": done,
            "last_round_pending_count": len(pending),
            "last_round_processed_count": processed,
            "last_round_error_count": len(errors),
            "elapsed_seconds": round(time.time() - started, 3),
            "last_round_errors": errors[:20],
        }
        write_status(args.run_root, payload)
        print(json.dumps(payload, ensure_ascii=False), flush=True)

        if errors:
            return 2
        if args.expected_count and done >= args.expected_count:
            break
        if not args.watch:
            break
        if processed == 0 and not pending:
            idle_polls += 1
        else:
            idle_polls = 0
        if args.max_idle_polls and idle_polls >= args.max_idle_polls:
            break
        time.sleep(max(1.0, float(args.poll_seconds)))

    final_payload = {
        "status": STATUS,
        "claim_limit": "runtime_sanity / exploratory_not_validation only",
        "run_root": str(args.run_root),
        "case_kind": args.case_kind,
        "workers": workers,
        "processed_total": sum(1 for r in all_results if r.get("processed")),
        "error_total": sum(1 for r in all_results if r.get("error")),
        "solver_done_count": count_solver_done(args.run_root),
        "run_done_count": count_done(args.run_root),
        "elapsed_seconds": round(time.time() - started, 3),
    }
    write_status(args.run_root, final_payload)
    print(json.dumps(final_payload, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
