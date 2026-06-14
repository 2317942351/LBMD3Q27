#!/usr/bin/env python3
"""stage11_analyze.py - analyze the W/R convergence results.
Reads results.txt (name W R R_over_W measured_angle rc nan).
Checks: (1) does error decrease as W/R decreases in each sweep?
        (2) do the two sweeps agree at matched W/R?"""
import sys, math

TARGET = 30.0
TOL = 2.0   # the <2 deg target

rows = []
with open(sys.argv[1]) as f:
    for line in f:
        parts = line.split()
        if len(parts) < 7 or parts[0] in ('name',): continue
        name, W, R, RoW, angle, rc, nan = parts[0], float(parts[1]), float(parts[2]), float(parts[3]), parts[4], parts[5], parts[6]
        if angle == 'FAIL':
            rows.append({'name':name,'W':W,'R':R,'RoW':RoW,'angle':None,'rc':int(rc),'nan':int(nan),'sweep':name.split('_')[0]})
        else:
            rows.append({'name':name,'W':W,'R':R,'RoW':RoW,'angle':float(angle),'rc':int(rc),'nan':int(nan),'sweep':name.split('_')[0]})

print(f"{'name':<14} {'W':>4} {'R':>4} {'R/W':>5} {'angle':>7} {'err':>7} {'status':>8}")
ok_rows = []
for r in rows:
    if r['angle'] is None:
        print(f"{r['name']:<14} {r['W']:4.0f} {r['R']:4.0f} {r['RoW']:5.1f} {'FAIL':>7} {'-':>7} {'FAILED':>8}")
    else:
        err = r['angle'] - TARGET
        status = 'OK' if abs(err) < TOL else f'+{err:.2f}'
        print(f"{r['name']:<14} {r['W']:4.0f} {r['R']:4.0f} {r['RoW']:5.1f} {r['angle']:7.2f} {err:+7.2f} {status:>8}")
        ok_rows.append(r)

print()
# sweep 1: fixed R=24, vary W. Error should DECREASE as W decreases (R/W increases).
s1 = [r for r in ok_rows if r['sweep']=='s1']
s1.sort(key=lambda r: r['RoW'])   # ascending R/W
print("SWEEP 1 (fixed R=24, vary W), sorted by R/W ascending:")
for r in s1:
    print(f"  R/W={r['RoW']:5.1f} (W={r['W']:.0f}): angle={r['angle']:.2f}, err={r['angle']-TARGET:+.2f}")
if len(s1) >= 2:
    errs = [r['angle']-TARGET for r in s1]
    mono = all(errs[i] >= errs[i+1] for i in range(len(errs)-1))
    print(f"  error monotonically decreasing as R/W increases: {mono}")

print()
# sweep 2: fixed W=6, vary R. Error should DECREASE as R increases (R/W increases).
s2 = [r for r in ok_rows if r['sweep']=='s2']
s2.sort(key=lambda r: r['RoW'])
print("SWEEP 2 (fixed W=6, vary R), sorted by R/W ascending:")
for r in s2:
    print(f"  R/W={r['RoW']:5.1f} (R={r['R']:.0f}): angle={r['angle']:.2f}, err={r['angle']-TARGET:+.2f}")
if len(s2) >= 2:
    errs = [r['angle']-TARGET for r in s2]
    mono = all(errs[i] >= errs[i+1] for i in range(len(errs)-1))
    print(f"  error monotonically decreasing as R/W increases: {mono}")

print()
# collapse check: at matched R/W, do the sweeps agree?
print("COLLAPSE CHECK (matched R/W, sweep1 vs sweep2):")
s1_by = {round(r['RoW'],1): r for r in s1}
s2_by = {round(r['RoW'],1): r for r in s2}
common = sorted(set(s1_by.keys()) & set(s2_by.keys()))
if common:
    for k in common:
        a1 = s1_by[k]['angle']; a2 = s2_by[k]['angle']
        print(f"  R/W={k}: sweep1={a1:.2f}, sweep2={a2:.2f}, diff={abs(a1-a2):.2f}")
    diffs = [abs(s1_by[k]['angle']-s2_by[k]['angle']) for k in common]
    print(f"  max|sweep1-sweep2| at matched R/W = {max(diffs):.2f} deg")
else:
    print(f"  no exact R/W match between sweeps (s1 R/W: {sorted(s1_by)}, s2 R/W: {sorted(s2_by)})")

print()
print("=== STAGE11 VERDICT ===")
# decisive: does error drop below 2 deg at smallest W/R in either sweep?
all_ok = s1 + s2
if all_ok:
    best = min(all_ok, key=lambda r: abs(r['angle']-TARGET))
    print(f"best case: {best['name']}, R/W={best['RoW']}, angle={best['angle']:.2f}, err={best['angle']-TARGET:+.2f}")
    if abs(best['angle']-TARGET) < TOL:
        print(f"REDIRECT: error < {TOL} deg achievable by reducing W/R. Pivot to IntWidth/mesh/radius selection.")
    else:
        # check scaling trend
        if len(s1) >= 2 and len(s2) >= 2:
            s1_mono = all((s1[i]['angle']-TARGET) >= (s1[i+1]['angle']-TARGET) for i in range(len(s1)-1))
            s2_mono = all((s2[i]['angle']-TARGET) >= (s2[i+1]['angle']-TARGET) for i in range(len(s2)-1))
            if s1_mono and s2_mono:
                print("PARTIAL: error decreasing with R/W in both sweeps but not below 2 deg yet. Trend supports W/R scaling; extrapolate cost.")
            else:
                print("REAUTHORIZE: error NOT consistently decreasing with W/R. Wall-surface BC design warranted.")
        else:
            print("INCONCLUSIVE: not enough converged cases.")
else:
    print("REAUTHORIZE or INCONCLUSIVE: no converged cases to assess scaling.")
