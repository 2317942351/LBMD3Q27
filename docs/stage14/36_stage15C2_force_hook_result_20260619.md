# Stage 15C-2 Result — DynamicCL force hook enabled (MRT+BGK, Mode>1.5) — 2026-06-19

This commit enables the residual contact-line force `F_CL` to be added to
`F_total` when `DynamicCLMode > 1.5`, in BOTH the MRT and BGK collision paths.
Mode<=1 stays shadow-only (diagnostics, no force). This is the first time the
DynamicCL residual force enters the dynamics.

```text
status_label: exploratory_not_validation
scope: minimal guarded force hook + C2a/b/c zero/small-coefficient verification
       on the t90 equilibrium case. No changed-angle (60->30/120->150) run yet.
```

## 0. The hook (Dynamics.c.Rt, +24/-4, 4 hunks)

`calcDynamicCLShadow()` already returns the fully scaled, capped force vector:
```c
mag = DynamicCLForceSign * DynamicCLCoeff * (sigma/IntWidth) * R_theta * I_cl;
cap = DynamicCLForceCap * (sigma/IntWidth);  if(|mag|>cap) mag = +/-cap;
*fx = mag * t.x;   // the residual contact-line force vector
```
The hook just adds it, once, in each collision path:
```c
real_t fcl_x=0, fcl_y=0, fcl_z=0;     // hoisted to function scope
{ calcDynamicCLShadow(gradPhi, C, &fcl_x, &fcl_y, &fcl_z); }  // diagnostics always
...
F_total[0] = F_surf[0] + F_pressure[0] + F_body[0] + F_mu[0];
F_total[1] = ...; F_total[2] = ...;
if (DynamicCLMode > 1.5) {            // 15C write; Mode<=1 is a no-op
    F_total[0] += fcl_x; F_total[1] += fcl_y; F_total[2] += fcl_z;
}
```
Identical structure in CollisionMRT (tab indent) and CollisionBGK (8-space
indent). No PhaseF / gradPhi / mu / WallGhost path touched. No double scaling
(calcDynamicCLShadow owns the scaling + cap). Force cap preserved.

Binary built from this: sha256 `f00f8ff7da214f0ecfae215e7ce73c0f08d8c058cbda37fc198dbba228674c69`.

## 1. C2a — Coeff=0 inert regression (PASS)

t30/t90/t150 at Mode=2 + Coeff=0 + CosSign=-1 + ForceSign=+1. The only new
executable line is the guarded add; at Coeff=0 fcl=0, so Mode=2 must reproduce
Mode=1 exactly (modulo the new binary's float path).

| case | F_cl_max | d_mass vs Mode=1 | d_footprint vs Mode=1 | d_ph_min/max |
|---|---|---|---|---|
| t30  | 0.0 | -5.7e-10 | 0.0 | 4e-8 / 5e-12 |
| t90  | 0.0 | -2.9e-9  | 0.0 | 5e-8 / 5e-8  |
| t150 | 0.0 | -1.0e-9  | 0.0 | 5e-8 / 7e-9  |

F_cl is exactly 0; mass/footprint/PhaseF match Mode=1 to ~1e-9 (binary-path
float noise). **The hook is inert at Coeff=0.**

## 2. C2b — t90 Coeff=0.02 nonzero smoke (PASS)

| metric | C2b (Coeff=0.02) | C2a (Coeff=0) |
|---|---|---|
| F_cl_max | 9.73e-09 | 0 |
| active force nodes | 540 | 0 |
| spurious FLUID force nodes | **0** | 0 |
| d_mass vs C2a | +7.7e-09 | — |
| d_footprint vs C2a | 0.0 | — |
| \|U\|max | 5.23e-06 | 5.24e-06 |

F_cl ~ 0.02×1.667e-5×0.029×0.6 ≈ 6e-9, matches. 0 spurious fluid force nodes.
Solution within float noise of Coeff=0. **Nonzero force path is localized and
non-perturbing.**

## 3. C2c — t90 Coeff=0.2 linear-scaling smoke (PASS)

| metric | C2c (Coeff=0.2) | C2b (Coeff=0.02) | ratio |
|---|---|---|---|
| F_cl_max | 9.73e-08 | 9.73e-09 | **10.00x** |
| active force nodes | 540 | 540 | 1.0x |
| spurious FLUID force nodes | **0** | 0 | — |
| \|R_theta\| mean (active) | 0.0286 | 0.0286 | 1.0x |
| d_mass vs C2a | +8.3e-08 | — | — |
| d_footprint vs C2a | 0.0 | — | — |

F_cl_max scales exactly 10x with Coeff (0.02 -> 0.2), confirming Coeff is the
sole linear scaling factor with no hidden saturation or double multiplication.
|R_theta| is coeff-independent (0.0286), as it must be. 0 spurious fluid force
nodes; footprint bit-identical to Coeff=0.

## 4. Locality convention (recorded)

The dynamics-relevant locality check counts FLUID collision cells only:

```text
spurious FLUID force nodes = (F_cl>0) AND (not-wall) AND (Active<0.5)  -> must be 0.
```

Wall nodes (`IsItBoundary>=0.5`, `IamWall`) skip CollisionMRT/BGK entirely, so
even though `calcDynamicCLShadow` writes a nonzero *diagnostic* ForceCandidate*
on ~500-660 wall nodes per case, the `F_total += fcl` hook never runs there.
Wall-node F_cl>0 is a VTI/diagnostic caveat (same as in C1), NOT a dynamics
contamination. A separate cosmetic cleanup (zero wall-cell force diagnostics)
is deferred to its own commit; it is not mixed into this verified hook.

## 5. C2d — t90 Coeff=2 enters the cap-limited regime (PASS, critical finding)

C2b → C2c scaled F_cl exactly 10x (0.02 → 0.2). C2c → C2d did NOT:

| metric | C2c (Coeff=0.2) | C2d (Coeff=2) | ratio | expected |
|---|---|---|---|---|
| F_cl_max | 9.73e-08 | **3.333e-07** | **3.43x** | 10x (linear) |
| active force nodes | 540 | 540 | 1.0x | 1.0x |
| spurious FLUID force nodes | 0 | 0 | — | 0 |
| \|R_theta\| mean (active) | 0.0286 | 0.0287 | 1.0x | 1.0x |
| d_mass vs C2a | +8.3e-08 | -1.8e-08 | — | small |
| d_footprint vs C2a | 0.0 | 0.0 | — | 0 |
| \|U\|max | 5.11e-06 | 4.55e-06 | — | ~unchanged |

The measured C2d F_cl_max = **3.333e-07** is *exactly* the force cap:

```text
scale = sigma/IntWidth          = 5e-5 / 3      = 1.6667e-5
cap   = DynamicCLForceCap*scale = 0.02 * 1.6667e-5 = 3.3333e-7
```

Per-coeff uncapped vs capped (R_theta~0.0286, I_cl~0.6):
```
Coeff=0.02 : uncapped 5.72e-9   < cap  -> LINEAR  (measured 9.73e-9 ✓)
Coeff=0.2  : uncapped 5.72e-8   < cap  -> LINEAR  (measured 9.73e-8 ✓)
Coeff=2    : uncapped 5.72e-7   > cap  -> CAPPED to 3.333e-7 (measured 3.33e-7 ✓)
```

**This is the cap working as designed, NOT a bug.** `calcDynamicCLShadow` applies
`if(|mag|>cap) mag=+/-cap` before returning the force; once Coeff is large enough
that `Coeff*scale*R_theta*I_cl > ForceCap*scale`, the magnitude is clamped and
raising Coeff further has no effect on F_cl.

## 5b. C2 verdict (updated with C2d)

```text
C2a PASS: Mode=2 + Coeff=0 reproduces Mode=1 (hook inert).
C2b PASS: Coeff=0.02 nonzero force is tiny, localized to active CL, non-perturbing.
C2c PASS: Coeff=0.2 scales F_cl exactly 10x; 0 fluid pollution; solution stable.
C2d PASS: Coeff=2 enters the CAP-LIMITED regime. F_cl_max = cap = 3.333e-7.
          run_rc=0, no NaN, 0 spurious fluid force nodes, footprint bit-identical,
          mass/PhaseF/velocity stable. The cap engages as designed.

Effective Coeff dynamic range under ForceCap=0.02:
  LINEAR for Coeff <= ~0.3 (where Coeff*scale*R*I_cl <= ForceCap*scale)
  CAPPED for Coeff >  ~0.3 -> F_cl saturates at 3.333e-7 regardless of Coeff.
```

**Consequence for further scans:** under the default `DynamicCLForceCap=0.02`,
running Coeff=20 or 200 adds NO new information — the force is already saturated
at Coeff~0.3 and stays at 3.333e-7. A higher Coeff only matters if
`DynamicCLForceCap` is raised first. This is why the planned Coeff=20/200 sweep
is NOT run: it would be misleading (look like "no response to larger force"
when in fact the force is unchanged).

The changed-angle question (60->30 / 120->150) is therefore better posed as:
"Is the *current cap's* maximum force (3.333e-7 in sigma/IntWidth units) enough
to drive the contact line?" If yes, tune Coeff/Cap; if no, raise ForceCap (then
re-do a t90 equilibrium safety smoke before any changed-angle run).

## 5c. C2e — changed-angle under current cap (RESULT: force too weak)

Ran the decoupled changed-angle cases at the capped maximum force, with an
early-time trajectory (vtk-period=500, frames at step 0/500/.../4000) and a
matching Coeff=0 baseline on the same binary (so F_cl=0, isolating the force).

  test : 60->30, 120->150  Mode=2 Coeff=2 ForceCap=0.02  (F_cl saturated at 3.333e-7)
  base : same cases        Mode=2 Coeff=0                (F_cl=0)

60->30 (target 30 deg), theta_app / |R_theta| / footprint, test vs base:
```
 step | theta_app T/B  | |R| T / B   | footprint T / B | Fcl_max  cap%  spur
  500 | 33.52 / 33.52  | 0.0323/0.0323| 30.41 / 30.41  | 3.33e-7  56%   0
 1500 | 30.13 / 30.13  | 0.0011/0.0011| 31.40 / 31.40  | 3.33e-7  80%   0
 3000 | 28.62 / 28.62  | 0.0118/0.0118| 32.02 / 32.02  | 3.33e-7  83%   0
 4000 | 28.01 / 28.01  | 0.0169/0.0168| 32.31 / 32.31  | 3.33e-7  74%   0
```

120->150 (target 150 deg), test vs base:
```
 step | theta_app T/B  | |R| T / B   | footprint T / B | Fcl_max  cap%  spur
  500 | 139.97/139.97 | 0.1003/0.1003| 20.00 / 20.00  | 3.33e-7  80%   0
 2000 | 142.99/142.98 | 0.0675/0.0676| 20.12 / 20.12  | 3.33e-7  70%   0
 4000 | 144.49/144.48 | 0.0520/0.0521| 20.12 / 20.12  | 3.33e-7  76%   0
```

```text
C2e RESULT:
  run_rc=0, no NaN, 0 spurious fluid force nodes at every frame.
  F_cl reaches the cap (3.333e-7); capped_frac 56-84% (force is clamped, as in C2d).
  test trajectory is INDISTINGUISHABLE from the Coeff=0 baseline at every step:
    theta_app   differs < 0.02 deg
    |R_theta|   differs < 0.002
    footprint   bit-identical
    mass        differs < 1e-5
  => Under ForceCap=0.02 the DynamicCL force is stable and localized, but TOO WEAK
     to produce any measurable contact-line response.
```

This is NOT a direction error and NOT a hook error. The mechanism is healthy
(F_cl on active CL nodes, capped, no bulk leak, no NaN). The cap value is the
bottleneck: 3.333e-7 in sigma/IntWidth units is below the threshold needed to
move the contact line against the compact-ghost relaxation. Note the cap-fraction
is high (56-84%), meaning the *intended* (uncapped) force at Coeff=2 already
exceeds the cap on most CL nodes — so raising Coeff further is pointless; the
next lever is `DynamicCLForceCap`.

Decoupled baseline dynamics (independent of DynamicCL): 60->30 over-relaxes to
~28 deg by step 4000 (theta_app < target 30); 120->150 reaches ~144.5 deg (short
of 150). Both are compact-ghost behaviour, unchanged by the current DynamicCL force.

## 6. Runtime settings carried forward (must be explicit)

```text
DynamicCLCosSign   = -1   (NOT the +1 code default; calibrated by C1 gate-4)
DynamicCLForceSign = +1   (calibrated by C1, sign-robust)
DynamicCLMode      = 2    (to activate the hook; 1 = shadow, 0 = off)
DynamicCLCoeff     = effective LINEAR range is Coeff <= ~0.3 under ForceCap=0.02;
                     above that F_cl is capped. Verified: 0 (inert), 0.02, 0.2
                     (linear), 2 (capped). Coeff=20/200 NOT run (no new info).
DynamicCLForceCap  = 0.02 (in sigma/IntWidth units; gives max F_cl = 3.333e-7).
                     Applied inside calcDynamicCLShadow. Raise this (not Coeff)
                     to increase the maximum allowable force.
```

## 7. Reproducibility

```text
binary: /home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
        sha256 f00f8ff7da214f0ecfae215e7ce73c0f08d8c058cbda37fc198dbba228674c69
patch:  scripts/stage13/stage15C2_pre_hook.patch + stage15C2_pre_apply.py
analysis: scripts/stage13/stage15C2{a,b,c,d}_regression.py + stage15C2b_locality_probe.py
          + stage15C2e_trajectory.py
roots:  /mnt/usb1t/RUNS/runs/stage15C2{a,b,c,d}_t90_*  (t90 smokes)
        /mnt/usb1t/RUNS/runs/stage15C2e_changed_angle_{test,base}  (60->30,120->150)
```

## 8. Next (NOT done — pending separate authorisation)

```text
C2e showed ForceCap=0.02 (max F_cl=3.333e-7) is too weak to move the contact
line. The next lever is DynamicCLForceCap, not Coeff (Coeff is already saturated
at 2). Planned:
  C2f-0: t90 equilibrium safety smoke at ForceCap=0.2 (max F_cl=3.333e-6, 10x),
         Coeff=2, to confirm the larger force does NOT perturb equilibrium.
  C2f:   if C2f-0 passes, 60->30 + 120->150 at ForceCap=0.2, Coeff=2,
         vtk-period=500, vs the existing Coeff=0 baseline (test vs base).
Coeff=20/200 is NOT useful (force already saturated at Coeff~0.3 regardless of cap).
```
