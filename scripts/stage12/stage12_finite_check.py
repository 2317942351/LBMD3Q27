#!/usr/bin/env python3
import vtk, numpy as np, sys
from vtk.util.numpy_support import vtk_to_numpy
r=vtk.vtkXMLImageDataReader(); r.SetFileName(sys.argv[1]); r.Update()
pf=vtk_to_numpy(r.GetOutput().GetCellData().GetArray('PhaseField'))
print('total cells:', len(pf))
print('n_nan:', int(np.isnan(pf).sum()))
print('n_inf:', int(np.isinf(pf).sum()))
print('n_finite:', int(np.isfinite(pf).sum()))
fin=pf[np.isfinite(pf)]
print('finite range:', fin.min(), fin.max())
print('n>0.5:', int((pf>0.5).sum()))
print('n<-100 (sentinel):', int((pf<-100).sum()))
