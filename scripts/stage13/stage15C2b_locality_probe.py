#!/usr/bin/env python3
"""C2b locality probe: classify the F_cl>0 nodes precisely.
Goal: separate (a) cosmetic wall-node diagnostic writes (no dynamics effect)
from (b) fluid nodes that would actually receive an unwanted F_total += fcl.
"""
import numpy as np, vtk, collections
from vtk.util.numpy_support import vtk_to_numpy as v2n

p = "/mnt/usb1t/RUNS/runs/stage15C2b_t90_coeff0p02/diag_wall_t90/output/case_VTK_P00_00004000.vti"
r = vtk.vtkXMLImageDataReader(); r.SetFileName(p); r.Update()
d = r.GetOutput().GetCellData(); A = {}
for i in range(d.GetNumberOfArrays()):
    a = d.GetArray(i); A[a.GetName()] = v2n(a)
dims = tuple(v-1 for v in r.GetOutput().GetDimensions()); nx, ny, nz = dims
ph  = A["PhaseField"].reshape((nx,ny,nz))
isb = A["IsItBoundary"].reshape((nx,ny,nz))
act = A["DynamicCLActive"].reshape((nx,ny,nz))
fmag= A["DynamicCLForceCandidateMag"].reshape((nx,ny,nz))
blk = A["DynamicCLBlockedReason"].reshape((nx,ny,nz))
wcf = A["DynamicCLWallContextFound"].reshape((nx,ny,nz))

nz_mask = fmag > 0
m_active = act > 0.5
m_notwall = isb < 0.5
m_clband = (ph > 0.05) & (ph < 0.95)

print("total F_cl>0 nodes:", int(nz_mask.sum()))
print("  inside active & not-wall & clband:", int((nz_mask & m_active & m_notwall & m_clband).sum()))
print()

# the 166 nodes
m166 = nz_mask & ~m_active
print("=== nodes with F_cl>0 AND Active<0.5  (count=%d) ===" % int(m166.sum()))
print("  are wall (IsItBoundary>=0.5):", int((m166 & (isb>=0.5)).sum()))
print("  are fluid (IsItBoundary<0.5):", int((m166 & (isb<0.5)).sum()))
print("  WallContextFound>0.5        :", int((m166 & (wcf>0.5)).sum()))
print("  blocked-reason hist         :", dict(collections.Counter(np.round(blk[m166][np.isfinite(blk[m166])]).astype(int).tolist())))
print("  max |F_cl| on these         : %.3e" % float(np.abs(fmag[m166]).max()))
print()

# THE decisive question: do any FLUID nodes OUTSIDE the active band get a
# nonzero fcl that the hook would add to F_total?
fluid_outside_fcl = nz_mask & m_notwall & ~m_active
print("=== FLUID nodes with F_cl>0 but Active<0.5: %d ===" % int(fluid_outside_fcl.sum()))
print("  (these are the ONLY nodes where the hook could add an unwanted F_total contribution)")
if fluid_outside_fcl.sum() > 0:
    print("  -> of these, in clband:", int((fluid_outside_fcl & m_clband).sum()))
    print("  -> of these, out-of-clband:", int((fluid_outside_fcl & ~m_clband).sum()))
    print("  -> max |F_cl|:", float(np.abs(fmag[fluid_outside_fcl]).max()))
print()
print("=== all wall nodes (IsItBoundary>=0.5): collision is SKIPPED (IamWall), so even")
print("    if calcDynamicCLShadow wrote a nonzero fcl there, the F_total += fcl hook")
print("    never executes for them. Wall-node F_cl>0 is cosmetic diagnostic only. ===")
