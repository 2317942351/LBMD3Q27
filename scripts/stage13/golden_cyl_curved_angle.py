# Self-calibrating curved-wall (cylinder) contact-angle measurer.
# 2D z-center slice. Cylinder circle (CX,CY,RS). Droplet cap on top.
# cos(theta)= n_s . n_lg ; n_s=solid->fluid=outward radial; n_lg=liq->gas=-grad(q)/|grad|.
# Synthetic: for target theta & wrap beta, solve u=Cdy-CY from cos(theta)=[RS-u cos(b)]/Rd(u).
import sys, numpy as np
CX,CY,RS=48.0,48.0,20.0
N=96
def rd_of_u(u,be): return np.sqrt(RS**2 + u**2 - 2*u*RS*np.cos(be))
def costh_of_u(u,be): return (RS - u*np.cos(be))/rd_of_u(u,be)
def synth_field(theta_deg, beta_deg, W=3.0):
    th=np.radians(theta_deg); be=np.radians(beta_deg)
    ct=np.cos(th)
    # scan u in (0.1, 80) for costh_of_u(u)==ct ; costh decreases monotonically with u
    lo,hi=0.1,80.0
    for _ in range(60):
        mid=0.5*(lo+hi)
        if costh_of_u(mid,be) > ct: lo=mid
        else: hi=mid
    u=0.5*(lo+hi); Cdy=CY+u; Rd=rd_of_u(u,be)
    ix=np.arange(N)+0.5; iy=np.arange(N)+0.5; X,Y=np.meshgrid(ix,iy)
    dd=np.sqrt((X-CX)**2+(Y-Cdy)**2)-Rd
    q=0.5*(1.0-np.tanh(2.0*dd/W))
    dc=np.sqrt((X-CX)**2+(Y-CY)**2); q[dc<RS]=0.0
    return q,(Cdy,Rd)
def measure(q, x0=CX, y0=CY, rs=RS):
    ny,nx=q.shape
    ix=np.arange(nx)+0.5; iy=np.arange(ny)+0.5; X,Y=np.meshgrid(ix,iy)
    gy,gx=np.gradient(q,1.0,1.0)
    dc=np.sqrt((X-x0)**2+(Y-y0)**2)
    band=(dc>rs-2.0)&(dc<rs+3.0)&(q>0.2)&(q<0.8)&(Y>y0+1)
    if not band.any(): return float("nan"),0
    nsx=(X[band]-x0)/dc[band]; nsy=(Y[band]-y0)/dc[band]
    gmag=np.sqrt(gx[band]**2+gy[band]**2)+1e-12
    nlx=-gx[band]/gmag; nly=-gy[band]/gmag
    costh=np.clip(nsx*nlx+nsy*nly,-1,1)
    return float(np.median(np.degrees(np.arccos(costh)))), int(band.sum())
def validate():
    print("=== SELF-VALIDATION synthetic cylinder caps (Rs=20,W=3) ===")
    print("%6s %6s %10s %8s %10s"%("true","beta","achieved","measured","n"))
    for th in [60,90,120]:
        for be in [20,30,40]:
            q,(Cdy,Rd)=synth_field(th,be)
            ach=np.degrees(np.arccos(np.clip(costh_of_u(Cdy-CY,np.radians(be)),-1,1)))
            m,n=measure(q)
            print("%6d %6d %10.1f %10.1f %8d"%(th,be,ach,m,n))
if __name__=="__main__": validate()
# --- contour-tangent measure (geometric, less biased) ---
def measure_contour(q, x0=CX, y0=CY, rs=RS):
    ny,nx=q.shape
    ix=np.arange(nx)+0.5; iy=np.arange(ny)+0.5
    # extract q=0.5 contour points (right half, above cylinder), sub-cell
    pts=[]
    for j in range(ny):
        row=q[j]
        for i in np.where(np.diff(np.sign(row-0.5))!=0)[0]:
            if i+1>=nx: continue
            x0c,x1c=ix[i],ix[i+1]; v0,v1=row[i],row[i+1]
            if v1==v0: continue
            x=x0c+(0.5-v0)/(v1-v0)*(x1c-x0c)
            if x>x0: pts.append((x,iy[j]))
    pts=np.array(pts)
    if len(pts)<5: return float("nan")
    dc=np.sqrt((pts[:,0]-x0)**2+(pts[:,1]-y0)**2)
    # contact = contour pts with dc just above rs (on the cylinder), upper half
    cand=pts[(dc>rs-0.5)&(dc<rs+3.0)&(pts[:,1]>y0)]
    if len(cand)<2: return float("nan")
    # right contact: max x among cand
    rc=cand[np.argmax(cand[:,0])]
    # local contour tangent: neighbour pts within 6 cells of rc along contour (sort by angle around droplet)
    # take contour pts within radius 6 of rc
    d=np.sqrt((pts[:,0]-rc[0])**2+(pts[:,1]-rc[1])**2)
    loc=pts[d<6.0]
    if len(loc)<3: return float("nan")
    # fit line y=a x+b -> tangent direction (1,a); angle of tangent above horizontal
    A=np.vstack([loc[:,0],np.ones_like(loc[:,0])]).T
    (a,_),*_=np.linalg.lstsq(A,loc[:,1],rcond=None)  # dy/dx
    td_x,td_y=1.0,a  # droplet tangent vector
    # cylinder tangent at rc: perpendicular to radial (rc-center)
    rx=rc[0]-x0; ry=rc[1]-y0
    tx,ty=-ry,rx  # cylinder tangent (one direction)
    # contact angle through liquid between solid tangent and interface tangent
    cosang=abs((td_x*tx+td_y*ty)/(np.sqrt(td_x*td_x+td_y*td_y)*np.sqrt(tx*tx+ty*ty)))
    # need correct quadrant: use normals. n_s=(rx,ry)/rs outward; n_lg=liq->gas.
    # interface tangent td=(1,a); normal to it (rotate 90): one of (-a,1) or (a,-1). pick liq->gas (pointing away from droplet interior ~ upward-outward)
    return None
