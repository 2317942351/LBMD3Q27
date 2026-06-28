# Stage14 B41-B47 Force Closure Execution Plan

Date: 2026-06-28

Branch: `work/phasefield-c-reference-20260623`

Status: execution plan. This document does not claim contact-angle validation,
curved wetting validation, dynamic-impact readiness, or a completed solver
repair.

## Current Technical Position

B40 narrowed the next actionable branch to stress/F_mu time-level and
fixed-point feedback. The relevant TCLB path is:

```text
incoming g AddDensity after streaming
  -> m0 = M*g
  -> p = m0[0], rho = rho(C)
  -> gradPhi/mu
  -> stress from (m0 - EQ(U,p))*Omega
  -> F_mu = stress * gradPhi
  -> F_total = F_surf + F_pressure + F_body + F_mu
  -> U = m0[1:3] + 0.5*F_total/rho_eff
  -> h update and g update
  -> TCLB streaming
```

The code anchor for the active stress/F_mu loop is:

```text
third_party/tclb_snapshots/stage17B_diffuse_solid_shadow/models/multiphase/d3q27_pf_velocity/Dynamics.c.Rt
  force loop around lines 3687-3714
  post-force velocity shadow around lines 4050-4088
```

B40 evidence at the first important force node:

```text
case = wall_60to30_10
Density_h = 1.0
Density_l = 0.005
step = 13
mask = low_rho
ijk = [93, 1, 5]
ForceOverRhoNorm = 2636.4146763472127
FmuNorm = 14.492372866456925
FpressureNorm = 0.022145923403073742
FsurfNorm = 8.358087817285956e-06
StressPreForceNorm = 383.3219828909969
StressPostForceNorm = 2029121.044003016
StressPostOverPreRatio = 5293.515985437302
first PhaseFromH OOB = step 20
```

Therefore the next work is not WallGhost tuning, curved compact write, dynamic
contact line, force cap promotion, or dynamic impact.

## Teacher MCP Decisions

Teacher MCP was consulted twice for this branch.

Decision 1:

```text
status = NEEDS_FIX
recommendation = split B41 into stress-source audit before active candidate
implementation
```

Decision 2:

```text
status = PASS
recommendation = B41 should reuse existing B40 stress-source AddField
diagnostics and should not modify the solver
```

Rationale:

```text
B40 already outputs:
  B40StressMomentRawNorm
  B40StressMomentRelaxedNorm
  B40StressIncomingRawNorm
  B40StressIncomingNeqPreNorm
  B40StressBGKPopNeqPreNorm
  B40StressPostForceNorm
  B40Fmu* candidates
  B40ForceOverRho* candidates
```

Adding duplicate B41 fields would only increase code clutter and compile risk.
B41 is a ranking/report stage.

## B41: Stress-Source Audit

Purpose:

```text
Rank the stress definitions already exposed by B40 instrumentation and decide
which stress sources deserve active default-off B42 implementation.
```

Implementation:

```text
scripts/stage14/run_stage14_b41_stress_source_audit_remote.sh
scripts/stage14/stage14_b41_stress_source_rank.py
```

Runtime:

```text
server = yuan@192.168.1.16
gpu = CUDA_VISIBLE_DEVICES=1
root = /mnt/usb1t/RUNS/runs/stage14_B41_stress_source_audit_20260628
case = wall_60to30_10
iterations = 20
vtk_period = 1
vtk_field_set = b40stress
binary = existing B40 binary
```

No TCLB source change is allowed in B41.

Pass condition:

```text
RC=0
all expected B40 stress-source fields present
B41 ranking JSON/CSV/MD generated
B42 candidate recommendation made
```

Fail condition:

```text
missing required stress fields
ranker cannot identify an implementable candidate
runtime fails before producing usable VTI
```

## B42: Default-Off Active Stress Candidates

Only after B41 passes, add active modes:

```text
FmuStressClosureMode = 3  candidate from pre-force moment/raw source
FmuStressClosureMode = 4  candidate from BGK population non-equilibrium source
```

Exact mapping is decided by B41 ranking. Defaults remain:

```text
FmuStressClosureMode = 0
```

B42 must not change:

```text
F_pressure
F_surf
F_body
h update
WallGhost
PhaseF write
default legacy behavior
```

Pass condition:

```text
compiles after full RT regeneration
20-step P100 gate completes
ForceOverRho step-13 reduced at least 10x vs B40 or delayed
StressPostOverPreRatio substantially reduced
PhaseFromH does not fail earlier than B40
no hidden cap/limiter is used as the success mechanism
```

Reject condition:

```text
candidate still crosses ForceOverRho around step 13 with comparable magnitude
candidate only works by suppressing force through a limiter
candidate changes legacy mode 0 behavior
```

## B43: F_mu Coefficient and Stress Definition Derivation

Purpose:

```text
Derive the coefficient that should multiply the selected stress source in the
MRT implementation, instead of guessing between current legacy scale and BGK
scale.
```

Current code:

```text
stage14_fmu_from_stress:
  scale = (0.5 - tau) * (Density_h - Density_l)
```

Open question:

```text
If stress already includes Omega relaxation, should F_mu use:
  (0.5 - tau)
  (0.5 - tau)/tau
  a moment-wise MRT relaxation factor
  or another coefficient derived from the discrete forcing scheme?
```

Output:

```text
Markdown derivation with code-variable mapping
explicit candidate scale modes
short runtime matrix comparing B42 selected source with derived scale
```

B43 cannot claim physical closure unless B44-B46 pass.

## B44: Short Stability Closure Gate

Purpose:

```text
Promote the best B42/B43 combination to a named default-off physical candidate
and test basic stability without contact-angle claims.
```

Gates:

```text
density ratio 200: wall_60to30_10, 100 steps
density ratio 1000: wall_60to30_10, 20 steps
```

Pass condition:

```text
RC=0
no NaN/nonfinite
PhaseFromH remains bounded without hard clamp
ForceOverRho does not show explosive growth
mass drift < 1% for the 100-step gate
```

## B45: Phase h-Update and Mass Closure

Purpose:

```text
After the force path is stable, revisit PhaseF -> tmp1/Fphi -> h update ->
PhaseFromH. B45 determines whether the remaining phase drift is a true h
equation problem or was downstream of force feedback.
```

Code anchor:

```text
Dynamics.c.Rt around h update:
  h = h - omega * (h - heq + 0.5*Fphi) + Fphi
```

Pass condition:

```text
h and PhaseFromH stay bounded without hard clamp
mass drift is below threshold
no unexplained Fphi/Heq cancellation blow-up
```

## B46: Flat-Wall Physical Wetting Gate

Only after B44 and B45 pass:

```text
static flat wall 30/90/150
decoupled wall 60->30
decoupled wall 120->150
spurious velocity audit
mass drift audit
```

Pass condition:

```text
decoupled cases move toward the target angle
static morphology agrees with measured angle
pure-phase spurious velocity is bounded
mass drift remains within threshold
```

This is the earliest stage where a limited flat-wall wetting claim may be
made. It is still not curved-wall validation or dynamic-impact readiness.

## B47: Curved-Wall Return Gate

Only after B46 passes:

```text
Stage17B cylinder shadow replay
Stage17B sphere shadow replay
controlled write planning
cylinder/sphere static contact-angle gates
```

Do not enter dynamic impact until:

```text
flat wall passes
cylinder passes
sphere passes
mass/spurious velocity gates pass
controlled write path is proven not to alter unrelated fields
```

## Global Stop Rules

Stop and re-plan with Teacher MCP if any of these occur:

```text
B41 cannot rank stress sources
B42 candidate changes legacy default behavior
B43 derivation contradicts the implemented stress definition
B44 stabilizes only by hard limiting force or phase
B46 angle response is decoupled from target wetting
B47 shadow/write changes PhaseF outside the intended wall band
```
