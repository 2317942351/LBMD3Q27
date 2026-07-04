# Stage18 Closure Completion Implementation

Date: 2026-07-03

Status:

```text
method_closure_implementation_compiles
validation_not_claimed
```

This document records the second Stage18 closure pass. The goal is to close the
mathematical and TCLB-stage gaps before running contact-angle validation.

## Implemented TCLB-Semantic Fixes

### 1. Removed legacy action exposure

The previous `LegacyRun` stage was removed from `Dynamics.R`. The clean model
now exposes only the explicit Stage18 action sequence. This prevents scripts
from accidentally invoking the inherited monolithic `Run()` path.

### 2. Near-wall phase stencil reconstruction

New helper path in `Dynamics.c.Rt`:

```text
stage18_phase_from_neighbor(dx,dy,dz)
stage18_gradPhi_reconstructed()
stage18_lapPhi_reconstructed()
```

When `GradPhiMode`, `LaplaceMode`, or `MuWallFluxMode` is enabled and the node
is near a solid neighbor, solid/invalid phase samples are replaced by:

```text
WallPhase, if valid
otherwise clamped local PhaseF
```

`Stage18_Mu()` now computes `mu` from the same selected Laplace value saved in
`lapPhi`. This avoids the previous problem where a reconstructed `lp` could be
computed but `calcMu()` would re-read the legacy stencil.

Remaining limitation:

This is a compact reconstructed stencil, not yet a full high-order
diffuse-solid or compact-stencil wetting implementation. It is the first
physically consistent wall-safe path.

### 3. Per-link passive wall h source

`WettingWriteMode` now means:

```text
0: shadow/off
1: full wall equilibrium h source
2: per-link passive h source
```

Mode 2 preserves existing wall/solid `h_i` populations except directions that
point to neighboring fluid cells:

```text
if SolidIndicator(e_i) < 0.5:
    h_i = WallPhase * Gamma_i(u=0)
```

New wall ledger fields:

```text
WallHLinkWriteCount
WallHMassBefore
WallHMassAfter
WallHNetMass
```

New global:

```text
WallHNetMassTotal
```

This makes wall mass injection auditable per node and globally. It is still a
passive source for next-step TCLB streaming, not a direct `PhaseF` overwrite.

### 4. Global mass-conservation interface

Strict global boundedness cannot be completed inside one local CUDA device
stage. Stage18 now exposes the required two-pass interface:

First pass ledgers:

```text
PhaseClippedMass
PhaseRedistributionWeightTotal
PhaseMassRedistributionWeight
PhaseCorrectionDelta
```

Second pass setting:

```text
PhaseGlobalCorrection
```

`PhaseBoundednessMode` now means:

```text
0: off
1: shadow ledger
2: local bounded h projection
3: apply externally computed global correction in the interface band
```

The required host/case-controller formula for mode 3 is:

```text
PhaseGlobalCorrection = -PhaseClippedMass / max(PhaseRedistributionWeightTotal, eps)
```

Then each eligible interface node applies:

```text
delta_h_i = w_i * PhaseGlobalCorrection * PhaseMassRedistributionWeight
```

This is the correct TCLB-compatible structure for strict mass correction:
global reduction first, then a separate write pass.

### 5. Force insertion audit and candidate mode

New fields:

```text
ForceHalfVelocityX/Y/Z
ForceMomentumBeforeX/Y/Z
ForceMomentumAfterX/Y/Z
ForceEquivalentInjectedX/Y/Z
```

`ForceInsertionMode` now affects the actual MRT force moment scale:

```text
0: legacy-compatible full mF scale
1: half mF candidate
```

This does not claim final Guo/MRT forcing correctness. It creates a controlled
candidate and an equivalent-momentum audit so force insertion can be compared
against the expected one-force update.

## Implemented Book-Method Fixes

### Conservative Allen-Cahn moment audit

In addition to zero-order closure, Stage18 now records first moment of the phase
source:

```text
PhaseFphiFirstMomentX
PhaseFphiFirstMomentY
PhaseFphiFirstMomentZ
```

This is needed because conservative Allen-Cahn closure is not only
`sum(F_phi)=0`; the first moment controls the interface sharpening/advection
term.

### Boundedness without hiding mass error

Mode 1 records clipping without writing.

Mode 2 is explicitly local and should be treated as a safety/debugging
projection.

Mode 3 is the methodologically correct global redistribution hook. Validation
must use the global ledger and correction if long-time mass conservation is part
of the claim.

## What Remains After This Pass

Still not complete until compiled and gated:

```text
full non-diagonal phase MRT
full Cahn-Hilliard branch
static droplet Laplace pressure validation
spurious-current validation
flat-wall contact-angle morphology validation
cylinder/sphere wetting validation
dynamic impact
```

The important change is that these validations will no longer be run on an
obviously unclosed stage graph.

## Required Next Checks

1. Full TCLB RT regeneration and CUDA build.
2. Source audit confirms:

```text
LegacyRun stage absent
Stage18_Mu uses selected lapPhi
WallPhasePopulationSource saves h
ForceInsertionMode appears in Dynamics.c
PhaseGlobalCorrection appears in Dynamics.c
```

3. Minimal smoke only:

```text
bulk 1-20 steps
flat wall 90 deg, WettingWriteMode=0
flat wall 90 deg, WettingWriteMode=2
```

No contact-angle validation should be claimed before these pass.

## Compile Result

Remote:

```text
yuan@192.168.1.16
```

Target:

```text
d3q27_pf_velocity_clean_2026_q27_stage18closure2
```

Binary:

```text
/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_clean_2026_q27_stage18closure2/main
```

Log:

```text
/home/yuan/lbm2026_stage18_closure2_compile_20260703.log
```

Result:

```text
STAGE18_SPLIT_SOURCE_AUDIT_OK=1
BUILD_RC=0
sha256=3f3784099aca12ca139df260bf994e95e4162a109d122710726ada15f5e7b2de
```

During the first compile attempt, TCLB exposed an important official semantics
constraint:

```text
Field stencil offsets must be compile-time constants.
```

The attempted helper `stage18_phase_from_neighbor(dx,dy,dz)` failed because it
wrapped `PhaseF(dx,dy,dz)` and `SolidIndicator(dx,dy,dz)` behind runtime integer
arguments. The implementation was corrected to explicit compile-time offset
accesses, for example `PhaseF(1,0,0)` and `SolidIndicator(1,0,0)`.
