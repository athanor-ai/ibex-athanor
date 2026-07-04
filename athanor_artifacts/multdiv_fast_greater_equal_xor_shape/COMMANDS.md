# Replay Notes

Verify package hashes:

```bash
sha256sum -c SHA256SUMS
```

## Whole-Core Integration Note

`SOURCE_DIFF.patch` renames `ibex_multdiv_fast` to
`ibex_multdiv_fast_gate` so the module-local gold and gate sources can coexist
for package checks. Whole-core replayers must rename the gate module back to
`ibex_multdiv_fast`, or apply only the expression rewrite to the live
`ibex_multdiv_fast` definition, before integrating into `ibex_top`. Otherwise
the top-level build will not instantiate the transformed module.
