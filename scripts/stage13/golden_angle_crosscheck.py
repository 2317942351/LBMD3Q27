# Trusted contact-angle measurer with analytic self-validation.
# Methods: (B) bbox sphere-cap theta=2*atan(h/a); (C) q=0.5 contour circle-fit theta=arccos(-yc/R).
# Self-validates on synthetic tanh spherical caps of known theta (30/60/90/120/150).
import sys, numpy as np
def measure_2d(pf, iy, ix, floor, label="", verbose=True):
    # pf: 2D (ny,nx) [y,x]; iy, ix: cell-center coords; floor: y of floor plane
    mask=pf>0.5
    ys,xs=np.where(mask)
    if len(xs)==0: return None
    yphys=iy[ys]-floor; xphys=ix[xs]
    h=yphys.max()-yphys.min(); a=(xphys.max()-xphys.min())/2.0
    th_bbox=2*np.degrees(np.arctan(h/a)) if a>0 else float("nan")
    # contour right+left halves, sub-cell linear interp at q=0.5
    pts=[]
    ny,nx=pf.shape
    for j in range(ny):
        row=pf[j]
        cr=np.where(np.diff(np.sign(row-0.5))!=0)[0]
        for i in cr:
            if i+1>=nx: continue
            x0,x1=ix[i],ix[i+1]; v0,v1=row[i],row[i+1]
            if v1==v0: continue
            x=x0+(0.5-v0)/(v1-v0)*(x1-x0); pts.append((x, iy[j]))
    pts=np.array(pts)
    th_circ=float("nan")
    if len(pts)>=6:
        xs2=pts[:,0]-ix[nx//2]; ys2=pts[:,1]-floor
        A=np.column_stack([2*xs2,2*ys2,np.ones_like(xs2)]); b=xs2**2+ys2**2
        sol,*_=np.linalg.lstsq(A,b,rcond=None); xc,yc,F=sol
        R=np.sqrt(max(xc*xc+yc*yc-F,1e-9))
        th_circ=np.degrees(np.arccos(np.clip(-yc/R,-1,1)))
    if verbose:
        print("  %-10s bbox_h/a=%.1f deg   contour_circle=%.1f deg   (h=%.2f a=%.2f npts=%d)"%(label,th_bbox,th_circ,h,a,len(pts)))
    return th_bbox,th_circ
def synth_and_validate():
    print("=== SELF-VALIDATION on synthetic tanh spherical caps (W=3, a=24, 96x96) ===")
    N=96; W=3.0; a=24.0; xc=48.0
    ix=np.arange(N)+0.5; iy=np.arange(N)+0.5; floor=0.0
    X,Y=np.meshgrid(ix,iy)  # (N,N) [y,x]
    for th in [30,60,90,120,150]:
        Rs=a/np.sin(np.radians(th)); yc=-Rs*np.cos(np.radians(th))  # center height (floor at 0)
        d=np.sqrt((X-xc)**2+(Y-yc)**2)-Rs   # signed, <0 inside sphere
        q=0.5*(1.0-np.tanh(2.0*d/W))        # q=1 inside droplet
        # zero out below floor (y<floor) -- cap is above floor
        q[Y<floor]=0.0
        measure_2d(q, iy, ix, floor, label="true=%d"%th)
if __name__=="__main__":
    synth_and_validate()
    if len(sys.argv)>2 and sys.argv[1]=="measure":
        import vtk
        from vtk.util.numpy_support import vtk_to_numpy
        p=sys.argv[2]; lab=sys.argv[3] if len(sys.argv)>3 else "?"
        print("=== REAL %s (%s) ==="%(p.split("/")[-1],lab))
        r=vtk.vtkXMLPImageDataReader(); r.SetFileName(p); r.Update(); o=r.GetOutput()
        nx,ny,nz=o.GetDimensions()[0]-1,o.GetDimensions()[1]-1,o.GetDimensions()[2]-1
        orig=o.GetOrigin(); sp=o.GetSpacing(); cd=o.GetCellData()
        def get(n):
            a=cd.GetArray(n); return vtk_to_numpy(a).reshape((nz,ny,nx)) if a is not None else None
        pf3=get("PhaseField")
        if pf3 is None: pf3=get("PhaseF")
        iy=np.arange(ny)*sp[1]+orig[1]+0.5*sp[1]; ix=np.arange(nx)*sp[0]+orig[0]+0.5*sp[0]
        # measure on center z-slice and average over 3 z-slices around center
        for kz in [nz//2-1,nz//2,nz//2+1]:
            measure_2d(pf3[kz], iy, ix, orig[1], label="z=%d"%kz)
