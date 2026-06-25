# Stage17B-B10 Initial Cylinder-Cap Equilibrium Audit

Date: 2026-06-25

Status:

```text
B10 offline gate: COMPLETE
claim limit: offline initial-condition audit only; not contact-angle validation
solver edits: none
```

This stage does not run a new TCLB case, does not validate static contact
angle, and does not justify dynamic impact cases.

## Purpose

B9 showed that the neutral `90 deg` cylinder drift is already present in the
pure legacy zero-write baseline.  The B9 momentum probe showed a finite early
force transient, but not a sustained pressure / `F_mu` / `F/rho` blow-up.

B10 therefore tests the next hypothesis:

```text
The CylinderCapInit field is already a discrete non-equilibrium state near
the curved cylinder wall, so the first few TCLB steps release this residual
before any controlled wetting write path can be judged.
```

## Input

The audit reconstructs the exact B9 neutral-cylinder initialization from:

```text
cases/diagnostics/stage17B_B9_baseline_20260625_lite/
  cylinder_init090_b9_A_legacy_lite_s0001/case.xml
```

Key parameters:

| parameter | value |
|---|---:|
| grid | `96 x 96 x 96` |
| density ratio | `200` |
| `Density_h` | `1.0` |
| `Density_l` | `0.005` |
| `sigma` | `5e-05` |
| `IntWidth` | `3` |
| cylinder center | `(48, 48, 48)` |
| cylinder radius | `20` |
| cylinder axis | `z` / `AnalyticSolidAxis=2` |
| parent cap sphere center | `(48, 85.65074619549219, 48)` |
| parent cap sphere radius | `37.650746195492204` |
| target `radAngle` | `90d` |

The relevant TCLB initializer is in:

```text
third_party/tclb_snapshots/stage17B_diffuse_solid_shadow/
  models/multiphase/d3q27_pf_velocity/Dynamics.c.Rt
```

It constructs a 3D parent-sphere phase field and then masks the z-axis
cylinder solid:

```text
Ri = sqrt((X-Cx)^2 + (Y-Cy)^2 + (Z-Cz)^2)
radial = sqrt((X-Sx)^2 + (Y-Sy)^2)
PhaseF = (radial < solid_radius) ? PhaseField_l : cap_pf
```

This is not the same as a purely 2D circular cap on a cylinder cross-section.

## Method

Script:

```text
scripts/stage17/stage17B_B10_initial_cap_equilibrium.py
```

Artifacts:

```text
artifacts/stage17B_B10_initial_cap_equilibrium_20260625/
```

The script:

1. parses the B9 `case.xml`;
2. reconstructs `CylinderCapInit` for both coordinate assumptions:
   `cell_center = i + 0.5` and `node = i`;
3. evaluates the same D3Q27 isotropic Laplace stencil used by TCLB
   `myLaplace`:

```text
face=16, edge=4, corner=1, center=-152, divided by 36
```

4. evaluates the same D3Q27 isotropic gradient stencil family divided by `72`;
5. computes the same chemical-potential formula used by `calcMu`:

```text
mu = 4*(12*sigma/IntWidth)*(C-PhaseField_l)*(C-PhaseField_h)*(C-pfavg)
     - (1.5*sigma*IntWidth)*lapPhi
```

6. summarizes full fluid, interface, near-wall, near-wall-interface, contact
   core, bulk-liquid, and bulk-gas regions.

Important limitation:

```text
B10 is an offline periodic-stencil audit. It does not include TCLB streaming,
stage timing, WallGhost consumption, or boundary update semantics.
```

Therefore B10 can support or weaken the initial-condition-release hypothesis,
but it cannot replace a TCLB step-0 / step-1 field replay comparison.

## Key Metrics

The preferred coordinate assumption is `cell_center`, matching the analysis
convention already used by B9 morphology metrics.

| metric | value |
|---|---:|
| interface cells | `38520` |
| near-wall interface cells | `2540` |
| contact-core cells | `556` |
| interface `mu` std | `2.841528294e-05` |
| near-wall interface `mu` std | `7.333138378e-05` |
| near-wall / interface `mu` std ratio | `2.58` |
| contact-core max `|mu|` | `2.701512172e-04` |
| max `|mu - mean(mu_interface)|` | `3.672759065e-04` |
| max `|grad(phi)|` in near-wall band | `6.009252126e-01` |

The `node` coordinate assumption gives the same conclusion:

| metric | value |
|---|---:|
| near-wall interface `mu` std | `7.412009790e-05` |
| contact-core max `|mu|` | `2.789779355e-04` |
| max `|mu - mean(mu_interface)|` | `3.671768221e-04` |

This makes the finding insensitive to the half-cell coordinate convention.

## Classification

`classification.json` reports:

```text
status = b10_offline_initial_cap_audit_complete
primary_suspect = initial_cap_nearwall_discrete_mu_nonuniformity
preferred_coord_mode = cell_center
next_recommended_gate =
  compare TCLB step-0/step-1 VTI PhaseField and ReplayMu against this
  offline reconstruction before changing solver physics
```

## Figures

Generated files:

```text
midplane_phase_mu_grad_cell_center.png
midplane_phase_mu_grad_node.png
mu_grad_hist_cell_center.png
mu_grad_hist_node.png
```

The midplane images show the reconstructed initial phase field, the discrete
chemical-potential field, and `|grad(phi)|` on the cylinder midplane.  The
strongest `mu` deviations sit in the near-wall / interface region, which is
exactly where B9 first saw the contact-line release.

## Interpretation

B10 supports the current B9 root-cause ranking:

```text
primary: CylinderCapInit / phase boundedness / initialization release
secondary: early finite force transient responding to the release
lower priority here: sustained pressure/F_mu/F_over_rho blow-up
```

This does not mean the momentum model is fully cleared.  It means the next
evidence-efficient action is not another wetting write-path patch and not a
dynamic run.  The next action should be a TCLB field replay:

```text
offline reconstructed PhaseF / lapPhi / mu
  vs
TCLB step-0 and step-1 PhaseField / ReplayLapPhi / ReplayMu
```

Only after that comparison should the code branch choose between:

1. fixing or replacing `CylinderCapInit`;
2. adding an equilibrium pre-relaxation / bounded-phase shadow correction;
3. revisiting stencil / WallGhost consumption if TCLB replay disagrees with
   the offline reconstruction;
4. returning to controlled wetting write response after neutral `90 deg`
   cylinder drift is controlled.

## Files Produced

```text
scripts/stage17/stage17B_B10_initial_cap_equilibrium.py
artifacts/stage17B_B10_initial_cap_equilibrium_20260625/metrics.json
artifacts/stage17B_B10_initial_cap_equilibrium_20260625/classification.json
artifacts/stage17B_B10_initial_cap_equilibrium_20260625/region_metrics.csv
artifacts/stage17B_B10_initial_cap_equilibrium_20260625/radial_profile_cell_center.csv
artifacts/stage17B_B10_initial_cap_equilibrium_20260625/radial_profile_node.csv
artifacts/stage17B_B10_initial_cap_equilibrium_20260625/contact_angle_profile_cell_center.csv
artifacts/stage17B_B10_initial_cap_equilibrium_20260625/contact_angle_profile_node.csv
artifacts/stage17B_B10_initial_cap_equilibrium_20260625/midplane_phase_mu_grad_cell_center.png
artifacts/stage17B_B10_initial_cap_equilibrium_20260625/midplane_phase_mu_grad_node.png
artifacts/stage17B_B10_initial_cap_equilibrium_20260625/mu_grad_hist_cell_center.png
artifacts/stage17B_B10_initial_cap_equilibrium_20260625/mu_grad_hist_node.png
```

## Commands

```powershell
python -m py_compile scripts/stage17/stage17B_B10_initial_cap_equilibrium.py
python scripts/stage17/stage17B_B10_initial_cap_equilibrium.py `
  --case cases/diagnostics/stage17B_B9_baseline_20260625_lite/cylinder_init090_b9_A_legacy_lite_s0001/case.xml `
  --out artifacts/stage17B_B10_initial_cap_equilibrium_20260625
git diff --check
```
