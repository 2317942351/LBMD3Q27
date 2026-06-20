# Project state — comprehensive analysis & handoff — 2026-06-20

Definitive state-of-project after the 2026-06-19/20 session (15 commits, docs
38-52). Written as the rigorous synthesis the work demands, and the handoff for
the next phase (curved-wall wetting BC). All results exploratory_not_validation
unless a gate is explicitly stated as passed.

## 1. The project

TCLB D3Q27 conservative phase-field LBM (`d3q27_pf_velocity`), Fakhari/Mitchell
high-density-ratio route. Goal: correct static contact angle (theta within +/-2
deg) on plane/cylinder/sphere walls, reusable later for dynamic droplet impact on
a staggered cylinder array. Repo github 2317942351/LBMD3Q27, branch
stage15-dynamicCL-residual (LOCAL, not pushed). Compute on HM570 (yuan@192.168.1.16).

## 2. What is SETTLED (do not re-litigate)

```
A. The static contact-angle error on the FLAT wall is model-intrinsic and small.
   Calibrated bbox-h/a measurement (golden2.py, self-validated vs synthetic tanh
   caps) shows the compact-ghost BC reproduces theta=30..150 within +/-2.6 deg
   (eq30 32.3, eq45 45.0, eq60 62.2, eq90 89.8, eq120 121.4, eq135 137.6,
   eq150 149.8). [docs 40, 43] FLAT-WALL GATE: CLOSED.

B. DynamicCL (residual contact-line body force): sign fixed to ForceSign=-1
   (CosSign=-1), confirmed by the INDEPENDENT radial projection of the candidate
   force (gate_c1_force_dir.py), NOT by the ThetaApp diagnostic. The hook is
   code-verified (binary f00f8ff7). But it has ZERO net macro effect on contact-
   line relaxation (base == cap 0.2 == cap 0.5). [docs 38, 40] It is a correct
   but ineffective lever in this regime; shelved, not the path.

C. Mobility M sets the contact-line relaxation RATE (not the equilibrium angle).
   M=0.6 ~2x faster than M=0.3. The "slow relaxation" is the chosen M operating
   point, not a defect. [doc 42]

D. The earlier "static BC is broken / WallGhostV2 pivot" conclusion (doc 39) was
   REVERSED (doc 40): it was an artefact of the un-calibrated DynamicCLThetaApp
   band-mean diagnostic. WallGhostV2 refactor is NOT needed.

E. The compact-ghost wetting BC is the validated wall-phase channel; WallGradMode
   and WallMuMode are diagnostic-only (never write). permissive.access=TRUE stays.
```

## 3. The ONE open frontier: curved-wall wetting BC (cylinder/sphere)

```
The compact-ghost BC that is validated on the flat wall does NOT transfer to
curved geometry:
- compact-stencil q_s WRITE NaNs on AnalyticCylinder (~step 250, 80% PhaseF NaN).
  [doc 46] Cause confirmed: the WRITE injection onto the staircase cylinder wall
  (WriteAllowedFlag=0 control is stable). [doc 49]
- gate-A fix (compact write gated to flat-only; analytic ghost on curves, commit
  43dab28, binary 341fb2fc): PARTIAL -- neutral/obtuse cylinder STABLE (theta=90
  runs 30k clean) but acute theta=60 still NaNs, and neutral reads ~115 vs 90
  (+25 deg). [docs 50, 51]
```

### Why both paths fail -- the structural root cause
Both the compact-stencil write and the analytic Briant ghost depend on PER-WALL-
NODE values on a JAGGED STAIRCASE cylinder mask (the `<Cylinder>` Wall zone is a
staircase approximation; it does NOT match the analytic cylinder SDF). The gradient
stencil reads PhaseF on those jagged wall nodes -> jagged near-wall gradient ->
acute instability and/or wrong macroscopic angle. The q_s MATH (bounded, strict
gate) is correct; the q_f selection already uses the analytic SDF. The failure is
purely the staircase WRITE TARGET.

A purely local q_w(theta) "smooth ghost formula" is UNDER-DETERMINED (the wall
value depends on the global contact-line position; the compact-stencil anchors it
via local q_f, which is the right idea). [doc 52] => option B is NOT a formula
swap; it is a BOUNDARY-SMOOTHING / NEAR-WALL-GRADIENT change.

## 4. Candidate option-B approaches (ranked, with the deciding experiment each needs)

```
B-i. Diffuse solid indicator (psi): replace the sharp staircase mask with a
     diffuse solid field; the near-wall gradient becomes smooth by construction.
     Most principled; largest change (Dynamics.R + the wetting path). The LBM_Saclay
     psi/varphi idea (doc 34) is the reference; needs redesign against the live
     compact-stencil code (the doc-34 pack targeted the wrong snapshot).
B-ii. Analytic near-wall gradient: keep the staircase mask but make the gradient
     stencil near the wall read the ANALYTIC equilibrium profile (from the SDF),
     not the stored jagged PhaseF. Moderate change in calcGradPhi / the force path.
B-iii. Resolution/mask-quality: test whether a LARGER or finer cylinder mask
     (less relative staircase jaggedness) restores stability with the existing
     compact-stencil write. Cheapest diagnostic -- if R=30/40 cylinder is stable,
     it confirms jaggedness is the cause and bounds the problem.
```

## 5. Binaries / artifacts

```
f00f8ff7 : original (flat-wall validation, docs 40-43).
341fb2fc : gate-A (compact write flat-only; cylinder neutral/obtuse stable).
           compile tree /home/yuan/src/TCLB_lbm2026_compile_lane has gate-A applied.
Trusted measurers (repo/scripts/stage13/): golden2_calibrated_angle.py (flat),
  golden_cyl_curved_angle.py (cylinder, +/-4 deg), gate_c1_force_dir.py (force dir).
Run roots: /mnt/usb1t/RUNS/runs/stage15D_* (flat), stage17_* (cylinder).
```

## 6. Immediate next work (B1, offline, safe, no server compute)

The mandatory gate before ANY curved-wall dynamics edit:
```
B1. Decide the option-B approach by the deciding experiments:
    - run B-iii (compact-stencil write on a larger cylinder R=30/40) to confirm
      jaggedness is the cause and bound it;
    - on synthetics (golden_cyl), prototype B-i (does a diffuse-solid-smoothed
      indicator give a clean gradient field?) and B-ii offline.
    Lock the approach + the sign convention against known-truth synthetics BEFORE
    editing TCLB. This prevents a stable-but-wrong BC (the project's recurring
    failure mode, docs 40/47) slipping past the +/-4 deg measurer.
```

## 7. Recommendation
Push the 15-commit milestone now (secures flat-wall validation + cylinder partial
stabilisation + the structural curved-wall finding + the first source fix). Then
B1 (offline) -> B2 (shadow) -> B3 (write) -> B4 (audit) per doc 52.
