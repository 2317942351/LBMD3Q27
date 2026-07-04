# Stage18 Taichi Phase-Field Bulk Kernel Gate

Date: 2026-07-04
Branch: `work/phasefield-c-reference-20260623`
Status: `implemented_taichi_bulk_kernel_gate`

## Purpose

This gate explicitly moves the clean `h_i` bulk lifecycle from NumPy to Taichi
kernels. It remains intentionally narrow:

```text
no wall
no wetting
no pressure force
no momentum population
no curved geometry
```

## Implemented Files

```text
tools/taichi_phasefield_clean_2026/phasefield_bulk_lifecycle_taichi.py
tools/taichi_phasefield_clean_2026/run_hm570_phasefield_bulk_kernel.sh
```

## Kernel Timeline

```text
Python args and ti.init
  -> setup ti.field buffers
  -> initialize_kernel
  -> phase_from_h_kernel
  -> grad_normal_kernel
  -> collide_h_kernel
  -> pull_stream_kernel
  -> phase_from_h_kernel
  -> ti.sync
  -> Python metrics from to_numpy
  -> buffer swap
```

Field mapping:

```text
h[2,nx,ny,nz,Q]       streamed phase population double buffer
c_field[nx,ny,nz]     derived C=sum(h)
grad_field[nx,ny,nz]  derived central gradient
normal_field[...]     derived interface normal
e_field[Q]            D3Q27 lattice velocities
w_field[Q]            D3Q27 weights
```

## Run Commands

Local CPU if Taichi is installed:

```powershell
python tools/taichi_phasefield_clean_2026/phasefield_bulk_lifecycle_taichi.py --arch cpu --debug --out artifacts/stage18_taichi_phasefield_bulk_kernel_20260704_cpu
```

Remote P100:

```bash
bash tools/taichi_phasefield_clean_2026/run_hm570_phasefield_bulk_kernel.sh
```

## Pass Meaning

Pass means only that this Taichi kernel lifecycle preserves finite, bounded
bulk `h_i -> C` evolution for the tiny periodic test. It is not contact-angle
validation and not a force-closure result.

## 2026-07-04 P100 Result

Remote run:

```text
server: yuan@192.168.1.16
GPU: CUDA_VISIBLE_DEVICES=1, Tesla P100-PCIE-16GB
run root: /mnt/usb1t/RUNS/runs/stage18_taichi_phasefield_bulk_kernel_20260704
Taichi: 1.7.4
Python: 3.11.15
grid: 24 x 24 x 24
steps: 20
precision: f64
```

Downloaded evidence:

```text
artifacts/stage18_taichi_phasefield_bulk_kernel_20260704/metrics.json
artifacts/stage18_taichi_phasefield_bulk_kernel_20260704/step_metrics.csv
artifacts/stage18_taichi_phasefield_bulk_kernel_20260704/env.log
artifacts/stage18_taichi_phasefield_bulk_kernel_20260704/run.log
artifacts/stage18_taichi_phasefield_bulk_kernel_20260704/run.stderr
artifacts/stage18_taichi_phasefield_bulk_kernel_20260704/done.status
```

Result:

```text
status: pass
mass0: 1151.6332540613578
max_abs_mass_drift: 1.1368683772161603e-12
final C min/max: 3.992974908641072e-07 / 0.9959226329896159
final h min/max: 2.5161923572328813e-10 / 0.2950880835544435
C out-of-bounds cells: 0
nonfinite_count: 0
```

Implementation note:

Taichi 1.7.4 rejected postponed string annotations from
`from __future__ import annotations` and rejected `@ti.func` argument
annotations such as `ti.i32`. The kernel script therefore uses real Taichi
kernel annotations and leaves `@ti.func wrap_index` unannotated, matching the
official Taichi scope/type rules for this environment.
