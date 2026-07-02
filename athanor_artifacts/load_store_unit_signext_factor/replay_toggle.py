#!/usr/bin/env python3
"""Deterministic LSU-local toggle replay for the sign-extension candidate."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path


PKG = Path(__file__).resolve().parent
LOGS = PKG / "logs"
WORK = LOGS / "toggle_work"
CYCLES = 200
VCD_PATH = LOGS / "lsu_toggle.vcd"
VCD_FROM_WORK = "../lsu_toggle.vcd"
TRACE_PATH = PKG / "toggle_trace.json"
RECEIPT_PATH = PKG / "toggle_proxy.json"
SIM_LOG_PATH = LOGS / "toggle_replay.log"
VECTOR_WIDTH = 145


def _split_top_and_helpers(text: str) -> tuple[str, str]:
    matches = list(re.finditer(r"(?m)^module\s+\w+\s*\(", text))
    if len(matches) < 2:
        raise ValueError("expected top module plus helper modules")
    return text[: matches[1].start()], text[matches[1].start() :]


def _rename_top(top: str, new_name: str) -> str:
    return re.sub(
        r"(?m)^module\s+ibex_load_store_unit\s*\(",
        f"module {new_name} (",
        top,
        count=1,
    )


def _lcg(seed: int) -> int:
    return (seed * 1664525 + 1013904223) & 0xFFFFFFFF


def _make_trace() -> list[dict[str, int]]:
    seed = 0x1BADB002
    trace: list[dict[str, int]] = []
    for cycle in range(CYCLES):
        seed = _lcg(seed ^ cycle)
        data_rdata = seed
        seed = _lcg(seed)
        lsu_wdata = seed ^ ((cycle * 0x1020304) & 0xFFFFFFFF)
        seed = _lcg(seed)
        adder = (seed + cycle) & 0xFFFFFFFF
        trace.append(
            {
                "cycle": cycle,
                "data_gnt_i": 1 if cycle % 7 != 3 else 0,
                "data_rvalid_i": 1 if cycle % 5 in (1, 2, 4) else 0,
                "data_bus_err_i": 1 if cycle in (73, 151) else 0,
                "data_pmp_err_i": 1 if cycle in (89,) else 0,
                "data_rdata_i": data_rdata,
                "lsu_we_i": 1 if cycle % 4 == 0 else 0,
                "lsu_type_i": [0, 1, 2, 3][cycle % 4],
                "lsu_wdata_i": lsu_wdata,
                "lsu_sign_ext_i": 1 if cycle % 6 in (2, 3, 5) else 0,
                "lsu_req_i": 1 if cycle % 3 != 0 else 0,
                "adder_result_ex_i": adder,
            }
        )
    return trace


def _trace_assignment(entry: dict[str, int]) -> str:
    return "\n".join(
        [
            f"      data_gnt_i = 1'b{entry['data_gnt_i']};",
            f"      data_rvalid_i = 1'b{entry['data_rvalid_i']};",
            f"      data_bus_err_i = 1'b{entry['data_bus_err_i']};",
            f"      data_pmp_err_i = 1'b{entry['data_pmp_err_i']};",
            f"      data_rdata_i = 32'h{entry['data_rdata_i']:08x};",
            f"      lsu_we_i = 1'b{entry['lsu_we_i']};",
            f"      lsu_type_i = 2'b{entry['lsu_type_i']:02b};",
            f"      lsu_wdata_i = 32'h{entry['lsu_wdata_i']:08x};",
            f"      lsu_sign_ext_i = 1'b{entry['lsu_sign_ext_i']};",
            f"      lsu_req_i = 1'b{entry['lsu_req_i']};",
            f"      adder_result_ex_i = 32'h{entry['adder_result_ex_i']:08x};",
        ]
    )


def _write_testbench(trace: list[dict[str, int]], path: Path) -> None:
    cases = []
    for entry in trace:
        cases.append(
            f"    {entry['cycle']}: begin\n{_trace_assignment(entry)}\n    end"
        )
    case_body = "\n".join(cases)
    path.write_text(
        f"""`timescale 1ns/1ps
module tb;
  reg clk_i = 1'b0;
  reg rst_ni = 1'b0;
  reg data_gnt_i = 1'b0;
  reg data_rvalid_i = 1'b0;
  reg data_bus_err_i = 1'b0;
  reg data_pmp_err_i = 1'b0;
  reg [31:0] data_rdata_i = 32'h0;
  reg lsu_we_i = 1'b0;
  reg [1:0] lsu_type_i = 2'b00;
  reg [31:0] lsu_wdata_i = 32'h0;
  reg lsu_sign_ext_i = 1'b0;
  reg lsu_req_i = 1'b0;
  reg [31:0] adder_result_ex_i = 32'h0;

  wire gold_data_req_o;
  wire [31:0] gold_data_addr_o;
  wire gold_data_we_o;
  wire [3:0] gold_data_be_o;
  wire [31:0] gold_data_wdata_o;
  wire [31:0] gold_lsu_rdata_o;
  wire gold_lsu_rdata_valid_o;
  wire gold_addr_incr_req_o;
  wire [31:0] gold_addr_last_o;
  wire gold_lsu_req_done_o;
  wire gold_lsu_resp_valid_o;
  wire gold_load_err_o;
  wire gold_load_resp_intg_err_o;
  wire gold_store_err_o;
  wire gold_store_resp_intg_err_o;
  wire gold_busy_o;
  wire gold_perf_load_o;
  wire gold_perf_store_o;

  wire gate_data_req_o;
  wire [31:0] gate_data_addr_o;
  wire gate_data_we_o;
  wire [3:0] gate_data_be_o;
  wire [31:0] gate_data_wdata_o;
  wire [31:0] gate_lsu_rdata_o;
  wire gate_lsu_rdata_valid_o;
  wire gate_addr_incr_req_o;
  wire [31:0] gate_addr_last_o;
  wire gate_lsu_req_done_o;
  wire gate_lsu_resp_valid_o;
  wire gate_load_err_o;
  wire gate_load_resp_intg_err_o;
  wire gate_store_err_o;
  wire gate_store_resp_intg_err_o;
  wire gate_busy_o;
  wire gate_perf_load_o;
  wire gate_perf_store_o;

  wire [{VECTOR_WIDTH - 1}:0] gold_vec = {{
    gold_data_req_o, gold_data_addr_o, gold_data_we_o, gold_data_be_o,
    gold_data_wdata_o, gold_lsu_rdata_o, gold_lsu_rdata_valid_o,
    gold_addr_incr_req_o, gold_addr_last_o, gold_lsu_req_done_o,
    gold_lsu_resp_valid_o, gold_load_err_o, gold_load_resp_intg_err_o,
    gold_store_err_o, gold_store_resp_intg_err_o, gold_busy_o,
    gold_perf_load_o, gold_perf_store_o
  }};

  wire [{VECTOR_WIDTH - 1}:0] gate_vec = {{
    gate_data_req_o, gate_data_addr_o, gate_data_we_o, gate_data_be_o,
    gate_data_wdata_o, gate_lsu_rdata_o, gate_lsu_rdata_valid_o,
    gate_addr_incr_req_o, gate_addr_last_o, gate_lsu_req_done_o,
    gate_lsu_resp_valid_o, gate_load_err_o, gate_load_resp_intg_err_o,
    gate_store_err_o, gate_store_resp_intg_err_o, gate_busy_o,
    gate_perf_load_o, gate_perf_store_o
  }};

  gold_lsu gold (
    .clk_i(clk_i), .rst_ni(rst_ni), .data_req_o(gold_data_req_o),
    .data_gnt_i(data_gnt_i), .data_rvalid_i(data_rvalid_i),
    .data_bus_err_i(data_bus_err_i), .data_pmp_err_i(data_pmp_err_i),
    .data_addr_o(gold_data_addr_o), .data_we_o(gold_data_we_o),
    .data_be_o(gold_data_be_o), .data_wdata_o(gold_data_wdata_o),
    .data_rdata_i(data_rdata_i), .lsu_we_i(lsu_we_i),
    .lsu_type_i(lsu_type_i), .lsu_wdata_i(lsu_wdata_i),
    .lsu_sign_ext_i(lsu_sign_ext_i), .lsu_rdata_o(gold_lsu_rdata_o),
    .lsu_rdata_valid_o(gold_lsu_rdata_valid_o), .lsu_req_i(lsu_req_i),
    .adder_result_ex_i(adder_result_ex_i),
    .addr_incr_req_o(gold_addr_incr_req_o),
    .addr_last_o(gold_addr_last_o),
    .lsu_req_done_o(gold_lsu_req_done_o),
    .lsu_resp_valid_o(gold_lsu_resp_valid_o),
    .load_err_o(gold_load_err_o),
    .load_resp_intg_err_o(gold_load_resp_intg_err_o),
    .store_err_o(gold_store_err_o),
    .store_resp_intg_err_o(gold_store_resp_intg_err_o),
    .busy_o(gold_busy_o), .perf_load_o(gold_perf_load_o),
    .perf_store_o(gold_perf_store_o)
  );

  gate_lsu gate (
    .clk_i(clk_i), .rst_ni(rst_ni), .data_req_o(gate_data_req_o),
    .data_gnt_i(data_gnt_i), .data_rvalid_i(data_rvalid_i),
    .data_bus_err_i(data_bus_err_i), .data_pmp_err_i(data_pmp_err_i),
    .data_addr_o(gate_data_addr_o), .data_we_o(gate_data_we_o),
    .data_be_o(gate_data_be_o), .data_wdata_o(gate_data_wdata_o),
    .data_rdata_i(data_rdata_i), .lsu_we_i(lsu_we_i),
    .lsu_type_i(lsu_type_i), .lsu_wdata_i(lsu_wdata_i),
    .lsu_sign_ext_i(lsu_sign_ext_i), .lsu_rdata_o(gate_lsu_rdata_o),
    .lsu_rdata_valid_o(gate_lsu_rdata_valid_o), .lsu_req_i(lsu_req_i),
    .adder_result_ex_i(adder_result_ex_i),
    .addr_incr_req_o(gate_addr_incr_req_o),
    .addr_last_o(gate_addr_last_o),
    .lsu_req_done_o(gate_lsu_req_done_o),
    .lsu_resp_valid_o(gate_lsu_resp_valid_o),
    .load_err_o(gate_load_err_o),
    .load_resp_intg_err_o(gate_load_resp_intg_err_o),
    .store_err_o(gate_store_err_o),
    .store_resp_intg_err_o(gate_store_resp_intg_err_o),
    .busy_o(gate_busy_o), .perf_load_o(gate_perf_load_o),
    .perf_store_o(gate_perf_store_o)
  );

  always #5 clk_i = ~clk_i;

  task apply_cycle;
    input integer cycle;
    begin
      case (cycle)
{case_body}
        default: begin
          data_gnt_i = 1'b0;
          data_rvalid_i = 1'b0;
          data_bus_err_i = 1'b0;
          data_pmp_err_i = 1'b0;
          data_rdata_i = 32'h0;
          lsu_we_i = 1'b0;
          lsu_type_i = 2'b00;
          lsu_wdata_i = 32'h0;
          lsu_sign_ext_i = 1'b0;
          lsu_req_i = 1'b0;
          adder_result_ex_i = 32'h0;
        end
      endcase
    end
  endtask

  integer cycle;
  initial begin
    $dumpfile("{VCD_FROM_WORK}");
    $dumpvars(0, tb.gold);
    $dumpvars(0, tb.gate);

    repeat (4) @(posedge clk_i);
    rst_ni = 1'b1;
    @(negedge clk_i);

    for (cycle = 0; cycle < {CYCLES}; cycle = cycle + 1) begin
      apply_cycle(cycle);
      @(posedge clk_i);
      #1;
      if (gold_vec !== gate_vec) begin
        $display("MISMATCH cycle=%0d gold=%h gate=%h", cycle, gold_vec, gate_vec);
        $fatal(1);
      end
      @(negedge clk_i);
    end

    $display("LSU toggle replay completed cycles={CYCLES}");
    $finish;
  end
endmodule
"""
    )


def _run(cmd: list[str], cwd: Path) -> str:
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)
    output = result.stdout + result.stderr
    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed with {result.returncode}\n{output}")
    return output


def _normalize_value(value: str, width: int) -> str | None:
    value = value.lower()
    if any(ch not in "01" for ch in value):
        return None
    if len(value) < width:
        value = value.zfill(width)
    return value[-width:]


def _count_vcd_toggles(vcd_path: Path) -> tuple[int, int]:
    id_owner: dict[str, str] = {}
    id_width: dict[str, int] = {}
    scopes: list[str] = []
    in_defs = True
    prev: dict[str, str] = {}
    counts = {"gold": 0, "gate": 0}

    with vcd_path.open() as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if in_defs:
                if line.startswith("$scope"):
                    parts = line.split()
                    if len(parts) >= 3:
                        scopes.append(parts[2])
                elif line.startswith("$upscope"):
                    if scopes:
                        scopes.pop()
                elif line.startswith("$var"):
                    parts = line.split()
                    if len(parts) >= 5:
                        owner = None
                        if "gold" in scopes:
                            owner = "gold"
                        elif "gate" in scopes:
                            owner = "gate"
                        if owner is not None:
                            width = int(parts[2])
                            ident = parts[3]
                            id_owner[ident] = owner
                            id_width[ident] = width
                elif line.startswith("$enddefinitions"):
                    in_defs = False
                continue

            if line[0] in "01xz":
                ident = line[1:]
                raw_value = line[0]
            elif line[0] in "bBrR":
                pieces = line.split()
                if len(pieces) != 2:
                    continue
                raw_value, ident = pieces[0][1:], pieces[1]
            else:
                continue

            owner = id_owner.get(ident)
            if owner is None:
                continue
            value = _normalize_value(raw_value, id_width[ident])
            if value is None:
                prev.pop(ident, None)
                continue
            old = prev.get(ident)
            if old is not None:
                counts[owner] += sum(a != b for a, b in zip(old, value))
            prev[ident] = value

    return counts["gold"], counts["gate"]


def main() -> None:
    LOGS.mkdir(exist_ok=True)
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir()

    gold_text = (PKG / "gold.v").read_text()
    gate_text = (PKG / "gate.v").read_text()
    gold_top, gold_helpers = _split_top_and_helpers(gold_text)
    gate_top, _gate_helpers = _split_top_and_helpers(gate_text)

    (WORK / "gold_lsu.v").write_text(_rename_top(gold_top, "gold_lsu") + gold_helpers)
    (WORK / "gate_lsu_top.v").write_text(_rename_top(gate_top, "gate_lsu"))

    trace = _make_trace()
    TRACE_PATH.write_text(json.dumps(trace, indent=2) + "\n")
    _write_testbench(trace, WORK / "toggle_tb.v")

    compile_log = _run(
        [
            "iverilog",
            "-g2012",
            "-o",
            "toggle_simv",
            "gold_lsu.v",
            "gate_lsu_top.v",
            "toggle_tb.v",
        ],
        WORK,
    )
    sim_log = _run(["vvp", "toggle_simv"], WORK)
    SIM_LOG_PATH.write_text(compile_log + sim_log)

    gold_toggles, gate_toggles = _count_vcd_toggles(VCD_PATH)
    delta_pct = (
        0.0
        if gold_toggles == 0
        else ((gate_toggles - gold_toggles) / gold_toggles) * 100.0
    )
    receipt = {
        "power_status": "measured",
        "power_evidence_type": "toggle_proxy",
        "power_method": "iverilog_vcd_hierarchy_toggle",
        "stimulus": "deterministic_lsu_local_trace_v1",
        "sim_cycles": CYCLES,
        "gold_toggles": gold_toggles,
        "gate_toggles": gate_toggles,
        "toggle_delta_pct": round(delta_pct, 6),
        "toggle_status": "neutral_or_better" if gate_toggles <= gold_toggles else "regression",
        "vcd": "logs/lsu_toggle.vcd",
        "trace": "toggle_trace.json",
        "simulation_log": "logs/toggle_replay.log",
        "equivalence_mismatches": 0,
    }
    RECEIPT_PATH.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    if gate_toggles > gold_toggles:
        raise SystemExit("gate toggle count regressed")


if __name__ == "__main__":
    main()
