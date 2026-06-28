# Stage14-B36 To B40 Execution Runbook

Date: 2026-06-27

Branch: `work/phasefield-c-reference-20260623`

Status: updated after B35-B37 runtime evidence on 2026-06-28.

B36 and B37 have been executed and rejected as repair candidates. B38 is no
longer a flat-wall contact-angle gate. The current B38 is a diagnostic
first-bad force ledger.

## Hard Gate Before B36

B36 is not allowed until all of the following exist:

```text
B33 non-USB runtime root
B33 b33_matrix_digest.json
B33 L0_full/b33_argmax_trace.json
B33 L1_noFmu/L2_noSurf/L3_noPressure/L4_zeroForce key summaries
B34 replay compare result for at least L0_full
Teacher MCP review of B33/B34 runtime evidence
```

The B34 pass condition is:

```text
ReplayMomentumDeltaG ~= 1.0 * ReplayMF
```

at B33 first-bad co-located nodes.

If this condition fails, B36 must not modify `calcMu`, `calcGradPhi`,
`F_surf`, or `F_mu`. The branch is MRT force insertion or replay timing.

## B36: Minimal Repair Candidate

B36 must implement exactly one selected branch, default off.

### Branch A: MRT Force Insertion / Replay Timing

Trigger:

```text
B34 replay compare fails:
ReplayMomentumDeltaG - 1.0*ReplayMF is not near zero
```

Code anchors:

```text
Dynamics.c.Rt:
  half-force velocity around U = m0[2:4] + 0.5*F_total/rho
  h update before g update
  mF[2:4] = momentum_force_injection_scale * F_total/rho
  m = m0 - (m0 - EQ + 0.5*mF)*Omega + mF
```

Allowed work:

```text
Add a shadow-only MomentumInsertionAuditMode
Record expected delta_g, actual delta_g, and residual at every B33 first-bad node
Only after proof, add an explicit MomentumClosureProbeMode candidate
```

Forbidden:

```text
Changing F_surf/F_mu formulas
Changing contact-angle or WallGhost code
```

### Branch B: `mu/lapPhi` First

Trigger:

```text
ReplayLapPhi or ReplayMu crosses before stress/F_mu/Ftotal/rho
```

Code anchors:

```text
calcMu(C)
STAGE13_PHASE_FOR_STENCIL
calcMuNoGhostShadow(C)
ReplayLapPhi
ReplayMu
```

Allowed candidate:

```text
Stage14B36MuStencilMode = 0 legacy, 1 no-ghost shadow, 2 guarded write candidate
```

Start with shadow-only:

```text
B36MuNoGhost
B36LapPhiNoGhost
B36MuDeltaGhost
B36FsurfNoGhost
```

### Branch C: `gradPhi/F_surf` First

Trigger:

```text
GradPhiNorm or FsurfNorm crosses before stress/F_mu
```

Code anchors:

```text
calcGradPhi()
calcGradPhiRawNoGhostShadow()
calc_Fs(mu, gradPhi)
```

Allowed candidate:

```text
Stage14B36SurfaceForceMode = 0 legacy, 1 no-ghost shadow, 2 bounded-gradient shadow, 3 explicit write candidate
```

### Branch D: Stress/F_mu Time-Level First

Trigger:

```text
B18FmuPostForce or StressPostForceNorm is huge
while mu/gradPhi/Fsurf are not first.
```

Code anchors:

```text
stage14_fmu_from_stress(...)
B18StressPreForce/PostForce/ForceExcluded/Incoming
FmuStressClosureMode
```

Allowed candidate:

```text
FmuStressClosureMode=3 force-excluded non-equilibrium candidate
FmuStressClosureMode=4 prefactor-tau shadow candidate
```

Do not replace `F_mu` by zero as a repair.

### Branch E: Prefactor Consistency

Trigger:

```text
B35 prefactor shadow shows the BGK-style (0.5-tau)/tau scaling resolves
the first-bad force scale and remains consistent with B34.
```

Code anchors:

```text
MRT F_mu: (0.5-tau)
BGK F_mu: (0.5-tau)/tau
```

Allowed candidate:

```text
FmuPrefactorMode = 0 legacy, 1 BGK-style shadow, 2 BGK-style write candidate
```

Requires literature check before write mode.

## B37: GradPhi Force-Consumer Cap Attempt

B37 was executed as a default-off force-consumer `gradPhi` cap candidate:

```text
case = wall_60to30_10
Density_l = 0.005
steps = 20
cap modes = shadow/write
caps = 20, 10, 5
```

B37 is rejected:

```text
cap_hit_fraction = 0.0 at first onset
step 15 |gradPhi| ~= 0.391
step 15 ForceOverRhoNorm ~= 8.854e5
step 20 ForceOverRhoNorm ~= 9.281e152
step 20 nonfinite_total = 1151148
```

Meaning:

```text
Excessive |gradPhi| is not the first-order root cause.
B37 must not be promoted as a repair.
```

## B38: First-Bad Force Ledger

B38 replaces the old contact-angle gate. It must run before any further write
candidate:

```text
case = wall_60to30_10
Density_l = 0.005
steps = 20
vtk_period = 1
vtk_field_set = b33ledger
Stage14B18ClosureDiagnosticsMode = 1
```

Required outputs:

```text
b38_key_summary.json
b38_argmax_trace.json
stage14_B38_first_bad_ledger_digest.json
stage14_B38_first_bad_ledger_digest.md
binary_sha256.txt
run.log / run.status / case_metadata.json
```

B38 pass criterion is diagnostic completeness, not physical stability:

```text
Identify whether the next branch is:
  mu_or_laplace_branch
  grad_or_surface_force_branch
  fmu_stress_timelevel_branch
  force_density_denominator_branch
  force_assembly_or_fmu_numerator_branch
```

## B39: Single Evidence-Selected Repair Candidate

Only after B38 and Teacher MCP review:

```text
Choose one branch only.
Keep it default-off.
Do not mix stress, denominator, pressure, wetting, and phase updates in one patch.
Verify with wall_60to30_10 20-step first.
```

If B38 shows stress/F_mu leads, B39 may target:

```text
FmuStressClosureMode candidate
Fmu prefactor consistency
pre-force or force-excluded non-equilibrium stress
```

If B38 shows denominator alone leads, B39 may target:

```text
force-density denominator closure derived from phase mixture/rho floor
```

If B38 shows mu/lapPhi or grad/Fsurf leads, B39 returns to stencil and surface
force reconstruction.

## B40: Stress Construction Audit

B39 showed that none of the existing `FmuStressClosureMode` choices is a
sufficient repair. Therefore B40 is not a short stability gate yet. It is a
stress construction audit.

```text
Audit:
  current relaxed-stress path
  incoming raw stress
  incoming non-equilibrium stress
  post-force shadow stress
  equilibrium stress subtraction
  MRT/BGK F_mu prefactor consistency
```

Only after B40 identifies a mathematically defensible stress path can a new
default-off write candidate be created. Flat-wall contact-angle validation
remains after the selected candidate survives a short stability re-gate.

## B40: Dynamic Impact Preflight

B40 is a preflight, not production impact.

Inputs required:

```text
B37 pass
B38 pass
B39 pass
selected B36 mode documented
default legacy behavior or explicit selected mode clearly stated
```

Preflight outputs:

```text
short dynamic setup only
force closure fields
mass/KE/spurious velocity
interface morphology frames
restartability check
```

Forbidden:

```text
large production impact run
paper claim
validation_passed wording
```

## Current Stop Point

As of 2026-06-28:

```text
B35 coupled numerator split completed.
B36 force-over-rho cap rejected.
B37 gradPhi force-consumer cap rejected.
Server reboot recovered /mnt/usb1t and P100 access.
B38 first-bad ledger is the immediate next operational action.
B39 mode matrix completed afterward and rejected all existing FmuStressClosureMode values.
B40 stress construction audit is now the immediate next operational action.
```
