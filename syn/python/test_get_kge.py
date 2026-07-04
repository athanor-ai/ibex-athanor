#!/usr/bin/env python3

from pathlib import Path

import pytest

from get_kge import choose_reference_cell, get_kge, read_lib


def test_choose_reference_cell_prefers_nangate_when_available() -> None:
    cell_dict = {"NAND2_X1": 1.0, "sky130_fd_sc_hd__nand2_1": 1.2}
    assert choose_reference_cell(cell_dict, "auto") == "NAND2_X1"


def test_choose_reference_cell_accepts_sky130_when_nangate_missing() -> None:
    cell_dict = {"sky130_fd_sc_hd__nand2_1": 1.2}
    assert choose_reference_cell(cell_dict, "auto") == "sky130_fd_sc_hd__nand2_1"


def test_read_lib_auto_handles_sky130_only_reference(tmp_path: Path) -> None:
    lib = tmp_path / "sky130.lib"
    lib.write_text(
        '    cell ("sky130_fd_sc_hd__nand2_1") {\n'
        "        area : 1.2;\n"
        "    }\n"
        '    cell ("sky130_fd_sc_hd__buf_2") {\n'
        "        area : 2.4;\n"
        "    }\n"
    )

    weighted = read_lib(str(lib), "auto")

    assert weighted["sky130_fd_sc_hd__nand2_1"] == 1.0
    assert weighted["sky130_fd_sc_hd__buf_2"] == 2.0


def test_read_lib_honors_explicit_reference_cell(tmp_path: Path) -> None:
    lib = tmp_path / "cells.lib"
    lib.write_text(
        '  cell ("CUSTOM_REF") {\n'
        "\tarea : 4.0;\n"
        "  }\n"
        '  cell ("CUSTOM_BUF") {\n'
        "\tarea : 10.0;\n"
        "  }\n"
    )

    weighted = read_lib(str(lib), "CUSTOM_REF")

    assert weighted["CUSTOM_BUF"] == 2.5


def test_choose_reference_cell_fails_closed_without_known_reference() -> None:
    with pytest.raises(RuntimeError, match="Could not auto-select"):
        choose_reference_cell({"CUSTOM": 1.0}, "auto")


def test_get_kge_handles_legacy_cell_first_reports(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = tmp_path / "area.rpt"
    report.write_text(
        "sky130_fd_sc_hd__nand2_1 1000\n"
        "sky130_fd_sc_hd__buf_2 500\n"
    )

    get_kge(
        str(report),
        {"sky130_fd_sc_hd__nand2_1": 1.0, "sky130_fd_sc_hd__buf_2": 2.0},
    )

    assert capsys.readouterr().out.strip() == "Area in kGE =  2.0"


def test_get_kge_handles_current_yosys_count_area_cell_reports(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = tmp_path / "area.rpt"
    report.write_text(
        "  2000 6.31E+03 sky130_fd_sc_hd__nand2_1\n"
        "  3000 8.50E+03 sky130_fd_sc_hd__buf_2\n"
    )

    get_kge(
        str(report),
        {"sky130_fd_sc_hd__nand2_1": 1.0, "sky130_fd_sc_hd__buf_2": 2.0},
    )

    assert capsys.readouterr().out.strip() == "Area in kGE =  8.0"
