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

Xu 2024 phase-field LBM book:

```text
Title: 相场格子玻尔兹曼方法理论与应用
English title: Theory and Application of Phase-Field-Based Lattice Boltzmann Method
Author: 徐兴春
Publisher/date: 国防工业出版社, 2024-06
Local-only markdown: C:/Users/yuanz/Downloads/相场格子玻尔兹曼方法理论与应用.md
Local SHA256: 845A2F5F3A392AD78DC4F665494FB5A66488B284C5F4D38B94FA48FF6C69F186
Repo metadata: references/phasefield_lbm_book_2024/
Project audit: docs/stage14/178_phasefield_lbm_book_ch3_ch7_code_audit_20260703.md
Use: phase-field boundedness, conservative Allen-Cahn source closure, MRT phase-field options, force/pressure closure.
Limit: not a contact-angle/wetting-boundary validation source; do not commit full book text.
```

Huang and Liu 2023 LBM phase/wetting excerpt:

```text
Title: 格子Boltzmann方法 从入门到精通
Authors: 黄海波, 刘魁
Publisher/date: 中国科学技术大学出版社, 2023
Local-only markdown: C:/Users/yuanz/Downloads/格子BOLTZMANN方法从入门到精通_相场多相流润湿篇.md
Local SHA256: 504571167012619CD6BD85BE125A01F9AEA41E55407E23A2C85782CA0EA05052
Repo metadata: references/huang_liu_2023_lbm_phase_wetting/
Project anchor: docs/stage14/183_huang_liu_lbm_phase_wetting_context_anchor_20260703.md
Use: curved boundary streaming semantics, phase-field h-population source timing, contact-angle validation workflow boundaries.
Limit: do not copy full excerpt; do not mix Shan-Chen/free-energy contact-angle formulas directly into the current conservative Allen-Cahn TCLB model.
```

He, Li, Wang, and Tong 2023 LBM theory/application excerpt:

```text
Title: 格子Boltzmann方法的理论及应用
Authors: 何雅玲, 李庆, 王勇, 童自翔
Publisher/date: 高等教育出版社, 2023
Local-only markdown: C:/Users/yuanz/Downloads/15215943_相场多相流润湿篇.md
Local SHA256: EF76B77D366466B1E25299121CEAF7808E4C4FADEC1CBF816BED009A1E9EAB5F
Repo metadata: references/he_li_wang_tong_2023_lbm_theory_phase_wetting/
Project anchor: docs/stage14/184_he_li_wang_tong_lbm_theory_phase_wetting_anchor_20260703.md
Use: model-family separation for contact-angle formulas, phase-field wetting options, complex-boundary mass-loss audits.
Limit: do not copy full excerpt; do not transplant pseudo-potential virtual-density or color-gradient formulas directly into the current phase-field solver.
```

Contact-angle LBM implementation manual:

```text
Title: 接触角/润湿边界 LBM 实现方法参考手册
Local-only markdown: C:/Users/yuanz/Downloads/接触角LBM实现方法参考手册.md
Local SHA256: 2DE13B390E4BCA2351C6804D7BD87612122D83C115127B2BE7E5763D5E2BB1A5
Repo metadata: references/contact_angle_lbm_manual_20260704/
Project anchor: docs/stage18/026_contact_angle_lbm_manual_code_audit_20260704.md
Use: model-family separation for wetting formulas, phase-field surface-free-energy/geometric contact-angle boundary choices, near-wall gradient/Laplace audit, and validation workflow constraints.
Limit: do not copy the full manual text; do not mix Shan-Chen wall-density or color-gradient virtual-density formulas into the current conservative Allen-Cahn phase-field solver.
```

Taichi official documentation:

```text
Docs site: https://docs.taichi-lang.org/
Docs source: https://github.com/taichi-dev/docs.taichi.graphics
Taichi source: https://github.com/taichi-dev/taichi
Local snapshot anchor: references/taichi_official_docs_20260704/
Project audit: docs/stage18/008_taichi_route_assessment_and_official_docs_anchor_20260704.md
Use: GPU LBM implementation semantics, Taichi kernel/function scope, explicit double buffering, field layout, CUDA sync/debug/profiling.
Limit: Taichi can simplify implementation semantics but does not by itself fix conservative phase-field, force closure, or wetting boundary physics. The existing Re=100 Taichi cylinder script is GPU feasibility evidence only, not the phase-field model architecture.
```

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
