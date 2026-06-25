# Stage14-B17 Onset Mask/Argmax Diagnostics

Date: 2026-06-25

Status: diagnostic complete. This is not contact-angle validation, not a solver fix, and not a dynamic-impact preflight.

## Purpose

B17 was run because Stage14-74 had already moved the primary risk away from a pure `tmp1/Fphi` source-term failure and toward:

```text
stress / F_mu / force-over-rho feedback
    -> oversized velocity input
    -> h update / PhaseFromH leaves [0, 1]
    -> pressure and phase source terms amplify the failure
```

The missing evidence was spatial: full-field maxima did not say whether the first large values occurred in the contact-line band, diffuse interface, low-density gas, or bulk liquid. B17 therefore adds a VTI analyzer that computes mask-specific statistics and argmax co-located traces.

## Code Added

- `scripts/stage14/stage14_b17_onset_mask_argmax.py`
  - Reads `.vti` frames directly.
  - Fails clearly if only `.pvti` shells exist.
  - Builds masks: `fluid_all`, `near_wall`, `interface_strict`, `interface_wide`, `near_interface_wall`, `liquid_bulk`, `gas_bulk`, `low_rho`, `solid`.
  - Computes derived norms for `F_mu`, `F_total`, `F/rho`, pressure force, velocity, and stress tensors.
  - Writes:
    - `b17_mask_stats.csv`
    - `b17_argmax_trace.json`
    - `b17_first_onset.json`
    - `b17_field_presence.json`
    - `b17_key_summary.json`

- `scripts/stage14/run_stage14_b17_onset_remote.sh`
  - Runs the short P100 case and executes the B17 analyzer on the server.
  - Downloads are intentionally light; VTI files are left on the server.

No TCLB solver physics was changed for B17.

## Run Record

Server:

```text
yuan@192.168.1.16
GPU: CUDA_VISIBLE_DEVICES=1, Tesla P100-PCIE-16GB
run root: /mnt/usb1t/RUNS/runs/stage14_B17_onset_mask_argmax_20260625
case root: /mnt/usb1t/RUNS/runs/stage14_B17_onset_mask_argmax_20260625/probe_wall_60to30_R200_step20
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
iterations = 20
vtk_period = 1
```

Binary SHA256:

```text
66cb03cd52ddc819ec7cebfbd7ed9c976827912db290bcc563a407466544f946
```

Runtime status:

```text
RUN_RC = 0
DRIVER_RC = 3
ANALYZER_RC = 0
VTI_COUNT = 21
```

`DRIVER_RC=3` is expected for this failing diagnostic because `stage14_s2_replay_smoke.py` flags nonfinite fields from step 17 onward. The run itself completed with `RUN_RC=0`; the B17 analyzer completed successfully.

Local lightweight artifacts:

```text
artifacts/stage14_B17_onset_mask_argmax_20260625/
```

## First Onset Summary

From `b17_key_summary.json`:

| Trigger | Step | Mask | Value |
|---|---:|---|---:|
| `StressPostForceNorm > 1e3` | 13 | `near_interface_wall` | `1.275366e6` |
| `ForceOverRhoNorm > 1e3` | 13 | `near_interface_wall` | `2.092377e3` |
| `ReplayHPostMaxAbs > 1` | 13 | `low_rho` | `2.233706` |
| `ReplayPhaseFromH > 1.001` | 13 | `low_rho` | `2.791220` |
| `FmuRawNorm > 1e3` | 14 | `low_rho` | `1.007235e5` |
| `ReplayPressureInput > 1e3` | 14 | `low_rho` | `6.779061e5` |
| `StressInputNorm > 1e3` | 14 | `low_rho` | `1.646657e6` |

The B17 classifier returns:

```text
primary_branch = stress_timelevel_or_fixed_point_feedback
reason = Post-force stress grows no later than F/rho and before or with phase loss.
```

## Step 12-14 Mask Evidence

Key max-abs values from `b17_step12_14_key_mask_stats.csv`:

| Step | Mask | `StressPre` | `StressPost` | `FmuRaw` | `F/rho` | `PhaseFromH` | `HPost` | `PressureInput` |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 12 | `low_rho` | `5.866` | `466.298` | `0.226` | `41.410` | `0.0199` | `0.0060` | `0.0120` |
| 12 | `near_interface_wall` | `0.1308` | `0.1120` | `0.0059` | `0.4108` | `0.9895` | `0.2932` | `2.96e-4` |
| 13 | `low_rho` | `118.291` | `2.359442e5` | `4.534` | `908.942` | `2.7912` | `2.2337` | `0.3259` |
| 13 | `near_interface_wall` | `304.181` | `1.275366e6` | `11.184` | `2092.377` | `0.9895` | `0.6171` | `0.4379` |
| 14 | `low_rho` | `1.646657e6` | `3.593019e11` | `1.007235e5` | `1.099147e6` | `1.479183e11` | `1.856543e10` | `6.779061e5` |
| 14 | `near_interface_wall` | `0.5482` | `1.0297` | `0.0223` | `1.2956` | `0.9894` | `0.2932` | `0.00153` |

The spatial split matters:

- At step 12, the strongest early warning is not the main contact-line interface. It is low-density near-wall gas: `StressPost/StressPre` is about `79.5`, `UPost` reaches about `20`, while `PhaseFromH`, `HPost`, `tmp1`, and `Fphi` remain small there.
- At step 13, `near_interface_wall` develops `StressPostForceNorm = 1.275e6` and `ForceOverRhoNorm = 2.092e3`, while `low_rho` already has `PhaseFromH = 2.791` and `HPost = 2.234`.
- At step 14, the low-density branch has fully blown up. Pressure also becomes huge, but only after the step-13 stress/F-rho/H onset.

## Argmax Co-Located Evidence

The digest file `b17_step12_14_argmax_digest.json` gives the exact co-located values. One representative early low-density point at step 12 is:

```text
ijk = [93, 1, 90]
mask = low_rho, gas_bulk, near_wall
phase = 6.3747e-4
rho_force = 5.4718e-3
StressPre = 5.866
StressPost = 466.298
StressPost/StressPre = 79.486
FmuRaw = 0.226
ForceOverRho = 41.410
UPre = 1.454
UPost = 20.017
HPost = 1.8756e-4
Fphi = 4.6807e-5
```

This point shows the chronology clearly: the post-force stress and half-force velocity are already pathological in low-density gas before `h` or `PhaseFromH` at that point are large.

At step 13, the first configured `near_interface_wall` threshold crossing is:

```text
StressPostForceNorm = 1.275366e6
ForceOverRhoNorm = 2.092377e3
FmuRawNorm = 11.184
ReplayHPostMaxAbs = 0.617
ReplayPhaseFromH = 0.989
```

At the same step, the first phase/H bound failure is in `low_rho`, not the main contact-line interface:

```text
ReplayPhaseFromH = 2.791
ReplayHPostMaxAbs = 2.234
```

## Interpretation

B17 strengthens the Stage14-74 interpretation:

```text
post-force stress / low-density force-over-rho feedback
    -> oversized UPost / phase-advection velocity
    -> h equilibrium/update overshoot in low-density gas
    -> PhaseFromH leaves [0, 1]
    -> pressure, F_mu, tmp1/Fphi amplify later
```

`tmp1/Fphi` is not the first producer in this run:

- Step 13 `near_interface_wall` has `ReplayTmp1` still near `1/3` and `ReplayFphiMaxAbs` about `0.0215`.
- Step 13 `low_rho` has `ReplayTmp1` about `0.0267` and `ReplayFphiMaxAbs` about `0.00189`.
- Step 14 `tmp1` and pressure become large only after the step-13 phase/H failure.

Pressure closure remains a real branch, but B17 does not support making it the immediate first fix:

- At step 13, pressure input is below the configured large threshold.
- The largest pressure-input threshold crossing appears at step 14 in `low_rho`, after `StressPost`, `F/rho`, `HPost`, and `PhaseFromH` have already failed.

## Next Route

Do not continue tuning `WallGhost`, `DynamicCL`, `ForceCap`, or curved compact write as the next primary branch.

The next step should be Stage14-B18: split the post-force stress and low-density force closure without changing legacy defaults:

1. Add shadow stress candidates in TCLB:
   - legacy stress input
   - pre-half-force stress
   - post-half-force stress
   - force-excluded nonequilibrium stress candidate
2. Add shadow `F_mu` candidates from each stress tensor.
3. Add shadow `F_total/rho` using:
   - raw rho
   - bounded physical rho floor
   - phase-consistent mixture rho
4. Add shadow phase-advection velocity candidates:
   - current `U`
   - pre-force `m0[1:3]`
   - bounded `U` only as diagnostic shadow, not as a validation fix
5. Re-run the same 20-step case and require the winning branch to explain step 12-13 at the same argmax locations.

Only after B18 identifies a physically justified candidate should a new explicit physics mode be implemented.

## Prohibited Claims

Do not claim:

- contact-angle validation passed
- dynamic impact basis is ready
- density ratio 200 is stable
- `PressureClosureMode=1` is a validated physical pressure closure
- any force cap or clamp is a valid physical fix

The supported claim is:

```text
B17 localized the earliest large producer to post-force stress / F-rho feedback,
first in low-density near-wall gas and then in near-interface-wall nodes,
with phase/H failure following at step 13 and pressure/tmp1 amplification later.
```
