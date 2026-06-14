#!/usr/bin/env python3
"""v1_debug_neutral.py - debug the theta=90 (neutral) 1D equilibrium.
At theta=90, dfs_dphi=0, so the NBC says slope=0 -> phi_g = phi[0].
The equilibrium is just a tanh interface from phi_w (wall) to PHI_H (bulk).
For a symmetric double well with phi_l=0, phi_h=1, the equilibrium mu=0
and the profile is phi(x) = phi_avg + 0.5*(phi_h-phi_l)*tanh((x-x0)*(2/W_eff))
where W_eff relates to kappa and the double-well curvature.

This script solves the neutral case with a good initial guess and checks
convergence of the Newton solve. If this works, the sweep can proceed.
"""
import numpy as np
import math

SIGMA = 5e-5
W = 6.0
PHI_L = 0.0
PHI_H = 1.0
PHI_AVG = 0.5
KAPPA = 1.5 * SIGMA * W
MU_SCALE = 12.0 * SIGMA / W

def mu_bulk(phi):
    return 4.0 * MU_SCALE * (phi-PHI_L)*(phi-PHI_H)*(phi-PHI_AVG)

# Analytic equilibrium for a symmetric double-well + gradient term:
#   mu = mu_bulk(phi) - kappa * phi'' = 0  (mu_eq = 0 at coexistence)
#   => kappa * phi'' = mu_bulk(phi)
# Multiply by phi' and integrate: (kappa/2)(phi')^2 = psi(phi) - psi(phi_h)
# where psi is the bulk free-energy density (antiderivative of mu_bulk).
# psi(phi) = integral of 4*MU_SCALE*(phi)(phi-1)(phi-0.5) dphi
# The equilibrium tanh profile: phi(x) = 0.5*(1 - tanh((x-x0)/lambda))
# with lambda chosen so that kappa/lambda^2 matches the double-well curvature.
# For phi_bulk = 4*MU_SCALE*phi*(phi-1)*(phi-0.5), near phi=0.5:
#   d mu_bulk/d phi|_{0.5} = 4*MU_SCALE*((0.5-1)*(0.5-0.5) + ...) = 4*MU_SCALE*(-0.25) = -MU_SCALE
# So the interface curvature gives kappa/lambda^2 = MU_SCALE (magnitudes), i.e.
#   lambda = sqrt(kappa/MU_SCALE) = sqrt(1.5*sigma*W / (12*sigma/W)) = sqrt(1.5*W^2/12) = W*sqrt(0.125)
#          = W * 0.3536
# The tanh argument is (x-x0)/lambda, and the "IntWidth" W corresponds to
# 2*lambda in the convention phi = 0.5*(1-tanh(2*(x-x0)/W)), so lambda = W/2. Check:
#   W*sqrt(0.125) = W*0.3536, W/2 = 0.5*W. Close but not equal -> the tanh is an
#   APPROXIMATION; the true profile is elliptic. For initialization it's fine.

lam = W * math.sqrt(0.125)
print(f"kappa={KAPPA:.6e}, MU_SCALE={MU_SCALE:.6e}, lambda={lam:.4f}")

# 1D grid
L = 40.0
N = 201
x = np.linspace(0.0, L, N)
dx = x[1]-x[0]

# Initial guess: tanh centered at x0=5 (interface 5 lu from wall), phi going 0->1
x0 = 5.0
phi_init = 0.5*(1.0 - np.tanh((x - x0)/lam))
# at theta=90, phi_g = phi[0]
phi_g_init = phi_init[0]
mu_eq_init = 0.0
y = np.concatenate([phi_init, [phi_g_init], [mu_eq_init]])
print(f"initial: phi[0]={phi_init[0]:.4f}, phi[N-1]={phi_init[-1]:.4f}, phi_g={phi_g_init:.4f}")

def lap_at(i, y):
    if i == 0:
        return (y[N] - 2.0*y[0] + y[1])
    if i == N-1:
        return (y[N-2] - 2.0*y[N-1] + PHI_H)
    return (y[i-1] - 2.0*y[i] + y[i+1])

def residual(y, dfs=0.0):
    r = np.zeros(N+2)
    r[N-1] = y[N-1] - PHI_H
    slope_c = (y[0]-y[N])/(2.0*dx)
    r[N] = KAPPA*slope_c + dfs
    mu_eq = y[N+1]
    for i in range(N):
        r[i] = mu_bulk(y[i]) - KAPPA*lap_at(i, y) - mu_eq
    return r

r0 = residual(y)
print(f"initial residual max = {np.max(np.abs(r0)):.3e}")

# Newton
for it in range(100):
    r = residual(y)
    rmax = np.max(np.abs(r))
    if rmax < 1e-12:
        print(f"CONVERGED at iter {it}, rmax={rmax:.3e}")
        break
    eps = 1e-7
    J = np.zeros((N+2, N+2))
    for j in range(N+2):
        yp = y.copy(); yp[j] += eps
        J[:, j] = (residual(yp) - r)/eps
    try:
        dy = np.linalg.solve(J, -r)
    except np.linalg.LinAlgError:
        print(f"iter {it}: singular Jacobian")
        break
    # backtracking
    alpha = 1.0
    accepted = False
    for _ in range(30):
        yn = y + alpha*dy
        if np.max(np.abs(residual(yn))) < rmax:
            y = yn; accepted = True; break
        alpha *= 0.5
    if not accepted:
        y = y + dy
    y[:N] = np.clip(y[:N], -0.5, 1.5)
    y[N] = max(-0.5, min(1.5, y[N]))
    if it % 10 == 0 or it < 5:
        print(f"iter {it}: rmax={rmax:.3e}, alpha={alpha:.3f}, phi[0]={y[0]:.4f}, phi_g={y[N]:.4f}, mu_eq={y[N+1]:.3e}")
else:
    print(f"NOT CONVERGED, final rmax={rmax:.3e}")

# measure candidate residual at theta=90 (dfs=0, mwt=0)
phi = y[:N]; phi_g = y[N]; mu_eq = y[N+1]
lap_wall = (phi_g - 2.0*phi[0] + phi[1])
cp_resid = mu_bulk(phi_g) - KAPPA*lap_wall - 0.0
nat_resid = KAPPA*(phi[0]-phi_g)/(2.0*dx) + 0.0
print(f"\n=== theta=90 result ===")
print(f"phi[0]={phi[0]:.6f}, phi_g={phi_g:.6f}, mu_eq={mu_eq:.3e}")
print(f"natural_BC_residual = {nat_resid:.3e}")
print(f"candidate cp_residual = {cp_resid:.3e}")
