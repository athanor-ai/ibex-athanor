#!/usr/bin/env python3
from __future__ import annotations
import json, os, re, shutil, subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
STA=os.environ.get('STA','sta')
LIBERTY_ENV=os.environ.get('LIBERTY')
if not LIBERTY_ENV:
    raise SystemExit('Set LIBERTY')
LIBERTY_SRC=Path(LIBERTY_ENV)
LIBERTY=HERE/'replay_sky130_fd_sc_hd__tt_025C_1v80.lib'
TOPS={'gold':'ibex_branch_predict','gate':'ibex_branch_predict_gate'}
INPUTS='fetch_rdata_i fetch_pc_i fetch_valid_i'
OUTPUTS='predict_branch_taken_o predict_branch_pc_o'

def run(name:str)->dict[str,object]:
    top=TOPS[name]
    netlist=Path(f'{name}_mapped.v')
    tcl=HERE/f'{name}_sta.tcl'
    checks=HERE/f'{name}_sta_checks.rpt'
    tcl.write_text(f'''read_liberty {LIBERTY.name}
read_verilog {netlist.name}
link_design {top}
create_clock -name clk_i -period 10 [get_ports clk_i]
set_false_path -from [get_ports rst_ni]
set_input_delay -clock clk_i 2 [get_ports {{{INPUTS}}}]
set_output_delay -clock clk_i 2 [get_ports {{{OUTPUTS}}}]
report_checks -path_delay max -format full_clock_expanded -group_count 10 > {checks.name}
report_checks -path_delay max -format short -group_count 10
report_tns
report_wns
''')
    r=subprocess.run([STA,'-exit',tcl.name],cwd=HERE,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False)
    (HERE/f'{name}_sta_yosys66.log').write_text(r.stdout)
    if r.returncode:
        return {'status':'sta_failed','returncode':r.returncode}
    text=checks.read_text() if checks.exists() else ''
    arrivals=[float(x) for x in re.findall(r'(?m)^\s+(\d+(?:\.\d+)?)\s+data arrival time\s*$', text)]
    wns=re.search(r'wns\s+(-?\d+(?:\.\d+)?)', r.stdout, re.I)
    tns=re.search(r'tns\s+(-?\d+(?:\.\d+)?)', r.stdout, re.I)
    return {'status':'ok','max_data_arrival_ns':max(arrivals) if arrivals else None,'wns_ns':float(wns.group(1)) if wns else None,'tns_ns':float(tns.group(1)) if tns else None}
shutil.copyfile(LIBERTY_SRC, LIBERTY)
try:
    receipt={'gold':run('gold'),'gate':run('gate')}
finally:
    LIBERTY.unlink(missing_ok=True)
ga=receipt['gold'].get('max_data_arrival_ns'); ta=receipt['gate'].get('max_data_arrival_ns')
receipt['delta']={'data_arrival_ns':ta-ga if isinstance(ga,float) and isinstance(ta,float) else None,'data_arrival_pct':(ta-ga)/ga*100 if isinstance(ga,float) and isinstance(ta,float) and ga else None}
(HERE/'timing_opensta_10ns_2ns_io.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps(receipt,indent=2,sort_keys=True))
