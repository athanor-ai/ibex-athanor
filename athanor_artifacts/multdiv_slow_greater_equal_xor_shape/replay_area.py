#!/usr/bin/env python3
from __future__ import annotations
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
YOSYS = os.environ.get('YOSYS', 'yosys')
LIBERTY_ENV = os.environ.get('LIBERTY')
if not LIBERTY_ENV:
    raise SystemExit('Set LIBERTY to sky130_fd_sc_hd__tt_025C_1v80.lib before replay.')
LIBERTY_SRC = Path(LIBERTY_ENV)
LIBERTY = Path('replay_sky130_fd_sc_hd__tt_025C_1v80.lib')
TOP = 'ibex_multdiv_slow'
FILES = {'gold': Path('gold.v'), 'gate': Path('gate_greater_equal_xor_shape.v')}


def run_yosys(name: str, path: Path) -> dict[str, object]:
    script = f'''
read_verilog {path}
hierarchy -check -top {TOP}
proc; opt; memory; opt
techmap; opt
dfflibmap -liberty {LIBERTY}
abc -dff -liberty {LIBERTY}
clean
stat -liberty {LIBERTY}
write_verilog -noattr -noexpr -nohex -nodec {name}_mapped.v
'''
    result = subprocess.run([YOSYS, '-p', script], cwd=HERE, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    (HERE / f'{name}_yosys66.log').write_text(result.stdout)
    if result.returncode:
        return {'status': 'yosys_failed', 'returncode': result.returncode}
    area_match = re.search(r"Chip area for module '\\?ibex_multdiv_slow':\s+([0-9.]+)", result.stdout)
    return {'status': 'ok', 'area': float(area_match.group(1)) if area_match else None}


shutil.copyfile(LIBERTY_SRC, HERE / LIBERTY)
try:
    receipt = {name: run_yosys(name, path) for name, path in FILES.items()}
finally:
    (HERE / LIBERTY).unlink(missing_ok=True)
gold = receipt['gold'].get('area')
gate = receipt['gate'].get('area')
receipt['delta'] = {'area_pct': (gate - gold) / gold * 100 if isinstance(gold, float) and isinstance(gate, float) else None}
(HERE / 'area_yosys66.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
print(json.dumps(receipt, indent=2, sort_keys=True))
