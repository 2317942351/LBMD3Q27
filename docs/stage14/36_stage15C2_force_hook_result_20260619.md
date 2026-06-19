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

## 5. C2 verdict

```text
C2a PASS: Mode=2 + Coeff=0 reproduces Mode=1 (hook inert).
C2b PASS: Coeff=0.02 nonzero force is tiny, localized to active CL, non-perturbing.
C2c PASS: Coeff=0.2 scales F_cl exactly 10x; 0 fluid pollution; solution stable.
=> the guarded F_CL hook is verified in the safe regime (t90, Coeff up to 0.2).
```

Not yet done: Coeff 2/20/200, and the changed-angle response (60->30 / 120->150)
which is the actual physics target. Those proceed under separate authorisation,
each as a small step, on top of this committed hook.

## 6. Runtime settings carried forward (must be explicit)

```text
DynamicCLCosSign   = -1   (NOT the +1 code default; calibrated by C1 gate-4)
DynamicCLForceSign = +1   (calibrated by C1, sign-robust)
DynamicCLMode      = 2    (to activate the hook; 1 = shadow, 0 = off)
DynamicCLCoeff     = scan (verified 0, 0.02, 0.2; 2/20/200 pending)
DynamicCLForceCap  = 0.02 (in sigma/IntWidth units; applied inside calcDynamicCLShadow)
```

## 7. Reproducibility

```text
binary: /home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
        sha256 f00f8ff7da214f0ecfae215e7ce73c0f08d8c058cbda37fc198dbba228674c69
patch:  scripts/stage13/stage15C2_pre_hook.patch + stage15C2_pre_apply.py
analysis: scripts/stage13/stage15C2{a,b,c}_regression.py + stage15C2b_locality_probe.py
roots:  /mnt/usb1t/RUNS/runs/stage15C2{a,b,c}_t90_*
```
