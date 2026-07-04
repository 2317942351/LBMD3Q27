# Huang-Liu 2023 LBM Phase/Wetting Excerpt: Code Map

Date: 2026-07-03
Status: `literature_anchor`
Source: `C:/Users/yuanz/Downloads/格子BOLTZMANN方法从入门到精通_相场多相流润湿篇.md`
SHA256: `504571167012619CD6BD85BE125A01F9AEA41E55407E23A2C85782CA0EA05052`

The full text is not committed. This file stores only project-specific
paraphrases and code-routing notes.

## Section Map

| Local excerpt lines | Topic | Useful for current project |
|---:|---|---|
| 10-136 | Curved no-slip boundary, interpolation bounce-back and non-equilibrium extrapolation | TCLB solid/ghost streaming semantics; curved-wall boundary implementation must be per-link and time-level aware. |
| 137-167 | Force calculation on moving solids | Future dynamic impact and moving boundary force accounting; not part of the present static wetting repair. |
| 182-219 | Shan-Chen contact angle | Historical contact-angle workflow only; do not mix pseudo-potential virtual-density formulas into current phase-field model. |
| 825-1305 | Free-energy contact angle and sample code | Useful as a validation pattern for static contact angle, but not a direct formula transplant into the current Allen-Cahn phase-field solver. |
| 1308-1447 | Phase-field model, Cahn-Hilliard and conservative Allen-Cahn | Confirms that order-parameter range, interface width, and source construction are primary physics, not plotting details. |
| 1590-1683 | Interface tracking LBM: `h_i`, source, equilibrium | Directly maps to current `h` population, `tmp1`, `F_phi`, and B113 normalized source work. |
| 1684-end | N-S LBM and forcing | Supports later force/pressure closure audit after phase boundedness is repaired. |

## Current TCLB Code Anchors

Primary model snapshot:

`third_party/tclb_snapshots/stage14_B111_slim_wall_h_quarantine/models/multiphase/d3q27_pf_velocity/`

Important files:

- `Dynamics.R`
- `Dynamics.c.Rt`
- `Boundary.c.Rt`
- `scripts/stage14/stage14_s2_replay_smoke.py`

Direct anchors observed on 2026-07-03:

- `Dynamics.R:1045`: `PhaseEquationMode`.
- `Dynamics.c.Rt:4716`: `calcPhaseF()`.
- `Dynamics.c.Rt:5158`: `calcF_phi(...)`.
- `Dynamics.c.Rt:5169-5188`: B113 legacy/normalized `tmp1` helper functions.
- `Dynamics.c.Rt:5542`, `6075`, `6496`: active `tmp1` call sites.
- `Dynamics.c.Rt:5742`, `6395`: `rho(C)` interpolation.
- `Dynamics.c.Rt:5761`: `p = m0[0]`.
- `Dynamics.c.Rt:5831-5833`, `6423-6425`: pressure and surface-force consumers.
- `Boundary.c.Rt:745`: analytic wall ghost function.
- `Boundary.c.Rt:1956`: current compact-stencil write gate still limited to flat analytic solids.
- `Boundary.c.Rt:2211`: `PhaseF = WallGhost` path, a critical active-write hazard.

## Project-Specific Interpretation

### 1. B113 Is Supported, But It Is Only The First Phase-Source Fix

The excerpt's phase-field chapter writes the interface-tracking equation with
a source proportional to `phi * (1 - phi)` for the common `[0,1]` order
parameter. The current solver historically used:

```text
tmp1 = (1 - 4*(C - 0.5)^2) / IntWidth
```

That is algebraically tied to `PhaseField_l=0`, `PhaseField_h=1`. B113's
normalized helper is therefore a justified repair direction for nonstandard
order-parameter ranges. It does not, by itself, prove that the whole `h`
collision/source time integration is correct.

### 2. `h_i` Source Timing Must Be Audited Against The Book's Equilibrium Form

The excerpt presents the phase distribution equation as a collision-plus-source
LBE and places a source correction in the phase equilibrium definition. The
current TCLB path applies a generated update with `heq`, `0.5*Fphi`, and
`+Fphi`. Therefore the next source-level audit must check:

```text
sum_i h_i^{eq}
sum_i Fphi_i
sum_i e_i Fphi_i
the sign and half-step placement of Fphi
```

This is exactly why `PhaseEquationMode` should become a family of derived
modes, not a stack of local clamps.

### 3. Curved Walls Need Per-Link Boundary Semantics, Not A Passive Scalar Patch Alone

The curved-wall chapter emphasizes link distance `q`, interpolation, and
post-collision population timing. For TCLB, this reinforces a major earlier
finding: a C-style passive ghost value cannot be copied into TCLB solid nodes
without accounting for `AddDensity` streaming and collision stages.

Implication for current code:

- `WallGhost` may remain useful as a scalar diagnostic or reconstruction input.
- It must not be treated as equivalent to a full per-link boundary population.
- Any future sphere/cylinder repair must distinguish wall phase reconstruction
  from momentum population bounce-back/QIBB.

### 4. Contact-Angle Literature Is Useful For Validation, Not For Direct Formula Mixing

The excerpt includes Shan-Chen and free-energy contact-angle material. Those
sections are valuable because they show how contact-angle cases are structured
and checked. They do not authorize mixing pseudo-potential virtual-density
logic or free-energy wall-energy formulas directly into the current
conservative Allen-Cahn phase-field model.

Current rule:

```text
Do not tune WallGhost to match an angle while h_i -> PhaseF morphology is invalid.
Use contact angle only after phase boundedness and droplet shape are credible.
```

## Impact On Next Work

This anchor strengthens the current route:

1. Complete B114 build/smoke for B113 normalized `tmp1`.
2. Add a B115 source-equilibrium timing audit around `heq`, `Fphi`, and
   half-source placement.
3. Only after the phase producer is credible, re-open pressure/force closure.
4. Only after flat-wall morphology is credible, re-open contact-angle and
   sphere/cylinder wetting validation.

It does not justify immediately returning to grid refinement, dynamic impact,
or curved compact-stencil writes.
