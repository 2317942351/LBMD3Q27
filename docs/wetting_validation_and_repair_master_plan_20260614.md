# Wetting Validation And Repair Master Plan

Status: `runtime_sanity / exploratory_not_validation`.

This document is a planning and gating document. It is not PRE reproduction,
not validation, not a production fix, and not authorization for additional
GPU jobs. It does not modify solver physics code and does not authorize
`Stage8OperatorMode=2`, `sphere11`, 50k runs, long runs, or dynamic impact
cases.

The purpose is to convert the current exploratory Stage8/Track A work into a
deterministic wetting roadmap. Each stage must answer one technical question,
and each failure must route to one correction path before more compute is used.

## Current State

The active public branch is:

```text
codex/track-a-usable-angle-ladder
```

The current Track A matrix contains 17 shadow-only cases:

```text
Stage8OperatorMode = 1
steps = 0, 100, 1000
status = runtime_sanity / exploratory_not_validation
```

Current Track A results:

```text
plane 20/25/30/60/90/120 deg: shadow_pass
plane 150 deg: blocked by normal limiter
cylinder 30/45/60/90/120 deg: blocked by normal limiter
sphere 30/45/60/90/120 deg: blocked by normal limiter
eligible_for_short_write: 0
short_write_pass: 0
```

Important interpretation:

```text
Track A has not run write mode.
Track A has not run sphere11.
Track A has not run 50k, 200k, 400k, or 600k wetting cases.
Track A has not run liquid impact or high-Weber dynamics.
Track A did not modify Stage8/Stage8g solver physics code.
```

Cylinder-specific boundary:

```text
The current cylinder case is a z-extruded solid cylinder with a tangent
diffuse spherical droplet. It is a one-direction-curvature runtime feasibility
diagnostic, not cap-on-cylinder validation.
```

Missing geometry metrics:

```text
cylinder local contact-angle extraction is incomplete
cylinder axial and azimuthal symmetry metrics are incomplete
cylinder internal-void metrics are incomplete
sphere local contact-angle extraction is incomplete
sphere contact-line height and axisymmetry metrics are incomplete
sphere internal-void and lower-side film metrics are incomplete
```

Therefore the current result must not be read as "curved wetting validation
failed". The correct statement is:

```text
Curved-surface shadow candidates are normal-limiter dominated before the
geometry, initializer, local angle, and write-integration gates have been
closed.
```

## Final Goals

### G1: Flat Wall Static Wetting Closed

Flat wall cases must demonstrate a closed static baseline:

```text
target contact angle is specified unambiguously
droplet shape matches spherical-cap geometry within accepted tolerance
theta_fit, height, contact radius, and volume are consistent
mass drift is bounded
max Mach and spurious currents are bounded
nonfinite_total = 0
internal gas void / center bubble count = 0
grid and interface-width sensitivity are understood before publication claims
```

### G2: Cylinder Static Wetting Closed

Cylinder cases must be treated as the independent one-curvature bridge between
flat wall and sphere:

```text
local wall normal transfer is correct
local wall-angle transfer is correct
local contact angle along the contact line is measurable
axial and azimuthal symmetry errors are bounded
initial condition is not the dominant error source
curvature radius and grid sensitivity are understood
write mode does not create mass drift, leakage, or center bubbles
```

### G3: Sphere Static Wetting Closed

Sphere cases may start only after the cylinder middle-angle route is
understood:

```text
local wall-angle and wall-normal transfer are correct
local contact-angle distribution is correct
contact-line height variation is bounded
axisymmetry error is bounded
mass conservation is bounded
lower-side film and outer-wall contamination are absent or explained
center bubbles are absent
sphere radius, grid spacing, and interface width are sensitivity-audited
```

### G4: Low-Angle Wetting Closed Separately

Low angles such as 11, 8, and 5 deg are a separate research track:

```text
low angle = low-angle wetting limit problem
not part of the middle-angle usable ladder
not allowed to block 30-120 deg cylinder/sphere progress
not allowed to authorize dynamic morphology
```

The low-angle route must separately audit:

```text
tan(pi/2 - theta) amplification
cos residual versus tan residual
curvature-aware relation
grid / R / W sensitivity
low-angle-specific initialization
```

### G5: Dynamic Morphology Starts Only After Static Closure

Dynamic droplet morphology or impact may start only after G1-G3 are at least
closed for middle angles:

```text
no dynamic impact before flat wall closure
no dynamic impact before cylinder blocker attribution
no dynamic impact before sphere middle-angle static route is understood
no high-Weber or publication-style impact claim from shadow wetting metrics
```

## Hypotheses And Decisive Tests

Each hypothesis must be resolved by a decisive test before a correction is
implemented.

### H1: Contact-Angle Postprocessing Is Incomplete

Decisive test:

```text
Run no new solver jobs. Apply geometry postprocessing to existing flat/cylinder
/sphere shadow outputs where lightweight metrics are available, and identify
which required quantities remain unknown.
```

Expected pass outcome:

```text
theta_fit and local contact angle can be extracted reproducibly
geometry errors are quantified instead of reported as unknown
limiter classification and angle error classification agree or are explainably
different
```

Expected fail outcome:

```text
contact line cannot be extracted robustly
theta_fit remains unknown
local contact angle is too noisy to rank cases
```

Correction action:

```text
build or repair the contact-line extractor before any write run
add local tangent-plane fallback only as a diagnostic label
do not promote cases based on limiter metrics alone
```

Stop condition:

```text
If postprocessing cannot measure the required angle or internal-void metrics,
stop the corresponding phase and do not run write mode.
```

### H2: Curved Initializers Are Non-Equilibrium

Decisive test:

```text
Compare tangent diffuse spherical droplet, lifted droplet, local tangent-plane
cap, and approximate cap-on-cylinder/cap-on-sphere initializers in shadow mode.
```

Expected pass outcome:

```text
cap-like initialization reduces normal_limiter_fraction, candidate demand,
profile mismatch, and internal-void risk without introducing nonfinite values
```

Expected fail outcome:

```text
all initializers remain limiter dominated
cap-like initialization creates bubbles or worse mass drift
```

Correction action:

```text
if cap-like initializer helps, formalize the initializer and rerun shadow gates
if all initializers fail, route to H4/H5/H6 instead of long runs
```

Stop condition:

```text
If initializer mismatch remains unresolved, no curved short-write or 50k run is
authorized.
```

### H3: Curved Wall-Angle Or Wall-Normal Transfer Is Wrong

Decisive test:

```text
For cylinder and sphere shadow cases, compare gathered wall normal against
analytic geometry normal and verify local wall angle zones.
```

Expected pass outcome:

```text
fluid nodes near cylinder receive target cylinder wall angle
fluid nodes near sphere receive target sphere wall angle
outer wall nodes receive neutral angle
fallback_angle_count is near zero
dot(gathered normal, analytic normal) is positive and close to one
Stage8NormalAgreement p05 is acceptable
```

Expected fail outcome:

```text
wrong angle zone reaches fluid nodes
fallback angle appears in contact-line band
normal orientation flips or is poorly aligned with analytic geometry
```

Correction action:

```text
repair local wall-angle gather and local normal transfer
do not change contact relation before geometry transfer is correct
```

Stop condition:

```text
If angle or normal transfer fails, stop curved-surface physics-candidate work.
```

### H4: Curvature Radius, Grid, Or Interface Width Is Insufficient

Decisive test:

```text
Run shadow-only cylinder radius matrix first: R_cyl = 16, 24, 32, 48 for
theta = 60 and 90. Extend to sphere radius only after cylinder attribution.
```

Expected pass outcome:

```text
normal_limiter_fraction and candidate demand decrease monotonically or
explainably as R/W and grid resolution improve
```

Expected fail outcome:

```text
radius increase does not reduce limiter demand
limiter remains high even on gentler curvature
```

Correction action:

```text
if radius controls the failure, plan grid/R/W sensitivity before write mode
if radius does not control it, route to H5/H6
```

Stop condition:

```text
No grid-converged or publication-style claim is allowed without radius/grid/W
sensitivity.
```

### H5: Stage8g Curved-Boundary Normal Candidate Is Too Stiff

Decisive test:

```text
Use shadow-only diagnostics to compare tan-residual, cos-residual,
residual-relaxed, curvature-aware, and profile-consistent candidates without
writing gradPhiVal.
```

Expected pass outcome:

```text
one candidate reduces limiter-equivalent metrics, candidate demand, and
profile mismatch while preserving nonfinite_total = 0 and vector_limiter = 0
```

Expected fail outcome:

```text
all candidate forms remain limiter dominated
improvement occurs only by hidden clipping or unreported damping
```

Correction action:

```text
formalize the least-stiff mathematically interpretable candidate only after
shadow gates pass
keep all caps and regularization reported as diagnostics
```

Stop condition:

```text
No write mode is authorized from a stiff candidate.
```

### H6: Wall PhaseF Profile Path Conflicts With Fluid-Boundary Gradient Candidate

Decisive test:

```text
Compare profile target, gradient target, target-normal residual direction, and
profile-candidate mismatch sign in the active contact band.
```

Expected pass outcome:

```text
profile path and gradient candidate demand are directionally consistent
profile mismatch remains low where limiter demand is high
```

Expected fail outcome:

```text
profile path and gradient candidate drive opposite corrections
profile mismatch is high in the same region as limiter demand
```

Correction action:

```text
unify wall profile and fluid-boundary gradient contracts before write mode
do not hide the conflict with a stronger limiter
```

Stop condition:

```text
If profile/candidate conflict is unresolved, curved write mode remains
forbidden.
```

### H7: Write-Mode Integration Creates Mass Drift Or Center Bubbles

Decisive test:

```text
After shadow, geometry, and initializer gates pass, run only 100 -> 1000 ->
5000 short-write sequences and inspect mass, Mach, nonfinite, local angle, and
internal-void metrics.
```

Expected pass outcome:

```text
nonfinite_total = 0
mass drift < 1%
max Mach remains in the accepted range
center-bubble count = 0
theta/local-angle metrics remain acceptable
```

Expected fail outcome:

```text
write mode creates mass drift, center bubble, leakage, Mach spike, nonfinite
values, or angle collapse
```

Correction action:

```text
route to center-bubble regression, mass-conservation audit, or write-integration
audit instead of increasing runtime
```

Stop condition:

```text
If short write fails, no 50k run is allowed.
```

## Required Phases

### Phase 0: Evidence Freeze And No Blind Long Runs

Purpose:

```text
freeze Track A as runtime_sanity / exploratory_not_validation
separate current evidence from future write authorization
```

Cases:

```text
existing Track A 17-case matrix
existing Stage8g/Stage8h shadow evidence
```

Run length:

```text
no new solver runs
```

Required metrics:

```text
case status
solver/postprocess rc
nonfinite_total
normal_limiter_fraction
vector_limiter_fraction
candidate demand
known unknown geometry metrics
```

Pass gate:

```text
all current evidence is documented with status boundaries
blocked cases are not treated as validation failures
```

Fail branches:

```text
missing artifact provenance -> rebuild artifact index
conflicting claims -> correct documentation before new runs
```

Must not be done:

```text
no 50k runs
no sphere11
no write mode
no dynamic impact
no validation claim
```

### Phase 1: Flat Wall Closure

Purpose:

```text
turn the flat-wall baseline from shadow feasibility into a static wetting
closure candidate
```

Cases:

```text
30, 60, 90, 120 deg
optional diagnostics: 20 and 150 deg
```

Run length:

```text
shadow review first
short write only after explicit approval: 100 -> 1000 -> 5000
50k only after short-write audit passes
```

Required metrics:

```text
theta_fit
height error
contact radius error
volume or phase mass drift
nonfinite_total
max Mach
spurious current estimate when velocity is available
center bubble / internal void count
```

Pass gate:

```text
abs(theta_fit - theta_target) < 3 deg
height error < 5%
contact radius error < 5%
mass drift < 1%
nonfinite_total = 0
center bubble count = 0
```

Fail branches:

```text
theta wrong but limiter low -> repair postprocessing or initializer
limiter high -> contact relation remains too stiff
mass drift high -> mass conservation audit
center bubble -> free-droplet / bulk regression
```

Must not be done:

```text
do not run cylinder write before flat closure
do not use flat shadow alone as validation
```

### Phase 2A: Cylinder Wall-Normal And Wall-Angle Transfer Audit

Purpose:

```text
determine whether cylinder blocker is geometry transfer or later physics
```

Cases:

```text
theta = 60, 90 deg
R_cyl = 16, 24, 32, 48
Stage8OperatorMode = 1
steps = 0, 100, 1000
```

Required metrics:

```text
Stage8FluidWallAngle p50/p95/p99
Stage8NormalAgreement p05/p50/p95
dot(gathered wall normal, analytic cylinder radial normal)
fallback_angle_count
normal_limiter_fraction
profile_target_mismatch
candidate_demand
```

Pass gate:

```text
local angle zones are correct
analytic normal dot is positive and high
fallback count is near zero in contact band
```

Fail branches:

```text
analytic radial dot bad -> repair local normal transfer
angle fallback high -> repair wall-angle gather
transfer good but limiter high -> Phase 2B/2D
R improves limiter -> Phase 2D plus curvature sensitivity
R does not improve limiter -> candidate or initializer likely dominates
```

Must not be done:

```text
do not write corrected gradients
do not run 50k cylinder
do not tune M/W/radAngle to bypass the transfer audit
```

### Phase 2B: Cylinder Initializer Audit

Purpose:

```text
separate non-equilibrium initial shape stress from boundary-candidate failure
```

Cases:

```text
current tangent diffuse spherical droplet
lifted droplet
local tangent-plane cap initializer
approximate cap-on-cylinder initializer
theta = 60, 90 deg first
Stage8OperatorMode = 1
steps = 0, 100, 1000
```

Required metrics:

```text
normal_limiter_fraction
candidate demand p50/p95/p99
profile mismatch p50/p95/p99
mass/rho drift
max Mach
internal void count when available
contact band active count
```

Pass gate:

```text
cap-like initializer clearly reduces limiter demand without nonfinite values or
voids
```

Fail branches:

```text
cap-like init helps -> formalize initializer
lifted init helps only partly -> initial contact-line stress is important
all initializers fail -> Phase 2D candidate stiffness audit
```

Must not be done:

```text
do not promote tangent spherical droplet as cap-on-cylinder validation
do not run long cases to let a bad initializer relax without attribution
```

### Phase 2C: Cylinder Local Contact-Angle Postprocessor

Purpose:

```text
measure curved contact angle directly instead of using limiter alone
```

Cases:

```text
existing and future cylinder shadow artifacts with available PhaseField data
theta = 60, 90 first
```

Run length:

```text
postprocessing only unless raw data is missing and a separate run is approved
```

Required metrics:

```text
phi = 0.5 interface extraction status
three-phase contact-line extraction status
local wall normal
local interface normal
local contact angle mean/p95/max error
axial symmetry error
azimuthal symmetry error
internal void count
```

Pass gate:

```text
local angle extraction is reproducible
mean local angle error < 5 deg
p95 local angle error < 10 deg
axisymmetry metrics are reported
```

Fail branches:

```text
contact line unstable -> repair extractor
theta noise high -> smooth/postprocess or refine grid
angle and limiter disagree -> investigate profile path or candidate demand
```

Must not be done:

```text
do not classify cylinder geometry from limiter alone after this phase begins
```

### Phase 2D: Cylinder Candidate Stiffness Audit

Purpose:

```text
determine whether the curved-boundary normal candidate is mathematically too
stiff after geometry transfer and initializer effects are controlled
```

Cases:

```text
theta = 60, 90 first
selected R_cyl from Phase 2A
best available initializer from Phase 2B
shadow only
```

Required metrics:

```text
tan-residual demand
cos-residual demand
residual-relaxed demand
curvature-aware demand
profile-consistency mismatch
normal limiter or limiter-equivalent fraction
vector limiter fraction
```

Pass gate:

```text
a candidate reduces demand and limiter-equivalent metrics without hidden clamp
or profile conflict
```

Fail branches:

```text
all candidates stiff -> low-level boundary-operator audit
profile conflict dominant -> unify wall profile and fluid gradient contracts
```

Must not be done:

```text
do not implement a production fix in the same step as diagnostic attribution
do not write mode until a separate write-gate plan is approved
```

### Phase 3: Cylinder Short-Write And Static Validation Candidate

Purpose:

```text
test whether a shadow-clean cylinder route survives actual write integration
```

Cases:

```text
theta = 60, 90 first
then 30, 45, 120 only after 60/90 pass
```

Run length:

```text
100 -> 1000 -> 5000
50k only after short-write audit
```

Required metrics:

```text
nonfinite_total
mass/rho drift
max Mach
local contact angle distribution
axisymmetry
center bubble / internal void count
spurious current
limiter/candidate diagnostics if still available
```

Pass gate:

```text
nonfinite_total = 0
mass drift < 1%
center bubble count = 0
mean local angle error < 5 deg
p95 local angle error < 10 deg
max Mach not elevated
```

Fail branches:

```text
mass drift -> mass-conservation/write-integration audit
center bubble -> center-bubble regression
angle collapse -> candidate/write contract audit
nonfinite -> first-bad-cell packet
```

Must not be done:

```text
do not run cylinder 50k if 100/1000/5000 does not pass
do not claim validation before audit
```

### Phase 4: Sphere Middle-Angle Validation Candidate

Purpose:

```text
move from one-curvature cylinder to two-curvature sphere only after cylinder is
understood
```

Cases:

```text
sphere 90
sphere 60
sphere 45
sphere 30
```

Run length:

```text
shadow first
short write only after shadow + geometry gate
50k only after short write passes
```

Required metrics:

```text
local contact-angle distribution
contact-line height variation
axisymmetry error
mass/rho drift
max Mach
lower-side film fraction
bottom/outer-wall contamination
center bubble / internal void count
outer90 limiter count
fallback angle limiter count
```

Pass gate:

```text
nonfinite_total = 0
outer90 limiter count = 0
fallback angle limiter count = 0
normal limiter or equivalent demand below gate
mean local angle error < 5 deg
p95 local angle error < 10 deg
center bubble count = 0
```

Fail branches:

```text
sphere 90 fails -> sphere normal/angle transfer or two-curvature geometry issue
90 passes but 30/45 fails -> contact relation curvature/angle coupling
cap-on-sphere init improves -> formalize sphere initializer
R_sphere increase improves -> grid/curvature sensitivity
write creates bubble -> center-bubble regression
```

Must not be done:

```text
do not include sphere11 in the usable-angle ladder
do not run sphere 50k before short-write gate
do not use flat spherical-cap formula as sphere validation
```

### Phase 5: Low-Angle Special Track

Purpose:

```text
solve or bound the low-angle wetting limit separately from middle-angle closure
```

Cases:

```text
flat 11/8/5
cylinder 20/15/11
sphere 20/15/11
```

Run length:

```text
shadow and postprocessing first
write only under a separate low-angle gate
```

Required metrics:

```text
tan amplification diagnostics
cos residual diagnostics
curvature-aware demand
grid/R/W sensitivity
low-angle initializer comparison
mass drift
center bubble count
```

Pass gate:

```text
low-angle candidate passes shadow gates without hidden clipping and survives
short-write checks
```

Fail branches:

```text
low angle requires finer grid
low angle requires regularized relation
current model cannot reliably solve the requested low angle
```

Must not be done:

```text
do not let sphere11 block 30-120 deg work
do not use low-angle failure as evidence that middle-angle route is invalid
```

### Phase 6: Center-Bubble Regression

Purpose:

```text
make center bubble and internal void formation an explicit regression signal
```

Cases:

```text
free static droplet
flat 90
flat 30
cylinder 90
cylinder 60
sphere 90
sphere 60
original impact case only after static tests
```

Required metrics:

```text
liquid-core connected component count
internal gas void count
centerline PhaseField min/max
pressure/rho extrema
mass drift
max Mach
interface thickness statistics
spurious current
```

Pass gate:

```text
free droplet and static wall cases do not create internal voids or center
bubbles
```

Fail branches:

```text
free droplet bubble -> bulk/initializer problem
flat clean but cylinder/sphere bubble -> curved wall boundary problem
static clean but impact bubble -> dynamic pressure/We/Mobility issue
low-angle only bubble -> low-angle contact-line issue
```

Must not be done:

```text
do not treat center bubble as a visualization artifact without connected
component evidence
```

### Phase 7: Dynamic Morphology Only After Static Closure

Purpose:

```text
start dynamic wetting or impact only after static plane/cylinder/sphere closure
```

Cases:

```text
flat spreading
cylinder spreading
sphere morphology evolution
droplet impact
```

Run length:

```text
defined by a separate dynamic validation plan
```

Required metrics:

```text
fixed case definition
contact-angle convention
mass conservation
max Mach
nonfinite/failcheck
grid/time-step sensitivity
literature comparison if a validation claim is desired
```

Pass gate:

```text
G1-G3 are closed for relevant angles and audit approves dynamic extension
```

Fail branches:

```text
static gate incomplete -> return to static wetting
dynamic-only failure -> pressure, mobility, Weber, and impact-regime audit
```

Must not be done:

```text
no dynamic impact before static closure
no publication-style dynamic claim from runtime-only evidence
```

## Output Policy

Every output in this route must remain one of:

```text
runtime_sanity
exploratory_not_validation
failed_negative_evidence
validation_candidate only after a separate audit gate
```

Forbidden claims:

```text
PRE reproduction
validated physical prediction
production fix
publication-ready result
grid-converged result
verified high-We result
```

Allowed outputs:

```text
source snapshots
patches
XML templates
CSV/JSON summaries
Markdown reports
PNG figures
lightweight logs
```

Forbidden uploads:

```text
.vti/.pvti/.pri/.vtk raw fields
binaries
archives
credentials
large files over the repository audit threshold
```

## Forbidden Actions

These actions are forbidden until their explicit gates pass:

```text
no blind 50k runs before gates
no write mode before shadow + geometry gate
no dynamic impact before static closure
no sphere11 inside usable-angle ladder
no claiming validation from shadow metrics alone
no hiding failure with unreported clamp, damping, pressure shift, or selective
frame choice
no tuning M/W/radAngle to bypass a failed geometry or candidate audit
```

## Immediate Next Work Order

The deterministic route is:

```text
Phase 0 freeze -> WP1 flat wall closure -> WP2 cylinder blocker attribution
-> WP3 cylinder contact-angle postprocessor -> WP4 cylinder short-write gate
-> WP5 sphere middle-angle route -> WP6 low-angle special track
-> WP7 center-bubble regression -> WP8 dynamic morphology
```

No run should be launched unless its work package states:

```text
the question being answered
the expected pass/fail interpretation
the stop condition
the artifact set to publish
```
