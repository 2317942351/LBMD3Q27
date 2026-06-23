#!/bin/bash
# C3 main (gpu1): ForceCap=0.5 amplitude. Safety eq30/t90/eq150 first; changed-angle only if gate PASS.
set -u
BIN=/home/yuan/src/TCLB_lbm2026_compile_lane/CLB/d3q27_pf_velocity_q27_geometric/main
ROOT=/mnt/usb1t/RUNS/runs/stage15C3_cap0p5_20260619
RUNNER=/home/yuan/stage13_flat_wall_diagnostic_run.py
INJECT=/home/yuan/inject_forcecap.py
A3=/home/yuan/analyze3.py
CAP=0.5
COMMON="--binary $BIN --dynamic-cl-mode 2 --cos-sign -1.0 --force-sign -1.0 --dynamic-cl-coeff 2 --int-width 3 --mobility 0.3 --iterations 4000 --vtk-period 500"
export PATH=/usr/local/cuda-12.6/bin:/usr/bin:/bin:/usr/local/bin
export LD_LIBRARY_PATH=/usr/local/cuda-12.6/lib64:${LD_LIBRARY_PATH:-}
export OMPI_MCA_plm_rsh_agent=/usr/bin/ssh CUDA_DEVICE_ORDER=PCI_BUS_ID

python3 "$RUNNER" --matrix equilibrium --root "$ROOT" $COMMON --gpu 1 --force >/dev/null 2>&1
python3 "$RUNNER" --matrix decoupled  --root "$ROOT" $COMMON --gpu 1 --force >/dev/null 2>&1
for c in diag_wall_t30 diag_wall_t90 diag_wall_t150 decouple_wall_60to30 decouple_wall_120to150; do
  python3 "$INJECT" "$ROOT/$c/case.xml" "$CAP" >/dev/null; done
echo "verify cap in t90:"; grep -E 'DynamicCLForceCap|DynamicCLForceSign|DynamicCLCoeff' "$ROOT/diag_wall_t90/case.xml"

run_one(){ ( cd "$ROOT/$1" || exit 9; export CUDA_VISIBLE_DEVICES=$2
  timeout 3000 "$BIN" case.xml > run.log 2>&1
  echo "[run] $1 rc=$? nan=$(grep -c NaN run.log)" ); }

echo "### C3 SAFETY eq30/t90/eq150 @ cap=$CAP"
run_one diag_wall_t30 1; run_one diag_wall_t90 1; run_one diag_wall_t150 1
python3 "$A3" "$ROOT/diag_wall_t30" 30 $CAP | tee "$ROOT/safety_t30.txt"
python3 "$A3" "$ROOT/diag_wall_t90" 90 $CAP | tee "$ROOT/safety_t90.txt"
python3 "$A3" "$ROOT/diag_wall_t150" 150 $CAP | tee "$ROOT/safety_t150.txt"

python3 - "$ROOT" <<'PY'
import sys
ROOT=sys.argv[1]
def datalines(fn):
    return [l.split() for l in open(ROOT+"/"+fn) if l.strip() and l.strip()[0].isdigit()]
def maxcol(fn,c):
    m=0
    for s in datalines(fn):
        try: m=max(m,int(float(s[c])))
        except: pass
    return m
def endcol(fn,c):
    dl=datalines(fn); return float(dl[-1][c]) if dl else float('nan')
# cols: 0step 1th_app 2|R| 3NaN 4n_act 5sumPF 6foot 7maxF 8capped% 9spur_fluid
nan=max(maxcol("safety_t30.txt",3),maxcol("safety_t90.txt",3),maxcol("safety_t150.txt",3))
spur=max(maxcol("safety_t30.txt",9),maxcol("safety_t90.txt",9),maxcol("safety_t150.txt",9))
th30=endcol("safety_t30.txt",1); th150=endcol("safety_t150.txt",1)
ok=(nan==0) and (spur==0) and (th30>=22.5) and (th150>=147.0)
print("GATE nan=%d spur_fluid=%d eq30_end=%.2f(base23.71) eq150_end=%.2f(base149.05) => %s"%(nan,spur,th30,th150,"PASS" if ok else "FAIL"))
open(ROOT+"/c3_gate.txt","w").write("PASS\n" if ok else "FAIL\n")
PY
GATE=$(cat "$ROOT/c3_gate.txt" 2>/dev/null)
echo "### C3 SAFETY GATE = $GATE"
if [ "$GATE" != "PASS" ]; then echo "C3_ABORT_SAFETY" > "$ROOT/marker"; echo "!! abort changed-angle"; exit 0; fi

echo "### C3 CHANGED-ANGLE @ cap=$CAP"
run_one decouple_wall_60to30 1; run_one decouple_wall_120to150 1
python3 "$A3" "$ROOT/decouple_wall_60to30" 30 $CAP | tee "$ROOT/traj_60to30.txt"
python3 "$A3" "$ROOT/decouple_wall_120to150" 150 $CAP | tee "$ROOT/traj_120to150.txt"
echo "C3_DONE" > "$ROOT/marker"
