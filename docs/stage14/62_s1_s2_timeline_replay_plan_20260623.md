# Stage14-62: S1/S2 Timeline And Replay Plan

Date: 2026-06-23

Status: `plan_frozen_before_solver_edit`

Branch:

```text
work/phasefield-c-reference-20260623
```

## Decision

Proceed into S1/S2, but do not change curved-wall wetting physics yet.

The required order is:

```text
S1: audit PhaseF / WallGhost / gradPhi / mu / force producer-consumer timeline
S2: C-to-TCLB first-10-step field replay
S3: only then touch curved-wall wetting implementation
```

This order is mandatory because the current failure mode may be caused by TCLB
execution semantics rather than by the wetting formula alone.

## Official TCLB Constraints Used

TCLB model-development documentation describes the model as a set of R-defined
fields, densities, stages, and actions that generate C/CUDA execution code. The
constraints relevant here are:

```text
AddDensity defines distribution/density variables with lattice offsets.
Nonzero dx/dy/dz density entries are streamed by the framework.
AddField defines non-streaming node fields used for state, caches, and output.
AddStage defines a function plus explicit load/save sets.
Actions execute ordered stage lists.
The generated solver uses alternating buffers; fields that must persist must be
saved through the intended stage.
Inside Dynamics.c.Rt, x = x(0,0,0) is needed when a field value must be copied
from the current loaded value into the written value for the next buffer.
```

Official documentation sources:

```text
https://docs.tclb.io/
https://docs.tclb.io/tutorials/model-development/3.-d2q9-shanchen-srt/
```

The Shan-Chen model-development tutorial is used here only for TCLB execution
semantics: it explains adding distributions as `AddDensity`, separate fields as
`AddField`, iteration stages with explicit `save`/`load`, and the A/B buffer
caveat. It is not used as phase-field wetting physics.

Local code already reflects these semantics:

```text
Dynamics.R:248-294 defines stages/actions.
lattice.R:1-59 defines g/h AddDensity streaming populations.
Dynamics.R:86-93 defines WallGhost and related diagnostic fields.
Dynamics.R:223-234 defines gradPhiVal_* and PhaseF fields.
Dynamics.c.Rt:620-631 calcPhaseF writes PhaseF after Run.
Dynamics.c.Rt:1235-1413 CollisionMRT consumes PhaseF, gradPhi, mu, and force.
Boundary.c.Rt:1467-1510 computes gradPhiVal_*.
Boundary.c.Rt:1648-1777 computes WallGhost / wall PhaseF.
```

## Current Geometric Action Timeline

For `Options$geometric`, the current iteration action is:

```text
Iteration:
  1. BaseIter -> Run
  2. calcPhase -> calcPhaseF
  3. calcPhaseGrad -> calcPhaseGrad
  4. calcWall_CA -> calcWallPhase
  5. calcWallPhase_correction -> calcWallPhase_correction
```

This means `Run` at step `n` consumes the saved fields from the end of step
`n-1`, then `calcPhaseF`, `calcPhaseGrad`, and `calcWallPhase` produce the
fields to be consumed by `Run` at step `n+1`.

That one-stage lag is not automatically wrong. It must be made explicit and
matched in the C reference replay.

## S1 Producer-Consumer Map

| Quantity | Producer | Consumer | Current Time-Level Risk |
|---|---|---|---|
| `h0..h26` | `CollisionMRT/BGK` in `Run` | TCLB streaming and `calcPhaseF` | Streaming densities, not C current arrays. |
| `g0..g26` | `CollisionMRT/BGK` in `Run` | TCLB streaming and next `Run` | Streaming densities; wall/solid bounce semantics must be per-link verified later. |
| `PhaseF` fluid | `calcPhaseF` from `sum(h)` | `calcGradPhi`, `calcMu`, `calcWallPhase`, output | `Run` consumes previous saved `PhaseF`, not the `sum(h)` produced later in the same action. |
| `PhaseF` wall/solid | `calcWallPhase` / correction mirrors finite fluid value | stencil center and output | Must remain a finite mirror or neutral value; must not be treated as active physical mass. |
| `WallGhost` | `calcWallPhase` | `STAGE13_PHASE_FOR_STENCIL` and `STAGE13_BOUNDARY_PHASE` | Passive ghost only; must not collide, stream, or be summed as physical phase mass. |
| `gradPhiVal_*` | `calcPhaseGrad` / init | `calcWallPhase`, output, sometimes `getGradPhi` | Current order computes it after `Run`; if `Run` uses `calcGradPhiRaw` directly, cached gradPhiVal is not the force gradient except in explicit consumers. |
| `gradPhi` local | `calcGradPhi()` inside `Run` | `calcMu`, `calc_Fp`, `calc_Fs`, DynamicCL, normals | Must prove stencil source is `STAGE13_PHASE_FOR_STENCIL`, not raw `PhaseF=-999`. |
| `mu` local | `calcMu(C)` inside collision | `calc_Fs` | Not saved as a field currently; S2 needs either output diagnostics or host recomputation from exported PhaseF/WallGhost. |
| `F_surf` local | `calc_Fs(mu, gradPhi)` | `F_total`, velocity and population update | Not saved; S2 needs diagnostic fields or C-side recomputation with identical inputs. |
| `F_pressure` local | `calc_Fp(p, gradPhi)` | `F_total` | Depends on pressure moment `p=m0[0]` from streamed `g`; cannot be replayed from PhaseF alone. |
| `F_total` local | force loop in collision | velocity update and `g` collision | Requires flow-population replay or diagnostic fields. |

## S1 Tasks

### S1.1 Static source audit

Create a machine-readable timeline artifact from the active model:

```text
artifacts/s1_timeline_audit_20260623/
  stages.csv
  fields_of_interest.csv
  producer_consumer_edges.csv
  timeline_summary.json
  unresolved_edges.csv
```

Minimum fields:

```text
PhaseF
WallGhost
WallGhostRaw
WallGhostClamped
WallGhostClampHit
WettingPathId
LocalRadAngle
gradPhiVal_x/y/z
gradPhi_PhaseF
PhaseStencilGhostUseCount
PhaseStencilFallbackCount
PhaseStencilMidpointFallbackCount
ForceIterResidual
ForceIterCount
```

Minimum functions:

```text
Init
Init_distributions
Run
CollisionMRT
CollisionBGK
calcPhaseF
calcGradPhi
calcMu
calc_Fp
calc_Fs
calcPhaseGrad
calcWallPhase
calcWallPhase_correction
BounceBack
```

### S1.2 Confirm generated code stage semantics

On the remote compile lane, inspect the generated model after source generation:

```text
/home/yuan/src/TCLB_lbm2026_compile_lane/
```

Confirm:

```text
which files contain generated stage kernels
which density groups each stage loads
which field groups each stage saves
whether PhaseF/WallGhost/gradPhi fields are loaded with the expected stencil depth
```

No physics edit is allowed if generated stage order differs from the source
audit.

### S1.3 Decide if diagnostic-only fields are required

If S2 cannot reconstruct `mu`, `F_surf`, `F_pressure`, or `F_total` from output
fields with no ambiguity, add diagnostic fields only:

```text
ReplayMu
ReplayLapPhi
ReplayGradPhiX/Y/Z
ReplayFsurfX/Y/Z
ReplayFpressureX/Y/Z
ReplayFtotalX/Y/Z
ReplayPhaseFromH
ReplayStageId
ReplayStepLocal
```

Rules:

```text
diagnostic fields must not feed back into collision
default output disabled unless ReplayDiagnosticsMode>0
legacy behavior must be bitwise or numerically unchanged when diagnostics off
diagnostics must be committed separately from any wetting-physics edit
```

## S2 C-to-TCLB Replay Plan

### S2.1 Reference case selection

Start with the smallest cases:

```text
case A: periodic bulk planar tanh, no wall
case B: flat wall theta90, neutral wetting, no curved geometry
case C: flat wall theta30/150, wetting ghost active
```

Do not start with cylinder or sphere. Curved geometry remains frozen until these
pass.

### S2.2 Step window

Compare:

```text
after Init
after step 0
after step 1
after step 2
after step 5
after step 10
```

For the first implementation, output every step 0-10 if affordable. The domain
must be intentionally small enough that full VTI/CSV extraction is cheap.

### S2.3 Fields to compare

Mandatory:

```text
fluid_mask
solid_or_wall_mask
PhaseF
WallGhost
WallGhostRaw
WallGhostClamped
WallGhostClampHit
WettingPathId
LocalRadAngle
gradPhiVal_x/y/z
ReplayLapPhi or C-recomputed lapPhi
ReplayMu or C-recomputed mu
ReplayFsurf_x/y/z or C-recomputed F_surf
PhaseStencilGhostUseCount
PhaseStencilFallbackCount
PhaseStencilMidpointFallbackCount
```

Flow coupling fields:

```text
U/V/W
pnorm or P/Pstar
ReplayFpressure_x/y/z
ReplayFtotal_x/y/z
ForceIterResidual
ForceIterCount
```

Population fields are required before claiming full replay:

```text
h0..h26
g0..g26
```

If VTI output cannot provide all population fields economically, use a tiny
domain and a CSV dump action or binary-to-CSV extractor. Do not substitute
macroscopic-only comparison for population replay.

### S2.4 C reference extension

Extend `reference_solvers/phasefield_d3q27_c` in layers:

```text
S2a: import TCLB initial fields and geometry mask
S2b: compute grad/lap/mu/F_surf from passive ghost-aware stencils
S2c: reproduce phase-population h collide/stream for 10 steps
S2d: reproduce flow-population g collide/stream or compare TCLB diagnostics
S2e: emit per-step CSV metrics and field dumps
```

The C reference must match TCLB time levels:

```text
Run consumes saved PhaseF/WallGhost/gradPhi from previous stage boundary.
calcPhaseF writes next PhaseF from post-stream h.
calcPhaseGrad writes next gradPhiVal.
calcWallPhase writes next WallGhost and wall PhaseF mirror.
```

Do not reorder C into a cleaner physical sequence unless the replay explicitly
labels it as an alternative algorithm. The first target is TCLB equivalence.

### S2.5 Metrics

For each field and each step:

```text
max_abs_error_fluid
rms_error_fluid
max_abs_error_near_wall
rms_error_near_wall
max_abs_error_wall_ghost
nonfinite_count
sentinel_read_count
mass_fluid_phase
mass_population_h
max_abs_u
max_abs_mu
max_abs_Fsurf
max_abs_Ftotal
```

For wall cases:

```text
ghost_clamp_fraction
ghost_raw_minus_clamped_max
wetting_path_histogram
phase_stencil_ghost_use_count
phase_stencil_fallback_count
```

## Pass/Fail Gates

### Gate S1

Pass only if:

```text
all producer-consumer edges are mapped
no unresolved PhaseF/WallGhost/gradPhi/mu/force consumer remains
generated stage order matches source Dynamics.R action order
WallGhost is proven passive: AddField only, no AddDensity, no collision path
all stencil macros route solid/wall reads through valid ghost/mirror logic
```

Fail if:

```text
any stencil can still read PhaseF=-999 or a special-point magic value
any force input depends on an undocumented time level
any diagnostic field feeds back into collision
```

### Gate S2

Pass only if:

```text
bulk periodic case matches C replay for steps 0-10 within roundoff/stencil tolerance
flat theta90 wall case matches C replay with zero or explained ghost bias
flat theta30/150 wall cases show the expected WallGhost sign and no sentinel reads
population h/g or explicitly scoped macro fields agree at the declared time level
mass metrics distinguish fluid physical mass from wall/ghost output fields
```

Fail if:

```text
the first mismatch occurs before wall logic but is not explained
TCLB and C use different coordinate offsets
PhaseF output mass is used as physical mass without a fluid mask
ghost clamp hides the main wetting response
```

## Implementation Order After This Plan

1. Improve `scripts/audit_tclb_execution_semantics.py` into an S1 timeline
   extractor.
2. Run S1 locally and against the remote generated compile lane.
3. Add diagnostic-only replay fields if S1 proves they are necessary.
4. Implement C reference S2a/S2b first; validate against exported initial fields.
5. Run 10-step bulk replay.
6. Run 10-step flat-wall replay.
7. Only after S1/S2 pass, design the curved-wall wetting patch.

## Explicit Non-Goals

Not allowed in S1/S2:

```text
no compact-stencil curved-wall write-path change
no DynamicCL force change
no MRT relaxation retuning
no Cahn-Hilliard replacement
no dynamic impact case
no validation_passed claim
```

Allowed claims after S1/S2 pass:

```text
TCLB execution timeline is mapped
C reference and TCLB agree for declared small replay cases
curved-wall implementation can now be modified with a reliable baseline
```

## Immediate Next Command Set

Local:

```text
python scripts/audit_tclb_execution_semantics.py ^
  --model-dir third_party/tclb_snapshots/stage9_analytic_wetting_diffuse_interface/models/multiphase/d3q27_pf_velocity ^
  --out-dir artifacts/s1_timeline_audit_20260623
```

Remote:

```text
ssh -i C:\Users\yuanz\Desktop\lbm-new\.ssh\id_ed25519 yuan@192.168.1.16 \
  "cd /home/yuan/src/TCLB_lbm2026_compile_lane && find . -maxdepth 4 -type f | grep -E 'Dynamics|Boundary|stage|Action|Kernel|\\.cu|\\.c' | head -200"
```

Those commands are audit-only. No solver physics should be edited until their
outputs are reviewed.
