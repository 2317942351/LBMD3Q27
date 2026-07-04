# He-Li-Wang-Tong 2023 LBM Theory/Application Excerpt: Code Map

Date: 2026-07-03
Status: `literature_anchor`
Source: `C:/Users/yuanz/Downloads/15215943_相场多相流润湿篇.md`
SHA256: `EF76B77D366466B1E25299121CEAF7808E4C4FADEC1CBF816BED009A1E9EAB5F`

The full source text is not committed. This file stores only project-specific
paraphrases and code-routing notes.

## Section Map

| Local excerpt lines | Topic | Current project meaning |
|---:|---|---|
| 23-102 | Free-energy contact-angle format | Surface free energy and Cahn wall relation belong to free-energy/phase-field style models; do not mix blindly with pseudo-potential formulas. |
| 103-168 | Pseudo-potential contact-angle format | Virtual density and fluid-solid force are pseudo-potential tools; they are useful warning examples but not direct repairs for this TCLB phase-field solver. |
| 169-230 | Color-gradient contact-angle format | Contact angle may be imposed by correcting interface normal/gradient direction; useful conceptually for geometry, but model-specific. |
| 231-341 | Phase-field theory | Chemical potential, double-well free energy, order parameter, and density interpolation define the phase-field closure being audited. |
| 428-534 | Large-density-ratio phase-field model | Large density ratio requires correct phase equation and force coupling; average-density or matched-density models can give misleading apparent stability. |
| 535-605 | Phase-field contact-angle format | Phase-field wetting uses surface free energy or geometric contact-angle reconstruction of virtual order parameter; chemical-potential no-flux is part of mass conservation. |
| 609-840 | Complex boundary treatment | Interpolated curved boundaries are per-link and may cause mass loss; correction requires explicit incoming/outgoing mass accounting. |

## Code Anchors

Primary active snapshot:

`third_party/tclb_snapshots/stage14_B111_slim_wall_h_quarantine/models/multiphase/d3q27_pf_velocity/`

Relevant files:

- `Dynamics.R`
- `Dynamics.c.Rt`
- `Boundary.c.Rt`
- `scripts/stage14/stage14_s2_replay_smoke.py`

Observed anchors:

- `Dynamics.R:1045`: `PhaseEquationMode`.
- `Dynamics.c.Rt:4716`: `calcPhaseF()`.
- `Dynamics.c.Rt:5158`: `calcF_phi(...)`.
- `Dynamics.c.Rt:5169-5188`: B113 normalized `tmp1` helper path.
- `Dynamics.c.Rt:5742`, `6395`: `rho(C)` interpolation.
- `Dynamics.c.Rt:5761`: `p = m0[0]`.
- `Boundary.c.Rt:745`: analytic wall ghost function.
- `Boundary.c.Rt:1956`: compact-stencil write is gated to flat analytic solids.
- `Boundary.c.Rt:2211`: direct `PhaseF = WallGhost` active-write hazard.

## Project-Specific Interpretation

### 1. Contact-Angle Formulas Must Not Be Mixed Across Model Families

The excerpt lays out different contact-angle formats for free-energy,
pseudo-potential, color-gradient, and phase-field models. This is directly
relevant because the current project has accumulated many wetting ideas from
different LBM families.

Rule for future repair:

```text
No pseudo-potential virtual density or color-gradient gradient-correction
formula may be used as a physical repair for the current phase-field model
unless it is explicitly re-derived as a phase-field order-parameter boundary.
```

### 2. Phase-Field Wetting Has Two Main Legitimate Paths

For the current model, the relevant phase-field wetting paths are:

```text
surface-free-energy boundary:
  n_w dot grad(phi) constrained by dH/dphi_w

geometric contact-angle boundary:
  construct a local virtual order parameter from fluid-side values and target angle
```

This supports using geometric `WallGhost` as a candidate only if it is treated
as a virtual order-parameter reconstruction with the right phase equation and
mass behavior. It does not justify writing arbitrary ghost values into
`PhaseF`.

### 3. Chemical-Potential No-Flux Is A Missing Gate

The phase-field contact-angle section notes that chemical potential should have
a no-flux wall condition for global mass conservation. In current TCLB code,
the wall work has focused heavily on `WallGhost`, `PhaseF`, and `h_i`.

Next audit implication:

```text
After B113/B115 phase-source timing is checked, add a wall mu/grad-mu no-flux
audit before claiming static wetting validation.
```

### 4. Interpolated Curved Boundaries Can Break Mass Conservation

The complex-boundary chapter explicitly states that interpolation-based curved
boundary schemes can destroy mass conservation and shows a mass-loss correction
based on outgoing and incoming distributions.

This maps strongly to Stage14 history:

- B59/B60/B63/B68/B81/B98/B111 are all attempts to repair wall-origin `h_i`
  streaming or `PhaseF` reconstruction.
- The new literature says this must be framed as a distribution-level
  incoming/outgoing mass budget, not only as a local phase clamp.

Therefore, future curved sphere/cylinder work should include:

```text
per-link outgoing h_i budget
per-link incoming reconstructed h_i budget
net wall mass delta
optional conservative redistribution
```

### 5. Large Density Ratio Stability Is Not A TCLB GPU Question

The large-density-ratio phase-field discussion warns that some models can look
stable only because they are effectively matched-density or average-density
systems. The current `rho(C)` path makes phase overshoot dangerous:

```text
if C leaves [PhaseField_l, PhaseField_h],
rho(C), viscosity, force/rho, and morphology are no longer physical.
```

So the first repair remains phase boundedness and source closure, not grid
refinement or GPU throughput.

## How This Changes The Work Plan

This source strengthens, but does not replace, the current route:

1. Finish B113/B114 normalized `tmp1` algebra smoke.
2. Add B115: source/equilibrium/half-source timing audit.
3. Add B116: chemical-potential wall no-flux audit.
4. Reframe wall `h_i` repair as per-link incoming/outgoing mass budget.
5. Only then resume contact-angle validation and curved-wall writes.

It specifically argues against:

- mixing virtual density from pseudo-potential into the current phase-field
  solver;
- treating color-gradient normal correction as a drop-in wetting formula;
- claiming contact angle success when mass/morphology is being repaired by
  clamps;
- ignoring mass loss introduced by interpolation at curved boundaries.
