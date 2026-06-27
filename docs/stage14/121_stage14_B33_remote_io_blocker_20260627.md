# Stage14-B33 Remote I/O Blocker

Date: 2026-06-27

Branch: `work/phasefield-c-reference-20260623`

Status: B33 runtime not completed. This is an operations blocker, not a
numerical verdict.

## What Was Attempted

B33 first-bad-cell ledger was launched on the P100 server:

```text
server = yuan@192.168.1.16
gpu = CUDA_VISIBLE_DEVICES=1
initial root = /mnt/usb1t/RUNS/runs/stage14_B33_first_bad_ledger_20260627
binary = /home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
binary sha256 = 263bdd7bfc48e179dcab367f61481814b426682f96a32ddf2a6d96bb47d7d97b
```

The first probe started:

```text
L0_full
MomentumForceMode = 0
vtk_field_set = b33ledger
```

## Failure Mode

The solver/driver reached the analyzer phase, then `/mnt/usb1t` produced I/O
errors:

```text
Bus error ... stage14_b17_onset_mask_argmax.py
Input/output error writing L0_full_analyzer.status
Input/output error writing L0_full_light_artifact_manifest.txt
Input/output error from find/wc/deletion manifest paths
```

After that, SSH to `192.168.1.16` began failing during key exchange:

```text
kex_exchange_identification: read: Connection reset
Connection reset by 192.168.1.16 port 22
```

`Test-NetConnection` from Windows still reports TCP port 22 open, so the host
is reachable at the TCP level, but SSH handshakes are being reset.

## Interpretation

This is not evidence that B33 physics failed. It means the runtime root on
`/mnt/usb1t` became unreliable during the analyzer/write phase.

Do not use the incomplete B33 attempt to draw conclusions about:

```text
mu/lapPhi
F_surf
F_mu
F_total/rho
MRT force insertion
contact angle
dynamic impact
```

## Mitigation Already Added

`scripts/stage14/run_stage14_b33_first_bad_ledger_remote.sh` was updated so
the default root no longer hardcodes `/mnt/usb1t`. It now uses:

```text
ROOT_BASE=/mnt/win_sda2/RUNS/runs
ROOT=$ROOT_BASE/stage14_B33_first_bad_ledger_20260627
```

and falls back to:

```text
/home/yuan/runs/stage14_B33_first_bad_ledger_20260627
```

if `ROOT_BASE` is unavailable or not writable.

The B33 runner also now preserves `b33_argmax_trace.json`, because B34 replay
comparison requires first-bad-cell co-located `ReplayMF` and
`ReplayMomentumDeltaG`.

## Recovery Commands

After SSH works again:

```bash
ssh -i C:\Users\yuanz\Desktop\lbm-new\.ssh\id_ed25519 yuan@192.168.1.16 \
  "df -h /mnt/usb1t /mnt/win_sda2 /home; findmnt /mnt/usb1t /mnt/win_sda2"
```

Upload current scripts:

```powershell
scp -i C:\Users\yuanz\Desktop\lbm-new\.ssh\id_ed25519 `
  scripts/stage14/stage14_s2_replay_smoke.py `
  scripts/stage14/stage14_b17_onset_mask_argmax.py `
  scripts/stage14/stage14_b23_b24_matrix_digest.py `
  scripts/stage14/run_stage14_b33_first_bad_ledger_remote.sh `
  scripts/stage14/stage14_b34_mrt_replay_compare.py `
  yuan@192.168.1.16:/home/yuan/
```

Run B33 on a non-USB root:

```bash
CUDA_VISIBLE_DEVICES=1 ROOT_BASE=/mnt/win_sda2/RUNS/runs \
  bash /home/yuan/run_stage14_b33_first_bad_ledger_remote.sh
```

If `/mnt/win_sda2` is unavailable:

```bash
CUDA_VISIBLE_DEVICES=1 ROOT=/home/yuan/runs/stage14_B33_first_bad_ledger_20260627 \
  bash /home/yuan/run_stage14_b33_first_bad_ledger_remote.sh
```

## Required Next Evidence

B33 is incomplete until these files exist under the new root:

```text
stage14_B33.status
b33_matrix_digest.csv
b33_matrix_digest.json
L0_full/b33_key_summary.json
L0_full/b33_argmax_trace.json
L1_noFmu/b33_key_summary.json
L2_noSurf/b33_key_summary.json
L3_noPressure/b33_key_summary.json
L4_zeroForce/b33_key_summary.json
```

Then run B34 replay comparison against preserved argmax traces:

```bash
python /home/yuan/stage14_b34_mrt_replay_compare.py \
  /path/to/L0_full/b33_argmax_trace.json \
  --out /path/to/b34_replay_compare_L0_full.json
```
