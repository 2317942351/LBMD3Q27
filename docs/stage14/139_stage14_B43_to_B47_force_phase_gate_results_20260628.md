# Stage14 B43-B47 Force/Phase Gate Results

Date: 2026-06-28

Branch: `work/phasefield-c-reference-20260623`

Status: B43-B45 executed; B46/B47 blocked by B45 stop rule. This is not
contact-angle validation, not curved-wall validation, and not dynamic-impact
readiness.

## Code Path Under Review

The current evidence comes from existing shadow-only diagnostics in:

```text
third_party/tclb_snapshots/stage17B_diffuse_solid_shadow/models/multiphase/d3q27_pf_velocity/Dynamics.c.Rt
third_party/tclb_snapshots/stage17B_diffuse_solid_shadow/models/multiphase/d3q27_pf_velocity/Dynamics.R
```

Relevant anchors:

```text
Dynamics.c.Rt:
  Stage14B21HPopulationAuditMode gate around line 202
  Stage14B22VelocityProducerAuditMode gate around line 206
  Stage14B40StressAuditMode gate around line 222
  Stage14B42StressDecompositionMode gate around line 226
  B40FmuLegacyScale write around line 3835
  B22ForceOverRhoMag write around line 4455
  B21HPostOutOfBoundsFlag write around line 4804

Dynamics.R:
  B40/B42 diagnostic AddField/AddQuantity around lines 521-599 and 1092-1134
  B21/B22 diagnostic AddField/AddQuantity around lines 633-708 and 1168-1233
```

The active solver path was not changed by B43-B45. B43/B44 are VTI
post-processing gates. B45 uses the existing B21/B22 shadow-only fields.

## B43 Result: Scale Probe

Runtime:

```text
remote root = /mnt/usb1t/RUNS/runs/stage14_B43_scale_probe_focus13_20260628
local artifacts = artifacts/stage14_B43_scale_probe_focus13_20260628
binary sha256 = d8e3295335f2c43d9b825e9082f4be7a7cfbf265b48e0d4f15a1a5aaec8a70de
case = wall_60to30_10
step = 13
density ratio = 200
```

Low-density mask:

| candidate | F/rho max | interpretation |
| --- | ---: | --- |
| zero | 4.0565 | sanity check only, not physical |
| legacy_hundredth | 30.2118 | scale-down shadow, not solver repair |
| legacy_tenth | 267.123 | scale-down shadow, not solver repair |
| legacy | 2636.41 | active baseline |

B43 verdict:

```text
b43_postprocess_scale_candidate_strong
```

Meaning:

```text
The F_mu coefficient magnitude is implicated, but this is only a
post-processing scale probe. It does not justify changing the physical solver
formula by an arbitrary factor.
```

## B44 Result: Force Balance

Runtime:

```text
remote root = /mnt/usb1t/RUNS/runs/stage14_B44_force_balance_20260628
local artifacts = artifacts/stage14_B44_force_balance_20260628
case = wall_60to30_10
step = 13
```

Low-density mask:

| candidate | F/rho max | net/term | F_mu fraction | interpretation |
| --- | ---: | ---: | ---: | --- |
| legacy_hundredth | 30.2118 | 0.9465 | 0.7667 | local magnitude reduced, still F_mu dominated |
| legacy_tenth | 267.123 | 0.9330 | 0.9705 | local magnitude reduced, F_mu dominated |
| legacy | 2636.41 | 0.9312 | 0.9970 | unstable baseline |

B44 verdict:

```text
b44_force_balance_candidate_found
```

Conservative interpretation:

```text
The scale-down candidates can reduce local F/rho, but the force field remains
dominated by F_mu and the net/term ratio is not evidence of a closed physical
balance. B44 does not promote a solver repair.
```

## B45 Result: Phase Boundedness

Runtime:

```text
remote root = /mnt/usb1t/RUNS/runs/stage14_B45_phase_boundedness_20260628
local artifacts = artifacts/stage14_B45_phase_boundedness_20260628
case = wall_60to30_10
steps = 0-20
vtk field set = b45phase
```

First events:

| event | first step |
| --- | ---: |
| `ReplayPhaseFromH` outside [0,1] | 3 |
| `B21HPostOutOfBoundsFlag` | 4 |
| `B21HPostSum > 1` | 9 |
| `B22ForceOverRhoMag > 100` | 13 |
| `B22ForceOverRhoMag > 1000` | 13 |
| `B22FmuMag > 1` | 13 |

B45 verdict:

```text
b45_phase_gate_failed
b45_h_update_boundedness_fails_first
```

Meaning:

```text
The earliest visible failure is not the step-13 F/rho explosion. The phase
transport chain is already leaving bounds by step 3-4. Force feedback then
amplifies the unstable state later.
```

## Teacher MCP Review

Teacher MCP reviewed the B43-B45 evidence and agreed that B46/B47 should be
blocked. Key recommendation:

```text
Stop any B46/B47 execution; mark them as blocked by B45.
Initiate a diagnostic probe for steps 0-4 with h-populations, macroscopic h,
PhaseFromH, and phase-field gradients at the first OOB cells.
```

## B46/B47 Decision

Generated artifacts:

```text
artifacts/stage14_B46_B47_gate_decision_20260628/b46_b47_gate_decision.json
artifacts/stage14_B46_B47_gate_decision_20260628/b46_b47_gate_decision.md
artifacts/stage14_B46_B47_gate_decision_20260628/teacher_b43_b47_review_summary.md
```

Decision:

```text
B46 = b46_blocked_by_b45_phase_boundedness
B47 = b47_blocked_by_b45_phase_boundedness
```

Rationale:

```text
Flat-wall contact angle morphology is not physically interpretable when
PhaseFromH already leaves [0,1] by step 3.

Curved-wall shadow/controlled-write cannot be promoted when the flat-wall
phase transport baseline is unbounded.
```

## Next Branch

Next branch should be:

```text
B48_h_population_phasefromh_timelevel_closure
```

Target:

```text
PhaseF -> h populations -> h update -> TCLB streaming -> PhaseFromH
```

Required first probe:

```text
steps 0-4, first OOB cells, full h-population producer-consumer timeline
```

Do not do:

```text
do not promote F_mu scale-down as physical repair
do not run contact-angle validation while B45 fails
do not enter dynamic impact
do not write curved-wall PhaseF
```

Minimum reopen gate:

```text
wall_60to30_10, density ratio 200, at least 100 steps:
  PhaseField and PhaseFromH bounded in [0,1] without hard clamp
  no NaN/nonfinite
  force/rho finite and non-explosive
  mass drift reported and below threshold
```
