# Current Stage Index

Status: `runtime_sanity / exploratory_not_validation`.

Current diagnostic lane:

1. Stage8c: local wall-angle and wall-normal transfer for fluid-boundary gradient candidates.
2. Stage8d: sphere shadow limiter attribution; limiter hits concentrated in the sphere 11 degree region.
3. Stage8e: normal-residual-only wetting candidate; vector limiter removed, but normal limiter remains high.
4. Stage8f: normal-limiter root-cause attribution; diagnostic-only, not a fix.
5. Stage8g: cap-contract / low-angle regularization shadow diagnostic; completed short shadow gates only.

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
implementation is Stage8g, a cap-contract revision and low-angle regularized
contact-relation diagnostic. It starts in shadow mode and must not change the
Stage8f conclusion.

Current write boundary:

```text
Stage8OperatorMode=2 sphere write remains forbidden.
No sphere 50k, 200k, 400k, or 600k Stage8f/Stage8g run is authorized by this index.
No Stage8g write run is authorized until a separate post-Stage8g shadow gate
is defined and passed.
```

Stage8g planned gate:

```text
flat low-angle shadow: wall005/008/011/015/020/025/030, Stage8gMode=0/1/2/3
sphere z48 shadow: free-sphere and approximate cap-on-sphere initializers,
                   Stage8gMode=0/1/2/3
all Stage8g cases: Stage8OperatorMode=1, outputs at 0/100/1000 only
```

Current Stage8g result:

```text
build/source rc = 0/0
flat cases = 28/28 completed, nonfinite_total=0, vector_limiter_fraction=0
sphere cases = 8/8 completed, nonfinite_total=0, vector_limiter_fraction=0
best sphere cap-on-sphere mode3 normal_limiter_fraction = 45.64%
best sphere free-sphere mode3 normal_limiter_fraction = 77.06%
outer90/fallback limiter hits = 0 in all sphere cases
decision = Stage8g shadow improves diagnosis but does not pass sphere write gate
```

Therefore:

```text
Stage8OperatorMode=2 sphere write remains forbidden.
No Stage8g sphere 50k/200k/400k/600k run is authorized.
Next route must be a new Stage8h audit/diagnostic plan.
```
