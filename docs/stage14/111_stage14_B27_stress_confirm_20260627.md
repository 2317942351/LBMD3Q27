# Stage14-B27 Stress Confirmation

Date: 2026-06-27

Branch: `work/phasefield-c-reference-20260623`

Status: diagnostic evidence, not contact-angle validation.

## Runtime Evidence

Remote run root:

```text
/mnt/usb1t/RUNS/runs/stage14_B27_stress_confirm_v6_20260627
```

Local light artifact mirror:

```text
artifacts/stage14_B27_stress_confirm_v6_20260627/
```

Binary:

```text
/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
sha256 = 2a5729a8041dcd3db150149b623764862778d799cd657b55ab43fc2cab47cef6
```

All B27 driver and analyzer jobs finished with `RC=0`; `stage14_B27.status`
contains `OVERALL_RC=0`.

## Probe Matrix

All probes used:

```text
case = wall_60to30_10
Density_h = 1.0
Density_l = 0.005
PressureClosureMode = 1
ForceFixedPointMode = 2
PhaseAdvectionVelocityMode = 1
vtk_field_set = b27stress
```

| Probe | Change | Key result |
|---|---|---|
| `S0_legacy_stress` | legacy force split | force/velocity/phase thresholds fire at steps 11-14 |
| `S1_density_floor_stress` | force denominator floor | indistinguishable from S0; denominator floor is not first priority |
| `S2_noFmu_stress` | omit `F_mu` by diagnostic switch | downstream `B21/B22/phase` thresholds disappear |
| `S3_noSurf_stress` | omit `F_surf` by diagnostic switch | all configured thresholds disappear |
| `S4_noMomentum_stress` | no momentum force | all configured thresholds disappear |

S0 representative onsets:

```text
B22MomentumSpeed > 1: step 11, value 2.8205
B21HeqVelocityMachShadow > 1: step 12, value 3.3317
B22ForceOverRhoMag: step 13, value 2092.38
PhaseFromH: step 13, value 2.7912
B22FmuMag: step 14, value 100723.55
B22FpressureMag: step 14, value 94703.74
```

S2 keeps only the early `B18StressPostOverPre` ratio trigger. That ratio is
not enough by itself to produce the observed downstream instability when
`F_mu` is removed from `F_total`.

## Interpretation

B27 narrows the active chain to:

```text
F_surf = mu * gradPhi
  -> stress/F_mu coupling
  -> F_total/rho
  -> phase-advection velocity and h update
  -> PhaseFromH leaves the physical interval
```

The result does not support promoting `MomentumForceMode=1` as a fix. That
switch simply removes `F_mu` and is diagnostic only.

The density-floor branch is deprioritized because `S1` did not shift the onset
relative to `S0`.

The next candidate must keep `F_surf` present while changing only the `F_mu`
stress closure in a controlled, default-off mode.

## Next Step

Proceed to B28:

```text
FmuStressClosureMode = 0 legacy
FmuStressClosureMode = 1 freeze first-pass F_mu in multi-pass loops
FmuStressClosureMode = 2 incoming non-equilibrium stress from pre-force m0
```

The B28 claim limit is:

```text
candidate mode removes or delays the B27-confirmed short-onset mechanism
```

No contact-angle or dynamic-impact readiness claim is allowed.
