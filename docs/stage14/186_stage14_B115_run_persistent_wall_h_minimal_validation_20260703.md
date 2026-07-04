# Stage14-B115 minimal validation: persistent wall-h attempt

Date: 2026-07-03
Branch: work/phasefield-c-reference-20260623

## Purpose

This was a necessary-only check. It did not run contact-angle validation, grid refinement, curved-wall cases, or long-time morphology cases.

The question was narrow:

> Does making the wall-origin h-population repair persistent in TCLB's saved h population stop the earliest flat-wall PhaseF / PhaseFromH blow-up?

## Code path tested

Local model snapshot:

- `third_party/tclb_snapshots/stage14_B115_persistent_wall_h_slim/models/multiphase/d3q27_pf_velocity/Dynamics.R`
- `third_party/tclb_snapshots/stage14_B115_persistent_wall_h_slim/models/multiphase/d3q27_pf_velocity/Dynamics.c.Rt`

B115 final tested implementation used the lower-cost `Run()`-tail persistence path, not a new TCLB stage. Reason: adding a new stage required regenerating `LatticeAccess.inc.cpp`, which stayed in RT generation for too long and was not necessary for this minimal question.

Key implementation points:

- Added setting `Stage14B115PersistentWallHMode`.
- Relaxed the entry gate in `stage14_b68_apply_wall_h_streaming_repair()` so B81/B85 can call it without enabling B68.
- In `calcPhaseF()`, avoided the old in-stage B81/B85 repair when B115 persistence mode is active.
- Added a `Run()` tail call:
  - after `CollisionMRT()` and `pnorm=sum(g)`;
  - before `BaseIter` saves h;
  - only when `Stage14B115PersistentWallHMode > 1.5` and B81/B85 is enabled.

This preserves the intended TCLB semantics: repaired h is saved by the existing `BaseIter` stage and can be streamed into the next iteration.

## Build result

Remote compile lane:

- `/home/yuan/src/TCLB_lbm2026_compile_lane`

Binary:

- `/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric_b115runpersist/main`

SHA256:

```text
6acfd6f64c4f9c14e426b3fe02988249edb081a5203348a903d878d9a68a0bfa
```

Notes:

- Full RT generation completed through `LatticeContainer.inc.cpp`.
- `LatticeAccess.inc.cpp` was reused from B113-slim because no new stage remained in the final B115 run-persist implementation.
- Source audit passed for the new setting and B115 call path.

## Minimal run

Run root:

- `/mnt/usb1t/RUNS/runs/stage14_B115_run_persist_min_20260703`

Case:

- `wall_t90_10`

Key settings:

```text
Density_h=1.0
Density_l=0.005
PhaseEquationMode=1
Stage14B115PersistentWallHMode=2
Stage14B81PhaseBoundaryReconMode=2
Stage14B85NoIncreaseReconMode=2
Stage14B81ReconDeltaCap=0.02
Stage14B68WallHStreamingMode=0
Stage14B83CurrentWallGhostFinalizeMode=0
Stage14B59PassiveWallHMode=0
```

Result:

```text
RUN_RC=0, but failcheck stopped at step 5 due to NaN in P.
```

Summary failures:

```text
nonfinite_PhaseField_step_5
nonfinite_ReplayForceOverRho_step_5
nonfinite_ReplayPhaseFromH_step_5
```

Step 5 extrema from `s2_replay_smoke_summary.json`:

```text
PhaseField nonfinite_count = 88342 / 737280
ReplayPhaseFromH nonfinite_count = 88342 / 737280
ReplayForceOverRho nonfinite_count = 181654 / 2211840
PhaseField max_abs ~= 1.27e308
ReplayForceOverRho max_abs ~= 1.10e290
```

Important diagnostic observation:

```text
B81Mode = 0 in output frames
B81WallLinkCount = 0
B81AppliedDeltaSum = 0
B81WriteApplied = 0
B85 fields also remain zero
```

This means the tested B115 path did not actually apply an effective wall-link reconstruction in the saved evidence frames. It is not a numerical parameter issue and should not be followed by more case sweeps.

## Interpretation

B115 produced a useful negative result.

The earlier hypothesis was partly right: writing wall-origin h repair only inside `calcPhaseF()` is not sufficient if the repaired h is not persisted into the active AddDensity h stream. However, the tested `Run()`-tail persistence did not solve the instability because it repairs the fluid-node incoming h after the current collision, while the earliest failure still appears in streamed `h` consumed by `calcPhaseF()` at step 5.

The evidence now points more narrowly to TCLB wall/solid source semantics:

1. The destabilizing h populations are likely emitted from wall/solid source nodes through TCLB streaming.
2. Repairing only the destination fluid node after `CollisionMRT()` is too late or is overwritten by the next wall/solid source behavior.
3. B81/B85 diagnostics staying zero shows the current repair path is not reaching the effective wall-link population set under this minimal field set and stage order.

## Next necessary code step

Do not run broader validation next.

The next fix should target the source-side h population semantics:

1. Audit `updateBoundary()` / bounceback behavior for h populations on `IamWall || IamSolid` nodes.
2. Make wall/solid h passive at the source before TCLB streaming, using bounded `WallGhost` / neutral fallback, not active bounceback h.
3. Ensure the source-side write is saved by an existing stage that already saves h, avoiding new stage generation.
4. Only then rerun the same single `wall_t90_10`, 10-step gate.

Acceptance for the next gate remains minimal:

```text
No NaN by step 10.
PhaseField nonfinite_count = 0.
ReplayPhaseFromH nonfinite_count = 0.
No contact-angle claim.
```

## Local evidence

Downloaded lightweight evidence:

- `artifacts/stage14_B115_run_persist_min_20260703/compile.log`
- `artifacts/stage14_B115_run_persist_min_20260703/s2_replay_smoke_summary.json`
- `artifacts/stage14_B115_run_persist_min_20260703/case_metadata.json`
- `artifacts/stage14_B115_run_persist_min_20260703/wall_t90_10_run.log`

Remote VTI retained but not downloaded:

- `/mnt/usb1t/RUNS/runs/stage14_B115_run_persist_min_20260703/wall_t90_10/output/case_VTK_P00_00000000.vti`
- `/mnt/usb1t/RUNS/runs/stage14_B115_run_persist_min_20260703/wall_t90_10/output/case_VTK_P00_00000005.vti`
