# Target Physical Case Plan

Date: 2026-06-06

## User Target

```text
liquid: water-like heavy phase
gas: air-like light phase
rho_ratio = 772
droplet diameter D = 1 mm
droplet radius R = 0.5 mm
release height H = 10 mm above wall
gravity = -z
wall types = dry wall first, then liquid film
contact angles = 45, 90, 135 deg
outputs = beta(t), beta_max, shape snapshots, mass conservation, Mach
termination = droplet reaches static/resting state
```

## Physical Scaling Check

Assuming water-air properties near room temperature:

```text
rho_l ~= 998 kg/m^3
rho_g ~= 1.293 kg/m^3
mu_l ~= 0.89-1.00 mPa s
sigma ~= 0.072 N/m
g = 9.81 m/s^2
```

Free-fall impact velocity from 10 mm:

```text
U = sqrt(2 g H) = sqrt(2 * 9.81 * 0.010) ~= 0.443 m/s
```

Dimensionless numbers based on droplet diameter:

```text
rho_ratio ~= 772
We = rho_l U^2 D / sigma ~= 2.7
Re = rho_l U D / mu_l ~= 440-500
Bo = rho_l g D^2 / sigma ~= 0.136
```

Important implication:

```text
The exact 1 mm / 10 mm free-fall case is not high-We. It is a low-to-moderate
We wetting, spreading, recoil, and settling problem. It is appropriate for
contact-angle comparison, but not for splash-regime validation.
```

Approximate heights required for genuinely high Weber numbers at `D=1 mm`:

```text
We=100  -> H ~= 0.37 m
We=380  -> H ~= 1.40 m
```

## Numerical Strategy

### Preferred Publication Strategy

Do not simulate the entire 10 mm air fall at publication grid density unless
the fall itself is the subject of the paper. Instead:

```text
place droplet close to the wall, usually 0.2D-0.5D above it
initialize droplet velocity Uz = -sqrt(2gH) in physical scaling
keep gravity enabled in -z
run spreading/recoil/settling
```

Reason:

```text
Uniform-grid LBM makes a 10D vertical air gap expensive. With D resolved by
128 cells, the 10 mm fall alone is 1280 lattice cells high before adding wall,
droplet diameter, and top margin.
```

### Full Free-Fall Strategy

Use only if explicitly required after the near-wall impact strategy is proven:

```text
lower-resolution pilot with D=48-64 cells
domain height >= 12D
long pre-impact run under gravity
compare impact velocity at contact with sqrt(2gH)
then repeat near-wall equivalent case to verify equivalence
```

## Grid Density Plan

Minimum practical levels:

```text
pilot:      R0 = 16-24 lu, D = 32-48 cells
engineering: R0 = 32 lu, D = 64 cells
paper target on P100 if memory allows: R0 = 40-48 lu, D = 80-96 cells
paper target on larger GPU/HPC: R0 = 64-96 lu, D = 128-192 cells
```

Interface settings should start from TCLB/Wang-style values:

```text
interface width w = 5 lu
mobility M = 0.05
```

For dry-wall contact-angle studies, `R0/w` should be large enough:

```text
R0=32 -> R0/w=6.4, usable for trends
R0=64 -> R0/w=12.8, preferred for publication
```

## Domain Plan

For near-wall impact:

```text
wall = z=0
gravity = GravitationZ < 0
initial droplet center z = R0 + gap
gap = 0.2D to 0.5D for near-wall impact initialization
side boundaries = periodic unless the spread approaches side boundaries
top boundary = wall or outflow only after testing reflection effects
```

Recommended domain sizes:

```text
pilot R0=24:      nx=ny=192, nz=128
engineering R0=32: nx=ny=256-320, nz=160-192
publication R0=48: nx=ny=384-448, nz=240-288
publication R0=64: nx=ny=512-640, nz=320-384
```

P100 16 GB warning:

```text
TCLB ContactAngle_45_full used about 1.2 GiB for roughly 1.0 million cells.
A 256 x 256 x 192 case is about 12.6 million cells and may approach the
practical memory limit after buffers and VTK output.
R0=64 publication grids likely need a larger GPU or domain decomposition.
```

## Contact-Angle Sweep

Cases:

```text
theta = 45 deg
theta = 90 deg
theta = 135 deg
```

Before impact:

```text
run static droplet relaxation for each theta
measure apparent theta from phi=0.5 contour
record spurious-current level
use the same wetting convention in impact runs
```

Impact comparisons:

```text
beta(t) = D_wet(t) / D0
beta_max
time to beta_max
recoil/oscillation damping
resting footprint diameter
final apparent contact angle
mass drift
max Mach
snapshots at fixed t* and at physical events
```

## Resting-State Criterion

The run is considered static/resting only when all are satisfied over a moving
window, for example 5000-20000 steps depending on resolution:

```text
relative change of beta < 1e-4 to 5e-4 per window
center-of-mass speed < 1e-4 lu/step, or < 1% of initial impact velocity
u_max in liquid < 1e-3 lu/step, adjusted by pilot result
mass drift remains within acceptance threshold
no nonfinite values
```

For publication, thresholds must be justified by grid/time-step sensitivity.

## Implementation Tasks

1. Build `z=0` dry-wall XML templates under `cases/dry_wall/`.
2. Confirm TCLB lower-z and upper-z wall syntax with a small axis/wall test.
3. Implement or configure droplet-only initial velocity. A global `VelocityZ`
   is not acceptable for publication cases.
4. Run static contact-angle calibration for 45/90/135 deg.
5. Run pilot impact cases at `R0=16-24`.
6. Promote to `R0=32` engineering grid after mass and Mach are acceptable.
7. Run grid sensitivity.
8. Only then run long-to-rest production cases.

