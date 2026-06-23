import sys, numpy as np, vtk
from vtk.util.numpy_support import vtk_to_numpy
def load(p):
    r=vtk.vtkXMLPImageDataReader(); r.SetFileName(p); r.Update(); o=r.GetOutput()
    nx,ny,nz=o.GetDimensions()[0]-1,o.GetDimensions()[1]-1,o.GetDimensions()[2]-1
    orig=o.GetOrigin(); sp=o.GetSpacing(); cd=o.GetCellData()
    def get(n):
        a=cd.GetArray(n); return vtk_to_numpy(a).reshape((nz,ny,nx)) if a is not None else None
    return get,(nx,ny,nz),orig,sp
def main():
    p=sys.argv[1]; label=sys.argv[2]
    get,shape,orig,sp=load(p); nx,ny,nz=shape
    pf3=get("PhaseField")
    if pf3 is None: pf3=get("PhaseF")
    kz=nz//2
    pf=pf3[kz]  # (ny,nx) [y,x]
    # droplet bbox where q>0.5
    mask=pf>0.5
    ys,xs=np.where(mask)
    if len(xs)==0:
        print("%s: no q>0.5 cells on center slice"%label); return
    y0,y1=ys.min(),ys.max(); x0,x1=xs.min(),xs.max()
    h_cells=y1-y0+1; w_cells=x1-x0+1
    # expected cap height for a spherical cap of footprint radius a and angle theta:
    a_latt=(x1-x0+1)/2.0
    print("%s: droplet bbox y[%d,%d] x[%d,%d]  height=%d cells  width=%d cells  (a~%.1f latt)"%(label,y0,y1,x0,x1,h_cells,w_cells,a_latt))
    print("  expected height for theta: 30->%.1f, 60->%.1f, 90->%.1f, 120->%.1f, 150->%.1f cells (R=24)"%(
        24*(1-np.cos(np.radians(30))),24*(1-np.cos(np.radians(60))),24*(1-np.cos(np.radians(90))),
        24*(1-np.cos(np.radians(120))),24*(1-np.cos(np.radians(150)))))
    # ASCII: zoom to bbox +2, q thresholded. rows = y (top down), cols=x
    yy0=max(0,y0-1); yy1=min(ny-1,y1+1); xx0=max(0,x0-1); xx1=min(nx-1,x1+1)
    sub=pf[yy0:yy1+1, xx0:xx1+1]
    ramp=" .:-=+*#%@"
    print("  ASCII q-field (top=y%d, rows=y down; cols=x %d..%d):"%(yy1,xx0,xx1))
    for j in range(sub.shape[0]-1,-1,-1):
        row=sub[j]
        s="".join(ramp[min(len(ramp)-1,int(v*len(ramp)))] if v>0.02 else " " for v in row)
        print("    "+s)
main()
