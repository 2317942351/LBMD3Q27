# Stage14-B43 Postprocess F_mu Scale Probe

Status: post-processing diagnostic. No TCLB field or active solver path is changed.

Root: `/mnt/usb1t/RUNS/runs/stage14_B43_scale_probe_focus13_20260628/B43_scale_probe`
Focus step: `13`
Legacy low-rho F/rho: `2636.41`
Verdict: `b43_postprocess_scale_candidate_strong`

| mask | candidate | physical | scale | F_mu | F/rho | F/rho / legacy | note |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| fluid_all | zero | no | 0 | 0 | 4.05651 | 0.00153865 | sanity check only; not a physical closure |
| fluid_all | legacy_hundredth | yes | 0.002985 | 0.144924 | 30.2118 | 0.0114594 | diagnostic magnitude sweep |
| fluid_all | legacy_tenth | yes | 0.02985 | 1.44924 | 267.123 | 0.101321 | diagnostic magnitude sweep |
| fluid_all | negative_legacy | yes | 0.2985 | 14.4924 | 2628.68 | 0.997067 | sign check |
| fluid_all | legacy | yes | 0.2985 | 14.4924 | 2636.41 | 1 | current active scale |
| fluid_all | no_density_diff | yes | 0.3 | 14.5652 | 2649.64 | 1.00502 | remove density-difference multiplier |
| fluid_all | bgk_style | yes | 0.373125 | 18.1155 | 3286.82 | 1.2467 | opposite sign of existing stage14_fmu_bgk_scale |
| fluid_all | bgk_legacy_sign | yes | 0.373125 | 18.1155 | 3294.55 | 1.24963 | existing stage14_fmu_bgk_scale: (0.5-tau)/tau |
| interface_wide | zero | no | 0 | 0 | 0.000321994 | 1.22133e-07 | sanity check only; not a physical closure |
| interface_wide | legacy_hundredth | yes | 0.002985 | 3.51115e-06 | 0.000363425 | 1.37848e-07 | diagnostic magnitude sweep |
| interface_wide | legacy_tenth | yes | 0.02985 | 3.51115e-05 | 0.000864045 | 3.27735e-07 | diagnostic magnitude sweep |
| interface_wide | negative_legacy | yes | 0.2985 | 0.000351115 | 0.00612717 | 2.32406e-06 | sign check |
| interface_wide | legacy | yes | 0.2985 | 0.000351115 | 0.00651339 | 2.47055e-06 | current active scale |
| interface_wide | no_density_diff | yes | 0.3 | 0.000352879 | 0.0065451 | 2.48257e-06 | remove density-difference multiplier |
| interface_wide | bgk_style | yes | 0.373125 | 0.000438894 | 0.00770482 | 2.92246e-06 | opposite sign of existing stage14_fmu_bgk_scale |
| interface_wide | bgk_legacy_sign | yes | 0.373125 | 0.000438894 | 0.00809115 | 3.069e-06 | existing stage14_fmu_bgk_scale: (0.5-tau)/tau |
| low_rho | zero | no | 0 | 0 | 4.05651 | 0.00153865 | sanity check only; not a physical closure |
| low_rho | legacy_hundredth | yes | 0.002985 | 0.144924 | 30.2118 | 0.0114594 | diagnostic magnitude sweep |
| low_rho | legacy_tenth | yes | 0.02985 | 1.44924 | 267.123 | 0.101321 | diagnostic magnitude sweep |
| low_rho | negative_legacy | yes | 0.2985 | 14.4924 | 2628.68 | 0.997067 | sign check |
| low_rho | legacy | yes | 0.2985 | 14.4924 | 2636.41 | 1 | current active scale |
| low_rho | no_density_diff | yes | 0.3 | 14.5652 | 2649.64 | 1.00502 | remove density-difference multiplier |
| low_rho | bgk_style | yes | 0.373125 | 18.1155 | 3286.82 | 1.2467 | opposite sign of existing stage14_fmu_bgk_scale |
| low_rho | bgk_legacy_sign | yes | 0.373125 | 18.1155 | 3294.55 | 1.24963 | existing stage14_fmu_bgk_scale: (0.5-tau)/tau |

## Interpretation

`zero` is a sanity check only. A passable physical candidate must be non-zero and later justified by force-balance and benchmark gates.
