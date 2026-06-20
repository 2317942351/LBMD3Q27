# Stage 17 — compact-stencil cylinder NaN: diagnostic confirmation + fix approach — 2026-06-20

Confirms doc 48's hypothesis diagnostically and refines the fix. The compact-
stencil q_s WRITE is the NaN cause on the cylinder; without it the cylinder is
stable. No source changed yet; this sets up the fix.

## 1. Diagnostic results (cyl_t90, M=0.6, IntWidth=3, compact-stencil)

```
WriteAllowedFlag=1 (q_s WRITTEN to wall nodes):  PhaseF 80% NaN by step 250
  (711768 / 884768 cells), run stopped on NaN. Violent, early divergence from
  the wall outward.
WriteAllowedFlag=0 (q_s computed as diagnostic but NOT written; analytic ghost
  used instead): ran 1500 steps clean, 0 NaN, 0 failcheck stop.
```
=> the q_s WRITE injection onto the staircase cylinder wall is the cause. The
   q_s MATH (bounded, strict gate) is not the problem; the geometric injection
   onto a jagged staircase boundary is.

This matches doc 48's leading hypothesis (staircase Wall-zone mask != analytic
cylinder SDF): the per-wall-node q_s values written on the jagged staircase
create a high-frequency near-wall phase pattern that destabilises the phase
solve within ~250 steps. The flat wall has no jaggedness (mask == SDF exactly),
so the same write is stable there.

## 2. Refined fix approach (choose by evidence; A first, B for accuracy)

```text
A. Stabilisation gate (minimal, safe): only write the compact q_s on FLAT walls
   (AnalyticSolidType==1); on curved geometry (cylinder/sphere, type 2/3) fall
   back to the existing analytic Briant ghost. One-line gate in calcWallPhase
   where stage13_compact_write_requested() is evaluated. Effect: cylinder becomes
   STABLE (== doc-47 old-BC behaviour) but its angle accuracy is the analytic
   ghost's (~+/-7..15 deg, doc 47). Does not change validated flat-wall results.
   Lowest-risk; unblocks cylinder RUNS but not cylinder ACCURACY.

B. Principled accuracy fix: on curved walls, write the ANALYTIC EQUILIBRIUM near-
   wall phase (tanh profile of the analytic SDF, oriented by the contact-angle
   condition) instead of a per-staircase-node q_s. This gives a SMOOTH near-wall
   field (no staircase jaggedness) -> stable AND accurate. Moderate source change
   in calcWallPhase / a new helper; needs build + the golden_cyl measurer to
   confirm angles within ~5 deg.

C. Diffuse solid (psi/varphi, LBM_Saclay idea from doc 34): structural, smooths
   the whole boundary. Largest change; long-term option.
```

Recommended sequence: implement A now (cheap, restores cylinder stability, no
risk to flat-wall validation), THEN B for cylinder accuracy (the real goal).
C is a separate larger decision.

## 3. Honest status after audit + diagnostic

```text
- The compact-stencil q_s write is validated and stable on FLAT walls (docs 40-43).
- On CURVED geometry the q_s write destabilises the phase solve (this doc + doc 48).
- The cause is confirmed (q_s write on staircase, not the q_s math); the fix is
  well-scoped (A then B). No source changed yet.
```

## 4. Next action (source change; main-agent owned, per AGENTS.md)
Implement option A (gate compact write to flat-only) in Boundary.c.Rt, rebuild
on the server compile lane, re-run cyl_t90 compact-stencil to confirm stability,
then proceed to B for accuracy. Shadow/audit before any validation claim.

## Reproducibility
```
bash /home/yuan/diag_cyl_nan.sh    # WriteAllowedFlag=1 -> NaN by step 250
WriteAllowedFlag=0 variant         # stable to 1500 steps (this doc §1)
scripts mirrored: repo/scripts/stage13/diag_cyl_nan.sh
```
