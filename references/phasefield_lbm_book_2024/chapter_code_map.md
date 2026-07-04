# Xu 2024 Phase-Field LBM Book: Project Use Map

Status: literature_metadata_only
Full text is local-only: `C:/Users/yuanz/Downloads/相场格子玻尔兹曼方法理论与应用.md`
Local SHA256: `845A2F5F3A392AD78DC4F665494FB5A66488B284C5F4D38B94FA48FF6C69F186`

Copyright boundary: do not commit the full book text. This file records only
project-specific mapping notes for LBMD3Q27.

## Relevant Chapters

| Chapter | Book topic | Current project use |
|---|---|---|
| 3 | Cahn-Hilliard model, chemical potential, curvature-driven effects, boundedness and dispersed-phase volume conservation | Explains why `PhaseField` leaving `[PhaseField_l, PhaseField_h]` is a physical and numerical failure, not a cosmetic overshoot. Supports replacing hard clamps with boundedness plus mass redistribution or a corrected phase equation. |
| 4 | Conservative Allen-Cahn equation, standard LBE, second-order truncation errors, collision/source corrections | Directly maps to TCLB `h` population update, `tmp1`, `F_phi`, `heq`, and the current B60/B111 boundedness patches. Provides the main theoretical route for a real phase-equation repair. |
| 5 | Higher-order corrected LBE models and source-format comparisons | Useful for deciding whether current `F_phi` discretization is a low-order source of interface distortion; supports source-term A/B tests before changing wetting BCs. |
| 6 | MRT and non-diagonal MRT phase-field models | Relevant if BGK-style `h` collision remains unstable after fixing producer-consumer semantics. This is a second-stage redesign path, not a quick patch. |
| 7 | Two-phase model, static droplet, large-density-ratio behavior, spurious currents, interface-force formats | Maps to `calc_Fp`, `calc_Fs`, `F_mu`, stress reconstruction, `rho(C)`, and pressure-force closure audits. Supports keeping force/pressure closure separate from wall wetting. |

## Direct Code Map

Primary snapshot for the current solver line:

`third_party/tclb_snapshots/stage14_B111_slim_wall_h_quarantine/models/multiphase/d3q27_pf_velocity/`

| Book concept | TCLB code path | Audit question |
|---|---|---|
| Sequence-parameter boundedness | `Dynamics.c.Rt`, `CollisionMRT`, `CollisionBGK`, `calcPhaseF`; diagnostics `ReplayPhaseFromH`, `ReplayHPreSum`, `ReplayHPostSum`, B60/B111 modes | Is `PhaseF=sum(h)` bounded by construction, or only repaired after invalid `h_i` has already polluted `rho`, `mu`, and force? |
| Conservative Allen-Cahn source | `Dynamics.c.Rt`: `tmp1 = (1 - 4*(C-0.5)^2)/IntWidth`, `calcF_phi`, `F_phi[i]`, `h` update | Does the current source form match a corrected conservative Allen-Cahn LBE, including zeroth and first moment constraints under TCLB streaming semantics? |
| LBE truncation-error correction | `Dynamics.c.Rt`: current `h - omega*(h - heq + 0.5*Fphi) + Fphi` update and B60 limiter | Is B60 a numerical limiter only, or does it correspond to a legitimate second-order source/collision correction? |
| Phase-field population time level | `Dynamics.R`: `AddDensity` vs `AddField`; `Dynamics.c.Rt`: `calcPhaseF` before collision | Does TCLB streaming make `h_i` a post-stream population while diagnostics or repairs treat it as a current C-array value? |
| Chemical-potential and curvature terms | `Dynamics.c.Rt`: `calcMu`, `calcGradPhi`, `calc_Fs` | Are gradients/Laplace/stencils near walls consuming solid sentinel or nonphysical ghost values? |
| Density interpolation from phase | `Dynamics.c.Rt`: `rho = Density_l + (C - PhaseField_l)*(Density_h - Density_l)/(PhaseField_h - PhaseField_l)` | Does any out-of-range `C` create negative/huge density and amplify `F/rho`? |
| Pressure and interface-force format | `Dynamics.c.Rt`: `p=m0[0]`, `calc_Fp`, `calc_Fs`, `F_mu`, `F_total`, `PressureClosureMode` | Does the code use the pressure moment, physical pressure, or a reference-subtracted pressure in a way consistent with the selected two-phase model? |
| Spurious current and force closure | `Dynamics.c.Rt`: stress reconstruction, `F_mu`, force fixed-point loop, `ForceDensityClosureMode` | Is `F_mu` a stabilizing correction, or a feedback amplifier when `gradPhi`/rho are already invalid? |
| Wetting boundary as downstream consumer | `Boundary.c.Rt`: `WallGhost`, `stage13_compute_analytic_wall_ghost`, `h` reconstruction in Zou-He helpers | Do not tune `WallGhost` until the bulk/near-wall phase population equation is bounded and conservative enough to preserve morphology. |

## Engineering Use

This book should drive the next solver repair branch in this order:

1. Establish the exact conservative Allen-Cahn equation intended by the TCLB model.
2. Derive the discrete zeroth and first moments of `calcF_phi`.
3. Compare that derivation with the current generated `h` update and TCLB streaming order.
4. Replace ad hoc hard clamps with a conservative boundedness correction only after the moment mismatch is identified.
5. Revisit pressure/force closure with the chapter 7 two-phase force-format discussion.
6. Return to contact-angle and curved wetting only after flat-wall morphology is stable.

## Context Anchor

For context-compaction-safe notes specifically tied to
`PhaseF / h population / F_phi / boundedness / rho(C) / force closure`, see:

`docs/stage14/179_phasefield_lbm_book_context_anchor_20260703.md`
