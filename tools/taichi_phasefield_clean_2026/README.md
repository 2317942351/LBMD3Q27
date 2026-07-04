# Taichi Phase-Field Clean 2026

Status: clean book-derived phase-field LBM lane.

This folder is intentionally separate from `tools/taichi_lbm/`. The existing
Re=100 Taichi cylinder script is single-phase GPU feasibility evidence only.
It is not the architecture base for this phase-field solver.

## Current Scope

The first implemented gate is offline algebra, not GPU execution:

```text
D3Q27 weights and lattice moments
  -> h_i equilibrium moments
  -> F_phi moments
  -> one-step h collision/source update
  -> JSON/CSV evidence
```

This matches the project decision that the next solver must be built from the
phase-field LBM model in the literature anchors before adding wetting or curved
walls.

## Files

- `phasefield_algebra_gate.py`
  - Pure Python/NumPy source-moment harness.
  - Does not require Taichi.
  - Verifies D3Q27 moment closure for the first conservative Allen-Cahn
    candidate and the current TCLB-like sharpening source.
- `phasefield_bulk_lifecycle_gate.py`
  - Pure Python/NumPy tiny-grid producer-consumer loop.
  - Tests `h_src -> collide/source -> pull stream -> C=sum(h_dst)` without
    wall, wetting, pressure force, or curved geometry.
- `phasefield_bulk_lifecycle_taichi.py`
  - Taichi kernel version of the same bulk h-population lifecycle.
  - Uses explicit `h[2,nx,ny,nz,Q]` double buffers and module-level kernels.
- `run_hm570_phasefield_bulk_kernel.sh`
  - Remote P100 runner that creates/reuses a Taichi Python environment and
    executes the kernel gate with `CUDA_VISIBLE_DEVICES=1`.
- `phasefield_full_solver.py`
  - Full-stack first Taichi solver skeleton: phase population, momentum
    population, rho/tau, chemical potential, force fields, flat-wall geometry,
    wetting ghost fields, boundary kernels, and diagnostics.
- `run_hm570_phasefield_full_solver.sh`
  - Remote P100 runner for periodic droplet and flat-wall smoke cases.

## Non-Goals

- No contact-angle validation.
- No wall or curved-boundary write path.
- No use of the Re=100 single-phase cylinder as a phase-field template.
- No hard clamp treated as physical validation.
