#!/usr/bin/env python3
from __future__ import annotations
import json, os, re, shutil, subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
YOSYS=os.environ.get('YOSYS','yosys')
LIBERTY_ENV=os.environ.get('LIBERTY')
if not LIBERTY_ENV:
    raise SystemExit('Set LIBERTY')
LIBERTY_SRC=Path(LIBERTY_ENV)
LIBERTY=HERE/'replay_sky130_fd_sc_hd__tt_025C_1v80.lib'
TOPS={'gold':'ibex_branch_predict','gate':'ibex_branch_predict_gate'}
FILES={'gold':HERE/'gold_elab.v','gate':HERE/'gate_elab.v'}

def run(name:str,path:Path)->dict[str,object]:
    top=TOPS[name]
    script=f'''
read_verilog {path.name}
hierarchy -check -top {top}
proc; opt; memory; opt
techmap; opt
dfflibmap -liberty {LIBERTY.name}
abc -dff -liberty {LIBERTY.name}
clean
stat -liberty {LIBERTY.name}
write_verilog -noattr -noexpr -nohex -nodec {name}_mapped.v
'''
    r=subprocess.run([YOSYS,'-p',script],cwd=HERE,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=False)
    (HERE/f'{name}_yosys66.log').write_text(r.stdout)
    if r.returncode:
        return {'status':'yosys_failed','returncode':r.returncode}
    m=re.search(r"Chip area for module '\\?"+re.escape(top)+r"':\s+([0-9.]+)", r.stdout)
    return {'status':'ok','area':float(m.group(1)) if m else None}
shutil.copyfile(LIBERTY_SRC, LIBERTY)
try:
    receipt={name:run(name,path) for name,path in FILES.items()}
finally:
    LIBERTY.unlink(missing_ok=True)
g=receipt['gold'].get('area'); t=receipt['gate'].get('area')
receipt['delta']={'area_pct':(t-g)/g*100 if isinstance(g,float) and isinstance(t,float) else None}
(HERE/'area_yosys66.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps(receipt,indent=2,sort_keys=True))
