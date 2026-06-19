#!/usr/bin/env python3
"""C1 sanity probe: WHERE are the 'active' nodes, and why does the contact-line
band collapse frac_outward to 0.5? Inspect the y-stratification and the
geometry of the 'active' mask so we understand the 2026-06-19 finding that
guard-1 (active & not-wall & clband) kills the direction signal.

Diagnostic only; does not change anything.
"""
from __future__ import annotations
import glob
from pathlib import Path
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy as v2n

ROOT = Path("/home/yuan/stage15b_shadow_matrix")
CX = CZ = 48.0
EPS_Q = 0.05

def load(path):
    r = vtk.vtkXMLImageDataReader(); r.SetFileName(str(path)); r.Update()
    img = r.GetOutput(); d = img.GetCellData(); A = {}
    for i in range(d.GetNumberOfArrays()):
        a = d.GetArray(i); A[a.GetName()] = v2n(a).copy()
    dims = tuple(v - 1 for v in img.GetDimensions())
    return dims, A

def probe(name, dims, A):
    nx, ny, nz = dims
    ph3 = A["PhaseField"].reshape((nx, ny, nz))
    isb = A["IsItBoundary"].reshape((nx, ny, nz))
    act = A["DynamicCLActive"].reshape((nx, ny, nz))
    cr  = A["DynamicCLCosResidual"].reshape((nx, ny, nz))
    TX  = A["DynamicCLTangentialX"].reshape((nx, ny, nz))
    TZ  = A["DynamicCLTangentialZ"].reshape((nx, ny, nz))

    print(f"\n===== {name}  dims={dims} =====")
    # active by y-layer
    act_per_y = act.sum(axis=(0, 2))
    print(f"  active counts by y-layer: {act_per_y.astype(int).tolist()}")
    isb_per_y = (isb >= 0.5).sum(axis=(0, 2))
    print(f"  IsItBoundary>=0.5 by y-layer: {isb_per_y.astype(int).tolist()}")

    # how many active nodes are wall vs not, and in-band vs out-of-band
    m_act = act > 0.5
    n_act = int(m_act.sum())
    m_wall = isb >= 0.5
    m_clband = (ph3 > EPS_Q) & (ph3 < 1 - EPS_Q)
    print(f"  active total={n_act}  active&wall={int((m_act & m_wall).sum())}"
          f"  active&not-wall={int((m_act & ~m_wall).sum())}")
    print(f"  active&not-wall&clband={int((m_act & ~m_wall & m_clband).sum())}"
          f"  active&not-wall&out-of-band={int((m_act & ~m_wall & ~m_clband).sum())}")

    # for the in-band not-wall active set, examine the geometry: radial position
    # distribution and the cos_res sign by radial bin. A contact line on a FLAT
    # lower wall has a CIRCULAR footprint, so the band nodes sit at a ring of
    # roughly constant radius. If frac_outward==0.5 it may be because the ring
    # is symmetric in azimuth and t.e_r averages to ~0 -- which is expected for
    # a CIRCULAR contact line (tangents are azimuthal, perpendicular to radial!).
    xs = np.arange(nx).reshape((nx, 1, 1)).astype(float)
    zs = np.arange(nz).reshape((1, 1, nz)).astype(float)
    rr = np.broadcast_to(np.sqrt((xs - CX) ** 2 + (zs - CZ) ** 2), (nx, ny, nz)).copy()
    m = m_act & ~m_wall & m_clband
    if m.sum() > 0:
        rr_a = rr[m]; cr_a = cr[m]
        erx = np.broadcast_to((xs - CX) / (rr + 1e-12), (nx, ny, nz)).copy()
        erz = np.broadcast_to((zs - CZ) / (rr + 1e-12), (nx, ny, nz)).copy()
        tanr = (TX * erx + TZ * erz)[m]
        print(f"  in-band active: radius mean={rr_a.mean():.2f} min={rr_a.min():.2f}"
              f" max={rr_a.max():.2f}  (droplet center r=0)")
        print(f"  in-band active: cos_res mean={cr_a.mean():+.4f} sign>0 frac={np.mean(cr_a>0):.3f}")
        print(f"  in-band active: t.e_r mean={tanr.mean():+.4f}  |t.e_r| mean={np.mean(np.abs(tanr)):.4f}")
        print(f"  NOTE: if |t.e_r| ~ 0 on a ring, tangents are AZIMUTHAL (perp to"
              f" radial) -> that is why a flat circular contact line gives D~0.")
        # what is the dominant tangent direction? compare |t_y| vs horizontal tan
        TY = A["DynamicCLTangentialY"].reshape((nx,ny,nz))
        ty_a = TY[m]; txa = TX[m]; tza = TZ[m]
        hmag = np.sqrt(txa**2 + tza**2)
        print(f"  |t_y| mean={np.mean(np.abs(ty_a)):.4f}  |t_horiz| mean={np.mean(hmag):.4f}"
              f"  (t_y dominant => tangents point UP the wall, not along footprint)")

for cd in sorted((ROOT / "decoupled").glob("decouple_wall_*")):
    vtis = sorted(glob.glob(str(cd / "output" / "case_VTK_P00_*.vti")),
                  key=lambda p: int(p.split("_")[-1].split(".")[0]))
    dims, A = load(vtis[-1])
    probe(f"dec/{cd.name}", dims, A)
