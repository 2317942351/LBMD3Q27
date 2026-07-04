# Stage14 Context Anchor: Phase-Field LBM Book for Root-Cause Repair

Date: 2026-07-03
Branch: `work/phasefield-c-reference-20260623`
Status: `context_anchor_for_compaction`
Source book: `C:/Users/yuanz/Downloads/相场格子玻尔兹曼方法理论与应用.md`
Source SHA256: `845A2F5F3A392AD78DC4F665494FB5A66488B284C5F4D38B94FA48FF6C69F186`

This file is deliberately compact and should survive future context
compaction. It records only project-specific paraphrases and line references.
Do not commit the full book text.

## Why This Anchor Exists

The current LBMD3Q27 failure should no longer be treated mainly as a contact
angle recognition problem or a curved `WallGhost` problem. The book material
most relevant to the active root-cause path is:

```text
PhaseF / h population / F_phi / boundedness / rho(C) / force closure
```

The code path to audit is:

```text
TCLB AddDensity streaming of h_i
  -> calcPhaseF()
  -> PhaseF / C
  -> tmp1 and F_phi
  -> h collision/update
  -> next streamed h_i
  -> rho(C), mu(C), gradPhi, force, F/rho
```

The immediate repair target is therefore the phase population equation and its
producer-consumer timing in TCLB. Wetting and curved-surface work must be
downstream validation, not the first repair lever.

## Fixed Book-to-Code Map

| Book lines | Book concept, paraphrased | Current TCLB code anchor | Repair implication |
|---|---|---|---|
| 381-383 | Choose the phase equation by whether the order parameter must be conservative; conservative Allen-Cahn exists to remove curvature-driven interface motion while keeping simpler second-order structure than Cahn-Hilliard. | `Dynamics.c.Rt:5143` `calcF_phi`; `Dynamics.c.Rt:6024` `tmp1`; `Dynamics.c.Rt:6090` generated `h` update. | Before changing wetting, define the exact target equation: conservative Allen-Cahn, corrected conservative Allen-Cahn, or Cahn-Hilliard-like model. |
| 397-403 | Standard LBE phase models contain second-order error terms; valid corrections require source moments, collision-step corrections, or MRT coupling. | `Dynamics.c.Rt:5143-5149`, `6024-6124`, `6452-6498`; `Dynamics.R:970-1003` B60/B63/B68/B98/B111 switches. | `F_phi` cannot be tuned empirically. Derive zeroth/first/second moments and compare against the generated TCLB update. |
| 409-411 | Conservative Allen-Cahn is attractive because it can use phase gradients and maintain locality, but correction choices affect locality. | `calcGradPhi`, `calcPhaseF`, `calcF_phi`; diagnostics `ReplayPhaseFromH`, `ReplayHPreSum`, `ReplayHPostSum`. | Prefer local repair first: correct the `h` update and source moments before introducing broad nonlocal wall patches. |
| 413-417 | Order-parameter overshoot can create negative density/viscosity, divergence, and false interface motion; hard truncation damages smoothness and mass conservation unless compensated. | `Dynamics.c.Rt:5691`, `6201`, `6351` `rho(C)`; `Dynamics.c.Rt:899-1040` B60 limiter; `Dynamics.c.Rt:4701-4847` `calcPhaseF`. | B60/B111 guards are diagnostic or emergency protection, not a publishable physical repair unless paired with conservative redistribution or a derived bounded scheme. |
| 899-907 | Global mass conservation can coexist with dispersed phase volume loss or droplet shrinkage; boundedness and volume conservation are distinct. | Stage14 morphology failures; `ReplayPhaseFromH`; contact-angle images returning distorted droplets. | A stable total `sum(PhaseF)` is insufficient. Validation needs morphology, interface volume, and phase bounds together. |
| 1276-1280 | Single-relaxation LBE for conservative phase equations needs second-order correction; relaxation choice affects boundedness and interface stability. | `CollisionMRT()` phase section at `Dynamics.c.Rt:6024-6124`; `CollisionBGK()` phase section at `6452-6498`. | The next solver branch should introduce explicit `PhaseEquationMode` candidates, not another ad hoc limiter. |
| 1382-1390, 1501-1505 | Phase equilibrium and source terms must satisfy moment constraints; source has zero zeroth moment and controlled first moment in the model described there. | `calcF_phi(i,tmp1,nx,ny,nz)` returns `wh[i] * tmp1 * e_i dot n`; diagnostics `ReplayFphiSum`, `ReplayFphiMaxAbs`. | First repair audit: compute `sum_i F_phi_i` and `sum_i e_i F_phi_i` in D3Q27 exactly, then compare to intended Allen-Cahn sharpening flux. |
| 1557-1568, 1645-1650 | Correction can be done through collision-step differences or source-term time-derivative corrections; these are distinct numerical models. | B60 source scaling; B63 post-stream projection; B68 wall-origin streaming repair; B111 quarantine. | Do not mix multiple correction philosophies in one validation claim. Implement one named mode with derivation and gate it. |
| 2701-2728 | MRT phase-field models have moment-space source/equilibrium requirements; some standard MRT variants retain `O(Ma^2)` errors. | Current model uses MRT for momentum, but phase population update remains generated around `h`, `heq`, `F_phi`. | Phase MRT/non-diagonal MRT is a second-stage redesign if corrected BGK/source repair fails. Do not jump to it before source moment audit. |
| 2948-2984 | Non-diagonal MRT can cancel second-order errors by coupling moments, with only specific moment updates changed. | Potential future `PhaseEquationMode=non_diagonal_mrt_shadow` branch. | Keep as future redesign path. It is not a local wall-contact patch. |
| 3292-3296 | Two-distribution phase-field LBM couples phase separation and interface force; order-parameter boundedness is stricter in two-phase flow because density and viscosity are interpolated from phase. | `rho(C)` at `5691/6201/6351`; `calcTau`; `F_total/rho`; `ForceDensityClosureMode`. | Low-density blow-up can originate from phase overshoot, not from force closure alone. Fix phase boundedness before interpreting `F/rho` spikes. |
| 3320-3348 | Interface force format and equivalent pressure are linked; different force formats correspond to different pressure definitions. | `p=m0[0]` at `5710`; `calc_Fp` at `5610/5780/6379`; `calc_Fs`; `F_mu` at `5823-5829` and `6421-6426`. | Pressure closure must be derived, not switched by convenience. `m0[0]` may be a lattice pressure moment, not automatically the physical pressure required by the selected force format. |
| 3350-3366 | Different interface-force formats are mathematically equivalent continuously but have different discrete errors, locality, momentum conservation, and spurious current behavior. | `F_surf + F_pressure + F_body + F_mu`; stress reconstruction; force fixed-point loop. | After phase boundedness is repaired, audit force format as a separate closure problem. Do not hide phase failure by omitting `F_mu`. |
| 3490-3500 | Static droplet and spurious-current tests are canonical gates; examples use controlled density ratios, interface width, mobility, and long equilibrium checks. | Future flat-wall/static droplet gates; Stage14 short-run probes are onset diagnostics only. | Contact angle and morphology gates must be preceded by bounded static droplet and pressure/force equilibrium checks. |

## PhaseF and `h` Population Context

The current code makes `PhaseF` a product of streamed `h_i`, not an independent
C-array style current field. This is essential because TCLB `AddDensity`
populations participate in framework streaming.

Current code anchors:

- `Dynamics.R:700`: `calcPhase` loads phase populations and saves `PhaseF`.
- `Dynamics.c.Rt:4701`: `calcPhaseF()` begins the phase reconstruction stage.
- `Dynamics.c.Rt:4838` and `5046`: diagnostics write `ReplayPhaseFromH`.
- `Dynamics.c.Rt:6066/6124` and `6467/6498`: `ReplayHPreSum` and
  `ReplayHPostSum` bracket the generated update.

Context to preserve:

1. `PhaseF` is a producer for density, viscosity, chemical potential, gradient,
   force, and wetting.
2. If streamed `h_i` already produces an out-of-range `PhaseF`, all downstream
   fields are consumers of invalid physics.
3. A wall or wetting patch that changes only `WallGhost` cannot fix a broken
   `h_i -> PhaseF` producer.

## `F_phi` and Boundedness Context

Current implementation:

```text
tmp1 = (1 - 4*(C - 0.5)^2) / IntWidth
F_phi[i] = wh[i] * tmp1 * (e_i dot n)
h update includes both +0.5*Fphi inside relaxation and +Fphi outside.
```

Code anchors:

- `Dynamics.c.Rt:5143-5149`: `calcF_phi`.
- `Dynamics.c.Rt:6024`: MRT-path `tmp1`.
- `Dynamics.c.Rt:6120-6121`: `ReplayFphiMaxAbs` and `ReplayFphiSum`.
- `Dynamics.c.Rt:6452-6462`: BGK-path `tmp1` and `F_phi`.

Book-derived constraint:

The source must satisfy the target conservative Allen-Cahn moment constraints.
The important audit is not only whether `F_phi` is numerically small; it is:

```text
sum_i F_phi_i
sum_i e_i F_phi_i
sum_i e_i e_i F_phi_i
```

under the exact D3Q27 weights and TCLB time level. If these moments do not match
the intended equation, a limiter can delay failure but cannot validate the
physics.

## `rho(C)` Amplification Context

Current implementation:

- `Dynamics.c.Rt:5691`: `rho = Density_l + (C - PhaseField_l)*(Density_h - Density_l)/(PhaseField_h - PhaseField_l)` in `CollisionMRT()`.
- `Dynamics.c.Rt:6201`: helper density interpolation.
- `Dynamics.c.Rt:6351`: the same density interpolation in `CollisionBGK()`.

Book-derived constraint:

At density ratios 200 or 1000, phase overshoot is not a small visual defect.
Any `C < PhaseField_l` or `C > PhaseField_h` changes density and viscosity
outside their intended ranges, then `F_total/rho` can amplify the error. This
means grid refinement is not a root-cause fix unless the discrete phase equation
is already bounded and conservative.

## Force and Pressure Closure Context

Current implementation:

- `Dynamics.c.Rt:5710`: `p = m0[0]`.
- `Dynamics.c.Rt:5610`: `calc_Fp`.
- `Dynamics.c.Rt:5780`: pressure input is consumed by `calc_Fp`.
- `Dynamics.c.Rt:5823-5829`: MRT path constructs `F_mu` and `F_total`.
- `Dynamics.c.Rt:6379`, `6421-6426`: BGK path pressure and `F_mu`.
- `Dynamics.R:961-964`: diagnostic switches for momentum force and pressure
  closure.

Book-derived constraint:

The selected interface-force format defines what pressure variable is
consistent. Therefore, `p=m0[0]` must be audited as a model statement, not just
a coding convenience. The force closure repair must answer:

```text
Is m0[0] the pressure distribution moment, physical pressure, or a normalized
lattice pressure surrogate?

Does calc_Fp expect physical pressure, pressure difference, or reference-
subtracted pressure?

Does F_mu reconstruct stress at the same time level as gradPhi and rho(C)?
```

This should be done after the first phase boundedness producer is no longer
creating invalid `C`.

## What This Book Says to Stop Doing

Do not treat these as final repairs:

- tuning `WallGhost` while `PhaseF=sum(h)` is invalid;
- claiming contact-angle validation from distorted morphology;
- using B60/B111 hard guards as physical evidence without conservation and
  source-moment derivation;
- using grid refinement as the main repair when the population equation is not
  closed;
- dropping `F_mu` or changing `PressureClosureMode` as a "fix" before deriving
  the chosen force format.

## Next Solver Repair Route

The next substantial work should be one coherent branch:

1. Write the exact target equation: conservative Allen-Cahn form, variables,
   bounds, mobility, interface width, and normal definition.
2. Derive the D3Q27 moment constraints for `heq` and `F_phi`.
3. Compare the derivation with current `calcF_phi`, `tmp1`, and generated `h`
   update in both `CollisionMRT()` and `CollisionBGK()`.
4. Add a new explicit mode only after the mismatch is identified:

```text
PhaseEquationMode=legacy
PhaseEquationMode=corrected_source
PhaseEquationMode=bounded_mass_conservative
```

5. Use B60/B111 only as diagnostics/emergency guards during the transition.
6. Re-test static droplet/flat wall morphology only after boundedness is closed.
7. Re-enter contact-angle recognition and curved compact-stencil wetting only
   after flat-wall morphology is physically credible.

## One-Sentence Root-Cause Memory

The book supports the current diagnosis that the root repair path starts at
`h_i` population evolution and conservative Allen-Cahn source closure; `rho(C)`
and force/pressure closure amplify the same failure, while wetting/contact-angle
BCs are downstream validation targets rather than the first fix.
