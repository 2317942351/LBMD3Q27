#!/usr/bin/env python3
"""Summarize Track A usable-angle shadow metrics from lightweight files.

This script does not read raw VTI/PVTI/PRI/VTK fields. Missing runtime metrics
are reported as pending/unknown; values are never fabricated.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


STATUS = "runtime_sanity"
CLAIM_LIMIT = "runtime_sanity / exploratory_not_validation only"
SUMMARY_DIR = Path("artifacts") / "track_a_usable_angle_ladder_summary_20260613"
MANIFEST = Path("cases") / "track_a_usable_angle_ladder_20260613" / "manifest.json"

PASS_MAX_MACH_DEFAULT = 1.0e-3
WP1_CASE_FILTERS = {"plane030", "plane060", "plane090", "plane120", "plane020"}
WP1_PRIMARY_CASES = {"track_a_plane_theta030_shadow", "track_a_plane_theta060_shadow", "track_a_plane_theta090_shadow", "track_a_plane_theta120_shadow"}
WP1_SMOKE_CASES = {"track_a_plane_theta030_shadow", "track_a_plane_theta090_shadow"}


def unknown() -> str:
    return "unknown"


def is_unknown_value(value: Any) -> bool:
    return value is None or value == "" or value == unknown()


def clean(value: Any) -> Any:
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean(v) for v in value]
    return value


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_first_row(path: Path) -> dict[str, Any]:
    with path.open("r", newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    return rows[-1] if rows else {}


def load_metric_file(case_id: str, metrics_root: Path) -> tuple[dict[str, Any], str | None]:
    candidates = [
        metrics_root / case_id / "track_a_metrics.json",
        metrics_root / case_id / "metrics.json",
        metrics_root / f"{case_id}.json",
        metrics_root / case_id / "track_a_metrics.csv",
        metrics_root / case_id / "metrics.csv",
        metrics_root / f"{case_id}.csv",
    ]
    for path in candidates:
        if not path.exists():
            continue
        if path.suffix.lower() == ".json":
            return read_json(path), str(path)
        if path.suffix.lower() == ".csv":
            return read_csv_first_row(path), str(path)
    return {}, None


def load_case_xml(case_id: str, metrics_root: Path) -> tuple[dict[str, Any], str | None]:
    path = metrics_root / case_id / "case.xml"
    if not path.exists():
        return {}, None
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return {"xml_parse_error": True}, str(path)
    params: dict[str, Any] = {}
    for elem in root.findall(".//Param"):
        name = elem.attrib.get("name")
        value = elem.attrib.get("value")
        zone = elem.attrib.get("zone")
        if not name:
            continue
        key = name if zone is None else f"{name}:{zone}"
        params[key] = value
    geometry = root.find(".//Geometry")
    if geometry is not None:
        for key, value in geometry.attrib.items():
            params[f"Geometry:{key}"] = value
    return params, str(path)


def parse_filter(value: str | None) -> set[str]:
    out: set[str] = set()
    if not value:
        return out
    for raw in value.split(","):
        token = raw.strip().lower()
        if token:
            out.add(token)
    return out


def selected_by_filter(row: dict[str, Any], filters: set[str]) -> bool:
    if not filters:
        return True
    group = str(row.get("case_group", "")).lower()
    angle = int(row.get("theta_target_deg", 0))
    angle3 = f"{angle:03d}"
    candidates = {
        str(row.get("case_id", "")).lower(),
        f"{group}{angle}",
        f"{group}{angle3}",
        f"{group}_theta{angle3}",
        f"theta{angle3}",
    }
    return bool(candidates & filters)


def parse_numeric_param(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("d"):
        try:
            return float(text[:-1])
        except ValueError:
            return None
    try:
        return float(text)
    except ValueError:
        return None


def to_float(value: Any) -> float | None:
    if value is None or value == "" or value == unknown():
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def to_int(value: Any) -> int | None:
    f = to_float(value)
    if f is None:
        return None
    return int(round(f))


def pick(metrics: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in metrics:
            return metrics[name]
    return None


def percentile(metrics: dict[str, Any], base: str, p: str) -> Any:
    return pick(metrics, f"{base}_{p}", f"{base}.{p}", f"{base} {p}")


def fit_plane_spherical_cap(*_: Any, **__: Any) -> dict[str, Any]:
    """Placeholder for future PhaseField/interface fitting."""
    return {"status": "pending", "reason": "raw interface data not provided"}


def compute_plane_cap_theory(volume: float, theta_deg: float) -> dict[str, float]:
    """Compute flat-wall spherical-cap target geometry from volume and theta."""
    theta = math.radians(theta_deg)
    tan_half = math.tan(theta / 2.0)
    if theta <= 0.0 or tan_half <= 0.0 or volume <= 0.0:
        raise ValueError("volume and theta must be positive")
    # V = pi h (3 a^2 + h^2) / 6 and h = a tan(theta/2).
    factor = math.pi * tan_half * (3.0 + tan_half * tan_half) / 6.0
    a = (volume / factor) ** (1.0 / 3.0)
    h = a * tan_half
    r_cap = (a * a + h * h) / (2.0 * h)
    return {
        "theta_deg": theta_deg,
        "volume": volume,
        "contact_radius": a,
        "base_diameter": 2.0 * a,
        "height": h,
        "spherical_cap_radius": r_cap,
    }


def estimate_contact_line(*_: Any, **__: Any) -> dict[str, Any]:
    """Placeholder for future contact-line extraction from interface data."""
    return {"status": "pending", "reason": "raw interface data not provided"}


def compute_local_contact_angles(*_: Any, **__: Any) -> dict[str, Any]:
    """Placeholder for future local angle distribution calculation."""
    return {"status": "pending", "reason": "raw interface data not provided"}


def compute_axisymmetry_error(*_: Any, **__: Any) -> dict[str, Any]:
    """Placeholder for future axisymmetry and directional-deviation metrics."""
    return {"status": "pending", "reason": "raw interface data not provided"}


def compute_internal_void_count(*_: Any, **__: Any) -> dict[str, Any]:
    """Placeholder for future connected-component void detection."""
    return {"status": "pending", "reason": "phase-field data not provided"}


def plane_theory_from_case_xml(params: dict[str, Any], theta_deg: float) -> dict[str, Any]:
    radius = parse_numeric_param(params.get("CapInitRadius"))
    if radius is None or radius <= 0.0:
        return {"status": "pending", "reason": "CapInitRadius missing or nonpositive"}
    theta = math.radians(theta_deg)
    h = radius * (1.0 - math.cos(theta))
    a = radius * math.sin(theta)
    volume = math.pi * h * (3.0 * a * a + h * h) / 6.0
    from_volume = compute_plane_cap_theory(volume, theta_deg)
    return {
        "status": "computed_from_case_xml",
        "theta_theory_deg": theta_deg,
        "cap_init_radius": radius,
        "h_theory": h,
        "a_theory": a,
        "volume_theory": volume,
        "h_over_a_theory": h / a if a else math.nan,
        "cap_theory_from_volume": from_volume,
    }


def compute_wp1_plane_geometry(
    row: dict[str, Any],
    metrics: dict[str, Any],
    case_params: dict[str, Any],
) -> dict[str, Any]:
    if row.get("case_group") != "plane":
        return {}

    theta_target = to_float(row.get("theta_target_deg"))
    out: dict[str, Any] = {
        "wp1_selected_case": row["case_id"] in {f"track_a_plane_theta{angle:03d}_shadow" for angle in [20, 30, 60, 90, 120]},
        "geometry_source": "lightweight_metrics_only",
        "raw_interface_data_present": False,
    }

    theta_fit = pick(
        metrics,
        "theta_fit_deg",
        "fitted_apparent_contact_angle_deg",
        "angle_apparent_deg",
        "apparent_contact_angle_deg",
    )
    theta_fit_f = to_float(theta_fit)
    out["theta_fit"] = theta_fit_f if theta_fit_f is not None else unknown()
    out["theta_fit_deg"] = theta_fit_f if theta_fit_f is not None else unknown()
    if theta_fit_f is not None and theta_target is not None:
        out["theta_fit_error_deg"] = theta_fit_f - theta_target
        out["theta_fit_abs_error_deg"] = abs(theta_fit_f - theta_target)
    else:
        out["theta_fit_error_deg"] = unknown()
        out["theta_fit_abs_error_deg"] = unknown()

    theory = plane_theory_from_case_xml(case_params, theta_target or math.nan) if theta_target is not None else {}
    out["geometry_theory_status"] = theory.get("status", "pending")
    for key in ["h_theory", "a_theory", "volume_theory", "h_over_a_theory", "cap_init_radius"]:
        out[key] = theory.get(key, unknown())

    h_sim = pick(metrics, "h_sim", "height_sim", "cap_height_sim")
    a_sim = pick(metrics, "a_sim", "contact_radius_sim", "base_radius_sim")
    volume_sim = pick(metrics, "volume_sim", "phase_volume_sim", "liquid_volume_sim")
    out["h_sim"] = h_sim if h_sim is not None and h_sim != "" else unknown()
    out["a_sim"] = a_sim if a_sim is not None and a_sim != "" else unknown()
    out["volume_sim"] = volume_sim if volume_sim is not None and volume_sim != "" else unknown()

    h_error = pick(metrics, "height_error")
    a_error = pick(metrics, "contact_radius_error")
    volume_error = pick(metrics, "volume_error", "volume_relative_error")
    if h_error is None and to_float(h_sim) is not None and to_float(out.get("h_theory")):
        h_error = abs(to_float(h_sim) - to_float(out["h_theory"])) / to_float(out["h_theory"])
    if a_error is None and to_float(a_sim) is not None and to_float(out.get("a_theory")):
        a_error = abs(to_float(a_sim) - to_float(out["a_theory"])) / to_float(out["a_theory"])
    out["height_error"] = h_error if h_error is not None and h_error != "" else unknown()
    out["contact_radius_error"] = a_error if a_error is not None and a_error != "" else unknown()
    out["volume_error"] = volume_error if volume_error is not None and volume_error != "" else unknown()

    internal_void = pick(metrics, "internal_void_count")
    center_bubble = pick(metrics, "center_bubble_count")
    if internal_void is None and center_bubble is not None:
        internal_void = center_bubble
    out["internal_void_count"] = internal_void if internal_void is not None and internal_void != "" else unknown()
    out["center_bubble_count"] = center_bubble if center_bubble is not None and center_bubble != "" else unknown()

    spurious = pick(metrics, "spurious_current", "spurious_current_estimate", "max_spurious_current")
    out["spurious_current"] = spurious if spurious is not None and spurious != "" else unknown()
    phase_mass = pick(metrics, "phase_mass_relative_change", "phase_drift", "fluid_phase_drift")
    out["phase_mass_relative_change"] = phase_mass if phase_mass is not None and phase_mass != "" else unknown()
    rho_drift = pick(metrics, "rho_relative_change", "rho_drift", "fluid_rho_drift")
    out["rho_relative_change"] = rho_drift if rho_drift is not None and rho_drift != "" else unknown()

    missing = []
    for key in [
        "theta_fit_error_deg",
        "h_sim",
        "height_error",
        "a_sim",
        "contact_radius_error",
        "phase_mass_relative_change",
        "internal_void_count",
    ]:
        if is_unknown_value(out.get(key)):
            missing.append(key)
    out["geometry_missing_metrics"] = ",".join(missing)
    out["geometry_status"] = "complete" if not missing else "geometry_pending"
    if missing:
        out["geometry_pending_reason"] = "missing required flat-wall metrics: " + ",".join(missing)
    else:
        out["geometry_pending_reason"] = ""
    return out


def geometry_requirements(group: str) -> list[str]:
    if group == "plane":
        return [
            "theta_fit_error_deg",
            "height_error",
            "contact_radius_error",
            "phase_mass_relative_change",
            "internal_void_count",
        ]
    if group == "cylinder":
        return [
            "local_angle_error_mean_deg",
            "local_angle_error_p95_deg",
            "internal_void_count",
        ]
    if group == "sphere":
        return [
            "local_angle_error_mean_deg",
            "local_angle_error_p95_deg",
            "internal_void_count",
        ]
    return []


def classify_track_a_case(row: dict[str, Any]) -> tuple[str, str]:
    """Classify one Track A case without inventing missing metrics."""
    if not row.get("metrics_source"):
        return "pending", "no lightweight runtime metrics found"

    solver_rc = row.get("solver_returncode", unknown())
    if solver_rc != unknown() and to_int(solver_rc) != 0:
        return "blocked", "solver return code is nonzero"
    post_rc = row.get("postprocess_returncode", unknown())
    if post_rc != unknown() and to_int(post_rc) != 0:
        return "blocked", "postprocess return code is nonzero"

    required_runtime = [
        "nonfinite_total",
        "vector_limiter_fraction",
        "normal_limiter_fraction",
        "outer90_limiter_count",
        "fallback_angle_limiter_count",
        "max_mach",
        "candidate_demand_p50",
        "candidate_demand_p95",
    ]
    missing_runtime = [key for key in required_runtime if row.get(key) == unknown()]
    if missing_runtime:
        return "incomplete", "missing required runtime metrics: " + ",".join(missing_runtime)

    if to_int(row.get("nonfinite_total")) != 0:
        return "blocked", "nonfinite_total is not zero"
    if to_float(row.get("vector_limiter_fraction")) != 0.0:
        return "blocked", "vector limiter is nonzero"
    normal_limiter = to_float(row.get("normal_limiter_fraction"))
    if normal_limiter is None or normal_limiter >= 0.05:
        return "blocked", "normal limiter fraction is >= 5%"
    if to_int(row.get("outer90_limiter_count")) != 0:
        return "blocked", "outer90 limiter count is nonzero"
    if to_int(row.get("fallback_angle_limiter_count")) != 0:
        return "blocked", "fallback angle limiter count is nonzero"
    max_mach = to_float(row.get("max_mach"))
    if max_mach is None or max_mach > PASS_MAX_MACH_DEFAULT:
        return "blocked", "max Mach is missing or elevated"
    demand_p50 = to_float(row.get("candidate_demand_p50"))
    if demand_p50 is None or demand_p50 >= 1.2:
        return "blocked", "candidate demand p50 is too high"
    demand_p95 = to_float(row.get("candidate_demand_p95"))
    if demand_p95 is None or demand_p95 >= 3.0:
        return "blocked", "candidate demand p95 is too high"

    missing_geometry = [key for key in geometry_requirements(str(row.get("case_group"))) if is_unknown_value(row.get(key))]
    if missing_geometry:
        return "geometry_pending", "runtime shadow gates pass; geometry metrics pending: " + ",".join(missing_geometry)

    group = str(row.get("case_group"))
    if group == "plane":
        theta_error = to_float(row.get("theta_fit_error_deg"))
        if theta_error is None or abs(theta_error) >= 3.0:
            return "blocked", "plane fitted angle error is too high"
        height_error = to_float(row.get("height_error"))
        if height_error is None or height_error >= 0.05:
            return "blocked", "plane height error is too high"
        radius_error = to_float(row.get("contact_radius_error"))
        if radius_error is None or radius_error >= 0.05:
            return "blocked", "plane contact radius error is too high"
        mass_drift = to_float(row.get("phase_mass_relative_change"))
        if mass_drift is None or abs(mass_drift) >= 0.01:
            return "blocked", "plane phase mass drift is too high"
    if group in {"cylinder", "sphere"}:
        mean_angle_error = to_float(row.get("local_angle_error_mean_deg"))
        if mean_angle_error is None or mean_angle_error >= 5.0:
            return "blocked", "mean local angle error is too high"
        p95_angle_error = to_float(row.get("local_angle_error_p95_deg"))
        if p95_angle_error is None or p95_angle_error >= 10.0:
            return "blocked", "p95 local angle error is too high"
    if to_int(row.get("internal_void_count")) not in (0, None):
        return "blocked", "internal void count is nonzero"
    if row.get("internal_void_count") == unknown():
        return "blocked", "internal void count is missing"

    if str(row.get("write_run_present")).lower() == "true":
        return "short_write_pass", "future category requires separate real short-write audit"
    return "eligible_for_short_write", "shadow and geometric metrics meet Track A planning gates"


def build_case_rows(manifest: dict[str, Any], metrics_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group, info in manifest["case_groups"].items():
        for angle in info["angles_deg"]:
            angle_int = int(angle)
            case_id = f"track_a_{group}_theta{angle_int:03d}_shadow"
            metrics, source = load_metric_file(case_id, metrics_root)
            case_params, case_xml_source = load_case_xml(case_id, metrics_root)
            row: dict[str, Any] = {
                "status": STATUS,
                "claim_limit": CLAIM_LIMIT,
                "case_id": case_id,
                "case_group": group,
                "theta_target_deg": angle_int,
                "stage8_operator_mode": manifest.get("stage8_operator_mode", 1),
                "steps": "/".join(str(s) for s in manifest.get("steps", [])),
                "metrics_source": source or "",
                "case_xml_source": case_xml_source or "",
            }
            wp1_geometry = compute_wp1_plane_geometry(row, metrics, case_params)
            fields = {
                "solver_returncode": pick(metrics, "solver_returncode", "solver_rc", "run_returncode"),
                "postprocess_returncode": pick(metrics, "postprocess_returncode", "postprocess_rc"),
                "nonfinite_total": pick(metrics, "nonfinite_total"),
                "max_mach": pick(metrics, "max_mach", "mach_max", "maxMach"),
                "phase_mass_relative_change": pick(wp1_geometry, "phase_mass_relative_change") if wp1_geometry else pick(metrics, "phase_mass_relative_change", "phase_drift", "fluid_phase_drift"),
                "rho_relative_change": pick(wp1_geometry, "rho_relative_change") if wp1_geometry else pick(metrics, "rho_relative_change", "rho_drift", "fluid_rho_drift"),
                "normal_limiter_fraction": pick(metrics, "normal_limiter_fraction"),
                "vector_limiter_fraction": pick(metrics, "vector_limiter_fraction", "limiter_fraction"),
                "outer90_limiter_count": pick(metrics, "outer90_limiter_count", "outer90_normal_limiter_count"),
                "fallback_angle_limiter_count": pick(metrics, "fallback_angle_limiter_count", "fallback_angle_normal_limiter_count"),
                "stage8_fluid_wall_angle_p50": percentile(metrics, "stage8_fluid_wall_angle", "p50"),
                "stage8_fluid_wall_angle_p95": percentile(metrics, "stage8_fluid_wall_angle", "p95"),
                "stage8_normal_agreement_p50": percentile(metrics, "stage8_normal_agreement", "p50"),
                "stage8_normal_agreement_p95": percentile(metrics, "stage8_normal_agreement", "p95"),
                "profile_target_mismatch_p50": percentile(metrics, "profile_target_mismatch", "p50"),
                "profile_target_mismatch_p95": percentile(metrics, "profile_target_mismatch", "p95"),
                "profile_target_mismatch_p99": percentile(metrics, "profile_target_mismatch", "p99"),
                "active_count": pick(metrics, "active_count"),
                "limiter_count": pick(metrics, "limiter_count", "normal_limiter_count"),
                "candidate_demand_p50": pick(metrics, "candidate_demand_p50", "cap_demand_ratio_p50"),
                "candidate_demand_p95": pick(metrics, "candidate_demand_p95", "cap_demand_ratio_p95"),
                "candidate_demand_p99": pick(metrics, "candidate_demand_p99", "cap_demand_ratio_p99"),
                "theta_fit": pick(wp1_geometry, "theta_fit", "theta_fit_deg") if wp1_geometry else pick(metrics, "theta_fit_deg", "fitted_apparent_contact_angle_deg"),
                "theta_fit_deg": pick(wp1_geometry, "theta_fit_deg") if wp1_geometry else pick(metrics, "theta_fit_deg", "fitted_apparent_contact_angle_deg"),
                "theta_fit_error_deg": pick(wp1_geometry, "theta_fit_error_deg") if wp1_geometry else pick(metrics, "theta_fit_error_deg"),
                "theta_fit_abs_error_deg": pick(wp1_geometry, "theta_fit_abs_error_deg") if wp1_geometry else None,
                "h_sim": pick(wp1_geometry, "h_sim") if wp1_geometry else pick(metrics, "h_sim", "height_sim"),
                "h_theory": pick(wp1_geometry, "h_theory") if wp1_geometry else pick(metrics, "h_theory"),
                "a_sim": pick(wp1_geometry, "a_sim") if wp1_geometry else pick(metrics, "a_sim", "contact_radius_sim"),
                "a_theory": pick(wp1_geometry, "a_theory") if wp1_geometry else pick(metrics, "a_theory"),
                "volume_sim": pick(wp1_geometry, "volume_sim") if wp1_geometry else pick(metrics, "volume_sim"),
                "volume_theory": pick(wp1_geometry, "volume_theory") if wp1_geometry else pick(metrics, "volume_theory"),
                "volume_error": pick(wp1_geometry, "volume_error") if wp1_geometry else pick(metrics, "volume_error"),
                "height_error": pick(metrics, "height_error"),
                "contact_radius_error": pick(metrics, "contact_radius_error"),
                "local_angle_error_mean_deg": pick(metrics, "local_angle_error_mean_deg"),
                "local_angle_error_p95_deg": pick(metrics, "local_angle_error_p95_deg"),
                "local_angle_error_max_deg": pick(metrics, "local_angle_error_max_deg"),
                "axisymmetry_error": pick(metrics, "axisymmetry_error"),
                "axial_symmetry_error": pick(metrics, "axial_symmetry_error"),
                "circumferential_symmetry_error": pick(metrics, "circumferential_symmetry_error"),
                "contact_line_height_variation": pick(metrics, "contact_line_height_variation"),
                "internal_void_count": pick(wp1_geometry, "internal_void_count") if wp1_geometry else pick(metrics, "internal_void_count", "center_bubble_count"),
                "center_bubble_count": pick(wp1_geometry, "center_bubble_count") if wp1_geometry else pick(metrics, "center_bubble_count"),
                "spurious_current": pick(wp1_geometry, "spurious_current") if wp1_geometry else pick(metrics, "spurious_current", "spurious_current_estimate"),
                "geometry_status": pick(wp1_geometry, "geometry_status") if wp1_geometry else pick(metrics, "geometry_status"),
                "geometry_missing_metrics": pick(wp1_geometry, "geometry_missing_metrics") if wp1_geometry else pick(metrics, "geometry_missing_metrics"),
                "geometry_pending_reason": pick(wp1_geometry, "geometry_pending_reason") if wp1_geometry else pick(metrics, "geometry_pending_reason"),
                "geometry_source": pick(wp1_geometry, "geometry_source") if wp1_geometry else None,
                "geometry_theory_status": pick(wp1_geometry, "geometry_theory_status") if wp1_geometry else None,
                "lower_side_film_fraction": pick(metrics, "lower_side_film_fraction"),
                "bottom_outer_wall_contamination": pick(metrics, "bottom_outer_wall_contamination"),
                "write_run_present": pick(metrics, "write_run_present"),
            }
            if wp1_geometry:
                fields["height_error"] = pick(wp1_geometry, "height_error")
                fields["contact_radius_error"] = pick(wp1_geometry, "contact_radius_error")
            for key, value in fields.items():
                row[key] = value if value is not None and value != "" else unknown()
            classification, reason = classify_track_a_case(row)
            if classification == "short_write_pass":
                classification = "blocked"
                reason = "short_write_pass cannot be assigned by Track A shadow summary"
            row["case_recommendation"] = classification
            row["classification_reason"] = reason
            rows.append(row)
    return rows


def write_wp1_plane_outputs(out_dir: Path, summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    plane_rows = [
        row for row in rows
        if row.get("case_id") in {
            "track_a_plane_theta020_shadow",
            "track_a_plane_theta030_shadow",
            "track_a_plane_theta060_shadow",
            "track_a_plane_theta090_shadow",
            "track_a_plane_theta120_shadow",
        }
    ]
    if not plane_rows:
        return

    keys = [
        "status",
        "claim_limit",
        "case_id",
        "theta_target_deg",
        "case_recommendation",
        "classification_reason",
        "geometry_status",
        "geometry_missing_metrics",
        "theta_fit",
        "theta_fit_deg",
        "theta_fit_error_deg",
        "theta_fit_abs_error_deg",
        "h_sim",
        "h_theory",
        "height_error",
        "a_sim",
        "a_theory",
        "contact_radius_error",
        "volume_sim",
        "volume_theory",
        "volume_error",
        "phase_mass_relative_change",
        "rho_relative_change",
        "max_mach",
        "nonfinite_total",
        "normal_limiter_fraction",
        "vector_limiter_fraction",
        "internal_void_count",
        "center_bubble_count",
        "spurious_current",
        "metrics_source",
        "case_xml_source",
    ]
    with (out_dir / "wp1_plane_geometry_summary.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys)
        writer.writeheader()
        for row in plane_rows:
            writer.writerow({key: row.get(key, unknown()) for key in keys})

    eligible = [row for row in plane_rows if row.get("case_recommendation") == "eligible_for_short_write"]
    smoke_ready = WP1_SMOKE_CASES <= {row["case_id"] for row in eligible}
    payload = {
        "status": STATUS,
        "claim_limit": CLAIM_LIMIT,
        "not_pre_reproduction": True,
        "not_validation": True,
        "not_production_fix": True,
        "solver_physics_modified": False,
        "simulations_run_by_this_script": False,
        "wp1_objective": "flat-wall closure from existing Track A shadow outputs",
        "metrics_root": summary.get("metrics_root"),
        "selected_cases": [row["case_id"] for row in plane_rows],
        "eligible_for_short_write": [row["case_id"] for row in eligible],
        "plane030_and_plane090_eligible": smoke_ready,
        "short_write_templates_generated": False,
        "short_write_100_ran": False,
        "block_reason": (
            "geometry metrics remain pending"
            if not eligible
            else "short-write template generation requires explicit template step"
        ),
        "rows": plane_rows,
    }
    (out_dir / "wp1_plane_geometry_summary.json").write_text(json.dumps(clean(payload), indent=2), encoding="utf-8")

    lines = [
        "# WP1 Plane Geometry Summary",
        "",
        "Status: `runtime_sanity / exploratory_not_validation`.",
        "",
        "This is not PRE reproduction, not validation, and not a production fix.",
        "No solver physics code was modified and no solver run is launched by this report.",
        "",
        "## Scope",
        "",
        "Selected flat-wall cases: plane020, plane030, plane060, plane090, plane120.",
        "Plane150, cylinder, sphere, sphere11, liquid impact, write mode, and 50k runs are excluded.",
        "",
        "## Result",
        "",
    ]
    if eligible:
        lines.append("Eligible for short write:")
        lines.extend(f"- `{row['case_id']}`" for row in eligible)
    else:
        lines.append("No selected flat-wall case is eligible for short write yet.")
    lines.extend(["", "## Cases", ""])
    for row in plane_rows:
        lines.append(
            f"- `{row['case_id']}`: `{row['case_recommendation']}`; "
            f"theta_fit={row.get('theta_fit_deg')}; "
            f"theta_error={row.get('theta_fit_error_deg')}; "
            f"h_error={row.get('height_error')}; "
            f"a_error={row.get('contact_radius_error')}; "
            f"internal_void={row.get('internal_void_count')}; "
            f"normal_limiter={row.get('normal_limiter_fraction')}; "
            f"reason={row.get('classification_reason')}"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The lightweight Track A metrics include fitted apparent contact angle for the",
            "flat-wall shadow cases, so WP1 can compute `theta_fit_error_deg`.",
            "However, the local `runtime_outputs/track_a_overnight_20260613` tree does not",
            "contain raw VTI/PVTI/PRI/VTK fields or precomputed `h_sim`, `a_sim`,",
            "`height_error`, `contact_radius_error`, or internal-void metrics.",
            "Those values are therefore reported as `unknown` and the cases remain",
            "`geometry_pending` rather than `eligible_for_short_write`.",
            "",
            "## Short Write Decision",
            "",
        ]
    )
    if smoke_ready:
        lines.append("Plane030 and plane090 are eligible, so a later explicitly approved 100-step short-write smoke may be planned.")
    else:
        lines.append("Plane030 and plane090 are not both eligible because required geometry metrics are pending. No 100-step short-write is run.")
    lines.extend(
        [
            "",
            "No validation claim is made; this remains `runtime_sanity / exploratory_not_validation`.",
        ]
    )
    (out_dir / "wp1_plane_geometry_report.md").write_text("\n".join(lines), encoding="utf-8")


def write_report(path: Path, summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    counts = summary.get("classification_counts", {})
    ran = [r for r in rows if r.get("metrics_source")]
    pending = [r for r in rows if r.get("case_recommendation") == "pending"]
    blocked = [r for r in rows if r.get("case_recommendation") == "blocked"]
    geometry_pending = [r for r in rows if r.get("case_recommendation") == "geometry_pending"]
    shadow_pass = [r for r in rows if r.get("case_recommendation") == "shadow_pass"]
    eligible = [r for r in rows if r.get("case_recommendation") == "eligible_for_short_write"]
    lines = [
        "# Track A Overnight Summary",
        "",
        "Status: `runtime_sanity / exploratory_not_validation`.",
        "",
        "This is not PRE reproduction, not validation, and not a production fix.",
        "",
        "Stage8 physics code was not modified by Track A execution. All cases are",
        "Stage8OperatorMode=1 shadow diagnostics; no sphere11 case, write mode,",
        "50k run, liquid-impact run, or high-Weber dynamic run is included.",
        "",
        f"Start time: {summary.get('start_time', 'unknown')}",
        f"End time: {summary.get('end_time', 'unknown')}",
        f"GPU used: {summary.get('gpu_used', 'unknown')}",
        f"Metrics root: `{summary.get('metrics_root', 'unknown')}`",
        "",
        "## Classification Counts",
        "",
    ]
    for key in ["pending", "incomplete", "blocked", "geometry_pending", "shadow_pass", "eligible_for_short_write", "short_write_pass"]:
        lines.append(f"- `{key}`: {counts.get(key, 0)}")
    lines.extend(
        [
            "",
            "## Cases Ran",
            "",
        ]
    )
    if ran:
        for row in ran:
            lines.append(
                f"- `{row['case_id']}`: `{row['case_recommendation']}`; "
                f"solver_rc={row.get('solver_returncode')}; post_rc={row.get('postprocess_returncode')}; "
                f"nonfinite={row.get('nonfinite_total')}; Mach={row.get('max_mach')}; "
                f"normal_limiter={row.get('normal_limiter_fraction')}; "
                f"vector_limiter={row.get('vector_limiter_fraction')}; "
                f"demand_p50={row.get('candidate_demand_p50')}; "
                f"demand_p95={row.get('candidate_demand_p95')}; "
                f"profile_mismatch_p95={row.get('profile_target_mismatch_p95')}; "
                f"theta_fit={row.get('fitted_apparent_contact_angle_deg', 'unknown')}; "
                f"reason={row.get('classification_reason')}"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Cases Not Run", ""])
    if pending:
        for row in pending:
            lines.append(f"- `{row['case_id']}`: {row.get('classification_reason')}")
    else:
        lines.append("- none")
    lines.extend(["", "## Shadow Pass", ""])
    lines.extend([f"- `{r['case_id']}`" for r in shadow_pass] or ["- none"])
    lines.extend(["", "## Geometry Pending", ""])
    if geometry_pending:
        for row in geometry_pending:
            lines.append(f"- `{row['case_id']}`: {row.get('classification_reason')}")
    else:
        lines.append("- none")
    lines.extend(["", "## Eligible For Short Write", ""])
    lines.extend([f"- `{r['case_id']}`" for r in eligible] or ["- none"])
    if not eligible:
        lines.append("")
        lines.append("No 100/1000/5000 short-write templates were generated because no case")
        lines.append("reached `eligible_for_short_write`.")
    lines.extend(["", "## Blocked", ""])
    if blocked:
        for row in blocked:
            lines.append(f"- `{row['case_id']}`: {row.get('classification_reason')}")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Execution Notes",
            "",
            "- Plane cases use a spherical-cap initializer and provide fitted apparent",
            "  contact angle when the flat-wall postprocessor succeeds.",
            "- Cylinder cases use a z-extruded solid cylinder with a tangent diffuse",
            "  spherical droplet. This is a one-direction-curvature runtime-feasibility",
            "  diagnostic, not cap-on-cylinder validation.",
            "- Cylinder and sphere classifications are driven by shadow limiter metrics",
            "  because full local angle, axisymmetry, and internal-void geometry metrics",
            "  remain pending.",
            "- In the remote queue logs, solver runtime was tens of seconds per case;",
            "  the main wall-time cost was Python/VTI postprocessing and raw-field",
            "  cleanup after each case.",
            "",
            "## Metrics Included",
            "",
            "Each CSV/JSON row includes available values for nonfinite_total, max_mach,",
            "phase/rho drift, limiter fractions, wall-angle/normal statistics,",
            "profile-target mismatch, active and limiter counts, candidate demand,",
            "fitted apparent angle when available, mass drift when available, and",
            "internal void count when available.",
            "",
            "No validation claim is made; this remains `runtime_sanity / exploratory_not_validation`.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--metrics-root", "--input", dest="metrics_root", type=Path, default=Path("runtime_outputs/track_a_usable_angle_ladder_20260613"))
    parser.add_argument("--out-dir", "--output", dest="out_dir", type=Path, default=SUMMARY_DIR)
    parser.add_argument("--case-filter", default="")
    parser.add_argument("--case-group", choices=["plane", "cylinder", "sphere", "all"], default="all")
    parser.add_argument("--summary-prefix", default="track_a_summary")
    parser.add_argument("--start-time", default="unknown")
    parser.add_argument("--end-time", default="unknown")
    parser.add_argument("--gpu-used", default="unknown")
    args = parser.parse_args()

    repo = args.repo_root.resolve()
    manifest_path = args.manifest if args.manifest.is_absolute() else repo / args.manifest
    metrics_root = args.metrics_root if args.metrics_root.is_absolute() else repo / args.metrics_root
    out_dir = args.out_dir if args.out_dir.is_absolute() else repo / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = read_json(manifest_path)
    rows = build_case_rows(manifest, metrics_root)
    filters = parse_filter(args.case_filter)
    rows = [
        row for row in rows
        if (args.case_group == "all" or row.get("case_group") == args.case_group)
        and selected_by_filter(row, filters)
    ]
    summary_prefix = args.summary_prefix
    if summary_prefix == "track_a_summary" and args.case_group != "all":
        summary_prefix = f"track_a_{args.case_group}_summary"
    summary = {
        "status": STATUS,
        "claim_limit": CLAIM_LIMIT,
        "not_pre_reproduction": True,
        "not_validation": True,
        "not_production_fix": True,
        "solver_physics_modified": False,
        "simulations_run_by_this_script": False,
        "metrics_root": str(metrics_root),
        "start_time": args.start_time,
        "end_time": args.end_time,
        "gpu_used": args.gpu_used,
        "classification_counts": {},
        "rows": rows,
    }
    for row in rows:
        key = row["case_recommendation"]
        summary["classification_counts"][key] = summary["classification_counts"].get(key, 0) + 1

    write_csv(out_dir / f"{summary_prefix}.csv", rows)
    (out_dir / f"{summary_prefix}.json").write_text(json.dumps(clean(summary), indent=2), encoding="utf-8")
    write_report(out_dir / f"{summary_prefix.replace('_summary', '_report')}.md", summary, rows)
    if args.case_group in {"plane", "all"}:
        write_wp1_plane_outputs(out_dir, summary, rows)
    print(json.dumps({"status": STATUS, "rows": len(rows), "out_dir": str(out_dir)}, indent=2))


if __name__ == "__main__":
    main()
