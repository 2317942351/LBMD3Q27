# PRE 2025 Sphere Known-Bad Geometry Diagnostic

Date: 2026-06-11

Status: failed_negative_evidence

## Scope

This note freezes the old reduced PRE 2025 spherical wetting setup as a
negative diagnostic, not as a static wetting calibration case.

## Known-Bad Setup

```text
domain = 80 x 80 x 140
R_drop = 24 lu
R_solid = 24 lu
solid_center_z = 24 lu
bottom_gap = solid_center_z - R_solid = 0 lu
IntWidth = 6 lu
bottom_gap / IntWidth = 0
global radAngle = 11d
OuterDomain radAngle = 11d
SolidSphere radAngle = 11d
```

## Decision

The `z24/global radAngle=11d` setup is classified as
`failed_negative_evidence / known-bad bottom-contact global-low-angle wetting`.
It must not be used as a PRE Table II static wetting validation case or as a
contact-angle calibration target.

## Reason

The solid sphere touches the z-min outer wall, and the outer wall shares the
same strong low-angle wetting parameter as the solid sphere. This creates a
nonphysical lower-wall wetting channel. Long-time liquid leakage toward the
bottom boundary is therefore a geometry/boundary failure mode, not evidence
that `radAngle`, mobility, or interface width fitting alone can recover the
case.

## Replacement Smoke Geometry

The next diagnostic geometry separates the solid sphere from the lower domain
wall and neutralizes the outer wall:

```text
domain = 80 x 80 x 180
R_drop = 24 lu
R_solid = 24 lu
solid_center_z = 48 lu
drop_center_z = 96 lu
bottom_gap = 24 lu
bottom_gap / IntWidth = 4 for IntWidth=6
global/default radAngle = 90d
OuterDomain radAngle = 90d
SolidSphere radAngle = 11d for theta030/sphere-low-angle smoke
```

This replacement remains `exploratory_not_validation` until parser/runtime
smoke, morphology checks, mass/Mach/nonfinite reporting, and read-only audit
are complete.
