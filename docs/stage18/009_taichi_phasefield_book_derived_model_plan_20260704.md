# Stage18 Taichi Book-Derived Phase-Field Model Plan

Date: 2026-07-04
Branch: `work/phasefield-c-reference-20260623`
Status: `book_derived_model_plan`
Claim limit: this is a design gate, not a computation result or contact-angle
validation.

## Decision

Do not extend the Taichi route from `tools/taichi_lbm/taichi_cylinder_re100.py`.
That script is single-phase D2Q9 BGK evidence that the P100/Taichi path can run,
but it does not contain the phase-field model needed here.

The clean Taichi route must start from the three book anchors already in this
repository:

- `references/phasefield_lbm_book_2024/chapter_code_map.md`
- `references/huang_liu_2023_lbm_phase_wetting/chapter_code_map.md`
- `references/he_li_wang_tong_2023_lbm_theory_phase_wetting/chapter_code_map.md`

## Target Model To Specify Before Coding

The first Taichi phase-field solver must define these equations and moments
before any GPU implementation is treated as meaningful:

```text
order parameter: C in [0, 1] or phi in [-1, 1]
phase population: h_i
moment closure: sum_i h_i = C
phase source: F_phi_i with documented zeroth and first moments
chemical potential: mu(C, grad C, laplace C)
density interpolation: rho(C)
viscosity/mobility relation: tau_h, tau_g, M, interface width W
momentum population: g_i
force closure: F_pressure + F_surf + optional F_mu
wetting BC: surface-free-energy or geometric order-parameter reconstruction
```

The default first candidate should be conservative Allen-Cahn because the
current TCLB model already uses streamed `h_i` and a source-like `F_phi`. A
Cahn-Hilliard implementation remains a second candidate if the conservative AC
moments or boundedness cannot be closed cleanly.

## Why This Route Is Different From Re=100 Expansion

Re=100 cylinder development would validate only single-phase streaming,
bounce-back, force extraction, and wake post-processing. It would not answer the
current blocker:

```text
h_i -> C_from_h -> F_phi -> h_post -> streaming -> C_from_h_next
```

The current failure history shows that apparent `PhaseF` stability can hide
invalid streamed `h_i`. Therefore a Taichi solver must expose `h_i` buffers,
source moments, boundedness, mass drift, and wall population ledgers from the
first implementation.

## Taichi Implementation Mapping

Use explicit fields and double buffers:

```text
config dataclass: Python-only constants and runtime knobs
solid / wall / geometry SDF: ti.field or NumPy-to-field upload
g[2, nx, ny, nz, Qg]: streamed momentum populations
h[2, nx, ny, nz, Qh]: streamed phase populations
C, rho, u, mu, gradC, laplaceC: ti.field diagnostics/consumers
force fields: ti.Vector.field for pressure/surface/F_mu/total force
ledger fields: mass, clamp, boundary-link, wetting write counters
```

Producer-consumer order for the first clean solver:

```text
initialize C/u/rho -> initialize h/g equilibrium
  -> compute C = sum(h_src)
  -> compute rho(C), gradC, laplaceC, mu
  -> compute phase source F_phi
  -> collide h_src -> h_collide
  -> stream h_collide -> h_dst
  -> phase boundary reconstruction
  -> compute C_next = sum(h_dst)
  -> compute force closure from C_next or documented time level
  -> collide/stream g with one documented force insertion
  -> diagnostics and buffer swap
```

No kernel may silently read and write the same streamed population buffer unless
the in-place scheme is separately proven race-free.

## First Verification Gates

1. Algebra-only moment gate:
   - `sum_i h_i^eq = C`
   - `sum_i F_phi_i` equals the selected equation's required source moment
   - `sum_i e_i F_phi_i` equals the selected first-moment correction
   - one-cell and tiny-grid updates match the written derivation

2. Bulk phase gate:
   - no wall, no wetting, no curved geometry
   - `C` remains finite and bounded without using a hidden validation clamp
   - mass drift is reported before and after any boundedness correction

3. Force closure gate:
   - pressure/surface/`F_mu` terms are isolated
   - one force-insertion path is selected and documented
   - no contact-angle tuning is allowed while force closure is unstable

4. Flat-wall wetting gate:
   - only after bulk phase and force gates pass
   - validate morphology plots and angle extraction together
   - include decoupled response cases, not just equilibrium cases

5. Cylinder/sphere gate:
   - per-link or diffuse-solid ledger required
   - surface-free-energy and geometric reconstruction must not be mixed without
     a derivation

## Non-Goals

- Do not use Re=100 cylinder as the phase-field architecture base.
- Do not hard-clamp `C` and call the case validated.
- Do not tune wetting before `h_i` and force closure are correct.
- Do not copy full copyrighted book text into the repository.
- Do not treat Taichi as a substitute for mathematical closure.
