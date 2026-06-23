#!/usr/bin/env python3
"""Gate 3 probe: WHY do y>=2 fluid nodes report DynamicCLWallContextFound=1
with WallDy=-1 (claiming their (x,y-1,z) neighbour is a wetting wall)?

For the flat-wall case the only real wall is y=0. If a y=2 node reports a
wet wall at y=1, then either:
  (a) the y=1 node has IsBoundary>0 and AnalyticFlag>0 (it got mis-marked), or
  (b) the field-access IsBoundary(0,-1,0) does not mean what we think.

This script reads the final-step VTI and inspects the y=1 layer's flags
directly, and cross-checks a sample of y=2 context-found nodes.
"""
import sys
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy


def main():
    path = sys.argv[1]
    reader = vtk.vtkXMLPImageDataReader()
    reader.SetFileName(path)
    reader.Update()
    out = reader.GetOutput()
    dims = out.GetDimensions()
    nx_c, ny_c, nz_c = dims[0] - 1, dims[1] - 1, dims[2] - 1
    cd = out.GetCellData()

    def get(name):
        a = cd.GetArray(name)
        return vtk_to_numpy(a).reshape((nz_c, ny_c, nx_c)) if a is not None else None

    print(f"cells: {nx_c}x{ny_c}x{nz_c}")
    ib = get("IsItBoundary")       # the raw boundary flag stored as a field
    af = get("AnalyticFlag")
    lra = get("LocalRadAngle")
    found = get("DynamicCLWallContextFound")
    wdy = get("DynamicCLWallDy")

    # --- what does the y=1 LAYER look like? (cell index iy=1) ---
    print("\n=== y=1 cell layer (iy=1) flags ===")
    for nm, arr in [("IsItBoundary", ib), ("AnalyticFlag", af), ("LocalRadAngle", lra),
                    ("DynamicCLWallContextFound", found)]:
        if arr is not None:
            sl = arr[:, 1, :]
            print(f"  {nm}: nonzero={np.count_nonzero(sl)}, sum={sl.sum():.1f}, "
                  f"unique={np.unique(np.round(sl,4))}")

    # --- a sample of y=2 context-found nodes: what is their (x,1,z) neighbour? ---
    print("\n=== y=2 nodes WITH context_found=1: inspect (x,1,z) neighbour ===")
    if found is not None:
        cf2 = found[:, 2, :] > 0.5
        zz, xx = np.where(cf2)
        print(f"  y=2 context_found count: {cf2.sum()}")
        if cf2.sum() > 0:
            sample = np.random.choice(len(zz), min(5, len(zz)), replace=False)
            for s in sample:
                iz, ix = zz[s], xx[s]
                print(f"  cell (ix={ix}, iy=2, iz={iz}): "
                      f"its (iy=1) nb IsB={ib[iz,1,ix]:.0f} AF={af[iz,1,ix]:.0f} "
                      f"LRA={lra[iz,1,ix]:.4f} found_here={found[iz,2,ix]:.0f} "
                      f"wdy={wdy[iz,2,ix]:.0f}")

    # --- cross-tabulate: for ALL context_found nodes, what is their y-1 neighbour? ---
    print("\n=== all context_found nodes: IsBoundary of their (x,y-1,z) neighbour ===")
    if found is not None and ib is not None:
        cf = found > 0.5
        zz, yy, xx = np.where(cf)
        # neighbour at y-1; skip those at y=0
        valid = yy > 0
        nb_ib = ib[zz[valid], yy[valid] - 1, xx[valid]]
        nb_af = af[zz[valid], yy[valid] - 1, xx[valid]]
        print(f"  context_found nodes with y>0: {valid.sum()}")
        print(f"  their (y-1) neighbour IsItBoundary: unique={np.unique(nb_ib)}, "
              f"count IsB>0={np.count_nonzero(nb_ib)}")
        print(f"  their (y-1) neighbour AnalyticFlag: unique={np.unique(nb_af)}, "
              f"count AF>0={np.count_nonzero(nb_af)}")
        # breakdown by the context_found node's own y
        print(f"  --- breakdown of context_found count by node y, with y-1 nb IsB=1 ---")
        for y in range(min(8, ny_c)):
            sel = yy == y
            if sel.sum() == 0:
                continue
            if y > 0:
                nb_sel = ib[zz[sel], y - 1, xx[sel]]
                isb1 = np.count_nonzero(nb_sel)
                af_sel = af[zz[sel], y - 1, xx[sel]]
                af1 = np.count_nonzero(af_sel)
                print(f"    y={y}: found={sel.sum()}, their(y-1)IsB>0={isb1}, (y-1)AF>0={af1}")
            else:
                print(f"    y={y}: found={sel.sum()} (y=0, no y-1 nb)")


if __name__ == "__main__":
    main()
