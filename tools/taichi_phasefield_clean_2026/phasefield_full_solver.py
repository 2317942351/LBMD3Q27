"""Full-stack first Taichi phase-field multiphase LBM skeleton.

This file intentionally builds the whole solver dataflow before optimizing
individual closures. It is not a validation-grade model yet. It is a complete
running framework for:

- h_i phase populations,
- g_i momentum populations,
- rho(C), tau(C), gradC, laplaceC, mu,
- pressure/surface/body force placeholders,
- flat-wall geometry and wetting ghost fields,
- momentum bounce-back,
- phase wall source/write modes,
- diagnostics ledgers.

First target: run a low-risk 24^3 droplet case on P100, then a flat-wall
theta=90 case, and use the same executable for later closure replacement.
"""

import argparse
import csv
import importlib.util
import json
import math
import platform
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

if importlib.util.find_spec("taichi") is None:
    raise SystemExit("Taichi is not installed for this Python.")

import taichi as ti


Q = 27
CS2 = 1.0 / 3.0

h = None
g = None
e_field = None
w_field = None
opp_field = None

c_field = None
c_raw_field = None
rho_field = None
tau_field = None
pressure_field = None
mu_field = None
laplace_field = None
grad_field = None
normal_field = None
u_field = None
u_half_field = None

f_pressure_field = None
f_surf_field = None
f_mu_field = None
f_body_field = None
f_total_field = None
force_over_rho_field = None

solid_field = None
wall_field = None
sdf_field = None
wall_normal_field = None
target_theta_field = None
wall_c_ghost_field = None
write_allowed_field = None


@dataclass
class StepMetrics:
    step: int
    mass: float
    mass_drift: float
    c_min: float
    c_max: float
    c_oob_low: int
    c_oob_high: int
    rho_min: float
    rho_max: float
    mu_min: float
    mu_max: float
    u_max: float
    force_over_rho_max: float
    wall_cells: int
    write_allowed_cells: int
    wall_ghost_min: float
    wall_ghost_max: float
    nonfinite_count: int


def d3q27_lattice() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
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
    e = np.asarray(velocities, dtype=np.int32)
    w = np.asarray(weights, dtype=np.float64)
    opp = np.zeros(Q, dtype=np.int32)
    for i in range(Q):
        for j in range(Q):
            if np.all(e[j] == -e[i]):
                opp[i] = j
                break
    return e, w, opp


def setup_fields(nx: int, ny: int, nz: int) -> None:
    global h, g, e_field, w_field, opp_field
    global c_field, c_raw_field, rho_field, tau_field, pressure_field, mu_field
    global laplace_field, grad_field, normal_field, u_field, u_half_field
    global f_pressure_field, f_surf_field, f_mu_field, f_body_field
    global f_total_field, force_over_rho_field
    global solid_field, wall_field, sdf_field, wall_normal_field
    global target_theta_field, wall_c_ghost_field, write_allowed_field

    shape = (nx, ny, nz)
    h = ti.field(dtype=ti.f64, shape=(2, nx, ny, nz, Q))
    g = ti.field(dtype=ti.f64, shape=(2, nx, ny, nz, Q))
    e_field = ti.Vector.field(3, dtype=ti.i32, shape=Q)
    w_field = ti.field(dtype=ti.f64, shape=Q)
    opp_field = ti.field(dtype=ti.i32, shape=Q)

    c_field = ti.field(dtype=ti.f64, shape=shape)
    c_raw_field = ti.field(dtype=ti.f64, shape=shape)
    rho_field = ti.field(dtype=ti.f64, shape=shape)
    tau_field = ti.field(dtype=ti.f64, shape=shape)
    pressure_field = ti.field(dtype=ti.f64, shape=shape)
    mu_field = ti.field(dtype=ti.f64, shape=shape)
    laplace_field = ti.field(dtype=ti.f64, shape=shape)
    grad_field = ti.Vector.field(3, dtype=ti.f64, shape=shape)
    normal_field = ti.Vector.field(3, dtype=ti.f64, shape=shape)
    u_field = ti.Vector.field(3, dtype=ti.f64, shape=shape)
    u_half_field = ti.Vector.field(3, dtype=ti.f64, shape=shape)

    f_pressure_field = ti.Vector.field(3, dtype=ti.f64, shape=shape)
    f_surf_field = ti.Vector.field(3, dtype=ti.f64, shape=shape)
    f_mu_field = ti.Vector.field(3, dtype=ti.f64, shape=shape)
    f_body_field = ti.Vector.field(3, dtype=ti.f64, shape=shape)
    f_total_field = ti.Vector.field(3, dtype=ti.f64, shape=shape)
    force_over_rho_field = ti.Vector.field(3, dtype=ti.f64, shape=shape)

    solid_field = ti.field(dtype=ti.i32, shape=shape)
    wall_field = ti.field(dtype=ti.i32, shape=shape)
    sdf_field = ti.field(dtype=ti.f64, shape=shape)
    wall_normal_field = ti.Vector.field(3, dtype=ti.f64, shape=shape)
    target_theta_field = ti.field(dtype=ti.f64, shape=shape)
    wall_c_ghost_field = ti.field(dtype=ti.f64, shape=shape)
    write_allowed_field = ti.field(dtype=ti.i32, shape=shape)

    e_np, w_np, opp_np = d3q27_lattice()
    e_field.from_numpy(e_np)
    w_field.from_numpy(w_np)
    opp_field.from_numpy(opp_np)


@ti.func
def wrap_index(i, n):
    out = i
    if out < 0:
        out += n
    if out >= n:
        out -= n
    return out


@ti.func
def clamp01(x):
    y = x
    if y < 0.0:
        y = 0.0
    if y > 1.0:
        y = 1.0
    return y


@ti.func
def feq(q, rho, u):
    e = e_field[q]
    eu = ti.cast(e[0], ti.f64) * u[0] + ti.cast(e[1], ti.f64) * u[1] + ti.cast(e[2], ti.f64) * u[2]
    uu = u.dot(u)
    return w_field[q] * rho * (1.0 + eu / CS2 + 0.5 * eu * eu / (CS2 * CS2) - 0.5 * uu / CS2)


@ti.func
def heq(q, c, u):
    e = e_field[q]
    eu = ti.cast(e[0], ti.f64) * u[0] + ti.cast(e[1], ti.f64) * u[1] + ti.cast(e[2], ti.f64) * u[2]
    return w_field[q] * c * (1.0 + eu / CS2)


@ti.kernel
def build_geometry_kernel(nx: ti.i32, ny: ti.i32, nz: ti.i32, geometry_mode: ti.i32, theta_deg: ti.f64):
    for x, y, z in ti.ndrange(nx, ny, nz):
        solid = 0
        wall = 0
        sdf = 1.0e9
        wn = ti.Vector([0.0, 0.0, 0.0])
        if geometry_mode == 1:
            if y == 0:
                solid = 1
                sdf = -0.5
                wn = ti.Vector([0.0, 1.0, 0.0])
            elif y == 1:
                wall = 1
                sdf = 0.5
                wn = ti.Vector([0.0, 1.0, 0.0])
        solid_field[x, y, z] = solid
        wall_field[x, y, z] = wall
        sdf_field[x, y, z] = sdf
        wall_normal_field[x, y, z] = wn
        target_theta_field[x, y, z] = theta_deg * math.pi / 180.0
        wall_c_ghost_field[x, y, z] = 0.5
        write_allowed_field[x, y, z] = wall


@ti.kernel
def initialize_fields_kernel(
    hbuf: ti.i32,
    gbuf: ti.i32,
    nx: ti.i32,
    ny: ti.i32,
    nz: ti.i32,
    radius: ti.f64,
    width: ti.f64,
    rho_l: ti.f64,
    rho_g: ti.f64,
):
    cx = 0.5 * ti.cast(nx - 1, ti.f64)
    cy = 0.5 * ti.cast(ny - 1, ti.f64)
    cz = 0.5 * ti.cast(nz - 1, ti.f64)
    for x, y, z in ti.ndrange(nx, ny, nz):
        dx = ti.cast(x, ti.f64) - cx
        dy = ti.cast(y, ti.f64) - cy
        dz = ti.cast(z, ti.f64) - cz
        r = ti.sqrt(dx * dx + dy * dy + dz * dz)
        c = 0.5 * (1.0 - ti.tanh(2.0 * (r - radius) / width))
        if solid_field[x, y, z] == 1:
            c = 0.0
        rho = rho_g + c * (rho_l - rho_g)
        u = ti.Vector([0.0, 0.0, 0.0])
        c_field[x, y, z] = c
        c_raw_field[x, y, z] = c
        rho_field[x, y, z] = rho
        pressure_field[x, y, z] = rho * CS2
        u_field[x, y, z] = u
        u_half_field[x, y, z] = u
        for q in ti.static(range(Q)):
            h[hbuf, x, y, z, q] = w_field[q] * c
            g[gbuf, x, y, z, q] = feq(q, rho, u)


@ti.kernel
def phase_from_h_kernel(buf: ti.i32, nx: ti.i32, ny: ti.i32, nz: ti.i32):
    for x, y, z in ti.ndrange(nx, ny, nz):
        c = 0.0
        for q in ti.static(range(Q)):
            c += h[buf, x, y, z, q]
        c_raw_field[x, y, z] = c
        if solid_field[x, y, z] == 1:
            c = 0.0
        c_field[x, y, z] = c


@ti.kernel
def phase_bound_kernel(nx: ti.i32, ny: ti.i32, nz: ti.i32, mode: ti.i32):
    for x, y, z in ti.ndrange(nx, ny, nz):
        c = c_field[x, y, z]
        if mode == 1:
            c = clamp01(c)
            c_field[x, y, z] = c


@ti.kernel
def rho_tau_kernel(nx: ti.i32, ny: ti.i32, nz: ti.i32, rho_l: ti.f64, rho_g: ti.f64, nu_l: ti.f64, nu_g: ti.f64):
    for x, y, z in ti.ndrange(nx, ny, nz):
        c = clamp01(c_field[x, y, z])
        rho = rho_g + c * (rho_l - rho_g)
        nu = nu_g + c * (nu_l - nu_g)
        rho_field[x, y, z] = rho
        tau_field[x, y, z] = 0.5 + nu / CS2
        pressure_field[x, y, z] = rho * CS2


@ti.kernel
def grad_laplace_mu_kernel(nx: ti.i32, ny: ti.i32, nz: ti.i32, beta: ti.f64, kappa: ti.f64, grad_eps: ti.f64):
    for x, y, z in ti.ndrange(nx, ny, nz):
        xp = wrap_index(x + 1, nx)
        xm = wrap_index(x - 1, nx)
        yp = wrap_index(y + 1, ny)
        ym = wrap_index(y - 1, ny)
        zp = wrap_index(z + 1, nz)
        zm = wrap_index(z - 1, nz)

        c0 = c_field[x, y, z]
        gx = 0.5 * (c_field[xp, y, z] - c_field[xm, y, z])
        gy = 0.5 * (c_field[x, yp, z] - c_field[x, ym, z])
        gz = 0.5 * (c_field[x, y, zp] - c_field[x, y, zm])
        lap = (
            c_field[xp, y, z] + c_field[xm, y, z]
            + c_field[x, yp, z] + c_field[x, ym, z]
            + c_field[x, y, zp] + c_field[x, y, zm]
            - 6.0 * c0
        )
        grad = ti.Vector([gx, gy, gz])
        mag = ti.sqrt(gx * gx + gy * gy + gz * gz)
        normal = ti.Vector([0.0, 0.0, 0.0])
        if mag > grad_eps:
            normal = grad / mag
        grad_field[x, y, z] = grad
        normal_field[x, y, z] = normal
        laplace_field[x, y, z] = lap
        mu_field[x, y, z] = beta * c0 * (c0 - 1.0) * (2.0 * c0 - 1.0) - kappa * lap


@ti.kernel
def wetting_kernel(nx: ti.i32, ny: ti.i32, nz: ti.i32, mode: ti.i32):
    for x, y, z in ti.ndrange(nx, ny, nz):
        ghost = 0.5
        if wall_field[x, y, z] == 1:
            theta = target_theta_field[x, y, z]
            # First-candidate geometric shadow: theta=90 keeps local C.
            # Non-90 introduces a bounded bias only as an initial skeleton.
            bias = 0.25 * ti.cos(theta)
            ghost = clamp01(c_field[x, y, z] + bias)
            if mode == 1 and write_allowed_field[x, y, z] == 1:
                c_field[x, y, z] = ghost
        wall_c_ghost_field[x, y, z] = ghost


@ti.kernel
def force_kernel(nx: ti.i32, ny: ti.i32, nz: ti.i32, gx_body: ti.f64, gy_body: ti.f64, gz_body: ti.f64, force_mode: ti.i32):
    for x, y, z in ti.ndrange(nx, ny, nz):
        grad = grad_field[x, y, z]
        mu = mu_field[x, y, z]
        f_surf = mu * grad
        f_pressure = ti.Vector([0.0, 0.0, 0.0])
        f_mu = ti.Vector([0.0, 0.0, 0.0])
        f_body = ti.Vector([gx_body, gy_body, gz_body]) * rho_field[x, y, z]
        if force_mode == 0:
            f_surf = ti.Vector([0.0, 0.0, 0.0])
            f_body = ti.Vector([0.0, 0.0, 0.0])
        f_total = f_pressure + f_surf + f_mu + f_body
        if solid_field[x, y, z] == 1:
            f_total = ti.Vector([0.0, 0.0, 0.0])
        f_pressure_field[x, y, z] = f_pressure
        f_surf_field[x, y, z] = f_surf
        f_mu_field[x, y, z] = f_mu
        f_body_field[x, y, z] = f_body
        f_total_field[x, y, z] = f_total
        force_over_rho_field[x, y, z] = f_total / ti.max(rho_field[x, y, z], 1.0e-30)


@ti.kernel
def momentum_macro_kernel(buf: ti.i32, nx: ti.i32, ny: ti.i32, nz: ti.i32, momentum_mode: ti.i32):
    for x, y, z in ti.ndrange(nx, ny, nz):
        mom = ti.Vector([0.0, 0.0, 0.0])
        rho = rho_field[x, y, z]
        for q in ti.static(range(Q)):
            e = e_field[q]
            fq = g[buf, x, y, z, q]
            mom += ti.Vector([ti.cast(e[0], ti.f64), ti.cast(e[1], ti.f64), ti.cast(e[2], ti.f64)]) * fq
        u = (mom + 0.5 * f_total_field[x, y, z]) / ti.max(rho, 1.0e-30)
        if momentum_mode == 0:
            u = ti.Vector([0.0, 0.0, 0.0])
        if solid_field[x, y, z] == 1:
            u = ti.Vector([0.0, 0.0, 0.0])
        u_half_field[x, y, z] = u
        u_field[x, y, z] = u


@ti.kernel
def collide_phase_kernel(src: ti.i32, dst: ti.i32, nx: ti.i32, ny: ti.i32, nz: ti.i32, omega_h: ti.f64, width: ti.f64, phase_advection_mode: ti.i32):
    for x, y, z in ti.ndrange(nx, ny, nz):
        c = c_field[x, y, z]
        n = normal_field[x, y, z]
        u = u_field[x, y, z]
        if phase_advection_mode == 0:
            u = ti.Vector([0.0, 0.0, 0.0])
        tmp1 = (1.0 - 4.0 * (c - 0.5) * (c - 0.5)) / width
        for q in ti.static(range(Q)):
            e = e_field[q]
            edotn = ti.cast(e[0], ti.f64) * n[0] + ti.cast(e[1], ti.f64) * n[1] + ti.cast(e[2], ti.f64) * n[2]
            fphi = w_field[q] * tmp1 * edotn
            h[dst, x, y, z, q] = h[src, x, y, z, q] - omega_h * (h[src, x, y, z, q] - heq(q, c, u) + 0.5 * fphi) + fphi
            if solid_field[x, y, z] == 1:
                h[dst, x, y, z, q] = 0.0


@ti.kernel
def collide_momentum_kernel(src: ti.i32, dst: ti.i32, nx: ti.i32, ny: ti.i32, nz: ti.i32, momentum_mode: ti.i32):
    for x, y, z in ti.ndrange(nx, ny, nz):
        rho = rho_field[x, y, z]
        tau = tau_field[x, y, z]
        omega = 1.0 / tau
        u = u_field[x, y, z]
        f = f_total_field[x, y, z]
        for q in ti.static(range(Q)):
            e = e_field[q]
            ev = ti.Vector([ti.cast(e[0], ti.f64), ti.cast(e[1], ti.f64), ti.cast(e[2], ti.f64)])
            eu = ev.dot(u)
            ef = ev.dot(f)
            uf = u.dot(f)
            guo = w_field[q] * (1.0 - 0.5 * omega) * (ef / CS2 + eu * ef / (CS2 * CS2) - uf / CS2)
            gnext = g[src, x, y, z, q] - omega * (g[src, x, y, z, q] - feq(q, rho, u)) + guo
            if momentum_mode == 0:
                gnext = feq(q, rho, ti.Vector([0.0, 0.0, 0.0]))
            g[dst, x, y, z, q] = gnext
            if solid_field[x, y, z] == 1:
                g[dst, x, y, z, q] = feq(q, rho, ti.Vector([0.0, 0.0, 0.0]))


@ti.kernel
def stream_kernel(src_h: ti.i32, dst_h: ti.i32, src_g: ti.i32, dst_g: ti.i32, nx: ti.i32, ny: ti.i32, nz: ti.i32):
    for x, y, z in ti.ndrange(nx, ny, nz):
        for q in ti.static(range(Q)):
            e = e_field[q]
            xn = wrap_index(x - e[0], nx)
            yn = wrap_index(y - e[1], ny)
            zn = wrap_index(z - e[2], nz)
            h[dst_h, x, y, z, q] = h[src_h, xn, yn, zn, q]
            g[dst_g, x, y, z, q] = g[src_g, xn, yn, zn, q]


@ti.kernel
def boundary_kernel(hbuf: ti.i32, gbuf: ti.i32, nx: ti.i32, ny: ti.i32, nz: ti.i32, phase_wall_mode: ti.i32):
    for x, y, z in ti.ndrange(nx, ny, nz):
        if solid_field[x, y, z] == 1:
            for q in ti.static(range(Q)):
                h[hbuf, x, y, z, q] = 0.0
                g[gbuf, x, y, z, q] = g[gbuf, x, y, z, opp_field[q]]
        elif wall_field[x, y, z] == 1 and phase_wall_mode == 1:
            ghost = wall_c_ghost_field[x, y, z]
            for q in ti.static(range(Q)):
                h[hbuf, x, y, z, q] = w_field[q] * ghost


def numpy_metrics(step: int, hbuf: int, gbuf: int, mass0: float) -> StepMetrics:
    ti.sync()
    arrays = {
        "c": c_field.to_numpy(),
        "h": h.to_numpy()[hbuf],
        "g": g.to_numpy()[gbuf],
        "rho": rho_field.to_numpy(),
        "mu": mu_field.to_numpy(),
        "u": u_field.to_numpy(),
        "force_over_rho": force_over_rho_field.to_numpy(),
        "wall": wall_field.to_numpy(),
        "write_allowed": write_allowed_field.to_numpy(),
        "ghost": wall_c_ghost_field.to_numpy(),
    }
    nonfinite = 0
    for value in arrays.values():
        nonfinite += int(np.size(value) - np.count_nonzero(np.isfinite(value)))
    c = arrays["c"]
    mass = float(np.sum(c))
    u_mag = np.linalg.norm(arrays["u"], axis=-1)
    force_mag = np.linalg.norm(arrays["force_over_rho"], axis=-1)
    ghost = arrays["ghost"]
    return StepMetrics(
        step=step,
        mass=mass,
        mass_drift=mass - mass0,
        c_min=float(np.min(c)),
        c_max=float(np.max(c)),
        c_oob_low=int(np.count_nonzero(c < -1.0e-12)),
        c_oob_high=int(np.count_nonzero(c > 1.0 + 1.0e-12)),
        rho_min=float(np.min(arrays["rho"])),
        rho_max=float(np.max(arrays["rho"])),
        mu_min=float(np.min(arrays["mu"])),
        mu_max=float(np.max(arrays["mu"])),
        u_max=float(np.max(u_mag)),
        force_over_rho_max=float(np.max(force_mag)),
        wall_cells=int(np.count_nonzero(arrays["wall"])),
        write_allowed_cells=int(np.count_nonzero(arrays["write_allowed"])),
        wall_ghost_min=float(np.min(ghost)),
        wall_ghost_max=float(np.max(ghost)),
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

    build_geometry_kernel(args.nx, args.ny, args.nz, args.geometry_mode, args.theta_deg)
    initialize_fields_kernel(0, 0, args.nx, args.ny, args.nz, args.radius, args.width, args.rho_l, args.rho_g)
    phase_from_h_kernel(0, args.nx, args.ny, args.nz)
    phase_bound_kernel(args.nx, args.ny, args.nz, args.phase_bound_mode)
    rho_tau_kernel(args.nx, args.ny, args.nz, args.rho_l, args.rho_g, args.nu_l, args.nu_g)
    grad_laplace_mu_kernel(args.nx, args.ny, args.nz, args.beta, args.kappa, args.grad_eps)
    wetting_kernel(args.nx, args.ny, args.nz, args.wetting_mode)
    force_kernel(args.nx, args.ny, args.nz, args.body_gx, args.body_gy, args.body_gz, args.force_mode)
    momentum_macro_kernel(0, args.nx, args.ny, args.nz, args.momentum_mode)
    ti.sync()
    mass0 = float(np.sum(c_field.to_numpy()))

    h_src = 0
    h_collide = 1
    h_stream = 0
    g_src = 0
    g_collide = 1
    g_stream = 0

    rows = [numpy_metrics(0, h_src, g_src, mass0)]
    for step in range(1, args.steps + 1):
        phase_from_h_kernel(h_src, args.nx, args.ny, args.nz)
        phase_bound_kernel(args.nx, args.ny, args.nz, args.phase_bound_mode)
        rho_tau_kernel(args.nx, args.ny, args.nz, args.rho_l, args.rho_g, args.nu_l, args.nu_g)
        grad_laplace_mu_kernel(args.nx, args.ny, args.nz, args.beta, args.kappa, args.grad_eps)
        wetting_kernel(args.nx, args.ny, args.nz, args.wetting_mode)
        force_kernel(args.nx, args.ny, args.nz, args.body_gx, args.body_gy, args.body_gz, args.force_mode)
        momentum_macro_kernel(g_src, args.nx, args.ny, args.nz, args.momentum_mode)
        collide_phase_kernel(h_src, h_collide, args.nx, args.ny, args.nz, args.omega_h, args.width, args.phase_advection_mode)
        collide_momentum_kernel(g_src, g_collide, args.nx, args.ny, args.nz, args.momentum_mode)
        stream_kernel(h_collide, h_stream, g_collide, g_stream, args.nx, args.ny, args.nz)
        boundary_kernel(h_stream, g_stream, args.nx, args.ny, args.nz, args.phase_wall_mode)

        h_src = h_stream
        h_collide = 1 - h_src
        h_stream = h_src
        g_src = g_stream
        g_collide = 1 - g_src
        g_stream = g_src

        phase_from_h_kernel(h_src, args.nx, args.ny, args.nz)
        phase_bound_kernel(args.nx, args.ny, args.nz, args.phase_bound_mode)
        rho_tau_kernel(args.nx, args.ny, args.nz, args.rho_l, args.rho_g, args.nu_l, args.nu_g)
        grad_laplace_mu_kernel(args.nx, args.ny, args.nz, args.beta, args.kappa, args.grad_eps)
        force_kernel(args.nx, args.ny, args.nz, args.body_gx, args.body_gy, args.body_gz, args.force_mode)
        momentum_macro_kernel(g_src, args.nx, args.ny, args.nz, args.momentum_mode)

        if step % args.output_period == 0 or step == args.steps:
            rows.append(numpy_metrics(step, h_src, g_src, mass0))

    final = rows[-1]
    max_abs_mass_drift = max(abs(row.mass_drift) for row in rows)
    gate_pass = (
        final.nonfinite_count == 0
        and final.c_oob_low == 0
        and final.c_oob_high == 0
        and max_abs_mass_drift <= args.mass_tol
        and final.u_max <= args.umax_tol
    )
    args.out.mkdir(parents=True, exist_ok=True)
    write_csv(args.out / "step_metrics.csv", rows)
    report = {
        "status": "pass" if gate_pass else "fail",
        "claim_limit": "full-stack skeleton run only; not validation",
        "taichi_version": ti.__version__,
        "arch": args.arch,
        "default_fp": "f64",
        "fast_math": False,
        "debug": args.debug,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "git_head": git_head(),
        "grid": [args.nx, args.ny, args.nz],
        "steps": args.steps,
        "geometry_mode": args.geometry_mode,
        "rho_l": args.rho_l,
        "rho_g": args.rho_g,
        "density_ratio": args.rho_l / args.rho_g,
        "phase_bound_mode": args.phase_bound_mode,
        "wetting_mode": args.wetting_mode,
        "phase_wall_mode": args.phase_wall_mode,
        "force_mode": args.force_mode,
        "momentum_mode": args.momentum_mode,
        "phase_advection_mode": args.phase_advection_mode,
        "mass0": mass0,
        "mass_tolerance": args.mass_tol,
        "umax_tolerance": args.umax_tol,
        "max_abs_mass_drift": max_abs_mass_drift,
        "final": asdict(final),
    }
    (args.out / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "out": str(args.out), "steps": args.steps}, indent=2))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("artifacts/stage18_taichi_full_solver_20260704"))
    parser.add_argument("--arch", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--device-memory-gb", type=float, default=6.0)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--nx", type=int, default=24)
    parser.add_argument("--ny", type=int, default=24)
    parser.add_argument("--nz", type=int, default=24)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--output-period", type=int, default=1)
    parser.add_argument("--geometry-mode", type=int, default=0, help="0 periodic bulk, 1 flat wall at y=0")
    parser.add_argument("--theta-deg", type=float, default=90.0)
    parser.add_argument("--radius", type=float, default=6.0)
    parser.add_argument("--width", type=float, default=4.0)
    parser.add_argument("--rho-l", type=float, default=1.0)
    parser.add_argument("--rho-g", type=float, default=0.1)
    parser.add_argument("--nu-l", type=float, default=0.1)
    parser.add_argument("--nu-g", type=float, default=0.1)
    parser.add_argument("--omega-h", type=float, default=1.0)
    parser.add_argument("--beta", type=float, default=0.01)
    parser.add_argument("--kappa", type=float, default=0.01)
    parser.add_argument("--grad-eps", type=float, default=1.0e-12)
    parser.add_argument("--phase-bound-mode", type=int, default=1)
    parser.add_argument("--wetting-mode", type=int, default=0, help="0 shadow only, 1 write C at wall band")
    parser.add_argument("--phase-wall-mode", type=int, default=0, help="0 none, 1 write h=w*Cghost at wall band")
    parser.add_argument("--force-mode", type=int, default=0, help="0 off, 1 surface/body force on")
    parser.add_argument("--momentum-mode", type=int, default=0, help="0 frozen/reset equilibrium, 1 coupled BGK")
    parser.add_argument("--phase-advection-mode", type=int, default=0, help="0 h_eq uses zero velocity, 1 h_eq uses u")
    parser.add_argument("--mass-tol", type=float, default=1.0e-8)
    parser.add_argument("--umax-tol", type=float, default=10.0)
    parser.add_argument("--body-gx", type=float, default=0.0)
    parser.add_argument("--body-gy", type=float, default=0.0)
    parser.add_argument("--body-gz", type=float, default=0.0)
    args = parser.parse_args()
    report = run(args)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
