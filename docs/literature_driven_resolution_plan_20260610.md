# Literature-Driven Resolution Plan

Date: 2026-06-10
Status: planning artifact, exploratory_not_validation until executed and audited

## Purpose

This plan converts the 2025 TCLB wetting-boundary article evidence and the
current project audit into an executable sequence.

The immediate question is:

```text
Is the current center low-phase/void morphology caused by
1) a wrong wetting boundary,
2) an unresolved gas film/dimple/interface-thickness problem,
3) wrong effective surface tension or dimensionless mapping,
4) beta/contact-line postprocessing,
5) or a real physical air-entrapment feature?
```

The current evidence does not support continuing long target impact runs as
validation. The next work must close the above causes in a controlled order.

## Literature Lessons To Enforce

### Lesson 1: Static Boundary Angle Is Necessary But Not Sufficient

Source evidence:

- Sashko et al. 2025 compare surface-energy and geometric wetting boundaries.
- They show differences are most visible in dynamic/late regions, not only in
  static apparent contact angle.
- The paper explicitly notes that early inertia-dominated impact behavior can
  match even when the wetting-boundary treatment later differs.

Project consequence:

```text
The current two-row static contact-angle pass cannot validate dynamic impact.
```

Therefore every dynamic impact gate must include:

- first-fluid-layer contact state;
- second-fluid-layer contact state;
- center-gas/outer-liquid-ring event;
- beta definitions;
- mass/rho/Mach/nonfinite;
- morphology review.

### Lesson 2: Thin Films Below Interface Resolution Are Not Trustworthy

Source evidence:

- In the Mitra comparison in Sashko et al. 2025, the authors state that the
  experimental minimum film thickness `h*_exp = 0.01` is only one cell in their
  mesh.
- They report deviation and eventual interface tearing when
  `h*_simulation < 0.06`, about six cells and close to `xi=5`.

Project consequence:

```text
If the relevant gas film/dimple/center bubble is O(IntWidth) or only a few
cells, it cannot be accepted as resolved physical evidence.
```

For current 10 uL theta57:

- R25: `dx=53.46 um`, `IntWidth=6 lu=321 um`.
- R40: `dx=33.41 um`, `IntWidth=6 lu=200.5 um`.
- Expected physical bubble diameter is order `20-100 um`.
- Current R40 center low-phase equivalent diameter is about `728 um`.

This means:

```text
the simulated center feature is not a resolved 20-100 um physical bubble.
```

### Lesson 3: Mobility Is A Dynamic Wetting Parameter

Source evidence:

- Sashko et al. 2025 capillary intrusion test sweeps
  `M in {0.025, 0.05, 0.075}`.
- Surface-energy is more mobility-sensitive at low contact angle.
- Geometric + staircase can reduce sensitivity in some low-angle cases.

Project consequence:

```text
M must be swept in dynamic wetting/contact-line tests, not only chosen from
static contact-angle success.
```

Current project evidence is consistent with this:

- q27 Li-impact M/IntWidth sweep showed `M=0.01` avoided the first-fluid
  center-gas ring by the current short-run criterion;
- larger `M` and smaller `IntWidth` produced earlier/stronger annular contact.

### Lesson 4: Surface Tension Must Use sigma_eff

Source evidence:

- The phase-field model contains input `sigma`, but impact dimensionless groups
  depend on effective pressure-jump surface tension.
- The project q27 Laplace sweep found a linear mapping:

```text
laplace_slope = A_q27 * sigma_input + B_q27
A_q27 = 1.6279932875649252
B_q27 = 4.533658854592553e-06
sigma_eff = laplace_slope / 2
```

Project consequence:

```text
Do not define We, Bo, Oh, or target impact velocity from sigma_input alone.
Use sigma_eff and record the calibration.
```

### Lesson 5: Postprocessing Is Not The Main Remaining Cause

Source/project evidence:

- Multiple beta definitions in the q27 Li-impact analogue gave beta around
  `1.50-1.51`.
- The old four-layer projection was not the sole reason for maximum-spreading
  discrepancy.
- Wall-ghost `PhaseField` can copy/reflect the first fluid layer and is not an
  independent physical liquid layer.
- However, center gas with outer liquid ring also appears in the first fluid
  layer, so the issue is not just wall-ghost plotting.

Project consequence:

```text
Continue reporting multiple beta definitions, but focus diagnosis on dynamic
wetting/gas drainage/interface resolution.
```

## Execution Gates

### Gate A: Clean Source And Binary Audit

Purpose:

```text
Ensure official benchmark reproduction is not contaminated by exploratory
initializer patches.
```

Actions:

1. Read HM570 source patch state for:
   - `Dynamics.R`;
   - `Dynamics.c.Rt`;
   - `Boundary.c.Rt`;
   - generated `Consts.h` for each binary.
2. Build or record these binaries:
   - `surface_q27`;
   - `surface_q27_staircaseimp`;
   - `geometric_q27`;
   - `geometric_q27_staircaseimp`;
   - optional `geometric_q27_staircaseimp_tprec`.
3. Confirm composite-tail parameters are default-off and absent from official
   benchmark XMLs, or rebuild from a clean source checkout.

Required report:

```text
binary path
SHA256
compile options
build log
source patch state
whether q27 phase field is enabled
whether geometric/surface/staircase branch is enabled
```

Stop condition:

- any hidden patch affects standard droplet, sphere, capillary, or wall
  initialization;
- binary options cannot be verified.

### Gate B: Sphere Spread Static Curved-Wetting Reproduction

Literature basis:

- Sashko et al. 2025 first validate wetting boundaries with droplet spreading
  on a sphere against analytical spherical-cap geometry.
- Setup: `128^3`, `R_d=R_s=24`, `rho*=1000`, `mu*=100`, `M=0.05`,
  `xi=5`, `sigma=0.01`, periodic domain, bounce-back + wetting sphere,
  contact angles `30-130 deg`.
- Grid dependence uses `R in {12,24,48}` at constant `Cn=xi/R=5/12`.
- Main metric is nondimensional height `h* = h/(2 R_d)` against Eq. 57.

Minimum execution:

```text
variants:
  surface_q27
  geometric_q27
  surface_q27_staircaseimp
  geometric_q27_staircaseimp

base case:
  domain = 128^3
  R_d = 24
  R_s = 24
  rho* = 1000
  mu* = 100
  M = 0.05
  IntWidth = 5
  sigma_input = 0.01 first, with sigma_eff reported if q27 route requires it
  theta = 30, 60, 90, 120, 130 deg

optional after base:
  R = 12, 24, 48 with constant Cn = 5/12
```

Outputs:

- case XML;
- run.log;
- generated config;
- summary JSON;
- `h*`;
- analytical `h*`;
- relative error;
- mass/rho drift;
- max Mach;
- nonfinite;
- final morphology;
- overlay showing sphere, phi=0.5 interface, top height, and contact region.

Pass decision:

- If sphere spread cannot reproduce article-level behavior, stop planar impact
  escalation and debug wetting/source/boundary implementation.
- If it passes only for surface or only for geometric, use that branch for
  later dynamic tests but record the branch-specific limitation.
- If staircase changes low/high angle behavior as article suggests, keep it as
  evidence; do not assume it fixes flat-wall center void.

### Gate C: Capillary Intrusion Dynamic Wetting Reproduction

Literature basis:

- Sashko et al. 2025 use capillary intrusion against a Washburn-type analytical
  solution to test dynamic wetting.
- Coarse case: `256 x 12 x 12`, pipe `R=5`, `L=20R`, reservoir `L0=96`,
  `rho*=1000`, `mu*=100`, `M=0.05`, `xi=5`, `La=1`, theta `20-80 deg`.
- Refined case: `512 x 22 x 22`, `R=10`.
- Mobility sensitivity: `M in {0.025, 0.05, 0.075}` at `t*=30`.

Minimum execution:

```text
variants:
  geometric_q27
  surface_q27
  geometric_q27_staircaseimp if cost allows

coarse:
  theta = 20, 40, 60, 80 deg
  M = 0.05
  R = 5

refined:
  theta = 20 and 60 deg
  M = 0.05
  R = 10

mobility:
  theta = 20 and 60 deg
  M = 0.025, 0.05, 0.075
  R = 10
```

Outputs:

- front position `x(t)`;
- nondimensional `x*(t*)`;
- comparison to Eq. 58;
- error at article comparison time;
- mass/rho drift;
- max Mach;
- nonfinite;
- interface morphology.

Pass decision:

- If `M` sensitivity is strong, use it to define the planar impact `M` range.
- If low-angle under-resolution is reproduced and improves with `R=10`, this
  supports the current interpretation that center void needs grid/interface
  resolution, not just beta correction.

### Gate D: Sphere Impact Dynamic Curved Benchmark

Literature basis:

- Sashko et al. 2025 sphere impact tests show wetting methods are
  indistinguishable in early inertia-dominated regions but differ in the third
  region.
- Method comparison setup: `160 x 352 x 160`, `R_d=28`, `R_s=35`,
  `rho*=1000`, `mu*=100`, `M=0.05`, `H=200`, gravity-driven,
  `Re=60`, `We=6`, `Bo=0.84`, theta `20-120 deg`.
- Mitra comparison: `theta=86`, `Re=2891`, `We=43.7`, `M=0.02`,
  `R_s=58`, `288 x 512 x 288`.

Minimum execution:

```text
first pass:
  Re = 60
  We = 6
  theta = 40, 80, 120 deg
  variants = surface_q27, geometric_q27
  optional = +staircase variants

defer:
  Mitra Re=2891/We=43.7 until resource and Mach mapping are audited
```

Outputs:

- nondimensional height/film metric `h*(t*)`;
- region R1/R2/R3 behavior;
- morphology snapshots;
- mass/rho drift;
- max Mach;
- nonfinite.

Pass decision:

- Matching early R1/R2 is not enough.
- Require interpretable third-region behavior and no unresolved tearing.

### Gate E: Planar Dynamic Wetting Matrix

Literature basis:

- Capillary intrusion shows `M` sensitivity.
- Sphere impact shows late dynamic wetting matters.
- Mitra comparison warns about unresolved thin films near `xi`.

Purpose:

```text
classify the center void in planar impact before any target production run
```

Recommended matrix:

```text
case:
  q27 geometric dry wall
  theta090 first
  R = 24 or 32
  D = 2R
  wall = z-min
  velocity scaled so max Mach target < 0.05

M:
  0.005
  0.01
  0.025

IntWidth:
  4
  6
  8

run window:
  contact to shortly after beta_max
  not long-to-rest initially
```

Required metrics:

- beta_area and beta_box using:
  - wall-intersection contour;
  - near-wall contour chord;
  - layer projection;
- wall ghost / first fluid / second fluid contact maps;
- center low-phase equivalent diameter;
- annular ring event step;
- first contact;
- beta_max and time;
- mass/rho drift;
- max Mach;
- nonfinite;
- morphology montage.

Pass decision:

```text
If M=0.01 or lower and/or W adjustment removes or shrinks the first-fluid
center void without hurting mass/Mach, select that as the next impact route.

If the center void persists and does not shrink with R/grid increase, the
planar dry-wall route is not publication-ready under current model/resources.

If the void shrinks with grid but remains under-resolved, document required
resolution and decide whether multi-GPU/decomposition is necessary.
```

### Gate F: Low-We Planar Literature Comparison

Literature basis:

- Current 10 uL theta57 has `We≈5.3`, not high-We.
- Many beta correlations are for higher We ranges.
- Existing comparison shows beta magnitude is not obviously impossible for
  low-We; morphology is the bigger issue.

Minimum execution:

1. Select one literature case with:
   - `D`;
   - `U`;
   - density/viscosity/surface tension;
   - static contact angle;
   - beta_max or morphology sequence;
   - preferably low-We `O(1-10)`.
2. Match `Re`, `We`, `Bo`, `theta` using `sigma_eff`.
3. Run selected `M/W/grid` from Gate E.
4. Report error metrics and morphology, not only overlays.

Pass decision:

- If beta and morphology match within an agreed error band, promote only to
  `validation_candidate` after read-only audit.
- If beta matches but morphology fails, do not promote.
- If morphology matches but beta fails, audit beta convention and physical
  parameters.

### Gate G: Return To User Target Runs

Only after Gates A-F:

1. Re-run 10 uL theta57 near-wall equivalent.
2. Re-run 10 uL theta57 full gravity top-to-wall with checkpoint/restart and
   at least 50-150 morphology frames.
3. Re-run original `rho_ratio=772`, `D=1 mm`, `H=10 mm`, `theta=90` dry-wall.
4. Add theta045/theta135 only after theta090 morphology is acceptable.
5. Add liquid-film cases last.

Required target outputs:

- beta_area(t);
- beta_box(t);
- beta_max;
- first contact;
- recoil/resting candidate;
- mass/rho drift;
- max Mach;
- nonfinite;
- morphology frames;
- center void/dimple scale;
- case XML;
- run.log;
- summary JSON;
- artifact paths.

## Practical Resource Plan

Single P100 16 GB limitation:

- R50 10 uL refinement already failed at 19.66M cells.
- Prefer benchmark cases around `128^3`, `121^3`, and carefully chosen
  `160 x 352 x 160` only when memory-audited.
- For larger cases, plan multi-GPU decomposition or use a different machine.

Disk policy:

- Keep raw VTI/PVTI remote-only.
- For long runs, delete raw after curated XML/log/CSV/JSON/PNG artifacts and
  provenance are confirmed.
- Do not delete checkpoints required for continuation unless the case is
  explicitly classified as failed and no longer needed.

## Immediate Next Action

Start with Gate A and Gate B.

Do not run another long planar impact continuation until:

```text
1. clean source/binary state is verified;
2. sphere-spread reproduction is at least partially passed;
3. capillary intrusion dynamic wetting sensitivity is planned or underway.
```

This is the shortest route that directly tests the model and wetting boundary
using the same paper's own logic, while preserving the ability to return to
the 10 uL theta57 and rho_ratio=772 targets with defensible evidence.
