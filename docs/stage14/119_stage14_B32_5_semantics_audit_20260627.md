# Stage14-B32.5 TCLB Semantics Audit

Date: 2026-06-27

Branch: `work/phasefield-c-reference-20260623`

Status: completed. Static source audit passed with warnings.

## Purpose

B32.5 was inserted after Teacher MCP pre-review of the B33-B40 campaign. The
goal was to avoid misreading a TCLB stage/load or AddDensity/AddField timing
issue as a force-closure formula issue.

This is not a runtime result. It does not validate contact angle, curved
wetting, or dynamic impact.

## Artifact

```text
artifacts/stage14_B32_5_semantics_audit_20260627/
```

Generated files:

```text
stage14_B32_5_semantics_audit.json
stage14_B32_5_semantics_audit.md
```

## Verdict

```text
semantics_audit_pass_with_warnings
```

## Key Code Findings

| Check | Result | Meaning |
|---|---|---|
| `pnorm/U/V/W` primary state | warning | Primary state is `AddDensity`, but conditional OutFlow helper `AddField(name="U", dx=...)` exists and is recorded. This does not block B33 because current wall probes are not OutFlow cases. |
| Replay/Bxx diagnostics | pass | `ReplayMu`, `ReplayLapPhi`, `ReplayGradPhiX`, `ReplayFsurfX`, `ReplayFmuX`, `ReplayFtotalX`, `ReplayForceOverRhoX`, `B18ProbeActive`, `B21ProbeActive`, `B22ProbeActive` are `AddField`, not streamed densities. |
| Stage14 settings | pass | `ReplayDiagnosticsMode`, `MomentumClosureDiagnosticsMode`, `Stage14B18ClosureDiagnosticsMode`, `Stage14B21HPopulationAuditMode`, `Stage14B22VelocityProducerAuditMode`, `MomentumForceMode`, `FmuStressClosureMode`, `PressureClosureMode`, `ForceDensityClosureMode`, `ForceFixedPointMode` exist. |
| `CollisionMRT` order | pass | Source order is `PhaseF -> calcMu -> m0 -> pressure input -> calcGradPhi -> F_pressure/F_surf -> F_mu -> F_total -> half-force U -> h update -> MRT mF/g update -> momentum-after-g replay`. |
| MRT/BGK `F_mu` prefactor | warning | MRT uses `(0.5-tau)` while BGK uses `(0.5-tau)/tau`; keep as B35 branch, do not change in B32.5/B33. |
| boundary sentinel | pass | `SPECIAL_POINT_HUGE_MAGIC_NUMBER = -999.0` is present. |

## Important Source Anchors

`Dynamics.R`:

```text
AddDensity pnorm/U/V/W: lines 27-30
Replay/Bxx AddField diagnostics: lines 224-507
Stage14 settings: lines 1062-1078
geometric Iteration action: line 664
```

`Dynamics.c.Rt`:

```text
CollisionMRT start: line 2957
PhaseF consumed: line 2959
calcMu(C): line 2971
m0 from streamed g: line 3012
pressure input: line 3059
calcGradPhi: line 3092
calc_Fp/calc_Fs: lines 3130-3132
MRT F_mu: line 3176
F_total assembly: line 3193
half-force velocity: line 3332
h update: line 3957
MRT mF insertion and g update: lines 3975-3978
momentum-after-g replay: line 4009
```

## Consequence For B33

B33 can proceed without changing TCLB physical code. It should use existing
`AddField` diagnostics plus a richer `b33ledger` VTI field set to co-locate the
first bad cell.

B33 must still treat these warnings as active risks:

1. OutFlow helper fields mean any future OutFlow case needs a separate
   streaming semantics audit.
2. The MRT/BGK `F_mu` prefactor mismatch is a real B35 candidate branch.

## Claim Limit

Allowed:

```text
B32.5 static semantics audit passed with warnings.
```

Forbidden:

```text
runtime stability proven
contact angle validated
dynamic impact preflight passed
```
