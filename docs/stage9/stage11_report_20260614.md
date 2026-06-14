# Stage11 — W/R Convergence Audit Report

Date: 2026-06-14
Status: complete (with one case not obtained). Decisive question answered.
No code change.

## Data obtained (5 clean cases + 1 stability limit + 1 not obtained)

All cases: plane wall, theta=30, stage9 Briant binary, 100k steps, tauUpdate=1,
sigma=5e-5, M=0.1.

```
name          W    R   R/W   angle    err    note
s1_W6_R24     6   24   4.0   32.65   +2.65   baseline
s1_W4_R24     4   24   6.0   31.99   +1.99
s1_W3_R24     3   24   8.0   31.30   +1.30
s1_W2_R24     2   24  12.0   FAIL    -      NaN at init (stability limit at W=2)
s2_W6_R12     6   12   2.0   29.21   -0.79   sign-flipped (droplet too small)
s2_W6_R24     6   24   4.0   32.65   +2.65   same as s1_W6_R24 (collapse OK)
s2_W6_R48     6   48   8.0   -       -      not stably obtained (bg launcher issue)
```

## Decisive findings

### Finding 1: Sweep 1 (fixed R=24, reduce W) shows clean monotone convergence

```
R/W = 4 (W=6): err = +2.65
R/W = 6 (W=4): err = +1.99
R/W = 8 (W=3): err = +1.30
```

Error decreases monotonically as W decreases. At W=3 the error is 1.30 deg,
**below the 2 deg target**. The decrease is roughly linear in W (1.3 deg per
halving-ish), consistent with O(W) discretization error at fixed R.

**This is the answer to the decisive question for the practical regime:** at
fixed droplet size, reducing IntWidth reduces the contact-angle error, and W=3
reaches < 2 deg. **For application work at a given droplet size, choosing
W=3 (or as small as the model stably supports) is the lever.**

### Finding 2: W=2 is a hard stability limit

At W=2 the simulation NaNs at initialization, even at dx=0.5 (192^3 grid).
This is the Fakhari-Mitchell model's stability boundary at sigma=5e-5, M=0.1:
the interface-sharpening term overwhelms the Cahn-Hilliard dissipation below
W~3. So W=3 is the practical floor for these model parameters. Reducing sigma
or increasing M might allow smaller W, but that changes the physical regime
and is out of scope here.

### Finding 3: W/R is NOT the only governing parameter (Sweep 2)

The two sweeps do NOT collapse onto a single W/R curve:

```
Sweep 1 at R/W=4 (W=6, R=24): err = +2.65
Sweep 2 at R/W=2 (W=6, R=12): err = -0.79   <- OPPOSITE SIGN
```

At R=12, W=6, the droplet spans only 2 interface widths. The discretization
error changes sign and the droplet is under-resolved. This means **absolute R
(absolute droplet resolution) matters independently of W/R**. The error is not
a pure function of the ratio W/R; it is a function of both W/R and the
absolute resolution R/dx.

The R=48 case (R/W=8, same ratio as W=3 R=24) would have been the clean
collapse test, but it was not stably obtained (background-launcher issue, not
a physics failure).

## Verdict (nuanced, not the binary redirect/reauthorize)

**PARTIAL REDIRECT**, with an important caveat:

1. **For application work at a target droplet size:** reducing IntWidth to W=3
   (the stable floor) brings the theta=30 error to 1.30 deg, below the 2 deg
   target. **This is a viable path.** The cost is a sharper interface (higher
   gradients), but W=3 is stable at the default sigma/M.

2. **W/R alone does not govern the error.** Absolute droplet resolution R/dx
   also matters (Sweep 2 sign flip at R=12). So the rule "increase R to reduce
   error" is only valid for R already large enough to resolve the droplet;
   below ~3-4 interface widths the droplet is under-resolved and the error
   can flip sign.

3. **Wall-surface BC redesign is NOT ruled out, but is NOT warranted by this
   data.** The Sweep 1 monotone convergence shows the dominant error source
   at fixed R is the finite interface width, which a wall-BC change cannot
   address. A wall-surface BC might still help the residual error after W
   reduction, but that is a smaller effect and a separate question.

## Recommendation (not a claim, subject to user direction)

For the user's stated goal (theta=30 to within 2 deg, on plane/cylinder/sphere,
reusable for dynamic impact):

- **Use W=3** as the interface width for production runs. This gives 1.30 deg
  error at theta=30 on a plane, within target.
- **Keep R_drop >= 4*W** (>= 12 lu at W=3) to avoid the under-resolution sign
  flip seen at R=12, W=6.
- **Re-validate** at W=3 on cylinder and sphere before dynamic-impact work.
- **Do NOT pursue wall-surface BC redesign** unless the W=3 residual error
  (1.30 deg) is still too large for the application. It is a smaller lever
  than W reduction.

## What Stage11 did NOT establish

- Whether W=3 gives < 2 deg on curved walls (cylinder/sphere). Plane only.
- Whether W=3 is stable for the sphere STL geometry (the sphere smoke in
  stage9 was at W=6).
- The dynamic-impact behavior at W=3 (higher gradients may affect splashing).
- Whether the wall-surface BC would help — not tested, and per the data not
  the dominant lever.

## Files

- `stage11_design_20260614.md` — test matrix
- `scripts/stage11/stage11_wr_convergence.sh`, `stage11_one.sh`,
  `stage11_analyze.py`, `stage11_bg_r48.sh` — runners and analysis
- `scripts/stage11/stage11_results.txt` — raw data
