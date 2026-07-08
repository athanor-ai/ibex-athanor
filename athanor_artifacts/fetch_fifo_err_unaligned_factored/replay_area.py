#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
YOSYS = os.environ.get("YOSYS", "yosys")
LIBERTY_ENV = os.environ.get("LIBERTY")
if not LIBERTY_ENV:
    raise SystemExit("Set LIBERTY to sky130_fd_sc_hd__tt_025C_1v80.lib before replay.")
LIBERTY_SRC = Path(LIBERTY_ENV)
LIBERTY = HERE / "replay_sky130_fd_sc_hd__tt_025C_1v80.lib"


def _run_yosys(name: str, flow: str) -> str:
    result = subprocess.run(
        [YOSYS, "-p", flow],
        cwd=HERE,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    (HERE / f"{name}_yosys66.log").write_text(result.stdout)
    if result.returncode:
        raise SystemExit(f"{name} yosys failed with {result.returncode}")
    return result.stdout


def _generic_cells(text: str) -> int:
    matches = list(re.finditer(r"(?m)^\s+(\d+)\s+cells\s*$", text))
    if not matches:
        raise SystemExit("could not parse generic cell count")
    return int(matches[-1].group(1))


def _run_count(name: str) -> dict[str, object]:
    source = f"ibex_fetch_fifo_{name}_measure_v2001.v"
    generic_flow = (
        f"read_verilog -sv -DFORMAL=0 {source}; "
        "synth -flatten -top ibex_fetch_fifo; stat"
    )
    liberty_flow = (
        f"read_verilog -sv -DFORMAL=0 {source}; "
        f"synth -flatten -top ibex_fetch_fifo; abc -liberty {LIBERTY.name}; stat"
    )
    generic_log = _run_yosys(f"{name}_generic", generic_flow)
    liberty_log = _run_yosys(name, liberty_flow)
    return {
        "generic_cells": _generic_cells(generic_log),
        "liberty_cells": _generic_cells(liberty_log),
    }


def _write_timing_netlist(name: str) -> None:
    top = f"ibex_fetch_fifo_{name}"
    source = f"ibex_fetch_fifo_{name}_v2001.v"
    flow = (
        f"read_verilog -sv -DFORMAL=0 {source}; "
        f"hierarchy -check -top {top}; proc; opt; memory; opt; techmap; opt; "
        f"dfflibmap -liberty {LIBERTY.name}; abc -dff -liberty {LIBERTY.name}; clean; "
        f"stat -liberty {LIBERTY.name}; "
        f"write_verilog -noattr -noexpr -nohex -nodec {name}_mapped.v"
    )
    _run_yosys(f"{name}_mapped", flow)


shutil.copyfile(LIBERTY_SRC, LIBERTY)
try:
    receipt = {"gold": _run_count("gold"), "gate": _run_count("gate")}
    _write_timing_netlist("gold")
    _write_timing_netlist("gate")
finally:
    LIBERTY.unlink(missing_ok=True)

gold = receipt["gold"]
gate = receipt["gate"]
receipt["delta"] = {
    "generic_cells": gate["generic_cells"] - gold["generic_cells"],
    "generic_pct": (gate["generic_cells"] - gold["generic_cells"]) / gold["generic_cells"] * 100,
    "liberty_cells": gate["liberty_cells"] - gold["liberty_cells"],
    "liberty_pct": (gate["liberty_cells"] - gold["liberty_cells"]) / gold["liberty_cells"] * 100,
}
receipt["selected_lead_manifest_summary"] = json.loads((HERE / "lead_manifest.json").read_text())["area"]
(HERE / "area_yosys66_packet.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print(json.dumps(receipt, indent=2, sort_keys=True))
