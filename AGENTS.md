# TCLB Project Rules

This folder is independent from `D3Q27/` and parent legacy LBM routes.

## Scope

Use TCLB as the main external production-code candidate for:

```text
high-density-ratio phase-field multiphase LBM
droplet impact on dry wall and liquid film
contact-angle variation
publication-style comparison metrics
```

The active TCLB model is:

```text
/home/yuan/src/TCLB/models/multiphase/d3q27_pf_velocity
```

## Evidence Boundary

- Wang 2023 IJMF is a comparison and validation literature source.
- Fei 2019 PoF is non-orthogonal MRT and dry-wall impact comparison evidence,
  but it uses a pseudopotential route, not the same TCLB phase-field model.
- TCLB `d3q27_pf_velocity` is closest to the Fakhari/Mitchell phase-field
  high-density-ratio route and must be validated on its own standard cases.
- Do not claim equivalence between TCLB and Wang 2023 ULBM(NMRT) unless a
  separate formula and numerical audit proves it.

## Required Claim Discipline

Exploratory runs may demonstrate:

```text
runtime stability
configuration feasibility
postprocessing and visualization pipeline
first-order trends
```

They must not be described as:

```text
validated physical prediction
Wang 2023 reproduction
publication-ready result
grid-converged result
verified high-We result
```

Execution output and conclusion authorization are separate. Execution agents
may produce commands, files, metrics, figures, and observations. Validation,
production, or publication-grade conclusions require main-agent integration
and a read-only audit result.

Use only these status labels:

```text
exploratory_not_validation
runtime_sanity
validation_candidate
validation_passed
production_candidate
publication_ready
failed_negative_evidence
```

## Before Publication-Level Claims

Any dry-wall or film-impact claim needs:

```text
fixed case definition
fixed beta extraction rule
mass conservation report
max Mach report
nonfinite/failcheck report
grid/time-step sensitivity
at least one literature data comparison case
clear contact-angle convention
```

## Forbidden Shortcuts

Do not hide numerical failure with clipping, unreported damping, pressure
shifts, force cancellation, selective frame choice, or cherry-picked samples.

## Subagent Workflow

For long TCLB execution, follow:

```text
docs\subagent_goal_operating_model.md
```

Required roles:

```text
main agent: plans, integrates, and owns final claims
execution agent: runs cases and produces bounded artifacts only
audit agent: read-only review before any validation/production claim
experience-skill agent: records durable fixes and repeated failure modes
file-index agent: maintains remote/local path and artifact provenance
```

Audit is mandatory before promoting any result from exploratory to validation
or production, before using Wang 2023/Fei 2019/TCLB benchmark comparisons as
proof, and before writing paper-facing figures or tables.
