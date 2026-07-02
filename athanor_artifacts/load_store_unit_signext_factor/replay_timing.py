#!/usr/bin/env python3
from __future__ import annotations
import json, os, re, subprocess
from pathlib import Path
HERE=Path(__file__).parent
STA=os.environ.get('STA','sta')
LIBERTY=os.environ.get('LIBERTY')
if not LIBERTY:
    raise SystemExit('Set LIBERTY to sky130_fd_sc_hd__tt_025C_1v80.lib')
TOP='ibex_load_store_unit'
INPUTS='data_gnt_i data_rvalid_i data_bus_err_i data_pmp_err_i data_rdata_i lsu_we_i lsu_type_i lsu_wdata_i lsu_sign_ext_i lsu_req_i adder_result_ex_i'
OUTPUTS='data_req_o data_addr_o data_we_o data_be_o data_wdata_o lsu_rdata_o lsu_rdata_valid_o addr_incr_req_o addr_last_o lsu_req_done_o lsu_resp_valid_o load_err_o load_resp_intg_err_o store_err_o store_resp_intg_err_o busy_o perf_load_o perf_store_o'
def run(name: str) -> dict[str, object]:
    checks=HERE/f'logs/{name}_sta_checks.replay.rpt'
    tcl=HERE/f'{name}_sta_replay.tcl'
    tcl.write_text(f'''read_liberty {LIBERTY}\nread_verilog {name}_mapped.v\nlink_design {TOP}\ncreate_clock -name clk_i -period 10 [get_ports clk_i]\nset_false_path -from [get_ports rst_ni]\nset_input_delay -clock clk_i 2 [get_ports {{{INPUTS}}}]\nset_output_delay -clock clk_i 2 [get_ports {{{OUTPUTS}}}]\nreport_checks -path_delay max -format full_clock_expanded -group_count 20 > logs/{name}_sta_checks.replay.rpt\nreport_checks -path_delay max -format short -group_count 20\nreport_tns\nreport_wns\n''')
    result=subprocess.run([STA,'-exit',tcl.name],cwd=HERE,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False)
    (HERE/f'logs/{name}_sta_yosys66.replay.log').write_text(result.stdout)
    if result.returncode:
        return {'status':'sta_failed','returncode':result.returncode}
    txt=checks.read_text(errors='replace') if checks.exists() else ''
    arrivals=[float(x) for x in re.findall(r'(?m)^\s+(\d+(?:\.\d+)?)\s+data arrival time\s*$', txt)]
    wns=re.search(r'wns\s+(-?\d+(?:\.\d+)?)', result.stdout, re.I)
    tns=re.search(r'tns\s+(-?\d+(?:\.\d+)?)', result.stdout, re.I)
    return {'status':'ok','max_data_arrival_ns':max(arrivals) if arrivals else None,'wns_ns':float(wns.group(1)) if wns else None,'tns_ns':float(tns.group(1)) if tns else None}
receipt={'gold':run('gold'),'gate':run('gate')}
g=receipt['gold'].get('max_data_arrival_ns'); t=receipt['gate'].get('max_data_arrival_ns')
receipt['delta']={'data_arrival_ns': t-g if isinstance(g,float) and isinstance(t,float) else None}
(HERE/'timing_yosys66_10ns_2ns_io.replay.json').write_text(json.dumps(receipt, indent=2, sort_keys=True)+'\n')
print(json.dumps(receipt, indent=2, sort_keys=True))
