# ibex_fetch_fifo native-agent ablation

This package records native one-shot LLM agent runs against the same
`rtl/ibex_fetch_fifo.sv` optimization target as the accepted
`fetch_fifo_err_unaligned_factored` module-local benchmark.

The purpose is to compare a frozen one-response native agent with the Kairos
orchestrated evidence loop. A native lane is allowed one prompt and one final
candidate answer. It may inspect the target RTL and run ordinary local tools,
but it must not use Kairos orchestration, `kairos optimize`, Athanor artifact
directories, prior optimization receipts, or iterative rejection feedback as
solution hints.

This is not a model leaderboard and not a statistical claim. Each lane keeps
the raw response and patch even when the result is rejected. A candidate is not
accepted unless the normal Athanor evidence bar proves equivalence and records
area, timing, and toggle/activity results.

## Lanes

| Lane | Model | Status | Owner | Notes |
| --- | --- | --- | --- | --- |
| Kairos reference | Kairos orchestrated flow | Complete | Dexter | Accepted module-local packet in `../fetch_fifo_err_unaligned_factored/`. |
| GPT-5.5 native one-shot | `gpt-5.5` | Raw candidate captured | Dexter | Native self-report claims a verified win; Athanor verdict remains pending until full selected replay closes. |
| Opus 4.8 native one-shot | `opus-4.8` | Planned | Quan | Same prompt hash and scoring rubric; not blocking the first package. |

## Scoring Contract

For each native lane, capture:

- raw model response and any candidate patch;
- whether the model used forbidden context or touched non-target files;
- parse/elaboration, synthesis, formal/equivalence, area, timing, and
  toggle/activity results when run;
- final proposal-quality classification: `verified_win`, `rejected_unverified`,
  `no_candidate`, `syntax_or_elab_failure`, or `inconclusive`.

The accepted Kairos reference is the comparison point, not a hint source for
native agents.
