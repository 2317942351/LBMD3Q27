# Stage14-B116 TCLB Model Semantics Audit

Date: 2026-07-03

Scope:

```text
third_party/tclb_snapshots/stage14_B115_persistent_wall_h_slim/
```

This audit follows the local `$tclb-model-development` skill and therefore treats TCLB as a staged generated solver, not as a plain C array implementation.

## Executive Conclusion

The current model is not primarily blocked by contact-angle recognition, compact-stencil geometry, or grid density. The most suspicious fault is still the TCLB producer-consumer path for the phase population `h` near wall/solid nodes:

```text
wall/solid h source population
  -> AddDensity streaming
  -> calcPhaseF sums streamed h
  -> PhaseF / PhaseFromH leaves [0,1]
  -> rho(C), tau(C), mu, F/rho, pressure/stress closure explode
```

B115 did not solve this because it repairs fluid-side incoming `h` after `Run()` but the first consumer of `PhaseF` and the next streamed source-side wall/solid `h` semantics are still not closed.

## 1. Dynamics.R Contract

### 1.1 Streaming populations

`lattice.R` declares both momentum and phase populations with `AddDensity`:

```R
AddDensity( name="g1", dx= 1, dy= 0, dz= 0, group="g")
...
AddDensity( name="h1", dx= 1, dy= 0, dz= 0, group="h")
...
AddDensity( name="h26",dx= 0, dy=-1, dz=-1, group="h")
```

By TCLB official semantics, these are streamed populations loaded through offsets. They must not be read as ordinary C arrays at the current node.

### 1.2 Macro and wall normal variables are also density-style storage

`Dynamics.R` declares the following as `AddDensity(dx=0)`:

```R
AddDensity(name="pnorm", dx=0, dy=0, dz=0, group="Vel")
AddDensity(name="U", dx=0, dy=0, dz=0, group="Vel")
AddDensity(name="V", dx=0, dy=0, dz=0, group="Vel")
AddDensity(name="W", dx=0, dy=0, dz=0, group="Vel")
AddDensity(name="nw_x", dx=0, dy=0, dz=0, group="nw")
AddDensity(name="nw_y", dx=0, dy=0, dz=0, group="nw")
AddDensity(name="nw_z", dx=0, dy=0, dz=0, group="nw")
```

Even with zero offset, they still participate in the density/stage mechanism. They are not plain `AddField` caches. This matters because `BaseIter`, `calcPhase`, `calcWall_CA`, and gradient stages load different groups.

### 1.3 Non-streaming wall and diagnostic fields

`WallGhost`, `WallH`, `AnalyticFlag`, `PhaseF`, and replay diagnostics are `AddField`. This is conceptually right, but field writes only matter when the active stage saves them.

Current save/load design:

```R
save_iteration = c("g","h","Vel","nw", "solid_boundary", "runtime_diagnostics", ...)
load_iteration = c("g","h","Vel","nw", "solid_boundary", "runtime_diagnostics", ...)
load_phase     = c("g","h","Vel","nw", "solid_boundary", "runtime_diagnostics", ...)
```

Important stages:

```R
AddStage("calcPhase", "calcPhaseF",
  save=Fields$name %in% c("PhaseF", "ReplayPhaseFromH", ...),
  load=DensityAll$group %in% load_phase)

AddStage("BaseIter", "Run",
  save=Fields$group %in% save_iteration,
  load=DensityAll$group %in% load_iteration)

AddStage("calcWall_CA", "calcWallPhase",
  save=Fields$name %in% stage13_wall_phase_save_fields,
  load=DensityAll$group %in% c("nw", "gradPhi", "PF", "solid_boundary", ...))
```

## 2. Actual Iteration Timeline

For geometric mode:

```R
AddAction("Iteration",
  c("BaseIter", "calcPhase", calcGrad, "calcWall_CA",
    "calcWallPhase_correction", "calcPhaseB83Finalize"))
```

Actual order:

```text
BaseIter / Run()
  -> updateBoundary()
  -> CollisionMRT()/CollisionBGK()
  -> h update
  -> optional B115 fluid-side wall-link repair at Run() tail
  -> save g/h/Vel/nw/solid_boundary/runtime diagnostics

calcPhase / calcPhaseF()
  -> updateBoundary() again
  -> optional receiver-side h repair/quarantine
  -> PhaseF = sum(h) on fluid nodes
  -> save PhaseF/ReplayPhaseFromH diagnostics

calcPhaseGrad
  -> consumes PhaseF

calcWall_CA / calcWallPhase()
  -> computes WallGhost and wall PhaseF on wall/solid nodes
  -> save wall fields

calcWallPhase_correction
  -> correction path for wall fields

calcPhaseB83Finalize
  -> optional final PhaseF from current WallGhost
```

Key implication:

```text
Run() consumes the previous saved PhaseF and WallGhost before current calcWall_CA recomputes them.
```

Therefore a wall wetting formula that only updates `WallGhost` in `calcWall_CA` cannot repair the `h` update already performed inside `Run()` for the same iteration.

## 3. High-Confidence Problem Areas

### F1. B115 repair is receiver-side and gated away from wall/solid nodes

Code pattern:

```c
if (Stage14B115PersistentWallHMode > 1.5 &&
    !(IamWall || IamSolid) &&
    (Stage14B81PhaseBoundaryReconMode > 0.5 || Stage14B85NoIncreaseReconMode > 0.5)) {
    stage14_b68_apply_wall_h_streaming_repair(1);
}
```

And inside `stage14_b68_apply_wall_h_streaming_repair`:

```c
if ((IamWall || IamSolid) || (...)) return;
```

This cannot fix source-side wall/solid populations. It only modifies fluid nodes. If the actual problem is wall/solid `h_q` being streamed out through TCLB `AddDensity`, B115 is structurally aimed at the wrong side.

This matches the B115 evidence where `B81WallLinkCount = 0` and `B81WriteApplied = 0`: the intended wall-link repair did not reach the effective population set.

### F2. `calcPhaseF()` computes `PhaseF` from streamed `h` after an `updateBoundary()` call

Code pattern:

```c
real_t b62_pre_sum = sum(h);
updateBoundary();
real_t b62_post_sum = sum(h);
...
PhaseF = stage14_b98_passive_ghost_phase_from_h(raw_phase_from_h, PhaseF(0,0,0));
```

Because `h` is `AddDensity`, this sum is a sum over streamed local variables. The boundary update inside `calcPhaseF()` can alter `h` again before `PhaseF=sum(h)`. That makes the actual producer of `PhaseF`:

```text
previous stage-saved h
  + TCLB streaming offset
  + calcPhaseF updateBoundary/BounceBack side effects
  + optional local h repairs
```

This is not equivalent to a C solver's explicit current-array `phi=sum(h[x])`.

### F3. Wall/solid `BounceBack()` actively rewrites `h`

`BounceBack()` swaps all `g` populations and then swaps all `h` populations:

```c
tmp = h1; h1 = h2; h2 = tmp;
...
tmp = h24; h24 = h25; h25 = tmp;
```

Later optional modes can replace wall/solid `h` with passive weighted values or zero outgoing values, but these are mode-gated. In legacy/default path, wall/solid `h` is an active bounced population, not a passive ghost-only reservoir.

This is directly inconsistent with the desired C-like ghost semantics:

```text
wall ghost should provide phase boundary information
wall ghost should not act as a colliding/streaming phase population source
```

### F4. Current wall wetting data is produced after the phase population collision

`calcWallPhase()` computes `WallGhost` after `BaseIter` and `calcPhase`. This is useful for next-step gradients and diagnostics, but it does not influence the just-completed `h` collision in `Run()`.

This creates a one-step lag at best, and an ineffective repair at worst if the saved wall/solid `h` populations remain incompatible.

### F5. `calcMu()` and `calcGradPhi()` depend on `PhaseF` validity

`calcMu()` uses a Laplace stencil through `STAGE13_PHASE_FOR_STENCIL`. This is improved versus old raw `PhaseF=-999` reads, but the input is still the current saved/loaded `PhaseF`.

If `PhaseF` has already been corrupted by `h` streaming before `calcMu()`, then `mu`, `F_surf`, `F_mu`, and `F/rho` become downstream amplifiers, not first causes.

### F6. Force closure is still a secondary risk, but not the first wall-case failure

`CollisionMRT()` still contains risk areas:

```text
p = m0[0]
pressure_force_input = stage14_pressure_force_input(p, rho)
F_mu from stress reconstruction
U = m0[1:3] + 0.5 F/rho
mF[1:3] = F_total/rho
```

These need a formal force-closure pass, but B114/B115 evidence says `PhaseFromH` is already nonfinite by step 5/10. Therefore force closure should not be the next first edit unless a no-force wall case proves `PhaseFromH` remains bounded.

### F7. Too many historical modes now obscure the active path

The model contains many stage switches:

```text
B59, B60, B63, B68, B71, B76, B77, B78, B80, B81,
B84, B85, B91, B95, B98, B99, B103, B104, B106,
B108, B111, B113, B115
```

This is useful for audit history but makes the active physical path hard to reason about. The next repair should use a clean minimal snapshot with only:

```text
legacy baseline
required h source-side repair
minimal diagnostics
one explicit mode switch
```

## 4. What Is Not The Main Problem Right Now

### Not contact-angle image recognition

Contact-angle recognition can be improved later, but current morphology is physically broken before angle fitting is meaningful.

### Not compact-stencil curved-wall method yet

The compact-stencil/diffuse-solid work can help curved surfaces later. It does not fix flat-wall `h` population boundedness.

### Not grid density first

Increasing resolution may delay instability, but it does not solve an incorrect TCLB streaming/source semantic.

### Not simply `tmp1`

B113 normalized `tmp1` fixed a real algebra inconsistency, but B114/B115 showed instability persists before `tmp1` can be the decisive lever.

## 5. Current Root-Cause Hypothesis

Most likely root:

```text
The wall/solid nodes are still active h-population sources under TCLB AddDensity streaming.
The intended ghost/wetting value is stored in WallGhost/PhaseF fields, but the actual streamed h populations that calcPhaseF sums are not consistently made passive and bounded at the source side before the next streaming access.
```

This explains:

- B81/B85 style fluid-side repairs often reporting zero effective link count.
- B115 tail persistence not preventing step-5 nonfinite `PhaseFromH`.
- Morphology breaking even when contact-angle diagnostics or initial geometry are reasonable.
- Why direct C logic did not map cleanly: the C code controls arrays explicitly, but TCLB controls population streaming through `AddDensity`.

## 6. Next Code Direction

Do not run another full contact-angle campaign yet.

The next implementation should be a clean B116 candidate:

```text
Stage14B116PassiveWallHSourceMode
```

Required design:

1. Operate on wall/solid nodes, not only fluid nodes.
2. Execute at a point whose stage saves group `h`.
3. Replace or neutralize wall/solid source `h_q` values before they can be streamed to fluid nodes.
4. Use bounded `WallGhost` when valid, otherwise neutral phase.
5. Preserve momentum bounceback for `g`; do not confuse momentum wall handling with phase-population ghost handling.
6. Add only minimal diagnostics:
   - wall/solid h pre-sum;
   - wall/solid h post-sum;
   - outgoing wall-to-fluid h pre/post sum;
   - write-applied flag;
   - finite flag.
7. Validate only `wall_t90_10` first.

Acceptance for the next gate:

```text
wall_t90_10 reaches step 10
PhaseField nonfinite_count = 0
ReplayPhaseFromH nonfinite_count = 0
No contact-angle validation claim
```

Only after this passes should work return to:

1. conservative phase equation/source moment closure;
2. chemical-potential no-flux wall audit;
3. force/pressure/stress closure;
4. contact-angle morphology and metric repair;
5. curved wall compact/diffuse-solid integration.
