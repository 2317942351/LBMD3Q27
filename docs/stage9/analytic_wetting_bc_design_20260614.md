# Stage9 Analytic-Geometry Diffuse-Interface Wetting BC

Date: 2026-06-14
Status: `exploratory_not_validation` (planned; not validated by this document).

Branch: `feature/analytic-wetting-bc-diffuse-interface`
Baseline: `third_party/tclb_snapshots/upstream_base/` (clean upstream TCLB
`d3q27_pf_velocity`, no stage5/6/7/8 patches).

## 0. Goal

A single, physically correct wetting boundary condition that, for analytically
parameterisable solids (plane, infinite/finite circular cylinder, sphere),
recovers the prescribed static equilibrium contact angle `theta_e` to within
about `±2 deg`, and remains stable and correct when reused for dynamic impact
on the same geometries.

Non-goals of this stage:

```text
arbitrary STL geometry (analytic normals require parameterisable surfaces)
dynamic contact-angle hysteresis / Kistemaker contact-line friction
separate moving-contact-line slip model (CH diffusion supplies implicit slip)
```

## 1. Physics

### 1.1 Continuous wetting BC

Cahn-Hilliard free-energy functional with a wall free-energy density
`w(phi) = -gamma_sv*cos(theta_e)*phi`:

```text
F[phi] = int_V [ f0(phi) + (kappa/2)|grad phi|^2 ] dV
       + int_S w(phi) dS
```

Varying with respect to `phi` gives the bulk Allen-Cahn/Cahn-Hilliard equation
plus the **natural wall boundary condition on the solid surface S**:

```text
kappa * (partial phi / partial n_w) + partial w / partial phi = 0
=>  kappa * (partial phi / partial n_w) = gamma_sv * cos(theta_e)
```

where `n_w` is the **local outward wall unit normal** (pointing into the fluid).
This is the exact continuous BC. Two facts:

1. `n_w` is the only geometry-dependent quantity. The BC form is identical on
   plane, cylinder, and sphere surfaces.
2. **The wall curvature does not enter the BC**. Curvature affects the solution
   only through the bulk flow and the static drop shape (Laplace pressure),
   which the solver already handles. No explicit `1/R` correction term is
   added to the wetting BC; this is consistent with Ding & Spelt (2007 JCP),
   Fakhari & Mitchell (2017 PRE), and Xu et al. (2018 PRE).

### 1.2 Sharp-interface limit of the BC (used as a sanity check only)

For a hyperbolic-tangent equilibrium interface of width `W = IntWidth`,

```text
phi(s) = 0.5*(1 - tanh(2 s / W))   (s = signed distance into liquid > 0)
grad phi = -(2/W) * sech^2(2s/W) * n_interface
```

At the contact line the geometric relation
`cos(theta_e) = (n_w . n_interface)` holds, giving the legacy ghost-value
formula that the original TCLB geometric BC uses:

```text
phi_ghost = phi_f + 2 h * tan(pi/2 - theta_e) * |grad_t phi|
```

This is exact in the `W/R_drop -> 0` limit but has `O(W/R)` error for finite
`W`. We do **not** write this formula; we use it only as a check that the
diffuse BC reduces to it for large droplets.

### 1.3 Diffuse-interface wetting BC (what we actually implement)

We avoid the sharp-interface approximation entirely. Discretise the continuous
BC directly on the diffuse interface using one-sided differences along the
analytic wall normal `n_w`:

Let `phi_0` be the phase value at the first fluid node adjacent to the wall,
located at signed distance `h_0 > 0` from the wall along `+n_w`. Let `phi_1` be
the phase at distance `h_1 > h_0` along the same normal. A second-order
one-sided approximation to `partial phi / partial n_w` at the wall is:

```text
g0 = ( phi_1*(h0^2) - phi_0*(h1^2) ) / ( h0*h1*(h0 - h1) )     // weight on phi_0 side
g1 = ( phi_0*h1^2 - phi_1*h0^2 ) / ( h0*h1*(h1 - h0) )          // = d phi / d n at wall
d phi / d n_w |_wall  ~=  g1
```

We compute the trilinearly-interpolated phase values `phi_0`, `phi_1` at the
two probe points `x_0 = x - h_0*n_w_from_fluid` and
`x_1 = x - h_1*n_w_from_fluid`, where `x` is the first fluid node and
`n_w_from_fluid = -n_w` (pointing from the fluid node toward the wall).

The continuous BC `kappa * d phi/d n_w|_wall = gamma_sv * cos(theta_e)` then
becomes a linear relation on the **wall ghost value** `phi_w` (the value of
`phi` exactly on the wall). With `phi_w` defined on the wall and a centered
two-point formula `(phi_0 - phi_w)/h_0`:

```text
kappa * (phi_0 - phi_w) / h_0 = gamma_sv * cos(theta_e)
=>  phi_w = phi_0 - (h_0 / kappa) * gamma_sv * cos(theta_e)
```

The coefficient `(h_0/kappa)*gamma_sv` is the lattice-equivalent wetting
potential per lattice unit. We do not introduce a new parameter; we map it onto
the model's existing interface parameters so that the **sharp-interface limit**
of this expression reproduces the original `2 h tan(...) |grad_t phi|` term,
which fixes the free constant. The resulting form (see Appendix A for the
algebra) is:

```text
phi_ghost = phi_0 + 2 h_0 * tan(pi/2 - theta_e) * |grad_t phi|
            + curvature_correction(h_0, R_solid)
```

where `|grad_t phi|` is the tangential gradient magnitude computed by
**projecting the analytic-gradient stencil onto the analytic tangent plane**
(spanned by `n_w`), and

```text
curvature_correction(h, R) = h^2 / R * tan(pi/2 - theta_e) * |grad_t phi|   (sphere/cylinder only)
```

is the leading `O(h^2/R)` curvature correction that makes the centered
difference consistent on a curved wall. For `R -> infinity` (plane) the
correction vanishes. For `h = 0.5 lu, R = 24 lu` it is about `1%` of the leading
term, which is below the `±2 deg` target but above numerical noise, so we keep
it explicit.

### 1.4 Why this is the right physical content

**CORRECTED 2026-06-14 (see audit_findings_20260614.md).** The original
section claimed the BC is "the exact Cahn-Hilliard natural BC" with "no
clipping". Both claims are overstated. The corrected version:

- The Briant formula is the closed-form wall value for an equilibrium tanh
  interface of width `IntWidth`. It is derived from the surface-energy balance
  under the assumption that the near-wall interface has reached its
  equilibrium shape. This is a stronger assumption than the continuous
  Cahn-Hilliard natural BC.
- All wall geometry enters through the analytic `n_w` and signed distance `h`.
- The wall ghost value IS clipped to `[PhaseField_l, PhaseField_h]`. This is a
  physical bound on the order parameter (the mirror of a bounded phase), but
  it means a "stable" result could be clip-dominated. Diagnostics
  (`WallGhostRaw`, `WallGhostClampHit`) are required to distinguish and are
  NOT yet implemented (reviewer concern 7.2).
- The contact-angle error is **model-intrinsic** (present in upstream), scales
  with cot(theta), and is NOT removed by this BC. See audit point B.

## 2. What was wrong before (root causes this stage addresses)

**CORRECTED 2026-06-14 (see audit_findings_20260614.md).** The original
section overstated what stage9 fixes. The corrected version:

1. **`PhaseF` field overload (PARTIALLY addressed).** Fluid phase, wall ghost
   value, and the `-999` solid sentinel shared one storage field. Stage9 adds
   a separate `WallGhost` field, but the `-999` sentinel is **still used** on
   the legacy lattice path (it is how `Init_wallNorm` detects solid). The
   analytic path mirrors the fluid value into `PhaseF` instead of `-999`, but
   only on analytic-flagged nodes. The field overload is reduced, not removed.
2. **Lattice-recovered wall normal on curved walls (ADDRESSED).** `Init_wallNorm`
   quantised the wall normal to one of 27 lattice directions. On a sphere this
   normal can point into the solid (392 special points in the theta030 case).
   Fix: inject the analytic normal and signed distance when an analytic
   geometry is declared AND the fluid-side probe is a real fluid node. Corner/
   edge nodes still fall back to the lattice normal.
3. **`tan(pi/2 - theta)` sharp-interface formula (FORMULA CHANGED, ERROR
   UNCHANGED).** The analytic branch now uses the Briant surface-energy
   formula instead of the tan formula. **But measurement shows both formulas
   give identical contact angles** (77.60 deg at theta=75 for both, matching
   the unmodified upstream binary). The cot(theta)-scaled contact-angle error
   is model-intrinsic, not a wall-BC formula artifact. The stage5-8 sign-flip
   on the sphere is fixed by the analytic normal, NOT by the formula change.
4. **`permissive.access=TRUE` in Dynamics.R (RETAINED, NOT REMOVED).** The
   original design doc said this would be removed. It cannot be: TCLB's strict
   checker rejects the intentional multi-stage PhaseF write (calcPhase writes
   fluid PhaseF, then calcWall_CA overrides wall-node PhaseF). The flag is
   retained. The Dynamics.R comment documents this accurately; this design
   doc previously did not.

## What stage9 does NOT fix (honest)

- The cot(theta)-scaled contact-angle error (model-intrinsic; present in
  upstream). theta=30 measures 35.65 deg; theta=11 would be worse.
- The `-999` sentinel on the legacy lattice path.
- Corner/edge nodes still using the lattice normal.

To reduce the contact-angle error, the levers are: reduce IntWidth (O(W/R)
scaling), increase droplet radius, or a fundamentally different wall BC that
does not assume an equilibrium tanh interface. None of these are implemented.

## 3. Implementation plan (source files in stage9 snapshot)

### 3.1 New analytic-geometry helpers (`Boundary.c.Rt`, prepended to wetting
section)

```c
// Returns 1 if this node is an analytic-wetting boundary fluid node
// (first fluid node adjacent to an analytic solid surface). Sets out_n and
// out_h. out_n is the outward wall unit normal (pointing into the fluid).
// out_h is the signed distance from this node to the wall along out_n ( > 0 ).
CudaDeviceFunction bool analyticWallGeometry(
    vector_t* out_n, real_t* out_h);

CudaDeviceFunction vector_t analyticSphereNormal();   // (x-c)/|x-c|
CudaDeviceFunction real_t analyticSphereDistance();   // |x-c| - R
CudaDeviceFunction vector_t analyticCylinderNormal(); // (x_perp - c_perp)/|...|
CudaDeviceFunction real_t analyticCylinderDistance();
CudaDeviceFunction vector_t analyticPlaneNormal();    // plane_axis unit
CudaDeviceFunction real_t analyticPlaneDistance();
```

### 3.2 Modified `Init_wallNorm`

For every wall/solid node, after the existing lattice-normal computation,
**and** for every first-fluid-node-adjacent-to-wall node, if an analytic
geometry is declared for that node's zone, store the analytic normal in
`nw_x/nw_y/nw_z` and the analytic signed distance in a new field `WallH`.
Special-boundary-point detection (`NORMAL_POINTING_INTO_SOLID_ON_NEXT_NODE`)
becomes unreachable for analytic nodes because the analytic normal never
points into the solid.

### 3.3 Rewritten `calcWallPhase` normal branch

```c
if (analyticWallGeometry(&n_w, &h)) {
    // sample phase at h0 = h and h1 = 2h along the analytic normal
    real_t phi_0 = phaseAtProbe(-h0 * n_w);   // trilinear
    real_t phi_1 = phaseAtProbe(-h1 * n_w);
    vector_t g   = analyticGradTangent(n_w);  // gradient projected on tangent plane
    real_t gt    = vecMag(g);
    real_t tan_t = tan(PI/2.0 - radAngle);
    real_t kappa_corr = (AnalyticSolidCurvature > 0.0)
                        ? (h0*h0/AnalyticSolidCurvature) : 0.0;
    PhaseF_ghost = phi_0 + 2.0*h0 * tan_t * gt
                        + kappa_corr * tan_t * gt;
    WallGhost = PhaseF_ghost;   // separate field, not PhaseF
} else {
    // legacy lattice path (unchanged), kept for non-analytic geometries
}
```

### 3.4 Solid sentinel removal

`Init()` and `InitFromFieldsStage()` currently set `PhaseF = -999` on wall/solid
nodes. We keep that for the **legacy lattice path only**, because the existing
`Init_wallNorm` uses `PhaseF_dyn < -100` to detect solid. The **analytic path**
uses `IsBoundary` and `IamSolid` instead, so on analytic zones the `-999` write
is skipped and replaced by writing the analytic ghost value into `WallGhost`.
This keeps both paths testable and avoids breaking the legacy path in the same
commit.

### 3.5 Settings / fields / quantities (`Dynamics.R`)

New settings (all default-off, so unmodified cases behave identically):

```text
AnalyticWetting        (0/1)   enable analytic-geometry wetting path
AnalyticSolidType      (0=off,1=plane,2=cylinder,3=sphere)
AnalyticSolidCenterX/Y/Z
AnalyticSolidRadius             (cylinder/sphere)
AnalyticSolidAxis               (0=x,1=y,2=z) for cylinder/plane
AnalyticSolidCurvature          (1/R for sphere, 1/R for cylinder, 0 plane)
                              read-only helper, computed from Radius
```

New fields:

```text
WallGhost    stencil3d=2    ghost phi on wall nodes (analytic path)
WallH        stencil3d=1    analytic signed distance to wall
```

New quantities: `WallGhost`, `WallH`, `AnalyticWallNormal`.

## 4. Validation protocol

All runs must be on the stage9 source, with binary SHA and options snapshot
recorded.

1. **Plane regression** (gate A): theta = 30/90/150 on a flat wall,
   `AnalyticSolidType=1`. Must reproduce the existing flat-wall fitted angles
   to within fitting noise. Verifies the analytic path does not break the
   passing flat-wall result.
2. **Sphere theta=30 short** (gate B): 1000-step run,
   `AnalyticSolidType=3`, R_solid=24, drop centred above. Pass criteria:
   - `NumSpecialPoints` (legacy) == 0 within the analytic zone;
   - two-row near-wall contact angle in [28, 32] deg;
   - `nonfinite_total == 0`, max Mach < 1e-2.
3. **Sphere theta=30 long** (gate C): 200000-step run. Pass criteria:
   - H1-H2 relative error < 5% (was ~105%);
   - fitted angle in [28, 32] deg;
   - fluid phase drift < 1%, max Mach < 1e-3, nonfinite == 0.
4. **Cylinder theta=30** (gate D): analogous to gate C on a horizontal
   cylinder.
5. **Dynamic plane impact theta=90** (gate E, post-validation): reuse the same
   BC for a droplet impact on a flat wall; verify maximum spreading ratio is
   within literature spread for the same We/Re.

None of gates B-E authorise publication-ready claims until a separate
read-only audit accepts them.

## Appendix A. Diffuse-BC -> sharp-interface-formula algebra

Start from the wall-centered BC with `phi_w` defined on the wall and a centered
two-point formula using `phi_0` at `h_0`:

```text
d phi/d n|_wall ~ (phi_0 - phi_w) / h_0
```

Continuous BC: `kappa (phi_0 - phi_w)/h_0 = gamma_sv cos(theta_e)`.

We want a **ghost value** `phi_ghost` located at `s = -h_0` (mirrored into the
solid), so that a fluid-side centered difference `(phi_0 - phi_ghost)/(2 h_0)`
reproduces the same wall derivative:

```text
(phi_0 - phi_ghost)/(2 h_0) = (phi_0 - phi_w)/h_0
=> phi_ghost = phi_0 - 2 (phi_0 - phi_w) = 2 phi_w - phi_0
```

Substituting `phi_w = phi_0 - (h_0/kappa) gamma_sv cos(theta_e)`:

```text
phi_ghost = phi_0 - 2 (h_0/kappa) gamma_sv cos(theta_e)
```

The model's equilibrium interface has `|grad phi| ~ 2/W` and bulk chemical
potential `mu_bulk = 4 (12 sigma/W)(phi - phi_l)(phi - phi_h)(phi - phi_avg)`
with `kappa = 1.5 sigma W`. Substituting `(gamma_sv/kappa) = (2/W) cos(theta_e)`
into the sharp-interface relation `|grad_t phi| = (2/W) sin(theta_e)` and using
`cos(theta_e) = (2/W) cot(theta_e) * (W/2)`, the prefactor collapses to

```text
2 (h_0/kappa) gamma_sv cos(theta_e) = 2 h_0 tan(pi/2 - theta_e) |grad_t phi|
```

recovering the legacy formula in the `W/R -> 0` limit. The curvature
correction in section 1.3 is the leading finite-curvature term obtained by
expanding the centered difference about the curved-wall tangent plane.
