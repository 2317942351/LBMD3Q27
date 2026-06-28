# Stage14-B38 First-Bad Force Ledger Digest

This is diagnostic-only. It is not contact-angle validation and not a solver fix.

- Root: `/mnt/usb1t/RUNS/runs/stage14_B40_stress_construction_audit_final_20260628/B40_stress_audit`
- Verdict: `fmu_stress_timelevel_branch`
- Analyzer branch: `stress_timelevel_or_fixed_point_feedback`
- B18 branch: `not_available`
- B40 branch: `post_force_shadow_amplification`

## Selected ForceOverRho Argmax

- Step: `13`
- Mask: `low_rho`
- ijk: `[93, 1, 5]`
- max_abs: `2636.4146763472127`

## Co-Located Values

- `PhaseField`: `0.0005735800909220209`
- `ReplayPhaseFromH`: `0.0005735800909220209`
- `Rho`: `0.005570712190467411`
- `ReplayRhoForForce`: `0.005505073722284272`
- `ReplayForceRhoEffective`: `0.005505073722284272`
- `ReplayTau`: `0.8`
- `ReplayTauUsed`: `0.8`
- `GradPhiNorm`: `0.13667178422416873`
- `FsurfNorm`: `8.358087817285956e-06`
- `FbodyNorm`: `0.0`
- `FmuNorm`: `14.492372866456925`
- `FpressureNorm`: `0.022145923403073742`
- `FmuRawNorm`: `14.492372866456925`
- `FtotalNorm`: `14.513657155803632`
- `ForceOverRhoNorm`: `2636.4146763472127`
- `StressPreForceNorm`: `383.3219828909969`
- `StressPostForceNorm`: `2029121.044003016`
- `StressPostMinusPreNorm`: `2028737.722020125`
- `StressPostOverPreRatio`: `5293.515985437302`

## Interpretation Notes

- ForceOverRho first crosses threshold at step 13.
- ReplayMu and ReplayLapPhi do not lead the failure under current thresholds.
- ReplayGradPhi and Fsurf do not lead the failure under current thresholds.
- At the selected argmax, |Ftotal|=14.5137, |F/rho|=2636.41, rho_eff=0.00550507.
- At the selected argmax, |Fmu|=14.4924, |Fsurf|=8.35809e-06.
- At the selected argmax, |Fmu_raw_before_mode|=14.4924.

## First Onsets

- `first_force_over_rho_onset`: `{'case': 'wall_60to30_10', 'field': 'ForceOverRhoNorm', 'mask': 'low_rho', 'step': 13, 'threshold': 1000.0, 'trigger': 'threshold_force_over_rho_large', 'value': 2636.4146763472127}`
- `first_fmu_onset`: `{'case': 'wall_60to30_10', 'field': 'FmuNorm', 'mask': 'low_rho', 'step': 14, 'threshold': 1000.0, 'trigger': 'threshold_fmu_large', 'value': 64341.717939158065}`
- `first_fmu_raw_onset`: `{'case': 'wall_60to30_10', 'field': 'FmuRawNorm', 'mask': 'low_rho', 'step': 14, 'threshold': 1000.0, 'trigger': 'threshold_fmu_raw_large', 'value': 64341.717939158065}`
- `first_stress_post_onset`: `{'case': 'wall_60to30_10', 'field': 'StressPostForceNorm', 'mask': 'low_rho', 'step': 13, 'threshold': 1000.0, 'trigger': 'threshold_stress_post_large', 'value': 2029121.044003016}`
- `first_b18_stress_post_onset`: `None`
- `first_b18_fmu_post_onset`: `None`
- `first_b18_force_raw_onset`: `None`
- `first_b18_force_floor_onset`: `None`
- `first_b18_force_phase_mix_onset`: `None`
- `first_lap_phi_onset`: `None`
- `first_mu_onset`: `None`
- `first_grad_phi_onset`: `None`
- `first_fsurf_onset`: `None`
- `first_pressure_input_onset`: `None`
- `first_phase_from_h_onset`: `{'case': 'wall_60to30_10', 'field': 'ReplayPhaseFromH', 'mask': 'near_wall', 'step': 20, 'threshold': 1.001, 'trigger': 'threshold_phase_from_h_out_of_bounds', 'value': 1.0058111047359959}`
- `first_hpost_onset`: `None`
- `first_b40_stress_match_delta_onset`: `None`
- `first_b40_stress_moment_raw_onset`: `{'case': 'wall_60to30_10', 'field': 'B40StressMomentRawNorm', 'mask': 'low_rho', 'step': 13, 'threshold': 1000.0, 'trigger': 'threshold_b40_stress_moment_raw_large', 'value': 17562.500913644606}`
- `first_b40_stress_moment_relaxed_onset`: `{'case': 'wall_60to30_10', 'field': 'B40StressMomentRelaxedNorm', 'mask': 'low_rho', 'step': 14, 'threshold': 1000.0, 'trigger': 'threshold_b40_stress_moment_relaxed_large', 'value': 1724171.86862168}`
- `first_b40_stress_incoming_raw_onset`: `{'case': 'wall_60to30_10', 'field': 'B40StressIncomingRawNorm', 'mask': 'low_rho', 'step': 14, 'threshold': 1000.0, 'trigger': 'threshold_b40_stress_incoming_raw_large', 'value': 525010.2617897798}`
- `first_b40_stress_incoming_neq_pre_onset`: `{'case': 'wall_60to30_10', 'field': 'B40StressIncomingNeqPreNorm', 'mask': 'low_rho', 'step': 13, 'threshold': 1000.0, 'trigger': 'threshold_b40_stress_incoming_neq_pre_large', 'value': 17562.500913644602}`
- `first_b40_stress_bgk_pop_neq_pre_onset`: `{'case': 'wall_60to30_10', 'field': 'B40StressBGKPopNeqPreNorm', 'mask': 'low_rho', 'step': 13, 'threshold': 1000.0, 'trigger': 'threshold_b40_stress_bgk_pop_neq_pre_large', 'value': 17562.500913644606}`
- `first_b40_stress_post_onset`: `{'case': 'wall_60to30_10', 'field': 'B40StressPostForceNorm', 'mask': 'low_rho', 'step': 13, 'threshold': 1000.0, 'trigger': 'threshold_b40_stress_post_large', 'value': 2029121.044003016}`
- `first_b40_stress_post_over_relaxed_onset`: `{'case': 'wall_60to30_10', 'field': 'B40StressPostOverRelaxed', 'mask': 'near_interface_wall', 'step': 1, 'threshold': 10.0, 'trigger': 'threshold_b40_stress_post_over_relaxed_large', 'value': 2.7643583244716704e+293}`
- `first_b40_fmu_moment_raw_legacy_onset`: `{'case': 'wall_60to30_10', 'field': 'B40FmuMomentRawLegacyNorm', 'mask': 'low_rho', 'step': 14, 'threshold': 1000.0, 'trigger': 'threshold_b40_fmu_moment_raw_legacy_large', 'value': 474001584.9744175}`
- `first_b40_fmu_moment_relaxed_legacy_onset`: `{'case': 'wall_60to30_10', 'field': 'B40FmuMomentRelaxedLegacyNorm', 'mask': 'low_rho', 'step': 14, 'threshold': 1000.0, 'trigger': 'threshold_b40_fmu_moment_relaxed_legacy_large', 'value': 64341.717939158065}`
- `first_b40_fmu_bgk_pop_neq_pre_bgk_onset`: `{'case': 'wall_60to30_10', 'field': 'B40FmuBGKPopNeqPreBGKNorm', 'mask': 'low_rho', 'step': 14, 'threshold': 1000.0, 'trigger': 'threshold_b40_fmu_bgk_pop_neq_pre_bgk_large', 'value': 592501981.218022}`
- `first_b40_force_moment_raw_legacy_onset`: `{'case': 'wall_60to30_10', 'field': 'B40ForceOverRhoMomentRawLegacyNorm', 'mask': 'low_rho', 'step': 13, 'threshold': 1000.0, 'trigger': 'threshold_b40_force_moment_raw_legacy_large', 'value': 7596.8317022518095}`
- `first_b40_force_moment_relaxed_legacy_onset`: `{'case': 'wall_60to30_10', 'field': 'B40ForceOverRhoMomentRelaxedLegacyNorm', 'mask': 'low_rho', 'step': 13, 'threshold': 1000.0, 'trigger': 'threshold_b40_force_moment_relaxed_legacy_large', 'value': 2636.4146763472127}`
- `first_b40_force_bgk_pop_neq_pre_bgk_onset`: `{'case': 'wall_60to30_10', 'field': 'B40ForceOverRhoBGKPopNeqPreBGKNorm', 'mask': 'low_rho', 'step': 13, 'threshold': 1000.0, 'trigger': 'threshold_b40_force_bgk_pop_neq_pre_bgk_large', 'value': 9495.989154937075}`
