# Stage14-B38 First-Bad Force Ledger Digest

This is diagnostic-only. It is not contact-angle validation and not a solver fix.

- Root: `C:\Users\yuanz\Desktop\lbm-new\repo\artifacts\stage14_B39_fmu_stress_mode_matrix_20260628\M1_freeze_iter1`
- Verdict: `fmu_stress_timelevel_branch`
- Analyzer branch: `stress_timelevel_or_fixed_point_feedback`
- B18 branch: `stress_amplification_shadow`

## Selected ForceOverRho Argmax

- Step: `13`
- Mask: `low_rho`
- ijk: `[93, 1, 5]`
- max_abs: `2636.4146763472127`

## Co-Located Values

- `PhaseField`: `0.0005735800909220209`
- `ReplayPhaseFromH`: `0.0005735800909220209`
- `ReplayPhaseConsumed`: `0.0005076117811902231`
- `Rho`: `0.005570712190467411`
- `ReplayRho`: `0.005505073722284272`
- `ReplayRhoForForce`: `0.005505073722284272`
- `ReplayForceRhoRaw`: `0.005505073722284272`
- `ReplayForceRhoEffective`: `0.005505073722284272`
- `ReplayTau`: `0.8`
- `ReplayTauUsed`: `0.8`
- `ReplayLapPhi`: `0.2726986034593614`
- `ReplayMu`: `-6.115445016490777e-05`
- `GradPhiNorm`: `0.13667178422416873`
- `FsurfNorm`: `8.358087817285956e-06`
- `FbodyNorm`: `0.0`
- `FmuNorm`: `14.492372866456925`
- `FpressureNorm`: `0.022145923403073742`
- `FpressurePhysicalNorm`: `0.022145923403073742`
- `FmuRawNorm`: `14.492372866456925`
- `FmuDeltaNorm`: `0.0`
- `FtotalNorm`: `14.513657155803632`
- `ForceOverRhoNorm`: `2636.4146763472127`
- `StressInputNorm`: `383.3219828909969`
- `StressIter1Norm`: `383.3219828909969`
- `StressPreForceNorm`: `383.3219828909969`
- `StressPostForceNorm`: `2029121.044003016`
- `StressPostMinusPreNorm`: `2028737.722020125`
- `StressPostOverPreRatio`: `5293.515985437302`
- `B18ProbeActive`: `1.0`
- `B18StressPreForceNorm`: `383.3219828909969`
- `B18StressPostForceNorm`: `2029121.044003016`
- `B18StressPostMinusPreNorm`: `2028737.722020125`
- `B18StressPostOverPre`: `5293.515985437302`
- `B18StressAmplificationFlag`: `1.0`
- `B18FmuPreForceNorm`: `14.492372866456925`
- `B18FmuPostForceNorm`: `78936.10366794969`
- `B18FmuForceExcludedNorm`: `67643.86807411582`
- `B18FmuCandidateDeltaNorm`: `78921.6203419358`
- `B18ForceOverRhoRawNorm`: `2636.414676347212`
- `B18ForceOverRhoDensityFloorNorm`: `2636.414676347212`
- `B18ForceOverRhoPhaseMixtureNorm`: `2636.414676347212`
- `B18RhoDenominatorRaw`: `0.005505073722284272`
- `B18RhoDenominatorFloor`: `0.005505073722284272`
- `B18RhoDenominatorPhaseMix`: `0.005505073722284272`
- `ReplayM0`: `[-12.05641679289414, 6.959865578304051, 18.408717443052815]`
- `ReplayVelocityHalfForce`: `[-375.1004091412089, -1259.8500151163196, 51.00276918588525]`
- `ReplayMF`: `[-726.0879846966295, -2533.6197613892473, 65.18810348566487]`
- `ReplayMomentumAfterG`: `[-738.1444014870794, -2526.6598958094837, 83.59682092865114]`
- `ReplayMomentumDeltaG`: `[-726.0879846941853, -2533.6197613877875, 65.18810348559833]`
- `UPreForceNorm`: `23.079813531530068`
- `UPostForceNorm`: `1315.493694394284`
- `PhaseAdvVelocityNorm`: `0.2`
- `ReplayHPreMaxAbs`: `0.0001229790100148458`
- `ReplayHPostMaxAbs`: `0.00013612206091827547`
- `ReplayHeqMaxAbs`: `0.00014137928127964732`
- `ReplayTmp1`: `0.0006764721486264526`
- `ReplayFphiMaxAbs`: `5.010878687918643e-05`

## Interpretation Notes

- ForceOverRho first crosses threshold at step 13.
- ReplayMu and ReplayLapPhi do not lead the failure under current thresholds.
- ReplayGradPhi and Fsurf do not lead the failure under current thresholds.
- At the selected argmax, |Ftotal|=14.5137, |F/rho|=2636.41, rho_eff=0.00550507.
- At the selected argmax, |Fmu|=14.4924, |Fsurf|=8.35809e-06.
- At the selected argmax, |Fmu_raw_before_mode|=14.4924.
- B18 stress shadow at argmax: pre=383.322, post=2.02912e+06, post/pre=5293.515985437302.

## First Onsets

- `first_force_over_rho_onset`: `{'case': 'wall_60to30_10', 'field': 'ForceOverRhoNorm', 'mask': 'low_rho', 'step': 13, 'threshold': 1000.0, 'trigger': 'threshold_force_over_rho_large', 'value': 2636.4146763472127}`
- `first_fmu_onset`: `{'case': 'wall_60to30_10', 'field': 'FmuNorm', 'mask': 'low_rho', 'step': 14, 'threshold': 1000.0, 'trigger': 'threshold_fmu_large', 'value': 64341.717939158065}`
- `first_fmu_raw_onset`: `{'case': 'wall_60to30_10', 'field': 'FmuRawNorm', 'mask': 'low_rho', 'step': 14, 'threshold': 1000.0, 'trigger': 'threshold_fmu_raw_large', 'value': 64341.717939158065}`
- `first_stress_post_onset`: `{'case': 'wall_60to30_10', 'field': 'StressPostForceNorm', 'mask': 'low_rho', 'step': 13, 'threshold': 1000.0, 'trigger': 'threshold_stress_post_large', 'value': 2029121.044003016}`
- `first_b18_stress_post_onset`: `{'case': 'wall_60to30_10', 'field': 'B18StressPostForceNorm', 'mask': 'low_rho', 'step': 13, 'threshold': 1000.0, 'trigger': 'threshold_b18_stress_post_large', 'value': 2029121.044003016}`
- `first_b18_fmu_post_onset`: `{'case': 'wall_60to30_10', 'field': 'B18FmuPostForceNorm', 'mask': 'low_rho', 'step': 13, 'threshold': 1000.0, 'trigger': 'threshold_b18_fmu_post_large', 'value': 78936.10366794969}`
- `first_b18_force_raw_onset`: `{'case': 'wall_60to30_10', 'field': 'B18ForceOverRhoRawNorm', 'mask': 'low_rho', 'step': 13, 'threshold': 1000.0, 'trigger': 'threshold_b18_force_raw_large', 'value': 2636.414676347212}`
- `first_b18_force_floor_onset`: `{'case': 'wall_60to30_10', 'field': 'B18ForceOverRhoDensityFloorNorm', 'mask': 'low_rho', 'step': 13, 'threshold': 1000.0, 'trigger': 'threshold_b18_force_floor_large', 'value': 2636.414676347212}`
- `first_b18_force_phase_mix_onset`: `{'case': 'wall_60to30_10', 'field': 'B18ForceOverRhoPhaseMixtureNorm', 'mask': 'low_rho', 'step': 13, 'threshold': 1000.0, 'trigger': 'threshold_b18_force_phase_mix_large', 'value': 2636.414676347212}`
- `first_lap_phi_onset`: `None`
- `first_mu_onset`: `None`
- `first_grad_phi_onset`: `None`
- `first_fsurf_onset`: `None`
- `first_pressure_input_onset`: `{'case': 'wall_60to30_10', 'field': 'ReplayPressureInput', 'mask': 'low_rho', 'step': 14, 'threshold': 1000.0, 'trigger': 'threshold_pressure_input_large', 'value': 1948.2675345866123}`
- `first_phase_from_h_onset`: `{'case': 'wall_60to30_10', 'field': 'ReplayPhaseFromH', 'mask': 'near_wall', 'step': 20, 'threshold': 1.001, 'trigger': 'threshold_phase_from_h_out_of_bounds', 'value': 1.0058111047359957}`
- `first_hpost_onset`: `None`
