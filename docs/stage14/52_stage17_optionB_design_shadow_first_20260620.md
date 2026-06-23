# Stage 17 option B — design: smooth curved-wall wetting BC (shadow-first) — 2026-06-20

Design for the curved-wall fix (gate-A limits, doc 51). The implementation is
research-grade (a stable AND accurate curved-wall ghost); this doc fixes the
approach BEFORE coding, because a "stable-but-wrong" BC would pass the +/-4 deg
measurer and be a silent error -- exactly the failure mode this project has hit
twice (docs 40, 47). No source changed here.

## 1. Why the existing two paths both fail on the staircase cylinder

Both write a PER-WALL-NODE value on the jagged staircase boundary:
- compact-stencil q_s write (doc 46): the q_s is bounded & the gate is strict, but
  injecting it onto staircase nodes destabilises the phase solve (~step 250, 80% NaN).
- analytic Briant ghost (gate-A, doc 50/51): phi_0 + 2*h0*tan(pi/2-theta)*|grad_t phi|.
  The |grad_t phi| is amplified by the staircase jaggedness; for acute theta the
  prefactor is large too -> acute NaN; for neutral it stays bounded but the per-node
  jaggedness gives the wrong macroscopic angle (~+25 deg at theta=90).

Shared root cause: dependence on the per-node staircase geometry / lattice gradient.
option B must remove that dependence.

## 2. The construction to try (smooth, analytic-SDF-anchored, no lattice gradient)

For a wall node on a CURVED solid (AnalyticSolidType>=1.5):
- Use the ANALYTIC signed distance sd (<0 inside solid) and analytic normal n_sf
  only. Do NOT use a lattice neighbour phase probe or a lattice |grad_t phi|.
- Set the wall ghost from the equilibrium diffuse-interface profile evaluated at
  the wall node, oriented by the contact angle:
    q_ghost = 0.5 * [ 1 - tanh( (2/W) * (sd_eff) ) ],   with sd_eff chosen so the
  imposed angle is theta. For the contact-angle Neumann condition
  n_sf.grad(q) = -(4/W) q_w (1-q_w) cos(theta), the equilibrium profile along n_sf
  that satisfies it has its zero-crossing shifted by (W/2) ln(...) proportional to
  cos(theta) -- i.e. the wall value is q_w(theta) = 0.5[1 - sinh-shift relation].
  The closed form for the equilibrium wall value of a tanh interface at angle theta
  is q_w = 0.5[1 - tanh( (W/2)*kappa_term ... )]; the EXACT expression and its sign
  convention (liquid-vs-gas side, acute-vs-obtuse) MUST be derived carefully and
  UNIT-TESTED against synthetic cylinder caps of known theta (golden_cyl.py) BEFORE
  any dynamics write. This is the load-bearing derivation; do not guess the sign.

Key invariant the construction must satisfy (validation handle): on the same
analytic cylinder, the synthetic caps (golden_cyl synth_field) have a KNOWN theta;
the ghost formula evaluated at those wall nodes must reproduce the cap's interface
to within the measurer tolerance. If it does not, the sign/form is wrong -- fix
the formula, do not enable the write.

## 3. Implementation plan (shadow-first, mandatory)

```
B1. Derive + unit-test the q_w(theta) formula offline (pure python, against the
    golden_cyl synth caps at 30/60/90/120/150). Lock the sign convention. This is
    the gate before any TCLB edit.
B2. Add the smooth ghost as a SHADOW field on curved walls (compute into a spare/
    new diagnostic, e.g. WallGhostPhiV2), do NOT change WallGhost/PhaseF/dynamics.
    Rebuild. Run cyl 60/90/120 (gate-A binary + shadow). Confirm 0 NaN (shadow must
    not destabilise) and read WallGhostPhiV2 -> measure implied angle vs target.
B3. Only if B2 shadow implies correct angles (within ~+/-5 deg) AND is stable for
    acute theta, enable the write: on AnalyticSolidType>=1.5 set WallGhost/PhaseF =
    smooth ghost (replacing the analytic Briant ghost). Rebuild, re-run cyl 60/90/120,
    measure with golden_cyl. Gate: stable for all theta AND within ~+/-5 deg.
B4. Audit (read-only review) before any validation_candidate label.
```

## 4. Risk register

- Sign convention of q_w(theta): highest risk (cf. the ForceSign saga, doc 38).
  Mitigated by B1 offline unit test against synthetics.
- Acute stability: the smooth profile has NO gradient-probe term, so the
  tan()*|grad| blow-up is gone by construction -- but stability must still be
  confirmed empirically (B2/B3) because the staircase mask remains.
- Measurer ceiling: golden_cyl is ~+/-4 deg; a wrong-by-3-deg BC could slip through.
  Mitigated by the B1 synthetic unit test (known-truth, not measurer-limited) and
  by checking 60 AND 120 (asymmetric errors reveal sign/convention bugs).

## 5. Recommendation
Secure the current 14-commit milestone (push) before B1-B4, because option B edits
the TCLB BC core and a rollback point is valuable. Then proceed B1 (offline
derivation+test) as the next concrete step -- it needs no server compute, just
careful maths + the golden_cyl synthetics already on hand.
