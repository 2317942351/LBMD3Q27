# Stage14-66: S2 Iteration Diagnostics And Phase-Advection Velocity Probe

Date: 2026-06-23

Status: `probe_completed_not_fix`

Branch:

```text
work/phasefield-c-reference-20260623
```

## Current Evidence

The latest P100 diagnostic binary before this note was:

```text
/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
sha256: f3ff88a9577f7e0df6ea031c3a6190902d00a728f0c8099c75e1fc4a0190ebf8
mtime: 2026-06-23 14:17:41 +0800
```

Two short flat-wall acute cases were run on the P100 lane:

```text
/mnt/usb1t/RUNS/runs/stage14_s2_iterdiag_wall60_20260623
/mnt/usb1t/RUNS/runs/stage14_s2_iterdiag_wall60_ff1_20260623
```

Local summaries are archived in:

```text
artifacts/stage14_s2_iterdiag_20260623/
  iterdiag_wall60_default_summary.json
  iterdiag_wall60_ff1_summary.json
```

The case is:

```text
wall_60to30_10
Density_l = 0.001
Density_h = 1
force_fixed_iterator = 2 for default
force_fixed_iterator = 1 for ff1 control
```

## Key Numeric Chain

Default `force_fixed_iterator=2`:

```text
step  Phase max_abs  PhaseFromH max_abs  FtotalIter1 max_abs  Ftotal max_abs  Ftotal/rho max_abs  UPost max_abs  StressYY max_abs
1     1              1                   2.903e-05           2.903e-05       1.040e-02          5.201e-03    4.860e-05
2     1              1                   2.655e-05           2.651e-05       1.906e-02          9.530e-03    3.173e-03
3     1              1                   4.541e-04           2.087e-03       2.087e+00          1.046e+00    4.652e-02
4     1.166e+04      1.166e+04           8.824e-02           9.124e+01       9.124e+04          4.562e+04    2.271e+03
5     4.634e+49      4.634e+49           3.118e+08           4.110e+22       7.732e+26          3.866e+26    1.394e+24
6     8.656e+306     8.656e+306          1.991e+145          4.040e+189      8.726e+139         4.363e+139   5.392e+190
```

Control `force_fixed_iterator=1`:

```text
step  Phase max_abs  PhaseFromH max_abs  Ftotal max_abs  Ftotal/rho max_abs  UPost max_abs  StressYY max_abs
1     1              1                   2.903e-05       1.292e-02          6.459e-03    0
2     1              1                   2.976e-05       2.976e-02          1.488e-02    3.610e-03
3     1              1                   5.217e-04       4.177e-01          2.113e-01    7.238e-03
4     1              1                   4.093e-03       4.093e+00          2.050e+00    1.460e-01
5     1              1                   3.080e-01       3.030e+02          1.514e+02    2.788e+00
6     1.140e+08      1.140e+08           1.842e+03       1.805e+06          9.027e+05    1.718e+04
```

## Interpretation

The original `WallGhost ~= 97` pollution path is no longer the earliest
failure. After the phase-validity guard, `WallGhost` remains in the physical
range `[0,1]`.

The current earliest failure path is:

```text
finite near-wall gas PhaseF
-> F_mu / F_total feedback
-> F_total / rho in rho ~= Density_l gas
-> huge post-force velocity U
-> h equilibrium and h update use that huge U
-> ReplayPhaseFromH becomes nonphysical
-> next step consumes corrupted PhaseF and everything diverges
```

`force_fixed_iterator=2` is a strong amplifier: at step 4, `FtotalIter1` is only
about `8.8e-2`, while the final fixed-point value is about `9.1e1`. However,
`force_fixed_iterator=1` is not a fix. It delays the blow-up to step 6, where
`UPost` still reaches about `9.0e5` and `PhaseFromH` reaches about `1.14e8`.

The generated MRT code confirms that the phase-field population update uses
the post-force velocity:

```text
U = m0[1] + 0.5 * F_total[0] / rho
V = m0[2] + 0.5 * F_total[1] / rho
W = m0[3] + 0.5 * F_total[2] / rho
heq(h) = heq(C, U, V, W)
h = h - omega_phi * (h - heq + 0.5*Fphi) + Fphi
```

Because `heq(h)` contains quadratic velocity terms, once `U` reaches `O(10^4)`
or larger, the phase population update is guaranteed to generate a nonphysical
`PhaseField` even if the consumed phase and wall ghost were still finite.

## Code Change Added In This Step

This step adds a diagnostic switch, not a validation fix:

```text
PhaseAdvectionVelocityMode = 0
  legacy behavior: h-equilibrium uses post-force velocity

PhaseAdvectionVelocityMode = 1
  MRT diagnostic: h-equilibrium uses pre-force m0 velocity
  momentum g update still uses the legacy post-force velocity
```

New output quantity:

```text
ReplayPhaseAdvVelocity
```

Purpose:

```text
If PhaseAdvectionVelocityMode=1 keeps PhaseFromH finite while UPostForce remains huge,
then the immediate producer of the phase blow-up is confirmed to be the h-equilibrium
advection velocity path, not WallGhost or calcMu alone.

If it still blows up at the same step, then the corruption is not only through
h-equilibrium velocity and the next target is Fphi/source or population streaming.
```

Default behavior remains unchanged because the new mode defaults to `0`.

## Files Modified

```text
third_party/tclb_snapshots/stage9_analytic_wetting_diffuse_interface/models/multiphase/d3q27_pf_velocity/Dynamics.R
third_party/tclb_snapshots/stage9_analytic_wetting_diffuse_interface/models/multiphase/d3q27_pf_velocity/Dynamics.c.Rt
scripts/stage14/stage14_s2_replay_smoke.py
scripts/stage14/stage14_vti_probe.py
scripts/audit_tclb_execution_semantics.py
```

The S1 static audit was regenerated:

```text
artifacts/s1_timeline_audit_20260623/
fields = 146
producer_consumer_edges = 96
unresolved_edges = 14
s1_gate_status = needs_review
```

## Checks Completed

```text
C:\ProgramData\anaconda3\python.exe -m py_compile scripts/stage14/stage14_s2_replay_smoke.py scripts/stage14/stage14_vti_probe.py scripts/audit_tclb_execution_semantics.py
git diff --check
```

Both passed.

## Next P100 Probe

The remote binary was rebuilt successfully:

```text
sha256: be8ff8ee54553dfa175200e56fa1ccc74e2d3a120c03944061ee4493a59ac362
mtime: 2026-06-23 14:57:09 +0800
```

The first attempt wrote to `/mnt/usb1t` and is invalid because the filesystem
was full:

```text
/mnt/usb1t: 100% used, 0 available
/mnt/usb1t/RUNS/runs/stage14_s2_phaseadv_m0_wall60_20260623
step 5/6 VTI files were truncated or empty
```

The valid rerun was written to `/home`:

```text
/home/yuan/stage14_s2_phaseadv_m0_wall60_20260623
local summary:
artifacts/stage14_s2_phaseadv_m0_wall60_20260623/s2_replay_smoke_summary.json
```

Command:

```bash
python3 /home/yuan/stage14_s2_replay_smoke.py \
  --root /home/yuan/stage14_s2_phaseadv_m0_wall60_20260623 \
  --binary /home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main \
  --gpu 1 \
  --iterations 6 \
  --vtk-period 1 \
  --log-period 1 \
  --cases wall_60to30_10 \
  --replay-mode 1 \
  --phase-advection-velocity-mode 1 \
  --force-fixed-iterator 2 \
  --force \
  --run \
  --summarize
```

Result:

```text
RUN_RC = 0
summary failures = []

step 4:
  PhaseFromH max_abs = 1
  UPostForce max_abs = 4.562e4
  PhaseAdvVelocity max_abs = 0.4218

step 5:
  PhaseFromH max_abs = 3.169e13
  UPostForce max_abs = 1.636e23
  PhaseAdvVelocity max_abs = 1.214e9

step 6:
  PhaseFromH max_abs = 1.318e105
  UPostForce max_abs = 9.722e85
  PhaseAdvVelocity max_abs = 1.560e46
```

Conclusion:

```text
PhaseAdvectionVelocityMode=1 prevents the immediate step-4 h-population blow-up,
but it is not a fix. The momentum g update has already injected a large enough
velocity/pressure state that the next saved action boundary corrupts PhaseF by
steps 5-6.
```

This confirms the next target is the momentum-force/MRT feedback path, not
another wetting-boundary edit.

## Do Not Claim

Do not claim:

```text
contact-angle validation passed
PhaseAdvectionVelocityMode=1 is the physical fix
force_fixed_iterator=1 is acceptable
Density_l=0.005 or 0.01 is a validated parameter fix
curved-wall compact-stencil wetting is complete
dynamic impact foundation is ready
```

This is still S2 runtime-semantics diagnosis.
