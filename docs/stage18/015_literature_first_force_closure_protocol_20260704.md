# Stage18 Literature-First Force Closure Protocol

Date: 2026-07-04
Branch: `work/phasefield-c-reference-20260623`
Status: `mandatory_protocol_for_next_force_closure_work`

## Purpose

The next solver work must repair the bulk force/momentum closure before wall
wetting. The repair is not allowed to be an empirical stabilizing patch. Every
new closure mode must be derived from trusted references first, then mapped to
the Taichi implementation.

Current priority:

```text
pressure / F_surf / momentum force insertion / low-density F/rho closure
  before
wall/solid h_i per-link mass-conserving boundary
```

Reason: the current Taichi full skeleton already fails in a periodic droplet
case without walls when force, momentum and phase advection are enabled. Wall
contact-angle work cannot be trusted until the bulk coupled model is stable and
mathematically closed.

## Trusted Source Stack

Use sources in this order.

### 1. Local book anchors

- `references/phasefield_lbm_book_2024/chapter_code_map.md`
  - Chapter 3: phase-field free energy, chemical potential, boundedness and
    dispersed-phase volume conservation.
  - Chapter 4: conservative Allen-Cahn equation, phase LBE, source moments and
    truncation-error corrections.
  - Chapter 7: two-phase model, static droplet, large-density-ratio behavior,
    spurious currents, pressure and interface-force formats.
- `references/huang_liu_2023_lbm_phase_wetting/chapter_code_map.md`
  - Phase-field model and Cahn-Hilliard / conservative Allen-Cahn sections.
  - N-S LBM and forcing sections.
- `references/he_li_wang_tong_2023_lbm_theory_phase_wetting/chapter_code_map.md`
  - Phase-field theory, density interpolation, large-density-ratio phase-field
    model and contact-angle theory.

### 2. Primary force-insertion literature

- Guo, Zheng and Shi, 2002, "Discrete lattice effects on the forcing term in
  the lattice Boltzmann method", Physical Review E, DOI:
  `10.1103/PhysRevE.65.046308`.
  - Required use: derive the discrete forcing term and half-force macroscopic
    velocity convention before modifying `collide_momentum_kernel`.

### 3. Conservative phase-field / high-density-ratio literature

- Conservative Allen-Cahn phase-field LBM literature must be used for the phase
  equation source moments, not only local clamps.
- High-density-ratio phase-field LBM papers must be used when changing
  `rho(C)`, pressure closure, or low-density `F/rho` handling.
- Wetting/contact-angle papers are only used after the bulk force/momentum gate
  passes; they do not override bulk pressure/force closure.

### 4. Taichi official semantics

- `references/taichi_official_docs_20260704/README_TAICHI_OFFICIAL_DOCS.md`
- Required constraints:
  - explicit double buffers for streamed populations;
  - separate collision, streaming, boundary and diagnostics kernels until gates
    pass;
  - `ti.sync()` before Python reads and run verdicts;
  - `default_fp=ti.f64`, `fast_math=False` for closure debugging;
  - no hidden in-place updates of `g_i` or `h_i`.

## Required Derivation Before Code Changes

Before changing `tools/taichi_phasefield_clean_2026/phasefield_full_solver.py`,
write a short derivation section in the next result document containing:

```text
1. selected continuum equations
2. selected LBE form
3. equilibrium moments
4. source/force moments
5. macroscopic velocity definition
6. pressure variable definition
7. density interpolation and minimum-density handling
8. exact Taichi fields/kernels that produce and consume each quantity
```

No code path is allowed to be called "physical repair" unless those eight items
are present.

## Current Code Mapping

Current implementation file:

`tools/taichi_phasefield_clean_2026/phasefield_full_solver.py`

Relevant producer-consumer chain:

```text
h_i[src]
  -> phase_from_h_kernel
  -> C
  -> rho_tau_kernel
  -> rho(C), tau(C), pressure placeholder
  -> grad_laplace_mu_kernel
  -> gradC, laplaceC, mu
  -> force_kernel
  -> F_pressure, F_surf, F_mu, F_total, F_total/rho
  -> momentum_macro_kernel
  -> u = (sum e_i g_i + 0.5 F_total) / rho
  -> collide_momentum_kernel
  -> g_i post-collision with selected force insertion
  -> stream_kernel
  -> next g_i[src]
```

Current risk points:

| Kernel | Current behavior | Risk |
|---|---|---|
| `rho_tau_kernel` | `rho = rho_g + C(rho_l-rho_g)`, `pressure = rho cs2` | pressure is a placeholder and may not be the hydrodynamic pressure required by the selected phase-field model |
| `force_kernel` | `F_surf = mu gradC`, `F_pressure = 0`, `F_mu = 0` | force split is not yet derived; surface force alone may be inconsistent with pressure and momentum closure |
| `momentum_macro_kernel` | `u = (mom + 0.5 F)/rho` | correct only if the population forcing scheme matches the same half-force convention |
| `collide_momentum_kernel` | BGK plus Guo-style source | must be verified against Guo forcing moments and the chosen pressure formulation |
| `collide_phase_kernel` | h equilibrium uses `u` when advection is enabled | any momentum error immediately contaminates phase transport |

## Mandatory Bulk Gates

Do not touch wall/solid wetting repair until these gates pass.

### Gate F1: force off, momentum on

Purpose: isolate whether `g_i` collision/streaming is stable without force.

Expected:

```text
periodic droplet, ratio 10
force_mode = 0
momentum_mode = 1
phase_advection_mode = 0
mass drift near machine precision
u_max remains near zero
nonfinite = 0
```

### Gate F2: surface force shadow, no momentum insertion

Purpose: measure `mu`, `gradC`, `F_surf`, `F/rho` magnitude without feeding it
back into `g_i` or `h_i`.

Expected:

```text
F_surf finite
F/rho finite
force extrema localized at interface
no phase morphology change caused by shadow force
```

### Gate F3: force insertion variants

Purpose: prove force is injected exactly once.

Required variants:

```text
0 no population source, no half-force velocity
1 half-force macro velocity only
2 Guo source only with matching macro velocity
3 low-density safe diagnostic cap, marked non-physical
```

The selected physical variant must match the literature-derived macroscopic
velocity and source moments. The cap variant is only a diagnostic stabilizer.

### Gate F4: pressure closure variants

Purpose: replace the pressure placeholder with a documented pressure model.

Required variants:

```text
0 rho cs2 placeholder
1 reference-subtracted pressure shadow
2 literature-derived physical pressure mode
```

The physical pressure mode cannot become default until a static droplet
Laplace-pressure check and spurious-current check are added.

### Gate F5: density ratio ladder

Only after F1-F4 pass at ratio 10:

```text
ratio 10 -> 50 -> 200 -> 1000
```

Failure at any ratio stops the ladder and records the first failing producer:

```text
C / rho / mu / F_surf / F_pressure / F_mu / F_total/rho / u / g_i
```

## Claim Limits

Allowed claims:

```text
bulk_force_closure_probe_pass/fail
force_insertion_variant_pass/fail
pressure_closure_shadow_pass/fail
```

Forbidden claims:

```text
contact angle validated
dynamic impact ready
high-density-ratio solved
wall wetting repaired
```

## Next Implementation Document

The next work item should create:

`docs/stage18/016_taichi_force_momentum_literature_derived_closure_20260704.md`

It must include:

1. reference equations used;
2. code changes made;
3. mode table;
4. P100 run root;
5. per-case metrics;
6. pass/fail verdict under the claim limits above.

