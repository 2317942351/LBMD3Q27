# Stage14-B38 First-Bad Force Ledger Digest

This is diagnostic-only. It is not contact-angle validation and not a solver fix.

- Root: `/mnt/usb1t/RUNS/runs/stage14_B38_first_bad_force_ledger_retry_20260628/L0_b33ledger_b18`
- Verdict: `fmu_stress_timelevel_branch`
- Analyzer branch: `fmu_force_over_rho_feedback`
- B18 branch: `stress_amplification_shadow`

## Selected ForceOverRho Argmax

- Step: `15`
- Mask: `low_rho`
- ijk: `[14, 1, 14]`
- max_abs: `885434.9865443383`

## Co-Located Values

- `PhaseField`: `9.056482555393055e-09`
- `ReplayPhaseFromH`: `9.056482555393055e-09`
- `ReplayPhaseConsumed`: `4.534355803792498e-09`
- `Rho`: `0.005000009011200143`
- `ReplayRho`: `0.005000004511684025`
- `ReplayRhoForForce`: `0.005000004511684025`
- `ReplayForceRhoRaw`: `0.005000004511684025`
- `ReplayForceRhoEffective`: `0.005000004511684025`
- `ReplayTau`: `0.8`
- `ReplayTauUsed`: `0.8`
- `ReplayLapPhi`: `0.2679492750756162`
- `ReplayMu`: `-6.0288585078271357e-05`
- `GradPhiNorm`: `0.13397463687642877`
- `FsurfNorm`: `8.077141293655088e-06`
- `FbodyNorm`: `0.0`
- `FmuNorm`: `4427.203279090591`
- `FpressureNorm`: `0.02434348887518085`
- `FpressurePhysicalNorm`: `0.02434348887518085`
- `FmuRawNorm`: `11.380036184253331`
- `FmuDeltaNorm`: `0.0`
- `FtotalNorm`: `4427.178927524575`
- `ForceOverRhoNorm`: `885434.9865443383`
- `StressInputNorm`: `287.5235665519975`
- `StressIter1Norm`: `287.5235665519975`
- `StressPreForceNorm`: `287.5235665519975`
- `StressPostForceNorm`: `230174915351.82053`
- `StressPostMinusPreNorm`: `230174915064.29697`
- `StressPostOverPreRatio`: `800542780.2391785`
- `B18ProbeActive`: `1.0`
- `B18StressPreForceNorm`: `287.5235665519975`
- `B18StressPostForceNorm`: `230174915351.82053`
- `B18StressPostMinusPreNorm`: `230174915064.29697`
- `B18StressPostOverPre`: `800542780.2391785`
- `B18StressAmplificationFlag`: `1.0`
- `B18FmuPreForceNorm`: `11.380036184253331`
- `B18FmuPostForceNorm`: `9158415794.71234`
- `B18FmuForceExcludedNorm`: `7850070681.228793`
- `B18FmuCandidateDeltaNorm`: `9158415806.092375`
- `B18ForceOverRhoRawNorm`: `885434.9865443382`
- `B18ForceOverRhoDensityFloorNorm`: `885434.9865443382`
- `B18ForceOverRhoPhaseMixtureNorm`: `885434.9865443382`
- `B18RhoDenominatorRaw`: `0.005000004511684025`
- `B18RhoDenominatorFloor`: `0.005000004511684025`
- `B18RhoDenominatorPhaseMix`: `0.005000004511684025`
- `ReplayM0`: `[0.00027812787303105324, -333.09934000972197, 0.000278127872756162]`
- `ReplayVelocityHalfForce`: `[0.37097956271771626, -443050.59261186846, 0.3709795623432745]`
- `ReplayMF`: `[0.7414028696893704, -885434.9865437174, 0.7414028689410367]`
- `ReplayMomentumAfterG`: `[0.7419204711914062, -885768.0858001709, 0.7416839599609375]`
- `ReplayMomentumDeltaG`: `[0.7416423433183752, -885434.9864601612, 0.7414058320881813]`
- `UPreForceNorm`: `333.09934000995423`
- `UPostForceNorm`: `443050.5926121791`
- `PhaseAdvVelocityNorm`: `0.2`
- `ReplayHPreMaxAbs`: `9.174151850694042e-10`
- `ReplayHPostMaxAbs`: `1.0369717249003207e-09`
- `ReplayHeqMaxAbs`: `1.2629020609081326e-09`
- `ReplayTmp1`: `6.045807678905471e-09`
- `ReplayFphiMaxAbs`: `4.4783760584484827e-10`

## Interpretation Notes

- ForceOverRho first crosses threshold at step 15.
- PhaseFromH does not cross the configured out-of-bounds threshold before the force ledger failure.
- ReplayMu and ReplayLapPhi do not lead the failure under current thresholds.
- ReplayGradPhi and Fsurf do not lead the failure under current thresholds.
- At the selected argmax, |Ftotal|=4427.18, |F/rho|=885435, rho_eff=0.005.
- At the selected argmax, |Fmu|=4427.2, |Fsurf|=8.07714e-06.
- At the selected argmax, |Fmu_raw_before_mode|=11.38.
- B18 stress shadow at argmax: pre=287.524, post=2.30175e+11, post/pre=800542780.2391785.

## First Onsets

- `first_force_over_rho_onset`: `{'case': 'wall_60to30_10', 'field': 'ForceOverRhoNorm', 'mask': 'low_rho', 'step': 15, 'threshold': 1000.0, 'trigger': 'threshold_force_over_rho_large', 'value': 885434.9865443383}`
- `first_fmu_onset`: `{'case': 'wall_60to30_10', 'field': 'FmuNorm', 'mask': 'low_rho', 'step': 15, 'threshold': 1000.0, 'trigger': 'threshold_fmu_large', 'value': 4427.203279090591}`
- `first_fmu_raw_onset`: `{'case': 'wall_60to30_10', 'field': 'FmuRawNorm', 'mask': 'near_interface_wall', 'step': 16, 'threshold': 1000.0, 'trigger': 'threshold_fmu_raw_large', 'value': 6535.948743877294}`
- `first_stress_post_onset`: `{'case': 'wall_60to30_10', 'field': 'StressPostForceNorm', 'mask': 'low_rho', 'step': 14, 'threshold': 1000.0, 'trigger': 'threshold_stress_post_large', 'value': 2250.338818100119}`
- `first_b18_stress_post_onset`: `{'case': 'wall_60to30_10', 'field': 'B18StressPostForceNorm', 'mask': 'low_rho', 'step': 14, 'threshold': 1000.0, 'trigger': 'threshold_b18_stress_post_large', 'value': 2250.338818100119}`
- `first_b18_fmu_post_onset`: `{'case': 'wall_60to30_10', 'field': 'B18FmuPostForceNorm', 'mask': 'low_rho', 'step': 15, 'threshold': 1000.0, 'trigger': 'threshold_b18_fmu_post_large', 'value': 9158415794.71234}`
- `first_b18_force_raw_onset`: `{'case': 'wall_60to30_10', 'field': 'B18ForceOverRhoRawNorm', 'mask': 'low_rho', 'step': 15, 'threshold': 1000.0, 'trigger': 'threshold_b18_force_raw_large', 'value': 885434.9865443382}`
- `first_b18_force_floor_onset`: `{'case': 'wall_60to30_10', 'field': 'B18ForceOverRhoDensityFloorNorm', 'mask': 'low_rho', 'step': 15, 'threshold': 1000.0, 'trigger': 'threshold_b18_force_floor_large', 'value': 885434.9865443382}`
- `first_b18_force_phase_mix_onset`: `{'case': 'wall_60to30_10', 'field': 'B18ForceOverRhoPhaseMixtureNorm', 'mask': 'low_rho', 'step': 15, 'threshold': 1000.0, 'trigger': 'threshold_b18_force_phase_mix_large', 'value': 885434.9865443382}`
- `first_lap_phi_onset`: `None`
- `first_mu_onset`: `None`
- `first_grad_phi_onset`: `None`
- `first_fsurf_onset`: `None`
- `first_pressure_input_onset`: `{'case': 'wall_60to30_10', 'field': 'ReplayPressureInput', 'mask': 'near_interface_wall', 'step': 16, 'threshold': 1000.0, 'trigger': 'threshold_pressure_input_large', 'value': 1210.1179737746318}`
- `first_phase_from_h_onset`: `None`
- `first_hpost_onset`: `None`
