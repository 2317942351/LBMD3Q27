# PRE 2025 3D Phase-Field Wetting Boundary Paper vs TCLB Analysis

Date: 2026-06-09

Status: `exploratory_not_validation`

Article analyzed from local HTML:

```text
C:\Users\yuanz\Desktop\在具有大密度比和复杂固体边界的三维相场格玻尔兹曼模型中实现的润湿边界方案 _物理评论 E --- Wetting boundary scheme implemented in three-dimensional phase-field lattice Boltzmann model with large density ratios and complex solid boundaries _ Phys. Rev. E.html
```

Article metadata extracted from the HTML:

```text
title = Wetting boundary scheme implemented in three-dimensional phase-field lattice Boltzmann model with large density ratios and complex solid boundaries
journal = Physical Review E 112, 065303
doi = 10.1103/xz95-6bmt
authors = Changli Wang, Chengjie Zhan, Zhenhua Chai, Gui Long, Junyu Duan, Jianfeng Xu, Junfeng Xiao
published = 2025-12-01
```

Claim boundary:

```text
This note is an article/TCLB comparison and reproduction feasibility analysis.
It does not validate the current TCLB rho772 dry-wall impact route.
It does not claim formula equivalence between the article model and TCLB.
It does not promote any TCLB result beyond the labels already recorded in the TCLB project docs.
```

## 1. Article Model

### 1.1 Governing Equations

The paper uses a three-dimensional phase-field LB framework for liquid-gas-solid wetting with large density ratios. The order parameter is:

```text
phi = 0: gas
phi = 1: liquid
```

The phase transport equation is a conservative Allen-Cahn-type equation:

```text
d(phi)/dt + div(u phi) = div[ M_phi (grad(phi) - lambda n) ]
n = grad(phi) / |grad(phi)|
lambda = 4 phi (1 - phi) / W
```

The paper explicitly uses:

```text
interface thickness W = 6
```

The momentum equation is a consistent and conservative incompressible two-phase NS form. A key distinction from many older phase-field LB routes is that the paper includes mass-diffusion consistency terms:

```text
m_phiC = -(rho_A - rho_B) M_phi (grad(phi) - lambda n)
```

and places related terms into the momentum/force treatment. The surface tension force is written through the chemical potential:

```text
F_s = mu_phi grad(phi)
mu_phi = 4 beta phi (phi - 1) (phi - 1/2) - kappa laplacian(phi)
beta = 12 sigma / W
kappa = 3 sigma W / 2
```

The HTML formula extraction for the density/viscosity interpolation appears inconsistent with the text convention `phi=0 gas, phi=1 liquid`; for exact coding, verify Eq. (6) against the PDF before implementing.

### 1.2 LBM Discretization

The article states that:

```text
phase-field distribution = D3Q19, MRT
fluid distribution = D3Q19, MRT
phase relaxation tau_f = 1.1
other phase relaxation parameters = 1
dx = dt = 1
gradients and Laplacians = second-order isotropic finite differences
gradient stencil for derivatives = 27 directions in 3D
```

This is not the same population/stencil structure as the current TCLB default route.

### 1.3 Wetting Boundary Scheme

The paper's wetting boundary is a free-energy wetting boundary scheme. The boundary condition is imposed on the wall-normal order-parameter gradient:

```text
n_w dot grad(phi)|_xw = Theta phi_w (1 - phi_w)
Theta = -sqrt(2 beta / kappa) cos(theta)
```

The scheme reconstructs wall/solid-side order parameter values from a wall intersection geometry:

```text
phi_w = s/(h+s) phi_p + h/(h+s) phi_s
```

Combining this with the wetting condition gives the paper's explicit `phi_s` formula. For `theta=90 deg`, the formula reduces to:

```text
phi_s = phi_p
```

The 3D boundary treatment has three geometry tasks:

1. Identify the solid-fluid interface and wall normal.
2. Determine the distance variables `h` and `s`.
3. Interpolate `phi_p` at the normal-line intersection in 3D.

The paper estimates `n_w` from the solid indicator over a broad neighborhood:

```text
s(x) = 0 for fluid nodes
s(x) = 1 for solid nodes
normal vector computed using weighted neighboring solid indicators
normal-vector neighborhood = 93 surrounding nodes
```

Then it computes `h` and `s` using the 26 nodes surrounding the target solid node.

The intersection point `x_p` is classified into:

```text
on-node intersection: phi_p = phi_n1
on-edge intersection: linear interpolation between two nodes
on-face intersection: barycentric interpolation over three nodes
```

This 3D interpolation logic is the paper's most relevant implementation idea for TCLB complex-geometry wetting.

### 1.4 Distribution Function Boundary Conditions

For the phase-field populations, the paper uses a no-flux style treatment:

```text
f_bar_alpha(x_s, t+dt) = f_alpha(x_f, t+dt)
```

For the fluid populations, it uses an interpolated no-slip boundary condition with a piecewise formula depending on `delta`. This is not identical to the current TCLB bounce-back/boundary implementation and should not be assumed equivalent.

## 2. Current TCLB Model

Current TCLB project model:

```text
remote source = /home/yuan/src/TCLB/models/multiphase/d3q27_pf_velocity
main production candidate family = d3q27_pf_velocity
current claim scope = TCLB phase-field route, not Wang 2023 or PRE 2025 formula equivalence
```

### 2.1 Core Route

TCLB `d3q27_pf_velocity` is the Fakhari/Mitchell-style high-density-ratio phase-field model:

```text
hydrodynamic populations = D3Q27
phase-field populations = D3Q15 by default
phase-field populations = D3Q27 when compile option q27=TRUE
collision = weighted MRT by default
BGK = optional testing/education route, not the production route
order parameter = PhaseField_l=0 gas, PhaseField_h=1 liquid
density = linear in PhaseField through Density_l and Density_h
```

The TCLB phase mobility setting is:

```text
omega_phi = 1 / (3M + 0.5)
```

This differs from the article's fixed `tau_f=1.1` setting and explicit `M_phi = c_s^2 (tau_f - 0.5) dt`.

TCLB uses:

```text
IntWidth
sigma
radAngle
Viscosity_l, Viscosity_h
tauUpdate
Gravity and buoyancy settings
```

The chemical-potential form in TCLB is similar in spirit to a free-energy phase-field route, but the coefficients and discrete forcing path are not identical to the article's consistent conservative model.

### 2.2 Current Wetting Branches

The TCLB source provides multiple compile-time wetting routes:

```text
surface-energy wetting: geometric=FALSE
geometric wetting: geometric=TRUE
staircase improvement: staircaseimp=TRUE
more precise second triangle interpolation: tprec=TRUE
q27 phase-field populations: q27=TRUE
```

Observed current binaries on HM570:

| binary | q27 | geometric | staircaseimp | tprec | note |
|---|---:|---:|---:|---:|---|
| `/home/yuan/src/TCLB/CLB/d3q27_pf_velocity/main` | no | no | no | no | baseline surface-energy/q15 phase route |
| `/home/yuan/src/TCLB/CLB/d3q27_pf_velocity_geometric/main` | no | yes | no | no | q15 phase + geometric wetting |
| `/home/yuan/src/TCLB/CLB/d3q27_pf_velocity_q27_geometric/main` | yes | yes | no | no | current q27 + geometric route; source contains default-off local initializer patches |
| `/home/yuan/src/TCLB/CLB/d3q27_pf_velocity_q27_geometric_staircaseimp/main` | yes | yes | yes | no | q27 + geometric + staircase, built for planar-wall A/B only so far |

For a formal PRE article reproduction, build fresh and record clean-source binaries instead of relying on a binary that includes unrelated default-off droplet-tail/velocity patches.

### 2.3 TCLB Boundary Implementation vs Article

TCLB surface-energy branch reconstructs wall `PhaseF` through:

```text
a = -h * (4/IntWidth) * cos(radAngle)
PhaseF = (1 + a - sqrt((1+a)^2 - 4a pf_f))/(a + 1e-12) - pf_f
```

TCLB geometric branch uses:

```text
PhaseF = tan(pi/2 - radAngle) * grad_tangent * 2h + pf_f
```

TCLB `staircaseimp` computes an actual wall normal, finds the intersected D3Q27 cell face, subdivides the face into triangles, and uses barycentric interpolation coefficients. This is conceptually close to the paper's 3D face-intersection interpolation, but it is not the same algorithm:

| item | PRE 2025 article | TCLB current implementation |
|---|---|---|
| Hydrodynamic lattice | D3Q19 | D3Q27 |
| Phase-field lattice | D3Q19 | D3Q15 default, D3Q27 optional |
| Phase equation | conservative AC with explicit mass-consistency terms | Fakhari/Mitchell phase-field route |
| Wall normal estimate | weighted solid indicator over 93 surrounding nodes | D3Q27-neighborhood weighted normal, then nearest D3Q27 direction; staircase stores actual intersection normal |
| Distance handling | explicit `h` and `s` from 26-neighbor geometry | `h = 0.5 |nw|` or `0.5 |nw_actual|`; no direct article `s` reconstruction |
| Wetting formula | free-energy `n_w dot grad(phi)=Theta phi_w(1-phi_w)`, explicit `phi_s` formula | surface-energy quadratic formula or geometric tangent-gradient formula |
| Intersection interpolation | on-node, on-edge, on-face classification | triangle-face barycentric interpolation in `staircaseimp`; fallback paths for solid interpolation nodes |
| Fallback logic | not fully visible in HTML beyond classification | explicit `IsSpecialBoundaryPoint` categories and fallback to simpler/surface-energy handling |
| Distribution boundary | no-flux phase population and interpolated no-slip fluid population | TCLB updateBoundary/bounce-back/Zou-He/outflow routes; not formula-equivalent |

Conclusion:

```text
TCLB already contains several ideas that overlap with the article: actual normals,
triangle interpolation, and wetting-wall phase reconstruction.

However, the current TCLB model is not the PRE 2025 article model.
Any reproduction should be called an analogue or independent TCLB benchmark
unless the article equations and wall formula are implemented directly.
```

## 3. Useful Lessons For Current TCLB Work

### 3.1 Directly Useful

1. Curved/complex wetting must be validated before using complex geometry claims.

   The article validates on a sphere, in a tube, and on conical fibers. For TCLB, the analogous route should be:

   ```text
   static sphere wetting -> capillary rise/intrusion -> cone/fiber transport -> impact
   ```

2. Use geometry-observable metrics, not only raw contact angle.

   The article's sphere test compares the theoretical and simulated maximum droplet height `Hmax`. For TCLB, this is better than relying only on a local two-row planar contact-angle metric when testing curved boundaries.

3. Report spurious velocity near the contact line.

   The paper reports spurious velocities of order `10^-4` in the sphere test. TCLB reproduction should report:

   ```text
   max velocity
   max Mach
   contact-line-local velocity
   spurious velocity at static equilibrium
   ```

4. Separate static and dynamic wetting validation.

   The paper uses capillary rise for dynamic wetting. This is highly relevant to TCLB because current dry-wall impact issues include dynamic contact-line behavior and central low-phase/annular contact artifacts.

5. For curved geometry, enable and audit `staircaseimp` and preferably `tprec`.

   TCLB's geometric-only planar route is insufficient to judge the article's complex-boundary claims. The article's experience suggests that actual-boundary intersection and interpolation choices matter strongly.

### 3.2 Potentially Useful But Requires Implementation

1. Add a PRE-style free-energy wall reconstruction branch.

   TCLB surface-energy wetting has a related quadratic formula, but it is not the article's exact `phi_s` reconstruction with explicit `h`, `s`, and `phi_p`. A direct test branch could implement:

   ```text
   paper_normal_93
   paper_h_s_26
   paper_phi_p_interpolation
   paper_phi_s_free_energy_wall_value
   ```

2. Add boundary diagnostic counters.

   TCLB currently marks special boundary points internally. For reproduction, output counters should include:

   ```text
   normal_points_into_solid
   next_interpolation_nodes_solid
   next-next_interpolation_nodes_solid
   surface-energy fallback count
   triangle interpolation count
   tprec second-triangle interpolation count
   ```

3. Add a paper-style solid-normal audit.

   Compare:

   ```text
   analytic normal for sphere/tube/cone
   TCLB nw rounded normal
   TCLB ActualNormal from staircaseimp
   PRE-style 93-neighbor normal if implemented
   ```

### 3.3 Not Directly Transferable

The article is not a dry-wall droplet-impact validation paper. It does not provide:

```text
planar dry-wall beta(t)
beta_max for impact
high-We planar impact morphology
rho772 dry-wall or liquid-film impact data
45/90/135 planar impact sweeps
```

Therefore it cannot by itself validate the current TCLB dry-wall impact campaign. It can only strengthen the wetting-boundary validation route.

## 4. Article Cases And Extracted Data

### 4.1 Case A: Droplet Resting On A Spherical Surface

Purpose:

```text
static accuracy of 3D curved wetting boundary
```

Full-size article setup:

```text
domain = 230 x 230 x 400 lu
initial droplet radius = 80 lu
solid sphere radius Rs = 80 lu
liquid/gas density ratio = 1000
liquid/gas dynamic viscosity ratio = 900
interface thickness W = 6
first shown contact angles = 40, 70, 100, 130 deg
additional table angles = 30, 50, 70, 90, 110, 130, 150 deg
reported spurious velocity scale = O(1e-4)
reported average runtime = about 0.08 s per time step on NVIDIA RTX 4090
```

Analytical observable:

```text
Hmax = k + Rs
```

where `k`, `H1`, and `H2` are obtained from the spherical-cap geometry in article Eq. (42). The volume is written as the difference between the liquid spherical cap and the solid-sphere cap.

Extracted Table I:

| theta (deg) | expected Hmax | simulated Hmax | relative error (%) | spurious velocity (1e-4) |
|---:|---:|---:|---:|---:|
| 30 | 142.85 | 141.07 | 1.25 | 1.18 |
| 50 | 164.29 | 162.49 | 1.10 | 1.70 |
| 70 | 182.06 | 182.42 | 0.20 | 1.22 |
| 90 | 198.54 | 200.32 | 0.90 | 1.28 |
| 110 | 213.32 | 215.81 | 1.17 | 1.22 |
| 130 | 225.66 | 229.17 | 1.56 | 0.45 |
| 150 | 234.64 | 238.56 | 1.67 | 0.48 |

Reduced comparison against Sashko et al. improved energy/geometric schemes:

```text
domain = 80 x 80 x 140 lu
initial droplet radius = 24 lu
solid sphere radius = 24 lu
other parameters = same as the full-size sphere setup
error definition = relative error of theoretical vs simulated (H1 - H2)
```

Extracted Table II:

| theta (deg) | our scheme error (%) | IE scheme error (%) | IG scheme error (%) |
|---:|---:|---:|---:|
| 30 | 4.2 | 14.1 | 7.5 |
| 40 | 2.1 | 8.6 | 6.9 |
| 50 | 2.0 | 6.9 | 5.9 |
| 60 | 1.2 | 3.4 | 3.1 |
| 70 | 0.4 | 1.7 | 1.6 |
| 80 | 0.6 | 0.1 | 0.2 |
| 90 | 1.3 | 1.1 | 1.1 |
| 100 | 1.8 | 2.0 | 2.1 |
| 110 | 2.1 | 2.3 | 2.6 |
| 120 | 2.8 | 2.9 | 3.3 |
| 130 | 2.9 | 3.3 | 3.9 |

Data quality:

```text
Table I and Table II are direct numeric data from the HTML.
Figure 8 and Figure 9 are bitmap figures and should only be digitized if curve-level overlay is required.
```

### 4.2 Case B: Capillary Rise In Cylindrical Tubes

Purpose:

```text
dynamic wetting/contact-line validation against Lucas-Washburn-type theory
```

Governing comparison:

```text
Lucas-Washburn equation with gravity and viscous resistance
dynamic contact angle model:
cos(theta_d) = cos(theta) - tanh[4.96 (mu v / sigma)^0.702] [cos(theta) + 1]
```

Article setup:

```text
domain = 230 x 230 x 1000 lu
liquid density = 1000 kg/m3
gas density = 1.42 kg/m3
liquid dynamic viscosity = 1.0e-2 N s/m2
gas dynamic viscosity = 1.6e-5 N s/m2
surface tension = 0.0203 N/m
```

Figure 11:

```text
tube radius r = 0.2 mm
contact angles = 20, 40, 60 deg
subcase a: g = 0
subcase b: g = 3 m/s2
observable = h(t), rise height in mm vs time in s
figure axis h range = 0 to about 0.012 mm
```

Figure 12:

```text
tube radius r = 0.267 mm
contact angles = 20, 40, 60 deg
subcase a: g = 0
subcase b: g = 2 m/s2
observable = h(t), rise height in mm vs time in s
figure axis h range = 0 to about 0.012 mm
```

Data quality:

```text
The HTML contains bitmap curves only, not CSV/table point data.
Curve-level reproduction requires digitizing Fig. 11 and Fig. 12.
Parameters above are directly extractable from the text.
```

### 4.3 Case C: Self-Propelled Droplet On Conical Fibers

Purpose:

```text
complex gas-liquid-solid wetting on curved conical surfaces
dynamic self-propulsion and power-law motion
```

Common setup:

```text
domain = 210 x 210 x 500 lu
liquid density = 1000 kg/m3
gas density = 1.42 kg/m3
liquid dynamic viscosity = 1.0e-2 N s/m2
gas dynamic viscosity = 1.6e-5 N s/m2
surface tension = 0.0227 N/m
```

Theory:

```text
F_drive approximately sigma [ cos(theta_a) L2 - cos(theta_r) L1 ]
single-side mode: droplet moves along one side of cone
wrapping mode: droplet wraps around the cone circumference
hybrid mode: wrapping-to-single-side transition
```

Text-reported initial demonstrations:

```text
single-side example 1:
  cone height H = 6.1 mm
  cone base radius Rb = 0.50 mm
  static contact angle theta = 60 deg
  initial droplet radius Ri = 0.36 mm
  figure = Fig. 14

single-side example 2:
  cone height H = 6.1 mm
  cone base radius Rb = 0.62 mm
  initial droplet radius Ri = 0.81 mm
  figure = Fig. 15
```

Power-law findings:

```text
single-side mode: d ~ t^0.5
wrapping mode: d ~ t^0.25
```

Figure 16:

```text
single-side mode
H = 6.1 mm
theta = 40 deg
Ri = 0.36 mm
base radii from figure legend: Rb = 0.39, 0.50, 0.70 mm
plots: d(t) and d vs t^0.5
```

Figure 17:

```text
single-side mode
H = 6.1 mm
Rb = 0.50 mm
Ri = 0.36 mm
static contact angles from figure legend: theta = 40, 50, 60 deg
plots: d(t) and d vs t^0.5
```

Figure 18:

```text
wrapping mode
H = 6.1 mm
theta = 30 deg
Ri = 0.36 mm
base radii from figure legend: Rb = 0.78, 0.94, 1.09 mm
plots: d(t) and d vs t^0.25
```

Figure 19:

```text
wrapping mode
H = 6.1 mm
Rb = 0.94 mm
Ri = 0.36 mm
static contact angles from figure legend: theta = 20, 25, 30, 40 deg
plots: d(t) and d vs t^0.25
note: theta=40 deg tail after t > 0.85 s changes trend as the mode transitions
```

Figure 20:

```text
hybrid-mode morphology sequence
H = 7.7 mm
Rb = 0.94 mm
Ri = 0.62 mm
reported stages:
  t = 0 to 0.62 s: wrapping mode
  t = 0.92 s: advancing contact line begins to lose stability
  t = 1.08 s: intermediate state
  t = 1.23 s: transition to single-side mode completed
```

Figure 21:

```text
hybrid mode
H = 7.7 mm
theta = 40 deg
Rb = 0.94 mm
initial droplet radii from figure legend: Ri = 0.63, 0.55, 0.47 mm
plots: d(t), d vs t^0.5, d vs t^0.25
transition points marked as Ai
```

Data quality:

```text
The conical-fiber result curves are bitmap-only in the saved HTML.
The power-law exponents and parameter values are extractable from text and figure legends.
Exact pointwise d(t) data require figure digitization or author data.
```

## 5. Can Current TCLB Reproduce These Cases?

### 5.1 Exact Model Reproduction

Current status:

```text
not currently possible without implementation changes
```

Reasons:

```text
1. Article uses D3Q19 phase and D3Q19 fluid MRT; TCLB uses D3Q27 fluid and D3Q15/D3Q27 phase.
2. Article uses a consistent conservative NS/AC formulation with explicit mass-diffusion correction terms; TCLB uses the Fakhari/Mitchell route.
3. Article's free-energy wall reconstruction is not identical to TCLB surface-energy or geometric wetting branches.
4. Article's normal and distance construction uses a 93-neighbor normal plus 26-neighbor h/s treatment; TCLB does not currently implement that exact geometry pipeline.
```

Therefore, a TCLB run can be a comparative analogue or independent reproduction benchmark, not an exact article-model reproduction.

### 5.2 Sphere Static Wetting Reproduction

Feasibility:

```text
high for reduced Table II case
medium to low for full Table I case on a single Tesla P100
```

The reduced article comparison is the best first target:

```text
domain = 80 x 80 x 140
R_drop = 24
R_solid = 24
angles = 30 to 130 deg
metric = relative error in H1 - H2, plus Hmax if geometry extraction is robust
```

The full-size case:

```text
domain = 230 x 230 x 400 = 21.16 million cells
```

This is likely too large for the current single P100 q27/staircase route. The project already has negative memory evidence from a `320 x 320 x 192` q27 run of similar cell count failing on a 16 GB P100. Full-size reproduction should wait for either:

```text
multi-GPU/domain decomposition readiness
lower-memory q15/surface exploratory check
or a different GPU with more memory
```

Minimum TCLB reproduction route:

```text
1. Build clean q15/q27, surface/geometric/staircase/tprec binaries.
2. Generate solid sphere geometry and initial droplet on sphere.
3. Run the 80 x 80 x 140, R=24 matrix first.
4. Postprocess H1, H2, Hmax, contact-line shape, contact angle, mass/rho drift, max Mach, nonfinite, and spurious velocity.
5. Compare against Table II first; only then attempt Table I full-size or scaled equivalent.
```

Expected status after first successful runs:

```text
runtime_sanity or validation_candidate for curved static wetting metric only,
after read-only audit.
```

### 5.3 Capillary Rise Reproduction

Feasibility:

```text
medium for a scaled/surrogate capillary case
low for the exact 230 x 230 x 1000 case on current single-GPU resources
```

Cell count:

```text
230 x 230 x 1000 = 52.9 million cells
```

This is not practical as a first run on the current P100 workflow. A scaled case can still test dynamic wetting if dimensionless controls are reported:

```text
radius in lu
contact angle
effective sigma from Laplace calibration
measured theta_eff
viscosity and density ratios
gravity
capillary front extraction rule
x_front/h(t) curve error against Lucas-Washburn
```

TCLB support likely needed:

```text
solid cylinder mask or tube geometry generator
reservoir/initial interface setup
capillary front postprocess
possibly OutFlow or closed-domain reservoir boundary treatment
```

This is highly relevant to current TCLB impact work because it tests dynamic contact-line motion without the extra complexity of impact, recoil, and gas entrapment.

Expected status:

```text
exploratory_not_validation until scaled case and exact observable mapping pass audit.
```

### 5.4 Conical-Fiber Self-Propulsion Reproduction

Feasibility:

```text
medium as a qualitative complex-geometry benchmark
low as an immediate quantitative validation case
```

Reasons:

```text
1. Domain size 210 x 210 x 500 = 22.05 million cells, again near the known single-P100 memory problem for q27 routes.
2. The geometry is more complex than sphere/tube and requires robust conical solid mask generation.
3. The paper reports power laws and morphology, but the saved HTML does not provide pointwise d(t) data.
4. The case is useful for discovering/diagnosing wetting dynamics, but less directly tied to current planar dry-wall beta(t) validation.
```

Best use in TCLB:

```text
After sphere and capillary pass, run one smaller cone surrogate to test:
  ActualNormal quality
  special-boundary fallback counts
  contact-line continuity
  droplet transport direction
  d vs t^0.5 or d vs t^0.25 trend
```

Expected status:

```text
exploratory_not_validation or runtime_sanity, not publication validation.
```

## 6. Recommended TCLB Reproduction Plan

### Stage P0: Reference Package

Create a local reference package:

```text
references/pre2025_wetting_boundary/
  metadata.json
  extracted_tables.csv
  figure_map.json
  table_I_sphere_Hmax.csv
  table_II_sashko_comparison.csv
  capillary_fig11_digitized.csv   optional
  capillary_fig12_digitized.csv   optional
  cone_fig16_21_digitized.csv     optional
```

Do not treat digitized bitmap curves as exact until axis calibration and uncertainty are recorded.

### Stage P1: Clean Build Audit

Build and record:

```text
d3q27_pf_velocity_surface_q15
d3q27_pf_velocity_surface_q15_staircaseimp
d3q27_pf_velocity_geometric_q15
d3q27_pf_velocity_geometric_q15_staircaseimp_tprec
d3q27_pf_velocity_q27_geometric
d3q27_pf_velocity_q27_geometric_staircaseimp_tprec
```

For every binary:

```text
Consts.h options
options.R
SHA256
build log
source patch status
```

### Stage P2: Reduced Sphere Static Wetting

Run the reduced Table II setup first:

```text
80 x 80 x 140
R_drop = 24
R_solid = 24
theta = 30,40,50,60,70,80,90,100,110,120,130 deg
```

Candidate primary metrics:

```text
H1 - H2 relative error
Hmax relative error
near-wall two-row angle
global spherical-cap angle
spurious velocity
mass/rho drift
max Mach
nonfinite
special-boundary/fallback counts
```

This stage is the most useful immediate bridge between the paper and TCLB.

### Stage P3: Scaled Capillary Rise

Use a smaller tube geometry and compare dimensionless or physical-scaled h(t):

```text
theta = 20,40,60 deg
two gravity conditions
two tube radii if feasible
```

Acceptance should be curve-based:

```text
front-position RMSE or relative error
slope/error in h(t) or h^2(t)
mass/rho drift
max Mach
nonfinite
contact-line stability
```

### Stage P4: Complex Curved Geometry Stress Test

Run a small cone/fiber surrogate only after P2/P3 evidence is clean:

```text
single-side mode first
one wrapping-mode case second
track droplet tip distance d(t)
fit d vs t^0.5 or d vs t^0.25 only after initial transient is excluded
```

### Stage P5: Decide What To Borrow Into Planar Impact

Only after P2/P3 audit:

```text
if staircase/tprec improves curved static/dynamic wetting:
  consider it for non-planar geometries, not necessarily planar dry wall

if PRE-style surface free-energy wall reconstruction is implemented and improves low-angle static mass/angle:
  test it on planar static contact angle before impact

if capillary dynamic wetting exposes M/IntWidth sensitivity:
  reuse that sensitivity matrix before another dry-wall impact sweep
```

## 7. Bottom-Line Judgment

1. The article is highly relevant to TCLB wetting-boundary validation, especially for curved or complex solid boundaries.

2. The article is not a direct validation source for the current planar dry-wall droplet-impact problem.

3. The strongest immediate TCLB task is not another impact run. It is a reduced sphere static wetting reproduction of Table II with clean `surface/geometric/staircase/tprec` binaries and Hmax/H1-H2 postprocessing.

4. Current TCLB can likely reproduce the article's benchmark family as an independent TCLB analogue, but exact reproduction of the article model requires a new wall-boundary implementation and probably a distinct D3Q19/D3Q19 conservative LB branch.

5. Full-size article cases are likely too large for the current single-P100 q27 route. Use reduced sphere first, scaled capillary second, and defer cone/full-size cases until memory and geometry-generation issues are solved.

