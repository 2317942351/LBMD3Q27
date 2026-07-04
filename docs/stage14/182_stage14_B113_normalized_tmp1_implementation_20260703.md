# Stage14-B113 Normalized Tmp1 Implementation

Date: 2026-07-03
Branch: `work/phasefield-c-reference-20260623`
Status: `implemented_static_checked_not_built`

## Purpose

B113 implements the smallest confirmed solver repair from B112:

```text
PhaseEquationMode=0 -> legacy tmp1, unchanged default
PhaseEquationMode=1 -> normalized tmp1 using PhaseField_l / PhaseField_h
```

No GPU run was executed in this step. This is a source-level implementation and
static check only.

## Why This Patch Exists

B112 showed:

```text
F_phi D3Q27 moments are closed.
MRT heq sum is closed.
legacy tmp1 fails for non-[0,1] phase ranges.
```

The failing formula was:

```c
tmp1 = (1.0 - 4.0*(C - 0.5)*(C - 0.5))/IntWidth;
```

It assumes `PhaseField_l=0` and `PhaseField_h=1`, while the model exposes these
as configurable settings.

## Code Changes

Files changed:

- `third_party/tclb_snapshots/stage14_B111_slim_wall_h_quarantine/models/multiphase/d3q27_pf_velocity/Dynamics.R`
- `third_party/tclb_snapshots/stage14_B111_slim_wall_h_quarantine/models/multiphase/d3q27_pf_velocity/Dynamics.c.Rt`

### New diagnostics

Added fields and quantities:

```text
ReplayTmp1Legacy
ReplayTmp1Normalized
ReplayTmp1Mode
```

Existing diagnostics retained:

```text
ReplayTmp1
ReplayTmp1BoundedShadow
ReplayPhaseOutOfBoundsFlag
```

### Updated setting

`PhaseEquationMode` comment is now:

```text
0 legacy tmp1
1 normalized legacy source using PhaseField_l/h
higher modes reserved
```

Default remains `0`.

### New helper functions

Added:

```c
stage14_b113_tmp1_legacy(C)
stage14_b113_tmp1_normalized(C)
stage14_b113_tmp1_for_mode(C)
stage14_b113_record_tmp1_diagnostics(C, active_tmp1)
```

Normalized formula:

```c
q = (C - PhaseField_l) / (PhaseField_h - PhaseField_l);
tmp1 = abs(PhaseField_h - PhaseField_l) * 4.0 * q * (1.0 - q) / IntWidth;
```

If the span is degenerate, the helper falls back to legacy behavior.

### Replaced call sites

All active `tmp1` source sites now call the helper:

- `Init_distributions()`
- `CollisionMRT()`
- `CollisionBGK()`

Verified by `rg` that the old runtime pattern no longer appears in the active
snapshot.

## Static Checks

Passed:

```text
git diff --check -- Dynamics.R Dynamics.c.Rt
```

Source grep confirmed:

```text
ReplayTmp1Legacy
ReplayTmp1Normalized
ReplayTmp1Mode
stage14_b113_tmp1_for_mode
```

## Offline Formula Check

Using the B112 helper:

```text
range 0.0 1.0
C=0.0 legacy=0.0 normalized=0.0
C=0.5 legacy=0.25 normalized=0.25
C=1.0 legacy=0.0 normalized=0.0

range -1.0 1.0
C=-1.0 legacy=-2.0 normalized=0.0
C=0.0 legacy=0.0 normalized=0.5
C=1.0 legacy=0.0 normalized=0.0
```

Meaning:

- For the default `[0,1]` range, normalized mode matches legacy.
- For `[-1,1]`, normalized mode removes the erroneous negative source amplitude.

## What This Does Not Fix Yet

B113 does not solve:

- BGK `heq` inconsistency from B112.
- B60/B111 conservative boundedness.
- `calcMu` / `calcGradPhi` near-wall stencil validity.
- pressure/force closure.
- contact-angle recognition or droplet morphology.

It only removes a confirmed algebraic inconsistency in phase-source amplitude
while preserving legacy defaults.

## Next Gate

Recommended next step is B114:

1. Generate TCLB source from the modified snapshot.
2. Build on the P100 compile lane.
3. Run two short smoke cases:

```text
PhaseEquationMode=0, PhaseField_l/h=0/1
PhaseEquationMode=1, PhaseField_l/h=0/1
```

The first check must show no regression for `[0,1]`. A second synthetic
`[-1,1]` no-wall phase-source probe can then confirm `ReplayTmp1Normalized`
behaves correctly.

Claim limit:

Do not claim contact-angle improvement from B113 alone.
