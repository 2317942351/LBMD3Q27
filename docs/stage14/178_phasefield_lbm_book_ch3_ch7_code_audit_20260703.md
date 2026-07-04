# Stage14 Literature Audit: Xu 2024 Phase-Field LBM Book, Ch. 3-7

Date: 2026-07-03
Branch: `work/phasefield-c-reference-20260623`
Status: `literature_guided_solver_audit`
Claim limit: this is not contact-angle validation and not dynamic-impact readiness.

## Source

Book: `相场格子玻尔兹曼方法理论与应用`
English title: `Theory and Application of Phase-Field-Based Lattice Boltzmann Method`
Author: Xu Xingchun
Publisher/date: National Defense Industry Press, 2024-06
Local file: `C:/Users/yuanz/Downloads/相场格子玻尔兹曼方法理论与应用.md`
Local SHA256: `845A2F5F3A392AD78DC4F665494FB5A66488B284C5F4D38B94FA48FF6C69F186`

Repository policy: the full book text is not committed. Metadata and
project-specific chapter mapping are stored in:

`references/phasefield_lbm_book_2024/`

## Bottom Line

The book is useful for the current LBMD3Q27 work, but not primarily as a
wetting-boundary reference. Its value is stronger and more immediate: it
supports a root-cause route through phase-field boundedness, conservative
Allen-Cahn LBE source closure, MRT/non-diagonal MRT phase-field options, and
two-phase force/pressure closure.

This changes the priority:

1. Stop treating grid refinement or `WallGhost` tuning as the main repair.
2. Audit and repair the `h` population equation and `PhaseF=sum(h)` producer.
3. Only after morphology remains bounded should flat-wall contact angle and
   curved wetting be used as validation gates.

## Chapter-to-Code Mapping

### Chapter 3: Cahn-Hilliard, Chemical Potential, Curvature, Boundedness

Project relevance:

- The book treats sequence-parameter boundedness as a first-class numerical
  property. This directly matches the observed Stage14 failure where
  `PhaseField` leaves `[0,1]` and then density, viscosity, force, and morphology
  become meaningless.
- It also explains why a global mass-conserving model can still suffer
  dispersed-phase volume loss or apparent droplet shrinkage.

Code paths:

- `Dynamics.c.Rt:4701` `calcPhaseF()`
- `Dynamics.c.Rt:5491` `tmp1 = (1.0 - 4.0*(PhaseF - C0)*(PhaseF - C0))/IntWidth`
- `Dynamics.c.Rt:6024` `tmp1 = (1.0 - 4.0*(C - 0.5)*(C - 0.5))/IntWidth`
- `Dynamics.c.Rt:5691` and `6351` density interpolation from `C`

Audit implication:

`PhaseField` overshoot is not a plotting artifact. When `C` leaves the physical
range, `rho(C)` and `tau(C)` are no longer physically controlled. A later
contact-angle number cannot be trusted because the morphology is already
created by an invalid phase equation.

### Chapter 4: Conservative Allen-Cahn LBE and Second-Order Correction

Project relevance:

- This is the most important chapter for the current TCLB model.
- The current solver evolves an `h` population and reconstructs `PhaseF` from
  streamed `h_i`. That must recover a conservative Allen-Cahn-type target
  equation with the correct source moments.

Code paths:

- `Dynamics.c.Rt:5143` `calcF_phi(...)`
- `Dynamics.c.Rt:6024-6121` MRT path phase update and diagnostics
- `Dynamics.c.Rt:6452-6495` BGK path phase update and diagnostics
- `Dynamics.c.Rt:6090` generated update:

```text
h = h - omega * (h - heq + 0.5*Fphi) + Fphi
```

- `Dynamics.R:198`, `252`: `ReplayPhaseFromH`, `ReplayHPreSum`, and related
  diagnostic fields.

Audit implication:

B60/B111 boundedness work is not yet a physical model repair. It is a guardrail
around a possibly inconsistent source/collision update. The next repair must
derive the moment constraints of `F_phi` and compare them to the generated TCLB
update under actual streaming order.

### Chapter 5: Higher-Order Corrected LBE and Source-Format Comparison

Project relevance:

- The book compares source/correction forms and their effect on boundedness,
  interface profile, and numerical error.
- This supports creating explicit `PhaseEquationMode` candidates rather than
  accumulating local clamps.

Code paths:

- `Dynamics.c.Rt:906-1004` B60 bounded source limiter.
- `Dynamics.c.Rt:6024-6121` and `6452-6495` source application.
- `scripts/stage14/stage14_s2_replay_smoke.py` should remain a producer-consumer
  probe, not a validation script.

Audit implication:

If `F_phi` is the first producer that breaks boundedness, the fix should be a
source/collision correction branch with conservation checks, not a hard clamp
used as a validation result. A hard limiter can be kept as a diagnostic shadow or
safety guard, but not as the scientific explanation.

### Chapter 6: MRT and Non-Diagonal MRT Phase-Field Models

Project relevance:

- The current model uses MRT for momentum and BGK-like logic for phase
  populations. The book provides a structured path for phase-field MRT/non-
  diagonal MRT only if simpler corrected source models fail.

Code paths:

- `Dynamics.c.Rt:5658` `CollisionMRT()`
- `Dynamics.c.Rt:6326` `CollisionBGK()`
- `Dynamics.R` population declarations: `g` and `h` groups are fields/densities
  with different TCLB streaming semantics.

Audit implication:

Do not immediately rewrite `h` as MRT. First prove whether the current BGK-style
phase population update violates the conservative Allen-Cahn moment requirements
or TCLB time-level semantics. MRT/non-diagonal MRT is a second-stage redesign,
not a patch for the next commit.

### Chapter 7: Two-Phase Model, Static Droplet, Spurious Currents, Force Formats

Project relevance:

- This chapter supports the separate force/pressure closure line that Stage14
  has been pursuing.
- It reinforces that interface force format, pressure representation, and
  spurious current control are coupled with phase boundedness.

Code paths:

- `Dynamics.c.Rt:5610` `calc_Fp(...)`
- `Dynamics.c.Rt:5622` `calc_Fs(...)`
- `Dynamics.c.Rt:5710` `p = m0[0]`
- `Dynamics.c.Rt:5780-5829` pressure/surface/body/`F_mu` construction.
- `Dynamics.c.Rt:5823-5829`, `6421-6426`: stress-derived `F_mu`.
- `Dynamics.c.Rt:6510`: force insertion into the pressure/momentum population.

Audit implication:

Pressure and `F_mu` closure must remain separate from wetting BC tuning. If
`PhaseF` is already invalid, `gradPhi`, `mu`, and `F_mu` can only amplify the
failure. If `PhaseF` is bounded but spurious currents remain large, then chapter
7 becomes the primary guide for selecting pressure/force formulation.

## Current Code Risks Reframed by the Book

### R1. Boundedness is not closed by construction

Evidence in code:

- `PhaseF` is reconstructed from `h` in `calcPhaseF()`.
- The phase update computes `tmp1` from `C` and applies `F_phi` to every
  population.
- B60/B111 can limit or replace some values, but they are not documented as a
  derived conservative corrected LBE model.

Risk:

The solver may be numerically safe only when the limiter happens to mask the
error. This cannot support contact-angle validation or impact simulation.

### R2. Current source correction status is unclear

Evidence in code:

- `calcF_phi` is used in both MRT and BGK paths.
- The generated `h` update contains `+0.5*Fphi` inside the relaxation term and
  `+Fphi` outside it.

Risk:

Without a moment derivation, it is not clear whether the discrete source recovers
the intended conservative Allen-Cahn equation, especially under TCLB streaming.

### R3. `rho(C)` and force-over-rho amplify any phase error

Evidence in code:

- `rho = Density_l + (C - PhaseField_l)*(Density_h - Density_l)/(PhaseField_h - PhaseField_l)`
- Force insertion uses `F_total/rho` in the velocity and population updates.

Risk:

At density ratio 200 or 1000, small phase overshoot can become a force closure
failure. This is why grid refinement alone is not a root-cause repair.

### R4. Wall wetting is a downstream consumer, not the first fix

Evidence in code:

- `Boundary.c.Rt` writes `WallGhost`, wall `PhaseF`, and reconstructs boundary
  `h` populations.
- `WallGhost` is meaningful only if adjacent fluid `PhaseF`, `gradPhi`, and `h`
  populations are physically bounded.

Risk:

Further `WallGhost` tuning can create visually plausible local contact angles
while the droplet body is produced by a broken phase equation.

## Next Work Direction

The next branch should be literature-guided and code-first:

1. Write a short derivation note for the intended conservative Allen-Cahn
   equation used by this TCLB model.
2. Derive required zeroth and first moments of `F_phi` for the D3Q27/D3Q15
   phase population.
3. Compare the derivation against `calcF_phi`, `heq`, `tmp1`, and the generated
   `h` update in both `CollisionMRT()` and `CollisionBGK()`.
4. Verify TCLB time levels: streamed `h_i` -> `calcPhaseF()` -> `C` -> force ->
   `h` update -> next streamed `h_i`.
5. Implement a new explicit mode only after the mismatch is identified:

```text
PhaseEquationMode=legacy
PhaseEquationMode=corrected_source
PhaseEquationMode=bounded_mass_conservative
```

6. Keep hard clamps as diagnostics or emergency guards, not as validation
   evidence.
7. Re-run flat wall morphology and contact-angle recognition only after
   `PhaseField` remains bounded without nonphysical mass creation.
8. Return to sphere/cylinder compact-stencil wetting only after flat-wall phase
   equation closure is stable.

## Explicit Non-Goals

- Do not use this book as evidence that contact-angle BC is correct.
- Do not commit the full book text.
- Do not promote Stage12/Stage14 results to validation.
- Do not continue grid refinement as the primary repair.
- Do not enter dynamic impact until flat-wall phase boundedness and morphology
  are stable.
