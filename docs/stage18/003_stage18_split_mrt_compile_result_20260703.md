# Stage18 Split MRT Compile Result

Date: 2026-07-03

## Result

Stage18 clean phase-field model source generation and CUDA build passed on the remote TCLB compile lane.

```text
remote: yuan@192.168.1.16
compile lane: /home/yuan/src/TCLB_lbm2026_compile_lane
target: CLB/d3q27_pf_velocity_clean_2026_q27_stage18split
binary: /home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_clean_2026_q27_stage18split/main
sha256: e59b2e7567c1fe5d1f3f8bb7cdb5cda1f1f8a4a54f7a57943f0fe71c79a06864
log: /home/yuan/lbm2026_stage18_clean_split_mrt_compile_20260703.log
```

The log contains:

```text
STAGE18_SPLIT_SOURCE_AUDIT_OK=1
BUILD_RC=0
```

## What Changed

The clean Stage18 action no longer calls the inherited monolithic `CollisionMRT()` path. The action now exposes the TCLB producer-consumer chain:

```text
IterationInput
  -> PhaseFromH
  -> GeometryBuild
  -> GradPhi
  -> Mu
  -> WettingBoundary
  -> ForceClosure
  -> MomentumCollision
  -> PhaseCollision
  -> ConservativeBoundednessCorrection
  -> AuditSlim
```

`IterationInput` explicitly loads and re-saves streamed `g_i/h_i` populations from the previous framework streaming step. This makes later stages consume action-local declared values instead of implicit C-array state.

## MRT Policy

`Stage18_MomentumCollision()` now transforms and reconstructs all 27 `g_i` moments:

```text
m0 = M * g
g_after = invM * m_after
```

The relaxation spectrum is explicit:

```text
MomentumMRTMode = 1
shear omega = 1/tau or MRTShearOmegaOverride
bulk/high-order omega = MRTBulkOmega
all configurable omega values are clamped to [MRTMinOmega, MRTMaxOmega]
```

This is the current book-guided robust MRT repair for the momentum population. It is not yet a non-diagonal phase MRT. The phase population `h_i` remains in the split `Stage18_PhaseCollision()` path so its `heq/F_phi` source moments can be audited independently.

## TCLB Structural Fixes

- Added `InitForceAudit` to initialize force and audit fields in `Init`.
- Marked external initialization populations as `non.mandatory=TRUE`.
- Removed the old `LegacyIteration` action from the clean model.
- Downgraded inherited `Run()` to a compatibility no-op so clean actions cannot accidentally re-enter old boundary/collision sequencing.
- Replaced clean-stage force helper calls with `stage18_calc_Fp/Fb/Fs` to avoid generated member redeclaration conflicts.
- Reduced legacy global/tracker helpers to the globals actually declared by Stage18.
- Added `getGradPhi()` to satisfy `AddQuantity("GradPhi", vector=TRUE)`.

## Meaning

This compile result proves that the clean Stage18 split-collision architecture is syntactically and structurally acceptable to TCLB source generation and CUDA compilation.

It does not prove:

```text
phase boundedness
contact angle correctness
wetting boundary correctness
dynamic impact readiness
```

The next gate should be a minimal Stage18 runtime smoke focused on:

```text
PhaseFromH boundedness
g/h streaming consistency
force insertion audit
bulk or neutral-wall stability
```
