"""Tiny-grid bulk h-population lifecycle gate.

This script tests the first real producer-consumer loop for the clean
phase-field solver, still without Taichi:

    C -> h_eq initialization
      -> C=sum(h_src)
      -> grad C and interface normal
      -> F_phi
      -> h collision/source
      -> periodic pull streaming
      -> C_next=sum(h_dst)

No wall, wetting, pressure force, or curved geometry is included. The purpose is
to prove that the clean route has an explicit h-population lifecycle and a mass
ledger before moving the same kernels to Taichi.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from phasefield_algebra_gate import CS2, d3q27_lattice, fphi_tclb_like, heq_linear


@dataclass
class StepMetrics:
    step: int
    mass: float
    mass_drift: float
    c_min: float
    c_max: float
    c_oob_low: int
    c_oob_high: int
    h_min: float
    h_max: float
    fphi_sum_max_abs: float
    grad_max: float
    normal_ambiguous_count: int
    nonfinite_count: int


def initialize_droplet(nx: int, ny: int, nz: int, radius: float, width: float) -> np.ndarray:
    x = np.arange(nx, dtype=np.float64)[:, None, None]
    y = np.arange(ny, dtype=np.float64)[None, :, None]
    z = np.arange(nz, dtype=np.float64)[None, None, :]
    cx = 0.5 * (nx - 1)
    cy = 0.5 * (ny - 1)
    cz = 0.5 * (nz - 1)
    r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2)
    return 0.5 * (1.0 - np.tanh(2.0 * (r - radius) / width))


def initialize_h(c: np.ndarray, e: np.ndarray, w: np.ndarray) -> np.ndarray:
    q = e.shape[0]
    h = np.empty((q,) + c.shape, dtype=np.float64)
    u = np.zeros(3, dtype=np.float64)
    for i in range(q):
        # u=0, so heq is w_i*C. Keep the call structure aligned with the
        # algebra gate for future velocity-bearing tests.
        h[i] = w[i] * c
    return h


def phase_from_h(h: np.ndarray) -> np.ndarray:
    return np.sum(h, axis=0)


def central_grad_periodic(c: np.ndarray) -> np.ndarray:
    grad = np.empty((3,) + c.shape, dtype=np.float64)
    grad[0] = 0.5 * (np.roll(c, -1, axis=0) - np.roll(c, 1, axis=0))
    grad[1] = 0.5 * (np.roll(c, -1, axis=1) - np.roll(c, 1, axis=1))
    grad[2] = 0.5 * (np.roll(c, -1, axis=2) - np.roll(c, 1, axis=2))
    return grad


def normals_from_grad(grad: np.ndarray, eps: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mag = np.sqrt(np.sum(grad * grad, axis=0))
    ambiguous = mag < eps
    normal = np.zeros_like(grad)
    normal[:, ~ambiguous] = grad[:, ~ambiguous] / mag[~ambiguous]
    return normal, mag, ambiguous


def collide_h(
    h: np.ndarray,
    c: np.ndarray,
    normal: np.ndarray,
    e: np.ndarray,
    w: np.ndarray,
    omega: float,
    interface_width: float,
    grad_eps: float,
) -> tuple[np.ndarray, float]:
    q = e.shape[0]
    out = np.empty_like(h)
    fphi_sum = np.zeros_like(c)
    u = np.zeros(3, dtype=np.float64)
    for i in range(q):
        heq_i = w[i] * c
        edotn = e[i, 0] * normal[0] + e[i, 1] * normal[1] + e[i, 2] * normal[2]
        tmp1 = (1.0 - 4.0 * (c - 0.5) * (c - 0.5)) / interface_width
        fphi_i = w[i] * tmp1 * edotn
        out[i] = h[i] - omega * (h[i] - heq_i + 0.5 * fphi_i) + fphi_i
        fphi_sum += fphi_i
    return out, float(np.max(np.abs(fphi_sum)))


def pull_stream_periodic(h_collide: np.ndarray, e: np.ndarray) -> np.ndarray:
    q = e.shape[0]
    out = np.empty_like(h_collide)
    for i in range(q):
        ex, ey, ez = (int(v) for v in e[i])
        out[i] = np.roll(h_collide[i], shift=(ex, ey, ez), axis=(0, 1, 2))
    return out


def metrics_for_step(
    step: int,
    c: np.ndarray,
    h: np.ndarray,
    mass0: float,
    fphi_sum_max_abs: float,
    grad_mag: np.ndarray,
    ambiguous: np.ndarray,
) -> StepMetrics:
    nonfinite_count = int(np.size(c) - np.count_nonzero(np.isfinite(c)))
    nonfinite_count += int(np.size(h) - np.count_nonzero(np.isfinite(h)))
    mass = float(np.sum(c))
    return StepMetrics(
        step=step,
        mass=mass,
        mass_drift=mass - mass0,
        c_min=float(np.min(c)),
        c_max=float(np.max(c)),
        c_oob_low=int(np.count_nonzero(c < -1.0e-12)),
        c_oob_high=int(np.count_nonzero(c > 1.0 + 1.0e-12)),
        h_min=float(np.min(h)),
        h_max=float(np.max(h)),
        fphi_sum_max_abs=fphi_sum_max_abs,
        grad_max=float(np.max(grad_mag)),
        normal_ambiguous_count=int(np.count_nonzero(ambiguous)),
        nonfinite_count=nonfinite_count,
    )


def write_csv(path: Path, rows: list[StepMetrics]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(asdict(rows[0]).keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("artifacts/stage18_taichi_phasefield_bulk_lifecycle_20260704"))
    parser.add_argument("--nx", type=int, default=24)
    parser.add_argument("--ny", type=int, default=24)
    parser.add_argument("--nz", type=int, default=24)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--radius", type=float, default=6.0)
    parser.add_argument("--width", type=float, default=4.0)
    parser.add_argument("--omega", type=float, default=1.0)
    parser.add_argument("--grad-eps", type=float, default=1.0e-12)
    parser.add_argument("--mass-tol", type=float, default=1.0e-10)
    args = parser.parse_args()

    e, w = d3q27_lattice()
    c0 = initialize_droplet(args.nx, args.ny, args.nz, args.radius, args.width)
    h = initialize_h(c0, e, w)
    mass0 = float(np.sum(c0))

    rows: list[StepMetrics] = []
    c = phase_from_h(h)
    grad = central_grad_periodic(c)
    normal, grad_mag, ambiguous = normals_from_grad(grad, args.grad_eps)
    rows.append(metrics_for_step(0, c, h, mass0, 0.0, grad_mag, ambiguous))

    for step in range(1, args.steps + 1):
        c = phase_from_h(h)
        grad = central_grad_periodic(c)
        normal, grad_mag, ambiguous = normals_from_grad(grad, args.grad_eps)
        h_collide, fphi_sum_max_abs = collide_h(h, c, normal, e, w, args.omega, args.width, args.grad_eps)
        h = pull_stream_periodic(h_collide, e)
        c_next = phase_from_h(h)
        grad_next = central_grad_periodic(c_next)
        _, grad_mag_next, ambiguous_next = normals_from_grad(grad_next, args.grad_eps)
        rows.append(metrics_for_step(step, c_next, h, mass0, fphi_sum_max_abs, grad_mag_next, ambiguous_next))

    final = rows[-1]
    gate_pass = (
        final.nonfinite_count == 0
        and max(abs(row.mass_drift) for row in rows) <= args.mass_tol
        and all(row.c_oob_low == 0 and row.c_oob_high == 0 for row in rows)
    )

    args.out.mkdir(parents=True, exist_ok=True)
    write_csv(args.out / "step_metrics.csv", rows)
    report = {
        "status": "pass" if gate_pass else "fail",
        "claim_limit": "bulk h-population lifecycle gate only; no wall, no wetting, no force, no Taichi GPU",
        "grid": [args.nx, args.ny, args.nz],
        "steps": args.steps,
        "radius": args.radius,
        "width": args.width,
        "omega": args.omega,
        "mass_tolerance": args.mass_tol,
        "mass0": mass0,
        "max_abs_mass_drift": max(abs(row.mass_drift) for row in rows),
        "final": asdict(final),
    }
    (args.out / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "steps": args.steps, "out": str(args.out)}, indent=2))
    return 0 if gate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())

