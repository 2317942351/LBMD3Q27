# Literature Case Matrix For TCLB Validation

Date: 2026-06-06

Purpose: identify which literature cases can be used for data-level validation
of the TCLB route. Cases are ranked by how directly they can produce numerical
comparison data, not by general relevance.

## Validation Levels

```text
A = data-level comparison: curve/table/scalar error can be computed.
B = semi-quantitative comparison: morphology plus partial scalar metrics.
C = background/method evidence only.
```

## A-Level Cases

### A1. TCLB/Fakhari-Route Bubble Rise

Source and availability:

```text
TCLB example:
  /home/yuan/src/TCLB/example/multiphase/d3q27_pf_velocity/bubbleRiseBenchmark.xml.RT
The XML cites Safi et al. (2017), Computers & Mathematics with Applications.
```

Why it matters:

```text
This is built into the exact TCLB model used for the project.
It validates buoyancy, density/viscosity ratio handling, surface tension,
phase-field transport, and GPU runtime on a dynamic benchmark.
```

Comparison outputs:

```text
bubble centroid versus time
rise velocity versus time
terminal Reynolds number if reference data are digitized
phase mass conservation
max velocity / Mach
shape snapshots at literature times
```

Status:

```text
Already completed once on HM570 as a runtime sanity case.
Needs a formal reproduction notebook/script and digitized reference table.
```

### A2. TCLB Contact-Angle Static Droplet

Source and availability:

```text
TCLB examples:
  ContactAngle_45.xml
  ContactAngle_45_symX.xml
  ContactAngle_45_symXZ.xml
```

Why it matters:

```text
The final target compares 45, 90, and 135 deg contact angles.
Before impact, the wall wetting implementation must reproduce static apparent
angles under the same postprocessing convention.
```

Comparison outputs:

```text
apparent contact angle from phi=0.5 contour
equilibrium droplet footprint radius and height
phase mass drift
spurious current / max velocity after relaxation
```

Acceptance direction:

```text
apparent angle within about 3-5 deg after contour-fit convention is fixed
mass drift reported
spurious velocity small relative to intended impact speed
```

### A3. Wang 2023 Co-Current Two-Phase Poiseuille Flow

Source and availability:

```text
Wang et al. 2023 IJMF, DOI 10.1016/j.ijmultiphaseflow.2023.104582.
Local files:
  references/papers/wang2023_ijmf_ucl.pdf
  references/extracted/wang2023_ijmf_d3q27_vlm.md
```

Why it matters:

```text
It is the clearest table/curve validation in the Wang 2023 paper.
It tests high density ratio and interface velocity continuity.
Wang 2023 reports that the Local gradient scheme improves the interface
discontinuity problem.
```

Comparison outputs:

```text
layer-averaged velocity profile
L2 or max relative error against analytical Eq. (30)
rows matching Wang Table 2 where possible
interface continuity error
mass and Mach diagnostics
```

Risk:

```text
TCLB is not Wang 2023 ULBM(NMRT). This case validates physical behavior and
accuracy, not formula equivalence.
```

### A4. Wang 2023 Bubble Rise In Water

Source and availability:

```text
Wang 2023 Section 3 validation.
The extracted table reports Bo, Mo, experimental Re, NMRT Re, and errors for
three cases.
```

Why it matters:

```text
It gives direct scalar error metrics against experimental data and other
methods. It is closer to realistic density-ratio multiphase dynamics than a
static contact-angle check.
```

Comparison outputs:

```text
terminal Reynolds number
bubble centroid and shape snapshots
phase mass drift
Mach / nonfinite report
```

Target literature values from the extracted Wang table:

```text
Case 1: Bo=32.2, Mo=8.20e-4, Exp Re=55.3, Wang NMRT Re=55.54
Case 2: Bo=115,  Mo=4.63e-3, Exp Re=94.0, Wang NMRT Re=92.83
Case 3: Bo=339,  Mo=43.1,    Exp Re=18.3, Wang NMRT Re=19.12
```

### A5. Fei 2019 Dry-Wall Fuel-Droplet Impact

Source and availability:

```text
Fei et al. 2019 Physics of Fluids, DOI 10.1063/1.5087266.
Local files:
  references/papers/fei2019_pof_nmrt.pdf
  references/extracted/fei2019_pof_nmrt_vlm.md
```

Why it matters:

```text
This is the closest data-level dry-wall impact validation found in the local
literature set. It compares spreading diameter with experiments and SPH for
fuel droplets at high Reynolds and Weber numbers.
```

Available dry-wall cases from the extraction:

```text
ethanol: R=1.2 mm, U=3.1 m/s, Re about 2500, We about 410
simulation: R0=70 lu, U=0.125, nu_l=0.0035, domain about 9R x 9R x 3.5R
diesel: R=1.3 mm, U=3.1 m/s, Re about 930, We about 350
simulation: R0=50 lu
```

Comparison outputs:

```text
spreading diameter versus time
beta_max
snapshots at published times
liquid volume/mass evolution
```

Risk:

```text
Fei 2019 uses a pseudopotential multiphase route, while TCLB d3q27_pf_velocity
uses phase-field dynamics. Use this as dry-wall physical validation, not as a
method-equivalence proof.
```

## B-Level Cases

### B1. Wang 2023 Rayleigh-Taylor Instability

Use for:

```text
large-density-ratio dynamic instability morphology
front/spike/bubble location versus time if reference curves are digitized
```

Risk:

```text
Useful for dynamic confidence, but less directly connected to wall impact.
```

### B2. Wang 2023 Binary Droplet Collision

Use for:

```text
high density ratio up to 1000 or 5000
morphology sequence versus experimental snapshots
collision outcome regime
```

Risk:

```text
Harder to reduce to a single robust scalar unless collision-specific metrics
are implemented.
```

### B3. Wang 2023 Thin Liquid-Film Splash

Source details:

```text
rho_h/rho_l = 1000
mu_h/mu_l = 67
domain = 14R0 x 14R0 x 6R0
R0 = 60 lu
w = 5
M_phi = 0.05
We = 380
Re = 6000
U0 = 0.045 lu
h* = 0.15 and 0.35 in simulation
experimental comparison h* = 0.07 and 0.16
```

Use for:

```text
crown diameter evolution
prompt splash / crown morphology
breakup point
qualitative comparison with experiment snapshots
```

Risk:

```text
This is expensive and not a first validation case. It should follow A1-A5.
It validates liquid-film splash, not dry-wall contact-angle settling.
```

## C-Level Sources

### C1. Wang 2024 JFM

Use only for:

```text
same-group ULBM/NMRT phase-field formula context
possible supplementary formula expressions
```

Do not use as:

```text
D3Q27 high-We dry-wall validation
```

### C2. General Droplet-Impact Correlations

Useful external references include:

```text
Mao et al. / dry-wall spreading data: We about 50-1080, multiple surfaces.
NIST/Kurabayashi-Yang wetting correction: contact-angle effect at low We.
Langmuir inkjet droplet controlled contact angle: beta correlation with theta.
```

Use for:

```text
sanity range of beta_max
contact-angle trend direction
discussion of model limitations
```

Do not use as sole validation unless the original data are digitized and the
case properties match the simulation.

## Recommended Validation Order

```text
1. ContactAngle_45/90/135 static droplets
2. TCLB bubbleRise benchmark
3. Wang 2023 Poiseuille profile
4. Wang 2023 or TCLB Rayleigh-Taylor dynamic case
5. Fei 2019 dry-wall ethanol/diesel spreading curve
6. Wang 2023 thin-film splash crown diameter
7. User target: 1 mm droplet, 10 mm release, theta=45/90/135, run to rest
```

