#!/usr/bin/env python3

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def read_repo_file(path: str) -> str:
    return (REPO_ROOT / path).read_text()


def test_static_sdc_uses_sky130_drive_cell() -> None:
    for path in ("syn/ibex_top.nangate.sdc", "syn/ibex_top_abc.nangate.sdc"):
        text = read_repo_file(path)
        assert "sky130_fd_sc_hd__buf_2" in text
        assert "BUF_X2" not in text


def test_generated_sdc_uses_port_collections() -> None:
    text = read_repo_file("syn/tcl/flow_utils.tcl")

    assert "create_clock -name $lr_synth_clk_input" in text
    assert "\\[get_ports $lr_synth_clk_input\\]" in text
    assert "set_output_delay -clock $lr_synth_clk_input" in text
    assert "\\[get_ports [lindex $output 0]\\]" in text
    assert "set_input_delay -clock $lr_synth_clk_input" in text
    assert "\\[get_ports [lindex $input 0]\\]" in text


def test_latch_map_targets_sky130_latches() -> None:
    text = read_repo_file("syn/rtl/latch_map.v")

    assert "module $_DLATCH_P_" in text
    assert "sky130_fd_sc_hd__dlxtp_1" in text
    assert ".GATE(E)" in text
    assert "module $_DLATCH_N_" in text
    assert "sky130_fd_sc_hd__dlxtn_1" in text
    assert ".GATE_N(E)" in text
    assert "DLH_X1" not in text


def test_sta_netlist_export_uses_opensta_safe_lhs() -> None:
    text = read_repo_file("syn/tcl/yosys_run_synth.tcl")

    assert "write_verilog -noattr -noexpr -nohex -nodec -simple-lhs" in text


def test_sta_path_groups_use_register_cells() -> None:
    text = read_repo_file("syn/tcl/sta_utils.tcl")

    assert "set flops [all_registers -edge_triggered]" in text
    assert "group_path -name reg2reg -from $flops -to $flops" in text
    assert "group_path -name reg2out -from $flops -to $outputs_list" in text
    assert "group_path -name in2reg -from $inputs_list -to $flops" in text
    assert "-clock_pins" not in text
    assert "-data_pins" not in text
