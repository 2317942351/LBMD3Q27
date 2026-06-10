# PRE 2025 Table II q27 Geometric 200k TCLB Analogue

Status: `exploratory_not_validation`

This artifact is a TCLB `d3q27_pf_velocity_q27_geometric` analogue comparison
for the reduced spherical static-wetting setup in PRE 2025 Table II. It is not
an exact reproduction of the PRE D3Q19/D3Q19 conservative Allen-Cahn MRT model
or of its wetting-boundary reconstruction.

## Paths

- Remote run root:
  `/media/yuan/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_tableII_q27_geometric_200k_20260610`
- Local artifact:
  `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_tableII_q27_geometric_200k_20260610`
- Local case XMLs:
  `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\pre2025_sphere_tableII_q27_geometric_200k_20260610`
- Summary CSV:
  `summary\pre2025_sphere_tableII_summary.csv`
- Comparison CSV:
  `summary\tableII_q27_geometric_200k_comparison.csv`
- Comparison figure:
  `summary\tableII_q27_geometric_200k_comparison.png`

## Case Definition

```text
domain = 80 x 80 x 140 lu
R_drop = 24 lu
R_solid = 24 lu
target theta = 30,40,50,60,70,80,90,100,110,120,130 deg
TCLB radAngle = target theta in this batch
Density_h/Density_l = 1000
dynamic viscosity ratio = 900
M = 0.2
IntWidth = 6
sigma = 5e-5
tauUpdate = 3
steps = 200000
VTK interval = 20000
```

## Main Result

All 11 q27-geometric cases completed to 200000 steps with
`run.returncode=0`, `postprocess_returncode=0`, no run-log NaN hits, and
`max_nonfinite_count=0`. The maximum Mach number was very small
(`6.22e-4` max over the batch).

The result is numerically stable but not quantitatively matched to PRE Table II.
TCLB q27-geometric H1-H2 errors are substantially larger than the article's
scheme:

```text
mean TCLB H1-H2 error = 12.4967 %
max TCLB H1-H2 error = 32.5064 % at theta030
mean PRE 2025 scheme error = 1.9455 %
max fitted-angle offset = 30.2527 deg at theta130
max fluid-only phase drift = 1.2683 %
max fluid-only rho drift = 1.2484 %
NumSpecialPoints = 392 for every case
```

Representative rows:

```text
theta030: H1-H2 error 32.5064 %, fitted angle 45.0698 deg
theta090: H1-H2 error 7.7076 %, fitted angle 101.4220 deg
theta130: H1-H2 error 8.1489 %, fitted angle 160.2527 deg
```

## Interpretation

The current q27-geometric route is a stable exploratory route for this reduced
spherical benchmark, unlike the earlier q27-geometric-staircaseimp batch that
hit PhaseField NaNs on most non-90 angles. The dominant issue here is a
systematic wetting-response mismatch: the fitted apparent angle is larger than
the target across the sweep, especially toward the high-angle end.

The next diagnostic direction is not a longer same-parameter run. The useful
next screen is an inverse `radAngle` map using the same Table II target geometry
to test whether TCLB can be calibrated by input-angle remapping, followed by
small `M`, `sigma`, and boundary-variant checks if remapping alone is
insufficient.

## Raw Data Policy

Curated logs, XML/config files, TCLB CSV logs, postprocess CSV/JSON summaries,
and comparison outputs are local. Raw VTI/PVTI fields remain remote-only unless
a later audit needs specific frames.
