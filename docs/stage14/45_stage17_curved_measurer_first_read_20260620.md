# Stage 17 — calibrated curved-wall (cylinder) angle measurer + first real read — 2026-06-20

Builds the curved-substrate analogue of the flat-wall golden2 measurer (doc 40),
self-validated against synthetic droplet caps of known theta on the cylinder.
Applied to the doc-44 cylinder smoke for a first real read. This scopes (but does
not close) the cylinder ANGLE gate; the BC-level validation (WallCompactStencil
write on AnalyticCylinder, theta 60/90/120) is the remaining work.

```text
status_label: exploratory_not_validation (measurer validated on synthetics;
              first real read is a smoke that used the old stage12 BC params)
```

## 1. Measurer: grad-normal method, calibrated against synthetic cylinder caps

2D z-centre slice. Cylinder = analytic circle (CX,CY)=(48,48), Rs=20. Droplet cap
on top. cos(theta) = n_s . n_lg, with n_s = solid->fluid = outward radial,
n_lg = liq->gas = -grad(q)/|grad(q)|, averaged (median) over the contact band
(dc in [Rs-2,Rs+3], q in [0.2,0.8], upper surface).

Synthetic generator solves u=Cdy-CY from cos(theta) = [Rs - u cos(beta)]/Rd(u),
beta = contact wrap angle; places a tanh droplet parent circle meeting the
cylinder at the prescribed theta. Self-consistent (achieved == true, exact).

The grad measure under-reads systematically (band-averaging bias), so it is
CALIBRATED against synthetics (beta=30 representative) and inverted, exactly like
golden2.py for the flat wall.

## 2. Calibration (beta=30) and inversion

```
true 40->30.8  60->49.6  80->74.1  90->84.1  100->93.1  120->112.1  140->131.5  150->132.8
inversion self-consistent (true 60/90/120 invert back to 60/90/120, 0 error)
beta-sensitivity at theta=90: beta 20/25/30/35/40 -> meas 78.2/82.5/84.1/86.9/86.5
  => ~+/-4 deg uncertainty from droplet size (beta) dependence.
```

The contour-tangent geometric measure was also tried but was unstable (contact-
point detection + local-tangent fit is noisy at W=3); the calibrated grad measure
is the usable tool for now. A robust contour measure is a future refinement.

## 3. First real read: doc-44 cylinder smoke (t90, step 2000)

```
grad-measured = 91.2 deg ; calibrated-inverted true = 97.9 deg ; target 90.
```
I.e. the cylinder droplet sits at ~92-98 deg (call ~95 +/- 4). Caveat: this smoke
used stage12_cap_static_run.py's XML, which sets the OLD wetting-BC params and may
not enable WallCompactStencilMode=2 (the validated flat-wall BC). So this read
validates the MEASURER on real data, NOT the compact-ghost BC on a cylinder.

## 4. Remaining work to close the cylinder angle gate (Stage 17 proper)

```text
1. Run cylinder static theta = 60 / 90 / 120 with WallCompactStencilMode=2 +
   WriteAllowedFlag=1 on the AnalyticCylinder zone (the validated flat-wall BC
   path), M=0.3 (or 0.6 for faster relaxation), sufficient steps to settle.
   The flat-wall runner (stage13_flat_wall_diagnostic_run.py) renders the compact-
   stencil params; a cylinder variant needs the AnalyticCylinder geometry block
   (see stage12_cap_static_run.py case_spec geom=="cylinder") + the compact-
   stencil Model params merged.
2. Measure with the calibrated curved measurer (golden_cyl.py). Gate: within
   ~+/-5 deg of target (the measurer's calibrated uncertainty).
3. Then sphere static, then low-We impact.
```

## 5. Tools committed
```
/home/yuan/golden_cyl.py  -- curved measurer + synthetic self-validation + calibration
repo/scripts/stage13/golden_cyl_curved_angle.py (mirror)
```
