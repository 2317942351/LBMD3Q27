# Stage8 Boundary-Fluid Gradient Wetting Artifacts

Status: `runtime_sanity / exploratory_not_validation`.

This directory contains curated public evidence only:

- remote cleanup logs for the full-disk incident,
- Stage8 flat-wall XML inputs,
- run return codes,
- finiteness summaries,
- flat-wall gate metrics,
- batch logs,
- binary SHA/path text.

Raw `.vti/.pvti/.pri` fields, binaries, compressed archives, and credentials are
not included.

The first Stage8 attempt under
`tclb_flat_wall_cap_stage8_wall011_modes_20260612` failed because the remote
disk was full and VTI output was truncated. That raw output was deleted on
HM570 and is not part of this artifact.

The valid light-output runs are:

- `tclb_flat_wall_cap_stage8_wall011_modes_light_20260612`: 2000-step four-mode
  smoke. Modes 0, 1, and 2 pass runtime sanity; mode 3 is
  `failed_negative_evidence`.
- `tclb_flat_wall_cap_stage8_wall011_mode2_10k_light_20260612`: 10000-step
  mode2 extension. This passes runtime sanity and remains exploratory only.
