# Stage14 B114: B113 slim normalized tmp1 minimal validation

Date: 2026-07-03

## Purpose

This is a minimal necessary validation for the B113 normalized `tmp1` algebra path. It is not a contact-angle validation, not a morphology validation, and not a curved-wall test.

The goal is only to answer:

1. Is the B113 slim binary present and identifiable?
2. Does the `b113tmp1` VTK field-set summary require only the slim fields?
3. Does `PhaseEquationMode=1` remove the current wall instability by itself?

## Solver and artifacts

Remote binary:

`/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric_b113slimtmp1/main`

SHA256:

`bb67e438c331df6fab915bb5360192622b9fdeb8aaf728a594bcfc2589ebb791`

Remote runtime evidence:

`/mnt/usb1t/RUNS/runs/stage14_B114_b113_slim_tmp1_min_20260703/`

Local lightweight evidence:

`artifacts/stage14_B114_b113_slim_tmp1_minimal_20260703/`

## Script fix

`stage14_s2_replay_smoke.py` now maps:

```python
REQUIRED_FIELDS_BY_VTK_SET = {
    "b113tmp1": B113_TMP1_FIELDS,
    ...
}
```

This prevents the slim B113 field-set from being judged against the old full replay field list. This is a validation-script fix only; it does not change solver physics.

## Minimal run result

Case: `wall_t90_10`

Parameters:

- `Density_h = 1.0`
- `Density_l = 0.005`
- `vtk_field_set = b113tmp1`
- `iterations = 10`
- modes tested: `PhaseEquationMode=0` and `PhaseEquationMode=1`

Both modes produced VTI frames at steps `[0, 10]`. Required B113 fields were present in both frames; there were no missing required fields.

### Step 0

Both modes were finite and inactive in the slim tmp1 diagnostics:

- `ReplayPhaseFromH`: finite, zero
- `ReplayTmp1`: finite, zero
- `ReplayTmp1BoundedShadow`: finite, zero
- `ReplayFphiMaxAbs`: finite, zero
- `ReplayPhaseOutOfBoundsFlag`: zero

### Step 10

Both modes still fail with essentially identical instability.

Mode 0:

- `ReplayPhaseFromH`: `553348` nonfinite cells; max abs about `4.29e241`
- `ReplayTmp1`: `522492` nonfinite cells; max abs about `5.56e307`
- `ReplayTmp1BoundedShadow`: `519668` nonfinite cells
- `ReplayFphiMaxAbs`: finite but huge, max about `1.98e145`
- `ReplayPhaseOutOfBoundsFlag`: `6654` nonzero cells

Mode 1:

- `ReplayPhaseFromH`: `553348` nonfinite cells; max abs about `4.29e241`
- `ReplayTmp1`: `522492` nonfinite cells; max abs about `5.56e307`
- `ReplayTmp1BoundedShadow`: `519668` nonfinite cells
- `ReplayFphiMaxAbs`: finite but huge, max about `1.98e145`
- `ReplayPhaseOutOfBoundsFlag`: `6654` nonzero cells

## One-step attempt

A new one-step run was attempted at:

`/mnt/usb1t/RUNS/runs/stage14_B114_b113_slim_tmp1_1step_20260703/`

It is not physical evidence. Both modes timed out with `RUN_RC=124` before VTI output, with repeated server-side X authorization messages:

`Authorization required, but no authorization protocol specified`

No conclusion should be drawn from that run except that this short wrapper path needs launch-environment cleanup before being used.

## Conclusion

B113 normalized `tmp1` is integrated into the slim solver branch and selectable through `PhaseEquationMode`, but it is not a sufficient fix for the wall case. The old hypothesis remains stronger:

```text
wall / h_i streaming or reconstruction
  -> PhaseF / PhaseFromH leaves the physical range
  -> tmp1/Fphi and heq amplify the damage
  -> rho(C), mu, and force become invalid
  -> morphology/contact angle becomes meaningless
```

Therefore the next necessary work should not be more contact-angle runs or grid refinement. The next code target should be the producer-consumer closure around `h_i` wall streaming/reconstruction and the phase source/equilibrium timing:

- `PhaseF -> tmp1/Fphi -> h update -> PhaseFromH`
- incoming/outgoing wall `h_i` mass budget
- no-flux/chemical-potential wall handling only after the above path is bounded

## Claim limits

Do not claim:

- contact-angle validation passed
- morphology is repaired
- dynamic impact readiness
- B113 solved the current instability

Allowed claim:

- B113 normalized `tmp1` algebra path is compiled and selectable, but the minimal wall test still fails by step 10 in both legacy and normalized modes.
