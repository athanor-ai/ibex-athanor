#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <out-dir>" >&2
  exit 2
fi

out_dir="$1"
core_root="${CV32E40P_ROOT:-<local>/oss-demo-targets/cv32e40p}"
top="${CV32E40P_TOP:-cv32e40p_wrapper}"
sv2v_bin="${SV2V:-sv2v}"

mkdir -p "$out_dir/generated" "$out_dir/log" "$out_dir/reports"

if [ ! -d "$core_root" ]; then
  echo "CV32E40P root not found: $core_root" >&2
  exit 2
fi

cv32e40p_sources=(
  "scripts/lint/config_0p_0f_0z_0lat_0c/cv32e40p_config_pkg.sv"
  "rtl/include/cv32e40p_apu_core_pkg.sv"
  "rtl/include/cv32e40p_fpu_pkg.sv"
  "rtl/include/cv32e40p_pkg.sv"
  "bhv/cv32e40p_sim_clock_gate.sv"
  "rtl/cv32e40p_obi_interface.sv"
  "rtl/cv32e40p_hwloop_regs.sv"
  "rtl/cv32e40p_apu_disp.sv"
  "rtl/cv32e40p_popcnt.sv"
  "rtl/cv32e40p_ff_one.sv"
  "rtl/cv32e40p_fifo.sv"
  "rtl/cv32e40p_prefetch_controller.sv"
  "rtl/cv32e40p_prefetch_buffer.sv"
  "rtl/cv32e40p_aligner.sv"
  "rtl/cv32e40p_compressed_decoder.sv"
  "rtl/cv32e40p_decoder.sv"
  "rtl/cv32e40p_int_controller.sv"
  "rtl/cv32e40p_controller.sv"
  "rtl/cv32e40p_cs_registers.sv"
  "rtl/cv32e40p_alu_div.sv"
  "rtl/cv32e40p_mult.sv"
  "rtl/cv32e40p_alu.sv"
  "rtl/cv32e40p_load_store_unit.sv"
  "rtl/cv32e40p_ex_stage.sv"
  "rtl/cv32e40p_id_stage.sv"
  "rtl/cv32e40p_if_stage.sv"
  "rtl/cv32e40p_sleep_unit.sv"
  "rtl/cv32e40p_register_file_ff.sv"
  "rtl/cv32e40p_core.sv"
  "rtl/cv32e40p_top.sv"
  "scripts/lint/cv32e40p_wrapper.sv"
)

abs_sources=()
for rel in "${cv32e40p_sources[@]}"; do
  src="$core_root/$rel"
  if [ ! -f "$src" ]; then
    echo "CV32E40P source not found: $src" >&2
    exit 2
  fi
  abs_sources+=("$src")
done

manifest="$out_dir/reports/source_manifest.sha256"
filelist="$out_dir/reports/sv2v_filelist.txt"
: >"$manifest"
: >"$filelist"
for rel in "${cv32e40p_sources[@]}"; do
  sha256sum "$core_root/$rel" | sed "s#  $core_root/#  #" >>"$manifest"
  printf '%s\n' "$rel" >>"$filelist"
done

wrapper="$out_dir/generated/cv32e40p_wrapper.v"
frontend_script="$out_dir/generated/cv32e40p_frontend.ys"
frontend_netlist="$out_dir/generated/cv32e40p_frontend.v"

"$sv2v_bin" "${abs_sources[@]}" >"$wrapper" 2>"$out_dir/log/sv2v.log"

cat >"$frontend_script" <<EOF
read_verilog cv32e40p_wrapper.v
hierarchy -check -top $top
proc
opt
fsm
opt
memory
opt
clean
write_verilog -noattr cv32e40p_frontend.v
check
stat
EOF

(
  cd "$out_dir/generated"
  yosys -s "$(basename "$frontend_script")"
) >"$out_dir/log/yosys_frontend.log" 2>&1

sed -E '/^CPU: /d; /^Time spent: /d' \
  "$out_dir/log/yosys_frontend.log" >"$out_dir/log/yosys_frontend.normalized.log"
