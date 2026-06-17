#!/usr/bin/env python3
"""Static geometry/zone/normal audit for TCLB wetting cases.

This is the C0 gate for the compact-stencil wetting repair route.  It reads a
TCLB ``case.xml`` and reconstructs the declared wall, sphere, and cylinder
solid masks without launching the solver.  The output is deliberately explicit
so another engineer can verify the geometry contract before touching the
wetting boundary implementation.

Outputs written to ``--out-dir``:

``geometry_audit.csv``
    All solid-boundary and fluid-boundary nodes with zone, angle, neighbor,
    normal, and distance diagnostics.

``wall_boundary_nodes.csv``
    Solid boundary nodes only.  ``node_type=2``.

``fluid_boundary_nodes.csv``
    Fluid boundary nodes only.  ``node_type=-1``.

``normal_comparison.csv``
    Boundary-node normal comparison subset.

``zone_angle_consistency.csv``
    Aggregated node counts by zone, target angle, and node type.

``summary.json``
    Counts, normal-error percentiles, warnings, and failure flags.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


D3Q19_OFFSETS: list[tuple[int, int, int]] = [
    (dx, dy, dz)
    for dz in (-1, 0, 1)
    for dy in (-1, 0, 1)
    for dx in (-1, 0, 1)
    if (dx, dy, dz) != (0, 0, 0) and (dx * dx + dy * dy + dz * dz) <= 2
]

D3Q27_WEIGHTS: list[tuple[int, int, int, float]] = []
for _dz in (-1, 0, 1):
    for _dy in (-1, 0, 1):
        for _dx in (-1, 0, 1):
            _r2 = _dx * _dx + _dy * _dy + _dz * _dz
            if _r2 == 0:
                _w = 8.0 / 27.0
            elif _r2 == 1:
                _w = 2.0 / 27.0
            elif _r2 == 2:
                _w = 1.0 / 54.0
            else:
                _w = 1.0 / 216.0
            D3Q27_WEIGHTS.append((_dx, _dy, _dz, _w))


@dataclass(frozen=True)
class BoxShape:
    zone: str
    x0: int
    x1: int
    y0: int
    y1: int
    z0: int
    z1: int
    nx: int
    ny: int
    nz: int


@dataclass(frozen=True)
class SphereShape:
    zone: str
    cx: float
    cy: float
    cz: float
    radius: float


@dataclass(frozen=True)
class CylinderShape:
    zone: str
    cx: float
    cy: float
    cz: float
    radius: float
    axis: int


Shape = BoxShape | SphereShape | CylinderShape


CSV_FIELDS = [
    "i",
    "j",
    "k",
    "node_type",
    "zone_id",
    "target_radAngle_deg",
    "solid_neighbor_count",
    "fluid_neighbor_count",
    "analytic_normal_x",
    "analytic_normal_y",
    "analytic_normal_z",
    "raw_mask_normal_x",
    "raw_mask_normal_y",
    "raw_mask_normal_z",
    "smooth_mask_normal_x",
    "smooth_mask_normal_y",
    "smooth_mask_normal_z",
    "TCLB_current_nw_x",
    "TCLB_current_nw_y",
    "TCLB_current_nw_z",
    "angle_error_analytic_vs_smooth",
    "angle_error_tclb_vs_smooth",
    "distance_to_sphere",
    "distance_to_outer_wall",
    "outer_wall_flag",
    "sphere_wall_flag",
    "cylinder_wall_flag",
]


def idx(x: int, y: int, z: int, nx: int, ny: int) -> int:
    return (z * ny + y) * nx + x


def in_bounds(x: int, y: int, z: int, nx: int, ny: int, nz: int) -> bool:
    return 0 <= x < nx and 0 <= y < ny and 0 <= z < nz


def parse_angle_deg(value: str | None) -> float | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith(("d", "D")):
        return float(text[:-1])
    return math.degrees(float(text))


def parse_number(value: str | None, default: float = 0.0) -> float:
    if value is None:
        return default
    text = value.strip()
    if text.endswith(("d", "D")):
        return math.radians(float(text[:-1]))
    return float(text)


def parse_int(value: str | None, default: int = 0) -> int:
    if value is None:
        return default
    return int(round(float(value)))


def axis_range(attrs: dict[str, str], axis: str, dim: int) -> tuple[int, int]:
    count_key = f"n{axis}"
    start_key = f"d{axis}"
    count_text = attrs.get(count_key)
    start_text = attrs.get(start_key)
    if count_text is None and start_text is None:
        return 0, dim
    count = parse_int(count_text, 1 if start_text is not None else dim)
    if start_text is None:
        start = 0
    else:
        raw = parse_int(start_text)
        start = dim + raw if raw < 0 else raw
    start = max(0, min(dim, start))
    end = max(start, min(dim, start + max(0, count)))
    return start, end


def box_from_xml(zone: str, attrs: dict[str, str], dims: tuple[int, int, int]) -> BoxShape:
    nx, ny, nz = dims
    x0, x1 = axis_range(attrs, "x", nx)
    y0, y1 = axis_range(attrs, "y", ny)
    z0, z1 = axis_range(attrs, "z", nz)
    return BoxShape(zone, x0, x1, y0, y1, z0, z1, nx, ny, nz)


def sphere_from_xml(zone: str, attrs: dict[str, str], params: dict[str, float]) -> SphereShape:
    if params.get("AnalyticSolidType") == 3:
        return SphereShape(
            zone,
            params.get("AnalyticSolidCenterX", 0.0),
            params.get("AnalyticSolidCenterY", 0.0),
            params.get("AnalyticSolidCenterZ", 0.0),
            params.get("AnalyticSolidRadius", 0.0),
        )
    x0 = parse_number(attrs.get("dx"), 0.0)
    y0 = parse_number(attrs.get("dy"), 0.0)
    z0 = parse_number(attrs.get("dz"), 0.0)
    sx = parse_number(attrs.get("nx"), 0.0)
    sy = parse_number(attrs.get("ny"), sx)
    sz = parse_number(attrs.get("nz"), sx)
    radius = min(sx, sy, sz) * 0.5
    return SphereShape(zone, x0 + sx * 0.5, y0 + sy * 0.5, z0 + sz * 0.5, radius)


def cylinder_from_xml(zone: str, attrs: dict[str, str], params: dict[str, float]) -> CylinderShape:
    axis = int(params.get("AnalyticSolidAxis", 2.0))
    if params.get("AnalyticSolidType") == 2:
        return CylinderShape(
            zone,
            params.get("AnalyticSolidCenterX", 0.0),
            params.get("AnalyticSolidCenterY", 0.0),
            params.get("AnalyticSolidCenterZ", 0.0),
            params.get("AnalyticSolidRadius", 0.0),
            axis,
        )
    x0 = parse_number(attrs.get("dx"), 0.0)
    y0 = parse_number(attrs.get("dy"), 0.0)
    z0 = parse_number(attrs.get("dz"), 0.0)
    sx = parse_number(attrs.get("nx"), 0.0)
    sy = parse_number(attrs.get("ny"), 0.0)
    sz = parse_number(attrs.get("nz"), 0.0)
    cx = x0 + sx * 0.5
    cy = y0 + sy * 0.5
    cz = z0 + sz * 0.5
    if axis == 0:
        radius = min(sy, sz) * 0.5
    elif axis == 1:
        radius = min(sx, sz) * 0.5
    else:
        radius = min(sx, sy) * 0.5
    return CylinderShape(zone, cx, cy, cz, radius, axis)


def parse_case_xml(path: Path) -> tuple[tuple[int, int, int], list[Shape], dict[str, float], dict[str, float], float]:
    root = ET.parse(path).getroot()
    geom = root.find("Geometry")
    if geom is None:
        raise ValueError(f"{path} has no Geometry element")
    dims = (parse_int(geom.get("nx")), parse_int(geom.get("ny")), parse_int(geom.get("nz")))

    params: dict[str, float] = {}
    rad_by_zone: dict[str, float] = {}
    default_angle = 90.0
    model = root.find("Model")
    if model is not None:
        for param in model.findall("Param"):
            name = param.get("name")
            value = param.get("value")
            if not name:
                continue
            if name == "radAngle":
                angle = parse_angle_deg(value)
                if angle is None:
                    continue
                zone = param.get("zone")
                if zone:
                    rad_by_zone[zone] = angle
                else:
                    default_angle = angle
                continue
            try:
                params[name] = parse_number(value)
            except (TypeError, ValueError):
                continue

    shapes: list[Shape] = []
    for wall in geom.findall("Wall"):
        zone = wall.get("name") or "UnnamedWall"
        for child in list(wall):
            tag = re.sub(r"^\{.*\}", "", child.tag)
            attrs = {str(k): str(v) for k, v in child.attrib.items()}
            if tag == "Box":
                shapes.append(box_from_xml(zone, attrs, dims))
            elif tag == "Sphere":
                shapes.append(sphere_from_xml(zone, attrs, params))
            elif tag == "Cylinder":
                shapes.append(cylinder_from_xml(zone, attrs, params))
    return dims, shapes, params, rad_by_zone, default_angle


def shape_signed_distance(shape: Shape, x: float, y: float, z: float) -> float:
    if isinstance(shape, SphereShape):
        return math.sqrt((x - shape.cx) ** 2 + (y - shape.cy) ** 2 + (z - shape.cz) ** 2) - shape.radius
    if isinstance(shape, CylinderShape):
        if shape.axis == 0:
            return math.sqrt((y - shape.cy) ** 2 + (z - shape.cz) ** 2) - shape.radius
        if shape.axis == 1:
            return math.sqrt((x - shape.cx) ** 2 + (z - shape.cz) ** 2) - shape.radius
        return math.sqrt((x - shape.cx) ** 2 + (y - shape.cy) ** 2) - shape.radius

    dx = 0.0 if shape.x0 <= x < shape.x1 else min(abs(x - shape.x0), abs(x - (shape.x1 - 1)))
    dy = 0.0 if shape.y0 <= y < shape.y1 else min(abs(y - shape.y0), abs(y - (shape.y1 - 1)))
    dz = 0.0 if shape.z0 <= z < shape.z1 else min(abs(z - shape.z0), abs(z - (shape.z1 - 1)))
    outside = math.sqrt(dx * dx + dy * dy + dz * dz)
    inside_margin = min(
        x - shape.x0 + 0.5,
        shape.x1 - 0.5 - x,
        y - shape.y0 + 0.5,
        shape.y1 - 0.5 - y,
        z - shape.z0 + 0.5,
        shape.z1 - 0.5 - z,
    )
    return -inside_margin if outside == 0.0 else outside


def normalize(v: tuple[float, float, float]) -> tuple[float | None, float | None, float | None]:
    mag = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if mag < 1.0e-14 or not math.isfinite(mag):
        return (None, None, None)
    return (v[0] / mag, v[1] / mag, v[2] / mag)


def shape_normal(shape: Shape, x: int, y: int, z: int) -> tuple[float | None, float | None, float | None]:
    if isinstance(shape, SphereShape):
        return normalize((x - shape.cx, y - shape.cy, z - shape.cz))
    if isinstance(shape, CylinderShape):
        if shape.axis == 0:
            return normalize((0.0, y - shape.cy, z - shape.cz))
        if shape.axis == 1:
            return normalize((x - shape.cx, 0.0, z - shape.cz))
        return normalize((x - shape.cx, y - shape.cy, 0.0))

    candidates: list[tuple[float, tuple[float, float, float]]] = []
    if shape.x1 - shape.x0 == 1:
        normal = (1.0, 0.0, 0.0) if shape.x0 == 0 else (-1.0, 0.0, 0.0)
        candidates.append((abs(x - shape.x0), normal))
    if shape.y1 - shape.y0 == 1:
        normal = (0.0, 1.0, 0.0) if shape.y0 == 0 else (0.0, -1.0, 0.0)
        candidates.append((abs(y - shape.y0), normal))
    if shape.z1 - shape.z0 == 1:
        normal = (0.0, 0.0, 1.0) if shape.z0 == 0 else (0.0, 0.0, -1.0)
        candidates.append((abs(z - shape.z0), normal))
    if not candidates:
        distances = [
            (abs(x - shape.x0), (-1.0, 0.0, 0.0)),
            (abs(x - (shape.x1 - 1)), (1.0, 0.0, 0.0)),
            (abs(y - shape.y0), (0.0, -1.0, 0.0)),
            (abs(y - (shape.y1 - 1)), (0.0, 1.0, 0.0)),
            (abs(z - shape.z0), (0.0, 0.0, -1.0)),
            (abs(z - (shape.z1 - 1)), (0.0, 0.0, 1.0)),
        ]
        candidates.append(min(distances, key=lambda item: item[0]))
    return candidates[0][1]


def assign_solids(dims: tuple[int, int, int], shapes: list[Shape]) -> tuple[bytearray, list[int], list[str]]:
    nx, ny, nz = dims
    total = nx * ny * nz
    solid = bytearray(total)
    zone_idx = [-1] * total
    zones: list[str] = []
    zone_to_idx: dict[str, int] = {}

    def zid(zone: str) -> int:
        if zone not in zone_to_idx:
            zone_to_idx[zone] = len(zones)
            zones.append(zone)
        return zone_to_idx[zone]

    for shape in shapes:
        zone_id = zid(shape.zone)
        if isinstance(shape, BoxShape):
            for z in range(shape.z0, shape.z1):
                for y in range(shape.y0, shape.y1):
                    base = idx(shape.x0, y, z, nx, ny)
                    for x in range(shape.x0, shape.x1):
                        p = base + (x - shape.x0)
                        solid[p] = 1
                        zone_idx[p] = zone_id
            continue
        for z in range(nz):
            for y in range(ny):
                for x in range(nx):
                    if shape_signed_distance(shape, x, y, z) <= 0.0:
                        p = idx(x, y, z, nx, ny)
                        solid[p] = 1
                        zone_idx[p] = zone_id
    return solid, zone_idx, zones


def solid_at(solid: bytearray, x: int, y: int, z: int, dims: tuple[int, int, int]) -> int:
    nx, ny, nz = dims
    if not in_bounds(x, y, z, nx, ny, nz):
        return 1
    return solid[idx(x, y, z, nx, ny)]


def smooth_value(solid: bytearray, x: int, y: int, z: int, dims: tuple[int, int, int]) -> float:
    value = 0.0
    for dx, dy, dz, weight in D3Q27_WEIGHTS:
        value += weight * solid_at(solid, x + dx, y + dy, z + dz, dims)
    return value


def mask_normal(solid: bytearray, x: int, y: int, z: int, dims: tuple[int, int, int], *, smooth: bool) -> tuple[float | None, float | None, float | None]:
    if smooth:
        gx = 0.5 * (smooth_value(solid, x + 1, y, z, dims) - smooth_value(solid, x - 1, y, z, dims))
        gy = 0.5 * (smooth_value(solid, x, y + 1, z, dims) - smooth_value(solid, x, y - 1, z, dims))
        gz = 0.5 * (smooth_value(solid, x, y, z + 1, dims) - smooth_value(solid, x, y, z - 1, dims))
    else:
        gx = 0.5 * (solid_at(solid, x + 1, y, z, dims) - solid_at(solid, x - 1, y, z, dims))
        gy = 0.5 * (solid_at(solid, x, y + 1, z, dims) - solid_at(solid, x, y - 1, z, dims))
        gz = 0.5 * (solid_at(solid, x, y, z + 1, dims) - solid_at(solid, x, y, z - 1, dims))
    return normalize((-gx, -gy, -gz))


def angle_between(a: tuple[float | None, float | None, float | None], b: tuple[float | None, float | None, float | None]) -> float | None:
    if any(v is None for v in a + b):
        return None
    dot = float(a[0] * b[0] + a[1] * b[1] + a[2] * b[2])  # type: ignore[operator]
    return math.degrees(math.acos(max(-1.0, min(1.0, dot))))


def nearest_shape(shapes: list[Shape], zone: str, x: int, y: int, z: int) -> Shape | None:
    candidates = [shape for shape in shapes if shape.zone == zone]
    if not candidates:
        return None
    return min(candidates, key=lambda shape: abs(shape_signed_distance(shape, x, y, z)))


def neighbor_info(
    solid: bytearray,
    zone_idx: list[int],
    zones: list[str],
    x: int,
    y: int,
    z: int,
    dims: tuple[int, int, int],
) -> tuple[int, int, str | None, tuple[float | None, float | None, float | None]]:
    nx, ny, nz = dims
    solid_neighbors = 0
    fluid_neighbors = 0
    zone_votes: Counter[str] = Counter()
    normal_sum = [0.0, 0.0, 0.0]
    current_solid = solid[idx(x, y, z, nx, ny)] > 0
    for dx, dy, dz in D3Q19_OFFSETS:
        xx, yy, zz = x + dx, y + dy, z + dz
        if not in_bounds(xx, yy, zz, nx, ny, nz):
            continue
        pp = idx(xx, yy, zz, nx, ny)
        if solid[pp]:
            solid_neighbors += 1
            zid = zone_idx[pp]
            if 0 <= zid < len(zones):
                zone_votes[zones[zid]] += 1
            if not current_solid:
                normal_sum[0] -= dx
                normal_sum[1] -= dy
                normal_sum[2] -= dz
        else:
            fluid_neighbors += 1
            if current_solid:
                normal_sum[0] += dx
                normal_sum[1] += dy
                normal_sum[2] += dz
    inherited_zone = zone_votes.most_common(1)[0][0] if zone_votes else None
    return solid_neighbors, fluid_neighbors, inherited_zone, normalize(tuple(normal_sum))


def fmt(value: float | int | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        return f"{value:.12g}"
    return str(value)


def percentile(values: list[float], q: float) -> float | None:
    clean = sorted(v for v in values if math.isfinite(v))
    if not clean:
        return None
    if len(clean) == 1:
        return clean[0]
    pos = (len(clean) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return clean[lo]
    frac = pos - lo
    return clean[lo] * (1.0 - frac) + clean[hi] * frac


def audit(case_xml: Path, out_dir: Path, metadata_path: Path | None = None) -> dict[str, Any]:
    dims, shapes, params, rad_by_zone, default_angle = parse_case_xml(case_xml)
    nx, ny, nz = dims
    solid, zone_idx, zones = assign_solids(dims, shapes)
    metadata: dict[str, Any] = {}
    if metadata_path and metadata_path.exists():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    sphere_shapes = [shape for shape in shapes if isinstance(shape, SphereShape)]
    cylinder_shapes = [shape for shape in shapes if isinstance(shape, CylinderShape)]

    rows: list[dict[str, Any]] = []
    normal_errors_as: list[float] = []
    normal_errors_ts: list[float] = []

    for z in range(nz):
        for y in range(ny):
            for x in range(nx):
                p = idx(x, y, z, nx, ny)
                solid_neighbors, fluid_neighbors, inherited_zone, tclb_n = neighbor_info(
                    solid, zone_idx, zones, x, y, z, dims
                )
                if solid[p]:
                    if fluid_neighbors == 0:
                        continue
                    node_type = 2
                    zid = zone_idx[p]
                    zone = zones[zid] if 0 <= zid < len(zones) else inherited_zone or "UnknownSolid"
                else:
                    if solid_neighbors == 0:
                        continue
                    node_type = -1
                    zone = inherited_zone or "UnknownNeighborSolid"

                shape = nearest_shape(shapes, zone, x, y, z)
                analytic_n = shape_normal(shape, x, y, z) if shape is not None else (None, None, None)
                raw_n = mask_normal(solid, x, y, z, dims, smooth=False)
                smooth_n = mask_normal(solid, x, y, z, dims, smooth=True)
                err_as = angle_between(analytic_n, smooth_n)
                err_ts = angle_between(tclb_n, smooth_n)
                if err_as is not None:
                    normal_errors_as.append(err_as)
                if err_ts is not None:
                    normal_errors_ts.append(err_ts)

                dist_sphere = min((shape_signed_distance(shape, x, y, z) for shape in sphere_shapes), default=None)
                dist_outer = min(x, y, z, nx - 1 - x, ny - 1 - y, nz - 1 - z)
                target_angle = rad_by_zone.get(zone, default_angle)
                row = {
                    "i": x,
                    "j": y,
                    "k": z,
                    "node_type": node_type,
                    "zone_id": zone,
                    "target_radAngle_deg": target_angle,
                    "solid_neighbor_count": solid_neighbors,
                    "fluid_neighbor_count": fluid_neighbors,
                    "analytic_normal_x": analytic_n[0],
                    "analytic_normal_y": analytic_n[1],
                    "analytic_normal_z": analytic_n[2],
                    "raw_mask_normal_x": raw_n[0],
                    "raw_mask_normal_y": raw_n[1],
                    "raw_mask_normal_z": raw_n[2],
                    "smooth_mask_normal_x": smooth_n[0],
                    "smooth_mask_normal_y": smooth_n[1],
                    "smooth_mask_normal_z": smooth_n[2],
                    "TCLB_current_nw_x": tclb_n[0],
                    "TCLB_current_nw_y": tclb_n[1],
                    "TCLB_current_nw_z": tclb_n[2],
                    "angle_error_analytic_vs_smooth": err_as,
                    "angle_error_tclb_vs_smooth": err_ts,
                    "distance_to_sphere": dist_sphere,
                    "distance_to_outer_wall": dist_outer,
                    "outer_wall_flag": 1 if "outer" in zone.lower() else 0,
                    "sphere_wall_flag": 1 if "sphere" in zone.lower() or isinstance(shape, SphereShape) else 0,
                    "cylinder_wall_flag": 1 if "cyl" in zone.lower() or isinstance(shape, CylinderShape) else 0,
                }
                rows.append(row)

    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "geometry_audit.csv", rows)
    write_csv(out_dir / "wall_boundary_nodes.csv", [row for row in rows if row["node_type"] == 2])
    write_csv(out_dir / "fluid_boundary_nodes.csv", [row for row in rows if row["node_type"] == -1])
    write_csv(out_dir / "normal_comparison.csv", rows)

    aggregates: dict[tuple[str, int, float], int] = defaultdict(int)
    for row in rows:
        aggregates[(str(row["zone_id"]), int(row["node_type"]), float(row["target_radAngle_deg"]))] += 1
    zone_rows = [
        {
            "zone_id": zone,
            "node_type": node_type,
            "target_radAngle_deg": angle,
            "count": count,
            "outer_wall_flag": 1 if "outer" in zone.lower() else 0,
            "sphere_wall_flag": 1 if "sphere" in zone.lower() else 0,
            "cylinder_wall_flag": 1 if "cyl" in zone.lower() else 0,
        }
        for (zone, node_type, angle), count in sorted(aggregates.items())
    ]
    write_csv(out_dir / "zone_angle_consistency.csv", zone_rows, fields=[
        "zone_id",
        "node_type",
        "target_radAngle_deg",
        "count",
        "outer_wall_flag",
        "sphere_wall_flag",
        "cylinder_wall_flag",
    ])

    node_counts = Counter(str(row["node_type"]) for row in rows)
    zone_counts = Counter(str(row["zone_id"]) for row in rows)
    warnings: list[str] = []
    failures: list[str] = []
    if not rows:
        failures.append("no_boundary_nodes_detected")
    target_zone = metadata.get("target_wall_zone")
    if target_zone and target_zone not in zone_counts:
        failures.append(f"target_zone_missing_from_boundary_nodes:{target_zone}")
    if percentile(normal_errors_as, 0.95) is None:
        warnings.append("no analytic-vs-smooth normal comparisons were available")
    elif percentile(normal_errors_as, 0.95) > 35.0:
        warnings.append("analytic-vs-smooth normal p95 exceeds 35 deg; inspect normal_comparison.csv")

    summary = {
        "status": "FAIL" if failures else "PASS_C0_STATIC_GEOMETRY_AUDIT",
        "claim_limit": "geometry audit only; not wetting validation",
        "case_xml": str(case_xml),
        "metadata_path": str(metadata_path) if metadata_path else None,
        "out_dir": str(out_dir),
        "grid": [nx, ny, nz],
        "total_cells": nx * ny * nz,
        "solid_cells": int(sum(1 for value in solid if value)),
        "fluid_cells": int(sum(1 for value in solid if not value)),
        "boundary_node_counts": dict(node_counts),
        "zone_boundary_counts": dict(zone_counts),
        "radAngle_default_deg": default_angle,
        "radAngle_by_zone_deg": rad_by_zone,
        "analytic_params": params,
        "shape_count": len(shapes),
        "shape_zones": [shape.zone for shape in shapes],
        "normal_error_analytic_vs_smooth_deg": {
            "count": len(normal_errors_as),
            "p50": percentile(normal_errors_as, 0.50),
            "p95": percentile(normal_errors_as, 0.95),
            "max": max(normal_errors_as) if normal_errors_as else None,
        },
        "normal_error_tclb_vs_smooth_deg": {
            "count": len(normal_errors_ts),
            "p50": percentile(normal_errors_ts, 0.50),
            "p95": percentile(normal_errors_ts, 0.95),
            "max": max(normal_errors_ts) if normal_errors_ts else None,
        },
        "failures": failures,
        "warnings": warnings,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    fields = fields or CSV_FIELDS
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: fmt(row.get(field)) for field in fields})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_xml", type=Path)
    parser.add_argument("--metadata", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = args.out_dir or (args.case_xml.parent / "geometry_audit")
    summary = audit(args.case_xml, out_dir, args.metadata)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"].startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
