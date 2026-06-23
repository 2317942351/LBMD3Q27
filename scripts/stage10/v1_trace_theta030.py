#!/usr/bin/env python3
"""v1_trace.py - trace Newton iterations for theta=30 to see why it diverges."""
import numpy as np, math
SIGMA=5e-5; W=6.0; PHI_L=0.0; PHI_H=1.0; PHI_AVG=0.5
KAPPA=1.5*SIGMA*W; MU_SCALE=12.0*SIGMA/W
def mu_bulk(p): return 4.0*MU_SCALE*(p-PHI_L)*(p-PHI_H)*(p-PHI_AVG)

L=80.0; N=401
x=np.linspace(0,L,N); dx=x[1]-x[0]
lam=W*math.sqrt(0.125)
phi_init=PHI_AVG+0.5*(PHI_H-PHI_L)*np.tanh((x-4.0)/lam)
phi_init=np.clip(phi_init,0.001,0.999); phi_init[-1]=PHI_H
y=np.concatenate([phi_init,[phi_init[0]],[0.0]])

theta=math.radians(30.0)
h_g=1.0
dfs=-h_g*math.cos(theta)*MU_SCALE
print(f"theta=30: cos={math.cos(theta):.4f}, dfs={dfs:.3e}, h_g*MU_SCALE={h_g*MU_SCALE:.3e}")

def lap(i,y):
    if i==0: return (y[N]-2*y[0]+y[1])
    if i==N-1: return (y[N-2]-2*y[N-1]+PHI_H)
    return (y[i-1]-2*y[i]+y[i+1])
def resid(y):
    r=np.zeros(N+2)
    r[N-1]=y[N-1]-PHI_H
    r[N]=KAPPA*(y[0]-y[N])/(2*dx)+dfs
    mu_eq=y[N+1]
    for i in range(N-1):
        r[i]=mu_bulk(y[i])-KAPPA*lap(i,y)-mu_eq
    r[N+1]=mu_eq
    return r

for it in range(15):
    r=resid(y); rmax=np.max(np.abs(r))
    print(f"iter {it}: rmax={rmax:.3e}, phi[0]={y[0]:.4f}, phi_g={y[N]:.4f}, mu_eq={y[N+1]:.3e}, NBC_resid={r[N]:.3e}")
    if rmax<1e-12:
        print("CONVERGED"); break
    eps=1e-7; J=np.zeros((N+2,N+2))
    for j in range(N+2):
        yp=y.copy(); yp[j]+=eps; J[:,j]=(resid(yp)-r)/eps
    try: dy=np.linalg.solve(J,-r)
    except np.linalg.LinAlgError: print("singular"); break
    alpha=1.0
    for _ in range(30):
        yn=y+alpha*dy
        if np.max(np.abs(resid(yn)))<rmax: y=yn; break
        alpha*=0.5
    else: y=y+dy
    y[:N]=np.clip(y[:N],-0.5,1.5); y[N]=max(-0.5,min(1.5,y[N]))
