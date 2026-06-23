# Current Stage Index

## Current Baseline: Phase-Field Rebuild (2026-06-23)

Status: `audit_baseline / exploratory_not_validation`.

The current working baseline is defined by:

```text
docs/stage14/56_phasefield_rebuild_baseline_20260623.md
docs/stage14/57_mcmp_c_reference_bridge_20260623.md
docs/stage14/55_tclb_execution_semantics_constraints_20260623.md
docs/stage14/58_phasefield_rebuild_execution_plan_20260623.md
docs/stage14/59_current_progress_and_next_solver_targets_20260623.md
docs/stage14/60_stage18_p100_semantics_smoke_20260623.md
```

Branch:

```text
stage15-dynamicCL-residual
```

Baseline tag:

```text
baseline/phasefield-rebuild-20260623
```

Current decision:

```text
inherit flat-wall calibrated compact-ghost evidence and diagnostic tooling
inherit the flat-only compact-write safety gate
freeze DynamicCL, WallGhostV2, direct curved compact-write, and old-BC curved claims
use external MCMP C++ codes only as structural references, not as phase-field physics
build a minimal phase-field C/C++ reference or equivalent TCLB semantics map before
new solver physics edits
```

Current extension on branch `work/phasefield-c-reference-20260623`:

```text
reference_solvers/phasefield_d3q27_c now contains an executable C++ scaffold
server g++ self-test passed with checks=96 failures=0
scripts/audit_tclb_execution_semantics.py extracts TCLB density/field/stage risks
remote P100/storage audit summaries are under artifacts/remote_space_audit_20260623
stage18 P100 smoke: flat and corrected z-axis cylinder runtime chains run; old axis=0 cylinder template fails with P NaN
no solver physics has been changed yet on this branch
```

The rest of this file preserves earlier stage history and should not be read as
the current modification authority.

Status: `runtime_sanity / exploratory_not_validation`.

Current diagnostic lane:

1. Stage8c: local wall-angle and wall-normal transfer for fluid-boundary gradient candidates.
2. Stage8d: sphere shadow limiter attribution; limiter hits concentrated in the sphere 11 degree region.
3. Stage8e: normal-residual-only wetting candidate; vector limiter removed, but normal limiter remains high.
4. Stage8f: normal-limiter root-cause attribution; diagnostic-only, not a fix.
5. Stage8g: cap-contract / low-angle regularization shadow diagnostic; completed short shadow gates only.
6. Stage8h: contact-relation and profile-path audit; shadow-only diagnostic route.

Do not treat any Stage8 lane as PRE reproduction, validation, production fix, or publication-ready evidence.

Current Stage8f result:

```text
vector limiter fraction = 0 in final flat and sphere shadow frames
flat wall low-angle normal limiter falls from 88.78% at wall005 to 0% at wall025/wall030
z48 sphere free-sphere normal limiter fraction = 85.28%
z48 sphere cap-on-sphere normal limiter fraction = 73.04%
outer90 normal limiter count = 0 in both sphere shadows
classification = low-angle tan amplification plus current normal-cap contract;
                 initial geometry stress contributes but is not sufficient
```

Current evidence does not support entering sphere write mode. Stage8g is
complete as a shadow diagnostic and did not pass the sphere write gate. The
current implementation route is Stage8h, a contact-relation and profile-path
audit that remains shadow-only.

Current write boundary:

```text
Stage8OperatorMode=2 sphere write remains forbidden.
No sphere 50k, 200k, 400k, or 600k Stage8f/Stage8g/Stage8h run is authorized by this index.
No Stage8g or Stage8h write run is authorized until a separate post-shadow gate
is defined and passed.
```

Stage8g completed gate:

```text
flat low-angle shadow: wall005/008/011/015/020/025/030, Stage8gMode=0/1/2/3
sphere z48 shadow: free-sphere and approximate cap-on-sphere initializers,
                   Stage8gMode=0/1/2/3
all Stage8g cases: Stage8OperatorMode=1, outputs at 0/100/1000 only
```

Current Stage8g result:

```text
build/source rc = 0/0
flat cases = 28/28 completed, nonfinite_total=0, vector_limiter_fraction=0
sphere cases = 8/8 completed, nonfinite_total=0, vector_limiter_fraction=0
best sphere cap-on-sphere mode3 normal_limiter_fraction = 45.64%
best sphere free-sphere mode3 normal_limiter_fraction = 77.06%
outer90/fallback limiter hits = 0 in all sphere cases
decision = Stage8g shadow improves diagnosis but does not pass sphere write gate
```

Therefore:

```text
Stage8OperatorMode=2 sphere write remains forbidden.
No Stage8g sphere 50k/200k/400k/600k run is authorized.
Next route is Stage8h audit/diagnostic, not a hidden Stage8g write.
```

Current Stage8h route:

```text
purpose = contact-relation and wall-profile-path shadow audit
baseline = Stage8gMode=3
Stage8hMode = 0/1/2/3/4
flat cases = wall005/008/011/015/020/025/030, 35 cases
sphere cases = free-sphere and cap-on-sphere initializers, 10 cases
all Stage8h cases: Stage8OperatorMode=1, outputs at 0/100/1000 only
write flag = WallStage8hWriteAllowedFlag fixed at 0
```

Stage8h planning criteria:

```text
nonfinite_total = 0
outer90/fallback Stage8h limiter-equivalent hits = 0
vector_limiter_fraction = 0
candidate demand p50 < 1.2
candidate demand p95 < 3.0
sphere cap-on-sphere Stage8h limiter-equivalent < 10-15%
flat wall020/wall025/wall030 remain benign
```

Until these data exist and pass read-only audit:

```text
Stage8OperatorMode=2 sphere write remains forbidden.
No Stage8h sphere 50k/200k/400k/600k run is authorized.
```

Stage8h completed shadow run:

```text
flat cases = 35/35 completed
sphere z48 shadow cases = 10/10 completed
postprocess pool workers = 20 on a 40 physical-core dual-socket Xeon Gold 6230 host
postprocess errors = 0
raw VTI/PVTI/PRI/VTK remaining in copied artifacts = 0
nonfinite_total = 0 for all completed Stage8h cases
vector_limiter_fraction = 0 for all completed Stage8h cases
```

Stage8h shadow decision:

```text
Stage8hMode 1, 2, and 4 substantially reduce sphere candidate demand compared
with Stage8hMode 0/3 baseline.

Best shadow mode is Stage8hMode 4:
  max sphere Stage8h limiter-equivalent fraction = 0
  max sphere candidate-demand p50 = 0.115
  max sphere candidate-demand p95 = 0.201
  outer90/fallback Stage8h limiter-equivalent counts = 0

This is planning evidence for a separate short write-gate proposal only.
It is not validation and does not authorize sphere Stage8OperatorMode=2 yet.
```

## Stage9 (new, 2026-06-14): analytic-geometry diffuse-interface wetting BC

Status: `exploratory_not_validation`.

Stage9 abandons the stage7/8 limiter-relaxation approach and replaces the root
cause directly: the wetting boundary condition now uses the **analytic** wall
normal and signed distance for parameterisable solids (plane, cylinder,
sphere), instead of the lattice-recovered normal that introduced the sign-flip
and the 392 special points on the theta030 sphere.

Stage9 is built from `upstream_base` (not from stage8h), so all stage5/6/7/8
diagnostic machinery is removed from the write path. The new path is:

```text
source = third_party/tclb_snapshots/stage9_analytic_wetting_diffuse_interface/
patch  = third_party/tclb_snapshots/patches/stage9_analytic_wetting_diffuse_interface_20260614.diff
design = docs/stage9/analytic_wetting_bc_design_20260614.md
cases  = cases/diagnostics/stage9_analytic_wetting_20260614/
```

Key source changes vs upstream:

```text
- removed SetOptions(permissive.access=TRUE) in Dynamics.R
- added WallGhost, WallH, AnalyticFlag fields (separate from PhaseF)
- added analytic geometry primitives: plane/cylinder/sphere normal + distance
- added diffuse-interface wetting BC stage9_calc_wall_ghost with O(h^2/R)
  curvature correction
- Init_wallNorm tags analytic nodes and overwrites nw_* with the analytic unit
  normal, clearing legacy special-point flags on analytic nodes
- calcWallPhase takes an early analytic branch that writes WallGhost and
  mirrors the fluid value into PhaseF (replaces -999 on analytic nodes)
```

The analytic path is fully opt-in: `AnalyticWetting=0` (default) leaves all
behaviour identical to upstream TCLB. No unmodified case is affected.

Stage9 gates (not yet run; this is the plan):

```text
gate A = plane theta030/090/150 regression (analytic normal = lattice normal)
gate B = sphere theta030 1000-step smoke (special points -> 0, angle in [28,32])
gate C = sphere theta030 200000-step long (H1-H2 < 5%, angle in [28,32])
gate D = cylinder theta030/090 (curved-wall wetting)
gate E = dynamic plane impact theta090 (post-validation extension)
```

Stage9 does NOT authorise:

```text
validation, production, or publication-ready claims
promotion of any stage5/6/7/8 result
reuse of the stage8h Stage8OperatorMode=2 write path
```

Stage9 authorises only:

```text
building d3q27_pf_velocity_q27_geometric from the stage9 snapshot
running the gate A/B/C/D cases in cases/diagnostics/stage9_analytic_wetting_20260614/
reporting the resulting metrics as exploratory_not_validation
```
