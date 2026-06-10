# PRE 2025 Author Raw-Data Workbook

Status: `exploratory_not_validation`

Source workbook:

```text
C:\Users\yuanz\Downloads\raw data.xlsx
```

Extracted on 2026-06-10 with:

```text
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\extract_pre2025_raw_data_xlsx.py
```

## Data Boundary

This workbook is the author-provided curve data for selected figures in the
Phys. Rev. E 112, 065303 wetting-boundary paper. It is not the raw Table II
spherical-static error table.

The extracted workbook contains usable series for:

```text
Fig.11(a): 6 h(t) series
Fig.11(b): 6 s(t) series
Fig.12(a): 6 s(t) series
Fig.12(b): 6 s(t) series
Fig.16(a): 3 d(t) series
Fig.17(a): 3 d(t) series
Fig.18(a): 3 d(t) series
Fig.19(a): 4 d(t) series
Fig.21(a): 3 d(t) series
```

`Fig.13(a)` appears in the workbook only as a label in the current extraction;
no adjacent `t`/observable columns were found.

## Outputs

```text
raw_data_summary.json
raw_data_long.csv
extract_stdout.json
Fig_*_raw_block.csv
```

`raw_data_long.csv` schema:

```text
figure
series_index
metadata
observable
t
value
source_row
source_t_col
source_value_col
```

The raw block CSV files preserve the spreadsheet cells for each detected
figure block. `raw_data_summary.json` records series counts, value ranges, and
source-cell provenance.

## Use In TCLB Work

For the current Table II reduced spherical-static setup, continue using:

```text
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\references\pre2025_wetting_boundary\table_II_sphere_errors.csv
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\references\pre2025_wetting_boundary\table_II_sphere_targets.csv
```

The Excel data should be treated as supplementary literature data for later
capillary-rise, conical-surface, or dynamic wetting cases. It does not remove
the current Table II model-boundary caveat: TCLB is still an analogue unless
the PRE D3Q19/D3Q19 MRT model and wetting boundary reconstruction are
implemented directly.
