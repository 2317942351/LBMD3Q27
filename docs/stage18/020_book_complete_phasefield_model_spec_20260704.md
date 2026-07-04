# Stage18 Book-Derived Complete Phase-Field High-Density Wetting Model Spec

Date: 2026-07-04
Branch: `work/phasefield-c-reference-20260623`
Status: `implementation_spec_started`

## Why This Document Exists

The Taichi solver had reached a stable engineering baseline, but that baseline
was not a complete high-density-ratio wetting phase-field LBM. In particular:

- local/global boundedness correction was stabilizing the order parameter, but
  it was not the full conservative Allen-Cahn model;
- constant reference momentum density was a useful pressure/velocity clue, but
  it was not yet a derived pressure distribution model;
- neutral wall `h_i` per-link reflection fixed wall mass loss, but it did not
  impose a physical contact angle.

This document defines the model that the code must converge toward. It is a
guardrail against treating a stable scaffold as a publishable solver.

## Literature Anchors

Project-local anchors:

- `references/phasefield_lbm_book_2024/chapter_code_map.md`
  - Ch. 4: conservative Allen-Cahn LBE, phase source and collision/source
    corrections.
  - Ch. 5: higher-order source correction and source-format comparisons.
  - Ch. 6: MRT and non-diagonal MRT phase-field collision route.
  - Ch. 7: high-density-ratio two-phase force, pressure, static droplet and
    spurious-current validation.
- `references/huang_liu_2023_lbm_phase_wetting/chapter_code_map.md`
  - Conservative Allen-Cahn `h_i`, source timing, N-S forcing and wetting
    workflow.
- `references/he_li_wang_tong_2023_lbm_theory_phase_wetting/chapter_code_map.md`
  - Large density ratio, phase-field wetting, chemical-potential no-flux and
    per-link curved boundary mass accounting.
- `references/taichi_official_docs_20260704/README_TAICHI_OFFICIAL_DOCS.md`
  - Taichi field/kernel semantics, explicit double buffers and reduction
    behavior.

## Target Continuous Model

The selected mainline is a conservative Allen-Cahn phase-field model coupled to
an incompressible / pressure-velocity LBM momentum equation:

```text
rho(C) = rho_g + C (rho_l - rho_g),  C in [0, 1]

mu = beta C(C - 1)(2C - 1) - kappa laplace(C)

partial_t C + div(C u) =
  div( M [grad(C) - 4 C(1-C) n / W] )

F_surf = mu grad(C)
momentum equation uses a pressure variable p, not rho(C) as the streamed
weakly-compressible population density.
```

This means the old route

```text
g_i equilibrium density = rho(C)
```

is not acceptable as the final high-density-ratio model. Earlier gates proved
that this path fails even without force or phase advection.

## Discrete Phase Population Requirements

For the phase population `h_i`:

```text
sum_i h_i = C
sum_i h_i^eq = C
sum_i Fphi_i = 0
sum_i e_i Fphi_i = 4 C(1-C) n / W
```

The old source

```text
Fphi_i = w_i [1 - 4(C - 0.5)^2] (e_i dot n) / W
```

has two limitations:

1. it is tied to `C in [0,1]` through a hard-coded midpoint;
2. on D3Q27, `sum_i e_i w_i (e_i dot n) = cs2 n`, so the first moment is short
   by a factor `cs2` unless explicitly corrected.

The current implementation therefore introduces:

```text
phase_equation_mode = 0: legacy source
phase_equation_mode = 1: normalized conservative AC source
phase_equation_mode = 2: moment-corrected conservative AC source
```

Mode 2 is the first real book-derived candidate. It is still subject to
algebra and droplet gates; it is not a validation claim by itself.

The source magnitude is deliberately separated as:

```text
phase_source_scale
```

because mobility, interface width and phase relaxation must be matched. A
moment-corrected source can be algebraically right and still too strong for the
chosen `omega_h`, grid and interface width. Therefore source-scale sweeps are a
model-closure audit, not empirical contact-angle tuning.

## Momentum / Pressure Requirements

The momentum population `g_i` must not use `rho(C)` as its weakly-compressible
zeroth moment for the final model. The pressure-velocity path is:

```text
sum_i g_i = p / cs2
sum_i e_i g_i = rho_ref u
u = (sum_i e_i g_i + 0.5 F) / rho_ref
```

The implementation now separates:

```text
pressure_model = 0: legacy rho(C) cs2 placeholder
pressure_model = 1: reference-subtracted rho(C) cs2 diagnostic
pressure_model = 2: pressure-velocity sum(g_i) cs2 candidate
```

The `pressure_model=2` equilibrium is:

```text
g_i^eq = w_i [p/cs2
              + rho_ref (e_i dot u)/cs2
              + rho_ref (e_i dot u)^2/(2 cs2^2)
              - rho_ref |u|^2/(2 cs2)]
```

This is the correct architectural direction for high-density-ratio static
droplets, but it still requires Laplace pressure and spurious-current gates.

## Force Closure Requirements

The code must keep these force components separable:

```text
F_pressure = -grad(p) candidate / diagnostic
F_surf = mu grad(C)
F_mu = stress-reconstruction correction, default off until derived
F_body = rho(C) g
```

Current claim limit:

```text
F_surf + Guo forcing can run in short gates at density ratio 10.
```

Still missing before final model:

- pressure jump validation for static droplets;
- spurious current threshold;
- proof that Guo half-force is injected exactly once for the selected
  pressure-velocity equilibrium;
- derived `F_mu` stress reconstruction or a decision to omit it.

## Wetting Boundary Requirements

Wetting must act on `h_i` at the missing incoming link level, not by late
overwriting macro `C` or `PhaseF`.

Implemented modes:

```text
phase_wall_mode = 0: no phase wall repair
phase_wall_mode = 1: legacy h_i = w_i Cghost wall-band overwrite
phase_wall_mode = 2: neutral per-link reflection, mass ledger closed
phase_wall_mode = 3: wetting per-link reconstruction candidate
```

Mode 3 uses the shadow wall ghost only to reconstruct missing incoming phase
populations:

```text
h_in(q from solid) =
  h_out(opp(q)) + w_i [C_ghost(theta) - C_fluid]
```

This is not the final curved-wall formula, but it is the correct location in
the Taichi population lifecycle. It must be audited with:

- per-link missing count;
- stream mass before;
- reconstructed incoming mass;
- wall mass delta;
- global phase mass correction delta.

Before any contact-angle claim, flat wall must pass:

```text
theta 90 neutral morphology
theta 30 / 150 static morphology
decoupled 60 -> 30 and 120 -> 150 response direction
mass drift threshold
spurious velocity threshold
```

## Taichi Producer-Consumer Timeline

```text
Python args/constants
  -> ti.init(f64, fast_math=False)
  -> setup_fields()
  -> build_geometry_kernel()
  -> initialize_fields_kernel()
  -> phase_from_h_kernel()
  -> phase boundedness / global correction
  -> rho_tau_kernel()
  -> pressure_from_g_kernel() if pressure_model>=2
  -> grad_laplace_mu_kernel()
  -> wetting_kernel()
  -> force_kernel()
  -> momentum_macro_kernel()
  -> collide_phase_kernel()
  -> collide_momentum_kernel()
  -> stream_kernel()
  -> boundary_kernel()
  -> buffer swap
  -> diagnostics with ti.sync()
```

Rules:

- `h` and `g` are streamed double-buffer populations.
- `C`, `rho`, `mu`, `pressure`, `force`, `wall ghost` are non-streaming fields.
- No kernel reads and writes the same streamed buffer as a physical update.
- Wall reconstruction happens during missing-link stream handling.
- Boundedness correction is still a safety layer, not the definition of the
  phase equation.

## Current Code Changes In This Stage

Main file:

`tools/taichi_phasefield_clean_2026/phasefield_full_solver.py`

New/updated implementation points:

- `phase_mobility_factor(...)`
- `phase_source(...)`
- `phase_equation_mode`
- `phase_source_scale`
- `phase_source_sum_field`
- `phase_source_first_field`
- `geq_pressure_velocity(...)`
- `pressure_from_g_kernel(...)`
- `pressure_model=2`
- `phase_wall_mode=3`

## Validation Gates

Minimum next gates:

1. Algebra gate:
   - `sum(Fphi)` near zero;
   - `sum(e_i Fphi)` matches `4 C(1-C)n/W` for mode 2.
2. Bulk droplet:
   - density ratio 10, then 50, 200, 1000;
   - no nonfinite;
   - mass drift bounded;
   - pressure jump sign and magnitude plausible.
3. Flat wall:
   - neutral 90 morphology;
   - 30/150 morphology;
   - decoupled response direction.
4. Curved wall:
   - SDF/per-link geometry;
   - cylinder and sphere static contact angle;
   - only then dynamic impact.

## Forbidden Claims

Do not claim:

```text
complete high-density-ratio model validated
contact angle solved
sphere/cylinder solved
dynamic impact ready
```

until the gates above pass with morphology plots and metrics.
