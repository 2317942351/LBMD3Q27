# Wetting Boundary Article Analysis

Status: exploratory_not_validation literature analysis
Date: 2026-06-09

## Source

Article:

```text
Sashko, D.; Mitchell, T. R.; Laniewski-Wollk, L.; Leonardi, C. R.
Phase field lattice Boltzmann method for liquid-gas flows in complex geometries
with efficient and consistent wetting boundary treatment.
Computers & Mathematics with Applications, 186, 101-129, 2025.
DOI: 10.1016/j.camwa.2025.03.014
```

Local extracted text:

```text
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\tmp\wetting2025\article_visible_text.txt
```

Local metadata:

```text
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\tmp\wetting2025\preloaded_state.json
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\tmp\wetting2025\crossref.json
```

The paper states that implementation details are available from:

```text
https://github.com/CFD-GO/TCLB
```

## Main Contribution

The paper is a TCLB-based three-dimensional phase-field LBM wetting-boundary
study for curved and complex solid geometries. It is not a direct planar
dry-wall droplet-impact validation case.

The paper implements and compares:

- surface-energy wetting boundary condition;
- geometric wetting boundary condition extended to three-dimensional curved
  boundaries;
- interpolation-based staircase-approximation improvement applied consistently
  to both wetting methods;
- a more precise two-barycentric-coordinate geometric staircase variant, which
  did not materially improve the reported benchmarks.

The paper's relevant evidence for this project is therefore:

- the active TCLB model family is appropriate to audit through official
  high-density-ratio phase-field wetting benchmarks;
- geometric and surface-energy wetting should be compared rather than assumed
  interchangeable;
- staircase improvement can materially affect late-stage spreading/rebound;
- unresolved thin films or near-wall gas layers can cause profile deviation and
  interface tearing.

## Governing Model

The phase variable is defined as:

```text
phi_H = 1 for liquid/high-density phase
phi_L = 0 for gas/low-density phase
phi_0 = 0.5
```

The interface is tracked by the conservative Allen-Cahn equation:

```text
d phi/dt + div(phi u)
  = div( M (grad phi - [1 - 4(phi - phi_0)^2] n / xi) )
```

where `M` is mobility, `xi` is interface width, and
`n = grad(phi) / |grad(phi)|`.

Hydrodynamics is described by incompressible two-phase Navier-Stokes:

```text
div(u) = 0
rho (du/dt + u . grad u)
  = -grad p + div(mu(grad u + grad u^T)) + F_s + F_b
```

with:

```text
F_s = mu_phi grad(phi)
F_b = rho g
```

The chemical potential is:

```text
mu_phi = 1.5 sigma [ 32 phi(phi - 1)(phi - 0.5)/xi - xi laplacian(phi) ]
```

Numerical implementation in the paper:

- phase-field LBE: default D3Q15, SRT collision, selected for performance;
- hydrodynamic LBE: D3Q27, weighted MRT collision;
- phase-field gradient: isotropic finite difference, not purely local moment
  reconstruction;
- phase density relation:

```text
rho = rho_L + (phi - phi_L)/(phi_H - phi_L) * (rho_H - rho_L)
```

This is consistent with treating the current TCLB `d3q27_pf_velocity` route as
a conservative Allen-Cahn phase-field model, not as a pseudopotential route and
not as Wang 2023 ULBM/NMRT equivalence evidence.

## Wetting Boundary Methods

### Surface-Energy Method

The surface-energy method imposes contact angle by introducing a wall free
energy. The paper uses a cubic wall-energy form to reduce spurious film at the
solid surface. After discretisation, the wall/ghost phase value is computed
from the neighboring fluid phase value, the wall-normal distance, interface
width, and the prescribed angle.

Important interpretation:

- cheaper and faster;
- requires fewer neighboring values;
- can be stable;
- in this paper it is more sensitive to mobility and shows larger deviations
  at low contact angle in capillary intrusion and spreading comparisons.

### Geometric Method

The geometric method enforces the relationship between the wall-normal and
wall-tangential phase-field gradient components:

```text
tan(pi/2 - theta) = - (n_w . grad(phi)_w) / |P(grad(phi)_w)|
```

The ghost/boundary phase value is then determined from the projected gradient
near the wall. In this implementation, the method avoids explicitly building a
full local wall-aligned coordinate system and instead uses gradient projection,
which is more suitable for three-dimensional curved boundaries.

Important interpretation:

- better low-angle performance in the paper's dynamic capillary benchmark;
- more expensive than surface-energy;
- needs a wider near-wall stencil because it uses phase-gradient information
  from a farther layer.

### Staircase Improvement

For curved solids, the true wall normal does not usually align with a lattice
direction. The paper introduces a solid volume fraction field `C_s` and computes
the wall normal by:

```text
n_w = - grad(C_s) / |grad(C_s)|
```

Then a ray along this normal intersects the next lattice layer. The physical
quantity needed by the wetting boundary condition is interpolated from three
nearby nodes using barycentric coordinates. The same interpolation idea is
applied to both surface-energy and geometric wetting.

Important interpretation:

- this is aimed at curved/complex geometries, not primarily a flat wall;
- it can substantially change late-stage spreading and rebound;
- it adds cost and still has edge-case fallbacks when interpolation nodes are
  themselves solid or boundary nodes.

## Benchmark 1: Droplet Spread On Sphere

Purpose:

```text
static curved-wetting benchmark against analytical spherical-cap geometry
```

Reported setup:

```text
domain = 128 x 128 x 128
droplet radius R_d = 24
solid sphere radius R_s = 24
density ratio rho* = 1000
viscosity ratio mu* = 100
mobility M = 0.05
additional M tested = 0.025 and 0.1
interface width xi = 5
surface tension sigma = 0.01
boundary = periodic domain boundaries
solid = bounce-back + wetting on sphere
initial droplet bottom = immediately above sphere top
contact-angle range = 30 to 130 deg
metric = nondimensional droplet height h* = h/(2 R_d)
```

Main findings:

- both surface-energy and geometric methods reproduce the analytical trend;
- staircase improvement strongly reduces error for intermediate contact angles;
- geometric is slightly more accurate at low contact angles;
- using a more precise two-barycentric geometric interpolation did not improve
  accuracy;
- remaining error is mainly attributed to inaccurate numerical surface normals
  from the discretised solid fraction field;
- using analytical sphere normals gives near-perfect agreement;
- grid sensitivity was tested with `R in {12,24,48}` at constant Cahn number
  `Cn = xi/R = 5/12`.

Reported relative errors from Table 1 show improved methods mostly around
1-8% for intermediate angles, with larger errors near 30 deg and some increase
again near 130 deg.

Project implication:

This is the best first reproduction case for verifying our geometric and
geometric+staircase binaries against article evidence before using them for
complex dynamic claims. It is still not proof that a planar dry-wall impact
case is validated.

## Benchmark 2: Capillary Intrusion

Purpose:

```text
dynamic wetting benchmark against Washburn-type analytical solution
```

Reported analytical model:

```text
sigma cos(theta) = 4 R (x mu_l + mu_g (L - x)) dx/dt
```

Reported setup:

```text
domain = 256 x 12 x 12
initial liquid reservoir length L0 = 96
capillary radius R = 5
capillary length L = 20 R
density ratio rho* = 1000
viscosity ratio mu* = 100
mobility M = 0.05
interface width xi = 5
Laplace number La = 1
contact angles = 20 to 80 deg
boundaries = no-slip + wetting on solid walls, periodic on domain boundaries
refined comparison = 512 x 22 x 22 with R = 10
mobility sensitivity = M in {0.025, 0.05, 0.075}, compared at t* = 30
```

Main findings:

- most angles are reproduced well even on coarse mesh;
- theta = 20 deg is under-resolved on the coarse mesh because the relevant
  near-wall film thickness is not resolved when `xi = R`;
- refining to `R = 10` improves accuracy;
- geometric wetting better predicts low-angle intrusion than surface-energy;
- surface-energy is more mobility-sensitive, especially at low contact angles;
- staircase improvement reduces mobility sensitivity and helps geometric at
  low angle, but does not universally improve every capillary result.

Project implication:

This directly supports our decision to sweep `M`, `IntWidth`, and grid
resolution when center gas/air film behavior appears abnormal. A failure at the
near-wall gas layer cannot be diagnosed from a single impact run.

## Benchmark 3: Droplet Impact On Sphere

Purpose:

```text
dynamic curved-impact benchmark and literature/experiment comparison
```

Method-comparison setup:

```text
domain = 160 x 352 x 160
droplet radius R_d = 28
sphere radius R_s = 35
R* = R_s/R_d = 1.25
density ratio rho* = 1000
viscosity ratio mu* = 100
mobility M = 0.05
initial gap H = 200 from droplet south pole to sphere top
initial velocity = 0
driving = gravity
boundaries = periodic domain boundaries
solid = bounce-back + wetting
Re = 60
We = 6
Bo = 0.84
contact angles = 20 to 120 deg
metric = nondimensional north-pole/film height h*
```

Mitra et al. experimental comparison:

```text
theta = 86 deg
Re = 2891
We = 43.7
R* = 1.15
rho* = 1000
mu* = 100
M = 0.02 for stability
sphere radius R_s = 58
domain = 288 x 512 x 288
initial gap H = 200
initial velocity = 0
driving = gravity
```

Main findings:

- in the first two inertia-dominated regions, all wetting-boundary variants
  are almost indistinguishable and match expected height profiles;
- this early-time match is not sufficient to validate wetting boundary accuracy;
- the third region is where surface tension, inertia, gravity, and wettability
  compete, and boundary-condition differences become significant;
- low contact angles give smaller minimum film thickness and gentler rebound;
- high contact angles can rebound;
- staircase improvement significantly affects spreading and bouncing,
  especially around 40 and 60 deg;
- in the Mitra comparison, the simulation could not resolve the full
  experimental time range because `h*_exp = 0.01` corresponds to only one cell;
- profile deviation and eventual interface tearing were observed when
  `h*_simulation < 0.06`, about six cells and close to `xi = 5`.

Project implication:

This is directly relevant to our center-void/air-film concern. The article
supports the interpretation that unresolved near-wall films, dimples, or thin
gas layers can cause numerical deviation and interface tearing. It does not
prove our current center cavity is physical; it tells us that the diagnostic
must include film/dimple resolution relative to `IntWidth`, local cell count,
Mach, mass drift, and grid sensitivity.

## Benchmark 4: Rough Fracture Flow

Purpose:

```text
engineering-style complex-geometry demonstration and performance comparison
```

Reported setup:

```text
domain = 288 x 288 x 32
density ratio rho* = 1000
viscosity ratio mu* = 100
mobility M = 0.05
roughness sigma = 0.2
mean aperture = 1
periodic all directions
driving force gx = 2.5e-7
surface tension sigma = 0.003
contact angle theta = 45 deg
maximum steady Ca = 0.0014
Re = 0.2
```

Main findings:

- both wetting approaches yield similar overall relative permeability trends;
- transition-region behavior differs because capillary forces are sensitive to
  the wetting-boundary treatment;
- this affects gas entrapment and liquid-channel formation;
- edge-case handling is needed in rough geometries;
- geometric can fall back to surface-energy-like handling where geometric
  data cannot be safely obtained.

Project implication:

For complex/curved geometry work, the article requires reporting how often the
staircase or geometric boundary condition falls back to simpler handling. For a
flat wall this is less central, but for sphere reproduction it is mandatory.

## Performance Findings

On the fracture-flow case with an NVIDIA Tesla V100:

- standard surface-energy is fastest;
- surface-energy + staircase is about 14% slower;
- baseline geometric runs at about 80% of baseline surface-energy speed;
- geometric + staircase is about 35% slower than baseline geometric.

Project implication:

`geometric + staircaseimp` is justified as a diagnostic and benchmark route,
but it is not free. It should be used deliberately where boundary geometry or
wetting behavior makes it informative.

## Relevance To Current TCLB Planar Impact Work

### What The Paper Supports

The paper supports the following for our project:

- using TCLB `d3q27_pf_velocity` as a serious high-density-ratio phase-field
  production-code candidate;
- treating geometric and surface-energy wetting as distinct model branches;
- reproducing official/publication wetting benchmarks before paper-facing
  claims;
- testing staircase improvement as a meaningful boundary-condition variant;
- performing `M`, `IntWidth`, and grid sensitivity when near-wall films,
  center gas pockets, or rebound/spreading discrepancies appear;
- using late-time morphology, not just early inertia-dominated behavior, to
  evaluate wetting-boundary correctness.

### What The Paper Does Not Support

The paper does not by itself support:

- claiming validation of our planar `rho_ratio=772` dry-wall droplet impact;
- claiming equivalence to Wang 2023 ULBM/NMRT or pseudopotential models;
- calling small-grid exploratory impact runs validation;
- using early-time impact agreement alone as a wetting-boundary validation;
- accepting a center cavity as physical without a dimple/film resolution audit.

### Direct Diagnostic Consequences

For our current center-void and insufficient spreading issue, the paper points
to these likely diagnostics:

1. Measure gas film/dimple thickness in cells and compare it with `IntWidth`.
   If the relevant feature is below roughly `IntWidth` or below about six cells,
   the paper warns that deviation or interface tearing can occur.

2. Re-run controlled short pilots with `M` and `IntWidth` sweeps. The paper
   explicitly shows mobility sensitivity and stronger low-angle sensitivity in
   dynamic wetting benchmarks.

3. Compare `geometric`, `surface-energy`, and `staircaseimp` variants, but do
   not interpret equal early impact behavior as proof that the boundary is
   correct.

4. Prefer an article reproduction gate before relying on the method for final
   planar impact results:

```text
Laplace sigma_eff closure
planar static radAngle -> theta_eff closure
sphere static spread reproduction
capillary intrusion reproduction
sphere impact reproduction
then planar dry-wall/film target simulations
```

## Recommended Reproduction Route

Minimum route:

1. Build/source audit:
   - surface-energy q27;
   - surface-energy q27 + staircaseimp;
   - geometric q27;
   - geometric q27 + staircaseimp;
   - optional geometric q27 + staircaseimp + tprec.

2. Laplace closure:
   - periodic droplets at multiple radii;
   - fit `Delta p = 2 sigma_eff/R`;
   - use `sigma_eff` for We, Bo, Oh, and impact comparison.

3. Sphere spread:
   - reproduce `128^3`, `R_d=R_s=24`, `rho*=1000`, `mu*=100`, `M=0.05`,
     `xi=5`, `sigma=0.01`, angles 30-130 deg;
   - compare `h*` to the paper's Eq. 57 analytical solution;
   - report relative error, mass drift, max Mach, nonfinite, and overlay plots.

4. Capillary intrusion:
   - start with `256 x 12 x 12`, `R=5`, `L=20R`, `L0=96`;
   - then `512 x 22 x 22`, `R=10`;
   - compare front position to Eq. 58;
   - sweep `M = 0.025, 0.05, 0.075`.

5. Sphere impact:
   - reproduce the method-comparison case first (`Re=60`, `We=6`);
   - if resources allow, reproduce the Mitra comparison (`Re=2891`, `We=43.7`);
   - focus on three-region `h*` evolution and late-time boundary-condition
     differences.

6. Return to planar dry-wall:
   - only after the above gates identify whether our planar center cavity is
     due to unresolved dimple/film, wetting-boundary branch, mobility/interface
     parameters, or postprocessing of contact/spreading.

## Claim Status

This article provides strong literature support for a validation pathway, but
does not itself promote any existing project run beyond:

```text
exploratory_not_validation
```

Promotion requires read-only audit of reproduced benchmarks and complete
reporting of case XML, run logs, summary JSON, metric CSV, mass/rho drift,
max Mach, nonfinite counts, morphology, and artifact provenance.
