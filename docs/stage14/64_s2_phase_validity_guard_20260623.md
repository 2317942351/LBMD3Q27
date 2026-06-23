# Stage14-64: S2 Phase Validity Guard

Date: 2026-06-23

Status: `remote_compile_in_progress`

Branch:

```text
work/phasefield-c-reference-20260623
```

## Purpose

This patch contains a narrow runtime-pollution guard found during S2 replay
smoke testing. It is not a contact-angle validation result and does not modify
the wetting formula, MRT collision, force model, or phase equation.

The immediate failure was:

```text
case: wall_60to30_10
geometry: Stage13-size flat wall
GPU: P100
result: finite through step 3, nonfinite by step 6
step 4 evidence:
  PhaseField max_abs ~= 11662
  WallGhost max_abs ~= 97
  WettingPathId = -20
  AnalyticFlag = 0.5
  WallGhostRaw = WallGhostClamped = WallGhost = PhaseF
  WallGhostClampHit = 0
```

The observed path was an analytic overlap/edge fallback copying a nonphysical
`PhaseF` value into `WallGhost`, after which near-wall `gradPhi` / `lapPhi` /
`mu` stencils could consume it.

## Code Changes

Modified files:

```text
third_party/tclb_snapshots/stage9_analytic_wetting_diffuse_interface/models/multiphase/d3q27_pf_velocity/Dynamics.R
third_party/tclb_snapshots/stage9_analytic_wetting_diffuse_interface/models/multiphase/d3q27_pf_velocity/Dynamics.c.Rt
third_party/tclb_snapshots/stage9_analytic_wetting_diffuse_interface/models/multiphase/d3q27_pf_velocity/Boundary.c.Rt
```

Added setting:

```text
PhaseValidityEps = 1e-3
```

Unified phase validity guard:

```text
valid iff finite and PhaseField_l - eps <= phi <= PhaseField_h + eps
```

Applied to:

```text
Dynamics.c.Rt:
  stage13_phase_is_valid()
  STAGE13_PHASE_FOR_STENCIL input selection

Boundary.c.Rt:
  stage13_boundary_phase_is_valid()
  analytic probe gate
  analytic overlap/fallback WallGhost/PhaseF selection
```

Also changed `PhaseStencilGhostUseCount`,
`PhaseStencilFallbackCount`, and `PhaseStencilMidpointFallbackCount` so their
increments occur only when `ReplayDiagnosticsMode > 0.5`. The fallback return
values are unchanged; only diagnostic counter writes are gated.

## Why This Matters

The old guard accepted:

```text
-100 < PhaseF < 100
```

That was sufficient only for rejecting the historical solid sentinel `-999`.
It was not sufficient for phase-field physics, where the physical range is
normally `[0, 1]`. In the S2 failure, `PhaseF ~= 97` passed the old guard and
was treated as valid `WallGhost`.

The new guard prevents this exact contamination path from being considered
valid stencil input. If the acute case still fails, the next failure should be
closer to the true producer in the `PhaseF -> WallGhost -> gradPhi/lapPhi/mu ->
force` chain rather than being masked by a nonphysical ghost copy.

## Verification So Far

Local checks:

```text
C:\ProgramData\anaconda3\python.exe -m py_compile scripts\stage14\stage14_s2_replay_smoke.py scripts\audit_tclb_execution_semantics.py
git diff --check
```

Both passed.

Remote compile lane:

```text
/home/yuan/src/TCLB_lbm2026_compile_lane
```

Compile command:

```bash
bash /home/yuan/src/TCLB_lbm2026_compile_lane/scripts/remote_c1b_compile.sh \
  /home/yuan/src/TCLB_lbm2026_compile_lane \
  d3q27_pf_velocity_q27_geometric \
  /home/yuan/lbm2026_logs_s1s2_20260623_after_phaseguard
```

At the time this note was written, the compile was still in TCLB `tools/RT`
source generation for:

```text
CLB/d3q27_pf_velocity_q27_geometric/LatticeAccess.inc.cpp
```

The old binary remained:

```text
/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
sha256: 0e17fa5d2bfbbe280d4173fbbef17b77fe7f09946bc5896f326950642178c2a7
mtime: 2026-06-23 12:17:23 +0800
```

Do not run or interpret S2 results until the binary timestamp and SHA change.

## Next Runtime Gate

After compile succeeds, run on a P100:

```bash
python3 /home/yuan/stage14_s2_replay_smoke.py \
  --root /mnt/usb1t/RUNS/runs/stage14_s2_replay_smoke_20260623_stage13geom_after_phaseguard_all \
  --binary /home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main \
  --gpu 1 \
  --iterations 10 \
  --vtk-period 1 \
  --log-period 1 \
  --cases all \
  --replay-mode 1 \
  --force \
  --run \
  --summarize
```

Required interpretation:

```text
PASS only if all 4 short cases complete without nonfinite fields.
If wall_60to30 still fails, inspect earliest bad VTI for:
  PhaseField
  WallGhost / WallGhostRaw / WallGhostClamped / WallGhostClampHit
  WettingPathId
  ReplayPhaseFromH
  ReplayLapPhi / ReplayMu
  ReplayF*
```

This gate is still runtime-semantics work. It is not contact-angle validation.
