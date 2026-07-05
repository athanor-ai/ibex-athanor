#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <out-dir>" >&2
  exit 2
fi

out_dir="$1"
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
liberty="${LR_SYNTH_CELL_LIBRARY_PATH:?LR_SYNTH_CELL_LIBRARY_PATH is required}"
default_yosys="/workdir/_tools/oss-cad-suite-20260630/bin/yosys"
if [ -n "${YOSYS:-}" ]; then
  yosys_bin="$YOSYS"
elif [ -x "$default_yosys" ]; then
  yosys_bin="$default_yosys"
else
  yosys_bin="yosys"
fi
sv2v_bin="${SV2V:-/workdir/.local/bin/sv2v}"
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

if [ ! -f "$liberty" ]; then
  echo "Liberty file not found: $liberty" >&2
  exit 2
fi

mkdir -p \
  "$out_dir/fullcore_noabc" \
  "$out_dir/generated/baseline" \
  "$out_dir/generated/gate" \
  "$out_dir/log" \
  "$out_dir/reports"

YOSYS="$yosys_bin" SV2V="$sv2v_bin" \
  bash "$repo_root/syn/cv32e40p_idstage_hazard_tail_fullcore_noabc_profile.sh" \
  "$out_dir/fullcore_noabc"

run_variant() {
  local kind="$1"
  local bundle="$out_dir/fullcore_noabc/$kind/cv32e40p_wrapper_bundle.v"
  local yosys_script="$out_dir/generated/$kind/cv32e40p_idstage_partitioned_mapped.ys"
  local mapped_netlist="$out_dir/generated/$kind/cv32e40p_id_stage_mapped.v"
  local sta_netlist="$out_dir/generated/$kind/cv32e40p_id_stage_sta.v"

  cat >"$yosys_script" <<EOF
read_verilog $bundle
hierarchy -check -top cv32e40p_id_stage
proc
opt
fsm
opt
memory
opt
techmap
opt
dfflibmap -liberty $liberty
opt
abc -liberty $liberty
opt
flatten
clean
write_verilog -noattr $mapped_netlist
setundef -zero
splitnets
clean
write_verilog -noattr -noexpr -nohex -nodec -simple-lhs $sta_netlist
check
tee -o $out_dir/reports/${kind}_area.rpt stat -liberty $liberty
EOF

  "$yosys_bin" -s "$yosys_script" >"$out_dir/log/${kind}_yosys_mapped.log" 2>&1
  python3 - "$out_dir" "$out_dir/fullcore_noabc" "$out_dir/log/${kind}_yosys_mapped.log" \
    "$out_dir/log/${kind}_yosys_mapped.normalized.log" <<'PY'
from pathlib import Path
import sys

out_dir, noabc_dir, raw_log, normalized_log = sys.argv[1:]
skip_prefixes = ("CPU: ", "Time spent: ", "End of script. Logfile hash: ")
lines = []
for line in Path(raw_log).read_text(encoding="utf-8", errors="replace").splitlines():
    if line.startswith(skip_prefixes):
        continue
    lines.append(line.replace(out_dir, "<out-dir>").replace(noabc_dir, "<fullcore-noabc-dir>"))
Path(normalized_log).write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
}

run_variant baseline
run_variant gate

python3 - "$out_dir" "$yosys_bin" "$sv2v_bin" "$liberty" <<'PY'
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

out_dir = Path(sys.argv[1])
yosys_bin = sys.argv[2]
sv2v_bin = sys.argv[3]
liberty = Path(sys.argv[4])


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command_version(cmd: str, arg: str) -> str:
    proc = subprocess.run([cmd, arg], check=True, text=True, capture_output=True)
    output = (proc.stdout or proc.stderr).strip().splitlines()
    if not output:
        raise SystemExit(f"no version output from {cmd} {arg}")
    return output[0]


def area(path: Path) -> float:
    text = path.read_text(encoding="utf-8", errors="replace")
    matches = re.findall(r"Chip area for module '\\cv32e40p_id_stage':\s+([0-9.]+)", text)
    if not matches:
        raise SystemExit(f"missing cv32e40p_id_stage chip area in {path}")
    return float(matches[-1])


def warnings(log_path: Path) -> list[str]:
    return [
        line
        for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        if "Warning:" in line
    ]


baseline_area = area(out_dir / "reports" / "baseline_area.rpt")
gate_area = area(out_dir / "reports" / "gate_area.rpt")
delta = gate_area - baseline_area
if delta < 0:
    classification = "partitioned_mapped_area_positive_requires_full_core_selected_flow"
elif delta == 0:
    classification = "partitioned_mapped_area_neutral_no_spend"
else:
    classification = "partitioned_mapped_area_negative_no_spend"

summary = {
    "schema": "athanor.cv32e40p_idstage_hazard_tail_partitioned_mapped_profile.v1",
    "ath_ticket": "ATH-2686",
    "scope": "partitioned_id_stage_mapped_area_gate_only",
    "classification": classification,
    "transform": "factor id_stage RAW forwarding operand-live predicates into helper wires",
    "toolchain": {
        "sv2v": command_version(sv2v_bin, "--version"),
        "yosys": command_version(yosys_bin, "-V"),
        "liberty": str(liberty),
        "yosys_command": "dfflibmap -liberty; abc -liberty; stat -liberty on top cv32e40p_id_stage",
    },
    "partitioned_mapped_profile": {
        "baseline_area": baseline_area,
        "gate_area": gate_area,
        "area_delta": delta,
        "area_delta_pct": (delta / baseline_area) * 100.0,
        "baseline_warning_count": len(warnings(out_dir / "log" / "baseline_yosys_mapped.normalized.log")),
        "gate_warning_count": len(warnings(out_dir / "log" / "gate_yosys_mapped.normalized.log")),
    },
    "source_profile": {
        "fullcore_noabc_summary_sha256": sha256(
            out_dir / "fullcore_noabc" / "reports" / "profile_summary.json"
        ),
        "fullcore_noabc_sha256s_sha256": sha256(out_dir / "fullcore_noabc" / "SHA256SUMS"),
    },
    "artifacts": {
        "baseline_yosys_script_sha256": sha256(
            out_dir / "generated" / "baseline" / "cv32e40p_idstage_partitioned_mapped.ys"
        ),
        "gate_yosys_script_sha256": sha256(
            out_dir / "generated" / "gate" / "cv32e40p_idstage_partitioned_mapped.ys"
        ),
        "baseline_mapped_netlist_sha256": sha256(
            out_dir / "generated" / "baseline" / "cv32e40p_id_stage_mapped.v"
        ),
        "gate_mapped_netlist_sha256": sha256(
            out_dir / "generated" / "gate" / "cv32e40p_id_stage_mapped.v"
        ),
        "baseline_sta_netlist_sha256": sha256(
            out_dir / "generated" / "baseline" / "cv32e40p_id_stage_sta.v"
        ),
        "gate_sta_netlist_sha256": sha256(
            out_dir / "generated" / "gate" / "cv32e40p_id_stage_sta.v"
        ),
        "baseline_area_report_sha256": sha256(out_dir / "reports" / "baseline_area.rpt"),
        "gate_area_report_sha256": sha256(out_dir / "reports" / "gate_area.rpt"),
        "baseline_yosys_log_sha256": sha256(
            out_dir / "log" / "baseline_yosys_mapped.normalized.log"
        ),
        "gate_yosys_log_sha256": sha256(out_dir / "log" / "gate_yosys_mapped.normalized.log"),
    },
    "boundary": (
        "CV32E40P cv32e40p_id_stage partitioned mapped-area gate only; "
        "not full-core selected-flow PPA, no OpenSTA timing, no formal, no toggle, "
        "no cold-replay, no accepted optimization, and no headline claim."
    ),
}
(out_dir / "reports" / "profile_summary.json").write_text(
    json.dumps(summary, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY

(
  cd "$out_dir"
  {
    find generated reports -type f
    find log -name '*.normalized.log' -type f
    find fullcore_noabc/reports -type f
  } | sort | xargs sha256sum >SHA256SUMS
)
