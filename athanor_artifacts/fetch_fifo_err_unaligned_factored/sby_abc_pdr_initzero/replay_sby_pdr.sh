#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

SBY=${SBY:-sby}
OUT_DIR=${OUT_DIR:-sby_pdr_replay_out}
PARENT_DIR=${PARENT_DIR:-..}

prepare_case() {
  local case_dir=$1
  local gate_file=$2
  rm -rf "$case_dir"
  mkdir -p "$case_dir"
  cp "$PARENT_DIR/ibex_fetch_fifo_gold_exposed.v" "$case_dir/"
  cp "$PARENT_DIR/$gate_file" "$case_dir/ibex_fetch_fifo_gate_exposed.v"
  cp "miter_initzero.sv" "$case_dir/"
  cp "initzero.sby" "$case_dir/"
}

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

positive_dir="$OUT_DIR/positive"
prepare_case "$positive_dir" "ibex_fetch_fifo_gate_exposed.v"
(
  cd "$positive_dir"
  "$SBY" -f initzero.sby > sby.stdout 2> sby.stderr
)
grep -q '^PASS 0 0$' "$positive_dir/initzero_pdr/status"

mutant_dir="$OUT_DIR/mutant"
prepare_case "$mutant_dir" "ibex_fetch_fifo_gate_mutant_exposed.v"
set +e
(
  cd "$mutant_dir"
  "$SBY" -f initzero.sby > sby.stdout 2> sby.stderr
)
mutant_rc=$?
set -e
if [ "$mutant_rc" -eq 0 ]; then
  echo "mutant unexpectedly passed SBY/ABC PDR" >&2
  exit 1
fi
grep -q '^FAIL 2 0$' "$mutant_dir/initzero_pdr/status"

printf '%s\n' \
  'sby_abc_pdr_initzero: positive PASS, mutant FAIL as expected' \
  > "$OUT_DIR/summary.txt"
cat "$OUT_DIR/summary.txt"
