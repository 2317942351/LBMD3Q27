# Stage 17 code audit — compact-stencil write NaN on cylinder: hypothesis + approach — 2026-06-20

Code review of the compact-stencil write BC (Boundary.c.Rt, stage9 snapshot) to
determine, before any source change, WHY it NaNs on AnalyticCylinder (~step 1000,
doc 46) when it runs cleanly on the flat wall. This doc records the audit and the
proposed approach; no code is changed.

## 1. What the code does (reconstruction flow)

`calcWallPhase()` runs on wall/solid nodes (IamWall || IamSolid):
- computes analytic normal n_w_a and signed distance sd_a via
  `stage9_analytic_wall_normal_and_distance` (dispatches on AnalyticSolidType:
  1=plane, 2=cylinder, 3=sphere). For cylinder: `stage9_cylinder_normal` /
  `stage9_cylinder_signed_distance` (perpendicular components to axis).
- guard: takes the analytic branch only if `nmag_a > 0.5 && d_to_surface_a < 1.5`.
- probes fluid phase at the lattice neighbour along sign(n_w_a): pf_f = PhaseF_dyn(probe).
- if compact-write requested AND `stage13_compact_solution_can_write()` (STRICT:
  valid + method-complete + fallback 0/4 + bounded-delta small + applied-residual
  small) -> WallGhost = q_s-based ghost; else WallGhost = pf_f (mirror).
- always sets PhaseF = pf_f on the wall node (so gradient stencils never see the
  -999 sentinel).

`stage13_compute_compact_stencil_solution` finds q_f via the 7-plane triangle
search (`stage13_find_compact_qf` -> `stage13_try_compact_triangle` with barycentric
inside test, geometric-fluid vertex gate via analytic SDF), solves q_s from the
contact-angle quadratic (`stage13_fill_compact_stencil_solution`), bounds it
(`stage13_bound_q` to [-eps,1+eps]).

The q_s path is well-guarded and bounded. The NaN is in **P (pressure/density)**,
i.e. the hydrodynamic solve diverges -- not the phase field per se.

## 2. Leading hypothesis: staircase Wall-zone mask != analytic cylinder SDF

```text
Flat wall: the Wall zone (FlatLowerY = the plane y=0) matches the analytic plane
  SDF EXACTLY. Every wall node sits on the analytic surface; d_to_surface_a ~ 0.5
  uniformly; normals are constant. No jaggedness.

Cylinder: the Wall zone is <Cylinder dx="28" nx="40" dy="28" ny="40" dz="0" nz="96">
  -- a STAIRCASE approximation of the cylinder. The analytic SDF is radius 20,
  center (48,48,48), axis z. These two disagree at the surface: some "wall" nodes
  are slightly outside the analytic cylinder (d_to_surface_a ~ 0..1.5, normals
  vary per node), forming a jagged boundary.
```

Consequence: the compact-stencil WallGhost/PhaseF written on these jagged wall
nodes (even when individually bounded) create a high-frequency near-wall phase
pattern -> large near-wall |grad phi| -> large surface-tension force (mu*grad phi)
-> local velocity spikes -> P NaN by ~step 1000. The flat wall has no such
jaggedness, so it is stable.

Secondary possibility: at some staircase corner a wall node's analytic-normal
probe lands on ANOTHER wall node (pf_f stale) AND d_to_surface_a is in the
0..1.5 window, so it takes the analytic branch with a contaminated pf_f. The
guards mostly catch this (both_probes_fluid, valid checks) but a staircase corner
on a curve is exactly where they may be borderline.

NOT the likely cause: the q_s quadratic itself (bounded + strict write gate);
the cylinder normal/distance formulae (simple, correct).

## 3. Confirmatory diagnostic (cheap, no code change)

Re-run cyl_t90 compact-stencil with vtk-period=250 and Failcheck=250 to capture
the frame just before the NaN, then ASCII-map PhaseF and (if present) |U| on a
z-centre slice to LOCATE the blow-up:
- if the explosion is on the staircase cylinder surface (jagged ring) -> confirms
  the mask/SDF-jaggedness hypothesis.
- if it is at a single corner/node -> points to a probe-contamination corner case.

## 4. Fix approach options (after confirmation; pick by evidence)

```text
A. Diffuse/analytic near-wall phase: stop writing per-wall-node ghosts on the
   staircase; instead reconstruct the near-wall phase directly from the analytic
   SDF + equilibrium tanh profile (so the gradient sees a smooth field, not a
   jagged one). Most principled; moderate code change.
B. Diffuse solid indicator (psi): adopt the LBM_Saclay-style diffuse solid mask
   (doc 34 idea) so the boundary is smooth, not staircase. Largest change; the
   doc-34 pack targeted the wrong snapshot but the IDEA is reusable.
C. Stability guard: cap the near-wall gradient / surface-tension force, or the
   velocity, on the cylinder (a damping fix). Smallest change; risks hiding the
   error (clipping) -- only acceptable if reported, per AGENTS.md.
D. Better cylinder mask: make the Wall-zone mask match the analytic cylinder
   more closely (reduce deep staircase corners). Cheap to try; may only delay NaN.
```

Recommended order: run the §3 diagnostic first; if it confirms staircase-surface
blow-up, option A (analytic near-wall phase) is the principled fix; B is the
structural long-term fix; C/D are fallbacks.

## 5. Discipline
This is a code-level change on TCLB; per AGENTS.md it needs main-agent ownership,
shadow-first, and an audit before any validation claim. The diagnostic (§3) is
read-only and can proceed now.

## 6. Files audited
```
Boundary.c.Rt: calcWallPhase (1648-1790), stage13_compute_compact_stencil_solution
  (1064-1120), stage13_fill_compact_stencil_solution (775-860),
  stage13_find_compact_qf (~860-1060), stage9_analytic_wall_normal_and_distance
  (393-404), stage9_cylinder_normal/signed_distance (308-335).
```
