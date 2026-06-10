# Wall Geometric Bounded Diagnostic Stage 3 2026-06-10

Status: `runtime_sanity`

This note records a diagnostic-only bounded wall control for TCLB
`d3q27_pf_velocity_q27_geometric`. It is not a physics fix and must not be used
as validation evidence.

## Bounded Clean Lane

```text
source =
  /home/yuan/src/TCLB_clean_wall_bounded_diag_20260610
base =
  copied from /home/yuan/src/TCLB_clean_wall_diag_20260610
base_commit =
  ded67cd768cf7e727bd078af139e3ec7895076e5
binary =
  /home/yuan/src/TCLB_clean_wall_bounded_diag_20260610/CLB/d3q27_pf_velocity_q27_geometric/main
binary_sha256 =
  2b950ce317784beed5b403944e9db8f6a9bd415b3c5acddb962c86fb2ea7c3e5
options =
  q27=TRUE, geometric=TRUE, staircaseimp=FALSE, isograd=FALSE, tprec=FALSE
provenance =
  /mnt/8A0E24070E23EAC1/runs/tclb_wall_bounded_diag_provenance_20260610
```

The earlier read-only diagnostics remain in `WallPhasePred`. The bounded lane
adds:

```text
WallPhaseBoundedPred
WallClampDelta
```

The actual wall `PhaseF` write is clamped to `[PhaseField_l, PhaseField_h]`
only as a causal localization control. The special
`NORMAL_POINTING_INTO_SOLID_ON_NEXT_NODE` branch is not clamped before its
correction stage, so the original correction semantics are preserved.

## Short Flat/Curved Comparison

Run root:

```text
/mnt/8A0E24070E23EAC1/runs/tclb_wall_geom_diag_bounded_flat_curved_20260610
```

Local curated artifacts:

```text
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\wall_geom_diag_bounded_flat_curved_20260610
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\wall_geom_diag_bounded_summary_20260610
```

All six cases `flat/curved x radAngle 11/30/90` completed with solver rc `0`,
postprocess rc `0`, and nonfinite count `0`.

Step-50 comparison:

```text
case              raw pred>1  actual wall phi>1 bounded  actual wall phi>1 baseline  fluid phi>1 bounded  max Mach bounded
flat_theta011     2024        0                         2056                        732                  2.61e-4
curved_theta011   100         0                         100                         2108                 2.21e-4
flat_theta030     1020        0                         1036                        772                  1.58e-4
curved_theta030   0           0                         0                           2228                 1.73e-4
flat_theta090     192         0                         208                         908                  1.68e-5
curved_theta090   0           0                         0                           2324                 6.78e-5
```

Interpretation:

```text
The bounded diagnostic successfully prevents actual wall PhaseField>1 while
keeping the raw formula overrun visible. However, the step-50 fluid cells can
still show very small PhaseField>1 counts. Therefore a hidden wall clamp is not
a physical fix and does not by itself prove the long-time morphology issue is
resolved.
```

## radAngle 11, 1000-Step Evolution

Run roots:

```text
/mnt/8A0E24070E23EAC1/runs/tclb_wall_geom_diag_baseline_rad011_1000_20260610
/mnt/8A0E24070E23EAC1/runs/tclb_wall_geom_diag_bounded_rad011_1000_20260610
```

Local curated artifacts:

```text
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\wall_geom_diag_baseline_rad011_1000_20260610
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\wall_geom_diag_bounded_rad011_1000_20260610
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\wall_geom_diag_rad011_1000_summary_20260610
```

Key step-1000 values:

```text
case              variant   raw pred>1  actual wall phi>1  fluid phi>1  raw pred max  actual wall max  max Mach
flat_theta011     baseline  1896        1896               0            1.09842       1.09842          2.41e-4
flat_theta011     bounded   1868        0                  0            1.11320       1.00000          2.32e-4
curved_theta011   baseline  212         212                0            1.45718       1.45718          3.43e-4
curved_theta011   bounded   208         0                  0            1.48097       1.00000          3.42e-4
```

By step `250`, the fluid `PhaseField>1` count is zero for both baseline and
bounded variants. The persistent difference is the wall ghost: the baseline
continues to write actual wall values greater than one, while the bounded
control prevents actual wall overrun but leaves raw formula overrun visible.

## Curved radAngle 11, 10000-Step Evolution

Run roots:

```text
/mnt/8A0E24070E23EAC1/runs/tclb_wall_geom_diag_baseline_curved_rad011_10k_20260610
/mnt/8A0E24070E23EAC1/runs/tclb_wall_geom_diag_bounded_curved_rad011_10k_20260610
```

Local curated artifacts:

```text
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\wall_geom_diag_baseline_curved_rad011_10k_20260610
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\wall_geom_diag_bounded_curved_rad011_10k_20260610
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\wall_geom_diag_curved_rad011_10k_summary_20260610
```

Key step-10000 values:

```text
variant   raw pred>1  actual wall phi>1  fluid phi>1  raw pred max  actual wall max  max Mach  nonfinite
baseline  558         558                0            1.43299       1.43299          4.58e-4   0
bounded   528         0                  0            1.46184       1.00000          4.53e-4   0
```

The raw low-angle geometric formula remains over-bounded through 10000 steps,
but the fluid field remains bounded in this short-to-medium diagnostic window.
Thus, the immediate failure mode is not bulk fluid nonfinite growth; the open
question is whether the wall ghost contaminates long-time near-wall gradients,
chemical potential, surface force, mass drift, and apparent contact-angle
relaxation.

## Current Diagnosis

Supported by clean-lane short, 1000-step, and 10000-step controls:

```text
1. The direct low-angle overrun source is still the normal geometric branch:
   PhaseF_wall = pf_f + tan(pi/2 - radAngle) * grad_tangent * 2h.
2. The overrun is not a curved-only fallback bug; flat walls also show it.
3. A bounded diagnostic can suppress actual wall PhaseField>1 without changing
   the raw formula prediction, so it is useful for causality testing.
4. The bounded diagnostic does not make a valid physical wetting scheme. It can
   hide wall values that the model uses to impose contact angle.
5. In the 1000- and 10000-step tests, fluid PhaseField did not develop
   persistent >1 growth or nonfinite values; the longer PRE sphere drift must
   be tested through contact-angle/mass/force metrics, not only phi_max.
```

## Next Solution Direction

Do not promote the clamp to a candidate production fix.

The next defensible implementation should be a named physics candidate:

```text
profile-consistent geometric wall reconstruction
```

Minimum requirements for that candidate:

```text
1. Preserve the target contact-angle relation but avoid unconditional positive
   addition from |grad_tangent|.
2. Keep ghost PhaseField bounded or asymptotically profile-consistent near the
   diffuse interface.
3. Report raw reconstruction terms, boundedness, mass drift, Mach, nonfinite,
   and fallback-path counts.
4. Pass the same flat/curved radAngle 11/30/90 health gate before any 200k or
   600k PRE sphere rerun.
5. Only after the health gate, run a theta030 sphere comparison against:
   baseline clean diagnostic, bounded diagnostic control, and the new physics
   candidate.
```

Claim limit:

```text
This stage is runtime_sanity and causal localization only. It is not a PRE
reproduction, not a publication-ready method, and not validation_passed.
```
