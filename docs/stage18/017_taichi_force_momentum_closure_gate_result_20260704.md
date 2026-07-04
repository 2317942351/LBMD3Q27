# Stage18 Taichi Force/Momentum Closure Gate Result

Date: 2026-07-04
Branch: `work/phasefield-c-reference-20260623`
Status: `bulk_momentum_density_root_cause_identified`

## Claim Limit

This is not contact-angle validation, not wall wetting repair, and not a final
high-density-ratio model. It is a bulk periodic droplet force/momentum closure
gate.

## Source Discipline

This work follows:

- `docs/stage18/015_literature_first_force_closure_protocol_20260704.md`
- `docs/stage18/016_taichi_force_momentum_literature_derived_closure_plan_20260704.md`

Reference basis:

- Project book anchors for conservative Allen-Cahn, density interpolation,
  pressure/interface force and high-density-ratio phase-field behavior:
  - `references/phasefield_lbm_book_2024/chapter_code_map.md`
  - `references/huang_liu_2023_lbm_phase_wetting/chapter_code_map.md`
  - `references/he_li_wang_tong_2023_lbm_theory_phase_wetting/chapter_code_map.md`
- Guo forcing discrete source convention:
  - Guo, Zheng and Shi, Phys. Rev. E 65, 046308, DOI:
    `10.1103/PhysRevE.65.046308`

## Code Changes

Main file:

`tools/taichi_phasefield_clean_2026/phasefield_full_solver.py`

Added explicit bulk closure controls:

```text
--pressure-model
--pressure-reference
--force-closure-mode
--force-insertion-mode
--rho-force-floor
--force-accel-cap
--surface-force-scale
--pressure-force-scale
--momentum-density-mode
--momentum-rho-ref
```

Added force component diagnostics:

```text
pressure_min/max
f_pressure_max
f_surf_max
f_mu_max
f_body_max
f_total_max
force_over_rho_max
force_cap_hits
g_min/g_max
```

Added runner:

`tools/taichi_phasefield_clean_2026/run_hm570_force_closure_gates.sh`

## Run Roots

P100 server:

```text
yuan@192.168.1.16
CUDA_VISIBLE_DEVICES=1
```

Remote:

```text
/mnt/usb1t/RUNS/runs/stage18_taichi_force_closure_20260704_r1
/mnt/usb1t/RUNS/runs/stage18_taichi_force_closure_20260704_r2
```

Local artifacts:

```text
artifacts/stage18_taichi_force_closure_20260704_r1/
artifacts/stage18_taichi_force_closure_20260704_r2/
```

Environment:

```text
Taichi 1.7.4
Python 3.11.15
NumPy 1.26.4
GPU Tesla P100-PCIE-16GB
default_fp=f64
fast_math=False
grid=24x24x24
steps=20
density ratio=10
geometry=periodic droplet
```

## Gate Results

### Original rho(C)-momentum distribution path

| Case | Description | Verdict | Key result |
|---|---|---|---|
| F1 | no force, momentum on, no phase advection | fail | `u_max=2.46e51`, `g=[-5.53e50,1.71e50]` |
| F2 | surface force shadow, no injection | fail | same `g_i` blow-up as F1 |
| F3 | surface force + Guo, no phase advection | fail | `u_max=2.34e50` |
| F4 | surface force + Guo + phase advection | fail | `mass drift=310`, `C=[0,1]`, `u_max=9830` |
| F5 | capped acceleration version of F4 | fail | cap reduces `F/rho` to 0.01 but does not fix morphology |
| F6 | pressure force shadow only | fail | same `g_i` blow-up as F1 |
| F7 | pressure + surface + Guo | fail | `g_i` becomes nonfinite |

Critical observation:

```text
F1 fails with F_total = 0.
```

Therefore the first failure is earlier than `F_surf`, `F_pressure`, `F_mu`, or
Guo force insertion. The unstable branch is the momentum population equation
when `g_i` uses the spatially varying phase density `rho(C)` as a weakly
compressible mass distribution for a static droplet.

### Constant momentum-density diagnostic path

New diagnostic mode:

```text
--momentum-density-mode 1
--momentum-rho-ref 1.0
```

| Case | Description | Verdict | Key result |
|---|---|---|---|
| F8 | constant momentum density, no force | pass | `u_max=1.39e-17`, mass conserved |
| F9 | constant momentum density, surface force + Guo, no phase advection | pass | `u_max=0.00152`, mass conserved |

This is the important result of this stage.

## Interpretation

The current full Taichi skeleton originally initialized and relaxed `g_i` with:

```text
g_i^eq = f_i^eq(rho(C), u)
u = (sum e_i g_i + 0.5 F) / rho(C)
```

For a static diffuse droplet, `rho(C)` has a large spatial gradient across the
interface. With a weakly compressible density-distribution `g_i`, this creates
a pressure/density imbalance even when `F_total=0`. That is why F1 explodes
before any surface force or force insertion can be blamed.

The constant-momentum-density diagnostic removes that artificial static density
distribution from the momentum populations. F8 then remains stable, and F9 can
carry a small surface force with Guo insertion for 20 steps.

This supports the literature-derived direction:

```text
the momentum solver should move toward a pressure/velocity formulation,
not a naive rho(C)-as-g_i-density weakly compressible formulation.
```

It also explains why earlier TCLB work kept hitting ambiguous
`pressure / F_surf / F_mu / F/rho` failures: the pressure variable and momentum
population variable were not cleanly separated.

## What This Does Not Prove

- It does not prove the constant-density diagnostic is the final physical
  model.
- It does not validate high density ratio.
- It does not validate contact angle.
- It does not complete pressure closure.
- It does not include `F_mu` stress reconstruction.

The diagnostic only proves that the previous `rho(C)` momentum-population path
is too early a failure point to support force/wetting validation.

## Next Required Work

### B next: pressure/velocity formulation

Implement a named physical candidate, separate from diagnostic mode:

```text
MomentumDistributionModel = pressure_velocity
```

Required derivation before code:

```text
1. pressure distribution equilibrium moments
2. velocity definition with force
3. relation between hydrodynamic pressure, rho(C), and p/rho terms
4. interface force balance with mu gradC or equivalent stress divergence
5. Guo/source term consistency
```

### Minimum next gates

```text
P1: pressure_velocity, no force, no phase advection, ratio 10
P2: pressure_velocity, surface force + Guo, no phase advection, ratio 10
P3: pressure_velocity, surface force + Guo + phase advection, ratio 10
P4: same as P1-P3 at ratio 50
```

Only after P1-P4 pass should the work return to wall/solid `h_i` per-link mass
conservation.

