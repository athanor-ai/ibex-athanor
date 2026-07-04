#!/usr/bin/env python3

from pathlib import Path
import importlib.util


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


def load_top_level_first():
    spec = importlib.util.spec_from_file_location(
        "top_level_first", REPO_ROOT / "athanor/top_level_first.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_top_level_first_prefers_csv_timing_reports(tmp_path: Path) -> None:
    top_level_first = load_top_level_first()
    reports = tmp_path / "reports"
    timing = reports / "timing"
    timing.mkdir(parents=True)
    (reports / "area.rpt").write_text("Chip area for module '\\ibex_top': 12.5\n")
    (timing / "overall.csv.rpt").write_text(
        "Start Point, End Point, WNS (ns)\na,b,-2.5\nc,d,-1.0\n"
    )
    (timing / "overall.rpt").write_text(
        "Startpoint: a\nEndpoint: b\nPath Group: clk_i\nPath Type: max\n"
    )

    metrics = top_level_first.collect_metrics(
        {
            "area_report_glob": "reports/*area*.rpt",
            "top_module": "ibex_top",
            "timing_report_dir": "reports/timing",
            "timing_groups": ["overall"],
        },
        tmp_path,
    )

    assert metrics["area"] == 12.5
    assert metrics["wns"]["overall"] == -2.5


def test_top_level_first_equivalence_accepts_artifacts_already_in_workdir(
    tmp_path: Path, monkeypatch
) -> None:
    top_level_first = load_top_level_first()
    (tmp_path / "gold.v").write_text("module ibex_if_stage; endmodule\n")
    (tmp_path / "gate.v").write_text("module ibex_if_stage; endmodule\n")

    def fake_run(*args, **kwargs):
        log = kwargs["stdout"]
        log.write(
            "Found 1 $equiv cells in equiv:\n"
            "  Of those cells 1 are proven and 0 are unproven.\n"
            "Equivalence successfully proven!\n"
        )

        class Result:
            returncode = 0

        return Result()

    monkeypatch.setattr(top_level_first.subprocess, "run", fake_run)

    result, ys, log = top_level_first.run_equivalence(
        {"_active_unit_top": "ibex_if_stage", "equiv_seq": 1, "env": {}},
        tmp_path / "gold.v",
        tmp_path / "gate.v",
        tmp_path,
    )

    assert result["proven"] is True
    assert result["proven_cells"] == 1
    assert result["unproven_cells"] == 0
    assert ys == tmp_path / "equiv.ys"
    assert log == tmp_path / "equiv.log"
