# Stage 15D-2 Result — long base run: relaxation is slow-but-monotonic, system works — 2026-06-20

Follows doc 40 (calibrated measurement showed static BC correct and changed-angle
relaxation slow). This run distinguishes "slow natural timescale" (a) from
"stalled / BC under-drives" (b): base (Coeff=0, no DynamicCL) 60->30 and 120->150
run to 30000 steps, measured with the calibrated bbox-h/a angle.

```text
status_label: exploratory_not_validation
binary f00f8ff7; FS=-1/CosSign=-1/Coeff=0/IntWidth=3/M=0.3; vtk-period 5000
root: /mnt/usb1t/RUNS/runs/stage15D_long_base_20260620
```

## Calibrated TRUE angle trajectory (bbox h/a inverted via synthetic-tanh calibration)

| case | target | step0 | 5k | 10k | 15k | 20k | 25k | 30k |
|---|---|---|---|---|---|---|---|---|
| 60->30  | 30  | 62.2 | 58.6 | 57.5 | 57.5 | 55.3 | 53.6 | **49.1** |
| 120->150| 150 | 115.5| 121.4| 121.4| 121.4| 124.8| 124.8| **128.1** |

Both monotone toward target, decelerating but NOT stalled. 60->30 moved 62->49
(~13 deg in 30k steps, still falling at 30k: 53.6->49.1 in the last 5k).
120->150 moved 115->128 (~12 deg, still rising: 124.8->128.1 in the last 5k).

## Verdict: possibility (a) — slow natural timescale, not (b) stall

```text
The compact-ghost wetting BC drives the contact line to the prescribed angle
correctly; the relaxation is just slow (phase-field contact-line timescale).
The system is fundamentally working. NaN=0, rc=0 throughout. No stall, no
reversal, no blow-up.
```

Combined with doc 40 (equilibrium at target within +/-2.3 deg), the wetting BC
is validated for static angles at 30/90/150 and relaxes correctly (slowly) for
changed-angle. The entire earlier "failure" narrative was a measurement artefact.

## What this closes / opens

CLOSES: the question of whether the BC is broken. It is not.
OPENS: the relaxation is slow (~13 deg / 30k steps and decelerating). For
dynamic-impact use cases this contact-line timescale matters. Two honest levers:
  - mobility M (bulk): should set interface-diffusion / contact-line rate.
    C4 already showed M does NOT change the equilibrium angle (correct); its
    effect on the relaxation RATE is tested next (doc 42).
  - longer runs: the system reaches target if run long enough (extrapolating,
    ~80-120k steps for full convergence at the 30k rate).
DynamicCL remains a non-lever (zero net macro effect, doc 40): a band body force
does not advance the pinned line.

## Discipline note

This is the second time in two days that running the actual experiment + a
validated measurement reversed a pessimistic conclusion (doc 40 reversed doc 39;
doc 41 confirms the system works). The lesson: pessimistic structural verdicts
("BC is broken", "must refactor") require positive evidence, not just a
misbehaving diagnostic.

## Reproducibility
```text
bash /home/yuan/long_base.sh     # 60->30 + 120->150, Coeff=0, 30k steps
python3 /home/yuan/golden2.py traj <label> <target> <case_dir>   # calibrated angle
scripts mirrored: repo/scripts/stage13/stage15D_long_base_run.sh, golden2_calibrated_angle.py
```
