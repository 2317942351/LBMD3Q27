import sys, glob
from pathlib import Path
import numpy as np, vtk
from vtk.util.numpy_support import vtk_to_numpy
def load(p):
    r=vtk.vtkXMLPImageDataReader(); r.SetFileName(p); r.Update(); o=r.GetOutput()
    nx,ny,nz=o.GetDimensions()[0]-1,o.GetDimensions()[1]-1,o.GetDimensions()[2]-1
    orig=o.GetOrigin(); sp=o.GetSpacing(); cd=o.GetCellData()
    def get(n):
        a=cd.GetArray(n); return vtk_to_numpy(a).reshape((nz,ny,nx)) if a is not None else None
    return get,(nx,ny,nz),orig,sp
def main():
    casedir=sys.argv[1]; target=float(sys.argv[2]) if len(sys.argv)>2 else 90.0
    cap=float(sys.argv[3]) if len(sys.argv)>3 else 0.0
    x0,z0=48.0,48.0
    frames=sorted(glob.glob(str(Path(casedir)/"output"/"case_VTK_P00_*.pvti")),key=lambda p:int(p.split("_")[-1].split(".")[0]))
    print("# %s target=%.0f cap=%.2f frames=%d"%(Path(casedir).name,target,cap,len(frames)))
    print("%6s %8s %8s %5s %6s %12s %8s %11s %9s %9s"%("step","th_app","|R|","NaN","n_act","sumPhaseF","foot_r","max|Fcand|","capped%","spur_flu"))
    for p in frames:
        step=int(p.split("_")[-1].split(".")[0])
        get,(nx,ny,nz),orig,sp=load(p)
        act=(get("DynamicCLActive")>0.5); n_act=int(act.sum())
        pf=get("PhaseField")
        if pf is None: pf=get("PhaseF")
        nan=int(np.isnan(pf).sum()) if pf is not None else -1
        sump=float(pf.sum()) if pf is not None else float("nan")
        th=get("DynamicCLThetaApp"); res=get("DynamicCLCosResidual")
        th_m=float(th[act].mean()) if (th is not None and n_act>0) else float("nan")
        r_m=float(np.abs(res[act]).mean()) if (res is not None and n_act>0) else float("nan")
        fm=get("DynamicCLForceCandidateMag")
        maxf=float(np.nanmax(np.abs(fm))) if fm is not None else float("nan")
        isc=get("IsItBoundary")
        spur=-1
        if fm is not None and isc is not None:
            spur=int(((np.abs(fm)>1e-30)&(~act)&(isc<0.5)).sum())
        capfrac=float("nan")
        if fm is not None and cap>0 and n_act>0:
            capfrac=float((np.abs(fm[act])>=0.99*cap).mean()*100.0)
        foot=float("nan")
        if pf is not None:
            ix=np.arange(nx)*sp[0]+orig[0]+0.5*sp[0]; iz=np.arange(nz)*sp[2]+orig[2]+0.5*sp[2]
            band=(pf>0.4)&(pf<0.6)
            if band.any():
                kz,jy,ixs=np.where(band); rx=ix[ixs]-x0; rz=iz[kz]-z0
                foot=float(np.sqrt(rx*rx+rz*rz).mean())
        print("%6d %8.3f %8.4f %5d %6d %12.4e %8.2f %11.3e %9.1f %9d"%(step,th_m,r_m,nan,n_act,sump,foot,maxf,capfrac,spur))
main()
