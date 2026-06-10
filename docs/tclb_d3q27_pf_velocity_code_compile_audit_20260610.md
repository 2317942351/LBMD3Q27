# TCLB d3q27_pf_velocity Code and Compile Audit 2026-06-10

Status: `exploratory_not_validation`

Scope:

```text
remote source = /home/yuan/src/TCLB/models/multiphase/d3q27_pf_velocity
remote generated binaries = /home/yuan/src/TCLB/CLB/d3q27_pf_velocity*
active PRE 2025 sphere binary =
  /home/yuan/src/TCLB/CLB/d3q27_pf_velocity_q27_geometric/main
local trigger = user-provided first-round audit text about PhaseF wall update,
                PhaseField range assumptions, wall ghost phase, bulk-vs-wall
                separation, and q27 compile option
```

## Findings

### P0: Published unsafe access concern is present in the current source

GitHub issue 437 is still open and states two model-level unsafe behaviours:

```text
1. wall phase update reads PhaseF and writes PhaseF, creating a potential race
   condition because PhaseF is a stencil field.
2. Init_distributions saves and writes PhaseF, which may affect boundary cells.
```

The current HM570 source matches that pattern:

```text
/home/yuan/src/TCLB/models/multiphase/d3q27_pf_velocity/Dynamics.R
  line 1-5: SetOptions(permissive.access=TRUE), explicitly skips overwritten
            or premature-read checks
  line 72-76: save_initial includes PF
  line 123-125: BaseInit saves g,h,PF and calcPhase saves PhaseF
  line 129-139: calcWall/calcWall_CA and calcWallPhase_correction both save
                PhaseF
  line 160-168: Iteration action runs BaseIter, calcPhase, wall phase update

/home/yuan/src/TCLB/models/multiphase/d3q27_pf_velocity/Boundary.c.Rt
  line 674-681: calcWallPhase_correction writes PhaseF and reads
                PhaseF_dyn(nw_x,nw_y,nw_z)
  line 688-718: calcWallPhase writes PhaseF and reads dynamic neighbour
                phase field
```

Impact:

```text
This is a real source-code risk, not a case-setup typo. It can affect wall
phase ghost values, near-wall gradients, chemical potential, and surface force.
It is highly relevant to droplet impact and curved solid wetting diagnostics.
```

Claim limit:

```text
This audit proves the unsafe access pattern exists; it does not by itself prove
that every observed bubble or static-wetting error is caused by this pattern.
```

### P0: Current production-like binaries are not clean official-source builds

The remote source tree is modified:

```text
git commit = ded67cd768cf7e727bd078af139e3ec7895076e5
git status = modified Dynamics.R and Dynamics.c.Rt
untracked backups = Dynamics.R/Dynamics.c.Rt pre_* backup files
```

The generated binaries include local default-off initializer settings:

```text
d3q27_pf_velocity_q27_geometric/main
  sha256 = 3373620d4c4c8ba952a239bde02030d55ad5b8c5e0b637988bfcd05c111c58ba
  SUMMARY contains CompositeDropletTailRadius/Length and
  DropletOnlyVelocity/CompositeDropletTailVelocity* settings

d3q27_pf_velocity_q27/main
  sha256 = 0c19aaf425e5ff605994fdd17f478d9bdc3ef55b3c877658f790879a9e197899
  SUMMARY contains the same local initializer settings

d3q27_pf_velocity_q27_staircaseimp/main
  sha256 = 672b7612528fba29e7f2efb1f4b511781f2eac03e44de120b661cd3646a340e7
  SUMMARY contains the same local initializer settings
```

Impact:

```text
The PRE 2025 sphere runs using q27_geometric are not based on a clean upstream
binary, even though the added initializer options are default-off for those XMLs.
This is a provenance and publication-claim blocker. Any paper-facing result
must either use a clean rebuilt binary or explicitly disclose the modified
source tree and prove the default-off path is inert for the case.
```

### P1: PhaseField_l/h -1/+1 error is not present in the audited PRE 2025 case

The interrupted `theta030, radAngle011, M=0.1, IntWidth=6` XML does not set
`PhaseField_l` or `PhaseField_h`, so it uses TCLB defaults:

```text
PhaseField_h = 1
PhaseField_l = 0
```

The local source and TCLB docs both define these defaults as liquid/gas values.
The code also assumes the 0/1 convention in several places:

```text
Dynamics.c.Rt line 551:
  tmp1 = (1.0 - 4.0*(PhaseF - C0)*(PhaseF - C0))/IntWidth

Dynamics.c.Rt line 874-895:
  updateMyGlobals uses tmpPF = 1 - pf and pf < 0.5 phase classification
```

Impact:

```text
Do not change this model to PhaseField_l=-1, PhaseField_h=1 without a full
formula rewrite. However, this is not the cause of the latest PRE sphere
theta030 discrepancy because the audited case stayed on the 0/1 convention.
```

### P1: q27 was enabled for the active PRE 2025 q27_geometric runs

The active PRE 2025 sphere binary is:

```text
/home/yuan/src/TCLB/CLB/d3q27_pf_velocity_q27_geometric/main
```

Compile evidence:

```text
options.R:
  MODEL="d3q27_pf_velocity_q27_geometric"
  q27 = TRUE
  geometric = TRUE
  staircaseimp = FALSE

Consts.h:
  #define OPTIONS_q27 1
  #define OPTIONS_geometric 1
  #undef OPTIONS_staircaseimp

run.log:
  Model: d3q27_pf_velocity_q27_geometric

generated Dynamics.c:
  #ifdef OPTIONS_q27
  #define hPops 27
```

Impact:

```text
The pasted concern that q27 might not have been compiled is valid in general,
but it is not the active error in the q27_geometric PRE 2025 sphere matrix.
The non-q27 baseline binary /home/yuan/src/TCLB/CLB/d3q27_pf_velocity/main
does exist and should not be used accidentally for phase-field isotropy tests.
```

### P1: geometric boundary fallback still uses surface-energy formula on some special curved-boundary nodes

In geometric mode, the wall phase update can fall back to surface-energy logic:

```text
Boundary.c.Rt line 713-717:
  if IsSpecialBoundaryPoint == NORMAL_POINTING_INTO_SOLID_ON_FURTHER_NEXT_NODE,
  apply a = -h*(4/IntWidth)*cos(radAngle) and sqrt discriminant formula.
```

In the PRE 2025 reduced spherical case, `NumSpecialPoints=392` was observed.
Therefore this fallback path is not merely theoretical; special curved-boundary
nodes exist in the audited run.

Impact:

```text
This is a strong candidate for the low-angle curved-sphere discrepancy and
for staircaseimp failure modes. It can couple with PhaseField overshoot and
with the same-stage PhaseF read/write pattern. The next diagnostic should
export or instrument counts/min/max on the special-boundary fallback path,
not only global PhaseField min/max.
```

### P2: Wall interior PhaseF=1 and PhaseF=-999 sentinel remain fragile design choices

The source uses physical `PhaseF` as both phase variable and solid sentinel:

```text
Dynamics.c.Rt line 367 and 431:
  if IamWall or IamSolid, PhaseF = -999

Boundary.c.Rt line 877-878:
  abs(tmp) > 26000 detects 27 solid neighbours

Boundary.c.Rt line 701-704:
  h < 0.001 solid-surrounded branch sets PhaseF = 1
```

Impact:

```text
This does not directly prove the current theta030 error, but it is a brittle
curved/complex-boundary implementation pattern. A separate solid mask or wall
phase field would be safer than overloading PhaseF with sentinel values.
```

## Current PRE 2025 sphere case setup audit

Audited XML:

```text
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_radAngle011_M0p1_W6_600k_interrupted_20260610\case.xml
```

Important settings:

```text
binary = /home/yuan/src/TCLB/CLB/d3q27_pf_velocity_q27_geometric/main
domain = 80 x 80 x 140
target theta = 30 deg
TCLB radAngle = 11 deg
R_drop = 24
R_solid = 24
Density_h/l = 1 / 0.001
Viscosity_h/l = 0.09 / 0.1
tauUpdate = 3
sigma = 5e-5
M = 0.1
IntWidth = 6
gravity = 0
PhaseField_h/l = defaults 1 / 0
```

Run evidence:

```text
run.log model = d3q27_pf_velocity_q27_geometric
VTK frames = 0, 50000, 100000, 150000, 200000
postprocess nonfinite = 0
final fit angle = about 46.08 deg
final H1-H2 error = about 28.30 %
final fluid phase/rho drift = about -2.79 % / -2.74 %
```

Interpretation:

```text
The case setup does not contain the two easiest mistakes: wrong PhaseField
range or missing q27. The remaining discrepancy is more consistent with
model/source behaviour: wall phase update safety, special-boundary fallback,
curved-boundary wetting response, and long-time phase/rho drift.
```

## Recommended next actions

### A. Compile provenance gate before more publication-facing runs

Create two binary lanes:

```text
Lane 1 clean_upstream:
  reset or fresh clone at known commit, no local initializer patches,
  build q27, q27_geometric, q27_staircaseimp, q27_geometric_staircaseimp,
  save git commit, git status, options.R, Consts.h, SUMMARY, sha256.

Lane 2 experimental_patched:
  current tree with default-off initializer patches,
  same build evidence, clearly labelled exploratory only.
```

Do not mix results across lanes without explicit disclosure.

### B. Add a read-only wall-phase diagnostic build before changing physics

Instrument, but do not clamp, these quantities:

```text
min/max pf_f used by calcWallPhase
min discriminant in surface-energy formula
min/max written wall PhaseF
counts per IsSpecialBoundaryPoint category
counts of geometric path vs surface-energy fallback
near-wall min/max mu, |gradPhi|, P, U
```

This should be a diagnostic binary with a separate model name or compile tag.

### C. Separate bulk from wall using a small validation ladder

Run short, bounded checks:

```text
1. periodic static sphere, rho ratio 1, no walls, Laplace law
2. periodic static sphere, rho ratio 10
3. wall-attached theta90, same q27_geometric
4. wall-attached theta30/theta130
5. CPU single-rank vs GPU same case if practical
```

Promotion rule:

```text
If periodic sphere fails, debug bulk phase-field/force/mobility first.
If periodic sphere passes but wall cases fail, prioritize wall PhaseF and
special-boundary handling.
If CPU/GPU differ materially, the same-stage stencil access concern becomes
the dominant suspect.
```

### D. Do not use clamp as final fix

Temporary clamp of `pf_f` or discriminant can be used only for localization:

```text
pf_f = min(max(pf_f, 0), 1)
disc = max(disc, 0)
```

It must not be reported as a physical correction unless mass conservation and
thermodynamic consistency are re-derived and audited.
