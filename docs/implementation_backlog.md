# Implementation Backlog

Date: 2026-06-06

## Immediate

1. Verify z-wall geometry convention with a tiny TCLB run:

```text
Geometry nx=64 ny=64 nz=64
wall z=0
droplet CenterZ known
check VTI centroid and wall BOUNDARY output
```

2. Adapt `scripts/tclb_impact_drywall_postprocess.py` for arbitrary wall
normal, especially z-wall morphology labels.

3. Implement droplet-only initial velocity.

Options:

```text
use TCLB external/init field if supported
patch TCLB Init() locally for a case-specific velocity mask
start droplet near wall with global velocity only as exploratory fallback
```

4. Create static contact-angle cases:

```text
theta=45
theta=90
theta=135
```

5. Re-run the small `rho_ratio=772` dry-wall pilot with z-wall and report:

```text
beta(t)
mass drift
max Mach
morphology
```

## Validation

1. Formalize TCLB ContactAngle reproduction.
2. Formalize TCLB bubbleRise reproduction:
   - use `references\a1_bubbleRise_reference_gap_20260607.md` as the current
     evidence boundary;
   - current pre-audit digitized data are in
     `references\data\a1_bubbleRise_safi2017_reference.csv`;
   - current pre-audit comparison artifact is
     `artifacts\tclb_bubbleRise_A1_safi_compare_20260607`;
   - next step is read-only audit of the digitization and observable mappings,
     plus stronger reference provenance or independent digitization if needed,
     before any `validation_candidate` request.
3. Implement Wang 2023 Poiseuille or select a closer TCLB/Fakhari layered
   Poiseuille case if available.
4. Implement Fei 2019 dry-wall spreading comparison.
5. Implement Wang 2023 thin-film splash crown-diameter comparison.

## Production

Only after validation:

```text
R0 >= 32 engineering grid
grid sensitivity to R0 >= 48 if P100 memory allows
contact-angle sweep to resting state
liquid-film version
paper figures and tables
```
