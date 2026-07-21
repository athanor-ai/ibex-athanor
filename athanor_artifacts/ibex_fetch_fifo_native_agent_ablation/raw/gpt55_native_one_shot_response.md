# GPT-5.5 Native One-Shot Response

Captured from the native one-shot lane. This is raw candidate output for
ablation analysis; it is not an accepted Athanor/Kairos result.

## Status

candidate patch, verified_win

## Candidate patch

```diff
--- a/rtl/ibex_fetch_fifo.sv
+++ b/rtl/ibex_fetch_fifo.sv
@@ -217,7 +217,7 @@
   assign valid_pushed     [DEPTH-1] = valid_q[DEPTH-1] | (in_valid_i & lowest_free_entry[DEPTH-1]);
   assign valid_popped     [DEPTH-1] = pop_fifo ? 1'b0 : valid_pushed[DEPTH-1];
   assign valid_d [DEPTH-1]          = valid_popped[DEPTH-1] & ~clear_i;
-  assign entry_en[DEPTH-1]          = in_valid_i & lowest_free_entry[DEPTH-1];
+  assign entry_en[DEPTH-1]          = valid_d[DEPTH-1] & ~valid_q[DEPTH-1];
   assign rdata_d [DEPTH-1]          = in_rdata_i;
   assign err_d   [DEPTH-1]          = in_err_i;
```

## Rationale

For the top FIFO entry, `rdata_q[DEPTH-1]` and `err_q[DEPTH-1]` only need to
load when the top valid bit newly becomes set. The original enable also fires
on cycles where the incoming value is immediately invalidated by `pop_fifo` or
`clear_i`, causing unnecessary data/error flop activity. The replacement reuses
`valid_d[DEPTH-1]` and suppresses writes unless `valid_q[DEPTH-1]` transitions
from invalid to valid.

For `NUM_REQS=2, ResetAll=0`, this preserves output behavior while reducing
the measured top-entry register enable activity.

## Commands Run And Results

PASS: located target:

```bash
find <local> -path '*/rtl/ibex_fetch_fifo.sv' -print
```

PASS: inspected only target RTL:

```bash
sed -n '1,260p' rtl/ibex_fetch_fifo.sv
sed -n '261,520p' rtl/ibex_fetch_fifo.sv
```

PASS: tool availability:

```bash
command -v yosys
command -v verilator
command -v sv2v
command -v yosys-smtbmc
command -v z3
command -v iverilog
command -v vvp
```

PASS: lint final candidate:

```bash
verilator --lint-only -Wall -Wno-DECLFILENAME -Wno-PINMISSING -Ivendor/lowrisc_ip/ip/prim/rtl -GNUM_REQS=2 -GResetAll=0 <local-tmp>/ibex_fetch_fifo_baseline/ibex_fetch_fifo_cand.sv
```

PASS: formal prep, after stripping assertion macro use in scratch copies only:

```bash
sv2v <local-tmp>/ibex_fetch_fifo_baseline/orig_formal.sv <local-tmp>/ibex_fetch_fifo_baseline/cand_formal.sv <local-tmp>/ibex_fetch_fifo_baseline/equiv_top.sv > <local-tmp>/ibex_fetch_fifo_baseline/equiv_all.v
yosys -q -p 'read_verilog -formal <local-tmp>/ibex_fetch_fifo_baseline/equiv_all.v; prep -top equiv_top; async2sync; opt; write_smt2 -wires <local-tmp>/ibex_fetch_fifo_baseline/equiv.smt2'
```

PASS: bounded equivalence, 20 cycles:

```bash
yosys-smtbmc -s z3 -t 20 <local-tmp>/ibex_fetch_fifo_baseline/equiv.smt2
```

Result: `Status: PASSED`

PASS: temporal induction:

```bash
yosys-smtbmc -s z3 -i -t 20 <local-tmp>/ibex_fetch_fifo_baseline/equiv.smt2
```

Result: `Temporal induction successful. Status: PASSED`

PASS: Yosys synthesis area proxy:

```bash
yosys -p 'read_verilog <local-tmp>/ibex_fetch_fifo_baseline/orig_synth.v; chparam -set NUM_REQS 2 -set ResetAll 0 ibex_fetch_fifo_orig; synth -top ibex_fetch_fifo_orig; stat'
yosys -p 'read_verilog <local-tmp>/ibex_fetch_fifo_baseline/cand_synth.v; chparam -set NUM_REQS 2 -set ResetAll 0 ibex_fetch_fifo_cand; synth -top ibex_fetch_fifo_cand; stat'
```

Result: unchanged totals, both `556` cells, `286` wires, `793` wire bits.

PASS: Yosys timing proxy:

```bash
yosys -p 'read_verilog <local-tmp>/ibex_fetch_fifo_baseline/orig_synth.v; chparam -set NUM_REQS 2 -set ResetAll 0 ibex_fetch_fifo_orig; synth -top ibex_fetch_fifo_orig; ltp -noff'
yosys -p 'read_verilog <local-tmp>/ibex_fetch_fifo_baseline/cand_synth.v; chparam -set NUM_REQS 2 -set ResetAll 0 ibex_fetch_fifo_cand; synth -top ibex_fetch_fifo_cand; ltp -noff'
```

Result: unchanged longest topological path, both length `13`.

PASS: deterministic activity proxy:

```bash
iverilog -g2012 -o <local-tmp>/ibex_fetch_fifo_baseline/tb_activity.vvp <local-tmp>/ibex_fetch_fifo_baseline/sim_modules.v <local-tmp>/ibex_fetch_fifo_baseline/tb_activity.v
vvp <local-tmp>/ibex_fetch_fifo_baseline/tb_activity.vvp
```

Result: `orig_entry_en2=3057 cand_entry_en2=1371 delta=1686`.

PASS: repository not edited:

```bash
git diff -- rtl/ibex_fetch_fifo.sv
```

Result: no output.
