# Stage17B-B15 Corrected Offline Audit Gate

Date: 2026-06-25

Status: `b15_offline_audit_correction_complete`

Claim limit: offline comparison correction only; not contact-angle validation.

## Purpose

B13 and B14 changed the root-cause direction for the Stage17B initial-stencil
audit:

```text
B13: direct WallGhost substitution has no meaningful effect on initial mu/lapPhi.
B14: TCLB replay matches a periodic D3Q27 stencil on TCLB PhaseField and TCLB fluid nodes.
```

B15 turns that into a corrected audit gate.  It quantifies the difference
between the older B10/B11 comparison style and the corrected comparison
semantics:

```text
old style: offline reconstructed phase + offline-fluid mask
corrected style: TCLB PhaseField + TCLB fluid mask
```

This is a read-only offline audit.  It does not modify solver physics and does
not validate wetting/contact angle behavior.

## Inputs

Remote input case:

```text
/mnt/usb1t/RUNS/runs/stage17B_B13_initial_stencil_split_20260625/
  cylinder_init090_b13_initial_stencil_split_s0001/case.xml
```

Remote input VTI:

```text
/mnt/usb1t/RUNS/runs/stage17B_B13_initial_stencil_split_20260625/
  cylinder_init090_b13_initial_stencil_split_s0001/output/case_VTK_P00_00000000.vti
```

Local script:

```text
scripts/stage17/stage17B_B15_offline_audit_correction.py
```

## Key Result

Primary result:

```text
b10_b11_error_removed_by_tclb_fluid_mask_and_tclb_phase_reference
```

The corrected comparison shows that TCLB `InitialReplayMu` and
`InitialReplayLapPhi` agree with the periodic D3Q27 operator at roundoff level
when both sides use TCLB's own `PhaseField` and the comparison is restricted to
TCLB fluid cells.

## Important Numbers

| Quantity | Value |
|---|---:|
| B10-style near-interface `mu` max abs error | `3.46875e-04` |
| Corrected TCLB-fluid near-interface `mu` max abs error | `6.335806445462167e-19` |
| B10-style near-interface `lapPhi` max abs error | `1.5416666666666667` |
| Corrected TCLB-fluid near-interface `lapPhi` max abs error | `2.456368441983159e-15` |
| Offline phase vs TCLB phase `mu` max abs error on TCLB fluid near-interface | `3.530223573332822e-04` |
| Offline-fluid cells that are TCLB boundary cells | `51624` |
| Cylinder-overlap boundary cells | `800` |
| Outer/domain boundary cells | `50824` |

Regional comparison:

| Region | Cells | `mu` max abs error | `lapPhi` max abs error |
|---|---:|---:|---:|
| `b10_near_interface_offline_fluid` | `2856` | `3.46875e-04` | `1.5416666666666667` |
| `b11_near_interface_tclb_fluid` | `2540` | `6.335806445462167e-19` | `2.456368441983159e-15` |
| `corrected_near_interface_tclb_phase_fluid` | `2540` | `6.335806445462167e-19` | `2.456368441983159e-15` |
| `b10_contact_core_offline_fluid` | `872` | `3.46875e-04` | `1.5416666666666667` |
| `b11_contact_core_tclb_fluid` | `556` | `3.7269449679189215e-19` | `1.6583956430338276e-15` |
| `corrected_contact_core_tclb_phase_fluid` | `556` | `3.7269449679189215e-19` | `1.6583956430338276e-15` |
| `offline_fluid_tclb_boundary` | `51624` | `3.46875e-04` | `1.5416666666666667` |
| `cylinder_overlap_boundary` | `800` | `3.46875e-04` | `1.5416666666666667` |
| `outer_boundary` | `50824` | `2.25000e-04` | `1.0142869661070408` |

## Interpretation

1. The large B10-style error is not valid evidence of a solver-side
   `WallGhost`, `mu`, or `lapPhi` bug.
2. The older offline comparison mixed an offline-fluid mask with cells that TCLB
   classifies as boundary cells.  This added `51624` TCLB boundary cells to a
   comparison that was intended to be fluid-only.
3. After correcting the reference field and mask, the current TCLB replay
   agrees with the periodic D3Q27 stencil at roundoff level.
4. Remaining offline-vs-TCLB differences should be treated as reconstruction,
   mask, coordinate, or boundary-classification differences unless a corrected
   TCLB-fluid comparison still shows a residual.

## Consequence

Do not modify solver physics based on the old B10/B11 mismatch.  The next
correct step is to patch the offline audit scripts/reports so future gates
default to:

```text
TCLB PhaseField reference
TCLB fluid-cell masks
explicit separation of cylinder boundary cells and outer/domain boundary cells
```

Only after a corrected comparison still shows a non-roundoff residual should
the solver path be audited again for physics changes.

## Guardrails

This gate does not justify:

```text
contact-angle validation passed
controlled wetting write
dynamic impact setup
solver physics changes based on B10/B11 mismatch
```

It does justify:

```text
retiring the old offline-fluid-mask interpretation as a solver-bug argument
using B15-style corrected masks in the next audit scripts
pausing WallGhost/initial-stencil patching until corrected evidence requires it
```

## Files

Artifacts:

```text
artifacts/stage17B_B15_offline_audit_correction_20260625/b15_key_summary.json
artifacts/stage17B_B15_offline_audit_correction_20260625/b15_offline_audit_correction.json
artifacts/stage17B_B15_offline_audit_correction_20260625/current_vs_tclb_periodic_mu_by_region.csv
artifacts/stage17B_B15_offline_audit_correction_20260625/current_vs_tclb_periodic_lap_by_region.csv
artifacts/stage17B_B15_offline_audit_correction_20260625/offline_vs_tclb_phase_mu_by_region.csv
```

Verification:

```text
python -m py_compile scripts/stage17/stage17B_B15_offline_audit_correction.py
git diff --check
```
