#!/usr/bin/env python3
"""Read DynamicCL contact-line trajectory from a case's pvti frames.

Per frame prints: step, theta_app mean (active), |R_theta| mean (active),
mean radial projection of the candidate force (sign: + = outward/spread),
frac(radial>0), PhaseF NaN count, n_active.

Usage: python3 read_cl_traj.py <case_dir> [x0] [z0]
"""
import sys, glob
from pathlib import Path
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy


def load(p):
    r = vtk.vtkXMLPImageDataReader(); r.SetFileName(p); r.Update()
    o = r.GetOutput()
    dims = o.GetDimensions(); nx, ny, nz = dims[0]-1, dims[1]-1, dims[2]-1
    origin = o.GetOrigin(); spacing = o.GetSpacing()
    cd = o.GetCellData()
    def get(n):
        a = cd.GetArray(n)
        return (vtk_to_numpy(a).reshape((nz, ny, nx)) if a is not None else None)
    return get, (nx, ny, nz), origin, spacing


def main():
    casedir = sys.argv[1]
    x0 = float(sys.argv[2]) if len(sys.argv) > 2 else 48.0
    z0 = float(sys.argv[3]) if len(sys.argv) > 3 else 48.0
    frames = sorted(
        glob.glob(str(Path(casedir)/"output"/"case_VTK_P00_*.pvti")),
        key=lambda p: int(p.split("_")[-1].split(".")[0]),
    )
    print(f"# {casedir}: {len(frames)} frames; center=({x0},{z0})")
    print(f"{'step':>6} {'th_app':>9} {'|R|':>9} {'Fpar_mean':>12} {'Fpar>0%':>8} {'NaN':>8} {'n_act':>7}")
    for p in frames:
        step = int(p.split("_")[-1].split(".")[0])
        get, (nx, ny, nz), origin, spacing = load(p)
        active = get("DynamicCLActive")
        if active is None:
            print(f"{step:>6}  MISSING DynamicCLActive (field not in VTI)"); continue
        act = active > 0.5
        n_act = int(act.sum())
        pf = get("PhaseField")
        if pf is None: pf = get("PhaseF")
        nan = int(np.isnan(pf).sum()) if pf is not None else -1
        th = get("DynamicCLThetaApp"); res = get("DynamicCLCosResidual")
        th_m = float(th[act].mean()) if (th is not None and n_act > 0) else float('nan')
        r_m = float(np.abs(res[act]).mean()) if (res is not None and n_act > 0) else float('nan')
        fx = get("DynamicCLForceCandidateX"); fz = get("DynamicCLForceCandidateZ")
        fpar_mean = float('nan'); fpos = float('nan')
        if fx is not None and fz is not None and n_act > 0:
            ix = np.arange(nx)*spacing[0] + origin[0] + 0.5*spacing[0]
            iz = np.arange(nz)*spacing[2] + origin[2] + 0.5*spacing[2]
            kz, jy, ixs = np.where(act)   # shape (nz,ny,nx) -> [z,y,x]
            xc = ix[ixs]; zc = iz[kz]
            rx = xc - x0; rz = zc - z0
            rm = np.sqrt(rx*rx + rz*rz)
            good = rm > 1e-9
            erx = np.zeros_like(rx); erz = np.zeros_like(rz)
            erx[good] = rx[good]/rm[good]; erz[good] = rz[good]/rm[good]
            fpar = fx[act]*erx + fz[act]*erz
            fpar_mean = float(fpar.mean()); fpos = float((fpar > 0).mean())
        print(f"{step:>6} {th_m:>9.3f} {r_m:>9.4f} {fpar_mean:>+12.3e} {fpos:>8.3f} {nan:>8d} {n_act:>