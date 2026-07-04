# Stage18 Taichi Route Assessment And Official Docs Anchor

Date: 2026-07-04
Branch: `work/phasefield-c-reference-20260623`
Status: `route_assessment_and_tooling_anchor`

## Question

Would moving from TCLB to Taichi reduce the current project risks?

Short answer: yes for implementation transparency, no for the underlying
phase-field LBM mathematics. Taichi is a credible route for a clean GPU solver
baseline because it removes TCLB's generated-stage indirection and makes
population buffers, kernel order, and post-processing easier to inspect. It
does not automatically fix conservative phase-equation closure, pressure/force
closure, or wetting boundary physics.

## What Taichi Can Reduce

The current TCLB line repeatedly failed around generated execution semantics:

```text
Dynamics.R declarations
  -> RT generation
  -> generated stage load/save
  -> AddDensity streaming offsets
  -> wall/solid source populations
  -> next-step PhaseFromH
```

Taichi can make these pieces explicit:

```text
Python scope config/I/O
  -> @ti.kernel initialize
  -> @ti.kernel collide into buffer B
  -> @ti.kernel stream into buffer B or pull from buffer A
  -> @ti.kernel apply boundary populations
  -> swap src/dst
  -> @ti.kernel diagnostics/reductions
  -> Python-side analysis/plots
```

This is easier to audit because `f[src,...]` and `f[dst,...]` are ordinary
explicit buffers. There is no hidden RT-generated stage bridge comparable to
TCLB's `AddDensity` and `AddStage(save=...)` behavior.

## What Taichi Does Not Fix

Taichi does not solve these mathematical issues:

- whether the conservative Allen-Cahn or Cahn-Hilliard equation is the correct
  phase equation for the target density ratio and interface width;
- whether `sum_i h_i`, `sum_i F_phi_i`, and first moments of `F_phi` are
  consistent with the chosen LBE;
- whether `rho(C)` stays physical when `C` approaches bounds;
- whether pressure force, surface force, and `F_mu` stress reconstruction are
  double counted or time-level inconsistent;
- whether wall wetting is mass-conservative at per-link incoming/outgoing
  population level;
- whether sphere/cylinder curved wetting should be geometric ghost, surface
  free energy, diffuse solid, or another boundary construction.

Therefore Taichi should be treated as a clean implementation lane, not as an
escape from the model derivation.

## Existing Evidence In This Repo

There is already a Taichi single-phase GPU baseline:

- `tools/taichi_lbm/taichi_cylinder_re100.py`
- `tools/taichi_lbm/run_hm570_taichi_cylinder_re100.sh`
- `tools/taichi_lbm/analyze_cylinder_forces.py`
- `artifacts/taichi_cylinder_re100_20260703/REPORT.md`
- `artifacts/taichi_cylinder_re100_20260703/GRID_REFINEMENT_REPORT.md`

The existing report records an exploratory D2Q9 BGK Re=100 cylinder case on
P100. It is not phase-field validation, but it shows that Taichi GPU execution,
force-history output, and post-processing can work in this project environment.

## Official Taichi Documentation Downloaded

Local anchor:

`references/taichi_official_docs_20260704/README_TAICHI_OFFICIAL_DOCS.md`

Downloaded local snapshots:

- `references/taichi_official_docs_20260704/docs.taichi.graphics/`
- `references/taichi_official_docs_20260704/taichi/`

These are intentionally excluded from Git because the snapshot is large
(about 599 MiB). Only the lightweight README and commit identifiers should be
committed.

Important official files:

- `kernel_function.md`: Python scope vs Taichi scope, `@ti.kernel`, `@ti.func`.
- `kernel_sync.md`: GPU asynchronous execution and `ti.sync()`.
- `field.md`: Taichi global fields, vector fields, 0D fields, indexing.
- `differences_between_taichi_and_python_programs.md`: unsupported Python
  constructs in Taichi scope.
- `global_settings.md`: `ti.init(arch=ti.cuda)`, `debug=True`,
  `device_memory_GB`, `default_fp`, `fast_math`, profiler/offline cache.
- `debugging.md`: debug mode and bounds checks.
- `performance.md`: GPU loop parallelization, block dimensions, reductions,
  BLS/TLS, offline cache.

## Required Architecture If We Start A Taichi Phase-Field Solver

Do not directly port the TCLB file. Create a clean Taichi solver package with
one explicit dataflow:

```text
config dataclass
  -> lattice constants
  -> geometry mask/SDF
  -> distribution buffers g[2,nx,ny,nz,Q], h[2,nx,ny,nz,Q]
  -> macroscopic fields C/rho/u/mu/gradC
  -> collision kernels
  -> streaming kernels
  -> boundary kernels
  -> diagnostics kernels
  -> Python analysis/plots
```

Every field must declare:

- owner: Python scope or Taichi scope;
- storage: `ti.field`, `ti.Vector.field`, NumPy output, or scalar config;
- time level: pre-stream, post-stream, post-collision, or diagnostic;
- producer kernel;
- consumer kernel;
- whether it participates in double buffering.

## Recommended Gate Sequence

1. Taichi infrastructure gate:
   - CPU and CUDA smoke produce identical D2Q9/D3Q19 population sums on a tiny
     grid.
   - `debug=True` catches bounds errors.
   - output files record config and commit.

2. Single-phase LBM gate:
   - Poiseuille or lid-driven cavity.
   - Then Re=100 cylinder already started in `tools/taichi_lbm`.

3. Passive scalar/phase population gate:
   - advection-diffusion or conservative Allen-Cahn without momentum coupling.
   - verify `sum(h)` moments before wetting.

4. Bulk phase-field gate:
   - static droplet without walls.
   - mass drift, boundedness, curvature/Laplace pressure.

5. Coupled force gate:
   - pressure/surface force/F_mu variants isolated.
   - no wetting until force closure is stable.

6. Flat-wall wetting gate:
   - 30/90/150 and decoupled response with morphology plots.

7. Curved wall gate:
   - cylinder and sphere per-link or diffuse-solid boundary ledger.

8. Dynamic impact gate:
   - only after static flat/cylinder/sphere are credible.

## Decision

Taichi should be opened as a parallel clean implementation lane. It should not
replace the TCLB audit record yet, because the TCLB history contains valuable
failure evidence. The best next step is to build a small Taichi phase-field
baseline that reproduces the same mathematical model with explicit buffers,
then compare against C/TCLB on the first 10-20 steps.
