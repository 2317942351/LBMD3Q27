# TCLB Official Documentation Snapshot

Date: 2026-07-03

This directory is the local project anchor for TCLB official documentation and source references. It exists because the LBMD3Q27 repair work must follow TCLB model-development semantics rather than treating TCLB as a plain C array solver.

## Local Contents

- `TCLB_docs/`
  - Source snapshot of the official documentation repository downloaded from GitHub as a zip archive.
  - Public site: https://docs.tclb.io/
  - Source repository: https://github.com/CFD-GO/TCLB_docs
  - Recorded commit: see `TCLB_DOCS_COMMIT.txt`.

- `TCLB/`
  - Source snapshot of the official TCLB repository.
  - Repository: https://github.com/CFD-GO/TCLB
  - Recorded commit: see `TCLB_COMMIT.txt`.
  - The nested `.git` directory was removed intentionally so this project does not accidentally commit an embedded git repository.

## Key Official Files For Current Solver Repair

- `TCLB_docs/docs/5.-Model-development/basics.md`
  - Core model-development semantics.
  - Defines the role of `Dynamics.R`, `Dynamics.c`, `AddField`, `AddDensity`, `AddSetting`, `AddQuantity`, `AddNodeType`, `AddStage`, and `AddAction`.
  - Most important warning for this project: `AddDensity` is not a passive array. It is loaded with a predefined offset and participates in TCLB streaming semantics.

- `TCLB_docs/docs/tutorials/model-development/1.-finite-difference-wave-equation.md`
  - Minimal model structure: `conf.mk`, `Dynamics.R`, `Dynamics.c`, `Init()`, `Run()`, and `Color()`.

- `TCLB_docs/docs/tutorials/model-development/2.-D2Q9-Single-Relexation-Time.md`
  - LBM streaming/collision tutorial.
  - Shows that distribution functions should be declared with `AddDensity(...)` so TCLB handles streaming through density access.

- `TCLB_docs/docs/tutorials/model-development/3.-D2Q9-ShanChen-SRT.md`
  - TCLB multiphase contact-angle example, but it is pseudo-potential Shan-Chen, not phase-field Allen-Cahn/Cahn-Hilliard.
  - Use it for TCLB implementation idioms only, not as a direct physical formula source for the current phase-field wetting closure.

- `TCLB_docs/docs/tutorials/model-development/4.-D2Q9-HeatTransfer.md`
  - Double-distribution-function example with an additional scalar population.
  - Relevant for `h`-population producer-consumer timing, but still must be mapped carefully to the current D3Q27 phase-field model.

- `TCLB_docs/docs/tutorials/model-development/5.-SymbolicOperations_and_CLBM.md`
  - Moment-space and force-related implementation guidance.
  - Useful when auditing MRT force insertion and pressure/stress closure.

- `TCLB_docs/docs/XML-Reference/`
  - XML configuration reference for cases, geometry, parameters, setup elements, callbacks, and execution.

- `TCLB/models/`
  - Official model implementations. Use these as implementation-pattern references.

- `TCLB/src/`
  - RT templates and generated-code infrastructure.
  - Important files include `LatticeAccess.inc.cpp.Rt`, `Dynamics.h.Rt`, `Model.md.Rt`, and `tools/RT`.

## Project-Specific Interpretation

The current LBMD3Q27 failure must be audited against the TCLB model lifecycle:

```text
Dynamics.R declarations
  -> RT/source generation
  -> AddStage load/save field set
  -> Run()/Init()/auxiliary CudaDeviceFunction execution
  -> density streaming through AddDensity offsets
  -> field persistence through AddField saves
  -> VTI/AddQuantity output through get* functions
```

For the phase-field solver this means:

- `g` and `h` populations declared by `AddDensity` are streamed TCLB populations, not current-step C arrays.
- `PhaseF`, replay fields, and wall diagnostics must be `AddField` or `AddQuantity` outputs when they should not stream.
- Any write to `h` must be placed where the corresponding `AddStage(save=...)` actually persists it into the lattice state used by the next streaming step.
- Boundary, wall, and solid handling must be checked at the source side and consumer side. A fluid-node local repair can fail if wall/solid source populations still emit invalid streamed values.
- Adding settings, fields, stages, or densities changes generated source layout and requires full RT/source regeneration before a binary can be trusted.

## Guardrails For Future Work

- Do not directly port C-array code into TCLB without a producer-consumer timeline.
- Do not treat `AddDensity` variables as ordinary passive storage.
- Do not assume a diagnostic `AddQuantity` proves a field is persisted; persistence depends on `AddStage(save=...)`.
- Do not reuse pseudo-potential wetting formulas from official Shan-Chen examples as phase-field wetting physics.
- Do not claim contact-angle validation from shadow diagnostics, smoke tests, or short stability tests.
- Do not run dynamic impact until flat-wall phase-field boundedness, force closure, and static contact-angle gates are all passed.
