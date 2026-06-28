# Stage14-B38 First-Bad Force Ledger Result

Date: 2026-06-28

Branch: `work/phasefield-c-reference-20260623`

Status: diagnostic complete. Not a contact-angle validation. Not a solver fix.

## Runtime

Final evidence root:

```text
/mnt/usb1t/RUNS/runs/stage14_B38_first_bad_force_ledger_retry_20260628
```

Local artifact root:

```text
artifacts/stage14_B38_first_bad_force_ledger_retry_20260628
```

Binary:

```text
3f3e79b5f234136b515094c6dba6e2e2237e3bdbde8a31dcba1f65c37d0ce78e
```

Run status:

```text
OVERALL_RC=0
VERDICT=b38_first_bad_ledger_complete
```

## Case And Settings

```text
case = wall_60to30_10
Density_h = 1.0
Density_l = 0.005
iterations = 20
vtk_period = 1
vtk_field_set = b33ledger
ReplayDiagnosticsMode = 1
MomentumClosureDiagnosticsMode = 1
Stage14B18ClosureDiagnosticsMode = 1
MomentumClosureProbeMode = 1
PressureClosureMode = 1
ForceDensityClosureMode = 2
ForceDensityRhoFloor = 0.005
ForceFixedPointMode = 2
PhaseAdvectionVelocityMode = 2
FmuStressClosureMode = 2
```

## Main Finding

B38 identifies the next branch as:

```text
fmu_stress_timelevel_branch
```

The analyzer branch is:

```text
fmu_force_over_rho_feedback
```

The B18 shadow branch is:

```text
stress_amplification_shadow
```

This means the next work should not return to contact-angle tuning, curved-wall
wetting, `mu/lapPhi`, or `gradPhi` caps. The first short-run failure is now
localized to the stress/F_mu path under the current momentum closure settings.

## First-Bad Evidence

Selected argmax:

```text
step = 15
mask = low_rho
ijk = [14, 1, 14]
PhaseField = 9.056482555393055e-09
ReplayRhoForForce = 0.005000004511684025
```

Co-located values:

```text
ForceOverRhoNorm = 885434.9865443383
FtotalNorm = 4427.178927524575
FmuNorm = 4427.203279090591
FmuRawNorm = 11.380036184253331
FsurfNorm = 8.077141293655088e-06
FpressureNorm = 0.02434348887518085
FbodyNorm = 0.0
ReplayMu = -6.0288585078271357e-05
ReplayLapPhi = 0.2679492750756162
GradPhiNorm = 0.13397463687642877
```

Interpretation:

```text
Actual F_mu almost exactly equals F_total.
F_surf, pressure, body force, mu, lapPhi, and gradPhi are not the leading terms.
FmuRawNorm is small, but actual FmuNorm is large because FmuStressClosureMode=2
replaces the raw relaxed-stress F_mu with the incoming nonequilibrium candidate.
```

Stress shadow:

```text
StressPreForceNorm = 287.5235665519975
StressPostForceNorm = 230174915351.82053
StressPostOverPreRatio = 800542780.2391785
B18FmuPreForceNorm = 11.380036184253331
B18FmuPostForceNorm = 9158415794.71234
B18FmuForceExcludedNorm = 7850070681.228793
```

The post-force stress shadow is catastrophically amplified. It is not the
actual current write path, but it proves that using post-force/post-collision
stress in this chain is numerically invalid at the first-bad low-rho cell.

## First Onsets

```text
first_b18_stress_post_onset: step 14, value 2250.338818100119
first_stress_post_onset: step 14, value 2250.338818100119
first_force_over_rho_onset: step 15, value 885434.9865443383
first_fmu_onset: step 15, value 4427.203279090591
first_b18_fmu_post_onset: step 15, value 9158415794.71234
first_fmu_raw_onset: step 16, value 6535.948743877294
first_pressure_input_onset: step 16, value 1210.1179737746318
first_mu_onset: none
first_lap_phi_onset: none
first_grad_phi_onset: none
first_fsurf_onset: none
first_phase_from_h_onset: none
```

## Code Anchors

In `Dynamics.c.Rt`:

```text
stage14_b28_incoming_neq_active()
FmuStressClosureMode
stage14_fmu_from_stress(...)
F_mu raw from relaxed stress
F_mu replacement from b28_stress_incoming_neq when FmuStressClosureMode=2
F_total = F_surf + F_pressure + F_body + F_mu
ReplayForceOverRho = F_total / force_rho_eff
```

The suspicious branch is:

```text
FmuStressClosureMode = 2
  -> b18_stress_incoming from streamed g
  -> b28_stress_incoming_neq = b18_stress_incoming - preforce equilibrium stress
  -> stage14_fmu_from_stress(b28_stress_incoming_neq, gradPhi_force, tau)
  -> actual F_mu
```

## Decision

B38 rejects the idea that B39 should tune:

```text
WallGhost
compact-stencil wetting
contact-angle parameters
pressure removal
ForceOverRho cap
GradPhi cap
mu/lapPhi stencil
```

B39 should instead test a single default-off stress/F_mu closure branch. The
minimum matrix should compare:

```text
FmuStressClosureMode = 0 legacy relaxed stress
FmuStressClosureMode = 1 freeze iter1 F_mu
FmuStressClosureMode = 2 incoming nonequilibrium stress
```

If mode 0 or mode 1 removes the step-15 `F_mu/ForceOverRho` onset without
breaking momentum replay, B39 can promote that mode as the next candidate for
B40 short stability. If all modes fail, B39 must inspect the construction of
`b28_stress_incoming_neq` and the equilibrium stress subtraction in TCLB moment
space before adding another limiter.
