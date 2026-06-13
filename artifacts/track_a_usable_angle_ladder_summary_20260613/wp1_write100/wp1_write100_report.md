# WP1 Plane 100-Step Write Smoke

Status: `runtime_sanity / exploratory_not_validation`.

This is not validation and not a production fix. This smoke test only checks
whether the flat-wall write path immediately creates nonfinite values, large
mass drift, elevated Mach, or internal voids after the WP1 shadow geometry gate.

Cases:

```text
wp1_plane_theta030_write100
wp1_plane_theta090_write100
```

Run settings:

```text
Stage8OperatorMode = 2
iterations = 100
```

Remote raw:

```text
/media/yuan/新加卷1/RUNS/runs/wp1_plane_short_write_100_20260614
raw field files: 8
```

Result:

| case | theta error deg | h error | a error | phase mass drift | max Mach | nonfinite | internal void |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| plane030 | -0.5501 | 0.0364 | 0.0176 | -0.00129 | 1.18e-05 | 0 | 0 |
| plane090 | -0.9531 | 0.0168 | 0.000282 | 2.32e-06 | 6.60e-06 | 0 | 0 |

Both cases pass the 100-step WP1 write smoke. No 1000-step, 5000-step, 50k, or
curved-surface write run is authorized by this artifact.
