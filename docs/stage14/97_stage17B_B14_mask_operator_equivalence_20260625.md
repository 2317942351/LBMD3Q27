# Stage17B-B14 Mask / Operator Equivalence Audit

Date: 2026-06-25

Status: `mask_operator_equivalence_complete`

Claim limit: offline mask/operator audit only; not contact-angle validation.

## Purpose

B13 established a narrow fact:

```text
InitialReplayWallGhostUsed reaches 38 in the near-interface region
but removing WallGhost from the initial stencil does not change mu/lapPhi
at meaningful precision
```

That leaves the B10/B11 offline reconstruction itself as the next suspect.  
B14 tests whether the offline periodic D3Q27 operator is being applied to the
same field/mask semantics as TCLB's initial replay.

## Audit Setup

Inputs:

```text
TCLB step-0 VTI from B13
case.xml from B13
```

Compared operator modes:

```text
periodic stencil on TCLB PhaseField
center-on-boundary stencil on TCLB PhaseField
midpoint-on-boundary stencil on TCLB PhaseField
```

Mask groups:

```text
offline_fluid
tclb_fluid
near_interface_tclb_fluid
contact_core_tclb_fluid
offline_fluid_tclb_boundary
outer_boundary
cylinder_overlap_boundary
```

## Key Result

Primary result:

```text
tclb_replay_matches_periodic_stencil_on_tclb_phase
```

This is the key correction:

```text
TCLB current replay itself is not the source of the B12/B13 discrepancy.
The discrepancy is coming from the offline reconstruction and comparison masks.
```

## Important Numbers

Mask summary:

| Quantity | Value |
|---|---:|
| total cells | `884736` |
| TCLB boundary cells | `172968` |
| offline solid cells | `121344` |
| offline fluid cells that are TCLB boundary | `51624` |
| offline solid cells that are TCLB fluid | `0` |
| outer boundary cells | `50824` |
| cylinder overlap boundary cells | `800` |
| near-interface TCLB fluid cells | `2540` |
| contact-core TCLB fluid cells | `556` |

Operator comparison:

| Quantity | Value |
|---|---:|
| current vs periodic `mu` near-interface max abs | `6.34e-19` |
| current vs periodic `lapPhi` near-interface max abs | `2.46e-15` |
| current vs center-boundary `mu` near-interface max abs | `7.01e-05` |
| current vs center-boundary `lapPhi` near-interface max abs | `3.11e-01` |
| B13 ghost delta `mu` near-interface max abs | `1.81e-19` |
| B13 ghost delta `lapPhi` near-interface max abs | `8.05e-16` |
| `InitialReplayWallGhostUsed` near-interface max abs | `38` |
| `InitialGhostNeighborCount` near-interface max abs | `38` |
| `InitialNoGhostPhaseStencilFallbackCount` near-interface max abs | `0` |

Boundary distance histogram shows the TCLB boundary set spans both the curved solid neighborhood and the outer/domain walls. The large `phase_mean = 1.0` bins far from the cylinder confirm that the comparison mask is not limited to the solid-cylinder neighborhood.

## Interpretation

1. B13 already ruled out direct `WallGhost` value substitution as the source of the
   initial `mu/lapPhi` mismatch.
2. B14 now shows that TCLB's replay on its own `PhaseField` is essentially periodic-stencil
   consistent. `current_vs_periodic_mu` and `current_vs_periodic_lapPhi` are roundoff-level.
3. Therefore the offline B10/B11 mismatch is dominated by reconstruction semantics:
   mask choice, outer/domain wall treatment, and operator equivalence rather than
   a solver-side replay bug.
4. The next step is not to change wetting physics. It is to make the offline audit
   match TCLB's actual domain classification and stencil semantics.

## Next Gate

B15 should do one of the following:

```text
1. Rebuild B10/B11 offline reconstruction with TCLB-compatible fluid/boundary masks.
2. Restrict the offline periodic stencil to the same TCLB fluid mask used by the replay.
3. Only after the offline and TCLB classification agree, re-evaluate whether any
   remaining mismatch is a genuine initialization-profile issue.
```

Do not move to controlled wetting write or dynamic impact from B14 alone.

## Files

Artifacts:

```text
artifacts/stage17B_B14_mask_operator_20260625/b14_mask_operator_equivalence.json
artifacts/stage17B_B14_mask_operator_20260625/b14_key_summary.json
artifacts/stage17B_B14_mask_operator_20260625/operator_comparison.csv
artifacts/stage17B_B14_mask_operator_20260625/boundary_distance_hist.csv
```
