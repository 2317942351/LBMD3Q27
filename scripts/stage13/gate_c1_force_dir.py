#!/usr/bin/env python3
"""Stage15C gate C1: DynamicCLForceSign direction calibration (shadow, Mode=1).

For decoupled cases (60->30 should spread, 120->150 should retract), compute
the RADIAL projection of the candidate contact-line force over active nodes:

    r = (x - x0, z - z0)          # in-plane position from footprint center
    e_r = r / |r|
    F_parallel = F_cand_x * e_r_x + F_cand_z * e_r_z

Sign convention: F_parallel > 0 means the candidate force points OUTWARD
(spreads the footprint); F_parallel < 0 means INWARD (retracts).

Expected for correct ForceSign:
    60->30   (spread):  mean/median F_parallel > 0
    120->150 (retract): mean/median F_parallel < 0

Usage: python3 gate_c1_force_dir.py <pvti> <x0> <z0> <case_label>
"""
import sys
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy


def main():
    path = sys.argv[1]
    x0 = float(sys.argv[2]) if len(sys.argv) > 2 else 48.0  # footprint center x
    z0 = float(sys.argv[3]) if len(sys.argv) > 3 else 48.0  # footprint center z
    label = sys.argv[4] if len(sys.argv) > 4 else path

    reader = vtk.vtkXMLPImageDataReader()
    reader.SetFileName(path)
    reader.Update()
    dims = reader.GetOutput().GetDimensions()
    nx_c, ny_c, nz_c = dims[0] - 1, dims[1] - 1, dims[2] - 1
    origin = reader.GetOutput().GetOrigin()
    spacing = reader.GetOutput().GetSpacing()
    cd = reader.GetOutput().GetCellData()

    def get(name):
        a = cd.GetArray(name)
        return vtk_to_numpy(a).reshape((nz_c, ny_c, nx_c)) if a is not None else None

    active = get("DynamicCLActive")
    fx = get("DynamicCLForceCandidateX")
    fz = get("DynamicCLForceCandidateZ")
    fmag = get("DynamicCLForceCandidateMag")
    resid = get("DynamicCLCosResidual")
    found = get("DynamicCLWallContextFound")
    br = get("DynamicCLBlockedReason")

    if any(a is None for a in (active, fx, fz)):
        print(f"[{label}] missing required fields (active/fx/fz)")
        return

    # cell-center coordinates
    ix = np.arange(nx_c) * spacing[0] + origin[0] + 0.5 * spacing[0]
    iz = np.arange(nz_c) * spacing[2] + origin[2] + 0.5 * spacing[2]
    X, Z = np.meshgrid(ix, iz)  # shape (nz_c, nx_c), broadcast over y handled below

    act = active > 0.5
    n_act = int(act.sum())
    print(f"\n{'='*64}")
    print(f"C1 FORCE DIRECTION: {label}")
    print(f"{'='*64}")
    print(f"footprint center (x0,z0)=({x0},{z0}); active nodes={n_act}")

    if n_act == 0:
        print("  NO active nodes -- check BlockedReason")
        if br is not None:
            u, c = np.unique(br, return_counts=True)
            print(f"  BlockedReason: {dict(zip(u.tolist(),c.tolist()))}")
        return

    # collapse active over y to get per-(x,z) active presence; for radial proj
    # use the active mask summed over y (any active cell at that x,z)
    act_xz = (act.sum(axis=1) > 0)  # (nz_c, nx_c)
    # ForceCandidate is constant over y within the contact band in expectation;
    # average fx,fz over y for active cells to get a per-(x,z) force vector.
    fx_a = fx[act].mean(); fz_a = fz[act].mean()

    # For radial projection per active cell, use cell x,z coords. Stack active
    # cell coordinates directly.
    ay = np.where(act)  # (iz, iy, ix) tuples
    ax_coord = ix[ay[2]]
    az_coord = iz[ay[0]]
    rx = ax_coord - x0
    rz = az_coord - z0
    rmag = np.sqrt(rx*rx + rz*rz)
    # avoid div-by-zero at center
    good = rmag > 1e-9
    er_x = np.zeros_like(rx); er_z = np.zeros_like(rz)
    er_x[good] = rx[good] / rmag[good]
    er_z[good] = rz[good] / rmag[good]

    fx_c = fx[act]
    fz_c = fz[act]
    f_par = fx_c * er_x + fz_c * er_z  # radial projection per active cell

    print(f"  mean(F_parallel)   = {f_par.mean():+.6e}")
    print(f"  median(F_parallel) = {np.median(f_par):+.6e}")
    p10, p90 = np.percentile(f_par, [10, 90])
    print(f"  p10/p90(F_parallel)= {p10:+.6e} / {p90:+.6e}")
    print(f"  frac(F_parallel>0) = {(f_par>0).mean():.3f}  (outward)")
    print(f"  frac(F_parallel<0) = {(f_par<0).mean():.3f}  (inward)")
    print(f"  mean(|F_cand|)     = {np.abs(fmag[act]).mean():.6e}" if fmag is not None else "")
    if resid is not None:
        print(f"  mean(residual)     = {resid[act].mean():+.6e}  (sign of R_theta)")

    # footprint baseline (initial geometry, for C2 reference) - q=0.5 extent
    q = get("PhaseField")
    if q is not None:
        band = (q > 0.4) & (q < 0.6)
        if band.any():
            by = np.where(band)
            bx = ix[by[2]]; bz = iz[by[0]]
            print(f"  footprint baseline (q~0.5 band): "
                  f"x[{bx.min():.1f},{bx.max():.1f}] z[{bz.min():.1f},{bz.max():.1f}]")
            fr = np.sqrt((bx-x0)**2 + (bz-z0)**2)
            print(f"  footprint radius: mean={fr.mean():.2f} max={fr.max():.2f}")


if __name__ == "__main__":
    main()
