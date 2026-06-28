# Stage14-B41 Stress-Source Audit

Status: diagnostic ranking only. This is not a solver repair, not contact-angle validation, and not dynamic-impact readiness.

B41 reuses the B40 stress-construction fields by design. No TCLB solver field or active physics path is changed in B41.

Input stats: `C:\Users\yuanz\Desktop\lbm-new\repo\artifacts\stage14_B41_stress_source_audit_20260628\B41_stress_source_audit\b41_mask_stats.csv`
Focus step: `13`
Primary mask: `low_rho`
Verdict: `b41_no_better_implementable_candidate`

## Primary Ranking

| rank | candidate | stress | F_mu | F/rho | F/rho / legacy | B42 hint |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 1 | incoming_raw_population | 138.671 | n/a | n/a | n/a | shadow only unless B42 adds force reconstruction |
| 2 | legacy_relaxed_moment | 383.322 | 14.4924 | 2636.41 | 1 | existing legacy path / baseline |
| 3 | raw_moment_preforce | 17562.5 | 39.9641 | 7596.83 | 2.8815 | B42 candidate mode 3 |
| 4 | bgk_pop_neq_preforce | 17562.5 | 49.9552 | 9495.99 | 3.60186 | B42 candidate mode 4 |
| 5 | incoming_neq_preforce | 17562.5 | n/a | n/a | n/a | existing FmuStressClosureMode=2 / compare only |
| 6 | post_force_shadow | 2.02912e+06 | n/a | n/a | n/a | reject as active source |

## B42 Recommendation

Do not directly promote the rankable raw/BGK pre-force candidates into active B42 modes: their force-over-rho at the focus step is not better than the legacy relaxed-moment path. Use B42 for a new physically motivated stress definition, such as deviatoric/pressure-removed incoming stress or moment-wise MRT scaling, and use B43 derivation before any default-off candidate is treated as a repair.

## Guardrails

- Keep B42 modes default-off.
- Do not use post-force shadow stress as an active source.
- Do not claim contact-angle validation from B41/B42.
- If no candidate improves the force/stress metrics, escalate to F_mu coefficient derivation before more runtime tuning.
