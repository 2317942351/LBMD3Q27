# Stage14 B33-B40 Completion Audit

Date: 2026-06-28

Branch: `work/phasefield-c-reference-20260623`

Status: completion audit for the B33-B40 force-closure campaign. This document
does not claim contact-angle validation, curved wetting validation, or dynamic
impact readiness.

## Scope Audited

The audited objective is the Stage14 B33-B40 force-closure campaign:

```text
plan each stage from code evidence
implement required diagnostics/candidates
run the short gates on the P100 server
use Teacher MCP for high-risk branch decisions
write reviewable reports
push the resulting code, reports, and lightweight artifacts to GitHub
```

B41 is intentionally outside this completion audit. B41 is the next work item
selected by B40.

## Current Repository Evidence

Git state checked after upload:

```text
branch = work/phasefield-c-reference-20260623
HEAD   = 4b46c1f35dffe59485694a7ad90fa2b2805c14d7
origin/work/phasefield-c-reference-20260623 = 4b46c1f35dffe59485694a7ad90fa2b2805c14d7
commit = stage14 audit force stress closure through B40
```

Server state checked after reboot:

```text
server = yuan@192.168.1.16
host = HM570
/mnt/usb1t available = about 248G
P100 GPU 1/2 idle at check time
current binary sha256 = de2e77d723f5a52dfb2734e0c8fe9eef15caa092fbc91e1cf6367bdb3bcd4c43
B40 final run status = OVERALL_RC=0, VERDICT=b40_stress_construction_audit_complete
```

## Important B33 Clarification

`docs/stage14/121_stage14_B33_remote_io_blocker_20260627.md` remains true:
the original B33 first-bad-cell ledger run on `/mnt/usb1t` was interrupted by
remote storage I/O errors. That run is not numerical evidence and must not be
used to support any physics claim.

The campaign did not hide or overwrite that failed operational state. Instead,
the later stages narrowed and completed the intended diagnostic chain through:

```text
B34MRT lightweight replay matrix
B38 first-bad force ledger retry
B39 F_mu stress mode matrix
B40 stress construction audit
```

Therefore the valid statement is:

```text
B33 as originally launched was an operations blocker.
The first-bad/replay diagnostic function required by the campaign was later
closed by B34MRT and B38, not by pretending the original B33 run succeeded.
```

This distinction is important for later reviewers.

## Stage-by-Stage Audit

### B33: First-Bad Ledger Attempt

Evidence:

```text
docs/stage14/121_stage14_B33_remote_io_blocker_20260627.md
scripts/stage14/run_stage14_b33_first_bad_ledger_remote.sh
scripts/stage14/stage14_s2_replay_smoke.py
```

Result:

```text
operational blocker, not a numerical verdict
```

What was still useful:

```text
1. The runbook and field set defined the required first-bad fields.
2. The runner was corrected so future B33-style runs do not hardcode the USB root.
3. The B33 failure forced the campaign to use smaller B34MRT/B38 evidence paths.
```

Completion status:

```text
complete as documented blocker and superseded diagnostic route
```

### B34: MRT Replay Algebra Gate

Evidence:

```text
docs/stage14/120_stage14_B34_mrt_algebra_harness_20260627.md
docs/stage14/124_stage14_B34MRT_replay_correction_and_B35_branch_20260627.md
artifacts/stage14_B34_mrt_algebra_harness_20260627/
artifacts/stage14_B34MRT_runtime_compare_20260627/
artifacts/stage14_B34MRT_matrix_20260627/
scripts/stage14/stage14_b34_mrt_algebra_harness.py
scripts/stage14/stage14_b34_mrt_replay_compare.py
```

Key result:

```text
ReplayMomentumDeltaG ~= 1.0 * ReplayMF
```

This corrected the earlier half-force expectation. The generated TCLB code uses
half-force velocity in the equilibrium momentum row and then adds the explicit
force moment, so full `ReplayMF` is the correct local replay relation.

Important matrix results:

```text
L0_full filtered replay: 1093/1093 pass
L1_noFmu filtered replay: 1260/1260 pass
L2_noSurf filtered replay: 1260/1260 pass
L3_noPressure filtered replay: 1094/1094 pass
L4_zeroForce filtered replay: 1260/1260 pass
```

Teacher MCP:

```text
session-20260627-0f3298
status = PASS
decision = close MRT force insertion as primary root cause under this gate
```

Completion status:

```text
complete
```

### B35: Coupled Numerator Split

Evidence:

```text
docs/stage14/125_stage14_B35_coupled_numerator_split_20260628.md
artifacts/stage14_B35_coupled_numerator_split_20260628/
scripts/stage14/run_stage14_b35_coupled_numerator_split_remote.sh
scripts/stage14/compile_stage14_b35_after_source_remote.sh
```

Code-level additions are default-off diagnostics:

```text
Stage14B35CoupledNumeratorDiagnosticsMode
Stage14B35MuAbsCap
Stage14B35GradPhiCap
```

Result:

```text
B35 selected a force/stress/low-density amplification branch.
It did not repair the solver and did not change legacy behavior by default.
```

Completion status:

```text
complete
```

### B36: Force-Over-Rho Cap Candidate

Evidence:

```text
docs/stage14/126_stage14_B36_force_over_rho_cap_rejected_20260628.md
artifacts/stage14_B36_force_over_rho_cap_20260628/
scripts/stage14/run_stage14_b36_force_cap_remote.sh
scripts/stage14/stage14_b36_force_cap_gate.py
```

Code-level additions:

```text
Stage14B36ForceOverRhoLimiterMode
Stage14B36ForceOverRhoCap
```

Result:

```text
rejected repair candidate
```

Reason:

```text
The cap can bound written F/rho in selected modes, but the upstream pre-cap
force still grows. This makes it a limiter, not a root-cause repair.
```

Completion status:

```text
complete
```

### B37: GradPhi Force-Consumer Cap Candidate

Evidence:

```text
docs/stage14/127_stage14_B37_grad_phi_cap_rejected_20260628.md
artifacts/stage14_B37_grad_phi_cap_20260628/
scripts/stage14/run_stage14_b37_grad_cap_remote.sh
scripts/stage14/stage14_b37_grad_cap_gate.py
```

Code-level additions:

```text
Stage14B37GradPhiCapMode
Stage14B37GradPhiCap
```

Result:

```text
rejected repair candidate
```

Reason:

```text
cap_hit_fraction = 0.0 at first onset
```

The excessive-force branch is not caused by an excessive `|gradPhi|` cap event
at the first bad step.

Completion status:

```text
complete
```

### B38: First-Bad Force Ledger

Evidence:

```text
docs/stage14/128_stage14_B38_first_bad_force_ledger_plan_20260628.md
docs/stage14/129_stage14_B38_first_bad_force_ledger_result_20260628.md
artifacts/stage14_B38_first_bad_force_ledger_20260628/
artifacts/stage14_B38_first_bad_force_ledger_retry_20260628/
scripts/stage14/run_stage14_b38_first_bad_force_ledger_remote.sh
scripts/stage14/stage14_b38_first_bad_ledger_digest.py
```

Run status:

```text
OVERALL_RC=0
VERDICT=b38_first_bad_ledger_complete
```

Key selected node:

```text
step = 15
mask = low_rho
ijk = [14, 1, 14]
ForceOverRhoNorm = 885434.9865443383
FmuNorm = 4427.203279090591
FsurfNorm = 8.077141293655088e-06
FpressureNorm = 0.02434348887518085
StressPostOverPreRatio = 800542780.2391785
```

Result:

```text
fmu_stress_timelevel_branch
```

Completion status:

```text
complete
```

### B39: F_mu Stress Mode Matrix

Evidence:

```text
docs/stage14/130_stage14_B39_fmu_stress_mode_matrix_plan_20260628.md
docs/stage14/131_stage14_B39_fmu_stress_mode_matrix_result_20260628.md
artifacts/stage14_B39_fmu_stress_mode_matrix_20260628/
scripts/stage14/run_stage14_b39_fmu_stress_mode_matrix_remote.sh
```

Important status nuance:

```text
Remote OVERALL_RC=3 was caused by a postprocess prefix bug.
GPU runs and analyzers completed for all three modes.
The prefix bug was fixed locally and existing outputs were re-digested without
rerunning GPU.
```

Matrix result:

```text
FmuStressClosureMode = 0 legacy          rejected
FmuStressClosureMode = 1 freeze iter1    rejected
FmuStressClosureMode = 2 incoming neq    rejected
```

Teacher MCP:

```text
B39 plan approved by B38 evidence and Teacher MCP review.
```

Completion status:

```text
complete as rejected-mode matrix, not as repair
```

### B40: Stress Construction Audit

Evidence:

```text
docs/stage14/132_stage14_B40_stress_construction_audit_plan_20260628.md
docs/stage14/133_stage14_B40_stress_construction_audit_result_20260628.md
artifacts/stage14_B40_stress_construction_audit_20260628/
scripts/stage14/run_stage14_b40_stress_construction_audit_remote.sh
scripts/stage14/compile_stage14_b40_stress_audit_remote.sh
```

Run status:

```text
OVERALL_RC=0
VERDICT=b40_stress_construction_audit_complete
```

Code-level additions:

```text
Stage14B40StressAuditMode
B40StressMomentRawNorm
B40StressMomentRelaxedNorm
B40StressIncomingRawNorm
B40StressIncomingNeqPreNorm
B40StressBGKPopNeqPreNorm
B40StressPostForceNorm
B40Fmu* shadow fields
B40ForceOverRho* shadow fields
```

Key selected node:

```text
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
first PhaseFromH out-of-bounds = step 20
```

Result:

```text
B40 branch = post_force_shadow_amplification
primary branch = stress_timelevel_or_fixed_point_feedback
```

Teacher MCP:

```text
status = PASS
confidence = 0.90
recommendation = proceed to default-off B41 pre-force / consistent
                 non-equilibrium stress candidate
```

Completion status:

```text
complete
```

## Static Checks

The final pushed state was checked with:

```text
python -m py_compile scripts/stage14/stage14_s2_replay_smoke.py
python -m py_compile scripts/stage14/stage14_b17_onset_mask_argmax.py
python -m py_compile scripts/stage14/stage14_b23_b24_matrix_digest.py
python -m py_compile scripts/stage14/stage14_b38_first_bad_ledger_digest.py
python -m py_compile scripts/stage14/stage14_b36_force_cap_gate.py
python -m py_compile scripts/stage14/stage14_b37_grad_cap_gate.py
git diff --check
```

Result:

```text
py_compile passed
git diff --check reported only CRLF normalization warnings, not whitespace errors
```

## GitHub Upload Policy

Uploaded:

```text
code changes
stage scripts
reports
run logs
status files
key summaries
field-presence JSON
first-onset JSON
mask statistics CSV
digest JSON/Markdown
```

Intentionally not uploaded:

```text
VTI/PVTI raw fields
tar/gz archives
pycache/pyc
temporary Teacher MCP argument/context JSON
large *_argmax_trace.json files ignored by .gitignore
```

The review entry point is:

```text
docs/stage14/135_stage14_B35_to_B41_github_review_handoff_20260628.md
```

## Final Campaign Conclusion

The completed B33-B40 campaign proves this narrower result:

```text
The next actionable root-cause branch is not WallGhost, curved wetting, contact
angle response, force/rho capping, gradPhi capping, or MRT force insertion.
The next branch is stress/F_mu time-level and fixed-point feedback.
```

The selected next action is B41:

```text
default-off pre-force / consistent non-equilibrium stress candidate for F_mu
```

Forbidden claims remain:

```text
contact-angle validation passed
curved-wall wetting solved
dynamic impact ready
solver fixed
```
