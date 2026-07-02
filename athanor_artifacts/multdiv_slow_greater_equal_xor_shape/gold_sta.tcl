read_liberty replay_sky130_fd_sc_hd__tt_025C_1v80.lib
read_verilog gold_mapped.v
link_design ibex_multdiv_slow
create_clock -name clk_i -period 10 [get_ports clk_i]
set_false_path -from [get_ports rst_ni]
set_input_delay -clock clk_i 2 [get_ports {rst_ni mult_en_i div_en_i mult_sel_i div_sel_i operator_i signed_mode_i op_a_i op_b_i alu_adder_ext_i alu_adder_i equal_to_zero_i data_ind_timing_i imd_val_q_i multdiv_ready_id_i}]
set_output_delay -clock clk_i 2 [get_ports {alu_operand_a_o alu_operand_b_o imd_val_d_o imd_val_we_o multdiv_result_o valid_o}]
report_checks -path_delay max -format full_clock_expanded -group_count 10 > gold_sta_checks.rpt
report_checks -path_delay max -format short -group_count 10
report_tns
report_wns
