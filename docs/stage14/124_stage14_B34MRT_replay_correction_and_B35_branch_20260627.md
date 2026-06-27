# Stage14-B34MRT Replay Correction And B35 Branch

Date: 2026-06-27

Branch: `work/phasefield-c-reference-20260623`

Status: completed diagnostic gate. This is not contact-angle validation and not
dynamic-impact readiness.

## Why This Report Exists

The earlier B34 local harness incorrectly predicted:

```text
ReplayMomentumDeltaG ~= 0.5 * ReplayMF
```

That was too narrow because the default harness set the equilibrium momentum
rows to zero. The generated TCLB code uses the half-force velocity in the
momentum equilibrium row and then applies the explicit force moment.

Generated `Dynamics.c` evidence:

```text
U = momentum_U
m[1] = U + force_rho_inv * F_total[0] * momentum_force_injection_scale / 2
m[2] = V + force_rho_inv * F_total[1] * momentum_force_injection_scale / 2
m[3] = W + force_rho_inv * F_total[2] * momentum_force_injection_scale / 2
```

The upstream template evidence is:

```text
Dynamics.c.Rt:
  U = m0[1:4] + 0.5 * F_total * force_rho_inv
  mF[2:4] = momentum_force_injection_scale * F_total * force_rho_inv
  m = m0 - (m0 - EQ$Req + 0.5*mF)[selR] * Omega + mF
```

Therefore the correct local replay expectation for the generated Stage14 MRT
path is:

```text
ReplayMomentumDeltaG ~= 1.0 * ReplayMF
```

not half `ReplayMF`.

## Code Changes

The following scripts were corrected or extended:

```text
scripts/stage14/stage14_b34_mrt_algebra_harness.py
scripts/stage14/stage14_b34_mrt_replay_compare.py
scripts/stage14/stage14_s2_replay_smoke.py
scripts/stage14/stage14_b17_onset_mask_argmax.py
```

Changes:

1. `stage14_b34_mrt_algebra_harness.py` now sets `Req[1:4] = 0.5*F/rho` in the
   default node and predicts a full force-moment change.
2. `stage14_b34_mrt_replay_compare.py` defaults to `expected_scale=1.0`, still
   reports both half/full residuals, and supports `--max-mf-norm`,
   `--max-delta-norm`, `--max-step`, and relative tolerance.
3. `stage14_s2_replay_smoke.py` adds a lightweight `b34mrt` VTK field set so
   B34 can run without the huge full `b33ledger` output.
4. `stage14_b17_onset_mask_argmax.py` adds `MFNorm`, `MomentumAfterGNorm`, and
   `MomentumDeltaGNorm` targets for replay gate extraction.

## Runtime Evidence

Binary:

```text
263bdd7bfc48e179dcab367f61481814b426682f96a32ddf2a6d96bb47d7d97b
```

Remote roots:

```text
/home/yuan/stage14_runs/stage14_B34MRT_L0_20260627
/home/yuan/stage14_runs/stage14_B34MRT_matrix_20260627
```

Local artifacts:

```text
artifacts/stage14_B34MRT_runtime_compare_20260627/
artifacts/stage14_B34MRT_matrix_20260627/
```

### B34MRT Matrix Summary

| Probe | Meaning | Full-mF filtered replay | Onset result |
|---|---|---:|---|
| `L0_full` | full coupled force | 1093/1093 pass | `ForceOverRhoNorm` crosses at step 15 in `low_rho`; value `8.854e5` |
| `L1_noFmu` | remove `F_mu` | 1260/1260 pass | no configured onset |
| `L2_noSurf` | remove `F_surf` | 1260/1260 pass | no configured onset |
| `L3_noPressure` | remove pressure | 1094/1094 pass | `ForceOverRhoNorm` crosses at step 15 in `low_rho`; value `8.690e5` |
| `L4_zeroForce` | zero force | 1260/1260 pass | no configured onset |

The all-record L0/L3 compare still fails after the explosion because records
with `ReplayMF` or `ReplayMomentumDeltaG` of order `1e84` to `1e154` are not
valid for deciding local force-insertion algebra. The filtered comparison is
the correct B34 local-algebra gate; the unfiltered comparison is retained as
instability evidence.

## Scientific Conclusion

B34MRT closes the MRT force insertion branch for the current gate:

```text
ReplayMomentumDeltaG ~= ReplayMF
```

holds for non-exploded records in every force-split probe. The previous
`0.5*ReplayMF` expectation was a harness error, not a solver result.

The remaining instability pattern is:

```text
F_surf + F_mu coupled numerator
  -> low-rho force/rho denominator amplification
  -> force/rho blow-up around step 15
```

Pressure is not primary: `L3_noPressure` still fails like `L0_full`. Removing
`F_mu` or removing `F_surf` prevents the configured onset.

## Teacher MCP Review

Teacher MCP session `session-20260627-0f3298` returned `PASS` for this branch
change.

Key decision:

```text
Accept full-mF replay relation from B34MRT and close MRT force insertion as
primary root cause. Prioritize B35 coupled numerator split / low-density
denominator amplification.
```

## Next: B35

B35 must remain shadow-first. It should not change the physical write path by
default.

Required B35 probes:

1. Split `F_surf = mu * gradPhi` into shadow candidates:
   - legacy `mu, gradPhi`
   - no-ghost `mu/gradPhi`
   - bounded `mu`
   - gradient-norm limiter shadow
2. Split `F_mu` stress candidates:
   - legacy relaxed stress
   - incoming non-equilibrium stress
   - force-excluded stress
   - prefactor `(0.5-tau)` versus `(0.5-tau)/tau`
3. Record coupled candidate totals:
   - `F_surf_candidate + F_mu_candidate`
   - candidate force/rho with the same `ForceDensityClosureMode=2`
4. Run the lightweight B34MRT matrix again, with B35 shadow fields enabled.

B36 may only implement one minimal active candidate after B35 selects a branch.
