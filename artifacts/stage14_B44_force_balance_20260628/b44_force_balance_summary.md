# Stage14-B44 Force Balance Gate

Status: post-processing diagnostic only. No TCLB solver path is changed.

Root: `/mnt/usb1t/RUNS/runs/stage14_B44_force_balance_20260628/B44_force_balance`
Focus step: `13`
Legacy low-rho max F/rho: `2636.41`
Verdict: `b44_force_balance_candidate_found`

| mask | candidate | max F/rho | p99 F/rho | net/term | F_mu fraction | argmax rho_eff | note |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| fluid_all | zero | 4.05651 | 0.000814852 | 0.996711 | 0 | 0.00545097 | sanity check only; not physical |
| fluid_all | legacy_hundredth | 30.2118 | 0.00417036 | 0.946349 | 0.766562 | 0.00550507 | diagnostic magnitude sweep |
| fluid_all | legacy_tenth | 267.123 | 0.0381393 | 0.932954 | 0.970447 | 0.00550507 | diagnostic magnitude sweep |
| fluid_all | negative_legacy | 2628.68 | 0.376134 | 0.92516 | 0.996964 | 0.00550507 | sign check |
| fluid_all | legacy | 2636.41 | 0.377074 | 0.931212 | 0.996964 | 0.00550507 | current active scale |
| fluid_all | no_density_diff | 2649.64 | 0.378966 | 0.931211 | 0.996979 | 0.00550507 | remove density-difference multiplier |
| fluid_all | bgk_style | 3286.82 | 0.470285 | 0.926328 | 0.99757 | 0.00550507 | opposite sign of B40FmuBGKScale |
| fluid_all | bgk_legacy_sign | 3294.55 | 0.471224 | 0.931172 | 0.99757 | 0.00550507 | B40FmuBGKScale |
| interface_wide | zero | 0.000321994 | 0.000257091 | 0.329752 | 0 | 0.0555999 | sanity check only; not physical |
| interface_wide | legacy_hundredth | 0.000363425 | 0.000262548 | 0.332998 | 0.00953779 | 0.0555999 | diagnostic magnitude sweep |
| interface_wide | legacy_tenth | 0.000864045 | 0.000327019 | 0.359638 | 0.0878379 | 0.0555999 | diagnostic magnitude sweep |
| interface_wide | negative_legacy | 0.00612717 | 0.000901587 | 0.160686 | 0.490566 | 0.0555999 | sign check |
| interface_wide | legacy | 0.00651339 | 0.00121445 | 0.49666 | 0.490566 | 0.0555999 | current active scale |
| interface_wide | no_density_diff | 0.0065451 | 0.00121959 | 0.497086 | 0.491819 | 0.0555999 | remove density-difference multiplier |
| interface_wide | bgk_style | 0.00770482 | 0.00115575 | 0.216324 | 0.546219 | 0.0555999 | opposite sign of B40FmuBGKScale |
| interface_wide | bgk_legacy_sign | 0.00809115 | 0.00147081 | 0.515595 | 0.546219 | 0.0555999 | B40FmuBGKScale |
| low_rho | zero | 4.05651 | 0.000836959 | 0.997461 | 0 | 0.00545097 | sanity check only; not physical |
| low_rho | legacy_hundredth | 30.2118 | 0.00470978 | 0.94652 | 0.766663 | 0.00550507 | diagnostic magnitude sweep |
| low_rho | legacy_tenth | 267.123 | 0.0489633 | 0.932978 | 0.970463 | 0.00550507 | diagnostic magnitude sweep |
| low_rho | negative_legacy | 2628.68 | 0.491917 | 0.925164 | 0.996966 | 0.00550507 | sign check |
| low_rho | legacy | 2636.41 | 0.491501 | 0.931217 | 0.996966 | 0.00550507 | current active scale |
| low_rho | no_density_diff | 2649.64 | 0.493972 | 0.931216 | 0.996981 | 0.00550507 | remove density-difference multiplier |
| low_rho | bgk_style | 3286.82 | 0.614844 | 0.926332 | 0.997571 | 0.00550507 | opposite sign of B40FmuBGKScale |
| low_rho | bgk_legacy_sign | 3294.55 | 0.614429 | 0.931177 | 0.997571 | 0.00550507 | B40FmuBGKScale |

## Interpretation

A low net/term ratio alone is not a pass: local F/rho spikes can still destabilize h even when the global force nearly cancels.
A non-zero candidate must reduce local low-rho F/rho below threshold before it can move to an active default-off solver branch.
