# TCLB Experience Log

Date: 2026-06-07

Purpose: short durable lessons that should prevent repeated mistakes in long
goal-mode work. Keep this file compact. Do not use it as a chronological log.

## Durable Lessons

### VTK Cell Data Order

TCLB `.vti` cell data should be interpreted with x as the fastest index, then
y, then z:

```python
ix = linear % nx
iy = (linear // nx) % ny
iz = linear // (nx * ny)
arr = values.reshape((nz, ny, nx)).transpose(2, 1, 0)
```

The earlier axis confusion came from interpreting reshaped arrays incorrectly,
not from TCLB swapping XML axes.

### Align Morphology Steps With VTK Output Steps

Morphology snapshots can only be generated for steps that actually have VTK
output. Before running postprocessing, derive `--morphology-steps` from the
available `*_VTK_P00_*.vti` steps, then include event-critical frames such as
`first_contact_step` and late-window frames only if they are real output steps.

If a requested event step is not on the VTK cadence, rerun or plan the next case
with an aligned `VTK Iterations` interval, or explicitly use the nearest
available output step and label it as such. Do not interpret a missing
non-output morphology frame, such as requesting step 1000 when VTK interval is
400, as missing physics; it is an output-sampling/provenance issue.

### Digitized Literature Curves Need Plot-Element Guards

When digitizing colored curves from rendered literature figures, explicitly
exclude legend swatches and labels from the color mask, then sanity-check the
digitized range against the visible axis scale before computing errors. In the
Safi 2017 TC1 A1 comparison, an insufficient Fig. 5 legend exclusion initially
pulled the FeatFlow rise-velocity curve down near `0.126` at late times; the
correct red-curve extraction stays near the visible `0.34-0.36` plateau.

For TCLB `bubbleRise_1`, use the high-cadence TCLB CSV log
`GasTotalVelocityY / GasTotalPhase` for the bubble-region mean rise velocity
before falling back to coarse VTI centroid finite differences. The VTI frames
are useful for morphology and centroid, but their 2000-step cadence is too
coarse to stand in for the Safi mean-velocity observable without a clear
limitation note.

For A1 Safi comparison, record the rendered page path, axis limits, point
uncertainty, curve/series name, observable mapping, time conversion, and script
used. The current center-of-mass mapping `(centroid_y + 0.5)/L0`, rise-velocity
mapping `GasTotalVelocityY/GasTotalPhase/(L0*T_per_step)`, bubble proxy
`clipped(1 - PhaseField)`, and `L0=64` characteristic-length choice are audit
inputs, not validation facts. Do not promote from `runtime_sanity` solely from
L2 errors when the reference came from pixel extraction and only one `L0=64`
run is compared.

### Analysis Directory Before Redirect

When running postprocessing remotely, create the output directory before shell
redirection:

```bash
mkdir -p "$RUN/analysis_corrected"
python3 script.py ... > "$RUN/analysis_corrected/postprocess_stdout.json"
```

Shell redirection happens before Python can create directories.

### HM570 OpenMPI rsh Agent

On HM570, direct TCLB launch can fail before `MPI_Init` if OpenMPI tries the
default `plm_rsh_agent` list. Include the explicit agent in TCLB run commands:

```bash
export OMPI_MCA_plm_rsh_agent=/usr/bin/ssh
```

### TCLB Return Code Can Miss NaN Stop

TCLB can print `Checking PhaseField discovered NaN`, `NaN value discovered`,
and `Stopping due to Nan value` while still returning process code `0`. In the
PRE 2025 reduced spherical-static batch on 2026-06-10, theta030-080 and
theta100-130 all stopped at iteration 1000 with PhaseField NaN messages, but
the wrapper recorded `run.returncode=0`.

Batch runners must scan `run.log` for these messages before touching
`run.done`, before skipping a case as complete, and before treating
postprocess output as equilibrium data. Initial-frame postprocess results from
such cases are failure diagnostics only and should be classified as
`failed_negative_evidence`.

### Global Velocity Is Not Publication-Grade Impact Initialization

TCLB XML `VelocityX/Y/Z` initializes the whole domain. For droplet impact
publication cases, implement droplet-only velocity or document the run as
exploratory.

### Mach Guard Before Longer Pilots

The first z-wall `theta=90` smoke reached max Mach `0.0979` by 500 steps while
still not contacting the wall. Longer pilots should reduce lattice impact
velocity or revise scaling before spending more runtime. Do not hide high Mach
with postprocessing.

### Droplet-Only Hard Mask Can Still Be Exploratory

The HM570 droplet-only initialization patch assigns velocity only where the
initialized `PhaseF` is on the liquid side of the midpoint threshold. This is
better than global `VelocityZ`, but it creates a hard velocity mask across a
diffuse interface. The first near-wall contact pilot kept Mach low but reached
about `3.28%` phase mass drift, so do not scale this route to production before
auditing initialization smoothness, lattice velocity, near-wall gap, and grid
sensitivity.

The smooth phase-fraction mode (`DropletOnlyVelocity=2`) reduced the same
theta=90 near-wall pilot drift only to about `2.96%`. Treat it as an
insufficient improvement, not a fix. The next useful checks are scaling and
phase-field parameter sensitivity, not repeating the same A/B at larger
production grids.

Lowering the smooth droplet velocity from `-0.012` to `-0.008` reduced phase
drift to about `1.34%` and rho drift to about `0.18%` in the same 1600-step
small-grid window, with max Mach about `0.0177`. This supports a scaling
direction, but the beta was only about `0.84` by 1600 steps, so longer-window
or first-contact timing checks are needed before interpreting spreading trends.

Do not jump from this `u=-0.008` small-grid result directly to contact-angle
sweeps. First extend the theta=90 case to event timing and late/recoil/rest
status, then run one neighboring velocity or gap sensitivity. Only then consider
a single R0>=32 theta=90 exploratory pilot.

The 3200-step extension of the same `u=-0.008` case detected first contact at
step 1000 and kept Mach/nonfinite acceptable, but phase drift grew to about
`5.02%` while beta was still increasing. Short-window mass metrics are not
enough; long-window phase drift is currently the gate blocker before larger
grids or contact-angle sweeps.

Lowering only mobility-like `M` to `0.025` improved the same long-window gate
from about `5.02%` to about `4.14%` phase drift, with rho drift about `-0.686%`,
max Mach about `0.0180`, and nonfinite count `0`; however beta still increased
and `resting_candidate=false`. Treat this as `exploratory_not_validation`:
M-only tuning has not solved the long-window mass gate, so do not proceed to
`R0>=32` or contact-angle sweeps. Next checks should stay bounded to
phase-field sensitivity such as `IntWidth` or audited coupled `M/IntWidth`.

Reducing `IntWidth` from `5` to `4` with baseline `M=0.05` made the same
3200-step gate worse: phase drift rose to about `5.92%`, rho drift to about
`-1.07%`, and beta still increased through the last frame. Treat narrower
interface width as negative evidence for this setup; do not repeat the same
direction before trying a wider interface or auditing a coupled parameter move.

Increasing `IntWidth` from `5` to `6` with baseline `M=0.05` improved the same
3200-step gate to about `4.33%` phase drift and `-0.76%` rho drift, with max
Mach about `0.0149` and nonfinite count `0`; however beta_area still increased
late and `resting_candidate=false`. This points toward wider interface being a
useful direction, but it is not enough by itself. Treat any next coupled
`M/IntWidth` run as exploratory and audit it before scaling grids.

Combining `M=0.025` with `IntWidth=6` improved the long-window phase drift
further to about `3.65%`, with rho drift about `-0.59%`, max Mach about
`0.0154`, and nonfinite count `0`, but it still did not meet even the
engineering `2%` phase-drift preference and beta_area still increased late.
Do not keep spending runs on adjacent one-point tuning without first reviewing
the phase-field parameter meaning, wetting/boundary implementation, and mass
accounting.

If a shell wrapper loses the postprocess return code after producing summary
and metrics, record it explicitly in the artifact. Do not treat generated
summary files alone as a clean process-return proof; preserve run.log tail,
raw VTI/PVTI counts, postprocess stderr, and a local provenance note.

Do not use all-cell `phase_sum` as the bulk phase-mass gate when TCLB outputs
`BOUNDARY`. Wall/solid cells can carry wetting ghost `PhaseF`, while `Rho` is
zero on walls. Use `fluid_phase_*` over `BOUNDARY==0` for bulk mass, and report
`wall_phase_*` or z-min/z-max wall phase separately. Reprocessing the five
3200-step z-wall cases changed the apparent 3.65-5.92% all-cell drift into
about 0.64-1.17% fluid-only drift; the remaining blocker is not mass alone but
lack of resting state and missing validation/grid sensitivity.

The 9600-step extension of the same small-grid `R0=14`, theta=90,
`M=0.025`, `IntWidth=6`, smooth `DropletVelocityZ=-0.008` case is negative
evidence for simple time-extension of that candidate. Runtime, Mach, and
nonfinite checks stayed clean, but `beta_area` still peaked at the final frame,
late beta change exceeded the resting tolerance, and fluid-only phase/rho drift
worsened versus ext6400. Do not launch larger grids, 45/90/135 sweeps, or
paper-facing claims from long extensions of this same small-grid setup until a
changed and audited setup passes rest, mass, and validation gates.

When running HM570 checks from Windows PowerShell, quote the remote shell script
so variables expand on HM570, not locally. Prefer:

```powershell
ssh HM570 'RUN=/home/yuan/runs/<run>/theta090; tail -n 8 "$RUN/run.log"; find "$RUN/output" -name "*.vti" | wc -l'
```

Do not trust a malformed SSH result where `$RUN` is blank, remote paths collapse
to `/run.log`, or counts report zero for a known completed run; rerun with
single-quoted remote script before updating provenance.

For local PowerShell aggregation checks, wrap `foreach` in a script block before
piping to `ConvertTo-Json`; otherwise PowerShell can raise `An empty pipe
element is not allowed` and the check fails before inspecting files:

```powershell
& { foreach ($f in $files) { [pscustomobject]@{ file = $f } } } | ConvertTo-Json
```

Do not paste Bash heredoc syntax such as `python - <<'PY'` into PowerShell.
PowerShell parses `<<` as an invalid redirection and the command fails before
any copy or postprocess action starts. Use a PowerShell-native loop/object
pipeline, a temporary script file, or run the heredoc inside an SSH command
where Bash is actually interpreting it.

For small local Python inspections from PowerShell, prefer a quoted `-c`
one-liner instead of heredoc syntax:

```powershell
python -c "import json, pathlib; d=json.loads(pathlib.Path('artifact.json').read_text()); print(d.keys())"
```

This avoids the `Missing file specification after redirection operator` parser
error and keeps quick provenance checks reproducible.

Even inside `ssh HM570`, nested PowerShell quoting can corrupt a Bash heredoc
terminator and leave a trailing `PY` token to be executed by Python, producing
valid-looking stdout followed by a nonzero return code. Treat such output as a
diagnostic only, not a formal artifact. Prefer a remote script file, a simple
quoted one-liner, or an already-versioned postprocess script for formal checks.

When launching HM570 commands from Windows PowerShell, do not build remote
commands that both interpolate local variables and require remote `$PATH` or
`$?` expansion unless every `$` is deliberately escaped. A failed theta045/135
static-contact launch overwrote remote PATH enough that even `date` was not
found. Robust pattern:

```powershell
$remoteScript = "cd /home/yuan/src/TCLB; export PATH=/usr/local/cuda-12.6/bin:/usr/bin:/bin; ...; rc=`$?; echo `$rc > /path/run_return_code.txt; exit `$rc"
ssh HM570 $remoteScript
```

Prefer explicit absolute remote run paths for `scp` targets and create the
directory with a simple `ssh HM570 "mkdir -p /abs/path"` before copying.

When recording HM570 solver return codes from a Windows-launched SSH command,
do not rely on an unescaped remote `$?` inside a double-quoted PowerShell
string. In the A1 `coarse_L48` grid/time run, the solver completed and wrote
all 7 VTI/7 PVTI frames, but the wrapper left `run.returncode` empty because
return-code expansion was corrupted. For formal runs, use single-quoted remote
scripts or a remote shell script file, then verify the TCLB `run.log` total
duration line, raw VTI/PVTI counts, and curated postprocess outputs before
classifying the wrapper record.

A completed grid/time chain is not automatically a validation pass. The A1
L0=48/64/80 runs had clean runtime health, but Bonn comparison errors were
non-monotonic and the velocity CSV proxy spread exceeded the provisional gate.
Keep such results at `runtime_sanity` until an audit accepts a target reference
series, locks the velocity observable mapping, and approves thresholds.

Static contact-angle postprocessing must use the wall-normal coordinate for
the circle-center offset. In TCLB `ContactAngle_45.xml`, the lower wall normal
is `y`; in an x-mid section the horizontal image coordinate is `y`, while the
vertical coordinate is the tangential `z`. Using the tangential coordinate
produced a false `180 deg` result for theta090. The corrected normal-coordinate
fit gives theta090 about `89.17 deg`.

For static contact-angle convention audits, x-mid and z-mid slices map the
wall-normal coordinate differently. In an x-mid contour, plot x is `y`
wall-normal; in a z-mid contour, plot y is `y` wall-normal. Record this in the
summary JSON and do not compare circle-center offsets until the plotted axis
has been mapped back to the physical wall-normal direction.

The first official-derived static contact-angle calibration is incomplete, not
a pass. v3 postprocessing with input-angle metadata shows theta090 is plausible
and theta135 is close only under the complement interpretation
(`135.286 deg` complement for input `135 deg`), but theta045 still fails under
the complement interpretation (`57.662 deg` complement for input `45 deg`) and
has about `4.18%` phase drift plus about `0.90%` rho drift. v3 quantifies the
convention risk; it does not validate the wetting setup. Do not launch impact
contact-angle sweeps until this wetting convention and low-angle mass/fit
behavior pass read-only audit.

Read-only build-state inspection showed that the current HM570
`d3q27_pf_velocity/main` binary did not enable `geometric`, `staircaseimp`,
`isograd`, or `tprec`: generated `options.R` has these options as `FALSE`, and
generated `Consts.h` has the corresponding `#undef OPTIONS_*` entries. The
model `conf.mk` lists these as possible build variants, and `Dynamics.c`
contains conditional geometric branches, but this static contact-angle run set
used the non-geometric/default surface-energy wall update, where `radAngle`
enters through `-cos(radAngle)`. Do not treat the v3 complement behavior as
evidence for the geometric wetting boundary condition. The next bounded
calibration work should separate phase-side angle convention, circle-fit
definition, and theta045 mass/shape drift before changing impact cases.

The convention audit for `tclb_static_contact_angle_calib_20260607` tested 24
fit variants per angle and showed theta045 remains high under all of them:
liquid-side angle `55.7808-60.7211 deg` for requested `45 deg`. That means the
theta045 blocker is not explained away by x-mid/z-mid coordinate mapping,
wall-location assumption, or near-wall point filtering alone. Keep the result
`exploratory_not_validation` and do not launch impact contact-angle sweeps from
this calibration.

Low-angle static contact-angle response-surface runs are exploratory wetting
parameter diagnostics, not accepted calibration. The
`tclb_static_contact_angle_response_surface_energy_20260607` sweep showed that
`radAngle=30` and `35` still produced best liquid-side angles around `48.83`
and `51.02 deg`, with the largest phase/rho drift in the sweep; this does not
clear the theta045 blocker. For each future surface-energy response check,
record the requested `radAngle`, TCLB build option state, fit convention,
phase/rho drift, max Mach, nonfinite count, raw VTI/PVTI counts, remote raw
path, local curated artifact path, and claim limit together. Do not interpret
an improved low-angle fit alone as validation unless convention audit,
mass/rho behavior, finite checks, repeatability, and grid sensitivity pass
read-only audit.

Do not hard-code run ids inside reusable postprocess or audit scripts. The
static contact-angle convention audit originally wrote the calibration run id
into a response-sweep summary; use `run_root.name` or an explicit CLI argument
for provenance fields so copied scripts cannot silently mislabel future
artifacts.

The same rule applies to two-row static contact-angle audits. Before reusing
`tclb_static_contact_angle_two_row_audit.py` for q27 Stage-3 static wetting,
remove historical constants such as
`tclb_static_contact_angle_geometric_grid_density_20260607` and derive
`run_id` from the active run root. A correct angle table with the wrong run id
is still bad provenance and should not be used for gate decisions.

For low-angle static contact calibration under the current non-geometric
surface-energy wetting path, bracketing a target apparent angle is not enough.
The `radAngle=5/10/12` continuation weakly bracketed liquid-side 45 in the
fit-sensitivity range and produced postprocess complements near `45.5-46.4 deg`,
but phase drift rose to about `17-18%` and rho drift to about `-2.7%` to
`-2.8%`. Treat this as permission only for a single `exploratory_not_validation`
theta045 dry-wall pilot, not as calibrated wetting, not as validation, and not
as authorization for a 45/90/135 sweep. Future low-angle calibration work must
address mass/rho drift and fit-range width before any production or publication
claim.

Use radAngle-based case naming for low-angle inverse-response work unless the
measured liquid-side angle has passed audit. Names like `theta045` should not
be used for an input parameter that merely targets 45 deg but has not been
validated as a physical contact angle.

The first `radAngle=5d` target-45 dry-wall pilot confirmed the output chain but
not the physics gate. It ran cleanly with max Mach about `0.0146` and nonfinite
`0`, but `beta_area` was still maximal at the final 6400-step frame, late beta
change was large, fluid-only phase drift was about `2.27%`, and rho drift about
`-2.09%`. Do not extend this exact small-grid low-angle pilot or start a
45/90/135 sweep from it; first address low-angle wetting mass/rho drift,
fit-range width, or run a standard validation case.

The static `M=0.025`, `IntWidth=6` low-angle sensitivity is not a transferable
fix for target-45 wetting. In
`tclb_static_contact_angle_bracket_lowangle_M0025_W6_20260607`, BOUNDARY-aware
reanalysis showed the apparent `7.68-8.52%` all-cell phase drift is
wall/ghost-inclusive; the bulk `BOUNDARY==0` fluid-only phase drift is about
`1.53-1.65%`. However, the complement angles clustered at `52.74-52.96 deg`,
convention-audit liquid-side ranges stayed near `50.93-59.95 deg`, and rho
drift remained about `1.48-1.59%`. Treat this as mixed evidence: better bulk
phase mass, failed target angle. Do not use M0025/W6 to authorize another
low-angle impact pilot, 45/90/135 sweep, or status promotion.

Static contact-angle mass diagnostics should separate all-cell phase,
fluid-only phase over `BOUNDARY==0`, and wall/ghost phase where `BOUNDARY` is
available, mirroring the impact protocol. Existing static summaries that report
only all-cell `phase_sum`/`rho_sum` are useful for trend screening, but they are
not enough to diagnose wetting-wall mass leakage or to promote calibration.

When defining a remote path variable inside an SSH command launched from
Windows PowerShell, single-quote the remote script or escape `$`. A command
like `ssh HM570 "d=/abs/path; cat $d/file"` lets PowerShell expand `$d` locally
to blank, causing the remote command to inspect the home directory or `/file`
instead of the intended path. If remote output unexpectedly lists home files
such as `.bashrc` during an artifact audit, rerun immediately with:

```powershell
ssh HM570 'd=/abs/path; cat "$d/file"'
```

### 1 mm / 10 mm Free Fall Is Not High-We

For water-air with `D=1 mm` and `H=10 mm`, `U≈0.443 m/s` and `We≈2.7`.
Do not describe that target as high-We unless the physical setup changes.

### Keep Raw VTI Remote

Raw VTI/PVTI files are large. Keep them on HM570 by default and copy only
metrics, summaries, figures, case XML, and logs to local artifacts.

For TCLB `bubbleRise_1` with `BubbleType=-1`, the bubble proxy for centroid and
rise diagnostics is clipped `1 - PhaseField`, not raw `PhaseField`. Record the
phase convention, rise-axis choice, and VTK x-fastest order in any bubble-rise
summary. A Matplotlib `No contour levels were found within the data range`
warning during a morphology snapshot is a visualization limitation if the run
is finite and metrics are present; record it in stderr/README instead of
treating it as a numerical failure or hiding it.

For TCLB make targets generated by `makefile.main`, build-option variants such
as `d3q27_pf_velocity_geometric` are independent `CLB/<target>/main` outputs.
Before running cases with a new variant, record both the original and variant
`options.R`/`Consts.h` state and binary timestamps. The 2026-06-07 geometric
build proved `d3q27_pf_velocity_geometric` had `geometric=TRUE` while the
original `d3q27_pf_velocity` remained `geometric=FALSE`.

Use a long enough SSH timeout for first-time TCLB target builds. A 120 s
Windows SSH wrapper timeout interrupted the initial
`d3q27_pf_velocity_geometric` build during source generation, but retrying the
same independent target with a longer timeout completed cleanly. Treat local
wrapper timeout as inconclusive until HM570 process state, build log tail, and
target files are checked.

The original global/circle-fit interpretation of geometric-only theta045 was
too strict for judging the wetting boundary. That case completed 200000 steps
with max Mach about `9.4e-5` and nonfinite `0`; global/circle metrics gave
about `57.62-61.90 deg`, but the corrected local-tangent protocol gives about
`43.25 deg` for `phi=0.5`, true `3-8 lu`. Treat this as permission to continue
bounded geometric static theta090/theta135 under the same frozen protocol, not
as validation and not as impact-sweep authorization. Also check HM570 free disk
before static sweeps: one 128x64x128, 200000-step full-output case occupied
about `1.4G`, leaving only about `3.4G` free on this run.

Do not trust TCLB wrapper return code alone for failed static wetting cases.
The geometric-only `radAngle=5d` min-output diagnostic wrote return code `0`,
but `run.log` reported `Checking PhaseField discovered NaN` and `Stopping due
to Nan value`, with only the initial VTI/PVTI pair produced. For any future
case, classify success from `run.log`, failcheck text, final-frame existence,
and raw counts together. Geometric low-angle inverse sweeps are not safe under
the current `M=0.05`, `IntWidth=4` static setup; use a changed/audited route
such as stability parameter review or a different wetting build variant before
another low-angle run.

The `d3q27_pf_velocity_geometric_staircaseimp` build variant is not an
immediate theta045 fix. It built cleanly with `geometric=TRUE` and
`staircaseimp=TRUE`, and a bounded theta045 static run completed with only
initial/final VTK output, max Mach about `3.0e-5`, and nonfinite `0`. However,
the postprocess complement stayed at `59.511 deg` and the convention-audit
liquid-side range stayed `57.62-61.90 deg`, essentially matching the
geometric-only failure. Do not spend disk or time on theta090/theta135
continuation or impact sweeps from this build variant unless a materially
different wetting route is introduced.

When reusing remote postprocess scripts, verify the exact script path before
launching formal postprocess. In the `geometric_staircaseimp` diagnostic, the
first postprocess attempt pointed to a non-existent analysis-subdirectory copy
and returned `2`; rerunning with the script at the run root succeeded. Prefer
copying the local canonical script into the new run root or using a known
existing root-level script path, and record the failed attempt as a path issue
rather than a solver failure.

Do not use whole-cap circle fitting as the only static contact-angle metric.
The revised 2026-06-07 static evaluation showed that theta045 geometric and
geometric_staircase cases have global cap/circle complements around `59.51 deg`,
but near-contact-line local liquid-side angles around `43.15 +/- 0.10 deg`.
This means the earlier theta045 blocker was primarily an evaluation-definition
problem, not clear evidence that the geometric wetting boundary is wrong.
Report both local tangent angle and global cap/circle angle.

For local tangent static contact-angle metrics, distinguish the acute
tangent-wall angle from the liquid-side angle. For lower-wall sessile drops,
the local liquid-side angle equals the acute angle for requested angles
`<=90 deg`, but equals `180 deg - acute_angle` for obtuse cases such as
theta135. Forgetting this conversion falsely makes theta135 look like a
`~46 deg` result even though the liquid-side angle is about `133.6 deg`.

For the geometric static contact-angle protocol, distinguish true
wall-distance ranges from cumulative maximum-distance windows. The first
local-tangent audit used `--windows 3 4 5 6 8` as `0-w` fits, while the frozen
protocol requires true ranges such as `2-6`, `3-8`, and `4-10 lu`. Mixing these
definitions can hide the contact-line/cap transition and misreport the local
angle. The corrected theta045 geometric audit gives about `43.25 deg` for
`phi=0.5`, true `3-8 lu`, while farther `4-10 lu` windows drop toward
`42 deg`; report this sensitivity instead of averaging it away.

Do not use the theta045 local-tangent success to assume the same near-wall
window is a valid macroscopic gate for theta090/theta135. In the geometric
theta090/theta135 static cases, `phi=0.5`, true `3-8 lu` gives local angles
about `77.28 deg` and `118.11 deg`, while global/circle complements remain near
target at about `90.83 deg` and `133.85 deg`. Overlay images show the local
fit segments lie on curved near-wall interface regions, and the window trend
from `2-6` to `4-10 lu` is systematic. Treat this as an unresolved
microscopic contact-line versus macroscopic sessile-drop angle definition
problem, not as final proof that the geometric wetting model is wrong and not
as permission to start validation runs, sweeps, R0>=32 pilots, or liquid-film
cases. A later two-metric read-only audit only permits one theta090 bounded
runtime probe to test impact-chain health under `exploratory_not_validation`.

When launching remote Bash loops from Windows PowerShell, avoid unescaped
`$(...)` and `$var` constructs inside double-quoted SSH commands. PowerShell
can expand them locally before SSH, turning a remote loop into blank paths and
failed redirects. Use single-quoted remote commands or a remote script file,
for example `ssh HM570 'bash -lc "for th in ...; do ...; done"'`, and verify
the generated remote file list before classifying the run.

Treat HM570 low free space as a hard execution gate. On 2026-06-07,
`/home/yuan/runs` was on the root filesystem with only about `1.4G` free
(`99%` used) while `theta135` geometric static contact-angle was still running.
Do not launch new TCLB runs under this condition. Prefer raw-only cleanup of
old remote `.vti/.pvti` files after curated XML/log/CSV/JSON/PNG artifacts and
path provenance exist; do not delete whole run directories by default.

Use absolute remote analysis directories for formal HM570 postprocessing. A
relative `--analysis-dir analysis_contact_angle_global_phi_0p50` launched from
SSH created `/home/yuan/analysis_contact_angle_global_phi_0p50` instead of the
case directory and risked overwriting theta090/theta135 outputs. Prefer
`--analysis-dir /home/yuan/runs/<run>/<case>/<analysis_name>` and verify the
resulting file path before copying curated artifacts.

The `/mnt/data500/yuan/runs` route is failed history, not the accepted run
root. On 2026-06-07, `/mnt/data500` initially appeared as a 458G ext4 mount
with about `435G` free, but `rsync -aH /home/yuan/runs/` failed on the receiver
with `Input/output error (5)` while writing a VTI under
`/mnt/data500/yuan/runs/.../fine_L80/output/`. Immediately after that, HM570
froze/unresponsive. Do not reuse `/mnt/data500/yuan/runs` as the default path.

If HM570 is confirmed frozen or unresponsive after a storage I/O error, stop
remote retries in the active run. Repeated SSH attempts do not recover the
machine and can obscure the failure timeline. After manual recovery or reboot,
the first action must be health-only inspection (`dmesg`, `findmnt`, `df`, and
small write/read/delete on the candidate physical run root), not rsync,
cleanup, or TCLB execution.

The accepted DATA500 run root is `/media/yuan/DATA500/runs`, not the earlier
failed `/mnt/data500/yuan/runs` candidate. On 2026-06-07, `/media/yuan/DATA500`
was mounted as `ntfs3` on `/dev/sdc1`, with about `466G` total and `418G`
available; a small write/read/delete health check under the run root passed.
`/home/yuan/runs` was recreated as a compatibility symlink to
`/media/yuan/DATA500/runs`, so historical paths remain readable. When checking
size, use `du -sh /media/yuan/DATA500/runs`; `du -sh /home/yuan/runs` reports
only the symlink itself unless dereferenced.

The geometric static two-metric gate candidate is a protocol-revision artifact,
not a pass. It records that theta045 passes the microscopic local metric while
theta090/theta135 pass the macroscopic complement metric, but the frozen local
gate still fails. The 2026-06-07 read-only audit does not allow validation,
production, a sweep, an R0>=32 pilot, or a liquid-film case. It only allows one
theta090 dry-wall bounded runtime probe to test impact-chain health, with
`status=exploratory_not_validation`, the geometric binary path recorded
explicitly, DATA500 as the run root, and mandatory beta/mass/rho/Mach/nonfinite
and morphology reporting. Stop if nonfinite appears, Mach approaches 0.1, or
mass/rho drift worsens badly.

When sending multi-line Bash from Windows PowerShell to HM570, strip CRLF and
avoid locally parsed pipes. PowerShell repeatedly interpreted remote `grep -E`
pipelines before SSH, and CRLF in a piped script made Bash see `exit 0\r` as a
non-numeric exit argument even though TCLB had returned `0`. Prefer piping with
`ssh HM570 "tr -d '\r' | bash"` or uploading an LF-only helper script, then
judge solver success from `run.returncode`, `run.log`, final VTK existence, and
failcheck text together.

For multi-angle static batches, do not place `run.log`, `run.stderr`,
`run.returncode`, or `run.done` at the shared grid-tag directory level. The
first `tclb_static_contact_angle_geometric_grid_density_20260607` launch used
XML files under `<grid_tag>/contact_angle_...theta*.xml`; deriving `case_dir`
as `dirname(xml)` meant theta090/theta135 would overwrite theta045 logs even
though the VTK output directories were per-theta. Fix the runner to derive the
case directory from the XML `output=".../theta###/output/"` attribute, and copy
the XML into that theta directory. Preserve interrupted pre-fix output under a
clearly named folder instead of deleting it. If a completed case must be rerun,
archive its existing per-theta log files first; the runner intentionally uses
`>` redirection and relies on `run.done` plus `run.returncode==0` to skip
successful cases.

If HM570 begins timing out during DATA500-backed long batches, distinguish
local wait-command timeout from remote unreachability before acting. A local
PowerShell `Start-Sleep` wrapper can time out without proving the solver is
stuck. But if minimal SSH fails during banner exchange and name resolution or
TCP checks also fail, stop issuing heavy `find`, `tail`, or disk queries.
Record the last confirmed PID/case/iteration, wait for machine recovery, then
restart with health-only checks (`date`, `ps`, `batch.log`, per-case
`run.returncode`/`run.done`, `df`/`findmnt`, and kernel logs if available)
before resuming or classifying the run.

After copying a remote TCLB run tree to a new disk, do not assume the copy is
ready to resume. TCLB XML `output="..."` paths are absolute; copied XMLs from
DATA500 still wrote back to `/media/yuan/DATA500/runs` until retargeted. Before
launching on the copied tree, grep all active XML/manifest/helper scripts for
the old run root, retarget them to the new physical root, archive any partial
or corrupted logs from the copy, and verify a sample XML output path. Treat
copied partial logs with NUL bytes or missing returncode/done files as
interrupted provenance only, not numerical evidence.

For static contact-angle evaluation, do not use the contact-line anchored
`1-8 lu` arclength tangent as the sole wetting-model gate. OpenLB-style
contact-angle examples and common LBM sessile-drop calibration use a
macroscopic base-width/height spherical-cap apparent angle, often with the
base measured above the wall to reduce near-wall diffuse-interface influence.
In the geometric grid-density batch, theta090 is near target by this
macroscopic metric (`~90.9/90.4/90.0 deg` endpoint angle for R24/R32/R48),
while the local `1-8 lu` tangent gives `~80.4/83.0/85.3 deg`. Report these as
different observables: apparent sessile-drop angle versus microscopic
near-wall contact-line diagnostic. Do not reject the wetting model, promote
validation, or authorize impact sweeps from either metric alone; require an
audited fixed convention and sensitivity table.

When plotting static contact-angle overlays, make the displayed image
coordinate system match the fitted geometry. The OpenLB-style apparent script
computes contour points as `(tangent, wall-normal)`; for x-mid sections the raw
`section` array is transposed relative to that coordinate pair. The v2 overlay
images therefore showed base/height markers on a mismatched droplet image and
must not be used for visual judgment. Use v4 or later outputs, where the image
is displayed in tangent-vs-normal coordinates before overlaying contour,
base-width, and height markers.

For literature-style near-wall contact-angle measurement, add a separate
two-row interpolation metric instead of stretching the arclength tangent
window. The `interpolated_two_row_contact_angle` method finds `phi=0.5`
crossings on two near-wall rows, linearly interpolates interface positions,
then computes the angle between the two interface points and the solid wall.
On the geometric grid-density batch, the row-pair `1-2` metric gives near-input
values for completed R24/R32/R48 W6 cases: theta045 about `42.5-43.8 deg`,
theta090 about `87.7-88.8 deg`, and theta135 about `135.6-135.8 deg`. Report
this as a near-wall boundary-condition diagnostic, distinct from OpenLB-style
macroscopic apparent base-height angles, which still show large 45/135 shape
discrepancies.

TCLB `SaveCheckpoint` works for the geometric d3q27 phase-field binary and
writes both `case_checkpoint_<iter>_0.pri` and `case_restart_<iter>.xml`.
However, the generated restart XML preserves the original `output=` path and
`Solve Iterations`, so running it directly can overwrite or mix new VTK output
with the existing evidence. Before continuing a droplet-impact run, derive a
new restart-extension XML that keeps `LoadBinary file=...checkpoint...pri` but
changes `output=` to a fresh subdirectory and sets the desired additional
iteration count. Keep checkpoint `.pri` files remote-only unless explicitly
needed locally; they are hundreds of MB per checkpoint even for 96^3.

When postprocessing a TCLB restart extension, do not treat the extension's VTK
step numbers as absolute simulation time. They restart at local step zero, and
the local `*_00000000.vti` can reflect XML initial-output semantics even though
the log confirms `LoadBinary` later loads the checkpoint. For combined
droplet-impact metrics, offset extension steps by the checkpoint iteration and
exclude the extension local step 0 unless a direct field comparison proves it
is the checkpoint state. Record this choice in the combined summary.

When launching long HM570 commands from Windows PowerShell, upload LF-only
helper scripts instead of embedding complex Bash with parentheses, heredocs,
background jobs, or variable expansion inside one `ssh` command. PowerShell can
parse semicolons, parentheses, redirects, and `$variables` locally, producing
misleading errors or partial remote scripts. For queued GPU work, create a
versioned local script under `scripts/`, `scp` it to `/tmp`, inspect it with
`sed`, then launch it with `nohup`.

Do not start an impact continuation while another TCLB GPU solver is active on
HM570. If an old batch is occupying the GPU but a pilot has priority, avoid
killing the active solver unless explicitly requested. Pause or terminate only
the batch parent after recording the action, let the current solver finish, and
queue the priority run to start after both the batch parent and solver process
are gone. Record the queue PID, queue log, paused batch PID, and active solver
PID in the artifact/path index.

For R0=24 theta090 dry-wall impact, the 6400-step morphology can show
concentric/ring-like wall-footprint bands and a center low-phase/void risk even
when Mach and nonfinite checks are healthy. Do not interpret this as an
accepted resting droplet morphology. Extend from checkpoint and judge whether
the ring/void dissipates, stabilizes as a physical dry spot, or grows as a
numerical artifact before any route promotion.

For the same R0=24 theta090 dry-wall chain, the 0-65600 combined review showed
that a small late beta change can coexist with an unacceptable stabilized
annular footprint and center low-phase/void. Do not use `resting_candidate` or
late `beta_area/beta_box` plateau alone as the acceptance criterion. Require
visual morphology review, preferably key-step images around first contact,
maximum beta, prior continuation end, beta-box maximum, and final time.

TCLB restart stderr can contain `Missing comp parameter in LoadBinary` even
when the wrapper return code is zero. Before treating the segment as valid
provenance, check `run.log` for the actual checkpoint path loaded, the intended
fresh output path, `Solve Iterations`, and final/postprocessed frames. Report
the stderr line as a provenance warning rather than hiding it.

When increasing We for the R0=24 theta090 dry-wall route, a 3x velocity jump
from `DropletVelocityZ=-0.008` to `-0.024` gives a 9x relative We increase but
already reaches max Mach about `0.0901` in the 0-12800 combined run. Treat this
as near the current lattice-speed ceiling. Do not further increase velocity in
the same grid/parameter scaling unless a compressibility/Mach mitigation plan
is added. Continue from checkpoint or change scaling/grid instead.

When writing HM570 batch runners that discover XML files, verify the exact
remote XML depth after `scp` before launching. The 2026-06-08 Li Peisheng
Laplace sigma-sweep runner initially used `find "$root" -mindepth 3 -maxdepth
3`, but the XML files lived at `root/sigma_tag/*.xml`; it reported
`case_count=0` and performed no runs. The static-wetting runner had the same
risk after changing the case layout. Always run a remote `find <root> -maxdepth
... -name '*.xml'` smoke check and compare it with the manifest case count.

For TCLB phase-field Laplace-law checks, do not assume the input `sigma`
equals the postprocessed pressure-jump slope. In the Li Peisheng analogue
sigma sweep, effective Laplace slope was linear in input `sigma` with
R2 about `0.99999977`, but the slope ratio was about `1.634`. Treat this as
surface-tension tunability evidence and an absolute mapping/audit issue; do
not use the nominal input sigma alone to claim a physically matched Weber
number.

When comparing TCLB dry-wall spreading with literature `D* = D'/D`, explicitly
audit the spread definition before blaming the solver. The Li Peisheng
Re600/We11.56 analogue showed that global horizontal projection and near-wall
footprints with 1/2/4/8/16 layers all kept `beta_box_max=1.54`, with
`beta_area_max` only shifting about 1-2% under `phi=0.45/0.50/0.55`. Therefore
the large gap to empirical beta values is not caused by the current 4-layer
footprint extraction alone, but the exact literature convention still must be
reported separately from the model/parameter diagnosis.

For the TCLB `d3q27_pf_velocity` model, the `q27` compile option changes the
phase-field population stencil from the default D3Q15 `h` set to the full D3Q27
`h` set. Treat `d3q27_pf_velocity_q27_geometric` as a separate model route:
do not reuse the q15-geometric Laplace calibration coefficients, contact-angle
metrics, mass-drift behavior, or impact conclusions. Build and report it with
its own `sigma_input -> laplace_slope -> sigma_eff` calibration, static
wetting audit, and impact audit.

If the Codex thread reaches the platform subagent limit, do not treat failed
spawn attempts as permission to abandon the subagent operating model. Reuse an
existing agent for bounded side work when possible, and keep the main agent on
the critical path for live HM570 queue checks, gate decisions, and final claim
integration. Record the limit in the execution handoff so future agents do not
misread it as missing delegation.

When writing gate scripts that redirect stdout/stderr into an analysis
directory, create that directory in the gate script before the redirection,
even if the called postprocess helper also creates it internally. On
2026-06-08, the q27 Stage0 solver finished with `run.returncode=0`, but the
Stage0->Stage1 gate exited before postprocess because Bash opened
`R16/analysis/gate_postprocess_stdout.log` before the helper could create
`R16/analysis`. This was a provenance/gate-script failure, not a solver
failure. Fix by adding `mkdir -p "$run_dir/analysis"` or equivalent immediately
before redirected helper calls.

When replacing a remote watcher, avoid broad `pgrep -f ... | kill` patterns
inside the same SSH command because the command's own shell can match the
pattern and terminate before the replacement watcher is started. First inspect
existing watcher PIDs, then stop only the exact long-lived watcher PID, or
start the replacement in a separate command after confirming no watcher is
alive. On 2026-06-08, a q27 Stage2->Stage3 watcher replacement initially
matched the SSH wrapper process; the solver was unaffected, but the watcher had
to be started again as PID 60422.

When launching HM570 build/run commands from Windows PowerShell, avoid mixing
double-quoted remote shell strings with escaped `$PATH` and `$?`. On 2026-06-08
an attempted `make d3q27_pf_velocity_q27_geometric_staircaseimp` command passed
an empty or malformed PATH to the remote shell, producing misleading
`make: command not found` and `tail: command not found` output. Re-run with
single-quoted `ssh HM570 'bash -lc "..."'`, explicit
`PATH=/usr/local/cuda-12.6/bin:/usr/bin:/bin:/usr/local/bin`, and `/usr/bin/make`
when building TCLB variants.

For planar z-wall q27 Li-impact A/B tests, enabling
`staircaseimp=TRUE` did not alter the 0-6400 postprocessed fields at the
reported precision: first contact, beta maxima, max Mach, nonfinite count, and
fluid-only phase drift matched the q27 geometric baseline. Do not keep rerunning
the same planar-wall staircaseimp A/B as a likely explanation for the center
low-phase/void morphology; use it only when geometry is non-planar or when
staircase-specific interpolation fields are explicitly being tested.

For q27 Li-impact maximum-spreading audits, compute and plot at least three
definitions before blaming a single footprint rule: wall-plane `phi=0.5`
intersection/chord, first-fluid-plane near-wall `phi=0.5` chord, and the legacy
layer-projection `max(phi over z=0..3)>0.5` beta_box/beta_area. In the
2026-06-08 q27 Stage4 case these definitions all gave beta_max about
1.50-1.51, so the maximum-spreading discrepancy is not caused by the old
4-layer projection alone.

For q27 Li-impact dynamic wetting, do not interpret the z=0 wall-plane
`PhaseField` as an independent physical liquid layer. In the 2026-06-08
Stage4 theta090 output, z=0 is `BOUNDARY=16` while z=1 is fluid, but
`PhaseField(z=0) == PhaseField(z=1)` exactly at step 3200. This is consistent
with the geometric wetting wall-phase correction/copy behavior and means
wall-footprint plots are boundary-condition diagnostics, not standalone
physical contact evidence. However, the first fluid layer also showed center
gas with an outer liquid ring from step 3600, so the trapped-air/annular-contact
problem is not merely a wall-ghost plotting artifact. Always report wall-ghost,
first-fluid-layer, and second-fluid-layer contact metrics separately before
making conclusions about wetting or air entrapment.

For q27 Li-impact phase-field parameter sweeps, dynamic trapped-air behavior is
highly sensitive to `M` and `IntWidth` even when static contact-angle and
Laplace sigma gates are unchanged. In the 4000-step Re600/We11.56 theta090
sweep, `M=0.01` produced no first-fluid center-gas ring by the audit criterion,
while larger `M` and smaller `IntWidth` produced earlier and stronger annular
contact. Do not treat a static `radAngle` pass as sufficient evidence that
dynamic wetting/contact-line evolution is correct; report `M`, `IntWidth`,
ring-event step, beta, mass drift, Mach, and nonfinite together.

When the user specifies "droplet top is 10 mm above the wall", do not convert
it as "bottom gap is 10 mm". For a 10 uL spherical water droplet, `D≈2.673 mm`;
top-to-wall 10 mm implies bottom gap `≈7.327 mm`, free-fall impact speed
`≈0.379 m/s`, `We≈5.32`, and `Re≈1135` using water-air room-condition
properties. State this assumption explicitly because reversing the top/bottom
interpretation changes We/Re and initial center height.

For the q27 geometric 10 uL top-to-wall 10 mm theta57 high-frequency restart
from absolute step 10000, do not use frames after absolute step 14000 as
morphology evidence unless the VTI arrays are rechecked. On 2026-06-09, the
run wrote VTI files through local restart step 10000, but a post-run read
showed local step 4000 still finite while local step 4200 and later had
`PhaseField` all nonfinite, `P` all nonfinite, and `Rho/U` finite only on the
boundary-cell count. This was not a "postprocess ran before write finished"
artifact. Treat local step 4200 onward as failed negative evidence for that
restart, and do not regenerate blank morphology images as physical results.

For the 10 uL theta57 physical scene, diagnose post-contact instability with
short near-wall equivalent-impact probes before launching another full
top-to-wall fall or long-to-rest run. Keep physical Re/We/theta fixed, reduce
the lattice impact velocity (`impact_u_lu`) and recompute `nu_lu`,
`gravity_lu`, and calibrated `sigma_input`; then check nonfinite, max Mach,
mass/rho drift, beta, and morphology after rebound. On 2026-06-09, the first
near-wall probe `U_lu=0.015, M=0.01, IntWidth=4` ran 12000 steps with
nonfinite 0 but max Mach about 0.109, so reducing the time-step mapping was in
the right direction for NaN avoidance but still not conservative enough for a
long-to-rest run.

For the 10 uL theta57 near-wall equivalent long run, `U_lu=0.015`,
`M=0.01`, and `IntWidth=6` was the first stable long-run candidate. The
60000-step run completed with return code 0, 61 morphology frames, nonfinite
0, max Mach about 0.0382, and late beta changes 0.0. Keep the claim limited:
this proves a numerically stable exploratory image-production path for the
near-wall equivalent setup, not validation of the full top-to-wall free-fall
physics. The morphology still contains a small center low-phase/void-like
feature after spreading, so do not describe the result as physically accepted
without separate wetting/air-entrapment audit and comparison.

When the user asks for many detailed morphology images, distinguish real
simulation frames from postprocessed interpolation. Existing VTI output at
1000-step spacing can only support the 61 real frames `0,1000,...,60000`; it
cannot be honestly converted into 150 real 400-step frames. For the 2026-06-09
10 uL theta57 near-wall equivalent case, the correct solution was a separate
high-frequency rerun with `VTK Iterations=400`, producing 151 real frames
`0,400,...,60000`. Keep raw VTI/PVTI remote-only, pull curated PNG/CSV/JSON,
and record the high-frequency run separately from the lower-frequency long
candidate.

For the 2026-06-09 10 uL theta57 high-frequency near-wall sequence, the
remaining dominant issue is the persistent center low-phase/void-like feature
inside the footprint, not lack of image resolution or beta postprocessing.
After preserving the 151 curated PNG/CSV/JSON artifacts, it is acceptable to
delete the remote raw VTI/PVTI/checkpoint files to recover disk space. Future
work should treat the center void as a wetting/contact-line/air-entrapment and
phase-field parameter issue and test it with targeted diagnostics rather than
rerunning the same visualization-only case.

For strict "official gravity fall" theta57 tests, omit local
`DropletOnlyVelocity` and `DropletVelocity*` XML parameters entirely and use
only `VelocityX/Y/Z=0`, `GravitationZ`, `radAngle`, `Radius/Center*`,
`Density_*`, `Viscosity_*`, `sigma`, `M`, and `IntWidth`. However, if the
binary was built from the current HM570 working tree, the source still contains
a default-off droplet-only velocity extension branch, so the correct claim is
"the case did not enable the extension", not "the binary is unmodified official
source". A clean-source rebuild is needed before making that stronger claim.

In the 2026-06-09 complete 10 uL theta57 gravity fall
`official_gravity_26000`, the center low-phase/void-like morphology still
appeared after first contact: first fluid layer at step 20400, second fluid
layer at 20800, third fluid layer at 21200, and wall ghost plane at 20600.
Therefore the center void is not caused solely by the near-wall equivalent
impact initial condition or `DropletOnlyVelocity`; future diagnosis should
focus on geometric wetting/contact-line dynamics, trapped gas, `M/IntWidth`,
grid resolution, and possibly a geometric-vs-surface-energy A/B.

For the 2026-06-09 10 uL theta57 center-air literature check, do not interpret
the current multi-cell center low-phase footprint as a resolved physical
entrapped bubble. Literature such as Thoroddsen et al. 2005 JFM and Bouwhuis
et al. 2012 PRL supports dimple/annular first wetting and central air
entrapment during drop impact, but a scaling estimate for the present
`D=2.673 mm`, `U≈0.379 m/s` water-air case gives expected dimple/bubble scales
of microns to order `100 um`. The current grid has `dx≈53.46 um` and
`IntWidth=6 lu≈321 um`; the audit inner void radius is about `4.5 lu≈240 um`.
Therefore the current feature is a wetting/contact-line/gas-drainage/interface
diagnostic, not accepted resolved bubble physics. Record this distinction in
future beta and morphology comparisons.

For 10 uL theta57 dimple/refinement runs on HM570, do not assume R50+ grids are
single-GPU feasible on the Tesla P100 16GB. On 2026-06-09, an R50/W6 near-wall
probe with `320x320x192` cells, 10 steps, and essentially no interval VTK
output failed during initialization with `out of memory in cross.cu at line
83`; the run.log reported `Mesh size in config file: 320x320x192`,
`Mesh size 19660800`, and cumulative allocation pressure around the P100
limit. Treat this as failed negative evidence for direct single-card R50/R75/R100
near-wall refinement. Use a smaller intermediate grid such as R40 first, or
separately implement/verify multi-GPU decomposition before relaunching R50+.

When launching long HM570 runs from Windows PowerShell, prefer piping a remote
`bash -s` script over embedding remote variables and command substitutions in a
double-quoted `ssh HM570 "..."` string. On 2026-06-09, a dimple-refinement
launch accidentally expanded `$(cat "$remoteCase/driver.pid")` on Windows and
created misleading remote filenames such as `driver.pid;` and
`driver.nohup.log 2`. The solver did not start. Use a here-string piped to
`ssh HM570 bash -s` for commands containing `$`, `$(...)`, redirects, or
complex quoted paths.

For `hm570_run_single_q27_impact_with_postprocess.sh`, allow the case XML input
to already be the remote destination `case.xml`. A 2026-06-09 R40 relaunch
failed before solver start because `cp "$CASE_XML" "$REMOTE_CASE/case.xml"`
treated source and destination as the same file. The runner now resolves paths
and skips the copy when they are identical. Keep this behavior for restart and
manual relaunch workflows.

The 2026-06-09 composite sphere-tail initializer patch is default-off and only
changes initial phase-field geometry when both `CompositeDropletTailRadius` and
`CompositeDropletTailLength` are positive. `Radius` remains the equal-volume
reference sphere radius; `CompositeDropletBodyRadius=0` auto-solves the reduced
truncated-sphere body radius. The implemented tail points along `+Z`, matching
the current dry-wall impact convention where the top of a falling droplet is
in `+Z`. The smoke case `R25_L8_rt5` proved the parameter path and generated
initial morphology (`phi>0.5` bbox `49x49x57 lu`, nonfinite 0), but it is only
`exploratory_not_validation`. With `IntWidth=6`, an `8 lu` tail is only about
1.3 interface widths long, so treat it as an initialization perturbation and
not as a resolved needle-detachment necking model without further sensitivity
tests.

For the composite tail local velocity extension, prefer
`CompositeDropletTailVelocityMode=1` for the first physical comparison because
it applies a smooth near-uniform residual velocity to the short top cylinder.
The initial axial-ramp idea (`mode=2`) was too conservative for an 8 lu tail
with `IntWidth=6`: a `CompositeDropletTailVelocityZ=-0.002` smoke only reached
about `Uz=-0.00842` at the tail centerline. With `mode=1` and the same
`TailVelocityZ=-0.002`, the R25/L8/rt5 smoke reached centerline tail speeds
about `Uz=-0.00964`, kept max Mach about `0.0167`, and increased liquid-weighted
kinetic energy by only about `0.2669%` relative to the same smooth base
`DropletVelocityZ=-0.008`. Treat this as an initialization perturbation only,
not a validated syringe-detachment model.

For the 2026-06-09 10 uL top-to-wall theta57 free-fall composite-tail tests,
do not use the apparent completed `TailVelocityZ=-0.002` long run as a valid
morphology sequence. The run with `VTK Iterations=1000` and
`SaveCheckpoint Iterations=5000` completed only when `Log/Failcheck` was
reduced from 500 to 100, but direct VTI inspection showed that from step 100
the fluid fields already contained widespread nonfinite values, and from step
500 the fluid `PhaseField`/`P` were entirely nonfinite. The standard dry-wall
postprocess therefore produced blank morphology PNGs after step 0 and
`centroid_z=nan`. This is `failed_negative_evidence` for the current
R25/IntWidth4/M0.01/top10mm/freefall composite-tail configuration, including
the no-tail-velocity short probe. The step-0 initializer remains useful for
geometry inspection, but dynamic free-fall shape comparison needs a new
stability gate, likely using the previously stable near-wall-equivalent
settings or a separate IntWidth/M/resolution retuning before any physical
claim.

For composite-tail stability control, always gate raw fields before morphology
postprocessing. The script `scripts/tclb_vti_finiteness_gate.py` checks CSV
NaN/Inf and raw VTI `PhaseField,U,P,Rho` finite values in fluid cells. A
2026-06-09 six-case short matrix showed that sphere-only top-to-wall free-fall
controls stayed finite through 1200 steps for both `W4/U0.025` and
`W6/U0.015`, but adding the 8 lu composite tail made `W4/U0.025` fail at CSV
iteration 100 even with `CompositeDropletTailVelocityMode=0`; adding
`TailVelocityZ=-0.002` failed the same way. Therefore the immediate root cause
is the composite-tail geometry interacting with thin `IntWidth=4` and the
higher lattice scaling, not the `-0.002` velocity alone. The `W6/U0.015`
tail-geometry and tail-velocity short probes passed finite-field checks, but
their max Mach was about `0.116-0.117`, above a conservative 0.1 ceiling, so
they are only `runtime_sanity` for a short pre-contact window and not long-run
or morphology-comparison candidates.

When running high-cadence full 3D VTI probes on HM570, clean raw VTI/PVTI
immediately after curated JSON/CSV/log artifacts are preserved. The 1200-step
tail matrix briefly filled `/media/yuan/8A0E24070E23EAC1` to 100% because each
192x192x224 case with 100-step VTI cadence produced several GB. The final
curated matrix artifact is under 1 MB locally and the remote matrix directory
contains no raw VTI/PVTI/checkpoint files.

For priority cleanup, delete only raw field/checkpoint files after confirming
the run is either locally curated or `failed_negative_evidence`. On 2026-06-10,
the pilot top-to-wall run, composite-tail failed long run, and tail velocity
probe were cleaned by deleting only `*.vti`, `*.pvti`, and `*checkpoint*.pri`
under `/media/yuan/8A0E24070E23EAC1/runs`, with path-boundary checks and no
active TCLB solver process. The cleanup removed 281 files / 142.54 GiB and
left XML/log/CSV/JSON/PNG/restart XML/returncode provenance in place; the disk
recovered from 22G free / 98% used to 164G free / 82% used.

For Sashko2025 wetting-boundary reproduction, treat Gate A binary/source
provenance as a hard prerequisite before running the Gate B/C comparison
matrix. On 2026-06-10, non-compute preparation generated sphere-spread and
capillary-intrusion XMLs, but the read-only Gate A audit found missing
`surface_q27`, `surface_q27_staircaseimp`, and optional `tprec` binaries, while
the existing `geometric_q27` binary SHA `3373620d...` came from a source tree
with default-off exploratory initializer patches in `Dynamics.R` and
`Dynamics.c.Rt`. Do not describe such binaries as clean official source unless
a clean rebuild/audit proves it. Every Sashko2025 run must bind the exact
binary SHA plus `options.R`/`Consts.h` compile-option snapshot. Keep remote
runners defaulting to `MODE=dry-run`, and keep raw VTI/PVTI/checkpoints
remote-only unless a specific audit requires a curated copy.

For Sashko2025 surface-energy variants, do not invent `_surface` TCLB target
names. In the `d3q27_pf_velocity` build system, surface-energy wetting is the
default branch with `geometric=FALSE`: use
`/home/yuan/src/TCLB/CLB/d3q27_pf_velocity_q27/main` for `surface_q27` and
`/home/yuan/src/TCLB/CLB/d3q27_pf_velocity_q27_staircaseimp/main` for
`surface_q27_staircaseimp`. Confirm this through `options.R` and `Consts.h`
in Gate A before running any Gate B/C case. On 2026-06-10, an attempted
surface-target build was followed by HM570 SSH timeout, so recovery must first
check the build PID/log/binaries and must not blindly relaunch or start Gate B.

For PRE 2025 Table II reduced spherical static wetting, separate finite-field
route health from quantitative wetting-response accuracy. The
`q27_geometric_staircaseimp` batch produced `failed_negative_evidence` because
most non-90 angles hit PhaseField NaNs while returning `0`, but the
`q27_geometric` 200000-step full-angle batch completed all 11 angles with no
NaN/nonfinite and max Mach only about `6.22e-4`. That stable result is still
not a validation pass: its mean H1-H2 error was about `12.50%`, versus about
`1.95%` for the PRE scheme, and the fitted apparent angles were systematically
larger than targets. Do not keep extending the same parameter set; the next
diagnostic should test input-angle remapping and small parameter/boundary
sensitivity to identify whether the error is a calibratable radAngle-response
offset or a deeper curved-boundary wetting-formula mismatch.

For PRE 2025 sphere angle-remap diagnostics, keep target angle and TCLB input
`radAngle` as separate provenance fields. `scripts\make_pre2025_sphere_tableII_cases.py`
supports `--input-angle-map TARGET:RADANGLE,...`, and
`scripts\summarize_pre2025_sphere_tableII.py` records `tclb_radAngle_deg` from
the case XML. This prevents inverse-calibration screens from being confused
with direct Table II reproductions, where `radAngle=theta`.

For PRE 2025 reduced sphere theta030 inverse-angle work, do not extend a full
angle-remap batch just because most 20k cases finish. The estimated
`radAngle=10.6` case returned solver rc `0` and had no run-log NaN, but raw
VTI postprocess found `max_nonfinite_count=2935400`, fluid phase/rho drift
`-100%`, and no fit angle. Follow-up 20k screens found `radAngle=11,12,13,
13.5,14,16,18,20,22,24,26,28,30` all finite with max Mach about `6.68e-4`,
so the current finite bracket is `10.6 failed; 11.0 passed`. Treat these as
finite-field screens only: direct `radAngle=30` changed from H1-H2 error
about `130.5%` at 20k to `32.5%` at 200k, so 20k H1-H2 and contact-angle
values are not equilibrium calibration evidence. Run a single 200k theta030
pilot at `radAngle=11` before any full 11-angle inverse-angle extension.

The 2026-06-10 theta030/radAngle011 200k pilot is finite but not a clean
calibration pass. It completed with rc/postrc `0`, `max_nonfinite_count=0`,
`NumSpecialPoints=392`, and max Mach about `6.68e-4`. It improved theta030
H1-H2 error versus direct radAngle030 at 200k (`19.32%` vs `32.51%`) but
worsened fluid phase/rho drift (`-3.51%/-3.45%` vs about `-1.27%/-1.25%`),
and the fitted angle remained high (`43.76 deg` for a target 30 deg). Next
diagnostic should be a small 200k theta030 bracket inside the stable interval,
such as `radAngle=16,22` and optionally `26`, before any full-angle inverse
mapping run.

For PRE 2025 reduced sphere theta030/radAngle011 parameter sensitivity, do not
treat lower mobility as a simple mass-conservation fix. The 2026-06-10 200k
matrix showed `M=0.05, IntWidth=6` failed at Failcheck with PhaseField NaN
while TCLB still wrote `run.returncode=0`; it is `failed_negative_evidence`.
`M=0.1, IntWidth=6` completed and reduced fluid phase/rho drift relative to
the `M=0.2, IntWidth=6` radAngle011 baseline (`-2.79%/-2.74%` versus
`-3.51%/-3.45%`), but worsened H1-H2 error (`28.30%` versus `19.32%`) and
fitted angle (`46.08 deg` versus `43.76 deg`). `M=0.2, IntWidth=8` gave the
best H1-H2 error in this low-angle set (`17.47%`) and a lower fitted angle
(`42.95 deg`), but still had large fluid phase/rho drift
(`-3.23%/-3.18%`). Treat W8 as a diagnostic direction, not as validation or a
full-angle calibration license.

For PRE 2025 sphere runners, run-log NaN must force nonzero wrapper failure
even if TCLB returns rc 0. `scripts\hm570_prepare_pre2025_sphere_tableII.sh`
was patched on 2026-06-10 so a numerical-failure branch exits `3` when rc is
zero and `CONTINUE_ON_FAILURE=0`. Keep checking `run.numerical_failure`,
run-log NaN patterns, postprocess nonfinite counts, and final step together;
never use rc alone for promotion or cleanup decisions.

For the PRE 2025 reduced theta030 `radAngle011, M=0.1, IntWidth=6`
interrupted long-run diagnostic, a 0-to-600000 restart was used because no
usable checkpoint existed from the earlier 200000-step pilot. The run was
stopped after the 200000-step frame, leaving only 0/50000/100000/150000/200000
VTK outputs and a final log iteration near 202000. Treat this as an
interrupted exploratory morphology sequence only. The final 200000-step frame
still had about `28.30%` H1-H2 error, fit angle about `46.08 deg`, and fluid
phase/rho drift about `-2.79%/-2.74%`, so the large discrepancy is not only a
contact-angle mismatch; it also reflects incomplete relaxation plus material
loss in the current TCLB analogue. Future long runs of this type should save
checkpoints every `50000` or `100000` steps if stop/resume is expected.

For TCLB `d3q27_pf_velocity` code/compile audits, separate three layers before
changing parameters: case XML mistakes, compile-option mistakes, and source
structure risks. On 2026-06-10 the active PRE sphere binary was confirmed as
`d3q27_pf_velocity_q27_geometric` with `OPTIONS_q27=1` and the audited XML used
the default `PhaseField_h/l=1/0`, so missing q27 and `-1/+1` phase-field range
were ruled out for that case. However, the upstream unsafe `PhaseF` wall
read/write pattern and `permissive.access=TRUE` are present, and the current
HM570 binaries are not clean official-source builds because default-off
initializer patches are compiled into `Dynamics.R/Dynamics.c.Rt`. Treat future
publication-facing runs as blocked until a clean-source binary lane with
sha256, `options.R`, `Consts.h`, and `git status` provenance is available.

For PRE 2025 spherical static-wetting diagnostics, never interpret global
`PhaseField` min/max without separating fluid and boundary cells. The 2026-06-10
theta030/radAngle011/M0.1/W6 interrupted run had global `phi_max` up to `3.28`,
but a direct VTI audit showed all `phi>1` cells were boundary/near-solid ghost
cells: fluid `phi_max` stayed below `1.0` at every written frame, while boundary
`phi>1` counts grew from `64` at step 0 to `7192` at step 200000. Therefore the
built-in sphere initializer's missing-0.5 hypothesis was ruled out; the stronger
suspect is wall/solid ghost PhaseF generation and its coupling into near-wall
GradPhi/mu/surface force. Future PRE sphere reports must include fluid/boundary
split phi ranges and overrun counts.

For PRE 2025 low-angle spherical wetting with TCLB `q27_geometric`, the direct
source of the audited boundary ghost `PhaseF>1` cells is the normal geometric
wall formula, not VTI corruption, not the sphere initializer, and not the
surface-energy fallback branch for those cells. Replaying
`PhaseF = pf_f + tan(pi/2-radAngle)*grad_tangent*2h` on the saved VTI fields of
the theta030/radAngle011/M0.1/W6 interrupted run reproduced every audited
boundary overrun to about `1e-8`, with `idx1` and `idx2` both non-boundary
neighbors. The low-angle multiplier is large: `radAngle=11d` gives
`tan(pi/2-radAngle)=5.144554`; a postprocess-only replay at step 200000
predicted `phi>1` boundary counts `7192/1568/384/82/32/0` for radAngle
`11/20/30/45/60/75d`. Treat this as `exploratory_not_validation`: it explains
why low input angle can improve H1-H2 while worsening wall ghost phase and
mass/shape drift, but it is not a solver rerun at those alternative angles.

Local package/provenance validators should not scan their own source file for
old-path markers. In `validate_sashko2025_precompute_package.py`, include the
validator's own path in the scan exclusion list or limit the scan to generator
and runner inputs; otherwise the script can misreport its own historical path
constants as stale package evidence. After that fix, the Sashko2025 package
check reported `package_ok=true`, but Gate A still remained incomplete because
surface binaries were unconfirmed and the geometric binaries still lacked
copied `options.R` evidence.

Gate A provenance validators should also look for source-state markers in both
`artifacts/<audit>/source/git_status_short.txt` and the top-level
`artifacts/<audit>/git_status_short.txt`. Otherwise a curated audit can look as
if the source tree were clean even when the working tree is modified and full
of local exploratory patches. After widening the lookup, the Gate A validator
correctly disclosed `modified_source_tree_disclosed=true`, while the gate
itself still stayed closed because the surface binaries were missing and the
geometric binaries lacked copied `options.R` evidence.

Before any HM570 write or Gate A rerun, verify that the external run root is
actually mounted and writable. On 2026-06-10, `/media/yuan/8A0E24070E23EAC1`
and `/media/yuan/DATA500` were absent on HM570 while `/home/yuan/runs` still
pointed at the stale DATA500 path. The safe fallback for tiny provenance files
was `/home/yuan/tmp`, but that is not a replacement for restoring the active
run root before any build or solver launch.

For Sashko2025 sphere-spread runners, do not grep the literal word
`Failcheck` as a numerical failure. TCLB logs normal configuration lines such
as `Setting callback Failcheck`, which caused the first theta090
`geometric_q27_staircaseimp` run to be falsely marked
`CASE_NUMERICAL_FAILURE` despite rc 0, empty stderr, final VTK at 200000, and
no NaN/Inf. Failure scans should match concrete NaN/Inf/error messages, not
normal callback setup text.

For Sashko2025 sphere-spread postprocessing, do not use a plain global
`phi>0.5` top height as the equilibrium droplet height. The 2026-06-10
theta090 `geometric_q27_staircaseimp` overlay showed disconnected/periodic
high-phase regions near the top boundary, and the naive postprocess reported
`top_z=127`, `h_star=1.6458`, far above the Eq.57 theta090 target. The code
review should add connected-component or geometry-aware filtering anchored to
the solid sphere/droplet region before using `h_star` as a comparison metric.

For Sashko2025 sphere-spread height comparisons, a connected component is not
valid merely because it touches the solid sphere somewhere. The corrected
2026-06-10 review requires thresholded liquid cells outside the solid mask to
touch the top-side solid-sphere shell and extend above `solid_top_z` before
reporting `h_star`. On the completed theta090
`geometric_q27_staircaseimp` case, the final frame split into two liquid
components: one sphere-anchored component below `solid_top_z` and one detached
top/periodic component that caused the old `top_z=127`. The corrected summary
therefore sets `metric_valid=false` and `h_star=null`; do not turn this into an
Eq.57 error number. Keep the component JSON and overlay together with the
summary whenever reporting sphere-spread morphology.

For Sashko2025 sphere-spread runners, write provenance for interrupted and
postprocess-failed cases before relying on `run.done`. The runner should trap
SIGINT/SIGTERM into `run.interrupted`, clear stale `run.done`,
`run.numerical_failure`, postprocess return codes, and the old analysis
directory before reruns, and only touch `run.done` after both solver and
postprocess return zero. Numerical failure scans must check both `run.log` and
`run.stderr` with bounded NaN/Inf/error patterns, while the postprocess must
also report PhaseField/U/P/Rho nonfinite counts, not just PhaseField.

For current Sashko Gate A/B work, the canonical HM570 run root is
`/mnt/8A0E24070E23EAC1/runs` as of 2026-06-10 19:55 +0800. Older
`/media/yuan/8A0E24070E23EAC1/runs` and `/media/yuan/DATA500/runs` records are
historical unless a later mount audit proves they are active again. Before any
new solver launch, check `df -h /mnt/8A0E24070E23EAC1/runs`, free space, and
that generated XML `output=` paths match the canonical root.

For TCLB `q27_geometric` low-angle wetting, the 2026-06-10 clean-lane wall
diagnostics showed that the problem is not simply a curved-wall fallback bug.
The instrumented clean binary
`/home/yuan/src/TCLB_clean_wall_diag_20260610/CLB/d3q27_pf_velocity_q27_geometric/main`
had SHA256 `20be154bff84c1c4e29a37b7c422d85c279364076254ae2fb6caf68cf1f5573d`
and added read-only `WallPfF/WallGradTangent/WallTanCoeff/WallPhasePred/WallBCPath`
outputs. Short 50-step flat/curved runs all had rc 0, postprocess rc 0,
nonfinite 0, and max Mach below `3e-4`. At `radAngle=11d`, both flat and curved
normal geometric path (`WallBCPath=5`) overran immediately: flat step-50
`WallPhasePred_max=1.23943` with `2056` wall cells above 1, curved step-50
`WallPhasePred_max=1.43394` with `100` cells above 1. At theta030, curved
step-50 stayed bounded while flat had only a tiny overrun; theta090 was nearly
bounded. Future fixes should target the low-angle normal-geometric ghost
reconstruction `pf_f + tan(pi/2-radAngle)*grad_tangent*2h`, especially its
unconditional positive `|grad_tangent|` contribution and lack of bounded/profile
consistency. Hidden clamping is only a localization control, not a validated
physics fix.

For TCLB `q27_geometric` low-angle wetting, a bounded wall clamp can be used
only as a named causality control. The 2026-06-10 bounded clean lane
`/home/yuan/src/TCLB_clean_wall_bounded_diag_20260610` produced binary SHA256
`2b950ce317784beed5b403944e9db8f6a9bd415b3c5acddb962c86fb2ea7c3e5` and kept
raw `WallPhasePred` while adding `WallPhaseBoundedPred/WallClampDelta`. Short
flat/curved 50-step tests, radAngle011 1000-step tests, and curved radAngle011
10000-step tests all had rc 0 and nonfinite 0. The clamp zeroed actual wall
`PhaseField>1`, but raw low-angle predictions stayed overbounded; at curved
radAngle011 step10000, baseline had `558` actual wall cells above 1 with
`phase_wall_max=1.43299`, while bounded had actual wall count `0` but raw
`WallPhasePred_max=1.46184`. Fluid `PhaseField>1` was zero after the initial
adjustment window and max Mach stayed below `4.6e-4`. Do not treat this as a
wetting-boundary fix; use it to prove or disprove whether wall ghost values
drive later mass/contact-angle drift, then replace it with a
profile-consistent geometric reconstruction candidate.

For TCLB `q27_geometric` low-angle wetting, the first profile-consistent
diagnostic lane is useful evidence but not a sufficient wetting fix. The
2026-06-10 profile clean lane
`/home/yuan/src/TCLB_clean_wall_profile_diag_20260610` produced binary SHA256
`59e03a6233744f00189b6241551fab30d1a53867a90bee582295f9666899159a` and
replaced the normal geometric wall write with the quadratic
surface-energy/profile-like reconstruction while preserving raw
`WallPhasePred`. Flat/curved health gates passed with rc 0 and nonfinite 0;
the curved radAngle011 10000-step run kept actual wall and fluid `PhaseField>1`
counts at zero even though raw `WallPhasePred` stayed above one. In the real
theta030/radAngle011/M0.1/W6 sphere comparison, the 200000-step profile run
reduced the order-one wall ghost and improved bulk drift (`phase_max`
`1.00000043`, fluid phase/rho drift `-1.53%/-1.51%`), but worsened morphology:
H1-H2 error became `39.45%` and fitted angle `54.87 deg`, worse than baseline
M0.1/W6 and M0.2/W6/W8 controls. Do not extend this exact profile formula to
600k or full Table-II runs as a calibration solution. The next candidate must
preserve a signed/contact-angle-consistent geometric relation instead of simply
using the surface-energy fallback expression for all normal geometric walls.

For the theta030 reduced PRE-sphere profile lane, do not judge the low-angle
wetting response from 200k alone. The 2026-06-10 radAngle011/M0.1/W6 extension
to 600k showed continued slow relaxation: fitted angle/H1-H2 error moved from
`54.87 deg`/`39.45%` at 200k to `36.11 deg`/`6.39%` at 400k, with best H1-H2
agreement at 450k (`1.63%`, fitted angle `34.14 deg`). By 600k, the fitted
angle reached `29.56 deg`, but H1-H2 error worsened to `9.47%` and fluid
phase/rho drift reached `-2.82%`/`-2.77%`. Therefore a near-target global
contact angle is not enough; require height/volume drift and local contact-line
morphology together before calling a profile/geometric wetting candidate
acceptable.

For theta030 profile-lane sphere tests, explicitly audit bottom/underside film
before accepting a visually improved contact-angle trend. The 600k z-min
surface-film audit showed lower-hemisphere near-sphere liquid fraction growing
from `0.1048` at 200k to `0.2067` at 400k and `0.2650` at 600k; bottom120
fraction grew from `0.0566` to `0.1397` and `0.1839`; z-min outside-sphere
liquid fraction grew from `0.0536` to `0.1508` and `0.2288`, with phi maxima
near `1.0`. In the reduced geometry the solid sphere center is `z=24` with
`R_solid=24`, so it touches the z-min wall while the global low `radAngle=11d`
applies to both the outer-domain wall and the sphere. Run a lifted-sphere
geometry-isolation control before deciding whether the remaining problem is
mostly geometric contamination or the profile reconstruction itself.

The lifted-sphere theta030 profile control on 2026-06-11 supports geometry
contamination as a major part of the bottom-film failure. It changed only
`solid_center_z=24 -> 32` and `drop_center_z=72 -> 80`, leaving radAngle11,
M0.1, W6, density ratio, viscosity, and sigma unchanged. At 400k, the global
response stayed comparable to the original z24 run (`H1-H2` error `5.13%` vs
`6.39%`, fitted angle `34.30 deg` vs `36.11 deg`), but z-min outside-sphere
liquid fraction dropped from `0.1508` to `0.0406` and z-min liquid sum from
`4866.8` to `1320.1`. Do not use the z24 touching-bottom setup as the main
wetting calibration geometry. Continue formula work on liftZ32 or another
separated-wall geometry, while retaining z24 as a negative diagnostic case.

For TCLB generated-source lanes, do not trust `make -C CLB/<target>` alone after
editing `.Rt` model files. In the 2026-06-11 v5 unified-special diagnostic lane,
the first binary hash
`895f9bc3bdd8fbf2c6a9324bef8a152fee5a02388c4a48f74541ace9ca2f0ae7` was
superseded because generated source had not been regenerated. The valid route
was `make d3q27_pf_velocity_q27_geometric/source` followed by
`make -C CLB/d3q27_pf_velocity_q27_geometric`, producing binary hash
`f23fc0809c2cdaa1845f843fc81442bcf9614c8bb7b957bf47d95c662bf48e09`. Future
source-candidate reports must include generated-symbol grep evidence, valid
binary hash, and any superseded invalid hash.

For the separated PRE-sphere theta030 z48/gap24/outer90/sphere11 case, the
special/correction wall branches are not the dominant failure path. The 2026-06-11
v5 unified-special lane made the special and correction branches use the same
profile reconstruction and added `WallFluidSampleCount`, `WallFluidSampleH`,
`WallPhaseUnifiedProfilePred`, and `WallUnifiedProfileDelta`. The 100-step smoke
confirmed zonal radAngle worked and bounded the unified prediction, and the 50k
gate completed with rc 0 and nonfinite 0. However, the 50k morphology and global
metrics were numerically identical to v3 (`107.125719 deg` fitted angle,
`104.719123%` H1-H2 error, `-0.618564%/-0.605953%` fluid phase/rho drift, max
Mach `4.91852e-4`) because runtime `NumSpecialPoints=0`. Do not extend v5 as a
fix; move the next audit to the normal curved-wall PhaseF write and near-wall
gradient-read path.

For the separated PRE-sphere theta030 z48/gap24/outer90/sphere11 case, v6
normal-path diagnostics show that raw geometric wall overrun is no longer being
directly written in the current profile lane. The 2026-06-11 v6 passive build
`/home/yuan/src/TCLB_clean_wall_normal_path_v6diag_20260611` produced binary
SHA256 `bef819acdf0101bb2f109e1f5cfb225c81339e3aa7df48c3a03a59fe0119b06f` and
added `WallH`, `WallGeomNormal`, `WallGrad1/2`, `WallGradTangentVec`,
`WallNormalCoeff1/2`, `WallActualMinusProfile`, and `WallActualMinusRaw`. The
100-step smoke had solver/finiteness/wall-postprocess rc 0 and nonfinite 0. On
the normal path, `WallActualMinusProfile` was zero to roundoff, while raw
`WallPhasePred` still reached `1.38245` at step 100 with 180 raw wall-pred cells
above 1. Therefore the next formula audit should ask why the profile/unified
wall write imposes the wrong low-angle curved-sphere response, not whether the
old raw geometric overrun is still directly stored as wall `PhaseF`.

The v6 normal-path 50k gate on 2026-06-11 confirms the same conclusion after
early interface relaxation. In
`/mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_theta030_z48_gap24_outer90_sphere11_normal_path_v6diag_50k_20260611`,
solver, finiteness, PRE metrics, wall-v6, surface-film, and morphology return
codes were all `0`, `run.stderr` was empty, and nonfinite counts stayed `0`.
At 50k, the macroscopic contact response was still wrong (`107.125719 deg`
fitted angle, `104.719123%` H1-H2 error), while normal-path diagnostics showed
`WallActualMinusProfile=0`, raw `WallPhasePred_max=1.4480228`, actual wall
`PhaseField>1` count `0`, and fluid `PhaseField>1` count `0`. Do not extend v6
as a fix. The next candidate must audit and redesign the profile/unified
curved-wall reconstruction itself, with a flat-wall theta030/090/150 gate
before another curved z48 gate.

The v6 M-control run on 2026-06-11 shows that reducing mobility alone does not
fix the separated theta030 curved-sphere response. Using the same v6 binary
SHA256 `bef819acdf0101bb2f109e1f5cfb225c81339e3aa7df48c3a03a59fe0119b06f`,
the z48/gap24/outer90/sphere11 case with `M=0.1`, `W=6`, and 50k steps
completed solver/finiteness/PRE/wall-v6/surface-film/morphology return codes
`0`, with empty `run.stderr`, nonfinite counts `0`, max Mach `4.867e-4`, and
curated tar SHA256
`17e500fcc592c89b747718d39b3ebee7cf8cf8218753d23262609bb6b9c452bb`. Compared
with v6/M0.2 at 50k, M0.1 reduced fluid phase/rho drift from
`-0.6186%/-0.6060%` to `-0.4952%/-0.4851%` and reduced lower90/bottom120 film
fractions from `0.03161/0.00813` to `0.01339/0.00211`, but the apparent angle
remained wrong (`110.464 deg` versus `107.126 deg`) and H1-H2 error remained
above 100% (`107.24%` versus `104.72%`). Treat M as a time-scale/film-amount
control, not as the root fix for this failure. Do not mix this same-binary v6
M-control conclusion with the older z48/profile M0.1 200k lane as though they
were one continuation, because that run used a different diagnostic output lane
and early postprocess angle behavior.
