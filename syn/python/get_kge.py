#!/usr/bin/env python3

# Copyright lowRISC contributors.
# Licensed under the Apache License, Version 2.0, see LICENSE for details.
# SPDX-License-Identifier: Apache-2.0

# Parse a yosys area report and give a kGE equivalent

import argparse


def choose_reference_cell(cell_dict, ref_cell):
    if ref_cell != 'auto':
        return ref_cell

    for candidate in ('NAND2_X1', 'sky130_fd_sc_hd__nand2_1'):
        if candidate in cell_dict:
            return candidate

    raise RuntimeError(
        'Could not auto-select a reference cell from library. Tried: '
        'NAND2_X1, sky130_fd_sc_hd__nand2_1')


def read_lib(lib_file_path, ref_cell):
    with open(lib_file_path, 'r') as f:
        lib_file = f.readlines()

    cell_dict = {}
    weighted_dict = {}
    cell_name = None
    for line_idx, line in enumerate(lib_file):
        stripped = line.lstrip()
        if stripped.startswith('cell ('):
            if cell_name is not None:
                raise RuntimeError('{}:{} Found cell while searching for area'
                                   .format(lib_file_path, line_idx + 1))
            cell_name = stripped.split()[1].strip('()"')
        elif stripped.startswith('area'):
            if cell_name is None:
                raise RuntimeError('{}:{} Found area while searching for cell'
                                   .format(lib_file_path, line_idx + 1))
            try:
                cell_area = stripped.split()[2].strip(';')
                cell_dict[cell_name] = float(cell_area)
                cell_name = None
            except (IndexError, ValueError):
                raise RuntimeError('{}:{} Area declaration misformatted'
                                   .format(lib_file_path, line_idx + 1))

    ref_cell = choose_reference_cell(cell_dict, ref_cell)

    if ref_cell not in cell_dict:
        raise RuntimeError('Specified reference cell: {} was not found in '
                           'library: {}' .format(ref_cell, lib_file_path))

    for cell in cell_dict:
        weighted_dict[cell] = cell_dict[cell] / cell_dict[ref_cell]
    return weighted_dict


def get_kge(report_path, weighted_dict):
    with open(report_path, 'r') as f:
        report = f.readlines()
    ge = 0.0
    for line_idx, line in enumerate(report):
        data = line.split()
        if not data:
            continue
        cell = None
        count = None
        if data[0] in weighted_dict:
            cell = data[0]
            count = data[1] if len(data) > 1 else None
        elif data[-1] in weighted_dict:
            cell = data[-1]
            count = data[0]
        if cell is not None:
            try:
                ge += float(count) * weighted_dict[cell]
            except (TypeError, ValueError):
                raise RuntimeError('{}:{} Cell {} matched but was misformatted'
                                   .format(report_path, line_idx + 1, cell))
    print("Area in kGE = ", round(ge/1000, 2))


def main():
    arg_parser = argparse.ArgumentParser(
        description="""Calculate kGE from a Yosys report and LIB file""")

    arg_parser.add_argument('lib_file_path', help='Path to the LIB file')
    arg_parser.add_argument('report_path', help='Path to the report')
    arg_parser.add_argument('--cell', help='Reference cell (default:auto)',
                            default='auto')

    args = arg_parser.parse_args()

    weighted_dict = read_lib(args.lib_file_path, args.cell)
    get_kge(args.report_path, weighted_dict)


if __name__ == "__main__":
    main()
