# Stage8c Sphere Local-Transfer Shadow Artifacts

Status: `runtime_sanity / exploratory_not_validation`.

This folder contains curated public evidence for the Stage8c z48 sphere
local wall-angle/normal transfer and shadow-candidate gate. It intentionally
does not contain raw `.vti`, `.pvti`, `.pri`, binaries, compressed archives, or
credentials.

## Case

```text
case_id = theta030_shadow
remote = /mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_stage8c_local_transfer_shadow_20260612/theta030_shadow
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

`Stage8OperatorMode=1` is shadow-only. It computes the Stage8c corrected
gradient candidate and diagnostics but does not write `gradPhiVal`.

## Return Codes

```text
solver rc = 0
finiteness gate rc = 0
local-transfer audit rc = 0
raw VTI steps checked = 0, 100
```

The refreshed local-transfer audit separates original-field nonfinite counts
from derived dot-radial arrays where NaN means "not applicable". Original
diagnostic fields have `nonfinite_total=0` at steps 0 and 100.

## Main Observations

- XML zonal angles are parsed as expected: default/outer `90d`, sphere `11d`.
- Sphere wall local angle p50 is `0.1919862177 rad` at steps 0 and 100.
- Outer wall local angle p50 is `1.5707963268 rad` at steps 0 and 100.
- Fluid nodes near the sphere receive the sphere angle: p50 `0.1919862177 rad`.
- Fluid nodes near the outer wall receive the outer angle: p50 `1.5707963268 rad`.
- Near-sphere fluid data count is `11408`, with p50 neighbor count `6`.
- Near-sphere normal agreement p05 is `0.98245`.
- Geometry normals are used for all `11408` near-sphere data nodes.
- Fluid near-sphere normal dot sphere-radial p50 is about `0.99088`.
- Max Mach at step 100 is `1.8277e-4`.

These results pass the narrow local-transfer gate: the Stage8c wall-angle and
wall-normal data path distinguishes sphere and outer walls correctly for this
diagnostic geometry.

## Blocking Evidence

The shadow candidate is already limiter-dominated in the active contact region:

```text
step 0:   active_count = 780, delta_limiter_count = 388, grad_delta_active_p99 ~= 0.25
step 100: active_count = 832, delta_limiter_count = 320, grad_delta_active_p99 ~= 0.25
```

Because `Stage8MaxGradDelta=0.25` is hit in shadow mode, this package does not
authorize `Stage8OperatorMode=2` sphere write or 50k sphere runs. The next
technical step is a read-only audit of candidate magnitude, active-band
selection, and whether the corrected `gradPhiVal` is the operator that actually
controls the curved contact angle.

## Public Artifact Boundary

Included:

- XML and JSON case metadata,
- run logs and return codes,
- finiteness summary CSV/JSON,
- local-transfer summary CSV/JSON,
- scripts needed to regenerate the case and repeat the audit.

Excluded:

- raw VTI/PVTI/PRI fields,
- TCLB binaries,
- compressed raw output,
- credentials.

