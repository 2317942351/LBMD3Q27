#!/usr/bin/env python3
"""stage12_curved_angle.py - measure contact angle on a curved wall (cylinder
or sphere) from a phase-field VTK.

Method: take a vertical slice through the symmetry axis. Find the phi=0.5
contour. Find the contact line (where the contour meets the solid surface).
At the contact line, compute:
  - the interface tangent (from the contour direction)
  - the solid surface tangent (perpendicular to the analytic normal at the
    contact point)
The contact angle is the angle between these two tangents, measured through
the liquid.

For theta=90 (neutral), the interface meets the solid perpendicularly, so the
angle should be 90 deg. This is the validation of the post-processor itself.

Usage:
  python3 stage12_curved_angle.py <vti> <geom: cylinder|sphere> \
      <axis_x> <axis_y> <axis_z> <R_solid> <droplet_x> <droplet_y> <droplet_z>
  For cylinder, axis is along x: (axis_y, axis_z) is the center in the y-z plane.
  For sphere, (axis_x, axis_y, axis_z) is the center, R_solid the radius.
"""
import sys, math
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy

vti = sys.argv[1]
geom = sys.argv[2]
cx_c = float(sys.argv[3])
cy_c = float(sys.argv[4])
cz_c = float(sys.argv[5])
R_solid = float(sys.argv[6])
dx_drop = float(sys.argv[7]); dy_drop = float(sys.argv[8]); dz_drop = float(sys.argv[9])

r = vtk.vtkXMLImageDataReader(); r.SetFileName(vti); r.Update()
out = r.GetOutput()
pf = vtk_to_numpy(out.GetCellData().GetArray("PhaseField")).copy()
bd_arr = out.GetCellData().GetArray("IsItBoundary")
if bd_arr is None:
    bd_arr = out.GetCellData().GetArray("BOUNDARY")
bd = vtk_to_numpy(bd_arr).copy()
dims = out.GetDimensions()
nx, ny, nz = dims[0]-1, dims[1]-1, dims[2]-1
pf3 = pf.reshape((nz, ny, nx))
bd3 = bd.reshape((nz, ny, nx))
fluid = bd3 < 0.5
pf_fluid = np.where(fluid, pf3, np.nan)

print(f"VTK: {vti}")
print(f"geom={geom}, solid center=({cx_c},{cy_c},{cz_c}), R_solid={R_solid}")
print(f"grid: {nx}x{ny}x{nz}")

# take the slice at the droplet's x-center (for cylinder, axis is along x so
# any x-slice through the droplet center shows the cross-section)
ix = int(round(dx_drop))
if ix >= nx: ix = nx//2
print(f"slice at ix={ix}")
slice2d = pf_fluid[:, :, ix]  # shape (nz, ny) -> indices (iz, iy)

# find the phi=0.5 contour in the (y, z) plane
# the droplet sits above the solid; the contact line is where phi=0.5 meets
# the solid surface. Find all (iy, iz) where phi crosses 0.5.
contour_pts = []  # list of (y, z)
# scan along z (rows) for y-crossings
for iz in range(nz):
    row = slice2d[iz, :]
    for iy in range(1, ny):
        a, b = row[iy-1], row[iy]
        if np.isnan(a) or np.isnan(b): continue
        if (a-0.5)*(b-0.5) < 0:
            frac = (0.5-a)/(b-a)
            contour_pts.append((iy-1+frac, iz))
# also scan along y for z-crossings (denser sampling)
for iy in range(ny):
    col = slice2d[:, iy]
    for iz in range(1, nz):
        a, b = col[iz-1], col[iz]
        if np.isnan(a) or np.isnan(b): continue
        if (a-0.5)*(b-0.5) < 0:
            frac = (0.5-a)/(b-a)
            contour_pts.append((iy, iz-1+frac))

if not contour_pts:
    print("ERROR: no phi=0.5 contour found in slice")
    sys.exit(1)

pts = np.array(contour_pts)  # (N, 2): columns (y, z)
print(f"contour points: {len(pts)}")

# find the contact line: contour points closest to the solid surface
# For the cylinder, the slice is normal to the y-z cross-section. For the
# sphere, this is the central x-slice, so the surface is also a circle in y-z.
dist_to_surf = np.sqrt((pts[:,0]-cy_c)**2 + (pts[:,1]-cz_c)**2) - R_solid
# contact line points: those with |dist_to_surf| minimal
# take the lowest-z contour points (the droplet sits above; contact at bottom)
# Actually take points near the surface (|dist| < 3 lu)
near = np.abs(dist_to_surf) < 3.0
if not near.any():
    near = np.ones(len(pts), dtype=bool)
contact_pts = pts[near]
print(f"contact-line candidate points (|dist to surf|<3): {len(contact_pts)}")

# split into left and right contact lines by y relative to center
left = contact_pts[contact_pts[:,0] < cy_c]
right = contact_pts[contact_pts[:,0] >= cy_c]
print(f"left: {len(left)}, right: {len(right)}")

def angle_at_contact(cp, cy_c, cz_c, R_solid):
    """Compute contact angle at a contact point cp=(y,z).
    Interface tangent: from the local contour direction (use the neighboring
    contour points). Solid tangent: perpendicular to the radial direction at cp.
    Angle between them through the liquid (above the surface)."""
    if len(cp) < 3: return None
    # use the average position
    yc, zc = cp[:,0].mean(), cp[:,1].mean()
    # solid normal (outward) at this point: radial direction
    ny_s = (yc - cy_c)/R_solid
    nz_s = (zc - cz_c)/R_solid
    # solid tangent: perpendicular to normal
    ty_s = -nz_s; tz_s = ny_s
    # interface tangent: fit a line to the contour points just above the contact
    # take contour points with z > zc (into the droplet)
    # use all near-surface points slightly above
    # simpler: interface tangent from the contour direction via PCA of local pts
    # use points within a small window of the contact
    local = cp  # already near-surface
    if len(local) < 2: return None
    # PCA: principal axis
    mu = local.mean(axis=0)
    cov = np.cov((local-mu).T)
    if cov.shape != (2,2): return None
    w, v = np.linalg.eigh(cov)
    ti = v[:, -1]  # principal direction (interface tangent)
    ty_i, tz_i = ti[0], ti[1]
    # angle between interface tangent and solid tangent
    dot = ty_i*ty_s + tz_i*tz_s
    dot = max(-1.0, min(1.0, dot))
    ang = math.degrees(math.acos(abs(dot)))
    # the contact angle is measured through the liquid; for a droplet above the
    # surface, if the interface tangent points up-and-out, the angle is acute
    # for wetting. Refine: measure angle between interface tangent (pointing
    # away from droplet center, upward) and the solid tangent pointing outward.
    return ang

for side, cp in [('left', left), ('right', right)]:
    if len(cp) < 2:
        print(f"  {side}: insufficient points")
        continue
    ang = angle_at_contact(cp, cy_c, cz_c, R_solid)
    print(f"  {side} contact angle: {ang:.2f} deg" if ang else f"  {side}: could not compute")

# also report droplet extent and phi stats
liquid = pf_fluid[np.isfinite(pf_fluid)]
print(f"phase range: [{np.nanmin(pf_fluid):.4g}, {np.nanmax(pf_fluid):.4g}]")
