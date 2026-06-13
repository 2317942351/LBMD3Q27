#!/usr/bin/env python3
"""stage9_inspect_smoke.py - inspect the smoke-test VTK output for finiteness
and verify the AnalyticFlag field is being set on the flat wall."""
import sys
import vtk

def load_vti(path):
    r = vtk.vtkXMLImageDataReader()
    r.SetFileName(path)
    r.Update()
    return r.GetOutput()

def stats(ds, name):
    arr = ds.GetCellData().GetArray(name)
    if arr is None:
        return f"{name}: NOT PRESENT"
    import numpy as np
    n = arr.GetNumberOfTuples()
    vals = np.array([arr.GetValue(i) for i in range(n)])
    finite = np.isfinite(vals)
    nfin = int(finite.sum())
    nan_count = n - nfin
    if nfin > 0:
        vmin = float(vals[finite].min()); vmax = float(vals[finite].max())
        return f"{name}: n={n}, finite={nfin}, nan={nan_count}, range=[{vmin:.4g},{vmax:.4g}]"
    return f"{name}: n={n}, ALL NaN/Inf"

f0 = sys.argv[1]
f100 = sys.argv[2]
print(f"=== step 0: {f0} ===")
ds0 = load_vti(f0)
for name in ["PhaseField","Rho","P","BOUNDARY","WallGhost","WallH","AnalyticFlag","AnalyticWallNormal"]:
    print(" ", stats(ds0, name))

print(f"\n=== step 100: {f100} ===")
ds100 = load_vti(f100)
for name in ["PhaseField","Rho","P","BOUNDARY","WallGhost","WallH","AnalyticFlag","AnalyticWallNormal"]:
    print(" ", stats(ds100, name))

# Check if AnalyticFlag is set anywhere
arr = ds0.GetCellData().GetArray("AnalyticFlag")
if arr is not None:
    import numpy as np
    n = arr.GetNumberOfTuples()
    vals = np.array([arr.GetValue(i) for i in range(n)])
    print(f"\nAnalyticFlag step0: count>0.5 = {int((vals>0.5).sum())} of {n}")
