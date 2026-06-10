# TCLB Path Index

Date: 2026-06-07

Purpose: single path registry for new conversations and handoff. Read this
before searching old chats or D3Q27 artifacts.

## 1. Remote Execution Hosts

| Host | SSH alias | Role | Notes |
|---|---|---|---|
| HM570 | `HM570` | primary TCLB GPU execution host | Ubuntu Linux, Tesla P100-PCIE-16GB |

HM570 storage note, 2026-06-07:

```text
compatibility_run_root = /home/yuan/runs -> /media/yuan/DATA500/runs
physical_run_root = /media/yuan/DATA500/runs
mount = /media/yuan/DATA500
filesystem = ntfs3 on /dev/sdc1
capacity_check_20260607 = 466G total, 49G used, 418G available, 11% used
health_check_20260607 = small write/read/delete under /media/yuan/DATA500/runs
                        passed as user yuan
path_state_20260607 = /home/yuan/runs symlink recreated and representative
                      run.log under geometric theta090 was readable
new_case_generation = local generators now default to /media/yuan/DATA500/runs
                      for future cases
old_failed_candidate = /mnt/data500/yuan/runs was abandoned after receiver-side
                       Input/output error and HM570 freeze
safe_helper = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_migrate_runs_to_data500.py
```

HM570 storage update, 2026-06-08:

```text
current_physical_run_root = /media/yuan/8A0E24070E23EAC1/runs
current_mount = /media/yuan/8A0E24070E23EAC1
capacity_check_20260608 = 894G total, 560G used, 334G available, 63% used
health_check_20260608 = small write/read/delete under the current run root
                        passed as user yuan
reason = DATA500 became unstable during the static grid-density batch; copied
         partial data had stale XML output paths and incomplete/corrupted
         R24 theta045 log, so active XMLs were retargeted and the batch was
         restarted from the current run root
DATA500_status = historical/curated evidence path only until separate disk
                 health audit; do not write new runs there by default
```

HM570 storage observation, 2026-06-10:

```text
current_mount_status = /media/yuan/8A0E24070E23EAC1 and /media/yuan/DATA500
                       were not mounted/visible to user yuan during the
                       17:39 +0800 read-only check
/home/yuan/runs = stale symlink to /media/yuan/DATA500/runs while DATA500 was
                  absent
temporary_noncompute_artifacts = /home/yuan/tmp is acceptable only for small
                                read-only provenance artifacts, not solver
                                output or raw VTI/PVTI/checkpoint data
required_before_next_run = restore/check active external run root and update
                           this index before launching any build or TCLB run
```

HM570 storage update, 2026-06-10 19:55 +0800:

```text
current_physical_run_root = /mnt/8A0E24070E23EAC1/runs
current_mount = /mnt/8A0E24070E23EAC1
capacity_check_20260610_1955 = 894G total, 787G used, 107G available, 89% used
canonical_new_sashko_root = /mnt/8A0E24070E23EAC1/runs
note = /media/yuan/8A0E24070E23EAC1 entries are historical or stale for
       current Sashko Gate A/B execution unless a later mount audit restores
       that path. Do not generate new Sashko XML under /media by default.
```

## 2. Remote TCLB Source Trees

| Field | Value |
|---|---|
| host | HM570 |
| ssh_alias | `HM570` |
| source_root | `/home/yuan/src/TCLB` |
| git_remote | `https://github.com/CFD-GO/TCLB.git` |
| commit | `ded67cd768cf7e727bd078af139e3ec7895076e5` |
| model_dir | `/home/yuan/src/TCLB/models/multiphase/d3q27_pf_velocity` |
| example_dir | `/home/yuan/src/TCLB/example/multiphase/d3q27_pf_velocity` |
| claim_scope | runtime/validation candidate, not Wang 2023 equivalence |

Local HM570 source patch:

```text
files:
  /home/yuan/src/TCLB/models/multiphase/d3q27_pf_velocity/Dynamics.R
  /home/yuan/src/TCLB/models/multiphase/d3q27_pf_velocity/Dynamics.c.Rt
backup:
  *.pre_droplet_velocity_20260607
purpose:
  optional DropletOnlyVelocity and DropletVelocityX/Y/Z settings for
  exploratory droplet-only initialization; mode 1 is hard phase mask and
  mode 2 is smooth phase-fraction velocity weighting
status:
  exploratory_not_validation; patch changes initialization only and does not
  establish validation or Wang 2023 equivalence
```

## 3. Remote Built Binaries

| Model | Binary | GPU arch |
|---|---|---|
| `d3q27_pf_velocity` | `/home/yuan/src/TCLB/CLB/d3q27_pf_velocity/main` | `sm_60` |
| `d3q27_pf_velocity_geometric` | `/home/yuan/src/TCLB/CLB/d3q27_pf_velocity_geometric/main` | `sm_60`; independent build completed 2026-06-07; `geometric=TRUE`, `staircaseimp/isograd/tprec=FALSE`; original `d3q27_pf_velocity/main` remained `geometric=FALSE` |
| `d3q27_pf_velocity_geometric_staircaseimp` | `/home/yuan/src/TCLB/CLB/d3q27_pf_velocity_geometric_staircaseimp/main` | `sm_60`; independent build completed 2026-06-07; `geometric=TRUE`, `staircaseimp=TRUE`, `isograd/tprec=FALSE`; original and geometric-only binaries remained separate |
| `d3q27_pf_velocity_q27_geometric` | `/home/yuan/src/TCLB/CLB/d3q27_pf_velocity_q27_geometric/main` | `sm_60`; independent build completed 2026-06-08 and later rebuilt after default-off exploratory initializer extensions; `q27=TRUE`, `geometric=TRUE`, `BGK/thermo/staircaseimp/isograd/tprec=FALSE`; current Gate A 20260610 observed SHA256 `3373620d4c4c8ba952a239bde02030d55ad5b8c5e0b637988bfcd05c111c58ba`; original calibration-route SHA256 `7b8ad826493e262ecfa713a5ef90a47b61870a7467ce9bfe791dae76434ee066`; this is not a clean official-source binary unless a separate clean rebuild/audit proves it |
| `d3q27_pf_velocity_q27_geometric_staircaseimp` | `/home/yuan/src/TCLB/CLB/d3q27_pf_velocity_q27_geometric_staircaseimp/main` | `sm_60`; independent build completed 2026-06-08 for planar-wall A/B only; `q27=TRUE`, `geometric=TRUE`, `staircaseimp=TRUE`, `BGK/thermo/isograd/tprec=FALSE`; SHA256 `132a8c9fd41abe9275a105800f7fa7764a4ef77042f813cd4a1e3359d14453ef`; build log `/tmp/tclb_build_d3q27_pf_velocity_q27_geometric_staircaseimp_20260608.log`; status `exploratory_not_validation` |
| `d3q27_pf_velocity_q27` | `/home/yuan/src/TCLB/CLB/d3q27_pf_velocity_q27/main` | Real TCLB surface-energy q27 target for Sashko `surface_q27`; `q27=TRUE`, `geometric=FALSE`, `staircaseimp=FALSE`; build/audit attempted 2026-06-10 but HM570 became unreachable before completion could be confirmed |
| `d3q27_pf_velocity_q27_staircaseimp` | `/home/yuan/src/TCLB/CLB/d3q27_pf_velocity_q27_staircaseimp/main` | Real TCLB surface-energy q27 staircase target for Sashko `surface_q27_staircaseimp`; `q27=TRUE`, `geometric=FALSE`, `staircaseimp=TRUE`; build/audit attempted 2026-06-10 but HM570 became unreachable before completion could be confirmed |
| `d3q27_pf_velocity_q27_geometric_staircaseimp_tprec` | `/home/yuan/src/TCLB/CLB/d3q27_pf_velocity_q27_geometric_staircaseimp_tprec/main` | optional Gate A 20260610 tprec binary; missing at expected path during read-only audit; not required for the initial four-variant matrix unless explicitly added |

Run pattern:

```bash
cd /home/yuan/src/TCLB
export PATH=/usr/local/cuda-12.6/bin:$PATH
export OMPI_MCA_plm_rsh_agent=/usr/bin/ssh
CLB/d3q27_pf_velocity/main /media/yuan/8A0E24070E23EAC1/runs/<run_dir>/<case>.xml
```

`/home/yuan/runs` is a compatibility symlink to
`/media/yuan/DATA500/runs`, so historical paths may remain readable. Current
new execution uses `/media/yuan/8A0E24070E23EAC1/runs`.

## 4. Remote Run Directories

| Run id | Remote run dir | Alias | Status | Limitation |
|---|---|---|---|---|
| `tclb_static_contact_angle_geometric_grid_density_20260607` | active: `/media/yuan/8A0E24070E23EAC1/runs/tclb_static_contact_angle_geometric_grid_density_20260607`; unstable copied history: `/media/yuan/DATA500/runs/tclb_static_contact_angle_geometric_grid_density_20260607`; per-case dirs are `<grid_tag>/theta045`, `<grid_tag>/theta090`, and `<grid_tag>/theta135`; local cases under `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\static_contact_angle_geometric_grid_density_20260607` | none | `exploratory_not_validation`; restarted 2026-06-08 00:03 +08 under `/media/yuan/8A0E24070E23EAC1/runs` | Geometric static contact-angle grid-density and arclength-fit audit using `/home/yuan/src/TCLB/CLB/d3q27_pf_velocity_geometric/main`. Matrix: R=24/W=4 on 128x96x128; R=32/W=5 and W=6 on 160x128x160; R=48/W=6 and W=8 on 224x192x224; each at theta045/theta090/theta135, 200000 steps, VTK interval 200000. Purpose is to test whether the old wall-distance window fit under-resolved the contact-line angle; not validation, not grid convergence, and not authorization for rho772 sweeps. DATA500 partial copy was archived under `copied_partial_before_20260608_0005_retarget_to_8A0E` because XMLs still wrote to DATA500 and copied R24 theta045 log was incomplete/corrupted. Active XMLs were retargeted to `/media/yuan/8A0E24070E23EAC1/runs`; the corrected runner writes `run.log`, `run.stderr`, `run.returncode`, and `run.done` in each theta directory. Raw VTI/PVTI stay remote-only. |
| `tclb_static_contact_angle_geometric_openlb_style_apparent_20260608_v4` | remote analysis: `/media/yuan/8A0E24070E23EAC1/runs/tclb_static_contact_angle_geometric_grid_density_20260607/analysis_apparent_openlb_style_20260608_v4`; local artifact: `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_geometric_openlb_style_apparent_20260608_v4`; script: `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_static_contact_angle_apparent_audit.py` | none | `exploratory_not_validation` | Existing-output-only OpenLB-style macroscopic apparent contact-angle audit for completed geometric static grid-density cases. Uses `phi=0.5` contour, x/z mid-slices, endpoint base-height, low-band base-height, and a 2 lu reference-plane base-height spherical-cap estimate. It explicitly differs from the local `1-8 lu` contact-line tangent. Important correction: v3/v4 fixed the overlay plotting coordinates so images are displayed as tangent coordinate vs wall-normal coordinate; older v2 overlay images should not be used for visual judgment. Key result for theta090: endpoint apparent angles are about R24/W4 `90.86 deg`, R32/W5 `90.35 deg`, R32/W6 `90.35 deg`, R48/W6 `89.97 deg`, while local arclength tangent is about `80.42/83.05/83.05/85.28 deg`. Theta045 shows the opposite split: local tangent is near `43-46 deg`, but macro apparent/global values are about `56-75 deg`. Theta135 is also split and worsens macroscopically at R48/W6: local `130.13 deg`, endpoint `107.67 deg`, reference-plane `114.32 deg`, global circle `115.13 deg`. This supports treating the contact-angle gate as an observable-definition and morphology issue, not validation. No validation promotion or impact sweep authorization. Raw VTI/PVTI remain remote-only. |
| `tclb_static_contact_angle_geometric_two_row_20260608` | remote analysis: `/media/yuan/8A0E24070E23EAC1/runs/tclb_static_contact_angle_geometric_grid_density_20260607/analysis_two_row_contact_angle_20260608`; local artifact: `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_geometric_two_row_20260608`; script: `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_static_contact_angle_two_row_audit.py`; read-only audit: `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_geometric_two_row_20260608\read_only_audit_20260608.md` | none | `validation_candidate` for static contact-angle boundary-condition metric only; not validation_passed | Existing-output-only literature-style near-wall two-row interpolation audit for completed geometric static grid-density cases. Uses `phi=0.5`, row pairs `1-2`, `2-3`, `3-4`, x/z mid-slices, left/right contact lines, with preferred row pair `1-2`. Completed 12 cases through R48/W6 theta135; R48/W8 incomplete cases excluded. Key preferred `1-2` results: theta045 `42.51/43.17/43.24/43.81 deg` for R24/W4, R32/W5, R32/W6, R48/W6; theta090 `87.65/88.26/88.25/88.84 deg`; theta135 `135.68/135.76/135.80/135.58 deg`; max abs error `2.4923 deg`, max x/z left/right std `0.0419 deg`. Read-only audit accepts the two-row metric as the primary near-wall contact-angle boundary-condition metric and allows main-agent integration to treat geometric static contact angle as `validation_candidate` for that metric. Still not `validation_passed`; two-row phi threshold sensitivity is now completed and supports robustness under phi=0.45/0.50/0.55. Macro apparent/global circle discrepancies remain morphology diagnostics, not hard rejectors. No rho772 impact validation, production, publication, grid-convergence, or Wang 2023 equivalence claim. Raw VTI/PVTI remain remote-only. |
| `tclb_static_contact_angle_geometric_two_row_phi_sensitivity_20260608` | remote analyses: `/media/yuan/8A0E24070E23EAC1/runs/tclb_static_contact_angle_geometric_grid_density_20260607/analysis_two_row_contact_angle_phi0p45_20260608`, `...phi0p50_20260608`, `...phi0p55_20260608`; local artifact: `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_geometric_two_row_phi_sensitivity_20260608` | none | supports `validation_candidate` for static contact-angle boundary-condition metric only | Existing-output threshold sensitivity for the two-row near-wall metric, using completed cases only and preferred row pair `1-2`. Across `phi=0.45/0.50/0.55`, max angle span is `0.9010 deg` and max abs angle error is `2.6568 deg`, still within the `<=5 deg` operational gate. Outputs include long/summary CSV, markdown table, and threshold trend PNG. Raw VTI/PVTI remain remote-only. |
| `tclb_z_wall_rho772_geometric_theta090_bounded_u008_M0025_W6_20260608` | `/media/yuan/8A0E24070E23EAC1/runs/tclb_z_wall_rho772_geometric_theta090_bounded_u008_M0025_W6_20260608/theta090`; local artifact `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_geometric_theta090_bounded_u008_M0025_W6_20260608_theta090`; continuation XMLs stored locally as `continue_ext6400.xml` and `continue_ext9600.xml` | none | `exploratory_not_validation` | New current-root theta090 dry-wall bounded pilot using `/home/yuan/src/TCLB/CLB/d3q27_pf_velocity_geometric/main`, R0=14, 96^3, z-min wall, `DropletOnlyVelocity=2`, `DropletVelocityZ=-0.008`, `M=0.025`, `IntWidth=6`, `GravitationZ=-1e-6`, 3200 steps, VTK interval 400. Completed with return code 0 and postprocess complete. Metrics: first contact step `1200`; `beta_area_max=1.1679834` at final step `3200`; `beta_box_max=1.1428571` at step `2800`; late beta area change `0.1109438`; `resting_candidate=false`; fluid-only phase drift max `0.6386%`; rho drift max `0.5870%`; max Mach `0.0147893`; nonfinite `0`. This is runtime/health evidence only, not validation, not rest, not grid convergence, and not production. Raw VTI/PVTI remain remote-only. |
| `tclb_z_wall_rho772_geometric_theta090_bounded_u008_M0025_W6_chk6400_20260608` | `/media/yuan/8A0E24070E23EAC1/runs/tclb_z_wall_rho772_geometric_theta090_bounded_u008_M0025_W6_chk6400_20260608/theta090`; local artifact `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_geometric_theta090_bounded_u008_M0025_W6_chk6400_20260608_theta090`; prepared restart extension XML `extend_6400_to_9600.xml` | none | `exploratory_not_validation` | Checkpoint-enabled theta090 dry-wall bounded pilot using the geometric binary, R0=14, 96^3, z-min wall, `DropletOnlyVelocity=2`, `DropletVelocityZ=-0.008`, `M=0.025`, `IntWidth=6`, `GravitationZ=-1e-6`, 6400 steps, VTK interval 200, `SaveCheckpoint Iterations=3200 keep=2`. TCLB return code 0. Remote checkpoint files: `output/case_checkpoint_00003200_0.pri`, `output/case_checkpoint_00006400_0.pri`, `output/case_restart_00003200.xml`, `output/case_restart_00006400.xml`; checkpoint `.pri` files remain remote-only. Postprocess has 33 snapshots and 17 morphology PNGs plus montage. Metrics: first contact step `1000`; `beta_area_max=1.2329202`; `beta_box_max=1.2142857`; beta-area max step `6200`; late beta-area change `0.0052802`; `resting_candidate=true` under beta tolerance 0.01; fluid-only phase drift max `1.1369%`; rho drift max `1.0451%`; max Mach `0.0153867`; nonfinite `0`. This is a bounded exploratory pilot and restart-readiness result only, not validation, not grid convergence, not production. |

| `tclb_z_wall_rho772_geometric_theta090_R24_W6_chk6400_20260608` | `/media/yuan/8A0E24070E23EAC1/runs/tclb_z_wall_rho772_geometric_theta090_R24_W6_chk6400_20260608/theta090`; local artifact `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_geometric_theta090_R24_W6_chk6400_20260608_theta090`; combined 0-65600 artifact `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_geometric_theta090_R24_W6_chk6400_20260608_theta090_0_65600`; remote combined analysis `/media/yuan/8A0E24070E23EAC1/runs/tclb_z_wall_rho772_geometric_theta090_R24_W6_chk6400_20260608/theta090/analysis_combined_0_65600` | none | `exploratory_not_validation` | R0=24 theta090 dry-wall checkpoint pilot using geometric binary, grid `128^3`, `R0=24`, `IntWidth=6`, `M=0.025`, `DropletOnlyVelocity=2`, `DropletVelocityZ=-0.008`, `GravitationZ=-1e-6`, z-min wall. Chain completed `0->6400`, `6400->12800`, `12800->25600`, and `25600->65600` with return code `0`; checkpoint `.pri` remains remote-only. Combined 0-65600 metrics exclude restart local step 0 frames and use absolute steps: first contact `1600`; `beta_area_max=1.4590056` at `8800`; `beta_box_max=1.5` at `41600`; late 64800/65200/65600 beta-area change `0.0015384`; beta-only resting candidate `true`; max fluid-only phase drift `1.03966%`; max rho drift `0.99534%`; max Mach `0.0255851`; nonfinite `0`; last beta_area `1.4376383`; last beta_box `1.4583333`. Segment `25600->65600` stderr contains `Missing comp parameter in LoadBinary`, but run.log confirms loading `extend_12800_to_25600_checkpoint_00012800_0.pri` and solving 40000 steps. Morphology review shows the annular/ring-like footprint and center low-phase/void persist through 65600; beta plateau is not physical acceptance. This is negative morphology evidence and remains exploratory only, not validation, production, or publication. |
| `tclb_z_wall_rho772_geometric_theta090_R24_W6_u024_chk6400_20260608` | `/media/yuan/8A0E24070E23EAC1/runs/tclb_z_wall_rho772_geometric_theta090_R24_W6_u024_chk6400_20260608/theta090`; local artifact `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_geometric_theta090_R24_W6_u024_chk6400_20260608_theta090`; combined artifact `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_geometric_theta090_R24_W6_u024_chk6400_20260608_theta090_0_12800`; remote combined analysis `/media/yuan/8A0E24070E23EAC1/runs/tclb_z_wall_rho772_geometric_theta090_R24_W6_u024_chk6400_20260608/theta090/analysis_combined_0_12800` | none | `exploratory_not_validation` | High-We theta090 dry-wall probe after the low-We case formed a stable center void. Grid `128^3`, `R0=24`, `IntWidth=6`, `M=0.025`, `DropletOnlyVelocity=2`, `DropletVelocityZ=-0.024`, `GravitationZ=-1e-6`, z-min wall. Velocity is 3x the previous `-0.008` case, so relative We is 9x for this lattice setup; not the original 1 mm/10 mm low-We target. Chain completed `0->6400` and `6400->12800` with return code `0`; postprocess return code `0`; raw VTI/PVTI/checkpoint `.pri` remote-only. Combined metrics exclude restart local step 0: first contact `400`; `beta_area_max=1.7970863` at `4000`; `beta_box_max=1.7916667` at `3200`; late 12000/12400/12800 beta-area change `0.0203664`, not resting; max fluid-only phase drift `1.38123%`; max rho drift `1.32236%`; max Mach `0.0901429`; nonfinite `0`; last beta_area `1.5635846`. Morphology: no clean stabilized central hole by 12800, but grid-like low-phase footprint pattern remains and the droplet is still retracting. Mach is close to 0.1, so do not increase speed further at this lattice scaling. |
| `tclb_z_wall_rho772_geometric_theta090_bounded_u008_M0025_W6_ext12800_20260608` | restart extension under `/media/yuan/8A0E24070E23EAC1/runs/tclb_z_wall_rho772_geometric_theta090_bounded_u008_M0025_W6_chk6400_20260608/theta090/restart_from_6400_ext12800`; local artifact `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_geometric_theta090_bounded_u008_M0025_W6_chk6400_20260608_theta090_ext12800`; extension XML `extend_6400_to_12800.xml` | none | `exploratory_not_validation` | Restarted from `output/case_checkpoint_00006400_0.pri` and ran an additional 6400 iterations to absolute step 12800, writing to an independent output directory. TCLB return code 0. Combined metrics exclude the restart segment local step 0 VTI because restart output uses local step numbering and TCLB writes an initial XML-output frame. Combined 0-12800 results: `beta_area_max=1.3414266` at absolute step 11400; `beta_box_max=1.3571429` at absolute step 10000; last beta equals maxima; late beta change over 12400/12600/12800 is 0; `resting_candidate=true`; max Mach `0.0153867`; nonfinite `0`; reported segment max fluid-phase drift `1.4299%`; reported segment max rho drift `1.3145%`. User observed a central void/bubble morphology risk, so this remains exploratory runtime evidence and needs morphology/mass review before any promotion. Raw VTI/PVTI/checkpoint `.pri` remain remote-only. |
| `tclb_z_wall_rho772_geometric_theta090_bounded_u008_M0025_W6_20260607` | `/media/yuan/DATA500/runs/tclb_z_wall_rho772_geometric_theta090_bounded_u008_M0025_W6_20260607/theta090`; compatibility path via `/home/yuan/runs/...`; local artifact `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_geometric_theta090_bounded_u008_M0025_W6_20260607_theta090` | none | `exploratory_not_validation` | Single geometric theta090 dry-wall bounded runtime probe using `/home/yuan/src/TCLB/CLB/d3q27_pf_velocity_geometric/main`, R0=14, 96^3, `DropletOnlyVelocity=2`, `DropletVelocityZ=-0.008`, `M=0.025`, `IntWidth=6`, 3200 steps. Completed with return code 0 and final VTK. Metrics: first contact 1200, beta_area max `1.167983` at final step, beta_box max `1.142857`, late beta_area change `0.110944`, resting false, fluid-only phase drift max `0.6386%`, rho drift `-0.5870%`, max Mach `0.014789`, nonfinite `0`. Raw 9 VTI and 9 PVTI remain remote-only. Read-only audit `read_only_audit_20260607` says runtime health passes for this bounded probe only; no validation, R0>=32, 45/90/135 sweep, or liquid-film case is authorized. |
| `static_contact_angle_geometric_revised_gate_candidate_20260607` | existing-output-only local artifact `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_geometric_revised_gate_candidate_20260607`; script `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\geometric_static_revised_gate_candidate.py` | none | `exploratory_not_validation` | Candidate two-metric static contact-angle gate. Frozen local gate still fails; `validation_candidate_allowed=false`. Read-only audit permits only one `theta090` dry-wall bounded runtime probe as `exploratory_not_validation`, not validation, sweep, R0>=32, liquid-film, production, or publication evidence. |
| `static_contact_angle_geometric_local_vs_global_audit_20260607` | existing-output-only local artifact `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_geometric_local_vs_global_audit_20260607`; inputs from `/home/yuan/runs/tclb_static_contact_angle_geometric_calib_20260607/theta045` and `/home/yuan/runs/tclb_static_contact_angle_geometric_theta090_theta135_minout_20260607` | none | `exploratory_not_validation` | Frozen local-tangent gate remains failed for theta090/theta135, but geometric route is `unresolved_not_rejected` because macro complements are near target and overlays show curved near-wall local-fit regions. This older audit did not permit impact work; the later two-metric audit only permits a single bounded runtime probe. |
| `tclb_static_contact_angle_geometric_theta090_theta135_minout_20260607` | `/home/yuan/runs/tclb_static_contact_angle_geometric_theta090_theta135_minout_20260607`; local artifact `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_geometric_theta090_theta135_minout_20260607` | none | `exploratory_not_validation` | Geometric-only theta090/theta135 minimal-output static cases. Preferred local angles: theta045 `43.2468 deg`, theta090 `77.2764 deg`, theta135 `118.1133 deg`; macro complements for theta090/theta135 are near target. Current static validation gate remains failed; only the later audited single theta090 bounded runtime probe is allowed. |
| `tclb_static_contact_angle_geometric_protocol_20260607` | `/home/yuan/runs/tclb_static_contact_angle_geometric_protocol_20260607`; local artifact `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_geometric_protocol_20260607` | none | `exploratory_not_validation` | Existing-output-only protocol freeze and visual/sensitivity audit for geometric theta045. No TCLB simulation was launched; source case is `/home/yuan/runs/tclb_static_contact_angle_geometric_calib_20260607/theta045`; raw VTI/PVTI remain remote-only and local raw count is `0`. Primary protocol is `phi=0.5`, true wall-distance `3-8 lu`, x/z mid-slices, left/right average, metric `local_liquid_side_angle_deg`. Important correction: earlier local-tangent postprocess used cumulative `0-w` windows; this artifact uses true `2-6`, `3-8`, and `4-10 lu` ranges. Preferred theta045 result is `43.2468 deg` with error `-1.7532 deg`; phi/window sensitivity spans mean angles `42.0284-43.5174 deg`, with farther `4-10 lu` windows trending lower. Health inherited from geometric theta045: fluid-only phase drift `-0.8552%`, rho drift `-0.8249%`, max Mach `9.398e-5`, nonfinite `0`. This supports continuing the geometric static 90/135 gate, but does not promote validation or authorize impact sweeps. |
| `tclb_static_contact_angle_geometric_staircaseimp_20260607` | `/home/yuan/runs/tclb_static_contact_angle_geometric_staircaseimp_20260607/theta045`; analysis under `theta045/analysis_contact_angle_geometric_staircaseimp`; convention audit under `analysis_contact_angle_geometric_staircaseimp_convention_audit` | none | `exploratory_not_validation` | A2 geometric plus staircase-improvement theta045 diagnostic using `/home/yuan/src/TCLB/CLB/d3q27_pf_velocity_geometric_staircaseimp/main`. Build return code `0`; options `geometric=TRUE`, `staircaseimp=TRUE`, `isograd/tprec=FALSE`; original and geometric-only binaries remained unchanged. Case: `radAngle=45d`, 128x64x128, `M=0.05`, `IntWidth=4`, 200000 steps, VTK interval 200000. TCLB return code `0`; postprocess return code `0`; convention audit return code `0`; raw output `2` VTI and `2` PVTI, remote-only; local raw count `0`; remote size about `133M`; HM570 free disk about `3.2G` afterward. Metrics: postprocess complement `59.511398 deg`; convention-audit liquid-side range `57.620709-61.896170 deg`, best error `+12.620709 deg`; fluid-only phase drift `-0.855225%`; rho drift `-0.824869%`; max Mach `3.044e-5`; nonfinite `0`. This variant runs cleanly but does not improve theta045 relative to geometric-only; no 90/135 continuation, impact sweep, or status promotion is authorized. |
| `tclb_static_contact_angle_revised_eval_20260607` | `/home/yuan/runs/tclb_static_contact_angle_revised_eval_20260607`; per-case local tangent analyses for existing surface/geometric outputs | none | `exploratory_not_validation` | Existing-output-only revised static contact-angle evaluation. No new TCLB simulation. The revised primary metric is local liquid-side contact-line tangent angle, averaged over left/right contact lines, x/z mid-slices, and near-wall windows; global whole-cap/circle-fit complement is secondary. Results: surface theta045 local `39.882 +/- 0.330 deg`; surface theta090 local `84.048 +/- 2.262 deg`; surface theta135 local `133.623 +/- 2.974 deg` after obtuse-angle conversion; geometric theta045 local `43.150 +/- 0.100 deg`; geometric_staircase theta045 local `43.150 +/- 0.100 deg`. Updated interpretation: theta045 geometric route shows plausible local contact-line behavior; prior blocker was mainly global circle-fit evaluation, not clear wetting-model failure. This artifact motivated the stricter `tclb_static_contact_angle_geometric_protocol_20260607` true-window audit. No validation promotion or impact sweep without geometric 45/90/135 under frozen protocol, visual audit, threshold/grid sensitivity, and mass/rho/Mach/nonfinite gates. |
| `tclb_static_contact_angle_geometric_rad005_minout_20260607` | `/home/yuan/runs/tclb_static_contact_angle_geometric_rad005_minout_20260607/theta005` | none | `failed_negative_evidence` | Geometric-only low-angle response diagnostic using `/home/yuan/src/TCLB/CLB/d3q27_pf_velocity_geometric/main`, `radAngle=5d`, 128x64x128, `M=0.05`, `IntWidth=4`, 200000 requested steps, VTK interval 200000. TCLB wrapper wrote return code `0`, but `run.log` reports `Checking PhaseField discovered NaN` and `Stopping due to Nan value`; only the initial VTI/PVTI pair exists, no final frame, remote size about `66M`, local raw count `0`. This is not a contact-angle calibration point. Do not inverse-sweep geometric low angles or launch impact from it without a changed/audited route. |
| `tclb_static_contact_angle_geometric_calib_20260607` | `/home/yuan/runs/tclb_static_contact_angle_geometric_calib_20260607/theta045`; analysis under `theta045/analysis_contact_angle_geometric`; convention audit under `analysis_contact_angle_geometric_convention_audit` | none | `exploratory_not_validation` | A2 geometric-wetting build-option diagnostic using independently built `/home/yuan/src/TCLB/CLB/d3q27_pf_velocity_geometric/main`. Only theta045 was run because HM570 free disk was about `3.4G` after this single 1.4G static case. TCLB return code `0`; postprocess return code `0`; convention audit return code `0`; raw output `21` VTI and `21` PVTI, remote-only; local raw count `0`. Original global/circle metrics: input `45 deg`; postprocess complement `59.5114 deg`; convention-audit liquid-side range `57.6207-61.8962 deg`, best error `+12.6207 deg`. Revised local tangent protocol artifact reports theta045 `43.2468 deg` for `phi=0.5`, true `3-8 lu`, error `-1.7532 deg`. Health: fluid-only phase drift `-0.8552%`; rho drift `-0.8249%`; max Mach `9.398e-5`; nonfinite `0`; wall/ghost phase drift about `65.15%`. This single theta045 case does not authorize impact sweeps or validation promotion; geometric theta090/theta135 static cases are required next under the frozen local-tangent protocol. |
| `tclb_bubbleRise_A1_grid_time_20260607` | `/home/yuan/runs/tclb_bubbleRise_A1_grid_time_20260607/coarse_L48`, `/base_L64`, `/fine_L80`; analyses under each `analysis_bubbleRise_A1_<tag>` | none | `runtime_sanity` | A1 TC1 grid/time sensitivity chain for L0=48/64/80, not validation promotion. All three HM570 runs completed with 7 VTI and 7 PVTI each; raw VTI/PVTI remain remote-only. Remote sizes are about `131M`, `231M`, and `538M`. Runtime health: L48 max Mach `0.0317124`, nonfinite `0`, fluid phase/rho drift `4.07186e-5`/`3.65341e-5`; L64 max Mach `0.0223497`, nonfinite `0`, fluid phase/rho drift `2.93937e-5`/`2.63515e-5`; L80 max Mach `0.0179932`, nonfinite `0`, fluid phase/rho drift `1.69536e-5`/`1.52111e-5`. Postprocess stderr has Matplotlib no-contour warnings for early morphology frames, recorded as visualization limitations. `coarse_L48/run.returncode` is empty due to a first-run PowerShell/Bash wrapper return-code expansion issue, but `run.log` reaches total duration and outputs are complete. Per-case Bonn comparisons completed; grid/time spreads fail provisional gates (`center_of_mass_l2_abs_error_spread=0.0220774`, `rise_velocity_l2_abs_error_spread=0.0349694`), and the acceptance gate remains `runtime_sanity`. Does not validate rho772 impact, target contact angles, Wang 2023 equivalence, or A1 grid convergence. |
| `tclb_bubbleRise_A1_20260607` | `/home/yuan/runs/tclb_standard_d3q27_20260606_231035/bubbleRise_short`; analysis under `/home/yuan/runs/tclb_standard_d3q27_20260606_231035/bubbleRise_short/analysis_bubbleRise_A1_20260607` | none | `runtime_sanity` | Existing-output formalization of the TCLB built-in `bubbleRise_1` sanity case, not a new TCLB simulation. Remote raw output is 7 VTI and 7 PVTI, about `468M`, and remains remote-only; local raw VTI/PVTI count is `0`. Postprocess return code `0`; stderr contains one Matplotlib no-contour warning for a morphology frame and must be recorded as a visualization limitation, not a fatal numerical failure. Key metrics: bubble proxy is clipped `1 - PhaseField` because `BubbleType=-1`; rise direction is `positive_y_by_largest_bubble_proxy_centroid_displacement`; y-centroid displacement is `55.3067` cells; max Mach `0.02235`; max nonfinite `0`; max all-cell/fluid-only phase drift `9.72e-5`/`2.94e-5`; max all-cell/fluid-only rho drift `2.63e-5`/`2.63e-5`. A local pre-audit Safi TC1 comparison artifact now exists at `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_bubbleRise_A1_safi_compare_20260607`, using digitized FeatFlow Fig. 4/5 curves and TCLB CSV `GasTotalVelocityY/GasTotalPhase` for rise velocity; metrics include center-of-mass L2 abs error `0.0587` and rise-velocity L2 abs error `0.0145`. This remains `runtime_sanity` only; no promotion without read-only audit, stronger reference provenance if available, and grid/time-step sensitivity. |
| `tclb_static_contact_angle_calib_20260607` | `/home/yuan/runs/tclb_static_contact_angle_calib_20260607/theta045`, `/theta090`, `/theta135`; v3 analysis under each `analysis_contact_angle_v3`; convention audit under `/home/yuan/runs/tclb_static_contact_angle_calib_20260607/analysis_contact_angle_convention_audit` | none | `exploratory_not_validation` | A2 static contact-angle calibration derived from TCLB official `ContactAngle_45.xml`; all three angles completed 200000 steps with return code 0 and 21 VTI/PVTI each. Postprocess v3 added input-angle and complement-error reporting without launching new simulations. v3: theta045 apparent `122.3379 deg`, complement `57.6621 deg`, complement error `+12.6621 deg`, phase drift `+4.1804%`, rho drift `-0.9026%`, max Mach `9.53e-5`, nonfinite `0`; theta090 apparent `89.1689 deg`, complement `90.8311 deg`, complement error `+0.8311 deg`, phase drift `-0.1825%`, rho drift `+0.0364%`, max Mach `1.16e-5`, nonfinite `0`; theta135 apparent `44.7137 deg`, complement `135.2863 deg`, complement error `+0.2863 deg`, phase drift `-3.3408%`, rho drift `+0.7698%`, max Mach `1.67e-4`, nonfinite `0`. Convention audit compared 24 fit variants per angle across x/z mid-slices, wall locations, and near-wall point filters using `lower_wall_liquid_side_angle_deg = 180 - angle_from_circle_deg`; x-mid contour plot x is y wall-normal and z-mid contour plot y is y wall-normal. It found theta045 liquid-side angle `55.7808-60.7211 deg` (error `+10.7808` to `+15.7211 deg`), theta090 `88.3287-90.8311 deg`, and theta135 `129.3640-135.2863 deg`, with finite variants and max Mach below `4.7e-5`. Read-only gate remains no promotion and no impact sweep. Build-state audit found the current HM570 `d3q27_pf_velocity/main` binary has `geometric`, `staircaseimp`, `isograd`, and `tprec` disabled (`options.R=FALSE`, `Consts.h=#undef`), even though `conf.mk` lists them as possible build variants; therefore these runs used the non-geometric/default surface-energy wetting path and are not evidence for the geometric wetting boundary condition. Resolve theta045 low-angle wetting/mass/fit mismatch before any impact sweep. |
| `tclb_static_contact_angle_response_surface_energy_20260607` | `/home/yuan/runs/tclb_static_contact_angle_response_surface_energy_20260607/theta030`, `/theta035`, `/theta040`, `/theta045`, `/theta050`, `/theta060`; per-case analysis under `analysis_contact_angle_response`; convention audit under `/home/yuan/runs/tclb_static_contact_angle_response_surface_energy_20260607/analysis_contact_angle_convention_audit` | none | `exploratory_not_validation` | Low-angle response check for the default/non-geometric surface-energy wetting path using official `ContactAngle_45.xml`-derived static cases with `radAngle=30/35/40/45/50/60`, `M=0.05`, `IntWidth=4`, lower-y wall, 128x64x128 grid, 200000 steps, VTK interval 10000. All six cases have `run_return_code=0`, 21 VTI and 21 PVTI each, and raw VTI/PVTI remain remote-only; remote run size is about `8.1G`. Current HM570 build remains non-geometric/default surface-energy: `geometric`, `staircaseimp`, `isograd`, and `tprec` are `FALSE/#undef`. Corrected convention audit return code `0` and summary `run_id=tclb_static_contact_angle_response_surface_energy_20260607`; 24 variants per angle. Liquid-side ranges: theta030 `48.8321-57.2313 deg`, theta035 `51.0164-57.7338 deg`, theta040 `53.2827-59.0198 deg`, theta045 `55.7808-60.7211 deg`, theta050 `58.6713-62.9543 deg`, theta060 `65.3152-68.5590 deg`. Per-case postprocess complements and health: theta030 complement `50.5814 deg`, phase drift `7.9924%`, rho drift `-1.5230%`, max Mach `1.20e-4`, nonfinite `0`; theta035 `52.8261 deg`, `6.0308%`, `-1.2333%`, `1.14e-4`, `0`; theta040 `55.1045 deg`, `4.9787%`, `-1.0521%`, `1.05e-4`, `0`; theta045 `57.6621 deg`, `4.1804%`, `-0.9026%`, `9.53e-5`, `0`; theta050 `60.6172 deg`, `3.5144%`, `-0.7715%`, `8.56e-5`, `0`; theta060 `67.3294 deg`, `2.3867%`, `-0.5379%`, `6.38e-5`, `0`. This rejects using `radAngle=30/35` as a stable substitute for liquid-side 45 and does not clear the theta045 blocker; no 45/90/135 impact sweep is authorized. |
| `tclb_static_contact_angle_bracket_lowangle_20260607` | `/home/yuan/runs/tclb_static_contact_angle_bracket_lowangle_20260607/theta015`, `/theta018`, `/theta020`, `/theta022`, `/theta025`, `/theta028`; per-case analysis under `analysis_contact_angle_bracket`; convention audit under `/home/yuan/runs/tclb_static_contact_angle_bracket_lowangle_20260607/analysis_contact_angle_bracket_audit` | none | `exploratory_not_validation` | Follow-up low-angle bracket for the same non-geometric/default surface-energy path, `radAngle=15/18/20/22/25/28`, 128x64x128 grid, 200000 steps. All cases completed with run/postprocess/audit return code `0`, stderr empty, 21 VTI and 21 PVTI per case, raw remote-only, remote size about `8.1G`. Convention-audit liquid-side ranges: 15 `45.5173-59.1006 deg`, 18 `46.3092-58.8903`, 20 `47.0182-58.6007`, 22 `47.1096-58.3660`, 25 `47.8631-57.6266`, 28 `48.6100-57.3476`. Postprocess complements and health: 15 `47.2164 deg`, phase drift `16.2726%`, rho `-2.5780%`, max Mach `1.33e-4`, nonfinite `0`; 18 `48.0253`, `15.1672%`, `-2.4359%`; 20 `48.7512`, `14.2689%`, `-2.3214%`; 22 `48.8392`, `13.2292%`, `-2.1896%`; 25 `49.6052`, `11.3804%`, `-1.9562%`; 28 `50.3881`, `9.2934%`, `-1.6926%`. The 15-degree lower bound still does not robustly go below liquid-side 45 and mass/rho drift is far outside engineering preferences. |
| `tclb_static_contact_angle_bracket_lower_20260607` | `/home/yuan/runs/tclb_static_contact_angle_bracket_lower_20260607/theta005`, `/theta010`, `/theta012`; per-case analysis under `analysis_contact_angle_bracket`; convention audit under `/home/yuan/runs/tclb_static_contact_angle_bracket_lower_20260607/analysis_contact_angle_bracket_audit` | none | `exploratory_not_validation` | Lower-angle continuation for the same path, `radAngle=5/10/12`, 128x64x128 grid, 200000 steps. All cases completed with run/postprocess/audit return code `0`, stderr empty, 21 VTI and 21 PVTI per case, raw remote-only, remote size about `4.1G`. Convention-audit liquid-side ranges: 5 `43.8741-60.0582 deg`, 10 `44.6668-59.8532`, 12 `44.7333-59.7167`; postprocess complements and health: 5 `45.5354 deg`, phase drift `18.3009%`, rho `-2.8428%`, max Mach `1.36e-4`, nonfinite `0`; 10 `46.3477`, `17.5727%`, `-2.7472%`; 12 `46.4137`, `17.1268%`, `-2.6889%`. These points weakly bracket liquid-side 45 only through a broad fit-sensitivity range, while mass/rho drift is unacceptable; theta045 blocker remains uncleared and no single impact pilot or 45/90/135 sweep is authorized. Combined artifact: `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_bracket_combined_20260607`. |
| `tclb_static_contact_angle_bracket_lowangle_M0025_W6_20260607` | `/home/yuan/runs/tclb_static_contact_angle_bracket_lowangle_M0025_W6_20260607/theta005`, `/theta010`, `/theta015`; per-case analysis under `analysis_contact_angle_bracket_M0025_W6` and BOUNDARY-aware reanalysis under `analysis_contact_angle_bracket_M0025_W6_boundarymass`; convention audit under `/home/yuan/runs/tclb_static_contact_angle_bracket_lowangle_M0025_W6_20260607/analysis_contact_angle_bracket_M0025_W6_audit` | none | `exploratory_not_validation` | Static low-angle sensitivity using the same lower-y-wall geometry as the prior bracket but with `M=0.025`, `IntWidth=6`, `radAngle=5/10/15`, 128x64x128 grid, 200000 steps, VTK interval 10000. All three cases completed with TCLB/postprocess/audit return code `0`, 21 VTI and 21 PVTI per case, raw remote-only, remote size about `4.1G`, local raw count `0`. BOUNDARY-aware reanalysis return code `0`, stderr empty. Complements and health: theta005 `52.7401 deg`, all-cell phase drift `8.5176%`, fluid-only phase drift `1.6495%`, rho drift `1.5921%`, wall/ghost phase drift `153.3568%`, max Mach `1.4126e-4`, nonfinite `0`; theta010 `52.8157 deg`, `8.2010%`, `1.6046%`, `1.5488%`, `148.0239%`, `1.4010e-4`, `0`; theta015 `52.9568 deg`, `7.6811%`, `1.5296%`, `1.4764%`, `139.2290%`, `1.3811e-4`, `0`. Convention-audit liquid-side ranges are theta005 `50.9341-59.9471 deg`, theta010 `51.0110-59.8931 deg`, theta015 `51.1540-59.8179 deg`. The coupled M/IntWidth choice reduces bulk fluid-only phase drift to under the exploratory engineering preference, but it loses the exploratory 45-degree bracket and still has rho drift around `1.5%`; all-cell phase is wall/ghost-inclusive and must not be used as the bulk conservation gate. No calibration pass, no impact sweep, and no promotion. |
| `tclb_z_wall_rho772_rad005_target45_dropletsmooth_u008_M0025_W6_ext6400_20260607` | `/home/yuan/runs/tclb_z_wall_rho772_rad005_target45_dropletsmooth_u008_M0025_W6_ext6400_20260607/rad005_target45`; analysis under `/analysis` | none | `exploratory_not_validation` | Single dry-wall exploratory pilot allowed by read-only audit after static low-angle bracket, using input `radAngle=5d` as a liquid-side-45 target only. Case: 96x96x96, `R0=14`, z-wall, gravity `-z`, smooth `DropletOnlyVelocity=2`, `DropletVelocityZ=-0.008`, `M=0.025`, `IntWidth=6`, 6400 steps, VTK interval 400. TCLB return code `0`, postprocess return code `0`; postprocess stderr is a Matplotlib no-contour warning for an early morphology frame. Raw VTI/PVTI `17/17`, remote-only, remote size about `939M`, local raw count `0`. Metrics: first contact step `1200`; `beta_area_max=1.73427` at final step `6400`; `beta_box_max=1.71429` at step `6000`; late beta changes `0.06489/0.07143`; `resting_candidate=false`; all-cell phase drift `12.4209%`, fluid-only phase drift `2.2720%`, rho drift `-2.0886%`, max Mach `0.01461`, nonfinite `0`, wall ghost phase last `1885.7082`. Runtime/Mach/finite checks are healthy but the case is not rest and mass/rho drift exceeds engineering preferences; no promotion and no 45/90/135 sweep. |
| `tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext9600_20260607` | `/home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext9600_20260607/theta090` | none | `exploratory_not_validation` | 9600-step extension of the same small-grid theta=90 coupled `M=0.025`, `IntWidth=6` candidate; `R0=14`, z-wall, smooth `DropletOnlyVelocity=2`, `DropletVelocityZ=-0.008`, `CenterZ=22`; run reaches 9600 and stays numerically finite, but `beta_area` max is still at final step 9600, `late_beta_area_change=0.01505` over 8800,9200,9600, and `resting_candidate=false`; all-cell phase drift `+6.688%` is wall/ghost diagnostic only, fluid-only phase drift `-1.3355%`, rho drift `-1.2277%`, max Mach `0.01479`, nonfinite `0`; read-only audit keeps no promotion and treats this as negative evidence for continuing the same small-grid candidate |
| `tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext6400_20260607` | `/home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext6400_20260607/theta090` | none | `exploratory_not_validation` | 6400-step extension of current best small-grid candidate; `M=0.025`, `IntWidth=6`, `R0=14`, theta=90, z-wall, smooth `DropletOnlyVelocity=2`, `DropletVelocityZ=-0.008`, `CenterZ=22`; first contact step 1200; `beta_area` max still at final step 6400 and `resting_candidate=false`; fluid-only phase drift `-1.1369%`, rho drift `-1.0451%`, max Mach `0.01479`, nonfinite `0`; no status promotion, no `R0>=32` or contact-angle sweep from this result alone |
| `tclb_z_wall_rho772_dropletsmooth_u008_ext3200_M0025_W6_20260607` | `/home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_ext3200_M0025_W6_20260607/theta090` | none | `exploratory_not_validation` | Coupled `M=0.025`, `IntWidth=6` diagnostic; `R0=14`, theta=90, z-wall, smooth `DropletOnlyVelocity=2`, `DropletVelocityZ=-0.008`, `CenterZ=22`, 3200 steps; best current phase drift direction at about `3.65%` and rho drift about `-0.59%`, but still fails long-window phase gate and is not rest; postprocess return code was not captured, see local provenance note |
| `tclb_z_wall_rho772_dropletsmooth_u008_ext3200_W6_20260607` | `/home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_ext3200_W6_20260607/theta090` | none | `exploratory_not_validation` | IntWidth-only sensitivity versus prior ext3200 baseline; `M=0.05`, `IntWidth=6`, `R0=14`, theta=90, z-wall, smooth `DropletOnlyVelocity=2`, `DropletVelocityZ=-0.008`, `CenterZ=22`, 3200 steps; phase drift improves versus baseline to about `4.33%` and rho drift about `-0.76%`, but still fails long-window phase gate and is not rest |
| `tclb_z_wall_rho772_dropletsmooth_u008_ext3200_W4_20260607` | `/home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_ext3200_W4_20260607/theta090` | none | `exploratory_not_validation` | IntWidth-only sensitivity versus prior ext3200 baseline; `M=0.05`, `IntWidth=4`, `R0=14`, theta=90, z-wall, smooth `DropletOnlyVelocity=2`, `DropletVelocityZ=-0.008`, `CenterZ=22`, 3200 steps; phase drift worsens to about `5.92%`, rho drift about `-1.07%`, not rest, negative evidence for reducing `IntWidth` alone |
| `tclb_z_wall_rho772_dropletsmooth_u008_ext3200_M0025_20260607` | `/home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_ext3200_M0025_20260607/theta090` | none | `exploratory_not_validation` | M-only sensitivity versus prior ext3200 baseline; `M=0.025`, `IntWidth=5`, `R0=14`, theta=90, z-wall, smooth `DropletOnlyVelocity=2`, `DropletVelocityZ=-0.008`, `CenterZ=22`, 3200 steps; phase drift improves from about `5.02%` baseline to about `4.14%`, but still fails long-window mass gate and is not validation |
| `tclb_z_wall_rho772_dropletsmooth_u008_ext3200_20260607` | `/home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_ext3200_20260607/theta090` | none | `exploratory_not_validation` | extended window; first contact step 1000; beta still growing; phase drift about `5.02%`; not rest |
| `tclb_z_wall_rho772_dropletsmooth_u008_nearwall_20260607` | `/home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_nearwall_20260607/theta090` | none | `exploratory_not_validation` | smooth droplet velocity with lower `Uz=-0.008`; phase drift about `1.34%`; `R0=14`, not run to rest |
| `tclb_z_wall_rho772_dropletsmooth_nearwall_20260607` | `/home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_nearwall_20260607/theta090` | none | `exploratory_not_validation` | smooth droplet velocity A/B; phase drift about `2.96%`; `R0=14`, not run to rest |
| `tclb_z_wall_rho772_dropletonly_nearwall_20260607` | `/home/yuan/runs/tclb_z_wall_rho772_dropletonly_nearwall_20260607/theta090` | none | `exploratory_not_validation` | droplet-only patch, theta=90 near-wall contact; phase drift about `3.28%`; `R0=14`, not run to rest |
| `tclb_z_wall_rho772_dropletonly_20260607` | `/home/yuan/runs/tclb_z_wall_rho772_dropletonly_20260607/theta090` | none | `exploratory_not_validation` | droplet-only patch, theta=90; no wall contact by 1200 steps |
| `tclb_z_wall_rho772_lowmach_contact_20260607` | `/home/yuan/runs/tclb_z_wall_rho772_lowmach_contact_20260607/theta090` | none | `exploratory_not_validation` | z-wall theta=90 low-Mach contact pilot; global `VelocityZ`; `R0=14`, not run to rest |
| `tclb_z_wall_rho772_pilot_20260607` | `/home/yuan/runs/tclb_z_wall_rho772_pilot_20260607/theta090` | none | `exploratory_not_validation` | z-wall theta=90 smoke only; no wall contact by 500 steps; global `VelocityZ`; max Mach `0.0979` near guard |
| `tclb_impact_rho772_drywall_explore_20260607_001950` | `/home/yuan/runs/tclb_impact_rho772_drywall_explore_20260607_001950` | `/home/yuan/runs/tclb_impact_rho772_drywall_explore_latest` | `exploratory_not_validation` | phase-field mass drift about `+12%`; wall normal x, not target z |
| `tclb_standard_d3q27_20260606_231035` | `/home/yuan/runs/tclb_standard_d3q27_20260606_231035` | `/home/yuan/runs/tclb_standard_d3q27_latest` | `runtime_sanity` | standard sanity only |
| `tclb_smoke_contact45` | `/home/yuan/runs/tclb_smoke_contact45` | none | `runtime_sanity` | smoke only |

For each future run, record:

```text
run_id
remote_run_dir
remote_alias
alias_type
resolved_alias_target
case_xml
generated_config
run_log
tclb_csv_log
raw_output_dir
analysis_dir
status
first_failure_or_limitation
postprocess_script
vtk_order_note
wall_axis
wall_side
gravity_direction
contact_angle
initial_velocity_method
local_artifact_dir
raw_vti_count
raw_pvti_count
remote_run_size
copy_policy
```

## 5. Local Artifact Mirrors

| Status | Local artifact dir | Remote source |
|---|---|---|
| TCLB built-in bubbleRise A1 sanity formalization, runtime only | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_bubbleRise_A1_20260607`; includes README, execution report, case XMLs, generated config XML, `run.log`, TCLB CSV log, metrics CSV, summary JSON, figures, postprocess logs, and script copy; local raw VTI/PVTI count is `0` | `/home/yuan/runs/tclb_standard_d3q27_20260606_231035/bubbleRise_short`; analysis `/home/yuan/runs/tclb_standard_d3q27_20260606_231035/bubbleRise_short/analysis_bubbleRise_A1_20260607`; raw VTI/PVTI remain remote-only, 7/7, remote size about `468M` |
| A1 Safi 2017 TC1 FeatFlow digitized-reference comparison, pre-audit runtime only | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_bubbleRise_A1_safi_compare_20260607`; includes `README.md`, `a1_safi_comparison_summary.json`, `definition_evidence.md`, pointwise `a1_safi_comparison.csv`, and two overlay figures; local raw VTI/PVTI count is `0` | Existing local A1 artifact and `references\data\a1_bubbleRise_safi2017_reference.csv`; no new remote TCLB simulation and no remote raw copy |
| A1 Bonn/INS TC1 ASCII-reference comparison, pre-audit runtime only | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_bubbleRise_A1_bonn_compare_20260607`; includes `README.md`, `a1_bonn_comparison_summary.json`, pointwise comparison CSV, interval velocity comparison CSV, and two overlay figures; local raw VTI/PVTI count is `0` | Existing local A1 artifact and `references\data\bonn_3d_rising_bubble_tc1\bonn_3d_rising_bubble_tc1_reference.csv`; no new remote TCLB simulation and no remote raw copy |
| A1 acceptance-gate evaluator, explicit failed validation-candidate gate | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_bubbleRise_A1_acceptance_gate_20260607`; includes `README.md`, `a1_acceptance_gate_summary.json`, and `read_only_audit_20260607.md`; local raw VTI/PVTI count is `0` | Existing local A1/Bonn/Safi summary JSON and audit markdown only; no new remote TCLB simulation and no remote raw copy |
| A1 grid/time sensitivity completed chain, runtime only | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_bubbleRise_A1_grid_time_20260607`; includes per-case curated `analysis_bubbleRise_A1_<tag>` outputs, postprocess logs, `README.md`, `a1_grid_time_sensitivity_summary.json`, and `read_only_audit_20260607.md`; per-case comparison artifacts are `...\tclb_bubbleRise_A1_grid_time_20260607_coarse_L48_bonn_compare`, `...\base_L64_bonn_compare`, and `...\fine_L80_bonn_compare`; local raw VTI/PVTI count is `0` | `/home/yuan/runs/tclb_bubbleRise_A1_grid_time_20260607/{coarse_L48,base_L64,fine_L80}`; raw VTI/PVTI remain remote-only, 7/7 per case, remote sizes about `131M`, `231M`, `538M` |

A1 Safi comparison read-only audit, 2026-06-07:

```text
audit_artifact = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_bubbleRise_A1_safi_compare_20260607\read_only_audit_20260607.md
decision = keep runtime_sanity; do not promote to validation_candidate
main reasons = bitmap-derived reference provenance is not independently calibrated;
               center_of_mass and rise_velocity errors exceed recorded
               digitization uncertainty; rise velocity remains a diffuse-interface
               Omega2 proxy; no grid/time-step sensitivity beyond L0=64
script = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\a1_bubbleRise_compare_safi2017.py
script_sha256 = 5AB50D3266131C382DD6573BEE01008150A19A17A1101E055264778238FF1CC8
reference_rows = 225 total: 110 center_of_mass, 115 rise_velocity
comparison_rows = 223 total: 108 center_of_mass, 115 rise_velocity
raw_vti_pvti_local = 0
velocity_crosscheck = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_bubbleRise_A1_safi_compare_20260607\a1_velocity_observable_crosscheck_summary.json
velocity_crosscheck_result = same positive rise direction, but max interval
                             nondimensional velocity difference 0.0461,
                             max relative difference 14.7%, cumulative
                             centroid prediction 6.94 cells high at step 12000;
                             do not lock velocity mapping for validation use
```

A1 Bonn/INS TC1 reference provenance, 2026-06-07:

```text
status = runtime_sanity reference provenance only; no validation promotion
script = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\a1_bubbleRise_download_bonn_reference.py
script_check = python -m py_compile returned 0
output_dir = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\references\data\bonn_3d_rising_bubble_tc1
curated_csv = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\references\data\bonn_3d_rising_bubble_tc1\bonn_3d_rising_bubble_tc1_reference.csv
summary_json = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\references\data\bonn_3d_rising_bubble_tc1\bonn_3d_rising_bubble_tc1_reference_summary.json
curated_rows = 5388 total: center_of_mass DROPS/NaSt3D/OpenFOAM
               601/595/301 and rise_velocity DROPS/NaSt3D/OpenFOAM
               3001/589/301
center_zip_sha256 = db617631d966df349549b729c44c216f6ae056f15c37171231de9e709c7f6842
center_zip_entries = TC1_centerOfMass_DROPS.txt,
                     TC1_centerOfMass_NaSt3D.txt,
                     TC1_centerOfMass_OpenFOAM.txt
velocity_zip_sha256 = 37cb998a692dccd0440d00fa3dc991f083e9258f2b4e02377f76a632d9585a68
velocity_zip_entries = TC1_riseVelocity_DROPS.txt,
                       TC1_riseVelocity_NaSt3D.txt,
                       TC1_riseVelocity_OpenFOAM.txt
comparison_vs_current_safi_bitmap = center_of_mass L2/max abs difference:
                                    DROPS 0.01040/0.01221,
                                    NaSt3D 0.01380/0.01591,
                                    OpenFOAM 0.02904/0.04549;
                                    rise_velocity L2/max abs difference:
                                    DROPS 0.00337/0.01377,
                                    NaSt3D 0.00339/0.01395,
                                    OpenFOAM 0.01382/0.02296
claim_limit = Bonn archive series are Adelsberger 2014 TC1 DROPS/NaSt3D/
              OpenFOAM ASCII data; do not rename as Safi 2017 FeatFlow
              without separate audit
```

A1 Bonn/INS TC1 direct comparison artifact, 2026-06-07:

```text
artifact = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_bubbleRise_A1_bonn_compare_20260607
script = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\a1_bubbleRise_compare_bonn_reference.py
script_check = python -m py_compile returned 0
status = runtime_sanity; no validation promotion
outputs = a1_bonn_pointwise_comparison.csv,
          a1_bonn_interval_velocity_comparison.csv,
          a1_bonn_comparison_summary.json,
          read_only_audit_20260607.md,
          figures\a1_bonn_center_of_mass_comparison.png,
          figures\a1_bonn_rise_velocity_comparison.png
local_raw_vti_pvti_count = 0
center_of_mass_pointwise_L2_max_abs =
  DROPS 0.04758 / 0.08268,
  NaSt3D 0.04471 / 0.07970,
  OpenFOAM 0.02981 / 0.04918
rise_velocity_csv_proxy_pointwise_L2_max_abs =
  DROPS 0.01490 / 0.03255,
  NaSt3D 0.01337 / 0.03134,
  OpenFOAM 0.02366 / 0.03582
rise_velocity_centroid_interval_L2_max_abs =
  DROPS 0.02783 / 0.03549,
  NaSt3D 0.02968 / 0.03685,
  OpenFOAM 0.01805 / 0.02990
claim_limit = audit input only; Bonn series are Adelsberger 2014 TC1
              DROPS/NaSt3D/OpenFOAM, not Safi 2017 FeatFlow; observable
              mapping and grid/time-step sensitivity remain unresolved
read_only_audit = keep runtime_sanity; do not promote to validation_candidate
                  because no accepted thresholds are frozen, Bonn series are
                  not audited as Safi FeatFlow equivalents, velocity
                  observable mapping remains unresolved, centroid interval
                  velocity has only six coarse intervals, only one L0=64 run
                  exists, center-of-mass errors remain nontrivial, and no
                  grid/time-step sensitivity is available
```

A1 acceptance-gate evaluator, 2026-06-07:

```text
protocol = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\docs\a1_bubbleRise_acceptance_protocol.md
script = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\a1_bubbleRise_acceptance_gate.py
artifact = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_bubbleRise_A1_acceptance_gate_20260607
outputs = README.md, a1_acceptance_gate_summary.json,
          read_only_audit_20260607.md
script_check = python -m py_compile returned 0
run_check = python scripts\a1_bubbleRise_acceptance_gate.py returned 0
status_decision = runtime_sanity
health_pass = max Mach 0.02235, nonfinite 0, fluid-only phase drift 2.94e-5,
              fluid-only rho drift 2.63e-5
failed_gate_reasons = thresholds provisional; no accepted Bonn target series;
                      Bonn ASCII data not accepted as Safi FeatFlow;
                      velocity observable unresolved; no grid/time-step
                      sensitivity; best Bonn center/velocity errors and
                      velocity cross-check exceed provisional strict thresholds
claim_limit = does not validate rho772 impact, contact-angle sweep, dry-wall
              or liquid-film target cases, Wang 2023 equivalence, or
              publication readiness
local_raw_vti_pvti_count = 0
```

A1 grid/time sensitivity completed chain, 2026-06-07:

```text
case_dir = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\a1_bubbleRise_grid_time_20260607
manifest = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\a1_bubbleRise_grid_time_20260607\tclb_bubbleRise_A1_grid_time_20260607_manifest.json
case_generator = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_a1_bubbleRise_sensitivity_cases.py
summary_script = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\a1_bubbleRise_grid_time_summary.py
artifact = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_bubbleRise_A1_grid_time_20260607
remote_run_root = /home/yuan/runs/tclb_bubbleRise_A1_grid_time_20260607
completed_cases = coarse_L48, base_L64, fine_L80
status = runtime_sanity
remote_raw_counts = 7 VTI and 7 PVTI per case
remote_sizes = coarse_L48 about 131M; base_L64 about 231M; fine_L80 about 538M
runtime_health =
  coarse_L48 max Mach 0.0317124, nonfinite 0,
             fluid phase/rho drift 4.07186e-5 / 3.65341e-5
  base_L64   max Mach 0.0223497, nonfinite 0,
             fluid phase/rho drift 2.93937e-5 / 2.63515e-5
  fine_L80   max Mach 0.0179932, nonfinite 0,
             fluid phase/rho drift 1.69536e-5 / 1.52111e-5
comparison_artifacts =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_bubbleRise_A1_grid_time_20260607_coarse_L48_bonn_compare
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_bubbleRise_A1_grid_time_20260607_base_L64_bonn_compare
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_bubbleRise_A1_grid_time_20260607_fine_L80_bonn_compare
grid_time_spreads =
  center_of_mass_l2_abs_error_spread 0.0220774
  center_of_mass_max_abs_error_spread 0.0292512
  rise_velocity_l2_abs_error_spread 0.0349694
  rise_velocity_max_abs_error_spread 0.0427376
acceptance_gate = rerun with grid-time summary; still runtime_sanity
claim_limit = completed sensitivity input only; spread and velocity-observable
              checks fail provisional gates, so no A1 validation promotion is
              supported
local_raw_vti_pvti_count = 0
```

| static contact-angle calibration, official TCLB ContactAngle-derived theta=45/90/135, exploratory and not accepted yet | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_static_contact_angle_calib_20260607_theta045`, `...\theta090`, `...\theta135`; each contains curated `analysis_contact_angle_v3`; v3 summary `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_calib_20260607_v3_summary.json`; convention audit `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_convention_audit_20260607`; older summary `...\static_contact_angle_calib_20260607_summary.json` | `/home/yuan/runs/tclb_static_contact_angle_calib_20260607/theta045`, `/theta090`, `/theta135`; v3 analysis under each `analysis_contact_angle_v3`; convention audit `/home/yuan/runs/tclb_static_contact_angle_calib_20260607/analysis_contact_angle_convention_audit` |
| low-angle static contact-angle response surface-energy sweep, exploratory and negative for substituting `radAngle=30/35` as liquid-side 45 | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_response_surface_energy_20260607`; includes `execution_report.md`, per-case XML/run logs/generated config XML/TCLB CSV log, per-case `analysis_contact_angle_response`, corrected convention audit under `analysis_contact_angle_convention_audit`, script copies, and `curated_no_raw.tgz`; local raw VTI/PVTI count is `0` | `/home/yuan/runs/tclb_static_contact_angle_response_surface_energy_20260607`; raw VTI/PVTI remain remote-only, 21/21 per angle, total remote size about `8.1G` |
| low-angle bracket 15/18/20/22/25/28, exploratory negative mass evidence | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_bracket_lowangle_20260607`; local raw VTI/PVTI count is `0`; combined report in `...\static_contact_angle_bracket_combined_20260607` | `/home/yuan/runs/tclb_static_contact_angle_bracket_lowangle_20260607`; raw VTI/PVTI remain remote-only, 21/21 per angle, total remote size about `8.1G` |
| lower bracket 5/10/12, exploratory weak angle bracket but failed mass/rho behavior | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_bracket_lower_20260607`; local raw VTI/PVTI count is `0`; combined report in `...\static_contact_angle_bracket_combined_20260607` | `/home/yuan/runs/tclb_static_contact_angle_bracket_lower_20260607`; raw VTI/PVTI remain remote-only, 21/21 per angle, total remote size about `4.1G` |
| low-angle bracket sensitivity with `M=0.025`, `IntWidth=6`, exploratory mixed/negative angle evidence | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\static_contact_angle_bracket_lowangle_M0025_W6_20260607`; includes `execution_report.md`, case XMLs, run logs, generated configs, TCLB CSV logs, per-case analysis, BOUNDARY-aware `analysis_contact_angle_bracket_M0025_W6_boundarymass`, convention audit, script copies, and `curated_no_raw.tgz`; local raw VTI/PVTI count is `0` | `/home/yuan/runs/tclb_static_contact_angle_bracket_lowangle_M0025_W6_20260607`; raw VTI/PVTI remain remote-only, 21/21 per angle, total remote size about `4.1G` |
| single radAngle=5 target-45 dry-wall exploratory pilot, negative/resting and mass evidence | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_rad005_target45_dropletsmooth_u008_M0025_W6_ext6400_20260607_rad005_target45`; includes README, XML, run.log, manifest, postprocess logs, metrics CSV, summary JSON, beta/mass/centroid/morphology figures, and script copy; local raw VTI/PVTI count is `0` | `/home/yuan/runs/tclb_z_wall_rho772_rad005_target45_dropletsmooth_u008_M0025_W6_ext6400_20260607/rad005_target45`; raw VTI/PVTI remain remote-only, 17/17, remote size about `939M` |
| z-wall smooth lower-velocity 9600-step coupled M0025/W6 diagnostic, exploratory negative evidence | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext9600_20260607_theta090` | `/home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext9600_20260607/theta090` |
| z-wall smooth lower-velocity 6400-step coupled M0025/W6 diagnostic, exploratory | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext6400_20260607_theta090` | `/home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_M0025_W6_ext6400_20260607/theta090` |
| z-wall smooth lower-velocity extended-window coupled M0025/W6 diagnostic, exploratory | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_ext3200_M0025_W6_20260607_theta090` | `/home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_ext3200_M0025_W6_20260607/theta090` |
| z-wall smooth lower-velocity extended-window IntWidth=6 sensitivity, exploratory | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_ext3200_W6_20260607_theta090` | `/home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_ext3200_W6_20260607/theta090` |
| z-wall smooth lower-velocity extended-window IntWidth-only sensitivity, exploratory | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_ext3200_W4_20260607_theta090` | `/home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_ext3200_W4_20260607/theta090` |
| z-wall smooth lower-velocity extended-window M-only sensitivity, exploratory | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_ext3200_M0025_20260607_theta090` | `/home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_ext3200_M0025_20260607/theta090` |
| z-wall smooth lower-velocity extended window, exploratory | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_ext3200_20260607_theta090` | `/home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_ext3200_20260607/theta090` |
| z-wall smooth lower-velocity near-wall contact, exploratory | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_u008_nearwall_20260607_theta090` | `/home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_u008_nearwall_20260607/theta090` |
| z-wall smooth droplet-velocity near-wall contact, exploratory | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_dropletsmooth_nearwall_20260607_theta090` | `/home/yuan/runs/tclb_z_wall_rho772_dropletsmooth_nearwall_20260607/theta090` |
| z-wall droplet-only near-wall contact, exploratory | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_dropletonly_nearwall_20260607_theta090` | `/home/yuan/runs/tclb_z_wall_rho772_dropletonly_nearwall_20260607/theta090` |
| z-wall low-Mach contact pilot, exploratory | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_lowmach_contact_20260607_theta090` | `/home/yuan/runs/tclb_z_wall_rho772_lowmach_contact_20260607/theta090` |
| z-wall smoke, exploratory | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_z_wall_rho772_pilot_20260607_theta090` | `/home/yuan/runs/tclb_z_wall_rho772_pilot_20260607/theta090` |
| current TCLB-local mirror | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_impact_rho772_drywall_explore_latest` | `/home/yuan/runs/tclb_impact_rho772_drywall_explore_latest` |
| historical D3Q27-era copy | `C:\Users\yuanz\Desktop\LBMCORE5\D3Q27\artifacts\tclb_impact_rho772_drywall_explore_v2_corrected` | older corrected copy, keep as history only |

Use the TCLB-local mirror for this project. Do not use the D3Q27-era copy as
the active artifact path.

Corrected fluid-only mass accounting for the five 3200-step z-wall theta=90
exploratory runs is summarized in:

```text
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\ext3200_fluidmass_summary.csv
```

Use `fluid_phase_*` metrics with `BOUNDARY==0` for bulk phase-mass diagnostics;
all-cell `phase_sum` includes wetting-wall ghost `PhaseF` and is diagnostic
only.

## 6. Local Case Templates

| Purpose | Path |
|---|---|
| case root | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases` |
| target dry-wall sweep | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\dry_wall\user_1mm_10mm_contact_angle_sweep` |
| static contact-angle calibration cases | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\static_contact_angle\contact_angle_theta*.xml` |
| geometric static grid-density contact-angle cases | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\static_contact_angle_geometric_grid_density_20260607` |
| near-wall XML template | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\dry_wall\user_1mm_10mm_contact_angle_sweep\pilot_near_wall_equivalent\impact_near_wall_template.xml` |
| z-wall smoke XMLs | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\dry_wall\user_1mm_10mm_contact_angle_sweep\pilot_near_wall_equivalent\impact_zwall_theta*_smoke.xml` |

## 7. Local References

| Source | Local path |
|---|---|
| Safi 2017 C&MA bubbleRise PDF/spec/data | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\references\papers\safi2017_camwa_3d_bubble_preprint.pdf`; gap/spec note `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\references\a1_bubbleRise_reference_gap_20260607.md`; digitization notes `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\references\data\a1_bubbleRise_safi2017_digitization_notes.md`; digitized TC1 FeatFlow Fig. 4/5 data `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\references\data\a1_bubbleRise_safi2017_reference.csv`; DOI `10.1016/j.camwa.2016.12.014`; existing A1 maps to TC1; digitized data are bitmap-derived and need audit before validation use |
| Adelsberger 2014 3D rising droplet benchmark provenance | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\references\papers\adelsberger2014_3d_rising_bubble_benchmark.pdf`; SHA256 `4153884D0A884A91EF176CB69F9138700E6C4B5993A7DEC460EC1C90FA48DB14`; extracted text `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\tmp\pdfs\safi2017\adelsberger2014_3d_rising_bubble_benchmark.txt`; provenance note `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\references\data\a1_bubbleRise_reference_provenance_20260607.md`; curated Bonn/INS TC1 ASCII data `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\references\data\bonn_3d_rising_bubble_tc1\bonn_3d_rising_bubble_tc1_reference.csv` with `5388` rows and summary JSON in the same folder; series names are `DROPS`, `NaSt3D`, and `OpenFOAM`, not Safi 2017 `FeatFlow` without audit |
| Wang 2023 IJMF PDF | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\references\papers\wang2023_ijmf_ucl.pdf` |
| Fei 2019 PoF PDF | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\references\papers\fei2019_pof_nmrt.pdf` |
| Wang 2024 JFM PDF | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\references\papers\wang2024_jfm_main.pdf` |
| Wang 2023 MinerU/VLM | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\references\extracted\wang2023_ijmf_d3q27_vlm.md` |
| Fei 2019 MinerU/VLM | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\references\extracted\fei2019_pof_nmrt_vlm.md` |
| Wang 2024 MinerU/VLM | `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\references\extracted\wang2024_jfm_main_vlm.md` |

## 8. Local Scripts

## q27 Geometric Phase-Field Calibration Route 20260608

```text
status = exploratory_not_validation
plan = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\docs\q27_geometric_phasefield_calibration_plan_20260608.md
execution_handoff = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\docs\q27_geometric_phasefield_execution_handoff_20260608.md
binary = /home/yuan/src/TCLB/CLB/d3q27_pf_velocity_q27_geometric/main
binary_sha256 = 7b8ad826493e262ecfa713a5ef90a47b61870a7467ce9bfe791dae76434ee066
build_log = /tmp/tclb_build_d3q27_pf_velocity_q27_geometric_20260608.log
compile_options = q27=TRUE, geometric=TRUE,
                  BGK/thermo/staircaseimp/isograd/tprec=FALSE
purpose = independent full-D3Q27 phase-field route for Laplace sigma
          calibration, static wetting audit, and Li impact analogue
claim_limit = not validation, not a replacement for the q15-geometric baseline,
              and not equivalent to Li Peisheng pseudopotential MRT or Wang
              2023 ULBM/NMRT
```

Stage-0 smoke queue:

```text
run_id = tclb_q27_geometric_stage0_laplace_smoke_20260608
remote_run_dir = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_stage0_laplace_smoke_20260608/R16
local_case = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\q27_geometric_calibration_20260608\stage0_laplace_smoke\q27_geometric_laplace_smoke_R16.xml
runner = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_start_q27_geometric_stage0_laplace_smoke_20260608.sh
queue_pid = 47747
queue_state_20260608_1551 = waiting for existing TCLB solver; current q15 Li
                            static-wetting batch was running theta090
queue_state_20260608_1638 = waiting for existing TCLB solver; current q15 Li
                            static-wetting batch was running theta100, with
                            theta110 still pending. This is a scheduling
                            blocker, not a q27 failure.
queue_state_20260608_1705 = q15 theta100 completed rc=0 and q15 theta110
                            started at 17:03:38 with solver PID 55672; q27
                            Stage0 still waiting_for_existing_solver and is
                            expected to start after theta110 completes
queue_state_20260608_1721 = q15 theta110 still running with solver PID 55672;
                            q27 Stage0 queue PID 47747 still waiting for
                            existing solver; GPU 100% busy and active disk
                            root has about 272G available
queue_state_20260608_1726 = q15 theta110 still running with solver PID 55672;
                            q27 Stage0 still waiting_for_existing_solver and
                            has no run.log, run.returncode, or
                            q27_stage0_smoke_summary.json yet
queue_state_20260608_1750 = q27 Stage0 solver completed rc=0; initial gate
                            script failed because R16/analysis did not exist
                            before redirection. Gate script fixed and
                            restarted; postprocess completed; Stage0 gate
                            passed and Stage1 started at 17:49:10 +08.
local_curated_artifacts = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\q27_geometric_calibration_20260608\stage0_laplace_smoke_R16
summary_json = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_stage0_laplace_smoke_20260608/R16/analysis/q27_stage0_smoke_summary.json
metrics_csv = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_stage0_laplace_smoke_20260608/R16/analysis/q27_stage0_smoke_metrics.csv
morphology_png = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_stage0_laplace_smoke_20260608/R16/analysis/q27_smoke_morphology_step_00002000.png
case = 81^3 periodic Laplace-style droplet, R=16,
       sigma_input=0.003892733564013841, M=0.025, IntWidth=6,
       2000 steps, VTK interval 1000
raw_policy = raw VTI/PVTI remote-only
```

Prepared but not launched q27 calibration stages:

```text
stage1_single_sigma_cases =
  local: C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\q27_geometric_calibration_20260608\stage1_laplace_single_sigma
  remote: /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_stage1_laplace_single_sigma_20260608
  local_curated_artifacts: C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\q27_geometric_calibration_20260608\stage1_laplace_single_sigma
  cases: 121^3, R=16/20/24, sigma_input=0.003892733564013841,
         M=0.025, IntWidth=6, 4000 steps, VTK interval 2000
  state_20260608_1754: all solver returncodes 0; postprocess returncode 0;
                       Laplace R2=0.9987003195771007,
                       sigma_eff=0.0031714316784367457,
                       nonfinite=0, max Mach=4.968369683008567e-05;
                       Stage1 gate passed and Stage2 started at 17:53:00 +08

stage2_sigma_sweep_cases =
  local: C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\q27_geometric_calibration_20260608\stage2_sigma_sweep
  remote: /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_stage2_sigma_sweep_20260608
  local_curated_artifacts: C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\q27_geometric_calibration_20260608\stage2_sigma_sweep
  cases: 4 sigma values x R=16/20/24, 121^3, M=0.025, IntWidth=6,
         4000 steps, VTK interval 2000
  sigma values: 0.0019463667820069205, 0.003892733564013841,
                0.005839100346020761, 0.007785467128027682
  state_20260608_1754: running; started by Stage1 gate at
                       2026-06-08T17:53:00+08:00; case_count=12
  state_20260608_1803: completed; 12/12 solver rc=0, 4/4 per-sigma
                       postprocess rc=0; global calibration R2=0.999999936842248;
                       A_q27=1.6279932875649252,
                       B_q27=4.533658854592553e-06,
                       min per-sigma R2=0.9986628042509424,
                       nonfinite=0, max Mach=0.00010116859490204438;
                       Stage2 gate passed and Stage3 started at 18:02:08 +08

stage3_static_wetting_cases =
  local: C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\q27_geometric_calibration_20260608\stage3_static_wetting_70_110
  remote: /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_stage3_static_wetting_70_110_20260608
  layout: R50_W6_N121x121x121/theta###
  cases: radAngle=70/80/90/100/110 deg, 121^3, R=50,
         M=0.025, IntWidth=6, 200000 steps, VTK interval 200000
  postprocess_update_20260608_1654: the remote Stage-3 runner now runs
                                    two-row contact-angle postprocess for
                                    phi=0.45, 0.50, and 0.55 into separate
                                    analysis directories instead of only
                                    phi=0.50
  postprocess_update_20260608_1710: the two-row audit script no longer
                                    hard-codes the historical geometric grid
                                    density run id; it derives run_id from
                                    the active run root. The Stage-3 runner
                                    now also writes
                                    analysis_two_row_phi_sensitivity_summary/
                                    q27_static_wetting_phi_sensitivity_summary.json
  read_only_gate_20260608_1717:
    local_script: C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_q27_stage3_static_wetting_gate.py
    remote_script: /tmp/tclb_q27_stage3_static_wetting_gate.py
    purpose: read-only gate after Stage 3; checks run.returncode/run.done and
             q27_static_wetting_phi_sensitivity_summary.json before allowing
             Stage-4 exploratory impact. It does not auto-launch Stage 4.
  state_20260608_1803: running; started by Stage2 gate at
                       2026-06-08T18:02:08+08:00 with theta070 first
  local_curated_artifacts: C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\q27_geometric_calibration_20260608\stage3_static_wetting_70_110
  state_20260608_2040: completed; 5/5 rc=0; phi=0.45/0.50/0.55 postprocess
                       rc=0; read-only gate allowed Stage4 exploratory only;
                       max angle error=1.4417 deg, max phi span=0.3700 deg,
                       max spread=0.0860 deg

support_scripts =
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_laplace_pressure_postprocess_q27.py
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_q27_sigma_sweep_calibration_summary.py
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_q27_static_wetting_phi_sensitivity_summary.py
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_q27_stage3_static_wetting_gate.py
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_q27_stage0_smoke_postprocess.py
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_start_q27_geometric_laplace_batch_20260608.sh
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_postprocess_q27_stage0_smoke_20260608.sh
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_gate_q27_stage0_then_start_stage1_20260608.sh
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_q27_geometric_li_impact_case.py
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_start_q27_geometric_static_wetting_20260608.sh
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_gate_q27_stage1_then_start_stage2_20260608.sh

launch_rule = do not launch Stage 1 until Stage 0 smoke has returncode 0,
              nonfinite=0, healthy mass/rho/Mach, and no obvious morphology
              failure. Do not launch Stage 2 or Stage 3 until Stage 1 has a
              usable Laplace-law result. Do not generate or launch Stage 4
              impact until Stage 2 provides a q27-calibrated sigma_input.

gate_watcher =
  remote_script: /tmp/hm570_gate_q27_stage0_then_start_stage1_20260608.sh
  pid: 51398
  log: /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_stage0_laplace_smoke_20260608/stage0_to_stage1_gate.log
  status_20260608_1614: waiting for Stage-0 run.returncode while q15 Li
                        static-wetting theta090 solver occupies GPU
  status_20260608_1638: still waiting for Stage-0 run.returncode while q15
                        Li static-wetting theta100 solver occupies GPU
  gate: run.returncode=0, postprocess succeeds, nonfinite=0, Mach<0.1,
        max phase drift<2%, max rho drift<2%

stage1_to_stage2_gate_watcher =
  remote_script: /tmp/hm570_gate_q27_stage1_then_start_stage2_20260608.sh
  pid: 52807
  log: /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_stage1_laplace_single_sigma_20260608/stage1_to_stage2_gate.log
  status_20260608_1630: waiting for Stage-1 analysis/laplace_summary.json
  status_20260608_1638: still waiting for Stage-1 analysis/laplace_summary.json;
                        Stage 1 has not started because Stage 0 has not run
  gate: all Stage-1 run.returncode=0, postprocess.returncode=0,
        nonfinite=0, R2>=0.995, Mach<0.1
  action_if_passed: start Stage-2 sigma sweep using
                    /tmp/hm570_start_q27_geometric_laplace_batch_20260608.sh

stage2_to_stage3_gate_watcher =
  local_script: C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_gate_q27_stage2_then_start_stage3_20260608.sh
  remote_script: /tmp/hm570_gate_q27_stage2_then_start_stage3_20260608.sh
  pid: 54622
  log: /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_stage2_sigma_sweep_20260608/stage2_to_stage3_gate.log
  status_20260608_1649: waiting for Stage-2 sigma summaries; sigma_dirs=4,
                        ready=0 because Stage 2 has not started yet
  gate: all Stage-2 run.returncode=0, all per-sigma postprocess.returncode=0,
        global sigma calibration R2>=0.995, each per-sigma Laplace R2>=0.995,
        nonfinite=0, Mach<0.1
  action_if_passed: write
                    analysis_sigma_calibration/q27_sigma_sweep_calibration_summary.json
                    and start Stage-3 static wetting using
                    /tmp/hm570_start_q27_geometric_static_wetting_20260608.sh

stage4_impact_generator =
  local_script: C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_q27_geometric_li_impact_case.py
  status: prepared only; no XML generated yet
  required_input: --sigma-input from Stage-2 q27 sigma sweep calibration
  purpose: generate Li Re600/We11.56 theta090 impact analogue using calibrated
           q27 sigma_input, U default 0.025, D=50, rho_ratio=720,
           viscosity_ratio=15, beta_box as primary Li D*/D analogue
  local_curated_artifacts: C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\q27_geometric_calibration_20260608\stage4_li_re600_we1156_theta090_impact
  state_20260608_2047: completed exploratory impact; solver rc=0,
                       postprocess rc=0; sigma_input_calibrated=0.003318220521467378;
                       first_contact_step=1200; beta_area_max=1.5113542745679722
                       at step 3600; beta_box_max=1.50 at step 3200;
                       max fluid-only phase drift=0.009671975908382707;
                       last fluid-only phase drift=-0.005429629323428565;
                       last rho drift=-0.005175595246472212;
                       max Mach=0.07189888851522883; nonfinite=0;
                       resting_candidate=false

stage4_calibrated_handoff =
  local_calibrated_generator: C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_q27_geometric_li_impact_from_calibration.py
  remote_calibrated_generator: /tmp/make_q27_geometric_li_impact_from_calibration.py
  remote_case_generator: /tmp/make_q27_geometric_li_impact_case.py
  local_runner: C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_start_q27_geometric_li_impact_20260608.sh
  remote_runner: /tmp/hm570_start_q27_geometric_li_impact_20260608.sh
  status_20260608_1702: scripts uploaded and checked; not launched
  calibration_formula: sigma_input_target = (2*sigma_eff_target - B_q27) / A_q27
  launch_condition: Stage-2 q27 calibration summary exists, Stage-3 static
                    wetting evidence is reviewed, and main agent explicitly
                    starts Stage 4; do not auto-launch Stage 4
```

## 8. Script Index

| Script | Purpose |
|---|---|
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_impact_drywall_postprocess.py` | dry-wall beta/mass/Mach/nonfinite/morphology postprocessing, including z-wall panels |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_bubble_rise_postprocess.py` | existing-output A1 bubbleRise metrics, mass/Mach/nonfinite, centroid, and morphology postprocessing |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_tclb_z_wall_pilot_cases.py` | generate exploratory z-wall rho772 smoke XMLs and manifest |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_tclb_static_contact_angle_cases.py` | generate official TCLB ContactAngle-derived static calibration XMLs and manifest |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_tclb_static_contact_angle_geometric_grid_density_cases.py` | generate the 15-case geometric static contact-angle grid-density/arclength audit matrix under DATA500; all outputs remain `exploratory_not_validation` |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_run_static_contact_angle_grid_density_batch.sh` | HM570 batch runner for the geometric static grid-density matrix; derives each case directory from the XML `output` attribute so logs and return codes are per-theta, not overwritten at grid-tag level |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_static_contact_angle_arclength_audit.py` | contact-line anchored arclength tangent audit for static cases; fits along the phi contour from the contact-line endpoint instead of using only wall-normal height bands |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_static_contact_angle_grid_density_batch_summary.py` | after the 15-case geometric static batch completes, orchestrates static-health and arclength postprocess, then writes one summary CSV/JSON without copying raw VTI/PVTI locally |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_static_contact_angle_postprocess.py` | fit static contact-angle contour and report apparent angle, mass/rho drift, Mach, nonfinite, and figures |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_static_contact_angle_convention_audit.py` | existing-output-only sensitivity audit for static contact-angle fit convention across slice axis, wall location, and wall-distance filters |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\a1_bubbleRise_compare_safi2017.py` | digitizes Safi 2017 TC1 FeatFlow Fig. 4/5 curves from rendered PDF page, compares against A1 metrics/TCLB CSV log, and writes pre-audit comparison CSV/JSON/figures |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\a1_bubbleRise_independent_digitization.py` | independent 600 dpi Safi Fig. 4/5 red-curve digitization check; writes separate audit CSV/JSON/Markdown without overwriting primary reference CSV |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\a1_bubbleRise_download_bonn_reference.py` | downloads Bonn/INS archived Adelsberger 2014 TC1 center-of-mass and rise-velocity ZIP files, curates DROPS/NaSt3D/OpenFOAM ASCII rows, and compares them against the current Safi bitmap digitization without promoting A1 validation status |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\a1_bubbleRise_compare_bonn_reference.py` | compares existing TCLB A1 output against curated Bonn/INS TC1 DROPS/NaSt3D/OpenFOAM ASCII data using center-of-mass, TCLB CSV velocity proxy, and saved-frame centroid interval velocity; writes pre-audit CSV/JSON/figures without promoting A1 validation status |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\a1_bubbleRise_acceptance_gate.py` | reads existing A1/Bonn/Safi summary JSON and audit notes, applies the A1 acceptance protocol, and writes a machine-readable `runtime_sanity` gate result without running TCLB or copying raw VTI/PVTI |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_a1_bubbleRise_sensitivity_cases.py` | generates A1 TC1 L0=48/64/80 grid/time sensitivity XML cases and manifest while preserving Re/Eo/rho-ratio/viscosity-ratio controls and aligned final nondimensional time |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\a1_bubbleRise_grid_time_summary.py` | reads the A1 grid/time manifest and per-case Bonn comparison summaries, writes sensitivity spread metrics when available, and explicitly reports missing inputs before HM570 runs |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_migrate_runs_to_data500.py` | prints a safe HM570 migration shell script for `/home/yuan/runs -> /media/yuan/DATA500/runs`; defaults to dry-run rsync with disk health checks, and never deletes the old run tree |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\geometric_static_revised_gate_candidate.py` | existing-output-only generator for the geometric static two-metric gate candidate; reads the 45/90/135 local/global artifacts and writes `static_contact_angle_geometric_revised_gate_candidate_20260607` without promoting validation |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_li_peisheng_laplace_pf_cases.py` | generates single-sigma TCLB phase-field Laplace-law analogue cases for Li Peisheng section 1.3 under `li_peisheng_re600_we1156_ca90_20260608`; status remains `exploratory_not_validation` |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_li_peisheng_laplace_sigma_sweep_pf_cases.py` | generates 3-sigma x 3-radius TCLB phase-field sigma-sweep Laplace analogue cases for Li Peisheng section 1.3; this maps tunability but is not Li pseudopotential k-equivalence |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_start_li_peisheng_laplace_sigma_sweep_pf_20260608.sh` | HM570 runner for the Li Peisheng sigma-sweep analogue; copies per-radius XML to run dirs, runs geometric TCLB, and postprocesses each sigma group |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_li_peisheng_static_wetting_pf_cases.py` | generates R32/W6 TCLB geometric static-wetting analogue cases for Li Peisheng 70/80/90/100/110 degree wall-wetting mapping |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_start_li_peisheng_static_wetting_pf_20260608.sh` | HM570 runner for Li Peisheng 70-110 degree static-wetting analogue and two-row contact-angle postprocess |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_q27_geometric_laplace_smoke_case.py` | generates Stage-0 q27+geometric runtime smoke XML and manifest; status remains `exploratory_not_validation` |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_start_q27_geometric_stage0_laplace_smoke_20260608.sh` | HM570 queue runner for the q27+geometric Stage-0 Laplace smoke; waits for existing TCLB solver processes before launching |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_q27_stage0_smoke_postprocess.py` | postprocesses q27 Stage-0 smoke into summary JSON, metrics CSV, mass/rho/Mach/nonfinite, and final morphology PNG |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_laplace_pressure_postprocess_q27.py` | q27 Laplace postprocess with corrected convention: `laplace_slope = 2*sigma_eff` |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_q27_geometric_laplace_cases.py` | generates q27+geometric Stage-1 121^3 single-sigma multi-radius Laplace cases |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_q27_geometric_sigma_sweep_cases.py` | generates q27+geometric Stage-2 sigma-input sweep cases for `sigma_input -> laplace_slope -> sigma_eff` calibration |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_q27_sigma_sweep_calibration_summary.py` | summarizes q27 sigma sweep into `laplace_slope = A_q27*sigma_input + B_q27` and `sigma_eff=(A*sigma+B)/2` |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_q27_geometric_static_wetting_cases.py` | generates q27+geometric Stage-3 radAngle 70/80/90/100/110 static wetting cases |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_start_q27_geometric_laplace_batch_20260608.sh` | generic q27 Laplace batch runner for Stage 1 and Stage 2, using the corrected q27 postprocess script |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_postprocess_q27_stage0_smoke_20260608.sh` | remote helper that postprocesses q27 Stage-0 smoke after solver returncode 0 |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_gate_q27_stage0_then_start_stage1_20260608.sh` | remote gate watcher; after Stage 0 passes finite/Mach/mass gates, starts Stage 1 single-sigma Laplace batch |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_q27_geometric_li_impact_case.py` | generates q27+geometric Li Re600/We11.56 theta090 impact XML only after a calibrated `--sigma-input` is supplied from Stage 2 |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_q27_geometric_li_impact_mw_sweep.py` | generates the q27 Li-impact 4000-step `M` x `IntWidth` dynamic-wetting diagnostic matrix |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_run_q27_li_impact_mw_sweep_4000.sh` | HM570 runner for the q27 Li-impact `M` x `IntWidth` sweep, including standard impact postprocess and wetting-contact event audit |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\summarize_q27_li_impact_mw_sweep.py` | summarizes q27 Li-impact `M` x `IntWidth` sweep into CSV/JSON/PNG comparison tables |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_impact_wetting_contact_event_audit.py` | read-only q27 impact dynamic-wetting audit that separates z=0 wall-ghost phase from first/second fluid layers and flags center-gas plus outer-liquid-ring contact events |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_center_void_scale_audit.py` | read-only center low-phase footprint scale audit for dimple/entrapped-air diagnostics; reports closed-annular center low-phase diameters in lu/um and draws 100 um bubble / 150 um dimple reference overlays |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_q27_geometric_10ul_top10mm_theta57_case.py` | generates the exploratory q27+geometric 10 uL, droplet-top-to-wall 10 mm, theta57 gravity-driven impact case with checkpoint/restart |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_run_single_q27_impact_with_postprocess.sh` | generic HM570 single-case q27 impact runner with checkpointed solve, standard dry-wall postprocess, and wetting-contact event audit |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_vti_finiteness_gate.py` | raw-field finite-value gate for TCLB VTI output; checks CSV NaN/Inf and fluid-cell `PhaseField,U,P,Rho` before morphology use |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_run_single_q27_impact_with_finiteness_gate.sh` | HM570 single-case runner that runs the finite-field gate before impact morphology postprocess and wetting audit |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_q27_geometric_10ul_theta57_tail_stability_matrix.py` | generates the six-case 10 uL theta57 composite-tail stability matrix for sphere/tail-geometry/tail-velocity A/B checks |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_run_q27_tail_stability_matrix_with_gate.sh` | HM570 matrix runner that gates each composite-tail stability case before optional postprocess |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_start_q27_geometric_static_wetting_20260608.sh` | q27+geometric Stage-3 static wetting runner for 70/80/90/100/110 cases plus two-row contact-angle postprocess |
| `C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_gate_q27_stage1_then_start_stage2_20260608.sh` | remote gate watcher; after Stage 1 Laplace passes run/postprocess/nonfinite/R2/Mach gates, starts Stage 2 sigma sweep |

10 uL theta57 dimple-refinement update, 2026-06-09:

```text
R50_probe =
  status = failed_negative_evidence
  remote = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_10ul_theta57_dimple_refinement_R50_probe_20260609/theta057_R50_W6_U0p015_nearwall
  result = 320x320x192 / 19.66M cells failed during initialization on the
           Tesla P100 16GB with `out of memory in cross.cu at line 83`;
           do not relaunch R50+ on one P100 without multi-GPU decomposition
           or a different memory strategy

R40_nearwall_refinement =
  status = exploratory_not_validation
  remote = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_10ul_theta57_dimple_refinement_R40_20260609/theta057_R40_W6_U0p015_nearwall
  local = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\q27_geometric_10ul_theta57_dimple_refinement_R40_20260609\theta057_R40_W6_U0p015_nearwall
  case = q27 geometric 10 uL theta57 near-wall equivalent, R=40, W=6,
         grid=256x256x160, U_lu=0.015, M=0.01, 12000 steps, VTK 400
  scale = dx=33.4126 um, IntWidth=200.5 um; still not enough to resolve a
          20-100 um physical air bubble cleanly
  metrics = run/post/wetting/center-scale rc all 0; nonfinite 0;
            max Mach 0.0600791; max fluid-only phase drift 1.10975%;
            beta_area_max 1.93764; beta_box_max 1.9375
  center_void = first-fluid closed-annular center low-phase at step 1600,
                equivalent diameter about 728 um; second/third fluid layers
                reach about 502 um. These values are much larger than the
                literature-order 20-100 um bubble diameter and about 150 um
                dimple lateral scale, so the center feature remains a
                numerical/wetting/gas-drainage/grid diagnostic, not resolved
                physical bubble evidence
  cleanup = curated artifacts synced locally; remote raw VTI/PVTI/checkpoint
            .pri deleted; remote case reduced from about 32G to about 7.7M
```

Important VTK convention:

```text
VTK cell data order is x fastest, then y, then z.
```

## 9. Do-Not-Copy Data

Do not copy these locally by default:

```text
/home/yuan/src/TCLB entire source tree
/home/yuan/runs/*/output/*.vti
/home/yuan/runs/*/output/*.pvti
complete raw output/ VTK dumps
failed-run intermediate VTI sequences
long production-run full 3D field series
```

Copy locally by default:

```text
case XML
generated config XML when important
run.log
TCLB CSV log if used for metrics
metrics CSV
summary JSON
figures
README/status marker
```

The first exploratory run directory is about `608M`; each VTI is about
`55 MiB`, so local mirrors should stay curated.

## 10. Composite Sphere-Tail Initializer Patch

2026-06-09 status: `exploratory_not_validation`.

The HM570 `d3q27_pf_velocity` source now includes an optional composite
droplet initializer for a volume-conserved spherical body plus a `+Z` top
cylinder tail:

```text
source = /home/yuan/src/TCLB/models/multiphase/d3q27_pf_velocity
patched files = Dynamics.R, Dynamics.c.Rt
remote backups = Dynamics.R.pre_composite_tail_20260609,
                 Dynamics.c.Rt.pre_composite_tail_20260609
rebuilt binary = /home/yuan/src/TCLB/CLB/d3q27_pf_velocity_q27_geometric/main
sha256 = 66df9caf87a5b4051ad306ed87456cdfc7b62b6f4c73a86ccd825f03beb77c01
build_log = /tmp/tclb_build_d3q27_pf_velocity_q27_geometric_composite_tail_20260609.log
```

New XML parameters are default-off:

```text
CompositeDropletTailRadius
CompositeDropletTailLength
CompositeDropletBodyRadius
```

Smoke case:

```text
remote = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_composite_tail_smoke_20260609/R25_L8_rt5
local_case = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\exploratory\q27_geometric_composite_tail_smoke_20260609
local_artifact = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\tclb_composite_tail_patch_20260609
parameters = Radius=25 lu, CompositeDropletTailRadius=5 lu,
             CompositeDropletTailLength=8 lu,
             CompositeDropletBodyRadius=0 auto-solve
result = run rc 0; initial phi>0.5 bbox 49x49x57 lu; nonfinite 0;
         max initial Mach 0.0138564; raw VTI/PVTI remote-only
```

Tail-local velocity extension, 2026-06-09:

```text
status = exploratory_not_validation
new parameters = CompositeDropletTailVelocityMode,
                 CompositeDropletTailVelocityX/Y/Z
mode 0 = off
mode 1 = smooth near-uniform extra velocity over the top tail cylinder
mode 2 = smooth axial-ramp extra velocity from root to tail top
rebuilt binary = /home/yuan/src/TCLB/CLB/d3q27_pf_velocity_q27_geometric/main
sha256 = 3373620d4c4c8ba952a239bde02030d55ad5b8c5e0b637988bfcd05c111c58ba
build_log = /tmp/tclb_build_d3q27_pf_velocity_q27_geometric_tail_velocity_uniform_20260609.log
smoke = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_composite_tail_velocity_smoke_20260609/R25_L8_rt5_tailvz_m0p002_uniform_v2
smoke_setting = DropletVelocityZ=-0.008,
                CompositeDropletTailVelocityMode=1,
                CompositeDropletTailVelocityZ=-0.002
smoke_result = run rc 0; max speed 0.00964188 lu/step;
               max Mach 0.0167002; tail centerline Uz about -0.00964
               near the connected cylinder; liquid-weighted kinetic-energy
               increment versus same smooth base velocity about 0.2669%
```

Top-to-wall free-fall composite-tail dynamic test, 2026-06-09:

```text
status = failed_negative_evidence
case = 10 uL theta57 top-to-wall free fall, R25, IntWidth=4, M=0.01,
       tail radius=5 lu, tail length=8 lu,
       CompositeDropletTailVelocityMode=1,
       CompositeDropletTailVelocityZ=-0.002
requested output = VTK every 1000 steps, checkpoint every 5000 steps
final run = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_10ul_theta57_tail_vz_m0p002_long_fail100_20260609/theta057_R25_top10mm_10ul_tailL8_rt5_tailvz_m0p002_long_fail100
local artifact = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\q27_geometric_10ul_theta57_tail_vz_m0p002_long_fail100_20260609\theta057_R25_top10mm_10ul_tailL8_rt5_tailvz_m0p002_long_fail100
result = run rc 0 and wrote VTI/checkpoints, but direct VTI audit found
         nonfinite fluid fields from step 100 onward and blank morphology PNGs
         after step 0; do not use this run for physical shape comparison
next action = use this only as negative evidence; rerun tail dynamics through a
              stability gate, preferably near-wall-equivalent or retuned
              IntWidth/M/resolution settings before full free-fall comparison
cleanup_20260610 = after local curated artifacts were confirmed, raw
                   VTI/PVTI/checkpoint .pri were deleted from:
                   q27_geometric_10ul_top10mm_theta57_pilot_20260609
                   (153 files / 76.53 GiB),
                   q27_geometric_10ul_theta57_tail_vz_m0p002_long_fail100_20260609
                   (59 files / 35.98 GiB), and
                   q27_geometric_10ul_theta57_tail_velocity_probe_20260609
                   (69 files / 30.03 GiB). Total removed 281 files /
                   142.54 GiB. Remaining raw/checkpoint count is 0 in all
                   three cleaned roots; disk changed from 22G free / 98% used
                   to 164G free / 82% used.
raw_policy = local curated artifacts only for these cleaned roots; remote
             XML/log/CSV/JSON/PNG/restart XML/returncode provenance retained
```

Composite-tail finite-field stability matrix, 2026-06-09:

```text
status = failed_negative_evidence
report = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\docs\tail_stability_control_analysis_20260609.md
remote = /media/yuan/8A0E24070E23EAC1/runs/tclb_q27_geometric_10ul_theta57_tail_stability_matrix_20260609
local_artifact = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\q27_geometric_10ul_theta57_tail_stability_matrix_20260609
local_cases = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\exploratory\q27_geometric_10ul_theta57_tail_stability_matrix_20260609
gate_script = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_vti_finiteness_gate.py
case_matrix = sphere_W4_U0p025, sphere_W6_U0p015,
              tailgeom_W4_U0p025, tailgeom_W6_U0p015,
              tailvz_m0p002_W4_U0p025, tailvz_m0p002_W6_U0p015
gate_result = sphere controls passed raw PhaseField/U/P/Rho finite-field checks
              through step 1200; W4/U0.025 composite-tail geometry failed at
              CSV iteration 100 even without tail velocity; W4/U0.025 with
              TailVelocityZ=-0.002 failed the same way; W6/U0.015 tail geometry
              and tail velocity passed finite-field checks but max Mach was
              about 0.116-0.117
interpretation = the immediate instability is tail geometry plus W4/thin
                 interface/higher lattice scaling, not primarily the -0.002
                 tail velocity. W6/U0.015 remains only runtime_sanity for the
                 short pre-contact window because Mach exceeds the conservative
                 ceiling.
raw_policy = all raw VTI/PVTI/checkpoint files deleted after curated summaries;
             remote matrix is about 4.5 MB, local curated artifact about 0.38 MB
```

## 11. New-Conversation Bootstrap Prompt

Use this at the start of a new TCLB goal-mode conversation:

```text
You are the TCLB subproject agent. First read:
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\AGENTS.md
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\docs\tclb_path_index.md
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\docs\tclb_project_handoff.md
C:\Users\yuanz\Desktop\LBMCORE5\TCLB\docs\subagent_goal_operating_model.md

HM570 is the remote execution host. TCLB source is /home/yuan/src/TCLB.
Future run directories should be generated under
/media/yuan/8A0E24070E23EAC1/runs unless a later disk audit changes the active
root. `/home/yuan/runs` is an older compatibility symlink to DATA500. Windows
local storage should keep only cases, references, scripts, and curated
artifacts. Do not copy raw VTI dumps locally unless explicitly requested.
```

## 12. Official 3D Wetting Boundary Reproduction Plan

2026-06-09 status: `exploratory_not_validation` planning artifact.

```text
local_plan = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\docs\official_wetting_boundary_reproduction_plan_20260609.md
paper = Phase field lattice Boltzmann method for liquid-gas flows in complex
        geometries with efficient and consistent wetting boundary treatment
DOI = 10.1016/j.camwa.2025.03.014
journal = Computers & Mathematics with Applications 186, 101-129
authors = D. Sashko, T. R. Mitchell, L. Laniewski-Wollk, C. R. Leonardi
source_model = /home/yuan/src/TCLB/models/multiphase/d3q27_pf_velocity
benchmark_topics = droplet spreading on sphere; capillary intrusion;
                   droplet impact on sphere
variant_scope = surface-energy wetting, geometric wetting, staircase
                improvement, optional tprec for geometric staircase
current_blocker = exact numerical benchmark parameter tables/figures not yet
                  recovered from ScienceDirect/SSRN; public GitHub link
                  TravisMitchell/3D_PF_benchmarkCases cited in source returns
                  404 via GitHub API on 2026-06-09
calibration_gate = build/source audit; Laplace sigma_eff; planar static wetting;
                   sphere static wetting; M/IntWidth/grid sensitivity;
                   capillary intrusion; sphere impact
```

analysis_report = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\docs\wetting_boundary_article_analysis_20260609.md
extracted_text = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\tmp\wetting2025\article_visible_text.txt
metadata = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\tmp\wetting2025\preloaded_state.json
           C:\Users\yuanz\Desktop\LBMCORE5\TCLB\tmp\wetting2025\crossref.json
note = Local read-only literature analysis of Sashko et al. 2025 wetting
       boundary article. It records governing model, surface-energy/geometric/
       staircase methods, benchmark parameters, conclusions, and relevance to
       current planar rho_ratio=772 droplet-impact diagnostics. This is a
       literature artifact only and does not promote any run beyond
       exploratory_not_validation.

## 13. Project Audit And Next Plan 20260610

```text
local_audit = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\docs\project_audit_and_next_plan_20260610.md
status = read-only main-agent audit
scope = prior TCLB static wetting, q27 sigma calibration, rho772 dry-wall
        impact, 10 uL theta57 impact, center-void diagnostics, and official
        wetting-boundary reproduction route
main_conclusion = static near-wall wetting and q27 sigma calibration are useful
                  candidate evidence, but dynamic planar impact is not
                  validated because center low-phase/annular morphology remains
                  unresolved and official article benchmarks have not been
                  reproduced
next_gate = clean source/binary audit, then Sashko 2025 sphere-spread
            reproduction, then capillary intrusion, then short planar
            M/IntWidth/grid dynamic-wetting matrix before any target production
```

## 14. Literature-Driven Resolution Plan 20260610

```text
local_plan = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\docs\literature_driven_resolution_plan_20260610.md
status = planning artifact, exploratory_not_validation until executed/audited
basis = Sashko et al. 2025 wetting-boundary article plus current project audit
core_lessons = static angle is necessary but not sufficient; thin films below
               IntWidth/few-cell resolution are not trustworthy; M is a dynamic
               wetting parameter; use sigma_eff not sigma_input for We; beta
               postprocessing alone is not the remaining dominant issue
execution_gates = clean source/binary audit; sphere spread; capillary intrusion;
                  sphere impact; planar M/IntWidth/grid dynamic-wetting matrix;
                  low-We planar literature comparison; return to target runs
immediate_next_action = Gate A clean source/binary audit, then Gate B Sashko
                        sphere-spread reproduction
```

## 15. Sashko 2025 Non-Compute Preparation 20260610

```text
status = exploratory_not_validation
preparation_note = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\docs\sashko2025_noncompute_preparation_20260610.md
readme = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\sashko2025_preparation_20260610\README.md
scope = file/script/case preparation only; no TCLB solver run launched
current_remote_run_root = /mnt/8A0E24070E23EAC1/runs for current Sashko Gate A/B
                          execution; older /media/yuan/8A0E24070E23EAC1/runs
                          entries are historical unless remounted and audited
raw_policy = raw VTI/PVTI/checkpoint files remote-only by default
claim_limit = Gate A/B/C prepared files are not validation_passed,
              production_candidate, or publication_ready
```

Gate A source/binary audit preparation and current finding:

```text
script = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_audit_sashko2025_source_binaries.sh
remote_audit_dir = /mnt/8A0E24070E23EAC1/runs/tclb_sashko2025_gateA_source_binary_audit_20260610
local_curated_artifact = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\sashko2025_gateA_source_binary_audit_20260610
purpose = read-only source/binary provenance for /home/yuan/src/TCLB and
          d3q27_pf_velocity binaries; records patch state, Consts.h,
          options.R, SHA256, and compile-option evidence
hard_gate = must be closed before using sphere-spread or capillary results as
            validation evidence
finding_20260610 = source commit ded67cd768cf7e727bd078af139e3ec7895076e5;
                   Dynamics.R and Dynamics.c.Rt modified by default-off
                   exploratory initializer patches; initial audit used
                   nonexistent `_surface` target names, now corrected to
                   real TCLB targets d3q27_pf_velocity_q27 and
                   d3q27_pf_velocity_q27_staircaseimp; these corrected
    surface targets still need confirmed build/audit after
    HM570 connectivity recovers; tprec binary missing;
    geometric_q27 and geometric_q27_staircaseimp present
  local_validator_note =
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\sashko2025_precompute_package_validation_20260610.json
    package_ok=true after excluding the validator file itself from scans;
    C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\sashko2025_gateA_source_binary_audit_20260610\gateA_local_validation_summary.json
    now reports initial_gate_b_theta090_allowed_after_audit=true and
    validation_claim_allowed=false; all four required q27 binaries have
    expected paths/options/SHA evidence, while optional tprec remains missing;
    the validator discloses modified source state so Gate A is provenance
    evidence for exploratory Gate B only, not a validation claim
  refreshed_noncompute_artifact =
    remote: /home/yuan/tmp/tclb_sashko2025_gateA_source_binary_audit_20260610_noncompute
    local: C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\sashko2025_gateA_source_binary_audit_20260610_noncompute
    raw_vti_pvti_pri_count = 0
    result = geometric_q27 and geometric_q27_staircaseimp have matching
             binary paths, SHA256, and options.R evidence; surface_q27 and
             surface_q27_staircaseimp are still missing, so
             initial_gate_b_theta090_allowed_after_audit=false
```

Gate B sphere-spread preparation:

```text
local_case_dir = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\sashko2025_sphere_spread_20260610
remote_root = /mnt/8A0E24070E23EAC1/runs/tclb_sashko2025_sphere_spread_20260610
generator = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_sashko2025_sphere_spread_cases.py
postprocess = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_sashko2025_sphere_spread_postprocess.py
runner = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_prepare_sashko2025_sphere_spread.sh
runner_default = MODE=dry-run; no solver; creates/updates remote run root and
                 batch log, then lists XMLs
xml_count = 20
matrix = surface_q27, geometric_q27, surface_q27_staircaseimp,
         geometric_q27_staircaseimp x theta 30/60/90/120/130
setup = 128^3, R_d=R_s=24, rho*=1000, mu*=100, M=0.05,
        IntWidth=5, sigma_input=0.01, default periodic outer boundaries,
        solid wetting sphere
target_csv = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\sashko2025_sphere_spread_20260610\sashko2025_sphere_spread_eq57_targets.csv
primary_metric = h_star = h/(2 R_d) vs Eq.57 target
audit_caveat = Eq.57 implementation is based on visible article text and must
               be checked against paper notation before exact reproduction
staging = local XML/manifest/README/target CSV staged to the remote root for
          dry-run only; raw VTI/PVTI/checkpoints are not staged locally
partial_execution_20260610 =
  stopped_by_user at 19:38:56 +0800. Completed
  geometric_q27_staircaseimp/theta090 to 200000 with solver rc 0 and original
  postprocess rc 0; geometric_q27/theta090 was interrupted after a 160000-step
  VTK frame; surface_q27_staircaseimp/theta090 and surface_q27/theta090 were
  not started. Stop marker:
  /mnt/8A0E24070E23EAC1/runs/tclb_sashko2025_sphere_spread_20260610/USER_STOPPED_20260610_1908.txt
connected_component_review_20260610 =
  local artifact:
  C:\Users\yuanz\Desktop\LBMCORE5\TCLB\artifacts\sashko2025_sphere_spread_theta090_partial_20260610\geometric_q27_staircaseimp_theta090\analysis_sashko2025_sphere_spread_connected_review_v2
  remote analysis:
  /mnt/8A0E24070E23EAC1/runs/tclb_sashko2025_sphere_spread_20260610/geometric_q27_staircaseimp/theta090/analysis_sashko2025_sphere_spread_connected_review_v2
  result = corrected postprocess rejects the final frame height metric:
           raw global top_z=127 is a disconnected periodic/top component;
           the sphere-anchored component does not extend above solid_top_z,
           so metric_valid=false, h_star=null, and Eq.57 comparison is invalid.
  health = max Mach 0.00911368, nonfinite PhaseField/U/P/Rho all 0,
           LiqTotalPhase drift +0.18793%, TotalDensity drift -0.22865%.
  claim_limit = negative morphology/postprocess evidence only; not validation.
```

Gate C capillary-intrusion preparation:

```text
local_case_dir = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\sashko2025_capillary_intrusion_20260610
remote_root = /media/yuan/8A0E24070E23EAC1/runs/tclb_sashko2025_capillary_intrusion_20260610
generator = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\make_sashko2025_capillary_intrusion_cases.py
postprocess = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\tclb_sashko2025_capillary_intrusion_postprocess.py
runner = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\scripts\hm570_prepare_sashko2025_capillary_intrusion.sh
runner_default = MODE=dry-run; no solver; creates/updates remote run root and
                 batch log, then lists XMLs
xml_count = 64
matrix = four wetting variants; coarse 256x12x12/R=5 theta 20/40/60/80;
         refined 512x22x22/R=10 theta 20/60; refined M sweep
         theta 20/40/60/80 at M=0.025/0.05/0.075
front_protocol = C:\Users\yuanz\Desktop\LBMCORE5\TCLB\cases\validation\sashko2025_capillary_intrusion_20260610\sashko2025_capillary_intrusion_front_protocol.json
geometry_note = uses TCLB Pipe syntax confirmed from annularTaylorBubble_DasC;
                exact pipe mask must be audited before result interpretation
primary_metric = x_front(t), x_front^2(t), and Washburn/Eq.58 comparison after
                 excluding entrance phase and aligning at x/L=0.1
staging = local XML/manifest/README/front protocol staged to the remote root
          for dry-run only; raw VTI/PVTI/checkpoints are not staged locally
postprocess_note = capillary runner has a postprocess hook for
                   tclb_sashko2025_capillary_intrusion_postprocess.py only in
                   MODE=run/wait-run, not in dry-run
```
