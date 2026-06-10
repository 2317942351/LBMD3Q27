# TCLB Remote And Local File Index

Date: 2026-06-07

Purpose: compact map of where source, references, case templates, remote runs,
and local artifacts live. Update after any successful run or artifact copy.

For new conversations, read `docs\tclb_path_index.md` first. This file is a
more detailed backing index and may contain secondary notes.

## Local Project Root

```text
C:\Users\yuanz\Desktop\LBMCORE5\TCLB
```

Key local files:

```text
README.md
AGENTS.md
docs\tclb_project_handoff.md
docs\literature_case_matrix.md
docs\target_physical_case_plan.md
docs\validation_and_output_protocol.md
docs\implementation_backlog.md
docs\subagent_goal_operating_model.md
docs\remote_local_file_index.md
docs\a1_bubbleRise_acceptance_protocol.md
scripts\tclb_impact_drywall_postprocess.py
scripts\tclb_bubble_rise_postprocess.py
scripts\a1_bubbleRise_compare_safi2017.py
scripts\a1_bubbleRise_acceptance_gate.py
scripts\make_a1_bubbleRise_sensitivity_cases.py
scripts\a1_bubbleRise_grid_time_summary.py
scripts\make_tclb_static_contact_angle_cases.py
scripts\tclb_static_contact_angle_postprocess.py
```

## Remote Execution Host

```text
ssh alias: HM570
TCLB source: /home/yuan/src/TCLB
TCLB commit: ded67cd768cf7e727bd078af139e3ec7895076e5
model: /home/yuan/src/TCLB/models/multiphase/d3q27_pf_velocity
binary: /home/yuan/src/TCLB/CLB/d3q27_pf_velocity/main
geometric binary: /home/yuan/src/TCLB/CLB/d3q27_pf_velocity_geometric/main
  built 2026-06-07 as an independent target; options.R has geometric=TRUE,
  while the original d3q27_pf_velocity binary remains geometric=FALSE
geometric staircase binary:
  /home/yuan/src/TCLB/CLB/d3q27_pf_velocity_geometric_staircaseimp/main
  built 2026-06-07 as an independent target; options.R has geometric=TRUE
  and staircaseimp=TRUE, while original and geometric-only binaries remain
  separate
CUDA: /usr/local/cuda-12.6
GPU: Tesla P100-PCIE-16GB
local source patch: optional droplet-only initialization parameters in
  Dynamics.R and Dynamics.c.Rt, backed up as *.pre_droplet_velocity_20260607;
  DropletOnlyVelocity=1 uses a hard phase mask and =2 uses smooth phase-fraction
  velocity weighting
compatibility run root: /home/yuan/runs -> /media/yuan/DATA500/runs
physical run root: /media/yuan/DATA500/runs
mount: /media/yuan/DATA500
filesystem: ntfs3 on /dev/sdc1
capacity check 2026-06-07: 466G total, 49G used, 418G available, 11% used
health check 2026-06-07: small write/read/delete under
  /media/yuan/DATA500/runs passed as user yuan
path state 2026-06-07: /home/yuan/runs symlink recreated and representative
  geometric theta090 run.log was readable through the compatibility path
old failed candidate: /mnt/data500/yuan/runs was abandoned after receiver-side
  Input/output error and HM570 freeze
local case generators: default to /media/yuan/DATA500/runs for future cases
current physical run root 2026-06-08: /media/yuan/8A0E24070E23EAC1/runs
current mount 2026-06-08: /media/yuan/8A0E24070E23EAC1
current capacity check 2026-06-08: 894G total, 560G used, 334G available, 63% used
current health check 2026-06-08: small write/read/delete under the current run
  root passed as user yuan
DATA500 status 2026-06-08: do not use for new runs until separate disk health
  audit; keep as historical/curated evidence path only
```

Run command pattern:

```bash
cd /home/yuan/src/TCLB
export PATH=/usr/local/cuda-12.6/bin:$PATH
export OMPI_MCA_plm_rsh_agent=/usr/bin/ssh
CLB/d3q27_pf_velocity/main /home/yuan/runs/<run_dir>/<case>.xml
```

For future generated cases, use
`/media/yuan/8A0E24070E23EAC1/runs/<run_dir>/<case>.xml` unless a later disk
audit changes the active root. Historical completed runs in this index may
remain listed under `/home/yuan/runs` or DATA500 for provenance.

## Remote Run Roots

Use this naming rule:

```text
/home/yuan/runs/tclb_<case>_<YYYYMMDD_HHMMSS>
/home/yuan/runs/tclb_<case>_latest -> symlink to latest successful run
```

Future naming rule:

```text
/media/yuan/8A0E24070E23EAC1/runs/tclb_<case>_<YYYYMMDD_HHMMSS>
/media/yuan/8A0E24070E23EAC1/runs/tclb_<case>_latest -> symlink to latest successful run
/home/yuan/runs -> /media/yuan/DATA500/runs historical compatibility symlink
```

Known remote runs:

| Status | Remote path | Purpose | Local copy |
|---|---|---|---|
| exploratory_not_validation | `/media/yuan/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_tableII_q27_geometric_200k_20260610` | PRE 2025 Table II reduced spherical-surface static wetting TCLB analogue using `/home/yuan/src/TCLB/CLB/d3q27_pf_velocity_q27_geometric/main`, domain `80x80x140`, `R_drop=24`, `R_solid=24`, theta `30..130`, `M=0.2`, `tauUpdate=3`, `IntWidth=6`, density ratio `1000`, dynamic viscosity ratio `900`, 200000 steps. All 11 angles completed with `run.returncode=0`, `postprocess_returncode=0`, no run-log NaN hits, and max nonfinite count `0`; max Mach `6.218e-4`. It is stable but not Table-II-accurate: mean TCLB H1-H2 error `12.4967%`, max `32.5064%` at theta030, versus PRE scheme mean `1.9455%`; fitted apparent angles are systematically higher than target, with max offset `30.2527 deg` at theta130. `NumSpecialPoints=392` for every case. This is not PRE reproduction or validation. | `TCLB\artifacts\pre2025_sphere_tableII_q27_geometric_200k_20260610`; curated XML/config/log/TCLB CSV/postprocess CSV+JSON/summary/comparison PNG/README only; local raw `.vti/.pvti` count `0`. |
| exploratory_not_validation / failed_negative_evidence | `/media/yuan/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_tableII_q27_geometric_anglemap_screen_20260610` | Inverse-input-angle diagnostic for the same PRE 2025 Table II reduced sphere geometry. Target theta remained `30..130`, but TCLB `radAngle` was remapped from the 200k fitted-angle response: `30:10.6`, `40:23.4`, `50:36.4`, `60:49.1`, `70:60.0`, `80:70.2`, `90:79.9`, `100:88.8`, `110:96.6`, `120:105.1`, `130:112.5`. Binary `/home/yuan/src/TCLB/CLB/d3q27_pf_velocity_q27_geometric/main`; 20000-step screen with VTK interval 10000. The theta030/radAngle10.6 case is `failed_negative_evidence`: solver rc `0` and no run-log NaN, but postprocess found `max_nonfinite_count=2935400`, fluid phase/rho drift `-100%`, and no finite fit angle. Therefore this anglemap must not be extended to 200000 steps. Other finite 20k cases are screening data only, not equilibrium calibration. | `TCLB\artifacts\pre2025_sphere_tableII_q27_geometric_anglemap_screen_20260610`; curated XML/config/log/TCLB CSV/postprocess CSV+JSON/summary/comparison PNG only; local raw `.vti/.pvti` count `0`. |
| exploratory_not_validation | `/media/yuan/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_tableII_q27_geometric_theta030_radangle_threshold_20260610` and `/media/yuan/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_tableII_q27_geometric_theta030_radangle_lower_bracket_20260610` | Theta030 low-input-angle finite-field threshold screens for the PRE 2025 reduced sphere setup. Tested `radAngle=14,16,18,20,22,24,26,28,30` and then `11,12,13,13.5` for 20000 steps. All 13 added cases completed with solver rc `0`, postprocess rc `0`, no run-log NaN, and `max_nonfinite_count=0`. Combined with the failed radAngle10.6 anglemap case, the current finite bracket is `10.6 failed; 11.0 passed` at 20000 steps. Max Mach among passed cases was `6.68e-4`; fluid phase drift ranged from `-0.5638%` to `-0.2617%`. These are finite-field screens only: direct radAngle030 changed from H1-H2 error `130.5%` at 20k to `32.5%` at 200k, so 20k contact angle/H1-H2 values must not be used as equilibrium calibration. | `TCLB\artifacts\pre2025_sphere_tableII_q27_geometric_theta030_radangle_threshold_20260610`, `TCLB\artifacts\pre2025_sphere_tableII_q27_geometric_theta030_radangle_lower_bracket_20260610`, and combined table `TCLB\artifacts\pre2025_sphere_tableII_q27_geometric_theta030_radangle_threshold_combined_20260610\theta030_radangle_20k_combined_summary.csv`; curated files only; local raw `.vti/.pvti` count `0`. |
| exploratory_not_validation | `/media/yuan/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_tableII_q27_geometric_theta030_radAngle011_200k_20260610` | Theta030 single 200000-step low-input-angle pilot for the PRE 2025 reduced sphere setup. Target theta is `30 deg`, TCLB input `radAngle=11 deg`, same `80x80x140`, `R_drop=24`, `R_solid=24`, `Density_h/l=1/0.001`, `Viscosity_h/l=0.09/0.1`, `M=0.2`, `IntWidth=6`, `tauUpdate=3`, `sigma=5e-5`. Completed to 200000 with solver rc `0`, postprocess rc `0`, no run-log NaN, `max_nonfinite_count=0`, `NumSpecialPoints=392`, and max Mach `6.68e-4`. Compared with direct theta030/radAngle030 at 200k, H1-H2 error improved from `32.5064%` to `19.3178%`, and fitted angle changed from `45.0698 deg` to `43.7649 deg`, but final fluid phase/rho drift worsened from about `-1.27%/-1.25%` to `-3.51%/-3.45%`. This is calibration evidence only; no validation promotion and no full inverse batch yet. | `TCLB\artifacts\pre2025_sphere_tableII_q27_geometric_theta030_radAngle011_200k_20260610`; curated XML/config/log/TCLB CSV/postprocess CSV+JSON/summary/comparison CSV only; local raw `.vti/.pvti` count `0`. |
| exploratory_not_validation / failed_negative_evidence | `/media/yuan/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_tableII_q27_geometric_theta030_radAngle011_param_sensitivity_200k_20260610` | Theta030/radAngle011 200000-step M/IntWidth sensitivity matrix for the same PRE 2025 reduced sphere setup. New cases: `M0p05_W6`, `M0p1_W6`, `M0p2_W8`, all with target theta `30 deg`, TCLB `radAngle=11 deg`, `80x80x140`, `R_drop=24`, `R_solid=24`, density ratio `1000`, dynamic viscosity ratio `900`, `tauUpdate=3`, `sigma=5e-5`. `M0p05_W6` is `failed_negative_evidence`: solver rc `0` but run.log has PhaseField NaN/Stopping due to Nan at Failcheck; step-0 geometry is not an equilibrium result. `M0p1_W6` completed with H1-H2 error `28.3017%`, fitted angle `46.0825 deg`, phase/rho drift `-2.7866%/-2.7429%`, max Mach `5.960e-4`, nonfinite `0`. `M0p2_W8` completed with H1-H2 error `17.4676%`, fitted angle `42.9514 deg`, phase/rho drift `-3.2268%/-3.1776%`, max Mach `7.727e-4`, nonfinite `0`. `NumSpecialPoints=392` for all postprocessed rows. This is parameter-diagnostic evidence only; no validation promotion. | `TCLB\artifacts\tclb_pre2025_sphere_tableII_q27_geometric_theta030_radAngle011_param_sensitivity_200k_20260610`; combined table `summary\theta030_radAngle011_param_sensitivity_with_baselines.csv`; curated tarball `TCLB\artifacts\tclb_pre2025_sphere_tableII_q27_geometric_theta030_radAngle011_param_sensitivity_200k_20260610_curated_no_raw.tar.gz`; local raw `.vti/.pvti/.pri` count `0`. Remote raw retained for now: 46 VTI/PVTI/PRI files, about `3.46 GB`. |
| exploratory_not_validation / failed_negative_evidence | `/media/yuan/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_tableII_20260609` | PRE 2025 Table II reduced spherical-surface static wetting TCLB analogue using `/home/yuan/src/TCLB/CLB/d3q27_pf_velocity_q27_geometric_staircaseimp/main`, domain `80x80x140`, `R_drop=24`, `R_solid=24`, theta `30..130`, `M=0.2`, `tauUpdate=3`, `IntWidth=6`, density ratio `1000`, dynamic viscosity ratio `900`. Batch completed 2026-06-10. Only theta090 reached 200000 iterations and postprocessed cleanly; theta030-080 and theta100-130 stopped at iteration 1000 with PhaseField NaN messages despite `run.returncode=0`, so they are `failed_negative_evidence`. Theta090 metrics: `H1_minus_H2_relative_error_percent=7.7076`, `fit_contact_angle_deg=101.4220`, final `mach_max_fluid=5.432e-5`, max over frames `3.204e-4`, fluid-only phase drift `-0.2589%`, fluid rho drift `-0.2548%`, nonfinite `0`, `NumSpecialPoints=7354`. Raw remote output: 21 VTI and 21 PVTI, about `3.7G`, remote-only. This is not a PRE reproduction or validation. | `TCLB\artifacts\pre2025_sphere_tableII_20260610`; curated XML/config/log/TCLB CSV/postprocess CSV+JSON/summary/README only; local raw `.vti/.pvti` count `0`. |
| exploratory_not_validation | active: `/media/yuan/8A0E24070E23EAC1/runs/tclb_static_contact_angle_geometric_grid_density_20260607`; unstable copied history: `/media/yuan/DATA500/runs/tclb_static_contact_angle_geometric_grid_density_20260607`; per-case remote dirs are `<grid_tag>/theta045`, `<grid_tag>/theta090`, and `<grid_tag>/theta135` | Running geometric static contact-angle grid-density/arclength-fit audit, not validation. Binary is `/home/yuan/src/TCLB/CLB/d3q27_pf_velocity_geometric/main`. Local generator is `TCLB\scripts\make_tclb_static_contact_angle_geometric_grid_density_cases.py`; runner is `TCLB\scripts\hm570_run_static_contact_angle_grid_density_batch.sh`; arclength postprocess script is `TCLB\scripts\tclb_static_contact_angle_arclength_audit.py`; batch summary script is `TCLB\scripts\tclb_static_contact_angle_grid_density_batch_summary.py`. Matrix has 15 cases: R24/W4 128x96x128, R32/W5 160x128x160, R32/W6 160x128x160, R48/W6 224x192x224, R48/W8 224x192x224, each at theta045/theta090/theta135. DATA500 partial copy was archived under `copied_partial_before_20260608_0005_retarget_to_8A0E`; active XMLs were retargeted to `/media/yuan/8A0E24070E23EAC1/runs`; the corrected runner derives case dir from XML `output` and writes per-theta `run.log`, `run.stderr`, `run.returncode`, copied XML, and `run.done`. Raw VTI/PVTI remain remote-only. | Local generated case XMLs and manifest only so far: `TCLB\cases\validation\static_contact_angle_geometric_grid_density_20260607`. No curated artifact directory yet. After completion, copy only XML/log/stderr/returncode/generated config/TCLB CSV/arclength CSV+JSON+PNG/summary; do not copy raw `.vti/.pvti` locally by default. |
| exploratory_not_validation | `/media/yuan/DATA500/runs/tclb_z_wall_rho772_geometric_theta090_bounded_u008_M0025_W6_20260607/theta090` | Single geometric theta090 dry-wall bounded runtime probe allowed by read-only audit only as impact-chain health evidence. Uses `/home/yuan/src/TCLB/CLB/d3q27_pf_velocity_geometric/main`, R0=14, 96^3, smooth droplet-only velocity `-0.008`, `M=0.025`, `IntWidth=6`, 3200 steps. Completed with TCLB/postprocess return code 0; first contact 1200; beta_area max `1.167983` at final step; beta_box max `1.142857`; resting false; fluid-only phase drift max `0.6386%`; rho drift `-0.5870%`; max Mach `0.014789`; nonfinite `0`; raw 9 VTI and 9 PVTI remote-only, about 498M run size. Read-only audit says runtime health passed for bounded probe only and does not authorize validation, R0>=32, sweep, or liquid-film cases. Physical/dimensionless time and z-max wall ghost phase are not separately reported. Postprocess script SHA256 is `F0A055099848EE799C85E023322CF77349BA550F16FBC6423ABD3EED356CC9DB`. | `TCLB\artifacts\tclb_z_wall_rho772_geometric_theta090_bounded_u008_M0025_W6_20260607_theta090`; curated README, `read_only_audit_20260607.md/json`, XML, manifest, generated config, run.log/stderr/returncode, TCLB CSV log, postprocess script/stdout/stderr/returncode, metrics CSV, summary JSON, and morphology/beta/mass/centroid PNGs; local raw `.vti/.pvti` count `0` |
| exploratory_not_validation | existing-output-only local gate candidate; source data from geometric static 45/90/135 artifacts | Candidate two-metric geometric static contact-angle gate. Frozen local gate still fails and `validation_candidate_allowed=false`; read-only audit permits only one `theta090` dry-wall bounded runtime probe as `exploratory_not_validation`, not validation, sweep, R0>=32, liquid-film, production, or publication evidence. | `TCLB\artifacts\static_contact_angle_geometric_revised_gate_candidate_20260607`; contains README, `geometric_static_revised_gate_candidate_summary.json`, audit JSON/MD, and per-case CSV; local raw `.vti/.pvti` count `0` |
| exploratory_not_validation | existing-output-only local audit; source remote paths `/home/yuan/runs/tclb_static_contact_angle_geometric_calib_20260607/theta045` and `/home/yuan/runs/tclb_static_contact_angle_geometric_theta090_theta135_minout_20260607` | Geometric static contact-angle local-vs-global integration audit. Frozen local-tangent gate remains failed, but route is `unresolved_not_rejected`; this older audit did not permit impact work. The later two-metric audit only permits one bounded runtime probe. | `TCLB\artifacts\static_contact_angle_geometric_local_vs_global_audit_20260607`; contains README and `local_vs_global_audit_summary.json`; local raw `.vti/.pvti` count `0` |
| exploratory_not_validation | `/home/yuan/runs/tclb_static_contact_angle_geometric_theta090_theta135_minout_20260607` | Geometric-only theta090/theta135 minimal-output static-contact cases. Preferred local angles are theta045 `43.2468 deg`, theta090 `77.2764 deg`, theta135 `118.1133 deg`; theta090/theta135 macro complements are near target. Current static validation gate remains failed; only the later audited single theta090 bounded runtime probe is allowed. | `TCLB\artifacts\static_contact_angle_geometric_theta090_theta135_minout_20260607`; curated XML, logs, generated configs, TCLB CSV logs, local/global metrics, summary, and figures; local raw `.vti/.pvti` count `0` |
| exploratory_not_validation | `/home/yuan/runs/tclb_static_contact_angle_geometric_staircaseimp_20260607/theta045`; analysis under `theta045/analysis_contact_angle_geometric_staircaseimp`; convention audit under `/home/yuan/runs/tclb_static_contact_angle_geometric_staircaseimp_20260607/analysis_contact_angle_geometric_staircaseimp_convention_audit` | A2 geometric plus staircase-improvement theta045 diagnostic using `/home/yuan/src/TCLB/CLB/d3q27_pf_velocity_geometric_staircaseimp/main`, `radAngle=45d`, 128x64x128, `M=0.05`, `IntWidth=4`, 200000 steps, VTK interval 200000. Build, TCLB run, postprocess, and convention audit all returned `0`. Raw output is `2` VTI and `2` PVTI, remote-only, remote size about `133M`. Metrics: complement `59.511398 deg`; convention-audit liquid-side range `57.620709-61.896170 deg`; best error `+12.620709 deg`; fluid-only phase drift `-0.855225%`; rho drift `-0.824869%`; max Mach `3.044e-5`; nonfinite `0`. This cleanly rejects `geometric_staircaseimp` as an immediate theta045 fix; no 90/135 continuation, impact sweep, or promotion. | `TCLB\artifacts\static_contact_angle_geometric_staircaseimp_20260607`; curated XML/config/log/TCLB CSV/metrics CSV/summary JSON/figures/stdout/stderr/script outputs/read-only audit only; local raw `.vti/.pvti` count `0`. Build audit: `TCLB\artifacts\tclb_build_geometric_staircaseimp_audit_20260607` |
| exploratory_not_validation | `/home/yuan/runs/tclb_static_contact_angle_revised_eval_20260607` | Existing-output-only revised static contact-angle evaluation for surface theta045/theta090/theta135, geometric theta045, and geometric_staircase theta045. Primary metric is local liquid-side contact-line tangent angle over 3-8 cell near-wall windows; global circle/cap angle is secondary. Key result: geometric theta045 and geometric_staircase theta045 local angles are `43.150 +/- 0.100 deg`, while global circle/cap remains about `59.511 deg`; this points to a metric-definition problem rather than a clear geometric wetting-model failure. No new TCLB run and no raw local copy. | `TCLB\artifacts\static_contact_angle_revised_eval_20260607`; includes summary CSV/JSON, angle/error figures, per-case local tangent CSV/JSON/PNG, script copy, README, and read-only audit; local raw `.vti/.pvti` count `0` |
| failed_negative_evidence | `/home/yuan/runs/tclb_static_contact_angle_geometric_rad005_minout_20260607/theta005` | Geometric-only low-angle static diagnostic, `radAngle=5d`, 200000 requested steps, VTK interval 200000. TCLB wrapper return code is `0`, but `run.log` reports `Checking PhaseField discovered NaN` and `Stopping due to Nan value`; only the initial VTI/PVTI pair exists, remote size about `66M`. This is a failed low-angle response point, not calibration. | `TCLB\artifacts\static_contact_angle_geometric_rad005_minout_20260607`; curated XML/config/run.log/TCLB CSV/read-only audit only; local raw `.vti/.pvti` count `0` |
| exploratory_not_validation | `/home/yuan/runs/tclb_static_contact_angle_geometric_calib_20260607/theta045`; analysis under `theta045/analysis_contact_angle_geometric`; convention audit under `/home/yuan/runs/tclb_static_contact_angle_geometric_calib_20260607/analysis_contact_angle_geometric_convention_audit` | A2 geometric-wetting theta045 diagnostic using `/home/yuan/src/TCLB/CLB/d3q27_pf_velocity_geometric/main`. Run return code `0`, postprocess return code `0`, convention audit return code `0`; 21 VTI and 21 PVTI remain remote-only, remote case size about `1.4G`; HM570 free disk was about `3.4G` afterward, so theta090/theta135 were not run. Metrics: complement `59.5114 deg`; convention-audit liquid-side range `57.6207-61.8962 deg`; best liquid-side error `+12.6207 deg`; fluid-only phase drift `-0.8552%`; rho drift `-0.8249%`; max Mach `9.398e-5`; nonfinite `0`. Conclusion: geometric-only route runs but still fails theta045 low-angle calibration; no impact sweep or promotion. | `TCLB\artifacts\static_contact_angle_geometric_calib_20260607`; curated XML/config/log/TCLB CSV/metrics CSV/summary JSON/figures/stdout/stderr/script outputs only; local raw `.vti/.pvti` count `0`. Build audit: `TCLB\artifacts\tclb_build_audit_20260607` |
| runtime_sanity | `/home/yuan/runs/tclb_standard_d3q27_20260606_231035/bubbleRise_short`; analysis under `/home/yuan/runs/tclb_standard_d3q27_20260606_231035/bubbleRise_short/analysis_bubbleRise_A1_20260607` | TCLB built-in `bubbleRise_1` A1 artifact formalization from existing output only, with no new TCLB simulation. Remote raw output is `7` VTI and `7` PVTI, about `468M`, and remains remote-only. Postprocess return code `0`; stderr has one Matplotlib no-contour warning for a morphology frame, recorded as a visualization limitation. Metrics: bubble proxy uses clipped `1 - PhaseField` because `BubbleType=-1`; rise direction is positive y by largest bubble-proxy centroid displacement; centroid displacement `55.3067` cells; max Mach `0.02235`; max nonfinite `0`; max all-cell/fluid-only phase drift `9.72e-5`/`2.94e-5`; max all-cell/fluid-only rho drift `2.63e-5`/`2.63e-5`. A pre-audit local Safi TC1 FeatFlow comparison now exists using digitized Fig. 4/5 curves: center-of-mass L2 abs error `0.0587`, rise-velocity L2 abs error `0.0145`, max Mach `0.02235`, nonfinite `0`. `definition_evidence.md` records Safi time/Omega2 definitions, TCLB `L0=64`, and HM570 `GasTotalVelocityY/GasTotalPhase` source evidence. Claim limit remains `runtime_sanity`; no data-level validation without read-only audit, stronger reference provenance if available, and grid/time-step checks. | `TCLB\artifacts\tclb_bubbleRise_A1_20260607`; curated README, execution report, XML/config/log/TCLB CSV/metrics CSV/summary JSON/figures/stdout/stderr/script copies only; local raw `.vti/.pvti` count `0`. Comparison artifact: `TCLB\artifacts\tclb_bubbleRise_A1_safi_compare_20260607`; curated CSV/JSON/PNG/README/definition evidence only; local raw `.vti/.pvti` count `0` |

A1 Safi read-only audit note:

```text
artifact: TCLB\artifacts\tclb_bubbleRise_A1_safi_compare_20260607\read_only_audit_20260607.md
decision: keep runtime_sanity; do not promote to validation_candidate
reason: bitmap-derived reference provenance is not independently calibrated,
        comparison errors exceed recorded digitization uncertainty, rise
        velocity remains a diffuse-interface Omega2 proxy, and only one L0=64
        run is available
script: TCLB\scripts\a1_bubbleRise_compare_safi2017.py
script_sha256: 5AB50D3266131C382DD6573BEE01008150A19A17A1101E055264778238FF1CC8
reference_rows: 225 total = 110 center_of_mass + 115 rise_velocity
comparison_rows: 223 total = 108 center_of_mass + 115 rise_velocity
raw_copy_policy: local raw VTI/PVTI count remains 0
velocity_crosscheck: TCLB\artifacts\tclb_bubbleRise_A1_safi_compare_20260607\a1_velocity_observable_crosscheck_summary.json
velocity_crosscheck_result: same positive rise direction, but max interval
                            nondimensional velocity difference 0.0461, max
                            relative difference 14.7%, and cumulative centroid
                            prediction from CSV velocity is 6.94 cells high at
                            step 12000; do not lock velocity mapping for
                            validation use
```

A1 Bonn/INS reference-data provenance note:

```text
status: runtime_sanity reference provenance only; no validation promotion
script: TCLB\scripts\a1_bubbleRise_download_bonn_reference.py
script_check: python -m py_compile returned 0
local_output_dir: TCLB\references\data\bonn_3d_rising_bubble_tc1
curated_csv: TCLB\references\data\bonn_3d_rising_bubble_tc1\bonn_3d_rising_bubble_tc1_reference.csv
summary_json: TCLB\references\data\bonn_3d_rising_bubble_tc1\bonn_3d_rising_bubble_tc1_reference_summary.json
README: TCLB\references\data\bonn_3d_rising_bubble_tc1\README.md
zip_files: TC1_centerOfMass.zip, TC1_riseVelocity.zip
ASCII_entries: TC1_centerOfMass_DROPS.txt, TC1_centerOfMass_NaSt3D.txt,
               TC1_centerOfMass_OpenFOAM.txt, TC1_riseVelocity_DROPS.txt,
               TC1_riseVelocity_NaSt3D.txt, TC1_riseVelocity_OpenFOAM.txt
center_zip_sha256: db617631d966df349549b729c44c216f6ae056f15c37171231de9e709c7f6842
velocity_zip_sha256: 37cb998a692dccd0440d00fa3dc991f083e9258f2b4e02377f76a632d9585a68
curated_rows: 5388 total; center_of_mass DROPS/NaSt3D/OpenFOAM =
              601/595/301; rise_velocity DROPS/NaSt3D/OpenFOAM =
              3001/589/301
comparison_vs_current_safi_bitmap: center_of_mass L2/max abs difference
                                   DROPS 0.01040/0.01221,
                                   NaSt3D 0.01380/0.01591,
                                   OpenFOAM 0.02904/0.04549;
                                   rise_velocity L2/max abs difference
                                   DROPS 0.00337/0.01377,
                                   NaSt3D 0.00339/0.01395,
                                   OpenFOAM 0.01382/0.02296
claim_limit: Bonn archive data are Adelsberger 2014 TC1 DROPS/NaSt3D/
             OpenFOAM series, not Safi 2017 FeatFlow unless separately
             audited
```

A1 Bonn/INS direct-comparison artifact:

```text
status: runtime_sanity audit input only; no validation promotion
artifact: TCLB\artifacts\tclb_bubbleRise_A1_bonn_compare_20260607
script: TCLB\scripts\a1_bubbleRise_compare_bonn_reference.py
script_check: python -m py_compile returned 0
inputs: TCLB\artifacts\tclb_bubbleRise_A1_20260607\bubble_rise_metrics.csv,
        TCLB\artifacts\tclb_bubbleRise_A1_20260607\run_files\bubbleRise_1_Log_P00_00000000.csv,
        TCLB\references\data\bonn_3d_rising_bubble_tc1\bonn_3d_rising_bubble_tc1_reference.csv
outputs: a1_bonn_pointwise_comparison.csv,
         a1_bonn_interval_velocity_comparison.csv,
         a1_bonn_comparison_summary.json,
         read_only_audit_20260607.md,
         README.md,
         figures\a1_bonn_center_of_mass_comparison.png,
         figures\a1_bonn_rise_velocity_comparison.png
local_raw_vti_pvti_count: 0
center_of_mass_L2_max_abs: DROPS 0.04758/0.08268,
                           NaSt3D 0.04471/0.07970,
                           OpenFOAM 0.02981/0.04918
rise_velocity_csv_proxy_L2_max_abs: DROPS 0.01490/0.03255,
                                    NaSt3D 0.01337/0.03134,
                                    OpenFOAM 0.02366/0.03582
rise_velocity_centroid_interval_L2_max_abs: DROPS 0.02783/0.03549,
                                            NaSt3D 0.02968/0.03685,
                                            OpenFOAM 0.01805/0.02990
claim_limit: Bonn/INS TC1 data are Adelsberger 2014 DROPS/NaSt3D/OpenFOAM
             series, not Safi FeatFlow without separate audit; observable
             mapping and grid/time-step sensitivity remain unresolved
read_only_audit: keep runtime_sanity; do not promote to validation_candidate
                 due to missing accepted thresholds, unresolved Bonn/Safi
                 mapping, unresolved velocity observable, coarse centroid
                 intervals, single L0=64 run, nontrivial center-of-mass
                 errors, and missing grid/time-step sensitivity
```

A1 acceptance-gate artifact:

```text
status: runtime_sanity; explicit failed gate for validation_candidate
protocol: TCLB\docs\a1_bubbleRise_acceptance_protocol.md
script: TCLB\scripts\a1_bubbleRise_acceptance_gate.py
script_check: python -m py_compile returned 0
run_check: python scripts\a1_bubbleRise_acceptance_gate.py returned 0
artifact: TCLB\artifacts\tclb_bubbleRise_A1_acceptance_gate_20260607
outputs: README.md, a1_acceptance_gate_summary.json,
         read_only_audit_20260607.md
inputs: existing A1 summary, Bonn comparison summary, Safi comparison summary,
        velocity observable cross-check summary, and Bonn/Safi read-only audits
local_raw_vti_pvti_count: 0
health_pass: max Mach 0.02235, nonfinite 0, fluid-only phase drift
             2.94e-5, fluid-only rho drift 2.63e-5
failed_gate_reasons: thresholds provisional, no accepted Bonn target series,
                     Bonn/Safi FeatFlow mapping unaccepted, velocity
                     observable unresolved, no grid/time-step sensitivity,
                     best Bonn center and velocity errors above provisional
                     strict thresholds, velocity cross-check above threshold
claim_limit: does not validate rho_ratio=772 impact, dry-wall/liquid-film
             target cases, contact-angle sweep, Wang 2023 equivalence, or
             publication readiness
```

A1 grid/time sensitivity completed chain:

```text
status: runtime_sanity; completed HM570 runs and Bonn comparisons, no validation promotion
case_dir: TCLB\cases\validation\a1_bubbleRise_grid_time_20260607
manifest: TCLB\cases\validation\a1_bubbleRise_grid_time_20260607\tclb_bubbleRise_A1_grid_time_20260607_manifest.json
case_generator: TCLB\scripts\make_a1_bubbleRise_sensitivity_cases.py
summary_script: TCLB\scripts\a1_bubbleRise_grid_time_summary.py
remote_run_root: /home/yuan/runs/tclb_bubbleRise_A1_grid_time_20260607
local_summary_artifact: TCLB\artifacts\tclb_bubbleRise_A1_grid_time_20260607
outputs: README.md, a1_grid_time_sensitivity_summary.json,
         read_only_audit_20260607.md, per-case curated analysis folders,
         per-case postprocess logs
completed_cases: coarse_L48, base_L64, fine_L80
remote_raw_counts: 7 VTI and 7 PVTI per case
remote_sizes: coarse_L48 about 131M; base_L64 about 231M; fine_L80 about 538M
comparison_artifacts:
  TCLB\artifacts\tclb_bubbleRise_A1_grid_time_20260607_coarse_L48_bonn_compare
  TCLB\artifacts\tclb_bubbleRise_A1_grid_time_20260607_base_L64_bonn_compare
  TCLB\artifacts\tclb_bubbleRise_A1_grid_time_20260607_fine_L80_bonn_compare
health:
  coarse_L48 max Mach 0.0317124; nonfinite 0; fluid phase/rho drift
             4.07186e-5 / 3.65341e-5
  base_L64   max Mach 0.0223497; nonfinite 0; fluid phase/rho drift
             2.93937e-5 / 2.63515e-5
  fine_L80   max Mach 0.0179932; nonfinite 0; fluid phase/rho drift
             1.69536e-5 / 1.52111e-5
grid_time_spreads:
  center_of_mass_l2_abs_error_spread 0.0220774
  rise_velocity_l2_abs_error_spread 0.0349694
gate_result: A1 acceptance gate rerun with grid-time summary and remains
             runtime_sanity; failed spread, velocity observable, target-series,
             and provisional-threshold checks
claim_limit: completed sensitivity input only; no A1 validation promotion, no
             rho772 impact validation, and no Wang 2023 equivalence
copy_policy: no raw VTI/PVTI copied locally
```

| exploratory_not_validation | `/home/yuan/runs/tclb_static_contact_angle_calib_20260607/theta045`, `/theta090`, `/theta135`; v3 analysis under each `analysis_contact_angle_v3`; convention audit under `/home/yuan/runs/tclb_static_contact_angle_calib_20260607/analysis_contact_angle_convention_audit` | Official TCLB ContactAngle-derived static wetting calibration before impact sweep; all three cases completed 200000 steps with return code 0 and 21 VTI/PVTI each. v3 postprocess added input-angle and complement-error fields without launching new simulations. v3: theta045 apparent `122.3379 deg`, complement `57.6621 deg`, complement error `+12.6621 deg`, phase drift `+4.1804%`, rho drift `-0.9026%`, max Mach `9.53e-5`, nonfinite `0`; theta090 apparent `89.1689 deg`, complement `90.8311 deg`, complement error `+0.8311 deg`, phase drift `-0.1825%`, rho drift `+0.0364%`, max Mach `1.16e-5`, nonfinite `0`; theta135 apparent `44.7137 deg`, complement `135.2863 deg`, complement error `+0.2863 deg`, phase drift `-3.3408%`, rho drift `+0.7698%`, max Mach `1.67e-4`, nonfinite `0`. Convention audit return code `0`, no stderr, and compared 24 variants per angle using corrected wall-normal coordinate mapping: x-mid contour plot x is y wall-normal, z-mid contour plot y is y wall-normal. It found theta045 liquid-side angle `55.7808-60.7211 deg` and therefore still fails low-angle calibration; theta090 and theta135 are close under liquid-side/complement interpretation. No validation promotion and no impact contact-angle sweep authorization. Build-state audit found the current HM570 `d3q27_pf_velocity/main` binary has `geometric`, `staircaseimp`, `isograd`, and `tprec` disabled (`options.R=FALSE`, `Consts.h=#undef`), even though `conf.mk` lists them as possible build variants; these runs used the non-geometric/default surface-energy wetting path and are not evidence for the geometric wetting boundary condition. This is not accepted calibration yet; resolve theta045 low-angle wetting/mass/fit mismatch first. | `TCLB\artifacts\tclb_static_contact_angle_calib_20260607_theta045`, `TCLB\artifacts\tclb_static_contact_angle_calib_20260607_theta090`, `TCLB\artifacts\tclb_static_contact_angle_calib_20260607_theta135`; each has curated `analysis_contact_angle_v3`; v3 summary `TCLB\artifacts\static_contact_angle_calib_20260607_v3_summary.json`; convention audit `TCLB\artifacts\static_contact_angle_convention_audit_20260607`; older summary `TCLB\artifacts\static_contact_angle_calib_20260607_summary.json` |
| exploratory_not_validation | `/home/yuan/runs/tclb_static_contact_angle_response_surface_energy_20260607` | Low-angle static response check for TCLB default/non-geometric surface-energy wetting parameter `radAngle=30/35/40/45/50/60`; all six cases completed with `run_return_code=0`, 21 VTI and 21 PVTI each, remote size about `8.1G`. Current HM570 build has `geometric/staircaseimp/isograd/tprec=FALSE/#undef`, so these are not geometric-BC results. Corrected convention audit return code `0`, stderr empty, and `run_id=tclb_static_contact_angle_response_surface_energy_20260607`. Liquid-side angle ranges from the 24-variant audit are theta030 `48.8321-57.2313 deg`, theta035 `51.0164-57.7338 deg`, theta040 `53.2827-59.0198 deg`, theta045 `55.7808-60.7211 deg`, theta050 `58.6713-62.9543 deg`, theta060 `65.3152-68.5590 deg`; this is negative evidence for using `radAngle=30/35` as a stable liquid-side 45 substitute. Per-case mass/rho/Mach/nonfinite are reported in the execution report; low-angle phase drift remains large (`7.99%` at theta030, `6.03%` at theta035). No validation promotion and no 45/90/135 impact sweep authorization. | `TCLB\artifacts\static_contact_angle_response_surface_energy_20260607`; curated XML/config/log/TCLB CSV/CSV/JSON/PNG/stdout/stderr/script copies only; local raw `.vti/.pvti` count `0`; includes `execution_report.md` and corrected convention audit artifacts |
| exploratory_not_validation | `/home/yuan/runs/tclb_static_contact_angle_bracket_lowangle_20260607` | Static low-angle bracket continuation for `radAngle=15/18/20/22/25/28`; all cases completed with run/postprocess/audit return code `0`, 21 VTI and 21 PVTI each, remote size about `8.1G`. Liquid-side ranges stay broad and mostly above 45; phase drift ranges `9.2934-16.2726%`, rho drift `-1.6926%` to `-2.5780%`. Not accepted calibration; no validation promotion. | `TCLB\artifacts\static_contact_angle_bracket_lowangle_20260607`; curated only, local raw `.vti/.pvti` count `0`; combined report `TCLB\artifacts\static_contact_angle_bracket_combined_20260607` |
| exploratory_not_validation | `/home/yuan/runs/tclb_static_contact_angle_bracket_lower_20260607` | Static lower bracket continuation for `radAngle=5/10/12`; all cases completed with run/postprocess/audit return code `0`, 21 VTI and 21 PVTI each, remote size about `4.1G`. Liquid-side 45 is bracketed only in an exploratory fit-sensitivity sense: ranges 5 `43.8741-60.0582 deg`, 10 `44.6668-59.8532`, 12 `44.7333-59.7167`; postprocess complements `45.5354-46.4137 deg`; phase drift `17.1268-18.3009%`, rho drift `-2.6889%` to `-2.8428%`. Read-only audit allows only a single 45 exploratory impact pilot, not validation and not a 45/90/135 sweep. | `TCLB\artifacts\static_contact_angle_bracket_lower_20260607`; curated only, local raw `.vti/.pvti` count `0`; combined report `TCLB\artifacts\static_contact_angle_bracket_combined_20260607` |
| exploratory_not_validation | `/home/yuan/runs/tclb_static_contact_angle_bracket_lowangle_M0025_W6_20260607` | Static low-angle sensitivity for `radAngle=5/10/15` using the prior lower-y-wall 128x64x128, 200000-step, VTK-10000 setup but with `M=0.025`, `IntWidth=6`. All cases completed with TCLB/postprocess return code `0`; convention audit return code `0`; BOUNDARY-aware reanalysis return code `0` and stderr empty; raw output is 21 VTI and 21 PVTI per angle, 63/63 total, about `4.1G`, remote-only. Complements and BOUNDARY-aware health: theta005 complement `52.7401 deg`, all-cell phase drift `8.5176%`, fluid-only phase drift `1.6495%`, wall/ghost phase drift `153.3568%`, rho drift `1.5921%`, max Mach `1.4126e-4`, nonfinite `0`; theta010 `52.8157`, `8.2010%`, `1.6046%`, `148.0239%`, `1.5488%`, `1.4010e-4`, `0`; theta015 `52.9568`, `7.6811%`, `1.5296%`, `139.2290%`, `1.4764%`, `1.3811e-4`, `0`. Convention-audit liquid-side ranges are `50.9341-59.9471`, `51.0110-59.8931`, and `51.1540-59.8179 deg`. This is mixed/negative evidence: fluid-only bulk drift is much smaller than all-cell wall/ghost-inclusive phase drift, but the liquid-side 45 bracket was not preserved and rho drift remains around `1.5%`. No validation promotion and no impact contact-angle sweep authorization. | `TCLB\artifacts\static_contact_angle_bracket_lowangle_M0025_W6_20260607`; curated XML/config/log/TCLB CSV/CSV/JSON/PNG/stdout/stderr/script copies plus `execution_report.md`; includes per-case `analysis_contact_angle_bracket_M0025_W6_boundarymass`; local raw `.vti/.pvti` count `0`; includes `curated_no_raw.tgz` |
| exploratory_not_validation | `/home/yuan/runs/tclb_z_wall_rho772_rad005_target45_dropletsmooth_u008_M0025_W6_ext6400_20260607/rad005_target45` | Single z-wall dry-wall exploratory pilot using input `radAngle=5d` as a liquid-side-45 target after static bracket audit. Run and postprocess return code `0`; raw VTI/PVTI `17/17`, remote size about `939M`, raw remote-only. Case: `R0=14`, 96x96x96, gravity `-z`, smooth `DropletOnlyVelocity=2`, `DropletVelocityZ=-0.008`, `M=0.025`, `IntWidth=6`, 6400 steps. Required impact metrics: `beta_area_max=1.73427` at final step 6400, `beta_box_max=1.71429` at step 6000, late beta changes `0.06489/0.07143`, `resting_candidate=false`, all-cell phase drift `12.4209%`, fluid-only phase drift `2.2720%`, rho drift `-2.0886%`, max Mach `0.01461`, nonfinite `0`, wall ghost phase last `1885.7082`. Runtime and finite checks are healthy, but mass/rho/resting fail exploratory gates for promotion; no 45/90/135 sweep. | `TCLB\artifacts\tclb_z_wall_rho772_rad005_target45_dropletsmooth_u008_M0025_W6_ext6400_20260607_rad005_target45`; curated XML/config/log/CSV/JSON/PNG/stdout/stderr/script copies only; local raw `.vti/.pvti` count `0` |
| exploratory_not_validation | `/home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext9600_20260607/theta090` | 9600-step extension of the same small-grid theta=90 coupled `M=0.025`, `IntWidth=6` candidate; `R0=14`, z-wall, smooth `DropletOnlyVelocity=2`, `DropletVelocityZ=-0.008`, `CenterZ=22`; run.log reaches 9600, `beta_area` max still at final step 9600, `late_beta_area_change=0.01505`, `resting_candidate=false`; all-cell phase drift `+6.688%` is wall/ghost diagnostic only, fluid-only phase drift `-1.3355%`, rho drift `-1.2277%`, max Mach `0.01479`, nonfinite `0`; audit says no promotion and treat as negative evidence for continuing this small-grid candidate | `TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext9600_20260607_theta090` |
| exploratory_not_validation | `/home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext6400_20260607/theta090` | 6400-step extension of current best small-grid candidate; `M=0.025`, `IntWidth=6`, `R0=14`, theta=90, z-wall, smooth `DropletOnlyVelocity=2`, `DropletVelocityZ=-0.008`, `CenterZ=22`; first contact 1200, `beta_area` max still at final step 6400, `resting_candidate=false`; fluid-only phase drift `-1.1369%`, rho drift `-1.0451%`, max Mach `0.01479`, nonfinite `0`; audit says no promotion, no larger grid or contact-angle sweep from this result alone | `TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext6400_20260607_theta090` |
| exploratory_not_validation | `/home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_ext3200_M0025_W6_20260607/theta090` | Coupled diagnostic against prior ext3200 baseline; `M=0.025`, `IntWidth=6`, `R0=14`, theta=90, z-wall, smooth `DropletOnlyVelocity=2`, `DropletVelocityZ=-0.008`, `CenterZ=22`, 3200 steps; phase drift improves to about 3.65% and rho drift to about -0.59%, best current direction but still fails long-window phase gate | `TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_ext3200_M0025_W6_20260607_theta090` |
| exploratory_not_validation | `/home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_ext3200_W6_20260607/theta090` | IntWidth-only sensitivity against prior ext3200 baseline; `M=0.05`, `IntWidth=6`, `R0=14`, theta=90, z-wall, smooth `DropletOnlyVelocity=2`, `DropletVelocityZ=-0.008`, `CenterZ=22`, 3200 steps; phase drift improves to about 4.33% and rho drift to about -0.76%, but still fails long-window phase gate | `TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_ext3200_W6_20260607_theta090` |
| exploratory_not_validation | `/home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_ext3200_W4_20260607/theta090` | IntWidth-only sensitivity against prior ext3200 baseline; `M=0.05`, `IntWidth=4`, `R0=14`, theta=90, z-wall, smooth `DropletOnlyVelocity=2`, `DropletVelocityZ=-0.008`, `CenterZ=22`, 3200 steps; phase drift worsens to about 5.92% and rho drift to about -1.07%, negative evidence for reducing `IntWidth` alone | `TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_ext3200_W4_20260607_theta090` |
| exploratory_not_validation | `/home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_ext3200_M0025_20260607/theta090` | M-only sensitivity against prior ext3200 baseline; `M=0.025`, `IntWidth=5`, `R0=14`, theta=90, z-wall, smooth `DropletOnlyVelocity=2`, `DropletVelocityZ=-0.008`, `CenterZ=22`, 3200 steps; phase drift improves to about 4.14% but still fails long-window mass gate | `TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_ext3200_M0025_20260607_theta090` |
| exploratory_not_validation | `/home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_ext3200_20260607/theta090` | extended theta=90 smooth u008 window; first contact at 1000, beta still growing, phase drift about 5.02% | `TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_ext3200_20260607_theta090` |
| exploratory_not_validation | `/home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_nearwall_20260607/theta090` | z=0 wall, gravity -z, theta=90 smooth droplet velocity with lower Uz; phase drift about 1.34% | `TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_nearwall_20260607_theta090` |
| exploratory_not_validation | `/home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_nearwall_20260607/theta090` | z=0 wall, gravity -z, theta=90 smooth droplet-velocity A/B; phase drift about 2.96% | `TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_nearwall_20260607_theta090` |
| exploratory_not_validation | `/home/yuan/runs/tclb_z_wall_rho772_dropletonly_nearwall_20260607/theta090` | z=0 wall, gravity -z, theta=90 droplet-only near-wall contact; phase drift about 3.28% | `TCLB\artifacts\tclb_z_wall_rho772_dropletonly_nearwall_20260607_theta090` |
| exploratory_not_validation | `/home/yuan/runs/tclb_z_wall_rho772_dropletonly_20260607/theta090` | z=0 wall, gravity -z, theta=90 droplet-only pilot; no wall contact by 1200 steps | remote-only except case generation |
| exploratory_not_validation | `/home/yuan/runs/tclb_z_wall_rho772_lowmach_contact_20260607/theta090` | z=0 wall, gravity -z, theta=90 low-Mach contact pilot; global VelocityZ; small grid | `TCLB\artifacts\tclb_z_wall_rho772_lowmach_contact_20260607_theta090` |
| exploratory_not_validation | `/home/yuan/runs/tclb_z_wall_rho772_pilot_20260607/theta090` | z=0 wall, gravity -z, theta=90 smoke; no contact by 500 steps; max Mach near guard | `TCLB\artifacts\tclb_z_wall_rho772_pilot_20260607_theta090` |
| exploratory_not_validation | `/home/yuan/runs/tclb_impact_rho772_drywall_explore_latest` | first rho772 dry-wall pipeline run, x-wall, small grid | `TCLB\artifacts\tclb_impact_rho772_drywall_explore_latest` |
| runtime_sanity | `/home/yuan/runs/tclb_standard_d3q27_latest` | TCLB bubble rise and contact angle sanity | currently indexed in old D3Q27 artifacts |
| runtime_sanity | `/home/yuan/runs/tclb_smoke_contact45` | reduced contact-angle smoke | currently remote-only |

## Local Artifacts

Current local artifacts:

```text
TCLB\artifacts\ext3200_fluidmass_summary.csv
TCLB\artifacts\tclb_bubbleRise_A1_20260607
TCLB\artifacts\tclb_bubbleRise_A1_reference_gap_20260607
TCLB\artifacts\tclb_bubbleRise_A1_safi_compare_20260607
TCLB\artifacts\static_contact_angle_calib_20260607_summary.json
TCLB\artifacts\static_contact_angle_calib_20260607_v3_summary.json
TCLB\artifacts\static_contact_angle_convention_audit_20260607
TCLB\artifacts\static_contact_angle_bracket_combined_20260607
TCLB\artifacts\static_contact_angle_bracket_lowangle_20260607
TCLB\artifacts\static_contact_angle_bracket_lower_20260607
TCLB\artifacts\static_contact_angle_bracket_lowangle_M0025_W6_20260607
TCLB\artifacts\static_contact_angle_response_surface_energy_20260607
TCLB\artifacts\tclb_z_wall_rho772_rad005_target45_dropletsmooth_u008_M0025_W6_ext6400_20260607_rad005_target45
TCLB\artifacts\tclb_static_contact_angle_calib_20260607_theta045
TCLB\artifacts\tclb_static_contact_angle_calib_20260607_theta090
TCLB\artifacts\tclb_static_contact_angle_calib_20260607_theta135
TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext9600_20260607_theta090
TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext6400_20260607_theta090
TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_ext3200_M0025_W6_20260607_theta090
TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_ext3200_W6_20260607_theta090
TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_ext3200_W4_20260607_theta090
TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_ext3200_M0025_20260607_theta090
TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_ext3200_20260607_theta090
TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_nearwall_20260607_theta090
TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_nearwall_20260607_theta090
TCLB\artifacts\tclb_z_wall_rho772_dropletonly_nearwall_20260607_theta090
TCLB\artifacts\tclb_z_wall_rho772_lowmach_contact_20260607_theta090
TCLB\artifacts\tclb_z_wall_rho772_pilot_20260607_theta090
TCLB\artifacts\tclb_impact_rho772_drywall_explore_latest
```

`TCLB\artifacts\static_contact_angle_convention_audit_20260607` contains:

```text
contact_angle_convention_audit.py
contact_angle_convention_audit_all_metrics.csv
static_contact_angle_convention_audit.csv
static_contact_angle_convention_audit_summary.json
static_contact_angle_convention_audit.png
postprocess_command.txt
postprocess_return_code.txt
postprocess_stderr.log
postprocess_stdout.json
```

Provenance for this existing-output static contact-angle convention audit:

```text
run_id: tclb_static_contact_angle_calib_20260607
remote analysis dir: /home/yuan/runs/tclb_static_contact_angle_calib_20260607/analysis_contact_angle_convention_audit
local artifact dir: C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_convention_audit_20260607
script: scripts\tclb_static_contact_angle_convention_audit.py
remote command: python3 /home/yuan/runs/tclb_static_contact_angle_calib_20260607/analysis_contact_angle_convention_audit/contact_angle_convention_audit.py --base /home/yuan/runs/tclb_static_contact_angle_calib_20260607 --out-dir /home/yuan/runs/tclb_static_contact_angle_calib_20260607/analysis_contact_angle_convention_audit
postprocess return code: 0
stderr: empty
status label: exploratory_not_validation
claim limit: existing-output fit-convention sensitivity only; no validation promotion and no impact sweep authorization
copy policy: curated CSV/JSON/PNG/log/script only; raw theta VTI/PVTI remain remote-only
```

Static convention audit result:

```text
angle definition: lower_wall_liquid_side_angle_deg = 180 - angle_from_circle_deg
coordinate note: x-mid slice contour plot x is y wall-normal; z-mid slice contour plot y is y wall-normal
theta045: 24/24 finite variants; liquid-side angle 55.7808-60.7211 deg; error +10.7808 to +15.7211 deg; best abs error 10.7808 deg
theta090: 24/24 finite variants; liquid-side angle 88.3287-90.8311 deg; best abs error 0.3851 deg
theta135: 24/24 finite variants; liquid-side angle 129.3640-135.2863 deg; best abs error 0.2398 deg
max Mach among best variants: 4.64e-5
nonfinite: 0 in PhaseF and velocity for best variants
gate: theta045 remains the blocker; do not launch 45/90/135 impact contact-angle sweep from this calibration
```

`TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext9600_20260607_theta090` contains:

```text
README.md
run_files\impact_zwall_theta090_dropletsmooth_u008_M0025_W6_ext9600.xml
run_files\impact_zwall_theta090_dropletsmooth_u008_M0025_W6_ext9600_config_P00_00000000.xml
run_files\impact_zwall_theta090_dropletsmooth_u008_M0025_W6_ext9600_Log_P00_00000000.csv
run_files\run.log
run_files\run_return_code.txt
run_files\run_start.txt
run_files\run_end.txt
run_files\manifest*.json
analysis\impact_drywall_beta_mass_metrics.csv
analysis\impact_drywall_summary.json
analysis\postprocess_*.*
analysis\tclb_impact_drywall_postprocess.py
analysis\impact_drywall_beta_t.png
analysis\impact_drywall_mass_velocity.png
analysis\impact_drywall_centroid.png
analysis\drywall_step_*_morphology.png
```

Provenance for this 9600-step coupled M/IntWidth diagnostic:

```text
run_id: tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext9600_20260607
remote source run path: /home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext9600_20260607/theta090
resolved target: same path, no latest alias
local artifact dir: C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext9600_20260607_theta090
status label: exploratory_not_validation
case template: cases\dry_wall\user_1mm_10mm_contact_angle_sweep\pilot_near_wall_equivalent\impact_near_wall_template.xml
case XML: cases\dry_wall\user_1mm_10mm_contact_angle_sweep\pilot_near_wall_equivalent\impact_zwall_theta090_dropletsmooth_u008_M0025_W6_ext9600.xml
remote executed XML: /home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext9600_20260607/theta090/impact_zwall_theta090_dropletsmooth_u008_M0025_W6_ext9600.xml
generated config XML: output/impact_zwall_theta090_dropletsmooth_u008_M0025_W6_ext9600_config_P00_00000000.xml
run.log: /home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext9600_20260607/theta090/run.log
TCLB CSV log: output/impact_zwall_theta090_dropletsmooth_u008_M0025_W6_ext9600_Log_P00_00000000.csv
metrics CSV: analysis/impact_drywall_beta_mass_metrics.csv
summary JSON: analysis/impact_drywall_summary.json
postprocess script: analysis/tclb_impact_drywall_postprocess.py
TCLB return code: 0
postprocess return code: 0
```

Case definition and audit result:

```text
theta: 90
wall_axis: z
wall_side: min
gravity_direction: -z
grid: 96 x 96 x 96
R0: 14
CenterZ: 22
VelocityZ: 0
DropletOnlyVelocity: 2 smooth phase-fraction weighting
DropletVelocityZ: -0.008
GravitationZ: -1e-6
M: 0.025
IntWidth: 6.0
Solve Iterations: 9600
VTK interval: 400
Log interval: 100
Failcheck interval: 100
first_contact_step: 1200
beta_area max: 1.3021088099456783 at step 9600
beta_box max: 1.2857142857142858 at step 7200
late_beta_area_change: 0.015053786964550397 over steps 8800,9200,9600
resting_candidate: false
all-cell phase drift: +6.688467977723006% wall/ghost diagnostic only
fluid-only phase drift: -1.3354949822091176%
fluid clipped phase drift: -1.3354227420845041%
rho drift: -1.2276700620208972%
max Mach: 0.014789263592322023
max nonfinite count: 0
wall ghost phase last: 1029.4048096189983
morphology steps: 0,1200,3600,6400,7600,8400,9200,9600
limitation: theta=90 only, R0=14 small grid, beta_area still peaks at final frame, not run to rest, fluid-only phase and rho drift worsen versus ext6400, no grid/time-step sensitivity, no literature comparison, no status promotion; do not launch R0>=32 or contact-angle sweep from this artifact
```

Raw output and copy policy:

```text
raw_output_dir: /home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext9600_20260607/theta090/output
raw_vti_count: 25
raw_pvti_count: 25
remote_run_size: 1.4G
local raw VTI/PVTI count: 0
copy_policy: keep raw VTI/PVTI remote-only; local artifact is curated run files plus metrics, summary JSON, postprocess logs/script, and beta/mass/centroid/morphology figures
```

`TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext6400_20260607_theta090` contains:

```text
README.md
run_files\impact_zwall_theta090_dropletsmooth_u008_M0025_W6_ext6400.xml
run_files\impact_zwall_theta090_dropletsmooth_u008_M0025_W6_ext6400_config_P00_00000000.xml
run_files\impact_zwall_theta090_dropletsmooth_u008_M0025_W6_ext6400_Log_P00_00000000.csv
run_files\run.log
run_files\run_return_code.txt
run_files\run_start.txt
run_files\run_end.txt
run_files\manifest*.json
analysis\impact_drywall_beta_mass_metrics.csv
analysis\impact_drywall_summary.json
analysis\postprocess_*.*
analysis\tclb_impact_drywall_postprocess.py
analysis\impact_drywall_beta_t.png
analysis\impact_drywall_mass_velocity.png
analysis\impact_drywall_centroid.png
analysis\drywall_step_*_morphology.png
```

Provenance for this 6400-step coupled M/IntWidth diagnostic:

```text
run_id: tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext6400_20260607
remote source run path: /home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext6400_20260607/theta090
resolved target: same path, no latest alias
local artifact dir: C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext6400_20260607_theta090
status label: exploratory_not_validation
case template: cases\dry_wall\user_1mm_10mm_contact_angle_sweep\pilot_near_wall_equivalent\impact_near_wall_template.xml
remote executed XML: /home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext6400_20260607/theta090/impact_zwall_theta090_dropletsmooth_u008_M0025_W6_ext6400.xml
generated config XML: output/impact_zwall_theta090_dropletsmooth_u008_M0025_W6_ext6400_config_P00_00000000.xml
run.log: /home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext6400_20260607/theta090/run.log
TCLB CSV log: output/impact_zwall_theta090_dropletsmooth_u008_M0025_W6_ext6400_Log_P00_00000000.csv
metrics CSV: analysis/impact_drywall_beta_mass_metrics.csv
summary JSON: analysis/impact_drywall_summary.json
postprocess script: analysis/tclb_impact_drywall_postprocess.py
TCLB return code: 0
postprocess return code: 0
```

Case definition and audit result:

```text
theta: 90
wall_axis: z
wall_side: min
gravity_direction: -z
grid: 96 x 96 x 96
R0: 14
CenterZ: 22
VelocityZ: 0
DropletOnlyVelocity: 2 smooth phase-fraction weighting
DropletVelocityZ: -0.008
GravitationZ: -1e-6
M: 0.025
IntWidth: 6.0
Solve Iterations: 6400
VTK interval: 400
Log interval: 100
Failcheck interval: 100
first_contact_step: 1200
beta_area max: 1.2329201553753413 at step 6400
beta_box max: 1.2142857142857142 at step 3600
late_beta_area_change: 0.010583201411355159 over steps 5600,6000,6400
resting_candidate: false
all-cell phase drift: +5.724% wall/ghost diagnostic only
fluid-only phase drift: -1.1369%
fluid clipped phase drift: -1.1368%
rho drift: -1.0451%
max Mach: 0.014789263592322023
max nonfinite count: 0
wall ghost phase last: 880.6069
limitation: theta=90 only, R0=14 small grid, not run to rest, no grid/time-step sensitivity, no literature comparison, no status promotion; do not launch R0>=32 or contact-angle sweep from this result alone
```

Raw output and copy policy:

```text
raw_output_dir: /home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext6400_20260607/theta090/output
raw_vti_count: 17
raw_pvti_count: 17
remote_run_size: 939M
copy_policy: keep raw VTI/PVTI remote-only; local artifact is curated run files plus metrics, summary JSON, postprocess logs/script, and beta/mass/centroid/morphology figures
morphology note: requested step 1000 did not exist because VTK interval is 400; first contact is step 1200 and event-aligned re-postprocessing now includes analysis/drywall_step_00001200_morphology.png
```

`TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_ext3200_M0025_W6_20260607_theta090` contains:

```text
README.md
run_files\*.xml
run_files\*_config_*.xml
run_files\*_Log_*.csv
run_files\run.log
run_files\manifest*
analysis\*metrics*.csv
analysis\*summary*.json
analysis\postprocess_*.*
analysis\*beta*.png
analysis\*mass*.png
analysis\*centroid*.png
analysis\*morphology*.png
```

Provenance for this coupled M/IntWidth diagnostic:

```text
run_id: tclb_z_wall_rho772_dropletsmooth_u008_ext3200_M0025_W6_20260607
remote source run path: /home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_ext3200_M0025_W6_20260607/theta090
resolved target: same path, no latest alias
local artifact dir: C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_ext3200_M0025_W6_20260607_theta090
status label: exploratory_not_validation
case definition: coupled M=0.025 and IntWidth=6 versus prior ext3200 baseline; R0=14, theta=90, z-wall, smooth DropletOnlyVelocity=2, DropletVelocityZ=-0.008, CenterZ=22, steps=3200
known limitations: theta=90 only, R0=14 small grid, beta_area still changing late, resting_candidate false, no grid/time-step sensitivity, no literature comparison, still fails long-window phase gate; not validation
conservative comparison: this is currently the best phase-drift direction, improving from baseline about 5.02%, M0025 about 4.14%, and W6 about 4.33% to about 3.65%; still above the engineering preference <2% and publication target <=1%
metrics: first_contact_step 1000; max_beta_area 1.1679834016380368 at step 3200; max_beta_box 1.1428571428571428 at step 2800; max_abs_phase_sum_rel_change 0.03651574445062725; max_abs_phase_clipped_sum_rel_change 0.03651595488247271; last rho drift -0.0058700103103808045; max_mach 0.01538668610509541; max_nonfinite_count 0; resting_candidate false; late_beta_area_change 0.03672937850204705
run completion note: run.log reaches 3200 it writing vtk and remote raw counts are complete; postprocess return code was not captured by wrapper, but summary JSON and metrics CSV were produced and a local postprocess_return_code_note.txt records the caveat
raw output: 17 VTI and 17 PVTI, about 939M, remote-only
copy policy: keep raw VTI/PVTI remote-only; local copy is curated run files plus metrics, summary JSON, postprocess logs/note, and beta/mass/centroid/morphology figures
```

Corrected fluid-mass accounting:

```text
summary CSV: C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\ext3200_fluidmass_summary.csv
script: scripts\tclb_impact_drywall_postprocess.py with BOUNDARY-aware fluid_phase_* and wall_phase_* metrics
local corrected directories: analysis_fluidmass under each ext3200 artifact
remote corrected directories: analysis_fluidmass under each corresponding HM570 run
case W5_base: fluid-only phase drift 0.98%, rho drift -0.89%, max Mach 0.01750, resting false
case M0025: fluid-only phase drift 0.75%, rho drift -0.69%, max Mach 0.01800, resting false
case W4: fluid-only phase drift 1.17%, rho drift -1.07%, max Mach 0.02169, resting false
case W6: fluid-only phase drift 0.83%, rho drift -0.76%, max Mach 0.01493, resting false
case M0025_W6: fluid-only phase drift 0.64%, rho drift -0.59%, max Mach 0.01539, resting false
interpretation: all-cell phase_sum includes wetting-wall ghost PhaseF and is diagnostic only; use fluid_phase_* with BOUNDARY==0 for bulk phase-mass gate
status: exploratory_not_validation; no case is run to rest or validation-ready
```

`TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_ext3200_W6_20260607_theta090` contains:

```text
README.md
run_files\*.xml
run_files\*_config_*.xml
run_files\*_Log_*.csv
run_files\run.log
run_files\run_return_code.txt
run_files\manifest*
analysis\*metrics*.csv
analysis\*summary*.json
analysis\postprocess_*.*
analysis\*beta*.png
analysis\*mass*.png
analysis\*centroid*.png
analysis\*morphology*.png
```

Provenance for this IntWidth=6 sensitivity run:

```text
run_id: tclb_z_wall_rho772_dropletsmooth_u008_ext3200_W6_20260607
remote source run path: /home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_ext3200_W6_20260607/theta090
resolved target: same path, no latest alias
local artifact dir: C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_ext3200_W6_20260607_theta090
status label: exploratory_not_validation
case definition: IntWidth=6 only versus prior ext3200 baseline; M=0.05, R0=14, theta=90, z-wall, smooth DropletOnlyVelocity=2, DropletVelocityZ=-0.008, CenterZ=22, steps=3200
known limitations: theta=90 only, R0=14 small grid, beta_area still changing late, resting_candidate false, no grid/time-step sensitivity, no literature comparison, still fails long-window phase gate; not validation
conservative comparison: widening IntWidth from 5 to 6 improves phase drift from the previous about 5.02% ext3200 baseline to about 4.33%, with rho drift about -0.76%; this is useful partial sensitivity evidence but not a gate pass
metrics: first_contact_step 1000; max_beta_area 1.162408270036634 at step 3200; max_beta_box 1.1428571428571428 at step 2800; max_abs_phase_sum_rel_change 0.043349867900737735; max_abs_phase_clipped_sum_rel_change 0.043349867900737735; last rho drift -0.007606532907224442; max_mach 0.014932342334988443; max_nonfinite_count 0; resting_candidate false; late_beta_area_change 0.042697957341174764
raw output: 17 VTI and 17 PVTI, about 939M, remote-only
copy policy: keep raw VTI/PVTI remote-only; local copy is curated run files plus metrics, summary JSON, postprocess logs, and beta/mass/centroid/morphology figures
```

`TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_ext3200_W4_20260607_theta090` contains:

```text
README.md
run_files\*.xml
run_files\*_config_*.xml
run_files\*_Log_*.csv
run_files\run.log
run_files\return_code.txt
run_files\manifest*
analysis\*metrics*.csv
analysis\*summary*.json
analysis\postprocess_*.*
analysis\*beta*.png
analysis\*mass*.png
analysis\*centroid*.png
analysis\*morphology*.png
```

Provenance for this IntWidth-only sensitivity run:

```text
run_id: tclb_z_wall_rho772_dropletsmooth_u008_ext3200_W4_20260607
remote source run path: /home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_ext3200_W4_20260607/theta090
resolved target: same path, no latest alias
local artifact dir: C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_ext3200_W4_20260607_theta090
status label: exploratory_not_validation
case definition: IntWidth=4 only versus prior ext3200 baseline; M=0.05, R0=14, theta=90, z-wall, smooth DropletOnlyVelocity=2, DropletVelocityZ=-0.008, CenterZ=22, steps=3200
known limitations: theta=90 only, R0=14 small grid, beta still changing late, resting_candidate false, no grid/time-step sensitivity, no literature comparison, fails long-window mass and rho gates; not validation
conservative comparison: reducing IntWidth from 5 to 4 worsens phase drift from the previous about 5.02% ext3200 baseline to about 5.92%, and rho drift reaches about -1.07%; this is negative evidence only
metrics: first_contact_step 800; max_beta_area 1.2460227566789277 at step 3200; max_beta_box 1.2857142857142858 at step 3200; max_abs_phase_sum_rel_change 0.059241829442477974; max_abs_phase_clipped_sum_rel_change 0.05924190361447539; last rho drift -0.010662533155103735; max_mach 0.021687991881696882; max_nonfinite_count 0; resting_candidate false; late_beta_area_change 0.053273701916041416
raw output: 17 VTI and 17 PVTI, about 939M, remote-only
copy policy: keep raw VTI/PVTI remote-only; local copy is curated run files plus metrics, summary JSON, postprocess logs, and beta/mass/centroid/morphology figures
```

`TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_ext3200_M0025_20260607_theta090` contains:

```text
README.md
run_files\*.xml
run_files\*_config_*.xml
run_files\*_Log_*.csv
run_files\run.log
run_files\manifest*
analysis_corrected\*metrics*.csv
analysis_corrected\*summary*.json
analysis_corrected\*beta*.png
analysis_corrected\*mass*.png
analysis_corrected\*centroid*.png
analysis_corrected\*morphology*.png
```

Provenance for this M-only sensitivity run:

```text
run_id: tclb_z_wall_rho772_dropletsmooth_u008_ext3200_M0025_20260607
remote source run path: /home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_ext3200_M0025_20260607/theta090
resolved target: same path, no latest alias
local artifact dir: C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_ext3200_M0025_20260607_theta090
status label: exploratory_not_validation
case definition: M=0.025 only versus prior ext3200 baseline; IntWidth=5, R0=14, theta=90, z-wall, smooth DropletOnlyVelocity=2, DropletVelocityZ=-0.008, CenterZ=22, steps=3200
known limitations: theta=90 only, R0=14 small grid, beta still changing late, resting_candidate false, no grid/time-step sensitivity, no literature comparison, still fails long-window mass gate; not validation
conservative comparison: phase drift improves from the previous about 5.02% ext3200 baseline to about 4.14%, but this is exploratory negative/partial evidence only
metrics: first_contact_step 1000; max_beta_area 1.206288070184215 at step 3200; max_beta_box 1.2142857142857142 at step 3000; max_abs_phase_sum_rel_change 0.04137198048360379; max_abs_phase_clipped_sum_rel_change 0.0413728316624303; last rho drift -0.006863765438545194; max_mach 0.01799600332812358; max_nonfinite_count 0; resting_candidate false; late_beta_area_change 0.03830466854617809
raw output: 17 VTI and 17 PVTI, about 939M, remote-only
copy policy: keep raw VTI/PVTI remote-only; local copy is curated run files plus corrected metrics, summary JSON, and beta/mass/centroid/morphology figures
```

`TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_ext3200_20260607_theta090` contains:

```text
README.md
run_files\impact_zwall_theta090_dropletsmooth_u008_ext3200.xml
run_files\impact_zwall_theta090_dropletsmooth_u008_ext3200_config_P00_00000000.xml
run_files\impact_zwall_theta090_dropletsmooth_u008_ext3200_Log_P00_00000000.csv
run_files\run.log
run_files\return_code.txt
analysis\impact_drywall_beta_mass_metrics.csv
analysis\impact_drywall_summary.json
analysis\impact_drywall_beta_t.png
analysis\impact_drywall_mass_velocity.png
analysis\impact_drywall_centroid.png
analysis\drywall_step_*_morphology.png
analysis\postprocess_stdout.json
analysis\postprocess_stderr.log
analysis\postprocess_return_code.txt
```

Provenance for this extended smooth lower-velocity pilot:

```text
remote source run path: /home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_ext3200_20260607/theta090
resolved target: same path, no latest alias
case template: cases\dry_wall\user_1mm_10mm_contact_angle_sweep\pilot_near_wall_equivalent\impact_near_wall_template.xml
executed XML: /home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_ext3200_20260607/theta090/impact_zwall_theta090_dropletsmooth_u008_ext3200.xml
generated config XML: output/impact_zwall_theta090_dropletsmooth_u008_ext3200_config_P00_00000000.xml
run.log: /home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_ext3200_20260607/theta090/run.log
TCLB CSV log: output/impact_zwall_theta090_dropletsmooth_u008_ext3200_Log_P00_00000000.csv
metrics CSV: analysis/impact_drywall_beta_mass_metrics.csv
summary JSON: analysis/impact_drywall_summary.json
postprocess script: scripts\tclb_impact_drywall_postprocess.py with event fields
postprocess command arguments: --radius 14 --wall-axis z --wall-side min --wall-layers 4 --threshold 0.5 --morphology-steps 0,400,800,1200,1600,2000,2400,2800,3200 --rest-beta-tolerance 0.01
status label: exploratory_not_validation
known limitations: R0=14 small grid, theta=90 only, beta still growing, resting_candidate false, phase drift about 5.02%, no literature comparison
metrics: first_contact_step 1000; max beta_area 1.208978 at step 3200; max beta_box 1.214286 at step 3000; max Mach 0.0174967; max phase drift 0.0502163; last rho drift -0.00894497; max nonfinite 0
raw output: 17 VTI and 17 PVTI, about 939M, remote-only
```

`TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_nearwall_20260607_theta090` contains:

```text
README.md
run_files\impact_zwall_theta090_dropletsmooth_u008_nearwall.xml
run_files\impact_zwall_theta090_dropletsmooth_u008_nearwall_config_P00_00000000.xml
run_files\impact_zwall_theta090_dropletsmooth_u008_nearwall_Log_P00_00000000.csv
run_files\run.log
run_files\return_code.txt
analysis\impact_drywall_beta_mass_metrics.csv
analysis\impact_drywall_summary.json
analysis\impact_drywall_beta_t.png
analysis\impact_drywall_mass_velocity.png
analysis\impact_drywall_centroid.png
analysis\drywall_step_*_morphology.png
analysis\postprocess_stdout.json
analysis\postprocess_stderr.log
analysis\postprocess_return_code.txt
```

Provenance for this smooth lower-velocity near-wall pilot:

```text
remote source run path: /home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_nearwall_20260607/theta090
resolved target: same path, no latest alias
case template: cases\dry_wall\user_1mm_10mm_contact_angle_sweep\pilot_near_wall_equivalent\impact_near_wall_template.xml
executed XML: /home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_nearwall_20260607/theta090/impact_zwall_theta090_dropletsmooth_u008_nearwall.xml
generated config XML: output/impact_zwall_theta090_dropletsmooth_u008_nearwall_config_P00_00000000.xml
run.log: /home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_nearwall_20260607/theta090/run.log
TCLB CSV log: output/impact_zwall_theta090_dropletsmooth_u008_nearwall_Log_P00_00000000.csv
metrics CSV: analysis/impact_drywall_beta_mass_metrics.csv
summary JSON: analysis/impact_drywall_summary.json
postprocess script: scripts\tclb_impact_drywall_postprocess.py
postprocess command arguments: --radius 14 --wall-axis z --wall-side min --wall-layers 4 --threshold 0.5 --morphology-steps 0,200,400,600,800,1000,1200,1400,1600
status label: exploratory_not_validation
known limitations: smooth phase-fraction velocity weighting, R0=14 small grid, theta=90 only, 1600-step window not run to rest, no literature comparison
metrics: max beta_area 0.837604; max beta_box 0.857143; max Mach 0.0177074; max phase drift 0.0133634; last rho drift -0.00177417; max nonfinite 0
raw output: 17 VTI and 17 PVTI, about 939M, remote-only
```

`TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_nearwall_20260607_theta090` contains:

```text
README.md
run_files\impact_zwall_theta090_dropletsmooth_nearwall.xml
run_files\impact_zwall_theta090_dropletsmooth_nearwall_config_P00_00000000.xml
run_files\impact_zwall_theta090_dropletsmooth_nearwall_Log_P00_00000000.csv
run_files\run.log
run_files\return_code.txt
analysis\impact_drywall_beta_mass_metrics.csv
analysis\impact_drywall_summary.json
analysis\impact_drywall_beta_t.png
analysis\impact_drywall_mass_velocity.png
analysis\impact_drywall_centroid.png
analysis\drywall_step_*_morphology.png
analysis\postprocess_stdout.json
analysis\postprocess_stderr.log
analysis\postprocess_return_code.txt
```

Provenance for this smooth droplet-velocity near-wall pilot:

```text
remote source run path: /home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_nearwall_20260607/theta090
resolved target: same path, no latest alias
case template: cases\dry_wall\user_1mm_10mm_contact_angle_sweep\pilot_near_wall_equivalent\impact_near_wall_template.xml
executed XML: /home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_nearwall_20260607/theta090/impact_zwall_theta090_dropletsmooth_nearwall.xml
generated config XML: output/impact_zwall_theta090_dropletsmooth_nearwall_config_P00_00000000.xml
run.log: /home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_nearwall_20260607/theta090/run.log
TCLB CSV log: output/impact_zwall_theta090_dropletsmooth_nearwall_Log_P00_00000000.csv
metrics CSV: analysis/impact_drywall_beta_mass_metrics.csv
summary JSON: analysis/impact_drywall_summary.json
postprocess script: scripts\tclb_impact_drywall_postprocess.py
postprocess command arguments: --radius 14 --wall-axis z --wall-side min --wall-layers 4 --threshold 0.5 --morphology-steps 0,200,400,600,800,1000,1200,1400,1600
status label: exploratory_not_validation
known limitations: smooth phase-fraction velocity weighting, R0=14 small grid, theta=90 only, not run to rest, no literature comparison, phase drift about 2.96%
metrics: max beta_area 1.119710; max beta_box 1.142857; max Mach 0.0252173; max phase drift 0.0296472; last rho drift -0.00438227; max nonfinite 0
raw output: 17 VTI and 17 PVTI, about 939M, remote-only
```

`TCLB\artifacts\tclb_z_wall_rho772_dropletonly_nearwall_20260607_theta090` contains:

```text
README.md
run_files\impact_zwall_theta090_dropletonly_nearwall.xml
run_files\impact_zwall_theta090_dropletonly_nearwall_config_P00_00000000.xml
run_files\impact_zwall_theta090_dropletonly_nearwall_Log_P00_00000000.csv
run_files\run.log
run_files\return_code.txt
analysis\impact_drywall_beta_mass_metrics.csv
analysis\impact_drywall_summary.json
analysis\impact_drywall_beta_t.png
analysis\impact_drywall_mass_velocity.png
analysis\impact_drywall_centroid.png
analysis\drywall_step_*_morphology.png
analysis\postprocess_stdout.json
analysis\postprocess_stderr.log
analysis\postprocess_return_code.txt
```

Provenance for this droplet-only near-wall pilot:

```text
remote source run path: /home/yuan/runs/tclb_z_wall_rho772_dropletonly_nearwall_20260607/theta090
resolved target: same path, no latest alias
case template: cases\dry_wall\user_1mm_10mm_contact_angle_sweep\pilot_near_wall_equivalent\impact_near_wall_template.xml
executed XML: /home/yuan/runs/tclb_z_wall_rho772_dropletonly_nearwall_20260607/theta090/impact_zwall_theta090_dropletonly_nearwall.xml
generated config XML: output/impact_zwall_theta090_dropletonly_nearwall_config_P00_00000000.xml
run.log: /home/yuan/runs/tclb_z_wall_rho772_dropletonly_nearwall_20260607/theta090/run.log
TCLB CSV log: output/impact_zwall_theta090_dropletonly_nearwall_Log_P00_00000000.csv
metrics CSV: analysis/impact_drywall_beta_mass_metrics.csv
summary JSON: analysis/impact_drywall_summary.json
postprocess script: scripts\tclb_impact_drywall_postprocess.py
postprocess command arguments: --radius 14 --wall-axis z --wall-side min --wall-layers 4 --threshold 0.5 --morphology-steps 0,200,400,600,800,1000,1200,1400,1600
status label: exploratory_not_validation
known limitations: droplet-only hard phase threshold, R0=14 small grid, theta=90 only, not run to rest, no literature comparison, phase drift about 3.28%
metrics: max beta_area 1.153995; max beta_box 1.142857; max Mach 0.0265875; max phase drift 0.0327978; last rho drift -0.0049454; max nonfinite 0
raw output: 17 VTI and 17 PVTI, about 939M, remote-only
```

`TCLB\artifacts\tclb_z_wall_rho772_lowmach_contact_20260607_theta090` contains:

```text
README.md
run_files\impact_zwall_theta090_lowmach_contact.xml
run_files\impact_zwall_theta090_lowmach_contact_config_P00_00000000.xml
run_files\impact_zwall_theta090_lowmach_contact_Log_P00_00000000.csv
run_files\run.log
run_files\return_code.txt
analysis\impact_drywall_beta_mass_metrics.csv
analysis\impact_drywall_summary.json
analysis\impact_drywall_beta_t.png
analysis\impact_drywall_mass_velocity.png
analysis\impact_drywall_centroid.png
analysis\drywall_step_*_morphology.png
analysis\postprocess_stdout.json
analysis\postprocess_stderr.log
analysis\postprocess_return_code.txt
```

Provenance for this low-Mach z-wall contact pilot:

```text
remote source run path: /home/yuan/runs/tclb_z_wall_rho772_lowmach_contact_20260607/theta090
resolved target: same path, no latest alias
case template: cases\dry_wall\user_1mm_10mm_contact_angle_sweep\pilot_near_wall_equivalent\impact_near_wall_template.xml
executed XML: /home/yuan/runs/tclb_z_wall_rho772_lowmach_contact_20260607/theta090/impact_zwall_theta090_lowmach_contact.xml
generated config XML: output/impact_zwall_theta090_lowmach_contact_config_P00_00000000.xml
run.log: /home/yuan/runs/tclb_z_wall_rho772_lowmach_contact_20260607/theta090/run.log
TCLB CSV log: output/impact_zwall_theta090_lowmach_contact_Log_P00_00000000.csv
metrics CSV: analysis/impact_drywall_beta_mass_metrics.csv
summary JSON: analysis/impact_drywall_summary.json
postprocess script: scripts\tclb_impact_drywall_postprocess.py
postprocess command arguments: --radius 14 --wall-axis z --wall-side min --wall-layers 4 --threshold 0.5 --morphology-steps 0,200,400,600,800,1000,1200
status label: exploratory_not_validation
known limitations: global VelocityZ, R0=14 small grid, theta=90 only, not run to rest, no literature comparison
metrics: max beta_area 0.476827; max beta_box 0.5; max Mach 0.0426445; max phase drift 0.00454951; last rho drift -0.00052298; max nonfinite 0
raw output: remote-only under output/
```

`TCLB\artifacts\tclb_z_wall_rho772_pilot_20260607_theta090` contains:

```text
README.md
run_files\impact_zwall_theta090_smoke.xml
run_files\impact_zwall_theta090_smoke_config_P00_00000000.xml
run_files\impact_zwall_theta090_smoke_Log_P00_00000000.csv
run_files\run.log
run_files\return_code.txt
analysis\impact_drywall_beta_mass_metrics.csv
analysis\impact_drywall_summary.json
analysis\impact_drywall_beta_t.png
analysis\impact_drywall_mass_velocity.png
analysis\impact_drywall_centroid.png
analysis\drywall_step_*_morphology.png
```

Provenance for this z-wall smoke:

```text
remote source run path: /home/yuan/runs/tclb_z_wall_rho772_pilot_20260607/theta090
resolved target: same path, no latest alias
case template: cases\dry_wall\user_1mm_10mm_contact_angle_sweep\pilot_near_wall_equivalent\impact_near_wall_template.xml
executed XML: /home/yuan/runs/tclb_z_wall_rho772_pilot_20260607/theta090/impact_zwall_theta090_smoke.xml
generated config XML: output/impact_zwall_theta090_smoke_config_P00_00000000.xml
run.log: /home/yuan/runs/tclb_z_wall_rho772_pilot_20260607/theta090/run.log
TCLB CSV log: output/impact_zwall_theta090_smoke_Log_P00_00000000.csv
metrics CSV: analysis/impact_drywall_beta_mass_metrics.csv
summary JSON: analysis/impact_drywall_summary.json
postprocess script: scripts\tclb_impact_drywall_postprocess.py
postprocess command arguments: --radius 14 --wall-axis z --wall-side min --wall-layers 4 --threshold 0.5
status label: exploratory_not_validation
known limitations: global VelocityZ, no wall contact by 500 steps, max Mach 0.0979 near 0.1 guard
raw output: 6 VTI and 6 PVTI, about 332M, remote-only
```

`TCLB\artifacts\tclb_impact_rho772_drywall_explore_latest` contains:

```text
README.md
run_files\impact_rho772_drywall_explore.xml
run_files\run.log
run_files\README.txt
run_files\summary.tsv
metrics\impact_drywall_beta_mass_metrics.csv
metrics\impact_drywall_summary.json
figures\impact_drywall_beta_t.png
figures\impact_drywall_mass_velocity.png
figures\impact_drywall_centroid.png
figures\drywall_step_*_morphology.png
```

Do not copy raw VTI dumps locally by default. Keep them remote and record the
remote path.

## References

Local references:

```text
references\papers\wang2023_ijmf_ucl.pdf
references\papers\fei2019_pof_nmrt.pdf
references\papers\wang2024_jfm_main.pdf
references\papers\safi2017_camwa_3d_bubble_preprint.pdf
references\a1_bubbleRise_reference_gap_20260607.md
references\data\a1_bubbleRise_safi2017_reference_template.csv
references\data\a1_bubbleRise_safi2017_digitization_notes.md
references\data\a1_bubbleRise_reference_provenance_20260607.md
references\data\a1_bubbleRise_safi2017_reference.csv
references\data\bonn_3d_rising_bubble_tc1\README.md
references\data\bonn_3d_rising_bubble_tc1\bonn_3d_rising_bubble_tc1_reference.csv
references\data\bonn_3d_rising_bubble_tc1\bonn_3d_rising_bubble_tc1_reference_summary.json
references\data\bonn_3d_rising_bubble_tc1\TC1_centerOfMass.zip
references\data\bonn_3d_rising_bubble_tc1\TC1_riseVelocity.zip
artifacts\tclb_bubbleRise_A1_bonn_compare_20260607\README.md
artifacts\tclb_bubbleRise_A1_bonn_compare_20260607\a1_bonn_comparison_summary.json
artifacts\tclb_bubbleRise_A1_bonn_compare_20260607\read_only_audit_20260607.md
artifacts\tclb_bubbleRise_A1_bonn_compare_20260607\a1_bonn_pointwise_comparison.csv
artifacts\tclb_bubbleRise_A1_bonn_compare_20260607\a1_bonn_interval_velocity_comparison.csv
artifacts\tclb_bubbleRise_A1_bonn_compare_20260607\figures\a1_bonn_center_of_mass_comparison.png
artifacts\tclb_bubbleRise_A1_bonn_compare_20260607\figures\a1_bonn_rise_velocity_comparison.png
references\papers\adelsberger2014_3d_rising_bubble_benchmark.pdf
docs\a1_bubbleRise_acceptance_protocol.md
artifacts\tclb_bubbleRise_A1_acceptance_gate_20260607\README.md
artifacts\tclb_bubbleRise_A1_acceptance_gate_20260607\a1_acceptance_gate_summary.json
artifacts\tclb_bubbleRise_A1_acceptance_gate_20260607\read_only_audit_20260607.md
cases\validation\a1_bubbleRise_grid_time_20260607\tclb_bubbleRise_A1_grid_time_20260607_manifest.json
artifacts\tclb_bubbleRise_A1_grid_time_20260607\README.md
artifacts\tclb_bubbleRise_A1_grid_time_20260607\a1_grid_time_sensitivity_summary.json
artifacts\tclb_bubbleRise_A1_grid_time_20260607\read_only_audit_20260607.md
references\extracted\wang2023_ijmf_d3q27_vlm.md
references\extracted\fei2019_pof_nmrt_vlm.md
references\extracted\wang2024_jfm_main_vlm.md
```

## Canonical Scripts

```text
scripts\tclb_impact_drywall_postprocess.py
scripts\tclb_bubble_rise_postprocess.py
scripts\a1_bubbleRise_independent_digitization.py
scripts\a1_bubbleRise_download_bonn_reference.py
scripts\a1_bubbleRise_compare_bonn_reference.py
scripts\a1_bubbleRise_acceptance_gate.py
scripts\make_a1_bubbleRise_sensitivity_cases.py
scripts\a1_bubbleRise_grid_time_summary.py
scripts\make_tclb_z_wall_pilot_cases.py
scripts\a1_bubbleRise_compare_safi2017.py
scripts\geometric_static_revised_gate_candidate.py
scripts\make_tclb_static_contact_angle_geometric_grid_density_cases.py
scripts\hm570_run_static_contact_angle_grid_density_batch.sh
scripts\tclb_static_contact_angle_arclength_audit.py
scripts\tclb_static_contact_angle_apparent_audit.py
scripts\tclb_static_contact_angle_two_row_audit.py
scripts\tclb_static_contact_angle_grid_density_batch_summary.py
```

Remote copy may be placed inside each run directory as:

```text
/home/yuan/runs/<run_dir>/analyze_impact_drywall_corrected.py
```

## Large Files Policy

Keep remote-only unless needed for a paper figure or debugging:

```text
*.vti
*.pvti
long raw TCLB logs from failed parameter sweeps
intermediate checkpoint dumps
```

Copy locally:

```text
case XML
generated config XML when important
run.log
TCLB CSV log when used for metrics
metrics CSV
summary JSON
publication/sanity figures
README/status marker
```

## Static Contact-Angle Geometric Protocol Artifact

```text
status = exploratory_not_validation
local_artifact = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_geometric_protocol_20260607
remote_protocol_artifact = /home/yuan/runs/tclb_static_contact_angle_geometric_protocol_20260607
source_remote_case = /home/yuan/runs/tclb_static_contact_angle_geometric_calib_20260607/theta045
binary = /home/yuan/src/TCLB/CLB/d3q27_pf_velocity_geometric/main
purpose = freeze geometric static contact-angle protocol and audit existing theta045 output
primary_protocol = phi=0.5, true wall-distance 3-8 lu, x/z mid-slices, left/right average, local_liquid_side_angle_deg
outputs = README.md, geometric_static_protocol_summary.json,
          geometric_theta045_phi_window_sensitivity.csv,
          geometric_theta045_phi_window_sensitivity.png,
          per-phi local tangent CSV/JSON/overlay/window PNG,
          tclb_static_contact_angle_local_tangent_audit.py
raw_policy = raw VTI/PVTI remote-only; local raw count 0
key_result = theta045 phi=0.5 true 3-8 lu local angle 43.2468 deg,
             error -1.7532 deg; 4-10 lu sensitivity trends lower near 42 deg
claim_limit = protocol/audit input only; no validation promotion and no impact sweep authorization
```

## Static Contact-Angle OpenLB-Style Apparent Artifact

```text
status = exploratory_not_validation
local_artifact = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_geometric_openlb_style_apparent_20260608_v2
remote_analysis = /media/yuan/8A0E24070E23EAC1/runs/tclb_static_contact_angle_geometric_grid_density_20260607/analysis_apparent_openlb_style_20260608_v2
source_remote_run = /media/yuan/8A0E24070E23EAC1/runs/tclb_static_contact_angle_geometric_grid_density_20260607
script = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_static_contact_angle_apparent_audit.py
purpose = compare OpenLB-style macroscopic base-width/height spherical-cap
          apparent angle against the existing local 1-8 lu arclength tangent
          for completed geometric static grid-density cases
outputs = openlb_style_apparent_contact_angle_summary.csv,
          openlb_style_apparent_contact_angle_summary.json,
          openlb_vs_local_arclength_comparison.csv,
          openlb_vs_local_arclength_comparison.md,
          apparent_angle_openlb_style_comparison.png,
          apparent_angle_openlb_style_error.png,
          selected theta090 x-mid apparent-angle overlays
raw_policy = raw VTI/PVTI remain remote-only; local raw count 0
claim_limit = evaluation-protocol evidence only; no validation promotion,
              no wetting-model pass/fail conclusion, and no impact sweep
              authorization without read-only audit
```

## Static Contact-Angle Two-Row Interpolation Artifact

```text
status = exploratory_not_validation
local_artifact = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_geometric_two_row_20260608
remote_analysis = /media/yuan/8A0E24070E23EAC1/runs/tclb_static_contact_angle_geometric_grid_density_20260607/analysis_two_row_contact_angle_20260608
source_remote_run = /media/yuan/8A0E24070E23EAC1/runs/tclb_static_contact_angle_geometric_grid_density_20260607
script = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_static_contact_angle_two_row_audit.py
purpose = literature-style near-wall contact-angle evaluation by linear
          interpolation of phi=0.5 interface crossings on two near-wall rows
outputs = two_row_contact_angle_summary.csv,
          two_row_contact_angle_summary.json,
          two_row_vs_openlb_apparent_summary.csv,
          two_row_vs_openlb_apparent_summary.md,
          two_row_contact_angle_comparison.png,
          read_only_audit_20260608.md,
          selected x-mid overlay PNGs for theta045/theta090/theta135
raw_policy = raw VTI/PVTI remain remote-only; local raw count 0
claim_limit = read-only audit accepts validation_candidate for the static
              near-wall contact-angle boundary-condition metric only; not
              validation_passed, not impact validation, not grid convergence,
              not production or publication readiness
```

## Static Contact-Angle Two-Row Phi Sensitivity Artifact

```text
status = validation_candidate support evidence for static near-wall
         contact-angle boundary-condition metric only
local_artifact = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_geometric_two_row_phi_sensitivity_20260608
remote_analysis = /media/yuan/8A0E24070E23EAC1/runs/tclb_static_contact_angle_geometric_grid_density_20260607/analysis_two_row_contact_angle_phi0p45_20260608
                  /media/yuan/8A0E24070E23EAC1/runs/tclb_static_contact_angle_geometric_grid_density_20260607/analysis_two_row_contact_angle_phi0p50_20260608
                  /media/yuan/8A0E24070E23EAC1/runs/tclb_static_contact_angle_geometric_grid_density_20260607/analysis_two_row_contact_angle_phi0p55_20260608
script = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_static_contact_angle_two_row_audit.py
purpose = threshold sensitivity for the preferred two-row 1-2 near-wall metric
outputs = two_row_phi_sensitivity_long.csv,
          two_row_phi_sensitivity_summary.csv,
          two_row_phi_sensitivity_summary.md,
          two_row_phi_sensitivity.png,
          per-threshold summary CSV/JSON/PNG
key_result = max phi0.45-0.55 angle span 0.9010 deg;
             max abs angle error 2.6568 deg
raw_policy = raw VTI/PVTI remain remote-only; local raw count 0
claim_limit = supports static contact-angle validation_candidate only; not
              validation_passed, impact validation, production, or publication
```

## rho772 Dry-Wall Geometric Theta090 Bounded Pilot 20260608

```text
status = exploratory_not_validation
remote_run_dir = /media/yuan/8A0E24070E23EAC1/runs/tclb_z_wall_rho772_geometric_theta090_bounded_u008_M0025_W6_20260608/theta090
local_artifact = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_geometric_theta090_bounded_u008_M0025_W6_20260608_theta090
binary = /home/yuan/src/TCLB/CLB/d3q27_pf_velocity_geometric/main
case_xml = local case.xml and remote case.xml
run_log = local run.log and remote run.log
summary_json = impact_drywall_summary.json
metrics_csv = impact_drywall_beta_mass_metrics.csv
figures = beta, mass/Mach/velocity, centroid, and morphology PNGs
continuation_inputs = continue_ext6400.xml, continue_ext9600.xml
raw_policy = raw VTI/PVTI remain remote-only; local raw count 0
key_result = returncode 0; first contact step 1200; beta_area_max 1.1679834
             at final step 3200; resting_candidate false; fluid-only phase
             drift 0.6386%; rho drift 0.5870%; max Mach 0.0147893;
             nonfinite 0
claim_limit = bounded runtime and health evidence only; not validation,
              not rest, not grid convergence, not production, not publication
```

## rho772 Dry-Wall Geometric Theta090 Checkpoint Pilot 20260608

```text
status = exploratory_not_validation
remote_run_dir = /media/yuan/8A0E24070E23EAC1/runs/tclb_z_wall_rho772_geometric_theta090_bounded_u008_M0025_W6_chk6400_20260608/theta090
local_artifact = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_geometric_theta090_bounded_u008_M0025_W6_chk6400_20260608_theta090
binary = /home/yuan/src/TCLB/CLB/d3q27_pf_velocity_geometric/main
case_xml = case.xml
restart_xml = restart_from_3200.xml, restart_from_6400.xml,
              extend_6400_to_9600.xml
checkpoint_remote_only = output/case_checkpoint_00003200_0.pri,
                         output/case_checkpoint_00006400_0.pri
summary_json = impact_drywall_summary.json
metrics_csv = impact_drywall_beta_mass_metrics.csv
figures = beta, mass/Mach/velocity, centroid, 17 morphology PNGs,
          morphology_montage_0_6400.png
raw_policy = raw VTI/PVTI and checkpoint .pri remain remote-only
key_result = returncode 0; first contact step 1000; beta_area_max 1.2329202;
             beta_area max step 6200; late beta_area_change 0.0052802;
             resting_candidate true under beta tolerance 0.01; fluid-only
             phase drift 1.1369%; rho drift 1.0451%; max Mach 0.0153867;
             nonfinite 0
claim_limit = bounded exploratory checkpoint/restart-readiness and runtime
              evidence only; not validation, grid convergence, production, or
              publication
```

## rho772 Dry-Wall Geometric Theta090 R0=24 Checkpoint Pilot 20260608

```text
status = exploratory_not_validation
remote_run_dir = /media/yuan/8A0E24070E23EAC1/runs/tclb_z_wall_rho772_geometric_theta090_R24_W6_chk6400_20260608/theta090
local_artifact = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_geometric_theta090_R24_W6_chk6400_20260608_theta090
binary = /home/yuan/src/TCLB/CLB/d3q27_pf_velocity_geometric/main
case_xml = run_files\case.xml and remote case.xml
restart_xml = restart_xml\case_restart_00003200.xml,
              restart_xml\case_restart_00006400.xml
checkpoint_remote_only = output/case_checkpoint_00003200_0.pri,
                         output/case_checkpoint_00006400_0.pri
summary_json = analysis\impact_drywall_summary.json
metrics_csv = analysis\impact_drywall_beta_mass_metrics.csv
figures = beta, mass/Mach/velocity, centroid, 17 morphology PNGs,
          morphology_montage_0_6400.png
key_result = returncode 0; first contact step 1600; beta_area_max 1.4322466
             at final step 6400; beta_box_max 1.4166667; late beta_area_change
             0.0124006; resting_candidate false; fluid-only phase drift
             0.7838%; rho drift 0.7504%; max Mach 0.0255851; nonfinite 0
morphology_risk = concentric/ring-like wall footprint and center low-phase/void
                  risk by 4000-6400; do not accept as resting morphology
continuation_12800 = remote XML extend_6400_to_12800.xml; queued under
                     restart_from_6400_ext12800 with queue PID 23238 after the
                     current static R48/W8 theta090 solver finishes
continuation_25600 = chain monitor PID 24016 waits for 12800 returncode 0,
                     creates extend_12800_to_25600.xml from the 12800 checkpoint,
                     then runs restart_from_12800_ext25600 to absolute 25600
raw_policy = raw VTI/PVTI and checkpoint .pri remain remote-only; local raw
             count 0
claim_limit = exploratory restart/runtime and morphology-risk evidence only;
              not validation, grid convergence, production, or publication
```

## rho772 Dry-Wall Geometric Theta090 R0=24 Combined 0-25600 20260608

```text
status = exploratory_not_validation
remote_analysis = /media/yuan/8A0E24070E23EAC1/runs/tclb_z_wall_rho772_geometric_theta090_R24_W6_chk6400_20260608/theta090/analysis_combined_0_25600
local_artifact = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_geometric_theta090_R24_W6_chk6400_20260608_theta090_0_25600
combine_script = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_combine_r24_theta090_0_25600.py
restart_note = combined metrics use absolute steps; restart local step 0 frames
               from 6400-12800 and 12800-25600 are excluded
outputs = combined_0_25600_summary.json,
          combined_0_25600_metrics.csv,
          combined_beta_0_25600.png,
          combined_mass_mach_0_25600.png,
          morphology_montage_0_25600.png,
          segment 6400-12800 and 12800-25600 summary/metrics/run logs
key_result = returncode 0 for 0-6400, 6400-12800, and 12800-25600; first contact
             step 1600; beta_area_max 1.4590056 at absolute step 8800;
             beta_box_max 1.4583333 at absolute step 6800; late window
             24800/25200/25600 beta_area change 0.0070271 and beta_box change
             0.0, so beta-only resting_candidate true; max fluid-only phase
             drift 0.9933%; max rho drift 0.9510%; max Mach 0.0255851;
             max nonfinite 0
morphology_review = center low-phase/void and annular/ring-like wall footprint
                    persist through 25600; beta plateau does not by itself make
                    this a physically accepted resting morphology
raw_policy = raw VTI/PVTI and checkpoint .pri remain remote-only; local raw
             count 0
claim_limit = exploratory_not_validation only; do not promote to validation,
              production, or publication without audit and morphology decision
```

## rho772 Dry-Wall Geometric Theta090 R0=24 Combined 0-65600 20260608

```text
status = exploratory_not_validation
remote_analysis = /media/yuan/8A0E24070E23EAC1/runs/tclb_z_wall_rho772_geometric_theta090_R24_W6_chk6400_20260608/theta090/analysis_combined_0_65600
local_artifact = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_geometric_theta090_R24_W6_chk6400_20260608_theta090_0_65600
combine_script = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_combine_r24_theta090_0_65600.py
restart_note = combined metrics use absolute steps; restart local step 0 frames
               from 6400-12800, 12800-25600, and 25600-65600 are excluded
outputs = combined_0_65600_summary.json,
          combined_0_65600_metrics.csv,
          key_metrics_0_65600.json,
          combined_beta_0_65600.png,
          combined_mass_mach_0_65600.png,
          morphology_montage_0_65600_sampled.png,
          key_morphology_review_0_65600.png,
          key_morphology\abs00000/01600/06400/08800/25600/41600/65600 PNGs,
          segment_25600_65600 summary/metrics/run logs/XML provenance
segment_25600_65600 = /media/yuan/8A0E24070E23EAC1/runs/tclb_z_wall_rho772_geometric_theta090_R24_W6_chk6400_20260608/theta090/restart_from_25600_ext65600
segment_returncode = 0
segment_stderr_note = run.stderr contains "[ 0] error ! Missing comp parameter in LoadBinary";
                      run.log confirms checkpoint load and 40000-step solve
checkpoint_loaded = restart_from_12800_ext25600/output/extend_12800_to_25600_checkpoint_00012800_0.pri
next_restart_xml = restart_from_25600_ext65600/output/extend_25600_to_65600_restart_00040000.xml
key_result = returncode 0 for 0-6400, 6400-12800, 12800-25600, and 25600-65600;
             first contact step 1600; beta_area_max 1.4590056 at absolute step
             8800; beta_box_max 1.5 at absolute step 41600; late window
             64800/65200/65600 beta_area change 0.0015384 and beta_box change
             0.0, so beta-only resting_candidate true; max fluid-only phase
             drift 1.03966%; max rho drift 0.99534%; max Mach 0.0255851;
             max nonfinite 0; last beta_area 1.4376383; last beta_box 1.4583333
morphology_review = annular/ring-like wall footprint and center low-phase/void
                    persist from about 25600 through 65600. The feature appears
                    stabilized, not dissipated. Therefore beta plateau is not
                    sufficient for physical acceptance of the impact result.
raw_policy = raw VTI/PVTI and checkpoint .pri remain remote-only; local raw
             count 0
claim_limit = exploratory_not_validation only; negative morphology evidence
              blocks validation, production, or publication claims for this
              pilot without a model/parameter explanation and read-only audit
```

## rho772 Dry-Wall Geometric Theta090 R0=24 High-We u024 20260608

```text
status = exploratory_not_validation
remote_run_dir = /media/yuan/8A0E24070E23EAC1/runs/tclb_z_wall_rho772_geometric_theta090_R24_W6_u024_chk6400_20260608/theta090
remote_analysis_0_12800 = /media/yuan/8A0E24070E23EAC1/runs/tclb_z_wall_rho772_geometric_theta090_R24_W6_u024_chk6400_20260608/theta090/analysis_combined_0_12800
local_artifact_0_6400 = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_geometric_theta090_R24_W6_u024_chk6400_20260608_theta090
local_artifact_0_12800 = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_geometric_theta090_R24_W6_u024_chk6400_20260608_theta090_0_12800
case_xml = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\dry_wall\user_1mm_10mm_contact_angle_sweep\pilot_near_wall_equivalent\impact_zwall_theta090_R24_W6_u024_chk6400.xml
manifest = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\dry_wall\user_1mm_10mm_contact_angle_sweep\pilot_near_wall_equivalent\tclb_z_wall_rho772_geometric_theta090_R24_W6_u024_chk6400_20260608_manifest.json
binary = /home/yuan/src/TCLB/CLB/d3q27_pf_velocity_geometric/main
velocity = DropletOnlyVelocity=2, DropletVelocityZ=-0.024
weber_note = velocity is 3x the previous u=-0.008 R24_W6 case, so We is 9x
             relative to that exploratory lattice setup; do not map this to
             the original 1 mm / 10 mm low-We physical target
chain = 0->6400 and 6400->12800 both returncode 0; postprocess returncode 0
restart_note = 6400->12800 loaded output/case_checkpoint_00006400_0.pri and
               wrote to restart_from_6400_ext12800/output; restart local step
               0 excluded from combined absolute-time metrics
stderr_note = restart segment contains "Missing comp parameter in LoadBinary";
              run.log confirms checkpoint load and 6400-step solve
next_restart_xml = restart_from_6400_ext12800/output/extend_6400_to_12800_restart_00006400.xml
outputs = combined_0_12800_summary.json,
          combined_0_12800_metrics.csv,
          combined_beta_0_12800.png,
          combined_mass_mach_0_12800.png,
          morphology_montage_0_12800.png,
          0-6400 dense morphology PNGs,
          segment 6400-12800 run logs/summary/metrics/morphology PNGs
key_result = first contact step 400; beta_area_max 1.7970863 at step 4000;
             beta_box_max 1.7916667 at step 3200; last beta_area 1.5635846;
             last beta_box 1.5833333; late 12000/12400/12800 beta-area change
             0.0203664 and beta-box change 0, so not resting; max fluid-only
             phase drift 1.38123%; max rho drift 1.32236%; max Mach 0.0901429;
             nonfinite 0
morphology_review = higher We removes the clean stabilized central hole seen in
                    the low-We 0-65600 case by step 12800, but a grid-like
                    low-phase pattern remains in the footprint and the droplet
                    is still retracting. Continue only with Mach monitoring;
                    do not increase speed further at this lattice scaling.
raw_policy = raw VTI/PVTI/checkpoint .pri remain remote-only; local raw count 0
claim_limit = high-We exploratory probe only; not validation, grid convergence,
              production, publication, or the original 1 mm / 10 mm We target
```

## rho772 Dry-Wall Geometric Theta090 Extension To 12800

```text
status = exploratory_not_validation
remote_run_dir = /media/yuan/8A0E24070E23EAC1/runs/tclb_z_wall_rho772_geometric_theta090_bounded_u008_M0025_W6_chk6400_20260608/theta090/restart_from_6400_ext12800
local_artifact = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_geometric_theta090_bounded_u008_M0025_W6_chk6400_20260608_theta090_ext12800
extension_xml = extend_6400_to_12800.xml
restart_source = output/case_checkpoint_00006400_0.pri from the 0-6400 run
summary_json = combined_0_12800_summary.json,
               impact_drywall_summary_localsteps.json
metrics_csv = combined_0_12800_metrics.csv,
              impact_drywall_beta_mass_metrics_localsteps.csv
figures = combined_beta_0_12800.png,
          combined_mass_mach_0_12800.png,
          morphology_montage_0_12800.png,
          extension morphology PNGs
raw_policy = raw VTI/PVTI and checkpoint .pri remain remote-only
key_result = beta plateaued by 12800 under current beta tolerance; max Mach
             0.0153867; nonfinite 0; reported segment max fluid phase drift
             1.4299%; reported segment max rho drift 1.3145%
claim_limit = exploratory restart/runtime evidence only; central void/bubble
              morphology and mass/rho drift require review before any
              validation or production claim
```

## Li Peisheng 1.3 TCLB Phase-Field Analogue 20260608

```text
status = exploratory_not_validation
literature_pdf = C:\Users\yuanz\Zotero\storage\KC5AQCLL\基于LBM伪势模型下的三维大密度液滴撞击壁面数值研究_李培生.pdf
mineru_copy = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\references\li_peisheng_pseudopotential_droplet_impact_mineru\li_peisheng_pseudopotential_droplet_impact.pdf
mineru_md = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\references\li_peisheng_pseudopotential_droplet_impact_mineru\li_peisheng_pseudopotential_droplet_impact.md
validation_extract = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\references\li_peisheng_pseudopotential_droplet_impact_mineru\model_validation_extraction.md
model_boundary = Li Peisheng uses D3Q15 pseudopotential MRT and G_w/k controls;
                 TCLB route here is D3Q27 phase-field/geometric. These are
                 analogous benchmarks, not formula-equivalent reproduction.
impact_case = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\li_peisheng_re600_we1156_ca90_20260608\li_re600_we1156_ca90_tclb_pf_geometric.xml
impact_remote = /media/yuan/8A0E24070E23EAC1/runs/tclb_li_peisheng_re600_we1156_ca90_R25_U003_20260608/theta090
impact_local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\li_peisheng_re600_we1156_ca90_tclb_pf_geometric_20260608_theta090
impact_key_result = returncode 0; first contact 1200; beta_area_max 1.5367513
                    at step 3200, t*=1.92; beta_box_max 1.54; max fluid-only
                    phase drift 0.9726%; last fluid-only drift -0.5191%;
                    rho drift last -0.4948%; max Mach 0.0986326; nonfinite 0.
                    Beta_max is below Scheller-Bousfield 2.1614,
                    Pasandideh-Fard 2.1955, and Asai 1.8420, so this is not
                    accepted validation evidence.
impact_spread_definition_audit = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\li_peisheng_re600_we1156_ca90_tclb_pf_geometric_20260608_theta090\spread_definition_audit
impact_spread_definition_key = whole-droplet horizontal projection, near-wall
                               footprint layers 1/2/4/8/16, and phi thresholds
                               0.45/0.50/0.55 all give beta_box_max 1.54;
                               beta_area_max range is about 1.515-1.549. Thus
                               the current low beta_max is not explained by
                               the 4-layer footprint definition alone, although
                               the literature D* vs TCLB beta convention still
                               needs to be frozen before validation.
laplace_single_sigma_remote = /media/yuan/8A0E24070E23EAC1/runs/tclb_li_peisheng_laplace_pf_sigma003893_20260608
laplace_single_sigma_local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\li_peisheng_laplace_pf_sigma003893_20260608
laplace_single_sigma_key = R16/R20/R24 returncode 0; postprocess returncode 0;
                           effective sigma slope 0.0063655 for input sigma
                           0.00389273; R2 0.998692; nonfinite 0.
sigma_sweep_remote = /media/yuan/8A0E24070E23EAC1/runs/tclb_li_peisheng_laplace_pf_sigma_sweep_20260608
sigma_sweep_local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\li_peisheng_laplace_pf_sigma_sweep_20260608
sigma_sweep_key = 3 input sigma values x R16/R20/R24, all run/postprocess
                  returncode 0; effective sigma/input ratio about 1.634;
                  effective_sigma vs input_sigma fit slope 1.63368 and
                  R2 0.99999977; nonfinite 0. This supports tunability but
                  exposes an absolute pressure/sigma mapping offset.
static_wetting_remote = /media/yuan/8A0E24070E23EAC1/runs/tclb_li_peisheng_static_wetting_pf_geometric_70_110_20260608
static_wetting_local_cases = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\li_peisheng_re600_we1156_ca90_20260608\static_wetting_pf_geometric_70_110_20260608
static_wetting_status = running as of 2026-06-08 14:36 +08, PID 41034;
                        R32_W6_N160x128x160, theta070/080/090/100/110,
                        200000 steps, raw VTI/PVTI remote-only. No contact
                        angle result yet.
raw_policy = raw VTI/PVTI remain remote-only; local artifacts are curated
             XML/log/CSV/JSON/PNG only.
claim_limit = exploratory_not_validation only; do not call this Li model
              validation until sigma mapping, static wetting mapping, impact
              beta discrepancy, and read-only audit are resolved.
```

## q27 Geometric Phase-Field Calibration Route 20260608

```text
status = exploratory_not_validation
plan = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\docs\q27_geometric_phasefield_calibration_plan_20260608.md
execution_handoff = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\docs\q27_geometric_phasefield_execution_handoff_20260608.md
binary = /home/yuan/src/TCLB/CLB/d3q27_pf_velocity_q27_geometric/main
binary_sha256 = 7b8ad826493e262ecfa713a5ef90a47b61870a7467ce9bfe791dae76434ee066
active_run_root = /media/yuan/8A0E24070E23EAC1/runs
raw_policy = raw VTI/PVTI/checkpoint .pri remain remote-only by default
```

Stage 0 smoke:

```text
remote_root = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_stage0_laplace_smoke_20260608
remote_case_dir = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_stage0_laplace_smoke_20260608/R16
local_case = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\q27_geometric_calibration_20260608\stage0_laplace_smoke\q27_geometric_laplace_smoke_R16.xml
runner = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_start_q27_geometric_stage0_laplace_smoke_20260608.sh
postprocess = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_q27_stage0_smoke_postprocess.py
gate_watcher = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_gate_q27_stage0_then_start_stage1_20260608.sh
queue_pid_20260608_1638 = 47747
gate_pid_20260608_1638 = 51398
state_20260608_1638 = waiting_for_existing_solver; q15 Li static-wetting
                       theta100 is running and theta110 is pending
```

Stage 1 single-sigma Laplace:

```text
remote_root = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_stage1_laplace_single_sigma_20260608
local_cases = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\q27_geometric_calibration_20260608\stage1_laplace_single_sigma
runner = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_start_q27_geometric_laplace_batch_20260608.sh
postprocess = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_laplace_pressure_postprocess_q27.py
gate_watcher = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_gate_q27_stage1_then_start_stage2_20260608.sh
gate_pid_20260608_1638 = 52807
state_20260608_1638 = waiting_for_stage1_summary; Stage 1 has not started
                       because Stage 0 has not run yet
```

Stage 2 sigma sweep:

```text
remote_root = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_stage2_sigma_sweep_20260608
local_cases = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\q27_geometric_calibration_20260608\stage2_sigma_sweep
summary_script = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_q27_sigma_sweep_calibration_summary.py
gate_watcher = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_gate_q27_stage2_then_start_stage3_20260608.sh
remote_gate_watcher = /tmp/hm570_gate_q27_stage2_then_start_stage3_20260608.sh
gate_pid_20260608_1649 = 54622
gate_log = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_stage2_sigma_sweep_20260608/stage2_to_stage3_gate.log
calibration_summary = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_stage2_sigma_sweep_20260608/analysis_sigma_calibration/q27_sigma_sweep_calibration_summary.json
state_20260608_1638 = prepared but not started
state_20260608_1649 = Stage2->Stage3 watcher waiting for Stage2 sigma
                       summaries; no q27 Stage2 run output yet
```

Stage 3 static wetting:

```text
remote_root = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_stage3_static_wetting_70_110_20260608
local_cases = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\q27_geometric_calibration_20260608\stage3_static_wetting_70_110
runner = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_start_q27_geometric_static_wetting_20260608.sh
expected_analysis_dirs = analysis_two_row_contact_angle_phi0p45,
                         analysis_two_row_contact_angle_phi0p50,
                         analysis_two_row_contact_angle_phi0p55
expected_phi_summary_dir = analysis_two_row_phi_sensitivity_summary
expected_phi_summary_json = analysis_two_row_phi_sensitivity_summary/q27_static_wetting_phi_sensitivity_summary.json
phi_summary_script = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_q27_static_wetting_phi_sensitivity_summary.py
remote_phi_summary_script = /tmp/tclb_q27_static_wetting_phi_sensitivity_summary.py
stage3_gate_script = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_q27_stage3_static_wetting_gate.py
remote_stage3_gate_script = /tmp/tclb_q27_stage3_static_wetting_gate.py
expected_stage3_gate_json = analysis_stage3_gate/q27_stage3_static_wetting_gate.json
state_20260608_1638 = prepared but not started
state_20260608_1654 = remote runner updated and bash-n checked to produce
                       phi-threshold sensitivity in the three directories
                       above after the TCLB solves finish
state_20260608_1710 = remote runner and Python postprocessors checked again;
                       two-row audit derives run_id from active run root and
                       Stage3 will write the phi sensitivity summary JSON/CSV
state_20260608_1717 = read-only Stage3 gate script uploaded and py_compile
                       checked; it does not launch Stage4
```

Stage 4 Li impact:

```text
generator = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_q27_geometric_li_impact_case.py
calibrated_generator = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_q27_geometric_li_impact_from_calibration.py
runner = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_start_q27_geometric_li_impact_20260608.sh
remote_generator = /tmp/make_q27_geometric_li_impact_case.py
remote_calibrated_generator = /tmp/make_q27_geometric_li_impact_from_calibration.py
remote_runner = /tmp/hm570_start_q27_geometric_li_impact_20260608.sh
expected_remote_root = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_stage4_li_re600_we1156_theta090_impact_20260608
expected_analysis_dir = theta090/analysis_impact
expected_summary_json = theta090/analysis_impact/impact_drywall_summary.json
expected_metrics_csv = theta090/analysis_impact/impact_drywall_beta_mass_metrics.csv
state_20260608_1638 = generator prepared only; no XML generated because
                       calibrated sigma_input from Stage 2 is required first
state_20260608_1702 = calibrated generator and runner uploaded to HM570 and
                       syntax-checked; not launched
raw_policy = raw VTI/PVTI/checkpoint .pri remain remote-only by default
```

Completed q27 calibrated execution results 20260608:

```text
status = exploratory_not_validation

stage0_local_curated =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\q27_geometric_calibration_20260608\stage0_laplace_smoke_R16
stage1_local_curated =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\q27_geometric_calibration_20260608\stage1_laplace_single_sigma
stage2_local_curated =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\q27_geometric_calibration_20260608\stage2_sigma_sweep
stage3_local_curated =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\q27_geometric_calibration_20260608\stage3_static_wetting_70_110
stage4_local_curated =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\q27_geometric_calibration_20260608\stage4_li_re600_we1156_theta090_impact

stage3_remote =
  /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_stage3_static_wetting_70_110_20260608
stage3_key_files =
  analysis_two_row_phi_sensitivity_summary/q27_static_wetting_phi_sensitivity_summary.json
  analysis_stage3_gate/q27_stage3_static_wetting_gate.json
stage3_key_result =
  70/80/90/100/110 all rc=0; phi=0.45/0.50/0.55 postprocess rc=0;
  read-only gate allowed Stage4 exploratory only; max angle error 1.4417 deg,
  max phi span 0.3700 deg, max spread 0.0860 deg.

stage4_remote =
  /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_stage4_li_re600_we1156_theta090_impact_20260608/theta090
stage4_key_files =
  case.xml
  queue.log
  run.log
  run.returncode
  analysis_impact/impact_drywall_summary.json
  analysis_impact/impact_drywall_beta_mass_metrics.csv
  analysis_impact/impact_drywall_beta_t.png
  analysis_impact/impact_drywall_mass_velocity.png
  analysis_impact/drywall_step_*_morphology.png
stage4_key_result =
  rc=0; postprocess rc=0; first contact step 1200; beta_area_max=1.51135
  at step 3600; beta_box_max=1.50 at step 3200; nonfinite=0;
  max Mach=0.07190; max fluid-only phase drift=0.9672%;
  last fluid-only phase drift=-0.54296%; last rho drift=-0.51756%;
  resting_candidate=false; late beta_box change=-0.08.

stage4_contactline_definition_audit_20260608 =
  script = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_impact_contactline_definition_audit_q27.py
  remote = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_stage4_li_re600_we1156_theta090_impact_20260608/theta090/analysis_contactline_definition_audit_0_12800
  local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\q27_geometric_calibration_20260608\stage4_li_re600_we1156_theta090_impact\analysis_contactline_definition_audit_0_12800
  definitions = wall_intersection_contour beta_chord, near_wall_contour_chord beta_chord,
                current layer_projection beta_box
  key_result = layer_projection beta_box max 1.50 at step 3200;
               wall_intersection/near_wall beta_chord max 1.5094369811
               at step 3600. This does not support blaming the old 4-layer
               footprint projection alone for the maximum-spreading value.

stage4_wetting_contact_event_audit_20260608 =
  script = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_impact_wetting_contact_event_audit.py
  remote = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_stage4_li_re600_we1156_theta090_impact_20260608/theta090/analysis_wetting_contact_event_audit_0_6400
  local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\q27_geometric_calibration_20260608\stage4_li_re600_we1156_theta090_impact\analysis_wetting_contact_event_audit_0_6400
  key_files = wetting_contact_event_metrics.csv,
              wetting_contact_event_summary.json,
              wetting_contact_event_timeseries.png,
              wetting_contact_event_planes.png
  key_result = wall z=0 is BOUNDARY=16 and first fluid z=1 is BOUNDARY=0,
               but PhaseField(z=0)==PhaseField(z=1) exactly at step 3200;
               center gas with outer liquid ring first appears at step 3600
               in both wall-ghost and first-fluid planes. Treat this as a
               dynamic wetting/air-entrapment diagnostic, not validation.

stage4_staircaseimp_ab_20260608 =
  status = exploratory_not_validation
  binary = /home/yuan/src/TCLB/CLB/d3q27_pf_velocity_q27_geometric_staircaseimp/main
  binary_sha256 = 132a8c9fd41abe9275a105800f7fa7764a4ef77042f813cd4a1e3359d14453ef
  options = q27=TRUE, geometric=TRUE, staircaseimp=TRUE, isograd=FALSE, tprec=FALSE
  remote = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_stage4_li_re600_we1156_theta090_impact_staircaseimp_ab_20260608/theta090
  local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\q27_geometric_calibration_20260608\stage4_li_re600_we1156_theta090_impact_staircaseimp_ab
  case_xml = case.xml
  key_files = run.log, run.stderr, manifest.json,
              analysis_impact/impact_drywall_summary.json,
              analysis_impact/impact_drywall_beta_mass_metrics.csv,
              analysis_contactline_definition_audit_0_6400/contactline_definition_audit_summary.json,
              analysis_contactline_definition_audit_0_6400/marked_*_max_step*.png
  key_result = 0-6400 rc=0; postprocess rc=0; first contact step 1200;
               beta_area_max=1.5113542746 at step 3600; beta_box_max=1.50
               at step 3200; max Mach=0.0718988885; nonfinite=0;
               max fluid-only phase drift=0.9671975908%;
               results match the q27 geometric baseline at the reported
               precision for this planar z-wall case.

stage4_mw_sweep_4000_20260609 =
  status = exploratory_not_validation
  script_generator = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_q27_geometric_li_impact_mw_sweep.py
  script_runner = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_run_q27_li_impact_mw_sweep_4000.sh
  script_summary = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\summarize_q27_li_impact_mw_sweep.py
  remote = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_stage4_li_re600_we1156_theta090_impact_mw_sweep_4000_20260608
  local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\q27_geometric_calibration_20260608\stage4_li_re600_we1156_theta090_impact_mw_sweep_4000
  matrix = M 0.01/0.025/0.05 x IntWidth 4/6/8, each to 4000 steps
  key_files = summary/mw_sweep_summary.csv,
              summary/mw_sweep_summary.json,
              summary/mw_sweep_summary.png,
              */analysis_wetting_contact_event_audit/wetting_contact_event_planes.png,
              */analysis_corrected/impact_drywall_summary.json
  key_result = all 9 cases rc=0, postprocess rc=0, wetting audit rc=0;
               `M=0.01` cases had no first-fluid center-gas ring by the audit
               criterion through 4000 steps, while larger M/smaller W produced
               earlier and stronger annular trapped-air behavior. This is a
               dynamic-wetting sensitivity diagnostic only.

physical_scene_10ul_top10mm_theta57_20260609 =
  status = exploratory_not_validation
  generator = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_q27_geometric_10ul_top10mm_theta57_case.py
  runner = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_run_single_q27_impact_with_postprocess.sh
  local_case = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\production_targets\q27_geometric_10ul_top10mm_theta57_pilot
  remote = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_10ul_top10mm_theta57_pilot_20260609/theta057_R25_top10mm_10ul
  local_artifact_expected = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\q27_geometric_10ul_top10mm_theta57_pilot_20260609\theta057_R25_top10mm_10ul
  physical_assumption = 10 uL spherical water droplet; droplet top is 10 mm
                        above wall; theta=57 deg; gravity=-z; released from rest
  key_lattice = R=25 lu, D=50 lu, grid=192x192x224, M=0.01, IntWidth=4,
                sigma_input=0.007214734769446644, estimated first contact
                step about 10964, checkpoint every 5000 steps keep=6
  cleanup_20260610 = raw output/*.vti, output/*.pvti, and checkpoint .pri
                     were deleted recursively from the remote pilot run root
                     after local curated artifacts were confirmed; 153 files /
                     76.53 GiB removed, remote root now about 5.5 MB, remaining
                     raw/checkpoint count 0
  raw_policy = local curated artifacts only; remote raw VTI/PVTI/checkpoint
               files no longer exist for this pilot run root

physical_scene_10ul_top10mm_theta57_hf_from10000_20260609 =
  status = failed_negative_evidence after abs step 14000; valid frames remain
           exploratory_not_validation
  remote = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_10ul_top10mm_theta57_pilot_20260609/theta057_R25_top10mm_10ul_hf_from10000
  local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\q27_geometric_10ul_top10mm_theta57_pilot_20260609\theta057_R25_top10mm_10ul_hf_from10000
  restart_note = started from checkpoint at absolute step 10000; local VTK
                 step + 10000 = absolute step; VTK interval 200
  key_files = analysis_preview_hf_current/drywall_step_00000000_morphology.png
              through drywall_step_00004000_morphology.png,
              montages/theta057_hf_valid_abs10000_14000_montage.png,
              montages/theta057_hf_validity_boundary_abs14000_14200.png
  finite_boundary = local step 4000 / absolute step 14000 was finite; local
                    step 4200 / absolute step 14200 and later had PhaseField
                    all nonfinite on post-run VTI inspection
  raw_policy = local curated artifacts only; remote raw VTI/PVTI/checkpoint
               files no longer exist for this high-frequency restart under the
               cleaned pilot run root

physical_scene_10ul_theta57_nearwall_stability_sweep_20260609 =
  status = exploratory_not_validation
  remote = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_10ul_theta57_nearwall_stability_sweep_20260609
  local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\q27_geometric_10ul_theta57_nearwall_stability_sweep_20260609
  purpose = short near-wall equivalent-impact stability sweep after the
            top-to-wall theta57 run became nonfinite
  completed_cases = theta057_R25_W4_U0p015_nearwall,
                    theta057_R25_W4_U0p0175_nearwall,
                    theta057_R25_W4_U0p02_nearwall,
                    theta057_R25_W6_U0p015_nearwall
  key_result = all four completed cases nonfinite 0 through 12000 steps;
               W6_U0p015 had max Mach 0.0475742, max fluid-only phase drift
               1.6664%, beta_area_max 1.90693, beta_box_max 1.9, and
               resting_candidate true. W4_U0p02 had max Mach 0.0698164 and
               resting_candidate false. W4_U0p015/U0p0175 had Mach near or
               above 0.1.
  cleanup = raw VTI/PVTI/checkpoint files for completed short cases deleted
            after local curated artifacts were copied, freeing about 49 GB
  raw_policy = curated only locally; raw short-sweep fields removed remotely

physical_scene_10ul_theta57_nearwall_long_candidate_20260609 =
  status = exploratory_not_validation
  remote = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_10ul_theta57_long_candidate_20260609/theta057_R25_W6_U0p015_nearwall
  local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\q27_geometric_10ul_theta57_long_candidate_20260609\theta057_R25_W6_U0p015_nearwall
  case = near-wall equivalent 10 uL theta57, R=25 lu, D=50 lu, grid
         192x192x96, M=0.01, IntWidth=6, impact_u_lu=0.015,
         sigma_input=0.0025955222359010464, gravity_lu=-8.208377725711593e-07
  physical_mapping = 10 uL spherical droplet; top-to-wall 10 mm defines
                     impact speed only; dt=2.115356436392676e-6 s/step;
                     60000 steps = 0.126921386 s
  key_files = case.xml, run.log, run.stderr, run.returncode,
              analysis_impact_0_60000/impact_drywall_summary.json,
              analysis_impact_0_60000/impact_drywall_beta_mass_metrics.csv,
              analysis_impact_0_60000/impact_drywall_beta_t.png,
              analysis_impact_0_60000/impact_drywall_mass_velocity.png,
              analysis_impact_0_60000/drywall_step_*_morphology.png,
              analysis_wetting_contact_event_audit_0_60000/wetting_contact_event_summary.json,
              montages/theta057_long_keyframes_0_60000.png,
              montages/theta057_long_all61frames_0_60000.png
  key_result = run rc 0; 61 snapshots through step 60000; nonfinite 0;
               max Mach 0.0382157; max fluid-only phase drift 1.6305%;
               last fluid-only phase drift -1.3380%; beta_area_max 1.89943;
               beta_box_max 1.9; first contact step 1000; late beta_area and
               beta_box changes 0.0; resting_candidate true by beta criterion
  morphology_note = stable image sequence produced, but a small center
                    low-phase/void-like feature persists, so this is not
                    physical validation or publication-ready acceptance
  raw_policy = raw VTI/PVTI/checkpoint .pri remain remote-only; checkpoint at
               step 60000 is available for continuation

physical_scene_10ul_theta57_nearwall_long_hf150_20260609 =
  status = exploratory_not_validation
  remote = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_10ul_theta57_long_hf150_20260609/theta057_R25_W6_U0p015_nearwall
  local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\q27_geometric_10ul_theta57_long_hf150_20260609\theta057_R25_W6_U0p015_nearwall
  local_case = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\production_targets\q27_geometric_10ul_top10mm_theta57_long_hf150
  case = high-frequency rerun of the stable near-wall equivalent 10 uL
         theta57 case, R=25 lu, D=50 lu, grid=192x192x96, M=0.01,
         IntWidth=6, impact_u_lu=0.015, VTK interval=400, 60000 steps
  physical_mapping = 10 uL spherical droplet; top-to-wall 10 mm defines
                     impact speed only; dt=2.115356436392676e-6 s/step;
                     60000 steps = 0.126921386 s; frame interval
                     0.0008461426 s
  key_files = case.xml, manifest.json, run.log, run.stderr, run.returncode,
              analysis_impact_0_60000_hf150/impact_drywall_summary.json,
              analysis_impact_0_60000_hf150/impact_drywall_beta_mass_metrics.csv,
              analysis_impact_0_60000_hf150/impact_drywall_beta_t.png,
              analysis_impact_0_60000_hf150/impact_drywall_mass_velocity.png,
              analysis_impact_0_60000_hf150/drywall_step_*_morphology.png,
              analysis_impact_0_60000_hf150/frame_index.csv,
              theta057_hf151_gallery.html,
              montages/theta057_hf151_allframes_0_60000.png,
              montages/theta057_hf151_early_0_12000_detail.png,
              montages/theta057_hf151_mid_12000_32000_detail.png,
              montages/theta057_hf151_late_32000_60000_detail.png,
              montages/theta057_hf151_max_spread_neighborhood_2400_6400.png
  key_result = run rc 0; 151 real snapshots through step 60000; postprocess
               rc 0; nonfinite 0; max Mach=0.0475741852; max fluid-only
               phase drift=1.6664076209%; last fluid-only phase drift
               -1.3380331296%; beta_area_max=1.9069274081 at step 4400;
               beta_box_max=1.9 at step 4000; first contact step 400;
               late beta_area and beta_box changes 0.0; resting_candidate
               true by beta criterion
  morphology_note = high-frequency image sequence for visual inspection only;
                    this remains near-wall equivalent exploratory evidence,
                    not validation of the full top-to-wall free-fall physics;
                    center low-phase/void-like morphology remains the main
                    unresolved physics/numerics issue
  cleanup = raw output/*.vti, output/*.pvti, and checkpoint .pri were deleted
            from the remote hf150 case after local 151-frame PNG/CSV/JSON
            artifacts were confirmed, reducing the remote case from about
            39 GB to about 18 MB and restoring the DATA500 run disk to about
            110 GB free / 88% used
  raw_policy = local curated artifacts only; remote raw VTI/PVTI/checkpoint
               files no longer exist for this hf150 run

physical_scene_10ul_theta57_official_gravity_26000_20260609 =
  status = exploratory_not_validation
  remote = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_10ul_theta57_official_gravity_26000_20260609/theta057_R25_top10mm_10ul
  local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\q27_geometric_10ul_theta57_official_gravity_26000_20260609\theta057_R25_top10mm_10ul
  local_case = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\production_targets\q27_geometric_10ul_top10mm_theta57_official_gravity_26000
  binary = /home/yuan/src/TCLB/CLB/d3q27_pf_velocity_q27_geometric/main
  binary_sha256 = 7b8ad826493e262ecfa713a5ef90a47b61870a7467ce9bfe791dae76434ee066
  options = q27=TRUE, geometric=TRUE, staircaseimp=FALSE, isograd=FALSE,
            tprec=FALSE, BGK=FALSE, thermo=FALSE
  case = complete gravity-driven 10 uL theta57 fall using official model
         parameters only in XML: VelocityX/Y/Z=0, GravitationZ=-8.208377725711593e-07,
         radAngle=57d, no DropletOnlyVelocity or DropletVelocity* XML params
  audit_limit = current binary source still contains a default-off local
                DropletOnlyVelocity extension branch, so claims must state
                that the case did not enable the extension; it is not a clean
                unmodified-source binary
  physical_mapping = 10 uL spherical water droplet; top-to-wall=10 mm;
                     D=2.673009235 mm; bottom gap=7.326990765 mm;
                     Uimpact=0.37908636 m/s; Re=1135.125; We=5.31912;
                     Bo=0.97025
  lattice = R=25 lu, D=50 lu, grid=192x192x224, CenterZ=162.0550963,
            bottom_gap=137.0550963 lu, M=0.01, IntWidth=6,
            sigma_input=0.0025955222359010464, estimated first contact
            step=18274.0, run steps=26000, VTK interval=200
  key_files = case.xml, manifest.json, run.log, run.stderr, run.returncode,
              analysis_impact_0_26000_official_gravity/impact_drywall_summary.json,
              analysis_impact_0_26000_official_gravity/impact_drywall_beta_mass_metrics.csv,
              analysis_impact_0_26000_official_gravity/impact_drywall_beta_t.png,
              analysis_impact_0_26000_official_gravity/impact_drywall_mass_velocity.png,
              analysis_impact_0_26000_official_gravity/drywall_step_*_morphology.png,
              analysis_impact_0_26000_official_gravity/frame_index.csv,
              analysis_wetting_contact_event_audit_0_26000_official_gravity/wetting_contact_event_summary.json,
              analysis_wetting_contact_event_audit_0_26000_official_gravity/wetting_contact_event_metrics.csv,
              analysis_wetting_contact_event_audit_0_26000_official_gravity/wetting_contact_event_timeseries.png,
              analysis_wetting_contact_event_audit_0_26000_official_gravity/wetting_contact_event_planes.png,
              theta057_official_gravity_gallery.html,
              montages/theta057_official_gravity_all131_0_26000.png,
              montages/theta057_official_gravity_contact_void_17000_22000.png,
              montages/theta057_official_gravity_postcontact_20000_26000.png
  key_result = run rc 0; postprocess rc 0; wetting audit rc 0; 131 snapshots
               through step 26000; nonfinite 0; first contact step=18200;
               beta_area_max=1.8422668999 at step 22000; beta_box_max=1.86
               at step 21800; max Mach=0.0731121004; max fluid-only phase
               drift=1.5162644425%; last fluid-only phase drift=-1.2569129807%;
               late beta_area change=-0.0024855515, late beta_box change=0.0
  center_void_result = center gas with surrounding liquid ring appears in the
                       first fluid layer at step 20400, second fluid layer
                       at step 20800, third fluid layer at step 21200, and
                       wall ghost plane at step 20600. This confirms the
                       center low-phase/void-like morphology is also present
                       in the complete gravity-driven fall, not only in the
                       near-wall equivalent impact setup
  cleanup = raw output/*.vti, output/*.pvti, and checkpoint .pri deleted after
            local curated artifacts were confirmed, reducing the remote case
            from about 80 GB to about 11 MB and restoring DATA500 to about
            110 GB free / 88% used
  raw_policy = local curated artifacts only; remote raw VTI/PVTI/checkpoint
               files no longer exist for this official-gravity run

physical_scene_10ul_theta57_dimple_refinement_R50_probe_20260609 =
  status = failed_negative_evidence
  remote = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_10ul_theta57_dimple_refinement_R50_probe_20260609/theta057_R50_W6_U0p015_nearwall
  local_case = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\production_targets\q27_geometric_10ul_theta57_dimple_refinement_R50_probe_20260609
  case = 10 uL theta57 near-wall equivalent dimple-refinement feasibility
         probe, R=50 lu, D=100 lu, grid=320x320x192, IntWidth=6,
         M=0.01, impact_u_lu=0.015, requested 10 steps with no interval VTK
  result = failed during initialization with `out of memory in cross.cu at
           line 83`; run.log reported mesh 320x320x192 / 19660800 cells and
           cumulative allocation pressure beyond the P100 16GB capacity
  claim_limit = single-card R50/R75/R100 near-wall refinement is not feasible
                on the current HM570 Tesla P100 without multi-GPU decomposition
                or a smaller grid; no physical conclusion
  raw_policy = no useful raw output; probe logs only remain remote

physical_scene_10ul_theta57_dimple_refinement_R40_20260609 =
  status = exploratory_not_validation
  remote = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_10ul_theta57_dimple_refinement_R40_20260609/theta057_R40_W6_U0p015_nearwall
  local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\q27_geometric_10ul_theta57_dimple_refinement_R40_20260609\theta057_R40_W6_U0p015_nearwall
  local_case = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\production_targets\q27_geometric_10ul_theta57_dimple_refinement_R40_20260609
  binary = /home/yuan/src/TCLB/CLB/d3q27_pf_velocity_q27_geometric/main
  case = 10 uL theta57 near-wall equivalent dimple-refinement run,
         R=40 lu, D=80 lu, grid=256x256x160, CenterZ=50 lu,
         near-wall bottom gap=10 lu, M=0.01, IntWidth=6,
         impact_u_lu=0.015, VTK interval=400, 12000 steps
  physical_mapping = D=2.673009235 mm, dx=33.412615 um, IntWidth=6 lu
                     ~=200.476 um, top-to-wall 10 mm only defines the
                     same impact speed U=0.37908636 m/s; Re=1135.125,
                     We=5.31912; dt=1.322097773e-6 s/step and 12000
                     steps = 0.01586517 s
  key_files = case.xml, manifest.json, run.log, run.stderr, run.returncode,
              analysis_impact/impact_drywall_summary.json,
              analysis_impact/impact_drywall_beta_mass_metrics.csv,
              analysis_impact/impact_drywall_beta_t.png,
              analysis_impact/impact_drywall_mass_velocity.png,
              analysis_impact/drywall_step_*_morphology.png,
              analysis_wetting_contact_event_audit/wetting_contact_event_summary.json,
              analysis_wetting_contact_event_audit/wetting_contact_event_metrics.csv,
              analysis_wetting_contact_event_audit/wetting_contact_event_timeseries.png,
              analysis_wetting_contact_event_audit/wetting_contact_event_planes.png,
              analysis_center_void_scale/center_void_scale_summary.json,
              analysis_center_void_scale/center_void_scale_metrics.csv,
              analysis_center_void_scale/center_void_scale_timeseries.png,
              analysis_center_void_scale/center_void_overlay_step_*.png
  key_result = run rc 0; solver duration 791.042426 s = 13.184 min;
               postprocess rc 0; wetting audit rc 0; center-void scale
               audit rc 0; 31 snapshots through step 12000; nonfinite 0;
               max Mach=0.0600791; max fluid-only phase drift=1.10975%;
               beta_area_max=1.9376442; beta_box_max=1.9375
  center_void_result = center gas/low-phase with surrounding liquid ring
                       appears at first fluid layer step 1600, second fluid
                       layer step 3200, third fluid layer step 3600. Using
                       the filtered closed-annular diagnostic, the center
                       low-phase equivalent diameter is about 728 um in the
                       first fluid layer at step 1600, about 502 um in the
                       second fluid layer at step 5600, and about 502 um in
                       the third fluid layer at step 12000. These scales are
                       far larger than the literature order 20-100 um
                       equivalent bubble diameter and about 150 um dimple
                       lateral scale recorded in
                       docs\center_air_entrapment_and_beta_literature_check_20260609.md
  interpretation = R40 improves dx and physical interface thickness relative
                   to R25, but the center low-phase feature remains hundreds
                   of microns wide. This is still a wetting/contact-line,
                   gas-drainage, phase-field-parameter, and grid-resolution
                   diagnostic, not resolved physical entrapped-bubble evidence
  cleanup = after local curated artifacts were confirmed, raw output/*.vti,
            output/*.pvti, and checkpoint .pri were deleted from the remote
            R40 case; remote case size reduced from about 32 GB to about
            7.7 MB and the 8A0E run disk returned to about 98 GB free / 90%
            used
  raw_policy = local curated artifacts only; remote raw VTI/PVTI/checkpoint
               files no longer exist for this R40 run

remote_only_large_files =
  stage4 output/*.vti
  stage4 output/*.pvti
  stage4 output/*checkpoint*.pri, about 1.43 GB each
```

composite_sphere_tail_initializer_patch_20260609 =
  status = exploratory_not_validation
  source = /home/yuan/src/TCLB/models/multiphase/d3q27_pf_velocity
  patched_files = Dynamics.R, Dynamics.c.Rt
  remote_backups = Dynamics.R.pre_composite_tail_20260609,
                   Dynamics.c.Rt.pre_composite_tail_20260609
  binary = /home/yuan/src/TCLB/CLB/d3q27_pf_velocity_q27_geometric/main
  binary_sha256 = 66df9caf87a5b4051ad306ed87456cdfc7b62b6f4c73a86ccd825f03beb77c01
  build_log = /tmp/tclb_build_d3q27_pf_velocity_q27_geometric_composite_tail_20260609.log
  local_artifact = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_composite_tail_patch_20260609
  local_case = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\exploratory\q27_geometric_composite_tail_smoke_20260609
  new_xml_parameters = CompositeDropletTailRadius,
                       CompositeDropletTailLength,
                       CompositeDropletBodyRadius
  behavior = default-off; when tail radius and length are positive, Radius is
             the equal-volume reference sphere radius and the reduced body
             radius is auto-solved unless CompositeDropletBodyRadius is positive
  smoke_remote = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_composite_tail_smoke_20260609/R25_L8_rt5
  smoke_parameters = Radius=25 lu, tail radius=5 lu, tail length=8 lu,
                     body radius auto-solved to 24.9223009877 lu,
                     tail volume fraction 0.0096
  smoke_result = run rc 0; stderr empty; initial and step-1 VTK written;
                 initial phi>0.5 bbox 49x49x57 lu; phase nonfinite 0;
                 max initial Mach 0.0138564
  raw_policy = raw VTI/PVTI remain remote-only; local curated files are case
               XML, run.log/stderr/returncode, summary JSON, midplane PNG,
               patched source copies and diffs

composite_tail_velocity_extension_20260609 =
  status = exploratory_not_validation
  source = /home/yuan/src/TCLB/models/multiphase/d3q27_pf_velocity
  patched_files = Dynamics.R, Dynamics.c.Rt
  remote_backups = Dynamics.R.pre_tail_velocity_20260609,
                   Dynamics.c.Rt.pre_tail_velocity_20260609,
                   Dynamics.R.pre_tail_velocity_uniform_20260609,
                   Dynamics.c.Rt.pre_tail_velocity_uniform_20260609
  binary = /home/yuan/src/TCLB/CLB/d3q27_pf_velocity_q27_geometric/main
  binary_sha256 = 3373620d4c4c8ba952a239bde02030d55ad5b8c5e0b637988bfcd05c111c58ba
  build_log = /tmp/tclb_build_d3q27_pf_velocity_q27_geometric_tail_velocity_uniform_20260609.log
  local_artifact = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_composite_tail_velocity_patch_20260609
  local_case = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\exploratory\q27_geometric_composite_tail_velocity_smoke_20260609
  new_xml_parameters = CompositeDropletTailVelocityMode,
                       CompositeDropletTailVelocityX,
                       CompositeDropletTailVelocityY,
                       CompositeDropletTailVelocityZ
  mode_definition = 0 off; 1 smooth near-uniform extra velocity over the top
                    tail cylinder; 2 smooth axial-ramp extra velocity from
                    root to tail top
  recommended_first_setting = CompositeDropletTailVelocityMode=1,
                              CompositeDropletTailVelocityZ=-0.002 for
                              DropletVelocityZ=-0.008 and R25/L8/rt5
  smoke_remote = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_composite_tail_velocity_smoke_20260609/R25_L8_rt5_tailvz_m0p002_uniform_v2
  smoke_result = run rc 0; stderr empty; max speed 0.00964188 lu/step;
                 max Mach 0.0167002; initial tail centerline Uz about
                 -0.00964 near z=60-62; liquid-weighted kinetic-energy
                 increment versus same smooth base velocity 0.2669%
  raw_policy = raw VTI/PVTI remain remote-only; local curated files are case
               XML, run.log/stderr/returncode, summary JSON, midplane phase/Uz
               PNG, patched source copies and diffs

composite_tail_freefall_negative_evidence_20260609 =
  status = failed_negative_evidence
  purpose = test user-requested top-tail local velocity
            CompositeDropletTailVelocityZ=-0.002 in a 10 uL theta57 top-to-wall
            free-fall case with VTK every 1000 steps and checkpoint every 5000
            steps
  requested_output = VTK Iterations=1000,
                     SaveCheckpoint Iterations=5000
  final_long_remote =
    /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_10ul_theta57_tail_vz_m0p002_long_fail100_20260609/theta057_R25_top10mm_10ul_tailL8_rt5_tailvz_m0p002_long_fail100
  final_long_local_artifact =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\q27_geometric_10ul_theta57_tail_vz_m0p002_long_fail100_20260609\theta057_R25_top10mm_10ul_tailL8_rt5_tailvz_m0p002_long_fail100
  final_long_case =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\exploratory\q27_geometric_10ul_theta57_tail_vz_m0p002_long_fail100_20260609\theta057_R25_top10mm_10ul_tailL8_rt5_tailvz_m0p002_long_fail100.xml
  observed_solver_log = run rc 0, analysis rc 0, wetting audit rc 0,
                        VTI files 0..26000 every 1000,
                        checkpoint/restart files at 5000, 10000, 15000,
                        20000, 25000
  critical_audit = direct VTI read showed PhaseField/P/U/Rho nonfinite in
                   fluid cells from step 100 and entirely nonfinite fluid
                   PhaseField/P from step 500 onward; dry-wall morphology PNGs
                   after step 0 are blank and must not be used as physical
                   droplet-shape evidence
  failed_full_runs =
    /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_10ul_theta57_composite_tail_vz_m0p002_20260609/theta057_R25_top10mm_10ul_tailL8_rt5_tailvz_m0p002
    /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_10ul_theta57_composite_tail_vz_m0p002_rerun_clean_20260609/theta057_R25_top10mm_10ul_tailL8_rt5_tailvz_m0p002_rerun_clean
  cadence_probe_remote =
    /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_10ul_theta57_tail_cadence_probe_20260609
  velocity_probe_remote =
    /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_10ul_theta57_tail_velocity_probe_20260609
  velocity_probe_local_artifact =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\q27_geometric_10ul_theta57_tail_velocity_probe_20260609
  interpretation = step-0 composite initializer is available, but this
                   R25/IntWidth4/M0.01/top10mm/freefall dynamic route is not a
                   usable shape comparison result; use near-wall-equivalent
                   stable settings or retune IntWidth/M/resolution before the
                   next dynamic tail run
  cleanup_20260610 = after local curated artifacts were confirmed, raw
                     output/*.vti, output/*.pvti, and checkpoint .pri were
                     deleted from the final_long run root and velocity_probe
                     run root. Removed final_long 59 files / 35.98 GiB and
                     velocity_probe 69 files / 30.03 GiB; both cleaned roots
                     now have remaining raw/checkpoint count 0 and are about
                     5.2 MB / 1.9 MB respectively.
  raw_policy = local curated artifacts only for final_long and velocity_probe;
               remote raw VTI/PVTI/checkpoint files no longer exist in those
               cleaned roots. The local artifact contains curated logs,
               summaries, and blank postprocess PNGs retained only as negative
               evidence.

composite_tail_stability_control_matrix_20260609 =
  status = failed_negative_evidence
  purpose = finite-field stability control after the invalid composite-tail
            free-fall morphology sequence; isolate sphere-only, tail geometry,
            and TailVelocityZ=-0.002 under W4/U0.025 and W6/U0.015 scaling
  remote =
    /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_10ul_theta57_tail_stability_matrix_20260609
  local =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\q27_geometric_10ul_theta57_tail_stability_matrix_20260609
  local_cases =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\exploratory\q27_geometric_10ul_theta57_tail_stability_matrix_20260609
  report =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\docs\tail_stability_control_analysis_20260609.md
  scripts =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_vti_finiteness_gate.py
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_run_single_q27_impact_with_finiteness_gate.sh
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_q27_geometric_10ul_theta57_tail_stability_matrix.py
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_run_q27_tail_stability_matrix_with_gate.sh
  gate = CSV NaN/Inf plus raw VTI PhaseField,U,P,Rho finite-field check in
         fluid cells; failed gate skips morphology postprocess
  matrix_result = sphere_W4_U0p025 and sphere_W6_U0p015 passed finite-field
                  gates through step 1200; tailgeom_W4_U0p025 and
                  tailvz_m0p002_W4_U0p025 failed at CSV iteration 100 with
                  fluid PhaseField/P/Rho nonfinite count 8183808 and U
                  nonfinite count 24551424; tailgeom_W6_U0p015 and
                  tailvz_m0p002_W6_U0p015 passed finite-field gates but had
                  max Mach about 0.116-0.117, above the conservative ceiling
  interpretation = W4/U0.025 composite-tail failure is driven by the tail
                   geometry plus thin interface/higher lattice scaling, not
                   primarily by TailVelocityZ=-0.002; W6/U0.015 is only a
                   short runtime_sanity direction and needs further Mach
                   control before long morphology comparison
  cleanup = raw VTI/PVTI/checkpoint files were deleted after curated gate
            JSON/CSV, impact summaries for passing cases, XML, and logs were
            copied; remote matrix directory is about 4.5 MB and local curated
            artifact is about 0.38 MB
  raw_policy = no raw VTI/PVTI/checkpoint files retained for this matrix

sashko2025_noncompute_preparation_20260610 =
  status = exploratory_not_validation
  scope = non-compute local file/script/case preparation only; no TCLB solver
          run launched
  project_note =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\docs\sashko2025_noncompute_preparation_20260610.md
  preparation_readme =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\sashko2025_preparation_20260610\README.md
  active_future_remote_root =
    /mnt/8A0E24070E23EAC1/runs for current Sashko Gate A/B execution;
    older /media/yuan/8A0E24070E23EAC1/runs entries are historical unless a
    later mount audit restores that path
  raw_policy = raw VTI/PVTI/checkpoint files remote-only by default;
               local keeps XML/scripts/docs/curated JSON CSV PNG logs only
  gateA_script =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_audit_sashko2025_source_binaries.sh
  gateA_future_remote =
    /mnt/8A0E24070E23EAC1/runs/tclb_sashko2025_gateA_source_binary_audit_20260610
  gateB_local_case_dir =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\sashko2025_sphere_spread_20260610
  gateB_remote_root =
    /mnt/8A0E24070E23EAC1/runs/tclb_sashko2025_sphere_spread_20260610
  gateB_files =
    manifest.json, README.md, sashko2025_sphere_spread_eq57_targets.csv,
    20 XML case files under four wetting-variant directories
  gateB_scripts =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_sashko2025_sphere_spread_cases.py
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_sashko2025_sphere_spread_postprocess.py
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_prepare_sashko2025_sphere_spread.sh
  gateC_local_case_dir =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\sashko2025_capillary_intrusion_20260610
  gateC_remote_root =
    /media/yuan/8A0E24070E23EAC1/runs/tclb_sashko2025_capillary_intrusion_20260610
  gateC_files =
    manifest.json, README.md,
    sashko2025_capillary_intrusion_front_protocol.json,
    64 XML case files under four wetting-variant directories
  gateC_scripts =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_sashko2025_capillary_intrusion_cases.py
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_sashko2025_capillary_intrusion_postprocess.py
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_prepare_sashko2025_capillary_intrusion.sh
  execution_safety = remote runners default MODE=dry-run; they create/update
                     remote run root and append batch logs, then list XMLs;
                     they do not start TCLB unless MODE=run or MODE=wait-run
                     is explicitly set
  staging_policy = local XML/manifest/README/target/protocol files may be
                   staged to the remote run roots for dry-run or later
                   execution; runner/postprocess scripts may be staged to
                   /tmp; raw VTI/PVTI/checkpoints must not be copied into
                   local preparation directories
  gateA_curated_local =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\sashko2025_gateA_source_binary_audit_20260610
  gateA_finding =
    source commit ded67cd768cf7e727bd078af139e3ec7895076e5; Dynamics.R and
    Dynamics.c.Rt modified by default-off exploratory initializer patches;
    initial Gate A audit used nonexistent `_surface` target paths for the
    surface-energy variants. The corrected true TCLB paths are
    surface_q27 -> /home/yuan/src/TCLB/CLB/d3q27_pf_velocity_q27/main and
    surface_q27_staircaseimp ->
    /home/yuan/src/TCLB/CLB/d3q27_pf_velocity_q27_staircaseimp/main.
    Corrected Gate A audit now reports all four required q27 binaries present
    with expected options and SHA evidence, and
    initial_gate_b_theta090_allowed_after_audit=true; geometric_q27 is present
    with the Gate A observed SHA
    3373620d4c4c8ba952a239bde02030d55ad5b8c5e0b637988bfcd05c111c58ba;
    geometric_q27_staircaseimp is present with SHA
    132a8c9fd41abe9275a105800f7fa7764a4ef77042f813cd4a1e3359d14453ef;
    surface_q27 has SHA
    0c19aaf425e5ff605994fdd17f478d9bdc3ef55b3c877658f790879a9e197899;
    surface_q27_staircaseimp has SHA
    672b7612528fba29e7f2efb1f4b511781f2eac03e44de120b661cd3646a340e7;
    optional tprec is still missing;
    local read-only package validation at
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\sashko2025_precompute_package_validation_20260610.json
    reports package_ok=true after excluding the validator file itself from
    scans. Gate A still does not allow validation claims because the source
    tree is modified and this is provenance for exploratory Gate B only.
  gateA_temp_noncompute =
    remote /home/yuan/tmp/tclb_sashko2025_gateA_source_binary_audit_20260610_noncompute;
    local C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\sashko2025_gateA_source_binary_audit_20260610_noncompute;
    result = geometric_q27 and geometric_q27_staircaseimp have matching
             binary paths, SHA256, and options.R evidence; surface_q27 and
             surface_q27_staircaseimp remain missing; raw_vti_pvti_pri_count=0;
             temporary provenance only until the real run root is restored
  gateC_postprocess_note =
    hm570_prepare_sashko2025_capillary_intrusion.sh includes a postprocess
    hook for tclb_sashko2025_capillary_intrusion_postprocess.py in run modes;
    dry-run does not call postprocess
  claim_limit = prepared cases are not validation_passed, production_candidate,
                publication_ready, or planar dry-wall validation

sashko2025_sphere_spread_theta090_partial_20260610 =
  status = exploratory_not_validation
  remote =
    /mnt/8A0E24070E23EAC1/runs/tclb_sashko2025_sphere_spread_20260610
  local =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\sashko2025_sphere_spread_theta090_partial_20260610
  stopped_by_user =
    /mnt/8A0E24070E23EAC1/runs/tclb_sashko2025_sphere_spread_20260610/USER_STOPPED_20260610_1908.txt
  completed_case =
    geometric_q27_staircaseimp/theta090, solver rc 0, original analysis rc 0,
    final VTK step 200000
  interrupted_case =
    geometric_q27/theta090 reached VTK step 160000 of 200000; no final
    run.returncode copied locally
  not_started =
    surface_q27_staircaseimp/theta090 and surface_q27/theta090
  corrected_postprocess =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_sashko2025_sphere_spread_postprocess.py
    now excludes solid cells, selects thresholded liquid connected components
    anchored to the top-side solid-sphere shell, requires extension above
    solid_top_z, records PhaseField/U/P/Rho nonfinite counts, and writes final
    component provenance JSON.
  corrected_analysis_local =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\sashko2025_sphere_spread_theta090_partial_20260610\geometric_q27_staircaseimp_theta090\analysis_sashko2025_sphere_spread_connected_review_v2
  corrected_analysis_remote =
    /mnt/8A0E24070E23EAC1/runs/tclb_sashko2025_sphere_spread_20260610/geometric_q27_staircaseimp/theta090/analysis_sashko2025_sphere_spread_connected_review_v2
  corrected_result =
    metric_valid=false at final step 200000; raw_global_top_z_lu=127.0 is a
    disconnected periodic/top component; the sphere-anchored component does
    not extend above solid_top_z, so selected_top_z_lu/h_star/error are null.
  health =
    max Mach 0.00911368; nonfinite PhaseField/U/P/Rho = 0; LiqTotalPhase
    drift +0.18793%; TotalDensity drift -0.22865%; raw VTI count remote 11.
  raw_policy =
    local curated JSON/CSV/PNG/log/XML only; no raw VTI/PVTI copied locally.
  claim_limit =
    negative morphology/postprocess evidence only; not validation_candidate,
    validation_passed, production_candidate, or publication_ready.

pre2025_sphere_theta030_radAngle011_M0p1_W6_600k_interrupted_20260610 =
  status = exploratory_not_validation
  purpose = interrupted long-run diagnostic for PRE 2025 reduced spherical
            static-wetting theta030, radAngle011, M=0.1, IntWidth=6
  remote =
    /mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_tableII_q27_geometric_theta030_radAngle011_M0p1_W6_600k_vtk50k_20260610
  local =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_radAngle011_M0p1_W6_600k_interrupted_20260610
  local_curated =
    analysis_interrupted_gallery/theta030_interrupted_frame_gallery.png
    analysis_interrupted_gallery/frames/theta030_frame_000000.png
    analysis_interrupted_gallery/frames/theta030_frame_050000.png
    analysis_interrupted_gallery/frames/theta030_frame_100000.png
    analysis_interrupted_gallery/frames/theta030_frame_150000.png
    analysis_interrupted_gallery/frames/theta030_frame_200000.png
    analysis_pre2025_sphere_interrupted/pre2025_sphere_metrics.csv
    analysis_pre2025_sphere_interrupted/pre2025_sphere_summary.json
    source_audit/phi_overshoot_audit.json
    source_audit/boundary_phi_context/boundary_phi_context_summary.csv
    source_audit/boundary_phi_context/boundary_phi_context_audit.json
    source_audit/geometric_wall_formula/geometric_wall_formula_summary.csv
    source_audit/geometric_wall_formula/geometric_wall_formula_audit.json
    source_audit/geometric_wall_angle_sensitivity/geometric_wall_angle_sensitivity_summary.csv
    source_audit/geometric_wall_angle_sensitivity/geometric_wall_angle_sensitivity_audit.json
    source_audit/figures/theta030_wall_phi_fluid_boundary_split.png
    source_audit/figures/theta030_geometric_wall_formula_reproduction.png
    source_audit/figures/theta030_geometric_wall_angle_sensitivity.png
    case.xml
    run.log
    batch_pre2025_sphere.log
  raw_policy = local curated artifacts only; raw VTI/PVTI/PRI remain remote
               and were not copied locally
  observed = 5 VTK frames at 0, 50000, 100000, 150000, 200000; final log
             iteration about 202000; no nonfinite counts in postprocess;
             GPU was idle after stop; related solver/batch processes were gone
  key_metrics = final fit angle about 46.08 deg; H1-H2 error about 28.30%;
                fluid phase drift about -2.79%; rho drift about -2.74%;
                max Mach about 2.42e-4
  source_audit_key_findings =
    fluid PhaseField stays below 1.0 at all written frames, while boundary
    ghost PhaseField reaches 3.278 at step 50000 and has 7192 cells above 1
    by step 200000; the normal geometric wall formula
    PhaseF=pf_f+tan(pi/2-radAngle)*grad_tangent*2h reproduces every audited
    boundary phi>1 cell to about 1e-8, with idx1/idx2 non-boundary neighbors;
    radAngle11 has tan coefficient 5.144554, and formula replay at step 200000
    predicts phi>1 counts of 7192/1568/384/82/32/0 for radAngle
    11/20/30/45/60/75 deg respectively
  claim_limit = interrupted exploratory diagnostic only; not a completed
                600000-step result and not validation evidence

tclb_d3q27_pf_velocity_code_compile_audit_20260610 =
  status = exploratory_not_validation
  report =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\docs\tclb_d3q27_pf_velocity_code_compile_audit_20260610.md
  audited_remote_source =
    /home/yuan/src/TCLB/models/multiphase/d3q27_pf_velocity
  audited_active_binary =
    /home/yuan/src/TCLB/CLB/d3q27_pf_velocity_q27_geometric/main
  active_binary_sha256 =
    3373620d4c4c8ba952a239bde02030d55ad5b8c5e0b637988bfcd05c111c58ba
  key_findings = unsafe PhaseF wall update pattern exists; q27 is enabled for
                 the active PRE sphere q27_geometric binary; PhaseField_l/h
                 were not set to -1/+1 in the audited PRE case; current source
                 tree and generated binaries include local default-off
                 initializer patches, so they are not clean official-source
                 builds
  claim_limit = code/compile audit only; no validation promotion

pre2025_sphere_phi_overshoot_solution_plan_audit_20260610 =
  status = exploratory_not_validation
  report =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\docs\pre2025_sphere_phi_overshoot_solution_plan_audit_20260610.md
  script =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\audit_pre2025_sphere_phi_overshoot.py
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\audit_pre2025_sphere_boundary_phi_context.py
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\audit_pre2025_sphere_geometric_wall_formula.py
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\audit_pre2025_sphere_geometric_wall_angle_sensitivity.py
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\plot_pre2025_sphere_wall_phi_diagnostics.py
  local_json =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_radAngle011_M0p1_W6_600k_interrupted_20260610\source_audit\phi_overshoot_audit.json
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_radAngle011_M0p1_W6_600k_interrupted_20260610\source_audit\boundary_phi_context\boundary_phi_context_audit.json
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_radAngle011_M0p1_W6_600k_interrupted_20260610\source_audit\geometric_wall_formula\geometric_wall_formula_audit.json
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_radAngle011_M0p1_W6_600k_interrupted_20260610\source_audit\geometric_wall_angle_sensitivity\geometric_wall_angle_sensitivity_audit.json
  remote_json =
    /mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_tableII_q27_geometric_theta030_radAngle011_M0p1_W6_600k_vtk50k_20260610/theta030/analysis_pre2025_sphere_interrupted/phi_overshoot_audit.json
    /mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_tableII_q27_geometric_theta030_radAngle011_M0p1_W6_600k_vtk50k_20260610/theta030/analysis_geometric_wall_formula/geometric_wall_formula_audit.json
    /mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_tableII_q27_geometric_theta030_radAngle011_M0p1_W6_600k_vtk50k_20260610/theta030/analysis_geometric_wall_angle_sensitivity/geometric_wall_angle_sensitivity_audit.json
  key_findings = global phi_max > 1 is entirely boundary/wall ghost phase in
                 the audited VTI frames; fluid phi max remains below 1;
                 built-in sphere initializer includes the 0.5 factor; current
                 XML correctly sets radAngle, not a wrong ContactAngle or
                 WettingAngle parameter; the geometric wall formula itself
                 reproduces the boundary overrun to roundoff accuracy, so the
                 direct source is the normal geometric branch's low-angle
                 tangent-gradient extrapolation, not the surface-energy
                 fallback path for these cells
  next_gate = clean-source compile lane, no-code flat/periodic/curved
              diagnostics, then wall-phase instrumentation before any
              physics fix or long run
  claim_limit = plan and audit only; no validation or publication promotion

wall_geom_diag_clean_lane_stage2_20260610 =
  status = runtime_sanity
  report =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\docs\wall_geom_diag_clean_lane_stage2_20260610.md
  clean_source =
    /home/yuan/src/TCLB_clean_wall_diag_20260610
  base_commit =
    ded67cd768cf7e727bd078af139e3ec7895076e5
  baseline_binary_sha256 =
    9f546d208e6e8a117ca0873072e8d03b09bd5ab6f13c9de569e60080df49dd4e
  instrumented_binary =
    /home/yuan/src/TCLB_clean_wall_diag_20260610/CLB/d3q27_pf_velocity_q27_geometric/main
  instrumented_binary_sha256 =
    20be154bff84c1c4e29a37b7c422d85c279364076254ae2fb6caf68cf1f5573d
  provenance_remote =
    /mnt/8A0E24070E23EAC1/runs/tclb_wall_diag_provenance_20260610
  run_roots =
    /mnt/8A0E24070E23EAC1/runs/tclb_wall_geom_diag_flat_curved_20260610
    /mnt/8A0E24070E23EAC1/runs/tclb_wall_geom_diag_flat_curved_rad011_20260610
  local_artifacts =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\wall_geom_diag_flat_curved_20260610
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\wall_geom_diag_flat_curved_rad011_20260610
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\wall_geom_diag_summary_20260610
  scripts =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_wall_geom_diag_short_cases.py
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\wall_geom_diag_postprocess.py
  key_findings =
    short flat/curved diagnostics all had solver and postprocess rc=0,
    nonfinite=0, max Mach below 3e-4; radAngle011 produced immediate
    WallPhasePred>1 in the normal geometric path on both flat and curved
    walls, with curved theta011 step-50 pred_max 1.433943 and flat theta011
    pred_max 1.239433; theta030 curved short run did not overrun at step 50
    while flat theta030 had a tiny overrun; theta090 results are near bounded
  raw_policy =
    local curated CSV/JSON/PNG/log/XML only; raw VTI/PVTI remain remote
  claim_limit =
    runtime_sanity and formula-path diagnostics only; not validation evidence

wall_geom_bounded_diag_stage3_20260610 =
  status = runtime_sanity
  report =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\docs\wall_geom_bounded_diag_stage3_20260610.md
  bounded_source =
    /home/yuan/src/TCLB_clean_wall_bounded_diag_20260610
  bounded_binary =
    /home/yuan/src/TCLB_clean_wall_bounded_diag_20260610/CLB/d3q27_pf_velocity_q27_geometric/main
  bounded_binary_sha256 =
    2b950ce317784beed5b403944e9db8f6a9bd415b3c5acddb962c86fb2ea7c3e5
  provenance_remote =
    /mnt/8A0E24070E23EAC1/runs/tclb_wall_bounded_diag_provenance_20260610
  run_roots =
    /mnt/8A0E24070E23EAC1/runs/tclb_wall_geom_diag_bounded_flat_curved_20260610
    /mnt/8A0E24070E23EAC1/runs/tclb_wall_geom_diag_baseline_rad011_1000_20260610
    /mnt/8A0E24070E23EAC1/runs/tclb_wall_geom_diag_bounded_rad011_1000_20260610
    /mnt/8A0E24070E23EAC1/runs/tclb_wall_geom_diag_baseline_curved_rad011_10k_20260610
    /mnt/8A0E24070E23EAC1/runs/tclb_wall_geom_diag_bounded_curved_rad011_10k_20260610
  local_artifacts =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\wall_geom_diag_bounded_flat_curved_20260610
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\wall_geom_diag_bounded_summary_20260610
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\wall_geom_diag_baseline_rad011_1000_20260610
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\wall_geom_diag_bounded_rad011_1000_20260610
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\wall_geom_diag_rad011_1000_summary_20260610
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\wall_geom_diag_baseline_curved_rad011_10k_20260610
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\wall_geom_diag_bounded_curved_rad011_10k_20260610
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\wall_geom_diag_curved_rad011_10k_summary_20260610
  scripts =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_wall_geom_diag_short_cases.py
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\wall_geom_diag_postprocess.py
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\compare_wall_geom_diag_bounded.py
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\plot_wall_geom_rad011_1000_evolution.py
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\plot_wall_geom_curved_rad011_10k_evolution.py
  key_findings =
    diagnostic-only wall clamp suppresses actual wall PhaseField>1 while
    preserving raw WallPhasePred overrun; 50-step flat/curved bounded cases,
    1000-step radAngle011 baseline/bounded cases, and 10000-step curved
    radAngle011 baseline/bounded cases all completed with rc=0 and nonfinite=0;
    at curved radAngle011 step10000, baseline actual wall phi>1 count is 558
    with phase_wall_max 1.43299, while bounded actual wall phi>1 is 0 and raw
    WallPhasePred remains overbounded with max 1.46184; fluid phi>1 is 0 and
    max Mach is below 4.6e-4
  raw_policy =
    local curated CSV/JSON/PNG/log/XML only; raw VTI/PVTI remain remote
  claim_limit =
    runtime_sanity localization control only; bounded clamp is not a physical
    wetting fix and must not be reported as validation or production

wall_geom_profile_diag_stage4_20260610 =
  status = runtime_sanity / exploratory_not_validation
  report =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\docs\wall_geom_profile_diag_stage4_20260610.md
  profile_source =
    /home/yuan/src/TCLB_clean_wall_profile_diag_20260610
  profile_binary =
    /home/yuan/src/TCLB_clean_wall_profile_diag_20260610/CLB/d3q27_pf_velocity_q27_geometric/main
  profile_binary_sha256 =
    59e03a6233744f00189b6241551fab30d1a53867a90bee582295f9666899159a
  provenance_remote =
    /mnt/8A0E24070E23EAC1/runs/tclb_wall_profile_diag_provenance_20260610
  run_roots =
    /mnt/8A0E24070E23EAC1/runs/tclb_wall_geom_diag_profile_flat_curved_20260610
    /mnt/8A0E24070E23EAC1/runs/tclb_wall_geom_diag_profile_rad011_1000_20260610
    /mnt/8A0E24070E23EAC1/runs/tclb_wall_geom_diag_profile_curved_rad011_10k_20260610
    /mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_50k_20260610
    /mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_200k_20260610
  local_artifacts =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\wall_geom_diag_profile_flat_curved_20260610
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\wall_geom_diag_profile_rad011_1000_20260610
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\wall_geom_diag_profile_curved_rad011_10k_20260610
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\wall_geom_diag_profile_summary_20260610
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_50k_20260610
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_200k_20260610
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_profile_candidate_summary_20260610
  scripts =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_wall_geom_diag_short_cases.py
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\wall_geom_diag_postprocess.py
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\compare_wall_geom_diag_profile.py
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\plot_wall_geom_profile_evolution.py
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_pre2025_sphere_tableII_cases.py
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\pre2025_sphere_wall_diag_postprocess.py
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\pre2025_sphere_single_case_frame_gallery.py
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\compare_pre2025_sphere_profile_candidate.py
  key_findings =
    profile candidate replaces the normal geometric wall write with the
    quadratic profile/surface-energy-like reconstruction while preserving raw
    WallPhasePred diagnostics; flat/curved health gates completed rc=0 with
    nonfinite=0; curved radAngle011 10k kept actual wall and fluid phi>1 counts
    at 0 while raw WallPhasePred stayed overbounded; theta030 sphere profile
    M0.1 W6 200k completed rc/postrc/wall-postrc=0 and no NaN stop, with final
    global phase_max 1.00000043, fluid phase/rho drift -1.53%/-1.51%, and max
    Mach 5.72e-4, but morphology worsened relative to earlier controls:
    H1-H2 error 39.45% and fitted angle 54.87 deg. Final raw WallPhasePred>1
    count was 4478, while actual wall/fluid phi>1 counts were only 52/132 at
    about 1e-7 overrun magnitude.
  raw_policy =
    local curated CSV/JSON/PNG/log/XML only; local raw .vti/.pvti/.pri count 0
  claim_limit =
    runtime_sanity and exploratory_not_validation only; do not continue this
    exact profile formula as a calibration solution or call it validation

wall_geom_profile_theta030_600k_extension_20260610 =
  status = exploratory_not_validation
  report =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\docs\wall_geom_profile_600k_extension_20260610.md
  run_root =
    /mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_600k_20260610
  local_artifacts =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_600k_20260610
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_600k_live_20260610
  case =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_600k_20260610
  runner =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_run_pre2025_sphere_profile_600k_20260610.sh
  binary =
    /home/yuan/src/TCLB_clean_wall_profile_diag_20260610/CLB/d3q27_pf_velocity_q27_geometric/main
  binary_sha256 =
    59e03a6233744f00189b6241551fab30d1a53867a90bee582295f9666899159a
  key_findings =
    theta030 profile radAngle011/M0.1/W6 extension completed 600000 steps with
    solver, PRE postprocess, wall diagnostic, and morphology return codes all
    0; nonfinite stayed 0. The 200k point reproduced the earlier profile run
    exactly. H1-H2 error improved from 39.45% at 200k to a best 1.63% at
    450k, then worsened to 9.47% at 600k while the fitted angle continued to
    29.56 deg. Fluid phase/rho drift reached -2.82%/-2.77% by 600k. Raw
    WallPhasePred remained overbounded with final max 1.6346 and 7074 wall
    cells above 1, while actual wall/fluid phi>1 counts were 0 from 350k to
    600k.
  raw_policy =
    remote raw VTI/PVTI retained on HM570; local curated artifact excludes
    .vti/.pvti/.pri and local raw count is 0
  claim_limit =
    exploratory trend test only; not validation, not calibration acceptance,
    and not publication evidence

pre2025_sphere_theta030_profile_liftZ32_400k_20260610 =
  status = exploratory_not_validation
  purpose =
    geometry isolation for the bottom-film/underside flow failure observed in
    the profile theta030 600k extension
  run_root =
    /mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_liftZ32_400k_20260610
  case =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_liftZ32_400k_20260610
  runner =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_run_pre2025_sphere_profile_liftZ32_400k_20260610.sh
  binary =
    /home/yuan/src/TCLB_clean_wall_profile_diag_20260610/CLB/d3q27_pf_velocity_q27_geometric/main
  binary_sha256 =
    59e03a6233744f00189b6241551fab30d1a53867a90bee582295f9666899159a
  report =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\docs\pre2025_sphere_theta030_profile_liftZ32_geometry_audit_20260610.md
  local_artifacts =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_profile_radAngle011_M0p1_W6_liftZ32_400k_20260610
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\pre2025_sphere_theta030_profile_z24_vs_liftZ32_compare_20260610
  geometry_delta =
    solid sphere center changed from z=24 to z=32; initial droplet center
    changed from z=72 to z=80; all physical parameters retained
  execution =
    started 2026-06-11T00:15:40+08:00, solver ended 2026-06-11T00:48:40+08:00,
    batch ended 2026-06-11T00:50:36+08:00; solver, PRE postprocess, wall diag,
    morphology, and surface-film audit rc all 0; run.done present; stderr empty;
    nonfinite/error scan negative
  key_findings =
    compared with the original z=24 touching-bottom geometry at 400k, liftZ32
    preserved the global relaxation path and slightly improved H1-H2 error
    (5.13% versus 6.39%) while reducing z-min outside-sphere liquid fraction
    from 0.1508 to 0.0406 and z-min liquid sum from 4866.8 to 1320.1; geometry
    contamination is strongly supported but residual lower-hemisphere film
    remains
  raw_policy =
    remote raw VTI/PVTI retained on HM570; local curated artifact excludes
    .vti/.pvti/.pri and local raw count is 0
  claim_limit =
    geometry-isolation exploratory control only; not validation or calibration
