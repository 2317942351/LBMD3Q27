# Teacher MCP Review Summary for Stage14 B43-B47

Date: 2026-06-28

Teacher session: `session-20260628-e8c21d`

Mode: `runtime_diagnostic`

Status returned by Teacher: `NEEDS_FIX`

## Evidence Sent

```text
B43 focus step 13:
  legacy low-rho F/rho = 2636.41
  legacy_hundredth low-rho F/rho = 30.2118
  legacy_tenth low-rho F/rho = 267.123
  status = postprocess only, no solver writeback

B44:
  legacy_hundredth net/term = 0.94652
  legacy_hundredth F_mu fraction = 0.766663
  legacy_tenth net/term = 0.932978
  legacy_tenth F_mu fraction = 0.970463

B45:
  PhaseFromH OOB step = 3
  HPost OOB step = 4
  F/rho > 100 step = 13
  F/rho > 1000 step = 13
```

## Teacher Verdict

Teacher agreed that B46/B47 should be blocked:

```text
B45 phase gate fails. The root cause appears to be in the
h-population / PhaseFromH streaming / time-level closure, not just force
magnitude.
```

Teacher also agreed that postprocess scale-down cannot be treated as a solver
physical repair:

```text
B43/B44 scaling helps force metrics but cannot fix the phase-field blow-up.
```

## Required Next Action

```text
Run a focused B48 diagnostic probe over steps 0-4:
  full h population producer-consumer timeline
  macroscopic h / PhaseFromH
  first OOB cells
  phase-field gradients and forcing at those cells
```

## Guardrail

```text
Do not execute B46 flat-wall contact-angle validation or B47 curved-wall
validation until B45 passes a boundedness gate.
```
