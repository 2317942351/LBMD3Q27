# Stage14-B34 MRT Algebra Harness

Date: 2026-06-27

Branch: `work/phasefield-c-reference-20260623`

Status: implemented locally. Runtime replay comparison waits for B33 argmax
traces because the first B33 remote run was interrupted by remote storage I/O
errors.

## Purpose

B34 checks the local MRT collision algebra used by the generated TCLB code. It
does not validate TCLB streaming, stage load/save, contact angle, or dynamic
impact.

The active MRT template in `Dynamics.c.Rt` is:

```text
mF[2:4] = momentum_force_injection_scale * F_total * force_rho_inv
m = m0 - (m0 - EQ$Req + 0.5*mF)[selR] * Omega + mF
g = invM %*% m
```

The corresponding half-force velocity is:

```text
U = m0[2:4] + 0.5 * F_total * force_rho_inv
```

## Files

```text
scripts/stage14/stage14_b34_mrt_algebra_harness.py
scripts/stage14/stage14_b34_mrt_replay_compare.py
artifacts/stage14_B34_mrt_algebra_harness_20260627/b34_default_smoke.json
```

## Local Smoke Result

Input:

```text
m0 = [1, 0, 0, 0, ...]
Req = [1, 0, 0, 0, ...]
F_total/rho = [0.01, -0.02, 0.03]
tau = 0.3
injection_scale = 1
```

Result:

```text
mF[1:3] = [0.01, -0.02, 0.03]
momentum_after_g = [0.005, -0.01, 0.015]
momentum_delta_g = [0.005, -0.01, 0.015]
```

Therefore, with the current MRT formula and `Omega=1` on the momentum rows,
the single-node algebra predicts:

```text
ReplayMomentumDeltaG ~= 0.5 * ReplayMF
```

This does not by itself prove a bug. It means B34 must compare this local
prediction against B33 replay fields at the first-bad nodes:

```text
ReplayMF
ReplayMomentumDeltaG
ReplayMomentumAfterG
ReplayM0
```

## Why This Matters

The model also uses half-force velocity:

```text
U = m0 + 0.5 * F/rho
```

If the population update also contributes only half of `F/rho`, the next-step
macro momentum may be consistent with one convention. If it contributes an
additional unexpected half or misses a needed half, the failure can look like a
stress/F_mu numerator problem while actually being a force-insertion convention
problem.

That is why B34 must be performed before any B36 physics repair.

## Next Runtime Comparison

After B33 completes and preserves `b33_argmax_trace.json`, run:

```text
python scripts/stage14/stage14_b34_mrt_replay_compare.py \
  artifacts/.../L0_full/b33_argmax_trace.json \
  --out artifacts/.../b34_replay_compare.json
```

Pass criterion:

```text
max_abs(ReplayMomentumDeltaG - 0.5*ReplayMF) <= tolerance
```

If the comparison fails, B35/B36 must not change `F_surf` or `F_mu` first.
The next branch would be MRT force insertion or replay-field timing.

## Teacher MCP Follow-Up

Teacher MCP reviewed the implemented B32.5/B34/B35 state and returned
`NEEDS_FIX`: B34 replay comparison now has higher priority than B35 physical
candidate work. The reason is that the local algebra already predicts a
specific replay relation:

```text
ReplayMomentumDeltaG ~= 0.5 * ReplayMF
```

If actual TCLB replay fields do not satisfy this at B33 first-bad nodes, the
next branch is force insertion or replay timing, not `F_surf/F_mu` physics.

## Historical Artifact Fallback

A temporary attempt was made to use existing B18 artifacts:

```text
artifacts/stage14_B18_shadow_closure_20260625/b18_argmax_trace.json
```

The comparison produced:

```text
record_count = 0
```

because the old argmax trace did not co-locate raw vector values for:

```text
ReplayMF
ReplayMomentumDeltaG
ReplayMomentumAfterG
ReplayM0
```

This is why B33 must be rerun with the updated analyzer. The analyzer now
includes those raw vectors in `COLOCATE_FIELDS`; old B18/B27/B32 summaries
cannot substitute for B33/B34.
