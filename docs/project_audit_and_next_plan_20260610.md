# TCLB Project Audit And Next Plan

Date: 2026-06-10
Status: read-only main-agent audit

## Claim Boundary

This audit follows the local project rules:

- TCLB `d3q27_pf_velocity` must be validated on its own standard cases.
- No equivalence claim is allowed between TCLB and Wang 2023 ULBM/NMRT.
- Exploratory runs may show runtime stability and first-order trends, but not
  validated physical prediction, grid convergence, or publication readiness.
- Dry-wall or film-impact claims require fixed case definition, fixed beta
  extraction, mass/Mach/nonfinite reports, grid/time sensitivity, literature
  comparison, and contact-angle convention.

## What Is Solidly Completed

### 1. Project Structure And Provenance

Completed:

- Active model and remote roots are recorded.
- Raw VTI/PVTI remote-only policy is established.
- Current run root is `/media/yuan/8A0E24070E23EAC1/runs`.
- File/path provenance is mostly maintained in `tclb_path_index.md` and
  `remote_local_file_index.md`.

Remaining risk:

- Historical `/home/yuan/runs`, `/media/yuan/DATA500/runs`, and
  `/media/yuan/8A0E24070E23EAC1/runs` paths coexist. Future execution should
  use the current active root unless a disk audit changes it.

### 2. Geometric Static Wetting Boundary Metric

Completed to `validation_candidate` for the boundary-condition metric only:

- Geometric static grid-density cases were run for R24/R32/R48-like cases.
- The two-row near-wall interpolation method was audited.
- Preferred row-pair `1-2` gives:
  - theta045 about `42.5-43.8 deg`;
  - theta090 about `87.7-88.8 deg`;
  - theta135 about `135.6-135.8 deg`.
- Max absolute error is recorded as about `2.49 deg`.
- Phi threshold sensitivity over `phi=0.45/0.50/0.55` is within about
  `0.90 deg`.

Interpretation:

- This supports that `radAngle` is being imposed consistently at the near-wall
  two-row level for static planar sessile drops.
- It does not prove that the whole sessile-drop morphology is perfect.
- It does not prove dynamic impact wetting is correct.
- It does not authorize `validation_passed`.

### 3. q27 Geometric Sigma Calibration

Completed as exploratory q27 calibration evidence:

- Independent `q27=TRUE, geometric=TRUE` binary was built.
- Stage 1 single-sigma Laplace:
  - `R=16/20/24`, `121^3`;
  - `sigma_input=0.003892733564013841`;
  - `R2=0.9987003195771007`;
  - `sigma_eff=0.0031714316784367457`;
  - nonfinite `0`;
  - max Mach about `4.97e-5`.
- Stage 2 sigma sweep:
  - 4 sigma values x 3 radii;
  - global calibration `R2=0.999999936842248`;
  - `A_q27=1.6279932875649252`;
  - `B_q27=4.533658854592553e-06`;
  - min per-sigma R2 about `0.9986628`;
  - nonfinite `0`;
  - max Mach about `1.01e-4`.

Interpretation:

- This is a real `sigma_input -> sigma_eff` calibration route.
- It is not final physical validation because the pressure-sampling protocol,
  radius range, q27 route consistency, and target-case mapping still need a
  read-only audit before paper-facing use.
- It cannot be reused for q15 geometric impact results.

### 4. q27 Static Wetting 70/80/90/100/110

Completed as exploratory/static gate evidence:

- q27+geometric `R=50`, `121^3`, `M=0.025`, `IntWidth=6` static wetting cases
  for theta70/80/90/100/110 completed with return code 0.
- Phi sensitivity postprocess completed.
- Gate allowed Stage 4 exploratory impact only.
- Recorded max angle error about `1.4417 deg`, max phi span about `0.3700 deg`.

Interpretation:

- This is strong static wetting evidence for the q27 route.
- It still does not validate dynamic dry-wall impact.

### 5. Impact Postprocess Tooling

Completed:

- Standard impact postprocess reports `beta_area`, `beta_box`, mass/rho drift,
  max Mach, nonfinite, centroid, and morphology.
- Additional wetting contact-event audit separates wall ghost plane from first
  and second fluid layers.
- Additional center-void scale audit exists and reports closed-annular
  low-phase feature scale.
- Maximum-spreading audit now compares multiple beta definitions in the q27 Li
  analogue.

Interpretation:

- The tooling is now good enough to diagnose failure modes.
- Tooling correctness does not imply solver/model correctness.

## Negative Evidence And Blockers

### 1. R0=24 rho772 theta090 Dry-Wall Impact

Status: exploratory negative morphology evidence.

Evidence:

- R0=24, `128^3`, `IntWidth=6`, `M=0.025`, `DropletVelocityZ=-0.008` reached
  0-65600 steps with return code 0.
- Nonfinite `0`, max Mach about `0.0256`.
- Fluid-only phase drift about `1.04%`, rho drift about `0.995%`.
- Beta appeared to plateau.
- But morphology review showed persistent annular/ring-like footprint and
  center low-phase/void.

Interpretation:

- Clean runtime and beta plateau are not physical acceptance.
- Center void/ring morphology blocks validation.
- Continuing the same case longer is low value unless the diagnostic question
  is specifically about asymptotic persistence.

### 2. Higher-Speed R0=24 Probe

Status: exploratory only.

Evidence:

- `DropletVelocityZ=-0.024`, 3x speed, relative We about 9x versus the
  previous lattice setup.
- Max Mach about `0.0901`, close to the `0.1` guard.
- Not resting by 12800.
- No clean stabilized central hole, but grid-like low-phase footprint remains.

Interpretation:

- Do not increase speed further at this lattice scaling.
- A higher-We or higher-impact route needs Mach mitigation through scaling,
  grid, or timestep/lattice mapping, not brute force velocity increase.

### 3. q27 Li Re600/We11.56 Theta090 Impact

Status: exploratory impact only.

Evidence:

- Calibrated `sigma_input=0.003318220521467378`.
- `beta_area_max=1.51135`, `beta_box_max=1.50`.
- Max Mach about `0.0719`.
- Nonfinite `0`.
- Resting candidate false.
- Multi-definition beta audit later showed beta around `1.50-1.51`, so the
  discrepancy is not just the legacy 4-layer footprint rule.
- Dynamic wetting audit found the first fluid layer can show center gas with an
  outer liquid ring.
- M/IntWidth sweep showed trapped-air behavior is sensitive to `M` and
  `IntWidth`; `M=0.01` avoided the first-fluid center-gas ring by the current
  short-run criterion, while larger `M` and smaller `IntWidth` produced earlier
  and stronger annular contact.

Interpretation:

- Maximum-spreading extraction is not the main sole cause of discrepancy.
- Dynamic wetting/contact-line evolution remains unresolved.
- Static wetting and Laplace gates are necessary but not sufficient.

### 4. 10 uL Theta57 Physical Scenario

Status: exploratory with negative center-void scale evidence.

Evidence:

- Current physical mapping:
  - volume `10 uL`;
  - `D=2.673 mm`;
  - top-to-wall gap `10 mm`;
  - bottom gap `7.327 mm`;
  - impact velocity about `0.379 m/s`;
  - `Re≈1135`;
  - `We≈5.32`;
  - `theta=57 deg`;
  - q27 geometric route.
- R25 official-gravity run:
  - `beta_area_max≈1.8423`;
  - max Mach about `0.0731`;
  - nonfinite `0`;
  - fluid-only phase drift about `1.52%`.
- R40 near-wall refinement:
  - `R=40`, `grid=256x256x160`, `dx=33.41 um`;
  - `IntWidth=6 lu = 200.5 um`;
  - max Mach about `0.0601`;
  - nonfinite `0`;
  - max fluid-only phase drift about `1.11%`;
  - center low-phase equivalent diameter about `728 um` first fluid layer.
- Literature-order trapped-air bubble diameter for this scale is about
  `20-100 um`, with dimple lateral scale about `150 um`.
- R50 single-P100 feasibility probe failed with GPU out-of-memory.

Interpretation:

- Air entrapment is physically plausible.
- Current simulated center feature is far too large to call a resolved physical
  bubble.
- The blocker is morphology/contact-line/gas-drainage/interface-resolution, not
  only beta magnitude.

### 5. Composite Tail Route

Status: failed negative evidence for current dynamic setup.

Evidence:

- Optional composite droplet tail initializer and tail velocity were patched
  into source and smoked successfully.
- The dynamic top-to-wall free-fall tail case found nonfinite fluid fields from
  step 100 and blank morphology after step 0.

Interpretation:

- Do not use this tail dynamic run for shape comparison.
- The local source has exploratory initializer patches. Future official
  benchmark reproduction should either use clean source state or explicitly
  disable/record these default-off patches.

## Main Diagnosis

The current project is not "complete". It has reached a useful diagnostic
state:

1. Static near-wall wetting is much better understood and can be treated as a
   boundary-condition `validation_candidate` for the two-row metric.
2. q27 surface-tension calibration is available and shows a strong linear
   `sigma_input -> sigma_eff` relationship.
3. Impact pipelines, checkpointing, and morphology plotting work.
4. However, dynamic contact/air entrapment/morphology is unresolved.

The central issue is:

```text
static contact angle pass + sigma_eff calibration
does not guarantee dynamic contact-line/gas-drainage correctness.
```

The persistent center low-phase/annular contact appears in the first fluid
layer, not only in the wall ghost plane. Therefore it is not merely a wall
plotting artifact. It is a real dynamic numerical/physical-model diagnostic.

## Why Validation Passed Cannot Be Claimed

Validation cannot be claimed because:

- No official TCLB wetting-boundary sphere/capillary/sphere-impact benchmark
  has been reproduced yet.
- Planar rho772 impact has no accepted literature match with error metrics.
- The R0=24 theta090 dry-wall result has negative morphology evidence.
- The 10 uL theta57 result has a center feature much larger than expected
  physical trapped-air scales.
- High-speed probes approach the Mach guard.
- M/IntWidth sensitivity changes dynamic trapped-air behavior, meaning the
  dynamic wetting route is not parameter-robust yet.
- Some local source patches are exploratory and must be controlled before
  official benchmark reproduction.

## Next Step Plan

### Gate 0: Freeze A Clean Execution State

Purpose:

```text
avoid mixing exploratory initializer patches with official model reproduction
```

Actions:

1. Audit current HM570 source tree and binary hashes.
2. Record whether composite-tail parameters are default-off in generated
   configs.
3. For official benchmark reproduction, build clean binaries or explicitly use
   default-off patched binaries with a source audit.

Pass criteria:

- binary path, compile options, SHA256, and source patch state are recorded;
- no hidden patch affects standard droplet/sphere/capillary cases.

### Gate 1: Official Article Sphere Spread Reproduction

Purpose:

```text
verify TCLB wetting boundary implementation against the 2025 official/article
curved static benchmark before using it for paper-facing impact claims
```

Minimum cases:

```text
domain = 128^3
R_d = R_s = 24
rho* = 1000
mu* = 100
M = 0.05
xi/IntWidth = 5
sigma = 0.01
theta = 30, 60, 90, 120, 130 deg first
variants = surface, geometric, surface+staircase, geometric+staircase
```

Metrics:

- final `h* = h/(2R_d)`;
- analytical solution from article Eq. 57;
- relative error;
- mass/rho drift;
- max Mach;
- nonfinite;
- overlay of sphere, phi=0.5 contour, contact line.

Pass criteria:

- intermediate angles reproduce article-level trend;
- low/high angle deviations are explainable and comparable to article;
- no nonfinite;
- morphology visually matches sphere-spread state.

### Gate 2: Capillary Intrusion Dynamic Wetting Reproduction

Purpose:

```text
test dynamic wetting, mobility sensitivity, and thin-film resolution with an
analytical reference before returning to dry-wall impact
```

Minimum cases:

```text
256 x 12 x 12, R=5, L=20R, L0=96
rho*=1000, mu*=100, M=0.05, xi=5, La=1
theta = 20, 40, 60, 80 deg
then R=10 / 512 x 22 x 22 for theta20 and theta60
M sensitivity = 0.025, 0.05, 0.075 for at least theta20 and theta60
```

Metrics:

- front position `x*(t*)`;
- error at article comparison time;
- mass/rho drift;
- max Mach;
- nonfinite;
- interface/morphology overlay.

Pass criteria:

- geometric route behaves as article reports;
- low-angle under-resolution appears/disappears consistently with refinement;
- M sensitivity is quantified.

### Gate 3: Planar Dynamic Wetting Diagnostic Matrix

Purpose:

```text
solve or classify the center void before any long target simulation
```

Recommended short matrix:

```text
case family = q27 geometric dry-wall, theta090
R = 24 or 32 first
M = 0.005, 0.01, 0.025
IntWidth = 4, 6, 8
velocity chosen so max Mach target < 0.05
run window = first contact to shortly after beta max, not to rest
```

Required outputs:

- wall ghost, first-fluid-layer, second-fluid-layer center-gas metrics;
- ring-event step;
- beta_area/beta_box by all three definitions;
- center void physical/lattice scale;
- mass/rho drift;
- max Mach;
- nonfinite;
- morphology sequence.

Pass criteria:

- choose a parameter set where center low-phase feature disappears or shrinks
  with refinement and does not destroy mass/Mach;
- or classify it as unavoidable under the current model/resolution, in which
  case the planar target cannot be publication-ready with this setup.

### Gate 4: Low-We Planar Literature Case

Purpose:

```text
separate beta_max disagreement from target-case ambiguity
```

Actions:

- Choose a published low-We flat-wall impact case with known `D`, `U`, liquid
  properties, static contact angle, and beta_max/morphology.
- Prefer a case close to `We=O(1-10)` if targeting the 10 uL theta57 case.
- If using Healy-type data, choose a case in its range `25 <= We <= 150`
  instead of forcing current `We≈5.3` into that correlation.

Pass criteria:

- dimensionless numbers matched using `sigma_eff`;
- beta definition matched or explicitly bracketed;
- error metric reported;
- morphology acceptable.

### Gate 5: Return To Target Runs

Only after Gates 1-4:

1. Re-run 10 uL theta57 near-wall equivalent with selected `M/W/grid`.
2. Re-run full gravity top-to-wall with checkpoint and at least 50-150
   morphology frames from contact through recoil/stabilization.
3. Then return to original rho_ratio=772 D=1 mm/H=10 mm dry-wall theta090,
   followed by theta045/theta135 and liquid film.

## Immediate Recommendation

Do not continue the existing R0=24 low-We center-void case as if more steps
will solve validation. The next best action is:

```text
Gate 0 clean source/binary audit
then Gate 1 sphere-spread official reproduction
then Gate 2 capillary intrusion
then Gate 3 short planar M/IntWidth/grid dynamic-wetting matrix
```

This sequence directly addresses the user's concern:

```text
Is the model wrong, is the wetting boundary wrong, or is beta/morphology
postprocessing wrong?
```

Current evidence says beta postprocessing alone is not the main issue. The
unresolved issue is dynamic wetting/gas drainage/interface resolution.
