# Stage18 Taichi Full Phase-Field Multiphase Solver System Plan

Date: 2026-07-04
Branch: `work/phasefield-c-reference-20260623`
Status: `system_plan_full_stack_first`

## Position

This plan replaces the slow "one tiny module at a time" route for the Taichi
lane. The clean algebra and bulk-kernel gates have already shown that the
`h_i -> C` lifecycle can run on P100. The next step should be a full-stack
solver skeleton:

```text
build all core physics and infrastructure first -> run a complete low-risk case
-> then replace weak closures with stronger literature-derived closures.
```

The objective is not to claim validation immediately. The objective is to avoid
getting trapped in local repairs and to make the whole phase-field multiphase
dataflow visible in one Taichi program.

## Sources Used

### Xu 2024 Phase-Field LBM Book

Repository anchor:

`references/phasefield_lbm_book_2024/chapter_code_map.md`

Use in this plan:

- Ch. 3: order-parameter boundedness, Cahn-Hilliard, chemical potential,
  curvature and volume conservation.
- Ch. 4: conservative Allen-Cahn LBE, source moments, collision/source
  corrections.
- Ch. 5: higher-order source/correction options and boundedness behavior.
- Ch. 6: MRT and non-diagonal MRT phase-field models as later upgrades.
- Ch. 7: two-phase force/pressure closure, static droplet, spurious currents,
  density-ratio behavior.

### Huang-Liu 2023 LBM Phase/Wetting Excerpt

Repository anchor:

`references/huang_liu_2023_lbm_phase_wetting/chapter_code_map.md`

Use in this plan:

- Keep phase-population source timing explicit.
- Treat curved boundaries as per-link, time-level sensitive population
  reconstruction.
- Use contact-angle examples as validation workflow references, not as formula
  transplants across model families.

### He-Li-Wang-Tong 2023 Theory/Wetting Excerpt

Repository anchor:

`references/he_li_wang_tong_2023_lbm_theory_phase_wetting/chapter_code_map.md`

Use in this plan:

- Do not mix pseudo-potential virtual density, color-gradient normal
  correction, and phase-field wetting formulas without re-derivation.
- Phase-field wetting should use either surface-free-energy boundary or
  geometric order-parameter reconstruction.
- Complex curved boundaries need incoming/outgoing distribution mass budgets.
- High density ratio requires phase boundedness and force closure before
  wetting claims.

### Taichi Official Documentation

Repository anchor:

`references/taichi_official_docs_20260704/README_TAICHI_OFFICIAL_DOCS.md`

Specific rules used:

- Kernels are called from Python scope; `@ti.func` is called only from Taichi
  scope.
- Kernel arguments require real Taichi/Python type hints; avoid postponed
  string annotations for Taichi 1.7.4.
- Use `ti.field` / `ti.Vector.field` as explicit global fields. No field
  slicing.
- Use explicit `ti.sync()` before Python-side timing, status decisions, and
  field reads.
- Use `ti.init(arch=ti.cuda, default_fp=ti.f64, fast_math=False, ...)` during
  closure debugging.
- `CUDA_VISIBLE_DEVICES=1` selects the P100 in the current server setup.

## Design Principle: Full Skeleton First

The next solver should not be a minimal `h_i` toy plus later additions. It
should include the complete architecture from the beginning:

```text
geometry/SDF
  + component/order-parameter fields
  + phase populations h_a,i
  + momentum populations g_i
  + rho(C), viscosity(C), mobility(C)
  + gradC/laplaceC/mu
  + pressure/surface/F_mu/body forces
  + one force-insertion path
  + wall/wetting boundary path
  + per-link mass/flux ledgers
  + diagnostics and plotting outputs
```

Some formulas may initially be simple or conservative defaults, but the
interfaces and fields must exist from day one. That makes later replacement
local and auditable.

## Mathematical Model Choice

### First Full Solver Candidate

Use a binary phase-field model as the first running target, with an internal
component dimension so it can grow toward multicomponent cases:

```text
NC = 2 by default
C = liquid volume fraction in [0, 1]
rho(C) = rho_l * C + rho_g * (1 - C)
nu(C) or tau_g(C) interpolated consistently
phase equation = conservative Allen-Cahn candidate
momentum equation = D3Q27 incompressible/weakly-compressible LBM candidate
force = F_pressure + F_surf + optional F_mu + F_body
```

Reason:

- The current TCLB problem centers on streamed `h_i`, `F_phi`, boundedness,
  `rho(C)`, and force closure.
- Conservative Allen-Cahn maps directly to the existing `h_i` population route
  and the books' source-moment discussion.
- Cahn-Hilliard remains a later mode if AC boundedness or mass behavior is not
  good enough.

### Multicomponent Extensibility

Do not hard-code every formula only for one scalar if avoidable. The field
layout should allow:

```text
h[2, NC-1 or NC, nx, ny, nz, Qh]
C[NC, nx, ny, nz] or C_primary[nx,ny,nz] with component reconstruction
rho_component[NC]
mu_component[NC] or mu_primary
```

The first executable mode may set `NC=2`, but the code structure should not
prevent future droplet-fluid-gas or multicomponent extension.

## Taichi Package Layout

Create a new package, not a pile of scripts:

```text
tools/taichi_phasefield_clean_2026/
  phasefield_full_solver.py
  run_hm570_phasefield_full_solver.sh
  configs/
    smoke_flat_wall.json
    static_droplet_ratio200.json
    flat_wetting_30_90_150.json
    sphere_cylinder_shadow.json
  README.md
```

`phasefield_full_solver.py` should contain all first-generation kernels, but
keep Python-side sections organized:

```text
1. config dataclass and constants
2. lattice tables
3. field allocation
4. geometry and initialization kernels
5. phase kernels
6. chemical-potential kernels
7. force kernels
8. momentum kernels
9. boundary/wetting kernels
10. diagnostics and I/O
11. run loop
```

## Field Map

### Lattice Tables

```text
e_h[Qh]              D3Q27 phase lattice directions
w_h[Qh]              D3Q27 phase weights
opp_h[Qh]            opposite links
e_g[Qg]              D3Q27 momentum lattice directions
w_g[Qg]              D3Q27 momentum weights
opp_g[Qg]            opposite links
```

### Phase Fields

```text
h[2, nx, ny, nz, Qh]         streamed phase population double buffer
C[nx, ny, nz]                order parameter, derived from h
C_raw[nx, ny, nz]            pre-correction order parameter
C_corrected[nx, ny, nz]      bounded/mass-corrected shadow or write target
gradC[nx, ny, nz].vec3       central or isotropic gradient
laplaceC[nx, ny, nz]         Laplace operator
normalC[nx, ny, nz].vec3     interface normal
mu[nx, ny, nz]               chemical potential
F_phi_diag[nx, ny, nz]       phase source diagnostic
```

### Momentum Fields

```text
g[2, nx, ny, nz, Qg]          streamed momentum population double buffer
rho[nx, ny, nz]               density from C
tau_g[nx, ny, nz]             momentum relaxation time
pressure[nx, ny, nz]          chosen pressure variable
u[nx, ny, nz].vec3            physical velocity
u_half[nx, ny, nz].vec3       half-force velocity, if selected
```

### Force Fields

```text
F_pressure[nx, ny, nz].vec3
F_surf[nx, ny, nz].vec3       e.g. mu * gradC in first candidate
F_mu[nx, ny, nz].vec3         optional stress reconstruction mode
F_body[nx, ny, nz].vec3
F_total[nx, ny, nz].vec3
force_over_rho[nx, ny, nz].vec3
```

### Geometry And Boundary Fields

```text
solid[nx, ny, nz]             0 fluid, 1 solid
wall[nx, ny, nz]              solid-fluid adjacent band
sdf[nx, ny, nz]               signed distance
wall_normal[nx, ny, nz].vec3
target_theta[nx, ny, nz]      local target contact angle
wall_C_ghost[nx, ny, nz]      virtual order-parameter value
write_allowed[nx, ny, nz]     controlled write flag
```

### Ledgers

```text
mass_phase_total[0D]
mass_phase_raw[0D]
mass_phase_corrected[0D]
phase_oob_low_count[0D]
phase_oob_high_count[0D]
wall_h_outgoing_sum[0D]
wall_h_incoming_sum[0D]
wall_h_delta_sum[0D]
wall_clamp_count[0D]
force_over_rho_max[0D]
nonfinite_count[0D]
```

Use 0D fields with `[None]` for reductions, per Taichi field rules.

## Kernel Timeline

The full solver should use this order from the start:

```text
Python config
  -> ti.init(arch, f64, fast_math=False, device_memory_GB)
  -> allocate fields
  -> load lattice tables
  -> build_geometry_kernel
  -> initialize_phase_kernel
  -> initialize_momentum_kernel

For each step:
  1. phase_from_h_kernel
  2. phase_bound_shadow_or_write_kernel
  3. rho_tau_from_C_kernel
  4. grad_laplace_mu_kernel
  5. wetting_ghost_shadow_or_write_kernel
  6. force_kernel
  7. momentum_macro_kernel
  8. collide_phase_kernel
  9. collide_momentum_kernel
  10. stream_phase_pull_kernel
  11. stream_momentum_pull_kernel
  12. boundary_phase_kernel
  13. boundary_momentum_kernel
  14. diagnostics_reduce_kernel
  15. ti.sync and Python output at selected period
  16. swap buffers
```

Rationale:

- `C=sum(h)` must be produced before `rho(C)`, `mu`, force, and wetting.
- Force must be computed before momentum collision.
- Boundary population writes must be after streaming when using pull streaming.
- Python reads must follow `ti.sync()` or implicit synchronization through
  `to_numpy()`.

## First Full-Stack Physics Choices

These are deliberately "run first, refine later" choices:

```text
Qh = D3Q27
Qg = D3Q27
phase equation = conservative Allen-Cahn-like source candidate
h_eq = w_h * C * (1 + e.u/cs2) initially
F_phi = w_h * tmp1(C,W) * e.normal initially
chemical potential = beta*C*(C-1)*(2C-1) - kappa*laplaceC
F_surf = mu * gradC initially
pressure = rho*cs2 or selected explicit pressure field, not opaque m0[0]
momentum collision = BGK first, MRT interface reserved but field layout ready
force insertion = one Guo-like explicit mode, no hidden double injection
boundary = bounce-back for momentum, geometric C ghost for phase as shadow/write mode
wetting = flat wall first, but sphere/cylinder SDF and normals present
```

This is not the final publishable model. It is the complete running framework.
After it runs, replace weak choices with stronger ones:

- corrected conservative AC source,
- Cahn-Hilliard mode,
- MRT/non-diagonal MRT phase collision,
- pressure/stress force format from Ch. 7,
- surface-free-energy wetting,
- per-link curved-wall mass correction.

## Full-Stack Execution Milestones

### M1. Full Solver Skeleton Runs

Implement all fields and kernels listed above. Run:

```text
periodic static droplet
density ratio 10
24^3 or 32^3
20-100 steps
```

Pass means executable dataflow, not validation.

### M2. Density-Ratio Ramp With Same Full Solver

Without adding new modules, run:

```text
ratio 10 -> 50 -> 200 -> 1000
```

Record:

```text
C bounds
mass drift
rho min/max
force_over_rho max
u max
nonfinite count
```

This identifies whether instability is phase boundedness, force-over-rho, or
momentum collision.

### M3. Flat Wall Wetting With Full Ledgers

Run in the same solver:

```text
flat wall theta 30/90/150
decoupled 60->30 and 120->150
```

Output morphology images, angle estimates, and wall h ledgers. Do not claim
success from angle alone.

### M4. Curved Geometry Already Present

Use the same SDF system for:

```text
cylinder
sphere
```

Start with shadow wetting, then controlled phase population write. The per-link
incoming/outgoing mass ledger must already exist.

### M5. Dynamic Impact Preflight

Only after M1-M4 are numerically credible:

```text
droplet initialized with impact velocity
flat wall first
cylinder/sphere later
```

## What Not To Do

- Do not make Re=100 single-phase cylinder the architecture base.
- Do not return to local TCLB `WallGhost` patches as the main line.
- Do not tune contact angle before full solver phase/momentum fields are
  visible.
- Do not omit pressure/force closure just to make the phase equation look
  stable.
- Do not hide boundedness with a clamp unless the mass removed/added is
  reported and redistributed by a named mode.

## Immediate Implementation Instruction

Start a new file:

```text
tools/taichi_phasefield_clean_2026/phasefield_full_solver.py
```

Implement the complete field allocation and kernel skeleton first, including
all core physics modules with first-candidate formulas. The first run target is:

```text
periodic static droplet
24^3
density ratio 10
20 steps
arch=cuda on P100
```

Then run the exact same executable with:

```text
flat wall geometry, theta=90, density ratio 10, 20 steps
```

Only after both run should formulas be optimized.

