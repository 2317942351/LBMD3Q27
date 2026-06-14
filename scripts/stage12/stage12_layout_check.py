#!/usr/bin/env python3
"""Check the reshape convention and BOUNDARY layout."""
import sys, numpy as np, vtk
from vtk.util.numpy_support import vtk_to_numpy
r=vtk.vtkXMLImageDataReader(); r.SetFileName(sys.argv[1]); r.Update()
out=r.GetOutput()
bd_arr = out.GetCellData().GetArray("IsItBoundary")
if bd_arr is None:
    bd_arr = out.GetCellData().GetArray("BOUNDARY")
bd=vtk_to_numpy(bd_arr).copy()
pf=vtk_to_numpy(out.GetCellData().GetArray("PhaseField")).copy()
dims=out.GetDimensions()
nx,ny,nz=dims[0]-1,dims[1]-1,dims[2]-1
print(f"dims(nodes)={dims}, cells={nx}x{ny}x{nz}, total={len(bd)}")
# TCLB layout: linear index = ix + iy*nx + iz*nx*ny  (x fastest)
bd3_xfirst = bd.reshape((nz, ny, nx))  # iz, iy, ix
# count solid per x-slice to find where the cylinder is
for ix in range(0, nx, 16):
    sl = bd3_xfirst[:, :, ix]
    print(f"x={ix}: solid fraction = {int((sl>0.5).sum())}/{sl.size} = {(sl>0.5).sum()/sl.size:.3f}")
# the cylinder spans x=0..96 (full domain). Check a slice at x=48 (center)
ix=48
sl=bd3_xfirst[:,:,ix]
print(f"\nslice x={ix}: shape={sl.shape}, n_solid={int((sl>0.5).sum())}")
# where is the solid? z ranges
iz_solid = np.where((sl>0.5).any(axis=1))[0]  # rows (z) with any solid
iy_solid = np.where((sl>0.5).any(axis=0))[0]  # cols (y) with any solid
print(f"solid z-rows: {iz_solid.min()}..{iz_solid.max()}")
print(f"solid y-cols: {iy_solid.min()}..{iy_solid.max()}")
# This tells us whether the cylinder cross-section is a disk (expected) or
# something weird. For a disk at (y=48,z=48) R=20, solid should be a circle
# of radius 20, i.e. z in [28,68], y in [28,68].
