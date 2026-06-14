#!/usr/bin/env python3
"""v1b_imposed_wall.py - Stage10 V1 Option B: 1D imposed-wall-value consistency.

For a sweep of imposed wall values phi_w, solve the bulk Cahn-Hilliard
equilibrium (mu=0) on [0,L] with phi[0]=phi_w, phi[N-1]=PHI_H. The ghost phi_g
is an unknown determined by node-0's equilibrium equation.

Then measure:
  R_nbc = kappa*(phi_w - phi_g)/(2*dx) + dfs_dphi   [natural BC residual]
  mwt_implied = kappa*(phi_w - phi_g)/(2*dx)         [the h_g*cos(theta)*MU_SCALE that makes NBC=0]
  R_cand = mu_bulk(phi_g) - kappa*lap_wall - mwt_implied   [candidate residual]

Pass: |R_cand| < 1e-8 for all converged phi_w.
"""
import numpy as np, math, json, os

SIGMA=5e-5; W=6.0; PHI_L=0.0; PHI_H=1.0; PHI_AVG=0.5
KAPPA=1.5*SIGMA*W; MU_SCALE=12.0*SIGMA/W

def mu_bulk(p): return 4.0*MU_SCALE*(p-PHI_L)*(p-PHI_H)*(p-PHI_AVG)

L=60.0; N=301
x=np.linspace(0,L,N); dx=x[1]-x[0]
lam=W*math.sqrt(0.125)

def solve_for_phiw(phi_w, tol=1e-13, maxit=100):
    """Solve bulk equilibrium with phi[0]=phi_w, phi[N-1]=PHI_H.
    Unknowns: phi[1..N-2] (N-2 of them) + phi_g (1). Total N-1.
    Equations: node 0 equilibrium (reads phi_g), nodes 1..N-2 equilibrium.
    """
    # initial guess: tanh from phi_w to PHI_H
    phi_init = phi_w + (PHI_H - phi_w)*(1.0 - np.exp(-x/5.0))
    phi_init[0]=phi_w; phi_init[-1]=PHI_H
    # unknown vector: [phi[1], phi[2], ..., phi[N-2], phi_g]
    u = np.concatenate([phi_init[1:N-1], [phi_w]])  # phi_g init = phi_w
    Nu = N-1  # number of unknowns

    def unpack(u):
        phi = np.empty(N)
        phi[0]=phi_w; phi[1:N-1]=u[:N-2]; phi[-1]=PHI_H
        phi_g = u[N-2]
        return phi, phi_g

    def lap_node(i, phi, phi_g):
        if i==0: return (phi_g - 2.0*phi[0] + phi[1])/(dx*dx)
        if i==N-1: return (phi[N-2] - 2.0*phi[N-1] + PHI_H)/(dx*dx)
        return (phi[i-1] - 2.0*phi[i] + phi[i+1])/(dx*dx)

    def resid(u):
        phi, phi_g = unpack(u)
        r = np.empty(Nu)
        # node 0 equilibrium: mu_bulk(phi_w) - kappa*lap0 = 0
        r[0] = mu_bulk(phi[0]) - KAPPA*lap_node(0, phi, phi_g)
        # nodes 1..N-2 equilibrium
        for i in range(1, N-1):
            r[i] = mu_bulk(phi[i]) - KAPPA*lap_node(i, phi, phi_g)
        return r

    for it in range(maxit):
        r = resid(u)
        rmax = np.max(np.abs(r))
        if rmax < tol:
            phi, phi_g = unpack(u)
            return phi, phi_g, rmax
        eps=1e-7
        J=np.zeros((Nu,Nu))
        for j in range(Nu):
            up=u.copy(); up[j]+=eps
            J[:,j]=(resid(up)-r)/eps
        try:
            du=np.linalg.solve(J,-r)
        except np.linalg.LinAlgError:
            return None
        alpha=1.0
        for _ in range(30):
            un=u+alpha*du
            if np.max(np.abs(resid(un)))<rmax: u=un; break
            alpha*=0.5
        else:
            u=u+du
        # clip phi interior to physical range to avoid runaway
        u[:N-2]=np.clip(u[:N-2],-0.5,1.5)
        u[N-2]=max(-0.5,min(1.5,u[N-2]))
    return None

print(f"Option B: imposed-wall-value consistency test")
print(f"L={L}, N={N}, dx={dx:.4f}, kappa={KAPPA:.6e}, MU_SCALE={MU_SCALE:.6e}")
print()
print(f"{'phi_w':>7} {'phi_g':>9} {'slope_c':>10} {'mwt_impl':>11} {'R_cand':>11} {'conv':>5}")

results=[]
for phi_w in [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]:
    sol = solve_for_phiw(phi_w)
    if sol is None:
        print(f"{phi_w:7.3f}  NO CONVERGENCE")
        results.append({'phi_w':phi_w,'converged':False})
        continue
    phi, phi_g, rmax = sol
    slope_c = (phi_w - phi_g)/(2.0*dx)
    mwt_impl = KAPPA*slope_c   # the h_g*cos(theta)*MU_SCALE that makes NBC=0
    lap_wall = (phi_g - 2.0*phi_w + phi[1])/(dx*dx)
    R_cand = mu_bulk(phi_g) - KAPPA*lap_wall - mwt_impl
    ok = "OK" if abs(R_cand)<1e-8 else "FAIL"
    print(f"{phi_w:7.3f} {phi_g:9.4f} {slope_c:10.4f} {mwt_impl:11.3e} {R_cand:11.3e} {ok:>5}")
    results.append({'phi_w':phi_w,'phi_g':phi_g,'slope_c':slope_c,
                    'mwt_implied':mwt_impl,'R_cand':R_cand,'rmax':rmax,'converged':True})

print()
print("=== Option B verdict ===")
conv_all = all(r.get('converged',False) for r in results)
if conv_all:
    rcands = [abs(r['R_cand']) for r in results if r.get('converged')]
    max_rcand = max(rcands)
    print(f"all phi_w converged: YES")
    print(f"max|R_cand| over sweep = {max_rcand:.3e}")
    if max_rcand < 1e-8:
        print("VERDICT: PASS. Candidate chemical-potential form is consistent with")
        print("the natural BC at every imposed wall value. Option A is warranted.")
    elif max_rcand < 1e-6:
        print("VERDICT: MARGINAL. max|R_cand| < 1e-6 but > 1e-8. Investigate before A.")
    else:
        print("VERDICT: FAIL. Candidate inconsistent with NBC. Stage10 STOPS.")
else:
    print("VERDICT: FAIL. Bulk equilibrium did not converge for some phi_w. Stage10 STOPS.")

out=os.path.join(os.path.dirname(__file__),'v1b_results.json')
with open(out,'w') as f: json.dump(results,f,indent=2)
print(f"\nresults saved to {out}")
