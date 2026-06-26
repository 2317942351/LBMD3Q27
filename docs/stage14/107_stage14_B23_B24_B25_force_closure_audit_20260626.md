# Stage14-B23/B24/B25 Force-Closure Audit

Date: 2026-06-26

Branch: `work/phasefield-c-reference-20260623`

Scope: diagnostic-only TCLB audit on the fixed Stage14-B22 binary. This is not a contact-angle validation, not a wetting fix, and not a dynamic-impact preflight.

## Inputs

All B23/B24 runs used the same regenerated binary:

```text
2a5729a8041dcd3db150149b623764862778d799cd657b55ab43fc2cab47cef6
/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
```

Common case and settings:

```text
case = wall_60to30_10
Density_h = 1.0
Density_l = 0.005
PhaseAdvectionVelocityMode = 1
PressureClosureMode = 1
ForceFixedPointMode = 2
Stage14B21HPopulationAuditMode = 1
Stage14B22VelocityProducerAuditMode = 1
GPU = CUDA_VISIBLE_DEVICES=1, Tesla P100
iterations = 14
```

Local artifacts:

```text
artifacts/stage14_B23_B24_force_closure_20260626/B23_mrt_force_audit_lite/
artifacts/stage14_B23_B24_force_closure_20260626/B24_force_split_matrix_lite/
```

Remote roots:

```text
/mnt/usb1t/RUNS/runs/stage14_B23_mrt_force_audit_20260626_lite_v2
/mnt/usb1t/RUNS/runs/stage14_B24_force_split_matrix_20260626_lite
```

Large `output/*.vti` files were deleted after analysis to restore USB space. JSON/CSV/status/log evidence was retained locally and remotely. Large `*_argmax_trace.json` files were also removed from the local commit candidate; the retained `*_mask_stats.csv`, `*_first_onset.json`, `*_key_summary.json`, and matrix digest files preserve the threshold/onset evidence.

## B22 Baseline Used By B23/B24

B22 fixed 20-step evidence showed the earliest visible valid chain:

```text
step 11: B22MomentumSpeed crosses threshold first, low-rho mask, value 2.8205
step 12: B22M0Speed and B22PhaseAdvSpeed cross threshold, low-rho mask, value 1.9236
step 12: B21HeqVelocityMachShadow reaches 3.3317
step 13: ReplayPhaseFromH exits [0,1], value 2.7912
step 13: B22ForceOverRhoMag reaches 2092.38
step 14: B22FpressureMag and B22FmuMag become very large
```

This supersedes the old invalid B22 smoke run. The old smoke run had stale generated accessor/output code and is retained only as compile-chain failure evidence under:

```text
artifacts/stage14_B22_velocity_producer_audit_20260626/invalid_smoke_compile_chain/
```

## B23: MRT Force-Insertion Probe

B23 varied `MomentumClosureProbeMode`:

```text
A0 = 0, legacy-like
A1 = 1, legacy diagnostic
A2 = 2, no-half-force g-equilibrium candidate
A3 = 3, no mF population injection
A4 = 4, half mF population injection
```

Digest:

| probe | MomentumClosureProbeMode | B22 branch | B22MomentumSpeed step | B22M0Speed step | PhaseFromH OOB step | B22 F/rho step | pressure-force step | F_mu step |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| A0 | 0 | post_force_momentum_velocity_first | 5 | 6 | 7 | 7 | 8 | 8 |
| A1 | 1 | post_force_momentum_velocity_first | 5 | 6 | 7 | 7 | 8 | 8 |
| A2 | 2 | fmu_force_component_first | 6 | 7 | 8 | 8 | 9 | 8 |
| A3 | 3 | post_force_momentum_velocity_first | 6 | 7 | 8 | 8 | 9 | 9 |
| A4 | 4 | post_force_momentum_velocity_first | 5 | 6 | 8 | 7 | 8 | 8 |

Interpretation:

1. Changing the MRT force insertion path can delay the onset by about one step, but does not remove the chain.
2. A2/A3 delay the m0/phase failure from steps 5-7 to steps 6-8, so MRT insertion details matter.
3. A2 switches the reported branch to `fmu_force_component_first`, so removing the half-force contribution from g-equilibrium exposes F_mu as an immediate producer.
4. This is not yet proof of a double-force-injection bug. It is evidence that the instability is not explained by pressure closure alone and that the force/stress/momentum loop must be audited before any wetting-path fix.

## B24: Force Split And Density Denominator Matrix

B24 varied `MomentumForceMode` and `ForceDensityClosureMode`:

```text
M0_FD0 = legacy total force, raw rho denominator
M1_noFmu = omit F_mu
M2_noPressure = omit F_pressure
M3_noSurf = omit F_surf
M4_zeroForce = no momentum force
M5_surfBodyOnly = surface/body only
M0_FD1 = legacy total force, denominator floored by Density_l
```

Digest:

| probe | MomentumForceMode | ForceDensityClosureMode | B22 branch | B22MomentumSpeed step | B22M0Speed step | PhaseFromH OOB step | B22 F/rho step | pressure-force step | F_mu step |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| M0_FD0 | 0 | 0 | post_force_momentum_velocity_first | 5 | 6 | 7 | 7 | 8 | 8 |
| M0_FD1 | 0 | 1 | post_force_momentum_velocity_first | 10 | 11 | 12 | 12 | 13 | 13 |
| M1_noFmu | 1 | 0 | not_available | - | - | - | - | - | - |
| M2_noPressure | 2 | 0 | post_force_momentum_velocity_first | 5 | 6 | 7 | 7 | 8 | 8 |
| M3_noSurf | 3 | 0 | not_available | - | - | - | - | - | - |
| M4_zeroForce | 4 | 0 | not_available | - | - | - | - | - | - |
| M5_surfBodyOnly | 5 | 0 | not_available | - | - | - | - | - | - |

`not_available` here means no configured B22 threshold crossing was detected within the 14-step diagnostic window. It does not mean the branch is physically validated.

Interpretation:

1. `ForceDensityClosureMode=1` delays the full chain by roughly five steps: momentum velocity 5 -> 10, m0 6 -> 11, phase loss 7 -> 12.
2. Removing pressure force does not delay the chain at all in this matrix: `M2_noPressure` matches `M0_FD0`.
3. Removing F_mu, removing F_surf, zeroing force, or keeping only surface/body force prevents the B22 threshold crossing within 14 steps. This strongly implicates force-component balance plus low-density `F_total/rho`, not pressure input alone.
4. The result does not justify making density-flooring or force removal a physical fix. It only localizes the unstable algebraic branch.

## B25: Pressure Closure Evidence Packet

The relevant code path in `Dynamics.c.Rt` is:

```text
p = m0[0]
pressure_force_input = stage14_pressure_force_input(p, rho)
calc_Fp(&F_pressure[0], &F_pressure[1], &F_pressure[2], pressure_force_input, gradPhi)
F_total = F_surf + F_pressure + F_body + F_mu
U = m0[1:3] + 0.5 * F_total * force_rho_inv
mF[2:4] = momentum_force_injection_scale * F_total * force_rho_inv
```

`stage14_pressure_force_input` currently exposes diagnostic candidates:

```text
PressureClosureMode = 0: pressure_moment = p = m0[0]
PressureClosureMode = 1: pressure_moment * rho * cs2
PressureClosureMode = 2: pressure_moment - PressureClosureReference
```

`calc_Fp` then applies:

```text
F_pressure = (-1/3) * pressure_input * (Density_h - Density_l) * gradPhi
```

This is why pressure closure needed review: `p=m0[0]`, `pnorm=sum(g)`, and `getP()=pstar*rho*cs2` are not automatically the same physical pressure. However, B24 shows that simply removing `F_pressure` does not delay the onset, while changing `F/rho` denominator and removing F_mu/F_surf does. Therefore B25 does not support promoting `PressureClosureMode=1` to a physical repair.

Current pressure conclusion:

```text
Pressure closure remains mathematically unresolved, but it is not the first supported Stage14-B22/B24 onset lever.
The immediate repair target is the low-density F_total/rho closure and the stress/F_mu/surface-force producer path.
```

## Code-Level Implication

The next code audit should focus on this producer-consumer chain:

```text
PhaseF/C
  -> rho(C), force_rho_inv
  -> gradPhi, mu
  -> F_surf = mu * gradPhi
  -> stress reconstruction
  -> F_mu = (0.5 - tau) * (rho_h - rho_l) * stress * gradPhi
  -> F_total
  -> U = m0 + 0.5 F_total / rho_eff
  -> h-equilibrium velocity and MRT mF injection
  -> h post/update
  -> PhaseFromH after streaming
```

Specific next tasks:

1. Add a B26 full-field, single-probe, sparse-step audit that keeps stress fields but writes only steps 4-8 for one or two modes. Full field every step over many modes is too large and has already filled `/mnt/usb1t` twice.
2. Add shadow-only candidates for force denominator choices that do not write to the solver: raw `rho(C)`, bounded `rho(C_clamped)`, mixture density based on bounded phase, and floor-by-Density_l.
3. Re-audit F_mu stress reconstruction at the exact B24 branch, especially comparing `M1_noFmu` and `M3_noSurf` against `M0_FD0` and `M0_FD1`.
4. Only after B26 identifies whether the unstable numerator is F_mu, F_surf/mu, or denominator collapse should a physical correction mode be designed.

## Claim Boundary

Allowed claims:

```text
B23/B24 localize the earliest visible chain to post-force momentum velocity, low-density F/rho, and force-component balance.
PressureClosureMode=1 remains diagnostic only.
MRT force insertion affects onset timing but does not alone remove the chain.
```

Forbidden claims:

```text
contact-angle validation passed
static wetting is solved
curved wall wetting is solved
dynamic impact is ready
ForceDensityClosureMode=1 is a validated physical fix
MomentumForceMode force removal is a physical fix
PressureClosureMode=1 is a validated pressure closure
```
