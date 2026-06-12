# Stage8d Sphere Shadow Limiter Attribution Artifacts

Status: `runtime_sanity / exploratory_not_validation`.

This folder contains curated public evidence for the Stage8d z48 sphere
shadow-only limiter attribution run. It intentionally excludes raw `.vti`,
`.pvti`, `.pri`, binaries, compressed archives, and credentials.

## Case

```text
case_id = theta030_shadow
remote = /mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_stage8d_shadow_limiter_attribution_20260612/theta030_shadow
domain = 80 x 80 x 180
solid_center = (40, 40, 48)
R_solid = 24
drop_center = (40, 40, 96)
R_drop = 24
bottom_gap = 24 lu
outer radAngle = 90 deg
sphere radAngle = 11 deg
M = 0.1
IntWidth = 6
Stage8OperatorMode = 1
```

`Stage8OperatorMode=1` is shadow-only. It computes diagnostics and candidate
fields but does not write `gradPhiVal`.

## Return Codes

```text
solver rc = 0
finiteness gate rc = 0
limiter attribution rc = 0
checked VTK steps = 0,100,...,1000
```

## Main Result

At step 1000:

```text
active_count = 924
limiter_count = 404
limiter_fraction = 43.72 %
sphere11_limiter_count = 404
outer90_limiter_count = 0
raw_delta_p99 = 0.6471
limited_delta_p99 = 0.25
limiter_ratio_p10 = 0.4621
max Mach = 3.084e-4
nonfinite_total = 0
```

The limiter is concentrated in the sphere 11 degree region and in high
tangent-gradient bins. This supports the attribution:

```text
sphere11_low_angle_candidate_dominated_raw_delta_exceeds_cap
```

## Decision Boundary

This artifact does not authorize `Stage8OperatorMode=2` or any sphere 50k
write run. Stage8d is an attribution packet only.

