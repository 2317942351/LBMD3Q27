# Stage14-B28 F_mu Stress Candidate Result

Date: 2026-06-27

Branch: `work/phasefield-c-reference-20260623`

Status: diagnostic candidate result. This is not contact-angle validation.

## Build

Compile lane:

```text
/home/yuan/src/TCLB_lbm2026_compile_lane
```

Full RT regeneration and CUDA build completed:

```text
BUILD_RC=0
binary_sha256 = 7ebe7053bdcb4a88468f58b9f4f0bd30e189fd589709c9849e357c4d0fedd74f
```

The compile guard checked that `FmuStressClosureMode` and
`ReplayFmuStressClosureMode` reached generated CUDA/source accessors.

## Runtime

Remote root:

```text
/mnt/usb1t/RUNS/runs/stage14_B28_fmu_stress_candidate_20260627
```

Local light artifacts:

```text
artifacts/stage14_B28_fmu_stress_candidate_20260627/
```

All driver/analyzer jobs finished with `RC=0`; `stage14_B28.status` contains
`OVERALL_RC=0`.

## Matrix Result

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

| Probe | `FmuStressClosureMode` | `MomentumForceMode` | Result |
|---|---:|---:|---|
| `C0_legacy_fmu_stress` | 0 | 0 | reproduces B27 failure |
| `C1_freeze_iter1_fmu_stress` | 1 | 0 | identical to legacy under single-pass force mode |
| `C2_incoming_neq_fmu_stress` | 2 | 0 | removes force/rho, F_mu, pressure, and phase thresholds in 14-step window |
| `C9_noFmu_reference` | 0 | 1 | removes all configured downstream thresholds, diagnostic reference only |

Key onset comparison:

| Probe | momentum step | heq Mach step | phase step | force/rho step | F_mu step | pressure step |
|---|---:|---:|---:|---:|---:|---:|
| C0 legacy | 11 | 12 | 13 | 13 | 14 | 14 |
| C1 freeze iter1 | 11 | 12 | 13 | 13 | 14 | 14 |
| C2 incoming neq | 12 | 13 | none | none | none | none |
| C9 noFmu | none | none | none | none | none | none |

## Interpretation

Mode 1 did not change behavior because B28/B27 use
`ForceFixedPointMode=2`, which intentionally makes the force loop single-pass.
It is therefore not a useful candidate for the current failure.

Mode 2 is the first candidate that keeps the surface-force path active while
removing the short-window force and phase blow-up. It does not make the solver
validated: the momentum and h-equilibrium Mach diagnostics still cross
thresholds at steps 12-13.

The strongest allowed statement is:

```text
FmuStressClosureMode=2 interrupts the B27 force/rho -> phase blow-up chain in
the 14-step diagnostic window, but leaves a velocity/Mach concern unresolved.
```

## Next Gate

Run B29 with:

```text
FmuStressClosureMode=2
wall_60to30_10
Density_l=0.005
20 steps, then 100 steps only if 20-step gate is usable
```

B29 is short stability only. It does not authorize flat-wall contact-angle
validation, curved-wall validation, or dynamic impact.
