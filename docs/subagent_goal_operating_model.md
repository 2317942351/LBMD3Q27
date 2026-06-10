# TCLB Subagent And Goal Operating Model

Date: 2026-06-07

Purpose: define how future long TCLB work should be executed without losing
context or repeating the same mistakes. This document is the local authority
for subagent roles in `C:\Users\yuanz\Desktop\LBMCORE5\TCLB`.

## Goal-Mode Start Rule

For a new conversation, start with a goal like:

```text
Goal: execute the TCLB rho_ratio=772 droplet-impact project to publication-grade
validation and target simulations, following
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\docs\subagent_goal_operating_model.md.
Use subagents: execution, audit, experience-skill, and file-index.
Do not claim validation until the validation protocol passes.
```

The main agent must first read:

```text
TCLB\README.md
TCLB\AGENTS.md
TCLB\docs\tclb_project_handoff.md
TCLB\docs\tclb_path_index.md
TCLB\docs\literature_case_matrix.md
TCLB\docs\target_physical_case_plan.md
TCLB\docs\validation_and_output_protocol.md
TCLB\docs\implementation_backlog.md
TCLB\docs\remote_local_file_index.md
TCLB\docs\subagent_goal_operating_model.md
```

## Roles

### Main Agent

Responsibilities:

```text
owns the goal and final claims
plans phases and acceptance gates
spawns and coordinates subagents
integrates execution results
decides when audit is required
updates handoff and index docs
keeps validation claims conservative
```

The main agent must not outsource final route claims or acceptance decisions.
It must also keep execution output and conclusion authorization separate:
execution agents can generate evidence, but only the main agent after audit can
state that a validation or production gate passed.

### Execution Agent

Responsibilities:

```text
implements bounded tasks
runs TCLB cases on HM570
creates or modifies case XML/templates/scripts within assigned paths
reports commands, paths, return codes, first failure metrics, and artifacts
```

Restrictions:

```text
must not claim physical validation
must not claim publication-ready result
must not claim Wang 2023 reproduction
must not claim TCLB equals Wang 2023 ULBM(NMRT)
must not claim grid convergence
must not claim mass-conservative rho_ratio=772
must not claim high-We for the 1 mm / 10 mm free-fall target
must not claim run-to-rest unless the window criteria pass audit
must not change validation thresholds without audit
must not hide failures with clipping, damping, pressure shifts, or sample selection
must not overwrite unrelated remote runs or local artifacts
```

Typical write scopes:

```text
TCLB\cases\<assigned_case>\
TCLB\scripts\<assigned_script>
TCLB\artifacts\<assigned_case>\
remote /home/yuan/runs/<assigned_run_name>
```

### Audit Agent

Responsibilities:

```text
read-only review of methods, claims, and gate transitions
checks whether results support the proposed statement
checks mass/Mach/grid/contact-angle/literature comparison risks
recommends next gate or rollback to exploratory status
```

Audit must stay read-only unless the user explicitly changes the role.

### Experience-Skill Agent

Responsibilities:

```text
extract repeated operational mistakes and durable fixes
turn them into short local project rules
recommend updates to TCLB\docs\experience_log.md or the TCLB skill
avoid long chronological logs
```

This role exists to prevent context-loss errors during long execution. It does
not replace the main handoff or final audit.

Examples of items it should record:

```text
VTK cell data order is x-fastest, then y, then z
do not use global VelocityZ as publication-grade droplet-only velocity
create analysis directories before redirecting postprocess stdout
P100 memory limits make full 10D free-fall expensive
```

### File-Index Agent

Responsibilities:

```text
maintains local/remote path map
records what exists, where, and whether it is source, config, run output, or artifact
records which large files remain remote-only
prevents loss of successful results after failures
```

Primary document:

```text
TCLB\docs\remote_local_file_index.md
```

## Mandatory Audit Triggers

Run a read-only audit before:

```text
claiming validation or publication readiness
promoting exploratory -> validation -> production
writing dry-wall, film-impact, or contact-angle conclusions into README/handoff/paper artifacts
changing beta, mass, Mach, or resting-state criteria
changing wall/contact-angle/wetting interpretation
changing physical scaling or claiming high-We status
switching from x-wall pilot to z-wall target production
using global velocity as a substitute for droplet-only velocity
starting large R0 >= 32 production runs
using a literature case as quantitative validation
submitting or freezing paper figures/tables
```

Run a read-only audit immediately when these risk signals appear:

```text
nonfinite values
max Mach near or above 0.1
large mass drift
axis, wall-normal, or VTK reshape reinterpretation
clipping, damping, pressure patching, force cancellation, or other shortcut pressure
```

Run an experience-skill review after:

```text
the same command class fails twice
a wrong axis/wall/reshape interpretation is discovered
a remote run succeeds but postprocessing fails
an environment/path issue costs significant time
a workaround becomes part of the standard workflow
```

Run a file-index review after:

```text
any successful remote run
any artifact copy to local
any new reference or extracted document is added
any case template or script becomes canonical
```

## Claim Levels

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

Only the main agent may promote a status, and only after audit for
`validation_passed`, `production_candidate`, or `publication_ready`.

## New Conversation Prompt

Use this prompt when starting a new goal-mode conversation:

```text
Use C:\Users\yuanz\Desktop\LBMCORE5\TCLB as the active project. Follow
TCLB\AGENTS.md and TCLB\docs\subagent_goal_operating_model.md. Work in goal
mode. Main agent plans and integrates. Use subagents for execution, read-only
audit, experience-skill capture, and file-index maintenance. Current final
target: rho_ratio=772, D=1 mm, H=10 mm free-fall equivalent, gravity -z,
dry-wall/liquid-film impact, contact angles 45/90/135, run to rest, output
beta(t), beta_max, mass, Mach, and morphology. Remember this target is
We≈2.7 for 10 mm free fall, not high-We. Do not claim validation until
TCLB\docs\validation_and_output_protocol.md and literature comparisons pass.
```

The prompt must explicitly include:

```text
active project root
remote TCLB source and commit
target physical case
current claim status
subagent roles
mandatory metrics
Mach guard and mass target
1 mm / 10 mm We caveat
artifact provenance requirement
forbidden equivalence and validation claims
```
