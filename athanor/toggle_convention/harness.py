#!/usr/bin/env python3
"""ATH-2590: the pinned toggle-stimulus convention harness.

Why this exists: three honest toggle measurements of the same IF-stage
candidate gave three different answers (+0.02%, +1.74%, 0.0%) because each used
a different stimulus. Toggle evidence is only meaningful under a PINNED
convention — and the convention must be infrastructure, not judgment.

What it does (module-agnostic; generalizes the accepted LSU/IF-stage kits):

  harness.py --gold gold.v --gate gate.v --top ibex_if_stage --out-dir logs/

1. Loads the selected convention from athanor/toolchain_policy.json
   (seed, cycles, reset protocol, duty classes, required-exercise minimums).
2. Parses the top module's port table from the gold netlist and GENERATES the
   testbench: both tops instantiated, driven by an identical deterministic LCG
   trace, with a per-cycle output-boundary equality check ($fatal on mismatch).
3. Simulates (iverilog/vvp), counts per-bit VCD hierarchy toggles per side.
4. REQUIRED-EXERCISE enforcement: measures the actual transition counts of the
   convention's listed signals and REFUSES to emit a receipt if the trace
   under-exercised them — a flat-because-nothing-moved result cannot exist.
5. Emits a receipt carrying the convention id + sha256 of the convention block
   + trace/VCD hashes + toolchain identity, the fields
   verify_public_receipts.py requires for any toggle-bearing public row.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POLICY = ROOT / "toolchain_policy.json"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_convention(conv: dict) -> str:
    return hashlib.sha256(
        json.dumps(conv, indent=4, sort_keys=True).encode()
    ).hexdigest()


def load_convention() -> dict:
    policy = json.loads(POLICY.read_text())
    conv = policy.get("selected_toggle_convention")
    if not conv:
        raise SystemExit("toolchain_policy.json has no selected_toggle_convention")
    return conv


def _modules(text: str) -> dict[str, str]:
    ms = list(re.finditer(r"(?m)^module\s+(\w+)\s*\(", text))
    out: dict[str, str] = {}
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        out[m.group(1)] = text[m.start():end]
    return out


def _ports(top_text: str):
    decls = re.findall(
        r"(?m)^\s*(input|output)\s+(?:wire\s+|reg\s+)?(?:\[(\d+):(\d+)\]\s*)?(\w+)\s*;",
        top_text,
    )
    ins = [(n, int(h) + 1 if h else 1) for d, h, _l, n in decls if d == "input"]
    outs = [(n, int(h) + 1 if h else 1) for d, h, _l, n in decls if d == "output"]
    if not ins or not outs:
        raise SystemExit("could not parse a non-empty port table from the gold top")
    return ins, outs


def _lcg(seed: int) -> int:
    return (seed * 1664525 + 1013904223) & 0xFFFFFFFF


def make_trace(conv: dict, ins) -> list[dict[str, int]]:
    seed = int(conv["seed"], 16)
    cycles = int(conv["cycles"])
    trace: list[dict[str, int]] = []
    for cycle in range(cycles):
        entry: dict[str, int] = {"cycle": cycle}
        for name, width in ins:
            if name in ("clk_i", "rst_ni"):
                continue
            seed = _lcg(seed ^ (cycle * 0x9E3779B9 & 0xFFFFFFFF))
            if width == 1:
                entry[name] = 1 if (seed >> 13) & 0x3 else 0
            else:
                value = 0
                for _ in range((width + 31) // 32):
                    seed = _lcg(seed)
                    value = (value << 32) | seed
                entry[name] = value & ((1 << width) - 1)
        trace.append(entry)
    return trace


def _tb(top: str, ins, outs, trace, cycles: int, vcd_rel: str) -> str:
    drv = ["  reg clk_i = 1'b0;", "  reg rst_ni = 1'b0;"]
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
    for side, mod in (("gold", "gold_top"), ("gate", "gate_top")):
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
    $dumpfile("{vcd_rel}");
    $dumpvars(0, tb.gold);
    $dumpvars(0, tb.gate);

    repeat (4) @(posedge clk_i);
    rst_ni = 1'b1;
    @(negedge clk_i);

    for (cycle = 0; cycle < {cycles}; cycle = cycle + 1) begin
      apply_cycle(cycle);
      @(posedge clk_i);
      #1;
      if (gold_vec !== gate_vec) begin
        $display("MISMATCH cycle=%0d gold=%h gate=%h", cycle, gold_vec, gate_vec);
        $fatal(1);
      end
      @(negedge clk_i);
    end

    $display("toggle convention replay completed cycles={cycles}");
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


def _normalize(value: str, width: int) -> str | None:
    value = value.lower()
    if any(ch not in "01" for ch in value):
        return None
    return value.zfill(width)[-width:]


def count_vcd(vcd_path: Path, exercise_signals: set[str]):
    """Per-side toggle totals + per-signal transition counts for the gold
    instance's inputs named in the convention's required-exercise list."""
    id_owner: dict[str, str] = {}
    id_width: dict[str, int] = {}
    id_name: dict[str, str] = {}
    scopes: list[str] = []
    in_defs = True
    prev: dict[str, str] = {}
    counts = {"gold": 0, "gate": 0}
    exercise: dict[str, int] = {s: 0 for s in exercise_signals}
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
                        owner = "gold" if "gold" in scopes else ("gate" if "gate" in scopes else None)
                        if owner:
                            ident = parts[3]
                            id_owner[ident] = owner
                            id_width[ident] = int(parts[2])
                            if owner == "gold" and parts[4] in exercise_signals and len(scopes) == 2:
                                id_name[ident] = parts[4]
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
            value = _normalize(raw_value, id_width[ident])
            if value is None:
                prev.pop(ident, None)
                continue
            old = prev.get(ident)
            if old is not None:
                flips = sum(a != b for a, b in zip(old, value))
                counts[owner] += flips
                if ident in id_name:
                    exercise[id_name[ident]] += flips
            prev[ident] = value
    return counts["gold"], counts["gate"], exercise


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gold", type=Path, required=True)
    ap.add_argument("--gate", type=Path, required=True)
    ap.add_argument("--top", required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()

    conv = load_convention()
    conv_sha = _sha256_convention(conv)
    out = args.out_dir
    work = out / "toggle_work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    gold_mods = _modules(args.gold.read_text())
    gate_mods = _modules(args.gate.read_text())
    if args.top not in gold_mods or args.top not in gate_mods:
        raise SystemExit(f"top {args.top} not found in both netlists")
    helpers = [n for n in gold_mods if n != args.top]
    for n in helpers:
        if gold_mods[n] != gate_mods.get(n):
            raise SystemExit(f"helper module {n} differs between gold and gate — only the top may differ")

    def rename(mod_text: str, new: str) -> str:
        return re.sub(rf"(?m)^module\s+{args.top}\s*\(", f"module {new} (", mod_text, count=1)

    ins, outs = _ports(gold_mods[args.top])
    (work / "gold_top.v").write_text(
        rename(gold_mods[args.top], "gold_top") + "\n" + "\n".join(gold_mods[n] for n in helpers)
    )
    (work / "gate_top.v").write_text(rename(gate_mods[args.top], "gate_top"))

    trace = make_trace(conv, ins)
    trace_path = out / "toggle_trace.json"
    trace_path.write_text(json.dumps(trace, indent=2) + "\n")
    vcd_path = out / "toggle.vcd"
    (work / "tb.v").write_text(
        _tb(args.top, ins, outs, trace, int(conv["cycles"]), "../toggle.vcd")
    )

    compile_log = _run(["iverilog", "-g2012", "-o", "simv", "gold_top.v", "gate_top.v", "tb.v"], work)
    sim_log = _run(["vvp", "simv"], work)
    (out / "toggle_sim.log").write_text(compile_log + sim_log)
    if "MISMATCH" in sim_log:
        raise SystemExit("boundary mismatch — dynamic equivalence violated under the convention trace")

    req = dict(conv.get("required_exercise", {}).get(args.top, {}))
    default_min = conv.get("required_exercise", {}).get("default", {}).get("_all_single_bit_inputs_min")
    if default_min:
        for n, w in ins:
            if w == 1 and n not in ("clk_i", "rst_ni"):
                req.setdefault(n, int(default_min))
    gold_t, gate_t, exercise = count_vcd(vcd_path, set(req))

    under = {s: (exercise.get(s, 0), m) for s, m in req.items() if exercise.get(s, 0) < m}
    if under:
        detail = ", ".join(f"{s}: {got} < required {m}" for s, (got, m) in sorted(under.items()))
        raise SystemExit(
            f"REQUIRED-EXERCISE FAILURE — no receipt emitted. Under-exercised: {detail}. "
            "A trace that does not exercise the convention's signals cannot produce toggle evidence."
        )

    delta_pct = 0.0 if gold_t == 0 else (gate_t - gold_t) / gold_t * 100.0
    receipt = {
        "power_status": "measured",
        "power_evidence_type": "toggle_convention",
        "power_method": "iverilog_vcd_hierarchy_toggle",
        "convention_id": conv["id"],
        "convention_sha256": conv_sha,
        "stimulus": conv["stimulus"],
        "sim_cycles": int(conv["cycles"]),
        "gold_toggles": gold_t,
        "gate_toggles": gate_t,
        "toggle_delta_pct": round(delta_pct, 6),
        "toggle_status": "neutral_or_better" if gate_t <= gold_t else "regression",
        "required_exercise_measured": exercise,
        "trace_sha256": _sha256_file(trace_path),
        "vcd_sha256": _sha256_file(vcd_path),
        "boundary_equality_every_cycle": True,
        "trace": str(trace_path.name),
        "vcd": str(vcd_path.name),
    }
    receipt_path = out / "toggle_convention_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
