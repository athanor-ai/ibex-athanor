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
    match = re.search(r"(?m)^\s+(\d+)\s+cells\s*$", text)
    if not match:
        raise SystemExit("could not parse generic cell count")
    return int(match.group(1))


def _liberty_area(text: str, top: str) -> float:
    match = re.search(rf"Chip area for module '\\?{top}':\s+([0-9.]+)", text)
    if not match:
        raise SystemExit(f"could not parse liberty area for {top}")
    return float(match.group(1))


def _run_one(name: str) -> dict[str, object]:
    top = f"ibex_fetch_fifo_{name}"
    source = f"ibex_fetch_fifo_{name}_v2001.v"
    generic_flow = (
        f"read_verilog {source}; hierarchy -check -top {top}; "
        "proc; opt; memory; opt; techmap; opt; stat"
    )
    liberty_flow = (
        f"read_verilog {source}; hierarchy -check -top {top}; "
        "proc; opt; memory; opt; techmap; opt; "
        f"dfflibmap -liberty {LIBERTY.name}; abc -dff -liberty {LIBERTY.name}; "
        f"clean; stat -liberty {LIBERTY.name}; "
        f"write_verilog -noattr -noexpr -nohex -nodec {name}_mapped.v"
    )
    generic_log = _run_yosys(f"{name}_generic", generic_flow)
    liberty_log = _run_yosys(name, liberty_flow)
    return {
        "generic_cells": _generic_cells(generic_log),
        "liberty_area": _liberty_area(liberty_log, top),
    }


shutil.copyfile(LIBERTY_SRC, LIBERTY)
try:
    receipt = {"gold": _run_one("gold"), "gate": _run_one("gate")}
finally:
    LIBERTY.unlink(missing_ok=True)

gold = receipt["gold"]
gate = receipt["gate"]
receipt["delta"] = {
    "generic_cells": gate["generic_cells"] - gold["generic_cells"],
    "generic_pct": (gate["generic_cells"] - gold["generic_cells"]) / gold["generic_cells"] * 100,
    "liberty_area": gate["liberty_area"] - gold["liberty_area"],
    "liberty_pct": (gate["liberty_area"] - gold["liberty_area"]) / gold["liberty_area"] * 100,
}
receipt["selected_lead_manifest_summary"] = json.loads((HERE / "lead_manifest.json").read_text())["area"]
(HERE / "area_yosys66_packet.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
print(json.dumps(receipt, indent=2, sort_keys=True))
