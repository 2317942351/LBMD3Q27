# Stage18 Flat-Wall Decoupled Wetting: Mode 4 Mass-Compensated Probe

Date: 2026-07-04
Branch: `work/phasefield-c-reference-20260623`
Status: `diagnostic_probe_passed_but_not_final_physics`

## Purpose

This note records the first flat-wall decoupled response runs after
`phase_wall_mode=3` failed to move the contact line.  It is a root-cause probe,
not a contact-angle validation claim.

The relevant producer-consumer path is:

```text
wall target theta
  -> wall_c_ghost_field from dC/dn(theta)
  -> near-wall grad/laplace/mu
  -> h_i collision
  -> pull streaming
  -> missing-link h_i wetting boundary
  -> C = sum_i h_i
```

## Baseline Evidence

Static/equilibrium large flat-wall gate:

```text
artifact: artifacts/stage18_flat_wall_perlink_large_20260704_r12_300
R=18, W=4, steps=300, phase_wall_mode=3
theta60  -> calibrated bbox 61.0 deg
theta90  -> calibrated bbox 88.53 deg
theta120 -> calibrated bbox 121.0 deg
```

This shows the initialized static shapes remain stable for 60/90/120.

Decoupled response with the pair-conservative boundary:

```text
artifact: artifacts/stage18_flat_wall_perlink_decoupled_20260704_r13_300
mode: phase_wall_mode=3
init60  -> target30  -> calibrated bbox 61.0 deg
init120 -> target150 -> calibrated bbox 121.0 deg

artifact: artifacts/stage18_flat_wall_perlink_decoupled_20260704_r14_1000
mode: phase_wall_mode=3
init60  -> target30  -> calibrated bbox 61.93 deg
init120 -> target150 -> calibrated bbox 121.0 deg
```

Interpretation: `phase_wall_mode=3` changes missing-link non-equilibrium
moments but preserves local `sum_i h_i = C`.  With `omega_h=1`, the next
collision relaxes most of that non-equilibrium signal back toward equilibrium.
The target angle reaches `wall_c_ghost_field`, but it does not enter the
macro-relevant phase-field closure strongly enough to move the contact line.

## Mode 4 Probe

`phase_wall_mode=4` was added as a diagnostic mode:

```text
missing incoming h_q += strength * w_q * (Cghost - Cfluid)
C = sum_i h_i is allowed to change locally
the summed wall delta is compensated through interface-cell redistribution
```

This is intentionally different from mode 3.  It tests whether the failed
decoupled response is caused by the target angle not entering the macro
`C=sum(h_i)` path.

New parameter:

```text
--phase-wall-wetting-strength
```

Default is `1.0` to preserve the first mode-4 behavior.  Lower values are
diagnostic relaxation strengths, not contact-angle sign or ghost-distance
tuning.

## Runtime Results

### r16, strength = 1.0

```text
artifact: artifacts/stage18_flat_wall_perlink_decoupled_mode4_20260704_r16_100
remote:   /mnt/usb1t/RUNS/runs/stage18_flat_wall_perlink_decoupled_mode4_20260704_r16_100
steps:    100
```

Results:

```text
init60  -> target30:
  calibrated bbox: 35.73 deg
  circle morphology: 45.90 deg
  phase_wall_delta_mass: +55.85
  nonfinite_count: 0

init120 -> target150:
  calibrated bbox: 114.91 deg
  circle morphology: 164.32 deg
  phase_wall_delta_mass: -15.98
  nonfinite_count: 0
```

Finding: mode 4 makes the acute case move strongly toward the target.  The
obtuse morphology plot also shows clear receding behavior, but the calibrated
bbox estimator is unreliable for the flattened/non-spherical shape and
disagrees with the circle fit.

### r17, strength = 0.5

```text
artifact: artifacts/stage18_flat_wall_perlink_decoupled_mode4_20260704_r17_100_s05
remote:   /mnt/usb1t/RUNS/runs/stage18_flat_wall_perlink_decoupled_mode4_20260704_r17_100_s05
steps:    100
```

Results:

```text
init60  -> target30:
  calibrated bbox: 42.31 deg
  circle morphology: 69.34 deg
  phase_wall_delta_mass: +17.29
  nonfinite_count: 0

init120 -> target150:
  calibrated bbox: 121.0 deg
  circle morphology: 156.18 deg
  phase_wall_delta_mass: -10.54
  nonfinite_count: 0
```

Finding: reducing the boundary relaxation strength reduces wall mass exchange.
The obtuse case remains directionally correct by the morphology/circle-fit
view, while the acute case becomes under-driven at 100 steps.

## Current Conclusion

Mode 4 is a real diagnostic breakthrough:

```text
mode 3: stable but target theta does not move C morphology
mode 4: stable and target theta does move C morphology
```

But mode 4 is not the final wetting boundary:

```text
1. It uses a large wall mass delta and then compensates globally.
2. The physical wetting condition should impose contact-angle gradient and
   chemical-potential/no-flux consistency, not behave like a wall mass source.
3. The two contact-angle estimators disagree for distorted/non-spherical
   shapes, so morphology images must remain part of the gate.
4. Runtime is too slow because mode 4 adds full-domain mass compensation every
   step.
```

## Next Repair Direction

Do not go to cylinder/sphere yet.

Next step should convert the mode-4 lesson into a stricter flat-wall boundary:

```text
1. Keep Cghost(theta) as the contact-angle condition.
2. Keep missing-link h_i per-link reconstruction.
3. Replace large wall mass injection with a zero-net wall phase source or a
   local interface-band redistribution ledger.
4. Make the near-wall phase source normal and mu/laplace stencil consume the
   same dC/dn(theta) condition.
5. Report wall mass delta, local compensation delta, and global mass drift
   separately.
6. Re-run only the 100-step decoupled flat-wall gate before any long run.
```

Acceptance for the next probe:

```text
nonfinite_count = 0
total mass drift near machine level
absolute wall mass delta substantially below r16/r17
init60 -> target30 moves below the initial 61 deg family
init120 -> target150 moves above the initial 121 deg family by morphology
no reliance on ghost-distance/sign as the repair knob
```
