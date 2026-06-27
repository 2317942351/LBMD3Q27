# Stage14-B32 Dynamic Preflight Force Split

Date: 2026-06-27

Branch: `work/phasefield-c-reference-20260623`

Status: completed. Runtime and analyzer succeeded, but dynamic impact preflight
is blocked by the flat-wall force-numerator gate.

## Purpose

B32 is not a dynamic impact simulation. It is a preflight blocker gate.

The B29-B31 evidence says:

```text
PhaseAdvectionVelocityMode=2 removes h-equilibrium / PhaseFromH as the first
visible failure in the short probe.

ForceDensityClosureMode=2 does not change the step-15 F_total/rho onset.
```

Therefore the remaining question before any impact setup is:

```text
Which force numerator path creates the unstable F_total?
```

## Runtime Plan

Remote root:

```text
/mnt/usb1t/RUNS/runs/stage14_B32_dynamic_preflight_force_split_20260627
```

Local artifacts, after download:

```text
artifacts/stage14_B32_dynamic_preflight_force_split_20260627/
```

Fixed settings:

```text
case = wall_60to30_10
Density_h = 1.0
Density_l = 0.005
FmuStressClosureMode = 2
PressureClosureMode = 1
ForceFixedPointMode = 2
PhaseAdvectionVelocityMode = 2
ForceDensityClosureMode = 2
iterations = 20
GPU = P100, CUDA_VISIBLE_DEVICES=1
```

Force split:

| Probe | MomentumForceMode | Meaning |
|---|---:|---|
| `N0_legacy_total_force` | 0 | full force |
| `N1_noFmu` | 1 | remove `F_mu` from `F_total` |
| `N2_noPressure` | 2 | remove `F_pressure` from `F_total` |
| `N3_noSurf` | 3 | remove `F_surf` from `F_total` |
| `N4_zeroForce` | 4 | no momentum force |
| `N5_surfBodyOnly` | 5 | `F_surf + F_body` only |

## Decision Rules

Allowed B32 outcome:

```text
dynamic_preflight_blocked_by_force_numerator
dynamic_preflight_blocked_by_stress_fmu
dynamic_preflight_blocked_by_surface_force
dynamic_preflight_blocked_by_pressure_force
dynamic_preflight_blocked_by_unresolved_force_balance
```

Forbidden B32 outcome:

```text
dynamic impact validated
production dynamic simulation ready
contact-angle validation passed
```

## Provisional Dynamic Preflight Conclusion

Dynamic impact is blocked before setup because the flat-wall 20/100 step
momentum-force gate is not yet stable. The dynamic case would consume exactly
the same force path:

```text
F_surf / F_mu / F_pressure
  -> F_total / rho
  -> momentum field
  -> phase advection and interface evolution
```

Starting impact before this path is stable would only hide the root cause under
transient geometry and impact inertia.

## Results

Runtime status:

```text
stage14_B32.status = OVERALL_RC=0
digest.status = DIGEST_RC=0
```

Binary:

```text
sha256 = 263bdd7bfc48e179dcab367f61481814b426682f96a32ddf2a6d96bb47d7d97b
```

Force split digest:

| Probe | MomentumForceMode | First momentum threshold | First force/rho threshold | First F_mu threshold | First pressure-force threshold | PhaseFromH threshold |
|---|---:|---:|---:|---:|---:|---:|
| `N0_legacy_total_force` | 0 | step 12, 1.577 | step 15, 8.85e5 | step 15, 4.43e3 | step 16, 1.70e7 | none |
| `N1_noFmu` | 1 | none | none | none | none | none |
| `N2_noPressure` | 2 | step 12, 1.567 | step 15, 8.69e5 | step 15, 4.35e3 | step 16, 1.63e7 | none |
| `N3_noSurf` | 3 | none | none | none | none | none |
| `N4_zeroForce` | 4 | none | none | none | none | none |
| `N5_surfBodyOnly` | 5 | none | none | none | none | none |

## B32 Verdict

Allowed outcome:

```text
dynamic_preflight_blocked_by_stress_fmu_and_surface_force_coupled_numerator
```

B32 shows:

1. Removing `F_pressure` does not remove the failure. `N2_noPressure` remains
   essentially the same as `N0_legacy_total_force`.
2. Removing `F_mu` removes all configured B22/B21/PhaseFromH thresholds within
   the 20-step gate.
3. Removing `F_surf` also removes all configured thresholds.
4. Keeping `F_surf + F_body` only does not fail within this gate.

The most defensible interpretation is not that `F_surf` alone is invalid.
Rather, the unstable numerator is the coupled path:

```text
F_surf = mu * gradPhi
  -> stress reconstruction / F_mu
  -> F_total
  -> F_total / rho
```

The pressure force can become enormous later, but under this matrix it is not
the first effective lever.

Dynamic impact remains blocked. A dynamic impact setup would add inertia and
moving contact-line transients on top of a flat-wall force path that is already
unstable by step 15.

## Next Required Work

The next stage must audit the coupled numerator formula, not the denominator:

```text
calcMu(C)
  -> F_surf = mu * gradPhi
  -> stress reconstruction used by F_mu
  -> F_mu scaling with (0.5 - tau) * (Density_h - Density_l)
  -> F_total and MRT force injection
```

Recommended next candidate is a shadow-first `FmuSurfaceCouplingAuditMode`:

```text
legacy F_surf + legacy F_mu
F_surf from bounded/shadow mu
F_mu from incoming non-equilibrium stress but with legacy F_surf
F_mu disabled only as diagnostic reference
surface-force-only reference retained as a diagnostic, not as a repair
```

No curved-wall validation, contact-angle claim, or dynamic impact run should be
started until this flat-wall numerator gate is closed.
