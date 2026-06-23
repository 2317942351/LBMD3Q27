# Stage14-63: S1 Replay Diagnostics Implementation

Date: 2026-06-23

Status: `compile_check_in_progress`

Branch:

```text
work/phasefield-c-reference-20260623
```

## Purpose

This step implements diagnostic-only fields required by the S1/S2 plan. It does
not change the wetting boundary formula, compact-stencil write path, MRT
relaxation, pressure force formula, or phase equation.

The goal is to make the internal TCLB collision quantities observable for the
first 10-step C-to-TCLB replay:

```text
PhaseF / WallGhost / gradPhi / lapPhi / mu / F_pressure / F_surf / F_mu / F_total
```

Before this change, `gradPhi`, `lapPhi`, `mu`, and force components existed
only as local variables inside `CollisionMRT()` / `CollisionBGK()` and could not
be audited from VTI outputs without reimplementing the exact TCLB time level on
the host.

## Modified Files

```text
scripts/audit_tclb_execution_semantics.py
third_party/tclb_snapshots/stage9_analytic_wetting_diffuse_interface/models/multiphase/d3q27_pf_velocity/Dynamics.R
third_party/tclb_snapshots/stage9_analytic_wetting_diffuse_interface/models/multiphase/d3q27_pf_velocity/Dynamics.c.Rt
```

Generated local audit artifacts:

```text
artifacts/s1_timeline_audit_20260623/
```

## Added Diagnostic Fields

All new replay fields are `AddField(..., group="runtime_diagnostics")`. They are
not `AddDensity`, therefore they do not participate in TCLB streaming.

```text
ReplayPhaseConsumed
ReplayPhaseFromH
ReplayLapPhi
ReplayMu
ReplayGradPhiX/Y/Z
ReplayFsurfX/Y/Z
ReplayFpressureX/Y/Z
ReplayFbodyX/Y/Z
ReplayFmuX/Y/Z
ReplayFtotalX/Y/Z
```

`ReplayDiagnosticsMode` controls output:

```text
0: getters return zero / diagnostics effectively disabled
1: write and output collision intermediate fields
```

`Run()` now zeroes the replay fields once per node after
`UpdateGlobalMarkers()`, so wall/solid nodes do not retain stale values from the
previous action boundary. Fluid collision paths write replay values only when
`ReplayDiagnosticsMode > 0.5`.

## Time-Level Meaning

The fields intentionally reflect the existing TCLB execution order:

```text
BaseIter / Run:
  consumes previous saved PhaseF and WallGhost
  writes ReplayPhaseConsumed, ReplayGradPhi*, ReplayLapPhi, ReplayMu, ReplayF*

calcPhase / calcPhaseF:
  sums h populations after Run
  writes PhaseF and ReplayPhaseFromH for the next action boundary
```

`ReplayPhaseConsumed` and `ReplayPhaseFromH` are both required. They distinguish
the phase field consumed by the collision from the phase field reconstructed
from `h` after the collision/streaming stage.

## Audit Result

Latest local S1 audit:

```text
densities=54
fields=110
stages=20
risks=13
timeline_edges=85
unresolved_edges=14
high_risks=SPECIAL_POINT_MAGIC
```

The unresolved edges are now split:

```text
CHECK:    4
COVERED: 10
```

The covered items are:

```text
gradPhi, mu, F_surf, F_pressure, F_total
```

They are no longer missing output channels; S2 must compare their numerical
values and time level.

The remaining true `CHECK` items are:

```text
PhaseF consumed by BaseIter from previous action boundary
WallGhost consumed by BaseIter from previous action boundary
WallGhost consumed by calcPhaseGrad from previous action boundary
WallGhost consumed by calcPhaseGrad_init from previous action boundary
```

These cannot be closed by static code inspection. They require the 0-10 step
C-to-TCLB replay.

## Remote Compile Status

The edited model files were synced to:

```text
/home/yuan/src/TCLB_lbm2026_compile_lane/models/multiphase/d3q27_pf_velocity/
```

Compile command launched:

```text
bash /home/yuan/src/TCLB_lbm2026_compile_lane/scripts/remote_c1b_compile.sh \
  /home/yuan/src/TCLB_lbm2026_compile_lane \
  d3q27_pf_velocity_q27_geometric \
  /home/yuan/lbm2026_logs_s1s2_20260623
```

At last check, the job was still in TCLB RT source-generation stage:

```text
make d3q27_pf_velocity_q27_geometric/source
tools/RT ... LatticeAccess.inc.cpp.Rt
```

No physics case has been launched.

## Current Interpretation

This is progress on the central root-cause path. The solver now has the
instrumentation needed to distinguish:

```text
wrong PhaseF/WallGhost time level
wrong near-wall gradPhi stencil input
wrong lapPhi / mu from ghost substitution
wrong pressure/surface/viscous force assembly
force iteration mismatch
```

It does not prove contact-angle correctness. It only makes the next replay
gate measurable.

## Next Gate

After remote compile succeeds:

1. Confirm generated `Dynamics.c` contains all `Replay*` getters and writes.
2. Run a tiny P100 `ReplayDiagnosticsMode=0` smoke to ensure diagnostics do not
   alter legacy output path.
3. Run tiny `ReplayDiagnosticsMode=1` cases for 0-10 steps:
   - periodic bulk planar tanh
   - flat wall theta90
   - flat wall theta30 / theta150
4. Compare exported TCLB fields against the C reference at the declared action
   boundary.

Do not proceed to cylinder/sphere compact-stencil wetting edits until S2 closes.
