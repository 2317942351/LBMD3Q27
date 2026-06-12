# Current Stage Index

Status: `runtime_sanity / exploratory_not_validation`.

Current diagnostic lane:

1. Stage8c: local wall-angle and wall-normal transfer for fluid-boundary gradient candidates.
2. Stage8d: sphere shadow limiter attribution; limiter hits concentrated in the sphere 11 degree region.
3. Stage8e: normal-residual-only wetting candidate; vector limiter removed, but normal limiter remains high.
4. Stage8f: normal-limiter root-cause attribution; diagnostic-only, not a fix.

Do not treat any Stage8 lane as PRE reproduction, validation, production fix, or publication-ready evidence.

Current Stage8f result:

```text
vector limiter fraction = 0 in final flat and sphere shadow frames
flat wall low-angle normal limiter falls from 88.78% at wall005 to 0% at wall025/wall030
z48 sphere free-sphere normal limiter fraction = 85.28%
z48 sphere cap-on-sphere normal limiter fraction = 73.04%
outer90 normal limiter count = 0 in both sphere shadows
classification = low-angle tan amplification plus current normal-cap contract;
                 initial geometry stress contributes but is not sufficient
```

Current evidence does not support entering sphere write mode. The next
implementation must be a new Stage8g plan, likely a cap-contract revision or
low-angle regularized contact relation, and it must start in shadow mode.

Current write boundary:

```text
Stage8OperatorMode=2 sphere write remains forbidden while Stage8f is active.
No sphere 50k, 200k, 400k, or 600k Stage8f run is authorized by this index.
No Stage8g write run is authorized until a separate Stage8g shadow gate is
defined and passed.
```
