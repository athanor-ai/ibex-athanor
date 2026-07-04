#!/usr/bin/env python3

from pathlib import Path
import importlib.util
import subprocess


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


def test_serv_selected_flow_harness_exports_opensta_artifacts() -> None:
    text = read_repo_file("syn/serv_yosys66.sh")

    assert "serv_synth_wrapper.v" in text
    assert "hierarchy -check -top $top" in text
    assert "chparam -set PRE_REGISTER $pre_register $top" in text
    assert "chparam -set WITH_CSR $with_csr $top" in text
    assert "chparam -set RF_WIDTH $rf_width $top" in text
    assert "write_verilog -noattr $mapped_netlist" in text
    assert (
        "write_verilog -noattr -noexpr -nohex -nodec -simple-lhs $sta_netlist" in text
    )
    assert "tee -o $out_dir/reports/area.rpt stat -liberty $liberty" in text
    assert "group_path -name reg2reg -from \\$flops -to \\$flops" in text
    assert "group_path -name reg2out -from \\$flops -to \\$output_ports" in text
    assert "group_path -name in2reg -from \\$input_ports -to \\$flops" in text
    assert "group_path -name in2out -from \\$input_ports -to \\$output_ports" in text
    assert (
        "write_paths \\$overall_paths $out_dir/reports/timing/overall.csv.rpt" in text
    )


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


def test_top_level_first_collects_generated_stage_artifacts(tmp_path: Path) -> None:
    top_level_first = load_top_level_first()
    reports = tmp_path / "reports"
    timing = reports / "timing"
    generated = tmp_path / "generated"
    timing.mkdir(parents=True)
    generated.mkdir()
    (reports / "area.rpt").write_text("Chip area for module '\\picorv32': 42.0\n")
    (timing / "overall.csv.rpt").write_text("Start Point,End Point,WNS (ns)\na,b,1.0\n")
    (generated / "picorv32_mapped.v").write_text("module picorv32; endmodule\n")
    (generated / "picorv32_sta.tcl").write_text("read_verilog picorv32_mapped.v\n")

    metrics = top_level_first.collect_metrics(
        {
            "area_report_glob": "reports/*area*.rpt",
            "top_module": "picorv32",
            "timing_report_dir": "reports/timing",
            "timing_groups": ["overall"],
            "generated_artifact_globs": ["generated/*.v", "generated/*.tcl"],
        },
        tmp_path,
    )
    out_dir = tmp_path / "receipt"
    (out_dir / "logs").mkdir(parents=True)

    top_level_first.copy_stage_artifacts(out_dir, "baseline", metrics)

    assert (out_dir / "logs" / "baseline_area.rpt").is_file()
    assert (out_dir / "reports" / "timing" / "baseline" / "overall.csv.rpt").is_file()
    assert (
        out_dir / "generated" / "baseline" / "picorv32_mapped.v"
    ).read_text() == "module picorv32; endmodule\n"
    assert (
        out_dir / "generated" / "baseline" / "picorv32_sta.tcl"
    ).read_text() == "read_verilog picorv32_mapped.v\n"


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


def test_top_level_first_patch_root_helpers_apply_and_restore_external_repo(
    tmp_path: Path,
) -> None:
    top_level_first = load_top_level_first()
    patch_root = tmp_path / "external-core"
    patch_root.mkdir()
    target = patch_root / "target.v"
    target.write_text("module target; wire keep = 1'b0; endmodule\n")
    subprocess.run(["git", "init"], cwd=patch_root, check=True, capture_output=True)
    subprocess.run(["git", "add", "target.v"], cwd=patch_root, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "baseline",
        ],
        cwd=patch_root,
        check=True,
        capture_output=True,
    )

    patch = tmp_path / "SOURCE_DIFF.patch"
    patch.write_text(
        "\n".join(
            [
                "diff --git a/target.v b/target.v",
                "index 0000000..1111111 100644",
                "--- a/target.v",
                "+++ b/target.v",
                "@@ -1 +1 @@",
                "-module target; wire keep = 1'b0; endmodule",
                "+module target; wire keep = 1'b1; endmodule",
                "",
            ]
        )
    )

    assert top_level_first._tree_dirty(patch_root) is False
    top_level_first._apply_source_patch(patch_root, patch)
    assert target.read_text() == "module target; wire keep = 1'b1; endmodule\n"
    assert top_level_first._tree_dirty(patch_root) is True
    top_level_first._apply_source_patch(patch_root, patch, reverse=True)
    assert target.read_text() == "module target; wire keep = 1'b0; endmodule\n"
    assert top_level_first._tree_dirty(patch_root) is False

    staged_only = patch_root / "a.v"
    staged_only.write_text("module a; endmodule\n")
    subprocess.run(["git", "add", "a.v"], cwd=patch_root, check=True)
    assert top_level_first._tree_dirty(patch_root) is True


def test_top_level_first_resolves_config_patch_root(tmp_path: Path) -> None:
    top_level_first = load_top_level_first()
    config_root = tmp_path / "from-config"
    override_root = tmp_path / "from-override"

    assert (
        top_level_first._resolve_patch_root({"patch_root": str(config_root)}, None)
        == config_root.resolve()
    )
    assert (
        top_level_first._resolve_patch_root(
            {"patch_root": str(config_root)}, override_root
        )
        == override_root.resolve()
    )
