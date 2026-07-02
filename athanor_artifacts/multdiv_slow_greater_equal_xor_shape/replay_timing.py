#!/usr/bin/env python3
from __future__ import annotations
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
STA = os.environ.get('STA', 'sta')
LIBERTY_ENV = os.environ.get('LIBERTY')
if not LIBERTY_ENV:
    raise SystemExit('Set LIBERTY to sky130_fd_sc_hd__tt_025C_1v80.lib before replay.')
LIBERTY_SRC = Path(LIBERTY_ENV)
LIBERTY = Path('replay_sky130_fd_sc_hd__tt_025C_1v80.lib')
TOP = 'ibex_multdiv_slow'
INPUTS = 'rst_ni mult_en_i div_en_i mult_sel_i div_sel_i operator_i signed_mode_i op_a_i op_b_i alu_adder_ext_i alu_adder_i equal_to_zero_i data_ind_timing_i imd_val_q_i multdiv_ready_id_i'
OUTPUTS = 'alu_operand_a_o alu_operand_b_o imd_val_d_o imd_val_we_o multdiv_result_o valid_o'


def run_sta(name: str) -> dict[str, object]:
    netlist = Path(f'{name}_mapped.v')
    tcl = HERE / f'{name}_sta.tcl'
    checks = HERE / f'{name}_sta_checks.rpt'
    tcl.write_text(f'''read_liberty {LIBERTY}
read_verilog {netlist}
link_design {TOP}
create_clock -name clk_i -period 10 [get_ports clk_i]
set_false_path -from [get_ports rst_ni]
set_input_delay -clock clk_i 2 [get_ports {{{INPUTS}}}]
set_output_delay -clock clk_i 2 [get_ports {{{OUTPUTS}}}]
report_checks -path_delay max -format full_clock_expanded -group_count 10 > {checks.name}
report_checks -path_delay max -format short -group_count 10
report_tns
report_wns
''')
    result = subprocess.run([STA, '-exit', tcl.name], cwd=HERE, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    (HERE / f'{name}_sta_yosys66.log').write_text(result.stdout)
    if result.returncode:
        return {'status': 'sta_failed', 'returncode': result.returncode}
    arrivals = [
        float(x)
        for x in re.findall(
            r'(?m)^\s+(\d+(?:\.\d+)?)\s+data arrival time\s*$',
            checks.read_text(),
        )
    ]
    wns_match = re.search(r'wns\s+(-?\d+(?:\.\d+)?)', result.stdout, re.I)
    tns_match = re.search(r'tns\s+(-?\d+(?:\.\d+)?)', result.stdout, re.I)
    return {
        'status': 'ok',
        'max_data_arrival_ns': max(arrivals) if arrivals else None,
        'wns_ns': float(wns_match.group(1)) if wns_match else None,
        'tns_ns': float(tns_match.group(1)) if tns_match else None,
    }

shutil.copyfile(LIBERTY_SRC, HERE / LIBERTY)
try:
    receipt = {'gold': run_sta('gold'), 'gate': run_sta('gate')}
finally:
    (HERE / LIBERTY).unlink(missing_ok=True)
ga = receipt['gold'].get('max_data_arrival_ns')
ta = receipt['gate'].get('max_data_arrival_ns')
receipt['delta'] = {
    'data_arrival_ns': ta - ga if isinstance(ga, float) and isinstance(ta, float) else None,
    'data_arrival_pct': (ta - ga) / ga * 100 if isinstance(ga, float) and isinstance(ta, float) and ga else None,
}
(HERE / 'timing_yosys66_10ns_2ns_io.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
print(json.dumps(receipt, indent=2, sort_keys=True))
