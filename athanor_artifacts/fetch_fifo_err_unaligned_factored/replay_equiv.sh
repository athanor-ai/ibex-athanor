#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
YOSYS=${YOSYS:-yosys}

run_positive() {
  local top=$1
  local log=$2
  "$YOSYS" -p "read_verilog -formal ibex_fetch_fifo_gold_exposed.v ibex_fetch_fifo_gate_exposed.v; read_verilog -formal ibex_fetch_fifo_relation_seq_miter.sv; prep -top ${top} -flatten; async2sync; opt; select -module ${top}; sat -seq 4 -tempinduct -set-init-zero -prove-asserts -show-inputs -show-outputs" | tee "$log"
  grep -q "SUCCESS" "$log"
}

run_positive ibex_fetch_fifo_relation_seq_miter ibex_fetch_fifo_relation_seq_miter_tempinduct_k4.log
run_positive ibex_fetch_fifo_relation_seq_no_occupancy_miter ibex_fetch_fifo_relation_seq_no_occupancy_miter_tempinduct_k4.log

"$YOSYS" -p "read_verilog -formal ibex_fetch_fifo_gold_exposed.v ibex_fetch_fifo_gate_mutant_exposed.v; read_verilog -formal ibex_fetch_fifo_relation_seq_miter.sv; prep -top ibex_fetch_fifo_relation_seq_miter -flatten; async2sync; opt; select -module ibex_fetch_fifo_relation_seq_miter; sat -seq 4 -tempinduct -set-init-zero -prove-asserts -show-inputs -show-outputs" | tee ibex_fetch_fifo_relation_seq_mutant_tempinduct_k4.log
if grep -q "SUCCESS" ibex_fetch_fifo_relation_seq_mutant_tempinduct_k4.log; then
  echo "mutant unexpectedly passed" >&2
  exit 1
fi
if ! grep -q "FAIL" ibex_fetch_fifo_relation_seq_mutant_tempinduct_k4.log; then
  echo "mutant did not produce the expected FAIL marker" >&2
  exit 1
fi
echo "mutant bite failed as expected"
