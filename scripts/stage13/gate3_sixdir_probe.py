#!/usr/bin/env python3
"""Gate 3 six-direction probe: for y=2 context_found nodes, scan ALL 6 face
neighbours to find which direction actually satisfies the wetting-wall test
(IsBoundary>0 AND AnalyticFlag>0 AND valid LocalRadAngle). Resolves the
contradiction: WallDy=-1 claims the (y-1) neighbour is the wet wall, but the
VTI shows (y-1) has AnalyticFlag=0 for y=2 nodes.
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
    dims = reader.GetOutput().GetDimensions()
    nx_c, ny_c, nz_c = dims[0] - 1, dims[1] - 1, dims[2] - 1
    cd = reader.GetOutput().GetCellData()

    def get(name):
        a = cd.GetArray(name)
        return vtk_to_numpy(a).reshape((nz_c, ny_c, nx_c)) if a is not None else None

    ib = get("IsItBoundary")
    af = get("AnalyticFlag")
    lra = get("LocalRadAngle")
    found = get("DynamicCLWallContextFound")
    wdx = get("DynamicCLWallDx"); wdy = get("DynamicCLWallDy"); wdz = get("DynamicCLWallDz")

    offsets = [(1,0,0,'+x'),(-1,0,0,'-x'),(0,1,0,'+y'),(0,-1,0,'-y'),(0,0,1,'+z'),(0,0,-1,'-z')]

    # Pick y=2 context_found nodes
    cf2 = (found[:, 2, :] > 0.5)
    zz, xx = np.where(cf2)
    print(f"y=2 context_found nodes: {cf2.sum()}")

    # For each, count how many of the 6 neighbours satisfy the FULL test
    pass_dirs = {o[3]: 0 for o in offsets}
    pass_isb_only = {o[3]: 0 for o in offsets}
    for s in range(len(zz)):
        iz, ix = zz[s], xx[s]
        for dx, dy, dz, name in offsets:
            nx, ny, nz = ix+dx, 1+dy, iz+dz   # node at y=2, neighbour y = 1+dy
            if not (0 <= nx < nx_c and 0 <= ny < ny_c and 0 <= nz < nz_c):
                continue
            isb = ib[nz, ny, nx]
            afv = af[nz, ny, nx]
            lrav = lra[nz, ny, nx]
            if isb > 0.5:
                pass_isb_only[name] += 1
                if afv > 0.5 and (lrav > 1e-6 and lrav < 3.14159265 - 1e-6):
                    pass_dirs[name] += 1

    print("\n=== for y=2 context_found nodes, neighbour pass counts ===")
    for name in pass_dirs:
        print(f"  {name}: IsB>0 = {pass_isb_only[name]}, "
              f"FULL(IsB>0 & AF>0 & valid LRA) = {pass_dirs[name]}")

    # Now: do the same but report, for a handful of nodes, all 6 nb flags raw
    print("\n=== raw 6-neighbour flags for 5 sample y=2 context_found nodes ===")
    sample = np.random.choice(len(zz), min(5, len(zz)), replace=False)
    for s in sample:
        iz, ix = zz[s], xx[s]
        print(f"  cell (ix={ix},iy=2,iz={iz}) recorded wdx={wdx[iz,2,ix]:.0f} "
              f"wdy={wdy[iz,2,ix]:.0f} wdz={wdz[iz,2,ix]:.0f}:")
        for dx, dy, dz, name in offsets:
            nx, ny, nz = ix+dx, 1+dy, iz+dz
            if 0 <= nx < nx_c and 0 <= ny < ny_c and 0 <= nz < nz_c:
                print(f"    {name}: IsB={ib[nz,ny,nx]:.0f} AF={af[nz,ny,nx]:.0f} "
                      f"LRA={lra[nz,ny,nx]:.4f}")

    # Cross-check: is the DynamicCLWallDy field maybe recording the OFFSET of the
    # NODE's own y-1, i.e. is it a constant -1 regardless of which dir matched?
    # If ALL context_found nodes anywhere have wdy=-1, wdx=0, wdz=0, then the
    # recording is suspicious (real walls are only at y=0, so +y/-x/+x/+z/-z
    # neighbours can never be walls -> only -y should ever match -> so wdy=-1
    # being universal is actually CONSISTENT, not a bug).
    print("\n=== sanity: WallDx/Dy/Dz over ALL context_found nodes ===")
    cf = found > 0.5
    print(f"  WallDx unique: {np.unique(wdx[cf])}")
    print(f"  WallDy unique: {np.unique(wdy[cf])}")
    print(f"  WallDz unique: {np.unique(wdz[cf])}")


if __name__ == "__main__":
    main()
