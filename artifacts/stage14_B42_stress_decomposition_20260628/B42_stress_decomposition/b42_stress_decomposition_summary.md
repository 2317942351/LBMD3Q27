# Stage14-B42 Stress Decomposition Audit

Status: shadow-only diagnostic. This is not a solver repair or contact-angle validation.

Input stats: `/mnt/usb1t/RUNS/runs/stage14_B42_stress_decomposition_20260628/B42_stress_decomposition/b42_mask_stats.csv`
Focus step: `13`
Mask: `low_rho`
Legacy F/rho: `2636.41`
Verdict: `b42_no_deviatoric_candidate`

| source | isotropic | deviatoric | iso/dev | dev F_mu | dev F/rho | dev F/rho / legacy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| legacy | n/a | 362.112 | n/a | 11.6735 | 2124.28 | 0.805747 |
| raw | n/a | 14322.6 | n/a | 71.278 | 13548 | 5.13879 |
| bgk | n/a | 14322.6 | n/a | 89.0975 | 16935.2 | 6.42358 |
| post | n/a | 1.76616e+06 | n/a | n/a | n/a | n/a |

## Recommendation

Deviatoric projection does not reduce the force-over-rho shadow below threshold; escalate to B43 stress-scale/forcing derivation.
