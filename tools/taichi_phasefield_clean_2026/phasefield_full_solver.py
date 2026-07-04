"""Book-derived Taichi phase-field multiphase LBM workbench.

This file intentionally keeps the whole solver dataflow in one auditable place
while the model is being closed against the project book anchors. It is not a
contact-angle validation claim. It is the clean implementation lane for:

- h_i phase populations,
- g_i momentum populations,
- rho(C), tau(C), gradC, laplaceC, mu,
- pressure/surface/body force closures,
- flat-wall geometry and per-link wetting reconstruction,
- momentum bounce-back,
- phase wall source/write modes,
- diagnostics ledgers.
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
EPS = 1.0e-30

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
force_cap_hit_field = None

solid_field = None
wall_field = None
sdf_field = None
wall_normal_field = None
target_theta_field = None
wall_c_ghost_field = None
write_allowed_field = None
phase_wall_missing_count_field = None
phase_wall_stream_mass_before_field = None
phase_wall_reflect_mass_field = None
phase_wall_delta_mass_field = None
mass_correction_delta = None
mass_correction_weight = None
mass_correction_count = None
phase_source_sum_field = None
phase_source_first_field = None


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
    pressure_min: float
    pressure_max: float
    droplet_volume_radius: float
    pressure_inside_mean: float
    pressure_outside_mean: float
    laplace_delta_p: float
    sigma_theory: float
    laplace_delta_p_target: float
    laplace_delta_p_relative_error: float
    mu_min: float
    mu_max: float
    u_max: float
    spurious_u_rms_interface: float
    interface_cells: int
    f_pressure_max: float
    f_surf_max: float
    f_mu_max: float
    f_body_max: float
    f_total_max: float
    force_over_rho_max: float
    force_cap_hits: int
    g_min: float
    g_max: float
    wall_cells: int
    write_allowed_cells: int
    phase_wall_missing_links: int
    phase_wall_stream_mass_before: float
    phase_wall_reflect_mass: float
    phase_wall_delta_mass: float
    mass_correction_delta: float
    mass_correction_weight: float
    mass_correction_count: int
    phase_source_sum_abs_max: float
    phase_source_first_max: float
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
    global f_total_field, force_over_rho_field, force_cap_hit_field
    global solid_field, wall_field, sdf_field, wall_normal_field
    global target_theta_field, wall_c_ghost_field, write_allowed_field
    global phase_wall_missing_count_field, phase_wall_stream_mass_before_field
    global phase_wall_reflect_mass_field, phase_wall_delta_mass_field
    global mass_correction_delta, mass_correction_weight, mass_correction_count
    global phase_source_sum_field, phase_source_first_field

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
    force_cap_hit_field = ti.field(dtype=ti.i32, shape=shape)

    solid_field = ti.field(dtype=ti.i32, shape=shape)
    wall_field = ti.field(dtype=ti.i32, shape=shape)
    sdf_field = ti.field(dtype=ti.f64, shape=shape)
    wall_normal_field = ti.Vector.field(3, dtype=ti.f64, shape=shape)
    target_theta_field = ti.field(dtype=ti.f64, shape=shape)
    wall_c_ghost_field = ti.field(dtype=ti.f64, shape=shape)
    write_allowed_field = ti.field(dtype=ti.i32, shape=shape)
    phase_wall_missing_count_field = ti.field(dtype=ti.i32, shape=shape)
    phase_wall_stream_mass_before_field = ti.field(dtype=ti.f64, shape=shape)
    phase_wall_reflect_mass_field = ti.field(dtype=ti.f64, shape=shape)
    phase_wall_delta_mass_field = ti.field(dtype=ti.f64, shape=shape)
    mass_correction_delta = ti.field(dtype=ti.f64, shape=())
    mass_correction_weight = ti.field(dtype=ti.f64, shape=())
    mass_correction_count = ti.field(dtype=ti.i32, shape=())
    phase_source_sum_field = ti.field(dtype=ti.f64, shape=shape)
    phase_source_first_field = ti.Vector.field(3, dtype=ti.f64, shape=shape)

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
def c_neighbor_or_center(x, y, z, nx, ny, nz, c0):
    xx = wrap_index(x, nx)
    yy = wrap_index(y, ny)
    zz = wrap_index(z, nz)
    value = c_field[xx, yy, zz]
    if solid_field[xx, yy, zz] == 1:
        value = c0
    return value


@ti.func
def feq(q, rho, u):
    e = e_field[q]
    eu = ti.cast(e[0], ti.f64) * u[0] + ti.cast(e[1], ti.f64) * u[1] + ti.cast(e[2], ti.f64) * u[2]
    uu = u.dot(u)
    return w_field[q] * rho * (1.0 + eu / CS2 + 0.5 * eu * eu / (CS2 * CS2) - 0.5 * uu / CS2)


@ti.func
def geq_pressure_velocity(q, pressure, rho_ref, u):
    e = e_field[q]
    eu = ti.cast(e[0], ti.f64) * u[0] + ti.cast(e[1], ti.f64) * u[1] + ti.cast(e[2], ti.f64) * u[2]
    uu = u.dot(u)
    pressure_part = pressure / CS2
    return w_field[q] * (pressure_part + rho_ref * (eu / CS2 + 0.5 * eu * eu / (CS2 * CS2) - 0.5 * uu / CS2))


@ti.func
def heq(q, c, u):
    e = e_field[q]
    eu = ti.cast(e[0], ti.f64) * u[0] + ti.cast(e[1], ti.f64) * u[1] + ti.cast(e[2], ti.f64) * u[2]
    return w_field[q] * c * (1.0 + eu / CS2)


@ti.func
def phase_mobility_factor(c, width, mode):
    bounded_c = clamp01(c)
    value = (1.0 - 4.0 * (bounded_c - 0.5) * (bounded_c - 0.5)) / width
    if mode >= 1:
        # Book-derived conservative Allen-Cahn route for C in [0, 1]:
        # |grad(C)|_eq ~ 4 C(1-C) / W.  This keeps the source normalized to
        # the order-parameter range instead of relying on a hard-coded 0.5.
        value = 4.0 * bounded_c * (1.0 - bounded_c) / width
    return value


@ti.func
def phase_source(q, c, n, width, mode):
    e = e_field[q]
    edotn = ti.cast(e[0], ti.f64) * n[0] + ti.cast(e[1], ti.f64) * n[1] + ti.cast(e[2], ti.f64) * n[2]
    scale = phase_mobility_factor(c, width, mode)
    source = w_field[q] * scale * edotn
    if mode >= 2:
        # Enforce sum_i e_i F_i = scale*n on D3Q27.  Without the 1/cs2
        # correction the first moment is only cs2*scale*n.
        source = source / CS2
    return source


@ti.func
def phase_source_scaled(q, c, n, width, mode, source_scale):
    return phase_source(q, c, n, width, mode) * source_scale


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
    momentum_density_mode: ti.i32,
    momentum_rho_ref: ti.f64,
    pressure_model: ti.i32,
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
        rho_mom = rho
        if momentum_density_mode == 1:
            rho_mom = momentum_rho_ref
        u = ti.Vector([0.0, 0.0, 0.0])
        c_field[x, y, z] = c
        c_raw_field[x, y, z] = c
        rho_field[x, y, z] = rho
        pressure = rho * CS2
        if pressure_model >= 2:
            pressure = CS2 * momentum_rho_ref
        pressure_field[x, y, z] = pressure
        u_field[x, y, z] = u
        u_half_field[x, y, z] = u
        for q in ti.static(range(Q)):
            h[hbuf, x, y, z, q] = w_field[q] * c
            if pressure_model >= 2:
                g[gbuf, x, y, z, q] = geq_pressure_velocity(q, pressure, rho_mom, u)
            else:
                g[gbuf, x, y, z, q] = feq(q, rho_mom, u)


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
def mass_correction_clip_kernel(hbuf: ti.i32, nx: ti.i32, ny: ti.i32, nz: ti.i32, mode: ti.i32):
    mass_correction_delta[None] = 0.0
    mass_correction_weight[None] = 0.0
    mass_correction_count[None] = 0
    if mode == 2:
        for x, y, z in ti.ndrange(nx, ny, nz):
            if solid_field[x, y, z] == 0:
                old_c = c_field[x, y, z]
                new_c = clamp01(old_c)
                delta = old_c - new_c
                if delta != 0.0:
                    c_field[x, y, z] = new_c
                    corr = new_c - old_c
                    for q in ti.static(range(Q)):
                        h[hbuf, x, y, z, q] += w_field[q] * corr
                    ti.atomic_add(mass_correction_delta[None], delta)
                weight = new_c * (1.0 - new_c)
                if weight > 1.0e-8:
                    ti.atomic_add(mass_correction_weight[None], weight)
                    ti.atomic_add(mass_correction_count[None], 1)


@ti.kernel
def mass_correction_redistribute_kernel(hbuf: ti.i32, nx: ti.i32, ny: ti.i32, nz: ti.i32, mode: ti.i32):
    if mode == 2:
        total_weight = mass_correction_weight[None]
        delta = mass_correction_delta[None]
        if ti.abs(delta) > 0.0 and total_weight > 1.0e-30:
            for x, y, z in ti.ndrange(nx, ny, nz):
                if solid_field[x, y, z] == 0:
                    c = c_field[x, y, z]
                    weight = c * (1.0 - c)
                    if weight > 1.0e-8:
                        add_c = delta * weight / total_weight
                        c_new = c + add_c
                        c_field[x, y, z] = c_new
                        for q in ti.static(range(Q)):
                            h[hbuf, x, y, z, q] += w_field[q] * add_c


@ti.kernel
def rho_tau_kernel(
    nx: ti.i32,
    ny: ti.i32,
    nz: ti.i32,
    rho_l: ti.f64,
    rho_g: ti.f64,
    nu_l: ti.f64,
    nu_g: ti.f64,
    pressure_model: ti.i32,
    pressure_reference: ti.f64,
):
    for x, y, z in ti.ndrange(nx, ny, nz):
        c = clamp01(c_field[x, y, z])
        rho = rho_g + c * (rho_l - rho_g)
        nu = nu_g + c * (nu_l - nu_g)
        rho_field[x, y, z] = rho
        tau_field[x, y, z] = 0.5 + nu / CS2
        pressure = rho * CS2
        if pressure_model == 1:
            pressure = pressure - pressure_reference
        if pressure_model >= 2:
            pressure = pressure_reference
        pressure_field[x, y, z] = pressure


@ti.kernel
def pressure_from_g_kernel(buf: ti.i32, nx: ti.i32, ny: ti.i32, nz: ti.i32, pressure_model: ti.i32):
    if pressure_model >= 2:
        for x, y, z in ti.ndrange(nx, ny, nz):
            pnorm = 0.0
            for q in ti.static(range(Q)):
                pnorm += g[buf, x, y, z, q]
            pressure = CS2 * pnorm
            if solid_field[x, y, z] == 1:
                pressure = 0.0
            pressure_field[x, y, z] = pressure


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
        cxp = c_neighbor_or_center(x + 1, y, z, nx, ny, nz, c0)
        cxm = c_neighbor_or_center(x - 1, y, z, nx, ny, nz, c0)
        cyp = c_neighbor_or_center(x, y + 1, z, nx, ny, nz, c0)
        cym = c_neighbor_or_center(x, y - 1, z, nx, ny, nz, c0)
        czp = c_neighbor_or_center(x, y, z + 1, nx, ny, nz, c0)
        czm = c_neighbor_or_center(x, y, z - 1, nx, ny, nz, c0)
        gx = 0.5 * (cxp - cxm)
        gy = 0.5 * (cyp - cym)
        gz = 0.5 * (czp - czm)
        lap = (
            cxp + cxm
            + cyp + cym
            + czp + czm
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
def force_kernel(
    nx: ti.i32,
    ny: ti.i32,
    nz: ti.i32,
    gx_body: ti.f64,
    gy_body: ti.f64,
    gz_body: ti.f64,
    force_mode: ti.i32,
    force_closure_mode: ti.i32,
    surface_force_scale: ti.f64,
    pressure_force_scale: ti.f64,
    rho_force_floor: ti.f64,
    force_accel_cap: ti.f64,
):
    for x, y, z in ti.ndrange(nx, ny, nz):
        xp = wrap_index(x + 1, nx)
        xm = wrap_index(x - 1, nx)
        yp = wrap_index(y + 1, ny)
        ym = wrap_index(y - 1, ny)
        zp = wrap_index(z + 1, nz)
        zm = wrap_index(z - 1, nz)
        grad_p = ti.Vector([
            0.5 * (pressure_field[xp, y, z] - pressure_field[xm, y, z]),
            0.5 * (pressure_field[x, yp, z] - pressure_field[x, ym, z]),
            0.5 * (pressure_field[x, y, zp] - pressure_field[x, y, zm]),
        ])
        grad = grad_field[x, y, z]
        mu = mu_field[x, y, z]
        f_surf_raw = surface_force_scale * mu * grad
        f_pressure_raw = -pressure_force_scale * grad_p
        f_surf = ti.Vector([0.0, 0.0, 0.0])
        f_pressure = ti.Vector([0.0, 0.0, 0.0])
        f_mu = ti.Vector([0.0, 0.0, 0.0])
        f_body = ti.Vector([gx_body, gy_body, gz_body]) * rho_field[x, y, z]
        active_closure = force_closure_mode
        if force_mode == 1 and force_closure_mode == 0:
            active_closure = 1
        if active_closure == 1 or active_closure == 3:
            f_surf = f_surf_raw
        if active_closure == 2 or active_closure == 3:
            f_pressure = f_pressure_raw
        if active_closure == 0:
            f_surf = ti.Vector([0.0, 0.0, 0.0])
            f_pressure = ti.Vector([0.0, 0.0, 0.0])
            f_body = ti.Vector([0.0, 0.0, 0.0])
        f_total = f_pressure + f_surf + f_mu + f_body
        cap_hit = 0
        rho_for_force = ti.max(rho_field[x, y, z], rho_force_floor)
        accel = f_total / rho_for_force
        accel_mag = ti.sqrt(accel.dot(accel))
        if force_accel_cap > 0.0 and accel_mag > force_accel_cap:
            f_total = f_total * (force_accel_cap / accel_mag)
            cap_hit = 1
        if solid_field[x, y, z] == 1:
            f_total = ti.Vector([0.0, 0.0, 0.0])
            cap_hit = 0
        f_pressure_field[x, y, z] = f_pressure
        f_surf_field[x, y, z] = f_surf
        f_mu_field[x, y, z] = f_mu
        f_body_field[x, y, z] = f_body
        f_total_field[x, y, z] = f_total
        force_over_rho_field[x, y, z] = f_total / rho_for_force
        force_cap_hit_field[x, y, z] = cap_hit


@ti.kernel
def momentum_macro_kernel(
    buf: ti.i32,
    nx: ti.i32,
    ny: ti.i32,
    nz: ti.i32,
    momentum_mode: ti.i32,
    force_insertion_mode: ti.i32,
    rho_force_floor: ti.f64,
    momentum_density_mode: ti.i32,
    momentum_rho_ref: ti.f64,
    velocity_density_mode: ti.i32,
):
    for x, y, z in ti.ndrange(nx, ny, nz):
        mom = ti.Vector([0.0, 0.0, 0.0])
        rho = rho_field[x, y, z]
        rho_macro = rho
        if momentum_density_mode == 1:
            rho_macro = momentum_rho_ref
        if velocity_density_mode == 1:
            rho_macro = rho
        elif velocity_density_mode == 2:
            rho_macro = ti.max(rho, rho_force_floor)
        for q in ti.static(range(Q)):
            e = e_field[q]
            fq = g[buf, x, y, z, q]
            mom += ti.Vector([ti.cast(e[0], ti.f64), ti.cast(e[1], ti.f64), ti.cast(e[2], ti.f64)]) * fq
        f = f_total_field[x, y, z]
        use_half_force = force_insertion_mode == 1 or force_insertion_mode == 2
        u = mom / ti.max(rho_macro, rho_force_floor)
        if use_half_force:
            u = (mom + 0.5 * f) / ti.max(rho_macro, rho_force_floor)
        if momentum_mode == 0:
            u = ti.Vector([0.0, 0.0, 0.0])
        if solid_field[x, y, z] == 1:
            u = ti.Vector([0.0, 0.0, 0.0])
        u_half_field[x, y, z] = u
        u_field[x, y, z] = u


@ti.kernel
def collide_phase_kernel(
    src: ti.i32,
    dst: ti.i32,
    nx: ti.i32,
    ny: ti.i32,
    nz: ti.i32,
    omega_h: ti.f64,
    width: ti.f64,
    phase_advection_mode: ti.i32,
    phase_wall_mode: ti.i32,
    phase_equation_mode: ti.i32,
    phase_source_scale: ti.f64,
):
    for x, y, z in ti.ndrange(nx, ny, nz):
        c = c_field[x, y, z]
        n = normal_field[x, y, z]
        u = u_field[x, y, z]
        if phase_advection_mode == 0:
            u = ti.Vector([0.0, 0.0, 0.0])
        if phase_wall_mode == 2 and wall_field[x, y, z] == 1:
            wn = wall_normal_field[x, y, z]
            u = u - wn * u.dot(wn)
        source_sum = 0.0
        source_first = ti.Vector([0.0, 0.0, 0.0])
        for q in ti.static(range(Q)):
            e = e_field[q]
            ev = ti.Vector([ti.cast(e[0], ti.f64), ti.cast(e[1], ti.f64), ti.cast(e[2], ti.f64)])
            fphi = phase_source_scaled(q, c, n, width, phase_equation_mode, phase_source_scale)
            source_sum += fphi
            source_first += ev * fphi
            h[dst, x, y, z, q] = h[src, x, y, z, q] - omega_h * (h[src, x, y, z, q] - heq(q, c, u) + 0.5 * fphi) + fphi
            if solid_field[x, y, z] == 1:
                h[dst, x, y, z, q] = 0.0
        phase_source_sum_field[x, y, z] = source_sum
        phase_source_first_field[x, y, z] = source_first


@ti.kernel
def collide_momentum_kernel(
    src: ti.i32,
    dst: ti.i32,
    nx: ti.i32,
    ny: ti.i32,
    nz: ti.i32,
    momentum_mode: ti.i32,
    force_insertion_mode: ti.i32,
    momentum_density_mode: ti.i32,
    momentum_rho_ref: ti.f64,
    pressure_model: ti.i32,
):
    for x, y, z in ti.ndrange(nx, ny, nz):
        rho = rho_field[x, y, z]
        rho_eq = rho
        if momentum_density_mode == 1:
            rho_eq = momentum_rho_ref
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
            source = 0.0
            if force_insertion_mode == 1 or force_insertion_mode == 3:
                source = guo
            eq = feq(q, rho_eq, u)
            if pressure_model >= 2:
                eq = geq_pressure_velocity(q, pressure_field[x, y, z], rho_eq, u)
            gnext = g[src, x, y, z, q] - omega * (g[src, x, y, z, q] - eq) + source
            if momentum_mode == 0:
                if pressure_model >= 2:
                    gnext = geq_pressure_velocity(q, pressure_field[x, y, z], rho_eq, ti.Vector([0.0, 0.0, 0.0]))
                else:
                    gnext = feq(q, rho_eq, ti.Vector([0.0, 0.0, 0.0]))
            g[dst, x, y, z, q] = gnext
            if solid_field[x, y, z] == 1:
                if pressure_model >= 2:
                    g[dst, x, y, z, q] = geq_pressure_velocity(q, 0.0, rho_eq, ti.Vector([0.0, 0.0, 0.0]))
                else:
                    g[dst, x, y, z, q] = feq(q, rho_eq, ti.Vector([0.0, 0.0, 0.0]))


@ti.kernel
def stream_kernel(src_h: ti.i32, dst_h: ti.i32, src_g: ti.i32, dst_g: ti.i32, nx: ti.i32, ny: ti.i32, nz: ti.i32, phase_wall_mode: ti.i32):
    for x, y, z in ti.ndrange(nx, ny, nz):
        for q in ti.static(range(Q)):
            e = e_field[q]
            xn = wrap_index(x - e[0], nx)
            yn = wrap_index(y - e[1], ny)
            zn = wrap_index(z - e[2], nz)
            if solid_field[xn, yn, zn] == 1 and solid_field[x, y, z] == 0:
                if phase_wall_mode == 2:
                    h[dst_h, x, y, z, q] = h[src_h, x, y, z, opp_field[q]]
                elif phase_wall_mode == 3:
                    ghost = wall_c_ghost_field[x, y, z]
                    h[dst_h, x, y, z, q] = h[src_h, x, y, z, opp_field[q]] + w_field[q] * (ghost - c_field[x, y, z])
                else:
                    h[dst_h, x, y, z, q] = 0.0
                g[dst_g, x, y, z, q] = g[src_g, x, y, z, opp_field[q]]
            else:
                h[dst_h, x, y, z, q] = h[src_h, xn, yn, zn, q]
                g[dst_g, x, y, z, q] = g[src_g, xn, yn, zn, q]


@ti.kernel
def boundary_kernel(hbuf: ti.i32, gbuf: ti.i32, nx: ti.i32, ny: ti.i32, nz: ti.i32, phase_wall_mode: ti.i32):
    for x, y, z in ti.ndrange(nx, ny, nz):
        phase_wall_missing_count_field[x, y, z] = 0
        phase_wall_stream_mass_before_field[x, y, z] = 0.0
        phase_wall_reflect_mass_field[x, y, z] = 0.0
        phase_wall_delta_mass_field[x, y, z] = 0.0
        if solid_field[x, y, z] == 1:
            for q in ti.static(range(Q)):
                h[hbuf, x, y, z, q] = 0.0
                g[gbuf, x, y, z, q] = g[gbuf, x, y, z, opp_field[q]]
        elif phase_wall_mode == 2 or phase_wall_mode == 3:
            missing = 0
            old_sum = 0.0
            reflected = 0.0
            for q in ti.static(range(Q)):
                old_sum += h[hbuf, x, y, z, q]
            for q in ti.static(range(Q)):
                e = e_field[q]
                xn = wrap_index(x - e[0], nx)
                yn = wrap_index(y - e[1], ny)
                zn = wrap_index(z - e[2], nz)
                if solid_field[xn, yn, zn] == 1:
                    val = h[hbuf, x, y, z, q]
                    reflected += val
                    missing += 1
            new_sum = 0.0
            for q in ti.static(range(Q)):
                new_sum += h[hbuf, x, y, z, q]
            phase_wall_missing_count_field[x, y, z] = missing
            phase_wall_stream_mass_before_field[x, y, z] = old_sum
            phase_wall_reflect_mass_field[x, y, z] = reflected
            phase_wall_delta_mass_field[x, y, z] = new_sum - old_sum
        elif wall_field[x, y, z] == 1 and phase_wall_mode == 1:
            ghost = wall_c_ghost_field[x, y, z]
            for q in ti.static(range(Q)):
                h[hbuf, x, y, z, q] = w_field[q] * ghost


def safe_mean(values: np.ndarray) -> float:
    if values.size == 0:
        return 0.0
    return float(np.mean(values))


def numpy_metrics(step: int, hbuf: int, gbuf: int, mass0: float, beta: float, kappa: float) -> StepMetrics:
    ti.sync()
    arrays = {
        "c": c_field.to_numpy(),
        "h": h.to_numpy()[hbuf],
        "g": g.to_numpy()[gbuf],
        "rho": rho_field.to_numpy(),
        "pressure": pressure_field.to_numpy(),
        "mu": mu_field.to_numpy(),
        "u": u_field.to_numpy(),
        "f_pressure": f_pressure_field.to_numpy(),
        "f_surf": f_surf_field.to_numpy(),
        "f_mu": f_mu_field.to_numpy(),
        "f_body": f_body_field.to_numpy(),
        "f_total": f_total_field.to_numpy(),
        "force_over_rho": force_over_rho_field.to_numpy(),
        "force_cap_hit": force_cap_hit_field.to_numpy(),
        "wall": wall_field.to_numpy(),
        "write_allowed": write_allowed_field.to_numpy(),
        "ghost": wall_c_ghost_field.to_numpy(),
        "phase_wall_missing": phase_wall_missing_count_field.to_numpy(),
        "phase_wall_mass_before": phase_wall_stream_mass_before_field.to_numpy(),
        "phase_wall_reflect_mass": phase_wall_reflect_mass_field.to_numpy(),
        "phase_wall_delta_mass": phase_wall_delta_mass_field.to_numpy(),
        "phase_source_sum": phase_source_sum_field.to_numpy(),
        "phase_source_first": phase_source_first_field.to_numpy(),
    }
    nonfinite = 0
    for value in arrays.values():
        nonfinite += int(np.size(value) - np.count_nonzero(np.isfinite(value)))
    c = arrays["c"]
    mass = float(np.sum(c))
    u_mag = np.linalg.norm(arrays["u"], axis=-1)
    inside = c > 0.9
    outside = c < 0.1
    interface = (c >= 0.1) & (c <= 0.9)
    droplet_volume_radius = float((3.0 * max(mass, 0.0) / (4.0 * math.pi)) ** (1.0 / 3.0)) if mass > 0.0 else 0.0
    pressure_inside_mean = safe_mean(arrays["pressure"][inside])
    pressure_outside_mean = safe_mean(arrays["pressure"][outside])
    laplace_delta_p = pressure_inside_mean - pressure_outside_mean
    sigma_theory = math.sqrt(max(kappa * beta, 0.0)) / 6.0
    laplace_delta_p_target = 2.0 * sigma_theory / droplet_volume_radius if droplet_volume_radius > 0.0 else 0.0
    laplace_delta_p_relative_error = (
        abs(laplace_delta_p - laplace_delta_p_target) / max(abs(laplace_delta_p_target), 1.0e-30)
        if laplace_delta_p_target != 0.0
        else 0.0
    )
    spurious_u_rms_interface = float(np.sqrt(np.mean(u_mag[interface] ** 2))) if np.count_nonzero(interface) else 0.0
    f_pressure_mag = np.linalg.norm(arrays["f_pressure"], axis=-1)
    f_surf_mag = np.linalg.norm(arrays["f_surf"], axis=-1)
    f_mu_mag = np.linalg.norm(arrays["f_mu"], axis=-1)
    f_body_mag = np.linalg.norm(arrays["f_body"], axis=-1)
    f_total_mag = np.linalg.norm(arrays["f_total"], axis=-1)
    force_mag = np.linalg.norm(arrays["force_over_rho"], axis=-1)
    phase_source_first_mag = np.linalg.norm(arrays["phase_source_first"], axis=-1)
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
        pressure_min=float(np.min(arrays["pressure"])),
        pressure_max=float(np.max(arrays["pressure"])),
        droplet_volume_radius=droplet_volume_radius,
        pressure_inside_mean=pressure_inside_mean,
        pressure_outside_mean=pressure_outside_mean,
        laplace_delta_p=laplace_delta_p,
        sigma_theory=sigma_theory,
        laplace_delta_p_target=laplace_delta_p_target,
        laplace_delta_p_relative_error=laplace_delta_p_relative_error,
        mu_min=float(np.min(arrays["mu"])),
        mu_max=float(np.max(arrays["mu"])),
        u_max=float(np.max(u_mag)),
        spurious_u_rms_interface=spurious_u_rms_interface,
        interface_cells=int(np.count_nonzero(interface)),
        f_pressure_max=float(np.max(f_pressure_mag)),
        f_surf_max=float(np.max(f_surf_mag)),
        f_mu_max=float(np.max(f_mu_mag)),
        f_body_max=float(np.max(f_body_mag)),
        f_total_max=float(np.max(f_total_mag)),
        force_over_rho_max=float(np.max(force_mag)),
        force_cap_hits=int(np.count_nonzero(arrays["force_cap_hit"])),
        g_min=float(np.min(arrays["g"])),
        g_max=float(np.max(arrays["g"])),
        wall_cells=int(np.count_nonzero(arrays["wall"])),
        write_allowed_cells=int(np.count_nonzero(arrays["write_allowed"])),
        phase_wall_missing_links=int(np.sum(arrays["phase_wall_missing"])),
        phase_wall_stream_mass_before=float(np.sum(arrays["phase_wall_mass_before"])),
        phase_wall_reflect_mass=float(np.sum(arrays["phase_wall_reflect_mass"])),
        phase_wall_delta_mass=float(np.sum(arrays["phase_wall_delta_mass"])),
        mass_correction_delta=float(mass_correction_delta[None]),
        mass_correction_weight=float(mass_correction_weight[None]),
        mass_correction_count=int(mass_correction_count[None]),
        phase_source_sum_abs_max=float(np.max(np.abs(arrays["phase_source_sum"]))),
        phase_source_first_max=float(np.max(phase_source_first_mag)),
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


def lattice_phase_mobility(omega_h: float) -> float:
    tau_h = 1.0 / omega_h
    return CS2 * (tau_h - 0.5)


def phase_post_source_factor(omega_h: float) -> float:
    return 1.0 - 0.5 * omega_h


def resolve_phase_source_scale(args: argparse.Namespace) -> dict[str, float | int | str]:
    """Resolve the source strength used by the h-population collision.

    The raw D3Q27 moment and the post-collision effective moment are different:

        h_post = h - omega_h (h - h_eq + 0.5 Fphi) + Fphi
        effective source contribution = (1 - 0.5 omega_h) Fphi

    The scale modes make this distinction explicit instead of hiding it inside
    a hand-picked phase_source_scale.
    """

    post_factor = phase_post_source_factor(args.omega_h)
    lat_mobility = lattice_phase_mobility(args.omega_h)
    mobility = args.phase_mobility
    if mobility < 0.0:
        mobility = lat_mobility

    mode = args.phase_source_scale_mode
    scale = args.phase_source_scale
    description = "manual"

    if mode == 1:
        # Keep the effective source strength of the old stable D3Q27 source
        # while using the moment-corrected mode-2 algebra.  This is the
        # conservative bridge from legacy to book-CAC source moments.
        scale = CS2 if args.phase_equation_mode >= 2 else 1.0
        description = "legacy_effective_strength"
    elif mode == 2:
        # Make the post-collision source moment equal the raw CAC target.
        # This is mathematically explicit but can be too strong and must be
        # proven by boundedness/Laplace gates before use.
        scale = 1.0 / max(abs(post_factor), EPS)
        description = "post_collision_target_strength"
    elif mode == 3:
        # Tie source strength to mobility relative to the lattice mobility.
        # For phase_equation_mode=2 and default mobility=M_lattice, this gives
        # CS2 and therefore matches the stable D3Q27 source strength while the
        # code still carries the corrected raw first moment.
        base = CS2 if args.phase_equation_mode >= 2 else 1.0
        scale = base * mobility / max(lat_mobility, EPS)
        description = "mobility_relative_strength"

    return {
        "mode": mode,
        "description": description,
        "effective_scale": scale,
        "requested_scale": args.phase_source_scale,
        "phase_mobility": mobility,
        "lattice_phase_mobility": lat_mobility,
        "post_source_factor": post_factor,
        "effective_post_scale": post_factor * scale,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    phase_scale_info = resolve_phase_source_scale(args)
    effective_phase_source_scale = float(phase_scale_info["effective_scale"])

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
    initialize_fields_kernel(
        0, 0, args.nx, args.ny, args.nz,
        args.radius, args.width, args.rho_l, args.rho_g,
        args.momentum_density_mode, args.momentum_rho_ref,
        args.pressure_model,
    )
    phase_from_h_kernel(0, args.nx, args.ny, args.nz)
    if args.phase_bound_mode == 2:
        mass_correction_clip_kernel(0, args.nx, args.ny, args.nz, args.phase_bound_mode)
        mass_correction_redistribute_kernel(0, args.nx, args.ny, args.nz, args.phase_bound_mode)
        phase_from_h_kernel(0, args.nx, args.ny, args.nz)
    else:
        phase_bound_kernel(args.nx, args.ny, args.nz, args.phase_bound_mode)
    rho_tau_kernel(args.nx, args.ny, args.nz, args.rho_l, args.rho_g, args.nu_l, args.nu_g, args.pressure_model, args.pressure_reference)
    pressure_from_g_kernel(0, args.nx, args.ny, args.nz, args.pressure_model)
    grad_laplace_mu_kernel(args.nx, args.ny, args.nz, args.beta, args.kappa, args.grad_eps)
    wetting_kernel(args.nx, args.ny, args.nz, args.wetting_mode)
    force_kernel(
        args.nx, args.ny, args.nz,
        args.body_gx, args.body_gy, args.body_gz,
        args.force_mode, args.force_closure_mode,
        args.surface_force_scale, args.pressure_force_scale,
        args.rho_force_floor, args.force_accel_cap,
    )
    momentum_macro_kernel(
        0, args.nx, args.ny, args.nz,
        args.momentum_mode, args.force_insertion_mode, args.rho_force_floor,
        args.momentum_density_mode, args.momentum_rho_ref,
        args.velocity_density_mode,
    )
    ti.sync()
    mass0 = float(np.sum(c_field.to_numpy()))

    h_src = 0
    h_collide = 1
    h_stream = 0
    g_src = 0
    g_collide = 1
    g_stream = 0

    rows = [numpy_metrics(0, h_src, g_src, mass0, args.beta, args.kappa)]
    for step in range(1, args.steps + 1):
        phase_from_h_kernel(h_src, args.nx, args.ny, args.nz)
        if args.phase_bound_mode == 2:
            mass_correction_clip_kernel(h_src, args.nx, args.ny, args.nz, args.phase_bound_mode)
            mass_correction_redistribute_kernel(h_src, args.nx, args.ny, args.nz, args.phase_bound_mode)
            phase_from_h_kernel(h_src, args.nx, args.ny, args.nz)
        else:
            phase_bound_kernel(args.nx, args.ny, args.nz, args.phase_bound_mode)
        rho_tau_kernel(args.nx, args.ny, args.nz, args.rho_l, args.rho_g, args.nu_l, args.nu_g, args.pressure_model, args.pressure_reference)
        pressure_from_g_kernel(g_src, args.nx, args.ny, args.nz, args.pressure_model)
        grad_laplace_mu_kernel(args.nx, args.ny, args.nz, args.beta, args.kappa, args.grad_eps)
        wetting_kernel(args.nx, args.ny, args.nz, args.wetting_mode)
        force_kernel(
            args.nx, args.ny, args.nz,
            args.body_gx, args.body_gy, args.body_gz,
            args.force_mode, args.force_closure_mode,
            args.surface_force_scale, args.pressure_force_scale,
            args.rho_force_floor, args.force_accel_cap,
        )
        momentum_macro_kernel(
            g_src, args.nx, args.ny, args.nz,
            args.momentum_mode, args.force_insertion_mode, args.rho_force_floor,
            args.momentum_density_mode, args.momentum_rho_ref,
            args.velocity_density_mode,
        )
        collide_phase_kernel(
            h_src, h_collide,
            args.nx, args.ny, args.nz,
            args.omega_h, args.width,
            args.phase_advection_mode,
            args.phase_wall_mode,
            args.phase_equation_mode,
            effective_phase_source_scale,
        )
        collide_momentum_kernel(
            g_src, g_collide, args.nx, args.ny, args.nz,
            args.momentum_mode, args.force_insertion_mode,
            args.momentum_density_mode, args.momentum_rho_ref,
            args.pressure_model,
        )
        stream_kernel(h_collide, h_stream, g_collide, g_stream, args.nx, args.ny, args.nz, args.phase_wall_mode)
        boundary_kernel(h_stream, g_stream, args.nx, args.ny, args.nz, args.phase_wall_mode)

        h_src = h_stream
        h_collide = 1 - h_src
        h_stream = h_src
        g_src = g_stream
        g_collide = 1 - g_src
        g_stream = g_src

        phase_from_h_kernel(h_src, args.nx, args.ny, args.nz)
        if args.phase_bound_mode == 2:
            mass_correction_clip_kernel(h_src, args.nx, args.ny, args.nz, args.phase_bound_mode)
            mass_correction_redistribute_kernel(h_src, args.nx, args.ny, args.nz, args.phase_bound_mode)
            phase_from_h_kernel(h_src, args.nx, args.ny, args.nz)
        else:
            phase_bound_kernel(args.nx, args.ny, args.nz, args.phase_bound_mode)
        rho_tau_kernel(args.nx, args.ny, args.nz, args.rho_l, args.rho_g, args.nu_l, args.nu_g, args.pressure_model, args.pressure_reference)
        pressure_from_g_kernel(g_src, args.nx, args.ny, args.nz, args.pressure_model)
        grad_laplace_mu_kernel(args.nx, args.ny, args.nz, args.beta, args.kappa, args.grad_eps)
        force_kernel(
            args.nx, args.ny, args.nz,
            args.body_gx, args.body_gy, args.body_gz,
            args.force_mode, args.force_closure_mode,
            args.surface_force_scale, args.pressure_force_scale,
            args.rho_force_floor, args.force_accel_cap,
        )
        momentum_macro_kernel(
            g_src, args.nx, args.ny, args.nz,
            args.momentum_mode, args.force_insertion_mode, args.rho_force_floor,
            args.momentum_density_mode, args.momentum_rho_ref,
            args.velocity_density_mode,
        )

        if step % args.output_period == 0 or step == args.steps:
            rows.append(numpy_metrics(step, h_src, g_src, mass0, args.beta, args.kappa))

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
        "phase_equation_mode": args.phase_equation_mode,
        "phase_source_scale": effective_phase_source_scale,
        "phase_source_scale_requested": args.phase_source_scale,
        "phase_source_scale_mode": args.phase_source_scale_mode,
        "phase_source_scale_description": phase_scale_info["description"],
        "phase_mobility": phase_scale_info["phase_mobility"],
        "lattice_phase_mobility": phase_scale_info["lattice_phase_mobility"],
        "phase_post_source_factor": phase_scale_info["post_source_factor"],
        "phase_effective_post_scale": phase_scale_info["effective_post_scale"],
        "wetting_mode": args.wetting_mode,
        "phase_wall_mode": args.phase_wall_mode,
        "force_mode": args.force_mode,
        "force_closure_mode": args.force_closure_mode,
        "force_insertion_mode": args.force_insertion_mode,
        "pressure_model": args.pressure_model,
        "pressure_reference": args.pressure_reference,
        "surface_force_scale": args.surface_force_scale,
        "pressure_force_scale": args.pressure_force_scale,
        "rho_force_floor": args.rho_force_floor,
        "force_accel_cap": args.force_accel_cap,
        "momentum_density_mode": args.momentum_density_mode,
        "velocity_density_mode": args.velocity_density_mode,
        "momentum_rho_ref": args.momentum_rho_ref,
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
    parser.add_argument("--phase-equation-mode", type=int, default=0, help="0 legacy source, 1 normalized CAC source, 2 moment-corrected CAC source")
    parser.add_argument("--phase-source-scale", type=float, default=1.0, help="explicit mobility/source scale multiplier for the CAC sharpening source")
    parser.add_argument("--phase-source-scale-mode", type=int, default=0, help="0 manual, 1 legacy effective strength, 2 post-collision target, 3 mobility-relative")
    parser.add_argument("--phase-mobility", type=float, default=-1.0, help="CAC mobility used by scale mode 3; negative uses cs2*(1/omega_h-0.5)")
    parser.add_argument("--phase-bound-mode", type=int, default=1)
    parser.add_argument("--wetting-mode", type=int, default=0, help="0 shadow only, 1 write C at wall band")
    parser.add_argument("--phase-wall-mode", type=int, default=0, help="0 none, 1 write h=w*Cghost at wall band, 2 neutral per-link reflect, 3 wetting per-link reconstruction")
    parser.add_argument("--force-mode", type=int, default=0, help="compatibility alias: 0 force off, 1 enables surface force if force-closure-mode is 0")
    parser.add_argument("--force-closure-mode", type=int, default=0, help="0 off, 1 surface, 2 pressure, 3 surface+pressure")
    parser.add_argument("--force-insertion-mode", type=int, default=0, help="0 none, 1 half-force+Guo, 2 half-force only, 3 Guo only")
    parser.add_argument("--pressure-model", type=int, default=0, help="0 rho*cs2, 1 rho*cs2 - reference, 2 pressure-velocity sum(g)*cs2")
    parser.add_argument("--pressure-reference", type=float, default=0.0)
    parser.add_argument("--surface-force-scale", type=float, default=1.0)
    parser.add_argument("--pressure-force-scale", type=float, default=1.0)
    parser.add_argument("--rho-force-floor", type=float, default=1.0e-12)
    parser.add_argument("--force-accel-cap", type=float, default=0.0, help="diagnostic cap on |F/rho|; 0 disables")
    parser.add_argument("--momentum-density-mode", type=int, default=0, help="0 g equilibrium uses rho(C), 1 diagnostic constant momentum density")
    parser.add_argument("--velocity-density-mode", type=int, default=0, help="0 use momentum density for u, 1 use local rho(C), 2 use max(rho(C), rho-force-floor)")
    parser.add_argument("--momentum-rho-ref", type=float, default=1.0)
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
