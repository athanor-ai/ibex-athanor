#!/usr/bin/env python3
"""IF-stage timing replay — STA-clean by construction.

Adapted from the accepted multdiv_slow kit with one addition: yosys-written
netlists can contain LHS-concatenation tie-off assigns
(``assign { a[7], a[1:0] } = 3'h0;``) that OpenSTA's Verilog reader rejects
with a syntax error and then recovers from, leaving the timing graph's
completeness ambiguous. This replay expands every such assign into per-bit
constant assigns before STA and FAILS CLOSED if the STA log contains ANY
Error or Warning — the timing numbers are only reported from a 100%-clean read.
"""
from __future__ import annotations
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
STA = os.environ.get('STA', 'sta')
LIBERTY_ENV = os.environ.get('LIBERTY')
if not LIBERTY_ENV:
    raise SystemExit('Set LIBERTY to sky130_fd_sc_hd__tt_025C_1v80.lib before replay.')
LIBERTY_SRC = Path(LIBERTY_ENV)
LIBERTY = Path('replay_sky130_fd_sc_hd__tt_025C_1v80.lib')
TOP = 'ibex_if_stage'
SDC = HERE / 'if_stage_10ns.sdc'

_CONCAT = re.compile(
    r"^(\s*)assign\s*\{\s*(?P<lhs>[^}]+)\}\s*=\s*(?P<width>\d+)'(?P<base>[bhd])(?P<val>[0-9a-fA-F_xzXZ]+)\s*;\s*$"
)
_SELECT = re.compile(r"^(?P<name>\\?[\w$.]+)\s*(?:\[(?P<hi>\d+)(?::(?P<lo>\d+))?\])?$")


def _const_bits(width: int, base: str, val: str) -> str:
    val = val.replace('_', '')
    if base == 'b':
        bits = val
    elif base == 'h':
        bits = ''.join(format(int(ch, 16), '04b') if ch not in 'xzXZ' else ch * 4 for ch in val)
    else:  # decimal
        bits = format(int(val), 'b')
    return bits.zfill(width)[-width:]


def expand_lhs_concats(src: Path, dst: Path) -> int:
    out, n = [], 0
    for line in src.read_text().splitlines():
        # gate-level netlists carry no arithmetic: `signed` on a wire decl is
        # semantically inert here, and OpenSTA's reader rejects the keyword.
        if line.lstrip().startswith('wire signed '):
            line = line.replace('wire signed ', 'wire ', 1)
        m = _CONCAT.match(line)
        if not m:
            out.append(line)
            continue
        indent = m.group(1)
        width = int(m.group('width'))
        bits = _const_bits(width, m.group('base'), m.group('val'))
        parts = [p.strip() for p in m.group('lhs').split(',')]
        pos = 0  # concat is MSB-first
        repl = []
        for part in parts:
            sm = _SELECT.match(part)
            if not sm:
                raise SystemExit(f'unhandled LHS concat element: {part!r} in {src}')
            hi = sm.group('hi')
            lo = sm.group('lo')
            if hi is None:
                raise SystemExit(f'plain-name LHS element needs declared width lookup: {part!r}')
            w = 1 if lo is None else int(hi) - int(lo) + 1
            chunk = bits[pos:pos + w]
            pos += w
            repl.append(f"{indent}assign {part} = {w}'b{chunk};")
        if pos != width:
            raise SystemExit(f'width mismatch expanding {line!r}: consumed {pos} of {width}')
        out.extend(repl)
        n += 1
    dst.write_text('\n'.join(out) + '\n')
    return n


def run_sta(name: str) -> dict[str, object]:
    netlist = HERE / f'{name}_mapped_sta.v'
    expanded = expand_lhs_concats(HERE / f'{name}_mapped.v', netlist)
    tcl = HERE / f'{name}_sta_replay.tcl'
    checks = HERE / f'{name}_sta_checks_replay.rpt'
    tcl.write_text(
        f'read_liberty {LIBERTY}\n'
        f'read_verilog {netlist.name}\n'
        f'link_design {TOP}\n'
        f'read_sdc {SDC.name}\n'
        f'report_checks -path_delay max -format full_clock_expanded -group_count 10 > {checks.name}\n'
        f'report_checks -path_delay max -format short -group_count 10\n'
        f'report_tns\nreport_wns\n'
    )
    result = subprocess.run([STA, '-exit', tcl.name], cwd=HERE, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    log = HERE / f'{name}_sta_replay.log'
    log.write_text(result.stdout)
    diagnostics = [ln for ln in result.stdout.splitlines() if ln.startswith(('Error:', 'Warning:'))]
    if result.returncode or diagnostics:
        return {
            'status': 'sta_not_clean',
            'returncode': result.returncode,
            'diagnostics': diagnostics[:10],
        }
    arrivals = [
        float(x)
        for x in re.findall(r'(?m)^\s+(\d+(?:\.\d+)?)\s+data arrival time\s*$', checks.read_text())
    ]
    wns = re.search(r'wns\s+(-?\d+(?:\.\d+)?)', result.stdout, re.I)
    tns = re.search(r'tns\s+(-?\d+(?:\.\d+)?)', result.stdout, re.I)
    return {
        'status': 'ok',
        'lhs_concats_expanded': expanded,
        'max_data_arrival_ns': max(arrivals) if arrivals else None,
        'wns_ns': float(wns.group(1)) if wns else None,
        'tns_ns': float(tns.group(1)) if tns else None,
    }


shutil.copyfile(LIBERTY_SRC, HERE / LIBERTY)
try:
    receipt = {'gold': run_sta('gold'), 'gate': run_sta('gate')}
finally:
    (HERE / LIBERTY).unlink(missing_ok=True)
for side in ('gold', 'gate'):
    if receipt[side].get('status') != 'ok':
        print(json.dumps(receipt, indent=2, sort_keys=True))
        sys.exit(f'{side} STA read was not clean — timing numbers withheld (fail-closed).')
ga = receipt['gold']['max_data_arrival_ns']
ta = receipt['gate']['max_data_arrival_ns']
receipt['delta'] = {
    'data_arrival_ns': ta - ga if isinstance(ga, float) and isinstance(ta, float) else None,
    'data_arrival_pct': (ta - ga) / ga * 100 if isinstance(ga, float) and isinstance(ta, float) and ga else None,
}
(HERE / 'timing_yosys66_10ns_2ns_io_replay.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
print(json.dumps(receipt, indent=2, sort_keys=True))
