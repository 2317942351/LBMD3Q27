# Stage14-B37 GradPhi Force-Consumer Cap Rejected

Date: 2026-06-28

Branch: `work/phasefield-c-reference-20260623`

Status: rejected repair candidate.

## Purpose

B37 tested whether capping the force-consuming `gradPhi` before `F_surf` and
`F_mu` removes the step-15 spike. The cap was default-off and had shadow and
write candidate modes. This was not a contact-angle validation.

## Runtime

Remote root:

```text
/mnt/usb1t/RUNS/runs/stage14_B37_grad_phi_cap_retry2_20260628
```

Local artifact root:

```text
artifacts/stage14_B37_grad_phi_cap_20260628
```

Binary:

```text
3f3e79b5f234136b515094c6dba6e2e2237e3bdbde8a31dcba1f65c37d0ce78e
```

## Result

B37 is rejected. The cap is wired, but it never activates in the failure
window:

```text
cap_hit_fraction = 0.0
step 15 max_pre_cap_grad_phi = 0.3912051178198273
step 15 max_post_cap_grad_phi = 0.3912051178198273
step 15 max_replay_force_over_rho = 885434.9865443383
step 20 max_replay_force_over_rho = 9.281471742419461e152
step 20 nonfinite_total = 1151148
```

Caps of 20, 10, and 5 all failed because the actual gradient magnitude is far
below the cap at first onset.

## Code Meaning

The relevant implementation is in
`third_party/tclb_snapshots/stage17B_diffuse_solid_shadow/models/multiphase/d3q27_pf_velocity/Dynamics.c.Rt`:

```text
calcGradPhi()
  -> stage14_b37_apply_grad_phi_cap(...)
  -> gradPhi_force
  -> calc_Fs(mu, gradPhi_force)
  -> stage14_fmu_from_stress(..., gradPhi_force, tau)
```

`calc_Fp` still consumes raw `gradPhi` by design, so B37 only tested the
surface/stress force consumer. The first failure is not an excessive
`|gradPhi|` problem.

## Decision

Do not promote B37 as a repair.

Next implication:

```text
The next probe must inspect mu, stress, F_mu, F_total and ForceOverRho
co-located at the first bad cell.
```
