# Stage17B-B11 TCLB Step-0 / Step-1 Replay Compare

Date: 2026-06-25

Status:

```text
B11 replay compare: COMPLETE
claim limit: TCLB replay comparison only; not contact-angle validation
solver edits: none
new compute: none; reused B9 VTI files on server
```

This stage does not validate a contact angle and does not justify B3 controlled
write or dynamic impact.

## Purpose

B10 reconstructed the B9 neutral cylinder `CylinderCapInit` field offline and
found near-wall chemical-potential nonuniformity.  B11 checks whether that
offline reconstruction actually matches TCLB output at the earliest available
frames.

The comparison answers a narrower question:

```text
Does TCLB step-0 PhaseField near the cylinder contact region match the
reconstructed CylinderCapInit field, or was B10 auditing the wrong field?
```

## Inputs

Case:

```text
cases/diagnostics/stage17B_B9_baseline_20260625_lite/
  cylinder_init090_b9_A_legacy_lite_s0001/case.xml
```

Remote VTI source:

```text
/mnt/usb1t/RUNS/runs/stage17B_B9_lite_20260625/
  cylinder_init090_b9_A_legacy_lite_s0001/output/
```

Frames:

```text
case_VTK_P00_00000000.vti
case_VTK_P00_00000001.vti
```

Server-side helper directory:

```text
/home/yuan/stage17B_B11_replay_compare_20260625/
```

Local artifacts:

```text
artifacts/stage17B_B11_replay_compare_20260625/
```

## Method

Script:

```text
scripts/stage17/stage17B_B11_replay_compare.py
```

The script:

1. imports the B10 reconstruction and D3Q27 stencil code;
2. reads B9 VTI files on the server using Python VTK;
3. compares offline `PhaseField`, `lapPhi`, and `mu` against TCLB
   `PhaseField`, `ReplayLapPhi`, and `ReplayMu`;
4. separates offline fluid from TCLB `IsItBoundary/BOUNDARY`, so outer walls
   and analytic-cylinder boundary cells do not contaminate contact-core
   comparisons.

## Result

Classification:

```text
status = b11_replay_compare_complete
primary_result =
  step0_phase_matches_offline_cap_in_nearwall_interface_and_contact_core
```

Key step-0 metrics:

| metric | value |
|---|---:|
| all offline-fluid `PhaseField` max diff | `5.0e-01` |
| near-interface TCLB-fluid `PhaseField` max diff | `3.33e-16` |
| contact-core TCLB-fluid `PhaseField` max diff | `2.22e-16` |
| TCLB boundary cells | `172968` |
| offline-fluid but TCLB-boundary cells | `51624` |
| offline-solid but TCLB-fluid cells | `0` |

Interpretation:

```text
The large all-fluid max difference is a mask mismatch, not a failure of
CylinderCapInit in the contact region.  In the near-wall interface and
contact core, TCLB step-0 PhaseField matches the offline reconstruction to
machine precision.
```

Step-0 replay diagnostic caveat:

| field | TCLB step-0 value | implication |
|---|---|---|
| `ReplayLapPhi` | zero everywhere | not yet a valid produced diagnostic |
| `ReplayMu` | zero everywhere | not yet a valid produced diagnostic |

So B10's offline `mu` evidence is not directly visible in the initial VTI
diagnostic fields.  A dedicated pre-collision / post-initialization replay is
needed if we want `calcMu(initial PhaseF)` from inside TCLB before the first
update.

Step-1 comparison:

| metric | value |
|---|---:|
| near-interface TCLB-fluid `PhaseField` max diff from initial offline field | `2.916743492e-02` |
| contact-core TCLB-fluid `PhaseField` max diff from initial offline field | `2.819095682e-02` |
| near-interface TCLB-fluid `ReplayMu` max abs | `5.668966893e-05` |
| contact-core TCLB-fluid `ReplayMu` max abs | `5.668966893e-05` |

Interpretation:

```text
The contact-region phase field changes measurably by the first completed step.
This is consistent with B9's early release timeline, but B11 still does not
identify the exact producer: h update, force/advection, WallGhost consumption,
or diagnostic timing.
```

## Updated Root-Cause Ranking

B11 updates the B10/B9 interpretation:

1. `CylinderCapInit` is confirmed to be the actual TCLB step-0 contact-region
   field.
2. The step-0 `ReplayMu/ReplayLapPhi` arrays are not valid initial-condition
   diagnostics because they are still zero-valued.
3. The first completed step already moves the contact-region phase by about
   `2.9e-2`, so the next evidence gate must inspect the first-step
   producer-consumer chain.

The current priority remains:

```text
primary: first-step phase update / initialization release
secondary: early force transient as response or amplifier
not yet supported as primary: Stage17B shadow/write path, sustained F_mu blow-up
```

## Next Gate

Do not modify wetting physics yet.  The next gate should add one of these
diagnostics:

```text
Option A: pre-collision/post-initialization replay fields
  InitialReplayLapPhi
  InitialReplayMu
  InitialReplayGradPhi
  InitialReplayWallGhostUsed

Option B: step-1 producer split
  PhaseF_pre_h_update
  HPreSum
  Fphi
  tmp1
  HPostSum
  PhaseFromH
  U/force used by phase advection
```

Option A is the cleaner immediate audit because it proves whether the initial
cap is already non-equilibrium inside the actual TCLB stencil before the first
collision/update.

## Commands

Local checks:

```powershell
python -m py_compile scripts/stage17/stage17B_B10_initial_cap_equilibrium.py scripts/stage17/stage17B_B11_replay_compare.py
git diff --check
```

Remote run:

```bash
cd /home/yuan/stage17B_B11_replay_compare_20260625
MPLCONFIGDIR=/tmp python3 stage17B_B11_replay_compare.py \
  --case case.xml \
  --vti0 /mnt/usb1t/RUNS/runs/stage17B_B9_lite_20260625/cylinder_init090_b9_A_legacy_lite_s0001/output/case_VTK_P00_00000000.vti \
  --vti1 /mnt/usb1t/RUNS/runs/stage17B_B9_lite_20260625/cylinder_init090_b9_A_legacy_lite_s0001/output/case_VTK_P00_00000001.vti \
  --out out
```

Produced files:

```text
artifacts/stage17B_B11_replay_compare_20260625/b11_replay_compare.json
artifacts/stage17B_B11_replay_compare_20260625/b11_replay_compare_summary.csv
```
