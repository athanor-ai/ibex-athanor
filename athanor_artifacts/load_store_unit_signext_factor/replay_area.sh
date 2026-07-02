#!/usr/bin/env bash
set -euo pipefail
: "${YOSYS:?Set YOSYS to the pinned Yosys 0.66+181 binary}"
: "${LIBERTY:?Set LIBERTY to sky130_fd_sc_hd__tt_025C_1v80.lib}"
$YOSYS -p "read_verilog gold.v; hierarchy -top ibex_load_store_unit; proc; flatten; synth -top ibex_load_store_unit; dfflibmap -liberty $LIBERTY; abc -liberty $LIBERTY; stat -liberty $LIBERTY; write_verilog -noattr gold_mapped.v" > logs/gold_yosys66.replay.log
$YOSYS -p "read_verilog gate.v; hierarchy -top ibex_load_store_unit; proc; flatten; synth -top ibex_load_store_unit; dfflibmap -liberty $LIBERTY; abc -liberty $LIBERTY; stat -liberty $LIBERTY; write_verilog -noattr gate_mapped.v" > logs/gate_yosys66.replay.log
python3 - <<'PY'
from pathlib import Path
import re,json
out={}
for name in ('gold','gate'):
    txt=Path(f'logs/{name}_yosys66.replay.log').read_text(errors='replace')
    areas=re.findall(r'Chip area for module .*?:\s+([0-9.]+)', txt)
    out[name+'_area']=float(areas[-1]) if areas else None
out['area_delta_pct']=(out['gate_area']-out['gold_area'])/out['gold_area']*100 if out['gold_area'] else None
print(json.dumps(out, indent=2, sort_keys=True))
Path('area_replay.json').write_text(json.dumps(out, indent=2, sort_keys=True)+'\n')
PY
