# Calibrated contact-angle measurer. Builds bbox-h/a calibration curve vs synthetic
# tanh caps (known theta), inverts real readings to true theta.
import sys, numpy as np, glob, vtk
from vtk.util.numpy_support import vtk_to_numpy
N=96; W=3.0; A_LATT=24.0; XC=48.0
IX=np.arange(N)+0.5; IY=np.arange(N)+0.5; FL=0.0
Xg,Yg=np.meshgrid(IX,IY)
def bbox_theta(pf, ix, iy, floor):
    mask=pf>0.5; ys,xs=np.where(mask)
    if len(xs)==0: return float("nan"),0
    yp=iy[ys]-floor; xp=ix[xs]
    h=yp.max()-yp.min(); a=(xp.max()-xp.min())/2.0
    return (2*np.degrees(np.arctan(h/a)) if a>0 else float("nan")), len(xs)
def build_calibration():
    ths=np.arange(20,161,5); cal=[]
    for th in ths:
        Rs=A_LATT/np.sin(np.radians(th)); yc=-Rs*np.cos(np.radians(th))
        d=np.sqrt((Xg-XC)**2+(Yg-yc)**2)-Rs
        q=0.5*(1.0-np.tanh(2.0*d/W)); q[Yg<FL]=0.0
        b,_=bbox_theta(q, IX, IY, FL); cal.append((th,b))
    cal=np.array(cal)  # col0=true, col1=reading
    return cal
CAL=None
def invert(reading):
    # mapping reading->true, monotonic; use the true->reading table reversed
    if reading!=reading: return float("nan")
    t=CAL[:,0]; b=CAL[:,1]
    return float(np.interp(reading, b, t))
def measure_pvti(p):
    r=vtk.vtkXMLPImageDataReader(); r.SetFileName(p); r.Update(); o=r.GetOutput()
    nx,ny,nz=o.GetDimensions()[0]-1,o.GetDimensions()[1]-1,o.GetDimensions()[2]-1
    orig=o.GetOrigin(); sp=o.GetSpacing(); cd=o.GetCellData()
    def get(n):
        a=cd.GetArray(n); return vtk_to_numpy(a).reshape((nz,ny,nx)) if a is not None else None
    pf3=get("PhaseField")
    if pf3 is None: pf3=get("PhaseF")
    iy=np.arange(ny)*sp[1]+orig[1]+0.5*sp[1]; ix=np.arange(nx)*sp[0]+orig[0]+0.5*sp[0]
    bs=[]; 
    for kz in range(max(0,nz//2-1),min(nz,nz//2+2)):
        b,_=bbox_theta(pf3[kz], ix, iy, orig[1]); bs.append(b)
    return float(np.nanmean(bs))
def main():
    global CAL; CAL=build_calibration()
    print("calibration (true -> bbox_reading): 30->%.1f 60->%.1f 90->%.1f 120->%.1f 150->%.1f"%(
        invert(25.1)+0, CAL[CAL[:,0]==60,1][0], CAL[CAL[:,0]==90,1][0], CAL[CAL[:,0]==120,1][0], CAL[CAL[:,0]==150,1][0]))
    print("(synth true=30 reads %.1f => invert-back %.1f)"%(CAL[CAL[:,0]==30,1][0], invert(CAL[CAL[:,0]==30,1][0])))
    mode=sys.argv[1]
    if mode=="eq":
        cases=[("eq30",30,"/mnt/usb1t/RUNS/runs/stage15C4_Msweep_20260619/M0p3/diag_wall_t30"),
               ("eq90",90,"/mnt/usb1t/RUNS/runs/stage15FSm1_revalidate_20260619/diag_wall_t90"),
               ("eq150",150,"/mnt/usb1t/RUNS/runs/stage15FSm1_baseline_20260619/diag_wall_t150")]
        print("%-6s %6s %10s %10s %8s"%("case","target","bbox_read","TRUE_inv","err"))
        for lab,t,d in cases:
            p=glob.glob(d+"/output/case_VTK_P00_00004000.pvti")
            if not p: print("%-6s no file"%lab); continue
            b=measure_pvti(p[0]); ti=invert(b)
            print("%-6s %6d %10.1f %10.1f %+8.1f"%(lab,t,b,ti,ti-t))
    elif mode=="traj":
        lab=sys.argv[2]; target=int(sys.argv[3]); d=sys.argv[4]
        fr=sorted(glob.glob(d+"/output/case_VTK_P00_*.pvti"),key=lambda p:int(p.split("_")[-1].split(".")[0]))
        print("== %s target=%d calibrated TRUE angle trajectory =="%(lab,target))
        print("%6s %10s %10s"%("step","bbox_read","TRUE_inv"))
        for p in fr:
            st=int(p.split("_")[-1].split(".")[0])
            b=measure_pvti(p); ti=invert(b)
            print("%6d %10.1f %10.1f"%(st,b,ti))
main()
