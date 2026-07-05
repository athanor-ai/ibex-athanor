#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <out-dir>" >&2
  exit 2
fi

out_dir="$1"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
core_root="${CV32E40P_ROOT:-/workdir/oss-demo-targets/cv32e40p}"
default_yosys="/workdir/_tools/oss-cad-suite-20260630/bin/yosys"
if [ -n "${YOSYS:-}" ]; then
  yosys_bin="$YOSYS"
elif [ -x "$default_yosys" ]; then
  yosys_bin="$default_yosys"
else
  yosys_bin="yosys"
fi
sv2v_bin="${SV2V:-sv2v}"
recon_script="$repo_root/syn/cv32e40p_recon.sh"
expected_yosys="Yosys 0.66+181"
expected_sv2v="sv2v v0.0.13"

actual_yosys="$("$yosys_bin" -V | head -n 1)"
if [[ "$actual_yosys" != "$expected_yosys"* ]]; then
  echo "Unexpected Yosys version: $actual_yosys (expected $expected_yosys)" >&2
  exit 2
fi

actual_sv2v="$("$sv2v_bin" --version | head -n 1)"
if [ "$actual_sv2v" != "$expected_sv2v" ]; then
  echo "Unexpected sv2v version: $actual_sv2v (expected $expected_sv2v)" >&2
  exit 2
fi

mkdir -p \
  "$out_dir/baseline" \
  "$out_dir/gate" \
  "$out_dir/gate_src" \
  "$out_dir/log" \
  "$out_dir/reports"

if [ ! -d "$core_root" ]; then
  echo "CV32E40P root not found: $core_root" >&2
  exit 2
fi

filelist="$out_dir/reports/sv2v_filelist.txt"
manifest="$out_dir/reports/source_manifest.sha256"
python3 - "$recon_script" "$filelist" <<'PY'
from pathlib import Path
import re
import sys

script = Path(sys.argv[1]).read_text(encoding="utf-8")
filelist = Path(sys.argv[2])
sources: list[str] = []
in_array = False
for line in script.splitlines():
    stripped = line.strip()
    if stripped.startswith("cv32e40p_sources=("):
        in_array = True
        continue
    if in_array and stripped == ")":
        break
    if in_array:
        match = re.search(r'"([^"]+)"', line)
        if match:
            sources.append(match.group(1))
if not sources:
    raise SystemExit("could not parse cv32e40p source list")
filelist.write_text("\n".join(sources) + "\n", encoding="utf-8")
PY

mapfile -t cv32e40p_sources <"$filelist"
: >"$manifest"
abs_sources=()
gate_sources=()
for rel in "${cv32e40p_sources[@]}"; do
  src="$core_root/$rel"
  if [ ! -f "$src" ]; then
    echo "CV32E40P source not found: $src" >&2
    exit 2
  fi
  sha256sum "$src" | sed "s#  $core_root/#  #" >>"$manifest"
  abs_sources+=("$src")
  gate_sources+=("$out_dir/gate_src/$rel")
done

python3 - "$core_root" "$out_dir/gate_src" "$filelist" <<'PY'
from pathlib import Path
import sys

core_root = Path(sys.argv[1])
gate_root = Path(sys.argv[2])
filelist = Path(sys.argv[3])
sources = filelist.read_text(encoding="utf-8").splitlines()

replacements = {
    "(regfile_waddr_ex_o     == regfile_addr_ra_id) && (rega_used_dec == 1'b1) && (regfile_addr_ra_id != '0)": "(regfile_waddr_ex_o     == regfile_addr_ra_id) && rega_forward_live",
    "(regfile_waddr_ex_o     == regfile_addr_rb_id) && (regb_used_dec == 1'b1) && (regfile_addr_rb_id != '0)": "(regfile_waddr_ex_o     == regfile_addr_rb_id) && regb_forward_live",
    "(regfile_waddr_ex_o     == regfile_addr_rc_id) && (regc_used_dec == 1'b1) && (regfile_addr_rc_id != '0)": "(regfile_waddr_ex_o     == regfile_addr_rc_id) && regc_forward_live",
    "(regfile_waddr_wb_i     == regfile_addr_ra_id) && (rega_used_dec == 1'b1) && (regfile_addr_ra_id != '0)": "(regfile_waddr_wb_i     == regfile_addr_ra_id) && rega_forward_live",
    "(regfile_waddr_wb_i     == regfile_addr_rb_id) && (regb_used_dec == 1'b1) && (regfile_addr_rb_id != '0)": "(regfile_waddr_wb_i     == regfile_addr_rb_id) && regb_forward_live",
    "(regfile_waddr_wb_i     == regfile_addr_rc_id) && (regc_used_dec == 1'b1) && (regfile_addr_rc_id != '0)": "(regfile_waddr_wb_i     == regfile_addr_rc_id) && regc_forward_live",
    "(regfile_alu_waddr_fw_i == regfile_addr_ra_id) && (rega_used_dec == 1'b1) && (regfile_addr_ra_id != '0)": "(regfile_alu_waddr_fw_i == regfile_addr_ra_id) && rega_forward_live",
    "(regfile_alu_waddr_fw_i == regfile_addr_rb_id) && (regb_used_dec == 1'b1) && (regfile_addr_rb_id != '0)": "(regfile_alu_waddr_fw_i == regfile_addr_rb_id) && regb_forward_live",
    "(regfile_alu_waddr_fw_i == regfile_addr_rc_id) && (regc_used_dec == 1'b1) && (regfile_addr_rc_id != '0)": "(regfile_alu_waddr_fw_i == regfile_addr_rc_id) && regc_forward_live",
}
marker = (
    "  assign reg_d_ex_is_reg_a_id  = "
    "(regfile_waddr_ex_o     == regfile_addr_ra_id) && "
    "(rega_used_dec == 1'b1) && (regfile_addr_ra_id != '0);\n"
)
insert = (
    "  logic rega_forward_live;\n"
    "  logic regb_forward_live;\n"
    "  logic regc_forward_live;\n\n"
    "  assign rega_forward_live = (rega_used_dec == 1'b1) && "
    "(regfile_addr_ra_id != '0);\n"
    "  assign regb_forward_live = (regb_used_dec == 1'b1) && "
    "(regfile_addr_rb_id != '0);\n"
    "  assign regc_forward_live = (regc_used_dec == 1'b1) && "
    "(regfile_addr_rc_id != '0);\n\n"
)

for rel in sources:
    src = core_root / rel
    dst = gate_root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    text = src.read_text(encoding="utf-8")
    if rel == "rtl/cv32e40p_id_stage.sv":
        if marker not in text:
            raise SystemExit("cv32e40p_id_stage insertion marker not found")
        text = text.replace(marker, insert + marker, 1)
        for old, new in replacements.items():
            if old not in text:
                raise SystemExit(f"missing forwarding predicate: {old}")
            text = text.replace(old, new, 1)
    dst.write_text(text, encoding="utf-8")
PY

"$sv2v_bin" "${abs_sources[@]}" \
  >"$out_dir/baseline/cv32e40p_wrapper_bundle.v" \
  2>"$out_dir/log/baseline_sv2v.log"
"$sv2v_bin" "${gate_sources[@]}" \
  >"$out_dir/gate/cv32e40p_wrapper_bundle.v" \
  2>"$out_dir/log/gate_sv2v.log"

run_variant() {
  local kind="$1"
  local bundle="$out_dir/$kind/cv32e40p_wrapper_bundle.v"
  "$yosys_bin" -p "read_verilog $bundle; synth -top cv32e40p_wrapper -noabc; stat" \
    >"$out_dir/log/${kind}_yosys_noabc.log" 2>&1
  python3 - "$out_dir" "$out_dir/log/${kind}_yosys_noabc.log" \
    "$out_dir/log/${kind}_yosys_noabc.normalized.log" <<'PY'
from pathlib import Path
import sys

out_dir, raw_log, normalized_log = sys.argv[1:]
skip_prefixes = ("CPU: ", "Time spent: ", "End of script. Logfile hash: ")
lines = []
for line in Path(raw_log).read_text(encoding="utf-8", errors="replace").splitlines():
    if line.startswith(skip_prefixes):
        continue
    lines.append(line.replace(out_dir, "<out-dir>"))
Path(normalized_log).write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
}

run_variant baseline
run_variant gate

python3 - "$out_dir" "$core_root" "$yosys_bin" "$sv2v_bin" <<'PY'
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

out_dir = Path(sys.argv[1])
core_root = Path(sys.argv[2])
yosys_bin = sys.argv[3]
sv2v_bin = sys.argv[4]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command_version(cmd: str, arg: str) -> str:
    proc = subprocess.run([cmd, arg], check=True, text=True, capture_output=True)
    output = (proc.stdout or proc.stderr).strip().splitlines()
    if not output:
        raise SystemExit(f"no version output from {cmd} {arg}")
    return output[0]


def stat_section_matching(lines: list[str], label: str, suffix: str) -> list[str]:
    starts = [
        i
        for i, line in enumerate(lines)
        if line.strip().startswith("===") and line.strip().endswith(suffix)
    ]
    if not starts:
        raise SystemExit(f"missing stat section {label}")
    start = starts[-1]
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].strip().startswith("===")),
        len(lines),
    )
    return lines[start:end]


def cells_and_hist(log_path: Path, label: str, suffix: str) -> tuple[int, dict[str, int]]:
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    section = stat_section_matching(lines, label, suffix)
    count = None
    hist: dict[str, int] = {}
    for line in section:
        match = re.match(r"\s+Number of cells:\s+(\d+)$", line)
        if not match:
            match = re.match(r"\s+(\d+) cells$", line)
        if match:
            count = int(match.group(1))
            hist = {}
            continue
        if count is None:
            continue
        parts = line.split()
        if len(parts) == 2 and parts[0].isdigit() and parts[1].startswith("$_"):
            hist[parts[1]] = int(parts[0])
        elif hist and line.strip().endswith("submodules"):
            break
    if count is None:
        raise SystemExit(f"no cell count in {log_path} / {label}")
    return count, hist


def warnings(log_path: Path) -> list[str]:
    return [
        line
        for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        if "Warning:" in line
    ]


baseline_log = out_dir / "log" / "baseline_yosys_noabc.normalized.log"
gate_log = out_dir / "log" / "gate_yosys_noabc.normalized.log"
baseline_hierarchy, baseline_hierarchy_hist = cells_and_hist(
    baseline_log, "design hierarchy", "design hierarchy ==="
)
gate_hierarchy, gate_hierarchy_hist = cells_and_hist(
    gate_log, "design hierarchy", "design hierarchy ==="
)
baseline_top, baseline_top_hist = cells_and_hist(
    baseline_log, "cv32e40p_id_stage", "\\cv32e40p_id_stage ==="
)
gate_top, gate_top_hist = cells_and_hist(
    gate_log, "cv32e40p_id_stage", "\\cv32e40p_id_stage ==="
)
cell_delta = gate_hierarchy - baseline_hierarchy
if cell_delta < 0:
    classification = "whole_core_noabc_area_positive_requires_selected_flow_timing_review"
elif cell_delta == 0:
    classification = "whole_core_noabc_area_neutral_no_spend"
else:
    classification = "whole_core_noabc_area_negative_no_spend"
summary = {
    "schema": "athanor.cv32e40p_idstage_hazard_tail_fullcore_noabc_profile.v1",
    "ath_ticket": "ATH-2686",
    "scope": "whole_core_noabc_area_screen_only",
    "transform": "factor id_stage RAW forwarding operand-live predicates into helper wires",
    "classification": classification,
    "design": {
        "id": "cv32e40p",
        "local_repo_path": str(core_root),
        "top": "cv32e40p_wrapper",
    },
    "toolchain": {
        "sv2v": command_version(sv2v_bin, "--version"),
        "yosys": command_version(yosys_bin, "-V"),
        "yosys_command": "synth -top cv32e40p_wrapper -noabc; stat",
    },
    "profile": {
        "baseline_cells": baseline_hierarchy,
        "gate_cells": gate_hierarchy,
        "cell_delta": cell_delta,
        "baseline_id_stage_cells": baseline_top,
        "gate_id_stage_cells": gate_top,
        "id_stage_cell_delta": gate_top - baseline_top,
        "baseline_id_stage_cell_types": baseline_top_hist,
        "gate_id_stage_cell_types": gate_top_hist,
        "baseline_hierarchy_cell_types": baseline_hierarchy_hist,
        "gate_hierarchy_cell_types": gate_hierarchy_hist,
        "baseline_warning_count": len(warnings(baseline_log)),
        "gate_warning_count": len(warnings(gate_log)),
    },
    "artifacts": {
        "source_manifest_sha256": sha256(out_dir / "reports" / "source_manifest.sha256"),
        "baseline_verilog_sha256": sha256(
            out_dir / "baseline" / "cv32e40p_wrapper_bundle.v"
        ),
        "gate_verilog_sha256": sha256(out_dir / "gate" / "cv32e40p_wrapper_bundle.v"),
        "baseline_yosys_log_sha256": sha256(baseline_log),
        "gate_yosys_log_sha256": sha256(gate_log),
    },
    "boundary": (
        "CV32E40P whole-core no-ABC generic Yosys area screen only; no mapped "
        "selected-flow area, no OpenSTA timing, no formal, no toggle, no "
        "cold-replay, no accepted optimization, and no headline claim."
    ),
}
summary_path = out_dir / "reports" / "profile_summary.json"
summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

(
  cd "$out_dir"
  {
    find baseline gate reports -type f
    find log -name '*.normalized.log' -type f
  } | sort | xargs sha256sum >SHA256SUMS
)
