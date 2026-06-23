#!/usr/bin/env python3
"""Stage 14A: per-node compact-stencil rejection audit.

This is a DIAGNOSTIC-ONLY script. It reads EXISTING Stage13 flat-wall VTI
outputs and classifies every WettingPathId = -30 (compact-write requested but
rejected) target-wall node into a rejection hypothesis. It does NOT change any
wetting physics, does NOT recompile, and does NOT run a new simulation.

It is the Stage 14A deliverable from
docs/handoff/24_stage14_next_step_plan_20260617.md.

Three hypotheses (see plan section 6):

    H1 (stencil/vertex): q_f came from a vertex on the wrong side of the
        interface or from a masked-solid vertex.
    H2 (geometry mask): stage13_compact_vertex_is_real_fluid() over-rejected
        because IsBoundary_dyn was stale; vertices are geometrically fluid but
        flagged solid.
    H3 (quadratic): the contact-relation quadratic had no in-range root, so
        every candidate was clamped or rejected despite valid vertices/q_f.

FallbackReason codes (decoded from Boundary.c.Rt:791-1090):

     0  valid (accepted root, write candidate)            -> ACCEPT
     1  compact mode off
     2  invalid normalization or interface width
     3  no valid first fluid probe                        -> H2/H1
     4  neutral branch (cos(theta) ~= 0, ~90 deg)         -> NEUTRAL (by design)
     5  no real root (discriminant < 0)                   -> H3
     6  degenerate equation (a~=0, b~=0)                  -> H3
     7  roots out of bounded range                        -> H3
     8  invalid normal / no candidate triangle            -> H1/H2
     9  no clean all-fluid triangle                       -> H1
    10  no accepted positive-distance triangle            -> H1
    11  unsupported normal mode

The reject_class assignment uses FallbackReason as the primary signal and
cross-checks with WallCSQVertexMaskBits / WallCSQVertexRealFluidBits /
WallCSQDiscriminant / WallCSQRootChoice so that the classification is
auditable per node, not a guess.

Per-node CSV columns (only fields actually present in the VTI; missing fields
are written as empty, never fabricated):

    case_id, target_angle_deg, i, j, k
    WettingPathId, WallCSQFallbackReason, WallCSQValid, WallCSQStrictWriteReady
    WallCSQQf, WallCSQQsRaw, WallCSQQsBounded, WallCSQBoundedDelta
    WallCSQDiscriminant, WallCSQRootChoice
    WallCSQDs, WallCSQDf, WallCSQResidual, WallCSQAppliedResidual
    WallCSQVertexMaskBits, WallCSQVertexRealFluidBits, WallCSQVertexPhaseCleanBits
    WallCSQVertexQMin, WallCSQVertexQMax
    WallCSQMethodComplete, WallGhostClampHit, LocalRadAngle_deg
    q_region_class            (pure_gas / interface / pure_liquid, from q_f)
    reject_class              (discriminant / root_range / vertex_mask /
                               vertex_real_fluid / no_fluid_probe /
                               no_clean_triangle / invalid_normal /
                               mode_off / neutral_90 / unsupported /
                               unknown_valid_rejected / unknown)
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np


# FallbackReason integer -> human label. Verified against Boundary.c.Rt.
FALLBACK_REASON_LABELS = {
    0: "valid",
    1: "mode_off",
    2: "invalid_norm_or_intwidth",
    3: "no_valid_first_fluid_probe",
    4: "neutral_90",
    5: "no_real_root_disc_lt_0",
    6: "degenerate_equation",
    7: "roots_out_of_range",
    8: "invalid_normal_or_no_candidate_triangle",
    9: "no_clean_all_fluid_triangle",
    10: "no_accepted_positive_distance_triangle",
    11: "unsupported_normal_mode",
}

# Hypothesis grouping for the summary. H3 = math, H1 = stencil, H2 = mask.
HYPOTHESIS_MAP = {
    "discriminant": "H3_quadratic",
    "root_range": "H3_quadratic",
    "degenerate": "H3_quadratic",
    "vertex_mask": "H1_stencil_vertex",
    "no_clean_triangle": "H1_stencil_vertex",
    "no_positive_distance_triangle": "H1_stencil_vertex",
    "vertex_real_fluid": "H2_geometry_mask",
    "no_fluid_probe": "H2_geometry_mask",
    "invalid_normal": "H2_geometry_mask",
    "mode_off": "config",
    "neutral_90": "neutral_by_design",
    "unsupported": "config",
    "unknown_valid_rejected": "unknown",
    "unknown": "unknown",
}

# Fields this script reads from the VTI, if present. None of these are required
# to be present; the script degrades gracefully and records what was missing.
NODE_FIELDS = [
    "WettingPathId",
    "WallCSQFallbackReason",
    "WallCSQValid",
    "WallCSQStrictWriteReady",
    "WallCSQQf",
    "WallCSQQsRaw",
    "WallCSQQsBounded",
    "WallCSQBoundedDelta",
    "WallCSQDiscriminant",
    "WallCSQRootChoice",
    "WallCSQDs",
    "WallCSQDf",
    "WallCSQResidual",
    "WallCSQAppliedResidual",
    "WallCSQVertexMaskBits",
    "WallCSQVertexRealFluidBits",
    "WallCSQVertexPhaseCleanBits",
    "WallCSQVertexQMin",
    "WallCSQVertexQMax",
    "WallCSQMethodComplete",
    "WallGhostClampHit",
    "LocalRadAngle",
]

CSV_COLUMNS = [
    "case_id",
    "target_angle_deg",
    "i", "j", "k",
    "WettingPathId",
    "WallCSQFallbackReason",
    "WallCSQFallbackReason_label",
    "WallCSQValid",
    "WallCSQStrictWriteReady",
    "WallCSQQf",
    "WallCSQQsRaw",
    "WallCSQQsBounded",
    "WallCSQBoundedDelta",
    "WallCSQDiscriminant",
    "WallCSQRootChoice",
    "WallCSQDs",
    "WallCSQDf",
    "WallCSQResidual",
    "WallCSQAppliedResidual",
    "WallCSQVertexMaskBits",
    "WallCSQVertexRealFluidBits",
    "WallCSQVertexPhaseCleanBits",
    "WallCSQVertexQMin",
    "WallCSQVertexQMax",
    "WallCSQMethodComplete",
    "WallGhostClampHit",
    "LocalRadAngle_deg",
    "q_region_class",
    "reject_class",
    "hypothesis",
]


def step_of(path: Path) -> int:
    match = re.search(r"P00_(\d+)\.vti$", path.name)
    return int(match.group(1)) if match else -1


def load_vti(path: Path) -> tuple[tuple[int, int, int], dict[str, np.ndarray]]:
    """Read a VTI. Identical loader to the existing audit so results match."""
    try:
        import vtk
        from vtk.util.numpy_support import vtk_to_numpy
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "vtk is required. Run this on the post-processing host (server)."
        ) from exc
    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(str(path))
    reader.Update()
    image = reader.GetOutput()
    dims = tuple(int(v) - 1 for v in image.GetDimensions())
    data = image.GetCellData()
    arrays: dict[str, np.ndarray] = {}
    for idx in range(data.GetNumberOfArrays()):
        array = data.GetArray(idx)
        arrays[array.GetName() or f"array_{idx}"] = vtk_to_numpy(array).copy()
    return dims, arrays


def flat_patch_mask(
    metadata: dict[str, Any], dims: tuple[int, int, int]
) -> np.ndarray | None:
    """Rebuild the target-wall patch mask exactly as the existing audit does."""
    patch = metadata.get("target_wall_patch")
    if not isinstance(patch, dict):
        return None
    nx, ny, nz = dims
    mask3 = np.zeros((nz, ny, nx), dtype=bool)
    x0 = int(patch.get("x_start", 0))
    y0 = int(patch.get("y_start", 0))
    z0 = int(patch.get("z_start", 0))
    xc = int(patch.get("x_count", nx))
    yc = int(patch.get("y_count", 1))
    zc = int(patch.get("z_count", nz))
    x1 = max(0, min(nx, x0 + xc))
    y1 = max(0, min(ny, y0 + yc))
    z1 = max(0, min(nz, z0 + zc))
    x0 = max(0, min(nx, x0))
    y0 = max(0, min(ny, y0))
    z0 = max(0, min(nz, z0))
    if x0 >= x1 or y0 >= y1 or z0 >= z1:
        return None
    mask3[z0:z1, y0:y1, x0:x1] = True
    return mask3.reshape(-1)


def target_wall_indices(
    arrays: dict[str, np.ndarray],
    metadata: dict[str, Any],
    dims: tuple[int, int, int],
) -> np.ndarray:
    """Flat indices of target-wall cells. Mirrors the existing audit's logic."""
    boundary = arrays.get("IsItBoundary")
    if boundary is None:
        return np.zeros(0, dtype=np.intp)
    wall_mask = boundary > 0.5
    local_angle = arrays.get("LocalRadAngle")
    patch_mask = flat_patch_mask(metadata, dims)
    if patch_mask is not None:
        return np.flatnonzero(wall_mask & patch_mask)
    bc_theta = metadata.get("bc_theta_deg")
    if bc_theta is None or local_angle is None:
        return np.flatnonzero(wall_mask)
    target_angle = float(bc_theta) * math.pi / 180.0
    return np.flatnonzero(
        wall_mask & np.isfinite(local_angle) & (np.abs(local_angle - target_angle) < 1.0e-6)
    )


def q_region(q_f: float) -> str:
    """Classify the fluid-side q_f into a phase region for cross-tabulation."""
    if not np.isfinite(q_f):
        return "unknown"
    if q_f <= 0.05:
        return "pure_gas"
    if q_f >= 0.95:
        return "pure_liquid"
    return "interface"


def classify_reject(
    fallback_reason: float,
    discriminant: float,
    root_choice: float,
    vertex_mask_bits: float,
    vertex_real_fluid_bits: float,
    csq_valid: float,
    wetting_path_id: float,
) -> str:
    """Map one rejected node to a reject_class.

    Primary signal is FallbackReason. Cross-checks make the assignment auditable
    rather than a black-box guess. The ordering matters: math (H3) is checked
    from reason/discriminant/root_choice, stencil (H1) from vertex bits, mask
    (H2) from the real-fluid bits vs mask-bit disagreement.
    """
    reason = int(round(fallback_reason)) if np.isfinite(fallback_reason) else -1

    # Reasons that are config / by-design, not defects.
    if reason == 4:
        return "neutral_90"
    if reason == 1:
        return "mode_off"
    if reason == 11:
        return "unsupported"
    if reason == 2:
        return "invalid_normal"  # invalid normalization -> grouped under mask/hygiene

    # H3: quadratic has no acceptable root.
    if reason == 5:
        return "discriminant"
    if reason == 6:
        return "degenerate"
    if reason == 7:
        return "root_range"
    # Defensive cross-check: even if reason==0, a negative discriminant means
    # the solver fell through to a fallback root.
    if np.isfinite(discriminant) and discriminant < 0.0:
        return "discriminant"
    if np.isfinite(root_choice) and root_choice <= -4.0:
        return "root_range"

    # H1: stencil could not find a clean all-fluid triangle.
    if reason == 9:
        return "no_clean_triangle"
    if reason == 10:
        return "no_positive_distance_triangle"
    # Vertex mask bits != 7 means at least one vertex was treated as
    # solid/boundary by the geometry mask. This is the stencil-quality signal.
    if np.isfinite(vertex_mask_bits) and vertex_mask_bits < 6.5:
        return "vertex_mask"

    # H2: no fluid probe / invalid normal / real-fluid bits disagree with mask.
    if reason == 3:
        return "no_fluid_probe"
    if reason == 8:
        return "invalid_normal"
    # Real-fluid bits < 7 but mask bits == 7: the mask said fluid, but the
    # real-fluid check disagreed -> classic stale IsBoundary_dyn symptom (H2).
    if (
        np.isfinite(vertex_mask_bits)
        and vertex_mask_bits >= 6.5
        and np.isfinite(vertex_real_fluid_bits)
        and vertex_real_fluid_bits < 6.5
    ):
        return "vertex_real_fluid"

    # Path = -30 but reason reports valid: the compact solve succeeded but the
    # strict-write gate (applied_residual / bounded_delta / write_allowed)
    # rejected it. This is a separate, important failure mode to surface.
    if reason == 0 and csq_valid > 0.5:
        return "unknown_valid_rejected"

    return "unknown"


def histogram_dict(values: np.ndarray) -> dict[str, int]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {}
    uniq, counts = np.unique(finite, return_counts=True)
    return {str(float(v)): int(c) for v, c in zip(uniq, counts)}


def finite_stats(values: np.ndarray) -> dict[str, Any]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {"count": int(values.size), "finite": 0, "min": None, "max": None,
                "max_abs": None, "mean": None, "p50": None, "p95": None}
    return {
        "count": int(values.size),
        "finite": int(finite.size),
        "min": float(np.min(finite)),
        "max": float(np.max(finite)),
        "max_abs": float(np.max(np.abs(finite))),
        "mean": float(np.mean(finite)),
        "p50": float(np.percentile(finite, 50)),
        "p95": float(np.percentile(finite, 95)),
    }


def audit_case(
    case_dir: Path, contact_line_eps: float
) -> dict[str, Any]:
    meta_path = case_dir / "case_metadata.json"
    metadata = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    target_angle_deg = metadata.get("bc_theta_deg")
    case_id = case_dir.name

    vtis = sorted((case_dir / "output").glob("case_VTK_P00_*.vti"), key=step_of)
    if not vtis:
        return {"case_id": case_id, "failure": "no_vti_outputs"}
    dims, arrays = load_vti(vtis[-1])

    present = {f: (f in arrays) for f in NODE_FIELDS}
    missing = [f for f in NODE_FIELDS if f not in arrays]
    idxs = target_wall_indices(arrays, metadata, dims)
    if idxs.size == 0:
        return {
            "case_id": case_id,
            "target_angle_deg": target_angle_deg,
            "final_vti": str(vtis[-1]),
            "missing_fields": missing,
            "target_wall_count": 0,
            "failure": "no_target_wall_nodes",
        }

    # Extract per-node arrays restricted to the target wall.
    get = lambda name: arrays[name][idxs] if name in arrays else np.full(idxs.size, np.nan)

    pid = get("WettingPathId")
    reason = get("WallCSQFallbackReason")
    csq_valid = get("WallCSQValid")
    strict_ready = get("WallCSQStrictWriteReady")
    qf = get("WallCSQQf")
    qs_raw = get("WallCSQQsRaw")
    qs_bounded = get("WallCSQQsBounded")
    bounded_delta = get("WallCSQBoundedDelta")
    discriminant = get("WallCSQDiscriminant")
    root_choice = get("WallCSQRootChoice")
    ds = get("WallCSQDs")
    df = get("WallCSQDf")
    residual = get("WallCSQResidual")
    applied_residual = get("WallCSQAppliedResidual")
    vmask = get("WallCSQVertexMaskBits")
    vreal = get("WallCSQVertexRealFluidBits")
    vphase = get("WallCSQVertexPhaseCleanBits")
    vqmin = get("WallCSQVertexQMin")
    vqmax = get("WallCSQVertexQMax")
    method_complete = get("WallCSQMethodComplete")
    clamp_hit = get("WallGhostClampHit")
    local_angle = get("LocalRadAngle")

    # --- Reject classification, per node ---
    reject_classes = np.empty(idxs.size, dtype=object)
    q_regions = np.empty(idxs.size, dtype=object)
    for n in range(idxs.size):
        reject_classes[n] = classify_reject(
            reason[n], discriminant[n], root_choice[n],
            vmask[n], vreal[n], csq_valid[n], pid[n],
        )
        q_regions[n] = q_region(qf[n])
    hypotheses = np.array([HYPOTHESIS_MAP.get(rc, "unknown") for rc in reject_classes])

    # Subsets.
    rejected_mask = np.isfinite(pid) & (np.abs(pid - (-30.0)) < 0.5)
    accepted_mask = np.isfinite(pid) & (np.abs(pid - 30.0) < 0.5)
    cl_band_mask = np.array([qr == "interface" for qr in q_regions])
    pure_mask = ~cl_band_mask

    # reason histogram over the whole target wall and over rejected only.
    reason_hist_all = histogram_dict(reason)
    reason_hist_rej = histogram_dict(reason[rejected_mask])
    reject_hist_all = {str(k): int(v) for k, v in zip(*np.unique(reject_classes, return_counts=True))}
    reject_hist_rej = {}
    if np.any(rejected_mask):
        rc_rej = reject_classes[rejected_mask]
        uniq, counts = np.unique(rc_rej, return_counts=True)
        reject_hist_rej = {str(k): int(v) for k, v in zip(uniq, counts)}

    # Hypothesis rollup over rejected nodes (the decision-relevant one).
    hyp_rej = {}
    if np.any(rejected_mask):
        h_rej = hypotheses[rejected_mask]
        uniq, counts = np.unique(h_rej, return_counts=True)
        hyp_rej = {str(k): int(v) for k, v in zip(uniq, counts)}

    # Cross-tab: reject_class x q_region (over rejected nodes).
    crosstab = {}
    if np.any(rejected_mask):
        for rc, qr in zip(reject_classes[rejected_mask], q_regions[rejected_mask]):
            crosstab.setdefault(str(rc), {})
            crosstab[str(rc)][str(qr)] = crosstab[str(rc)].get(str(qr), 0) + 1

    # Contact-line-band vs pure-phase coverage split.
    def frac(mask: np.ndarray, cond: np.ndarray) -> Any:
        sel = mask & cond
        if not np.any(mask):
            return None
        return float(np.mean(sel))

    summary = {
        "case_id": case_id,
        "target_angle_deg": target_angle_deg,
        "final_vti": str(vtis[-1]),
        "claim_limit": "stage14a reject diagnostic only; not validation_passed",
        "missing_fields": missing,
        "target_wall_count": int(idxs.size),
        "path30_fraction_all": frac(np.ones(idxs.size, bool), accepted_mask),
        "path_minus30_fraction_all": frac(np.ones(idxs.size, bool), rejected_mask),
        "rejected_count": int(np.count_nonzero(rejected_mask)),
        "accepted_count": int(np.count_nonzero(accepted_mask)),
        # contact-line band vs pure-phase split (the key 14B-relevant cut)
        "contact_line_band_count": int(np.count_nonzero(cl_band_mask)),
        "clband_path30_fraction": frac(cl_band_mask, accepted_mask),
        "clband_path_minus30_fraction": frac(cl_band_mask, rejected_mask),
        "clband_csq_valid_fraction": (
            float(np.mean(csq_valid[cl_band_mask] > 0.5))
            if np.any(cl_band_mask) else None
        ),
        "clband_strict_write_ready_fraction": (
            float(np.mean(strict_ready[cl_band_mask] > 0.5))
            if np.any(cl_band_mask) else None
        ),
        "purephase_path30_fraction": frac(pure_mask, accepted_mask),
        "purephase_path_minus30_fraction": frac(pure_mask, rejected_mask),
        # reason histograms
        "fallback_reason_histogram_all": reason_hist_all,
        "fallback_reason_histogram_rejected": reason_hist_rej,
        "reject_class_histogram_all": reject_hist_all,
        "reject_class_histogram_rejected": reject_hist_rej,
        # H1/H2/H3 rollup over rejected nodes
        "hypothesis_histogram_rejected": hyp_rej,
        # discriminant / bounded-delta diagnostics over rejected nodes
        "discriminant_stats_rejected": (
            finite_stats(discriminant[rejected_mask])
            if np.any(rejected_mask) else {}
        ),
        "bounded_delta_stats_rejected": (
            finite_stats(bounded_delta[rejected_mask])
            if np.any(rejected_mask) else {}
        ),
        "applied_residual_stats_rejected": (
            finite_stats(applied_residual[rejected_mask])
            if np.any(rejected_mask) else {}
        ),
        "qf_stats_rejected": (
            finite_stats(qf[rejected_mask]) if np.any(rejected_mask) else {}
        ),
        "ds_df_stats_rejected": {
            "ds": finite_stats(ds[rejected_mask]) if np.any(rejected_mask) else {},
            "df": finite_stats(df[rejected_mask]) if np.any(rejected_mask) else {},
        },
        "vertex_bits_stats_rejected": {
            "mask_bits_eq7_fraction": (
                float(np.mean(vmask[rejected_mask] >= 6.5))
                if np.any(rejected_mask) and not missing.count("WallCSQVertexMaskBits")
                else None
            ),
            "real_fluid_bits_eq7_fraction": (
                float(np.mean(vreal[rejected_mask] >= 6.5))
                if np.any(rejected_mask) and not missing.count("WallCSQVertexRealFluidBits")
                else None
            ),
        },
        "reject_class_x_q_region_crosstab_rejected": crosstab,
        # dominant-cause verdict per the user's 14A gate (>=60% dominant,
        # top-2 >=75% two-cause, else cross-tab required)
        "dominant_cause": _dominant_cause(hyp_rej, int(np.count_nonzero(rejected_mask))),
    }
    return summary, {
        "case_id": case_id,
        "target_angle_deg": target_angle_deg,
        "dims": dims,
        "idxs": idxs,
        "pid": pid, "reason": reason, "reason_label": np.array([
            FALLBACK_REASON_LABELS.get(int(round(r)), "unknown")
            if np.isfinite(r) else "unknown" for r in reason
        ]),
        "csq_valid": csq_valid, "strict_ready": strict_ready,
        "qf": qf, "qs_raw": qs_raw, "qs_bounded": qs_bounded,
        "bounded_delta": bounded_delta, "discriminant": discriminant,
        "root_choice": root_choice, "ds": ds, "df": df,
        "residual": residual, "applied_residual": applied_residual,
        "vmask": vmask, "vreal": vreal, "vphase": vphase,
        "vqmin": vqmin, "vqmax": vqmax, "method_complete": method_complete,
        "clamp_hit": clamp_hit, "local_angle": local_angle,
        "q_regions": q_regions, "reject_classes": reject_classes,
    }


def _dominant_cause(hyp_hist: dict[str, int], rejected_total: int) -> dict[str, Any]:
    if rejected_total <= 0 or not hyp_hist:
        return {"verdict": "no_rejected_nodes"}
    items = sorted(hyp_hist.items(), key=lambda kv: -kv[1])
    top1_name, top1 = items[0]
    top1_frac = top1 / rejected_total
    top2 = items[1][1] if len(items) > 1 else 0
    top2_frac = (top1 + top2) / rejected_total
    if top1_frac >= 0.60:
        verdict = "dominant_cause"
    elif top2_frac >= 0.75:
        verdict = "two_cause"
    else:
        verdict = "spread_cross_tab_required"
    return {
        "verdict": verdict,
        "top1": {"hypothesis": top1_name, "count": int(top1), "fraction": round(top1_frac, 4)},
        "top2": {"hypothesis": items[1][0] if len(items) > 1 else None,
                 "count": int(top2), "fraction": round(top2_frac, 4)},
        "rejected_total": int(rejected_total),
    }


def write_per_node_csv(
    rows: list[dict[str, Any]], case_records: list[tuple[dict, dict]], out_path: Path
) -> None:
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def build_rows(case_records: list[tuple[dict, dict]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for summary, nodes in case_records:
        n = nodes["idxs"].size
        dims = nodes["dims"]
        # VTK cell ordering is (k fastest in last dim). Recover (i,j,k) from the
        # flat cell index for human-readable coordinates.
        nx, ny, nz = dims
        flat = nodes["idxs"]
        # arrays are flattened in Fortran-free C order by vtk_to_numpy for
        # cell data: index = i + nx*(j + ny*k). Verify against dims.
        ks = flat // (nx * ny)
        rem = flat % (nx * ny)
        js = rem // nx
        is_ = rem % nx
        for m in range(n):
            rows.append({
                "case_id": nodes["case_id"],
                "target_angle_deg": nodes["target_angle_deg"],
                "i": int(is_[m]), "j": int(js[m]), "k": int(ks[m]),
                "WettingPathId": _f(nodes["pid"][m]),
                "WallCSQFallbackReason": _f(nodes["reason"][m]),
                "WallCSQFallbackReason_label": nodes["reason_label"][m],
                "WallCSQValid": _f(nodes["csq_valid"][m]),
                "WallCSQStrictWriteReady": _f(nodes["strict_ready"][m]),
                "WallCSQQf": _f(nodes["qf"][m]),
                "WallCSQQsRaw": _f(nodes["qs_raw"][m]),
                "WallCSQQsBounded": _f(nodes["qs_bounded"][m]),
                "WallCSQBoundedDelta": _f(nodes["bounded_delta"][m]),
                "WallCSQDiscriminant": _f(nodes["discriminant"][m]),
                "WallCSQRootChoice": _f(nodes["root_choice"][m]),
                "WallCSQDs": _f(nodes["ds"][m]),
                "WallCSQDf": _f(nodes["df"][m]),
                "WallCSQResidual": _f(nodes["residual"][m]),
                "WallCSQAppliedResidual": _f(nodes["applied_residual"][m]),
                "WallCSQVertexMaskBits": _f(nodes["vmask"][m]),
                "WallCSQVertexRealFluidBits": _f(nodes["vreal"][m]),
                "WallCSQVertexPhaseCleanBits": _f(nodes["vphase"][m]),
                "WallCSQVertexQMin": _f(nodes["vqmin"][m]),
                "WallCSQVertexQMax": _f(nodes["vqmax"][m]),
                "WallCSQMethodComplete": _f(nodes["method_complete"][m]),
                "WallGhostClampHit": _f(nodes["clamp_hit"][m]),
                "LocalRadAngle_deg": (
                    float(nodes["local_angle"][m] * 180.0 / math.pi)
                    if np.isfinite(nodes["local_angle"][m]) else ""
                ),
                "q_region_class": nodes["q_regions"][m],
                "reject_class": nodes["reject_classes"][m],
                "hypothesis": HYPOTHESIS_MAP.get(nodes["reject_classes"][m], "unknown"),
            })
    return rows


def _f(v: float) -> Any:
    return float(v) if np.isfinite(v) else ""


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path,
                   help="Stage13 flat-wall diagnostic root (contains case dirs)")
    p.add_argument("--out-dir", type=Path, default=None,
                   help="Output directory for JSON + CSV (default: <root>/stage14a_reject_audit)")
    p.add_argument("--contact-line-eps", type=float, default=0.05,
                   help="q_f band defining the contact line (default 0.05)")
    p.add_argument("--no-csv", action="store_true",
                   help="Skip writing the large per-node CSV")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = args.out_dir or (args.root / "stage14a_reject_audit")
    out_dir.mkdir(parents=True, exist_ok=True)

    case_dirs = sorted(
        path for path in args.root.iterdir()
        if path.is_dir() and (path / "case_metadata.json").exists()
    )
    case_records: list[tuple[dict, dict]] = []
    summaries: list[dict[str, Any]] = []
    for case_dir in case_dirs:
        result = audit_case(case_dir, args.contact_line_eps)
        if isinstance(result, tuple):
            summary, nodes = result
            case_records.append((summary, nodes))
            summaries.append(summary)
        else:
            summaries.append(result)

    report = {
        "stage": "stage14a_compact_reject_audit",
        "root": str(args.root),
        "claim_limit": "exploratory_not_validation; reject-classification diagnostic only",
        "fallback_reason_code_reference": FALLBACK_REASON_LABELS,
        "hypothesis_reference": {
            "H1_stencil_vertex": "q_f from wrong-side/masked vertex or no clean triangle",
            "H2_geometry_mask": "IsBoundary_dyn stale; vertices fluid but flagged solid / no probe",
            "H3_quadratic": "discriminant<0, degenerate, or both roots out of range",
            "config": "mode off / unsupported normal mode",
            "neutral_by_design": "cos(theta)~=0 (~90 deg) neutral branch",
            "unknown": "reason==0 valid but path=-30 (strict gate rejected), or unclassified",
        },
        "dominant_cause_rule": (
            "top1 hypothesis >=60% of rejected nodes => dominant_cause; "
            "top1+top2 >=75% => two_cause; else spread_cross_tab_required"
        ),
        "cases": summaries,
    }
    json_path = out_dir / "stage14a_reject_audit.json"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    if not args.no_csv and case_records:
        rows = build_rows(case_records)
        csv_path = out_dir / "stage14a_reject_per_node.csv"
        write_per_node_csv(rows, case_records, csv_path)
        report["per_node_csv"] = str(csv_path)
        report["per_node_row_count"] = len(rows)
        json_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    # Console: a compact per-case dominant-cause table.
    print("=" * 78)
    print("Stage 14A compact-stencil rejection audit")
    print("claim_limit: exploratory_not_validation; diagnostic only")
    print("=" * 78)
    for s in summaries:
        if "failure" in s:
            print(f"\n[{s['case_id']}] FAILURE: {s['failure']}")
            continue
        print(f"\n[{s['case_id']}] target={s['target_angle_deg']}deg  "
              f"target_wall_nodes={s['target_wall_count']}  "
              f"rejected(path-30)={s['rejected_count']}  "
              f"accepted(path30)={s['accepted_count']}")
        print(f"  contact-line band: {s['contact_line_band_count']} nodes  "
              f"path30={s['clband_path30_fraction']}  "
              f"path-30={s['clband_path_minus30_fraction']}  "
              f"strict_ready={s['clband_strict_write_ready_fraction']}")
        print(f"  fallback_reason_histogram_rejected: {s['fallback_reason_histogram_rejected']}")
        print(f"  hypothesis_histogram_rejected: {s['hypothesis_histogram_rejected']}")
        dc = s["dominant_cause"]
        print(f"  DOMINANT CAUSE: {dc.get('verdict')}  "
              f"top1={dc.get('top1')}  top2={dc.get('top2')}")
    print(f"\nWrote: {json_path}")
    if not args.no_csv and case_records:
        print(f"Wrote: {report.get('per_node_csv')}  ({report.get('per_node_row_count')} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
