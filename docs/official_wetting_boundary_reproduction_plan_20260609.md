# Official 3D phase-field wetting boundary reproduction plan

Status: exploratory_not_validation
Date: 2026-06-09

This note freezes the current reproduction plan for the official/author
three-dimensional phase-field wetting boundary treatment route:

- Paper: Phase field lattice Boltzmann method for liquid-gas flows in complex
  geometries with efficient and consistent wetting boundary treatment,
  Computers & Mathematics with Applications, 186, 101-129,
  DOI 10.1016/j.camwa.2025.03.014.
- Model family: TCLB `models/multiphase/d3q27_pf_velocity`.
- Official/publicly advertised benchmark topics: droplet spreading on a sphere,
  capillary intrusion, and droplet impact on a sphere.
- Boundary variants to compare: surface-energy wetting, geometric wetting,
  staircase-improved surface-energy wetting, staircase-improved geometric
  wetting, optionally `tprec` for the geometric staircase branch.

Do not treat these sphere/complex-geometry benchmarks as proof that the current
rho_ratio=772 planar dry-wall droplet-impact case is already validated. They
are a model-correctness and wetting-boundary reproduction route.

## Confirmed From TCLB Source And Official Documentation

Active source path on HM570:

```text
/home/yuan/src/TCLB/models/multiphase/d3q27_pf_velocity
```

Compile options from `conf.mk`:

```text
OPT="(q27 + OutFlow + BGK + thermo*planarBenchmark)*autosym*geometric*staircaseimp*isograd*tprec"
```

Relevant option meanings:

- `q27`: phase-field populations use D3Q27 instead of the default D3Q15 branch.
- default hydrodynamic populations are D3Q27.
- default collision is weighted MRT; `BGK` exists mainly for testing/education
  and should not be used as the production validation route.
- `geometric`: use geometric wetting boundary conditions instead of surface
  energy.
- default non-geometric branch is the surface-energy wetting boundary.
- `staircaseimp`: apply the staircase/geometry improvement to either wetting
  boundary family.
- `tprec`: more precise second-triangle interpolation for the geometric
  staircase branch.
- `OutFlow`: adds convective/Neumann outflow nodes and extra old-distribution
  storage; use only for open-boundary cases.
- `thermo` and `planarBenchmark`: thermocapillary route, not required for the
  non-isothermal-free reproduction of wetting/drop-impact cases unless the
  target benchmark explicitly uses temperature-dependent surface tension.

Key TCLB settings available in `Dynamics.R`:

```text
Density_h, Density_l
PhaseField_h=1, PhaseField_l=0
IntWidth
M, omega_phi = 1/(3*M + 0.5)
sigma
radAngle
Viscosity_h, Viscosity_l, tauUpdate
VelocityX/Y/Z
Pressure
GravitationX/Y/Z, BuoyancyX/Y/Z
Radius, CenterX/Y/Z, BubbleType
```

Useful exported quantities:

```text
Rho, PhaseField, U, P, Pstar, Normal, IsItBoundary
GradPhi        only with geometric
ActualNormal   only with staircaseimp
```

Important implementation details from `Boundary.c.Rt`:

- Surface-energy wetting computes wall phase from `radAngle`, wall-normal
  distance `h`, `IntWidth`, and neighboring fluid phase `pf_f`.
- Geometric wetting computes wall phase from the tangent component of
  the phase-field gradient and `tan(pi/2 - radAngle)`.
- Geometric branch needs near-wall phase-gradient storage and special finite
  difference handling close to boundaries.
- Staircase improvement computes an actual wall normal, intersects the normal
  ray with a D3Q27 cell face, and uses triangle/barycentric interpolation to
  sample phase or gradient at the corrected geometry location.
- If interpolation points fall inside solid, the code falls back to simpler
  handling or surface-energy-like treatment for special nodes. These fallback
  counts must be reported in any reproduction.

## External Parameter Data Still Needed

The DOI and article metadata are confirmed, but the full numerical parameter
tables/figures were not fully retrievable in this run from ScienceDirect/SSRN.
Before calling any reproduction exact, collect the following from the PDF,
supplement, author repository, or figure captions:

### Droplet Spreading On Sphere

Required exact data:

- computational domain size and boundary conditions;
- solid sphere radius and center;
- droplet radius, initial center, and initial overlap/separation from sphere;
- contact angles tested;
- density ratio and viscosity ratio;
- `sigma`, `M`, `IntWidth`, relaxation times or viscosities;
- whether phase field uses D3Q15 or D3Q27;
- geometry voxelization rule for the sphere;
- output time and convergence criterion;
- reported metric: apparent contact angle, wetted area, contact-line radius,
  spherical-cap geometry, final morphology, or error norm.

### Capillary Intrusion

Required exact data:

- capillary/pore geometry, radius or hydraulic diameter, length, and wall shape;
- inlet/reservoir configuration and boundary conditions;
- contact angle values;
- density/viscosity ratio and absolute lattice properties;
- `sigma`, `M`, `IntWidth`, relaxation parameters;
- body force or pressure difference, if any;
- Lucas-Washburn or modified analytical reference used by the paper;
- front-position extraction rule and time normalization.

### Droplet Impact On Sphere

Required exact data:

- droplet radius and sphere radius ratio;
- initial droplet-sphere gap and initial velocity;
- density ratio, viscosity ratio, `sigma`, `M`, `IntWidth`;
- target dimensionless groups: Re, We, Oh, density ratio, viscosity ratio,
  contact angle, nondimensional film or gap thickness if present;
- domain size and boundary conditions;
- metric definitions: spreading factor on the sphere, wetted arc, maximum
  wetted area, rebound/contact time, film thickness, morphology snapshots;
- reference data used by the paper, including Mitra et al. if applicable.

## Mandatory Calibration Closure Before Reproduction Claims

### C0. Build And Source Audit

Build and record separate binaries:

```text
surface_q27
surface_q27_staircaseimp
geometric_q27
geometric_q27_staircaseimp
geometric_q27_staircaseimp_tprec
```

For each binary record:

- compile options from generated `Consts.h`;
- executable path and SHA256;
- build log;
- source revision or source tree timestamp;
- whether local patches are present.

### C1. Laplace Sigma Closure

Purpose: close `sigma_input -> sigma_eff`.

Run periodic static droplets without walls at several radii. Fit:

```text
Delta p = 2 sigma_eff / R
```

Report:

- input `sigma`, fitted `sigma_eff`, intercept, R2, residuals;
- pressure sampling regions inside/outside droplet;
- radius extraction method from `phi=0.5`;
- mass/phase drift;
- maximum spurious velocity and Mach;
- nonfinite count.

Use `sigma_eff`, not blindly `sigma_input`, for We/Ca/Oh in impact comparisons.

### C2. Static Wetting Closure On Planar Wall

Purpose: verify `radAngle -> theta_eff` before curved geometry.

Run at least:

```text
theta = 45, 57, 70, 80, 90, 100, 110, 135 deg
R = 24, 32, 48 where feasible
IntWidth = 4, 6, 8 as resolution permits
```

Primary near-wall metric:

```text
two-row row-pair 1-2, phi=0.5, x/z mid-slices, left/right contact lines
```

Sensitivity:

```text
phi = 0.45, 0.50, 0.55
row pairs = 1-2, 2-3, 3-4
```

Auxiliary morphology metrics:

```text
endpoint spherical-cap apparent angle
low-band apparent angle
global circle fit
```

Gate for boundary-condition metric:

- target-angle error <= 5 deg;
- x/z and left/right spread <= 5 deg;
- nonfinite = 0;
- mass/rho drift and Mach reported.

### C3. Static Wetting Closure On Sphere

Purpose: verify wall-normal and staircase treatment in curved geometry.

Use the paper geometry once exact parameters are recovered. If exact parameters
remain unavailable, run a controlled surrogate matrix:

```text
sphere radius Rs = 24, 32, 48 lu
droplet radius Rd = 24, 32, 48 lu
theta = 45, 90, 135 deg first, then paper angles
variants = surface, surface_staircase, geometric, geometric_staircase
```

Report:

- apparent contact angle or wetted area on the sphere;
- contact-line distribution on the sphere;
- `Normal` vs `ActualNormal` statistics;
- special-boundary fallback counts;
- mass drift, max Mach, nonfinite;
- overlay plots showing sphere, `phi=0.5` interface, contact line, and normal.

This is the critical bridge between our planar-wall issue and the official
complex-geometry wetting paper.

### C4. Mobility, Interface Width, And Grid Closure

Purpose: separate physical disagreement from diffuse-interface numerics.

For every benchmark family keep these ratios controlled:

```text
Cahn number: Cn = IntWidth / characteristic radius
phase Peclet-like control: U * L / M
Mach: max(|u|)/cs, target comfortably below 0.1
```

Run a minimal sensitivity matrix:

```text
IntWidth = 4, 6, 8
M = 0.01, 0.025, 0.05
R or characteristic size = 24, 32, 48 where memory permits
```

Report which observable changes:

- contact-line location;
- dimple/void formation;
- maximum spreading;
- mass/rho drift;
- max Mach;
- late-time convergence.

### C5. Capillary Intrusion Closure

Purpose: verify dynamic wetting/contact-line motion independent of impact.

Compare intrusion front position against the paper reference law. At minimum:

```text
x_front(t)^2 should be linear in t for Lucas-Washburn-like regime
```

Use `sigma_eff` and measured `theta_eff`, not just input `sigma` and `radAngle`.

Report:

- front-position extraction overlay;
- x_front(t), x_front^2(t), slope and error;
- mass drift and phase leakage;
- contact-line stability;
- whether staircase changes the result.

### C6. Sphere Impact Closure

Purpose: reproduce the official closest impact benchmark before planar
rho_ratio=772 claims.

Only after C1-C5 pass, run paper-matched sphere-impact cases:

- same Re/We/Oh/rho ratio/viscosity ratio/contact angle as paper;
- same initial gap, velocity, and geometry;
- same beta/wetted-area/contact-line definition as paper.

Mandatory outputs:

```text
beta_area(t) or paper-equivalent spreading metric
beta_box(t), if applicable
contact line / wetted arc / wetted area
beta_max or max wetted metric
first contact time
rebound or resting candidate
mass drift, rho drift
max Mach
nonfinite
morphology snapshots with marked algorithmic features
case XML, run.log, summary JSON, metrics CSV, artifact paths
```

## Reproduction Execution Order

1. Retrieve full paper PDF/supplement and extract exact benchmark parameter
   tables. If unavailable, mark all runs as surrogate reproduction.
2. Build and audit binaries for surface/geometric/staircase/tprec variants.
3. Run Laplace sigma calibration with the same `M/IntWidth/grid` family.
4. Run planar static wetting only as a boundary-condition sanity bridge.
5. Run sphere static spreading and compare surface vs geometric vs staircase.
6. Run capillary intrusion and compare front-position dynamics.
7. Run sphere impact and compare the paper's spreading/morphology curves.
8. Only then decide whether the current planar dry-wall impact issue is a
   model/BC problem, a postprocessing metric problem, or an under-resolution
   problem.

## Gate Labels

- all new runs start as `exploratory_not_validation`;
- source/build sanity can become `runtime_sanity`;
- individual calibration closures can become `validation_candidate` only after
  read-only audit;
- do not assign `validation_passed` until exact paper parameters, metric
  definitions, and reproduced curves pass audit.

## Minimum Artifact Indexing

Each case must record:

```text
remote run dir
binary path and SHA256
case XML
run.log and stderr/returncode
summary JSON
metrics CSV
curated figures
raw VTI/PVTI retention policy
whether raw data stayed remote-only
```

Do not copy raw VTI/PVTI locally unless a specific audit requires it.

