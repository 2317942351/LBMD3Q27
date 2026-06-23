#!/usr/bin/env python3
"""Stage 14C-prime: stencil-dilution + F_surf_tangent + spurious-current audit.

DIAGNOSTIC ONLY. Reads EXISTING Stage13 flat-wall VTI outputs (no rerun, no
recompile, no wetting-physics change). It answers three questions that the
Stage 14A result left open (see 25_stage14A_result_20260617.md):

  Q1 (stencil dilution): The compact ghost is written into WallGhost at the
      contact line. How much of the solver's gradPhi / mu / F_surf actually
      comes from that ghost, given it enters the 26-point IsotropicGrad stencil
      at only 1-3 of 26 neighbours?

  Q2 (force direction): Is F_surf = mu*gradPhi, projected onto the contact-line
      tangent, pointing the right way (toward the target angle), and is it
      large enough to move the line?

  Q3 (spurious current): The circle-fit RMS grows 50-80x over 12k steps. Is the
      spurious velocity concentrated at the contact line (wetting-drive defect)
      or in the bulk interface (phase-field / surface-tension stability)?

This reproduces the solver's stencil EXACTLY because the run used NO OutFlow
option, so calcGradPhi / calcMu take the plain else-branch:
    gradPhi = IsotropicGrad(STAGE13_PHASE_FOR_STENCIL)
    lpPhi   = myLaplace(STAGE13_PHASE_FOR_STENCIL)
and STAGE13_PHASE_FOR_STENCIL(dx,dy,dz) returns:
    WallGhost   if IsBoundary(dx,dy,dz) > 0.5 and that ghost is valid,
    PhaseF(dx,dy,dz) otherwise (real fluid value).

Stencil weights (model.R IsotropicGrad / myLaplace, verified):
    grad component:  axial neighbour (coef 16, /72),
                     face-diagonal (coef 4, /72),
                     body-diagonal (coef 1, /72)
    laplacian:       axial (16), face-diag (4), body-diag (1), center -152, /36

Because every ghost enters only at the boundary neighbours of a boundary-fluid
node, the ghost contribution to gradPhi is the sum over those boundary
neighbours of coef*(WallGhost - PhaseF_center) — recoverable from VTI alone.

chemical potential (Dynamics.c.Rt:439-440, no thermo):
    mu = 4*(12*sigma/IntWidth)*(C-l)*(C-h)*(C-0.5(l+h)) - (1.5*sigma*IntWidth)*lpPhi
sigma, IntWidth, PhaseField_l/h are read from case_metadata.json.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np


# ---------------------------------------------------------------------------
# Stencil specification: (dx,dy,dz) -> coefficient, for the FLAT wall only.
# FlatLowerY is at y=0; the only boundary neighbours of a y=1 fluid node that
# can carry a WallGhost are those with dy = -1. For a y=1 node, neighbours with
# dy=-1 land at y=0 (the wall). All other neighbours (dy in {0,+1}) are fluid.
# So for FlatLowerY the ghost-carrying neighbour set is exactly dy==-1.
# ---------------------------------------------------------------------------

# IsotropicGrad weights (pre-division by 72). Component-specific sign handled
# separately because grad is a difference (a-b), not a sum.
GRAD_AXIAL = 16.0
GRAD_FACE = 4.0
GRAD_BODY = 1.0
GRAD_DIV = 72.0

# myLaplace weights (pre-division by 36), center -152.
LAP_AXIAL = 16.0
LAP_FACE = 4.0
LAP_BODY = 1.0
LAP_CENTER = -152.0
LAP_DIV = 36.0

# Full 26-neighbour offset list with weight class.
# class 'axial' (6): one coord +-1, coef 16
# class 'face'   (12): two coords +-1, coef 4
# class 'body'   (8): three coords +-1, coef 1
def neighbour_table() -> list[tuple[int, int, int, float, str]]:
    out: list[tuple[int, int, int, float, str]] = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                if dx == 0 and dy == 0 and dz == 0:
                    continue
                nz = (abs(dx) + abs(dy) + abs(dz))
                if nz == 1:
                    cls, w = "axial", GRAD_AXIAL
                elif nz == 2:
                    cls, w = "face", GRAD_FACE
                else:
                    cls, w = "body", GRAD_BODY
                out.append((dx, dy, dz, w, cls))
    return out


NEIGH = neighbour_table()


def step_of(path: Path) -> int:
    m = re.search(r"P00_(\d+)\.vti$", path.name)
    return int(m.group(1)) if m else -1


def load_vti(path: Path) -> tuple[tuple[int, int, int], dict[str, np.ndarray]]:
    import vtk
    from vtk.util.numpy_support import vtk_to_numpy
    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(str(path))
    reader.Update()
    img = reader.GetOutput()
    dims = tuple(int(v) - 1 for v in img.GetDimensions())
    data = img.GetCellData()
    arrays: dict[str, np.ndarray] = {}
    for i in range(data.GetNumberOfArrays()):
        a = data.GetArray(i)
        arrays[a.GetName() or f"array_{i}"] = vtk_to_numpy(a).copy()
    return dims, arrays


def reshape3(a: np.ndarray, dims: tuple[int, int, int]) -> np.ndarray:
    """VTI cell data is flattened; reshape to (nx,ny,nz) for indexing [x,y,z].
    Vector (multi-component) arrays come in as (ncells, ncomp); reshape each
    component into (nx,ny,nz) and stack along a new last axis."""
    nx, ny, nz = dims
    ncells = nx * ny * nz
    if a.ndim == 1:
        return a.reshape((nx, ny, nz))
    # multi-component: (ncells, ncomp) -> (nx,ny,nz,ncomp)
    ncomp = a.shape[1] if a.ndim == 2 else 1
    return a.reshape((nx, ny, nz, ncomp))


def shift(a3: np.ndarray, dx: int, dy: int, dz: int) -> np.ndarray:
    """Return a3 shifted so that index (x,y,z) reads neighbour at (x+dx,y+dy,z+dz).
    Boundary cells outside the domain are filled with NaN so they are excluded."""
    nx, ny, nz = a3.shape
    out = np.full_like(a3, np.nan)
    # out[i] = a3[i + d] per axis; compute src/dst slice ranges.
    def ranges(d, n):
        i0 = max(0, -d)
        i1 = min(n, n - d)
        return i0 + d, i1 + d, i0, i1  # src_start, src_end, dst_start, dst_end
    sxs, x1s, dxs, dx1 = ranges(dx, nx)
    sys, y1s, dys, dy1 = ranges(dy, ny)
    szs, z1s, dzs, dz1 = ranges(dz, nz)
    out[dxs:dx1, dys:dy1, dzs:dz1] = a3[sxs:x1s, sys:y1s, szs:z1s]
    return out


def stage13_value_for_stencil(
    phase3: np.ndarray, isbnd3: np.ndarray, ghost3: np.ndarray, center3: np.ndarray
) -> dict[tuple[int, int, int], np.ndarray]:
    """Reproduce STAGE13_PHASE_FOR_STENCIL(dx,dy,dz) per neighbour, returning the
    value the solver uses at each neighbour offset. For the NO-WallGradMode path:

        if IsBoundary(nbr)>0.5 and ghost valid:  ghost
        elif PhaseF(nbr) valid:                  PhaseF(nbr)
        elif ghost valid:                        ghost   (fallback)
        else:                                    center  (midpoint fallback)

    Also returns a boolean mask 'is_ghost_source' telling which offsets sourced
    from the WallGhost (for the dilution metric).
    """
    vals: dict[tuple[int, int, int], np.ndarray] = {}
    is_ghost: dict[tuple[int, int, int], np.ndarray] = {}
    for (dx, dy, dz, _w, _cls) in NEIGH:
        nb_phase = shift(phase3, dx, dy, dz)
        nb_isbnd = shift(isbnd3, dx, dy, dz)
        nb_ghost = shift(ghost3, dx, dy, dz)
        phase_valid = np.isfinite(nb_phase) & (nb_phase > -100.0) & (nb_phase < 100.0)
        ghost_valid = np.isfinite(nb_ghost) & (nb_ghost > -100.0) & (nb_ghost < 100.0)
        boundary_nbr = nb_isbnd > 0.5
        # primary ghost substitution: boundary neighbour with valid ghost
        use_ghost_primary = boundary_nbr & ghost_valid
        # else valid phase
        use_phase = (~use_ghost_primary) & phase_valid
        # else ghost fallback
        use_ghost_fb = (~use_ghost_primary) & (~use_phase) & ghost_valid
        # else center midpoint
        use_center = (~use_ghost_primary) & (~use_phase) & (~use_ghost_fb)

        val = np.where(use_ghost_primary, nb_ghost,
              np.where(use_phase, nb_phase,
              np.where(use_ghost_fb, nb_ghost, center3)))
        ig = use_ghost_primary | use_ghost_fb
        vals[(dx, dy, dz)] = val
        is_ghost[(dx, dy, dz)] = ig
    return vals, is_ghost


def grad_full_and_ghost(
    vals: dict, is_ghost: dict, comp: str
) -> tuple[np.ndarray, np.ndarray]:
    """Full gradPhi component and the ghost-sourced sub-sum, both /72."""
    signs = {
        "x": {(1,0,0):1,(-1,0,0):-1,(1,1,1):1,(-1,1,1):-1,(1,-1,1):1,(-1,-1,1):-1,
              (1,1,-1):1,(-1,1,-1):-1,(1,-1,-1):1,(-1,-1,-1):-1,(1,1,0):1,(-1,1,0):-1,
              (1,-1,0):1,(-1,-1,0):-1,(1,0,1):1,(-1,0,1):-1,(1,0,-1):1,(-1,0,-1):-1},
        "y": {(0,1,0):1,(0,-1,0):-1,(1,1,1):1,(-1,1,1):1,(1,-1,1):-1,(-1,-1,1):-1,
              (1,1,-1):1,(-1,1,-1):1,(1,-1,-1):-1,(-1,-1,-1):-1,(1,1,0):1,(-1,1,0):1,
              (1,-1,0):-1,(-1,-1,0):-1,(0,1,1):1,(0,-1,1):-1,(0,1,-1):1,(0,-1,-1):-1},
        "z": {(0,0,1):1,(0,0,-1):-1,(1,1,1):1,(-1,1,1):1,(1,-1,1):1,(-1,-1,1):1,
              (1,1,-1):-1,(-1,1,-1):-1,(1,-1,-1):-1,(-1,-1,-1):-1,(1,0,1):1,(-1,0,1):1,
              (1,0,-1):-1,(-1,0,-1):-1,(0,1,1):1,(0,-1,1):1,(0,1,-1):-1,(0,-1,-1):-1},
    }
    def wof(off):
        nz = abs(off[0])+abs(off[1])+abs(off[2])
        return GRAD_AXIAL if nz==1 else (GRAD_FACE if nz==2 else GRAD_BODY)
    total = None
    ghost = None
    for off in signs[comp]:
        s = signs[comp][off]; w = wof(off)
        term = s * w * vals[off]
        gterm = np.where(is_ghost[off], term, 0.0)
        if total is None:
            total = term.copy(); ghost = gterm.copy()
        else:
            total = total + term; ghost = ghost + gterm
    return total / GRAD_DIV, ghost / GRAD_DIV


def laplacian_full_and_ghost(vals: dict, is_ghost: dict, center3: np.ndarray):
    def wof(off):
        nz = abs(off[0])+abs(off[1])+abs(off[2])
        return LAP_AXIAL if nz==1 else (LAP_FACE if nz==2 else LAP_BODY)
    total = LAP_CENTER * center3
    ghost = np.zeros_like(center3)
    for (dx,dy,dz,_w,cls) in NEIGH:
        off = (dx,dy,dz); w = wof(off)
        total = total + w * vals[off]
        ghost = ghost + np.where(is_ghost[off], w * vals[off], 0.0)
    return total / LAP_DIV, ghost / LAP_DIV


def safe_div(num: np.ndarray, den: np.ndarray, fill=0.0) -> np.ndarray:
    return np.where(np.abs(den) > 1e-30, num / np.where(np.abs(den)>1e-30, den, 1.0), fill)


def stats_over(mask: np.ndarray, *arrs) -> list[dict]:
    out = []
    for a in arrs:
        if not np.any(mask):
            out.append({"count":0}); continue
        v = a[mask & np.isfinite(a)]
        if v.size == 0:
            out.append({"count":0}); continue
        out.append({
            "count": int(v.size),
            "min": float(np.min(v)), "max": float(np.max(v)),
            "mean": float(np.mean(v)), "p50": float(np.percentile(v,50)),
            "p95": float(np.percentile(v,95)),
            "mean_abs": float(np.mean(np.abs(v))),
            "max_abs": float(np.max(np.abs(v))),
        })
    return out


def audit_vti(case_dir: Path, vtis: list[Path], metadata: dict) -> dict:
    sigma = float(metadata.get("sigma", 5e-05))
    IntWidth = float(metadata.get("interface_width", metadata.get("IntWidth", 3)))
    # PhaseField_l/h are not in the flat-wall metadata; default to TCLB 0/1.
    pfl = float(metadata.get("PhaseField_l", 0.0))
    pfh = float(metadata.get("PhaseField_h", 1.0))
    bc_theta = metadata.get("bc_theta_deg")
    init_theta = metadata.get("init_theta_deg")

    per_step = []
    for vti in vtis:
        dims, A = load_vti(vti)
        nx, ny, nz = dims
        phase = reshape3(A["PhaseField"], dims)
        isbnd = reshape3(A["IsItBoundary"], dims)
        ghost = reshape3(A["WallGhost"], dims)
        center = phase  # PhaseF(0,0,0) is the center value
        U = reshape3(A["U"], dims)
        # U is a multi-component array; extract components
        if U.ndim == 4:
            ux, uy, uz = U[...,0], U[...,1], U[...,2]
        else:
            ux = uy = uz = U
        local_angle = reshape3(A["LocalRadAngle"], dims)

        vals, is_ghost = stage13_value_for_stencil(phase, isbnd, ghost, center)
        gxt, gxg = grad_full_and_ghost(vals, is_ghost, "x")
        gyt, gyg = grad_full_and_ghost(vals, is_ghost, "y")
        gzt, gzg = grad_full_and_ghost(vals, is_ghost, "z")
        lpt, lpg = laplacian_full_and_ghost(vals, is_ghost, center)

        # chemical potential and its ghost-sourced part
        C = phase
        pfavg = 0.5*(pfl+pfh)
        beta = 12.0*sigma/IntWidth
        kappa = 1.5*sigma*IntWidth
        mu_bulk_pref = 4.0*beta*(C-pfl)*(C-pfh)*(C-pfavg)
        mu_total = mu_bulk_pref - kappa*lpt
        # mu ghost part comes only through -kappa*lpt_ghost (the (C-..)(C-..)(C-..)
        # term uses center C, not neighbours, so it has no ghost contribution)
        mu_ghost = -kappa*lpg

        # F_surf = mu * gradPhi ; ghost part approx mu_total*grad_ghost (leading term)
        Fsx = mu_total*gxt; Fsy = mu_total*gyt; Fsz = mu_total*gzt
        Fsxg = mu_total*gxg; Fsyg = mu_total*gyg; Fszg = mu_total*gzg

        # wall normal: flat wall, n_w = +y (solid below, fluid above)
        nwx, nwy, nwz = 0.0, 1.0, 0.0

        # masks
        wall = isbnd > 0.5
        # boundary fluid nodes: y==1 row (just above the FlatLowerY wall)
        bf = np.zeros_like(wall, dtype=bool)
        if ny >= 2:
            bf[:, 1, :] = True
        bf = bf & (~wall)
        # target wall patch: exclude outer-domain edge columns
        tp = np.zeros_like(wall, dtype=bool)
        tp[1:nx-1, 0, 1:nz-1] = True
        target_wall = wall & tp
        # contact-line band: boundary fluid nodes with interface q
        q = (C - pfl) / (pfh - pfl) if abs(pfh-pfl) > 1e-30 else C
        clband = bf & (q > 0.05) & (q < 0.95) & np.isfinite(C)
        # bulk interface: interface band but NOT near wall (y >= 4)
        bulk_if = (q > 0.05) & (q < 0.95) & np.isfinite(C)
        bulk_if = bulk_if.copy()
        bulk_if[:, 0:4, :] = False

        # ghost fraction metrics on clband
        gmag = np.sqrt(gxt**2 + gyt**2 + gzt**2)
        ggmag = np.sqrt(gxg**2 + gyg**2 + gzg**2)
        # tangent/normal decomposition of gradPhi (n_w = +y)
        gn = gyt  # normal component
        gt_x, gt_z = gxt, gzt
        gtmag = np.sqrt(gxt**2 + gzt**2)
        ggn = gyg
        ggtx, ggtz = gxg, gzg
        ggtmag = np.sqrt(gxg**2 + gzg**2)
        ghost_frac_total = safe_div(ggmag, gmag)
        ghost_frac_tan = safe_div(ggtmag, gtmag)
        ghost_frac_norm = safe_div(np.abs(ggn), np.abs(gn))

        # F_surf tangent magnitude (along x-z plane = contact-line tangent plane)
        Fs_tan_mag = np.sqrt(Fsx**2 + Fsz**2)
        Fs_tan_ghost = np.sqrt(Fsxg**2 + Fszg**2)
        Fs_total_mag = np.sqrt(Fsx**2 + Fsy**2 + Fsz**2)

        # speed magnitudes
        Umag = np.sqrt(ux**2 + uy**2 + uz**2)
        # near-wall tangent velocity (x-z) at clband
        Utan_cl = np.sqrt(ux**2 + uz**2)

        rec = {
            "step": step_of(vti),
            "dims": list(dims),
            "clband_count": int(np.count_nonzero(clband)),
            "bulk_if_count": int(np.count_nonzero(bulk_if)),
            "target_wall_count": int(np.count_nonzero(target_wall)),
            # Q1 stencil dilution on clband
            "ghost_frac_total_cl": stats_over(clband, ghost_frac_total)[0],
            "ghost_frac_tan_cl": stats_over(clband, ghost_frac_tan)[0],
            "ghost_frac_norm_cl": stats_over(clband, ghost_frac_norm)[0],
            "gradmag_cl": stats_over(clband, gmag)[0],
            # Q2 F_surf on clband
            "Fs_total_mag_cl": stats_over(clband, Fs_total_mag)[0],
            "Fs_tan_mag_cl": stats_over(clband, Fs_tan_mag)[0],
            "Fs_tan_ghost_frac_cl": stats_over(clband, safe_div(Fs_tan_ghost, Fs_tan_mag))[0],
            "mu_cl": stats_over(clband, mu_total)[0],
            "mu_ghost_frac_cl": stats_over(clband, safe_div(np.abs(mu_ghost), np.abs(mu_total)+1e-30))[0],
            # direction sanity: sign of F_surf tangent vs target motion
            # 60->30 (shrink): footprint should shrink => Fs_tan points inward (negative radial)
            # We report mean of Fs projected onto radial-outward direction.
            # radial direction at (x,y,z): (x-cx, z-cz)/r with cx=cz=48
            # Q3 spurious current
            "Umag_cl": stats_over(clband, Umag)[0],
            "Utan_cl": stats_over(clband, Utan_cl)[0],
            "Umag_bulk_if": stats_over(bulk_if, Umag)[0],
            "Umag_all": stats_over(np.isfinite(Umag), Umag)[0],
            "maxU_all": float(np.nanmax(Umag)) if np.isfinite(Umag).any() else None,
        }

        # contact-line force direction: project F_surf onto radial outward at clband.
        # radial direction lies in the x-z plane (the wall plane); build full 3D grids.
        xv = np.arange(nx).reshape(nx, 1, 1)
        zv = np.arange(nz).reshape(1, 1, nz)
        xs = np.broadcast_to(xv, (nx, ny, nz)).astype(float)
        zs = np.broadcast_to(zv, (nx, ny, nz)).astype(float)
        cx = cz = 48.0
        rx = xs - cx; rz = zs - cz
        rrmag = np.sqrt(rx**2 + rz**2) + 1e-12
        rxn = rx / rrmag; rzn = rz / rrmag
        Fs_radial = Fsx*rxn + Fsz*rzn  # + = outward (expands footprint/raises angle)
        rec["Fs_radial_mean_cl"] = float(np.nanmean(Fs_radial[clband & np.isfinite(Fs_radial)])) if np.any(clband) else None
        rec["Fs_radial_p50_cl"] = float(np.nanpercentile(Fs_radial[clband & np.isfinite(Fs_radial)], 50)) if np.any(clband & np.isfinite(Fs_radial)) else None
        per_step.append(rec)
    return {
        "case": case_dir.name,
        "bc_theta_deg": bc_theta,
        "init_theta_deg": init_theta,
        "sigma": sigma,
        "IntWidth": IntWidth,
        "PhaseField_l": pfl,
        "PhaseField_h": pfh,
        "claim_limit": "stage14c-prime diagnostic; not validation_passed",
        "per_step": per_step,
    }


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path, help="root containing case dirs with output/*.vti")
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--steps", type=str, default="last",
                   help="'last' (default), 'all', or comma list like 0,4000,12000")
    return p.parse_args()


def select_vtis(case_dir: Path, mode: str) -> list[Path]:
    vtis = sorted((case_dir / "output").glob("case_VTK_P00_*.vti"), key=step_of)
    if not vtis:
        return []
    if mode == "last":
        return [vtis[-1]]
    if mode == "all":
        return vtis
    want = set()
    for tok in mode.split(","):
        try:
            want.add(int(tok))
        except ValueError:
            pass
    return [v for v in vtis if step_of(v) in want] or [vtis[-1]]


def main() -> int:
    args = parse_args()
    case_dirs = sorted(
        d for d in args.root.iterdir()
        if d.is_dir() and (d / "case_metadata.json").exists()
    )
    report = {
        "stage": "stage14c_prime_stencil_dilution_current",
        "root": str(args.root),
        "claim_limit": "exploratory_not_validation; diagnostic only",
        "stencil_note": (
            "Reproduces solver IsotropicGrad/myLaplace with STAGE13_PHASE_FOR_STENCIL "
            "(boundary neighbour -> WallGhost). Run used no OutFlow option, so the "
            "plain else-branch applies. ghost_frac_* are the fraction of gradPhi/mu "
            "magnitude sourced from WallGhost neighbours."
        ),
        "cases": [],
    }
    for cd in case_dirs:
        meta = json.loads((cd / "case_metadata.json").read_text(encoding="utf-8"))
        # inherit sigma/IntWidth if missing from metadata
        meta.setdefault("sigma", 5e-05)
        meta.setdefault("interface_width", meta.get("IntWidth", 3))
        vtis = select_vtis(cd, args.steps)
        if not vtis:
            report["cases"].append({"case": cd.name, "failure": "no_vti"})
            continue
        report["cases"].append(audit_vti(cd, vtis, meta))

    out_path = args.out or (args.root / "stage14c_prime_audit.json")
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    # console summary
    print("=" * 92)
    print("Stage 14C-prime: stencil dilution + F_surf tangent + spurious current")
    print("claim_limit: exploratory_not_validation; diagnostic only")
    print("=" * 92)
    for c in report["cases"]:
        if "failure" in c:
            print("\n[%s] FAILURE %s" % (c["case"], c["failure"])); continue
        ps = c["per_step"][-1]
        tgt = c["bc_theta_deg"]
        print("\n[%s] target=%s deg (step %s)" % (c["case"], tgt, ps["step"]))
        print("  Q1 ghost_frac on contact-line band:")
        print("    total  mean=%.4f p95=%.4f" % (ps["ghost_frac_total_cl"]["mean"], ps["ghost_frac_total_cl"]["p95"]))
        print("    tangent mean=%.4f p95=%.4f" % (ps["ghost_frac_tan_cl"]["mean"], ps["ghost_frac_tan_cl"]["p95"]))
        print("    normal  mean=%.4f p95=%.4f" % (ps["ghost_frac_norm_cl"]["mean"], ps["ghost_frac_norm_cl"]["p95"]))
        print("    mu_ghost_frac mean=%.4f" % ps["mu_ghost_frac_cl"]["mean"])
        print("  Q2 F_surf on contact-line band:")
        print("    |Fs_total| mean=%.4g p95=%.4g   |Fs_tan| mean=%.4g" % (
            ps["Fs_total_mag_cl"]["mean"], ps["Fs_total_mag_cl"]["p95"], ps["Fs_tan_mag_cl"]["mean"]))
        print("    Fs_radial mean=%.4g p50=%.4g  (+outward/raise angle)" % (
            ps.get("Fs_radial_mean_cl"), ps.get("Fs_radial_p50_cl")))
        print("  Q3 velocity:")
        print("    |U| clband mean=%.4g max=%.4g   bulk_if mean=%.4g   all max=%.4g" % (
            ps["Umag_cl"]["mean"], ps["Umag_cl"]["max"],
            ps["Umag_bulk_if"]["mean"], ps["maxU_all"]))
    print("\nWrote:", out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
