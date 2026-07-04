"""Offline algebra gate for the clean phase-field LBM route.

This script is deliberately independent of Taichi. It verifies the population
moments that must be true before the same equations are moved into GPU kernels.

The gate checks three phase-source variants:

    mode 0: legacy TCLB-like source
    mode 1: normalized conservative Allen-Cahn source
    mode 2: moment-corrected conservative Allen-Cahn source

For the D3Q27 lattice, a source proportional to w_i (e_i . n) has zero zeroth
moment and first moment cs2 * scale * n by isotropy.  The book-derived
moment-corrected mode divides by cs2 so that the first moment is scale*n.
The script records these identities, the h_eq moments, and the moment effect
of the common source update

    h_post = h - omega * (h - h_eq + 0.5 * F_phi) + F_phi

This is not a contact-angle validation and not a final physics model.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np


CS2 = 1.0 / 3.0


@dataclass(frozen=True)
class Case:
    name: str
    c: float
    normal: tuple[float, float, float]
    velocity: tuple[float, float, float]
    omega: float
    interface_width: float


@dataclass
class CaseMetrics:
    name: str
    c: float
    source_mode: int
    omega: float
    interface_width: float
    source_scale: float
    heq_sum: float
    heq_sum_err: float
    heq_first_x: float
    heq_first_y: float
    heq_first_z: float
    heq_first_err: float
    fphi_sum: float
    fphi_sum_abs: float
    fphi_first_x: float
    fphi_first_y: float
    fphi_first_z: float
    fphi_first_err: float
    fphi_second_trace: float
    hpost_sum: float
    hpost_sum_err: float
    hpost_first_x: float
    hpost_first_y: float
    hpost_first_z: float
    hpost_first_expected_x: float
    hpost_first_expected_y: float
    hpost_first_expected_z: float
    hpost_first_err: float
    pass_gate: bool


def d3q27_lattice() -> tuple[np.ndarray, np.ndarray]:
    velocities = []
    weights = []
    for x in (-1, 0, 1):
        for y in (-1, 0, 1):
            for z in (-1, 0, 1):
                s = abs(x) + abs(y) + abs(z)
                if s == 0:
                    w = 8.0 / 27.0
                elif s == 1:
                    w = 2.0 / 27.0
                elif s == 2:
                    w = 1.0 / 54.0
                else:
                    w = 1.0 / 216.0
                velocities.append((x, y, z))
                weights.append(w)
    return np.asarray(velocities, dtype=np.float64), np.asarray(weights, dtype=np.float64)


def normalize(v: Iterable[float]) -> np.ndarray:
    a = np.asarray(tuple(v), dtype=np.float64)
    mag = float(np.linalg.norm(a))
    if mag == 0.0:
        raise ValueError("normal vector must be nonzero")
    return a / mag


def heq_linear(c: float, velocity: np.ndarray, e: np.ndarray, w: np.ndarray) -> np.ndarray:
    eu = e @ velocity
    return w * c * (1.0 + eu / CS2)


def source_scale(c: float, interface_width: float, source_mode: int) -> float:
    c_bounded = min(1.0, max(0.0, c))
    if source_mode >= 1:
        return 4.0 * c_bounded * (1.0 - c_bounded) / interface_width
    return (1.0 - 4.0 * (c - 0.5) * (c - 0.5)) / interface_width


def fphi_source(c: float, normal: np.ndarray, interface_width: float, e: np.ndarray, w: np.ndarray, source_mode: int) -> np.ndarray:
    scale = source_scale(c, interface_width, source_mode)
    source = w * scale * (e @ normal)
    if source_mode >= 2:
        source = source / CS2
    return source


def first_moment(pop: np.ndarray, e: np.ndarray) -> np.ndarray:
    return pop @ e


def second_moment(pop: np.ndarray, e: np.ndarray) -> np.ndarray:
    out = np.zeros((3, 3), dtype=np.float64)
    for i in range(e.shape[0]):
        out += pop[i] * np.outer(e[i], e[i])
    return out


def analyze_case(case: Case, e: np.ndarray, w: np.ndarray, tol: float, source_mode: int) -> CaseMetrics:
    n = normalize(case.normal)
    u = np.asarray(case.velocity, dtype=np.float64)
    heq = heq_linear(case.c, u, e, w)
    fphi = fphi_source(case.c, n, case.interface_width, e, w, source_mode)

    # Start from equilibrium so the one-cell algebra gate is not contaminated by
    # an arbitrary nonequilibrium initial h. Streaming is tested in the next gate.
    h_pre = heq.copy()
    h_post = h_pre - case.omega * (h_pre - heq + 0.5 * fphi) + fphi

    heq_sum = float(np.sum(heq))
    heq_first = first_moment(heq, e)
    heq_first_expected = case.c * u

    fphi_sum = float(np.sum(fphi))
    fphi_first = first_moment(fphi, e)
    scale = source_scale(case.c, case.interface_width, source_mode)
    fphi_first_expected = CS2 * scale * n
    if source_mode >= 2:
        fphi_first_expected = scale * n
    fphi_second = second_moment(fphi, e)

    hpost_sum = float(np.sum(h_post))
    hpost_first = first_moment(h_post, e)
    hpost_first_expected = heq_first_expected + (1.0 - 0.5 * case.omega) * fphi_first_expected

    heq_first_err = float(np.linalg.norm(heq_first - heq_first_expected))
    fphi_first_err = float(np.linalg.norm(fphi_first - fphi_first_expected))
    hpost_first_err = float(np.linalg.norm(hpost_first - hpost_first_expected))
    heq_sum_err = abs(heq_sum - case.c)
    hpost_sum_err = abs(hpost_sum - case.c)
    pass_gate = (
        heq_sum_err <= tol
        and heq_first_err <= tol
        and abs(fphi_sum) <= tol
        and fphi_first_err <= tol
        and hpost_sum_err <= tol
        and hpost_first_err <= tol
    )

    return CaseMetrics(
        name=case.name,
        c=case.c,
        source_mode=source_mode,
        omega=case.omega,
        interface_width=case.interface_width,
        source_scale=scale,
        heq_sum=heq_sum,
        heq_sum_err=heq_sum_err,
        heq_first_x=float(heq_first[0]),
        heq_first_y=float(heq_first[1]),
        heq_first_z=float(heq_first[2]),
        heq_first_err=heq_first_err,
        fphi_sum=fphi_sum,
        fphi_sum_abs=abs(fphi_sum),
        fphi_first_x=float(fphi_first[0]),
        fphi_first_y=float(fphi_first[1]),
        fphi_first_z=float(fphi_first[2]),
        fphi_first_err=fphi_first_err,
        fphi_second_trace=float(np.trace(fphi_second)),
        hpost_sum=hpost_sum,
        hpost_sum_err=hpost_sum_err,
        hpost_first_x=float(hpost_first[0]),
        hpost_first_y=float(hpost_first[1]),
        hpost_first_z=float(hpost_first[2]),
        hpost_first_expected_x=float(hpost_first_expected[0]),
        hpost_first_expected_y=float(hpost_first_expected[1]),
        hpost_first_expected_z=float(hpost_first_expected[2]),
        hpost_first_err=hpost_first_err,
        pass_gate=pass_gate,
    )


def lattice_metrics(e: np.ndarray, w: np.ndarray) -> dict[str, object]:
    m0 = float(np.sum(w))
    m1 = w @ e
    m2 = second_moment(w, e)
    m4_xxxx = float(np.sum(w * e[:, 0] ** 4))
    m4_xxyy = float(np.sum(w * e[:, 0] ** 2 * e[:, 1] ** 2))
    return {
        "q": int(e.shape[0]),
        "weight_sum": m0,
        "first_moment": m1.tolist(),
        "second_moment": m2.tolist(),
        "second_moment_expected_diag": [CS2, CS2, CS2],
        "fourth_xxxx": m4_xxxx,
        "fourth_xxyy": m4_xxyy,
        "fourth_expected_xxxx": 3.0 * CS2 * CS2,
        "fourth_expected_xxyy": CS2 * CS2,
    }


def default_cases() -> list[Case]:
    return [
        Case("bulk_mid_x", 0.5, (1.0, 0.0, 0.0), (0.0, 0.0, 0.0), 1.0, 4.0),
        Case("bulk_mid_diag", 0.5, (1.0, 1.0, 1.0), (0.01, -0.02, 0.015), 0.8, 4.0),
        Case("liquid_side_y", 0.9, (0.0, 1.0, 0.0), (0.015, 0.0, -0.01), 1.2, 4.0),
        Case("gas_side_z", 0.1, (0.0, 0.0, 1.0), (-0.01, 0.02, 0.0), 1.6, 4.0),
        Case("near_bound_low", 1.0e-6, (1.0, -2.0, 0.5), (0.0, 0.0, 0.0), 1.0, 4.0),
        Case("near_bound_high", 1.0 - 1.0e-6, (-0.5, 1.0, 2.0), (0.0, 0.0, 0.0), 1.0, 4.0),
    ]


def write_csv(path: Path, rows: list[CaseMetrics]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(asdict(rows[0]).keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("artifacts/stage18_taichi_phasefield_algebra_20260704"))
    parser.add_argument("--tol", type=float, default=1.0e-12)
    parser.add_argument("--source-mode", type=int, default=2, help="0 legacy, 1 normalized CAC, 2 moment-corrected CAC")
    args = parser.parse_args()

    e, w = d3q27_lattice()
    rows = [analyze_case(case, e, w, args.tol, args.source_mode) for case in default_cases()]
    gate_pass = all(row.pass_gate for row in rows)

    args.out.mkdir(parents=True, exist_ok=True)
    write_csv(args.out / "case_moments.csv", rows)

    report = {
        "status": "pass" if gate_pass else "fail",
        "claim_limit": "offline algebra gate only; not a Taichi run and not contact-angle validation",
        "model_candidate": "D3Q27 conservative Allen-Cahn h population source moment gate",
        "source_mode": args.source_mode,
        "tolerance": args.tol,
        "cs2": CS2,
        "lattice": lattice_metrics(e, w),
        "cases": [asdict(row) for row in rows],
    }
    (args.out / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps({"status": report["status"], "cases": len(rows), "out": str(args.out)}, indent=2))
    return 0 if gate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
