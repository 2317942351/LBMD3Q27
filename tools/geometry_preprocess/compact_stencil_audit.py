#!/usr/bin/env python3
"""Deterministic C1b-unit audit for compact-stencil wetting interpolation.

This tool does not launch TCLB and does not write any solver field.  It turns
the Sugimoto-style compact-stencil contract into an executable geometry test:

* search the seven plane families;
* accept only three physical fluid vertices;
* require coordinate span <= one lattice spacing;
* require the wall-normal intersection point to lie inside the triangle;
* choose the valid candidate with the smallest normal-line distance.

The output is intended to catch algorithmic mistakes before the same contract
is moved into ``Boundary.c.Rt``.
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


Int3 = tuple[int, int, int]
Vec3 = tuple[float, float, float]

PLANE_FAMILIES: list[tuple[int, str, Int3]] = [
    (1, "x=Lx", (1, 0, 0)),
    (2, "y=Ly", (0, 1, 0)),
    (3, "z=Lz", (0, 0, 1)),
    (4, "x+y=Lxy", (1, 1, 0)),
    (5, "y+z=Lyz", (0, 1, 1)),
    (6, "z+x=Lzx", (1, 0, 1)),
    (7, "x+y+z=Lxyz", (1, 1, 1)),
]

CSV_FIELDS = [
    "case",
    "status",
    "method_complete",
    "fallback_reason",
    "solid_node_x",
    "solid_node_y",
    "solid_node_z",
    "normal_x",
    "normal_y",
    "normal_z",
    "plane_id",
    "plane_name",
    "plane_l",
    "candidate_count",
    "all_fluid_triangle_count",
    "inside_triangle_count",
    "q_clean_triangle_count",
    "fluid_vertex_count",
    "plane_fluid_node_count",
    "bary_min",
    "bary_max",
    "d_s",
    "d_line",
    "d_f",
    "q_f",
    "q_s_raw",
    "q_s_bounded",
    "q_w",
    "residual",
    "root_choice",
    "bounded_delta",
    "incremental_equivalent",
    "incremental_plane_id",
    "incremental_plane_l",
    "incremental_d_line",
]


@dataclass(frozen=True)
class SearchInput:
    name: str
    dims: Int3
    solid: bytearray
    q_field: list[float]
    solid_node: Int3
    normal: Vec3
    d_s: float
    theta_deg: float = 90.0
    interface_width: float = 4.0


@dataclass(frozen=True)
class StencilCandidate:
    plane_id: int
    plane_name: str
    plane_l: int
    t_line: float
    f_local: Vec3
    vertices_local: tuple[Int3, Int3, Int3]
    vertices_global: tuple[Int3, Int3, Int3]
    bary: Vec3
    q_f: float
    centroid_distance: float
    plane_fluid_node_count: int


@dataclass(frozen=True)
class SearchResult:
    method_complete: bool
    fallback_reason: str
    candidate_count: int
    all_fluid_triangle_count: int
    q_clean_triangle_count: int
    inside_triangle_count: int
    best: StencilCandidate | None


@dataclass(frozen=True)
class PlaneScan:
    candidate_count: int
    all_fluid_triangle_count: int
    q_clean_triangle_count: int
    inside_triangle_count: int
    candidates: list[StencilCandidate]


def flat_index(node: Int3, dims: Int3) -> int:
    x, y, z = node
    nx, ny, _nz = dims
    return (z * ny + y) * nx + x


def in_bounds(node: Int3, dims: Int3) -> bool:
    x, y, z = node
    nx, ny, nz = dims
    return 0 <= x < nx and 0 <= y < ny and 0 <= z < nz


def normalize(v: Vec3) -> Vec3 | None:
    mag = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if mag <= 1.0e-14 or not math.isfinite(mag):
        return None
    return (v[0] / mag, v[1] / mag, v[2] / mag)


def dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def mul(a: Vec3, s: float) -> Vec3:
    return (a[0] * s, a[1] * s, a[2] * s)


def norm(a: Vec3) -> float:
    return math.sqrt(dot(a, a))


def signs_from_normal(normal: Vec3) -> Int3:
    return (
        -1 if normal[0] < 0.0 else 1,
        -1 if normal[1] < 0.0 else 1,
        -1 if normal[2] < 0.0 else 1,
    )


def local_to_global(solid_node: Int3, signs: Int3, local: Int3) -> Int3:
    return (
        solid_node[0] + signs[0] * local[0],
        solid_node[1] + signs[1] * local[1],
        solid_node[2] + signs[2] * local[2],
    )


def is_fluid(node: Int3, dims: Int3, solid: bytearray) -> bool:
    if not in_bounds(node, dims):
        return False
    return solid[flat_index(node, dims)] == 0


def q_at(node: Int3, dims: Int3, q_field: list[float]) -> float:
    return q_field[flat_index(node, dims)]


def is_clean_q(value: float) -> bool:
    return math.isfinite(value) and value > -100.0


def barycentric(point: Vec3, a: Vec3, b: Vec3, c: Vec3) -> Vec3 | None:
    v0 = sub(b, a)
    v1 = sub(c, a)
    v2 = sub(point, a)
    d00 = dot(v0, v0)
    d01 = dot(v0, v1)
    d11 = dot(v1, v1)
    d20 = dot(v2, v0)
    d21 = dot(v2, v1)
    denom = d00 * d11 - d01 * d01
    if abs(denom) <= 1.0e-14:
        return None
    v = (d11 * d20 - d01 * d21) / denom
    w = (d00 * d21 - d01 * d20) / denom
    u = 1.0 - v - w
    return (u, v, w)


def point_in_triangle(bary: Vec3, tol: float) -> bool:
    return min(bary) >= -tol and max(bary) <= 1.0 + tol


def coordinate_span_ok(vertices: tuple[Int3, Int3, Int3]) -> bool:
    for axis in range(3):
        values = [vertex[axis] for vertex in vertices]
        if max(values) - min(values) > 1:
            return False
    return True


def nearby_plane_nodes(f_local: Vec3, coeff: Int3, plane_l: int) -> list[Int3]:
    ranges: list[range] = []
    for value in f_local:
        lo = max(0, math.floor(value) - 1)
        hi = max(lo, math.ceil(value) + 1)
        ranges.append(range(lo, hi + 1))
    nodes: list[Int3] = []
    for node in itertools.product(*ranges):
        if coeff[0] * node[0] + coeff[1] * node[1] + coeff[2] * node[2] != plane_l:
            continue
        nodes.append((int(node[0]), int(node[1]), int(node[2])))
    nodes.sort()
    return nodes


def interpolate_q(vertices_global: tuple[Int3, Int3, Int3], bary: Vec3, dims: Int3, q_field: list[float]) -> float:
    return sum(weight * q_at(node, dims, q_field) for weight, node in zip(bary, vertices_global))


def collect_plane_candidates(
    data: SearchInput,
    *,
    signs: Int3,
    plane_id: int,
    plane_name: str,
    coeff: Int3,
    plane_l: int,
    t_line: float,
    f_local: Vec3,
    bary_tol: float,
) -> PlaneScan:
    plane_nodes = nearby_plane_nodes(f_local, coeff, plane_l)
    plane_fluid_node_count = sum(
        1
        for local_node in plane_nodes
        if is_fluid(local_to_global(data.solid_node, signs, local_node), data.dims, data.solid)
    )
    candidates: list[StencilCandidate] = []
    candidate_count = 0
    all_fluid_triangle_count = 0
    q_clean_triangle_count = 0
    inside_triangle_count = 0
    for vertices_local in itertools.combinations(plane_nodes, 3):
        if not coordinate_span_ok(vertices_local):
            continue
        candidate_count += 1
        vertices_global = tuple(
            local_to_global(data.solid_node, signs, vertex) for vertex in vertices_local
        )
        if not all(is_fluid(node, data.dims, data.solid) for node in vertices_global):
            continue
        all_fluid_triangle_count += 1
        vertex_q = [q_at(node, data.dims, data.q_field) for node in vertices_global]
        if not all(is_clean_q(value) for value in vertex_q):
            continue
        q_clean_triangle_count += 1
        bary = barycentric(
            f_local,
            tuple(float(v) for v in vertices_local[0]),
            tuple(float(v) for v in vertices_local[1]),
            tuple(float(v) for v in vertices_local[2]),
        )
        if bary is None or not point_in_triangle(bary, bary_tol):
            continue
        inside_triangle_count += 1
        q_f = sum(weight * value for weight, value in zip(bary, vertex_q))
        centroid = (
            sum(v[0] for v in vertices_local) / 3.0,
            sum(v[1] for v in vertices_local) / 3.0,
            sum(v[2] for v in vertices_local) / 3.0,
        )
        candidates.append(
            StencilCandidate(
                plane_id=plane_id,
                plane_name=plane_name,
                plane_l=plane_l,
                t_line=t_line,
                f_local=f_local,
                vertices_local=vertices_local,
                vertices_global=vertices_global,  # type: ignore[arg-type]
                bary=bary,
                q_f=q_f,
                centroid_distance=norm(sub(centroid, f_local)),
                plane_fluid_node_count=plane_fluid_node_count,
            )
        )
    return PlaneScan(
        candidate_count=candidate_count,
        all_fluid_triangle_count=all_fluid_triangle_count,
        q_clean_triangle_count=q_clean_triangle_count,
        inside_triangle_count=inside_triangle_count,
        candidates=candidates,
    )


def search_compact_stencil(
    data: SearchInput,
    *,
    max_l: int,
    bary_tol: float = 1.0e-10,
) -> SearchResult:
    normal = normalize(data.normal)
    if normal is None:
        return SearchResult(False, "invalid_normal", 0, 0, 0, None)

    signs = signs_from_normal(normal)
    normal_abs = (abs(normal[0]), abs(normal[1]), abs(normal[2]))
    candidates: list[StencilCandidate] = []
    candidate_count = 0
    all_fluid_triangle_count = 0
    q_clean_triangle_count = 0
    inside_triangle_count = 0

    for plane_id, plane_name, coeff in PLANE_FAMILIES:
        denom = coeff[0] * normal_abs[0] + coeff[1] * normal_abs[1] + coeff[2] * normal_abs[2]
        if denom <= 1.0e-14:
            continue
        for plane_l in range(1, max_l + 1):
            t_line = plane_l / denom
            f_local = mul(normal_abs, t_line)
            scan = collect_plane_candidates(
                data,
                signs=signs,
                plane_id=plane_id,
                plane_name=plane_name,
                coeff=coeff,
                plane_l=plane_l,
                t_line=t_line,
                f_local=f_local,
                bary_tol=bary_tol,
            )
            candidate_count += scan.candidate_count
            all_fluid_triangle_count += scan.all_fluid_triangle_count
            q_clean_triangle_count += scan.q_clean_triangle_count
            inside_triangle_count += scan.inside_triangle_count
            candidates.extend(scan.candidates)

    if not candidates:
        if all_fluid_triangle_count == 0:
            reason = "no_all_fluid_triangle"
        elif q_clean_triangle_count == 0:
            reason = "no_clean_q_triangle"
        else:
            reason = "no_inside_triangle"
        return SearchResult(False, reason, candidate_count, all_fluid_triangle_count, q_clean_triangle_count, inside_triangle_count, None)

    best = min(candidates, key=lambda item: (max(0.0, item.t_line - data.d_s), item.centroid_distance, item.plane_id, item.plane_l))
    return SearchResult(True, "ok", candidate_count, all_fluid_triangle_count, q_clean_triangle_count, inside_triangle_count, best)


def search_compact_stencil_incremental(
    data: SearchInput,
    *,
    max_l: int,
    bary_tol: float = 1.0e-10,
) -> SearchResult:
    """Reference the paper's nearest-plane/increment-L search procedure.

    The production helper may use an exhaustive search if it gives the same
    minimum-distance accepted candidate. This reference implementation exists
    to prove that equivalence case by case.
    """
    normal = normalize(data.normal)
    if normal is None:
        return SearchResult(False, "invalid_normal", 0, 0, 0, None)

    signs = signs_from_normal(normal)
    normal_abs = (abs(normal[0]), abs(normal[1]), abs(normal[2]))
    plane_l_by_id = {plane_id: 1 for plane_id, _plane_name, _coeff in PLANE_FAMILIES}
    candidate_count = 0
    all_fluid_triangle_count = 0
    q_clean_triangle_count = 0
    inside_triangle_count = 0

    while True:
        active: list[tuple[float, int, str, Int3, int, Vec3]] = []
        for plane_id, plane_name, coeff in PLANE_FAMILIES:
            plane_l = plane_l_by_id[plane_id]
            if plane_l > max_l:
                continue
            denom = coeff[0] * normal_abs[0] + coeff[1] * normal_abs[1] + coeff[2] * normal_abs[2]
            if denom <= 1.0e-14:
                plane_l_by_id[plane_id] = max_l + 1
                continue
            t_line = plane_l / denom
            active.append((t_line, plane_id, plane_name, coeff, plane_l, mul(normal_abs, t_line)))
        if not active:
            if all_fluid_triangle_count == 0:
                reason = "no_all_fluid_triangle"
            elif q_clean_triangle_count == 0:
                reason = "no_clean_q_triangle"
            else:
                reason = "no_inside_triangle"
            return SearchResult(
                False,
                reason,
                candidate_count,
                all_fluid_triangle_count,
                q_clean_triangle_count,
                inside_triangle_count,
                None,
            )

        t_line, plane_id, plane_name, coeff, plane_l, f_local = min(active, key=lambda item: (item[0], item[1]))
        scan = collect_plane_candidates(
            data,
            signs=signs,
            plane_id=plane_id,
            plane_name=plane_name,
            coeff=coeff,
            plane_l=plane_l,
            t_line=t_line,
            f_local=f_local,
            bary_tol=bary_tol,
        )
        candidate_count += scan.candidate_count
        all_fluid_triangle_count += scan.all_fluid_triangle_count
        q_clean_triangle_count += scan.q_clean_triangle_count
        inside_triangle_count += scan.inside_triangle_count

        if scan.candidates:
            best = min(scan.candidates, key=lambda item: (item.centroid_distance, item.plane_id, item.plane_l))
            return SearchResult(
                True,
                "ok",
                candidate_count,
                all_fluid_triangle_count,
                q_clean_triangle_count,
                inside_triangle_count,
                best,
            )
        plane_l_by_id[plane_id] = plane_l + 1


def stencil_results_equivalent(a: SearchResult, b: SearchResult, *, tol: float = 1.0e-10) -> bool:
    if a.method_complete != b.method_complete:
        return False
    if a.best is None or b.best is None:
        return a.best is None and b.best is None
    return (
        a.best.plane_id == b.best.plane_id
        and a.best.plane_l == b.best.plane_l
        and abs(a.best.t_line - b.best.t_line) <= tol
        and abs(a.best.q_f - b.best.q_f) <= tol
        and a.best.vertices_global == b.best.vertices_global
    )


def contact_residual(q_s: float, q_f: float, d_s: float, d_f: float, theta_deg: float, width: float) -> float:
    d = d_s + d_f
    if d <= 0.0 or width <= 0.0:
        return math.nan
    q_w = (d_s * q_f + d_f * q_s) / d
    lhs = (q_f - q_s) / d
    rhs = -(4.0 / width) * q_w * (1.0 - q_w) * math.cos(math.radians(theta_deg))
    return lhs - rhs


def solve_qs(q_f: float, d_s: float, d_f: float, theta_deg: float, width: float, bound_eps: float = 1.0e-8) -> dict[str, Any]:
    d = d_s + d_f
    if d <= 0.0 or width <= 0.0:
        return {"valid": False, "fallback_reason": "invalid_distance_or_width"}
    cos_theta = math.cos(math.radians(theta_deg))
    if abs(cos_theta) <= 1.0e-12:
        q_s = q_f
        return {
            "valid": True,
            "q_s_raw": q_s,
            "q_s_bounded": min(max(q_s, -bound_eps), 1.0 + bound_eps),
            "q_w": q_f,
            "residual": 0.0,
            "discriminant": 0.0,
            "root_choice": "neutral_90",
            "bounded_delta": 0.0,
            "fallback_reason": "neutral_90",
        }

    a_dist = d_s
    b_dist = d_f
    c = a_dist * q_f
    k = -(4.0 / width) * cos_theta
    aa = k * b_dist * b_dist
    bb = -d - k * b_dist * (d - 2.0 * c)
    cc = q_f * d - k * c * (d - c)
    if abs(aa) <= 1.0e-14:
        if abs(bb) <= 1.0e-14:
            return {"valid": False, "fallback_reason": "degenerate_equation"}
        roots = [-cc / bb]
        disc = 0.0
    else:
        disc = bb * bb - 4.0 * aa * cc
        if disc < -1.0e-12:
            return {"valid": False, "fallback_reason": "negative_discriminant", "discriminant": disc}
        disc = max(0.0, disc)
        sqrt_disc = math.sqrt(disc)
        roots = [(-bb - sqrt_disc) / (2.0 * aa), (-bb + sqrt_disc) / (2.0 * aa)]

    in_bounds_roots = [root for root in roots if -bound_eps <= root <= 1.0 + bound_eps]
    chosen_from = in_bounds_roots if in_bounds_roots else roots
    q_s = min(chosen_from, key=lambda root: (abs(root - q_f), abs(contact_residual(root, q_f, d_s, d_f, theta_deg, width))))
    q_s_bounded = min(max(q_s, -bound_eps), 1.0 + bound_eps)
    q_w = (d_s * q_f + d_f * q_s) / d
    return {
        "valid": True,
        "q_s_raw": q_s,
        "q_s_bounded": q_s_bounded,
        "q_w": q_w,
        "residual": contact_residual(q_s, q_f, d_s, d_f, theta_deg, width),
        "discriminant": disc,
        "root_choice": "bounded_root" if in_bounds_roots else "nearest_root_out_of_bounds",
        "bounded_delta": abs(q_s_bounded - q_s),
        "fallback_reason": "ok" if in_bounds_roots else "roots_out_of_bounds",
    }


def make_field(dims: Int3, q_func: Callable[[int, int, int], float]) -> list[float]:
    nx, ny, nz = dims
    q_field = [0.0] * (nx * ny * nz)
    for z in range(nz):
        for y in range(ny):
            for x in range(nx):
                q_field[flat_index((x, y, z), dims)] = q_func(x, y, z)
    return q_field


def make_solid(dims: Int3, solid_func: Callable[[int, int, int], bool]) -> bytearray:
    nx, ny, nz = dims
    solid = bytearray(nx * ny * nz)
    for z in range(nz):
        for y in range(ny):
            for x in range(nx):
                solid[flat_index((x, y, z), dims)] = 1 if solid_func(x, y, z) else 0
    return solid


def synthetic_cases() -> list[SearchInput]:
    q_func = lambda x, y, z: 0.2 + 0.01 * x + 0.02 * y + 0.03 * z

    flat_dims = (8, 8, 8)
    flat_solid = make_solid(flat_dims, lambda _x, y, _z: y == 0)
    four_node_solid = make_solid(
        flat_dims,
        lambda x, y, z: y == 0 or (y == 1 and z == 5 and x in (3, 4)),
    )

    sphere_dims = (15, 15, 15)
    sphere_center = (7.0, 7.0, 7.0)
    sphere_radius = 4.0
    sphere_solid = make_solid(
        sphere_dims,
        lambda x, y, z: math.sqrt((x - sphere_center[0]) ** 2 + (y - sphere_center[1]) ** 2 + (z - sphere_center[2]) ** 2) <= sphere_radius,
    )
    sphere_node = (10, 9, 7)
    sphere_normal = normalize((sphere_node[0] - sphere_center[0], sphere_node[1] - sphere_center[1], 0.0))
    if sphere_normal is None:
        raise RuntimeError("invalid synthetic sphere normal")
    sphere_3d_node = (10, 9, 8)
    sphere_3d_normal = normalize(
        (
            sphere_3d_node[0] - sphere_center[0],
            sphere_3d_node[1] - sphere_center[1],
            sphere_3d_node[2] - sphere_center[2],
        )
    )
    if sphere_3d_normal is None:
        raise RuntimeError("invalid synthetic 3D sphere normal")

    cyl_dims = (15, 15, 15)
    cyl_center = (7.0, 7.0)
    cyl_radius = 4.0
    cyl_solid = make_solid(
        cyl_dims,
        lambda x, y, _z: math.sqrt((x - cyl_center[0]) ** 2 + (y - cyl_center[1]) ** 2) <= cyl_radius,
    )
    cyl_node = (10, 9, 7)
    cyl_normal = normalize((cyl_node[0] - cyl_center[0], cyl_node[1] - cyl_center[1], 0.0))
    if cyl_normal is None:
        raise RuntimeError("invalid synthetic cylinder normal")

    fallback_dims = (6, 6, 6)
    fallback_solid = make_solid(fallback_dims, lambda _x, _y, _z: True)
    fallback_q = make_field(fallback_dims, q_func)

    sentinel_dims = (8, 8, 8)
    sentinel_solid = make_solid(sentinel_dims, lambda _x, y, _z: y == 0 or y == 1)
    sentinel_q = make_field(sentinel_dims, q_func)
    for x, z in [(3, 2), (3, 3), (4, 2), (4, 3)]:
        sentinel_q[flat_index((x, 2, z), sentinel_dims)] = -999.0

    return [
        SearchInput(
            name="flat_wall_y_plus",
            dims=flat_dims,
            solid=flat_solid,
            q_field=make_field(flat_dims, q_func),
            solid_node=(3, 0, 3),
            normal=(0.0, 1.0, 0.0),
            d_s=0.5,
            theta_deg=90.0,
        ),
        SearchInput(
            name="four_node_plane_triangle_selection",
            dims=flat_dims,
            solid=four_node_solid,
            q_field=make_field(flat_dims, q_func),
            solid_node=(3, 0, 3),
            normal=(0.0, 1.0, 0.25),
            d_s=0.5,
            theta_deg=90.0,
        ),
        SearchInput(
            name="sphere_diagonal",
            dims=sphere_dims,
            solid=sphere_solid,
            q_field=make_field(sphere_dims, q_func),
            solid_node=sphere_node,
            normal=sphere_normal,
            d_s=0.5,
            theta_deg=30.0,
        ),
        SearchInput(
            name="sphere_full_3d_diagonal",
            dims=sphere_dims,
            solid=sphere_solid,
            q_field=make_field(sphere_dims, q_func),
            solid_node=sphere_3d_node,
            normal=sphere_3d_normal,
            d_s=0.5,
            theta_deg=30.0,
        ),
        SearchInput(
            name="cylinder_z_diagonal",
            dims=cyl_dims,
            solid=cyl_solid,
            q_field=make_field(cyl_dims, q_func),
            solid_node=cyl_node,
            normal=cyl_normal,
            d_s=0.5,
            theta_deg=150.0,
        ),
        SearchInput(
            name="fallback_no_fluid_vertices",
            dims=fallback_dims,
            solid=fallback_solid,
            q_field=fallback_q,
            solid_node=(3, 3, 3),
            normal=(0.0, 1.0, 0.0),
            d_s=0.5,
            theta_deg=90.0,
        ),
        SearchInput(
            name="q_hygiene_reject_sentinel_vertices",
            dims=sentinel_dims,
            solid=sentinel_solid,
            q_field=sentinel_q,
            solid_node=(3, 1, 3),
            normal=(0.0, 1.0, 0.0),
            d_s=0.5,
            theta_deg=90.0,
        ),
    ]


def result_row(data: SearchInput, result: SearchResult) -> dict[str, Any]:
    row: dict[str, Any] = {
        "case": data.name,
        "status": "PASS" if result.method_complete else "EXPECTED_FALLBACK" if data.name.startswith("fallback_") else "FAIL",
        "method_complete": int(result.method_complete),
        "fallback_reason": result.fallback_reason,
        "solid_node_x": data.solid_node[0],
        "solid_node_y": data.solid_node[1],
        "solid_node_z": data.solid_node[2],
        "normal_x": data.normal[0],
        "normal_y": data.normal[1],
        "normal_z": data.normal[2],
        "candidate_count": result.candidate_count,
        "all_fluid_triangle_count": result.all_fluid_triangle_count,
        "q_clean_triangle_count": result.q_clean_triangle_count,
        "inside_triangle_count": result.inside_triangle_count,
    }
    if result.best is None:
        return row
    best = result.best
    d_f = max(0.0, best.t_line - data.d_s)
    solve = solve_qs(best.q_f, data.d_s, d_f, data.theta_deg, data.interface_width)
    row.update(
        {
            "plane_id": best.plane_id,
            "plane_name": best.plane_name,
            "plane_l": best.plane_l,
            "fluid_vertex_count": 3,
            "plane_fluid_node_count": best.plane_fluid_node_count,
            "bary_min": min(best.bary),
            "bary_max": max(best.bary),
            "d_s": data.d_s,
            "d_line": best.t_line,
            "d_f": d_f,
            "q_f": best.q_f,
            "q_s_raw": solve.get("q_s_raw"),
            "q_s_bounded": solve.get("q_s_bounded"),
            "q_w": solve.get("q_w"),
            "residual": solve.get("residual"),
            "root_choice": solve.get("root_choice"),
            "bounded_delta": solve.get("bounded_delta"),
            "vertices_local": best.vertices_local,
            "vertices_global": best.vertices_global,
            "barycentric": best.bary,
        }
    )
    if solve.get("fallback_reason") not in (None, "ok", "neutral_90"):
        row["contact_solve_warning"] = solve.get("fallback_reason")
    return row


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        return f"{value:.12g}"
    if isinstance(value, (tuple, list)):
        return json.dumps(value)
    return str(value)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(CSV_FIELDS)
    extra_fields = sorted({key for row in rows for key in row if key not in fields})
    fields.extend(extra_fields)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: fmt(row.get(field)) for field in fields})


def run_audit(out_dir: Path, *, max_l: int) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    equivalence_failures: list[str] = []
    for data in synthetic_cases():
        result = search_compact_stencil(data, max_l=max_l)
        incremental_result = search_compact_stencil_incremental(data, max_l=max_l)
        row = result_row(data, result)
        equivalent = stencil_results_equivalent(result, incremental_result)
        row["incremental_equivalent"] = int(equivalent)
        if incremental_result.best is not None:
            row["incremental_plane_id"] = incremental_result.best.plane_id
            row["incremental_plane_l"] = incremental_result.best.plane_l
            row["incremental_d_line"] = incremental_result.best.t_line
        rows.append(row)
        if not equivalent:
            equivalence_failures.append(data.name)
        if data.name.startswith("fallback_"):
            if result.method_complete:
                failures.append(f"{data.name}:expected_fallback_but_completed")
        elif not result.method_complete:
            failures.append(f"{data.name}:{result.fallback_reason}")
        elif data.name.startswith("q_hygiene_") and row.get("plane_l") == 1:
            failures.append(f"{data.name}:selected_sentinel_contaminated_nearest_layer")
        elif data.name == "four_node_plane_triangle_selection":
            if row.get("plane_fluid_node_count") != 4:
                failures.append(f"{data.name}:did_not_exercise_four_node_plane")
            if row.get("fluid_vertex_count") != 3:
                failures.append(f"{data.name}:did_not_select_three_vertex_triangle")

    write_csv(out_dir / "compact_stencil_unit_audit.csv", rows)
    failures.extend(f"{name}:incremental_search_mismatch" for name in equivalence_failures)
    summary = {
        "status": "FAIL" if failures else "PASS_C1B_UNIT_STENCIL_AUDIT",
        "claim_limit": "deterministic stencil audit only; not solver validation",
        "out_dir": str(out_dir),
        "max_l": max_l,
        "case_count": len(rows),
        "method_complete_count": sum(1 for row in rows if int(row.get("method_complete", 0)) == 1),
        "expected_fallback_count": sum(1 for row in rows if str(row.get("status")) == "EXPECTED_FALLBACK"),
        "incremental_equivalence_failures": equivalence_failures,
        "four_node_triangle_case_count": sum(
            1 for row in rows if int(row.get("plane_fluid_node_count") or 0) == 4
        ),
        "failures": failures,
        "rows": rows,
    }
    (out_dir / "compact_stencil_unit_audit.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=Path("artifacts/stage13_compact_stencil_unit_audit"))
    parser.add_argument("--max-l", type=int, default=3)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_audit(args.out_dir, max_l=args.max_l)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"].startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
