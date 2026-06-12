# Current Stage Index

Status: `runtime_sanity / exploratory_not_validation`.

Current diagnostic lane:

1. Stage8c: local wall-angle and wall-normal transfer for fluid-boundary gradient candidates.
2. Stage8d: sphere shadow limiter attribution; limiter hits concentrated in the sphere 11 degree region.
3. Stage8e: proposed normal-residual-only wetting candidate; candidate diagnostic, not validation.

Do not treat any Stage8 lane as PRE reproduction, validation, production fix, or publication-ready evidence.

Current write boundary:

```text
Stage8OperatorMode=2 sphere write remains forbidden until Stage8e shadow gates pass.
No sphere 50k, 200k, 400k, or 600k Stage8e run is authorized by this index.
```
