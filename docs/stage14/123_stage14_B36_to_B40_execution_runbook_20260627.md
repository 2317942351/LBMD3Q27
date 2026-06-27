# Stage14-B36 To B40 Execution Runbook

Date: 2026-06-27

Branch: `work/phasefield-c-reference-20260623`

Status: runbook only. B36-B40 cannot start until B33 runtime and B34 replay
comparison are complete.

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
ReplayMomentumDeltaG ~= 0.5 * ReplayMF
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
ReplayMomentumDeltaG - 0.5*ReplayMF is not near zero
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

## B37: Flat-Wall Short Stability Gate

Only after one B36 candidate is selected:

```text
case = wall_60to30_10
Density_l = 0.005
steps = 20, 100, 500
vtk_period = sparse after 20-step proof
```

Pass:

```text
No nonfinite
No step-15 force/rho spike
PhaseFromH remains diagnostically bounded
B34 replay relation still passes
```

Fail:

```text
Return to selected B36 branch.
Do not try another unrelated physics patch without explaining why the branch changed.
```

## B38: Flat-Wall Contact-Angle Gate

Only after B37 passes:

```text
equilibrium wall theta 30, 90, 150
decoupled wall 60->30
decoupled wall 120->150
```

Required outputs:

```text
angle JSON/CSV
2D morphology images
mass drift
kinetic energy
spurious velocity
force closure digest
```

Pass criterion:

```text
decoupled cases move toward target BC
morphology and angle metric agree
force closure does not rely on clamp/zero-force hacks
```

## B39: Sphere/Cylinder Regression

Only after B38:

1. rerun Stage17B diffuse-solid shadow for cylinder and sphere.
2. rerun controlled-write curved cases only if shadow continuity remains good.
3. run static curved contact-angle cases.
4. compare with flat-wall force closure fields to ensure no new near-wall
   `F_total/rho` spike appears.

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

As of this runbook, B36-B40 are blocked by:

```text
B33 runtime unavailable due to remote I/O/SSH issue
B34 replay comparison lacking B33 co-located vectors
```

The immediate next operational action is to restore SSH and rerun B33 on a
non-USB root.
