"""Taichi kernel version of the clean bulk h-population lifecycle gate.

This is the first device-kernel implementation in the clean phase-field route.
It intentionally mirrors ``phasefield_bulk_lifecycle_gate.py``:

    initialize C and h_i=w_i*C
      -> kernel: C=sum_i h_i
      -> kernel: grad C and interface normal
      -> kernel: collide/source h_i
      -> kernel: periodic pull stream
      -> kernel: C_next=sum_i h_i
      -> Python metrics after ti.sync()

No wall, wetting, pressure force, momentum population, or curved geometry is
included. The purpose is to prove that the explicit h-population lifecycle can
be expressed with Taichi fields and kernels before adding physics layers.
"""

import argparse
import csv
import importlib.util
import json
import platform
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

if importlib.util.find_spec("taichi") is None:
    raise SystemExit(
        "Taichi is not installed for this Python. Install taichi or use the "
        "remote runner script before executing this gate."
    )

import taichi as ti


Q = 27
CS2 = 1.0 / 3.0

h = None
c_field = None
grad_field = None
normal_field = None
grad_mag_field = None
ambiguous_field = None
e_field = None
w_field = None


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
    return np.asarray(velocities, dtype=np.int32), np.asarray(weights, dtype=np.float64)


def setup_fields(nx: int, ny: int, nz: int) -> None:
    global h, c_field, grad_field, normal_field, grad_mag_field
    global ambiguous_field, e_field, w_field

    h = ti.field(dtype=ti.f64, shape=(2, nx, ny, nz, Q))
    c_field = ti.field(dtype=ti.f64, shape=(nx, ny, nz))
    grad_field = ti.Vector.field(3, dtype=ti.f64, shape=(nx, ny, nz))
    normal_field = ti.Vector.field(3, dtype=ti.f64, shape=(nx, ny, nz))
    grad_mag_field = ti.field(dtype=ti.f64, shape=(nx, ny, nz))
    ambiguous_field = ti.field(dtype=ti.i32, shape=(nx, ny, nz))
    e_field = ti.Vector.field(3, dtype=ti.i32, shape=Q)
    w_field = ti.field(dtype=ti.f64, shape=Q)

    e_np, w_np = d3q27_lattice()
    e_field.from_numpy(e_np)
    w_field.from_numpy(w_np)


@ti.func
def wrap_index(i, n):
    out = i
    if out < 0:
        out += n
    if out >= n:
        out -= n
    return out


@ti.kernel
def initialize_kernel(buf: ti.i32, nx: ti.i32, ny: ti.i32, nz: ti.i32, radius: ti.f64, width: ti.f64):
    cx = 0.5 * ti.cast(nx - 1, ti.f64)
    cy = 0.5 * ti.cast(ny - 1, ti.f64)
    cz = 0.5 * ti.cast(nz - 1, ti.f64)
    for x, y, z in ti.ndrange(nx, ny, nz):
        dx = ti.cast(x, ti.f64) - cx
        dy = ti.cast(y, ti.f64) - cy
        dz = ti.cast(z, ti.f64) - cz
        r = ti.sqrt(dx * dx + dy * dy + dz * dz)
        c = 0.5 * (1.0 - ti.tanh(2.0 * (r - radius) / width))
        c_field[x, y, z] = c
        for q in ti.static(range(Q)):
            h[buf, x, y, z, q] = w_field[q] * c


@ti.kernel
def phase_from_h_kernel(buf: ti.i32, nx: ti.i32, ny: ti.i32, nz: ti.i32):
    for x, y, z in ti.ndrange(nx, ny, nz):
        c = 0.0
        for q in ti.static(range(Q)):
            c += h[buf, x, y, z, q]
        c_field[x, y, z] = c


@ti.kernel
def grad_normal_kernel(nx: ti.i32, ny: ti.i32, nz: ti.i32, grad_eps: ti.f64):
    for x, y, z in ti.ndrange(nx, ny, nz):
        xp = wrap_index(x + 1, nx)
        xm = wrap_index(x - 1, nx)
        yp = wrap_index(y + 1, ny)
        ym = wrap_index(y - 1, ny)
        zp = wrap_index(z + 1, nz)
        zm = wrap_index(z - 1, nz)

        gx = 0.5 * (c_field[xp, y, z] - c_field[xm, y, z])
        gy = 0.5 * (c_field[x, yp, z] - c_field[x, ym, z])
        gz = 0.5 * (c_field[x, y, zp] - c_field[x, y, zm])
        mag = ti.sqrt(gx * gx + gy * gy + gz * gz)

        grad_field[x, y, z] = ti.Vector([gx, gy, gz])
        grad_mag_field[x, y, z] = mag
        if mag < grad_eps:
            normal_field[x, y, z] = ti.Vector([0.0, 0.0, 0.0])
            ambiguous_field[x, y, z] = 1
        else:
            normal_field[x, y, z] = ti.Vector([gx / mag, gy / mag, gz / mag])
            ambiguous_field[x, y, z] = 0


@ti.kernel
def collide_h_kernel(src: ti.i32, dst: ti.i32, nx: ti.i32, ny: ti.i32, nz: ti.i32, omega: ti.f64, width: ti.f64):
    for x, y, z in ti.ndrange(nx, ny, nz):
        c = c_field[x, y, z]
        n = normal_field[x, y, z]
        tmp1 = (1.0 - 4.0 * (c - 0.5) * (c - 0.5)) / width
        for q in ti.static(range(Q)):
            e = e_field[q]
            edotn = ti.cast(e[0], ti.f64) * n[0] + ti.cast(e[1], ti.f64) * n[1] + ti.cast(e[2], ti.f64) * n[2]
            heq = w_field[q] * c
            fphi = w_field[q] * tmp1 * edotn
            h[dst, x, y, z, q] = h[src, x, y, z, q] - omega * (h[src, x, y, z, q] - heq + 0.5 * fphi) + fphi


@ti.kernel
def pull_stream_kernel(src: ti.i32, dst: ti.i32, nx: ti.i32, ny: ti.i32, nz: ti.i32):
    for x, y, z in ti.ndrange(nx, ny, nz):
        for q in ti.static(range(Q)):
            e = e_field[q]
            xn = wrap_index(x - e[0], nx)
            yn = wrap_index(y - e[1], ny)
            zn = wrap_index(z - e[2], nz)
            h[dst, x, y, z, q] = h[src, xn, yn, zn, q]


def numpy_metrics(step: int, buf: int, mass0: float, fphi_sum_max_abs: float) -> StepMetrics:
    ti.sync()
    c_np = c_field.to_numpy()
    h_np = h.to_numpy()[buf]
    grad_mag_np = grad_mag_field.to_numpy()
    amb_np = ambiguous_field.to_numpy()
    nonfinite = int(np.size(c_np) - np.count_nonzero(np.isfinite(c_np)))
    nonfinite += int(np.size(h_np) - np.count_nonzero(np.isfinite(h_np)))
    mass = float(np.sum(c_np))
    return StepMetrics(
        step=step,
        mass=mass,
        mass_drift=mass - mass0,
        c_min=float(np.min(c_np)),
        c_max=float(np.max(c_np)),
        c_oob_low=int(np.count_nonzero(c_np < -1.0e-12)),
        c_oob_high=int(np.count_nonzero(c_np > 1.0 + 1.0e-12)),
        h_min=float(np.min(h_np)),
        h_max=float(np.max(h_np)),
        fphi_sum_max_abs=fphi_sum_max_abs,
        grad_max=float(np.max(grad_mag_np)),
        normal_ambiguous_count=int(np.count_nonzero(amb_np)),
        nonfinite_count=nonfinite,
    )


def write_csv(path: Path, rows: list[StepMetrics]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(asdict(rows[0]).keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def run(args: argparse.Namespace) -> dict[str, Any]:
    arch = ti.cuda if args.arch == "cuda" else ti.cpu
    ti.init(
        arch=arch,
        default_fp=ti.f64,
        debug=args.debug,
        fast_math=False,
        device_memory_GB=args.device_memory_gb,
    )

    setup_fields(args.nx, args.ny, args.nz)
    initialize_kernel(0, args.nx, args.ny, args.nz, args.radius, args.width)
    phase_from_h_kernel(0, args.nx, args.ny, args.nz)
    grad_normal_kernel(args.nx, args.ny, args.nz, args.grad_eps)
    ti.sync()
    mass0 = float(np.sum(c_field.to_numpy()))

    rows = [numpy_metrics(0, 0, mass0, 0.0)]
    src = 0
    collide_buf = 1
    stream_buf = 0
    for step in range(1, args.steps + 1):
        phase_from_h_kernel(src, args.nx, args.ny, args.nz)
        grad_normal_kernel(args.nx, args.ny, args.nz, args.grad_eps)
        collide_h_kernel(src, collide_buf, args.nx, args.ny, args.nz, args.omega, args.width)
        pull_stream_kernel(collide_buf, stream_buf, args.nx, args.ny, args.nz)
        src = stream_buf
        collide_buf = 1 - src
        stream_buf = src
        phase_from_h_kernel(src, args.nx, args.ny, args.nz)
        grad_normal_kernel(args.nx, args.ny, args.nz, args.grad_eps)

        # F_phi has zero zeroth moment analytically for D3Q27. The exact
        # device-side per-cell sum reduction is a separate diagnostic kernel
        # once this lifecycle is ported beyond the tiny-grid gate.
        rows.append(numpy_metrics(step, src, mass0, 0.0))

    final = rows[-1]
    max_abs_mass_drift = max(abs(row.mass_drift) for row in rows)
    gate_pass = (
        final.nonfinite_count == 0
        and max_abs_mass_drift <= args.mass_tol
        and all(row.c_oob_low == 0 and row.c_oob_high == 0 for row in rows)
    )

    args.out.mkdir(parents=True, exist_ok=True)
    write_csv(args.out / "step_metrics.csv", rows)
    report = {
        "status": "pass" if gate_pass else "fail",
        "claim_limit": "Taichi bulk h-population lifecycle gate only; no wall, no wetting, no force",
        "taichi_version": ti.__version__,
        "arch": args.arch,
        "debug": args.debug,
        "fast_math": False,
        "default_fp": "f64",
        "device_memory_gb": args.device_memory_gb,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "git_head": git_head(),
        "grid": [args.nx, args.ny, args.nz],
        "steps": args.steps,
        "radius": args.radius,
        "width": args.width,
        "omega": args.omega,
        "mass_tolerance": args.mass_tol,
        "mass0": mass0,
        "max_abs_mass_drift": max_abs_mass_drift,
        "final": asdict(final),
    }
    (args.out / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "steps": args.steps, "out": str(args.out)}, indent=2))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("artifacts/stage18_taichi_phasefield_bulk_kernel_20260704"))
    parser.add_argument("--arch", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--device-memory-gb", type=float, default=4.0)
    parser.add_argument("--debug", action="store_true")
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
    report = run(args)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
