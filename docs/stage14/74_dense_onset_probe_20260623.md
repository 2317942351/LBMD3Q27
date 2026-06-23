# Stage14-74 Dense Onset Probe: Phase-Momentum-Pressure Closure Triage

Date: 2026-06-23

Status: diagnostic only. This is not contact-angle validation and not a dynamic-impact preflight.

## Purpose

This probe implements the requested next branch:

```text
PhaseF -> tmp1/Fphi -> h update -> PhaseFromH
F_mu stress reconstruction time level
pressure closure: m0[0] vs physical/normalized pressure
```

The goal is to locate the earliest producer-consumer failure in `wall_60to30_10` at density ratio 200, not to tune contact angle or to claim a fix.

## Code Changes

Added diagnostic-only fields:

- `ReplayHPreSum`, `ReplayHPostSum`, `ReplayHeqSum`
- `ReplayHPreMaxAbs`, `ReplayHPostMaxAbs`, `ReplayHeqMaxAbs`
- `ReplayFphiSum`, `ReplayFphiMaxAbs`
- `ReplayTmp1`, `ReplayTmp1BoundedShadow`, `ReplayPhaseOutOfBoundsFlag`
- `ReplayStressPreForceShadowXX/XY/XZ/YY/YZ/ZZ`
- `ReplayStressPostForceShadowXX/XY/XZ/YY/YZ/ZZ`

All new fields are `AddField(..., group="runtime_diagnostics")` and are gated by existing replay or momentum-closure diagnostic switches. Legacy default behavior is not changed.

The first implementation attempted to compute h-population max-abs through R-template conversion of the TCLB `PV` object:

```r
as.character(h)
```

That failed during RT generation because `h` is an S4 object that cannot be coerced that way. The final implementation computes h-pop max-abs in generated C by explicitly scanning `h0..h26` and scanning `heq[]`. This is diagnostic-only and does not alter the h update.

## Build Record

Server:

```text
yuan@192.168.1.16
compile lane: /home/yuan/src/TCLB_lbm2026_compile_lane
binary: /home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
```

Binary SHA256:

```text
c1eaf74345866d86d328bc49a14e43e82e04f0a1162edd8b5d121f9e573fc54b
```

Important build caveat:

After a clean `rm -rf CLB/d3q27_pf_velocity_q27_geometric`, `make d3q27_pf_velocity_q27_geometric/source` completed but did not generate `Dynamics.c`. CUDA compilation then failed at:

```text
cuda.cu:1149:18: fatal error: Dynamics.c: no such file or directory
```

For this probe, `Dynamics.c` was generated explicitly with:

```bash
tools/RT -b -q \
  -f models/multiphase/d3q27_pf_velocity/Dynamics.c.Rt \
  -I tools,src,models/multiphase/d3q27_pf_velocity \
  -w CLB/d3q27_pf_velocity_q27_geometric/ \
  -o CLB/d3q27_pf_velocity_q27_geometric/Dynamics.c \
  -i options.R
```

Then `make -C CLB/d3q27_pf_velocity_q27_geometric -j 8` succeeded. Future build scripts should encode this explicitly or fix the TCLB source target dependency before treating a clean source-generation gate as reproducible.

## Run Record

Run root:

```text
/mnt/usb1t/RUNS/runs/stage14_dense_onset_probe_hmax_20260623
```

Case:

```text
wall_60to30_10
Density_h = 1.0
Density_l = 0.005
PressureClosureMode = 1
ForceFixedPointMode = 2
PhaseAdvectionVelocityMode = 1
MomentumForceMode = 0
MomentumClosureDiagnosticsMode = 1
MomentumClosureProbeMode = 1
GPU = P100, CUDA_VISIBLE_DEVICES=1
iterations = 20
vtk_period = 1
```

Result:

```text
RUN_RC=0
VTI frames: 21, step 0-20
```

The full VTI outputs are intentionally not copied into git because each frame is about 1.2 GB. The lightweight audit artifacts are in:

```text
artifacts/stage14_dense_onset_probe_hmax_20260623/
```

## First Failures

From `dense20_first_failures.json`:

| First trigger | Step | Value |
|---|---:|---:|
| `threshold_force_over_rho_large` | 13 | 2483.1279725962554 |
| `threshold_phase_bounds` | 13 | 2.791219556608537 |
| `threshold_phase_output_bounds` | 13 | 2.791219556608537 |
| `threshold_fmu_large` | 14 | 76185.37351188144 |
| `threshold_pressure_large` | 14 | 677906.1332551276 |
| `threshold_stress_large` | 14 | 1390838.0964059338 |
| `threshold_tmp1_large` | 14 | 14.109501559736659 |
| `threshold_fphi_large` | 15 | 2.160969453403737e+21 |
| first nonfinite phase / h / stress fields | 17 | nonfinite counts begin |

## Step 10-15 Onset Table

Values are max-absolute field statistics from `dense20_frames.csv`.

| step | PhaseField | PhaseFromH | HPreMax | HPostMax | HeqMax | Tmp1 | FphiMax | ForceOverRho | Ftotal | FmuRaw | PressureInput | StressInputYY | StressPostYY |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 1.0000151742270116 | 1.0000151742270116 | 0.29629687716924474 | 0.2962985866860857 | 0.29629969382154303 | 0.33333332861733816 | 0.024414630592411064 | 1.4818008012318717 | 0.007948521055014101 | 0.007946991336675714 | 0.0008267028123789402 | 0.41131734639085016 | 0.8172457502631222 |
| 11 | 1.0000186169231815 | 1.0000186169231815 | 0.2962985866860857 | 0.2963001497617178 | 0.29630079236346213 | 0.3333333310132446 | 0.024414254168044887 | 5.310882813187393 | 0.02855270179423073 | 0.028484473527653317 | 0.0017408651652777733 | 0.7015703547661184 | 9.188583727572826 |
| 12 | 1.0000221338821245 | 1.0000221338821245 | 0.2963001497617178 | 0.2963012429230518 | 0.2963018124197782 | 0.33333332961544637 | 0.024413896900741583 | 40.99750355011021 | 0.22432907193230367 | 0.2238605897893423 | 0.011968349263321394 | 5.491315044845218 | 443.2144714259732 |
| 13 | 2.791219556608537 | 2.791219556608537 | 0.2963012429230518 | 2.233706063315237 | 3.127171808902775 | 0.33333332723239417 | 0.024413564770582295 | 2483.1279725962554 | 13.990642363075947 | 13.967954862314539 | 0.5010038926203118 | 341.7464399445226 | 1766871.7706908982 |
| 14 | 276749289103.34906 | 276749289103.34906 | 2.233706063315237 | 222562803320.13647 | 311587924649.08453 | 14.109501559736659 | 0.7413743653742992 | 1099146.5821635409 | 128668.8123389724 | 76185.37351188144 | 677906.1332551276 | 1390838.0964059338 | 357482599926.7464 |
| 15 | 1.1782156068053921e+33 | 1.1782156068053921e+33 | 222562803320.13647 | 8.653117730593212e+32 | 1.2114364822830496e+33 | 1.0212022535857645e+23 | 2.160969453403737e+21 | 4.397952902690399e+18 | 6.472849134871902e+29 | 16453569071.085476 | 1.3941130287619464e+22 | 231641070725.375 | 5.641414315052318e+36 |

## Interpretation

The h-population max-abs diagnostics rule out the simplest hypothesis that hidden h-population cancellation is the first trigger before momentum feedback:

- Up to step 12, `HPreMaxAbs`, `HPostMaxAbs`, and `HeqMaxAbs` remain about `0.2963`.
- At step 12, `ForceOverRho` is already `40.9975` and `StressPostForceShadowYY` is already `443.214`, while phase and h populations are still close to bounded.
- At step 13, `tmp1` is still normal (`0.3333333`) and `FphiMaxAbs` is still normal (`0.0244136`), but `ForceOverRho` jumps to `2483.13`, `FmuRaw` to `13.968`, and `StressPostForceShadowYY` to `1.77e6`.
- At the same step, `HPostMaxAbs` and `HeqMaxAbs` rise while `HPreMaxAbs` is still normal. This points to the phase update being driven by an already pathological velocity/force state, not by the Allen-Cahn source term alone.
- At step 14, `tmp1` becomes large only after the consumed/produced phase is already out of bounds. Therefore `tmp1/Fphi` is a secondary amplifier in this run, not the first cause.

Current best branch:

```text
stress / F_mu time-level or force-over-rho feedback
    -> oversized U or phase-advection velocity
    -> heq/h-post population cancellation
    -> next PhaseFromH leaves [0,1]
    -> tmp1/Fphi and pressure terms amplify the failure
```

Pressure closure remains suspicious, but in this run it is not the first strong signal: at step 13 `Fpressure` is about `0.0227`, while `FmuRaw` is about `13.968`. Pressure then explodes at step 14 after phase has already left the physical range. This makes pressure closure the second branch, not the immediate next branch.

## Next Work Direction

Do not add a hard phase clamp as a validation fix. A clamp would hide the first bad producer and would not establish a correct static contact-angle basis.

Next diagnostic branch should be stress/F_mu and force-over-rho isolation:

1. Add a `StressClosureProbeMode` or equivalent shadow fields:
   - legacy current stress input
   - stress reconstructed from pre-half-force velocity
   - stress reconstructed from post-half-force velocity
   - stress reconstructed from post-collision non-equilibrium excluding explicit force contribution
2. Add shadow `F_mu` candidates from those stress tensors without changing default physics.
3. Run `wall_60to30_10` for steps 0-15 at density ratio 200.
4. Compare which candidate predicts or removes the step 12-13 jump in `ForceOverRho`.
5. Only after that, convert the winning branch into an explicit physics mode and re-run the minimal gates.

Pressure closure should be handled after stress/F_mu:

1. Audit `p = sum(g)`, `getP() = pstar*rho*cs2`, and `calc_Fp` against the original phase-field LBM formulation.
2. Determine whether `calc_Fp` should consume normalized pressure moment, physical pressure, or pressure difference from reference.
3. Promote `PressureClosureMode` only after this derivation is written down.

## Prohibited Claims

Do not claim:

- contact angle validation passed
- dynamic impact basis is ready
- `PressureClosureMode=1` is a physical fix
- `ForceFixedPointMode=2` is a physical fix
- density ratio 200 is stable

The only supported claim is:

```text
Stage14-74 localized the earliest observed onset away from tmp1/Fphi as the primary trigger and toward stress/F_mu / force-over-rho feedback before the h update.
```
