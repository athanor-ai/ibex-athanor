#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
STA = os.environ.get("STA", "sta")
LIBERTY_ENV = os.environ.get("LIBERTY")
if not LIBERTY_ENV:
    raise SystemExit("Set LIBERTY to sky130_fd_sc_hd__tt_025C_1v80.lib before replay.")
LIBERTY_SRC = Path(LIBERTY_ENV)
LIBERTY = HERE / "replay_sky130_fd_sc_hd__tt_025C_1v80.lib"
INPUTS = "clear_i in_valid_i in_addr_i in_rdata_i in_err_i out_ready_i"
OUTPUTS = "busy_o out_valid_o out_addr_o out_rdata_o out_err_o out_err_plus2_o"


def _run_sta(name: str) -> dict[str, object]:
    netlist = HERE / f"{name}_mapped.v"
    if not netlist.exists():
        raise SystemExit(f"{netlist.name} missing; run ./replay_area.py first")
    top = f"ibex_fetch_fifo_{name}"
    tcl = HERE / f"{name}_sta.tcl"
    checks = HERE / f"{name}_sta_checks.rpt"
    tcl.write_text(
        f"""read_liberty {LIBERTY.name}
read_verilog {netlist.name}
link_design {top}
create_clock -name clk_i -period 10 [get_ports clk_i]
set_false_path -from [get_ports rst_ni]
set_input_delay -clock clk_i 2 [get_ports {{{INPUTS}}}]
set_output_delay -clock clk_i 2 [get_ports {{{OUTPUTS}}}]
report_checks -path_delay max -format full_clock_expanded -group_count 10 > {checks.name}
report_checks -path_delay max -format short -group_count 10
report_tns
report_wns
"""
    )
    result = subprocess.run(
        [STA, "-exit", tcl.name],
        cwd=HERE,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    (HERE / f"{name}_sta_yosys66.log").write_text(result.stdout)
    if result.returncode:
        return {"status": "sta_failed", "returncode": result.returncode}
    arrivals = [
        float(x)
        for x in re.findall(
            r"(?m)^\s+(\d+(?:\.\d+)?)\s+data arrival time\s*$",
            checks.read_text(),
        )
    ]
    wns_match = re.search(r"wns\s+(-?\d+(?:\.\d+)?)", result.stdout, re.I)
    tns_match = re.search(r"tns\s+(-?\d+(?:\.\d+)?)", result.stdout, re.I)
    return {
        "status": "ok",
        "max_data_arrival_ns": max(arrivals) if arrivals else None,
        "wns_ns": float(wns_match.group(1)) if wns_match else None,
        "tns_ns": float(tns_match.group(1)) if tns_match else None,
    }


shutil.copyfile(LIBERTY_SRC, LIBERTY)
try:
    receipt = {"gold": _run_sta("gold"), "gate": _run_sta("gate")}
finally:
    LIBERTY.unlink(missing_ok=True)

gold_arrival = receipt["gold"].get("max_data_arrival_ns")
gate_arrival = receipt["gate"].get("max_data_arrival_ns")
receipt["delta"] = {
    "data_arrival_ns": gate_arrival - gold_arrival
    if isinstance(gold_arrival, float) and isinstance(gate_arrival, float)
    else None,
    "data_arrival_pct": (gate_arrival - gold_arrival) / gold_arrival * 100
    if isinstance(gold_arrival, float) and isinstance(gate_arrival, float) and gold_arrival
    else None,
}
(HERE / "timing_yosys66_10ns_2ns_io.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print(json.dumps(receipt, indent=2, sort_keys=True))
