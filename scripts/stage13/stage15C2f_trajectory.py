#!/usr/bin/env python3
"""C2f: changed-angle trajectory at ForceCap=0.2 vs Coeff=0 baseline (C2e base).
Classify: EFFECTIVE (test separates from base) / STILL_WEAK (indistinguishable) /
UNSTABLE (NaN/pollution). Pure post-processing.
"""
import json, glob
from pathlib import Path
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy as v2n

TEST = Path("/mnt/usb1t/RUNS/runs/stage15C2f_changed_angle_test")
BASE = Path("/mnt/usb1t/RUNS/runs/stage15C2e_changed_angle_base")  # Coeff=0 baseline (same binary)
OUT  = Path("/home/yuan/stage15C2f_trajectory"); OUT.mkdir(parents=True, exist_ok=True)
CX = CZ = 48.0
CASES = ["decouple_wall_60to30", "decouple_wall_120to150"]
TARGETS = {"decouple_wall_60to30": 30, "decouple_wall_120to150": 150}
CAP = 0.2 * 5e-5/3.0  # ForceCap=0.2

def load(p):
    r = vtk.vtkXMLImageDataReader(); r.SetFileName(p); r.Update()
    d = r.GetOutput().GetCellData(); A = {}
    for i in range(d.GetNumberOfArrays()):
        a = d.GetArray(i); A[a.GetName()] = v2n(a).copy()
    return tuple(v-1 for v in r.GetOutput().GetDimensions()), A

def frames(cd):
    vs = glob.glob(str(Path(cd)/"output"/"case_VTK_P00_*.vti"))
    return sorted(vs, key=lambda x: int(x.split("_")[-1].split(".")[0]))

def step_of(p): return int(p.split("_")[-1].split(".")[0])

def fm(p):
    dims, A = load(p); nx, ny, nz = dims
    ph = A["PhaseField"]; U = A["U"]
    U3 = U.reshape(ph.size, 3) if U.size == ph.size*3 else np.zeros((ph.size, 3))
    uspeed = np.sqrt(U3[:,0]**2 + U3[:,1]**2 + U3[:,2]**2)
    ph3 = ph.reshape((nx, ny, nz))
    xs = np.arange(nx).reshape((nx, 1, 1)).astype(float); zs = np.arange(nz).reshape((1, 1, nz)).astype(float)
    rr = np.broadcast_to(np.sqrt((xs-CX)**2 + (zs-CZ)**2), (nx, ny, nz))
    band = (ph3 > 0.05) & (ph3 < 0.95)
    footprint = float(rr[band].max()) if band.any() else float("nan")
    isb = A["IsItBoundary"].reshape((nx, ny, nz)); act = A["DynamicCLActive"].reshape((nx, ny, nz))
    fmag = A["DynamicCLForceCandidateMag"].reshape((nx, ny, nz))
    capp = A["DynamicCLCosApp"].reshape((nx, ny, nz)); rth = A["DynamicCLCosResidual"].reshape((nx, ny, nz))
    m = (act > 0.5) & (isb < 0.5) & band
    af = fmag[m] if m.any() else np.array([0.0])
    cf = float(np.mean(af >= CAP*0.999)) if af.size else 0.0
    spur = int(((fmag > 0) & (isb < 0.5) & ~(act > 0.5)).sum())
    if m.any():
        cm = capp[m].mean(); rm = rth[m].mean()
        ta = float(np.degrees(np.arccos(np.clip(cm, -1, 1))))
    else:
        cm = rm = float("nan"); ta = float("nan")
    return dict(step=step_of(p),
        nan=int((~np.isfinite(ph)).sum() + (~np.isfinite(U)).sum()),
        mass=float(ph.mean()), ph_min=float(ph.min()), ph_max=float(ph.max()),
        footprint=footprint, umax=float(uspeed.max()), fclmax=float(fmag.max()),
        capfrac=cf, spur=spur, R=float(rm), theta_app=ta)

results = {}
for case in CASES:
    results[case] = dict(target=TARGETS[case],
                         test=[fm(p) for p in frames(TEST/case)],
                         base=[fm(p) for p in frames(BASE/case)])

for case in CASES:
    t = TARGETS[case]
    print("\n" + "="*120)
    print("CASE " + case + "  target=" + str(t) + "deg   test ForceCap=0.2 Coeff=2  vs  base Coeff=0")
    print("="*120)
    hdr = "step | th_appT th_appB | |R|T |R|B | footT footB | massT massB | Fcl_max cap% spur |U|maxT"
    print(hdr); print("-"*120)
    bmap = {r["step"]: r for r in results[case]["base"]}
    for tr in results[case]["test"]:
        s = tr["step"]; br = bmap.get(s)
        if br is None: continue
        print("%5d | %7.2f %7.2f | %.4f %.4f | %6.2f %6.2f | %.5f %.5f | %.2e %3d%% %3d %.2e" % (
            s, tr["theta_app"], br["theta_app"], abs(tr["R"]), abs(br["R"]),
            tr["footprint"], br["footprint"], tr["mass"], br["mass"],
            tr["fclmax"], tr["capfrac"]*100, tr["spur"], tr["umax"]))
    tf, tl = results[case]["test"][1], results[case]["test"][-1]
    bf, bl = bmap.get(tf["step"]), bmap.get(tl["step"])
    print("\n  theta_app: test %.2f->%.2f  base %.2f->%.2f  (target %d)" % (
        tf["theta_app"], tl["theta_app"], bf["theta_app"], bl["theta_app"], t))
    print("  |R|:       test %.4f->%.4f  base %.4f->%.4f" % (
        abs(tf["R"]), abs(tl["R"]), abs(bf["R"]), abs(bl["R"])))
    print("  footprint: test %.2f->%.2f  base %.2f->%.2f" % (
        tf["footprint"], tl["footprint"], bf["footprint"], bl["footprint"]))

print("\n" + "="*120); print("CLASSIFICATION")
eff = {}
for case in CASES:
    t = results[case]["test"]; b = {r["step"]: r for r in results[case]["base"]}
    max_dtheta = max(abs(tr["theta_app"] - b[tr["step"]]["theta_app"]) for tr in t[1:])
    rt_red = abs(t[1]["R"]) - abs(t[-1]["R"])
    rb_red = abs(b[t[1]["step"]]["R"]) - abs(b[t[-1]["step"]]["R"])
    nan = max(r["nan"] for r in t); spur = max(r["spur"] for r in t)
    unstable = nan > 0 or spur > 0
    cls = "UNSTABLE" if unstable else ("EFFECTIVE" if max_dtheta > 0.05 else "STILL_WEAK")
    eff[case] = dict(max_dtheta=max_dtheta, rt_red=rt_red, rb_red=rb_red, nan=nan, spur=spur, cls=cls)
    print("  %s: max|d_theta_app(test-base)|=%.4fdeg  |R|red test=%+.4f base=%+.4f  NaN=%d spur=%d  -> %s" % (
        case, max_dtheta, rt_red, rb_red, nan, spur, cls))
(OUT/"summary.json").write_text(json.dumps({"results": results, "class": eff}, indent=2))
print("\nwrote " + str(OUT/"summary.json"))
