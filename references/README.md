# References

This folder stores only references needed for TCLB validation and target-case
planning. Do not copy unrelated D3Q27 route logs here.

## Local Reference Files

Expected copied files:

```text
papers/wang2023_ijmf_ucl.pdf
papers/fei2019_pof_nmrt.pdf
papers/wang2024_jfm_main.pdf
extracted/wang2023_ijmf_d3q27_vlm.md
extracted/fei2019_pof_nmrt_vlm.md
extracted/wang2024_jfm_main_vlm.md
```

## Primary Literature Links

Wang 2023 IJMF:

```text
DOI: https://doi.org/10.1016/j.ijmultiphaseflow.2023.104582
UCL: https://discovery.ucl.ac.uk/id/eprint/10174536/
ScienceDirect: https://www.sciencedirect.com/science/article/pii/S0301932223002021
```

Fei 2019 Physics of Fluids:

```text
DOI: https://doi.org/10.1063/1.5087266
UCL: https://discovery.ucl.ac.uk/10073968/
```

Luo, Fei, and Wang 2021 ULBM:

```text
DOI: https://doi.org/10.1098/rsta.2020.0397
```

Wang 2024 JFM:

```text
DOI: https://doi.org/10.1017/jfm.2024.441
```

A1 TCLB bubbleRise benchmark reference:

```text
Safi, M. A.; Prasianakis, N.; Turek, S. (2017).
Benchmark computations for 3D two-phase flows: A coupled lattice Boltzmann-level set study.
Computers & Mathematics with Applications 73(7), 2455-2470.
DOI: https://doi.org/10.1016/j.camwa.2016.12.014
PSI/DORA record: https://www.dora.lib4ri.ch/psi/islandora/object/psi%3A4287
local PDF/preprint: papers/safi2017_camwa_3d_bubble_preprint.pdf
local gap note: references/a1_bubbleRise_reference_gap_20260607.md
local provenance note: references/data/a1_bubbleRise_reference_provenance_20260607.md
local digitization notes: references/data/a1_bubbleRise_safi2017_digitization_notes.md
local digitized TC1 data: references/data/a1_bubbleRise_safi2017_reference.csv
local independent digitization check: artifacts/tclb_bubbleRise_A1_safi_compare_20260607/a1_safi_independent_digitization_600dpi_summary.json
related 3D benchmark paper: papers/adelsberger2014_3d_rising_bubble_benchmark.pdf
Bonn/INS TC1 ASCII data: references/data/bonn_3d_rising_bubble_tc1/bonn_3d_rising_bubble_tc1_reference.csv
Bonn/INS TC1 summary: references/data/bonn_3d_rising_bubble_tc1/bonn_3d_rising_bubble_tc1_reference_summary.json
Bonn/INS direct comparison artifact: artifacts/tclb_bubbleRise_A1_bonn_compare_20260607/a1_bonn_comparison_summary.json
current status: TC1 Fig. 4/5 FeatFlow curves are digitized from rendered bitmap page-09 and independently checked at 600 dpi; Bonn archive ASCII data for Adelsberger 2014 TC1 DROPS/NaSt3D/OpenFOAM have also been retrieved, curated, and compared directly with existing TCLB A1 output, but must not be relabeled as Safi 2017 FeatFlow without audit. A1 remains runtime_sanity, not validation-grade without audit, explicit thresholds, observable checks, and grid/time-step sensitivity
```

General dry-wall contact-angle/spreading references to retrieve if needed:

```text
Mao et al. dry-wall spreading data, We about 50-1080.
NIST/Kurabayashi-Yang wetting correction at low We.
Controlled-contact-angle inkjet spreading data.
```
