# Stage18 Taichi Phase-Field Algebra Gate

Date: 2026-07-04
Branch: `work/phasefield-c-reference-20260623`
Status: `implemented_offline_algebra_gate`

## Purpose

This is the first executable artifact for the clean Taichi phase-field route.
It deliberately does not use the existing Re=100 Taichi cylinder code and does
not require Taichi. The goal is to verify the population algebra that must be
true before writing GPU kernels.

Implemented script:

`tools/taichi_phasefield_clean_2026/phasefield_algebra_gate.py`

## What It Checks

The script builds the D3Q27 lattice and verifies:

```text
sum_i w_i = 1
sum_i w_i e_i = 0
sum_i w_i e_i e_i = cs2 I
sum_i h_i^eq = C
sum_i e_i h_i^eq = C u
sum_i F_phi_i = 0
sum_i e_i F_phi_i = cs2 * tmp1 * n
sum_i h_i^post = C
```

The source is the current TCLB-like sharpening form:

```text
F_phi_i = w_i * tmp1 * (e_i dot n)
tmp1 = (1 - 4 * (C - 0.5)^2) / W
```

The post-collision/source update tested is:

```text
h_post = h - omega * (h - h_eq + 0.5 * F_phi) + F_phi
```

This preserves the local zeroth moment when `sum(F_phi)=0`; its first-moment
effect is explicitly reported.

## Interpretation

Passing this gate does not prove the final phase-field model is physically
complete. It proves only that the candidate D3Q27 algebra is internally
consistent for equilibrium one-cell moment checks. The next gate must add
streaming and tiny-grid conservation/boundedness before any wetting work.

## Run Command

```powershell
python tools/taichi_phasefield_clean_2026/phasefield_algebra_gate.py --out artifacts/stage18_taichi_phasefield_algebra_20260704
```

Expected outputs:

```text
artifacts/stage18_taichi_phasefield_algebra_20260704/metrics.json
artifacts/stage18_taichi_phasefield_algebra_20260704/case_moments.csv
```

## Next Step

Implement a tiny-grid phase-population streaming gate in the same clean folder:

```text
h_src -> collide/source -> h_collide -> pull stream -> h_dst -> C=sum(h_dst)
```

No wall, wetting, pressure force, or curved geometry should be added until this
bulk population lifecycle is bounded and mass-accounted.

Implemented next script:

`tools/taichi_phasefield_clean_2026/phasefield_bulk_lifecycle_gate.py`

