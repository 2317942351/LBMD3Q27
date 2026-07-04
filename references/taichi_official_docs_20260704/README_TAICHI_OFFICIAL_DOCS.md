# Taichi Official Documentation Snapshot

Date: 2026-07-04

This directory is the local project anchor for evaluating a Taichi-based LBM
route for LBMD3Q27. The full downloaded snapshots are local-only and are
excluded by `.gitignore`.

## Local Contents

- `docs.taichi.graphics/`
  - Official Taichi documentation site source.
  - Repository: <https://github.com/taichi-dev/docs.taichi.graphics>
  - Recorded commit: `cf1c58e2bc3e78208a485b13569b2032eb3fbd60`
  - Public docs site: <https://docs.taichi-lang.org/>

- `taichi/`
  - Official Taichi source snapshot, sparse checkout for docs/examples.
  - Repository: <https://github.com/taichi-dev/taichi>
  - Recorded commit: `ba0e81dce559fb63a5958bf82feb1d00c55c02fe`

## Key Official Files For LBM Solver Development

- `docs.taichi.graphics/website/docs/lang/articles/kernels/kernel_function.md`
  - Distinguishes Python scope, Taichi scope, `@ti.kernel`, and `@ti.func`.
  - Critical rule: kernels are called from Python scope; `@ti.func` is called
    only inside Taichi scope.

- `docs.taichi.graphics/website/docs/lang/articles/kernels/kernel_sync.md`
  - Explains GPU kernel queueing and `ti.sync()`.
  - Critical for reliable timing, profiling, and post-kernel diagnostics.

- `docs.taichi.graphics/website/docs/lang/articles/basic/field.md`
  - Defines `ti.field`, `ti.Vector.field`, 0D fields, shape/index rules, and
    no-slicing behavior.
  - Critical for population arrays, macroscopic fields, and scalar ledgers.

- `docs.taichi.graphics/website/docs/lang/articles/reference/differences_between_taichi_and_python_programs.md`
  - Lists Python features that do not translate directly into Taichi scope.
  - Critical for avoiding hidden logic bugs inside kernels.

- `docs.taichi.graphics/website/docs/lang/articles/reference/global_settings.md`
  - Covers `ti.init(arch=ti.cuda)`, `debug=True`, `device_memory_GB`,
    `default_fp`, `fast_math`, `offline_cache`, and profiler settings.

- `docs.taichi.graphics/website/docs/lang/articles/debug/debugging.md`
  - Debug-mode and bounds-checking guidance.

- `docs.taichi.graphics/website/docs/lang/articles/performance_tuning/performance.md`
  - Loop parallelization, block dimensions, reductions, BLS/TLS, and offline
    cache.

- `taichi/python/taichi/examples/simulation/karman_vortex_street.py`
  - Official simulation example useful as a Taichi idiom reference, not a
    phase-field LBM model.

## Project-Specific Interpretation

Taichi can reduce several TCLB-specific failure modes:

- no generated `Dynamics.R -> RT -> Lists.cpp` action indirection;
- no implicit `AddDensity` streaming semantics;
- explicit host/device boundary via Python scope and Taichi scope;
- explicit double buffers for distribution functions;
- direct Python-side post-processing and figure generation.

Taichi does not remove the hard physics problems:

- conservative Allen-Cahn or Cahn-Hilliard closure must still be derived;
- `h_i` population moments, `F_phi`, `rho(C)`, `mu`, and force insertion still
  require formal validation;
- wetting boundary conditions still need per-link mass/flux accounting;
- GPU correctness still depends on kernel ordering, double buffering, atomic
  reductions, precision, and boundary writes.

## Guardrails

- Keep the full downloaded documentation/source snapshots local-only.
- Do not treat a Taichi prototype as validated because it runs on GPU.
- Start with a single-phase D2Q9/D3Q19/D3Q27 smoke only to validate framework
  semantics.
- For phase-field work, implement and test in this order:
  1. population streaming and double-buffer ledger;
  2. bulk phase equation moments;
  3. boundedness and mass conservation;
  4. pressure/force closure;
  5. flat-wall wetting;
  6. cylinder/sphere wetting;
  7. dynamic impact.
