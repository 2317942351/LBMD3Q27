#!/usr/bin/env python3
"""stage12_sphere_diag.py - diagnose the sphere theta=90 case."""
import sys, numpy as np, vtk
from vtk.util.numpy_support import vtk_to_numpy
r=vtk.vtkXMLImageDataReader(); r.SetFileName(sys.argv[1]); r.Update()
out=r.GetOutput()
pf=vtk_to_numpy(out.GetCellData().GetArray("PhaseField")).copy()
bd=vtk_to_numpy(out.GetCellData().GetArray("BOUNDARY")).copy()
af=vtk_to_numpy(out.GetCellData().GetArray("AnalyticFlag")).copy()
dims=out.GetDimensions()
nx,ny,nz=dims[0]-1,dims[1]-1,dims[2]-1
print(f"grid {nx}x{ny}x{nz}, total {len(pf)}")
print(f"PhaseField range [{pf.min():.4g},{pf.max():.4g}], n>0.5={int((pf>0.5).sum())}")
print(f"BOUNDARY: n>0.5 (solid)={int((bd>0.5).sum())}, n<0.5 (fluid)={int((bd<0.5).sum())}")
print(f"AnalyticFlag: n>0.5={int((af>0.5).sum())}")
# slice at x=40, show the (y,z) phase field
pf3=pf.reshape((nz,ny,nx)); bd3=bd.reshape((nz,ny,nx))
ix=40
sl=pf3[:,:,ix]
print(f"\nslice ix={ix}: phi range [{np.nanmin(sl):.4g},{np.nanmax(sl):.4g}]")
# print a coarse map: z (rows) vs y (cols), 'L'=liquid(>0.5), '.'=gas, '#'=solid, '?'=mid
print("z\\y :", end="")
for iy in range(0,ny,4): print(f"{iy:3d}",end="")
print()
for iz in range(0,nz,4):
    print(f"{iz:3d} :", end="")
    for iy in range(0,ny,4):
        p=sl[iz,iy]; b=bd3[iz,iy,ix]
        if b>0.5: c='#'
        elif p>0.7: c='L'
        elif p<0.3: c='.'
        else: c='?'
        print(f"  {c}",end="")
    print()
