# Stage 15C-4 / 15C-5 Result — C3 amplitude sweep + C4 mobility audit => pivot to WallGhostV2 — 2026-06-20

This doc records the two parallel lines run on 2026-06-20 (C3: ForceCap=0.5
amplitude; C4: eq30 mobility sweep) and the strategic decision they force:
**DynamicCL amplitude tuning is NOT the path to close the flat-wall gate.
The bottleneck is the compact-ghost static WallGhost wetting boundary, which
maps the prescribed contact angle incorrectly (eq30 target 30 -> measured 24).**
DynamicCL is demoted to a later dynamic-correction layer. Main line pivots to
Stage 15D (static WallGhost root-cause) then Stage 16 (WallGhostV2 refactor).

```text
status_label: exploratory_not_validation
scope: runtime sweeps on the committed hook binary f00f8ff7; no source change;
       no push. These runs CLOSE the DynamicCL-amplitude question (negatively)
       and motivate the WallGhostV2 pivot.
binary sha256: f00f8ff7da214f0ecfae215e7ce73c0f08d8c058cbda37fc198dbba228674c69
commit (this doc): see git log; branch stage15-dynamicCL-residual (local only)
```

## 1. C3 — ForceCap=0.5 amplitude (gpu1), FS=-1, Coeff=2, CosSign=-1, IntWidth=3, M=0.3

Run root: `/mnt/usb1t/RUNS/runs/stage15C3_cap0p5_20260619`

### 1a. Safety gate (eq30 / t90 / eq150) — PASS
Gate: NaN=0, spurious-FLUID force nodes=0 (|Fcand|>0 & active<0.5 & IsItBoundary<0.5),
eq30/eq150 not further from target than Coeff=0 baseline.

| case | base (Co=0) θ_app@4000 | cap=0.5 θ_app@4000 | Δ | capped% | spur_fluid |
|---|---|---|---|---|---|
| eq30  | 23.71 | 23.74 | +0.03 | 0 | 0 |
| t90   | 88.36 | 88.37 | ~0    | 0 | 0 |
| eq150 | 149.05 | 149.32 | +0.27 (toward 150) | 0 | 0 |

cap=0.5 does not destabilise equilibrium; force is below cap (capped%=0, max|Fcand|~1.7e-6 < cap 8.33e-6).

### 1b. Changed-angle — NOT improved; obtuse REGRESSES vs cap=0.2

| case | base θ@4000 | cap=0.2 (FS=-1) | cap=0.5 (FS=-1) | trend |
|---|---|---|---|---|
| 60->30  | 28.01 | 27.99 | **27.998** | flat (acute over-relax unaffected) |
| 120->150 | 144.48 | 145.35 | **144.56** | **regressed** back near base |

cap=0.5 max|Fcand| at 120->150 step500 = 3.90e-6 (vs cap=0.2 ~3.33e-6; stronger, still below cap).
The response is NON-MONOTONIC: a small force (cap=0.2) helps 120->150 by +0.87 deg,
a stronger force (cap=0.5) collapses the benefit to +0.08 deg. **Stronger force != closer to target.**

### 1c. C3 verdict
ForceCap 0.2 -> 0.5 does NOT "obviously strengthen the restoring effect". Per the
pre-registered criterion this is a NEGATIVE result. DynamicCL is correct-signed,
stable, localised, but CANNOT drive the contact line to target. Do not sweep cap=1.0/2.0
(non-monotonic trend says it is unproductive; also excluded from this round by plan).

## 2. C4 — eq30 mobility sweep (gpu2), Coeff=0 (DynamicCL off), IntWidth=3, M=0.1/0.3/0.6

Run root: `/mnt/usb1t/RUNS/runs/stage15C4_Msweep_20260619`

| M | eq30 θ_app@4000 | deviation from 30 | NaN | mass drift |
|---|---|---|---|---|
| 0.1 | 24.12 | -5.9 | 0 | -198 |
| 0.3 | 23.65 | -6.4 | 0 | -183 |
| 0.6 | 23.34 | -6.7 | 0 | -179 |

A 6x change in M moves the settled angle by only ~0.8 deg, and NOT toward 30
(if anything higher M is slightly worse). All three settle at ~24 deg.

### 2a. C4 verdict (per pre-registered criteria)
- M does NOT bring eq30 closer to 30 => the offset is NOT a mobility / contact-line
  relaxation problem.
- All runs stable, no oscillation, no abnormal mass drift at high M.
- => The eq30 6 deg offset is the **compact-ghost static WallGhost boundary itself
  settling at the wrong angle**, not dynamics.

This matches the repo's earlier expert root-cause packet: failures are controlled by
the curved-wall profile / unified wall PhaseF reconstruction / near-wall geometry
contract, not by bulk phase-field, zonal radAngle, outer-wall leakage, or M.

## 3. Combined conclusion (the two lines corroborate each other)

```text
C4: eq30=24 is static-BC, not mobility (M-independent).
C3: a correct-signed, stable, localised DynamicCL body force CANNOT overcome the
    static BC; more force is non-monotonic / slightly harmful.
=> The compact-ghost static WallGhost wetting boundary is the bottleneck.
=> DynamicCL is demoted to a LATER dynamic-correction layer (Stage 16E), NOT the
   primary repair. Main line pivots to WallGhostV2.
```

This realisation is the reason Stage 15C (DynamicCL) stops here. The DynamicCL
work is NOT wasted: CosSign=-1, ForceSign=-1, the guarded hook, the t90 safety
discipline, and the gate machinery are all reusable once the static BC is correct.

## 4. What is SETTLED vs OPEN after Stage 15C

```text
SETTLED:
  DynamicCLCosSign=-1, DynamicCLForceSign=-1 (doc 38).
  DynamicCL hook (47a6d22, binary f00f8ff7) is code-verified (C2a-d) and
  direction-verified (doc 38). It is a correct restoring force.
  DynamicCL amplitude tuning will not close the flat-wall gate.
  eq30 24 deg offset is static-BC-dominated, M-independent.
OPEN / NEXT:
  WHY does compact-ghost static WallGhost settle at 24 deg for target 30?
  (Stage 15D: measurement cross-check + target-angle mapping + IntWidth scan +
   WallGhost implied-angle audit; no source change.)
  Then Stage 16: WallGhostV2 refactor (PRE free-energy candidate + equilibrium-
  profile extension candidate), flat-wall static gate, then re-connect DynamicCL.
```

## 5. Discipline notes (adhered)

- No source change in this stage. No push. No WallGradMode/WallMuMode >= 2.
- No cylinder/sphere. No high-We.
- Every run bound: binary f00f8ff7, FS=-1/CosSign=-1, Coeff/Cap/M/IntWidth explicit,
  VTK field list verified (analyze3 read DynamicCL*, IsItBoundary, PhaseField).
- spurious-FLUID-force-node gate implemented via IsItBoundary<0.5 mask (=0 on all runs).
- Status remains exploratory_not_validation throughout.

## 6. Reproducibility

```text
# C3 (cap=0.5): generate eq+decoupled, inject cap=0.5, safety gate then changed-angle
bash /home/yuan/c3.sh
# C4 (M sweep): eq30 Coeff=0 at M=0.1/0.3/0.6
bash /home/yuan/c4.sh
# analyzer (rich): step th_app |R| NaN n_act sumPhaseF foot max|Fcand| capped% spur_fluid
python3 /home/yuan/analyze3.py <case_dir> <target> <cap>
scripts mirrored locally: repo/scripts/stage13/{c3.sh->outputs_c3.sh, c4.sh->outputs_c4.sh,
  analyze3.py, read_cl_traj.py, gate_c1_force_dir.py}
```
