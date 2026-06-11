#!/usr/bin/env bash
set -euo pipefail

# M-control for the PRE 2025 reduced sphere theta030 v6 normal-path diagnostic lane.
# Status: exploratory_not_validation. Raw VTI/PVTI/PRI remain on HM570.

RUN_ROOT="${1:-/mnt/8A0E24070E23EAC1/runs/tclb_pre2025_sphere_theta030_z48_gap24_outer90_sphere11_normal_path_v6diag_M0p1_50k_20260611}"
CASE_DIR="$RUN_ROOT/theta030"
BINARY="${BINARY:-/home/yuan/src/TCLB_clean_wall_normal_path_v6diag_20260611/CLB/d3q27_pf_velocity_q27_geometric/main}"
POSTPROCESS="${POSTPROCESS:-/tmp/tclb_pre2025_sphere_postprocess.py}"
WALL_POSTPROCESS="${WALL_POSTPROCESS:-/tmp/pre2025_sphere_wall_diag_postprocess.py}"
FINITENESS_GATE="${FINITENESS_GATE:-/tmp/tclb_vti_finiteness_gate.py}"
GALLERY_SCRIPT="${GALLERY_SCRIPT:-/tmp/pre2025_sphere_single_case_frame_gallery.py}"
SURFACE_FILM_AUDIT="${SURFACE_FILM_AUDIT:-/tmp/pre2025_sphere_surface_film_audit.py}"
TARGETS_CSV="${TARGETS_CSV:-/tmp/table_II_sphere_targets.csv}"

SOLID_CENTER_X=40
SOLID_CENTER_Y=40
SOLID_CENTER_Z=48
SOLID_RADIUS=24

cd /home/yuan/src/TCLB
export PATH=/usr/local/cuda-12.6/bin:$PATH
export OMPI_MCA_plm_rsh_agent=/usr/bin/ssh

mkdir -p "$CASE_DIR"
batch_log="$RUN_ROOT/batch_normal_path_v6diag_M0p1_50k.log"
current_case_dir=""

mark_interrupted() {
  local rc=$?
  local sig="${1:-unknown}"
  {
    echo "BATCH_INTERRUPTED $(date -Is) signal=$sig rc=$rc current_case_dir=${current_case_dir:-none}"
    echo "status=exploratory_not_validation"
    echo "reason=stopped_or_interrupted"
  } | tee -a "$batch_log" >/dev/null || true
  if [[ -n "${current_case_dir:-}" && -d "$current_case_dir" ]]; then
    {
      echo "status=exploratory_not_validation"
      echo "reason=stopped_or_interrupted"
      echo "signal=$sig"
      echo "timestamp=$(date -Is)"
    } > "$current_case_dir/run.interrupted" || true
  fi
  exit 130
}

trap 'mark_interrupted SIGINT' INT
trap 'mark_interrupted SIGTERM' TERM

{
  echo "BATCH_PREP $(date -Is)"
  echo "status=exploratory_not_validation"
  echo "purpose=v6_normal_path_M_control_only"
  echo "run_root=$RUN_ROOT"
  echo "case_dir=$CASE_DIR"
  echo "binary=$BINARY"
  echo "solid_center=($SOLID_CENTER_X,$SOLID_CENTER_Y,$SOLID_CENTER_Z)"
  echo "solid_radius=$SOLID_RADIUS"
  echo "raw_policy=remote-only"
} | tee -a "$batch_log"

xml="$CASE_DIR/pre2025_sphere_tableII_theta030.xml"
if [[ ! -f "$xml" ]]; then
  echo "MISSING_XML $xml" | tee -a "$batch_log"
  exit 2
fi
if [[ ! -x "$BINARY" ]]; then
  echo "MISSING_BINARY $BINARY" | tee -a "$batch_log"
  exit 3
fi
for helper in "$POSTPROCESS" "$WALL_POSTPROCESS" "$FINITENESS_GATE" "$GALLERY_SCRIPT" "$SURFACE_FILM_AUDIT"; do
  if [[ ! -f "$helper" ]]; then
    echo "MISSING_HELPER $helper" | tee -a "$batch_log"
    exit 4
  fi
done

current_case_dir="$CASE_DIR"
cp -f "$xml" "$CASE_DIR/case.xml"
echo "$BINARY" > "$CASE_DIR/binary.path"
sha256sum "$BINARY" > "$CASE_DIR/binary.sha256"

rm -f "$CASE_DIR/run.done" "$CASE_DIR/run.interrupted" "$CASE_DIR/run.numerical_failure"
rm -f "$CASE_DIR/run.returncode" "$CASE_DIR/analysis_pre2025_sphere.returncode"
rm -f "$CASE_DIR/analysis_wall_diag_v6.returncode" "$CASE_DIR/analysis_morphology.returncode"
rm -f "$CASE_DIR/analysis_surface_film.returncode" "$CASE_DIR/analysis_finiteness.returncode"
rm -rf "$CASE_DIR/analysis_pre2025_sphere" "$CASE_DIR/analysis_wall_diag_v6"
rm -rf "$CASE_DIR/analysis_morphology" "$CASE_DIR/analysis_surface_film" "$CASE_DIR/analysis_finiteness"

echo "CASE_START $(date -Is) theta=030 M0p1" | tee -a "$batch_log"
set +e
"$BINARY" "$CASE_DIR/case.xml" > "$CASE_DIR/run.log" 2> "$CASE_DIR/run.stderr"
rc=$?
set -e
printf '%s\n' "$rc" > "$CASE_DIR/run.returncode"
echo "CASE_END $(date -Is) theta=030 M0p1 rc=$rc" | tee -a "$batch_log"

if grep -Eiq '(^|[^A-Za-z])nan([^A-Za-z]|$)|(^|[^A-Za-z])inf([^A-Za-z]|$)|Stopping due to NaN|discovered NaN|NaN value|Checking .*discovered|error[[:space:]]*!' "$CASE_DIR/run.log" "$CASE_DIR/run.stderr"; then
  touch "$CASE_DIR/run.numerical_failure"
  echo "CASE_NUMERICAL_FAILURE $(date -Is) theta=030 M0p1" | tee -a "$batch_log"
  exit 6
fi
if [[ "$rc" -ne 0 ]]; then
  exit "$rc"
fi

mkdir -p "$CASE_DIR/analysis_finiteness"
set +e
python3 "$FINITENESS_GATE" \
  --root "$CASE_DIR" \
  --out-dir "$CASE_DIR/analysis_finiteness" \
  --arrays PhaseField,U,Rho \
  > "$CASE_DIR/analysis_finiteness_stdout.log" \
  2> "$CASE_DIR/analysis_finiteness_stderr.log"
finite_rc=$?
set -e
printf '%s\n' "$finite_rc" > "$CASE_DIR/analysis_finiteness.returncode"
echo "FINITENESS_END $(date -Is) rc=$finite_rc" | tee -a "$batch_log"
if [[ "$finite_rc" -ne 0 ]]; then
  exit "$finite_rc"
fi

mkdir -p "$CASE_DIR/analysis_pre2025_sphere"
set +e
python3 "$POSTPROCESS" \
  --root "$CASE_DIR" \
  --analysis-dir "$CASE_DIR/analysis_pre2025_sphere" \
  --targets-csv "$TARGETS_CSV" \
  --theta 30 \
  --solid-center-x "$SOLID_CENTER_X" \
  --solid-center-y "$SOLID_CENTER_Y" \
  --solid-center-z "$SOLID_CENTER_Z" \
  --solid-radius "$SOLID_RADIUS" \
  > "$CASE_DIR/analysis_pre2025_sphere_stdout.log" \
  2> "$CASE_DIR/analysis_pre2025_sphere_stderr.log"
post_rc=$?
set -e
printf '%s\n' "$post_rc" > "$CASE_DIR/analysis_pre2025_sphere.returncode"
echo "POSTPROCESS_END $(date -Is) rc=$post_rc" | tee -a "$batch_log"
if [[ "$post_rc" -ne 0 ]]; then
  exit "$post_rc"
fi

mkdir -p "$CASE_DIR/analysis_wall_diag_v6"
set +e
python3 "$WALL_POSTPROCESS" \
  --case-root "$CASE_DIR" \
  --out-dir "$CASE_DIR/analysis_wall_diag_v6" \
  --plot \
  > "$CASE_DIR/analysis_wall_diag_v6_stdout.log" \
  2> "$CASE_DIR/analysis_wall_diag_v6_stderr.log"
wall_rc=$?
set -e
printf '%s\n' "$wall_rc" > "$CASE_DIR/analysis_wall_diag_v6.returncode"
echo "WALL_DIAG_END $(date -Is) rc=$wall_rc" | tee -a "$batch_log"
if [[ "$wall_rc" -ne 0 ]]; then
  exit "$wall_rc"
fi

mkdir -p "$CASE_DIR/analysis_morphology"
set +e
python3 "$GALLERY_SCRIPT" \
  --case-root "$CASE_DIR" \
  --out-dir "$CASE_DIR/analysis_morphology" \
  --analysis-subdir "analysis_pre2025_sphere" \
  --solid-center-x "$SOLID_CENTER_X" \
  --solid-center-y "$SOLID_CENTER_Y" \
  --solid-center-z "$SOLID_CENTER_Z" \
  --solid-radius "$SOLID_RADIUS" \
  --title "v6 normal-path theta030 z48/gap24 outer90 sphere11 M0.1 W6, 0-50k" \
  > "$CASE_DIR/analysis_morphology_stdout.log" \
  2> "$CASE_DIR/analysis_morphology_stderr.log"
gallery_rc=$?
set -e
printf '%s\n' "$gallery_rc" > "$CASE_DIR/analysis_morphology.returncode"
echo "MORPHOLOGY_END $(date -Is) rc=$gallery_rc" | tee -a "$batch_log"
if [[ "$gallery_rc" -ne 0 ]]; then
  exit "$gallery_rc"
fi

mkdir -p "$CASE_DIR/analysis_surface_film"
set +e
python3 "$SURFACE_FILM_AUDIT" \
  --case-root "$CASE_DIR" \
  --out-dir "$CASE_DIR/analysis_surface_film" \
  --analysis-subdir analysis_pre2025_sphere \
  --solid-center-x "$SOLID_CENTER_X" \
  --solid-center-y "$SOLID_CENTER_Y" \
  --solid-center-z "$SOLID_CENTER_Z" \
  --solid-radius "$SOLID_RADIUS" \
  --shell-min 0 \
  --shell-max 8 \
  --phase-floor 1e-6 \
  --bin-deg 5 \
  --bottom-plane-zmax 8 \
  --plot \
  > "$CASE_DIR/analysis_surface_film_stdout.log" \
  2> "$CASE_DIR/analysis_surface_film_stderr.log"
film_rc=$?
set -e
printf '%s\n' "$film_rc" > "$CASE_DIR/analysis_surface_film.returncode"
echo "SURFACE_FILM_END $(date -Is) rc=$film_rc" | tee -a "$batch_log"
if [[ "$film_rc" -ne 0 ]]; then
  exit "$film_rc"
fi

tar -czf "$RUN_ROOT/curated_pre2025_sphere_normal_path_v6diag_M0p1_50k_no_raw.tar.gz" \
  --exclude='*.vti' --exclude='*.pvti' --exclude='*.pri' \
  -C "$RUN_ROOT" theta030 batch_normal_path_v6diag_M0p1_50k.log

touch "$CASE_DIR/run.done"
current_case_dir=""
echo "BATCH_END $(date -Is)" | tee -a "$batch_log"
