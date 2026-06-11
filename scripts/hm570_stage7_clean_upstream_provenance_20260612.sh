#!/usr/bin/env bash
set -euo pipefail

# Build a clean upstream TCLB lane for Stage7 provenance only.
# Status: runtime_sanity / exploratory_not_validation.

SRC_ROOT="${SRC_ROOT:-/home/yuan/src/TCLB}"
COMMIT="${COMMIT:-ded67cd768cf7e727bd078af139e3ec7895076e5}"
CLEAN_ROOT="${CLEAN_ROOT:-/home/yuan/src/TCLB_clean_upstream_ded67cd_20260612}"
PROV_ROOT="${PROV_ROOT:-/mnt/8A0E24070E23EAC1/runs/tclb_clean_upstream_ded67cd_provenance_20260612}"
TARGET="${TARGET:-d3q27_pf_velocity_q27_geometric}"

mkdir -p "$PROV_ROOT"

{
  echo "status=runtime_sanity"
  echo "claim_limit=clean_upstream_build_provenance_only"
  echo "src_root=$SRC_ROOT"
  echo "commit=$COMMIT"
  echo "clean_root=$CLEAN_ROOT"
  echo "prov_root=$PROV_ROOT"
  echo "target=$TARGET"
  echo "started=$(date -Is)"
} > "$PROV_ROOT/PROVENANCE.txt"

if [[ -e "$CLEAN_ROOT" && ! -d "$CLEAN_ROOT/.git" ]]; then
  echo "CLEAN_ROOT_EXISTS_NOT_GIT $CLEAN_ROOT" | tee "$PROV_ROOT/error.txt"
  exit 2
fi

if [[ ! -d "$CLEAN_ROOT/.git" ]]; then
  parent="$(dirname "$CLEAN_ROOT")"
  case "$CLEAN_ROOT" in
    /home/yuan/src/TCLB_clean_upstream_*) ;;
    *)
      echo "REFUSE_UNEXPECTED_CLEAN_ROOT $CLEAN_ROOT" | tee "$PROV_ROOT/error.txt"
      exit 3
      ;;
  esac
  mkdir -p "$parent"
  git clone "$SRC_ROOT" "$CLEAN_ROOT" > "$PROV_ROOT/git_clone.stdout.log" 2> "$PROV_ROOT/git_clone.stderr.log"
fi

cd "$CLEAN_ROOT"
git fetch --all --tags > "$PROV_ROOT/git_fetch.stdout.log" 2> "$PROV_ROOT/git_fetch.stderr.log" || true
git checkout "$COMMIT" > "$PROV_ROOT/git_checkout.stdout.log" 2> "$PROV_ROOT/git_checkout.stderr.log"
git rev-parse HEAD > "$PROV_ROOT/git_head.txt"
git status --short > "$PROV_ROOT/git_status_short.txt"

export PATH=/usr/local/cuda-12.6/bin:$PATH

set +e
./configure --enable-cuda=/usr/local/cuda-12.6 > "$PROV_ROOT/configure.stdout.log" 2> "$PROV_ROOT/configure.stderr.log"
configure_rc=$?
set -e
printf '%s\n' "$configure_rc" > "$PROV_ROOT/configure.returncode"
if [[ "$configure_rc" -ne 0 ]]; then
  exit "$configure_rc"
fi

set +e
make "${TARGET}/source" > "$PROV_ROOT/make_source.stdout.log" 2> "$PROV_ROOT/make_source.stderr.log"
source_rc=$?
set -e
printf '%s\n' "$source_rc" > "$PROV_ROOT/make_source.returncode"
if [[ "$source_rc" -ne 0 ]]; then
  exit "$source_rc"
fi

set +e
make -C "CLB/${TARGET}" > "$PROV_ROOT/make_build.stdout.log" 2> "$PROV_ROOT/make_build.stderr.log"
build_rc=$?
set -e
printf '%s\n' "$build_rc" > "$PROV_ROOT/make_build.returncode"
if [[ "$build_rc" -ne 0 ]]; then
  exit "$build_rc"
fi

sha256sum "CLB/${TARGET}/main" > "$PROV_ROOT/binary_sha256.txt"
cp -f "CLB/${TARGET}/options.R" "$PROV_ROOT/options.R"
cp -f "CLB/${TARGET}/Consts.h" "$PROV_ROOT/Consts.h"
cp -f "CLB/${TARGET}/SUMMARY" "$PROV_ROOT/SUMMARY"

{
  echo "completed=$(date -Is)"
  echo "binary=CLB/${TARGET}/main"
  cat "$PROV_ROOT/binary_sha256.txt"
} >> "$PROV_ROOT/PROVENANCE.txt"

find "$PROV_ROOT" -maxdepth 1 -type f -printf '%f\n' | sort > "$PROV_ROOT/file_manifest.txt"
