# DynamicCL Stage 15B — cos_eq source fix + activation gate tightening

Date: 2026-06-18 (verified 2026-06-19)
Branch: `stage15-dynamicCL-residual`
Status: `Stage15B: PASS for theta_eq sourcing and wetting-wall locality.
        NOT a physical-validation pass — the residual gate (gate 4) is blocked
        by the uncalibrated cos_app sign convention (DynamicCLCosSign).
        Stage15B code fix is verified; DynamicCL residual model has not yet
        passed equilibrium-residual=0. Next stage: Stage15C-pre sign
        calibration (shadow-only, DynamicCLMode=1 preserved, DynamicCLForceSign
        untouched).`

This records the fix to the two substantive bugs found in the Stage 15B
shadow diagnostic (commit `60a345d`). Both were diagnosed from the
`DynamicCLCosEq` field reading `[0.]` for the t30 case, which contradicts the
prescribed 30 deg target.

## 1. Bug A — `cos_eq = cos(radAngle)` reads the wrong angle

### Symptom
`DynamicCLCosEq unique = [0.]` for the t30 case. cos(30 deg) = 0.866, not 0,
so the equilibrium reference angle was wrong.

### Root cause
`radAngle` is declared as a **zonal** setting
(`Dynamics.R:393` `AddSetting(name="radAngle", ..., zonal=T)`). The flat-wall
case (`stage13_flat_wall_diagnostic_run.py:246-266`) only sets the target
angle in the `FlatLowerY` wall zone (y=0):

```text
radAngle = 90d                 # global default
radAngle = 90d zone=OuterDomain
radAngle = 30d zone=FlatLowerY   # ONLY the y=0 wall
```

`calcDynamicCLShadow` runs on **fluid** nodes (the function returns early on
`IamWall || IamSolid`). Fluid nodes (y>=1) are not in `FlatLowerY`, so the
bare symbol `radAngle` resolved to the **global default 90 deg (pi/2)**, giving
`cos_eq = cos(pi/2) = 0`.

The compact-ghost path in `Boundary.c.Rt` is correct because it runs on the
wall node itself (`if (IamWall || IamSolid)` block) and reads its own
zone-resolved `radAngle`. That path additionally stores the resolved angle
into the `LocalRadAngle` field (`Boundary.c.Rt:1709` etc.).

This was NOT a sign-convention bug. `DynamicCLCosSign` is left unchanged; it
must only be calibrated after `theta_eq` is sourced correctly.

### Fix
`calcDynamicCLShadow` no longer reads `radAngle` directly. It calls a new
helper, `stage15_find_wetting_wall_context`, which locates an adjacent
**wetting** wall node and reads that wall node's `LocalRadAngle`. The wall
node was populated by `calcWallPhase` with its own (correct) zone-resolved
angle, so `theta_eq` inherits the right value. No fallback to the local
zonal `radAngle` is permitted: failing to find a wetting-wall neighbour
blocks the node instead, to avoid silently reintroducing the 90 deg
reference.

## 2. Bug B — `stage13_is_fluid_boundary_node()` gate is too wide

### Symptom
`DynamicCLActive` spread to rows well outside the contact-line band
(reported as y=2,6,14,20,32,49,57,70 on the t30 case), including
outer-domain-wall skin.

### Root cause
The old gate was "any of my 6 face neighbours is a boundary node"
(`IsBoundary > 0`). `OuterDomain` is a `<Wall>` covering all six outer skins
of the 96x80x96 domain, so any fluid node touching x=0/95, y=79, or z=0/95
skin passed the gate. These are not contact-line nodes.

`LocalRadAngle` alone cannot distinguish `FlatLowerY` (30 deg) from
`OuterDomain` (90 deg), because both wall zones populate it. The reliable
discriminator is `AnalyticFlag`: it is set to 1 only on wall nodes close to
the analytic solid surface (`Boundary.c.Rt:1704`, within
`d_to_surface < 1.5` of the analytic y=0 plane). OuterDomain vertical walls
are far from that plane, so their `AnalyticFlag = 0`.

### Fix
The DynamicCL gate is replaced by `stage15_find_wetting_wall_context`,
which requires the neighbouring wall node to satisfy all of:
- `IsBoundary > 0.5`
- `AnalyticFlag > 0.5`  (rejects OuterDomain)
- `LocalRadAngle` finite and in (1e-6, pi-1e-6)  (rejects unpopulated / 0)

Search order: 6 face neighbours first (sufficient and cheapest for the flat
wall), then the remaining 20 nodes of the 26-neighbour ring (reserved for
future curved-surface compact-stencil support).

The contact-line band gate `DynamicCLEpsQ < q < 1-DynamicCLEpsQ` is kept and
now also feeds a distinct `DynamicCLBlockedReason` code, so pure-liquid and
pure-gas near-wall nodes are excluded even when they have a valid
wetting-wall neighbour.

## 3. Code changes

```text
Dynamics.R:
  + AddField/AddQuantity: DynamicCLThetaEq, DynamicCLWallContextFound,
    DynamicCLBlockedReason, DynamicCLWallDx/Dy/Dz
    (all group="wall_grad_diag", consistent with existing DynamicCL fields)

Dynamics.c.Rt:
  + stage15_neighbor_is_wetting_wall(dx,dy,dz)
  + stage15_find_wetting_wall_context(&theta, &dx, &dy, &dz)
  + forward declarations before calcDynamicCLShadow
  + getters getDynamicCLThetaEq / WallContextFound / BlockedReason / WallDx/Dy/Dz
  ~ calcDynamicCLShadow:
      stage13_is_fluid_boundary_node()  -> stage15_find_wetting_wall_context()
      cos(radAngle)                     -> cos(theta_eq from wall context)
      q-band gate                       -> kept, distinct blocked-reason code
```

`stage13_is_fluid_boundary_node()` itself is UNCHANGED; it is still used by
`calcGradPhiBoundaryCorrected` and `calcWallMuSource`. Only the DynamicCL
path stops using it.

## 4. Verification done (local, no compile yet)

- `git diff --check`: clean (no whitespace errors).
- Bracket balance (paren/brace/bracket) verified equal on both files.
- All 6 new DynamicCL fields have: assignment site + getter + AddField +
  AddQuantity. No field is written without being declared.

## 5. Verification status

Do NOT promote past `exploratory_not_validation` without gate 4 passing.

```text
gate 1 (compile):   COMPLETE (see §8.3). nvcc clean, binary e2a10d0e.
gate 2 (cos_eq):    PASS. flat-wall 30/90/150 DynamicCLMode=1 shadow, 1000 steps:
    theta030 DynamicCLCosEq unique = [+0.866]   (cos 30 deg, all active nodes)
    theta090 DynamicCLCosEq unique = [0.000]    (cos 90 deg)
    theta150 DynamicCLCosEq unique = [-0.866]   (cos 150 deg)
    DynamicCLThetaEq unique per case = [0.5236]/[1.5708]/[2.618] (pi/6, pi/2, 5pi/6)
    -> theta_eq is correctly sourced from the adjacent FlatLowerY wall's
       LocalRadAngle, NOT the fluid node's own zonal radAngle (90 deg).
       Bug A (cos_eq=0) is fixed.
gate 3 (locality):  PASS (with VTI-display caveat, see §9). t30 4740 active
    nodes: their DynamicCLThetaEq is uniquely [0.5236]=30 deg. No node reads
    the OuterDomain 90 deg. DynamicCLBlockedReason=2 (no wetting wall) blocked
    713580 of 737280 cells. Bug B (gate too wide) is fixed.
gate 4 (residual):  BLOCKED. mean|DynamicCLCosResidual| is currently ~1.79
    because cos_app has the wrong sign (cos_app ~ -0.92 for t30, i.e.
    theta_app ~ 157 deg) which is a DynamicCLCosSign calibration issue, NOT a
    theta_eq-source issue. Gate 4 is deferred until DynamicCLCosSign is
    calibrated; sign calibration is out of scope for this commit.
```

Runtime verification was done on server lane `192.168.1.16`, binary
`CLB/d3q27_pf_velocity_q27_geometric/main` (sha256 e2a10d0e...), runner
`stage13_flat_wall_diagnostic_run.py` with `--dynamic-cl-mode 1 --iterations
1000 --vtk-period 200 --mobility 0.3`, output under `/home/yuan/gate2_runs/`.
Diagnostic reader: `scripts/stage13/gate2_dynamiccl_diag.py` +
`gate3_context_probe.py` + `gate3_sixdir_probe.py`.

If gate 2 still yields cos_eq=0, then `LocalRadAngle` is not being read from
the wall neighbour correctly (e.g. the wall node never took the analytic
branch), and the wetting-wall-context helper must be re-audited — do NOT
revert to `cos(radAngle)`.

If gate 3 still shows activation on outer-domain skin, `AnalyticFlag` is not
a sufficient discriminator on some wall nodes; add a wall-type/path-id
discriminator. Do NOT loosen the band gate to hide it.

## 6. Explicitly NOT done in this change

- `DynamicCLCosSign` / `DynamicCLForceSign` left at defaults; calibrate only
  after gates 2-4 pass.
- `DynamicCLMode=2` (write force into F_total) still not enabled.
- No change to PhaseF / gradPhi / mu paths.
- No curved-surface (cylinder/sphere) DynamicCL run.

## 7. Latent same-class bug found (NOT fixed here, out of scope)

Static grep for `cos(radAngle)` after this fix showed the same zone-resolution
bug exists in two OTHER paths, not just DynamicCL:

```text
Dynamics.c.Rt:496  calcGradPhiBoundaryCorrected (Layer 1, WallGrad):
    gn_target_q = -WallGradContactSign * A_wet * cos(radAngle) * q * (1-q)
Dynamics.c.Rt:566  calcWallMuSource (Layer 2, WallMu):
    mu_wall = -WallMuScale * av * 6.0 * sigma * cos(radAngle) * q * (1-q)
```

Both run on FLUID nodes, so `radAngle` resolves to the global 90 deg default
off the `FlatLowerY` zone — identical root cause to Bug A.

Why this is NOT touched in this commit, and is safe to defer:
- `WallGradMode=2` (the path that returns the corrected gradient into the
  dynamics) is hard-refused by the runner (`stage13_flat_wall_diagnostic_run.py`
  Stage 15B-pre guard). mode<=1 only writes the diagnostic fields
  `WallGradDeltaMag` / `WallGradThetaApp`; it does not feed gradPhi.
- `WallMuMode` defaults to 0 and is not enabled in the 15B shadow run.
- Therefore neither path affects F_total, PhaseF, gradPhi, or mu in the
  current 15B gate, even though their `cos(radAngle)` is numerically wrong.

This is recorded so it is not lost. When WallGrad/WallMu are revisited (or
before any mode>=2 of either is re-enabled), they must be migrated to the
same `stage15_find_wetting_wall_context` theta_eq source as DynamicCL.
**Do not enable WallGradMode>=2 or WallMuMode>=2 before that migration.**

## 8. TCLB framework constraint discovered during compile (gate 1)

The first compile attempt failed twice, revealing two TCLB framework rules
that the initial `e72bf00` violated. Both were fixed before the binary built;
recording them here so the same mistakes are not repeated.

### 8.1 No forward declarations of CudaDeviceFunction members

`CudaDeviceFunction` functions are expanded by the RT code generator into
**member functions of a C++ template class** (`Node_Run<LA, Primal, G,
Stage>::...`). A C++ class member does not need (and cannot have) a separate
forward declaration inside the same class — adding one produced 44 nvcc
errors of the form `invalid redeclaration of member function
"Node_Run<...>::stage15_..." (declared at line N)`. Fix: delete the forward
declarations; in-class members may reference each other regardless of order.

### 8.2 Field-access macros require COMPILE-TIME CONSTANT offsets

`IsBoundary(dx,dy,dz)`, `AnalyticFlag(dx,dy,dz)`, `LocalRadAngle(dx,dy,dz)`
(and `PhaseF(dx,dy,dz)` etc.) expand to
`DynamicAccess<LatticeAccess<range_int<...>>>::load_*` template calls whose
offset is a **template parameter**. They therefore require **compile-time
constant** integer offsets. Passing a runtime loop variable or a function
`int` parameter produces nvcc errors `no instance of overloaded load_*
matches the argument list` / `expression must have a constant value`.

This is why the original `stage13_is_fluid_boundary_node` uses 6 literal
face-neighbour calls and nothing else. The first implementation of
`stage15_find_wetting_wall_context` added a 26-neighbour runtime loop (pass 2)
plus a variable-argument helper — both violated this rule (24 nvcc errors).

Fix: drop the 26-neighbour ring (it was only "reserved for future curved
support" and is not needed on the flat wall) and inline the three tests per
offset via a `#define STAGE15_CHECK_FACE(OX,OY,OZ)` macro (matching the
existing `STAGE13_PHASE_FOR_STENCIL` / `STAGE13_BOUNDARY_PHASE` macro pattern
already in the codebase), so every field access receives a literal offset.
`#undef` after use to avoid leaking the macro.

**Implication for future curved-surface DynamicCL**: any additional
neighbour offsets must be enumerated as literals (e.g. a second macro block
for edge/corner offsets), NOT via a loop. The compact-stencil curved-surface
work (Stage 4+) already handles its own geometry differently and does not go
through this helper.

### 8.3 Compile outcome

```text
server lane: /home/yuan/src/TCLB_lbm2026_compile_lane
binary:      CLB/d3q27_pf_velocity_q27_geometric/main
sha256:      e2a10d0e82b52d88b366c46d55852ddccf3a9ac5ca79c71339c30ca2fdd38d69
  (differs from 60a345d binary 8ab97df7..., confirming a fresh build)
codegen:     clean (stage15 helper + DynamicCLThetaEq present in generated
              Dynamics.c / Lattice.cu / cuda.cu; cos(radAngle) gone from the
              DynamicCL path; replaced by cos(theta_eq))
compile:     nvcc CUDA 12.6, -arch compute_60, 0 errors, exit 0
DynamicCLMode > 1.5 force-write: still commented only (line 1356 of generated
              Dynamics.c); Mode=1 shadow-only boundary preserved
```

gate 1 (compile) is COMPLETE. gates 2 and 3 PASSED at runtime (see §5).
gate 4 is BLOCKED pending DynamicCLCosSign calibration (see §9).

## 9. Gate 3 VTI-display caveat + cos_app sign issue (for future reference)

Two findings from the gate-3 runtime verification that are NOT bugs in this
commit, but must be recorded so they are not misread later.

### 9.1 VTI cell-data vs device node-data staggered offset

The first locality table (built from VTI cell-centered data, reshaped
(nz,ny,nx) per VTK's x-fastest ordering) showed DynamicCLActive cells
scattered across cell y = 1..77, which looked like a spurious spread. A
six-direction probe showed this is a **display artifact**, not physical
spread:

- All 4740 active nodes have DynamicCLThetaEq uniquely = [0.5236] = 30 deg.
  No node reads the OuterDomain 90 deg. If bulk nodes were truly (wrongly)
  activated, their theta_eq would be a mix of 30 deg and 90 deg; it is not.
- DynamicCLWallDy is uniquely [-1] over all active nodes, i.e. every active
  node found its wetting wall in the -y direction (towards y=0), exactly as
  expected for a flat wall. +x/-x/+y/+z/-z never match.
- IsItBoundary / AnalyticFlag / LocalRadAngle are stored as cell data in the
  VTI but read as node data by `AnalyticFlag(0,-1,0)` in the device code;
  the half-grid stagger between cell-center and node coordinates is what
  stretches the contact-line band across many cell-y rows when plotted.

Conclusion: gate 3 passes on the coordinate-independent criterion (theta_eq
identity). Any future plot of DynamicCLActive over (x,y,z) must account for
the cell/node stagger, or it will over-report the band width.

### 9.2 cos_app sign (DynamicCLCosSign calibration) — NOT done in this commit

For t30 equilibrium, the active nodes report DynamicCLCosApp in [-0.925,
-0.900] (i.e. theta_app ~ 157 deg), while DynamicCLCosEq = +0.866. Hence
DynamicCLCosResidual ~ +1.79, far from 0.

This is expected at this stage: DynamicCLCosSign (the convention mapping
the interface-normal / wall-normal dot product to cos_app) has not been
calibrated yet, and the plan explicitly defers sign calibration until after
theta_eq sourcing is verified. theta_eq sourcing is now verified (gate 2).
The next step would be DynamicCLCosSign calibration, then re-run gate 4.
That is a separate, explicitly-authorized change — do NOT touch
DynamicCLCosSign or DynamicCLForceSign as part of this commit.

### 9.3 Status summary

```text
Bug A (cos_eq=0, wrong theta_eq source):        FIXED, verified (gate 2).
Bug B (gate too wide, OuterDomain leakage):     FIXED, verified (gate 3).
DynamicCLMode=1 shadow-only boundary:           PRESERVED (gate 1 + code review).
DynamicCLCosSign calibration:                   NOT DONE (deferred).
DynamicCLMode=2 (force into F_total):           NOT ENABLED.
WallGrad/WallMu same-class cos(radAngle) bug:   RECORDED (§7), NOT FIXED.
```

This commit's scope (theta_eq source + wetting-wall gate) is complete and
runtime-verified for gates 1-3. Remaining work (sign calibration, gate 4,
mode 2) is explicitly out of scope.
