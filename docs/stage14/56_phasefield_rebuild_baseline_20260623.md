# Phase-Field Rebuild Baseline

Date: 2026-06-23

This document defines the next auditable starting point for modifying the TCLB
D3Q27 phase-field wetting model. It consolidates the useful Stage15/Stage17
work, freezes the routes that should not be continued, and states what must be
done before new physics edits are trusted.

This is a source and audit baseline, not a validation result.

## Baseline Identity

Repository:

```text
https://github.com/2317942351/LBMD3Q27
```

Current branch:

```text
stage15-dynamicCL-residual
```

Published PR:

```text
https://github.com/2317942351/LBMD3Q27/pull/1
```

Baseline tag to use after this document is committed:

```text
baseline/phasefield-rebuild-20260623
```

Active TCLB model snapshot:

```text
third_party/tclb_snapshots/stage9_analytic_wetting_diffuse_interface/
```

Active model path:

```text
third_party/tclb_snapshots/stage9_analytic_wetting_diffuse_interface/models/multiphase/d3q27_pf_velocity/
```

## Current Claim Level

Allowed:

```text
flat-wall static contact-angle evidence is documented and usable as a regression baseline
flat-wall calibrated measurement tools are usable for future regression gates
curved-wall failure modes are identified well enough to guide the next design
current branch is a good audit baseline for further work
```

Forbidden:

```text
validation_passed
curved cylinder/sphere wetting validated
dynamic impact foundation established
DynamicCL fixes the wetting problem
old curved-wall BC is acceptable for final work
compact-stencil direct write works on curved walls
```

## What Should Be Inherited

### 1. Flat-wall calibrated contact-angle baseline

The flat-wall compact-ghost path is the strongest positive result in the
current branch.

Recorded result:

```text
theta target 30 -> measured about 32.3 deg
theta target 45 -> measured about 45.0 deg
theta target 60 -> measured about 62.2 deg
theta target 90 -> measured about 89.8 deg
theta target 120 -> measured about 121.4 deg
theta target 135 -> measured about 137.6 deg
theta target 150 -> measured about 149.8 deg
```

Use this as a regression baseline only for flat-wall behavior. Do not transfer
the claim to cylinder or sphere geometry.

Primary evidence:

```text
docs/stage14/40_stage15D_calibrated_angle_reverses_pivot_20260620.md
docs/stage14/41_stage15D2_long_base_slow_monotonic_20260620.md
docs/stage14/42_stage15D3_mobility_controls_rate_20260620.md
docs/stage14/43_stage15D4_static_map_gate_closed_20260620.md
scripts/stage13/golden2_calibrated_angle.py
```

### 2. WallGhost as the single near-wall phase channel

The current useful direction is not another per-node formula swap. It is the
explicit channel:

```text
WallGhost -> STAGE13_PHASE_FOR_STENCIL -> gradPhi / lapPhi / mu / force
```

Useful implementation points:

```text
WallGhost is a separate field from PhaseF
raw solid sentinels are filtered by STAGE13_PHASE_FOR_STENCIL
gradPhi and Laplace paths consume STAGE13_PHASE_FOR_STENCIL
diagnostics expose ghost/fallback use counts
```

This channel should be retained, but it must be re-audited under TCLB execution
semantics before new curved-wall writes are enabled.

### 3. Compact-stencil diagnostics and flat-wall write

The compact-stencil diagnostics are useful:

```text
WallCSQQf
WallCSQQsRaw
WallCSQQsBounded
WallCSQResidual
WallCSQAppliedResidual
WallCSQStrictWriteReady
WettingPathId
```

The flat-wall write path is the only compact-stencil write path currently
allowed by baseline policy.

Current safety gate:

```text
compact_write = stage13_compact_write_requested() && (AnalyticSolidType < 1.5)
```

This gate should remain until curved-wall smoothing passes a shadow-first gate.

### 4. Calibrated measurement tools

Keep these as first-line diagnostics:

```text
scripts/stage13/golden2_calibrated_angle.py
scripts/stage13/golden_cyl_curved_angle.py
scripts/stage13/gate_c1_force_dir.py
scripts/stage13/read_cl_traj.py
```

Important lesson:

```text
unvalidated angle diagnostics caused at least one wrong pivot
```

Any new morphology claim must be backed by a known-truth synthetic measurement
or an explicitly calibrated postprocessor.

### 5. Force fixed-point instrumentation

The configurable force iteration fields and residual outputs are useful
instrumentation:

```text
ForceFixedTol
ForceFixedMaxIter
ForceIterResidual
ForceIterCount
```

They should remain, but they are not a substitute for wetting-boundary closure.

## What Must Be Frozen As History

### 1. Stage12 validation claims

Stage12 artifacts are useful negative and exploratory evidence. They must not
be promoted to validation. The decoupled response failures and geometry
confusion were part of the diagnostic path.

### 2. DynamicCL as a solution path

DynamicCL contains useful diagnostic lessons:

```text
wrong sign was identified and fixed
wall-zone theta context bug was identified
force direction tooling is useful
```

But in the current regime it showed essentially zero macroscopic contact-line
effect. It should be frozen as a diagnostic layer, not used as the next physics
lever.

Default for future baseline runs:

```text
DynamicCLMode = 0
DynamicCLCoeff = 0
```

### 3. WallGhostV2 refactor

The WallGhostV2 pivot was caused by an uncalibrated angle diagnostic. It was
reversed by the calibrated flat-wall measurement. Do not resurrect it unless a
new calibrated failure proves the current WallGhost channel is wrong.

### 4. Direct compact-stencil write on curved walls

Direct `q_s` writes onto the staircase cylinder wall caused NaNs. This path is
explicitly forbidden for curved geometry until a new smoothed boundary
representation passes shadow gates.

Forbidden condition:

```text
WallCompactStencilMode=2 and WallCompactStencilWriteAllowedFlag=1 on AnalyticSolidType>=2
```

### 5. Old curved-wall BC as a validation route

The old BC can be used as a negative control or runtime sanity check. It is not
accurate enough to validate cylinder/sphere contact angles.

## Current Curved-Wall Diagnosis

The open frontier is curved geometry.

Observed:

```text
compact-stencil direct write on cylinder -> NaN
write disabled control -> stable
gate-A flat-only compact write -> partial stability
acute theta=60 cylinder remains unstable
theta=90 cylinder reads about +25 deg high in gate-A result
```

Most likely structural cause:

```text
sharp staircase wall mask != analytic signed-distance surface
per-wall-node ghost writes inject jagged near-wall phase/gradient data
gradPhi / mu / surface force then amplify the jaggedness
```

Current recommended direction:

```text
Option B-i: diffuse solid indicator / smoothed boundary representation
```

This is supported only by offline evidence so far:

```text
docs/stage14/54_stage17_optionB_B1_diffuse_solid_validated_20260620.md
```

No solver implementation of Option B-i exists yet.

## Need For New Computation

No new computation is needed to define this baseline. The baseline is an audit
and source-control checkpoint.

New computation is required before any of the following claims:

```text
curved-wall fix works
diffuse-solid Option B improves the solver
C reference and TCLB agree
dynamic impact is ready
```

Required next compute sequence, after source edits only:

```text
1. source-level TCLB execution-semantics audit
2. compile gate on the isolated source lane
3. flat-wall regression: theta 30/90/150
4. cylinder shadow gate: theta 60/90/120, no dynamics write first
5. cylinder write gate only if shadow passes
6. sphere gate after cylinder
7. only then dynamic impact preflight
```

## Merge Policy

The branch can be merged as an audit baseline if reviewers accept the wording:

```text
audit baseline, not validation
flat-wall regression evidence retained
curved-wall unresolved
dynamic impact not established
```

If the goal is to keep `main` only for stable validated code, do not merge this
branch into `main`. Instead, keep the PR open as a draft and use the baseline
tag for future branches.

Recommended next working branch:

```text
work/phasefield-c-reference-20260623
```

or, for TCLB-only work after the C reference is specified:

```text
work/tclb-semantics-audit-20260623
```

## Next Engineering Task

Before editing the TCLB solver again, create a minimal phase-field C/C++
reference solver or complete an equivalent source-level TCLB execution
semantics audit.

The reference path should follow:

```text
reference_solvers/phasefield_d3q27_c/
```

The mature MCMP C++ codes may be used as a structural reference for:

```text
stage ordering
flag taxonomy
passive ghost treatment
boundary-fluid bounceback semantics
diagnostic output
benchmark ladder
```

They must not be used as a direct source of phase-field physics formulas.

