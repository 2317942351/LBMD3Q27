# Stage18 Taichi Force/Momentum Closure: Literature-Derived Modification Plan

Date: 2026-07-04
Branch: `work/phasefield-c-reference-20260623`
Status: `plan_then_execute`

## Objective

The next modification targets the bulk coupled solver before any wall/wetting
repair:

```text
pressure / F_surf / momentum force insertion / low-density F/rho closure
```

This is now higher priority than wall/solid `h_i` per-link mass conservation,
because the current `periodic_droplet_ratio10_coupled` case fails without any
wall. A wall contact-angle boundary cannot be meaningfully validated if the
periodic bulk droplet already becomes unstable when force, momentum and phase
advection are coupled.

## Trusted Sources

This plan follows the project literature-first protocol:

`docs/stage18/015_literature_first_force_closure_protocol_20260704.md`

Local book anchors:

- `references/phasefield_lbm_book_2024/chapter_code_map.md`
  - Ch. 4: conservative Allen-Cahn source moments.
  - Ch. 7: pressure/interface-force format, static droplet, spurious currents,
    density-ratio behavior.
- `references/huang_liu_2023_lbm_phase_wetting/chapter_code_map.md`
  - Phase LBE source timing and N-S LBM forcing.
- `references/he_li_wang_tong_2023_lbm_theory_phase_wetting/chapter_code_map.md`
  - Large-density-ratio phase-field models, density interpolation, force
    coupling and contact-angle model separation.

Primary external force-insertion anchor:

- Guo, Zheng and Shi, 2002, "Discrete lattice effects on the forcing term in
  the lattice Boltzmann method", Phys. Rev. E 65, 046308, DOI:
  `10.1103/PhysRevE.65.046308`.

Primary high-density-ratio phase-field anchors for this stage:

- Conservative Allen-Cahn phase-field LBM literature is used for the phase
  population/source route.
- Large-density-ratio phase-field LBM literature is used to keep pressure,
  surface force and density interpolation tied together rather than tuning
  them independently.

## Current Code State

Main file:

`tools/taichi_phasefield_clean_2026/phasefield_full_solver.py`

Current coupled chain:

```text
h_i[src]
  -> phase_from_h_kernel
  -> C
  -> rho_tau_kernel
  -> rho(C), tau(C), pressure = rho cs2
  -> grad_laplace_mu_kernel
  -> gradC, laplaceC, mu
  -> force_kernel
  -> F_surf = mu gradC, F_pressure = 0, F_mu = 0
  -> momentum_macro_kernel
  -> u = (sum e_i g_i + 0.5 F_total) / rho
  -> collide_momentum_kernel
  -> BGK + Guo-like force source
  -> stream_kernel
  -> next g_i[src]
```

Observed blocker from
`docs/stage18/014_taichi_full_solver_smoke_result_20260704.md`:

```text
periodic_droplet_ratio10_passive: pass
periodic_droplet_ratio10_coupled: fail
u_max approx 9830
mass drift approx 310
nonfinite = 0
```

The failure is therefore not caused by wall geometry. It is a coupled
bulk-force/momentum/phase-advection failure.

## Mathematical Closure Questions

### Q1. What is the pressure variable?

The current code stores:

```text
pressure = rho * cs2
```

This is only a placeholder. A phase-field two-phase model may use a pressure
distribution, a hydrodynamic pressure, a reference-subtracted pressure, or a
pressure tensor/stress-divergence formulation depending on the selected model.

First implementation requirement:

```text
PressureModel = 0: rho cs2 placeholder
PressureModel = 1: rho cs2 - reference, diagnostic
```

Do not call either one final. The purpose is to expose pressure-gradient
magnitude and its effect separately from `mu gradC`.

### Q2. Which interface force is active?

The current code uses:

```text
F_surf = mu gradC
F_pressure = 0
F_mu = 0
```

This is not enough to prove a correct pressure/interface-force split. The next
code must support:

```text
ForceClosureMode = 0: force off
ForceClosureMode = 1: F_surf only
ForceClosureMode = 2: F_pressure only
ForceClosureMode = 3: F_surf + F_pressure
```

`F_pressure` is implemented as `-grad(pressure)` for diagnosis. This is not yet
the final pressure closure; it is a controlled probe to determine whether the
pressure path is the first unstable branch.

### Q3. Is force injected exactly once?

Guo forcing requires a consistent relation between:

```text
macroscopic velocity definition
discrete source term
collision relaxation
force moment
```

The current code always uses:

```text
u = (mom + 0.5 F) / rho
Guo source in population update
```

The next code must expose force insertion as a mode:

```text
ForceInsertionMode = 0: no half-force velocity, no population source
ForceInsertionMode = 1: half-force velocity + Guo source
ForceInsertionMode = 2: half-force velocity only, no population source
ForceInsertionMode = 3: no half-force velocity + Guo source
```

Mode 1 is the literature candidate. Modes 0/2/3 are diagnostic probes and must
not be claimed as physical fixes.

### Q4. Is low-density F/rho the amplifier?

The current code divides by:

```text
max(rho, 1e-30)
```

That makes diagnostics mathematically well-defined but can hide a physically
invalid acceleration in gas/interface cells. The next code must expose:

```text
rho_force_floor
force_accel_cap
force_cap_hits
```

The cap mode is diagnostic only. If it makes the run stable, it proves the
amplifier, not the final physics.

## Implementation Plan

### Step 1. Add explicit closure settings

New command-line settings in `phasefield_full_solver.py`:

```text
--pressure-model
--pressure-reference
--force-closure-mode
--force-insertion-mode
--rho-force-floor
--force-accel-cap
--surface-force-scale
--pressure-force-scale
```

Existing `--force-mode` remains as a compatibility alias.

### Step 2. Add force component diagnostics

Extend `StepMetrics` with:

```text
pressure_min/max
f_pressure_max
f_surf_max
f_mu_max
f_body_max
f_total_max
force_cap_hits
g_min/g_max
```

These are required to decide whether the first failure branch is pressure,
surface force, low-density acceleration, or momentum population blow-up.

### Step 3. Split pressure and force kernels

`rho_tau_kernel` will store pressure according to `PressureModel`.

`force_kernel` will:

```text
compute grad(pressure)
compute F_pressure = - pressure_force_scale * grad(pressure)
compute F_surf = surface_force_scale * mu * gradC
select components via ForceClosureMode
apply optional diagnostic acceleration cap
write all component fields and force_over_rho
```

### Step 4. Split force insertion

`momentum_macro_kernel` will use `ForceInsertionMode`:

```text
0: u = mom / rho
1: u = (mom + 0.5 F) / rho
2: u = (mom + 0.5 F) / rho
3: u = mom / rho
```

`collide_momentum_kernel` will use the same mode:

```text
0: no Guo source
1: Guo source
2: no Guo source
3: Guo source
```

### Step 5. Minimal P100 gates

All gates use periodic droplet, ratio 10, 24^3, 20 steps first.

```text
F1 momentum_no_force:
  force_closure=0, momentum=1, insertion=0, phase_adv=0

F2 surface_shadow_no_injection:
  force_closure=1, momentum=1, insertion=0, phase_adv=0

F3 guo_surface_no_phase_adv:
  force_closure=1, momentum=1, insertion=1, phase_adv=0

F4 guo_surface_phase_adv:
  force_closure=1, momentum=1, insertion=1, phase_adv=1

F5 capped_surface_phase_adv:
  force_closure=1, momentum=1, insertion=1, phase_adv=1,
  force_accel_cap=0.01

F6 pressure_only_shadow:
  force_closure=2, momentum=1, insertion=0, phase_adv=0

F7 pressure_plus_surface_guo:
  force_closure=3, momentum=1, insertion=1, phase_adv=0
```

Interpretation:

```text
F1 fail -> momentum BGK/streaming is wrong even without force.
F2 fail -> force is not shadow-only or diagnostics are contaminating state.
F3 fail -> force insertion or surface force magnitude is unstable.
F4 fail but F3 pass -> phase advection by u is the amplifier.
F5 pass while F4 fail -> low-density F/rho acceleration is the amplifier.
F6/F7 isolate pressure-gradient contribution.
```

## Claim Limits

Allowed:

```text
bulk_force_closure_probe_pass/fail
force_insertion_variant_pass/fail
pressure_shadow_probe_pass/fail
```

Forbidden:

```text
contact angle validated
wall wetting repaired
high-density-ratio solved
dynamic impact ready
```

## What Is Deliberately Not Changed

- No wall/solid `h_i` per-link write in this stage.
- No contact-angle case in this stage.
- No sphere/cylinder wetting write in this stage.
- No empirical default cap.
- No `F_mu` stress reconstruction as default. `F_mu` remains zero until the
  pressure/surface-force/insertion probes identify the next stable branch.

