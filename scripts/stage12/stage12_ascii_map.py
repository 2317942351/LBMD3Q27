#!/usr/bin/env python3
"""stage12_ascii_map.py - high-resolution ASCII map of the droplet + cylinder
in the (y,z) slice, so the morphology can be described without rendering."""
import sys, numpy as np, vtk
from vtk.util.numpy_support import vtk_to_numpy
r=vtk.vtkXMLImageDataReader(); r.SetFileName(sys.argv[1]); r.Update()
out=r.GetOutput()
pf=vtk_to_numpy(out.GetCellData().GetArray("PhaseField")).copy()
bd_arr = out.GetCellData().GetArray("IsItBoundary")
if bd_arr is None:
    bd_arr = out.GetCellData().GetArray("BOUNDARY")
bd=vtk_to_numpy(bd_arr).copy()
dims=out.GetDimensions()
nx,ny,nz=dims[0]-1,dims[1]-1,dims[2]-1
pf3=pf.reshape((nz,ny,nx)); bd3=bd.reshape((nz,ny,nx))
ix=int(sys.argv[2])
sl=pf3[:,:,ix]; bds=bd3[:,:,ix]
# focus on the region of interest: z in [44,90], y in [28,68]
z0,z1=44,90; y0,y1=28,68
print(f"slice ix={ix}, showing z in [{z0},{z1}], y in [{y0},{y1}]")
print("legend: # = solid(cylinder), L = liquid(pf>0.8), l = mid-liquid(0.5..0.8),")
print("        ~ = interface(0.2..0.5), . = gas(<0.2), N = NaN")
print()
# header every 2 y
print("z  :", end="")
for iy in range(y0,y1,2): print(f"{iy%100:2d}",end=" ")
print("  y->")
for iz in range(z1,z0-1,-1):   # top to bottom
    print(f"{iz:3d}:", end="")
    for iy in range(y0,y1,2):
        if iz>=nz or iy>=ny: print("  ",end=" "); continue
        p=sl[iz,iy]; b=bds[iz,iy]
        if b>0.5: c='#'
        elif np.isnan(p): c='N'
        elif p>0.8: c='L'
        elif p>0.5: c='l'
        elif p>0.2: c='~'
        else: c='.'
        print(f"  {c}",end="")
    print()
print()
# column of y indices
print("y  :", end="")
for iy in range(y0,y1,2): print(f"{iy%100:2d}",end=" ")
print()
