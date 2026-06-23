# Stage14-67: Momentum Force Feedback Is The Next Solver Target

Date: 2026-06-23

Status: `root_cause_narrowed_momentum_feedback`

Branch:

```text
work/phasefield-c-reference-20260623
```

## Why This Note Exists

Stage14-66 proved that using the pre-force velocity for the phase-field
population update prevents the immediate step-4 `h` blow-up. It did not solve
the run: the momentum population update still drives the flow to nonphysical
values by steps 5-6.

Therefore the current main target is no longer:

```text
WallGhost
compact-stencil wetting formula
curved geometry normal
```

The current main target is:

```text
MRT momentum forcing / fixed-point feedback / low-density force-over-rho closure
```

## Artifact Index

```text
artifacts/stage14_s2_iterdiag_20260623/
  iterdiag_wall60_default_summary.json
  iterdiag_wall60_ff1_summary.json

artifacts/stage14_s2_phaseadv_m0_wall60_20260623/
  s2_replay_smoke_summary.json
  case_metadata.json

artifacts/stage14_s2_phaseadv_m0_ff1_wall60_20260623/
  s2_replay_smoke_summary.json
  case_metadata.json

artifacts/stage14_s2_phaseadv_comparison_20260623.csv
```

Remote valid run roots:

```text
/mnt/usb1t/RUNS/runs/stage14_s2_iterdiag_wall60_20260623
/mnt/usb1t/RUNS/runs/stage14_s2_iterdiag_wall60_ff1_20260623
/home/yuan/stage14_s2_phaseadv_m0_wall60_20260623
/home/yuan/stage14_s2_phaseadv_m0_ff1_wall60_20260623
```

Invalid/truncated run root due to full filesystem:

```text
/mnt/usb1t/RUNS/runs/stage14_s2_phaseadv_m0_wall60_20260623
```

Do not use that USB copy for numerical interpretation.

## Four-Case Comparison

All cases use:

```text
wall_60to30_10
Density_l = 0.001
Density_h = 1
binary sha256 = be8ff8ee54553dfa175200e56fa1ccc74e2d3a120c03944061ee4493a59ac362 for phaseadv runs
```

Key max-absolute values:

```text
case              step  PhaseFromH     Ftotal        UPost        PhaseAdv/UPre
legacy_ff2        4     1.166e4        9.124e1      4.562e4      UPre 4.218e-1
legacy_ff2        6     nonfinite      4.040e189    4.363e139    UPre 4.088e52

legacy_ff1        4     1.0            4.093e-3     2.050e0      UPre 1.837e-1
legacy_ff1        6     1.140e8        1.842e3      9.027e5      UPre 1.309e4

phaseadv_m0_ff2   4     1.0            9.124e1      4.562e4      PhaseAdv 4.218e-1
phaseadv_m0_ff2   6     1.318e105      1.720e89     9.722e85     PhaseAdv 1.560e46

phaseadv_m0_ff1   4     1.0            4.093e-3     2.050e0      PhaseAdv 1.837e-1
phaseadv_m0_ff1   5     1.0            3.081e-1     1.512e2      PhaseAdv 5.748e-1
phaseadv_m0_ff1   6     6.087e3        1.820e3      9.086e5      PhaseAdv 1.309e4
```

Interpretation:

```text
1. legacy_ff2 fails immediately at step 4 because the second fixed-point force
   iteration amplifies Ftotal from 8.824e-2 to 9.124e1.

2. legacy_ff1 delays the failure, but step 6 is still nonphysical because the
   first-iteration momentum forcing still grows to UPost ~= 9.0e5.

3. phaseadv_m0_ff2 proves the h-equilibrium velocity path is a direct trigger:
   step 4 stays finite when h uses m0 velocity. But the g update still injects
   a corrupted momentum state, so step 5-6 fail.

4. phaseadv_m0_ff1 is the cleanest current diagnostic. It suppresses both the
   second fixed-point amplification and the h post-force velocity trigger. It
   still reaches PhaseFromH ~= 6.1e3 by step 6. Therefore the first-iteration
   momentum forcing path itself is still too strong or inconsistent.
```

## Teacher Review

Teacher MCP session:

```text
session-20260623-504915
```

Verdict:

```text
PROBE
confidence = 0.9
```

Teacher agreed that the next target should be:

```text
momentum force / MRT feedback
```

and specifically recommended isolating fixed-point force amplification. We have
already done part of this with `force_fixed_iterator=1`, which shows that the
second iteration is a strong amplifier but not the only failure source.

## Code Path To Audit Next

Active MRT path in generated `Dynamics.c`:

```text
F_total = F_surf + F_pressure + F_body + F_mu

U = m0[1] + 0.5 * F_total[0] / rho
V = m0[2] + 0.5 * F_total[1] / rho
W = m0[3] + 0.5 * F_total[2] / rho

mF[1:3] = F_total / rho
m = m0 - (m0 - EQReq + 0.5*mF) * Omega + mF
g = invM * m
```

Risk questions:

```text
1. Is the Guo/MRT forcing term mapped to moment space correctly for this TCLB
   pressure-distribution formulation, or is force-over-rho injected twice?

2. Should `m[1:3]` in the final momentum state be `U + 0.5*F/rho`, given that
   `U` already contains `0.5*F/rho`?

3. Is `F_pressure = -(1/3)*p*(rho_h-rho_l)*gradPhi` using the right pressure
   moment and time level?

4. Is the `(0.5-tau)*(rho_h-rho_l)*stress*gradPhi` viscous force formula
   compatible with the current `stress` reconstruction and fixed-point loop?

5. Does low-density gas require a bounded velocity/force treatment or a
   different density-ratio-compatible phase-field formulation?
```

## Immediate Next Probe

Do not alter wetting BC yet.

This note originally proposed the next diagnostic. That probe has now been
implemented and run. See:

```text
docs/stage14/68_s2_momentum_force_mode_probe_20260623.md
artifacts/stage14_s2_momentum_force_probe_20260623/
```

Historical probe plan:

```text
A. Add `ReplayMomentumSourceVelocity` and `ReplayMomentumOutputMoment` to prove
   whether the final g moment contains one or two half-force contributions.

B. Add `MomentumForceMode` diagnostic switch:
   0 legacy
   1 no F_mu
   2 no F_pressure
   3 no F_surf
   4 no force in g update, but keep h diagnostics

C. Run the same wall_60to30_10, 6-step P100 probe for modes 1-4 on /home, not
   /mnt/usb1t.
```

Expected payoff:

```text
If disabling F_mu prevents growth, the viscous fixed-point/stress formula is the
primary defect.

If disabling F_pressure prevents growth, the pressure moment/time-level coupling
is the primary defect.

If disabling all g forcing prevents growth while h diagnostics remain finite,
the implementation issue is definitely in momentum forcing rather than wall
ghost or compact-stencil wetting.
```

Actual result:

```text
MomentumForceMode=4 (all momentum force disabled) stays bounded.
MomentumForceMode=5 (surface-only momentum force) stays bounded.
MomentumForceMode=0 fails with PhaseFromH ~= 6.087e3 by step 6.
MomentumForceMode=1 and 2 remain phase-bounded but still show large UPost when
only one of F_mu/F_pressure is removed.
```

The next target is therefore the pressure/viscous momentum-force closure and
the MRT force insertion path, not contact-angle tuning.

## Operational Constraint

`/mnt/usb1t` is full:

```text
/dev/sdd1 ext4 468G used 444G available 0 100% /mnt/usb1t
```

Until storage is cleaned or a different run root is selected, all new short
diagnostic runs must use:

```text
/home/yuan/<run_name>
```

There is about 16-20 GB free on `/` during this note, enough for a small number
of 6-step single-case VTI probes.

## Do Not Claim

Do not claim:

```text
contact-angle validation passed
PhaseAdvectionVelocityMode=1 is a final physical fix
force_fixed_iterator=1 is acceptable
compact-stencil wetting is validated
dynamic impact can start
```

The current result is narrower and more useful:

```text
WallGhost pollution is no longer the active earliest failure.
h post-force velocity is a direct trigger.
Momentum g forcing/fixed-point feedback remains the root path to fix.
```
