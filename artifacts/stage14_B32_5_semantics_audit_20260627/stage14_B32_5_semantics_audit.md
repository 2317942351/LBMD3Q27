# Stage14-B32.5 TCLB Semantics Audit

Verdict: `semantics_audit_pass_with_warnings`

Claim limit: static source semantics audit only. This is not a runtime
stability result, contact-angle validation, or dynamic-impact preflight.

## Checks

| check | status | detail |
|---|---|---|
| `streamed_macros_are_adddensity` | `warning` | `pnorm/U/V/W` primary state should be AddDensity streaming state. Conditional OutFlow AddField helpers are recorded as warnings. |
| `replay_fields_are_addfield` | `pass` | Replay/Bxx diagnostics should be AddField and must not participate in TCLB streaming. |
| `diagnostic_and_candidate_settings_exist` | `pass` | Stage14 diagnostic settings are available in model XML. |
| `collision_mrt_force_order` | `pass` | CollisionMRT producer-consumer anchors appear in expected source order. |
| `fmu_prefactor_mrt_bgk_recorded` | `warning` | MRT and BGK F_mu prefactors differ; this is recorded as a B35 branch, not changed in B32.5/B33. |
| `boundary_sentinel_guard_recorded` | `pass` | Boundary sentinel should be -999.0 after prior Stage13 audit. |

## Stage Markers

| marker | line |
|---|---:|
| `BaseIter` | 628 |
| `calcPhase` | 627 |
| `calcPhaseGrad` | 635 |
| `calcWall_CA` | 633 |
| `calcWallPhase_correction` | 637 |
| `geometric_iteration_action` | 664 |

## Next Gate

B33 first-bad-cell ledger if no fail status
