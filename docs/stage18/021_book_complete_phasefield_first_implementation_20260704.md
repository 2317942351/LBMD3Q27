# Stage18 Book-Derived Phase-Field Model: First Implementation Result

Date: 2026-07-04
Branch: `work/phasefield-c-reference-20260623`
Status: `first_book_model_implementation_gate_passed_with_caveats`

## Scope

The user explicitly rejected a toy model and requested implementation of the
book-derived high-density-ratio wetting phase-field LBM. This stage therefore
did not claim contact-angle validation. It changed the solver architecture so
that the book model can be tested directly instead of hiding behind stability
patches.

Main files:

- `tools/taichi_phasefield_clean_2026/phasefield_full_solver.py`
- `tools/taichi_phasefield_clean_2026/phasefield_algebra_gate.py`
- `docs/stage18/020_book_complete_phasefield_model_spec_20260704.md`

Artifacts:

- `artifacts/stage18_book_complete_algebra_20260704/`
- `artifacts/stage18_book_complete_cuda_smoke_20260704/`

## Implemented Model Entrances

### 1. Conservative Allen-Cahn source family

New setting:

```text
phase_equation_mode
```

Modes:

```text
0 legacy TCLB-like source
1 normalized conservative Allen-Cahn source
2 moment-corrected conservative Allen-Cahn source
```

For mode 2, the source satisfies the intended D3Q27 moments:

```text
sum_i Fphi_i = 0
sum_i e_i Fphi_i = phase_source_scale * 4 C(1-C)n/W
```

The solver now outputs:

```text
phase_source_sum_abs_max
phase_source_first_max
```

### 2. Pressure-velocity momentum population entrance

New pressure model:

```text
pressure_model = 2
```

This moves the momentum population away from the failed route:

```text
g_i zeroth moment = rho(C)
```

and toward:

```text
sum_i g_i = p / cs2
sum_i e_i g_i = rho_ref u
```

This is required because prior gates proved that the `rho(C)` weakly
compressible route can blow up even without force and phase advection.

### 3. Wetting per-link reconstruction entrance

New wall mode:

```text
phase_wall_mode = 3
```

This places wetting at the missing incoming `h_i` link:

```text
h_in(q from solid) =
  h_out(opp(q)) + w_i [C_ghost(theta) - C_fluid]
```

This is still a flat-wall first candidate, but it fixes the implementation
location: wetting enters streamed phase populations rather than late macro
`C/PhaseF` overwrites.

## Algebra Gate

Command:

```text
python tools/taichi_phasefield_clean_2026/phasefield_algebra_gate.py \
  --source-mode 2 \
  --out artifacts/stage18_book_complete_algebra_20260704
```

Result:

```text
status = pass
cases = 6
```

Key evidence:

```text
D3Q27 weight sum = 1
D3Q27 second moment = cs2 I
mode 2 fphi_sum_abs <= roundoff
mode 2 fphi_first matches 4 C(1-C)n/W
```

## CUDA Smoke Gate On P100

Remote:

```text
server: yuan@192.168.1.16
python: /home/yuan/miniforge3/envs/taichi-lbm-py311/bin/python
GPU: CUDA_VISIBLE_DEVICES=1
run root: /mnt/usb1t/RUNS/runs/stage18_book_complete_cuda_smoke_20260704
```

Minimal case:

```text
grid 10x10x10
steps 2
density ratio 10
pressure_model = 2
momentum_density_mode = 1
force_closure_mode = 1
force_insertion_mode = 1
phase_advection_mode = 1
phase_bound_mode = 2
```

Results:

| case | status | phase source | source scale | mass drift | mass correction delta | u_max |
|---|---|---:|---:|---:|---:|---:|
| `source_mode0_masscorr_2` | pass | 0 | old | `5.68e-14` | `0.0` | `5.36e-4` |
| `source_mode1_nocorr_2` | pass | 1 | old-equivalent | `5.68e-14` | `0.0` | `5.36e-4` |
| `source_mode2_scale1p0_masscorr_2` | pass | 2 | `1.0` | `5.68e-14` | `0.186846` | `7.83e-4` |
| `source_mode2_scale0p3333333333333333_masscorr_2` | pass | 2 | `1/3` | `5.68e-14` | `0.0` | `5.36e-4` |

## Interpretation

This is a real implementation advance, but not final validation.

Important finding:

```text
mode 2 is algebraically correct, but source_scale=1.0 is too strong for the
current interface width / omega_h / time integration. It immediately triggers
global mass correction. source_scale=1/3 restores the effective source strength
of the previous stable source while preserving the explicit moment-corrected
form.
```

This means the next closure task is not contact-angle tuning. It is to derive
and validate the mobility/source scaling relation:

```text
phase_source_scale, omega_h, mobility M, interface width W
```

against the book equations and static droplet morphology.

## What Is Still Missing

The current code is no longer merely a toy scaffold, but it is still not a
complete validated high-density-ratio wetting solver.

Missing:

- derived mobility / relaxation / source-scale relation;
- static droplet Laplace pressure gate;
- spurious-current threshold;
- high-density ladder `10 -> 50 -> 200 -> 1000`;
- rigorous `F_mu` or decision to omit it;
- chemical-potential no-flux wall audit;
- flat-wall `30/90/150` morphology and angle extraction;
- sphere/cylinder per-link SDF wall geometry.

## Next Required Work

Do not jump to dynamic impact.

Next gate sequence:

1. Derive and code `mobility` as an explicit input connected to `omega_h` and
   `phase_source_scale`.
2. Run bulk droplet 100/1000 steps with:
   - `phase_equation_mode=2`
   - `phase_source_scale=1/3` first
   - `pressure_model=2`
   - `phase_bound_mode=2` as a safety layer, with correction delta reported.
3. Add pressure jump and spurious-current metrics.
4. Only after bulk gates pass, test `phase_wall_mode=3` on flat wall
   `90/30/150`.

## Claim Limits

Allowed:

```text
book-model implementation entrance added
phase-source algebra gate passed
pressure-velocity population entrance added
wetting per-link write location added
P100 minimal CUDA smoke passed
```

Forbidden:

```text
high-density-ratio model validated
contact angle solved
complete wetting model proven
dynamic impact ready
```
