# Stage14-70: Momentum Closure Probe Result

Date: 2026-06-23

Status: `force_insertion_not_double_counted_next_pressure_stress_low_density`

## Claim Boundary

This is a six-step diagnostic result only. It is not contact-angle validation,
not a dynamic-impact readiness claim, and not a physical fix.

`MomentumClosureProbeMode` intentionally changes the diagnostic run in modes
2-4. These modes must not be used as production settings.

## Build And Run

Remote server:

```text
yuan@192.168.1.16
```

Compile lane:

```text
/home/yuan/src/TCLB_lbm2026_compile_lane
```

Binary:

```text
/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
sha256 = e0829e6c891fcd0a939291cc3ddd2097f41171ac88bb5bcd062e15693da1dabe
```

GPU:

```text
CUDA_VISIBLE_DEVICES=1
GPU 1 = Tesla P100-PCIE-16GB
```

Run root:

```text
/mnt/usb1t/RUNS/runs/stage14_momentum_closure_probe_20260623
```

Local artifacts:

```text
artifacts/stage14_momentum_closure_probe_20260623/
  binary_sha256.txt
  lbm2026_stage14_momentum_closure_build.log
  momentum_closure_single_node_smoke.txt
  momentum_closure_step6.csv
  momentum_closure_step6.json
```

USB space was sufficient, so no VTI cleanup was performed during this run:

```text
before: /mnt/usb1t 468G size, 195G used, 250G available
after : /mnt/usb1t 468G size, 224G used, 221G available
```

## Probe Setup

Case:

```text
wall_60to30_10
```

Common parameters:

```text
iterations = 6
vtk_period = 1
ReplayDiagnosticsMode = 1
MomentumClosureDiagnosticsMode = 1
PhaseAdvectionVelocityMode = 1
force_fixed_iterator = 1
MomentumForceMode = 0
Density_h = 1.0
Density_l = 0.001
```

Probe modes:

```text
A0 / mode 0: legacy
A1 / mode 1: record-only legacy
A2 / mode 2: no-half-force velocity for g-equilibrium
A3 / mode 3: no mF population injection
A4 / mode 4: half mF population injection
```

All five cases completed with `RUN_RC=0`.

## Step-6 Summary

Max-absolute values at step 6:

```text
mode  PhaseFromH  Ftotal      F/rho       U_half      mF          DeltaG      G_after     p_input     F_mu_raw
0     6.087e3     1.820e3     1.817e6     9.086e5     1.817e6     1.817e6     1.817e6     2.645e4     6.948e2
1     6.087e3     1.820e3     1.817e6     9.086e5     1.817e6     1.817e6     1.817e6     2.645e4     6.948e2
2     1.000e0     2.622e-2    1.931e1     9.751e0     1.931e1     9.656e0     9.751e0     3.876e-1    3.368e-2
3     1.000e0     6.311e0     6.298e3     3.149e3     6.298e3     3.149e3     3.149e3     9.160e1     2.306e0
4     6.149e1     1.810e2     1.806e5     9.030e4     1.806e5     1.355e5     1.355e5     2.627e3     6.760e1
```

## Main Finding

The legacy MRT update does not show a simple double injection of `F_total/rho`.

Evidence:

```text
mode 1 ReplayMF_max_abs             = 1.817300018e6
mode 1 ReplayMomentumDeltaG_max_abs = 1.817300018e6
```

The measured final g-derived momentum increment is approximately one
`F_total/rho`, not two.

However, the probe also shows that the legacy one-unit contribution is split
across two places:

```text
mode 2: remove half-force velocity from g-equilibrium, keep mF
        DeltaG ~= 0.5 * F/rho

mode 3: keep half-force velocity in g-equilibrium, remove mF
        DeltaG ~= 0.5 * F/rho

mode 4: keep half-force velocity and half mF
        DeltaG ~= 0.75 * F/rho
```

Interpretation:

```text
The current MRT path behaves like:
  0.5 * F/rho enters through the half-force velocity used by EQ$Req
  0.5 * F/rho enters through the moment source term mF structure
  total effective g momentum increment ~= 1.0 * F/rho
```

So the immediate Stage14-68 blow-up is not explained by "F/rho injected twice"
in the g population update.

## What Still Fails

The legacy and record-only runs still reproduce the same short-step failure:

```text
PhaseFromH_max_abs = 6.087e3
Ftotal_max_abs     = 1.820e3
F/rho_max_abs      = 1.817e6
U_half_max_abs     = 9.086e5
```

The active failure path remains:

```text
pressure/stress force grows
  -> force is divided by gas density about 0.001
  -> U_half becomes nonphysical
  -> g update carries this momentum into later phase update
  -> PhaseFromH leaves [0,1]
```

## Updated Root-Cause Ranking

Demoted:

```text
simple half-force double injection in MRT g update
```

Still high priority:

```text
1. pressure moment / pressure scale:
   p = m0[0] reaches 2.645e4 in the failing six-step run.
   Need to audit whether calc_Fp should use p, pstar, pressure minus reference,
   or another pressure distribution variable.

2. F_mu stress reconstruction:
   F_mu_raw reaches 6.948e2 in the failing six-step run.
   Need to audit whether stress comes from the correct time level and whether
   the fixed-point loop is internally consistent.

3. low-density closure:
   the direct division by rho in gas converts moderate forces into 1e6-scale
   velocity increments. This is a model-closure risk, not just a coding typo.

4. stage/load/save replay:
   if pressure/stress algebra looks correct, return to TCLB stage timing and
   AddDensity streaming replay for g/h.
```

## Next Work

Do not move to contact-angle tuning or dynamic impact.

The next branch should audit, in this order:

```text
calc_Fp pressure input and reference pressure
F_mu stress reconstruction time level
fixed-point loop residual for stress/F_mu
low-density force-over-rho closure
```

Any physical repair must be implemented behind a new explicit mode and compared
against this Stage14-70 baseline.
