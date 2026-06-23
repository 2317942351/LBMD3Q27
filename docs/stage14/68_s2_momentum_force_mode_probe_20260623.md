# Stage14-68: MomentumForceMode Probe Result

Date: 2026-06-23

Status: `root_cause_narrowed_to_pressure_viscous_momentum_feedback`

Branch:

```text
work/phasefield-c-reference-20260623
```

## Claim Boundary

This is a six-step runtime diagnostic only. It is not a contact-angle
validation, not a static wetting validation, and not evidence that dynamic
impact is ready.

The purpose was to isolate which momentum-force component turns the already
instrumented `wall_60to30_10` case unstable after the Stage14 phase-range guard
and `PhaseAdvectionVelocityMode=1` diagnostic.

## Remote State

Compile lane:

```text
/home/yuan/src/TCLB_lbm2026_compile_lane
```

Binary:

```text
/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
sha256 = 2819c41ae4d87eae57d42dcfc5d870d167a0d5c3ef52ce518425c4170209c3a2
```

GPU:

```text
CUDA_VISIBLE_DEVICES=1
server GPU 1 = Tesla P100-PCIE-16GB
```

USB cleanup before the probe:

```text
/mnt/usb1t before cleanup: 468G size, 444G used, 0 available, 100%
deleted: 561 files matching /mnt/usb1t/RUNS/runs/*/*/output/*.vti
deleted size: 275.782 GiB
/mnt/usb1t after cleanup: 468G size, 169G used, 276G available, 38%
```

Cleanup records:

```text
artifacts/stage14_s2_momentum_force_probe_20260623/usb1t_cleanup_vti_manifest_20260623.txt
artifacts/stage14_s2_momentum_force_probe_20260623/usb1t_cleanup_vti_summary_20260623.txt
```

The cleanup removed regenerable VTI volume snapshots only. It did not remove
case directories, `case.xml`, `case_metadata.json`, `run.log`, summaries, or
analysis outputs.

After the user clarified the storage policy, VTI snapshots are preserved when
available space is above 50 GiB. The current probe therefore keeps 42 VTI files
on the server:

```text
/mnt/usb1t/RUNS/runs/stage14_s2_momentum_force_probe_20260623
  modes 3,4,5 retain 7 VTI files each

/mnt/usb1t/RUNS/runs/stage14_s2_momentum_force_probe_20260623_vti_rerun
  modes 0,1,2 retain 7 VTI files each
```

Final space check after the probe:

```text
/mnt/usb1t: 468G size, 195G used, 250G available, 44%
/home/yuan: 107G size, 90G used, 11G available, 90%
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
PhaseAdvectionVelocityMode = 1
force_fixed_iterator = 1
Density_h = 1.0
Density_l = 0.001
```

Mode definitions:

```text
MomentumForceMode = 0: legacy F_total
MomentumForceMode = 1: omit F_mu from F_total
MomentumForceMode = 2: omit F_pressure from F_total
MomentumForceMode = 3: omit F_surf from F_total
MomentumForceMode = 4: set F_total = 0
MomentumForceMode = 5: surface-only F_total = F_surf + F_body
```

Local artifacts:

```text
artifacts/stage14_s2_momentum_force_probe_20260623/
  stage14_s2_momentum_force_probe_20260623_comparison.csv
  stage14_s2_momentum_force_probe_step6_key_metrics.csv
  stage14_s2_momentum_force_probe_20260623_topnodes.json
  remote_logs/
  vti_rerun_logs/
```

## Step-6 Key Metrics

Max-absolute values at step 6:

```text
mode  PhaseFromH  Ftotal      F/rho       UPost       F_mu       F_pressure  F_surf
0     6.087e3     1.820e3     1.817e6     9.086e5     6.948e2    1.180e3     2.728e-5
1     1.000e0     1.457e0     1.457e3     7.280e2     7.827e-1   1.457e0     2.728e-5
2     1.000e0     8.878e-2    8.778e1     4.379e1     8.878e-2   1.575e-1    2.728e-5
3     1.000e0     0.000e0     0.000e0     0.000e0     0.000e0    0.000e0     2.728e-5
4     1.000e0     0.000e0     0.000e0     0.000e0     0.000e0    0.000e0     2.728e-5
5     1.000e0     2.728e-5    8.077e-3    2.946e-3    2.720e-5   5.039e-4    2.728e-5
```

Interpretation:

```text
mode 0 fails: legacy momentum forcing still drives PhaseFromH to 6.087e3.
mode 1 remains phase-bounded when F_mu is omitted, but UPost is still 7.28e2.
mode 2 remains phase-bounded when F_pressure is omitted, with UPost 4.38e1.
mode 3 stays bounded when F_surf is omitted; pressure/viscous feedback is not seeded.
mode 4 stays bounded with all momentum force disabled.
mode 5 stays bounded with surface-only momentum force.
```

This means the surface force is a seed, but surface force alone is not the
pathological term in this short probe. The large amplification comes from the
pressure and viscous momentum-force feedback that develops after surface-force
motion is introduced.

## Node-Level Evidence

Worst step-6 node in mode 0:

```text
ijk = [6, 1, 89]
ReplayRho = 1.0017e-3
ReplayFpressure = [-1.757e-1, -1.180e3, 1.757e-1]
ReplayFmu       = [-2.077e-1, -6.401e2, 2.077e-1]
ReplayFsurf     = [1.203e-9, 8.082e-6, -1.203e-9]
ReplayFtotal    = [-3.834e-1, -1.820e3, 3.834e-1]
ReplayForceOverRho = [-3.827e2, -1.817e6, 3.827e2]
ReplayUPostForce   = [-2.386e2, -9.086e5, 2.386e2]
ReplayPhaseFromH   = 1.118e3 at this node; global max = 6.087e3
```

The collision-time replay field sees a near-gas density of approximately
`0.001`, so a force of order `1e3` immediately becomes an acceleration-like
source of order `1e6`. This is the direct numerical path from momentum forcing
to phase-field corruption in the six-step diagnostic.

Also note the same node has the regular output field `Rho = 1116.794`, while
`ReplayRho = 0.0010017`. That confirms the previous TCLB time-level warning:
regular output fields after the corrupted update are not interchangeable with
the collision-time producer-consumer replay fields.

## Updated Root-Cause Ranking

Current leading chain:

```text
F_surf seeds a small wall/interface momentum response
  -> pressure moment and viscous stress reconstruction produce F_pressure/F_mu
  -> F_total is divided by very low gas density
  -> UPostForce becomes nonphysical
  -> even with PhaseAdvectionVelocityMode=1, the g update corrupts subsequent h/PhaseF
  -> PhaseFromH leaves [0,1]
```

What this demotes:

```text
WallGhost direct pollution is not the active step-6 failure path here.
Compact-stencil wetting geometry is not the next thing to tune.
Surface force alone is not sufficient to reproduce the blow-up in this probe.
```

What remains possible:

```text
1. F_pressure has the wrong pressure moment, wrong time level, or wrong scaling
   for this pressure-distribution formulation.

2. F_mu/stress reconstruction is inconsistent with the current MRT force
   insertion or fixed-point loop.

3. The MRT force insertion may double-count the half-force correction:
   velocity is updated with 0.5*F/rho, then mF is injected into the moment
   update as F/rho.

4. Low-density force-over-rho treatment may require a density-ratio-compatible
   closure rather than the current direct division in gas cells.
```

## Next Solver Work

Do not proceed to contact-angle tuning or dynamic impact.

Next implementation target:

```text
Add a momentum producer-consumer diagnostic that records:
  m0[1:3] before force
  U after the 0.5*F/rho velocity correction
  mF[1:3]
  final g-derived momentum after the MRT update
  F_pressure pressure input p or pstar
  F_mu stress tensor input before and after the fixed-point update
```

Then run the same six-step P100 probe and answer one question:

```text
Does the current MRT update inject F/rho once, twice, or with the wrong pressure
distribution scaling?
```

Only after that is known should the code be changed physically. The current
`MomentumForceMode` switch is diagnostic only and must not be presented as a
solution.
