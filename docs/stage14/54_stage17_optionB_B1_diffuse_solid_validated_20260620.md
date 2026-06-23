# Stage 17 option B — B1 offline result: diffuse-solid smooths the near-wall gradient — 2026-06-20

B1 (the mandatory offline gate before any curved-wall dynamics edit, doc 52/53).
Prototype of option B-i (diffuse solid indicator) on the analytic cylinder shows
it removes the near-wall gradient jaggedness that destabilises the phase solve.
=> pursue B-i (diffuse solid) for the curved-wall fix; the q_s math stays, the
boundary indicator becomes smooth. No source changed.

## The offline experiment (pure python, no server compute)

Emulated the TCLB cylinder on the 96^2 z-slice: analytic signed distance sd to the
cylinder (centre 48,48, R=20); the sharp "solid" indicator I_sharp = (sd<0) (the
staircase mask TCLB's <Cylinder> Wall zone produces); and a DIFFUSE indicator
I_diff = gaussian_filter(I_sharp, sigma=1.5). Compared the near-wall gradient
(the quantity that feeds the phase solve / surface-tension force) in the band
|sd|<2.

```
indicator            near-wall |grad(I)| std / mean / max
sharp staircase      0.298 / 0.262 / 0.707
diffuse gauss s=1.5  0.044 / 0.198 / 0.255

phase field q over the indicator, near-wall |grad(q)| std / max
sharp                0.297 / 0.704
diffuse              0.178 / 0.548   (~40% smoother)
```

## Verdict

The diffuse-solid indicator reduces the near-wall gradient jaggedness by ~6x (std)
and ~3x (max) on the indicator, and ~40% on the tanh phase field. That jagged
gradient is exactly what destabilises the compact-stencil write (doc 46) and
contaminates the analytic ghost (docs 50-51). => smoothing the boundary indicator
is the principled fix; **option B-i (diffuse solid) is the chosen direction**.

This is consistent with the LBM_Saclay psi/varphi structural idea (doc 34): a
diffuse solid field psi replaces the sharp staircase mask, the wetting/contact-
angle condition is imposed on the diffuse psi, and the near-wall phase field is
smooth by construction.

## Why B1 first was the right call (the lesson)
A purely local q_w(theta) "smooth ghost formula" is under-determined (doc 52/53);
rushing one would have produced a stable-but-wrong BC. The offline prototype
instead identifies that the fix is boundary INDICATOR smoothing (diffuse solid),
not a new per-node ghost formula -- and validates it on known geometry before any
TCLB edit.

## Next (B2, after this B1 gate) -- structural TCLB change, shadow-first
```
B2. Implement a diffuse solid indicator (psi) for AnalyticSolidType>=1.5 in TCLB:
    - register a psi field (Dynamics.R), filled from the analytic SDF
      (psi = 0.5[1 - tanh(2*sd/w_psi)] or a few-mask-pass smoothing of the solid);
    - use psi (not the sharp IamWall/IamSolid) for the near-wall gradient/ghost
      path on curves;
    - SHADOW first: compute the diffuse-based ghost into a diagnostic, do NOT change
      dynamics; confirm 0 NaN on cyl 60/90/120 and that the implied angle (golden_cyl)
      is closer to target than the +25 deg analytic-ghost read.
B3. Enable the write only if B2 shadow passes; B4 audit (AGENTS.md).
```

## Reproducibility
```
offline prototype: see this doc (scipy.ndimage.gaussian_filter on the staircase
  cylinder indicator; compare near-wall |grad| sharp vs diffuse).
golden_cyl synthetics remain the known-truth validation set for B2/B3.
```
