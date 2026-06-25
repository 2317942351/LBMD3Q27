# Stage17B-B16 Corrected B11 Guardrail

Date: 2026-06-25

Status: `corrected_b11_guardrail_complete`

Claim limit: TCLB replay comparison only; not contact-angle validation.

## Purpose

B15 proved that the older B10/B11 mismatch was dominated by offline comparison
semantics:

```text
offline reconstructed phase + offline-fluid mask
```

mixed cells that TCLB classifies as boundary cells into a comparison intended to
be fluid-only.  B16 patches the B11 replay tool so future runs also emit a
corrected reference:

```text
periodic D3Q27 stencil applied to TCLB PhaseField
restricted to TCLB-fluid masks
```

This does not modify solver physics.  It makes the audit tool harder to misuse.

## Code Change

Updated:

```text
scripts/stage17/stage17B_B11_replay_compare.py
```

New corrected comparison fields:

```text
CorrectedReplayLapPhiOnTclbPhase
CorrectedReplayMuOnTclbPhase
CorrectedInitialReplayLapPhiOnTclbPhase
CorrectedInitialReplayMuOnTclbPhase
CorrectedInitialNoGhostReplayLapPhiOnTclbPhase
CorrectedInitialNoGhostReplayMuOnTclbPhase
```

New corrected masks:

```text
corrected_near_interface_tclb_phase_fluid
corrected_contact_core_tclb_phase_fluid
cylinder_overlap_boundary
outer_boundary
```

New classification behavior:

```text
primary_result = corrected_initial_replay_matches_tclb_phase_periodic_stencil
legacy_offline_diff_status = retired_as_solver_bug_evidence
```

when corrected initial `mu/lapPhi` residuals are roundoff-level.

## Run Setup

Remote input case:

```text
/mnt/usb1t/RUNS/runs/stage17B_B13_initial_stencil_split_20260625/
  cylinder_init090_b13_initial_stencil_split_s0001/case.xml
```

Remote input VTI:

```text
/mnt/usb1t/RUNS/runs/stage17B_B13_initial_stencil_split_20260625/
  cylinder_init090_b13_initial_stencil_split_s0001/output/case_VTK_P00_00000000.vti
```

Remote output:

```text
/home/yuan/stage17B_B16_corrected_b11_guardrail_20260625
```

Local artifacts:

```text
artifacts/stage17B_B16_corrected_b11_guardrail_20260625/
```

## Key Result

Classification:

```text
corrected_initial_replay_matches_tclb_phase_periodic_stencil
```

Legacy status:

```text
retired_as_solver_bug_evidence
```

Important numbers from the same B13 step-0 VTI:

| Quantity | Value |
|---|---:|
| Legacy `InitialReplayLapPhi` vs offline near-interface max abs diff | `1.5689882548145873` |
| Legacy `InitialReplayMu` vs offline near-interface max abs diff | `3.530223573332822e-04` |
| Corrected `InitialReplayLapPhi` vs TCLB-Phase periodic near-interface max abs diff | `2.456368441983159e-15` |
| Corrected `InitialReplayMu` vs TCLB-Phase periodic near-interface max abs diff | `6.335806445462167e-19` |
| Corrected no-ghost `InitialReplayLapPhi` near-interface max abs diff | `2.456368441983159e-15` |
| Corrected no-ghost `InitialReplayMu` near-interface max abs diff | `6.335806445462167e-19` |
| `InitialReplayWallGhostUsed` near-interface max abs | `38.0` |
| `InitialGhostDeltaLapPhi` near-interface max abs | `8.049116928532385e-16` |
| `InitialGhostDeltaMu` near-interface max abs | `1.810532924756067e-19` |
| Offline-fluid cells that are TCLB boundary cells | `51624` |

## Interpretation

1. The legacy B11 output still reports a nonzero difference against the old
   offline reconstruction.  That is retained for traceability, but it is no
   longer valid solver-bug evidence by itself.
2. The corrected initial replay comparison is roundoff-level for both
   `lapPhi` and `mu`.
3. Direct WallGhost substitution remains numerically irrelevant in this initial
   stencil test: current and no-ghost corrected residuals are identical at
   reported precision.
4. Future solver decisions should use `CorrectedInitial*OnTclbPhase` fields and
   `corrected_*_tclb_phase_fluid` masks before treating replay differences as
   physics bugs.

## Step-0 Replay Caution

At step 0, ordinary `ReplayLapPhi/ReplayMu` can still be non-representative of
the initialized internal state.  For initial-state audits, use:

```text
InitialReplayLapPhi
InitialReplayMu
CorrectedInitialReplayLapPhiOnTclbPhase
CorrectedInitialReplayMuOnTclbPhase
```

not ordinary `ReplayLapPhi/ReplayMu` alone.

## Consequence

B16 closes the tooling gap identified by B15.  The current evidence does not
support further solver patching on the basis of the old B10/B11 offline
mismatch.

The next physically meaningful question should move back to a currently active
failure mode, for example:

```text
flat-wall phase/momentum/pressure closure instability
or
controlled curved-wall write response after shadow-only diagnostics
```

but only with corrected TCLB-native masks and field references.

## Guardrails

B16 does not justify:

```text
contact-angle validation passed
controlled wetting write
dynamic impact setup
claiming WallGhost is unnecessary in general
changing solver physics from old B10/B11 residuals
```

B16 does justify:

```text
using corrected B11 output as the default replay audit baseline
retiring legacy offline-fluid-mask residuals as standalone solver-bug evidence
requiring TCLB PhaseField + TCLB fluid masks for future replay gates
```

## Files

Artifacts:

```text
artifacts/stage17B_B16_corrected_b11_guardrail_20260625/b11_replay_compare.json
artifacts/stage17B_B16_corrected_b11_guardrail_20260625/b11_replay_compare_summary.csv
```

Verification:

```text
python -m py_compile scripts/stage17/stage17B_B10_initial_cap_equilibrium.py scripts/stage17/stage17B_B11_replay_compare.py
git diff --check
```
