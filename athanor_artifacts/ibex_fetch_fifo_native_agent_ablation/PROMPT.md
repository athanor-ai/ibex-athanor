# Native One-Shot Agent Prompt

Use this prompt verbatim for each native one-shot lane.

```text
You are a native LLM coding agent evaluating a single-shot RTL optimization task.

Target: rtl/ibex_fetch_fifo.sv in this repository.

Goal: propose the smallest behavior-preserving RTL change you can find that improves synthesis area, timing, or toggle/activity for the default Ibex fetch FIFO configuration: NUM_REQS=2, ResetAll=0.

Hard constraints:
- Preserve the module interface, parameter names, reset behavior, clear_i behavior, ready/valid behavior, compressed-instruction alignment behavior, unaligned instruction behavior, and error/err_plus2 behavior.
- Do not change files outside rtl/ibex_fetch_fifo.sv unless required only for a local test harness; keep the final patch limited to rtl/ibex_fetch_fifo.sv.
- Do not use Kairos orchestration, kairos optimize, Athanor artifact directories, prior Athanor result packages, or existing optimization receipts as solution hints.
- You may inspect the target RTL and run ordinary open-source local tools if available.
- Produce one final answer only: a unified diff, the rationale, and the exact commands you ran with pass/fail results.

Acceptance bar:
- A candidate is only a win if it parses/elaborates, proves equivalent to the original for the stated configuration, and improves at least one measured PPA proxy without regressing the others under the recorded toolchain.
- If you cannot find such a candidate, say so and return either no patch or a clearly labeled rejected patch.
```
