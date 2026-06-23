# Stage14-65: S2 Low-Density Near-Wall Force Feedback

Date: 2026-06-23

Status: `root_cause_narrowed`

Branch:

```text
work/phasefield-c-reference-20260623
```

## Context

Stage14-64 fixed the immediate `WallGhost ~= 97` pollution path by replacing
the old `-100 < PhaseF < 100` guard with a physical phase-range guard. The new
binary was compiled on the server:

```text
/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
sha256: 6298559a9944d94e375e615e30f55227f9a8f19b63fa364f60e7feedcb163381
```

The S2 matrix was then run on P100:

```text
/mnt/usb1t/RUNS/runs/stage14_s2_replay_smoke_20260623_stage13geom_after_phaseguard_all
```

All TCLB processes returned `RUN_RC=0`, but the full matrix still failed because
`wall_60to30_10` developed nonfinite fields. The other cases stayed finite:

```text
bulk_tanh_10      finite through step 10
wall_t90_10       finite through step 10
wall_120to150_10  finite through step 10
wall_60to30_10    first nonfinite at step 6
```

## Important Correction

This is no longer the original `WallGhost ~= 97` bug.

For the failed `wall_60to30_10` run:

```text
WallGhost final range: [0, 1]
WallGhost nonfinite_count: 0
```

The old nonphysical ghost-copy path has been cut. The remaining failure appears
in the first fluid layer near the wall through force and velocity feedback.

## Earliest Failure Chain

At step 4 of the default `Density_l=0.001`, `force_fixed_iterator=2` run:

```text
ReplayPhaseConsumed is still physical:
  min ~= -8.3e-6
  max ~= 1.0

ReplayFtotal already becomes large:
  max_abs ~= 91.24

Top bad near-wall fluid node:
  ijk = [69, 1, 74]
  PhaseField = ReplayPhaseFromH ~= -11662
  Rho ~= -11650
  U_y ~= -25518
  ReplayPhaseConsumed ~= 3.09e-5
  ReplayFtotal_y ~= -52.61
  WallGhost = 0
  WettingPathId = 0
```

Interpretation:

```text
The consumed phase entering collision is still finite and near gas value.
The force update in the low-density near-wall gas layer produces an enormous
velocity, and the following h-population update produces the bad PhaseField.
```

This points at:

```text
PhaseF / WallGhost / gradPhi / mu / force -> velocity -> h collision/streaming
```

not at geometric normal or WallGhost clipping.

## Parameter Probes

Additional P100 probes used the same binary and only changed runtime parameters
in `scripts/stage14/stage14_s2_replay_smoke.py`.

Local summaries are archived under:

```text
artifacts/stage14_s2_replay_smoke_20260623_after_phaseguard/
```

Remote run roots:

```text
/mnt/usb1t/RUNS/runs/stage14_s2_probe_wall60_ff1_20260623
/mnt/usb1t/RUNS/runs/stage14_s2_probe_wall60_rho0p005_20260623
/mnt/usb1t/RUNS/runs/stage14_s2_probe_wall60_rho0p01_20260623
/mnt/usb1t/RUNS/runs/stage14_s2_probe_wall60_rho0p01_it10_20260623
```

Summary table:

```text
case              Density_l  force_iter  steps  failures  final Phase max_abs  final ReplayFtotal max_abs
default           0.001      2           10     yes       8.12e302             2.20e300
force_iter_1      0.001      1           6      no*       1.14e8               1.84e3
rho_0p005         0.005      2           6      no        1.00                 7.99e-4
rho_0p01          0.01       2           6      no        1.00                 3.19e-4
rho_0p01_it10     0.01       2           10     no        1.000015             5.86e-3
```

`force_iter_1` has no nonfinite values by step 6, but it is not acceptable:
`PhaseField` already reaches `1.14e8`. Reducing the force iteration count only
delays the blow-up. Raising `Density_l` from `0.001` to `0.005` or `0.01`
keeps the acute wall case finite over the tested window.

## Current Interpretation

The dominant remaining blocker is low-density near-wall force/velocity feedback,
especially in the acute contact-angle case. The current TCLB implementation can
produce a very large velocity update in gas-side near-wall cells before the
phase field itself is out of range.

This is compatible with the user's earlier concern about TCLB semantics:

```text
Population streaming/stage order and field time levels must be audited before
copying or modifying C logic. The failure now sits in the producer-consumer path
from force to velocity to h-population update.
```

## Do Not Claim

Do not claim:

```text
contact-angle validation passed
compact-stencil wetting BC is complete
dynamic impact foundation is ready
Density_l=0.01 is the final physical fix
```

The density scan is diagnostic. It shows sensitivity and localizes the failure.
It is not a physically justified replacement parameter yet.

## Next Code Targets

Before changing the wetting formula again, audit these in order:

1. MRT velocity update:

```text
rho = Density_l + (C - PhaseField_l)*(Density_h - Density_l)/(PhaseField_h - PhaseField_l)
u = m0[2:4] + 0.5 * F_total / rho
```

The dangerous state is finite `C` near gas value with very small `rho` and large
near-wall `F_total`.

2. `F_mu` fixed-point iteration:

```text
F_mu = (0.5 - tau) * (Density_h - Density_l) * stress * gradPhi
```

Reducing `force_fixed_iterator` does not solve the problem, but the iteration
amplifies it.

3. Phase equation update:

```text
h = h - omega * (h - heq + 0.5*Fphi) + Fphi
```

The first bad `PhaseField` appears in `ReplayPhaseFromH`, so the h-population
update/streaming is the immediate producer of the corrupted phase.

4. C-to-TCLB 10-step replay:

Use the new replay outputs plus `Rho`, `U`, `P`, and `GradPhi` to compare the
first near-wall layer. The next useful replay should include:

```text
Density_l=0.001 default acute case
Density_l=0.005 stabilized acute probe
force_fixed_iterator=1 delayed-blowup probe
```

The contrast between these cases should identify whether the mismatch is
primarily force scaling, velocity update timing, or phase-population collision.

## Scripts Added/Updated

Updated:

```text
scripts/stage14/stage14_s2_replay_smoke.py
```

It now accepts parameter overrides:

```text
--density-h
--density-l
--viscosity-h
--viscosity-l
--sigma
--mobility
--int-width
--force-fixed-iterator
```

Added:

```text
scripts/stage14/stage14_vti_probe.py
```

This helper prints co-located VTI values at the largest or nonfinite nodes in a
target field. It was used to identify the step-4 near-wall gas cell with large
`ReplayFtotal`, `U`, and corrupted `ReplayPhaseFromH`.
