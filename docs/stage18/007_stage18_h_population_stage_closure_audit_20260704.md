# Stage18 h Population Stage Closure Audit, 2026-07-04

## Scope

This note records the Stage18 closure21-closure28 work on the clean TCLB phase-field model:

`third_party/tclb_snapshots/stage18_clean_phasefield_model/models/multiphase/d3q27_pf_velocity_clean_2026`

It is a solver/staging audit, not a contact-angle validation. The current smoke script may print `pass`; that only means no NaN was reported in `PhaseField` or `Stage18Violation`. It does not mean the streamed phase populations are physically closed.

## Producer-Consumer Timeline Under Audit

Current intended phase path:

```text
InitDistributions
  -> streamed h_i AddDensity initialized from PhaseF
Iteration:
  -> first population stage reads h_i
  -> compute PhaseF and phase collision h_post
  -> later stages compute geometry, gradPhi, mu, wetting, force, momentum
  -> final population stage must save h_i for next iteration
next Iteration:
  -> first population stage reads the saved streamed h_i
```

The critical TCLB rule confirmed from generated code:

```text
each stage RunElement = LoadElement -> ExecElement -> SaveElement -> Glob
action stages use snapshot tab0/tab1 transitions between stages
AddDensity populations are read/written through pop_* and push_* generated functions
AddField state must be read with accessors such as HCur0(0,0,0) unless loaded as a stage member
```

## Results

### closure21

Binary:

`/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_clean_2026_q27_stage18closure21/main`

SHA:

`7ea434be6c907b45d73d06e82e9d63e4ce284aaa285de32e83a98d1d61d5b7d2`

Run:

`/mnt/usb1t/RUNS/runs/stage18_closure21_smoke_3step_dense_20260703`

Finding: local `real_t C = PhaseF` fixed one immediate stale-value issue, but step 3 still used `repair=3` and wiped bulk to `PhaseF=0.5`. Not acceptable.

### closure22

Binary SHA:

`c16e1aba321662d46731abcbdec882c8436ad0b6bac675c6d6d8a8ae98c64212`

Runs:

`/mnt/usb1t/RUNS/runs/stage18_closure22_smoke_3step_dense_20260703`

`/mnt/usb1t/RUNS/runs/stage18_closure22_smoke_5step_dense_20260703`

Change: removed `ConservativeBoundednessCorrection` from the iteration action and let `PhaseFromH` update `PhaseF` from `hpost_sum` in the same stage.

Finding: removed the worst midpoint wipeout, but the run still relied on `repair=2` after step 1. This proved that the streamed `h_i` input itself was bad before phase collision.

### closure24

Binary SHA:

`de478c261562b148471fc7aca622e56a51c080d6f436c75bc25b3597636828af`

Run:

`/mnt/usb1t/RUNS/runs/stage18_closure24_hraw_5step_dense_20260704`

Change: added minimal raw h diagnostics:

```text
PhaseHRawSum
PhaseHRawMin
PhaseHRawMax
PhaseHRawNonfiniteCount
```

Finding:

```text
bulk step 1: rawBad up to 19 in some nodes
bulk step 2+: rawBad = 27 in all 122880 nodes
flat wall step 2+: rawBad = 18..27 in all nodes
```

This rules out contact-angle/wall geometry as the first root cause. The bulk case already loses valid streamed h populations.

### closure25

Binary SHA:

`70097d3c94497051b5e91b0e9037666b611eadc764994f62116ed2bb9f7f2a77`

Run:

`/mnt/usb1t/RUNS/runs/stage18_closure25_single_h_stage_5step_dense_20260704`

Change: made `IterationInput` call `Stage18_PhaseFromH`, so the first h-loaded stage performs phase reconstruction/collision instead of doing an empty h pass-through followed by a second h stage.

Finding: step 1 raw h is valid, but step 2+ still reads invalid h. This indicates that h written during the action is not becoming the next action's valid h input.

### closure26b

Binary SHA:

`9c28386918463b393d7436398ddfbf186fb8d62ddc472bf42e04c1e19893360b`

Run:

`/mnt/usb1t/RUNS/runs/stage18_closure26b_final_h_commit_5step_dense_20260704`

Change: attempted to save h in the final `MomentumCollision` stage via HCur bridge.

Finding: nonfinite h disappeared, but bulk alternated between the initialized droplet and all-zero phase. Generated-code inspection showed `HCur0..HCur26` were used as bare variables in `Stage18_MomentumCollision`; `pop_MomentumCollision` did not load those fields, so they were not valid stage members.

### closure27

Binary SHA:

`3bbe7cd521064a7959df8d1f2fc96f7ee08892446300274530f2e06b1cef6e9c`

Run:

`/mnt/usb1t/RUNS/runs/stage18_closure27_hcur_accessor_5step_dense_20260704`

Change: final h commit reads HCur through AddField accessors:

```c
h0 = HCur0(0,0,0);
...
h26 = HCur26(0,0,0);
```

Finding: bulk phase no longer alternates to zero, but step 2+ still has `rawBad=27` in the raw streamed h input. The apparent stable `PhaseF` is maintained by saved-field fallback, not by valid h streaming.

### closure28

Binary SHA:

`28d43c49e21fbb31baa0c34cd697995d85029fee3ed9e3795d80b75d5913ab43`

Run:

`/mnt/usb1t/RUNS/runs/stage18_closure28_full_final_commit_5step_dense_20260704`

Change: final `MomentumCollision` saves full persistent state plus g/h:

```text
save_populations
save_stage18_persistent_state
save_contract_audit
save_phase_audit
save_wall_audit
save_mass_audit
```

Finding: same core issue remains. Bulk step 2+ still reads invalid h and uses `repair=2`.

## Current Root-Cause Assessment

The first current blocker is not wetting, contact-angle detection, pressure closure, or F_mu. The bulk case fails the stricter h-population gate.

The current most likely root cause is:

```text
Stage18 still violates TCLB AddDensity lifecycle for h_i:
  valid h_post is computed and can be mirrored into PhaseF/HCur,
  but the actual streamed h_i read by the next action is not valid.
```

Two important sub-findings:

1. `PhaseF` can be made to look stable through saved-field fallback.
2. That is not acceptable, because the phase equation is then no longer advanced by its streamed h populations.

Therefore, all contact-angle validation must remain blocked until:

```text
bulk_20 step 1..N:
  PhaseHRawNonfiniteCount = 0 everywhere
  PhasePopulationRepairApplied = 0 everywhere
  PhaseHRawSum tracks PhaseHPostSum without fallback
```

## Next Required Work

1. Inspect generated TCLB storage layout for `h0..h26` and whether `save_populations` in the final stage writes to the snapshot used as the next action's `tab0`.
2. Compare with official TCLB phase-field or passive scalar examples that update a streamed population across multiple stages.
3. If TCLB cannot safely update h in a late stage after non-population stages, restructure Iteration so the phase and momentum populations are both updated in one monolithic final population stage, while geometry/grad/mu/force are prepared as fields in earlier stages.
4. Remove or hard-disable fallback as a validation condition. Fallback can remain as a diagnostic guard, but a physical gate must fail when `PhasePopulationRepairApplied > 0`.
5. Only after h streaming is valid in bulk should wall/wetting write paths be re-enabled.

## Space Note

The dense VTI files for closure21/22/24/25/26b/27/28 were deleted on the server to recover USB space. Lightweight artifacts remain:

```text
case.xml
run.log
run.stderr
run.status
stage18_smoke_analysis.json
stage18_smoke_frames.csv
binary_sha256.txt
status/manifests
```

The USB mount `/mnt/usb1t` was recovered from about 22G free to about 29G free. Keep future runs short or remove regenerable VTI immediately.
