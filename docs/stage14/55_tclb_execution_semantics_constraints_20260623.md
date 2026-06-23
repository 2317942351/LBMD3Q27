# TCLB Execution Semantics Constraints

Date: 2026-06-23

This note records a hard constraint for the next wetting-boundary and
curved-wall repair stage.

The current evidence does not show that the official TCLB framework itself is
unable to solve phase-field wetting problems. The narrower and more useful
conclusion is:

```text
The migrated TCLB model must respect TCLB streaming, stage, and solid-node
semantics. Directly copying legacy C-array logic into TCLB templates is not a
valid implementation strategy.
```

## Why This Matters

The legacy C solver controls every array explicitly. Population buffers,
macroscopic fields, pseudo-potential values, ghost values, bounceback updates,
and diagnostics all have manually defined time levels.

TCLB does not work that way. Fields declared as streaming densities through
`AddDensity(dx=e_q)` are moved by the framework. Stages decide which density
groups and field groups are loaded and saved. Wall and solid nodes are not
automatically passive ghost arrays.

Therefore, a boundary formula can be mathematically correct and still be wrong
inside TCLB if it reads the wrong time level or stores a ghost value in a field
that later enters collision, streaming, or periodic transport.

## Hard Invariants

### 1. Streaming densities are not current-field caches

`AddDensity(dx=e_q)` variables are streamed by TCLB. They must not be treated as
arbitrary current-time arrays like `fin`, `fout`, `rho`, or `psi` in a legacy C
solver.

If wetting, force, or QIBB logic needs a current macroscopic field, it must use
an explicit non-streaming cache with a documented producer stage and consumer
stage.

Required audit evidence:

```text
field name
producer stage
consumer stage
whether it streams
whether it is valid on fluid, wall, and solid nodes
```

### 2. Coordinate alignment is part of the physics

TCLB outputs cell-centered `CellData`. The template coordinates `X`, `Y`, `Z`
must not be assumed identical to the legacy C array-index coordinates.

Any comparison against legacy C data or analytic droplet geometry must state
the coordinate convention and whether `CoordinateOffset=-0.5` or another offset
is active.

Required audit evidence:

```text
initial droplet center
solid center
wall plane location
cell-center convention
output interpretation convention
```

### 3. Ghost nodes must remain passive

In the legacy C solver, wall ghost nodes provide wall-side phase information.
They do not collide, stream, or inject populations into the fluid.

In TCLB, a wall or solid node can become active if its density populations are
allowed to collide, bounce back, or stream through periodic directions. This is
especially dangerous when the contact-angle ghost differs from the bulk phase.

Required audit evidence:

```text
wall/solid nodes do not perform fluid collision
wall/solid phase ghost is consumed only by intended near-wall stencil paths
wall/solid populations cannot re-enter the fluid through periodic streaming
mass diagnostics separate fluid-domain population mass from ghost/stale fields
```

### 4. Bounceback semantics must be verified per link

Legacy C selective halfway bounceback uses the boundary-fluid node's own
outgoing opposite population:

```text
fin[q] = fout[opp[q]]
```

A TCLB implementation that reads a ghost node's opposite distribution is not
equivalent unless proven per direction and per stage.

Required audit evidence:

```text
incoming link q
opposite link opp(q)
source population time level
source storage location
destination storage location
mass before and after bounce
```

This applies to flat walls and is mandatory for curved QIBB.

### 5. Periodic directions must not transport ghost bias

If a domain direction remains periodic, wall or solid populations and biased
phase values must be isolated from that periodic path. Otherwise, a wall
contact-angle phase bias can enter the bulk gas or liquid and become an
artificial condensation or evaporation source.

Required audit evidence:

```text
periodic directions in the case XML
solid/wall population groups participating in streaming
fields read by phase-gradient and chemical-potential stencils across periodic seams
```

### 6. Contact-angle clamping must match the intended time level

The legacy C code used current-field scans such as current `min_psi/max_psi`.
Replacing that with a fixed analytic clamp can be acceptable only if the
resulting bound is explicitly justified for the TCLB time level being used.

Required audit evidence:

```text
clamp source
clamp update frequency
fluid-only or all-node scan
effect on wall ghost values
effect on mass diagnostics
```

### 7. Diagnostics must distinguish physical mass from stale field output

TCLB output fields can include wall, solid, stale, or convenience quantities.
Mass drift inferred from an output scalar is not automatically population mass
drift.

Required audit evidence:

```text
fluid-mask mass
population-sum mass
output-field mass
ghost/wall contribution
solid contribution
```

### 8. Long-run Laplace differences remain open

Short bulk matching is not enough. A Laplace droplet long run previously showed
differences such as non-shrinking droplets, excessive velocity, and early
failure. Those symptoms point to unresolved stage, initialization, streaming,
stencil, or force-timing differences.

Before using the wetting model as a physical reference, the project must repeat
C-to-TCLB field comparison with:

```text
same initial field
same coordinate convention
same current-field cache semantics
same force timing
same wall/solid isolation policy
same diagnostic mask
```

### 9. Curved-wall QIBB is not complete until per-link semantics pass

Geometry diagnostics or scaffold code are not evidence that curved-wall physics
is reliable.

QIBB must be verified link by link:

```text
q distance per direction
pre-collision population source
post-collision population source
interpolated reflected population
mass contribution
solid/wall storage isolation
```

### 10. High density ratio is a model/EOS issue unless proven otherwise

Direct water-air density ratio failures should not be blamed on TCLB by
default. If the same parameter family fails in legacy C, it belongs to the
phase-field/pseudopotential/EOS stability envelope, not to the framework alone.

## Consequence For Compact-Stencil Wetting

The compact-stencil paper supplies the wall-side phase reconstruction logic:

```text
geometry normal -> fluid-side q_f -> contact-angle relation -> solid-side q_s
```

In TCLB, that is only part of a valid implementation. A solver patch must also
prove:

```text
q_f comes from the intended current-time non-streaming phase field
q_s is stored as a passive ghost quantity
q_s is consumed only by near-wall gradPhi/mu/Laplace paths
q_s cannot collide, stream, or enter periodic population paths
phase-gradient and chemical-potential consumers load the correct stage fields
mass and morphology diagnostics exclude stale ghost quantities unless reported separately
```

If these conditions are not proven, the implementation must remain:

```text
exploratory_not_validation
```

## Required Gates Before Further Solver Changes

Future changes must use this order:

```text
S0 static source semantics audit
S1 current-field cache audit
S2 passive ghost audit
S3 per-link bounce/QIBB audit
S4 C-to-TCLB bulk and wall replay
S5 compact-stencil runtime gate
```

The next solver modification should not begin from a formula edit. It should
begin by mapping TCLB density groups, field groups, `AddStage` save/load groups,
wall/solid update functions, near-wall stencil consumers, and periodic
directions used by each diagnostic case.
