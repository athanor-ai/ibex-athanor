#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <out-dir>" >&2
  exit 2
fi

out_dir="$1"
source_file="${PICORV32_SOURCE:-<local>/oss-demo-targets/picorv32/picorv32.v}"
top="${PICORV32_TOP:-picorv32}"
liberty="${LR_SYNTH_CELL_LIBRARY_PATH:?LR_SYNTH_CELL_LIBRARY_PATH is required}"
enable_fast_mul="${PICORV32_ENABLE_FAST_MUL:-1}"
enable_div="${PICORV32_ENABLE_DIV:-1}"
clk_period="${PICORV32_CLK_PERIOD_NS:-10}"
io_delay="${PICORV32_IO_DELAY_NS:-1.0}"
path_count="${PICORV32_STA_PATH_COUNT:-50}"

mkdir -p "$out_dir/generated" "$out_dir/log" "$out_dir/reports/timing"

if [ ! -f "$source_file" ]; then
  echo "PicoRV32 source not found: $source_file" >&2
  exit 2
fi

if [ ! -f "$liberty" ]; then
  echo "Liberty file not found: $liberty" >&2
  exit 2
fi

yosys_script="$out_dir/generated/picorv32_synth.ys"
sta_script="$out_dir/generated/picorv32_sta.tcl"
mapped_netlist="$out_dir/generated/picorv32_mapped.v"
sta_netlist="$out_dir/generated/picorv32_sta.v"

cat >"$yosys_script" <<EOF
read_verilog $source_file
chparam -set ENABLE_FAST_MUL $enable_fast_mul $top
chparam -set ENABLE_DIV $enable_div $top
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

yosys -s "$yosys_script" >"$out_dir/log/yosys.log" 2>&1

cat >"$sta_script" <<EOF
read_liberty $liberty
read_verilog $sta_netlist
link_design $top
create_clock -name clk -period $clk_period [get_ports clk]

set input_ports [get_ports {resetn mem_ready mem_rdata* pcpi_wr pcpi_rd* pcpi_wait pcpi_ready irq*}]
set output_ports [get_ports {trap mem_valid mem_instr mem_addr* mem_wdata* mem_wstrb* mem_la_read mem_la_write mem_la_addr* mem_la_wdata* mem_la_wstrb* pcpi_valid pcpi_insn* pcpi_rs1* pcpi_rs2* eoi* trace_valid trace_data*}]
set_input_delay -clock clk $io_delay \$input_ports
set_output_delay -clock clk $io_delay \$output_ports

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
