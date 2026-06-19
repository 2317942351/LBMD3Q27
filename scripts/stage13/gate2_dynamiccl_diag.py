#!/usr/bin/env python3
"""Gate 2 diagnostic reader for DynamicCL shadow fields.

Reads the final-step VTI of a flat-wall DynamicCL shadow run and reports the
key gate-2 statistics:
  - DynamicCLCosEq value distribution (expect ~+0.866 for t30)
  - where DynamicCLWallContextFound=1 (expect only near FlatLowerY, y=1)
  - DynamicCLActive / BlockedReason distribution (expect OuterDomain blocked)
  - cross-checks LocalRadAngle / AnalyticFlag on the wall neighbours

Usage:
  python3 gate2_dynamiccl_diag.py <pvti_or_vti_file>
"""
import sys
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy


def load_cell_array(reader, name):
    data = reader.GetOutput().GetCellData().GetArray(name)
    if data is None:
        return None
    return vtk_to_numpy(data)


def main():
    path = sys.argv[1]
    if path.endswith(".pvti"):
        reader = vtk.vtkXMLPImageDataReader()
    else:
        reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(path)
    reader.Update()
    cd = reader.GetOutput().GetCellData()

    avail = [cd.GetArrayName(i) for i in range(cd.GetNumberOfArrays())]
    print(f"=== file: {path}")
    print(f"=== cell arrays present: {len(avail)}")
    dims = reader.GetOutput().GetDimensions()
    print(f"=== dims (nodes): {dims}  -> cells: {dims[0]-1}x{dims[1]-1}x{dims[2]-1}")

    def get(name):
        a = cd.GetArray(name)
        return vtk_to_numpy(a) if a is not None else None

    for fld in [
        "DynamicCLCosEq", "DynamicCLThetaEq", "DynamicCLCosApp",
        "DynamicCLCosResidual", "DynamicCLActive", "DynamicCLIndicator",
        "DynamicCLWallContextFound", "DynamicCLBlockedReason",
        "DynamicCLRejectedReason", "DynamicCLWallDy",
        "LocalRadAngle", "AnalyticFlag", "PhaseField", "IsItBoundary",
    ]:
        a = get(fld)
        if a is None:
            print(f"\n[{fld}] NOT in output")
            continue
        nz = a[a != 0] if np.issubdtype(a.dtype, np.number) else a
        uniq = np.unique(np.round(a, 4))
        print(f"\n[{fld}] shape={a.shape} dtype={a.dtype}")
        print(f"   min={np.nanmin(a):.6f} max={np.nanmax(a):.6f} "
              f"mean={np.nanmean(a):.6f} nonzero={np.count_nonzero(a)}")
        print(f"   unique(rounded4, first 12): {uniq[:12]}"
              f"{' ...' if len(uniq) > 12 else ''}  (total {len(uniq)})")

    # --- gate 2 verdict: DynamicCLCosEq on ACTIVE nodes ---
    cos_eq = get("DynamicCLCosEq")
    active = get("DynamicCLActive")
    found = get("DynamicCLWallContextFound")
    if cos_eq is not None and active is not None:
        act = active > 0.5
        print("\n" + "=" * 60)
        print("GATE 2 VERDICT")
        print("=" * 60)
        print(f"nodes with DynamicCLActive>0.5: {act.sum()}")
        if act.sum() > 0:
            ce = cos_eq[act]
            print(f"  their DynamicCLCosEq: min={ce.min():.4f} max={ce.max():.4f} "
                  f"mean={ce.mean():.4f} unique={np.unique(np.round(ce,3))}")
            print(f"  EXPECTED for t30: ~ +0.866 (cos 30deg)")
            print(f"  cos30 = {np.cos(np.radians(30)):.4f}")
        else:
            print("  WARNING: zero active nodes -- check BlockedReason distribution")

    # --- gate 3: spatial locality table with CORRECT VTK cell ordering ---
    # VTK ImageData cell arrays are x-fastest, then y, then z (C order).
    # Reshape to (nz, ny, nx) so cell (ix,iy,iz) = arr3d[iz, iy, ix].
    nx_c, ny_c, nz_c = dims[0] - 1, dims[1] - 1, dims[2] - 1
    q = get("PhaseField")

    def locality_table(mask, label):
        if mask.sum() == 0:
            print(f"\n[{label}] no nodes in mask")
            return
        m3 = mask.reshape((nz_c, ny_c, nx_c))
        zz, yy, xx = np.where(m3)  # cell indices
        print(f"\n[{label}] count={mask.sum()}")
        print(f"  x (cell): min={xx.min()} max={xx.max()}  (grid cells 0..{nx_c-1})")
        print(f"  y (cell): min={yy.min()} max={yy.max()}  (grid cells 0..{ny_c-1})")
        print(f"  z (cell): min={zz.min()} max={zz.max()}  (grid cells 0..{nz_c-1})")
        uy, cy = np.unique(yy, return_counts=True)
        print(f"  unique y with counts: {dict(zip(uy.tolist(), cy.tolist()))}")
        if q is not None:
            qm = q[mask]
            print(f"  q (PhaseField) over mask: min={qm.min():.4f} max={qm.max():.4f} mean={qm.mean():.4f}")
        # wall-neighbour direction used by this mask (key for diagnosing why
        # y>1 nodes also report context_found)
        for dname in ("DynamicCLWallDx", "DynamicCLWallDy", "DynamicCLWallDz"):
            da = get(dname)
            if da is not None:
                dm = da[mask]
                uv, cv = np.unique(dm, return_counts=True)
                print(f"  {dname} over mask: {dict(zip(np.round(uv,0).tolist(), cv.tolist()))}")

    if found is not None:
        print("\n" + "=" * 60)
        print("GATE 3 LOCALITY (DynamicCLActive>0.5)")
        print("=" * 60)
        if active is not None and active.sum() > 0:
            locality_table(active > 0.5, "DynamicCLActive")
        if found is not None and found.sum() > 0:
            locality_table(found > 0.5, "DynamicCLWallContextFound")

    # BlockedReason distribution over the full grid (gate 2 already showed
    # this; repeat here for the gate-3 table completeness).
    br = get("DynamicCLBlockedReason")
    if br is not None:
        vals, counts = np.unique(br, return_counts=True)
        print(f"\n[DynamicCLBlockedReason] full-grid distribution:")
        labels = {0: "accepted/mode-off", 1: "wall/solid", 2: "no wetting wall",
                  3: "bad wall normal", 5: "q out of band", 6: "grad too small",
                  7: "|R_theta|<tol"}
        for v, c in zip(vals, counts):
            print(f"   {v:.0f} ({labels.get(int(v),'?')}): {c}")

    # --- BlockedReason distribution (expect OuterDomain/bulk blocked) ---
    br = get("DynamicCLBlockedReason")
    # (BlockedReason distribution is printed in the gate-3 locality section above)


if __name__ == "__main__":
    main()
