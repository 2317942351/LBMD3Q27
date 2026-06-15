#!/bin/bash
# Post-process all Stage12 validation cases: convergence plots + angle time series
# + summary judgment. Run AFTER the 12-case orchestrator finishes.
#
# Usage: bash postprocess_stage12_validation_20260615.sh
set -u

RUNROOT=/mnt/usb1t/RUNS/runs/stage12_validation_20260615
CONV=/home/yuan/stage12_convergence_plot.py
ANG=/home/yuan/stage12_angle_timeseries.py
export PATH=/usr/local/cuda-12.6/bin:/usr/bin:/bin

echo "=== post-processing all cases in $RUNROOT ==="
echo "=== $(date) ==="

SUMMARY_JSON="$RUNROOT/validation_summary_20260615.json"

for d in "$RUNROOT"/*/; do
  name=$(basename "$d")
  case "$name" in
    smoke_*|*_QUICK) echo "  skip $name (test case)"; continue ;;
  esac

  # check the run actually finished
  if ! grep -q "RUN_RC=" "$d/run.log" 2>/dev/null; then
    echo "  SKIP $name (no RUN_RC, not finished)"
    continue
  fi
  rc=$(grep -oP 'RUN_RC=\K[0-9]+' "$d/run.log")
  if [ "$rc" != "0" ]; then
    echo "  SKIP $name (RUN_RC=$rc, failed)"
    continue
  fi

  echo ">>> processing $name"
  python3 "$CONV" "$d" 2>&1 | tail -3
  python3 "$ANG" "$d" 2>&1 | tail -8
done

echo ""
echo "=== building summary judgment ==="
python3 - "$RUNROOT" "$SUMMARY_JSON" <<'PYEOF'
import json, math, sys
from pathlib import Path
runroot = Path(sys.argv[1])
out = Path(sys.argv[2])
results = []
for d in sorted(p for p in runroot.iterdir() if p.is_dir()):
    name = d.name
    if name.startswith("smoke_") or name.endswith("_QUICK"):
        continue
    conv_j = d / f"{name}_convergence.json"
    ang_j = d / f"{name}_angle_timeseries.json"
    if not conv_j.exists() or not ang_j.exists():
        continue
    conv = json.load(open(conv_j))
    ang = json.load(open(ang_j))
    dec = conv.get("mode") == "DECOUPLE"
    init_t = conv.get("init_theta_deg", 0)
    bc_t = conv.get("bc_theta_deg", 0)
    ang_end = ang.get("theta_grad_end_deg", float("nan"))
    ang_drift = ang.get("theta_grad_end_drift_deg", float("nan"))
    mass_ok = conv.get("mass_converged", False)
    ke_ok = conv.get("ke_converged", False)
    converged = conv.get("converged", False)
    if dec:
        moved = abs(ang_end - bc_t) < abs(ang_end - init_t)
        verdict = "PASS_DECOUPLE" if (moved and converged) else ("PARTIAL_DECOUPLE" if moved else "FAIL_DECOUPLE")
    else:
        tol = 8.0
        near = abs(ang_end - bc_t) < tol
        verdict = "PASS_EQUILIBRIUM" if (near and converged) else ("PARTIAL_EQUILIBRIUM" if near else "FAIL_EQUILIBRIUM")
    results.append({
        "case": name, "geometry": conv.get("geometry"), "mode": conv.get("mode"),
        "init_theta_deg": init_t, "bc_theta_deg": bc_t,
        "theta_grad_end_deg": ang_end, "theta_grad_end_drift_deg": ang_drift,
        "mass_converged": mass_ok, "ke_converged": ke_ok, "converged": converged,
        "verdict": verdict,
    })
out.write_text(json.dumps(results, indent=2, sort_keys=True))
print(f"{'case':<32} {'mode':<12} {'geom':<9} {'init':>5} {'bc':>5} {'end':>7} {'conv':>5} verdict")
print("-"*95)
verdicts = {}
for e in sorted(results, key=lambda x: (x.get("geometry",""), x.get("mode",""), x.get("case",""))):
    v = e.get("verdict","?")
    verdicts[v] = verdicts.get(v, 0) + 1
    ae = e.get("theta_grad_end_deg", float("nan"))
    ae_s = f"{ae:7.1f}" if isinstance(ae, (int,float)) and math.isfinite(ae) else "    nan"
    print(f"{e['case']:<32} {e.get('mode','?'):<12} {e.get('geometry','?'):<9} {e.get('init_theta_deg',0):>5.0f} {e.get('bc_theta_deg',0):>5.0f} {ae_s} {str(e.get('converged',False))[:3]:>5} {v}")
print("-"*95)
for v, c in sorted(verdicts.items()):
    print(f"  {v}: {c}")
print(f"\nsummary json: {out}")
PYEOF
