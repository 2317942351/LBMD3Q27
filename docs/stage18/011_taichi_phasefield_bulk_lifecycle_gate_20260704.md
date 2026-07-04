# Stage18 Taichi Phase-Field Bulk Lifecycle Gate

Date: 2026-07-04
Branch: `work/phasefield-c-reference-20260623`
Status: `implemented_numpy_bulk_lifecycle_gate`

## Purpose

This is the second executable artifact for the clean Taichi phase-field route.
It still does not use Taichi, because the goal is to prove the exact population
lifecycle before moving to GPU kernels.

Implemented script:

`tools/taichi_phasefield_clean_2026/phasefield_bulk_lifecycle_gate.py`

## Producer-Consumer Timeline

```text
initialize droplet C
  -> initialize h_i = w_i C
  -> C = sum_i h_i
  -> grad C and interface normal
  -> F_phi_i = w_i * tmp1 * (e_i dot n)
  -> h_collide_i = h_i - omega*(h_i - h_eq_i + 0.5F_phi_i) + F_phi_i
  -> periodic pull stream
  -> C_next = sum_i h_i
  -> mass/bounds/nonfinite ledger
```

No wall, wetting, pressure force, momentum population, or curved geometry is
included.

## Why This Matters

The TCLB failure history showed that a stable-looking `PhaseF` can hide invalid
streamed `h_i`. This gate makes `h_i` the primary state and treats `C=sum(h)` as
a derived consumer, matching the clean route needed before Taichi kernel work.

## Run Command

```powershell
python tools/taichi_phasefield_clean_2026/phasefield_bulk_lifecycle_gate.py --out artifacts/stage18_taichi_phasefield_bulk_lifecycle_20260704
```

Expected outputs:

```text
artifacts/stage18_taichi_phasefield_bulk_lifecycle_20260704/metrics.json
artifacts/stage18_taichi_phasefield_bulk_lifecycle_20260704/step_metrics.csv
```

## Gate Meaning

Pass means only:

- finite `h_i` and `C`;
- global mass conserved to the configured tolerance;
- `C` remains in `[0, 1]` for this tiny no-wall periodic test.

It does not prove static droplet equilibrium, pressure/force closure, wetting,
or dynamic impact readiness.

