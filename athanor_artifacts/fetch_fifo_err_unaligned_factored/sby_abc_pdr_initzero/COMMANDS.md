# Replay Commands

Set the selected OSS CAD Suite tools:

```bash
export PATH=/path/to/oss-cad-suite/bin:$PATH
export SBY=/path/to/oss-cad-suite/bin/sby
```

Verify the nested packet:

```bash
sha256sum -c SHA256SUMS
./replay_sby_pdr.sh
sha256sum -c SHA256SUMS
```

Expected replay result:

- Positive relation-aware SBY/ABC PDR run exits `0` and writes
  `PASS 0 0` in `sby_pdr_replay_out/positive/initzero_pdr/status`.
- Mutant run exits nonzero and writes `FAIL 2 0` in
  `sby_pdr_replay_out/mutant/initzero_pdr/status`.

Generated `sby_pdr_replay_out/` logs are replay output, not committed source.
