#!/usr/bin/env python3
"""v1b_diag.py - diagnose whether the Option B FAIL is a sign/convention error
or a real inconsistency. Check the ratio R_cand / mwt_implied and also compute
R_cand under alternative candidate definitions."""
import numpy as np, math, json
SIGMA=5e-5; W=6.0; PHI_L=0.0; PHI_H=1.0; PHI_AVG=0.5
KAPPA=1.5*SIGMA*W; MU_SCALE=12.0*SIGMA/W
def mu_bulk(p): return 4.0*MU_SCALE*(p-PHI_L)*(p-PHI_H)*(p-PHI_AVG)

with open('/home/yuan/v1b_results.json') as f: results=json.load(f)
print(f"{'phi_w':>6} {'phi_g':>8} {'mwt_impl':>11} {'R_cand':>11} {'R/mwt':>8} {'mu_bulk(phi_g)':>14} {'kappa*lap':>11}")
for r in results:
    if not r.get('converged'): continue
    pw=r['phi_w']; pg=r['phi_g']; mwt=r['mwt_implied']; Rc=r['R_cand']
    # recompute lap_wall from phi_g, phi_w, and a reconstructed phi[1]
    # phi[1] isn't stored; approximate lap_wall from R_cand definition:
    # R_cand = mu_bulk(phi_g) - kappa*lap_wall - mwt  => kappa*lap_wall = mu_bulk(phi_g) - mwt - R_cand
    mbg=mu_bulk(pg)
    klap = mbg - mwt - Rc
    ratio = Rc/mwt if abs(mwt)>1e-30 else float('inf')
    print(f"{pw:6.3f} {pg:8.4f} {mwt:11.3e} {Rc:11.3e} {ratio:8.3f} {mbg:14.3e} {klap:11.3e}")

print()
print("If R_cand/mwt ~ -1 consistently, the candidate has a sign/convention issue.")
print("If R_cand/mwt varies, it's a real shape inconsistency.")
print()
# Also: what would R_cand be if mu_wall_target = mwt but defined at phi_w not phi_g?
# candidate_alt: mu_bulk(phi_w) - kappa*lap_wall(phi_w) = mwt
# This tests whether the candidate should be evaluated at the wall node (phi_w)
# rather than the ghost (phi_g).
print("Alternative: candidate evaluated at phi_w (wall node) instead of phi_g (ghost):")
print(f"{'phi_w':>6} {'mu_bulk(phi_w)':>14} {'mu_bulk(phi_w)-klap-mwt':>24}")
for r in results:
    if not r.get('converged'): continue
    pw=r['phi_w']; pg=r['phi_g']; mwt=r['mwt_implied']; Rc=r['R_cand']
    mbg=mu_bulk(pg); klap=mbg-mwt-Rc
    R_alt = mu_bulk(pw) - klap - mwt
    print(f"{pw:6.3f} {mu_bulk(pw):14.3e} {R_alt:24.3e}")
