# Stage14-B26 To B32 Execution Plan

Date: 2026-06-27

Branch: `work/phasefield-c-reference-20260623`

Scope: evidence-first TCLB phase/momentum closure work. This is not contact-angle validation, not curved-wall validation, and not dynamic-impact readiness.

## Current Blocking Chain

The current credible chain is no longer a curved-wall `WallGhost` tuning problem:

```text
PhaseF/C
  -> rho(C), force_rho_inv
  -> gradPhi, mu
  -> F_surf = mu * gradPhi
  -> stress reconstruction
  -> F_mu = (0.5 - tau) * (rho_h - rho_l) * stress * gradPhi
  -> F_total
  -> U = m0 + 0.5 * F_total / rho_eff
  -> h equilibrium and h post-update
  -> PhaseFromH after streaming
  -> pressure/F_mu/tmp1 amplification after loss of bounded phase
```

The key TCLB code path is in:

```text
third_party/tclb_snapshots/stage17B_diffuse_solid_shadow/models/multiphase/d3q27_pf_velocity/Dynamics.c.Rt
```

Important current snippets:

```c
calc_Fs(&F_surf[0], &F_surf[1], &F_surf[2], mu, gradPhi);
F_total[0] = F_surf[0] + F_pressure[0] + F_body[0] + F_mu[0];
U = m0[1] + 0.5 * F_total[0] * force_rho_inv;
mF[2:4] = momentum_force_injection_scale * F_total * force_rho_inv;
C(h, h - omega * (h - heq + 0.5*Fphi) + Fphi)
```

The main unresolved question is which producer must be repaired first:

```text
denominator: low rho(C) makes F_total/rho unbounded
numerator: F_mu or F_surf becomes nonphysical before denominator amplification
stress time level: stress reconstruction from post-force/post-collision state is wrong
phase population: h/heq algebra or AddDensity streaming is the first invalid producer
```

## B26 Gate: Full Sparse Field Classification

Purpose: rerun the sparse full-field onset comparison with a correct VTI field set.

Reason for rerun: the first B26 run used `--vtk-field-set full`, which did not request any `B22*` fields. The analyzer therefore reported:

```text
b22_primary_branch = not_available
b26_conclusion = unresolved
```

This was a field-selection failure, not a physics conclusion.

Required correction:

```text
scripts/stage14/stage14_s2_replay_smoke.py
  adds VTK field set b26 = full replay + all B22 fields

scripts/stage14/run_stage14_b26_sparse_fullfield_remote.sh
  uses --vtk-field-set b26
  default root = /mnt/usb1t/RUNS/runs/stage14_B26_sparse_fullfield_v2_20260627
```

Acceptance:

```text
B22ProbeActive and B22 force/velocity fields are present in b26_field_presence.json
M0_FD0_full and M0_FD1_full both produce analyzer output
b26_sparse_digest.json classifies denominator, numerator, stress time-level, phase-first, or unresolved
no contact-angle claim is made
```

## B27 Gate: Classification Confirmation

Purpose: convert B26 into a narrow repair target.

If B26 says `denominator_supported`:

```text
Run a 3-probe short matrix:
  raw rho(C)
  bounded rho(C_clamped)
  phase-mixture rho from bounded C
Compare first B22MomentumSpeed, B22ForceOverRhoMag, PhaseFromH OOB.
```

If B26 says `numerator_supported`:

```text
Run a force-component matrix:
  legacy total force
  no F_mu
  no F_surf
  no F_pressure
  F_surf only
Compare F_mu, F_surf, mu, gradPhi, stress, and h/heq onset order.
```

If B26 says `stress_time_level_supported`:

```text
Run stress-candidate probes:
  legacy stress
  pre-force stress
  incoming g stress
  force-excluded stress
Compare F_mu candidates and momentum velocity onset.
```

If B26 is still unresolved:

```text
Do not repair physics.
Patch the analyzer/field set until the first producer can be classified.
```

## B28 Gate: Minimal Explicit Physics Candidate

Purpose: implement only one explicit candidate mode after B27 selects the branch.

Rules:

```text
Default behavior must remain legacy.
Candidate must have an explicit setting and a new mode id.
Do not reuse MomentumForceMode force-removal probes as physical repairs.
Do not make ForceDensityClosureMode=1 a default or call it validated.
```

Likely mode families:

```text
ForceDensityClosureMode=2: phase-consistent bounded mixture denominator
FmuStressClosureMode=1: pre-force/non-equilibrium stress candidate
PhaseVelocityClosureMode=1: bounded phase-advection velocity candidate
```

Only one family should be implemented per B28 commit.

## B29 Gate: Flat-Wall Short Stability

Purpose: prove the candidate removes the short onset without hiding the physics.

Minimum case:

```text
wall_60to30_10
Density_h = 1.0
Density_l = 0.005
steps = 20, then 100
GPU = P100, CUDA_VISIBLE_DEVICES=1
```

Pass criteria:

```text
PhaseFromH remains finite and inside a defensible tolerance
B22MomentumSpeed and B21HeqVelocityMachShadow no longer exceed thresholds early
mass drift and max velocity are reported
diagnostic fields explain what changed
```

## B30 Gate: Flat-Wall Wetting Direction

Purpose: only after B29 short stability, test whether the flat wall responds in the right direction.

Minimum cases:

```text
flat wall equilibrium: theta 30, 90, 150
flat wall decoupled: 60 -> 30, 120 -> 150
```

Pass criteria:

```text
decoupled angle moves toward the BC target
morphology plots agree with numeric angle direction
no NaN/nonfinite phase
mass and spurious velocity are bounded
```

## B31 Gate: Cylinder/Sphere Static Preflight

Purpose: return to geometry only after the flat-wall phase/momentum closure is not failing.

Minimum cases:

```text
cylinder theta 90, then 60/120
sphere theta 90, then 60/120
shadow diagnostics first if any instability appears
```

Pass criteria:

```text
solid/fluid mask and analytic normals are correct
PhaseF write path is explicit and guarded
Psi/WallGhost diagnostics are bounded
angle direction is consistent with BC target
```

## B32 Gate: Dynamic Impact Preflight Only

Purpose: create a low-We preflight readiness packet, not a production impact study.

Prerequisites:

```text
B29 flat-wall short stability passes
B30 flat-wall wetting direction passes
B31 cylinder/sphere static preflight passes
```

Preflight contents:

```text
low-We wall impact setup draft
initial droplet geometry and velocity sanity
CFL/Mach/Capillary/Weber estimates
mass/phase/KE/spurious velocity monitors
restart and artifact policy
```

Allowed result:

```text
dynamic_preflight_pass
dynamic_preflight_blocked_by_<reason>
```

Forbidden result:

```text
dynamic impact validated
production dynamic simulation ready
```

## Execution Guardrails

Do not commit:

```text
*.vti
*.pvti
*_argmax_trace.json unless explicitly curated and small
binary files
__pycache__
large tar payloads
```

Remote run policy:

```text
server = yuan@192.168.1.16
GPU = CUDA_VISIBLE_DEVICES=1
run root base = /mnt/usb1t/RUNS/runs
delete regenerable output/*.vti after analyzer finishes when space is below 50G or after light evidence is downloaded
```

Build policy:

```text
Changing AddField/AddQuantity/AddSetting requires full TCLB source regeneration.
Changing only Python VTK field sets does not require recompilation.
```

## Current Action

As of this document, B26 v2 is running remotely. B27 must wait for B26 v2 `b26_sparse_digest.json`.

