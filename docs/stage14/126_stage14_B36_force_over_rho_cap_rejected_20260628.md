# Stage14-B36 Force-Over-Rho Cap Rejected

Date: 2026-06-28

Branch: `work/phasefield-c-reference-20260623`

Status: rejected repair candidate.

## Purpose

B36 tested whether limiting the consumed `ForceOverRho` could prevent the
short-run blow-up. This was a default-off probe. It was not a contact-angle
validation.

## Runtime

Remote root:

```text
/mnt/usb1t/RUNS/runs/stage14_B36_force_over_rho_cap_20260628
```

Local artifact root:

```text
artifacts/stage14_B36_force_over_rho_cap_20260628
```

Binary:

```text
b7cb8affb50069bf18724725b9d51d4eb4c64f22be5d50a8d8b92a375a13f8a7
```

## Result

B36 is rejected because it can cap the written/replayed `ReplayForceOverRho`
in the candidate path while the upstream pre-cap quantity still grows to
catastrophic scale. It therefore hides a symptom instead of removing the
producer.

Observed failure class:

```text
B36ForceOverRhoPreCap still grows to ~1e154 class.
nonfinite fields still appear.
momentum_delta_g_not_mf remains.
```

## Code Meaning

The relevant path is:

```text
F_total producer
  -> stage14_b36_apply_force_over_rho_limiter(F_total, force_rho_eff)
  -> ReplayForceOverRho / mF / U
```

This can only operate after the force numerator has already been assembled. It
does not explain why `F_total` becomes unphysical.

## Decision

Do not promote B36 as a repair. It remains useful only as evidence that a late
force/rho limiter is not a root-cause solution.

Next implication:

```text
Return upstream to F_mu/stress/force assembly and producer-consumer timing.
```
