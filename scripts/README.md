# Scripts

Reusable postprocessing and run-management scripts for the TCLB project.

Current scripts:

```text
tclb_impact_drywall_postprocess.py
make_tclb_static_contact_angle_cases.py
tclb_static_contact_angle_postprocess.py
hm570_migrate_runs_to_data500.py
geometric_static_revised_gate_candidate.py
```

It reads TCLB `.vti` files and computes dry-wall:

```text
beta(t)
phase/rho mass drift
centroid
max velocity and Mach
morphology slices
summary JSON
```

The script assumes VTK image cell data ordering with x fastest, then y, then z.

`make_tclb_static_contact_angle_cases.py` generates official TCLB
`d3q27_pf_velocity` ContactAngle-derived calibration XMLs for theta 45/90/135.
`tclb_static_contact_angle_postprocess.py` fits the `PhaseField=0.5` contour in
the static contact-angle example and reports apparent angle, mass drift, Mach,
nonfinite count, and fit figures. These calibration outputs remain
`exploratory_not_validation` until read-only audit accepts the contact-angle
convention and mass behavior.

`hm570_migrate_runs_to_data500.py` prints a safe HM570 migration shell script
for moving future and migrated runs to `/media/yuan/DATA500/runs`. It defaults
to dry-run rsync and includes mount, dmesg, active-process, and write-health
checks. Use `--health-only` first after HM570 recovers from any storage-related
failure. Only `--execute --switch-symlink` prints a script that renames the old
run tree and creates `/home/yuan/runs -> /media/yuan/DATA500/runs`; it never
deletes the old `/home/yuan/runs` contents. Future case generators default to
`/media/yuan/DATA500/runs`.

`geometric_static_revised_gate_candidate.py` reads existing geometric static
45/90/135 local/global contact-angle artifacts and writes a two-metric gate
candidate under
`artifacts\static_contact_angle_geometric_revised_gate_candidate_20260607`.
It is existing-output-only and keeps the status at
`exploratory_not_validation`; it does not authorize validation promotion or
rho772 impact pilots.
