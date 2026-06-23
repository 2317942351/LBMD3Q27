#!/usr/bin/env python3
"""stage12_plot_cyl90.py - plot the cylinder theta=90 droplet cross-section.
Slice through the cylinder axis (x = droplet center), show the phase field in
the (y, z) plane with the phi=0.5 contour and the cylinder outline."""
import sys, math
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

vti = sys.argv[1]
out_png = sys.argv[2]
cy_c = float(sys.argv[3]); cz_c = float(sys.argv[4]); R_solid = float(sys.argv[5])
ix_slice = int(float(sys.argv[6]))

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

# slice at ix_slice through the cylinder axis
sl_pf = pf3[:, :, ix_slice].copy()      # shape (nz, ny): rows=z, cols=y
sl_bd = bd3[:, :, ix_slice].copy()

# mask solid nodes as NaN so they plot distinctly
sl_pf_masked = np.where(sl_bd > 0.5, np.nan, sl_pf)

fig, ax = plt.subplots(figsize=(8, 9))
# phase field: transpose so y is horizontal, z is vertical
im = ax.imshow(sl_pf_masked, origin='lower', extent=[0, ny, 0, nz],
               cmap='RdYlBu', vmin=0, vmax=1, aspect='equal', interpolation='nearest')
# phi=0.5 contour overlaid
Y = np.arange(0.5, ny); Z = np.arange(0.5, nz)
Zg, Yg = np.meshgrid(Z, Y, indexing='ij')
cs = ax.contour(Yg, Zg, sl_pf_masked, levels=[0.5], colors='black', linewidths=2.5)
# cylinder outline (cross-section = circle in y-z plane), filled lightly
circ_fill = plt.Circle((cy_c, cz_c), R_solid, fill=True, color='lightgray', alpha=0.4, zorder=0)
ax.add_patch(circ_fill)
circ = plt.Circle((cy_c, cz_c), R_solid, fill=False, color='green', linewidth=2.5, linestyle='--', zorder=5)
ax.add_patch(circ)
ax.plot(cy_c, cz_c, 'g+', markersize=14, markeredgewidth=2.5, zorder=6)  # cylinder axis
# apex marker
ax.plot(cy_c, cz_c + R_solid, 'r^', markersize=10, markeredgewidth=1.5, zorder=6,
        label='cylinder apex')
ax.text(cy_c+1, cz_c + R_solid + 1, f'apex z={cz_c+R_solid:.0f}', color='red', fontsize=9)
ax.set_xlabel('y (lattice units)', fontsize=11)
ax.set_ylabel('z (lattice units)', fontsize=11)
ax.set_title(f'Stage12 cylinder theta=90 (neutral), W=3, step 100000\n'
             f'slice x={ix_slice} (through cylinder axis)\n'
             f'cyl center=({cy_c},{cz_c}) R={R_solid}; droplet init (48,48,70) R=16\n'
             f'solid/fluid assignment must be confirmed with stage12_geometry_gate.py.',
             fontsize=9)
cbar = plt.colorbar(im, ax=ax, label='PhaseField (0=gas, 1=liquid)')
cbar.ax.tick_params(labelsize=9)
ax.set_xlim(20, ny-20)
ax.set_ylim(40, nz-30)
ax.set_aspect('equal')
plt.tight_layout()
plt.savefig(out_png, dpi=140, bbox_inches='tight')
print(f"saved {out_png}")

# also report key measurements
liquid = sl_pf_masked[np.isfinite(sl_pf_masked)]
print(f"slice ix={ix_slice}: fluid cells={len(liquid)}, "
      f"phi range=[{np.nanmin(sl_pf_masked):.4g}, {np.nanmax(sl_pf_masked):.4g}]")
# droplet extent: rows where phi>0.5
rows_liquid = np.where(np.nanmax(sl_pf_masked, axis=1) > 0.5)[0]
cols_liquid = np.where(np.nanmax(sl_pf_masked, axis=0) > 0.5)[0]
if len(rows_liquid) and len(cols_liquid):
    print(f"liquid spans z=[{rows_liquid.min()},{rows_liquid.max()}], y=[{cols_liquid.min()},{cols_liquid.max()}]")
