# Stage17B-B12 Initial Replay Diagnostic

Date: 2026-06-25

Status: `initial_replay_diagnostic_complete`

Claim limit: this is a TCLB internal replay diagnostic only. It is not contact-angle validation, not a sphere/cylinder wetting validation, and not a dynamic-impact preflight pass.

## Purpose

B11 proved that TCLB step-0 `PhaseField` in the near-wall interface/contact-core masks matches the offline `CylinderCapInit` reconstruction to machine precision, but the normal step-0 `ReplayLapPhi` and `ReplayMu` fields were zero-valued initial-output diagnostics. B12 adds output-only pre-collision/post-initialization replay fields to answer the missing question:

```text
After CylinderCapInit and before the first phase update, does TCLB internal
mu/lapPhi/gradPhi already show near-wall non-equilibrium?
```

## Code Changes

Snapshot:

```text
third_party/tclb_snapshots/stage17B_diffuse_solid_shadow/models/multiphase/d3q27_pf_velocity/
```

Added fields in `Dynamics.R`:

```text
InitialReplayLapPhi
InitialReplayMu
InitialReplayGradPhiX/Y/Z
InitialReplayWallGhostUsed
InitialReplayPhaseStencilFallbackCount
```

Added quantities:

```text
InitialReplayLapPhi
InitialReplayMu
InitialReplayGradPhi
InitialReplayWallGhostUsed
InitialReplayPhaseStencilFallbackCount
```

Added getters in `Dynamics.c.Rt` so TCLB generated output kernels compile.

`Init_distributions()` now writes the initial replay fields after phase initialization and before the first solver update. The stencil ghost/fallback counters are reset before `calcGradPhi()` so `InitialReplayWallGhostUsed` covers the initialization replay path through `gradPhi + mu/lapPhi`, not only `calcMu()`.

No physical path is changed. The new fields are output diagnostics gated by `ReplayDiagnosticsMode`.

## Build

Server:

```text
yuan@192.168.1.16
```

Compile lane:

```text
/home/yuan/src/TCLB_lbm2026_compile_lane
```

Binary:

```text
/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
```

Binary SHA256:

```text
5329438f60131855611961fc368e70bd850c87624f3d9de6e9369f23f0bba406
```

Build log:

```text
/home/yuan/stage17B_B12_full_build_countermove_20260625_155317.log
```

Important build lesson: adding `AddField/AddQuantity` requires full TCLB source regeneration. Narrow regeneration of `Dynamics.c` alone leaves `Lattice.cu`/`LatticeContainer`/quantity accessors inconsistent.

## Runtime

Run root:

```text
/mnt/usb1t/RUNS/runs/stage17B_B12_initial_replay_20260625
```

Case:

```text
cylinder_init090_b12_initial_replay_s0001
```

GPU:

```text
CUDA_VISIBLE_DEVICES=1
Tesla P100-PCIE-16GB
```

Run result:

```text
RC=0
```

VTI frames:

```text
output/case_VTK_P00_00000000.vti
output/case_VTK_P00_00000001.vti
```

The VTI files are large raw outputs and are not committed. They remain on the server run root. Local lightweight evidence is under:

```text
artifacts/stage17B_B12_initial_replay_20260625/
```

## Evidence Summary

Analyzer:

```text
scripts/stage17/stage17B_B11_replay_compare.py
```

The analyzer now has a VTK-free VTI XML/base64 fallback reader, so B12 can be reproduced without installing the heavy `vtk` Python package.

Key artifact:

```text
artifacts/stage17B_B12_initial_replay_20260625/b12_key_summary.json
```

Step-0 classification:

```text
primary_result = initial_replay_mu_differs_from_offline_reconstruction
```

Critical numbers:

| Quantity | Region | Value |
|---|---:|---:|
| `PhaseField` max abs diff vs offline | near-interface TCLB fluid | `3.33e-16` |
| `PhaseField` max abs diff vs offline | contact-core TCLB fluid | `2.22e-16` |
| `InitialReplayMu` max abs diff vs offline periodic stencil | near-interface TCLB fluid | `3.530e-04` |
| `InitialReplayLapPhi` max abs diff vs offline periodic stencil | near-interface TCLB fluid | `1.569` |
| `InitialReplayWallGhostUsed` max | near-interface TCLB fluid | `38` |
| `InitialReplayPhaseStencilFallbackCount` max | near-interface TCLB fluid | `0` |

Step-0 `InitialReplayMu` is nonzero in the near-wall interface:

```text
near-interface TCLB fluid:
  min      = -5.668966893213265e-05
  max      =  5.545489226169244e-05
  mean     =  2.602450711771746e-06
  std      =  1.454886404943444e-05
  max_abs  =  5.668966893213265e-05

contact-core TCLB fluid:
  min      = -5.668966893213265e-05
  max      =  5.545489226169244e-05
  mean     =  3.515114277813410e-06
  std      =  2.625569748298991e-05
  max_abs  =  5.668966893213265e-05
```

## Interpretation

1. B12 closes the B11 ambiguity: step-0 `ReplayMu/ReplayLapPhi` were zero because they were not produced for the initial VTI, not because the internal initial chemical-potential path was zero.

2. The true initial replay fields show nonzero near-wall chemical potential before the first update. This supports the current mainline: the early neutral drift can originate from an initial discrete nonequilibrium release path, not from a late contact-angle morphology metric alone.

3. B12 does not exactly match B10's offline periodic-stencil reconstruction. That is expected and important: B12 records the TCLB internal stencil path, and it shows strong wall-ghost consumption in the same masks.

4. `InitialReplayWallGhostUsed max = 38` and `InitialReplayPhaseStencilFallbackCount max = 0` means the discrepancy is not caused by sentinel fallback. It is a deliberate wall-ghost substitution path being consumed during the initialization replay.

## Current Verdict

B12 points to a narrower root-cause branch:

```text
CylinderCapInit matches step-0 PhaseField
  -> internal initial gradPhi/mu/lapPhi are already nonzero
  -> internal path consumes WallGhost heavily near the contact region
  -> B10 offline periodic stencil is not the same operator as TCLB initial replay
```

Therefore, the next gate should not tune `DynamicCL`, `ForceCap`, `M`, or contact-angle formulas. It should split the initial stencil producer:

```text
B13: initial stencil split
  A. current TCLB initial replay with wall ghost
  B. shadow periodic/no-ghost replay using the same PhaseF
  C. ghost-only delta field for gradPhi/lapPhi/mu
  D. step-1 h-update producer split if A/B/C do not explain the release
```

Only after this split is understood should solver physics be changed.

## Files

Committed lightweight evidence:

```text
artifacts/stage17B_B12_initial_replay_20260625/source_audit.json
artifacts/stage17B_B12_initial_replay_20260625/b12_key_summary.json
artifacts/stage17B_B12_initial_replay_20260625/replay_compare/b11_replay_compare.json
artifacts/stage17B_B12_initial_replay_20260625/replay_compare/b11_replay_compare_summary.csv
artifacts/stage17B_B12_initial_replay_20260625/runtime_probe/run_manifest.txt
artifacts/stage17B_B12_initial_replay_20260625/runtime_probe/binary_sha256.txt
artifacts/stage17B_B12_initial_replay_20260625/runtime_probe/done.status
artifacts/stage17B_B12_initial_replay_20260625/runtime_probe/cylinder_init090_b12_initial_replay_s0001/case.xml
artifacts/stage17B_B12_initial_replay_20260625/runtime_probe/cylinder_init090_b12_initial_replay_s0001/case_metadata.json
artifacts/stage17B_B12_initial_replay_20260625/runtime_probe/cylinder_init090_b12_initial_replay_s0001/run.log
artifacts/stage17B_B12_initial_replay_20260625/runtime_probe/cylinder_init090_b12_initial_replay_s0001/run.status
artifacts/stage17B_B12_initial_replay_20260625/runtime_probe/cylinder_init090_b12_initial_replay_s0001/run.stderr
```

Raw VTI location:

```text
/mnt/usb1t/RUNS/runs/stage17B_B12_initial_replay_20260625/cylinder_init090_b12_initial_replay_s0001/output/
```
