# Stage17B Plan: Diffuse-Solid / Analytic-SDF Curved Wetting Boundary

Date: 2026-06-23

Status: planning and guardrail document. No contact-angle validation is claimed.

## Decision

Do not abandon the phase-field model. The working diagnosis is narrower:

```text
curved solid representation
wall normal consistency
near-wall PhaseF / ghost reconstruction
contact-angle constraint on staircase boundaries
```

Flat-wall evidence remains useful as a diagnostic baseline, but curved cylinder/sphere wetting must stop using local patching of the current staircase wall write path.

## Repository Policy

### Freeze Flat-Wall Baseline

The flat-wall compact ghost baseline should be treated as a regression baseline, not a place for new physics experiments.

Baseline policy:

```text
IntWidth W = 3
R >= 4W
M = 0.6 for accelerated relaxation only
DynamicCLMode = 0
WallGhostV2 = off / not resurrected
compact-stencil write allowed only on flat analytic walls
```

Current safety gate in `Boundary.c.Rt`:

```c
bool compact_write = stage13_compact_write_requested() && (AnalyticSolidType < 1.5);
```

This means cylinder and sphere cannot take the compact-stencil direct-write path even when an XML file requests `WallCompactStencilMode=2` and `WallCompactStencilWriteAllowedFlag=1`.

### Deprecated Routes

Do not continue investing in these as primary fixes:

```text
DynamicCL
WallGhostV2
Stage10 ghost chemical potential
ForceSign / ForceCap tuning
mobility tuning used to mask an error
old Stage12 BC as validation evidence
direct We-impact tests
cylinder-array capture / detachment
curved compact-stencil direct write
```

They can remain as historical negative controls or diagnostic references, but they are not the next solution path.

## Why Stage17B

The current curved-wall failure chain is likely:

```text
analytic cylinder/sphere geometry
  -> represented as TCLB staircase solid mask
  -> near-wall PhaseF / gradPhi / ghost use staircase topology
  -> contact-line gradient becomes jagged
  -> local surface-force and stress terms become abnormal
  -> velocity / pressure / PhaseF diverge
  -> NaN, leakage, or wrong morphology
```

The required replacement is a consistent curved-boundary layer:

```text
solid representation + smooth wall normal + near-wall phase reconstruction + contact-angle constraint
```

The next branch is:

```text
stage17B-diffuse-solid-curved-wetting
```

The branch target is only:

```text
static cylinder/sphere wetting stability and contact-angle correctness
```

It must not include dynamic impact, We sweeps, dynamic contact angle, cylinder arrays, detachment, or capture.

## Stage17B Technical Route

### B1: Offline Analytic Geometry Unit Tests

Do not start in the TCLB solver. First build a small Python/C test for analytic cylinder and sphere SDF.

Cylinder SDF:

```text
d(x) = sqrt((x - xc)^2 + (z - zc)^2) - R
```

Diffuse solid indicator:

```text
psi_s = 0.5 * (1 - tanh(d / (sqrt(2) * eps_s)))
eps_s ~= 1.0 to 1.5 lattice units
```

Smooth solid normal:

```text
n_s = grad(psi_s) / (|grad(psi_s)| + eps)
```

B1 checks:

```text
cylinder/sphere normal continuity
no contact-line normal jumps
PsiGradMag has no isolated spikes
theta = 60 / 90 / 120 predicted ghost is bounded
jaggedness metric improves over staircase mask normals
```

Only after B1 passes should TCLB fields be added.

### B2: TCLB Shadow-Only

Add fields, but do not write `PhaseF`.

Shadow diagnostics:

```text
PsiSolid
PsiGradMag
PsiNormalX/Y/Z
PsiWallGhost
PsiThetaImplied
PsiJaggedness
PsiWriteAllowedFlag
NearWallForceMag
NearWallGradPhiMag
```

Run first:

```text
cylinder theta = 60, 90, 120
steps = 1000, 2000, 12000
```

Pass conditions:

```text
NaN = 0
PhaseF remains bounded or only minimally overshoots
mass drift remains explainable
PsiNormal is continuous
NearWallGradPhi has no isolated spikes
implied theta moves in the target direction
```

### B3: Controlled Write Gate

Only after B2 passes, enable writes. Writes must be restricted to a safe near-wall band:

```text
distance_to_solid <= 1.5 to 2.0 lu
|grad psi_s| > threshold
not corner / not ambiguous normal
fluid-side stencil reconstructed from analytic-SDF / diffuse-solid fields
```

The write normal must come from diffuse-solid or analytic SDF normal, not staircase wall-node topology.

### B4: Static Cylinder Validation

Cylinder comes before sphere because it is the clearest exposed failure.

Matrix:

```text
theta = 60, 90, 120
W = 3
M = 0.6
R >= 4W
steps >= 30000
```

Gate:

```text
theta error <= 3 to 5 degrees
NaN = 0
mass drift small
droplet does not leak down the cylinder
left/right contact lines are approximately symmetric
spurious current does not spike near contact line
```

Do not start with 30 degrees. Strong wetting is a later stress test.

### B5: Static Sphere Validation

Sphere is harder because the contact line is closed and three-dimensional anisotropy is stronger.

Order:

```text
sphere theta = 90
sphere theta = 60
sphere theta = 120
sphere theta = 30
```

Do not move to sphere 30 until the first three sphere cases pass.

### B6: Low-We Impact Preflight

Only after static cylinder and sphere pass.

Impact cannot diagnose the boundary while static curved wetting is still open because it mixes:

```text
contact-angle BC
dynamic contact line
inertia
interface thickness
surface tension
density and viscosity ratios
spurious current
mass conservation
wall dissipation
```

## Immediate Code Guardrails

1. Keep `AnalyticSolidType < 1.5` compact-write gate.
2. Keep `scripts/stage13/gen_cyl_compact.py` blocked by default. It may only generate legacy negative controls with `--legacy-unsafe-curved-compact-write`.
3. Extend source audit to require the flat-only compact-write gate.
4. Any new Stage17B write mode must default to shadow-only.
5. Any new Stage17B write mode must have a separate explicit setting and cannot reuse flat-wall compact-write permission.

## Interaction With Stage14-74

Stage14-74 remains valid but scoped:

```text
flat-wall density-ratio-200 dense onset probe
early onset points away from tmp1/Fphi as primary trigger
stress/F_mu / force-over-rho feedback remains a real closure concern
```

It does not replace Stage17B and does not validate curved wetting. The next branch ordering is:

```text
preserve Stage14-74 as closure evidence
freeze flat-wall baseline
build Stage17B diffuse-solid shadow path
only then return to curved static angle validation
```

## Claim Limits

Allowed:

```text
flat wall: closed in diagnostic context
curved wall: unresolved
impact: not authorized
publication validation: not claimed
```

Forbidden:

```text
contact angle validation passed
dynamic impact basis is ready
curved compact-stencil write is fixed
PressureClosureMode or ForceFixedPointMode is a physical fix
```
