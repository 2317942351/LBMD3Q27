# Stage17B-B13 Initial Stencil Split Diagnostic

Date: 2026-06-25

Status: `initial_stencil_split_complete`

Claim limit: this is a TCLB internal replay diagnostic only. It is not contact-angle validation, not a sphere/cylinder wetting validation, not a dynamic-impact preflight pass, and not a physical fix.

## Purpose

B12 proved two facts:

```text
step-0 PhaseField matches offline CylinderCapInit in the near-interface/contact-core masks
InitialReplayMu/InitialReplayLapPhi are nonzero before the first update
InitialReplayWallGhostUsed reaches 38 in the same near-interface region
```

B13 splits the initial stencil producer inside TCLB:

```text
same step-0 PhaseF
  -> current replay using STAGE13_PHASE_FOR_STENCIL with WallGhost substitution
  -> no-ghost shadow replay using the same TCLB stencil but ignoring WallGhost
  -> ghost-only delta = current - no-ghost
```

The goal is to test whether the B12 current-vs-offline discrepancy is caused directly by `WallGhost` value substitution.

## Code Changes

Snapshot:

```text
third_party/tclb_snapshots/stage17B_diffuse_solid_shadow/models/multiphase/d3q27_pf_velocity/
```

Added output-only fields in `Dynamics.R`:

```text
InitialNoGhostReplayLapPhi
InitialNoGhostReplayMu
InitialNoGhostReplayGradPhiX/Y/Z
InitialGhostDeltaLapPhi
InitialGhostDeltaMu
InitialGhostDeltaGradPhiX/Y/Z
InitialGhostStencilTouched
InitialGhostNeighborCount
InitialNoGhostPhaseStencilFallbackCount
```

Added matching `AddQuantity` entries and getters in `Dynamics.c.Rt`.

Added a no-ghost shadow selector:

```text
stage13_select_phase_for_stencil_no_ghost_shadow(...)
```

This selector deliberately ignores `WallGhost`. It returns valid `PhaseF`, then valid center `PhaseF`, then the phase midpoint fallback. It increments only B13 diagnostic counters.

Added shadow stencil functions:

```text
calcGradPhiRawNoGhostShadow()
calcMuNoGhostShadow(...)
```

These functions use the same TCLB stencil structure as `calcGradPhiRaw()` and `calcMu()`, but replace `STAGE13_PHASE_FOR_STENCIL` with `STAGE13_PHASE_FOR_STENCIL_NO_GHOST`.

The B13 path is called only inside `Init_distributions()` under `ReplayDiagnosticsMode`. It does not write:

```text
PhaseF
WallGhost
h
g
pnorm
```

## Static Gate

Local checks:

```text
python -m py_compile scripts/stage17/stage17B_B10_initial_cap_equilibrium.py scripts/stage17/stage17B_B11_replay_compare.py scripts/stage17/stage17B_shadow_source_audit.py
python scripts/stage17/stage17B_shadow_source_audit.py --out artifacts/stage17B_B13_initial_stencil_split_20260625/source_audit.json
git diff --check
```

Result:

```text
PASS_STAGE17B_SHADOW_SOURCE_GUARDRAILS
```

The source audit explicitly checks B13 fields, getters, no-ghost selector, no-ghost shadow functions, `Init_distributions()` wiring, and output-only guardrails.

## Build

Server:

```text
yuan@192.168.1.16
```

Compile lane:

```text
/home/yuan/src/TCLB_lbm2026_compile_lane
```

Build script:

```text
/home/yuan/stage17B_remote_build_shadow.sh
```

Build log:

```text
/home/yuan/stage17B_B13_full_build_20260625.log
```

Binary:

```text
/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
```

Binary SHA256:

```text
66cb03cd52ddc819ec7cebfbd7ed9c976827912db290bcc563a407466544f946
```

Build result:

```text
full TCLB source regeneration: complete
explicit Dynamics.c RT generation: complete
CUDA build: complete
```

## Runtime

Run root:

```text
/mnt/usb1t/RUNS/runs/stage17B_B13_initial_stencil_split_20260625
```

Case:

```text
cylinder_init090_b13_initial_stencil_split_s0001
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

Raw VTI files are retained on the server and are not committed:

```text
/mnt/usb1t/RUNS/runs/stage17B_B13_initial_stencil_split_20260625/cylinder_init090_b13_initial_stencil_split_s0001/output/case_VTK_P00_00000000.vti
/mnt/usb1t/RUNS/runs/stage17B_B13_initial_stencil_split_20260625/cylinder_init090_b13_initial_stencil_split_s0001/output/case_VTK_P00_00000001.vti
```

Local lightweight evidence:

```text
artifacts/stage17B_B13_initial_stencil_split_20260625/
```

## Key Result

Primary result:

```text
b13_no_significant_wallghost_delta_detected
```

Key step-0 values:

| Quantity | Value |
|---|---:|
| `PhaseField` near-interface TCLB-fluid max abs diff vs offline | `3.3306690738754696e-16` |
| `PhaseField` contact-core TCLB-fluid max abs diff vs offline | `2.220446049250313e-16` |
| current `InitialReplayMu` near-interface max abs diff vs offline | `3.530223573332822e-04` |
| no-ghost `InitialNoGhostReplayMu` near-interface max abs diff vs offline | `3.530223573332822e-04` |
| current `InitialReplayLapPhi` near-interface max abs diff vs offline | `1.5689882548145873` |
| no-ghost `InitialNoGhostReplayLapPhi` near-interface max abs diff vs offline | `1.5689882548145873` |
| `InitialGhostDeltaMu` near-interface max abs | `1.810532924756067e-19` |
| `InitialGhostDeltaLapPhi` near-interface max abs | `8.049116928532385e-16` |
| `InitialGhostDeltaMu` contact-core max abs | `1.7787691892340307e-19` |
| `InitialReplayWallGhostUsed` near-interface max abs | `38.0` |
| `InitialGhostNeighborCount` near-interface max abs | `38.0` |
| `InitialNoGhostPhaseStencilFallbackCount` near-interface max abs | `0.0` |
| no-ghost mu improvement vs current | `0.0` |
| no-ghost lap improvement vs current | `0.0` |

## Interpretation

B13 changes the root-cause tree.

The initial stencil does touch boundary-neighbor slots heavily:

```text
InitialReplayWallGhostUsed = 38
InitialGhostNeighborCount = 38
```

But disabling `WallGhost` in the no-ghost shadow replay does not change `mu` or `lapPhi` at meaningful precision:

```text
InitialGhostDeltaMu  ~ 1e-19
InitialGhostDeltaLapPhi ~ 1e-15
```

Therefore, the B12 current-vs-offline discrepancy is not explained by direct `WallGhost` value substitution. The stronger next hypothesis is:

```text
B10 offline operator / mask / coordinate reconstruction is not exactly the same
as TCLB's initial replay domain and boundary classification.
```

The boundary summary supports this direction:

```text
tclb_boundary_cells = 172968
offline_fluid_tclb_boundary_cells = 51624
offline_solid_tclb_fluid_cells = 0
```

So B14 should audit the TCLB-vs-offline geometry and mask equivalence before changing wetting physics.

## Next Gate

B14 should be a mask/operator equivalence gate:

```text
1. Export or reconstruct the exact TCLB fluid mask used by the stencil.
2. Compare offline solid/fluid classification against TCLB `IsItBoundary/BOUNDARY`.
3. Recompute offline lapPhi/mu using TCLB-fluid-only masks and the same fallback semantics.
4. Determine whether the B12/B13 current-vs-offline discrepancy disappears.
5. Only if the discrepancy persists after mask/operator alignment should the next branch inspect initialization profile equilibrium or h-update producer split.
```

Do not proceed to controlled wetting write, dynamic impact, or contact-angle validation based on B13 alone.

## Files

Committed lightweight evidence:

```text
artifacts/stage17B_B13_initial_stencil_split_20260625/source_audit.json
artifacts/stage17B_B13_initial_stencil_split_20260625/b13_key_summary.json
artifacts/stage17B_B13_initial_stencil_split_20260625/replay_compare/b11_replay_compare.json
artifacts/stage17B_B13_initial_stencil_split_20260625/replay_compare/b11_replay_compare_summary.csv
artifacts/stage17B_B13_initial_stencil_split_20260625/runtime_probe/run_manifest.txt
artifacts/stage17B_B13_initial_stencil_split_20260625/runtime_probe/binary_sha256.txt
artifacts/stage17B_B13_initial_stencil_split_20260625/runtime_probe/done.status
artifacts/stage17B_B13_initial_stencil_split_20260625/runtime_probe/cylinder_init090_b13_initial_stencil_split_s0001/case.xml
artifacts/stage17B_B13_initial_stencil_split_20260625/runtime_probe/cylinder_init090_b13_initial_stencil_split_s0001/case_metadata.json
artifacts/stage17B_B13_initial_stencil_split_20260625/runtime_probe/cylinder_init090_b13_initial_stencil_split_s0001/run.log
artifacts/stage17B_B13_initial_stencil_split_20260625/runtime_probe/cylinder_init090_b13_initial_stencil_split_s0001/run.status
artifacts/stage17B_B13_initial_stencil_split_20260625/runtime_probe/cylinder_init090_b13_initial_stencil_split_s0001/run.stderr
```
