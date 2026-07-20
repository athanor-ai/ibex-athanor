#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <out-dir>" >&2
  exit 2
fi

out_dir="$1"
serv_root="${SERV_ROOT:-<local>/oss-demo-targets/serv}"
top="${SERV_TOP:-serv_synth_wrapper}"
liberty="${LR_SYNTH_CELL_LIBRARY_PATH:?LR_SYNTH_CELL_LIBRARY_PATH is required}"
pre_register="${SERV_PRE_REGISTER:-1}"
with_csr="${SERV_WITH_CSR:-1}"
rf_width="${SERV_RF_WIDTH:-2}"
clk_period="${SERV_CLK_PERIOD_NS:-10}"
io_delay="${SERV_IO_DELAY_NS:-1.0}"
path_count="${SERV_STA_PATH_COUNT:-50}"

mkdir -p "$out_dir/generated" "$out_dir/log" "$out_dir/reports/timing"

if [ ! -d "$serv_root" ]; then
  echo "SERV root not found: $serv_root" >&2
  exit 2
fi

if [ ! -f "$liberty" ]; then
  echo "Liberty file not found: $liberty" >&2
  exit 2
fi

serv_files=(
  "$serv_root/rtl/serv_bufreg.v"
  "$serv_root/rtl/serv_bufreg2.v"
  "$serv_root/rtl/serv_alu.v"
  "$serv_root/rtl/serv_csr.v"
  "$serv_root/rtl/serv_ctrl.v"
  "$serv_root/rtl/serv_decode.v"
  "$serv_root/rtl/serv_immdec.v"
  "$serv_root/rtl/serv_mem_if.v"
  "$serv_root/rtl/serv_rf_if.v"
  "$serv_root/rtl/serv_rf_ram_if.v"
  "$serv_root/rtl/serv_rf_ram.v"
  "$serv_root/rtl/serv_state.v"
  "$serv_root/rtl/serv_debug.v"
  "$serv_root/rtl/serv_top.v"
  "$serv_root/rtl/serv_rf_top.v"
  "$serv_root/rtl/serv_aligner.v"
  "$serv_root/rtl/serv_compdec.v"
  "$serv_root/rtl/serv_synth_wrapper.v"
)

for f in "${serv_files[@]}"; do
  if [ ! -f "$f" ]; then
    echo "SERV source not found: $f" >&2
    exit 2
  fi
done

yosys_script="$out_dir/generated/serv_synth.ys"
sta_script="$out_dir/generated/serv_sta.tcl"
mapped_netlist="$out_dir/generated/serv_mapped.v"
sta_netlist="$out_dir/generated/serv_sta.v"

{
  for f in "${serv_files[@]}"; do
    printf 'read_verilog %s\n' "$f"
  done
  cat <<EOF
chparam -set PRE_REGISTER $pre_register $top
chparam -set WITH_CSR $with_csr $top
chparam -set RF_WIDTH $rf_width $top
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
create_clock -name clk -period $clk_period [get_ports clk]

set input_ports [get_ports {i_rst i_timer_irq i_ibus_rdt* i_ibus_ack i_dbus_rdt* i_dbus_ack i_rdata*}]
set output_ports [get_ports {o_ibus_adr* o_ibus_cyc o_dbus_adr* o_dbus_dat* o_dbus_sel* o_dbus_we o_dbus_cyc o_waddr* o_wdata* o_wen o_raddr*}]
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
