# Stage8c Local Wall-Angle Boundary-Gradient Artifacts

Status: `runtime_sanity / exploratory_not_validation`.

This folder contains curated Stage8c provenance, case metadata, return codes,
finiteness summaries, and CSV/JSON postprocess results. It intentionally does
not contain raw `.vti`, `.pvti`, `.pri`, binaries, or archives.

Primary run:

```text
remote = /mnt/8A0E24070E23EAC1/runs/tclb_flat_wall_cap_stage8c_low_angle_50k_light_20260612
local  = artifacts/stage8c_local_angle_boundary_gradient_20260612/tclb_flat_wall_cap_stage8c_low_angle_50k_light_20260612
```

Important outcome:

- wall005/008/011/015/020/025/030 all completed 50k with solver/finiteness/post rc 0.
- nonfinite total is 0 for all final frames.
- wall005 triggers the explicit `Stage8MaxGradDelta=0.25` limiter on 3808 active cells.
- wall008-wall030 do not trigger the delta limiter.

This is not validation and does not authorize sphere write mode yet.
