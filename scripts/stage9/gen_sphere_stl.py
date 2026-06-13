#!/usr/bin/env python3
"""gen_sphere_stl.py - generate an ASCII STL of a sphere of given radius and center.
Usage: python3 gen_sphere_stl.py <cx> <cy> <cz> <radius> <output.stl>
The sphere is the SOLID region (inside is solid). Triangulated via icosahedral
subdivision for a smooth surface."""
import sys, math

cx, cy, cz, R = (float(x) for x in sys.argv[1:5])
outfile = sys.argv[5]
n_sub = 4  # subdivisions; 4 gives ~2560 triangles, plenty for R=24 lu

# icosahedron vertices
t = (1.0 + math.sqrt(5.0)) / 2.0
verts = []
for x, y, z in [(-1,t,0),(1,t,0),(-1,-t,0),(1,-t,0),
                (0,-1,t),(0,1,t),(0,-1,-t),(0,1,-t),
                (t,0,-1),(t,0,1),(-t,0,-1),(-t,0,1)]:
    n = math.sqrt(x*x+y*y+z*z)
    verts.append((x/n, y/n, z/n))
faces = [(0,11,5),(0,5,1),(0,1,7),(0,7,10),(0,10,11),
         (1,5,9),(5,11,4),(11,10,2),(10,7,6),(7,1,8),
         (3,9,4),(3,4,2),(3,2,6),(3,6,8),(3,8,9),
         (4,9,5),(2,4,11),(6,2,10),(8,6,7),(9,8,1)]

def midpoint(a, b):
    return ((a[0]+b[0])/2, (a[1]+b[1])/2, (a[2]+b[2])/2)

# subdivide
for _ in range(n_sub):
    new_faces = []
    cache = {}
    def get_mid(i1, i2):
        key = (min(i1,i2), max(i1,i2))
        if key in cache: return cache[key]
        m = midpoint(verts[i1], verts[i2])
        n = math.sqrt(m[0]**2+m[1]**2+m[2]**2)
        verts.append((m[0]/n, m[1]/n, m[2]/n))
        idx = len(verts) - 1
        cache[key] = idx
        return idx
    for a, b, c in faces:
        ab = get_mid(a, b)
        bc = get_mid(b, c)
        ca = get_mid(c, a)
        new_faces.extend([(a,ab,ca),(b,bc,ab),(c,ca,bc),(ab,bc,ca)])
    faces = new_faces

# scale to radius R and translate, write BINARY STL (TCLB requires binary)
import struct
with open(outfile, 'wb') as f:
    # 80-byte header
    f.write(b'\0' * 80)
    # number of triangles
    f.write(struct.pack('<I', len(faces)))
    for a, b, c in faces:
        # vertices
        va = (verts[a][0]*R+cx, verts[a][1]*R+cy, verts[a][2]*R+cz)
        vb = (verts[b][0]*R+cx, verts[b][1]*R+cy, verts[b][2]*R+cz)
        vc = (verts[c][0]*R+cx, verts[c][1]*R+cy, verts[c][2]*R+cz)
        # normal
        ux, uy, uz = vb[0]-va[0], vb[1]-va[1], vb[2]-va[2]
        wx, wy, wz = vc[0]-va[0], vc[1]-va[1], vc[2]-va[2]
        nx = uy*wz - uz*wy
        ny = uz*wx - ux*wz
        nz = ux*wy - uy*wx
        nl = math.sqrt(nx*nx+ny*ny+nz*nz)
        if nl < 1e-30: nx, ny, nz, nl = 0, 0, 1, 1
        nx, ny, nz = nx/nl, ny/nl, nz/nl
        # normal (3 floats) + 3 vertices (9 floats) + attribute (uint16)
        f.write(struct.pack('<3f', nx, ny, nz))
        f.write(struct.pack('<3f', *va))
        f.write(struct.pack('<3f', *vb))
        f.write(struct.pack('<3f', *vc))
        f.write(struct.pack('<H', 0))
print(f"wrote {len(faces)} triangles (BINARY STL) to {outfile}")
print(f"sphere center=({cx},{cy},{cz}) radius={R}")

