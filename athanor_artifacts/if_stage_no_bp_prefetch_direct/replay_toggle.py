#!/usr/bin/env python3
"""Deterministic IF-stage-local toggle replay for the no_bp_prefetch_direct candidate.

Follows the accepted load_store_unit toggle convention
(iverilog_vcd_hierarchy_toggle): both tops driven by an identical
deterministic LCG trace, per-cycle output-boundary equality check, VCD
hierarchy per-bit toggle counts compared gold vs gate. The testbench is
GENERATED from the parsed ibex_if_stage port table (55 ports), rather than
hand-written like the smaller LSU one.
"""

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
VCD_PATH = LOGS / "if_stage_toggle.vcd"
VCD_FROM_WORK = "../if_stage_toggle.vcd"
TRACE_PATH = PKG / "toggle_trace.json"
RECEIPT_PATH = PKG / "toggle_proxy.json"
SIM_LOG_PATH = LOGS / "toggle_replay.log"
TOP = "ibex_if_stage"


def _modules(text: str) -> dict[str, str]:
    ms = list(re.finditer(r"(?m)^module\s+(\w+)\s*\(", text))
    out: dict[str, str] = {}
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        out[m.group(1)] = text[m.start():end]
    return out


def _ports(top_text: str) -> tuple[list[tuple[str, int]], list[tuple[str, int]]]:
    decls = re.findall(
        r"(?m)^\s*(input|output)\s+(?:wire\s+|reg\s+)?(?:\[(\d+):(\d+)\]\s*)?(\w+)\s*;",
        top_text,
    )
    ins = [(n, int(h) + 1 if h else 1) for d, h, _l, n in decls if d == "input"]
    outs = [(n, int(h) + 1 if h else 1) for d, h, _l, n in decls if d == "output"]
    return ins, outs


def _rename_top(mod_text: str, new_name: str) -> str:
    return re.sub(rf"(?m)^module\s+{TOP}\s*\(", f"module {new_name} (", mod_text, count=1)


def _lcg(seed: int) -> int:
    return (seed * 1664525 + 1013904223) & 0xFFFFFFFF


def _make_trace(ins: list[tuple[str, int]]) -> list[dict[str, int]]:
    seed = 0x1F57A6E1
    trace: list[dict[str, int]] = []
    for cycle in range(CYCLES):
        entry: dict[str, int] = {"cycle": cycle}
        for name, width in ins:
            if name in ("clk_i", "rst_ni"):
                continue
            seed = _lcg(seed ^ (cycle * 0x9E3779B9 & 0xFFFFFFFF))
            if width == 1:
                # duty-cycled control bits: deterministic but non-degenerate
                entry[name] = 1 if (seed >> 13) & 0x3 else 0
            else:
                value = 0
                for _ in range((width + 31) // 32):
                    seed = _lcg(seed)
                    value = (value << 32) | seed
                entry[name] = value & ((1 << width) - 1)
        trace.append(entry)
    return trace


def _tb(ins, outs, trace) -> str:
    drv = [f"  reg clk_i = 1'b0;", f"  reg rst_ni = 1'b0;"]
    for n, w in ins:
        if n in ("clk_i", "rst_ni"):
            continue
        drv.append(f"  reg [{w-1}:0] {n} = {w}'d0;" if w > 1 else f"  reg {n} = 1'b0;")
    for side in ("gold", "gate"):
        for n, w in outs:
            drv.append(f"  wire [{w-1}:0] {side}_{n};" if w > 1 else f"  wire {side}_{n};")
    total = sum(w for _, w in outs)
    for side in ("gold", "gate"):
        cat = ", ".join(f"{side}_{n}" for n, _ in outs)
        drv.append(f"  wire [{total-1}:0] {side}_vec = {{ {cat} }};")
    insts = []
    for side, mod in (("gold", "gold_if"), ("gate", "gate_if")):
        conns = [f".{n}({n})" for n, _ in ins] + [f".{n}({side}_{n})" for n, _ in outs]
        insts.append(f"  {mod} {side} (\n    " + ",\n    ".join(conns) + "\n  );")
    cases = []
    for entry in trace:
        assigns = "\n".join(
            f"      {n} = {w}'h{entry[n]:x};"
            for n, w in ins
            if n not in ("clk_i", "rst_ni")
        )
        cases.append(f"    {entry['cycle']}: begin\n{assigns}\n    end")
    case_body = "\n".join(cases)
    return f"""`timescale 1ns/1ps
module tb;
{chr(10).join(drv)}

{chr(10).join(insts)}

  always #5 clk_i = ~clk_i;

  task apply_cycle(input integer c);
  begin
    case (c)
{case_body}
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

    $display("IF-stage toggle replay completed cycles={CYCLES}");
    $finish;
  end
endmodule
"""


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
                            id_owner[parts[3]] = owner
                            id_width[parts[3]] = int(parts[2])
                elif line.startswith("$enddefinitions"):
                    in_defs = False
                continue
            if line[0] in "01xz":
                ident, raw_value = line[1:], line[0]
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

    gold_mods = _modules((PKG / "gold.v").read_text())
    gate_mods = _modules((PKG / "gate_no_bp_prefetch_direct.v").read_text())
    helpers = [n for n in gold_mods if n != TOP]
    for n in helpers:
        if gold_mods[n] != gate_mods.get(n):
            raise SystemExit(f"helper module {n} differs between gold and gate — harness invalid")

    ins, outs = _ports(gold_mods[TOP])
    (WORK / "gold_if.v").write_text(
        _rename_top(gold_mods[TOP], "gold_if") + "\n" + "\n".join(gold_mods[n] for n in helpers)
    )
    (WORK / "gate_if_top.v").write_text(_rename_top(gate_mods[TOP], "gate_if"))

    trace = _make_trace(ins)
    TRACE_PATH.write_text(json.dumps(trace, indent=2) + "\n")
    (WORK / "toggle_tb.v").write_text(_tb(ins, outs, trace))

    compile_log = _run(
        ["iverilog", "-g2012", "-o", "toggle_simv", "gold_if.v", "gate_if_top.v", "toggle_tb.v"],
        WORK,
    )
    sim_log = _run(["vvp", "toggle_simv"], WORK)
    SIM_LOG_PATH.write_text(compile_log + sim_log)
    if "MISMATCH" in sim_log:
        raise SystemExit("boundary mismatch during toggle replay — dynamic equivalence violated")

    gold_toggles, gate_toggles = _count_vcd_toggles(VCD_PATH)
    delta_pct = 0.0 if gold_toggles == 0 else (gate_toggles - gold_toggles) / gold_toggles * 100.0
    receipt = {
        "power_status": "measured",
        "power_evidence_type": "toggle_proxy",
        "power_method": "iverilog_vcd_hierarchy_toggle",
        "stimulus": "deterministic_if_stage_local_trace_v1",
        "sim_cycles": CYCLES,
        "gold_toggles": gold_toggles,
        "gate_toggles": gate_toggles,
        "toggle_delta_pct": round(delta_pct, 6),
        "toggle_status": "neutral_or_better" if gate_toggles <= gold_toggles else "regression",
        "vcd": "logs/if_stage_toggle.vcd",
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
