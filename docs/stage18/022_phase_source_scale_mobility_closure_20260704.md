# Stage18 Phase Source Scale / Mobility / Omega / W Closure

Date: 2026-07-04
Branch: `work/phasefield-c-reference-20260623`
Status: `phase_source_mobility_closure_gate_passed_ratio10`

## Objective

Close the relation between:

```text
phase_source_scale / mobility M / omega_h / interface width W
```

for the Taichi conservative Allen-Cahn phase population. This is required
before any static contact-angle validation, because the wall model consumes the
phase equation. A contact-angle target is meaningless if the bulk phase source
is too strong and morphology is repaired by mass correction.

## Discrete Update Being Closed

Current phase collision:

```text
h_i^post =
  h_i - omega_h [h_i - h_i^eq + 0.5 Fphi_i] + Fphi_i
```

Therefore the effective source contribution to post-collision moments is:

```text
(1 - 0.5 omega_h) Fphi_i
```

This means raw `Fphi_i` moment correctness is not sufficient. The effective
post-collision source moment must also be checked.

## Book-Derived Moment-Corrected Source

For `phase_equation_mode=2`:

```text
sum_i Fphi_i = 0
sum_i e_i Fphi_i =
  phase_source_scale * 4 C(1-C)n / W
```

The D3Q27 correction divides the old `w_i(e_i dot n)` source by `cs2`, because:

```text
sum_i e_i w_i (e_i dot n) = cs2 n
```

## Scale Modes Added

Solver:

`tools/taichi_phasefield_clean_2026/phasefield_full_solver.py`

New settings:

```text
--phase-source-scale-mode
--phase-mobility
```

Modes:

| mode | meaning | use |
|---:|---|---|
| 0 | manual `phase_source_scale` | controlled debug |
| 1 | legacy effective strength | bridge from old stable source |
| 2 | post-collision target strength | mathematically explicit but likely strong |
| 3 | mobility-relative strength | preferred closure audit mode |

Definitions:

```text
tau_h = 1 / omega_h
M_lattice = cs2 (tau_h - 0.5)
post_factor = 1 - 0.5 omega_h
```

For mode 3:

```text
phase_source_scale =
  base * phase_mobility / M_lattice

base = cs2 for phase_equation_mode >= 2
base = 1   for legacy modes
```

If `phase_mobility < 0`, the solver uses `M_lattice`, so mode 3 gives
`phase_source_scale=cs2` for the moment-corrected source. This matches the
previous stable D3Q27 effective source strength while retaining explicit
moment-corrected algebra.

## Why `scale=1.0` Was Too Strong

Prior CUDA smoke:

```text
phase_equation_mode=2
phase_source_scale=1.0
```

gave:

```text
mass_correction_delta = 0.186846 after only 2 steps on 10^3
```

With:

```text
phase_source_scale=1/3
```

the same gate gave:

```text
mass_correction_delta = 0.0
```

Therefore the source correction was algebraically right, but the raw source
strength was not closed to the relaxation/time integration.

## Gate Added

Offline algebra:

```text
python tools/taichi_phasefield_clean_2026/phasefield_algebra_gate.py \
  --source-mode 2 \
  --source-scale 0.3333333333333333 \
  --out artifacts/stage18_phase_source_closure_algebra_20260704
```

Result:

```text
status = pass
```

This gate now records:

- raw `Fphi` first moment;
- post-collision effective source factor;
- effective post-collision first moment.

## Claim Limit

This stage only closes the phase-source scale architecture. It does not yet
validate:

- high-density ratio;
- Laplace pressure jump;
- spurious current;
- wetting contact angle.

Next required runtime gate is bulk periodic droplet with:

```text
phase_equation_mode=2
phase_source_scale_mode=3
pressure_model=2
phase_bound_mode=2
```

## Runtime Gate Result

Remote:

```text
server: yuan@192.168.1.16
GPU: CUDA_VISIBLE_DEVICES=1, P100
run root: /mnt/usb1t/RUNS/runs/stage18_phase_source_closure_20260704
```

Local artifacts:

```text
artifacts/stage18_phase_source_closure_20260704/
artifacts/stage18_phase_source_closure_algebra_20260704/
```

Runtime parameters:

```text
grid = 24^3
density ratio = 10
phase_equation_mode = 2
phase_source_scale_mode = 3
phase_mobility = -1, resolved to M_lattice
phase_source_scale = 1/3
pressure_model = 2
force_closure_mode = 1
force_insertion_mode = 1
phase_advection_mode = 1
phase_bound_mode = 2
```

Results:

| case | steps | status | mass drift | mass correction delta | C min | C max | u_max |
|---|---:|---|---:|---:|---:|---:|---:|
| `bulk_mode2_mobilityscale_100` | 100 | pass | `6.37e-12` | `0.0` | `2.96e-7` | `0.996116` | `7.61e-5` |
| `bulk_mode2_mobilityscale_1000` | 1000 | pass | `6.53e-11` | `0.0` | `3.14e-7` | `0.995913` | `6.67e-5` |

The important evidence is:

```text
mass_correction_delta = 0.0
```

The run used `phase_bound_mode=2`, but it did not need to clip/redistribute
mass in the reported final states. Therefore the phase source closure is not
currently being hidden by the mass-correction safety layer at density ratio 10.

## Current Conclusion

The phase-source scale closure has now moved from an empirical `1/3` discovery
to an explicit model rule:

```text
phase_source_scale_mode = 3
phase_mobility = M_lattice = cs2(1/omega_h - 0.5)
phase_source_scale = cs2 for phase_equation_mode >= 2
```

This keeps the stable effective D3Q27 source strength while preserving the
moment-corrected conservative Allen-Cahn source algebra.

This is a real closure step, but it is still a bulk phase-equation gate. The
next physics gates remain:

1. Add Laplace pressure jump and spurious-current metrics.
2. Run density-ratio ladder `10 -> 50 -> 200 -> 1000`.
3. Only then reopen flat-wall wetting `90/30/150`.
