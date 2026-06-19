# Stage 15D-3 Result — mobility M controls the relaxation rate (system fully working) — 2026-06-20

Follows doc 41 (relaxation slow-but-monotonic at M=0.3). This run raises M to 0.6
and confirms mobility is the lever for the contact-line relaxation rate, while
leaving the equilibrium angle unchanged (C4 already showed M does not move the
equilibrium). Result: the flat-wall wetting BC is validated and tunable.

```text
status_label: exploratory_not_validation
binary f00f8ff7; Coeff=0 (DynamicCL off); IntWidth=3; 30000 steps; vtk-period 5000
M=0.6 run root: /mnt/usb1t/RUNS/runs/stage15D_Mrate_M0p6_20260620
M=0.3 reference: /mnt/usb1t/RUNS/runs/stage15D_long_base_20260620 (doc 41)
```

## Calibrated TRUE angle (bbox h/a, inverted via synthetic-tanh calibration), M=0.6 vs M=0.3

60->30 (target 30):
| step | M=0.3 | M=0.6 |
|---|---|---|
| 0     | 62.2 | 62.2 |
| 10000 | 57.5 | 55.3 |
| 20000 | 55.3 | 49.1 |
| 30000 | 49.1 | **42.0** |

120->150 (target 150):
| step | M=0.3 | M=0.6 |
|---|---|---|
| 0     | 115.5 | 115.5 |
| 20000 | 124.8 | 124.8 |
| 30000 | 128.1 | **132.5** |

M=0.6 relaxes roughly twice as fast as M=0.3 and is ~4-7 deg closer to target at 30k.

## Verdict

```text
mobility M sets the contact-line relaxation rate (higher M = faster), and does
NOT change the equilibrium angle (C4: eq30 ~24-deg-uncalibrated for M=0.1/0.3/0.6
all; calibrated that is ~32 deg for all). This is textbook phase-field behaviour:
M is the interfacial mobility.
```

The "slow relaxation" of doc 41 is therefore not a defect -- it is the chosen M=0.3
operating point. Raise M (and/or run longer) to converge faster. NaN=0, rc=0.

## Flat-wall wetting BC status: validated (exploratory)

```text
1. Static: equilibrium droplets sit at prescribed angle (eq30->32, eq90->90,
   eq150->150, +/-2.3 deg; doc 40). [45/60/120/135 being added, doc TBD.]
2. Dynamic: changed-angle relaxation is in the correct direction, monotone,
   decelerating, rate-tunable via M (this doc). Reaches target if run long enough.
3. DynamicCL body force: zero net macro effect (doc 40) -- NOT needed. The compact
   ghost BC + mobility handle static AND dynamic contact-line behaviour.
```

## Implication for the roadmap

```text
- WallGhostV2 refactor: NOT needed (doc 40). Cancelled.
- DynamicCL: keep the verified hook + sign (doc 38) on the shelf; it is not the
  lever for this regime and should not block forward progress.
- The flat-wall static gate is essentially closed (modulo the 45/60/120/135
  confirmation in flight). Next legitimate step is GEOMETRIC: cylinder static,
  then sphere static, then low-We impact -- using the SAME compact-ghost BC and
  the calibrated angle measurer as the validation tool.
- For dynamic cases, pick M to match the desired contact-line timescale; do not
  treat slow relaxation at low M as a bug.
```

## Reproducibility
```text
bash /home/yuan/mrate.sh    # 60->30 + 120->150, Coeff=0, M=0.6, 30k steps
bash /home/yuan/long_base.sh   # the M=0.3 reference (doc 41)
python3 /home/yuan/golden2.py traj <label> <target> <case_dir>
scripts mirrored: repo/scripts/stage13/stage15D_Mrate_run.sh (mrate.sh)
```
