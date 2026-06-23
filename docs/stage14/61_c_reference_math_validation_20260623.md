# Stage14-61: C Reference Math Validation

Date: 2026-06-23

Status: `formula_and_operator_validation_only`

## Question

Can the current mathematical method be validated first with C/C++ code before
continuing deeper TCLB solver modifications?

Answer: yes, but only at the layered formula/operator level at this stage. This
does not validate TCLB streaming, stage timing, GPU execution, wall bounceback,
or complete contact-angle dynamics.

## Implemented Check

The C++ reference scaffold in
`reference_solvers/phasefield_d3q27_c/phasefield_reference.cpp` now mirrors the
key phase-field formula chain used by the current TCLB model:

```text
mu = 4*(12*sigma/IntWidth)*(C-phi_l)*(C-phi_h)*(C-pfavg)
     - (1.5*sigma*IntWidth)*lapPhi

F_surf = mu * gradPhi

F_phi[q] = w[q] * tmp1 * (e[q] dot n)
tmp1 = (1 - 4*(C-C0)^2)/IntWidth
```

The self-test now covers:

```text
bulk phi=0/1 chemical potential
bulk gradient
continuous planar tanh equilibrium against calcMu
discrete D3Q27 isotropic Laplace residual on planar tanh
discrete D3Q27 isotropic gradient residual on planar tanh
surface-force residual F_surf = mu*gradPhi
Allen-Cahn source zeroth moment
Allen-Cahn source first moment under D3Q27 weights
Allen-Cahn source vanishing in bulk and peaking at interface
```

It writes:

```text
selftest_diagnostics.csv
math_validation_diagnostics.csv
selftest_fields.vtk
```

## Server Result

Run location:

```text
/home/yuan/lbm2026_phasefield_reference
```

Command:

```text
/usr/bin/make clean test
```

Result:

```text
checks=108 failures=0
```

Archived evidence:

```text
artifacts/phasefield_c_reference_math_validation_20260623/selftest_output.log
artifacts/phasefield_c_reference_math_validation_20260623/selftest_diagnostics.csv
artifacts/phasefield_c_reference_math_validation_20260623/math_validation_diagnostics.csv
artifacts/phasefield_c_reference_math_validation_20260623/selftest_fields.vtk
```

Key diagnostics:

```text
planar_mu_exact_laplace_max_abs = 4.06e-16
planar_mu_discrete_max_abs      = 5.72e-02
planar_mu_discrete_rms          = 7.93e-03
planar_laplace_error_max_abs    = 9.54e-03
planar_grad_error_max_abs       = 1.89e-02
planar_surface_force_max_abs    = 1.09e-02
bulk_mu_gas                     = 0
bulk_mu_liquid                  = 0
bulk_grad_norm                  = 0
allen_cahn_first_moment_error   = 7.76e-18
```

## Interpretation

The continuous planar tanh profile closes the current TCLB `calcMu` formula to
roundoff when the exact Laplace is used. This is useful evidence that the
chemical-potential formula itself is internally consistent for the standard
double-well/tanh interface.

The finite D3Q27 stencil has a nonzero residual at `IntWidth=4`. That residual is
small enough for a unit test but not negligible for near-wall contact-angle
work. It must be separated from wall contamination, ghost-node semantics, and
TCLB streaming timing in later gates.

The Allen-Cahn source moment check confirms that the implemented D3Q27 weighted
source has zero zeroth moment and first moment `tmp1*n/3`, consistent with the
D3Q27 second-order tensor. Future code must not silently reinterpret this
lattice moment as `tmp1*n` without the matching lattice prefactor elsewhere.

## What This Does Not Prove

This result does not prove:

```text
contact angle validation
compact-stencil wetting BC correctness
curved-wall correctness
TCLB streaming/stage timing correctness
passive ghost semantics in generated TCLB code
QIBB or bounceback equivalence to the C baseline
mass conservation in long runs
dynamic impact readiness
```

## Next Target

The next C-reference layer should be a one-dimensional or quasi-one-dimensional
explicit phase update with frozen velocity:

```text
phi current cache
grad/lap/mu from passive ghost-aware stencil
one phase-population collide/stream or explicit Allen-Cahn update
mass diagnostic
comparison against TCLB exported fields at the same stage
```

This is the minimum bridge needed before claiming that C and TCLB agree beyond
static formula tests.
