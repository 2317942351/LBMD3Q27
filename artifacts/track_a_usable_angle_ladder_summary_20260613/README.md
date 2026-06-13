# Track A Usable-Angle Summary Artifacts

Status: `runtime_sanity / exploratory_not_validation`.

This directory stores lightweight Track A planning summaries only. It is not a
PRE reproduction, not validation, not a production fix, and not publication
evidence.

Expected generated files:

```text
track_a_summary.csv
track_a_summary.json
```

The postprocessor reads only lightweight CSV/JSON metrics. It must not require
or store raw `.vti`, `.pvti`, `.pri`, or `.vtk` files in this repository.

If no simulations have been run, all runtime metrics remain `unknown` and every
case is classified as `pending`.
