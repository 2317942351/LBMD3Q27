# Stage14 Context Anchor: He-Li-Wang-Tong 2023 LBM Theory/Application

Date: 2026-07-03
Branch: `work/phasefield-c-reference-20260623`
Status: `context_anchor_for_compaction`
Source: `C:/Users/yuanz/Downloads/15215943_相场多相流润湿篇.md`
SHA256: `EF76B77D366466B1E25299121CEAF7808E4C4FADEC1CBF816BED009A1E9EAB5F`

This anchor records only project-specific conclusions. Do not commit the full
book excerpt.

## Why This Source Matters

This book excerpt is useful because it separates wetting/contact-angle
implementation by multiphase LBM model family:

```text
free-energy model
pseudo-potential model
color-gradient model
phase-field model
```

The current TCLB solver is a phase-field model. Therefore, contact-angle
formulas from pseudo-potential virtual density or color-gradient normal
correction cannot be pasted in as physical repairs unless they are explicitly
re-derived for the phase-field order parameter.

## Most Important Constraints For Current Code

### C1. Model-Family Separation

Do not mix formulas:

```text
pseudo-potential virtual density != phase-field WallGhost
color-gradient contact-angle normal correction != phase-field h_i source repair
free-energy density boundary != automatically valid for conservative Allen-Cahn
```

Use the non-phase-field sections only as cautionary analogies and validation
workflow references.

### C2. Phase-Field Wetting Has Two Legitimate Directions

For this project, the useful phase-field wetting options are:

```text
1. surface-free-energy boundary:
   n_w dot grad(phi) is set by dH(phi_w)/dphi_w

2. geometric contact-angle boundary:
   construct local virtual order parameter at solid/ghost location from target angle
```

This supports future `WallGhost` work only when it is treated as a controlled
virtual order-parameter reconstruction and not as arbitrary direct `PhaseF`
writing.

Code anchors:

- `Boundary.c.Rt:745` analytic wall ghost.
- `Boundary.c.Rt:1956` compact write gate.
- `Boundary.c.Rt:2211` direct `PhaseF = WallGhost` hazard.

### C3. Chemical-Potential No-Flux Must Be Audited

The phase-field contact-angle section states that chemical potential should
have a no-flux wall condition to preserve total mass. Current Stage14 work has
mostly traced `PhaseF`, `WallGhost`, and `h_i`.

Add to the next repair sequence:

```text
B116 candidate:
  audit grad(mu) dot n at wall
  audit calcMu near-wall stencil inputs
  reject solid sentinel contamination
  report wall chemical-potential flux
```

### C4. Curved/Interpolated Boundaries Can Create Mass Loss

The complex-boundary chapter explicitly identifies interpolation-induced mass
loss and a correction based on outgoing and incoming distribution sums.

This maps directly to the current wall `h_i` problem:

```text
wall-origin h_i reconstruction must be audited as incoming/outgoing population
mass balance, not only as PhaseF clamping.
```

Future wall repair should output:

```text
WallHOutgoingMass
WallHIncomingMass
WallHNetMassDelta
WallHMassCorrectionApplied
```

before claiming physical contact-angle validation.

### C5. Large Density Ratio Requires Correct Phase Closure First

The large-density-ratio phase-field section warns that apparent stability can
come from matched-density or average-density simplifications. Current code uses
`rho(C)` interpolation:

- `Dynamics.c.Rt:5742`
- `Dynamics.c.Rt:6395`

So if `C` leaves its valid range, `rho`, viscosity, and `F/rho` all become
invalid. Grid refinement cannot solve this root cause by itself.

## Effect On Next Work

This source reinforces the current route:

1. Finish B113/B114 normalized `tmp1` smoke.
2. Add B115: source/equilibrium/half-source timing audit.
3. Add B116: chemical-potential no-flux and near-wall `mu` audit.
4. Reframe wall `h_i` repair as per-link mass budget.
5. Resume contact angle only after morphology and mass are credible.

## One-Sentence Memory

He-Li-Wang-Tong 2023 is mainly a guard against model-family mixing: for this
phase-field TCLB solver, wetting must be implemented as phase-field
surface-free-energy or geometric order-parameter reconstruction, while curved
boundary fixes must include per-link population mass conservation.
