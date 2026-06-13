#!/usr/bin/env python3
"""Postprocess Stage8h contact-relation/profile-path shadow diagnostic VTI frames."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy


STATUS = "runtime_sanity"
STEP_RE = re.compile(r"_VTK_P\d+_(\d{8})\.vti$")
CS = math.sqrt(1.0 / 3.0)

REGION_LABELS = {
    0: "none_or_unknown",
    1: "sphere_upper",
    2: "sphere_lower90",
    3: "sphere_bottom120",
    4: "outer_or_other_wall",
}
CBIN_LABELS = {
    1: "c_0_0p05",
    2: "c_0p05_0p10",
    3: "c_0p10_0p30",
    4: "c_0p30_0p70",
    5: "c_0p70_0p90",
    6: "c_0p90_0p95",
    7: "c_0p95_1",
}
TANGENT_BINS = [
    ("t_0_0p005", 0.0, 0.005),
    ("t_0p005_0p01", 0.005, 0.01),
    ("t_0p01_0p02", 0.01, 0.02),
    ("t_0p02_0p05", 0.02, 0.05),
    ("t_0p05_0p10", 0.05, 0.10),
    ("t_0p10_inf", 0.10, math.inf),
]
NORMAL_RAW_ABS_BINS = [
    ("normal_raw_abs_0_1e-4", 0.0, 1.0e-4),
    ("normal_raw_abs_1e-4_1e-3", 1.0e-4, 1.0e-3),
    ("normal_raw_abs_1e-3_1e-2", 1.0e-3, 1.0e-2),
    ("normal_raw_abs_1e-2_5e-2", 1.0e-2, 5.0e-2),
    ("normal_raw_abs_5e-2_inf", 5.0e-2, math.inf),
]
NORMAL_AGREEMENT_BINS = [
    ("normal_0_0p5", 0.0, 0.5),
    ("normal_0p5_0p9", 0.5, 0.9),
    ("normal_0p9_0p99", 0.9, 0.99),
    ("normal_0p99_1p01", 0.99, 1.01),
]

REQUIRED_FIELDS = [
    "PhaseField",
    "Rho",
    "U",
    "BOUNDARY",
    "WallStage8ActiveWeight",
    "WallStage8LimiterReason",
    "WallStage8FluidWallAngle",
    "WallStage8NormalAgreement",
    "WallStage8VectorLimiterHit",
    "WallStage8NormalLimiterHit",
    "WallStage8LimiterRatio",
    "WallStage8VectorDeltaRawMag",
    "WallStage8VectorDeltaLimitedMag",
    "WallStage8NormalDeltaRaw",
    "WallStage8NormalDeltaLimited",
    "WallStage8TangentGradRaw",
    "WallStage8PhaseC",
    "WallStage8RegionTag",
    "WallStage8ContactBandTag",
    "WallStage8TanCoeffLocal",
    "WallStage8SphereRadialDot",
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


def step_of(path: Path) -> int:
    match = STEP_RE.search(path.name)
    return int(match.group(1)) if match else -1


def read_vti(path: Path) -> tuple[tuple[int, int, int], dict[str, np.ndarray]]:
    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(str(path))
    reader.Update()
    image = reader.GetOutput()
    dims = tuple(int(v) - 1 for v in image.GetDimensions())
    arrays: dict[str, np.ndarray] = {}
    cell_data = image.GetCellData()
    for i in range(cell_data.GetNumberOfArrays()):
        arr = cell_data.GetArray(i)
        if arr is not None:
            arrays[arr.GetName() or f"array{i}"] = vtk_to_numpy(arr)
    return dims, arrays


def scalar(values: np.ndarray | None) -> np.ndarray | None:
    if values is None:
        return None
    arr = np.asarray(values, dtype=float)
    if arr.ndim > 1:
        arr = arr[:, 0]
    return arr


def vector_mag(values: np.ndarray | None) -> np.ndarray | None:
    if values is None:
        return None
    arr = np.asarray(values, dtype=float)
    if arr.ndim == 1:
        arr = arr.reshape((-1, 1))
    return np.linalg.norm(arr[:, :3], axis=1)


def stats(values: np.ndarray, mask: np.ndarray | None = None) -> dict[str, float | int]:
    arr = np.asarray(values, dtype=float)
    if mask is not None:
        arr = arr[mask]
    if arr.size == 0:
        return {"count": 0, "nonfinite": 0}
    finite = np.isfinite(arr)
    out: dict[str, float | int] = {
        "count": int(arr.size),
        "nonfinite": int(arr.size - np.count_nonzero(finite)),
    }
    if np.any(finite):
        x = arr[finite]
        out.update(
            {
                "min": float(np.min(x)),
                "mean": float(np.mean(x)),
                "p05": float(np.percentile(x, 5)),
                "p10": float(np.percentile(x, 10)),
                "p50": float(np.percentile(x, 50)),
                "p90": float(np.percentile(x, 90)),
                "p95": float(np.percentile(x, 95)),
                "p99": float(np.percentile(x, 99)),
                "max": float(np.max(x)),
                "sum": float(np.sum(x)),
            }
        )
    return out


def finite_nonfinite_total(fields: dict[str, np.ndarray]) -> int:
    return int(sum(np.count_nonzero(~np.isfinite(v)) for v in fields.values()))


def bin_rows(
    *,
    step: int,
    group_name: str,
    labels: list[tuple[str, np.ndarray]],
    active: np.ndarray,
    vector_limiter: np.ndarray,
    normal_limiter: np.ndarray,
    stage8h_limiter: np.ndarray,
    ratio_cap_selected: np.ndarray,
    abs_cap_selected: np.ndarray,
    raw_delta: np.ndarray,
    ratio: np.ndarray,
    cap_demand_ratio: np.ndarray,
    stage8h_candidate_demand: np.ndarray,
    normal_raw_abs: np.ndarray,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for label, mask in labels:
        m = active & mask
        count = int(np.count_nonzero(m))
        vector_hit = int(np.count_nonzero(m & vector_limiter))
        normal_hit = int(np.count_nonzero(m & normal_limiter))
        stage8h_hit = int(np.count_nonzero(m & stage8h_limiter))
        ratio_count = int(np.count_nonzero(m & ratio_cap_selected))
        abs_count = int(np.count_nonzero(m & abs_cap_selected))
        rows.append(
            {
                "step": step,
                "group": group_name,
                "bin": label,
                "active_count": count,
                "limiter_count": vector_hit,
                "limiter_fraction": vector_hit / count if count else math.nan,
                "normal_limiter_count": normal_hit,
                "normal_limiter_fraction": normal_hit / count if count else math.nan,
                "stage8h_limiter_equivalent_count": stage8h_hit,
                "stage8h_limiter_equivalent_fraction": stage8h_hit / count if count else math.nan,
                "ratio_cap_selected_count": ratio_count,
                "ratio_cap_selected_fraction": ratio_count / count if count else math.nan,
                "abs_cap_selected_count": abs_count,
                "abs_cap_selected_fraction": abs_count / count if count else math.nan,
                "raw_delta_p95": stats(raw_delta, m).get("p95", math.nan),
                "raw_delta_p99": stats(raw_delta, m).get("p99", math.nan),
                "limiter_ratio_p50": stats(ratio, m).get("p50", math.nan),
                "cap_demand_ratio_p50": stats(cap_demand_ratio, m).get("p50", math.nan),
                "cap_demand_ratio_p95": stats(cap_demand_ratio, m).get("p95", math.nan),
                "cap_demand_ratio_p99": stats(cap_demand_ratio, m).get("p99", math.nan),
                "stage8h_candidate_demand_p50": stats(stage8h_candidate_demand, m).get("p50", math.nan),
                "stage8h_candidate_demand_p95": stats(stage8h_candidate_demand, m).get("p95", math.nan),
                "stage8h_candidate_demand_p99": stats(stage8h_candidate_demand, m).get("p99", math.nan),
                "normal_raw_abs_p50": stats(normal_raw_abs, m).get("p50", math.nan),
                "normal_raw_abs_p95": stats(normal_raw_abs, m).get("p95", math.nan),
            }
        )
    return rows

def summarize_frame(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    dims, arrays = read_vti(path)
    missing = [name for name in REQUIRED_FIELDS if name not in arrays]
    fields = {name: scalar(arrays.get(name)) for name in REQUIRED_FIELDS if scalar(arrays.get(name)) is not None}
    u_mag = vector_mag(arrays.get("U"))
    if u_mag is not None:
        fields["UMag"] = u_mag
    step = step_of(path)
    phase = fields["PhaseField"]
    boundary = fields["BOUNDARY"]
    fluid = np.isfinite(boundary) & (boundary == 0.0)
    active = fluid & np.isfinite(fields["WallStage8ActiveWeight"]) & (fields["WallStage8ActiveWeight"] > 0.0)
    vector_limiter = active & np.isfinite(fields["WallStage8VectorLimiterHit"]) & (fields["WallStage8VectorLimiterHit"] > 0.5)
    normal_limiter = active & np.isfinite(fields["WallStage8NormalLimiterHit"]) & (fields["WallStage8NormalLimiterHit"] > 0.5)
    raw_delta = fields["WallStage8VectorDeltaRawMag"]
    limited_delta = fields["WallStage8VectorDeltaLimitedMag"]
    ratio = fields["WallStage8LimiterRatio"]
    tangent = fields["WallStage8TangentGradRaw"]
    c = fields["WallStage8PhaseC"]
    region = np.rint(fields["WallStage8RegionTag"]).astype(int)
    contact_band = np.rint(fields["WallStage8ContactBandTag"]).astype(int)
    angle = fields["WallStage8FluidWallAngle"]
    normal_agree = fields["WallStage8NormalAgreement"]
    tan_coeff = fields["WallStage8TanCoeffLocal"]
    stage8g_mode = np.rint(fields["WallStage8gMode"]).astype(int)
    stage8h_mode = np.rint(fields["WallStage8hMode"]).astype(int)
    cap_source = np.rint(fields["WallStage8gCapSource"]).astype(int)
    limiter_class = np.rint(fields["WallStage8eLimiterClass"]).astype(int)
    ratio_cap_selected = active & np.isin(cap_source, [2, 4, 5, 6])
    abs_cap_selected = active & (cap_source == 1)
    target_scale_selected = active & (cap_source == 4)
    tangent_scale_selected = active & (cap_source == 5)
    floor_scale_selected = active & (cap_source == 6)
    cap_demand_ratio = fields["WallStage8gCapDemandRatio"]
    stage8h_candidate_demand = fields["WallStage8hCandidateDemandRatio"]
    stage8h_limiter = active & np.isfinite(fields["WallStage8hLimiterEquivalent"]) & (fields["WallStage8hLimiterEquivalent"] > 0.5)
    normal_raw_abs = fields["WallStage8eNormalRawAbs"]
    max_mach = float(np.nanmax(u_mag[fluid]) / CS) if u_mag is not None and np.any(fluid) else math.nan

    active_count = int(np.count_nonzero(active))
    vector_limiter_count = int(np.count_nonzero(vector_limiter))
    normal_limiter_count = int(np.count_nonzero(normal_limiter))
    stage8h_limiter_count = int(np.count_nonzero(stage8h_limiter))
    ratio_cap_selected_count = int(np.count_nonzero(ratio_cap_selected))
    abs_cap_selected_count = int(np.count_nonzero(abs_cap_selected))
    ratio_cap_limiter_count = int(np.count_nonzero(normal_limiter & ratio_cap_selected))
    abs_cap_limiter_count = int(np.count_nonzero(normal_limiter & abs_cap_selected))
    sphere11 = active & np.isfinite(angle) & (np.abs(angle - math.radians(11.0)) < 1e-6)
    outer90 = active & np.isfinite(angle) & (np.abs(angle - math.radians(90.0)) < 1e-6)
    fallback = active & (~sphere11) & (~outer90)
    summary: dict[str, Any] = {
        "status": STATUS,
        "step": step,
        "file": str(path),
        "dims": list(dims),
        "missing_required_fields": missing,
        "nonfinite_total": finite_nonfinite_total(fields),
        "fluid_count": int(np.count_nonzero(fluid)),
        "active_count": active_count,
        "stage8g_mode": int(np.nanmedian(stage8g_mode[active])) if np.any(active) else math.nan,
        "stage8h_mode": int(np.nanmedian(stage8h_mode[active])) if np.any(active) else math.nan,
        "limiter_count": vector_limiter_count,
        "limiter_fraction": vector_limiter_count / active_count if active_count else math.nan,
        "normal_limiter_count": normal_limiter_count,
        "normal_limiter_fraction": normal_limiter_count / active_count if active_count else math.nan,
        "stage8h_limiter_equivalent_count": stage8h_limiter_count,
        "stage8h_limiter_equivalent_fraction": stage8h_limiter_count / active_count if active_count else math.nan,
        "ratio_cap_selected_count": ratio_cap_selected_count,
        "ratio_cap_selected_fraction": ratio_cap_selected_count / active_count if active_count else math.nan,
        "abs_cap_selected_count": abs_cap_selected_count,
        "abs_cap_selected_fraction": abs_cap_selected_count / active_count if active_count else math.nan,
        "ratio_cap_limiter_count": ratio_cap_limiter_count,
        "ratio_cap_limiter_fraction_of_normal_limiter": ratio_cap_limiter_count / normal_limiter_count if normal_limiter_count else math.nan,
        "abs_cap_limiter_count": abs_cap_limiter_count,
        "abs_cap_limiter_fraction_of_normal_limiter": abs_cap_limiter_count / normal_limiter_count if normal_limiter_count else math.nan,
        "target_scale_limiter_count": int(np.count_nonzero(normal_limiter & target_scale_selected)),
        "tangent_scale_limiter_count": int(np.count_nonzero(normal_limiter & tangent_scale_selected)),
        "floor_scale_limiter_count": int(np.count_nonzero(normal_limiter & floor_scale_selected)),
        "raw_normal_scale_limiter_count": int(np.count_nonzero(normal_limiter & (cap_source == 2))),
        "sphere11_active_count": int(np.count_nonzero(sphere11)),
        "sphere11_limiter_count": int(np.count_nonzero(sphere11 & vector_limiter)),
        "sphere11_normal_limiter_count": int(np.count_nonzero(sphere11 & normal_limiter)),
        "sphere11_stage8h_limiter_equivalent_count": int(np.count_nonzero(sphere11 & stage8h_limiter)),
        "outer90_active_count": int(np.count_nonzero(outer90)),
        "outer90_limiter_count": int(np.count_nonzero(outer90 & vector_limiter)),
        "outer90_normal_limiter_count": int(np.count_nonzero(outer90 & normal_limiter)),
        "outer90_stage8h_limiter_equivalent_count": int(np.count_nonzero(outer90 & stage8h_limiter)),
        "fallback_angle_active_count": int(np.count_nonzero(fallback)),
        "fallback_angle_limiter_count": int(np.count_nonzero(fallback & vector_limiter)),
        "fallback_angle_normal_limiter_count": int(np.count_nonzero(fallback & normal_limiter)),
        "fallback_angle_stage8h_limiter_equivalent_count": int(np.count_nonzero(fallback & stage8h_limiter)),
        "max_mach": max_mach,
        "phase_fluid_min": float(np.nanmin(phase[fluid])) if np.any(fluid) else math.nan,
        "phase_fluid_max": float(np.nanmax(phase[fluid])) if np.any(fluid) else math.nan,
        "raw_delta_active": stats(raw_delta, active),
        "limited_delta_active": stats(limited_delta, active),
        "limiter_ratio_active": stats(ratio, active),
        "normal_delta_raw_active": stats(fields["WallStage8NormalDeltaRaw"], active),
        "normal_delta_limited_active": stats(fields["WallStage8NormalDeltaLimited"], active),
        "dn_try_active": stats(fields["WallStage8eDnTry"], active),
        "effective_cap_active": stats(fields["WallStage8eEffectiveCap"], active),
        "ratio_cap_active": stats(fields["WallStage8eRatioCap"], active),
        "abs_cap_active": stats(fields["WallStage8eAbsCap"], active),
        "cap_demand_ratio_active": stats(cap_demand_ratio, active),
        "normal_raw_abs_active": stats(normal_raw_abs, active),
        "target_normal_abs_active": stats(fields["WallStage8eTargetNormalAbs"], active),
        "target_minus_raw_abs_active": stats(fields["WallStage8eTargetMinusRawAbs"], active),
        "smooth_weight_c_active": stats(fields["WallStage8eSmoothWeightC"], active),
        "smooth_weight_g_active": stats(fields["WallStage8eSmoothWeightG"], active),
        "smooth_weight_t_active": stats(fields["WallStage8eSmoothWeightT"], active),
        "smooth_weight_total_active": stats(fields["WallStage8eSmoothWeightTotal"], active),
        "tan_coeff_times_tangent_active": stats(fields["WallStage8eTanCoeffTimesTangent"], active),
        "wall_profile_conflict_active": stats(fields["WallStage8eWallProfileConflict"], active),
        "tangent_mag_active": stats(tangent, active),
        "phase_c_active": stats(c, active),
        "normal_agreement_active": stats(normal_agree, active),
        "tan_coeff_active": stats(tan_coeff, active),
        "stage8g_effective_scale_active": stats(fields["WallStage8gEffectiveScale"], active),
        "stage8g_scale_target_active": stats(fields["WallStage8gScaleTarget"], active),
        "stage8g_scale_tangent_active": stats(fields["WallStage8gScaleTangent"], active),
        "stage8g_scale_floor_active": stats(fields["WallStage8gScaleFloor"], active),
        "stage8g_tan_raw_active": stats(fields["WallStage8gTanRaw"], active),
        "stage8g_tan_eff_active": stats(fields["WallStage8gTanEff"], active),
        "stage8g_regularization_ratio_active": stats(fields["WallStage8gRegularizationRatio"], active),
        "stage8g_profile_target_mismatch_active": stats(fields["WallStage8gProfileTargetMismatch"], active),
        "stage8g_profile_conflict_sign_active": stats(fields["WallStage8gProfileConflictSign"], active),
        "stage8g_write_allowed_flag_active": stats(fields["WallStage8gWriteAllowedFlag"], active),
        "stage8h_actual_cos_active": stats(fields["WallStage8hActualCos"], active),
        "stage8h_target_cos_active": stats(fields["WallStage8hTargetCos"], active),
        "stage8h_residual_cos_active": stats(fields["WallStage8hResidualCos"], active),
        "stage8h_dn_tan_raw_active": stats(fields["WallStage8hDnTanRaw"], active),
        "stage8h_dn_cos_raw_active": stats(fields["WallStage8hDnCosRaw"], active),
        "stage8h_dn_relaxed_active": stats(fields["WallStage8hDnRelaxed"], active),
        "stage8h_beta_relaxation_active": stats(fields["WallStage8hBetaRelaxation"], active),
        "stage8h_beta_source_active": stats(fields["WallStage8hBetaSource"], active),
        "stage8h_profile_normal_active": stats(fields["WallStage8hProfileNormal"], active),
        "stage8h_profile_target_mismatch_active": stats(fields["WallStage8hProfileTargetMismatch"], active),
        "stage8h_profile_consistency_weight_active": stats(fields["WallStage8hProfileConsistencyWeight"], active),
        "stage8h_candidate_demand_ratio_active": stats(fields["WallStage8hCandidateDemandRatio"], active),
        "stage8h_candidate_normal_delta_active": stats(fields["WallStage8hCandidateNormalDelta"], active),
        "stage8h_limiter_equivalent_active": stats(fields["WallStage8hLimiterEquivalent"], active),
        "stage8h_cos_to_tan_ratio_active": stats(fields["WallStage8hCosToTanRatio"], active),
        "stage8h_effective_cap_active": stats(fields["WallStage8hEffectiveCap"], active),
        "stage8h_write_allowed_flag_active": stats(fields["WallStage8hWriteAllowedFlag"], active),
    }

    rows: list[dict[str, Any]] = []

    def add_group(group_name: str, labels: list[tuple[str, np.ndarray]]) -> None:
        rows.extend(
            bin_rows(
                step=step,
                group_name=group_name,
                labels=labels,
                active=active,
                vector_limiter=vector_limiter,
                normal_limiter=normal_limiter,
                stage8h_limiter=stage8h_limiter,
                ratio_cap_selected=ratio_cap_selected,
                abs_cap_selected=abs_cap_selected,
                raw_delta=raw_delta,
                ratio=ratio,
                cap_demand_ratio=cap_demand_ratio,
                stage8h_candidate_demand=stage8h_candidate_demand,
                normal_raw_abs=normal_raw_abs,
            )
        )

    add_group("region", [(REGION_LABELS.get(i, str(i)), region == i) for i in sorted(REGION_LABELS)])
    add_group("theta_zone", [("sphere11", sphere11), ("outer90", outer90), ("fallback", fallback)])
    add_group("c_bin", [(CBIN_LABELS.get(i, str(i)), contact_band == i) for i in sorted(CBIN_LABELS)])
    add_group("tangent_bin", [(label, (tangent >= lo) & (tangent < hi)) for label, lo, hi in TANGENT_BINS])
    add_group("normal_raw_abs_bin", [(label, (normal_raw_abs >= lo) & (normal_raw_abs < hi)) for label, lo, hi in NORMAL_RAW_ABS_BINS])
    add_group(
        "cap_source",
        [
            ("abs_cap_selected", cap_source == 1),
            ("raw_normal_scale_selected", cap_source == 2),
            ("target_scale_selected", cap_source == 4),
            ("tangent_scale_selected", cap_source == 5),
            ("floor_scale_selected", cap_source == 6),
            ("none_or_inactive", cap_source == 0),
        ],
    )
    add_group("stage8g_mode", [(f"mode_{i}", stage8g_mode == i) for i in [0, 1, 2, 3]])
    add_group("stage8h_mode", [(f"mode_{i}", stage8h_mode == i) for i in [0, 1, 2, 3, 4]])
    add_group(
        "limiter_class",
        [
            ("none", limiter_class == 0),
            ("abs_cap_limiter", limiter_class == 1),
            ("ratio_cap_limiter", limiter_class == 2),
            ("secondary_vector_safety", limiter_class == 3),
            ("inactive_or_fallback", limiter_class < 0),
        ],
    )
    add_group(
        "normal_agreement_bin",
        [(label, (normal_agree >= lo) & (normal_agree < hi)) for label, lo, hi in NORMAL_AGREEMENT_BINS],
    )
    for c_label, c_mask in [(CBIN_LABELS.get(i, str(i)), contact_band == i) for i in sorted(CBIN_LABELS)]:
        add_group(
            f"c_x_tangent:{c_label}",
            [(t_label, c_mask & (tangent >= lo) & (tangent < hi)) for t_label, lo, hi in TANGENT_BINS],
        )
    return summary, rows

def flatten_summary(row: dict[str, Any]) -> dict[str, Any]:
    def s(group: str, key: str) -> Any:
        value = row.get(group, {})
        return value.get(key, math.nan) if isinstance(value, dict) else math.nan

    return {
        "step": row["step"],
        "stage8g_mode": row.get("stage8g_mode", math.nan),
        "stage8h_mode": row.get("stage8h_mode", math.nan),
        "nonfinite_total": row["nonfinite_total"],
        "max_mach": row["max_mach"],
        "active_count": row["active_count"],
        "limiter_count": row["limiter_count"],
        "limiter_fraction": row["limiter_fraction"],
        "normal_limiter_count": row["normal_limiter_count"],
        "normal_limiter_fraction": row["normal_limiter_fraction"],
        "stage8h_limiter_equivalent_count": row["stage8h_limiter_equivalent_count"],
        "stage8h_limiter_equivalent_fraction": row["stage8h_limiter_equivalent_fraction"],
        "ratio_cap_selected_count": row["ratio_cap_selected_count"],
        "ratio_cap_selected_fraction": row["ratio_cap_selected_fraction"],
        "abs_cap_selected_count": row["abs_cap_selected_count"],
        "abs_cap_selected_fraction": row["abs_cap_selected_fraction"],
        "ratio_cap_limiter_count": row["ratio_cap_limiter_count"],
        "ratio_cap_limiter_fraction_of_normal_limiter": row["ratio_cap_limiter_fraction_of_normal_limiter"],
        "abs_cap_limiter_count": row["abs_cap_limiter_count"],
        "abs_cap_limiter_fraction_of_normal_limiter": row["abs_cap_limiter_fraction_of_normal_limiter"],
        "raw_normal_scale_limiter_count": row.get("raw_normal_scale_limiter_count", math.nan),
        "target_scale_limiter_count": row.get("target_scale_limiter_count", math.nan),
        "tangent_scale_limiter_count": row.get("tangent_scale_limiter_count", math.nan),
        "floor_scale_limiter_count": row.get("floor_scale_limiter_count", math.nan),
        "sphere11_active_count": row["sphere11_active_count"],
        "sphere11_limiter_count": row["sphere11_limiter_count"],
        "sphere11_normal_limiter_count": row["sphere11_normal_limiter_count"],
        "sphere11_stage8h_limiter_equivalent_count": row["sphere11_stage8h_limiter_equivalent_count"],
        "outer90_active_count": row["outer90_active_count"],
        "outer90_limiter_count": row["outer90_limiter_count"],
        "outer90_normal_limiter_count": row["outer90_normal_limiter_count"],
        "outer90_stage8h_limiter_equivalent_count": row["outer90_stage8h_limiter_equivalent_count"],
        "fallback_angle_active_count": row["fallback_angle_active_count"],
        "fallback_angle_limiter_count": row["fallback_angle_limiter_count"],
        "fallback_angle_normal_limiter_count": row["fallback_angle_normal_limiter_count"],
        "fallback_angle_stage8h_limiter_equivalent_count": row["fallback_angle_stage8h_limiter_equivalent_count"],
        "raw_delta_p50": s("raw_delta_active", "p50"),
        "raw_delta_p95": s("raw_delta_active", "p95"),
        "raw_delta_p99": s("raw_delta_active", "p99"),
        "raw_delta_max": s("raw_delta_active", "max"),
        "limited_delta_p99": s("limited_delta_active", "p99"),
        "dn_try_p50": s("dn_try_active", "p50"),
        "dn_try_p95": s("dn_try_active", "p95"),
        "effective_cap_p50": s("effective_cap_active", "p50"),
        "effective_cap_p95": s("effective_cap_active", "p95"),
        "ratio_cap_p50": s("ratio_cap_active", "p50"),
        "ratio_cap_p95": s("ratio_cap_active", "p95"),
        "abs_cap_p50": s("abs_cap_active", "p50"),
        "cap_demand_ratio_p50": s("cap_demand_ratio_active", "p50"),
        "cap_demand_ratio_p95": s("cap_demand_ratio_active", "p95"),
        "cap_demand_ratio_p99": s("cap_demand_ratio_active", "p99"),
        "normal_raw_abs_p50": s("normal_raw_abs_active", "p50"),
        "normal_raw_abs_p95": s("normal_raw_abs_active", "p95"),
        "target_normal_abs_p50": s("target_normal_abs_active", "p50"),
        "target_minus_raw_abs_p50": s("target_minus_raw_abs_active", "p50"),
        "smooth_weight_c_p50": s("smooth_weight_c_active", "p50"),
        "smooth_weight_g_p50": s("smooth_weight_g_active", "p50"),
        "smooth_weight_t_p50": s("smooth_weight_t_active", "p50"),
        "smooth_weight_total_p50": s("smooth_weight_total_active", "p50"),
        "tan_coeff_times_tangent_p50": s("tan_coeff_times_tangent_active", "p50"),
        "limiter_ratio_p05": s("limiter_ratio_active", "p05"),
        "limiter_ratio_p10": s("limiter_ratio_active", "p10"),
        "limiter_ratio_p50": s("limiter_ratio_active", "p50"),
        "limiter_ratio_p95": s("limiter_ratio_active", "p95"),
        "normal_delta_raw_p99": s("normal_delta_raw_active", "p99"),
        "tangent_mag_p95": s("tangent_mag_active", "p95"),
        "tangent_mag_p99": s("tangent_mag_active", "p99"),
        "phase_c_p50": s("phase_c_active", "p50"),
        "normal_agreement_p05": s("normal_agreement_active", "p05"),
        "tan_coeff_p50": s("tan_coeff_active", "p50"),
        "wall_profile_conflict_p50": s("wall_profile_conflict_active", "p50"),
        "stage8g_effective_scale_p50": s("stage8g_effective_scale_active", "p50"),
        "stage8g_tan_raw_p50": s("stage8g_tan_raw_active", "p50"),
        "stage8g_tan_eff_p50": s("stage8g_tan_eff_active", "p50"),
        "stage8g_regularization_ratio_p50": s("stage8g_regularization_ratio_active", "p50"),
        "stage8g_profile_target_mismatch_p50": s("stage8g_profile_target_mismatch_active", "p50"),
        "stage8g_profile_conflict_sign_p50": s("stage8g_profile_conflict_sign_active", "p50"),
        "stage8g_write_allowed_flag_max": s("stage8g_write_allowed_flag_active", "max"),
        "stage8h_actual_cos_p50": s("stage8h_actual_cos_active", "p50"),
        "stage8h_target_cos_p50": s("stage8h_target_cos_active", "p50"),
        "stage8h_residual_cos_p50": s("stage8h_residual_cos_active", "p50"),
        "stage8h_dn_tan_raw_p50": s("stage8h_dn_tan_raw_active", "p50"),
        "stage8h_dn_cos_raw_p50": s("stage8h_dn_cos_raw_active", "p50"),
        "stage8h_dn_relaxed_p50": s("stage8h_dn_relaxed_active", "p50"),
        "stage8h_dn_relaxed_p95": s("stage8h_dn_relaxed_active", "p95"),
        "stage8h_beta_relaxation_p50": s("stage8h_beta_relaxation_active", "p50"),
        "stage8h_beta_source_p50": s("stage8h_beta_source_active", "p50"),
        "stage8h_profile_normal_p50": s("stage8h_profile_normal_active", "p50"),
        "stage8h_profile_target_mismatch_p50": s("stage8h_profile_target_mismatch_active", "p50"),
        "stage8h_profile_consistency_weight_p50": s("stage8h_profile_consistency_weight_active", "p50"),
        "stage8h_candidate_demand_ratio_p50": s("stage8h_candidate_demand_ratio_active", "p50"),
        "stage8h_candidate_demand_ratio_p95": s("stage8h_candidate_demand_ratio_active", "p95"),
        "stage8h_candidate_demand_ratio_p99": s("stage8h_candidate_demand_ratio_active", "p99"),
        "stage8h_candidate_normal_delta_p50": s("stage8h_candidate_normal_delta_active", "p50"),
        "stage8h_cos_to_tan_ratio_p50": s("stage8h_cos_to_tan_ratio_active", "p50"),
        "stage8h_effective_cap_p50": s("stage8h_effective_cap_active", "p50"),
        "stage8h_write_allowed_flag_max": s("stage8h_write_allowed_flag_active", "max"),
    }

def decision(rows: list[dict[str, Any]]) -> dict[str, Any]:
    final = rows[-1] if rows else {}
    stage8g_mode = final.get("stage8g_mode", math.nan)
    stage8h_mode = final.get("stage8h_mode", math.nan)
    vector_limiter_fraction = final.get("limiter_fraction", math.nan)
    normal_limiter_fraction = final.get("normal_limiter_fraction", math.nan)
    stage8h_limiter_fraction = final.get("stage8h_limiter_equivalent_fraction", math.nan)
    outer90_normal_limiter = final.get("outer90_normal_limiter_count", math.nan)
    outer90_stage8h_limiter = final.get("outer90_stage8h_limiter_equivalent_count", math.nan)
    fallback_stage8h_limiter = final.get("fallback_angle_stage8h_limiter_equivalent_count", math.nan)
    ratio_p50 = final.get("limiter_ratio_active", {}).get("p50", math.nan)
    ratio_p10 = final.get("limiter_ratio_active", {}).get("p10", math.nan)
    normal_delta_p99 = final.get("normal_delta_limited_active", {}).get("p99", math.nan)
    raw_delta_p99 = final.get("raw_delta_active", {}).get("p99", math.nan)
    ratio_cap_limiter_fraction = final.get("ratio_cap_limiter_fraction_of_normal_limiter", math.nan)
    abs_cap_limiter_fraction = final.get("abs_cap_limiter_fraction_of_normal_limiter", math.nan)
    cap_demand_p50 = final.get("cap_demand_ratio_active", {}).get("p50", math.nan)
    regularization_ratio_p50 = final.get("stage8g_regularization_ratio_active", {}).get("p50", math.nan)
    profile_mismatch_p50 = final.get("stage8g_profile_target_mismatch_active", {}).get("p50", math.nan)
    profile_conflict_p50 = final.get("wall_profile_conflict_active", {}).get("p50", math.nan)
    normal_raw_abs_p50 = final.get("normal_raw_abs_active", {}).get("p50", math.nan)
    target_minus_raw_abs_p50 = final.get("target_minus_raw_abs_active", {}).get("p50", math.nan)
    tangent_p95 = final.get("tangent_mag_active", {}).get("p95", math.nan)
    stage8h_demand_p50 = final.get("stage8h_candidate_demand_ratio_active", {}).get("p50", math.nan)
    stage8h_demand_p95 = final.get("stage8h_candidate_demand_ratio_active", {}).get("p95", math.nan)
    stage8h_demand_p99 = final.get("stage8h_candidate_demand_ratio_active", {}).get("p99", math.nan)
    stage8h_beta_p50 = final.get("stage8h_beta_relaxation_active", {}).get("p50", math.nan)
    stage8h_profile_weight_p50 = final.get("stage8h_profile_consistency_weight_active", {}).get("p50", math.nan)
    stage8h_cos_to_tan_p50 = final.get("stage8h_cos_to_tan_ratio_active", {}).get("p50", math.nan)
    stage8h_write_flag = final.get("stage8h_write_allowed_flag_active", {}).get("max", math.nan)
    root_cause = "undetermined_shadow_only"
    if rows:
        sphere_hits = final.get("sphere11_stage8h_limiter_equivalent_count", 0)
        total_hits = final.get("stage8h_limiter_equivalent_count", 0)
        outer_hits = final.get("outer90_stage8h_limiter_equivalent_count", 0)
        if total_hits and sphere_hits / total_hits > 0.9 and outer_hits == 0:
            root_cause = "sphere11_low_angle_stage8h_candidate_dominated"
        if np.isfinite(stage8h_limiter_fraction) and stage8h_limiter_fraction > 0.15:
            root_cause += "_candidate_demand_still_high"
        if np.isfinite(stage8h_cos_to_tan_p50) and stage8h_cos_to_tan_p50 < 0.75:
            root_cause += "_cos_residual_weaker_than_tan"
        if np.isfinite(stage8h_profile_weight_p50) and stage8h_profile_weight_p50 < 0.5:
            root_cause += "_profile_mismatch_weighted"
        if np.isfinite(vector_limiter_fraction) and vector_limiter_fraction > 0.001:
            root_cause += "_secondary_vector_safety_hit"
        if np.isfinite(profile_conflict_p50) and profile_conflict_p50 > 0.5:
            root_cause += "_profile_path_conflict"
    gate_pass = (
        rows
        and np.isfinite(stage8h_limiter_fraction)
        and stage8h_limiter_fraction <= 0.15
        and (not np.isfinite(vector_limiter_fraction) or vector_limiter_fraction <= 0.001)
        and (not np.isfinite(outer90_stage8h_limiter) or outer90_stage8h_limiter == 0)
        and (not np.isfinite(fallback_stage8h_limiter) or fallback_stage8h_limiter == 0)
        and (not np.isfinite(stage8h_demand_p50) or stage8h_demand_p50 < 1.2)
        and (not np.isfinite(stage8h_demand_p95) or stage8h_demand_p95 < 3.0)
        and (not np.isfinite(stage8h_write_flag) or stage8h_write_flag == 0.0)
    )
    if gate_pass:
        if stage8h_mode == 1:
            root_cause = "stage8h_mode1_residual_relaxation_shadow_gate_passed"
        elif stage8h_mode == 2:
            root_cause = "stage8h_mode2_cosine_residual_shadow_gate_passed"
        elif stage8h_mode == 3:
            root_cause = "stage8h_mode3_profile_path_shadow_gate_passed"
        elif stage8h_mode == 4:
            root_cause = "stage8h_mode4_combined_shadow_gate_passed"
        else:
            root_cause = "stage8h_mode0_stage8g_baseline_shadow_gate_passed"
    return {
        "status": STATUS,
        "claim_limit": "runtime_sanity / exploratory_not_validation only",
        "write_mode_allowed": False,
        "write_mode_blocked": True,
        "block_reason": "Stage8h is shadow-only; sphere Stage8OperatorMode=2 remains forbidden",
        "shadow_gate_passed_for_planning": bool(gate_pass),
        "root_cause_classification": root_cause,
        "final_stage8g_mode": stage8g_mode,
        "final_stage8h_mode": stage8h_mode,
        "final_vector_limiter_fraction": vector_limiter_fraction,
        "final_normal_limiter_fraction": normal_limiter_fraction,
        "final_stage8h_limiter_equivalent_fraction": stage8h_limiter_fraction,
        "final_limiter_ratio_p50": ratio_p50,
        "final_limiter_ratio_p10": ratio_p10,
        "final_outer90_normal_limiter_count": outer90_normal_limiter,
        "final_outer90_stage8h_limiter_equivalent_count": outer90_stage8h_limiter,
        "final_fallback_stage8h_limiter_equivalent_count": fallback_stage8h_limiter,
        "final_ratio_cap_limiter_fraction_of_normal_limiter": ratio_cap_limiter_fraction,
        "final_abs_cap_limiter_fraction_of_normal_limiter": abs_cap_limiter_fraction,
        "final_cap_demand_ratio_p50": cap_demand_p50,
        "final_regularization_ratio_p50": regularization_ratio_p50,
        "final_profile_target_mismatch_p50": profile_mismatch_p50,
        "final_profile_conflict_p50": profile_conflict_p50,
        "final_normal_raw_abs_p50": normal_raw_abs_p50,
        "final_target_minus_raw_abs_p50": target_minus_raw_abs_p50,
        "final_tangent_mag_p95": tangent_p95,
        "final_raw_delta_p99": raw_delta_p99,
        "final_normal_delta_limited_p99": normal_delta_p99,
        "final_stage8h_candidate_demand_ratio_p50": stage8h_demand_p50,
        "final_stage8h_candidate_demand_ratio_p95": stage8h_demand_p95,
        "final_stage8h_candidate_demand_ratio_p99": stage8h_demand_p99,
        "final_stage8h_beta_relaxation_p50": stage8h_beta_p50,
        "final_stage8h_profile_consistency_weight_p50": stage8h_profile_weight_p50,
        "final_stage8h_cos_to_tan_ratio_p50": stage8h_cos_to_tan_p50,
    }

def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
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
    parser.add_argument("--case-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    frames = sorted((args.case_root / "output").glob("*_VTK_P00_*.vti"), key=step_of)
    if not frames:
        raise SystemExit(f"no VTI frames under {args.case_root / 'output'}")
    summaries: list[dict[str, Any]] = []
    bin_rows_all: list[dict[str, Any]] = []
    for frame in frames:
        summary, bin_rows = summarize_frame(frame)
        summaries.append(summary)
        bin_rows_all.extend(bin_rows)
    payload = {
        "status": STATUS,
        "claim_limit": "runtime_sanity / exploratory_not_validation only",
        "case_root": str(args.case_root),
        "decision": decision(summaries),
        "frames": summaries,
    }
    (args.out_dir / "stage8h_shadow_attribution_summary.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    write_csv(args.out_dir / "stage8h_shadow_attribution_summary.csv", [flatten_summary(r) for r in summaries])
    write_csv(args.out_dir / "stage8h_shadow_attribution_bins.csv", bin_rows_all)
    print(json.dumps({"status": STATUS, "decision": payload["decision"], "frames": [r["step"] for r in summaries]}, indent=2))


if __name__ == "__main__":
    main()

