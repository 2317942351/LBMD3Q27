# Stage14-B39 Fmu Stress Mode Matrix Result

Date: 2026-06-28

Branch: `work/phasefield-c-reference-20260623`

Status: diagnostic complete. Existing `FmuStressClosureMode` choices are
rejected as a sufficient repair.

## Runtime

Remote root:

```text
/mnt/usb1t/RUNS/runs/stage14_B39_fmu_stress_mode_matrix_20260628
```

Local artifact root:

```text
artifacts/stage14_B39_fmu_stress_mode_matrix_20260628
```

Binary:

```text
3f3e79b5f234136b515094c6dba6e2e2237e3bdbde8a31dcba1f65c37d0ce78e
```

Important note:

```text
GPU runs and analyzers completed for all three modes:
  DRIVER_RC=0
  ANALYZER_RC=0

The remote OVERALL_RC=3 was caused by a postprocess prefix bug:
  b38 digest expected b38_key_summary.json while B39 produced b39_key_summary.json.

The prefix bug was fixed locally and the existing B39 analyzer outputs were
re-digested without rerunning GPU.
```

## Matrix

Common case:

```text
wall_60to30_10
Density_l = 0.005
iterations = 20
vtk_field_set = b33ledger
Stage14B18ClosureDiagnosticsMode = 1
PressureClosureMode = 1
ForceDensityClosureMode = 2
ForceFixedPointMode = 2
PhaseAdvectionVelocityMode = 2
```

Modes:

```text
M0_legacy_stress: FmuStressClosureMode = 0
M1_freeze_iter1:  FmuStressClosureMode = 1
M2_incoming_neq:  FmuStressClosureMode = 2
```

## Result Table

| probe | first ForceOverRho | first Fmu | first stress post | first phase OOB | verdict |
|---|---:|---:|---:|---:|---|
| M0 legacy | step 13, 2.636e3 | step 14, 6.434e4 | step 13, 2.029e6 | step 20 | rejected |
| M1 freeze iter1 | step 13, 2.636e3 | step 14, 6.434e4 | step 13, 2.029e6 | step 20 | rejected |
| M2 incoming neq | step 15, 8.854e5 | step 15, 4.427e3 | step 14, 2.250e3 | none by step 20 | rejected |

None of the three existing modes removes the instability. Mode 2 reproduces
the B38 failure. Modes 0 and 1 avoid the exact mode-2 `Fmu` replacement, but
they fail earlier through raw/legacy `Fmu` growth.

## Co-Located Evidence

### M0 / M1 First ForceOverRho Onset

Both modes have the same first `ForceOverRho` onset:

```text
step = 13
ijk = [93, 1, 5]
PhaseField = 5.735800909220209e-4
ReplayRhoForForce = 0.005505073722284272
ForceOverRhoNorm = 2636.4146763472127
FtotalNorm = 14.513657155803632
FmuNorm = 14.492372866456925
FmuRawNorm = 14.492372866456925
FsurfNorm = 8.358087817285956e-06
FpressureNorm = 0.022145923403073742
ReplayMu = -6.115445016490777e-05
GradPhiNorm = 0.13667178422416873
StressPreForceNorm = 383.3219828909969
StressPostForceNorm = 2029121.044003016
StressPostOverPreRatio = 5293.515985437302
```

At the next step, raw/actual F_mu explodes:

```text
step = 14
FmuNorm = FmuRawNorm = 64341.717939158065
FtotalNorm = 64423.736679553396
ForceOverRhoNorm = 11564721.794422468
StressInputNorm = 1724171.86862168
StressPostForceNorm = 39414897961677.0
```

### M2 First ForceOverRho/Fmu Onset

Mode 2 repeats B38:

```text
step = 15
ijk = [14, 1, 14]
PhaseField = 9.056482555393055e-09
ReplayRhoForForce = 0.005000004511684025
ForceOverRhoNorm = 885434.9865443383
FtotalNorm = 4427.178927524575
FmuNorm = 4427.203279090591
FmuRawNorm = 11.380036184253331
StressPostForceNorm = 230174915351.82053
StressPostOverPreRatio = 800542780.2391785
```

## Interpretation

B39 narrows the root cause further:

```text
Not enough to switch among existing FmuStressClosureMode values.
The shared failure is stress reconstruction / stress time-level / moment-space
stress definition, not only the mode-2 incoming nonequilibrium branch.
```

The low-level problem is now in how the code constructs the stress tensor used
for `F_mu` and its shadows:

```text
m0 -> EQ/Req -> m -> new_g -> stress
incoming g -> b18_stress_incoming
incoming equilibrium subtraction -> b28_stress_incoming_neq
post-force shadow -> stress_post_force_shadow
```

The failure happens before contact-angle physics can be trusted. It is still
not valid to run or claim static contact-angle validation or dynamic impact.

## Decision

B40 must be a stress-construction audit, not a short stability gate.

Required next code review:

```text
1. Compare stress definitions in MRT moment space:
   - current relaxed-stress path
   - incoming raw stress
   - incoming non-equilibrium stress
   - post-force stress shadow

2. Check whether stress uses physical population `g`, moment residual `m`,
   equilibrium distribution, or post-force/post-collision distribution with
   the wrong time level.

3. Check scaling/prefactor:
   - current MRT F_mu uses (0.5 - tau) * (Density_h - Density_l)
   - BGK path has a different tau scaling
   - B35 prefactor candidate did not become a complete write-mode proof

4. Add a B40 shadow-only stress algebra ledger before any new write candidate.
```

No B39 mode should be promoted to B40 stability or contact-angle validation.
