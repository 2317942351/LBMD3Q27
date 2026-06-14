#!/usr/bin/env python3
"""gen_cylinder_stl.py - generate a binary STL of a finite cylinder.
Axis along x (AnalyticSolidAxis=0), centered at (cx, cy) in the y-z plane,
radius R, spanning x in [x_min, x_max]. Normals point OUTWARD (away from axis)
on the lateral surface; the end caps are open (the cylinder is a tube whose
ends coincide with the domain wall, so TCLB's outer-domain wall closes them).

Usage: python3 gen_cylinder_stl.py <cx> <cy> <radius> <x_min> <x_max> <out.stl>
"""
import sys, math, struct

cx, cy = float(sys.argv[1]), float(sys.argv[2])
R = float(sys.argv[3])
x_min, x_max = float(sys.argv[4]), float(sys.argv[5])
outfile = sys.argv[6]

n_theta = 48   # circumferential segments
# lateral surface quads -> 2 triangles each
faces = []
for i in range(n_theta):
    a0 = 2.0*math.pi*i/n_theta
    a1 = 2.0*math.pi*(i+1)/n_theta
    # 4 corners of the quad strip
    y0a = cy + R*math.sin(a0); z0a = cx*0 + (0)  # placeholder
    # actually: y = cy + R sin(theta), z = cz + R cos(theta); but cz is the
    # cylinder axis z-coordinate. For axis along x centered at (cx_axis, cy_axis)
    # the perpendicular plane is (y,z); center in that plane is (cy, cz_axis).
    pass

# Redo cleanly: axis = x. Perpendicular plane is (y,z). Center in (y,z) = (cy_center, cz_center).
# But the user passed (cx, cy) = center in (y,z)? Re-read: cx is the x-axis location (irrelevant
# for an x-axis cylinder), cy is the y-center. We also need cz_center. For simplicity assume
# the cylinder is centered at (y=cy, z=cz_default) where cz_default is read from the domain.
# To keep the interface simple, treat argv[1]=cy_center, argv[2]=cz_center.
cy_center = float(sys.argv[1])
cz_center = float(sys.argv[2])
R = float(sys.argv[3])
x_min = float(sys.argv[4])
x_max = float(sys.argv[5])

faces = []
for i in range(n_theta):
    a0 = 2.0*math.pi*i/n_theta
    a1 = 2.0*math.pi*(i+1)/n_theta
    ya, za = cy_center + R*math.cos(a0), cz_center + R*math.sin(a0)
    yb, zb = cy_center + R*math.cos(a1), cz_center + R*math.sin(a1)
    # quad: (x_min,ya,za)-(x_min,yb,zb)-(x_max,yb,zb)-(x_max,ya,za)
    v00 = (x_min, ya, za)
    v01 = (x_min, yb, zb)
    v11 = (x_max, yb, zb)
    v10 = (x_max, ya, za)
    # two triangles; ensure outward normal (away from axis)
    # axis point at this theta: (any_x, cy_center + 0, cz_center + 0) projected
    # centroid of the quad
    mc = ((ya+yb)/2 - cy_center, (za+zb)/2 - cz_center)  # radial dir in (y,z)
    # try triangle (v00,v01,v11), compute normal, flip if dot with radial < 0
    for tri in [((v00,v01,v11)), ((v00,v11,v10))]:
        (p0,p1,p2) = tri
        ux,uy,uz = p1[0]-p0[0],p1[1]-p0[1],p1[2]-p0[2]
        wx,wy,wz = p2[0]-p0[0],p2[1]-p0[1],p2[2]-p0[2]
        nx = uy*wz-uz*wy; ny=uz*wx-ux*wz; nz=ux*wy-uy*wx
        nl=math.sqrt(nx*nx+ny*ny+nz*nz)
        if nl<1e-30: nx,ny,nz,nl=0,0,1,1
        nx,ny,nz=nx/nl,ny/nl,nz/nl
        # outward = normal points away from axis in (y,z): dot with radial
        dot = ny*mc[0]+nz*mc[1]
        if dot<0:
            p1,p2=p2,p1
            nx,ny,nz=-nx,-ny,-nz
        faces.append((nx,ny,nz,p0,p1,p2))

with open(outfile,'wb') as f:
    f.write(b'\0'*80)
    f.write(struct.pack('<I',len(faces)))
    for nx,ny,nz,p0,p1,p2 in faces:
        f.write(struct.pack('<3f',nx,ny,nz))
        f.write(struct.pack('<3f',*p0))
        f.write(struct.pack('<3f',*p1))
        f.write(struct.pack('<3f',*p2))
        f.write(struct.pack('<H',0))
print(f"wrote {len(faces)} triangles (cylinder lateral surface) to {outfile}")
print(f"cylinder axis=x, center(y,z)=({cy_center},{cz_center}), R={R}, x in [{x_min},{x_max}]")
