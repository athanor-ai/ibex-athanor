#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <out-dir>" >&2
  exit 2
fi

out_dir="$1"
core_root="${ULTRAEMBEDDED_RISCV_ROOT:-<local>/oss-demo-targets/ultraembedded-riscv}"
top="${ULTRAEMBEDDED_RISCV_TOP:-riscv_core}"
liberty="${LR_SYNTH_CELL_LIBRARY_PATH:?LR_SYNTH_CELL_LIBRARY_PATH is required}"
clk_period="${ULTRAEMBEDDED_RISCV_CLK_PERIOD_NS:-10}"
io_delay="${ULTRAEMBEDDED_RISCV_IO_DELAY_NS:-1.0}"
path_count="${ULTRAEMBEDDED_RISCV_STA_PATH_COUNT:-50}"

mkdir -p "$out_dir/generated" "$out_dir/log" "$out_dir/reports/timing"

if [ ! -d "$core_root" ]; then
  echo "ultraembedded/riscv root not found: $core_root" >&2
  exit 2
fi

if [ ! -f "$liberty" ]; then
  echo "Liberty file not found: $liberty" >&2
  exit 2
fi

core_files=(
  "$core_root/core/riscv/riscv_defs.v"
  "$core_root/core/riscv/riscv_alu.v"
  "$core_root/core/riscv/riscv_multiplier.v"
  "$core_root/core/riscv/riscv_divider.v"
  "$core_root/core/riscv/riscv_csr_regfile.v"
  "$core_root/core/riscv/riscv_csr.v"
  "$core_root/core/riscv/riscv_decoder.v"
  "$core_root/core/riscv/riscv_decode.v"
  "$core_root/core/riscv/riscv_exec.v"
  "$core_root/core/riscv/riscv_fetch.v"
  "$core_root/core/riscv/riscv_issue.v"
  "$core_root/core/riscv/riscv_lsu.v"
  "$core_root/core/riscv/riscv_mmu.v"
  "$core_root/core/riscv/riscv_pipe_ctrl.v"
  "$core_root/core/riscv/riscv_regfile.v"
  "$core_root/core/riscv/riscv_core.v"
)

for f in "${core_files[@]}"; do
  if [ ! -f "$f" ]; then
    echo "ultraembedded/riscv source not found: $f" >&2
    exit 2
  fi
done

yosys_script="$out_dir/generated/ultraembedded_riscv_synth.ys"
sta_script="$out_dir/generated/ultraembedded_riscv_sta.tcl"
mapped_netlist="$out_dir/generated/ultraembedded_riscv_mapped.v"
sta_netlist="$out_dir/generated/ultraembedded_riscv_sta.v"

{
  for f in "${core_files[@]}"; do
    printf 'read_verilog %s\n' "$f"
  done
  cat <<EOF
hierarchy -check -top $top
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
tee -o $out_dir/reports/area.rpt stat -liberty $liberty
EOF
} >"$yosys_script"

yosys -s "$yosys_script" >"$out_dir/log/yosys.log" 2>&1

cat >"$sta_script" <<EOF
read_liberty $liberty
read_verilog $sta_netlist
link_design $top
create_clock -name clk_i -period $clk_period [get_ports clk_i]

set input_ports [get_ports {rst_i mem_d_data_rd_i* mem_d_accept_i mem_d_ack_i mem_d_error_i mem_d_resp_tag_i* mem_i_accept_i mem_i_valid_i mem_i_error_i mem_i_inst_i* intr_i reset_vector_i* cpu_id_i*}]
set output_ports [get_ports {mem_d_addr_o* mem_d_data_wr_o* mem_d_rd_o mem_d_wr_o* mem_d_cacheable_o mem_d_req_tag_o* mem_d_invalidate_o mem_d_writeback_o mem_d_flush_o mem_i_rd_o mem_i_flush_o mem_i_invalidate_o mem_i_pc_o*}]
set_input_delay -clock clk_i $io_delay \$input_ports
set_output_delay -clock clk_i $io_delay \$output_ports

set flops [all_registers -edge_triggered]
group_path -name reg2reg -from \$flops -to \$flops
group_path -name reg2out -from \$flops -to \$output_ports
group_path -name in2reg -from \$input_ports -to \$flops
group_path -name in2out -from \$input_ports -to \$output_ports

proc write_paths {paths out_path} {
  set out [open \$out_path w]
  puts \$out "Start Point,End Point,WNS (ns)"
  foreach p \$paths {
    set start [get_property [get_property \$p startpoint] full_name]
    set end [get_property [get_property \$p endpoint] full_name]
    set slack [get_property \$p slack]
    puts \$out [format "%s,%s,%.4f" \$start \$end \$slack]
  }
  close \$out
}

proc timing_csv {group path count} {
  report_checks -group_count \$count -path_group \$group > \${path}.rpt
  set paths [find_timing_paths -group_count \$count -path_group \$group]
  write_paths \$paths \${path}.csv.rpt
}

report_checks -group_count $path_count > $out_dir/reports/timing/overall.rpt
set overall_paths [find_timing_paths -group_count $path_count]
write_paths \$overall_paths $out_dir/reports/timing/overall.csv.rpt
timing_csv reg2reg $out_dir/reports/timing/reg2reg $path_count
timing_csv reg2out $out_dir/reports/timing/reg2out $path_count
timing_csv in2reg $out_dir/reports/timing/in2reg $path_count
timing_csv in2out $out_dir/reports/timing/in2out $path_count
exit
EOF

sta "$sta_script" >"$out_dir/log/sta.log" 2>&1
