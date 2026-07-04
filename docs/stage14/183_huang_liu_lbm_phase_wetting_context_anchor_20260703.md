# Stage14 Context Anchor: Huang-Liu 2023 LBM Phase/Wetting Excerpt

Date: 2026-07-03
Branch: `work/phasefield-c-reference-20260623`
Status: `context_anchor_for_compaction`
Source: `C:/Users/yuanz/Downloads/格子BOLTZMANN方法从入门到精通_相场多相流润湿篇.md`
SHA256: `504571167012619CD6BD85BE125A01F9AEA41E55407E23A2C85782CA0EA05052`

This anchor records how the new literature changes or reinforces the current
LBMD3Q27 repair route. It deliberately avoids copying the full source text.

## Bottom Line

The excerpt is useful. Its value is not that it gives a magic contact-angle
formula to paste into TCLB. Its value is that it confirms three constraints:

```text
1. The phase population h_i and source term must be closed before wetting claims.
2. Curved-wall treatment is per-link and time-level sensitive.
3. Contact-angle examples are validation workflows, not interchangeable model formulas.
```

Therefore this source supports the current decision to fix:

```text
PhaseF -> tmp1/F_phi -> h update -> PhaseFromH -> rho(C) -> force closure
```

before returning to sphere/cylinder wetting or dynamic impact.

## Chapter-Specific Help

### Chapter 10: Phase-Field LBM

Use for:

- `h_i` population evolution.
- source term proportional to the equilibrium interface profile.
- distinction between Cahn-Hilliard and conservative Allen-Cahn style models.
- density and viscosity interpolation from order parameter.

Current code relevance:

- `Dynamics.c.Rt:4716` `calcPhaseF()`.
- `Dynamics.c.Rt:5158` `calcF_phi(...)`.
- `Dynamics.c.Rt:5169-5188` B113 `tmp1` helpers.
- `Dynamics.c.Rt:5542`, `6075`, `6496` active `tmp1` call sites.
- `Dynamics.c.Rt:5742`, `6395` `rho(C)` interpolation.
- `Dynamics.R:1045` `PhaseEquationMode`.

Immediate implication:

B113 is meaningful because the legacy `tmp1` formula implicitly assumes
`PhaseField_l=0` and `PhaseField_h=1`. The normalized source is the right
first repair. The next necessary step is not contact-angle retuning, but a
source/equilibrium timing audit:

```text
heq moment
Fphi zeroth moment
Fphi first moment
Fphi second moment
half-source placement in the TCLB generated h update
```

### Chapter 6: Curved Boundary And Moving Solid Force

Use for:

- curved wall link distance `q`;
- interpolation bounce-back;
- non-equilibrium extrapolation;
- momentum exchange concepts for future moving solid/dynamic impact work.

Current code relevance:

- `Boundary.c.Rt:745` analytic wall ghost.
- `Boundary.c.Rt:1956` compact write gate.
- `Boundary.c.Rt:2211` direct `PhaseF = WallGhost` hazard.
- `Dynamics.R:1029-1037` analytic solid and compact-stencil settings.

Immediate implication:

This literature reinforces the earlier TCLB-specific warning: a scalar
`WallGhost` is not equivalent to a full C-style passive ghost node, and it is
not equivalent to per-link curved-wall population reconstruction. Curved
sphere/cylinder work should remain behind flat-wall phase boundedness and
population timing gates.

### Chapters 8-9: Contact Angle In Shan-Chen And Free-Energy Models

Use for:

- validation case design;
- understanding how legacy wetting examples measure static contact angle;
- separating model families.

Do not use for:

- direct transfer of Shan-Chen virtual-density contact-angle formulas into the
  current phase-field model;
- claiming a phase-field contact-angle validation when morphology is already
  distorted;
- replacing the conservative Allen-Cahn source/force derivation.

## Effect On Current Plan

This source does not overturn the current plan. It sharpens it:

1. Finish B114: generate/compile/run B113 `PhaseEquationMode=0/1` smoke.
2. Add B115: inspect `heq/Fphi/h` source timing against the phase-field LBE.
3. Add B116 if needed: make `PhaseEquationMode=2` a derived source/equilibrium
   correction, not a limiter.
4. Revisit pressure/force closure only after `PhaseF` stays bounded and
   morphology is credible.
5. Revisit contact angle only after the droplet shape is physically credible.

## One-Sentence Memory

Huang-Liu 2023 supports the route of repairing the phase-population source and
TCLB streaming semantics first; it makes curved-wall wetting and contact-angle
measurement downstream validation gates rather than immediate tuning targets.
