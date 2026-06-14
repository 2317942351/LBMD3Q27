# HM570 Server Operational State

Date checked: 2026-06-15 00:51-00:59 CST

Host: `HM570`

Direct SSH path:

```text
ssh -i C:\Users\yuanz\Desktop\lbm-new\.ssh\id_ed25519 yuan@192.168.1.16
```

The `hm570` SSH alias may fail host-key validation in this workstation state.
Use the direct IP form until the alias known-host entry is repaired.

## Current Verdict

Historical build and Stage12 smoke records are real, but current server-side
computation is blocked because the data disks that contain the run tree and
built binary are not mounted.

Current GPUs are idle, but this is not sufficient to start work:

```text
0 Quadro P4000              19 MiB / 8192 MiB,   0% util
1 Tesla P100-PCIE-16GB       4 MiB / 16384 MiB,  0% util
2 Tesla P100-PCIE-16GB       4 MiB / 16384 MiB,  0% util
```

No active TCLB process matching `d3q27_pf_velocity`, `stage12`,
`TCLB_stage9`, or `case.xml` was found.

## Intended Operational Directories

Use the ASCII symlinks in scripts and logs. The symlink targets are
non-ASCII auto-mount names under `/media/yuan`; verify their literal values
with `readlink /home/yuan/data_sda` and `readlink /home/yuan/data_sdb` on the
server instead of hard-coding them from a Windows terminal.

Primary data symlink and run root:

```text
/home/yuan/data_sda
/home/yuan/data_sda/RUNS/runs
```

Secondary data symlink:

```text
/home/yuan/data_sdb
```

Historical compatibility symlink:

```text
/home/yuan/runs -> /media/yuan/DATA500/runs
```

Stage9 modified TCLB source and binary:

```text
/home/yuan/data_sda/RUNS/runs/stage9/src/TCLB_stage9_analytic_wetting_20260614/
/home/yuan/data_sda/RUNS/runs/stage9/src/TCLB_stage9_analytic_wetting_20260614/CLB/d3q27_pf_velocity_q27_geometric/main
```

Stage12 run roots:

```text
/home/yuan/data_sda/RUNS/runs/stage12_cap_static_smoke_20260614
/home/yuan/data_sda/RUNS/runs/stage12_native_static_axisfix_20260614
/home/yuan/data_sda/RUNS/runs/stage12_native_static
/home/yuan/data_sda/RUNS/runs/stage12
```

Scripts still accessible on the root/home disk:

```text
/home/yuan/build_stage9_capinit.sh
/home/yuan/build_stage9_capinit.log
/home/yuan/stage12_static_audit.py
/home/yuan/stage12_cap_static_run.py
/home/yuan/run_stage12_cap_static_smoke_20260614.sh
/home/yuan/stage12_native_static_run.sh
/home/yuan/run_stage12_native_static_audit_20260614.sh
/home/yuan/stage12_geometry_gate.py
/home/yuan/stage12_run.sh
/home/yuan/stage12_curved_angle.py
```

## Current Mount Evidence

`/media/yuan` is effectively empty:

```text
drwxr-x---+ 2 root root 4096 /media/yuan
```

`findmnt -R /home/yuan /media/yuan` returns no data-disk mounts.

`lsblk` shows the relevant data partitions with no mountpoint:

```text
sda2       2.7T    ntfs    UUID=348CE1818CE13DCC
sdb2       2.7T    ntfs    UUID=22684C9C684C7119
nvme0n1p3  930.8G  ntfs    UUID=10FEA576FEA5552E
```

`/etc/fstab` contains only these data-like entries:

```text
UUID=3d26f84e-cac2-4f0a-94be-295df6fd0257 /media/yuan/data500 ext4 defaults,nofail 0 2
/dev/disk/by-uuid/8A0E24070E23EAC1 /mnt/8A0E24070E23EAC1 auto nosuid,nodev,nofail,x-gvfs-show 0 0
```

The expected `/home/yuan/data_sda`, `/home/yuan/data_sdb`, and
`/home/yuan/runs` targets are therefore unusable in the current state.

## Direct Consequence

These currently fail because the target data tree is unavailable:

```text
/home/yuan/data_sda/RUNS/runs/stage9/src/TCLB_stage9_analytic_wetting_20260614/CLB/d3q27_pf_velocity_q27_geometric/main
/home/yuan/data_sda/RUNS/runs/stage12_cap_static_smoke_20260614/stage12_cap_static_smoke_summary_20260614.json
```

Therefore Stage9-Stage12 computation cannot be continued or reproduced on
the server until the relevant disks are mounted.

## Recovery Gate

Before launching any new computation, restore the mountpoints and then verify
the run tree by UUID rather than by duplicated NTFS labels:

```text
sda2 UUID=348CE1818CE13DCC -> target used by /home/yuan/data_sda
sdb2 UUID=22684C9C684C7119 -> target used by /home/yuan/data_sdb
```

After the mount is restored, run these read-only checks:

```bash
findmnt -R /home/yuan /media/yuan
readlink /home/yuan/data_sda
readlink /home/yuan/data_sdb
ls /home/yuan/data_sda/RUNS/runs
sha256sum /home/yuan/data_sda/RUNS/runs/stage9/src/TCLB_stage9_analytic_wetting_20260614/CLB/d3q27_pf_velocity_q27_geometric/main
ls /home/yuan/data_sda/RUNS/runs/stage12_cap_static_smoke_20260614
```

Expected historical binary SHA256:

```text
c046eb99e33192b379aad855fb2ab0222b72a9c7a1e63cc7d69389246e7eecd8
```

Only after these checks pass should Stage12 long static equilibrium gates be
started.
