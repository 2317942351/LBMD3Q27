# Stage14-B46/B47 Gate Decision

Status: blocked gate decision. This is not contact-angle validation and not curved-wall validation.

## Evidence Chain

- B43 verdict: `b43_postprocess_scale_candidate_strong`.
- B43 legacy low-rho F/rho: `2636.41`.
- B43 legacy_hundredth low-rho F/rho: `30.2118` (postprocess only).
- B44 verdict: `b44_force_balance_candidate_found`.
- B44 legacy_hundredth net/term: `0.94652`.
- B44 legacy_hundredth F_mu fraction: `0.766663`.
- B45 verdict: `b45_phase_gate_failed` / `b45_h_update_boundedness_fails_first`.
- B45 first PhaseFromH OOB step: `3`.
- B45 first HPost OOB step: `4`.
- B45 first F/rho > 1000 step: `13`.

## B46 Decision

Verdict: `b46_blocked_by_b45_phase_boundedness`

PhaseFromH leaves [0,1] before force-over-rho explosion, so flat-wall contact angle morphology is not physically interpretable.

Minimum reopen gate: B45 must run at least 100 steps with PhaseField and PhaseFromH bounded, no NaN, and force/rho finite without hard clamp.

## B47 Decision

Verdict: `b47_blocked_by_b45_phase_boundedness`

Curved-wall shadow/controlled-write gates depend on a bounded phase-field transport baseline. B45 failed before flat-wall physical validation.

Minimum reopen gate: B46 flat-wall static and decoupled direction gates must pass before curved-wall shadow/write can be interpreted physically.

## Next Branch

Next: `B48_h_population_phasefromh_timelevel_closure`.

Primary target: `PhaseF -> h populations -> h update -> streaming -> PhaseFromH`.

Required probe: steps 0-4 full h population producer-consumer audit at first OOB cells.

Do not:
- do not promote F_mu scale-down as physical repair
- do not run contact-angle validation while B45 fails
- do not enter dynamic impact
- do not write curved-wall PhaseF
