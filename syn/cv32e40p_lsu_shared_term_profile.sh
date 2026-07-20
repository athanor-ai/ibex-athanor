#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <out-dir>" >&2
  exit 2
fi

out_dir="$1"
core_root="${CV32E40P_ROOT:-<local>/oss-demo-targets/cv32e40p}"
yosys_bin="${YOSYS:-yosys}"
sv2v_bin="${SV2V:-sv2v}"

mkdir -p "$out_dir/generated/baseline" "$out_dir/generated/gate" "$out_dir/log" "$out_dir/reports"

obi_src="$core_root/rtl/cv32e40p_obi_interface.sv"
lsu_src="$core_root/rtl/cv32e40p_load_store_unit.sv"

for src in "$obi_src" "$lsu_src"; do
  if [ ! -f "$src" ]; then
    echo "CV32E40P source not found: $src" >&2
    exit 2
  fi
done

cp "$obi_src" "$out_dir/generated/baseline/cv32e40p_obi_interface.sv"
cp "$lsu_src" "$out_dir/generated/baseline/cv32e40p_load_store_unit.sv"
cp "$obi_src" "$out_dir/generated/gate/cv32e40p_obi_interface.sv"

python3 - "$lsu_src" "$out_dir/generated/gate/cv32e40p_load_store_unit.sv" <<'PY'
from pathlib import Path
import sys

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
text = src.read_text()
zero = "data_sign_ext_q == 2'b00"
allones = "data_sign_ext_q == 2'b10"
if text.count(zero) != 8 or text.count(allones) != 8:
    raise SystemExit("unexpected CV32E40P LSU sign-extension predicate count")
text = text.replace(zero, "data_sign_ext_is_zero")
text = text.replace(allones, "data_sign_ext_is_allones")
marker = "  logic [31:0] rdata_b_ext;  // sign extension for bytes\n"
insert = (
    marker
    + "\n"
    + "  logic data_sign_ext_is_zero;\n"
    + "  logic data_sign_ext_is_allones;\n"
    + "\n"
    + "  assign data_sign_ext_is_zero = data_sign_ext_q == 2'b00;\n"
    + "  assign data_sign_ext_is_allones = data_sign_ext_q == 2'b10;\n"
)
if marker not in text:
    raise SystemExit("CV32E40P LSU insertion marker not found")
dst.write_text(text.replace(marker, insert, 1))
PY

run_variant() {
  local kind="$1"
  local kind_dir="$out_dir/generated/$kind"
  "$sv2v_bin" \
    "$kind_dir/cv32e40p_obi_interface.sv" \
    "$kind_dir/cv32e40p_load_store_unit.sv" \
    >"$kind_dir/cv32e40p_load_store_unit.v"
  "$yosys_bin" -p \
    "read_verilog $kind_dir/cv32e40p_load_store_unit.v; synth -top cv32e40p_load_store_unit; stat" \
    >"$out_dir/log/${kind}_yosys.log" 2>&1
  python3 - "$out_dir" "$out_dir/log/${kind}_yosys.log" \
    "$out_dir/log/${kind}_yosys.normalized.log" <<'PY'
from pathlib import Path
import sys

out_dir, raw_log, normalized_log = sys.argv[1:]
skip_prefixes = ("CPU: ", "Time spent: ", "End of script. Logfile hash: ")
lines = []
for line in Path(raw_log).read_text().splitlines():
    if line.startswith(skip_prefixes):
        continue
    lines.append(line.replace(out_dir, "<out-dir>"))
Path(normalized_log).write_text("\n".join(lines) + "\n")
PY
}

run_variant baseline
run_variant gate

python3 - "$out_dir" <<'PY'
from pathlib import Path
import hashlib
import json
import re
import sys

out_dir = Path(sys.argv[1])

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def cell_count(log_path: Path) -> int:
    matches = re.findall(r"^\s+(\d+) cells$", log_path.read_text(), flags=re.MULTILINE)
    if not matches:
        raise SystemExit(f"no cell count in {log_path}")
    return int(matches[-1])

baseline_log = out_dir / "log" / "baseline_yosys.normalized.log"
gate_log = out_dir / "log" / "gate_yosys.normalized.log"
baseline_cells = cell_count(baseline_log)
gate_cells = cell_count(gate_log)
summary = {
    "schema": "athanor.cv32e40p_lsu_shared_term_profile.v1",
    "scope": "bounded_module_profile_only",
    "transform": "factor repeated data_sign_ext_q equality predicates",
    "baseline_cells": baseline_cells,
    "gate_cells": gate_cells,
    "cell_delta": gate_cells - baseline_cells,
    "classification": (
        "bounded_module_area_neutral_no_spend"
        if gate_cells == baseline_cells
        else "bounded_module_area_changed_requires_review"
    ),
    "artifacts": {
        "baseline_verilog_sha256": sha256(
            out_dir / "generated" / "baseline" / "cv32e40p_load_store_unit.v"
        ),
        "gate_verilog_sha256": sha256(
            out_dir / "generated" / "gate" / "cv32e40p_load_store_unit.v"
        ),
        "baseline_yosys_log_sha256": sha256(baseline_log),
        "gate_yosys_log_sha256": sha256(gate_log),
    },
    "boundary": (
        "CV32E40P load_store_unit module-level generic Yosys profile only; "
        "no full-core PPA, formal, toggle, cold-replay, or accepted-win claim."
    ),
}
(out_dir / "reports" / "profile_summary.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True) + "\n"
)
PY

(
  cd "$out_dir"
  {
    find generated reports -type f
    find log -name '*normalized.log' -type f
  } | sort | xargs sha256sum >SHA256SUMS
)
