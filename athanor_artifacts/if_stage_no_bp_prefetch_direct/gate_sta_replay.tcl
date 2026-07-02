read_liberty replay_sky130_fd_sc_hd__tt_025C_1v80.lib
read_verilog gate_mapped_sta.v
link_design ibex_if_stage
read_sdc if_stage_10ns.sdc
report_checks -path_delay max -format full_clock_expanded -group_count 10 > gate_sta_checks_replay.rpt
report_checks -path_delay max -format short -group_count 10
report_tns
report_wns
