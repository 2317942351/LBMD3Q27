# Stage14-B112 Phase Source Moment Audit Result

Date: 2026-07-03
Branch: `work/phasefield-c-reference-20260623`
Status: `offline_source_moment_audit_complete`
No GPU/TCLB run was executed.

## Purpose

B112 is the first implementation step after the full-book audit. It checks the
phase-population algebra before touching the GPU solver:

```text
D3Q27 velocity/weight set
  -> calcGamma
  -> heq conventions
  -> calcF_phi
  -> tmp1 legacy vs normalized form
  -> zeroth/first/second moments
```

This directly follows the book-derived requirement that conservative
Allen-Cahn LBE source terms must satisfy moment constraints before they are used
as a physical repair.

## New Files

- Script:
  `scripts/stage14/stage14_b112_phase_source_moment_audit.py`
- Evidence:
  `artifacts/stage14_B112_phase_source_moment_audit_20260703/b112_phase_source_moment_audit.json`
- Evidence table:
  `artifacts/stage14_B112_phase_source_moment_audit_20260703/b112_phase_source_moment_rows.csv`

## Static Check

Passed:

```text
python -m py_compile scripts/stage14/stage14_b112_phase_source_moment_audit.py
```

## Summary Output

The script ran 80 combinations over:

- `PhaseField_l/h = 0/1` and `-1/1`
- bulk/interface phase values
- zero and small nonzero velocity
- axis-aligned and oblique normals
- legacy and normalized `tmp1`

Key JSON summary:

```json
{
  "status": "b112_phase_source_moment_audit_complete",
  "row_count": 80,
  "max_abs_gamma_sum_error": 0.0,
  "max_abs_heq_mrt_sum_error": 0.0,
  "max_abs_heq_bgk_effective_sum_error": 0.875016125,
  "max_abs_fphi_sum": 0.0,
  "max_abs_fphi_first_moment_error": 3.3306690738754696e-16,
  "max_abs_fphi_second_moment": 5.204170427930421e-18,
  "legacy_tmp1_non01_min": -2.0,
  "legacy_tmp1_non01_max": 0.25,
  "normalized_tmp1_non01_min": 0.0,
  "normalized_tmp1_non01_max": 0.5
}
```

## Findings

### F1. D3Q27 `F_phi` moment closure is correct for the current weight convention

Code mirrored:

- `Dynamics.c.Rt:5143-5149`
- `Dynamics.c.Rt:6063`

Result:

```text
sum_i F_phi_i = 0
sum_i e_i F_phi_i = tmp1 / 3 * n
sum_i e_i e_i F_phi_i approximately 0
```

The largest first-moment error was only `3.33e-16`, i.e. roundoff level.

Meaning:

The root failure is not that `calcF_phi` uses the wrong D3Q27 lattice weights.
The source vector moment is algebraically clean once `tmp1` and `n` are valid.

### F2. Legacy `tmp1` is only valid for `PhaseField_l=0`, `PhaseField_h=1`

Current runtime code:

- `Dynamics.c.Rt:6024`
- `Dynamics.c.Rt:6452`

Current formula:

```c
tmp1 = (1.0 - 4.0*(C - 0.5)*(C - 0.5))/IntWidth;
```

For `PhaseField_l=-1`, `PhaseField_h=1`, the legacy formula generated:

```text
legacy_tmp1_non01_min = -2.0
legacy_tmp1_non01_max = 0.25
```

The normalized formula generated:

```text
normalized_tmp1_non01_min = 0.0
normalized_tmp1_non01_max = 0.5
```

Meaning:

This is a real repair target. The TCLB model exposes generic
`PhaseField_l/h`, but the source term hard-codes the `[0,1]` convention.
If any case or future branch uses `[-1,1]`, the sharpening source can reverse
sign in bulk and inject nonphysical interface motion.

Recommended B113 patch:

```c
q = (C - PhaseField_l) / (PhaseField_h - PhaseField_l);
tmp1 = (PhaseField_h - PhaseField_l) * 4.0 * q * (1.0 - q) / IntWidth;
```

Keep legacy default if needed, but implement the normalized formula behind
`PhaseEquationMode=1`.

### F3. MRT phase `heq` convention is internally consistent in D3Q27

Mirrored code:

- `Dynamics.c.Rt:6054-6055`
- `Dynamics.c.Rt:6090`

Result:

```text
max_abs_heq_mrt_sum_error = 0.0
```

Meaning:

For the active MRT-like phase update convention:

```text
heq_i = C * Gamma_i
sum_i heq_i = C
```

This is a good sign. It means the immediate phase-source repair can be narrow:
normalize `tmp1`, then gate `F_phi` and boundedness, instead of rewriting the
whole phase equilibrium first.

### F4. BGK phase path appears inconsistent under the q27 code mirror

Mirrored code:

- `Dynamics.c.Rt:6463`
- `Dynamics.c.Rt:6489`
- `model.R:55-57`

Observed:

```text
max_abs_heq_bgk_effective_sum_error = 0.875016125
```

Meaning:

The apparent BGK effective update:

```text
heq_i = C * Gamma_i
update uses w_h * heq_i
```

does not preserve `sum(heq)=C` under the D3Q27/q27 convention. This may be
irrelevant if production runs never use `OPTIONS_BGK`, but it is still a
solver-path hazard and should be guarded.

Recommended handling:

- Do not use BGK path for validation until this is resolved.
- Add a source audit guard that reports active collision path in case metadata.
- If BGK is needed, make its `heq` convention identical to the MRT path or
  prove why `w_h*heq` is intended.

## What B112 Changes in the Diagnosis

Before B112, there were three plausible direct sources:

1. D3Q27 `F_phi` weight/moment error.
2. Bad `tmp1` source amplitude.
3. Phase equilibrium convention mismatch.

After B112:

```text
F_phi lattice moments are not the primary bug.
tmp1 normalization is a confirmed patch point.
MRT heq is currently clean.
BGK heq remains suspicious but likely not the active path.
```

Therefore the next step should not be a broad phase-equation rewrite. It should
be a small, auditable B113:

```text
PhaseEquationMode=0 legacy
PhaseEquationMode=1 normalized_legacy_source
```

Then rerun the same source-moment audit plus a very short no-wall/static
interface smoke before re-entering wall cases.

## B113 Plan

1. Add helper functions in `Dynamics.c.Rt`:

```text
stage14_phase_q(C)
stage14_tmp1_legacy(C)
stage14_tmp1_normalized(C)
stage14_tmp1_for_mode(C)
```

2. Update all `tmp1` call sites:

- `Init_distributions()` around `Dynamics.c.Rt:5491`
- `CollisionMRT()` around `Dynamics.c.Rt:6024`
- `CollisionBGK()` around `Dynamics.c.Rt:6452`

3. Keep default behavior:

```text
PhaseEquationMode=0 -> exact legacy tmp1
PhaseEquationMode=1 -> normalized tmp1
```

4. Add diagnostics:

```text
ReplayTmp1Legacy
ReplayTmp1Normalized
ReplayTmp1Mode
```

5. Add refusal or warning in scripts:

```text
BGK path with q27 and PhaseEquationMode>0 is exploratory until heq is resolved.
```

## Claim Limit

B112 does not prove contact-angle correctness, static droplet correctness, or
dynamic impact readiness. It only proves that one algebraic component,
`F_phi` moments under D3Q27, is clean and that `tmp1` normalization is a
concrete repair point.
