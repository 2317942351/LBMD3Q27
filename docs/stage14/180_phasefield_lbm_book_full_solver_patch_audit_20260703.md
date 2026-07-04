# Stage14 Full-Book Solver Patch Audit

Date: 2026-07-03
Branch: `work/phasefield-c-reference-20260623`
Status: `book_guided_patch_audit`
Source book: `C:/Users/yuanz/Downloads/相场格子玻尔兹曼方法理论与应用.md`
Source SHA256: `845A2F5F3A392AD78DC4F665494FB5A66488B284C5F4D38B94FA48FF6C69F186`

This document audits the current TCLB solver against the whole book, but only
records project-specific paraphrases and local line references. It does not
quote or commit the full book text.

## Executive Conclusion

The book supports several concrete repairs, but it also argues against more
local wetting patches before the phase equation is closed. The highest-value
repair line is:

```text
TCLB h_i streaming semantics
  -> PhaseF=sum(h)
  -> conservative Allen-Cahn source moments
  -> boundedness and mass/volume conservation
  -> rho(C), tau(C)
  -> pressure/force closure
  -> wall wetting/contact-angle validation
```

The current code has accumulated many B-stage wall and guardrail switches.
Those were useful as diagnostics, but the book implies that the next substantial
solver repair should be a named phase-equation mode with a derivation, not
another local `WallGhost` or wall-link patch.

## Book-Wide Audit Map

| Book part | What it contributes | Current code area | Patch priority |
|---|---|---|---|
| Ch. 2, lines 649-741 | Collision-streaming order and macroscopic moment recovery. | `lattice.R` `h0..h26` are `AddDensity` with `dx/dy/dz`; `Dynamics.R:700-702` stage order; `calcPhaseF()` reconstructs `PhaseF`. | P0: audit and document producer-consumer time level before any physics write. |
| Ch. 3, lines 911-1040 | Cahn-Hilliard/mCHE, chemical potential, curvature-driven shrinkage, density/viscosity from phase. | `calcMu`, `myLaplace`, `rho(C)`, `calc_Fs`. | P1: chemical-potential/stencil repair after phase boundedness. |
| Ch. 4, lines 1280-1367 and 1368-1693 | Conservative Allen-Cahn target equation, source moments, second-order corrections. | `calcF_phi`, `tmp1`, `heq`, generated `h` update. | P0/P1: immediate formula audit and then explicit corrected mode. |
| Ch. 5, lines 2234-2558 | Higher-order source corrections, boundedness maps, parameter dependence of `tau_phi`, `M`, `W`. | `omega_phi`, `M`, `IntWidth`, B60 limiter. | P1: parameter gate and corrected source model; do not use hard clamp as validation. |
| Ch. 6, lines 2694-3264 | MRT and non-diagonal MRT phase models. | Current solver uses MRT for momentum but not a clean phase MRT branch. | P2 initially; P1 only if corrected BGK/source branch fails. |
| Ch. 7, lines 3286-3788 | Two-distribution phase-field LBM, force/pressure formats, spurious currents, static droplet gates. | `p=m0[0]`, `calc_Fp`, `calc_Fs`, `F_mu`, `F_total/rho`. | P1 after phase equation is bounded; P0 for diagnostics that prevent false claims. |

## P0 Repairs: Can Start From Code Now

### P0-1. Normalize `tmp1` by `PhaseField_l/h`, not hard-coded `0.5`

Evidence in code:

- `Dynamics.c.Rt:5491`: initialization uses
  `tmp1 = (1.0 - 4.0*(PhaseF - C0)*(PhaseF - C0))/IntWidth`, where
  `C0 = 0.5*(PhaseField_h - PhaseField_l)`.
- `Dynamics.c.Rt:6024` and `6452`: runtime uses
  `tmp1 = (1.0 - 4.0*(C - 0.5)*(C - 0.5))/IntWidth`.

Why this is a problem:

The book defines phase values generically as `phi_h` and `phi_l`; the interface
midpoint is `(phi_l + phi_h)/2`, and the conservative Allen-Cahn sharpening term
depends on the normalized double-well profile. The runtime code assumes
`PhaseField_l=0` and `PhaseField_h=1`. That is not robust and is inconsistent
with the generic model settings already exposed in `Dynamics.R:948-949`.

Patch direction:

Introduce a helper:

```c
q = (C - PhaseField_l) / (PhaseField_h - PhaseField_l);
tmp1 = (PhaseField_h - PhaseField_l) * 4.0 * q * (1.0 - q) / IntWidth;
```

or derive the exact project convention if `tmp1` is meant to be dimensionless.
At minimum, remove the hard-coded `0.5` from runtime and initialization.

Acceptance condition:

- `tmp1` is identical to the legacy formula when `PhaseField_l=0`,
  `PhaseField_h=1`.
- `tmp1` remains non-negative inside the phase interval and is zero at both
  bulk phases.
- `ReplayTmp1` and `ReplayTmp1BoundedShadow` differ only when `C` is truly out
  of range.

### P0-2. Resolve the MRT/BGK phase `heq` inconsistency

Evidence in code:

- MRT path:
  - `Dynamics.c.Rt:6054-6055`: `heq = EQ_h$feq * C`.
  - `Dynamics.c.Rt:6090`: `h = h - omega * (h - heq + 0.5*Fphi) + Fphi`.
- BGK path:
  - `Dynamics.c.Rt:6463`: `heq[i] = C * Gamma[i]`.
  - `Dynamics.c.Rt:6489`: `h = h - omega * (h - w_h*heq + 0.5*Fphi) + Fphi`.
- `model.R:55-57`: `w_h` is `wg` under q27 but a nonstandard vector under q15.

Why this is a problem:

The book treats `h_i^eq` and source moments as one coupled LBE design. The code
currently has two phase-update formulas that are not obviously the same model.
In q27, `Gamma` already includes weights via `calcGamma`; multiplying by `w_h`
again in one path would change moments unless the local R template convention
has intentionally separated `Gamma` and `w_h`.

Patch direction:

Before changing physics, add a small source-level audit script or generated
diagnostic that records:

```text
sum(heq)
sum(w_h * heq) in BGK path
sum(F_phi)
sum(e_i F_phi_i)
sum(e_i e_i F_phi_i)
```

Then choose exactly one phase-equation convention for both MRT and BGK:

```text
heq_i = w_i * phi * Gamma_i(u)
or
heq_i = phi * Gamma_i(u)
```

but not both implicitly.

Acceptance condition:

- `sum_i heq_i = C` for the active path.
- `sum_i e_i heq_i = C u` to the intended order.
- `ReplayHeqSum` equals `ReplayPhaseConsumed` in static and low-Mach probes.

### P0-3. Turn `PhaseEquationMode` from a reserved setting into a real switch

Evidence in code:

- `Dynamics.R:1039`: `PhaseEquationMode` exists but is marked reserved.
- Current real behavior is controlled by many B-stage local switches:
  `Stage14B60`, `B63`, `B68`, `B98`, `B111`, `B99`, etc.

Why this is a problem:

The book distinguishes different LBE correction models: collision-step
correction, source-term correction, MRT/non-diagonal MRT. Current code instead
mixes many local guardrails and wall repairs. This makes it hard to know which
mathematical model is being validated.

Patch direction:

Introduce one top-level phase equation switch while preserving legacy defaults:

```text
PhaseEquationMode=0 legacy
PhaseEquationMode=1 normalized_legacy_source
PhaseEquationMode=2 corrected_source_shadow
PhaseEquationMode=3 corrected_source_write
PhaseEquationMode=4 bounded_mass_conservative_shadow
PhaseEquationMode=5 bounded_mass_conservative_write
```

Do not remove old B-stage settings immediately. Instead, have new modes refuse
or override incompatible local write modes and report a diagnostic flag.

Acceptance condition:

- Legacy mode remains bitwise or numerically equivalent where possible.
- New modes can be audited from XML/case metadata without reading all B-stage
  knobs.
- Contact-angle validation scripts can refuse runs with mixed incompatible
  modes.

### P0-4. Add a source-moment unit test outside TCLB

Evidence in code:

- `Dynamics.c.Rt:5143-5149`: `calcF_phi` is simple enough to test outside TCLB.
- The book's Ch. 4 moment constraints make this mandatory before changing the
  solver.

Patch direction:

Add a lightweight Python or C harness under `scripts/stage14/`:

```text
input: D3Q27 velocities, weights, C, gradPhi normal, IntWidth
output: zeroth/first/second moments of heq and F_phi
compare: intended conservative Allen-Cahn moment constraints
```

Acceptance condition:

- The harness is independent of GPU/TCLB runtime.
- It reproduces the code's exact weight convention.
- It prints a fail/pass table suitable for a report.

## P1 Repairs: Need Derivation Before Write Path

### P1-1. Replace B60 limiter with a conservative boundedness correction

Evidence in code:

- `Dynamics.c.Rt:892-1042`: B60 scales `F_phi` by a single lambda to keep
  post-update populations/sums in bounds.
- The book warns that direct truncation or local limiting can harm smoothness
  and mass conservation unless the mass change is redistributed.

Patch direction:

Keep B60 as a diagnostic/emergency guard, but do not treat it as physical
validation. Design a new mode:

```text
bounded_mass_conservative_shadow/write
```

with explicit reporting of:

```text
local clipped mass
interface-band redistributed mass
global mass drift before and after correction
interface-volume drift
```

Acceptance condition:

- No validation claim is allowed if the guard is frequently active.
- Mass correction is applied to interface cells, not arbitrary bulk cells.

### P1-2. Repair `calcMu` and stencil consumption after phase is bounded

Evidence in code:

- `Dynamics.c.Rt:5055-5124`: `calcMu` consumes `STAGE13_PHASE_FOR_STENCIL` in
  the Laplace operator.
- Prior audits already flagged solid/sentinel contamination risk.

Book connection:

Ch. 3 and Ch. 7 both rely on consistent gradients/Laplace for chemical
potential and force. Once `PhaseF` is bounded, any remaining morphology failure
can be driven by stencil-level chemical-potential errors.

Patch direction:

Add a named stencil mode:

```text
PhaseStencilMode=legacy
PhaseStencilMode=validity_guarded
PhaseStencilMode=ghost_reconstructed
PhaseStencilMode=diffuse_solid_shadow
```

Do not mix this with phase-source correction in the same validation commit.

Acceptance condition:

- Solid/sentinel values are never consumed as physical `PhaseF`.
- Near-wall `ReplayLapPhi`, `ReplayGradPhi`, and ghost-use counters are
  reported separately from bulk values.

### P1-3. Derive pressure/force closure from the selected Ch. 7 force format

Evidence in code:

- `Dynamics.c.Rt:5710`: `p = m0[0]`.
- `Dynamics.c.Rt:5610-5614`: `calc_Fp` uses `(-1/3)*pressure*(Density_h-Density_l)*gradPhi`.
- `Dynamics.c.Rt:5622-5654`: `calc_Fs = mu * gradPhi`.
- `Dynamics.c.Rt:5823-5829` and `6421-6426`: `F_mu` stress correction.

Book connection:

Ch. 7 states that interface-force format and equivalent pressure are linked.
Continuous equivalence does not guarantee equal discrete error, spurious
currents, or momentum conservation.

Patch direction:

Add a derivation note before changing defaults:

```text
selected force format: potential / stress / pressure / mu-gradphi
expected pressure variable
whether p=m0[0] is pressure, p*, or normalized lattice pressure
where reference pressure is subtracted
where half-force velocity enters
```

Then upgrade `PressureClosureMode` from diagnostic to named physics modes only
after the derivation is complete.

Acceptance condition:

- Static droplet pressure jump and spurious velocity gate pass before wall
  wetting validation.
- `F_mu` is not omitted as a "fix" unless the selected force model says so.

### P1-4. Create parameter validity gates for `M`, `omega_phi`, `IntWidth`

Evidence in code:

- `Dynamics.R:951-953`: `IntWidth`, `omega_phi`, `M` define phase relaxation.
- Book Ch. 5 maps boundedness to mobility, interface width, and relaxation time.

Patch direction:

Add a script that reads case XML and reports:

```text
tau_phi = 1 / omega_phi
M
IntWidth / dx
estimated Pe*
whether the case lies in a conservative safety window
```

Do not use this as proof that the solver is correct; use it to reject bad
parameter sets.

Acceptance condition:

- Any contact-angle or impact case includes this parameter gate.
- Cases outside the conservative window are labeled exploratory.

## P2: Keep as Later Redesign, Not Immediate Patch

### P2-1. Non-diagonal phase MRT

Book Ch. 6 provides a serious redesign path, but the current evidence does not
yet prove the simple source/update path is unsalvageable. Do not implement
non-diagonal MRT until:

1. `tmp1` normalization and source moments are audited.
2. `heq` conventions are unified.
3. A corrected-source branch is tested and still fails.

### P2-2. Curved wetting controlled write

The current Stage17B shadow work remains useful for geometry and normals, but
the book does not support using curved wetting as the next repair while the
phase equation can still distort droplet morphology. Keep curved compact-stencil
write disabled until flat-wall morphology and static droplet gates are stable.

### P2-3. Dynamic impact

Ch. 7 includes dynamic benchmarks, but they are downstream tests. Dynamic impact
should remain blocked until:

- phase boundedness is closed,
- static droplet spurious current is acceptable,
- flat-wall contact angle morphology is credible,
- pressure/force closure is derived and gated.

## Concrete Patch Backlog

Recommended order:

1. `B112-book-source-moment-audit`
   - Add source-moment harness.
   - Audit D3Q27 weights, `heq`, `F_phi`, and `tmp1`.
   - No GPU required.

2. `B113-normalized-phase-source-mode`
   - Implement `PhaseEquationMode=1`.
   - Replace hard-coded `0.5` with normalized `q`.
   - Keep legacy default.

3. `B114-heq-convention-unification`
   - Resolve MRT/BGK `heq` inconsistency.
   - Add diagnostics so `sum(heq)=C`.

4. `B115-bounded-mass-conservative-shadow`
   - Convert B60 from limiter-only thinking into a conservative correction
     design.
   - Shadow first, write later.

5. `B116-static-droplet-force-closure-gate`
   - Only after phase is bounded.
   - Audit `p=m0[0]`, `calc_Fp`, `calc_Fs`, and `F_mu`.

6. `B117-flat-wall-contact-angle-regate`
   - Only after static droplet and phase gates pass.
   - Use morphology plus contact-angle recognition; do not trust angle alone.

## Stop Conditions

Stop and re-plan if any of these occur:

- `sum(heq)` cannot be made equal to `C` under the current TCLB template
  convention.
- `sum(F_phi)` is nonzero in static no-advection cases for reasons not explained
  by the target equation.
- `PhaseF` remains out of bounds in bulk away from walls after source
  normalization and heq unification.
- Static droplet spurious currents remain large with bounded phase; then force
  closure becomes the primary line.

## Final Assessment

There are repairable issues. The most actionable ones are not in the contact
angle post-processing and not first in the curved-wall compact stencil. They
are:

1. phase source normalization,
2. D3Q27 moment closure for `F_phi`,
3. MRT/BGK phase-equilibrium consistency,
4. conservative boundedness repair,
5. pressure/force closure after phase boundedness.

These are all compatible with TCLB, but they must be implemented as explicit,
auditable solver modes rather than more accumulated local diagnostic switches.
