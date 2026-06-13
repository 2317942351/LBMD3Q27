# Stage8h Contact-Relation And Profile-Path Audit

Status: `runtime_sanity / exploratory_not_validation`.

Stage8h is a shadow-only diagnostic lane built from Stage8g. It does not
authorize sphere `Stage8OperatorMode=2`, sphere 50k or longer runs, PRE
reproduction, validation, production, or publication-ready claims.

## Purpose

Stage8g improved the z48 sphere cap-on-sphere shadow result, but its best case
still had about `45.64 %` normal-limiter hits. That means cap-contract scaling
and low-angle `tan(pi/2 - theta)` regularization helped, but did not make the
candidate safe to write.

Stage8h tests whether the remaining blocker is caused by:

```text
1. the local contact relation target_normal = -tan_eff * tangent_mag
2. a cosine contact-angle residual being numerically less stiff
3. residual-relaxation scaling being required before any write test
4. wall profile path and fluid-gradient candidate mismatch
```

All Stage8h cases use `Stage8OperatorMode=1`. Candidate values are written to
diagnostic fields only.

## Source

```text
remote source = /home/yuan/src/TCLB_stage8h_contact_relation_and_profile_path_audit_20260613
public snapshot = third_party/tclb_snapshots/stage8h_contact_relation_and_profile_path_audit
patch = third_party/tclb_snapshots/patches/stage8h_contact_relation_and_profile_path_audit_20260613.diff
run root = /media/yuan/新加卷1/RUNS/runs/stage8/stage8h_contact_relation_and_profile_path_audit_20260613
```

The run environment is loaded with:

```bash
source "/media/yuan/新加卷1/RUNS/scripts/tclb_runs_env.sh"
```

## Stage8h Modes

All modes keep `Stage8gMode=3` as the Stage8g best shadow baseline.

```text
Stage8hMode=0: Stage8g best baseline; no Stage8h candidate change
Stage8hMode=1: residual-relaxation normal update
Stage8hMode=2: cosine-contact-residual update
Stage8hMode=3: profile-path conflict shadow on top of baseline candidate
Stage8hMode=4: combined residual-relaxation, cosine residual, and profile weight
```

The additional shadow quantities include:

```text
WallStage8hActualCos
WallStage8hTargetCos
WallStage8hResidualCos
WallStage8hDnTanRaw
WallStage8hDnCosRaw
WallStage8hDnRelaxed
WallStage8hBetaRelaxation
WallStage8hBetaSource
WallStage8hProfileNormal
WallStage8hProfileTargetMismatch
WallStage8hProfileConsistencyWeight
WallStage8hCandidateDemandRatio
WallStage8hCandidateNormalDelta
WallStage8hLimiterEquivalent
WallStage8hCosToTanRatio
WallStage8hEffectiveCap
WallStage8hWriteAllowedFlag
```

`WallStage8hWriteAllowedFlag` is fixed at `0`. Stage8h does not write
`gradPhiVal_*` for normal mode values.

## Case Matrix

Flat low-angle shadow:

```text
cases/diagnostics/flat_wall_cap_stage8h_contact_relation_20260613
wall angles = 5, 8, 11, 15, 20, 25, 30 deg
Stage8hMode = 0, 1, 2, 3, 4
case count = 35
steps = 0, 100, 1000
Stage8OperatorMode = 1
```

Sphere z48 shadow:

```text
cases/diagnostics/pre2025_sphere_stage8h_shadow_20260613
geometry = 80 x 80 x 180
R_drop = 24
R_solid = 24
solid_center = (40, 40, 48)
drop_center_z = 96 for free-sphere initializer
outer radAngle = 90 deg
sphere radAngle = 11 deg
M = 0.1
IntWidth = 6
initializers = free-sphere, approximate cap-on-sphere
Stage8hMode = 0, 1, 2, 3, 4
case count = 10
steps = 0, 100, 1000
Stage8OperatorMode = 1
```

The cap-on-sphere initializer is diagnostic only and is not an equilibrium
initializer.

## Planning Gate

Stage8h can only support planning a later short write gate if the shadow data
meet all of these constraints:

```text
nonfinite_total = 0
outer90/fallback Stage8h limiter-equivalent hits = 0
vector_limiter_fraction = 0
candidate demand p50 < 1.2
candidate demand p95 < 3.0
sphere cap-on-sphere Stage8h limiter-equivalent < 10-15 %
flat wall020/wall025/wall030 remain benign
wall011 improves substantially without hidden tan-cap-only suppression
```

Passing this planning gate would not be validation. It would only justify a
separate plan for a very short write test, starting at 100 steps, not 50k.

## Execution Boundary

The intended short matrix is run on two independent P100 queues:

```text
P100 A UUID = GPU-f650e558-d920-2fcb-0a8e-45cbc17c1ca2
P100 B UUID = GPU-2abee638-4460-b364-cd98-08cb6eaf11f7
CUDA_DEVICE_ORDER = PCI_BUS_ID
CUDA_VISIBLE_DEVICES = GPU UUID
```

Raw `.vti/.pvti/.pri/.vtk` outputs must stay remote only and should be deleted
after per-case analysis. Public artifacts may contain only curated XML,
JSON/CSV, logs, summaries, PNGs, source snapshots, and patches.

## Multicore Postprocessing

The HM570 host was confirmed as:

```text
CPU = Intel Xeon Gold 6230
sockets = 2
cores per socket = 20
threads per core = 1
physical cores = 40
NUMA nodes = 2, CPUs 0-19 and 20-39
```

Stage8h initially exposed a bottleneck: each flat case took only about tens of
seconds in the GPU solver, but the Python/VTK attribution pass could take
minutes while running serially behind each GPU queue. The Stage8h runner was
therefore split into:

```text
GPU queue: run TCLB solver and write run.returncode/run.solver_done
CPU pool: run finiteness gate, flat gate when needed, Stage8h attribution,
          then delete raw VTI/PVTI/PRI/VTK fields after successful analysis
```

The postprocess pool was run with `POSTPROCESS_WORKERS=20`. Although 40
physical cores are available, 20 workers is the conservative default because
each worker reads many VTK fields and the limiting resource can become data
volume I/O and memory bandwidth rather than CPU arithmetic.

Relevant scripts:

```text
scripts/stage8h_parallel_postprocess.py
scripts/hm570_stage8h_parallel_postprocess_20260613.sh
scripts/hm570_stage8h_run_queue_20260613.sh
scripts/hm570_run_flat_wall_cap_stage8h_20260613.sh
scripts/hm570_run_pre2025_sphere_stage8h_shadow_20260613.sh
```

## Completed Shadow Runs

Remote run root:

```text
/media/yuan/新加卷1/RUNS/runs/stage8/stage8h_contact_relation_and_profile_path_audit_20260613
```

Curated public artifacts:

```text
artifacts/flat_wall_cap_stage8h_contact_relation_20260613
artifacts/pre2025_sphere_stage8h_shadow_20260613
artifacts/stage8h_contact_relation_profile_provenance_20260613
artifacts/stage8h_contact_relation_profile_summary_20260613
```

Execution summary:

```text
flat cases = 35/35 completed
flat postprocess workers = 20
flat postprocess pool errors = 0
flat raw VTI/PVTI/PRI/VTK remaining = 0

sphere cases = 10/10 completed
sphere postprocess workers = 20
sphere postprocess pool errors = 0
sphere raw VTI/PVTI/PRI/VTK remaining = 0
```

The generated summary files are:

```text
artifacts/stage8h_contact_relation_profile_summary_20260613/stage8h_gate_summary.json
artifacts/stage8h_contact_relation_profile_summary_20260613/stage8h_flat_shadow_summary.csv
artifacts/stage8h_contact_relation_profile_summary_20260613/stage8h_sphere_shadow_summary.csv
```

## Current Results

All Stage8h flat and sphere shadow cases had:

```text
nonfinite_total = 0
vector_limiter_fraction = 0
Stage8hWriteAllowedFlag = 0
```

Flat-wall low-angle scan:

```text
Stage8hMode 0/3 preserve the Stage8g baseline demand and limiter-equivalent behavior.
Stage8hMode 1/2/4 remove limiter-equivalent hits across the flat scan.
Stage8hMode 4 gives the lowest candidate-demand ratios in flat shadow data.
```

Sphere z48 shadow:

```text
Stage8hMode 0 baseline:
  max Stage8h limiter-equivalent fraction = 77.06 %
  max candidate-demand p50 = 2.686
  max candidate-demand p95 = 6.811

Stage8hMode 1 residual relaxation:
  max Stage8h limiter-equivalent fraction = 1.73 %
  max candidate-demand p50 = 0.672
  max candidate-demand p95 = 0.939

Stage8hMode 2 cosine residual:
  max Stage8h limiter-equivalent fraction = 12.12 %
  max candidate-demand p50 = 0.458
  max candidate-demand p95 = 1.454

Stage8hMode 4 combined residual + cosine + profile weight:
  max Stage8h limiter-equivalent fraction = 0
  max candidate-demand p50 = 0.115
  max candidate-demand p95 = 0.201
```

For sphere shadows, `outer90` and fallback Stage8h limiter-equivalent counts
remained zero in all modes. This supports the current attribution that the
remaining Stage8g/Stage8h issue is concentrated in the sphere low-angle
contact relation/profile-candidate contract, not in outer-wall angle transfer.

## Current Decision

Stage8h is still an audit/diagnostic route. The completed shadow data are
promising for `Stage8hMode=1/2/4`, especially `Stage8hMode=4`, but they only
support planning a separate very short write-gate proposal. They do not
authorize write mode by themselves.

```text
Stage8OperatorMode=2 sphere write remains forbidden.
No Stage8h sphere 50k, 200k, 400k, or 600k run is authorized.
No validation or production claim is authorized.
```
